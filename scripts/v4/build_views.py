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
-- first BP (John, 2026-10-01): the earliest issuance among a building's MASTER permits and the PHASE permits a structure
-- ruling names (S002, 1951 Shattuck's Phase 1). Site work, temporary power, demolition, revisions never set it.
first_bp AS (SELECT ps.project_id, MIN(e.event_date) bp FROM ps JOIN structure_events se USING(structure_id)
             JOIN events e USING(event_id) WHERE se.role_in_structure IN ('master', 'phase') AND e.event_type_code = 'permit_issued'
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

# ADU TENURE FROM THE RENT BOARD (John, 2026-10-01: the ADU rule). Replaces ABAG's 30/30/30/10 GUESS with what the
# registry records, at three strengths that are never mixed:
#   board_labelled_adu      the Board itself labels a registered unit on the ADU's parcel as an ADU (Unit Status Code
#                           'ADU' or a designation naming ADU/JADU): that unit IS the ADU -- its status, rent, bedrooms
#   several_board_labelled  more than one such unit on the parcel: which one is unknown
#   parcel_registrations    units are registered on the parcel but none is labelled ADU: evidence about the PARCEL
#                           (n registered, how many with a tenancy begun after the ADU was finaled), never about the ADU
#   no_registration_found   nothing registered: NOT "not rented" -- owner or family use, or an unregistered rental
# Parcels join on the CURRENT canonical APN (registry rows on a retired APN are not reached here).
V_ADU_RENT_BOARD = r"""
CREATE VIEW v_adu_rent_board AS
WITH adu AS (
  SELECT s.structure_id, json_extract(s.notes, '$.master_permits[0]') master_permit, s.completed_on, s.status
  FROM structures s JOIN events e ON e.event_id = s.master_event_id
  WHERE json_extract(e.raw_payload, '$.ADU') = 'Yes'),
reg AS (
  SELECT a.structure_id, r.event_id, r.source_record_key unit_key,
         json_extract(r.raw_payload, '$."Unit Status Code"') unit_status,
         json_extract(r.raw_payload, '$."Unit Designation"') designation,
         json_extract(r.raw_payload, '$."Occupant Type"') occupant_type,
         json_extract(r.raw_payload, '$."Number of Bedrooms"') bedrooms,
         substr(json_extract(r.raw_payload, '$."Tenancy start date"'), 1, 10) tenancy_start,
         json_extract(r.raw_payload, '$."Starting Rent"') starting_rent,
         json_extract(r.raw_payload, '$."Rent Ceiling"') rent_ceiling,
         (json_extract(r.raw_payload, '$."Unit Status Code"') = 'ADU'
          OR upper(json_extract(r.raw_payload, '$."Unit Designation"')) IN ('ADU', 'JADU')
          OR upper(json_extract(r.raw_payload, '$."Unit Designation"')) LIKE '%ADU%') board_labelled
  FROM adu a JOIN structure_parcels sp USING(structure_id)
  JOIN parcel_identifiers pi ON pi.parcel_id = sp.parcel_id AND pi.is_current = 1
  JOIN events r ON r.event_type_code = 'registry_unit' AND r.raw_apn = pi.apn_normalized),
agg AS (
  SELECT a.structure_id, COUNT(reg.event_id) n_registered, COALESCE(SUM(reg.board_labelled), 0) n_labelled,
         COALESCE(SUM(a.completed_on IS NOT NULL AND reg.tenancy_start >= a.completed_on), 0) n_tenancy_after_final
  FROM adu a LEFT JOIN reg USING(structure_id) GROUP BY 1)
SELECT a.structure_id, a.master_permit, a.completed_on, a.status,
       CASE WHEN g.n_labelled = 1 THEN 'board_labelled_adu' WHEN g.n_labelled > 1 THEN 'several_board_labelled'
            WHEN g.n_registered > 0 THEN 'parcel_registrations' ELSE 'no_registration_found' END evidence,
       g.n_registered, g.n_labelled, g.n_tenancy_after_final,
       l.unit_key, l.unit_status, l.designation, l.occupant_type, l.bedrooms, l.tenancy_start, l.starting_rent,
       l.rent_ceiling
FROM adu a JOIN agg g USING(structure_id)
LEFT JOIN reg l ON l.structure_id = a.structure_id AND l.board_labelled AND g.n_labelled = 1
"""

# CITY RECORDS AT A PROJECT'S BUILDINGS (John, 2026-10-01: "load the commercial records for mixed-use projects").
# Every Accela listing (accela_listed, Building + Planning modules) whose address is one of the project's building
# addresses -- the permit address AND the ruled aliases (S003/S004) -- with its suite. This is where a ground-floor
# retail tenant improvement, a business-licence zoning certificate, a sign or a short-term-rental certificate shows
# up. in_project = the record is already one of the project's own (a master, attached or Planning record); the
# others are what happened at the building beyond its housing permits. Which of them are COMMERCIAL is the record's
# own type and text, read later -- not decided here.
V_PROJECT_LISTED = r"""
CREATE VIEW v_project_records_listed AS
WITH pa AS (SELECT DISTINCT ps.project_id, sa.address_id FROM project_structures ps JOIN structure_addresses sa USING(structure_id)),
own AS (SELECT project_id, record_key k FROM project_records
        UNION SELECT ps.project_id, e.source_record_key FROM project_structures ps JOIN structure_events se USING(structure_id)
              JOIN events e USING(event_id))
SELECT json_extract(p.notes, '$.project_key') AS project_key, p.name, e.source_record_key AS record_key,
       json_extract(e.raw_payload, '$._module') AS module,
       COALESCE(NULLIF(json_extract(e.raw_payload, '$."Record Type"'), ''), json_extract(e.raw_payload, '$."Project Name"')) AS record_type,
       e.event_date AS listed_on, json_extract(e.raw_payload, '$.Status') AS status, e.raw_description AS description,
       a.normalized AS address, ea.unit, (o.k IS NOT NULL) AS in_project
FROM pa JOIN projects p USING(project_id) JOIN event_addresses ea ON ea.address_id = pa.address_id
JOIN addresses a ON a.address_id = ea.address_id
JOIN events e ON e.event_id = ea.event_id AND e.event_type_code = 'accela_listed'
LEFT JOIN own o ON o.project_id = pa.project_id AND o.k = e.source_record_key
"""

# LICENSED BUSINESSES AT A PROJECT'S BUILDINGS TODAY (John, 2026-10-01): the City's business licences (export
# 2025-11-15) whose parcel is one of the project's buildings' CURRENT parcels, or whose location is one of their
# addresses (aliases included). matched_by says which. Rental-property licences are the building's own rental
# business (a rental licence names the owner); every other sub-type is a business AT the building -- the ground-floor
# tenants of a mixed-use project.
V_PROJECT_BUSINESSES = r"""
CREATE VIEW v_project_businesses AS
WITH pp AS (SELECT DISTINCT ps.project_id, pi.apn_normalized apn FROM project_structures ps
            JOIN structure_parcels sp USING(structure_id)
            JOIN parcel_identifiers pi ON pi.parcel_id = sp.parcel_id AND pi.is_current = 1),
pa AS (SELECT DISTINCT ps.project_id, sa.address_id FROM project_structures ps JOIN structure_addresses sa USING(structure_id)),
hit AS (SELECT pp.project_id, e.event_id, 'parcel' matched_by FROM pp
        JOIN events e ON e.event_type_code = 'business_license' AND e.raw_apn = pp.apn
        UNION
        SELECT pa.project_id, e.event_id, 'address' FROM pa JOIN event_addresses ea USING(address_id)
        JOIN events e ON e.event_id = ea.event_id AND e.event_type_code = 'business_license'),
one AS (SELECT project_id, event_id, MIN(matched_by) matched_by FROM hit GROUP BY 1, 2)  -- 'address' < 'parcel'
SELECT json_extract(p.notes, '$.project_key') AS project_key, p.name, e.source_record_key AS license,
       json_extract(e.raw_payload, '$.b1_per_sub_type') AS sub_type, json_extract(e.raw_payload, '$.dba') AS dba,
       json_extract(e.raw_payload, '$.b1_business_name') AS business_name, json_extract(e.raw_payload, '$.naics') AS naics,
       e.raw_description AS business_description, json_extract(e.raw_payload, '$.employee_num') AS employees,
       e.raw_address AS location, one.matched_by, e.event_date AS as_of
FROM one JOIN projects p USING(project_id) JOIN events e USING(event_id)
"""

# PEOPLE AND MONEY BY ROLE (John, 2026-10-01: "developer is not owner of record, just as architect or builder is
# not"). Every actor role on a project, each from ITS OWN record, never inferred from another role:
#   owner_of_record                    County assessor roll, on the project's current parcels
#   record_owner / applicant           the project's Planning records (CapDetail owner; the 2025-26 log's applicant)
#   contractor_primary / _additional the master and phase building permits' Licensed Professionals (CSLB number)
#   licensed_professional              another licence type on those permits, its type in the note
#   registry_owner / _owner_business / registry_manager   the Rent Board registry on the project's parcels
#   permit_owner                       the owner the master / phase building permit page lists
#   city_reviewer                      City staff who marked review tasks on the project's Planning records
#   inspector                          City inspectors on the building's inspections (as the record names them)
#   rental_operator / business_tenant  City business licences on the project's parcels or addresses: a 'Rental of Real
#                                      Property' licence is the rental operator; any other is a business there
#   property_manager / rental_owner / rental_owner_business   the Rent Board registry (its Manager / Owner fields)
#   funder                             the funding ledger (public money), with program, instrument and amount
#   developer / tax_credit_owner / general_partner / property_manager   CTCAC's List of Projects, by the project's
#                                      building addresses or current parcels (a UNION: a row reached both ways is one)
# John 2026-10-01: "add any other roles we didn't, such as rental operator or manager". Developer and architect come
# from the documents' title blocks (document_roles evidence) once loaded.
V_PROJECT_PEOPLE = r"""
CREATE VIEW v_project_people AS
WITH pk AS (SELECT project_id, json_extract(notes, '$.project_key') project_key FROM projects),
cur AS (SELECT DISTINCT pp.project_id, pi.apn_normalized apn FROM project_parcels pp
        JOIN parcel_identifiers pi ON pi.parcel_id = pp.parcel_id AND pi.is_current = 1)
SELECT pk.project_key, aa.role, a.display_name name, a.actor_id, s.source_kind source, NULL record, aa.coverage_note note
FROM pk JOIN project_parcels pp USING(project_id)
JOIN actor_actions aa ON aa.entity_type = 'parcel' AND aa.entity_id = pp.parcel_id AND aa.role = 'owner_of_record'
JOIN actors a USING(actor_id) LEFT JOIN sources s ON s.source_id = aa.source_id
UNION ALL
SELECT pk.project_key, aa.role, a.display_name, a.actor_id, s.source_kind, e.source_record_key, aa.coverage_note
FROM pk JOIN project_records pr USING(project_id)
JOIN events e ON e.source_record_key = pr.record_key AND e.event_type_code IN ('planning_filed', 'planning_log_entry')
JOIN actor_actions aa ON aa.event_id = e.event_id AND aa.role IN ('record_owner', 'applicant')
JOIN actors a USING(actor_id) LEFT JOIN sources s ON s.source_id = aa.source_id
UNION ALL
SELECT DISTINCT pk.project_key, 'city_reviewer', a.display_name, a.actor_id, s.source_kind, e.source_record_key, NULL
FROM pk JOIN project_records pr USING(project_id)
JOIN events e ON e.source_record_key = pr.record_key AND e.event_type_code = 'planning_task'
JOIN actor_actions aa ON aa.event_id = e.event_id AND aa.role = 'marked_review_task' 
JOIN actors a USING(actor_id) LEFT JOIN sources s ON s.source_id = aa.source_id
UNION ALL
SELECT pk.project_key, aa.role, a.display_name, a.actor_id, s.source_kind, e.source_record_key, aa.coverage_note
FROM pk JOIN project_structures ps USING(project_id)
JOIN structure_events se ON se.structure_id = ps.structure_id AND se.role_in_structure IN ('master', 'phase')
JOIN events e ON e.event_id = se.event_id
JOIN actor_actions aa ON aa.event_id = e.event_id AND aa.role IN ('contractor_primary', 'contractor_additional',
                                                                 'licensed_professional', 'permit_owner')
JOIN actors a USING(actor_id) LEFT JOIN sources s ON s.source_id = aa.source_id
UNION ALL
SELECT DISTINCT pk.project_key, CASE aa.role WHEN 'registry_manager' THEN 'property_manager'
       WHEN 'registry_owner' THEN 'rental_owner' WHEN 'registry_owner_business' THEN 'rental_owner_business' END,
       a.display_name, a.actor_id, s.source_kind, NULL, 'as the Rent Board registry lists it, 2026-07-13'
FROM pk JOIN cur USING(project_id)
JOIN events e ON e.event_type_code = 'registry_unit' AND e.raw_apn = cur.apn
JOIN actor_actions aa ON aa.event_id = e.event_id
JOIN actors a USING(actor_id) LEFT JOIN sources s ON s.source_id = aa.source_id
UNION ALL
SELECT b.project_key, CASE WHEN b.sub_type = 'Rental of Real Property' THEN 'rental_operator' ELSE 'business_tenant' END,
       COALESCE(b.business_name, b.dba), NULL, 'city_business_licenses', b.license, b.sub_type || ' -- ' || COALESCE(b.business_description, '')
FROM v_project_businesses b
UNION ALL
SELECT DISTINCT pk.project_key, 'inspector', trim(replace(replace(json_extract(e.raw_payload, '$.inspector'), '   ', ' '), '  ', ' ')),
       NULL, s.source_kind, NULL, 'as the inspection record names them'
FROM pk JOIN project_structures ps USING(project_id) JOIN structure_events se USING(structure_id)
JOIN events e ON e.event_id = se.event_id AND e.event_type_code = 'inspection'
LEFT JOIN sources s ON s.source_id = e.source_id
WHERE COALESCE(trim(json_extract(e.raw_payload, '$.inspector')), '') != ''
UNION ALL
SELECT DISTINCT pk.project_key, aa.role, a.display_name, a.actor_id, s.source_kind, e.source_record_key, aa.coverage_note
FROM pk JOIN (SELECT DISTINCT ps.project_id, sa.address_id FROM project_structures ps JOIN structure_addresses sa USING(structure_id)) pa
     USING(project_id)
JOIN event_addresses ea ON ea.address_id = pa.address_id
JOIN events e ON e.event_id = ea.event_id AND e.event_type_code = 'ctcac_project'
JOIN actor_actions aa ON aa.event_id = e.event_id
JOIN actors a USING(actor_id) LEFT JOIN sources s ON s.source_id = aa.source_id
UNION ALL
SELECT DISTINCT pk.project_key, aa.role, a.display_name, a.actor_id, s.source_kind, e.source_record_key, aa.coverage_note
FROM pk JOIN project_parcels pp USING(project_id)
JOIN events e ON e.event_type_code = 'ctcac_project'
JOIN json_each(json_extract(e.raw_payload, '$._current_parcel_ids')) cp ON cp.value = pp.parcel_id
JOIN actor_actions aa ON aa.event_id = e.event_id
JOIN actors a USING(actor_id) LEFT JOIN sources s ON s.source_id = aa.source_id
UNION ALL
SELECT pk.project_key, 'funder', json_extract(f.value, '$.funder'), NULL, 'funding_ledger', json_extract(f.value, '$.funding_id'),
       json_extract(f.value, '$.program') || ' -- ' || COALESCE(json_extract(f.value, '$.instrument'), '') || ' -- $' ||
       COALESCE(json_extract(f.value, '$.amount_usd'), '?')
FROM pk JOIN projects p USING(project_id), json_each(json_extract(p.notes, '$.funding')) f
"""

VIEWS = {"v_projects": V_PROJECTS, "v_project_timeline": V_PROJECT_RECORDS, "v_adu_rent_board": V_ADU_RENT_BOARD,
         "v_project_records_listed": V_PROJECT_LISTED, "v_project_businesses": V_PROJECT_BUSINESSES,
         "v_project_people": V_PROJECT_PEOPLE}


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
