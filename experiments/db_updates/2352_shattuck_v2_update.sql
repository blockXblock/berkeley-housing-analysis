-- 2352 Shattuck Ave (project_id 179) — populate construction history
-- from Accela reconnaissance on 2026-05-19
-- Source: notes/2026-05-19_accela_pipeline_recon.md
-- Backup: databases/backups/berkeley_housing_v2_pre_2352shattuck_20260519_165954.db

BEGIN TRANSACTION;

-- ============================================================================
-- STEP 1: Insert the 4 Accela permits verified tonight
-- ============================================================================

INSERT INTO permits (
  project_id, source_system, source_permit_id, permit_number,
  permit_type_id, permit_status_type_id,
  filed_date, issued_date, finaled_date,
  source_url, description, notes
) VALUES
  (179, 'accela', '18PLN-00000-00808', 'ZP2018-0135',
   2, 4,
   '2018-06-28', NULL, NULL,
   'https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Planning&TabName=Planning&capID1=18PLN&capID2=00000&capID3=00808&agencyCode=BERKELEY',
   'Logan Park entitlement: 8-story mixed-use, 237 dwelling units. Phase I (South) + Phase II (North).',
   'Verified via Claude in Chrome 2026-05-19. Staff Decision Approved 10/24/2019 by Sharon Gong. Case Closed 11/20/2019.'),

  (179, 'accela', NULL, 'DRCF2020-0003',
   4, 4,
   NULL, NULL, NULL,
   NULL,
   'Design Review Construction & Finish for Logan Park.',
   'Status verified from project description and prior reconnaissance. URL not captured this session.'),

  (179, 'accela', 'DUB19-00000-00KIJ', 'B2019-05574',
   5, 7,
   '2019-12-20', '2020-09-10', '2022-01-14',
   'https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB19&capID2=00000&capID3=00KIJ&agencyCode=BERKELEY',
   'Phase II of II - North Building. Building/Electrical/Mechanical/Plumbing permit. 8-story mixed use, 5 stories Type IIIA residential over 3 stories Type IA mixed use.',
   'Applicant: Bill Schrader (The Austin Group). Owner: CA AG LOGAN PARK PROPERTY OWNER. 553 inspections. Verified via CIC 2026-05-19.'),

  (179, 'accela', NULL, 'B2019-05575',
   5, 7,
   '2019-12-20', NULL, NULL,
   NULL,
   'Phase I of II - South Building (companion permit to B2019-05574).',
   'Status Finaled confirmed via Accela search results 2026-05-19. Detail page not individually visited. URL and date detail to be filled in by future pipeline run.');

-- ============================================================================
-- STEP 2: Insert project_events with provenance
-- ============================================================================

INSERT INTO project_events (
  project_id, event_type_id, event_date, event_date_precision,
  permit_id, summary, new_status_code,
  confidence_type_id, is_inferred, source_type, source_url,
  observed_by, observed_at
) VALUES (
  179, 2, '2018-06-28', 'exact',
  (SELECT id FROM permits WHERE permit_number = 'ZP2018-0135'),
  'ZP2018-0135 filed: Use Permit application for Logan Park 8-story mixed-use, 237 dwelling units.',
  'filed',
  1, 0, 'city_portal',
  'https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Planning&TabName=Planning&capID1=18PLN&capID2=00000&capID3=00808&agencyCode=BERKELEY',
  'jgage_cic_recon_2026-05-19', '2026-05-19'
);

INSERT INTO project_events (
  project_id, event_type_id, event_date, event_date_precision,
  permit_id, summary, new_status_code,
  confidence_type_id, is_inferred, source_type,
  observed_by, observed_at
) VALUES (
  179, 3, '2019-04-12', 'exact',
  (SELECT id FROM permits WHERE permit_number = 'ZP2018-0135'),
  'ZP2018-0135 Completeness Review: Application Complete (Sharon Gong).',
  'under_review',
  1, 0, 'city_portal',
  'jgage_cic_recon_2026-05-19', '2026-05-19'
);

INSERT INTO project_events (
  project_id, event_type_id, event_date, event_date_precision,
  permit_id, summary,
  confidence_type_id, is_inferred, source_type,
  observed_by, observed_at
) VALUES (
  179, 12, '2019-11-20', 'exact',
  (SELECT id FROM permits WHERE permit_number = 'ZP2018-0135'),
  'ZP2018-0135 Appeal phase: No Appeal Filed; Case Closed Approved (Karen Hernandez-Gonzalez).',
  1, 0, 'city_portal',
  'jgage_cic_recon_2026-05-19', '2026-05-19'
);

INSERT INTO project_events (
  project_id, event_type_id, event_date, event_date_precision,
  permit_id, summary, new_status_code,
  confidence_type_id, is_inferred, source_type, source_url,
  observed_by, observed_at
) VALUES (
  179, 2, '2019-12-20', 'exact',
  (SELECT id FROM permits WHERE permit_number = 'B2019-05574'),
  'B2019-05574 filed: Building/Electrical/Mechanical/Plumbing permit for Phase II North Building. Companion B2019-05575 (Phase I South) filed same day.',
  'filed',
  1, 0, 'city_portal',
  'https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB19&capID2=00000&capID3=00KIJ&agencyCode=BERKELEY',
  'jgage_cic_recon_2026-05-19', '2026-05-19'
);

INSERT INTO project_events (
  project_id, event_type_id, event_date, event_date_precision,
  permit_id, summary, new_status_code,
  confidence_type_id, is_inferred, source_type, source_url,
  observed_by, observed_at
) VALUES (
  179, 14, '2020-09-10', 'exact',
  (SELECT id FROM permits WHERE permit_number = 'B2019-05574'),
  'B2019-05574 Issued by David Lopez. Construction permitted to begin on Phase II North Building.',
  'issued',
  1, 0, 'city_portal',
  'https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB19&capID2=00000&capID3=00KIJ&agencyCode=BERKELEY',
  'jgage_cic_recon_2026-05-19', '2026-05-19'
);

INSERT INTO project_events (
  project_id, event_type_id, event_date, event_date_precision,
  permit_id, summary, new_status_code, details,
  confidence_type_id, is_inferred, source_type, source_url,
  observed_by, observed_at
) VALUES (
  179, 23, '2022-01-14', 'exact',
  (SELECT id FROM permits WHERE permit_number = 'B2019-05574'),
  'B2019-05574 Finaled: construction complete and final inspection passed (MD). Building physically ready for occupancy.',
  'finaled',
  'Note: The Certificate of Occupancy workflow phase in Accela was never marked complete by staff. Finaled status from inspection workflow is treated as the build-complete signal. CofO was later formalized 2024-12-10 on separate permit B2024-05208.',
  1, 0, 'city_portal',
  'https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB19&capID2=00000&capID3=00KIJ&agencyCode=BERKELEY',
  'jgage_cic_recon_2026-05-19', '2026-05-19'
);

-- ============================================================================
-- STEP 3: Verify counts (will print before commit)
-- ============================================================================
SELECT 'permits added' as check_label, COUNT(*) as count FROM permits WHERE project_id = 179;
SELECT 'project_events total' as check_label, COUNT(*) as count FROM project_events WHERE project_id = 179;

COMMIT;
