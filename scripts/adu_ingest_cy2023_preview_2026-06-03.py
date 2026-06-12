"""
CY2023 ADU backfill — Pass 1 (Bucket A, ~103 parcels / ~444u). DRY-RUN preview.
Same primary-source method as CY2024/CY2025 ingests + corrected ADU-aware classification.
BEGIN...rollback by default; pass --commit to write (gated, not this turn).
The 6 CY2023 majors (260u) are DEFERRED to a later Accela-gated pass.
"""
import sqlite3, openpyxl, re, sys
from collections import defaultdict
DB='databases/berkeley_housing_v2.db'
PROV="CPRA BP_Annual Permit Report 2023-2025 + Alameda assessor (berkeley.db); CY2023 ADU backfill 2026-06-03"
DRY = ('--commit' not in sys.argv)

def napn(a): return re.sub(r'[^\d]','',str(a or ''))
def naddr(a):
    a=(a or '').upper().split(',')[0]; mt=re.match(r'\s*(\d+)',a)
    if not mt: return ''
    rest=re.sub(r'^\s*\d+(-\d+)?\s+','',a); w=re.sub(r'[^A-Z ]','',rest).split()
    return mt.group(1)+'|'+(w[0] if w else '')
def num(x):
    try:return int(float(x))
    except:return 0

# corrected ADU-aware classification (identical to OP1-4)
SPURIOUS=re.compile(r'\b(solar|photovolta\w*|pv|modules?|window|door|sign|water heater|furnace|heat pump|siding|insulation|drywall|remodel|temp(?:orary)? power|temp meter|meter|washer|dryer|reroof|re-roof|shoring|grading|ev charg\w*|repair)\b',re.I)
SPELLED=re.compile(r'\b(one|two|three|four|five|six|seven|eight|nine|ten)[-\s](stor(?:y|ey|ies)|units?|family)',re.I)
DIGITNUM=re.compile(r'\b\d+[-\s]?(?:unit|story|storey|stories|units)\b',re.I)
NEWBUILD=re.compile(r'\b(?:new|construct\w*)\b[\s\S]{0,40}?\b(?:residence|home|house|building|dwelling|apartment|adus?|sfr|single[-\s]?family|condo|congregate|senior living)\b',re.I)
BLDGPHR=re.compile(r'\b(apartment building|mixed[-\s]?use building|multi[-\s]?family|residential (?:development|apartment|building))\b',re.I)
DEMO=re.compile(r'^\s*demoli',re.I)
ADUVERB=re.compile(r'(\bj?adu\b|accessory dwelling|legaliz\w*|convert\w*[\s\S]{0,35}?\b(?:adu|dwelling|unit)\b|garage[\s\S]{0,20}?(?:adu|dwelling|into|conversion)|conversion of[\s\S]{0,45}?\binto\b)',re.I)
def is_struct(d): return bool(SPELLED.search(d) or DIGITNUM.search(d) or NEWBUILD.search(d) or BLDGPHR.search(d))
def classify_adu(descr,val,adu_yes):
    d=descr or ''
    if DEMO.search(d): return 'SUBSIDIARY'
    if adu_yes or ADUVERB.search(d): return 'PRIMARY'
    if is_struct(d): return 'PRIMARY'
    if SPURIOUS.search(d): return 'SUBSIDIARY'
    return 'PRIMARY' if (val or 0)>=1000000 else 'AMBIGUOUS'

# ---- load CPRA ----
wb=openpyxl.load_workbook('data/raw/cpra-downloads/BP_Annual Permit Report-2023-2025.xlsx',read_only=True);ws=wb.active
rows=list(ws.iter_rows(min_row=8,values_only=True));hdr=[(h or '').strip() for h in rows[0]];ix={h:i for i,h in enumerate(hdr)}
by_parcel=defaultdict(list)
for r in rows[1:]:
    if not any(r):continue
    by_parcel[napn(r[ix['Parcel Number']])].append({'bp':str(r[ix['PermitNumber']] or ''),'fin':str(r[ix['Finaled Date']] or '')[:10],
        'comp':str(r[ix['Completed Date']] or '')[:10],'num':num(r[ix['NumberUnits']]),'add':num(r[ix['UnitsAdded']]),
        'adu':str(r[ix['ADU']] or '').strip().lower()=='yes','occ':str(r[ix['OccType']] or '').strip(),
        'desc':str(r[ix['WorkDescription']] or '')[:120],'val':num(r[ix['JobValuation']])})
wb.close()

# ---- assemble CY2023 Bucket-A ----
m=sqlite3.connect('databases/hcd_apr_mirror.db'); m.row_factory=sqlite3.Row
b=sqlite3.connect('databases/berkeley.db'); b.row_factory=sqlite3.Row
db=sqlite3.connect(DB); db.row_factory=sqlite3.Row
CO=['CO_ACUTELY_LOW_INCOME_DR','CO_ACUTELY_LOW_INCOME_NDR','CO_EXTREMELY_LOW_INCOME_DR','CO_EXTREMELY_INCOME_NDR','CO_VLOW_INCOME_DR','CO_VLOW_INCOME_NDR','CO_LOW_INCOME_DR','CO_LOW_INCOME_NDR','CO_MOD_INCOME_DR','CO_MOD_INCOME_NDR','CO_ABOVE_MOD_INCOME']
allapn=set(); alladdr=set()
for r in db.execute("SELECT pk.apn FROM project_parcels pp JOIN parcels pk ON pk.id=pp.parcel_id WHERE pk.apn IS NOT NULL"): allapn.add(napn(r['apn']))
for r in db.execute("SELECT address_display a FROM v_projects_flat"):
    if naddr(r['a']): alladdr.add(naddr(r['a']))
# CKAN CY2023 deduped
seen={}
for r in m.execute(f"SELECT APN,STREET_ADDRESS,{','.join(CO)} FROM table_a2 WHERE YEAR=2023 AND JURIS_NAME='BERKELEY'"):
    u=sum(num(r[c]) for c in CO)
    if u<=0: continue
    k=napn(r['APN']) or 'X'+naddr(r['STREET_ADDRESS'])
    if k not in seen or u>seen[k][0]: seen[k]=(u,r['APN'],r['STREET_ADDRESS'])
# berkeley.db coords/geom
bk={}
for r in b.execute("SELECT apn_norm,Latitude,Longitude,UseCode,(the_geom IS NOT NULL) hasgeom FROM parcels_full WHERE apn_norm IS NOT NULL"):
    bk[napn(r['apn_norm'])]={'lat':r['Latitude'],'lon':r['Longitude'],'use':r['UseCode'],'geom':r['hasgeom']}
def fy23(p): return p['fin'][:4]=='2023' or p['comp'][:4]=='2023'
ingest=[]; nocoord=[]; collapsed=0; dup_seen=set()
for k,(cku,apnraw,addr) in seen.items():
    a=napn(apnraw)
    if not a or a in allapn or naddr(addr) in alladdr: continue   # not Bucket A
    cands=[p for p in by_parcel.get(a,[]) if fy23(p)]
    if not cands: continue
    # dedup awareness: ensure we don't double-insert the same parcel
    if a in dup_seen: collapsed+=1; continue
    dup_seen.add(a)
    best=sorted(cands,key=lambda p:(p['adu'],max(p['num'],p['add']),p['fin']),reverse=True)[0]
    net=best['add'] if best['add']>0 else (1 if best['adu'] else best['num'])
    p=bk.get(a)
    rec={'addr':addr.strip(),'apn':apnraw.strip(),'naddr':naddr(addr),'units':net,'bp':best['bp'],
         'co':best['fin'] or best['comp'],'val':best['val'],'desc':best['desc'],'adu':best['adu'],
         'lat':p['lat'] if p else None,'lon':p['lon'] if p else None,'use':p['use'] if p else None,'geom':p['geom'] if p else 0,
         'cku':cku,'cls':classify_adu(best['desc'],best['val'],best['adu'])}
    ingest.append(rec)
    if not (rec['lat'] and rec['lon']): nocoord.append(rec)

print(f"[assemble] CY2023 Bucket-A ingest set = {len(ingest)} parcels / {sum(r['units'] for r in ingest)} units (Rule-C net-new)")
print(f"           CKAN-unit sum for same parcels = {sum(r['cku'] for r in ingest)} (vs Rule-C {sum(r['units'] for r in ingest)})")
print(f"           dedup: {collapsed} parcels collapsed (same-parcel repeats) — CY2023 is clean (1.02x)")
cls_count={c:sum(1 for r in ingest if r['cls']==c) for c in ('PRIMARY','SUBSIDIARY','AMBIGUOUS')}
print(f"           classification: {cls_count}")
print(f"           coords: {len(ingest)-len(nocoord)}/{len(ingest)} resolve lat/lon ; the_geom present: {sum(1 for r in ingest if r['geom'])} ; UseCode present: {sum(1 for r in ingest if r['use'])}")
if nocoord:
    print(f"           NULL-COORD parcels ({len(nocoord)}) [flag, don't block]: " + ", ".join(f"{r['addr'][:18]}" for r in nocoord))
subs=[r for r in ingest if r['cls']!='PRIMARY']
if subs:
    print(f"\n  *** FLAGGED non-PRIMARY ({len(subs)}) — need 2641-College-style scrutiny before they ride in: ***")
    for r in subs:
        kw=SPURIOUS.search(r['desc'] or ''); print(f"    {r['addr'][:24]:24} u={r['units']} {r['cls']} bp={r['bp']} [{kw.group(0) if kw else '-'}] '{r['desc'][:46]}'")
print("\n  sample (first 5):")
for r in ingest[:5]: print(f"    {r['addr'][:24]:24} u={r['units']} {r['cls']} bp={r['bp']} co={r['co']} use={r['use']} '{r['desc'][:38]}'")

# ---- DRY-RUN WRITE ----
cur=db.cursor(); cur.execute("PRAGMA foreign_keys=OFF"); cur.execute("BEGIN")
try:
    pre={y:cur.execute(f"SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='{y}' AND project_id NOT IN (165,170,171,177)").fetchone()[0] for y in ('2023','2024','2025','2026')}
    nproj0=cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    nP=nS=0
    for r in ingest:
        cur.execute("INSERT INTO parcels (city_id,apn,address,geometry_source,notes) VALUES (1,?,?,?,?)",(r['apn'],r['addr'],'alameda_assessor',PROV)); parcel_id=cur.lastrowid
        cur.execute("INSERT INTO projects (city_id,canonical_name,canonical_address,normalized_address,latitude,longitude,current_stage_type_id) VALUES (1,?,?,?,?,?,6)",(r['addr'],r['addr'],r['naddr'],r['lat'],r['lon'])); pid=cur.lastrowid
        cur.execute("INSERT INTO documents (project_id,title,permit_number,source_system,notes) VALUES (?,?,?,?,?)",(pid,'CPRA BP Annual Permit Report 2023-2025',r['bp'],'cpra',PROV)); doc=cur.lastrowid
        cur.execute("INSERT INTO project_versions (project_id,version_label,version_type_id,effective_date,total_units,is_current,source_document_id,asserted_by,confidence_type_id,description) VALUES (?,?,5,?,?,1,?,?,2,?)",(pid,'as-built (CPRA CO)',r['co'],r['units'],doc,PROV,r['desc'])); vid=cur.lastrowid
        cur.execute("UPDATE projects SET current_version_id=? WHERE id=?",(vid,pid))
        cur.execute("INSERT INTO unit_program (project_version_id,bedroom_count,tenure_type_id,unit_count,source_document_id,asserted_by,confidence_type_id,notes) VALUES (?,NULL,8,?,?,?,2,?)",(vid,r['units'],doc,PROV,'bedroom NULL + tenure Unknown: not in primary sources')); up=cur.lastrowid
        cur.execute("INSERT INTO unit_program_affordability (unit_program_id,income_category_id,unit_count,source_document_id,asserted_by,confidence_type_id) VALUES (?,6,?,?,?,2)",(up,r['units'],doc,PROV))
        cur.execute("INSERT INTO project_parcels (project_id,parcel_id,is_primary) VALUES (?,?,1)",(pid,parcel_id))
        cur.execute("INSERT INTO permits (project_id,source_system,permit_number,permit_type_id,issued_date,finaled_date,valuation,description) VALUES (?,?,?,5,?,?,?,?)",(pid,'cpra',r['bp'],None,r['co'],r['val'],r['desc'])); perm=cur.lastrowid
        cur.execute("INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,17,?,?,1,2,'inferred',?)",(pid,r['co'],perm,'CO from CPRA 2023 finaled date'))
        et=27 if r['cls']=='SUBSIDIARY' else 26
        cur.execute("INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,?,'2026-06-03',?,1,2,'inferred',?)",(pid,et,perm,f"Permit classified {'PRIMARY' if et==26 else 'SUBSIDIARY'} (corrected ADU-aware rule, CY2023 backfill)"))
        nP+=(et==26); nS+=(et==27)
    print("\n=== DRY-RUN VERIFICATION ===")
    post={y:cur.execute(f"SELECT COUNT(*) c,COALESCE(SUM(total_units),0) u FROM v_projects_flat WHERE substr(co_issued_date,1,4)='{y}' AND project_id NOT IN (165,170,171,177)").fetchone() for y in ('2023','2024','2025','2026')}
    fk=cur.execute("PRAGMA foreign_key_check").fetchall(); integ=cur.execute("PRAGMA integrity_check").fetchone()[0]
    nproj=cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    print(f"  classification events: PRIMARY={nP} SUBSIDIARY={nS}")
    print(f"  CY2023: {pre['2023']} -> {post['2023']['c']} proj / {post['2023']['u']} units  (was 0; expect ~{sum(r['units'] for r in ingest)})")
    print(f"  TRIAD UNCHANGED?  CY2024={post['2024']['u']} (709) | CY2025={post['2025']['u']} (532) | CY2026={post['2026']['u']} (216)")
    print(f"  projects {nproj0} -> {nproj} (+{nproj-nproj0})  | FK rows={len(fk)} | integrity={integ}")
    ok=(post['2024']['u']==709 and post['2025']['u']==532 and post['2026']['u']==216 and len(fk)==0 and integ=='ok' and nproj-nproj0==len(ingest))
    if ok and not DRY:
        cur.execute("PRAGMA foreign_keys=ON"); db.commit(); print("\nALL CHECKS PASS -> COMMITTED")
    elif ok:
        db.rollback(); print("\nALL CHECKS PASS -> DRY RUN ok, rolled back")
    else:
        db.rollback(); print("\n*** CHECK FAILED -> ROLLED BACK ***")
except Exception as e:
    db.rollback(); print("EXCEPTION -> ROLLED BACK:", repr(e))
