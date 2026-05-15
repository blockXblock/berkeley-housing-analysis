-- Migration: 2026-05-14 — Anna Head Student Housing bed count
-- Context: Project 171 (2400 Bowditch St) is UC Berkeley's Channing-Bowditch
--          Student Housing on the Anna Head School site. 750 units / ~1,500 beds.
--          Initial migration set tenure_type_id=8 (unknown) and beds_per_unit=NULL.
--          This update corrects to tenure=dormitory and beds_per_unit=2.

BEGIN TRANSACTION;

-- Update unit_program row for project 171 (Anna Head Student Housing)
-- project_version_id=168 is the current version for project 171
UPDATE unit_program
SET tenure_type_id = 5,  -- dormitory
    beds_per_unit = 2,   -- 750 units × 2 = 1,500 beds
    notes = 'UC Berkeley student housing. 750 units (~1,500 beds). Dorm-style configuration (tenure=dormitory). bedroom_count=1 retained from initial migration; not a traditional 1BR apartment. Updated 2026-05-14.'
WHERE id = 168;

COMMIT;
