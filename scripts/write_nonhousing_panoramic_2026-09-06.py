#!/usr/bin/env python3
"""GATED WRITE — UC Storage + 2130 Center as NON-RESIDENTIAL reconstructed entities.
0 dwelling units (so they never inflate housing counts), new `non_residential` classification +
`reconstructed_secondary`, Panoramic developer, description stating the real use. No unit_program
(no dwellings to describe). Snapshot: keep_snapshot_2026-09-06_pre-nonhousing-entities.db"""
import json, sqlite3, sys, datetime
sys.path.insert(0,'scripts'); from housing_rules.apn import to_canonical_apn
DB="databases/berkeley_housing_v2.db"; NOW=datetime.datetime.now().isoformat()
BY="panoramic_historic_reconstruction_2026-09-06"
TARGETS={"UC Storage":"UC Storage — 800 self-storage units (NOT dwellings), completed 2006. "
                       "Reconstructed from panoramic.com; not from the permit feed.",
         "2130 Center":"2130 Center — commercial (historic renovation; Ben & Jerry's, offices), "
                       "completed 2009. Reconstructed from panoramic.com; not from the permit feed."}
plan={p["tour_name"]:p for p in json.load(open("scratch/2026-09-06/entity_plan.json"))}
b=sqlite3.connect('file:databases/berkeley.db?mode=ro',uri=True)
coords={}
for apn,la,lo in b.execute("SELECT APN,Latitude,Longitude FROM parcels WHERE Latitude IS NOT NULL"):
    c=to_canonical_apn(apn,'alameda')
    if c and la not in (None,''): coords[c]=(float(la),float(lo),apn)
con=sqlite3.connect(DB); con.isolation_level=None; cur=con.cursor(); cur.execute("BEGIN")
try:
    # reuse reconstructed_secondary; add non_residential
    rsec=cur.execute("SELECT id FROM vocabulary_classification_types WHERE code='reconstructed_secondary'").fetchone()[0]
    nrid=cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM vocabulary_classification_types").fetchone()[0]
    cur.execute("INSERT INTO vocabulary_classification_types(id,code,label) VALUES (?,?,?)",
                (nrid,"non_residential","Non-Residential"))
    made=[]
    for name,desc in TARGETS.items():
        p=plan[name]; can=p["canon_apn"]; la,lo,apn_raw=coords[can]
        row=cur.execute("SELECT id FROM parcels WHERE apn_normalized=?",(can,)).fetchone()
        if row: parcel_id=row[0]
        else:
            cur.execute("""INSERT INTO parcels(city_id,apn,address,geometry_source,apn_raw,
                apn_normalized,assessing_county,created_at,updated_at)
                VALUES (1,?,?,?,?,?,'Alameda',?,?)""",(apn_raw,p["address"],"alameda_assessor",apn_raw,can,NOW,NOW))
            parcel_id=cur.lastrowid
        cur.execute("""INSERT INTO projects(city_id,canonical_name,canonical_address,normalized_address,
            latitude,longitude,current_stage_type_id,created_at,updated_at)
            VALUES (1,?,?,?,?,?,6,?,?)""",(name,p["address"],p["address"].upper(),la,lo,NOW,NOW))
        pid=cur.lastrowid
        cur.execute("""INSERT INTO project_versions(project_id,version_label,version_type_id,
            effective_date,total_units,is_current,asserted_by,asserted_at,confidence_type_id,description)
            VALUES (?,?,5,?,0,1,?,?,2,?)""",(pid,"As-Built (historic reconstruction)",f"{p['year']}-01-01",BY,NOW,desc))
        vid=cur.lastrowid
        cur.execute("UPDATE projects SET current_version_id=? WHERE id=?",(vid,pid))
        cur.execute("INSERT INTO project_parcels(project_id,parcel_id,is_primary) VALUES (?,?,1)",(pid,parcel_id))
        cur.execute("INSERT INTO project_participants(project_id,organization_id,role_type_id,asserted_by,asserted_at,confidence_type_id) VALUES (?,4,1,?,?,2)",(pid,BY,NOW))
        for cl in (rsec,nrid):
            cur.execute("""INSERT INTO project_classifications(project_id,classification_type_id,
                asserted_by,asserted_at,confidence_type_id,created_at) VALUES (?,?,?,?,2,?)""",(pid,cl,BY,NOW,NOW))
        made.append((pid,name))
    ids=tuple(m[0] for m in made)
    n=cur.execute(f"SELECT COUNT(*),COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE project_id IN {ids}").fetchone()
    if n[0]!=2 or n[1]!=0: raise RuntimeError(f"verify: {n}")
    cur.execute("COMMIT")
    print(f"  OK created {len(made)} non-residential entities (0 units): "+", ".join(f'proj{p} {nm}' for p,nm in made))
    print(f"    classifications: reconstructed_secondary({rsec}) + non_residential({nrid})")
except Exception as e:
    cur.execute("ROLLBACK"); import traceback; traceback.print_exc(); sys.exit(1)
finally: con.close()
