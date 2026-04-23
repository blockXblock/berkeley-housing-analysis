-- ============================================================================
-- compatibility views
-- ============================================================================
-- Purpose: present the normalized schema in a shape that existing scripts
-- (export_explorer_data.py, generate_kml.py, the explorer site, the Datasette
-- deployment) can consume without modification during the migration cutover.
--
-- Naming convention:
--   - v_*       = stable views intended for external consumers
--   - v_*_vN    = versioned views; bump the suffix on breaking changes
--   - _internal views are prefixed with v_internal_ and carry no stability promise
--
-- Breaking changes to v_* views require bumping the version suffix
-- (v_projects_flat -> v_projects_flat_v2) to avoid silently breaking consumers.
--
-- IMPORTANT: These views are designed against the schema in core.sql.
-- The exact column set was driven by what export_explorer_data.py and
-- generate_kml.py appear to need based on the current flat-table shape
-- (inferred from userMemories and typical Berkeley APR export patterns).
-- The migration plan calls for Claude Code to verify each view against the
-- actual script expectations and add columns as needed during Phase 3.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- v_projects_flat
-- ----------------------------------------------------------------------------
-- Flat per-project view, one row per project, with the current-version program
-- facts and aggregated affordability counts inlined. This is the closest
-- analogue to the legacy flat projects table and is what export_explorer_data.py
-- and generate_kml.py should read from.
--
-- Columns omitted from legacy that are now accessed via dedicated views:
--   - Per-bedroom breakdowns: see v_project_unit_mix
--   - Per-income-level detail: see v_project_affordability
--   - Permits: see v_project_permits
--   - Events: see v_project_events
-- ----------------------------------------------------------------------------

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
   WHERE e.project_id = p.id AND et.code = 'building_permit_issued') AS bp_issued_date,

  (SELECT MAX(e.event_date) FROM project_events e
   JOIN vocabulary_event_types et ON et.id = e.event_type_id
   WHERE e.project_id = p.id AND et.code = 'co_issued')              AS co_issued_date,

  p.created_at,
  p.updated_at

FROM projects p
JOIN cities c ON c.id = p.city_id
LEFT JOIN project_versions pv ON pv.id = p.current_version_id
LEFT JOIN vocabulary_project_version_types pvt ON pvt.id = pv.version_type_id
LEFT JOIN vocabulary_stage_types s ON s.id = p.current_stage_type_id;

-- ----------------------------------------------------------------------------
-- v_project_unit_mix
-- ----------------------------------------------------------------------------
-- Per-project bedroom distribution, current version only.
-- One row per (project, bedroom_count, tenure_type).
-- ----------------------------------------------------------------------------

CREATE VIEW v_project_unit_mix AS
SELECT
  p.id                                   AS project_id,
  p.canonical_address                    AS address_display,
  pv.id                                  AS project_version_id,
  u.bedroom_count                        AS bedroom_count,
  tt.code                                AS tenure_code,
  tt.label                               AS tenure_label,
  u.unit_count                           AS unit_count,
  u.avg_sqft                             AS avg_sqft,
  sp.code                                AS special_population_code
FROM projects p
JOIN project_versions pv ON pv.id = p.current_version_id
JOIN unit_program u ON u.project_version_id = pv.id
JOIN vocabulary_tenure_types tt ON tt.id = u.tenure_type_id
LEFT JOIN vocabulary_special_population_types sp ON sp.id = u.special_population_type_id;

-- ----------------------------------------------------------------------------
-- v_project_affordability
-- ----------------------------------------------------------------------------
-- Per-project affordability detail, current version only.
-- Aggregated across bedroom types within each income category for readability;
-- drop the GROUP BY and add bedroom_count if a consumer wants finer grain.
-- ----------------------------------------------------------------------------

CREATE VIEW v_project_affordability AS
SELECT
  p.id                                   AS project_id,
  p.canonical_address                    AS address_display,
  pv.id                                  AS project_version_id,
  ic.code                                AS income_category,
  ic.label                               AS income_category_label,
  SUM(a.unit_count)                      AS unit_count,
  MIN(a.ami_min)                         AS ami_min,
  MAX(a.ami_max)                         AS ami_max,
  GROUP_CONCAT(DISTINCT rt.code)         AS restriction_codes
FROM projects p
JOIN project_versions pv ON pv.id = p.current_version_id
JOIN unit_program u ON u.project_version_id = pv.id
JOIN unit_program_affordability a ON a.unit_program_id = u.id
JOIN vocabulary_income_categories ic ON ic.id = a.income_category_id
LEFT JOIN vocabulary_restriction_types rt ON rt.id = a.restriction_type_id
GROUP BY p.id, pv.id, ic.id;

-- ----------------------------------------------------------------------------
-- v_project_permits
-- ----------------------------------------------------------------------------

CREATE VIEW v_project_permits AS
SELECT
  p.id                                   AS project_id,
  p.canonical_address                    AS address_display,
  pt.code                                AS permit_type_code,
  pt.label                               AS permit_type_label,
  ps.code                                AS permit_status_code,
  ps.label                               AS permit_status_label,
  pr.permit_number                       AS permit_number,
  pr.source_permit_id                    AS source_permit_id,
  pr.source_system                       AS source_system,
  pr.filed_date                          AS filed_date,
  pr.issued_date                         AS issued_date,
  pr.finaled_date                        AS finaled_date,
  pr.valuation                           AS valuation,
  pr.source_url                          AS source_url,
  pr.description                         AS description
FROM projects p
JOIN permits pr ON pr.project_id = p.id
LEFT JOIN vocabulary_permit_types pt ON pt.id = pr.permit_type_id
LEFT JOIN vocabulary_permit_status_types ps ON ps.id = pr.permit_status_type_id;

-- ----------------------------------------------------------------------------
-- v_project_events
-- ----------------------------------------------------------------------------

CREATE VIEW v_project_events AS
SELECT
  e.id                                   AS event_id,
  p.id                                   AS project_id,
  p.canonical_address                    AS address_display,
  et.code                                AS event_type_code,
  et.label                               AS event_type_label,
  e.event_date                           AS event_date,
  e.event_date_precision                 AS event_date_precision,
  e.event_end_date                       AS event_end_date,
  e.summary                              AS summary,
  e.details                              AS details,
  e.units_affected                       AS units_affected,
  e.is_inferred                          AS is_inferred,
  cf.code                                AS confidence_code,
  e.source_type                          AS source_type,
  e.source_url                           AS source_url,
  e.observed_by                          AS observed_by,
  e.observed_at                          AS observed_at,
  pr.permit_number                       AS linked_permit_number,
  d.title                                AS linked_document_title
FROM project_events e
JOIN projects p ON p.id = e.project_id
JOIN vocabulary_event_types et ON et.id = e.event_type_id
LEFT JOIN vocabulary_confidence_types cf ON cf.id = e.confidence_type_id
LEFT JOIN permits pr ON pr.id = e.permit_id
LEFT JOIN documents d ON d.id = e.document_id;

-- ----------------------------------------------------------------------------
-- v_project_geometries_current
-- ----------------------------------------------------------------------------
-- Current geometry of each type for each project. Used by generate_kml.py
-- and the 3D visualization pipeline.
-- ----------------------------------------------------------------------------

CREATE VIEW v_project_geometries_current AS
SELECT
  g.id                                   AS geometry_id,
  p.id                                   AS project_id,
  p.canonical_address                    AS address_display,
  gt.code                                AS geometry_type_code,
  gt.label                               AS geometry_type_label,
  g.geojson                              AS geojson,
  g.height_meters                        AS height_meters,
  g.base_elevation_meters                AS base_elevation_meters,
  g.version_label                        AS version_label,
  g.edited_by                            AS edited_by,
  g.edit_notes                           AS edit_notes,
  d.title                                AS source_document_title,
  g.created_at                           AS created_at,
  g.updated_at                           AS updated_at
FROM project_geometries g
JOIN projects p ON p.id = g.project_id
JOIN vocabulary_geometry_types gt ON gt.id = g.geometry_type_id
LEFT JOIN documents d ON d.id = g.source_document_id
WHERE g.is_current = 1;

-- ----------------------------------------------------------------------------
-- v_project_documents
-- ----------------------------------------------------------------------------

CREATE VIEW v_project_documents AS
SELECT
  d.id                                   AS document_id,
  p.id                                   AS project_id,
  p.canonical_address                    AS address_display,
  dt.code                                AS document_type_code,
  dt.label                               AS document_type_label,
  d.title                                AS title,
  d.published_date                       AS published_date,
  d.permit_number                        AS permit_number,
  d.source_url                           AS source_url,
  d.source_system                        AS source_system,
  d.url_status                           AS url_status,
  d.url_last_verified                    AS url_last_verified,
  d.ia_url                               AS ia_url,
  d.r2_url                               AS r2_url,
  d.drive_url                            AS drive_url,
  d.sha256                               AS sha256,
  d.file_size_bytes                      AS file_size_bytes,
  d.page_count                           AS page_count,
  d.fetched_at                           AS fetched_at,
  -- Mirror status: how many mirrors do we have for this document?
  (CASE WHEN d.ia_url IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN d.r2_url IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN d.drive_url IS NOT NULL THEN 1 ELSE 0 END) AS mirror_count
FROM documents d
JOIN projects p ON p.id = d.project_id
LEFT JOIN vocabulary_document_types dt ON dt.id = d.document_type_id;

-- ----------------------------------------------------------------------------
-- v_project_stage_spans
-- ----------------------------------------------------------------------------
-- Derived timeline spans from project_events. One row per (project, stage)
-- with start_date = earliest event implying that stage, end_date = next stage's
-- start minus one day, or NULL if current.
--
-- This replaces the project_stage_spans table originally proposed by Perplexity.
-- At 174 projects, materialization is unnecessary; if the view becomes slow,
-- materialize in a follow-up pass.
-- ----------------------------------------------------------------------------

CREATE VIEW v_project_stage_spans AS
WITH stage_entries AS (
  SELECT
    e.project_id,
    et.implies_stage_type_id AS stage_type_id,
    MIN(e.event_date) AS start_date
  FROM project_events e
  JOIN vocabulary_event_types et ON et.id = e.event_type_id
  WHERE et.implies_stage_type_id IS NOT NULL
    AND e.event_date IS NOT NULL
  GROUP BY e.project_id, et.implies_stage_type_id
),
ordered AS (
  SELECT
    se.project_id,
    se.stage_type_id,
    se.start_date,
    LEAD(se.start_date) OVER (PARTITION BY se.project_id ORDER BY se.start_date) AS next_start
  FROM stage_entries se
)
SELECT
  o.project_id,
  p.canonical_address AS address_display,
  st.code AS stage_code,
  st.label AS stage_label,
  o.start_date,
  o.next_start AS end_date,
  (o.next_start IS NULL) AS is_current_stage
FROM ordered o
JOIN projects p ON p.id = o.project_id
JOIN vocabulary_stage_types st ON st.id = o.stage_type_id;

-- ----------------------------------------------------------------------------
-- v_organizations_with_projects
-- ----------------------------------------------------------------------------
-- Convenience view for "all projects by organization X" queries.
-- ----------------------------------------------------------------------------

CREATE VIEW v_organizations_with_projects AS
SELECT
  o.id                                   AS organization_id,
  o.name                                 AS organization_name,
  o.normalized_name                      AS organization_normalized_name,
  ot.code                                AS organization_type_code,
  rt.code                                AS role_code,
  rt.label                               AS role_label,
  p.id                                   AS project_id,
  p.canonical_address                    AS address_display,
  pp.start_date                          AS role_start_date,
  pp.end_date                            AS role_end_date
FROM organizations o
JOIN project_participants pp ON pp.organization_id = o.id
JOIN projects p ON p.id = pp.project_id
JOIN vocabulary_role_types rt ON rt.id = pp.role_type_id
LEFT JOIN vocabulary_organization_types ot ON ot.id = o.organization_type_id;

-- End of views_compat.sql
