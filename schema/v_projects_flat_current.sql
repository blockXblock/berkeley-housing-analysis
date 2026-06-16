-- v_projects_flat — AUTHORITATIVE CURRENT definition (extracted from the live canonical DB 2026-06-16).
-- The live DB is the source of truth. schema/views_compat.sql carries a STALE/drifted copy
-- (missing the merged_into_id soft-retire filter, the ADR-001 4-tier co_issued_date precedence,
-- bp_issued_date, and the ADR-002 verdict logic) — do NOT rebuild from it. This file adds the
-- project_assessed_value LEFT JOIN (assessed_value / assessed_net_taxable / assessed_exemption /
-- est_annual_tax / assessed_as_of_date). Recreate with: DROP VIEW v_projects_flat; then this.

CREATE VIEW v_projects_flat AS
SELECT
  p.id                                   AS project_id,
  c.slug                                 AS city_slug,
  p.canonical_name                       AS name,
  p.canonical_address                    AS address_display,
  p.normalized_address                   AS address_normalized,
  p.latitude                             AS latitude,
  p.longitude                            AS longitude,

  -- Current stage
  s.code                                 AS status_code,
  s.label                                AS status_label,

  -- Current version program facts
  pv.id                                  AS current_version_id,
  pvt.code                               AS current_version_type,
  pv.effective_date                      AS current_version_date,
  pv.total_units                         AS total_units,
  pv.building_sqft                       AS building_sqft,
  pv.height_stories                      AS height_stories,
  pv.height_feet                         AS height_feet,
  pv.parking_spaces                      AS parking_spaces,

  -- Aggregated affordability (current version only)
  COALESCE((
    SELECT SUM(a.unit_count)
    FROM unit_program u
    JOIN unit_program_affordability a ON a.unit_program_id = u.id
    JOIN vocabulary_income_categories ic ON ic.id = a.income_category_id
    WHERE u.project_version_id = pv.id AND ic.code = 'ELI'
  ), 0)                                  AS eli_units,

  COALESCE((
    SELECT SUM(a.unit_count)
    FROM unit_program u
    JOIN unit_program_affordability a ON a.unit_program_id = u.id
    JOIN vocabulary_income_categories ic ON ic.id = a.income_category_id
    WHERE u.project_version_id = pv.id AND ic.code = 'VLI'
  ), 0)                                  AS vli_units,

  COALESCE((
    SELECT SUM(a.unit_count)
    FROM unit_program u
    JOIN unit_program_affordability a ON a.unit_program_id = u.id
    JOIN vocabulary_income_categories ic ON ic.id = a.income_category_id
    WHERE u.project_version_id = pv.id AND ic.code = 'LI'
  ), 0)                                  AS li_units,

  COALESCE((
    SELECT SUM(a.unit_count)
    FROM unit_program u
    JOIN unit_program_affordability a ON a.unit_program_id = u.id
    JOIN vocabulary_income_categories ic ON ic.id = a.income_category_id
    WHERE u.project_version_id = pv.id AND ic.code = 'MOD'
  ), 0)                                  AS mod_units,

  COALESCE((
    SELECT SUM(a.unit_count)
    FROM unit_program u
    JOIN unit_program_affordability a ON a.unit_program_id = u.id
    JOIN vocabulary_income_categories ic ON ic.id = a.income_category_id
    WHERE u.project_version_id = pv.id AND ic.code = 'ABOVE_MOD'
  ), 0)                                  AS market_units,

  -- Primary stakeholders (current version where defined, else latest)
  (SELECT o.name FROM project_participants pp
   JOIN organizations o ON o.id = pp.organization_id
   JOIN vocabulary_role_types rt ON rt.id = pp.role_type_id
   WHERE pp.project_id = p.id AND rt.code = 'developer_of_record'
   ORDER BY pp.start_date DESC NULLS LAST LIMIT 1)   AS developer,

  (SELECT o.name FROM project_participants pp
   JOIN organizations o ON o.id = pp.organization_id
   JOIN vocabulary_role_types rt ON rt.id = pp.role_type_id
   WHERE pp.project_id = p.id AND rt.code LIKE 'architect%'
   ORDER BY pp.start_date DESC NULLS LAST LIMIT 1)   AS architect,

  (SELECT o.name FROM project_participants pp
   JOIN organizations o ON o.id = pp.organization_id
   JOIN vocabulary_role_types rt ON rt.id = pp.role_type_id
   WHERE pp.project_id = p.id AND rt.code = 'owner_current'
   ORDER BY pp.start_date DESC NULLS LAST LIMIT 1)   AS owner_current,

  -- Timeline anchors (most recent of each event type)
  (SELECT MAX(e.event_date) FROM project_events e
   JOIN vocabulary_event_types et ON et.id = e.event_type_id
   WHERE e.project_id = p.id AND et.code = 'application_submitted')  AS filed_date,

  (SELECT MAX(e.event_date) FROM project_events e
   JOIN vocabulary_event_types et ON et.id = e.event_type_id
   WHERE e.project_id = p.id AND et.code = 'entitlement_approved')   AS entitled_date,

  (SELECT MAX(e.event_date) FROM project_events e
   JOIN vocabulary_event_types et ON et.id = e.event_type_id
   WHERE e.project_id = p.id AND et.code = 'building_permit_issued' AND NOT EXISTS(SELECT 1 FROM project_events c JOIN vocabulary_event_types ct ON ct.id=c.event_type_id WHERE ct.code='permit_classified_subsidiary' AND c.permit_id=e.permit_id)) AS bp_issued_date,

  COALESCE(
   (SELECT MAX(e.event_date) FROM project_events e JOIN vocabulary_event_types et ON et.id=e.event_type_id WHERE e.project_id=p.id AND et.code='permit_finaled' AND e.is_inferred=0 AND IFNULL(e.event_date,'')<>'2024-01-01' AND NOT EXISTS(SELECT 1 FROM permits pp WHERE pp.id=e.permit_id AND (pp.completion_verdict IN ('does_not','ambiguous') OR (pp.completion_verdict='completes' AND pp.completion_basis='contested')))),
   (SELECT MAX(e.event_date) FROM project_events e JOIN vocabulary_event_types et ON et.id=e.event_type_id WHERE e.project_id=p.id AND et.code='co_issued' AND e.is_inferred=0 AND IFNULL(e.event_date,'')<>'2024-01-01' AND NOT EXISTS(SELECT 1 FROM permits pp WHERE pp.id=e.permit_id AND (pp.completion_verdict IN ('does_not','ambiguous') OR (pp.completion_verdict='completes' AND pp.completion_basis='contested')))),
   (SELECT MAX(e.event_date) FROM project_events e JOIN vocabulary_event_types et ON et.id=e.event_type_id WHERE e.project_id=p.id AND et.code='co_issued' AND IFNULL(e.event_date,'')<>'2024-01-01' AND NOT EXISTS(SELECT 1 FROM permits pp WHERE pp.id=e.permit_id AND (pp.completion_verdict IN ('does_not','ambiguous') OR (pp.completion_verdict='completes' AND pp.completion_basis='contested')))),
   (SELECT MAX(e.event_date) FROM project_events e JOIN vocabulary_event_types et ON et.id=e.event_type_id WHERE e.project_id=p.id AND et.code='co_issued' AND NOT EXISTS(SELECT 1 FROM permits pp WHERE pp.id=e.permit_id AND (pp.completion_verdict IN ('does_not','ambiguous') OR (pp.completion_verdict='completes' AND pp.completion_basis='contested'))))
  )
  AS co_issued_date,

  COALESCE(
   (SELECT MAX(e.event_date) FROM project_events e JOIN vocabulary_event_types et ON et.id=e.event_type_id WHERE e.project_id=p.id AND et.code='permit_finaled' AND e.is_inferred=0 AND IFNULL(e.event_date,'')<>'2024-01-01' AND EXISTS(SELECT 1 FROM permits pp WHERE pp.id=e.permit_id AND pp.completion_verdict='completes' AND pp.completion_basis='contested')),
   (SELECT MAX(e.event_date) FROM project_events e JOIN vocabulary_event_types et ON et.id=e.event_type_id WHERE e.project_id=p.id AND et.code='co_issued' AND e.is_inferred=0 AND IFNULL(e.event_date,'')<>'2024-01-01' AND EXISTS(SELECT 1 FROM permits pp WHERE pp.id=e.permit_id AND pp.completion_verdict='completes' AND pp.completion_basis='contested')),
   (SELECT MAX(e.event_date) FROM project_events e JOIN vocabulary_event_types et ON et.id=e.event_type_id WHERE e.project_id=p.id AND et.code='co_issued' AND IFNULL(e.event_date,'')<>'2024-01-01' AND EXISTS(SELECT 1 FROM permits pp WHERE pp.id=e.permit_id AND pp.completion_verdict='completes' AND pp.completion_basis='contested')),
   (SELECT MAX(e.event_date) FROM project_events e JOIN vocabulary_event_types et ON et.id=e.event_type_id WHERE e.project_id=p.id AND et.code='co_issued' AND EXISTS(SELECT 1 FROM permits pp WHERE pp.id=e.permit_id AND pp.completion_verdict='completes' AND pp.completion_basis='contested'))
  )
  AS co_issued_contested_date,

  p.created_at,
  p.updated_at,
  pav.assessed_value          AS assessed_value,
  pav.total_net_value         AS assessed_net_taxable,
  pav.exemption_amount        AS assessed_exemption,
  pav.est_annual_ad_valorem_tax AS est_annual_tax,
  pav.as_of_date              AS assessed_as_of_date

FROM projects p
JOIN cities c ON c.id = p.city_id
LEFT JOIN project_versions pv ON pv.id = p.current_version_id
LEFT JOIN vocabulary_project_version_types pvt ON pvt.id = pv.version_type_id
LEFT JOIN vocabulary_stage_types s ON s.id = p.current_stage_type_id
LEFT JOIN project_assessed_value pav ON pav.project_id = p.id
WHERE p.merged_into_id IS NULL
;
