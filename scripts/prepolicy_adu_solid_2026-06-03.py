"""
Pre-policy ADU backfill — SOLID set only (CKAN-anchored + PRIMARY-PERMIT-CONFIRMED).
DRY by default; --commit to write. Base: bdadce65 (post-Pass-2).
A completion is ingested only if a primary ADU-construction / new-structural permit
Finaled that year exists (BUILD signal or confirmed reclaim). WEAK (alteration only)
and NONE (no permit) are HELD for Accela. Stricter than CY2023 Pass 1 (consistency
flag documented in the change-note).
"""
import sqlite3, openpyxl, glob, re, sys
from datetime import date, datetime
from collections import defaultdict
DB='databases/berkeley_housing_v2.db'
PROV="CKAN parcel-pointer + CPRA primary permit (2018-2022) + Alameda assessor; pre-policy ADU SOLID 2026-06-03"
DRY=('--commit' not in sys.argv)
def pdate(x):
    if isinstance(x,datetime): return x.date()
    if isinstance(x,date): return x
    s=str(x).strip()
    try: return date.fromisoformat(s[:10]) if s and s.lower() not in('none','nan') else None
    except: return None
def num(x):
    try: return int(float(x))
    except: return 0
def napn(a): return re.sub(r'[^\d]','',str(a or ''))
def naddr(a):
    a=(a or '').upper().split(',')[0]; mt=re.match(r'\s*(\d+)',a)
    if not mt: return ''
    rest=re.sub(r'^\s*\d+(-\d+)?\s+','',a); w=re.sub(r'[^A-Z ]','',rest).split()
    return mt.group(1)+'|'+(w[0] if w else '')
BUILD=re.compile(r'''(
  \bj?adu\b | accessory\s+dwelling | accessory\s+(structure|unit|building) | in-?law\s+unit |
  \bdwelling\s+unit\b | second\s+(dwelling\s+)?unit |
  \bnew\b[\s\S]{0,40}?\b(home|house|residence|dwelling|apartment|sfr|single[\s-]?family|duplex|cottage|bungalow|adu|residential\s+building|mini-?dorm) |
  construct\w*[\s\S]{0,40}?\b(home|house|residence|dwelling|adu|unit|duplex|residential|sf\b) |
  convert\w*[\s\S]{0,55}?\b(adu|dwelling|unit|residence|duplex|habitable|apartment|studio\s+dwelling) |
  change\s+(of\s+)?use[\s\S]{0,55}?\b(residen|dwelling|single\s+family|apartment) |
  garage[\s\S]{0,30}?\b(adu|dwelling|studio|unit|conversion) |
  legaliz\w*[\s\S]{0,30}?\b(adu|unit|dwelling|conversion) |
  create[\s\S]{0,30}?\b(adu|unit|jadu|dwelling) |
  manufactured\s+(unit|home) | live[\s/-]?work | creation\s+of[\s\S]{0,15}unit
)''', re.I|re.X)
# confirmed reclaims (keyword-tail misses): "(N)", "SADU", "secondary unit", garage/in-law/creation
FORCE_PRIMARY={'B2014-02947','B2017-01506','B2018-00483','B2018-03653','B2019-02673','B2020-00794','B2017-03352','B2020-01576','B2018-02859'}
FORCE_EXCLUDE={'B2017-03905'}  # 2327 Curtis (habitable accessory space, no kitchen/bath)

by_parcel=defaultdict(list)
for f in sorted(glob.glob('data/raw/cpra-downloads/*.xlsx')):
    wb=openpyxl.load_workbook(f,read_only=True);ws=wb.active
    rows=list(ws.iter_rows(min_row=8,values_only=True));hdr=[(h or '').strip() for h in rows[0]];ix={h:i for i,h in enumerate(hdr)}
    for r in rows[1:]:
        if not any(r):continue
        fin=pdate(r[ix['Finaled Date']]) or pdate(r[ix['Completed Date']])
        if not fin or fin.year<2018 or fin.year>2022: continue
        by_parcel[napn(r[ix['Parcel Number']])].append({'bp':str(r[ix['PermitNumber']] or ''),'finy':fin.year,'fin':fin.isoformat(),
            'num':num(r[ix['NumberUnits']]),'add':num(r[ix['UnitsAdded']]),'adu':str(r[ix['ADU']] or '').strip().lower()=='yes',
            'full':str(r[ix['WorkDescription']] or ''),'desc':str(r[ix['WorkDescription']] or '')[:120],'val':num(r[ix['JobValuation']])})
    wb.close()
m=sqlite3.connect('databases/hcd_apr_mirror.db'); m.row_factory=sqlite3.Row
v=sqlite3.connect(DB); v.row_factory=sqlite3.Row
b=sqlite3.connect('databases/berkeley.db'); b.row_factory=sqlite3.Row
CO=['CO_ACUTELY_LOW_INCOME_DR','CO_ACUTELY_LOW_INCOME_NDR','CO_EXTREMELY_LOW_INCOME_DR','CO_EXTREMELY_INCOME_NDR','CO_VLOW_INCOME_DR','CO_VLOW_INCOME_NDR','CO_LOW_INCOME_DR','CO_LOW_INCOME_NDR','CO_MOD_INCOME_DR','CO_MOD_INCOME_NDR','CO_ABOVE_MOD_INCOME']
allapn=set(napn(r['apn']) for r in v.execute("SELECT pk.apn FROM project_parcels pp JOIN parcels pk ON pk.id=pp.parcel_id WHERE pk.apn IS NOT NULL"))
alladdr=set(naddr(r['a']) for r in v.execute("SELECT address_display a FROM v_projects_flat") if naddr(r['a']))
existing_parcels={napn(r['apn']):r['id'] for r in v.execute("SELECT id,apn FROM parcels WHERE apn IS NOT NULL")}
bk={napn(r['apn_norm']):{'lat':r['Latitude'],'lon':r['Longitude']} for r in b.execute("SELECT apn_norm,Latitude,Longitude FROM parcels_full WHERE apn_norm IS NOT NULL")}
DEMO_ONLY=re.compile(r'^\s*(demoli|.{0,30}\bdemo\b\s*$)',re.I)

ingest=[]; nocoord=[]
for y in range(2018,2023):
    seen={}
    for r in m.execute(f"SELECT APN,STREET_ADDRESS,{','.join(CO)} FROM table_a2 WHERE YEAR={y} AND JURIS_NAME='BERKELEY'"):
        u=sum(num(r[c]) for c in CO)
        if u<=0 or u>4: continue
        k=napn(r['APN']) or 'X'+naddr(r['STREET_ADDRESS'])
        if k not in seen or u>seen[k][0]: seen[k]=(u,r['APN'],r['STREET_ADDRESS'])
    for k,(cku,apnraw,addr) in seen.items():
        a=napn(apnraw)
        if not a or a in allapn or naddr(addr) in alladdr: continue
        cands=[p for p in by_parcel.get(a,[]) if p['finy']==y]
        build=[p for p in cands if (p['bp'] in FORCE_PRIMARY) or (p['bp'] not in FORCE_EXCLUDE and BUILD.search(p['full'] or '') and not DEMO_ONLY.search(p['full'] or ''))]
        if not build: continue   # WEAK/NONE -> HELD for Accela
        best=sorted(build,key=lambda p:(p['adu'],max(p['num'],p['add']),p['fin']),reverse=True)[0]
        net=best['add'] if best['add']>0 else (1 if best['adu'] else best['num']); net=min(max(net,1),4)
        p=bk.get(a,{})
        rec={'y':y,'apn':apnraw.strip(),'apnn':a,'addr':addr.strip(),'naddr':naddr(addr),'net':net,'bp':best['bp'],'fin':best['fin'],
             'val':best['val'],'desc':best['desc'],'lat':p.get('lat'),'lon':p.get('lon')}
        ingest.append(rec)
        if not (p.get('lat') and p.get('lon')): nocoord.append(rec)

print("="*60)
print(f"{'Year':5} {'SOLID parcels':>14} {'units':>7}")
print("="*60)
for y in range(2018,2023):
    yi=[r for r in ingest if r['y']==y]
    print(f"{y:5} {len(yi):>14} {sum(r['net'] for r in yi):>7}")
print("="*60)
print(f"  SOLID TOTAL: {len(ingest)} parcels / {sum(r['net'] for r in ingest)} units | null-coord={len(nocoord)}")

cur=v.cursor(); cur.execute("PRAGMA foreign_keys=OFF"); cur.execute("BEGIN")
try:
    exp={'2023':631,'2024':709,'2025':531,'2026':216}
    n0=cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    used=set(r[0] for r in cur.execute("SELECT canonical_address FROM projects"))
    for r in ingest:
        pcid=existing_parcels.get(r['apnn'])
        if pcid is None:
            cur.execute("INSERT INTO parcels (city_id,apn,address,geometry_source,notes) VALUES (1,?,?,?,?)",(r['apn'],r['addr'],'alameda_assessor',PROV)); pcid=cur.lastrowid; existing_parcels[r['apnn']]=pcid
        cad=r['addr'] if r['addr'] not in used else f"{r['addr']} [{r['bp']}]"; used.add(cad)
        cur.execute("INSERT INTO projects (city_id,canonical_name,canonical_address,normalized_address,latitude,longitude,current_stage_type_id) VALUES (1,?,?,?,?,?,6)",(r['addr'],cad,r['naddr'],r['lat'],r['lon'])); pid=cur.lastrowid
        cur.execute("INSERT INTO documents (project_id,title,permit_number,source_system,notes) VALUES (?,?,?,?,?)",(pid,'CPRA BP Annual Permit Report 2018-2022',r['bp'],'cpra',PROV)); doc=cur.lastrowid
        cur.execute("INSERT INTO project_versions (project_id,version_label,version_type_id,effective_date,total_units,is_current,source_document_id,asserted_by,confidence_type_id,description) VALUES (?,?,5,?,?,1,?,?,2,?)",(pid,'as-built (CPRA CO)',r['fin'],r['net'],doc,PROV,r['desc'])); vid=cur.lastrowid
        cur.execute("UPDATE projects SET current_version_id=? WHERE id=?",(vid,pid))
        cur.execute("INSERT INTO unit_program (project_version_id,bedroom_count,tenure_type_id,unit_count,source_document_id,asserted_by,confidence_type_id,notes) VALUES (?,NULL,8,?,?,?,2,?)",(vid,r['net'],doc,PROV,'bedroom NULL + tenure Unknown')); up=cur.lastrowid
        cur.execute("INSERT INTO unit_program_affordability (unit_program_id,income_category_id,unit_count,source_document_id,asserted_by,confidence_type_id) VALUES (?,6,?,?,?,2)",(up,r['net'],doc,PROV))
        cur.execute("INSERT INTO project_parcels (project_id,parcel_id,is_primary) VALUES (?,?,1)",(pid,pcid))
        cur.execute("INSERT INTO permits (project_id,source_system,permit_number,permit_type_id,issued_date,finaled_date,valuation,description) VALUES (?,?,?,5,?,?,?,?)",(pid,'cpra',r['bp'],None,r['fin'],r['val'],r['desc'])); perm=cur.lastrowid
        cur.execute("INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,17,?,?,1,2,'inferred',?)",(pid,r['fin'],perm,'CO from CPRA finaled date (primary-permit-confirmed)'))
        cur.execute("INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,26,'2026-06-03',?,1,2,'inferred',?)",(pid,perm,'Permit classified PRIMARY (CKAN-anchored + primary-permit-confirmed SOLID)'))
    post={yr:cur.execute(f"SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='{yr}' AND project_id NOT IN (165,170,171,177)").fetchone()[0] for yr in exp}
    py={yr:cur.execute(f"SELECT COUNT(*) c, COALESCE(SUM(total_units),0) u FROM v_projects_flat WHERE substr(co_issued_date,1,4)='{yr}' AND project_id NOT IN (165,170,171,177)").fetchone() for yr in ('2018','2019','2020','2021','2022')}
    fk=cur.execute("PRAGMA foreign_key_check").fetchall(); integ=cur.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"\n=== DRY-RUN VERIFICATION ===")
    print(f"  inserted {len(ingest)} projects (projects {n0}->{cur.execute('SELECT COUNT(*) FROM projects').fetchone()[0]})")
    print(f"  NEW pre-policy SOLID: " + " ".join(f"CY{y}={py[y]['u']}u/{py[y]['c']}p" for y in ('2018','2019','2020','2021','2022')))
    print(f"  2023-26 triad UNCHANGED? " + " ".join(f"CY{y}:{post[y]}{'OK' if post[y]==exp[y] else f'!=exp{exp[y]}'}" for y in exp))
    print(f"  FK={len(fk)} integrity={integ}")
    okk=all(post[y]==exp[y] for y in exp) and len(fk)==0 and integ=='ok'
    if okk and not DRY:
        cur.execute("PRAGMA foreign_keys=ON"); v.commit(); print("\nALL CHECKS PASS -> COMMITTED")
    elif okk:
        v.rollback(); print("\nALL CHECKS PASS -> DRY RUN rolled back")
    else:
        v.rollback(); print("\n*** CHECK FAILED -> ROLLED BACK ***")
except Exception as e:
    v.rollback(); print("EXCEPTION -> ROLLED BACK:", repr(e))
