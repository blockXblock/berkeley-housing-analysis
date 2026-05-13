-- Migration: 2026-05-13 — corrupted event date corrections
-- Context: v1→v2 migration created placeholder dates ('2018' year-only,
--          '2024-01-01' placeholders) for events where source data was
--          incomplete. Three projects identified with verified Accela
--          dates via Chrome Claude lookup on 2026-05-13.
-- Also: 2 new R-2 projects from CPRA import lacked current_stage_type_id;
--       set to 'permitted' (id=4).

BEGIN TRANSACTION;

-- Project 179 (2352 Shattuck Ave): "2018" year-only -> verified date
-- Event ID 2611: entitlement_approved
UPDATE project_events
SET event_date = '2019-10-24',
    event_date_precision = NULL,
    summary = 'Approved (verified: Staff Decision 10/24/2019 by Sharon Gong)',
    observed_by = 'Sharon Gong',
    source_type = 'city_portal'
WHERE id = 2611;

-- Project 140 (2136 San Pablo Ave): 2024-01-01 placeholder -> verified date
-- Event ID 240: application_submitted
UPDATE project_events
SET event_date = '2021-03-18',
    event_date_precision = NULL,
    summary = 'Filed (verified: ZP2021-0046 filed 03/18/2021)',
    observed_by = 'accela_verified',
    source_type = 'city_portal'
WHERE id = 240;

-- Project 149 (2198 San Pablo Ave): 2024-01-01 placeholder -> verified date
-- Event ID 261: application_submitted
UPDATE project_events
SET event_date = '2018-05-31',
    event_date_precision = NULL,
    summary = 'Filed (verified: ZP2018-0112 filed 05/31/2018)',
    observed_by = 'accela_verified',
    source_type = 'city_portal'
WHERE id = 261;

-- Projects 183 (2328 Channing Way) and 184 (2330 Blake St): NULL stage -> permitted
UPDATE projects
SET current_stage_type_id = 4,
    updated_at = CURRENT_TIMESTAMP
WHERE id IN (183, 184) AND current_stage_type_id IS NULL;

-- Fix A: Advance current_stage_type_id to match events (38 projects)
-- Logic: For projects where events imply a MORE ADVANCED stage than stored,
-- update to match. Skip withdrawn/stalled/pre_application (manual flags).
-- Skip "regression" cases where events imply EARLIER stage (missing events).
WITH project_events_summary AS (
  SELECT
    p.id as project_id,
    p.current_stage_type_id as current_stage_id,
    MAX(CASE WHEN vet.code = 'application_submitted' THEN 1 ELSE 0 END) as has_app_sub,
    MAX(CASE WHEN vet.code = 'application_complete' THEN 1 ELSE 0 END) as has_app_complete,
    MAX(CASE WHEN vet.code = 'entitlement_approved' THEN 1 ELSE 0 END) as has_entitled,
    MAX(CASE WHEN vet.code = 'building_permit_issued' THEN 1 ELSE 0 END) as has_bp,
    MAX(CASE WHEN vet.code = 'construction_start_observed' THEN 1 ELSE 0 END) as has_construction,
    MAX(CASE WHEN vet.code = 'topped_out' THEN 1 ELSE 0 END) as has_topped_out,
    MAX(CASE WHEN vet.code = 'co_issued' THEN 1 ELSE 0 END) as has_co,
    MAX(CASE WHEN vet.code = 'project_withdrawn' THEN 1 ELSE 0 END) as has_withdrawn
  FROM projects p
  LEFT JOIN project_events pe ON pe.project_id = p.id
  LEFT JOIN vocabulary_event_types vet ON vet.id = pe.event_type_id
  GROUP BY p.id
),
proposed AS (
  SELECT
    project_id,
    current_stage_id,
    CASE
      WHEN has_withdrawn = 1 THEN 8  -- withdrawn
      WHEN has_co = 1 THEN 6  -- completed
      WHEN has_topped_out = 1 OR has_construction = 1 THEN 5  -- under_construction
      WHEN has_bp = 1 THEN 4  -- permitted
      WHEN has_entitled = 1 THEN 3  -- entitled
      WHEN has_app_complete = 1 OR has_app_sub = 1 THEN 2  -- in_review
      ELSE current_stage_id
    END as proposed_stage_id
  FROM project_events_summary
)
UPDATE projects
SET current_stage_type_id = (
  SELECT proposed_stage_id
  FROM proposed
  WHERE proposed.project_id = projects.id
),
updated_at = CURRENT_TIMESTAMP
WHERE id IN (
  SELECT project_id
  FROM proposed
  WHERE current_stage_id IS NOT NULL
    AND proposed_stage_id > current_stage_id  -- Only advance, never reverse
    AND current_stage_id NOT IN (7, 8)  -- Don't override stalled or withdrawn
    AND current_stage_id != 1  -- Don't override pre_application
);

-- Step C: Mark 105 Jan 1 placeholder dates as inferred (year-only precision)
-- These are migration-created placeholder dates where v1 had year-only data.
-- Setting event_date_precision='year' and source_type='inferred' so downstream
-- consumers know these dates are approximations requiring Accela verification.
UPDATE project_events
SET event_date_precision = 'year',
    source_type = 'inferred'
WHERE event_date LIKE '%-01-01'
  AND observed_by = 'migration_v1_to_v2_20260507'
  AND (summary IS NULL OR summary = '')
  AND event_type_id IN (
    SELECT id FROM vocabulary_event_types
    WHERE code IN ('application_submitted', 'application_complete', 'entitlement_approved', 'building_permit_issued')
  );

-- Step D: Deduplicate documents and events
-- v1→v2 migration imported from overlapping source files (e.g., both
-- 1598_UNIVERSITY.txt and ZP2022-0011_1598_UNIVERSITY_Ave.txt) without
-- deduplication. Removes 138 duplicate documents and 447 duplicate events.

-- Dedupe documents: keep lowest ID per (project_id, title, published_date)
DELETE FROM documents WHERE id NOT IN (
  SELECT MIN(id) FROM documents GROUP BY project_id, title, COALESCE(published_date,'')
);

-- Dedupe events: keep lowest ID per (project_id, event_date, event_type_id, summary, observed_by)
DELETE FROM project_events WHERE id NOT IN (
  SELECT MIN(id) FROM project_events
  GROUP BY project_id, event_date, event_type_id, COALESCE(summary,''), COALESCE(observed_by,'')
);

COMMIT;
