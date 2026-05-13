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

COMMIT;
