#!/usr/bin/env python3
"""GATED WRITE — create 12 v2 project entities for the historic Panoramic buildings.

Provenance-first ("show where it's coming from"): each entity is a full project (projects +
as-built version + unit program + affordability + parcel link + Panoramic as developer) but is
tagged with a NEW classification `reconstructed_secondary` and carries asserted_by +
confidence + a description naming the source. Housing only (UC Storage / 2130 Center excluded per
John). Sources: developer website (confidence MEDIUM) or the tour's own caption (LOW).
Snapshot: keep_snapshot_2026-09-06_pre-panoramic-historic-entities.db
"""
import json, sqlite3, sys, datetime
sys.path.insert(0,'scripts')
from housing_rules.apn import to_canonical_apn
DB="databases/berkeley_housing_v2.db"; NOW=datetime.datetime.now().isoformat()
BY="panoramic_historic_reconstruction_2026-09-06"
SRCURL={"developer_site":"panoramic.com project page (developer self-report)",
        "tour_caption":"panoramic-kennedy-legacy tour caption (origin unrecorded)",
        "assessor":"Alameda assessor"}
plan=[p for p in json.load(open("scratch/2026-09-06/entity_plan.json")) if p["housing"]]

b=sqlite3.connect('file:databases/berkeley.db?mode=ro',uri=True)
coords={}
for apn,la,lo in b.execute("SELECT APN,Latitude,Longitude FROM parcels WHERE Latitude IS NOT NULL"):
    c=to_canonical_apn(apn,'alameda')
    if c and la not in (None,''): coords[c]=(float(la),float(lo),apn)

con=sqlite3.connect(DB); con.isolation_level=None; cur=con.cursor(); cur.execute("BEGIN")
try:
    # 1) new classification vocab type
    cid=cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM vocabulary_classification_types").fetchone()[0]
    cur.execute("INSERT INTO vocabulary_classification_types(id,code,label) VALUES (?,?,?)",
                (cid,"reconstructed_secondary","Reconstructed from Secondary Sources"))
    made=[]
    for p in plan:
        can=p["canon_apn"]; conf=p["conf"]; units=int(p["units"]) if p["units"] else None
        aff=int(p["affordable"]) if p["affordable"] else 0
        la,lo,apn_raw = coords[can]
        # parcel: reuse or create
        row=cur.execute("SELECT id FROM parcels WHERE apn_normalized=?",(can,)).fetchone()
        if row: parcel_id=row[0]
        else:
            cur.execute("""INSERT INTO parcels(city_id,apn,address,geometry_source,apn_raw,
                apn_normalized,assessing_county,created_at,updated_at)
                VALUES (1,?,?,?,?,?,'Alameda',?,?)""",
                (apn_raw,p["address"],"alameda_assessor",apn_raw,can,NOW,NOW))
            parcel_id=cur.lastrowid
        # project
        cur.execute("""INSERT INTO projects(city_id,canonical_name,canonical_address,
            normalized_address,latitude,longitude,current_stage_type_id,created_at,updated_at)
            VALUES (1,?,?,?,?,?,6,?,?)""",
            (p["tour_name"],p["address"],p["address"].upper(),la,lo,NOW,NOW))
        pid=cur.lastrowid
        desc=(f"Historic Panoramic Interests building, completed {p['year']}. Reconstructed from "
              f"{SRCURL[p['source']]}; not from the CPRA permit feed (predates it). Units {units}.")
        cur.execute("""INSERT INTO project_versions(project_id,version_label,version_type_id,
            effective_date,total_units,is_current,asserted_by,asserted_at,confidence_type_id,description)
            VALUES (?,?,5,?,?,1,?,?,?,?)""",
            (pid,"As-Built (historic reconstruction)",f"{p['year']}-01-01",units,BY,NOW,conf,desc))
        vid=cur.lastrowid
        cur.execute("UPDATE projects SET current_version_id=? WHERE id=?",(vid,pid))
        # unit program + affordability
        cur.execute("""INSERT INTO unit_program(project_version_id,bedroom_count,tenure_type_id,
            unit_count,notes,asserted_by,asserted_at,confidence_type_id)
            VALUES (?,1,1,?,?,?,?,?)""",
            (vid,units,"Bedroom mix unknown; 1BR placeholder for schema compliance",BY,NOW,conf))
        up=cur.lastrowid
        if units:
            if aff:
                cur.execute("""INSERT INTO unit_program_affordability(unit_program_id,income_category_id,
                    unit_count,asserted_by,asserted_at,confidence_type_id) VALUES (?,3,?,?,?,?)""",
                    (up,aff,BY,NOW,conf))  # LI
                cur.execute("""INSERT INTO unit_program_affordability(unit_program_id,income_category_id,
                    unit_count,asserted_by,asserted_at,confidence_type_id) VALUES (?,5,?,?,?,?)""",
                    (up,units-aff,BY,NOW,conf))  # ABOVE_MOD
            else:
                cur.execute("""INSERT INTO unit_program_affordability(unit_program_id,income_category_id,
                    unit_count,asserted_by,asserted_at,confidence_type_id) VALUES (?,6,?,?,?,?)""",
                    (up,units,BY,NOW,conf))  # UNKNOWN tier
        # parcel link, developer, classification
        cur.execute("INSERT INTO project_parcels(project_id,parcel_id,is_primary) VALUES (?,?,1)",(pid,parcel_id))
        cur.execute("""INSERT INTO project_participants(project_id,organization_id,role_type_id,
            asserted_by,asserted_at,confidence_type_id) VALUES (?,4,1,?,?,?)""",(pid,BY,NOW,conf))
        cur.execute("""INSERT INTO project_classifications(project_id,classification_type_id,
            asserted_by,asserted_at,confidence_type_id,notes,created_at)
            VALUES (?,?,?,?,?,?,?)""",(pid,cid,BY,NOW,conf,f"source: {p['source']}",NOW))
        made.append((pid,p["tour_name"],units))
    # verify via the flat view
    ids=tuple(m[0] for m in made)
    seen=cur.execute(f"SELECT COUNT(*),COALESCE(SUM(total_units),0) FROM v_projects_flat WHERE project_id IN {ids}").fetchone()
    if seen[0]!=len(made): raise RuntimeError(f"view shows {seen[0]}, expected {len(made)}")
    cur.execute("COMMIT")
    print(f"  OK created {len(made)} entities (ids {made[0][0]}-{made[-1][0]}), {seen[1]} units, classification id {cid}")
    for m in made: print(f"    proj{m[0]}  {m[1][:24]:24} {m[2]}u")
except Exception as e:
    cur.execute("ROLLBACK"); import traceback; traceback.print_exc(); print("  ROLLED BACK:",e); sys.exit(1)
finally: con.close()
