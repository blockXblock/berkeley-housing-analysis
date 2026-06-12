import sqlite3, re, sys
DB='databases/berkeley_housing_v2.db'
db=sqlite3.connect(DB); db.row_factory=sqlite3.Row
db.execute("BEGIN")

# ---- final adjudicated classifier (identical to approved preview) ----
SPURIOUS = re.compile(r'\b(solar|photovolta\w*|pv|modules?|window|door|sign|water heater|furnace|heat pump|siding|insulation|drywall|remodel|temp(?:orary)? power|temp meter|meter|washer|dryer|reroof|re-roof|shoring|grading|ev charg\w*|repair)\b', re.I)
SPELLED  = re.compile(r'\b(one|two|three|four|five|six|seven|eight|nine|ten)[-\s](stor(?:y|ey|ies)|units?|family)', re.I)
DIGITNUM = re.compile(r'\b\d+[-\s]?(?:unit|story|storey|stories|units)\b', re.I)
NEWBUILD = re.compile(r'\b(?:new|construct\w*)\b[\s\S]{0,40}?\b(?:residence|home|house|building|dwelling|apartment|adus?|sfr|single[-\s]?family|condo|congregate|senior living)\b', re.I)
BLDGPHR  = re.compile(r'\b(apartment building|mixed[-\s]?use building|multi[-\s]?family|residential (?:development|apartment|building))\b', re.I)
DEMO_LEAD= re.compile(r'^\s*demoli', re.I)
def is_struct(d): return bool(SPELLED.search(d) or DIGITNUM.search(d) or NEWBUILD.search(d) or BLDGPHR.search(d))
HOLD={179,176}
OVR={'B2024-00543':'SUBSIDIARY','B2025-02754':'SUBSIDIARY','B2025-04912':'SUBSIDIARY','B2025-01202':'SUBSIDIARY',
     'B2025-00709':'SUBSIDIARY','B2023-03256':'SUBSIDIARY','B2023-03308':'SUBSIDIARY','B2023-03832':'SUBSIDIARY',
     'B2022-01278':'SUBSIDIARY','B2024-02569':'SUBSIDIARY','B2024-02712':'SUBSIDIARY','B2025-00168':'PRIMARY'}
def classify(pid, pn, descr, val):
    if pid in HOLD: return 'HOLD'
    if pn in OVR: return OVR[pn]
    if descr is None or descr.strip()=='': return 'MANUAL'
    if DEMO_LEAD.search(descr): return 'SUBSIDIARY'
    if is_struct(descr): return 'PRIMARY'
    if SPURIOUS.search(descr): return 'SUBSIDIARY'
    return 'PRIMARY' if (val or 0)>=1000000 else 'AMBIGUOUS'

# distinct permits that drive a BP/CO milestone (those with a permit_id)
rows=db.execute("""SELECT DISTINCT e.permit_id pid_permit, e.project_id pid, pm.permit_number pn, pm.valuation val, pm.description descr
FROM project_events e JOIN vocabulary_event_types et ON et.id=e.event_type_id JOIN permits pm ON pm.id=e.permit_id
WHERE et.code IN ('building_permit_issued','co_issued')""").fetchall()
cls={}
for r in rows: cls[r['pid_permit']]=(r['pid'], r['pn'], classify(r['pid'], r['pn'], r['descr'], r['val']))
from collections import Counter
print("permit-level classification:", dict(Counter(v[2] for v in cls.values())))
amb=[v for v in cls.values() if v[2]=='AMBIGUOUS']
if amb:
    print("*** UNEXPECTED AMBIGUOUS at permit level -> ROLLBACK ***", amb); db.rollback(); sys.exit(1)

# ---- INSERT classification events (26 primary / 27 subsidiary); HOLD & MANUAL skipped ----
ins=0
for permit_id,(proj,pn,c) in cls.items():
    if c in ('HOLD',): continue
    etid = 26 if c=='PRIMARY' else 27 if c=='SUBSIDIARY' else None
    if etid is None: continue
    db.execute("""INSERT INTO project_events (project_id,event_type_id,event_date,permit_id,summary,is_inferred,source_type,created_at)
                  VALUES (?,?,?,?,?,1,?,?)""",
               (proj, etid, '2026-06-01', permit_id,
                f'Permit classified {c} (keyword/valuation rule + adjudication 2026-06-01)',
                'inferred','2026-06-01T00:00:00'))
    ins+=1
print(f"inserted {ins} classification events")

# ---- update v_projects_flat to exclude subsidiary-classified permits' milestones ----
orig=open('/tmp/v_projects_flat_ORIGINAL.sql').read().rstrip().rstrip(';')
NX="SELECT 1 FROM project_events c JOIN vocabulary_event_types ct ON ct.id=c.event_type_id WHERE ct.code='permit_classified_subsidiary' AND c.permit_id=e.permit_id"
new=orig.replace("et.code = 'building_permit_issued')", f"et.code = 'building_permit_issued' AND NOT EXISTS({NX}))")
new=new.replace("et.code = 'co_issued')", f"et.code = 'co_issued' AND NOT EXISTS({NX}))")
assert new!=orig and 'NOT EXISTS' in new, "view replacement failed"
db.execute("DROP VIEW v_projects_flat")
db.execute(new)
print("v_projects_flat recreated with subsidiary exclusion")

# ---- VERIFY before commit ----
def co(pid): 
    r=db.execute("SELECT co_issued_date, bp_issued_date FROM v_projects_flat WHERE project_id=?",(pid,)).fetchone(); return (r['bp_issued_date'], r['co_issued_date']) if r else (None,None)
nrows=db.execute("SELECT COUNT(*) c FROM v_projects_flat").fetchone()['c']
b113=co(113); c161=co(161); c135=co(135); c179=co(179)
print("\n=== VERIFY ===")
print(f"row count: {nrows} (expect 181)")
print(f"id113 2138 Kittredge bp_issued: {b113[0]} (expect NULL - bathroom-window permit dropped)")
print(f"id161 2555 College co_issued: {c161[1]} (expect 2025-07-25 - structural kept)")
print(f"id135 2150 Kittredge co_issued: {c135[1]} (expect 2024-01-01 - manual kept; solar/sign dropped)")
print(f"id179 2352 Shattuck co_issued: {c179[1]} (expect 2024-12-10 - HELD, unchanged)")
ok = (nrows==181 and b113[0] is None and c161[1]=='2025-07-25' and c135[1]=='2024-01-01' and c179[1]=='2024-12-10')
if ok:
    db.commit(); print("\nALL CHECKS PASS -> COMMITTED")
else:
    db.rollback(); print("\n*** CHECK FAILED -> ROLLED BACK (no changes written) ***")
