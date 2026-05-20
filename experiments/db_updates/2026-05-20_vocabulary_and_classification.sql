-- Vocabulary additions + 2680 Bancroft misattribution fix + 2352 Shattuck Finaled cleanup
-- Date: 2026-05-20 (rev2: respects project_events.project_id NOT NULL constraint)

BEGIN TRANSACTION;

-- STEP 1: Add 5 new event types to vocabulary_event_types

INSERT INTO vocabulary_event_types (code, label, description, implies_stage_type_id)
VALUES
  ('permit_finaled',
   'Permit Finaled',
   'A specific building permit reached Finaled status (final inspection workflow complete). Does not imply project-level completion because projects may have multiple primary permits. Project completion requires deliberate stage event, ideally informed by inspection data.',
   NULL),

  ('permit_classified_primary',
   'Permit Classified as Primary',
   'Classification metadata: this permit is part of the tracked project lifecycle. Used to distinguish project permits from unrelated work at the same parcel.',
   NULL),

  ('permit_classified_subsidiary',
   'Permit Classified as Subsidiary',
   'Classification metadata: this permit is not part of the tracked project lifecycle. May be subsidiary work, existing-building maintenance, or unrelated activity at the same parcel.',
   NULL),

  ('first_inspection_observed',
   'First Inspection Observed',
   'The first inspection event recorded on a primary permit. Evidence that construction has physically begun. More reliable than construction_start_observed.',
   5),

  ('final_inspection_passed',
   'Final Inspection Passed',
   'The final inspection that completed a permits inspection workflow. Underlying evidence for the permit_finaled status. Does not imply project completion because projects may have multiple primary permits.',
   NULL);

-- STEP 2: Fix event 2658 (2680 Bancroft misattribution)
-- Change event_type from co_issued to permit_finaled, keep project association
-- Classification system (Step 3) marks the permit as subsidiary so event is not interpreted as project completion

UPDATE project_events
SET
  event_type_id = (SELECT id FROM vocabulary_event_types WHERE code='permit_finaled'),
  summary = 'B2024-00543 Finaled: seismic retrofit work completed on existing Bancroft Hotel structure. This is not new-development completion - see classification event for permit 149.',
  details = 'Originally event_type_id=17 (co_issued); changed 2026-05-20 to permit_finaled. The Finaled status on B2024-00543 is a real fact about the permit (seismic retrofit completed), but B2024-00543 is subsidiary work, not new-development completion. The classification event added 2026-05-20 marks permit 149 as subsidiary so this event does not imply project 34 lifecycle completion. The new permit_finaled event type has implies_stage_type_id=NULL precisely to prevent automatic stage advancement.',
  observed_by = 'jgage_recon_2026-05-20',
  observed_at = '2026-05-20'
WHERE id = 2658;

-- STEP 3: Add classification event marking permit 149 as subsidiary

INSERT INTO project_events (
  project_id, event_type_id, event_date, event_date_precision,
  permit_id, summary, details,
  confidence_type_id, is_inferred, source_type,
  observed_by, observed_at
) VALUES (
  34,
  (SELECT id FROM vocabulary_event_types WHERE code='permit_classified_subsidiary'),
  '2026-05-20', 'exact',
  149,
  'B2024-00543 classified as subsidiary to project 34 (Bancroft Hotel new residential conversion).',
  'Permit is for seismic retrofit of the existing Bancroft Hotel structure, not for the new residential development. First classification under the Option C event-based classification system, 2026-05-20.',
  1, 0, 'observation',
  'jgage_recon_2026-05-20', '2026-05-20'
);

-- STEP 4: Retroactively fix 2352 Shattuck Finaled event

UPDATE project_events
SET
  event_type_id = (SELECT id FROM vocabulary_event_types WHERE code='permit_finaled'),
  details = COALESCE(details, '') || ' Event type updated 2026-05-20 from status_update to permit_finaled with introduction of dedicated vocabulary entry. Underlying data unchanged.',
  observed_by = 'jgage_recon_2026-05-20',
  observed_at = '2026-05-20'
WHERE id = 2793;

-- STEP 5: Verify counts before commit

SELECT 'check_1_new_vocab_count' as check_name, COUNT(*) as count
  FROM vocabulary_event_types
  WHERE code IN ('permit_finaled', 'permit_classified_primary', 'permit_classified_subsidiary',
                 'first_inspection_observed', 'final_inspection_passed');

SELECT 'check_2_event_2658_now_permit_finaled' as check_name,
  CASE
    WHEN event_type_id = (SELECT id FROM vocabulary_event_types WHERE code='permit_finaled')
    THEN 'yes'
    ELSE 'NO - rollback'
  END as result
  FROM project_events WHERE id = 2658;

SELECT 'check_3_classification_exists' as check_name, COUNT(*) as count
  FROM project_events
  WHERE permit_id = 149
    AND event_type_id = (SELECT id FROM vocabulary_event_types WHERE code='permit_classified_subsidiary');

SELECT 'check_4_event_2793_updated' as check_name,
  CASE
    WHEN event_type_id = (SELECT id FROM vocabulary_event_types WHERE code='permit_finaled')
    THEN 'yes'
    ELSE 'NO - rollback'
  END as result
  FROM project_events WHERE id = 2793;

COMMIT;
