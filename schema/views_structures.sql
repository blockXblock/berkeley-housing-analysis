-- views_structures.sql
-- Views for multi-structure queries
-- Requires: core.sql, structures.sql
-- Created: 2026-05-04

--------------------------------------------------------------------------------
-- v_unit_program_with_beds
-- Unit program with computed total beds
--------------------------------------------------------------------------------

CREATE VIEW v_unit_program_with_beds AS
SELECT
  up.*,
  CASE
    WHEN up.beds_per_unit IS NOT NULL THEN up.unit_count * up.beds_per_unit
    ELSE NULL
  END AS total_beds
FROM unit_program up;

--------------------------------------------------------------------------------
-- v_project_structures
-- Structures with type labels
--------------------------------------------------------------------------------

CREATE VIEW v_project_structures AS
SELECT
  s.*,
  vst.code AS structure_type_code,
  vst.label AS structure_type_label
FROM structures s
LEFT JOIN vocabulary_structure_types vst ON s.structure_type_id = vst.id;

--------------------------------------------------------------------------------
-- v_project_geometries_with_structures
-- Geometries with optional structure linkage
--------------------------------------------------------------------------------

CREATE VIEW v_project_geometries_with_structures AS
SELECT
  pg.*,
  s.label AS structure_label,
  vst.code AS structure_type_code
FROM project_geometries pg
LEFT JOIN structures s ON pg.structure_id = s.id
LEFT JOIN vocabulary_structure_types vst ON s.structure_type_id = vst.id;

--------------------------------------------------------------------------------
-- v_projects_with_structures_rollup
-- Projects with structure counts and aggregated heights
--------------------------------------------------------------------------------

CREATE VIEW v_projects_with_structures_rollup AS
SELECT
  p.id AS project_id,
  p.canonical_address,
  COUNT(s.id) AS structure_count,
  MAX(s.stories) AS max_stories,
  MAX(s.height_feet) AS max_height_feet,
  SUM(s.building_sqft) AS total_building_sqft
FROM projects p
LEFT JOIN structures s ON p.id = s.project_id
GROUP BY p.id;

--------------------------------------------------------------------------------
-- v_project_beds_summary
-- Bed counts by project (for UC dorm projects)
--------------------------------------------------------------------------------

CREATE VIEW v_project_beds_summary AS
SELECT
  pv.project_id,
  p.canonical_address,
  pv.total_units,
  SUM(up.unit_count * COALESCE(up.beds_per_unit, 1)) AS total_beds,
  CASE
    WHEN SUM(CASE WHEN up.beds_per_unit IS NOT NULL THEN 1 ELSE 0 END) > 0 THEN 1
    ELSE 0
  END AS has_explicit_bed_counts
FROM project_versions pv
JOIN projects p ON pv.project_id = p.id
LEFT JOIN unit_program up ON pv.id = up.project_version_id
WHERE pv.is_current = 1
GROUP BY pv.project_id;

--------------------------------------------------------------------------------
-- v_projects_current_flat
-- Flat view of current project state for common queries
--------------------------------------------------------------------------------

CREATE VIEW v_projects_current_flat AS
SELECT
  p.id AS project_id,
  p.canonical_address,
  p.latitude,
  p.longitude,
  pv.total_units,
  pv.height_stories,
  pv.height_feet,
  vps.code AS stage_code,
  vps.label AS stage_label,
  (SELECT COUNT(*) FROM structures s WHERE s.project_id = p.id) AS structure_count
FROM projects p
JOIN project_versions pv ON p.current_version_id = pv.id
LEFT JOIN vocabulary_stage_types vps ON p.current_stage_type_id = vps.id;
