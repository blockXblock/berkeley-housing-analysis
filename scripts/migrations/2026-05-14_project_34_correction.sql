-- Migration: 2026-05-14 — Project 34 (2680 Bancroft Way) stage correction
-- Context: Fix-A incorrectly advanced project 34 to 'completed' based on a
--          co_issued event for B2024-00543. That permit is a subsidiary seismic
--          retrofit on the existing Bancroft Hotel, not completion of the new
--          79-unit residential development.
--
-- Corrections:
--   1. Mark event 2658 as misattributed (preserve for traceability)
--   2. Revert project stage from completed (6) to entitled (3)

BEGIN TRANSACTION;

-- Mark co_issued event 2658 as misattributed subsidiary permit
-- Using source_type='inferred' (allowed by CHECK constraint) with detailed summary
UPDATE project_events
SET summary = COALESCE(summary, '') || ' [MISATTRIBUTED SUBSIDIARY: B2024-00543 is seismic retrofit on existing Bancroft Hotel, not new development completion. Stage advancement reverted 2026-05-14.]',
    source_type = 'inferred'
WHERE id = 2658;

-- Revert project 34 stage from completed (6) to entitled (3)
UPDATE projects
SET current_stage_type_id = 3,
    updated_at = CURRENT_TIMESTAMP
WHERE id = 34;

COMMIT;
