"""
OP1-4 combined gated write on berkeley_housing_v2.db  (2026-06-01)
Single corrected ADU-aware classification rule applied to BOTH years.
Snapshot in place: keep_snapshot_2026-06-01_pre-cy2025.db (sha ec4031f6).
Runs DRY by default (BEGIN...rollback). Pass --commit to write.

OP1  2641 College (id53): flip permit 148 (siding) PRIMARY->SUBSIDIARY  (-3u CY2025)
OP2  1752 Shattuck (id164): remove manual NO_DESC CO; re-anchor to CY2026 via B2023-00774 (72u,
       count primary-sourced); tenure/affordability -> UNKNOWN-with-provenance (migration defaults
       were unsourced + contradicted by State Density Bonus; real mix in DRCP doc 910, not extracted)
OP3  ingest 90 CY2025 ADUs (Bucket A), primary sources only, honest-unknowns
OP4  corrected ADU-aware classification on all 185 ADU permits (95 CY2024 + 90 CY2025)
       dispositions: 190 re-pick B2023-01652, 207 re-pick B2023-04099, 208 remove (demolish)
"""
import sqlite3, openpyxl, re, sys
from collections import defaultdict
DB='databases/berkeley_housing_v2.db'
PROV="CPRA BP_Annual Permit Report 2023-2025 + Alameda assessor (berkeley.db); CY2025 ADU ingest 2026-06-01"
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

# ---------- corrected ADU-aware classification rule (single rule, both years) ----------
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
    if DEMO.search(d): return 'SUBSIDIARY'             # demo is never a completion
    if adu_yes or ADUVERB.search(d): return 'PRIMARY'  # an ADU conversion/legalization IS a completion
    if is_struct(d): return 'PRIMARY'
    if SPURIOUS.search(d): return 'SUBSIDIARY'
    return 'PRIMARY' if (val or 0)>=1000000 else 'AMBIGUOUS'   # AMBIGUOUS -> PRIMARY per John's adjudication

# ---------- load CPRA (desc truncated [:120] to reproduce the reviewed classification) ----------
wb=openpyxl.load_workbook('data/raw/cpra-downloads/BP_Annual Permit Report-2023-2025.xlsx',read_only=True);ws=wb.active
rows=list(ws.iter_rows(min_row=8,values_only=True));hdr=[(h or '').strip() for h in rows[0]];ix={h:i for i,h in enumerate(hdr)}
by_permit={}; by_parcel=defaultdict(list)
for r in rows[1:]:
    if not any(r):continue
    rec={'bp':str(r[ix['PermitNumber']] or ''),'fin':str(r[ix['Finaled Date']] or '')[:10],'comp':str(r[ix['Completed Date']] or '')[:10],
         'num':num(r[ix['NumberUnits']]),'add':num(r[ix['UnitsAdded']]),'adu':str(r[ix['ADU']] or '').strip().lower()=='yes',
         'occ':str(r[ix['OccType']] or '').strip(),'desc':str(r[ix['WorkDescription']] or '')[:120],'val':num(r[ix['JobValuation']]),'apn':napn(r[ix['Parcel Number']])}
    by_permit[rec['bp']]=rec; by_parcel[rec['apn']].append(rec)
wb.close()

# ---------- assemble 90 CY2025 Bucket-A ingest set ----------
m=sqlite3.connect('databases/hcd_apr_mirror.db');m.row_factory=sqlite3.Row
b=sqlite3.connect('databases/berkeley.db');b.row_factory=sqlite3.Row
db=sqlite3.connect(DB);db.row_factory=sqlite3.Row
CO=['CO_ACUTELY_LOW_INCOME_DR','CO_ACUTELY_LOW_INCOME_NDR','CO_EXTREMELY_LOW_INCOME_DR','CO_EXTREMELY_INCOME_NDR','CO_VLOW_INCOME_DR','CO_VLOW_INCOME_NDR','CO_LOW_INCOME_DR','CO_LOW_INCOME_NDR','CO_MOD_INCOME_DR','CO_MOD_INCOME_NDR','CO_ABOVE_MOD_INCOME']
v2apn=set();v2addr=set()
for r in db.execute("SELECT pk.apn FROM project_parcels pp JOIN parcels pk ON pp.parcel_id=pk.id WHERE pk.apn IS NOT NULL"): v2apn.add(napn(r['apn']))
for r in db.execute("SELECT address_display a FROM v_projects_flat"):
    if naddr(r['a']): v2addr.add(naddr(r['a']))
seen={}
for r in m.execute(f"SELECT APN,STREET_ADDRESS,{','.join(CO)} FROM table_a2 WHERE YEAR=2025"):
    u=sum(num(r[c]) for c in CO)
    if u<=0: continue
    k=napn(r['APN']) or 'X'+naddr(r['STREET_ADDRESS'])
    if k not in seen or u>seen[k][0]: seen[k]=(u,r['APN'],r['STREET_ADDRESS'])
bk={napn(r['apn_norm']):{'lat':r['Latitude'],'lon':r['Longitude']} for r in b.execute("SELECT apn_norm,Latitude,Longitude FROM parcels_full WHERE apn_norm IS NOT NULL")}
def fy25(p): return p['fin'][:4]=='2025' or p['comp'][:4]=='2025'
ingest=[]
for k,(u,apnraw,addr) in seen.items():
    a=napn(apnraw)
    if not a or a in v2apn or naddr(addr) in v2addr: continue
    cands=[p for p in by_parcel.get(a,[]) if fy25(p)]
    if not cands: continue
    best=sorted(cands,key=lambda p:(p['adu'],max(p['num'],p['add']),p['fin']),reverse=True)[0]
    net=best['add'] if best['add']>0 else (1 if best['adu'] else best['num'])
    p=bk.get(a)
    ingest.append({'addr':addr.strip(),'apn':apnraw.strip(),'naddr':naddr(addr),'units':net,'bp':best['bp'],
        'co':best['fin'] or best['comp'],'val':best['val'],'desc':best['desc'],'adu':best['adu'],
        'lat':p['lat'] if p else None,'lon':p['lon'] if p else None,
        'cls':classify_adu(best['desc'],best['val'],best['adu'])})
print(f"[assemble] CY2025 ingest = {len(ingest)} projects, {sum(r['units'] for r in ingest)} units; "
      f"classes={ {c:sum(1 for r in ingest if r['cls']==c) for c in ('PRIMARY','SUBSIDIARY','AMBIGUOUS')} }")
assert len(ingest)==90 and sum(r['units'] for r in ingest)==106, "ingest set drift"
assert all(r['cls']=='PRIMARY' for r in ingest), "a CY2025 ADU did not classify PRIMARY under corrected rule"

# ---------- THE WRITE ----------
cur=db.cursor()
cur.execute("PRAGMA foreign_keys=OFF")
cur.execute("BEGIN")
try:
    pre24=cur.execute("SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='2024' AND project_id NOT IN (165,170,171,177)").fetchone()[0]
    pre25=cur.execute("SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='2025'").fetchone()[0]
    pre26=cur.execute("SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='2026'").fetchone()[0]
    # capture the 95 existing CY2024 ADU permits BEFORE OP3 adds more project_id>184 permits
    cy24_perms=cur.execute("SELECT id,project_id,permit_number,description,valuation FROM permits WHERE project_id>184").fetchall()
    assert len(cy24_perms)==95, f"expected 95 CY2024 ADU permits, got {len(cy24_perms)}"

    # ===== OP1 — 2641 College: flip permit 148 PRIMARY -> SUBSIDIARY =====
    cur.execute("DELETE FROM project_events WHERE id=2821 AND project_id=53 AND permit_id=148 AND event_type_id=26")
    assert cur.rowcount==1, "OP1: primary classification event 2821 not found"
    cur.execute("""INSERT INTO project_events(project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary)
                   VALUES (53,27,'2026-06-01',148,1,2,'inferred',?)""",
                ("Permit classified SUBSIDIARY: B2025-02413 = 760sf siding replacement on existing 2-story residence (not new construction). Corrected 2026-06-01; removes false 3u CY2025 CO. Sibling permit 146 already subsidiary -> 2641 College CO now NULL.",))

    # ===== OP2 — 1752 Shattuck (id164): remove manual CO; re-anchor to CY2026 via B2023-00774 (72u) =====
    cur.execute("DELETE FROM project_events WHERE id=305 AND project_id=164 AND event_type_id=17 AND permit_id IS NULL")
    assert cur.rowcount==1, "OP2: manual CO event 305 not found"
    cur.execute("""INSERT INTO project_events(project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary)
                   VALUES (164,17,'2026-05-26',202,1,2,'inferred',?)""",
                ("CO re-anchored to CY2026 per Accela inspection-Finaled 05/06/2026 & 05/26/2026 (B2023-00774 = 72-unit 7-story mixed-use). Replaces manual 2025-05-27 NO_DESC CO. 2023-permitted, completing 2026 -- pre-Middle-Housing project finishing post-policy, NOT policy evidence.",))
    # count 72 is primary-sourced (B2023-00774); tenure/affordability were unsourced migration defaults -> honest-unknown
    cur.execute("UPDATE project_versions SET total_units=72, description=description||' [As-built per permit B2023-00774: 72 units (entitlement was 68); CO re-anchored to CY2026 per Accela 05/2026. Tenure/affordability set UNKNOWN-with-provenance: prior Rental/Above-Moderate were unsourced v1->v2 migration defaults (source_document_id NULL), contradicted by State Density Bonus; real mix in DRCP doc 910, not yet extracted.]' WHERE id=161"); assert cur.rowcount==1
    cur.execute("UPDATE unit_program SET unit_count=72, tenure_type_id=8, notes=COALESCE(notes,'')||' | count=72 from B2023-00774 (primary); tenure UNKNOWN: migration default unsourced (2026-06-01)' WHERE id=161"); assert cur.rowcount==1
    cur.execute("UPDATE unit_program_affordability SET unit_count=72, income_category_id=6 WHERE id=156"); assert cur.rowcount==1

    # ===== OP3 — ingest 90 CY2025 ADUs (no schema rebuild; bedroom_count already nullable) =====
    new=[]
    for r in ingest:
        cur.execute("INSERT INTO parcels (city_id,apn,address,geometry_source,notes) VALUES (1,?,?,?,?)",(r['apn'],r['addr'],'alameda_assessor',PROV)); parcel_id=cur.lastrowid
        cur.execute("INSERT INTO projects (city_id,canonical_name,canonical_address,normalized_address,latitude,longitude,current_stage_type_id) VALUES (1,?,?,?,?,?,6)",(r['addr'],r['addr'],r['naddr'],r['lat'],r['lon'])); pid=cur.lastrowid
        cur.execute("INSERT INTO documents (project_id,title,permit_number,source_system,notes) VALUES (?,?,?,?,?)",(pid,'CPRA BP Annual Permit Report 2023-2025',r['bp'],'cpra',PROV)); doc=cur.lastrowid
        cur.execute("INSERT INTO project_versions (project_id,version_label,version_type_id,effective_date,total_units,is_current,source_document_id,asserted_by,confidence_type_id,description) VALUES (?,?,5,?,?,1,?,?,2,?)",(pid,'as-built (CPRA CO)',r['co'],r['units'],doc,PROV,r['desc'])); vid=cur.lastrowid
        cur.execute("UPDATE projects SET current_version_id=? WHERE id=?",(vid,pid))
        cur.execute("INSERT INTO unit_program (project_version_id,bedroom_count,tenure_type_id,unit_count,source_document_id,asserted_by,confidence_type_id,notes) VALUES (?,NULL,8,?,?,?,2,?)",(vid,r['units'],doc,PROV,'bedroom_count NULL + tenure Unknown: not in primary sources (CPRA/assessor)')); up=cur.lastrowid
        cur.execute("INSERT INTO unit_program_affordability (unit_program_id,income_category_id,unit_count,source_document_id,asserted_by,confidence_type_id) VALUES (?,6,?,?,?,2)",(up,r['units'],doc,PROV))
        cur.execute("INSERT INTO project_parcels (project_id,parcel_id,is_primary) VALUES (?,?,1)",(pid,parcel_id))
        cur.execute("INSERT INTO permits (project_id,source_system,permit_number,permit_type_id,issued_date,finaled_date,valuation,description) VALUES (?,?,?,5,?,?,?,?)",(pid,'cpra',r['bp'],None,r['co'],r['val'],r['desc'])); perm=cur.lastrowid
        cur.execute("INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,17,?,?,1,2,'inferred',?)",(pid,r['co'],perm,'CO from CPRA finaled date'))
        new.append((pid,perm,r))

    # ===== OP4 — corrected classification on all 185 ADU permits =====
    nP=nS=0; subs=[]
    # (a) 90 new CY2025 permits -> all PRIMARY
    for pid,perm,r in new:
        cur.execute("INSERT INTO project_events(project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,26,'2026-06-01',?,1,2,'inferred',?)",(pid,perm,"Permit classified PRIMARY (corrected ADU-aware rule 2026-06-01)")); nP+=1
    # (b) 95 existing CY2024 ADU permits -> corrected rule (AMBIGUOUS->PRIMARY); dispositions force the 3 wrong-picks SUBSIDIARY
    REPICK={250:('B2023-01652','2024-10-16',500000,'Alteration to convert a single family home to duplex (~1,800 sf each)'),
            267:('B2023-04099','2024-06-27',200000,'Convert basement into JADU - 495 sq ft studio')}
    DISPO_SUB={250,267,268}   # 190 solar, 207 remodel, 208 demolish
    co_by_oldperm={250:2907,267:2924}
    for pr in cy24_perms:
        cp=by_permit.get(pr['permit_number'],{})
        cls=classify_adu(pr['description'] or cp.get('desc',''), pr['valuation'] or cp.get('val',0), cp.get('adu',False))
        if cls=='AMBIGUOUS': cls='PRIMARY'
        if pr['id'] in DISPO_SUB: cls='SUBSIDIARY'
        et=27 if cls=='SUBSIDIARY' else 26
        cur.execute("INSERT INTO project_events(project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,?,'2026-06-01',?,1,2,'inferred',?)",
                    (pr['project_id'],et,pr['id'],f"Permit classified {cls} (corrected ADU-aware rule 2026-06-01)"))
        if et==27: nS+=1; subs.append((pr['project_id'],pr['permit_number']))
        else: nP+=1
    # (c) re-pick dispositions 190 & 207: add the real construction permit (PRIMARY) + re-point the CO event
    for oldperm,(bp,fin,val,desc) in REPICK.items():
        pid=cur.execute("SELECT project_id FROM permits WHERE id=?",(oldperm,)).fetchone()[0]
        cur.execute("INSERT INTO permits (project_id,source_system,permit_number,permit_type_id,issued_date,finaled_date,valuation,description) VALUES (?,?,?,5,?,?,?,?)",(pid,'cpra',bp,None,fin,val,desc)); newperm=cur.lastrowid
        cur.execute("INSERT INTO project_events(project_id,event_type_id,event_date,permit_id,is_inferred,confidence_type_id,source_type,summary) VALUES (?,26,'2026-06-01',?,1,2,'inferred',?)",(pid,newperm,f"Permit classified PRIMARY: re-pick {bp} (real 2024 construction permit) replaces wrongly-picked alteration permit as CO provenance")); nP+=1
        cur.execute("UPDATE project_events SET permit_id=?, event_date=?, summary=? WHERE id=?",(newperm,fin,f"CO re-anchored to construction permit {bp} (finaled {fin}); prior alteration-permit provenance corrected 2026-06-01",co_by_oldperm[oldperm]))
    print(f"[OP4] classification events: PRIMARY={nP} SUBSIDIARY={nS} (185 ADU permits + 2 re-pick); subsidiary set={subs}")

    # =================== VERIFICATION ===================
    print("\n=== VERIFICATION ===")
    UC="(165,170,171,177)"
    def co_units(y):
        return cur.execute(f"SELECT COUNT(*),COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='{y}' AND project_id NOT IN {UC}").fetchone()
    cy24=co_units('2024'); cy25=co_units('2025'); cy26=co_units('2026')
    major24=cur.execute("SELECT COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE substr(co_issued_date,1,4)='2024' AND project_id<=184").fetchone()[0]
    k113=cur.execute("SELECT bp_issued_date FROM v_projects_flat WHERE project_id=113").fetchone()[0]
    c53=cur.execute("SELECT co_issued_date FROM v_projects_flat WHERE project_id=53").fetchone()[0]
    c164=cur.execute("SELECT co_issued_date,total_units FROM v_projects_flat WHERE project_id=164").fetchone()
    t164=cur.execute("SELECT up.tenure_type_id,a.income_category_id FROM unit_program up JOIN unit_program_affordability a ON a.unit_program_id=up.id WHERE up.id=161").fetchone()
    c208=cur.execute("SELECT co_issued_date FROM v_projects_flat WHERE project_id=208").fetchone()[0]
    c190=cur.execute("SELECT co_issued_date FROM v_projects_flat WHERE project_id=190").fetchone()[0]
    c207=cur.execute("SELECT co_issued_date FROM v_projects_flat WHERE project_id=207").fetchone()[0]
    p190src=cur.execute("SELECT p.permit_number FROM project_events e JOIN permits p ON p.id=e.permit_id WHERE e.project_id=190 AND e.event_type_id=17").fetchone()
    p207src=cur.execute("SELECT p.permit_number FROM project_events e JOIN permits p ON p.id=e.permit_id WHERE e.project_id=207 AND e.event_type_id=17").fetchone()
    fk=cur.execute("PRAGMA foreign_key_check").fetchall()
    integ=cur.execute("PRAGMA integrity_check").fetchone()[0]
    nproj=cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    print(f"  permit-fix intact: 2138 Kittredge bp_issued={k113} (expect NULL); DB-level major CY2024={major24} (expect 786)")
    print(f"  CY2024 (excl UC) = {cy24[0]} proj / {cy24[1]} units   [pre {pre24}] (expect 709)")
    print(f"  CY2025 (excl UC) = {cy25[0]} proj / {cy25[1]} units   [pre {pre25}] (expect 532)")
    print(f"  CY2026 (excl UC) = {cy26[0]} proj / {cy26[1]} units   [pre {pre26}] (expect 216)")
    print(f"  OP1 2641 College(53): co={c53} (expect None)")
    print(f"  OP2 1752 Shattuck(164): co={c164[0]} units={c164[1]} tenure={t164[0]} income={t164[1]} (expect 2026-05-26 / 72 / 8 / 6)")
    print(f"  208 Kentucky: co={c208} (expect None)")
    print(f"  190 Addison: co={c190} via {p190src and p190src[0]} (expect 2024-10-16 / B2023-01652)")
    print(f"  207 Boynton: co={c207} via {p207src and p207src[0]} (expect 2024-06-27 / B2023-04099)")
    print(f"  projects={nproj} (expect 366=276+90)  FK rows={len(fk)} (expect 0)  integrity={integ}")

    ok = (k113 is None and major24==786 and cy24[1]==709 and cy25[1]==532 and cy26[1]==216
          and c53 is None and c164[0]=='2026-05-26' and c164[1]==72 and t164[0]==8 and t164[1]==6
          and c208 is None and c190=='2024-10-16' and (p190src and p190src[0]=='B2023-01652')
          and c207=='2024-06-27' and (p207src and p207src[0]=='B2023-04099')
          and nproj==366 and len(fk)==0 and integ=='ok')
    if ok and not DRY:
        cur.execute("PRAGMA foreign_keys=ON"); db.commit(); print("\nALL CHECKS PASS -> COMMITTED")
    elif ok and DRY:
        db.rollback(); print("\nALL CHECKS PASS -> DRY RUN ok, rolled back (re-run with --commit to write)")
    else:
        db.rollback(); print("\n*** CHECK FAILED -> ROLLED BACK (no changes) ***")
except Exception as e:
    db.rollback(); print("EXCEPTION -> ROLLED BACK:", repr(e))
