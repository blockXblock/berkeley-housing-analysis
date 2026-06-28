# SEQUESTERED 2026-06-28 — one-time pre-policy ADU backfill PREVIEW (2018-2022), CKAN-anchored.
# Superseded by the v4 event-stream rebuild; kept for provenance, DO NOT re-run. (.py disposition rule)
"""
Pre-policy ADU backfill PREVIEW 2018-2022 (read-only, DRY by default).
Pure-CPRA method: ADU/small (<=4u net-new) permits finaled per year, ADU-aware
classified (drop subsidiary), not already in v2, parcel-deduped, coords from assessor.
Same RIGOR as CY2023 Pass 1. Snapshot: keep_snapshot_2026-06-03_pre-prepolicy-adu.db (a5e63b1b).
ADU-ONLY: 2022's 6 majors are a separate later pass.
"""
import sqlite3, openpyxl, glob, re, sys
from datetime import date, datetime
from collections import defaultdict
DB='databases/berkeley_housing_v2.db'
PROV="CPRA BP_Annual Permit Report 2018-2022 + Alameda assessor; pre-policy ADU backfill 2026-06-03"
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
SPURIOUS=re.compile(r'\b(solar|photovolta\w*|pv|modules?|window|door|sign|water heater|furnace|heat pump|siding|insulation|drywall|remodel|temp(?:orary)? power|temp meter|meter|washer|dryer|reroof|re-roof|shoring|grading|ev charg\w*|repair)\b',re.I)
SPELLED=re.compile(r'\b(one|two|three|four|five|six|seven|eight|nine|ten)[-\s](stor(?:y|ey|ies)|units?|family)',re.I)
DIGITNUM=re.compile(r'\b\d+[-\s]?(?:unit|story|storey|stories|units)\b',re.I)
NEWBUILD=re.compile(r'\b(?:new|construct\w*)\b[\s\S]{0,40}?\b(?:residence|home|house|building|dwelling|apartment|adus?|sfr|single[-\s]?family|condo|congregate|senior living)\b',re.I)
BLDGPHR=re.compile(r'\b(apartment building|mixed[-\s]?use building|multi[-\s]?family|residential (?:development|apartment|building))\b',re.I)
DEMO=re.compile(r'^\s*demoli',re.I)
ADUVERB=re.compile(r'(\bj?adu\b|accessory dwelling|legaliz\w*|convert\w*[\s\S]{0,35}?\b(?:adu|dwelling|unit)\b|garage[\s\S]{0,20}?(?:adu|dwelling|into|conversion)|conversion of[\s\S]{0,45}?\binto\b)',re.I)
def is_struct(d): return bool(SPELLED.search(d) or DIGITNUM.search(d) or NEWBUILD.search(d) or BLDGPHR.search(d))
def classify(d,val,adu):
    d=d or ''
    if DEMO.search(d): return 'SUBSIDIARY'
    if adu or ADUVERB.search(d): return 'PRIMARY'
    if is_struct(d): return 'PRIMARY'
    if SPURIOUS.search(d): return 'SUBSIDIARY'
    return 'PRIMARY' if (val or 0)>=1000000 else 'AMBIGUOUS'

# load CPRA (both files) -> rows with parsed fields
recs=[]
for f in sorted(glob.glob('data/raw/cpra-downloads/*.xlsx')):
    wb=openpyxl.load_workbook(f,read_only=True);ws=wb.active
    rows=list(ws.iter_rows(min_row=8,values_only=True));hdr=[(h or '').strip() for h in rows[0]];ix={h:i for i,h in enumerate(hdr)}
    for r in rows[1:]:
        if not any(r):continue
        fin=pdate(r[ix['Finaled Date']]) or pdate(r[ix['Completed Date']])
        if not fin or fin.year<2018 or fin.year>2022: continue
        adu=str(r[ix['ADU']] or '').strip().lower()=='yes'
        ua=num(r[ix['UnitsAdded']]); net = ua if ua>0 else (1 if adu else 0)
        if net<=0 or net>4: continue   # ADU/small only
        recs.append({'apn':napn(r[ix['Parcel Number']]),'apnraw':str(r[ix['Parcel Number']] or ''),'addr':str(r[ix['StreetNumber']] or '')+' '+str(r[ix['StreetName']] or ''),
            'yr':fin.year,'fin':fin.isoformat(),'bp':str(r[ix['PermitNumber']] or ''),'net':net,'adu':adu,
            'desc':str(r[ix['WorkDescription']] or '')[:120],'fulldesc':str(r[ix['WorkDescription']] or ''),'val':num(r[ix['JobValuation']])})
    wb.close()

v=sqlite3.connect(DB); v.row_factory=sqlite3.Row
b=sqlite3.connect('databases/berkeley.db'); b.row_factory=sqlite3.Row
allapn=set(napn(r['apn']) for r in v.execute("SELECT pk.apn FROM project_parcels pp JOIN parcels pk ON pk.id=pp.parcel_id WHERE pk.apn IS NOT NULL"))
alladdr=set(naddr(r['a']) for r in v.execute("SELECT address_display a FROM v_projects_flat") if naddr(r['a']))
bk={napn(r['apn_norm']):{'lat':r['Latitude'],'lon':r['Longitude'],'use':r['UseCode'],'geom':r['the_geom'] is not None} for r in b.execute("SELECT apn_norm,Latitude,Longitude,UseCode,the_geom FROM parcels_full WHERE apn_norm IS NOT NULL")}

# assemble per year: classify, drop subsidiary, dedup by parcel-key within year, not-in-v2
byyear=defaultdict(lambda:{'ing':{}, 'sub':[], 'amb':[]})
for r in recs:
    if r['apn'] in allapn or naddr(r['addr']) in alladdr: continue
    cls=classify(r['desc'],r['val'],r['adu'])
    r['cls']=cls
    Y=byyear[r['yr']]
    if cls=='SUBSIDIARY': Y['sub'].append(r); continue
    k=r['apn'] or 'X'+r['bp']
    cur=Y['ing']
    if k not in cur or r['net']>cur[k]['net']: cur[k]=r

print("="*78)
print(f"{'Year':5} {'parcels':>8} {'units':>6} | {'PRIMARY':>8} {'AMBIG':>6} {'SUBSID(dropped)':>16} {'null-coord':>11}")
print("="*78)
amb_all=[]
for y in range(2018,2023):
    Y=byyear[y]; ing=list(Y['ing'].values())
    prim=[r for r in ing if r['cls']=='PRIMARY']; amb=[r for r in ing if r['cls']=='AMBIGUOUS']
    amb_all+=[(y,r) for r in amb]
    nocoord=[r for r in ing if not (bk.get(r['apn'],{}).get('lat'))]
    print(f"{y:5} {len(ing):>8} {sum(r['net'] for r in ing):>6} | {len(prim):>8} {len(amb):>6} {len(Y['sub']):>16} {len(nocoord):>11}")
print("="*78)
print(f"  TOTAL pre-policy ADU (2018-2022): {sum(len(byyear[y]['ing']) for y in range(2018,2023))} parcels / "
      f"{sum(r['net'] for y in range(2018,2023) for r in byyear[y]['ing'].values())} units")

print(f"\n=== ALL AMBIGUOUS across 2018-2022 ({len(amb_all)}) — full descriptions for adjudication ===")
for y,r in amb_all:
    print(f"  {y} {r['addr'][:22]:22} {r['bp']} net={r['net']} val={r['val']} ADU={r['adu']}")
    print(f"     FULL: {r['fulldesc'][:240]}")

# SUBSIDIARY flags (scrutiny)
sub_all=[(y,r) for y in range(2018,2023) for r in byyear[y]['sub']]
print(f"\n=== SUBSIDIARY (dropped, 2641-College pattern) — {len(sub_all)} total; sample 8 ===")
for y,r in sub_all[:8]:
    kw=SPURIOUS.search(r['desc'] or ''); print(f"  {y} {r['addr'][:22]:22} {r['bp']} [{kw.group(0) if kw else '-'}] '{r['desc'][:44]}'")

# DRY-RUN: insert all, verify existing years unchanged
cur=v.cursor(); cur.execute("PRAGMA foreign_keys=OFF"); cur.execute("BEGIN")
try:
    pre={yr:cur.execute(f"SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='{yr}' AND project_id NOT IN (165,170,171,177)").fetchone()[0] for yr in ('2023','2024','2025','2026')}
    n0=cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    ins=0
    for y in range(2018,2023):
        for r in byyear[y]['ing'].values():
            p=bk.get(r['apn'],{})
            cur.execute("INSERT INTO parcels (city_id,apn,address,geometry_source,notes) VALUES (1,?,?,?,?)",(r['apnraw'],r['addr'].strip(),'alameda_assessor',PROV)); pc=cur.lastrowid
            cur.execute("INSERT INTO projects (city_id,canonical_name,canonical_address,normalized_address,latitude,longitude,current_stage_type_id) VALUES (1,?,?,?,?,?,6)",(r['addr'].strip(),r['addr'].strip(),naddr(r['addr']),p.get('lat'),p.get('lon'))); pid=cur.lastrowid
            cur.execute("INSERT INTO documents (project_id,title,permit_number,source_system,notes) VALUES (?,?,?,?,?)",(pid,'CPRA BP Annual Permit Report 2018-2022',r['bp'],'cpra',PROV)); doc=cur.lastrowid
            cur.execute("INSERT INTO project_versions (project_id,version_label,version_type_id,effective_date,total_units,is_current,source_document_id,asserted_by,confidence_type_id,description) VALUES (?,?,5,?,?,1,?,?,2,?)",(pid,'as-built (CPRA CO)',r['fin'],r['net'],doc,PROV,r['desc'])); vid=cur.lastrowid
            cur.execute("UPDATE projects SET current_version_id=? WHERE id=?",(vid,pid))
            cur.execute("INSERT INTO unit_program (project_version_id,bedroom_count,tenure_type_id,unit_count,source_document_id,asserted_by,confidence_type_id,notes) VALUES (?,NULL,8,?,?,?,2,?)",(vid,r['net'],doc,PROV,'bedroom NULL + tenure Unknown')); up=cur.lastrowid
            cur.execute("INSERT INTO unit_program_affordability (unit_program_id,income_category_id,unit_count,source_document_id,asserted_by,confidence_type_id) VALUES (?,6,?,?,?,2)",(up,r['net'],doc,PROV))
            cur.execute("INSERT INTO project_parcels (project_id,parcel_id,is_primary) VALUES (?,?,1)",(pid,pc))
            cur.execute("INSERT INTO permits (project_id,source_system,permit_number,permit_type_id,issued_date,finaled_date,valuation,description) VALUES (?,?,?,5,?,?,?,?)",(pid,'cpra',r['bp'],None,r['fin'],r['val'],r['desc'])); perm=cur.lastrowid
            cur.execute("INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,17,?,?,1,2,'inferred',?)",(pid,r['fin'],perm,'CO from CPRA finaled date'))
            et=27 if r['cls']=='SUBSIDIARY' else 26
            cur.execute("INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,?,'2026-06-03',?,1,2,'inferred',?)",(pid,et,perm,f"Permit classified {'PRIMARY' if et==26 else 'SUBSIDIARY'} (ADU-aware rule, pre-policy backfill)"))
            ins+=1
    post={yr:cur.execute(f"SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='{yr}' AND project_id NOT IN (165,170,171,177)").fetchone()[0] for yr in ('2023','2024','2025','2026')}
    py={yr:cur.execute(f"SELECT COUNT(*) c, COALESCE(SUM(total_units),0) u FROM v_projects_flat WHERE substr(co_issued_date,1,4)='{yr}' AND project_id NOT IN (165,170,171,177)").fetchone() for yr in ('2018','2019','2020','2021','2022')}
    fk=cur.execute("PRAGMA foreign_key_check").fetchall(); integ=cur.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"\n=== DRY-RUN VERIFICATION ===")
    print(f"  inserted {ins} ADU projects (projects {n0}->{cur.execute('SELECT COUNT(*) FROM projects').fetchone()[0]})")
    print(f"  NEW pre-policy years: " + " ".join(f"CY{y}={py[y]['u']}({py[y]['c']}p)" for y in ('2018','2019','2020','2021','2022')))
    print(f"  EXISTING years UNCHANGED? " + " ".join(f"CY{y}:{pre[y]}->{post[y]}{'OK' if pre[y]==post[y] else ' CHANGED!'}" for y in ('2023','2024','2025','2026')))
    print(f"  FK={len(fk)} integrity={integ}")
    v.rollback(); print("  -> DRY RUN rolled back (no write)")
except Exception as e:
    v.rollback(); print("EXCEPTION -> ROLLED BACK:", repr(e))
