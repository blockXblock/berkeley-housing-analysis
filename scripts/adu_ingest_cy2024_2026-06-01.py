import sqlite3, openpyxl, re
from collections import defaultdict
DB='databases/berkeley_housing_v2.db'
def napn(a): return re.sub(r'[^\d]','',str(a or ''))
def naddr(a):
    a=(a or '').upper().split(',')[0]; mt=re.match(r'\s*(\d+)',a)
    if not mt: return ''
    rest=re.sub(r'^\s*\d+(-\d+)?\s+','',a); w=re.sub(r'[^A-Z ]','',rest).split()
    return mt.group(1)+'|'+(w[0] if w else '')
def num(x):
    try:return int(float(x))
    except:return 0

# ---------- assemble ingest set (primary sources only; Rule C net-new) ----------
m=sqlite3.connect('databases/hcd_apr_mirror.db');m.row_factory=sqlite3.Row
b=sqlite3.connect('databases/berkeley.db');b.row_factory=sqlite3.Row
db=sqlite3.connect(DB);db.row_factory=sqlite3.Row
CO=['CO_ACUTELY_LOW_INCOME_DR','CO_ACUTELY_LOW_INCOME_NDR','CO_EXTREMELY_LOW_INCOME_DR','CO_EXTREMELY_INCOME_NDR','CO_VLOW_INCOME_DR','CO_VLOW_INCOME_NDR','CO_LOW_INCOME_DR','CO_LOW_INCOME_NDR','CO_MOD_INCOME_DR','CO_MOD_INCOME_NDR','CO_ABOVE_MOD_INCOME']
v2apn=set();v2addr=set()
for r in db.execute("SELECT pk.apn FROM project_parcels pp JOIN parcels pk ON pp.parcel_id=pk.id WHERE pk.apn IS NOT NULL"): v2apn.add(napn(r['apn']))
for r in db.execute("SELECT address_display a FROM v_projects_flat"):
    if naddr(r['a']): v2addr.add(naddr(r['a']))
seen={}
for r in m.execute(f"SELECT APN,STREET_ADDRESS,CO_ISSUE_DT1,{','.join(CO)} FROM table_a2 WHERE YEAR=2024"):
    u=sum(num(r[c]) for c in CO)
    if u<=0 and not r['CO_ISSUE_DT1']: continue
    k=napn(r['APN']) or 'X'+naddr(r['STREET_ADDRESS'])
    if k not in seen or u>seen[k][0]: seen[k]=(u,r['APN'],r['STREET_ADDRESS'])
bucketA=[(napn(apn),apn,addr) for k,(u,apn,addr) in seen.items() if napn(apn) and napn(apn) not in v2apn and naddr(addr) not in v2addr]
wb=openpyxl.load_workbook('data/raw/cpra-downloads/BP_Annual Permit Report-2023-2025.xlsx',read_only=True);ws=wb.active
rows=list(ws.iter_rows(min_row=8,values_only=True));hdr=[(h or '').strip() for h in rows[0]];ix={h:i for i,h in enumerate(hdr)}
cpra=defaultdict(list)
for r in rows[1:]:
    if not any(r):continue
    cpra[napn(r[ix['Parcel Number']])].append({'bp':r[ix['PermitNumber']],'iss':str(r[ix['Issuance Date']] or '')[:10],'fin':str(r[ix['Finaled Date']] or '')[:10],'comp':str(r[ix['Completed Date']] or '')[:10],'num':num(r[ix['NumberUnits']]),'add':num(r[ix['UnitsAdded']]),'adu':str(r[ix['ADU']] or '').strip(),'occ':str(r[ix['OccType']] or '').strip(),'desc':str(r[ix['WorkDescription']] or '')[:120],'val':num(r[ix['JobValuation']])})
wb.close()
bk={}
for r in b.execute("SELECT apn_norm,Latitude,Longitude,UseCode FROM parcels_full WHERE apn_norm IS NOT NULL"):
    bk[napn(r['apn_norm'])]={'lat':r['Latitude'],'lon':r['Longitude']}
ingest=[]
for a,apnraw,addr in bucketA:
    cands=[p for p in cpra.get(a,[]) if p['fin'][:4]=='2024' or p['comp'][:4]=='2024']
    if not cands: continue   # the 1 HOLD (1825 Berkeley Way)
    best=sorted(cands,key=lambda p:(p['adu'].lower()=='yes',max(p['num'],p['add']),p['fin']),reverse=True)[0]
    net = best['add'] if best['add']>0 else (1 if best['adu'].lower()=='yes' else best['num'])
    p=bk.get(a)
    ingest.append({'addr':addr.strip(),'apn':apnraw.strip(),'naddr':naddr(addr),'units':net,
        'bp':best['bp'],'co':best['fin'] or best['comp'],'val':best['val'],'desc':best['desc'],
        'lat':p['lat'],'lon':p['lon']})
print(f"assembled {len(ingest)} ADU projects, net units sum = {sum(r['units'] for r in ingest)}")

# ---------- THE WRITE (transactional) ----------
PROV="CPRA BP_Annual Permit Report 2023-2025 + Alameda assessor (berkeley.db); ADU ingest 2026-06-01"
cur=db.cursor()
cur.execute("PRAGMA foreign_keys=OFF")
cur.execute("BEGIN")
try:
    # (1) rebuild unit_program with bedroom_count NULLABLE
    for vw in ('v_projects_flat','v_project_unit_mix','v_project_affordability'):
        cur.execute(f"DROP VIEW {vw}")
    cur.execute("""CREATE TABLE unit_program_new (
      id INTEGER PRIMARY KEY,
      project_version_id INTEGER NOT NULL REFERENCES project_versions(id) ON DELETE CASCADE,
      bedroom_count INTEGER CHECK (bedroom_count IS NULL OR bedroom_count BETWEEN 0 AND 10),
      tenure_type_id INTEGER NOT NULL REFERENCES vocabulary_tenure_types(id),
      unit_count INTEGER NOT NULL CHECK (unit_count >= 0),
      avg_sqft INTEGER,
      special_population_type_id INTEGER REFERENCES vocabulary_special_population_types(id),
      notes TEXT,
      source_document_id INTEGER REFERENCES documents(id),
      asserted_by TEXT, asserted_at TEXT,
      confidence_type_id INTEGER REFERENCES vocabulary_confidence_types(id),
      beds_per_unit INTEGER CHECK (beds_per_unit IS NULL OR beds_per_unit >= 0))""")
    cur.execute("""INSERT INTO unit_program_new SELECT id,project_version_id,bedroom_count,tenure_type_id,unit_count,avg_sqft,special_population_type_id,notes,source_document_id,asserted_by,asserted_at,confidence_type_id,beds_per_unit FROM unit_program""")
    cur.execute("DROP TABLE unit_program")
    cur.execute("ALTER TABLE unit_program_new RENAME TO unit_program")
    cur.execute("CREATE INDEX idx_unit_program_version ON unit_program(project_version_id)")
    for vw in ('v_project_unit_mix','v_project_affordability','v_projects_flat'):
        cur.execute(open(f'/tmp/{vw}_PREREBUILD.sql').read())
    # (2) insert the 95 ADU projects
    for r in ingest:
        cur.execute("INSERT INTO parcels (city_id,apn,address,geometry_source,notes) VALUES (1,?,?,?,?)",(r['apn'],r['addr'],'alameda_assessor',PROV)); parcel_id=cur.lastrowid
        cur.execute("INSERT INTO projects (city_id,canonical_name,canonical_address,normalized_address,latitude,longitude,current_stage_type_id) VALUES (1,?,?,?,?,?,6)",(r['addr'],r['addr'],r['naddr'],r['lat'],r['lon'])); pid=cur.lastrowid
        cur.execute("INSERT INTO documents (project_id,title,permit_number,source_system,notes) VALUES (?,?,?,?,?)",(pid,'CPRA BP Annual Permit Report 2023-2025',r['bp'],'cpra',PROV)); doc=cur.lastrowid
        cur.execute("INSERT INTO project_versions (project_id,version_label,version_type_id,effective_date,total_units,is_current,source_document_id,asserted_by,confidence_type_id,description) VALUES (?,?,5,?,?,1,?,?,2,?)",(pid,'as-built (CPRA CO)',r['co'],r['units'],doc,PROV,r['desc'])); vid=cur.lastrowid
        cur.execute("UPDATE projects SET current_version_id=? WHERE id=?",(vid,pid))
        cur.execute("INSERT INTO unit_program (project_version_id,bedroom_count,tenure_type_id,unit_count,source_document_id,asserted_by,confidence_type_id,notes) VALUES (?,NULL,8,?,?,?,2,?)",(vid,r['units'],doc,PROV,'bedroom_count NULL: not in primary sources (CPRA/assessor)')); up=cur.lastrowid
        cur.execute("INSERT INTO unit_program_affordability (unit_program_id,income_category_id,unit_count,source_document_id,asserted_by,confidence_type_id) VALUES (?,6,?,?,?,2)",(up,r['units'],doc,PROV))
        cur.execute("INSERT INTO project_parcels (project_id,parcel_id,is_primary) VALUES (?,?,1)",(pid,parcel_id))
        cur.execute("INSERT INTO permits (project_id,source_system,permit_number,permit_type_id,issued_date,finaled_date,valuation,description) VALUES (?,?,?,5,?,?,?,?)",(pid,'cpra',r['bp'],None,r['co'],r['val'],r['desc'])); perm=cur.lastrowid
        cur.execute("INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,17,?,?,1,2,'inferred',?)",(pid,r['co'],perm,'CO from CPRA finaled date'))
    print(f"inserted {len(ingest)} projects across 8 tables")
    # ---------- VERIFICATION (both checks) ----------
    print("\n=== POST-REBUILD VERIFICATION ===")
    nn=cur.execute("SELECT \"notnull\" FROM pragma_table_info('unit_program') WHERE name='bedroom_count'").fetchone()[0]
    adu_null=cur.execute("SELECT COUNT(*) FROM unit_program WHERE bedroom_count IS NULL").fetchone()[0]
    old1=cur.execute("SELECT COUNT(*) FROM unit_program WHERE bedroom_count=1").fetchone()[0]
    print(f"(a) bedroom_count notnull flag = {nn} (expect 0=nullable); ADU NULLs = {adu_null} (expect {len(ingest)}); existing bed=1 rows = {old1} (expect 179)")
    fk=cur.execute("PRAGMA foreign_key_check").fetchall()
    k113=cur.execute("SELECT bp_issued_date FROM v_projects_flat WHERE project_id=113").fetchone()[0]
    newids=cur.execute("SELECT project_id FROM v_projects_flat WHERE project_id>184").fetchall()
    UC="(165,170,171,177)"  # is_uc_project / group-quarters in v2 (report-time exclusion)
    cy24_major=cur.execute("SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='2024' AND project_id<=184").fetchone()[0]
    cy24_major_gq=cur.execute(f"SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='2024' AND project_id<=184 AND project_id NOT IN {UC}").fetchone()[0]
    cy24_total_gq=cur.execute(f"SELECT COUNT(*),COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='2024' AND project_id NOT IN {UC}").fetchone()
    print(f"(b) 2138 Kittredge bp_issued = {k113} (expect NULL = permit-fix intact); foreign_key_check rows = {len(fk)} (expect 0)")
    print(f"    permit-fix holds: DB-level major CY2024 CO units = {cy24_major} (expect 786; a revert would be ~1233)")
    print(f"    +group-quarters: major CY2024 excl UC = {cy24_major_gq} (expect 486 = corrected pre-ADU number)")
    print(f"    POST-ADU CY2024 (excl UC) = {cy24_total_gq[0]} proj / {cy24_total_gq[1]} units (expect ~101 / ~708-709)")
    vpf=cur.execute("SELECT COUNT(*) FROM v_projects_flat").fetchone()[0]
    print(f"    v_projects_flat rows: {vpf} (expect 276 = 181+95)")
    ok = (nn==0 and adu_null==len(ingest) and old1==179 and k113 is None and len(fk)==0
          and cy24_major==786 and cy24_major_gq==486 and 705<=cy24_total_gq[1]<=712 and vpf==276)
    if ok:
        cur.execute("PRAGMA foreign_keys=ON"); db.commit(); print("\nALL CHECKS PASS -> COMMITTED")
    else:
        db.rollback(); print("\n*** CHECK FAILED -> ROLLED BACK (no changes) ***")
except Exception as e:
    db.rollback(); print("EXCEPTION -> ROLLED BACK:", e)
