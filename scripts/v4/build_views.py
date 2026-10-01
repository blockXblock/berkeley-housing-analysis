#!/usr/bin/env python3
r"""build_views.py -- THE SERVING LAYER (cutover phase 6, decision D8). The last chain step.

Publishers read VIEWS, never re-derive a field. Each view is defined ONCE here, over the build's tables and the
projects' notes, and is recreated on every build (DROP + CREATE) because it is a projection, not data.

DECISIONS IT IMPLEMENTS (John, 2026-09-30, notes/v4/2026-09-30_phase6_field_map.md):
  D1  public id = project_key (anchor record, else first master permit, else external id); project_id is internal.
  D2  status from evidence: completed / under_construction / stale / entitled / in_review / withdrawn / denied / void;
      a project outside City permitting keeps its source status.
  D3  co_issued_date = the LAST building's completion (the project is complete); first_co_date alongside.
  D4  units: a project with buildings counts its buildings; an application-only project shows its STATED proposal
      (proposed_units), never mixed into built units.
  D5  developer/architect: not published (v2's were unsourced); record_owner and applicant instead.
  sq ft / parking / storeys / height (John: KEEP, from sources): the verbatim-quoted measures; the City's parcel-level
      taxable building sq ft alongside as a cross-check, labelled parcel-level.

  .venv/bin/python scripts/v4/build_views.py --db BUILD.db      # refuses live unless BUILD_VIEWS_ALLOW_LIVE=1
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
V4 = ROOT / "databases/berkeley_housing_v4.db"

V_PROJECTS = r"""
CREATE VIEW v_projects AS
WITH
ps AS (SELECT ps.project_id, s.structure_id, s.status, s.completed_on FROM project_structures ps
       JOIN structures s USING(structure_id)),
built AS (SELECT project_id, COUNT(*) n_buildings,
                 SUM(status = 'complete') n_complete, SUM(status = 'STALE_NEEDS_SOURCE') n_stale,
                 MIN(completed_on) first_co, MAX(completed_on) last_co
          FROM ps GROUP BY project_id),
units_b AS (SELECT ps.project_id, SUM(u.unit_count) units FROM ps JOIN units u USING(structure_id) GROUP BY 1),
adu_b AS (SELECT ps.project_id, SUM(u.unit_count) adu_units FROM ps JOIN units u USING(structure_id)
          JOIN structures s USING(structure_id) JOIN events e ON e.event_id = s.master_event_id
          WHERE json_extract(e.raw_payload, '$.ADU') = 'Yes' GROUP BY 1),          -- the CPRA permit's own ADU field
first_bp AS (SELECT ps.project_id, MIN(e.event_date) bp FROM ps JOIN structure_events se USING(structure_id)
             JOIN events e USING(event_id) WHERE se.role_in_structure = 'master' AND e.event_type_code = 'permit_issued'
             GROUP BY 1),
valuation AS (SELECT ps.project_id, SUM(CAST(json_extract(e.raw_payload, '$.JobValuation') AS REAL)) v
              FROM ps JOIN structures s USING(structure_id) JOIN events e ON e.event_id = s.master_event_id GROUP BY 1),
par AS (SELECT project_id, MIN(parcel_id) parcel_id FROM project_parcels GROUP BY 1),
pt AS (SELECT par.project_id, json_extract(g.geojson, '$.properties.label_point[1]') lat,
              json_extract(g.geojson, '$.properties.label_point[0]') lon
       FROM par JOIN geometries g ON g.entity_type = 'parcel' AND g.entity_id = par.parcel_id),
av AS (SELECT pp.project_id, SUM(a.land + a.improvements) assessed_value, SUM(a.total_net_value) net_taxable,
              MAX(a.as_of_date) as_of FROM project_parcels pp JOIN assessed_values a USING(parcel_id) GROUP BY 1),
area AS (SELECT pp.project_id, SUM(ar.building_sqft_taxable) bsf FROM project_parcels pp
         JOIN parcel_area ar USING(parcel_id) GROUP BY 1),
own AS (SELECT pp.project_id, group_concat(DISTINCT ac.display_name) owners FROM project_parcels pp
        JOIN actor_actions aa ON aa.entity_type = 'parcel' AND aa.entity_id = pp.parcel_id AND aa.role = 'owner_of_record'
        JOIN actors ac USING(actor_id) GROUP BY 1),
appl AS (SELECT pr.project_id, group_concat(DISTINCT ac.display_name) applicants FROM project_records pr
         JOIN events e ON e.source_record_key = pr.record_key AND e.event_type_code = 'planning_log_entry'
         JOIN actor_actions aa ON aa.event_id = e.event_id AND aa.role = 'applicant' JOIN actors ac USING(actor_id)
         GROUP BY 1),
tiers AS (SELECT p.project_id,
                 SUM(CASE WHEN json_extract(t.value, '$.income_tier') = 'ELI' THEN CAST(json_extract(t.value, '$.units') AS INT) END) eli,
                 SUM(CASE WHEN json_extract(t.value, '$.income_tier') = 'VLI' THEN CAST(json_extract(t.value, '$.units') AS INT) END) vli,
                 SUM(CASE WHEN json_extract(t.value, '$.income_tier') = 'LI'  THEN CAST(json_extract(t.value, '$.units') AS INT) END) li,
                 SUM(CASE WHEN json_extract(t.value, '$.income_tier') = 'MOD' THEN CAST(json_extract(t.value, '$.units') AS INT) END) mod
          FROM projects p, json_each(json_extract(p.notes, '$.affordability')) t GROUP BY 1)
SELECT
  json_extract(p.notes, '$.project_key')                          AS project_key,      -- D1 public id
  p.project_id                                                    AS project_id,       -- internal; renumbers
  p.name                                                          AS name,
  json_extract(p.notes, '$.name_basis')                           AS name_basis,
  json_extract(p.notes, '$.address')                              AS address_display,
  json_extract(p.notes, '$.anchor')                               AS anchor_record,
  json_extract(p.notes, '$.anchor_role')                          AS anchor_role,
  pt.lat AS latitude, pt.lon AS longitude,
  CASE                                                                                 -- D2
    WHEN json_extract(p.notes, '$.anchor_role') = 'outside_city_permitting' THEN json_extract(p.notes, '$.status')
    WHEN b.n_buildings > 0 AND b.n_complete = b.n_buildings THEN 'completed'
    WHEN b.n_buildings > 0 AND b.n_stale = b.n_buildings THEN 'stale'
    WHEN b.n_buildings > 0 THEN 'under_construction'
    WHEN json_extract(p.notes, '$.denied') IS NOT NULL OR json_extract(p.notes, '$.record_status') = 'Denied' THEN 'denied'
    WHEN json_extract(p.notes, '$.ended') = 'Withdrawn' OR json_extract(p.notes, '$.record_status') = 'Withdrawn' THEN 'withdrawn'
    WHEN json_extract(p.notes, '$.ended') = 'Void' OR json_extract(p.notes, '$.record_status') IN ('Void', 'Expired') THEN 'void'
    WHEN json_extract(p.notes, '$.entitled') IS NOT NULL THEN 'entitled'
    ELSE 'in_review' END                                          AS status,
  COALESCE(b.n_buildings, 0)                                      AS n_buildings,
  COALESCE(u.units, 0)                                            AS units_built_or_permitted,                -- D4
  json_extract(p.notes, '$.proposed_units')                       AS proposed_units,                          -- D4
  COALESCE(adu.adu_units, 0)                                      AS adu_units,
  json_extract(p.notes, '$.beds')                                 AS beds,
  t.eli AS eli_units, t.vli AS vli_units, t.li AS li_units, t.mod AS mod_units,
  CASE WHEN COALESCE(u.units, 0) > 0 AND t.project_id IS NOT NULL
       THEN u.units - COALESCE(t.eli,0) - COALESCE(t.vli,0) - COALESCE(t.li,0) - COALESCE(t.mod,0) END AS market_units,
  json_extract(p.notes, '$.measures.gross_sqft.value')            AS building_sqft,
  json_extract(p.notes, '$.measures.parking_spaces.value')        AS parking_spaces,
  json_extract(p.notes, '$.measures.stories.value')               AS height_stories,
  json_extract(p.notes, '$.measures.height_feet.value')           AS height_feet,
  ar.bsf                                                          AS parcel_taxable_building_sqft,           -- parcel-level cross-check
  val.v                                                           AS construction_valuation,
  json_extract(p.notes, '$.pathways')                             AS pathways,
  json_extract(p.notes, '$.filed')                                AS filed_date,
  json_extract(p.notes, '$.accepted')                             AS accepted_date,
  json_extract(p.notes, '$.entitled')                             AS entitled_date,
  json_extract(p.notes, '$.entitled_by')                          AS entitled_by,
  fb.bp                                                           AS bp_issued_date,
  CASE WHEN b.n_buildings > 0 AND b.n_complete = b.n_buildings THEN b.last_co
       WHEN json_extract(p.notes, '$.anchor_role') = 'outside_city_permitting'
            AND json_extract(p.notes, '$.status') = 'completed' THEN json_extract(p.notes, '$.status_date')
       END                                                        AS co_issued_date,                          -- D3
  b.first_co                                                      AS first_co_date,
  o.owners                                                        AS owner_current,                           -- D5
  ap.applicants                                                   AS planning_applicant,                      -- D5
  av.assessed_value, av.net_taxable AS assessed_net_taxable, av.as_of AS assessed_as_of_date,
  ROUND(av.net_taxable * 0.0125)                                  AS est_annual_tax_1pct_rule,
  CASE WHEN json_extract(p.notes, '$.anchor_role') = 'outside_city_permitting'
         OR EXISTS (SELECT 1 FROM json_each(json_extract(p.notes, '$.classifications')) c
                    WHERE json_extract(c.value, '$.rhna_effect') LIKE 'EXCLUDE%')
       THEN 1 ELSE 0 END                                          AS rhna_excluded,   -- UC (classification rulings)
  json_extract(p.notes, '$.classifications')                      AS classifications,
  json_extract(p.notes, '$.affordability')                        AS affordability_evidence,
  json_extract(p.notes, '$.funding')                              AS funding
FROM projects p
LEFT JOIN built b USING(project_id) LEFT JOIN units_b u USING(project_id) LEFT JOIN first_bp fb USING(project_id)
LEFT JOIN valuation val USING(project_id) LEFT JOIN pt USING(project_id) LEFT JOIN av USING(project_id)
LEFT JOIN area ar USING(project_id) LEFT JOIN own o USING(project_id) LEFT JOIN appl ap USING(project_id)
LEFT JOIN tiers t USING(project_id) LEFT JOIN adu_b adu USING(project_id)
"""

V_PROJECT_RECORDS = r"""
CREATE VIEW v_project_timeline AS
SELECT json_extract(p.notes, '$.project_key') AS project_key, pr.record_key, pr.role, e.event_type_code, e.event_date,
       e.raw_description
FROM projects p JOIN project_records pr USING(project_id)
JOIN events e ON e.source_record_key = pr.record_key AND e.event_type_code IN ('planning_filed', 'planning_task')
UNION ALL
SELECT json_extract(p.notes, '$.project_key'), json_extract(s.notes, '$.master_permits[0]'), se.role_in_structure,
       e.event_type_code, e.event_date, e.raw_description
FROM projects p JOIN project_structures ps USING(project_id) JOIN structures s USING(structure_id)
JOIN structure_events se USING(structure_id) JOIN events e USING(event_id)
WHERE e.event_type_code IN ('permit_submitted', 'permit_issued', 'permit_finaled', 'permit_completed')
"""

VIEWS = {"v_projects": V_PROJECTS, "v_project_timeline": V_PROJECT_RECORDS}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    a = ap.parse_args()
    if Path(a.db).resolve() == V4.resolve() and os.environ.get("BUILD_VIEWS_ALLOW_LIVE") != "1":
        raise SystemExit("REFUSED: views reach live by swapping in a verified build, not by writing live.")
    con = sqlite3.connect(a.db)
    for name, ddl in VIEWS.items():
        con.execute(f"DROP VIEW IF EXISTS {name}")
        con.execute(ddl)
    con.commit()
    for name in VIEWS:
        n = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"{name}: {n} rows")
    np_ = con.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    nv = con.execute("SELECT COUNT(*), COUNT(DISTINCT project_key) FROM v_projects").fetchone()
    assert nv[0] == np_ and nv[1] == np_, f"v_projects must have one row per project and unique keys: {nv} vs {np_}"
    print("v_projects: one row per project, project_key unique -- OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
