-- ============================================================================
-- Berkeley vocabulary seeds
-- ============================================================================
-- Seed values for every vocabulary table, tuned for Berkeley's permit system.
--
-- CONVENTIONS:
--   - "code" is stable machine identifier (snake_case, never changed once used)
--   - "label" is human-readable display text (can be edited freely)
--   - "description" is optional clarifying text
--
-- REVIEW TAGS:
--   Lines marked "-- REVIEW:" are values inferred from general domain knowledge
--   or from the project's user memory, NOT verified against Berkeley's actual
--   Accela/Clariti system. Before committing, cross-check against:
--     - Berkeley's Accela permit type dropdowns
--     - Actual permit records in the current berkeley_housing_analysis.db
--     - HCD APR form field definitions
--     - City of Berkeley Planning Dept. documentation
--
-- This file is idempotent: uses INSERT OR IGNORE so it can be re-run safely.
-- To change a label or description, UPDATE the row directly; to deprecate a
-- code, add a "deprecated_YYYYMMDD_" prefix rather than deleting (preserves FK).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Cities
-- ----------------------------------------------------------------------------

INSERT OR IGNORE INTO cities (slug, name, state, country) VALUES
  ('berkeley', 'City of Berkeley', 'CA', 'US');

-- ----------------------------------------------------------------------------
-- Project version types
-- ----------------------------------------------------------------------------

INSERT OR IGNORE INTO vocabulary_project_version_types (code, label, description) VALUES
  ('proposal',            'Initial Proposal',           'First application submission; pre-entitlement program.'),
  ('revised_proposal',    'Revised Proposal',           'Program revision during planning review, pre-entitlement.'),
  ('entitled',            'Entitled',                   'Program as approved by Planning Commission or staff.'),
  ('building_permit_set', 'Building Permit Set',        'Program reflected in issued building permits.'),
  ('as_built',            'As-Built',                   'Program as constructed, per final inspection / CO.');

-- ----------------------------------------------------------------------------
-- Stage types (project lifecycle macro-stages)
-- ----------------------------------------------------------------------------
-- REVIEW: Stage names are derived from general planning vocabulary. Cross-check
-- against Berkeley's actual status strings in the legacy flat table before
-- relying on these codes for status transitions.

INSERT OR IGNORE INTO vocabulary_stage_types (code, label, description) VALUES
  ('pre_application',     'Pre-Application',            'Early/informal discussions, no formal filing yet.'),
  ('in_review',           'In Review',                  'Application filed; under planning or staff review.'),
  ('entitled',            'Entitled',                   'Planning approval granted; may or may not have building permit.'),
  ('permitted',           'Permitted',                  'Building permit issued; construction not yet observed.'),
  ('under_construction',  'Under Construction',         'Active construction observed or reported.'),
  ('completed',           'Completed',                  'Certificate of Occupancy issued or equivalent.'),
  ('stalled',             'Stalled',                    'No visible progress; permit lapse risk or financing issue.'),
  ('withdrawn',           'Withdrawn',                  'Application withdrawn by applicant or denied.');

-- ----------------------------------------------------------------------------
-- Substage types (more granular than stages; optional)
-- ----------------------------------------------------------------------------
-- REVIEW: Substages are useful for construction sequencing (excavation, frame,
-- topout, interior). Populate incrementally as observations warrant.

INSERT OR IGNORE INTO vocabulary_substage_types (code, label, description, parent_stage_type_id) VALUES
  ('demo_complete',       'Demolition Complete',        'Site cleared; foundation work may begin.',
    (SELECT id FROM vocabulary_stage_types WHERE code = 'under_construction')),
  ('foundation',          'Foundation',                 'Foundation pour and basement/podium work.',
    (SELECT id FROM vocabulary_stage_types WHERE code = 'under_construction')),
  ('framing',             'Framing',                    'Structural frame construction.',
    (SELECT id FROM vocabulary_stage_types WHERE code = 'under_construction')),
  ('topped_out',          'Topped Out',                 'Structural frame reached full height.',
    (SELECT id FROM vocabulary_stage_types WHERE code = 'under_construction')),
  ('facade',              'Facade',                     'Exterior skin and envelope installation.',
    (SELECT id FROM vocabulary_stage_types WHERE code = 'under_construction')),
  ('interior',            'Interior',                   'Interior finishes and MEP rough-in.',
    (SELECT id FROM vocabulary_stage_types WHERE code = 'under_construction'));

-- ----------------------------------------------------------------------------
-- Tenure types
-- ----------------------------------------------------------------------------

INSERT OR IGNORE INTO vocabulary_tenure_types (code, label, description) VALUES
  ('rental',              'Rental',                     'Rental tenure.'),
  ('ownership',           'Ownership',                  'For-sale ownership tenure (condo, TIC, SFR).'),
  ('cooperative',         'Cooperative',                'Housing cooperative membership.'),
  ('student',             'Student Housing',            'University or affiliated student housing.'),
  ('dormitory',           'Dormitory',                  'Dorm-style student housing.'),
  ('sro',                 'Single Room Occupancy',      'SRO units.'),
  ('permanent_supportive','Permanent Supportive',       'PSH for formerly homeless with services.'),
  ('unknown',             'Unknown',                    'Tenure not yet determined from sources.');

-- ----------------------------------------------------------------------------
-- Special population types
-- ----------------------------------------------------------------------------
-- REVIEW: Categories below are from HCD APR form conventions. Verify against
-- current HCD Table A2 category list before using for APR output.

INSERT OR IGNORE INTO vocabulary_special_population_types (code, label, description) VALUES
  ('senior',              'Senior',                     'Age-restricted senior housing (typically 55+ or 62+).'),
  ('student',             'Student',                    'Student housing.'),
  ('homeless_formerly',   'Formerly Homeless',          'Units targeted to formerly homeless households.'),
  ('homeless_at_risk',    'At-Risk of Homelessness',    'Units targeted to households at risk of homelessness.'),
  ('disabled',            'Persons with Disabilities',  'Units with accessibility or disability-targeted programs.'),
  ('veteran',             'Veteran',                    'Veteran-targeted housing.'),
  ('farmworker',          'Farmworker',                 'Farmworker-targeted housing.'),
  ('mental_health',       'Mental Health Services',     'Housing integrated with mental health services.'),
  ('ada',                 'ADA-Compliant',              'Units meeting specific ADA / accessibility standards.');

-- ----------------------------------------------------------------------------
-- Income categories (AMI bands)
-- ----------------------------------------------------------------------------
-- Standard HCD / HUD income category definitions as of 2025. AMI percent bands
-- are stored separately on unit_program_affordability (ami_min, ami_max);
-- these codes are the authoritative categorical buckets.

INSERT OR IGNORE INTO vocabulary_income_categories (code, label, description) VALUES
  ('ELI',                 'Extremely Low Income',       '0-30% AMI.'),
  ('VLI',                 'Very Low Income',            '30-50% AMI.'),
  ('LI',                  'Low Income',                 '50-80% AMI.'),
  ('MOD',                 'Moderate Income',            '80-120% AMI.'),
  ('ABOVE_MOD',           'Above Moderate Income',      'Above 120% AMI (market rate).'),
  ('UNKNOWN',             'Unknown',                    'Income category not yet determined from sources.');

-- ----------------------------------------------------------------------------
-- Restriction types
-- ----------------------------------------------------------------------------

INSERT OR IGNORE INTO vocabulary_restriction_types (code, label, description) VALUES
  ('deed_restriction',    'Deed Restriction',           'Recorded deed restriction enforcing affordability.'),
  ('regulatory_agreement','Regulatory Agreement',       'Regulatory agreement with funder or jurisdiction.'),
  ('inclusionary',        'Inclusionary Condition',     'Inclusionary housing condition of approval.'),
  ('density_bonus',       'Density Bonus',              'Affordability provided under State density bonus law.'),
  ('tcac',                'TCAC / LIHTC',               'Tax Credit Allocation Committee regulatory agreement.'),
  ('hcd',                 'HCD Agreement',              'California HCD regulatory agreement.'),
  ('none',                'None',                       'No recorded affordability restriction.');

-- ----------------------------------------------------------------------------
-- Organization types
-- ----------------------------------------------------------------------------

INSERT OR IGNORE INTO vocabulary_organization_types (code, label, description) VALUES
  ('developer',           'Developer',                  'Real estate developer.'),
  ('owner',               'Property Owner',             'Owner of record.'),
  ('architect',           'Architect / Design Firm',    'Architectural or design firm.'),
  ('engineer',            'Engineer',                   'Structural, civil, MEP, or other engineering firm.'),
  ('general_contractor',  'General Contractor',         'GC or construction firm.'),
  ('property_manager',    'Property Manager',           'Property management firm.'),
  ('lender',              'Lender',                     'Construction or permanent financing provider.'),
  ('investor',            'Investor',                   'Equity investor or syndicator.'),
  ('nonprofit_sponsor',   'Nonprofit Sponsor',          'Nonprofit housing sponsor or CHDO.'),
  ('government',          'Government',                 'Government agency (city, county, state, federal).'),
  ('consultant',          'Consultant',                 'Planning, environmental, or other consultant.'),
  ('other',               'Other',                      'Other organization type.');

-- ----------------------------------------------------------------------------
-- Role types (linking organizations/people to projects)
-- ----------------------------------------------------------------------------

INSERT OR IGNORE INTO vocabulary_role_types (code, label, description) VALUES
  ('developer_of_record',    'Developer of Record',     'Entitled the project.'),
  ('co_developer',           'Co-Developer',            'Joint venture partner.'),
  ('owner_current',          'Current Owner',           'Current owner of record.'),
  ('owner_original',         'Original Owner',          'Original owner at entitlement (may have sold).'),
  ('architect_design',       'Design Architect',        'Design architect.'),
  ('architect_record',       'Architect of Record',     'Architect of record on permit drawings.'),
  ('engineer_structural',    'Structural Engineer',     'Structural engineer.'),
  ('engineer_civil',         'Civil Engineer',          'Civil engineer.'),
  ('general_contractor',     'General Contractor',      'Construction firm.'),
  ('property_manager',       'Property Manager',        'Manages rentals.'),
  ('asset_manager',          'Asset Manager',           'Manages property on behalf of investors.'),
  ('lender_construction',    'Construction Lender',     'Construction financing.'),
  ('lender_permanent',       'Permanent Lender',        'Permanent financing.'),
  ('investor_equity',        'Equity Investor',         'Equity investor.'),
  ('leasing_agent',          'Leasing Agent',           'Rental leasing agent.'),
  ('sales_agent',            'Sales Agent',             'Condo or unit sales agent.'),
  ('nonprofit_sponsor',      'Nonprofit Sponsor',       'Nonprofit sponsor on affordable project.'),
  ('applicant',              'Applicant',               'Applicant of record on planning filing.'),
  ('consultant_planning',    'Planning Consultant',     'Planning consultant.'),
  ('consultant_environmental','Environmental Consultant','CEQA or environmental consultant.'),
  ('staff_planner',          'Staff Planner',           'City staff planner assigned to project.');

-- ----------------------------------------------------------------------------
-- Permit types
-- ----------------------------------------------------------------------------
-- REVIEW: Berkeley Accela uses specific permit type codes (e.g. "ZP", "UP",
-- "AUP", "DR", "BLDG"). The codes below are common planning/building vocabulary;
-- verify exact Berkeley codes against the current flat table's permit_number
-- prefixes before finalizing the mapping.

INSERT OR IGNORE INTO vocabulary_permit_types (code, label, description) VALUES
  ('zoning_certificate',  'Zoning Certificate',         'Zoning compliance certificate.'),
  ('use_permit',          'Use Permit',                 'Use permit (UP) / conditional use.'),
  ('admin_use_permit',    'Administrative Use Permit',  'Administrative use permit (AUP).'),
  ('design_review',       'Design Review',              'Design review approval.'),
  ('building_permit',     'Building Permit',            'Building permit (BP / BLDG).'),
  ('demo_permit',         'Demolition Permit',          'Demolition permit.'),
  ('grading_permit',      'Grading Permit',             'Grading / excavation permit.'),
  ('mechanical_permit',   'Mechanical Permit',          'Mechanical trade permit.'),
  ('electrical_permit',   'Electrical Permit',          'Electrical trade permit.'),
  ('plumbing_permit',     'Plumbing Permit',            'Plumbing trade permit.'),
  ('encroachment',        'Encroachment Permit',        'Public right-of-way encroachment.'),
  ('sb35_streamlined',    'SB35 Streamlined Approval',  'State-streamlined approval under SB 35.'),
  ('sb9_ministerial',     'SB9 Ministerial',            'Ministerial approval under SB 9.'),
  ('density_bonus',       'Density Bonus Application',  'State density bonus application.'),
  ('other',               'Other',                      'Other permit type.');

-- ----------------------------------------------------------------------------
-- Permit status types
-- ----------------------------------------------------------------------------
-- REVIEW: Accela status strings are free-form per jurisdiction. Cross-check
-- Berkeley's actual Accela status vocabulary against this list before relying
-- on status_type_id joins.

INSERT OR IGNORE INTO vocabulary_permit_status_types (code, label, description) VALUES
  ('filed',               'Filed / Submitted',          'Application filed but not yet reviewed.'),
  ('incomplete',           'Incomplete',                'Filed but deemed incomplete, awaiting submittal.'),
  ('under_review',        'Under Review',               'Under active review.'),
  ('approved',            'Approved',                   'Approved; may not yet be issued.'),
  ('issued',              'Issued',                     'Permit issued.'),
  ('in_construction',     'In Construction',            'Construction active under permit.'),
  ('finaled',             'Finaled',                    'Permit finaled / closed out.'),
  ('expired',             'Expired',                    'Permit expired without final.'),
  ('withdrawn',           'Withdrawn',                  'Permit withdrawn by applicant.'),
  ('denied',              'Denied',                     'Permit denied.'),
  ('cancelled',           'Cancelled',                  'Permit cancelled.'),
  ('unknown',             'Unknown',                    'Status not yet determined.');

-- ----------------------------------------------------------------------------
-- Document types
-- ----------------------------------------------------------------------------

INSERT OR IGNORE INTO vocabulary_document_types (code, label, description) VALUES
  ('application',         'Application',                'Planning or building application.'),
  ('plan_set',            'Plan Set',                   'Architectural plan set.'),
  ('staff_report',        'Staff Report',               'Staff report to Planning Commission / ZAB.'),
  ('zab_packet',          'ZAB Packet',                 'Zoning Adjustments Board agenda packet.'),
  ('design_review_packet','Design Review Packet',       'Design Review Committee packet.'),
  ('agenda',              'Agenda',                     'Meeting agenda.'),
  ('minutes',             'Minutes',                    'Meeting minutes.'),
  ('mitigated_neg_dec',   'Mitigated Negative Declaration','CEQA Mitigated Negative Declaration.'),
  ('eir',                 'Environmental Impact Report','CEQA Environmental Impact Report.'),
  ('categorical_exemption','Categorical Exemption',     'CEQA Categorical Exemption determination.'),
  ('fee_schedule',        'Fee Schedule',               'Project fee schedule.'),
  ('fee_receipt',         'Fee Receipt',                'Fee payment receipt.'),
  ('inspection_report',   'Inspection Report',          'Inspection record.'),
  ('certificate_of_occupancy','Certificate of Occupancy','Final CO or TCO.'),
  ('conditions_of_approval','Conditions of Approval',   'Project COAs.'),
  ('affordable_housing_agreement','Affordable Housing Agreement','Affordability regulatory agreement.'),
  ('density_bonus_application','Density Bonus Application','SB1818 / State density bonus application.'),
  ('sb35_application',    'SB35 Application',           'SB 35 streamlined approval application.'),
  ('correspondence',      'Correspondence',             'Letter or email correspondence.'),
  ('public_comment',      'Public Comment',             'Public comment submission.'),
  ('rendering',           'Rendering',                  'Project rendering image.'),
  ('photograph',          'Photograph',                 'Site photograph.'),
  ('other',               'Other',                      'Other document type.');

-- ----------------------------------------------------------------------------
-- Event types (timeline)
-- ----------------------------------------------------------------------------
-- REVIEW: Event codes are a first-pass vocabulary. Adjust as you encounter
-- events in the legacy data that don't fit these categories. Adding new event
-- types later is cheap (INSERT OR IGNORE); renaming existing codes is not.
-- implies_stage_type_id is populated via a second UPDATE pass below so the
-- stage-type subquery resolves cleanly.

INSERT OR IGNORE INTO vocabulary_event_types (code, label, description) VALUES
  ('pre_app_meeting',     'Pre-Application Meeting',    'Informal pre-filing meeting with staff.'),
  ('application_submitted','Application Submitted',     'Formal application filed.'),
  ('application_complete','Application Deemed Complete','Application deemed complete by staff.'),
  ('review_started',      'Review Started',             'Active review began.'),
  ('comments_issued',     'Comments Issued',            'Staff comments issued to applicant.'),
  ('revision_submitted',  'Revision Submitted',         'Applicant resubmitted revised plans.'),
  ('hearing_scheduled',   'Hearing Scheduled',          'Public hearing scheduled.'),
  ('hearing_held',        'Hearing Held',               'Public hearing held.'),
  ('entitlement_approved','Entitlement Approved',       'Planning approval granted.'),
  ('entitlement_denied',  'Entitlement Denied',         'Planning approval denied.'),
  ('appeal_filed',        'Appeal Filed',               'Approval appealed.'),
  ('appeal_resolved',     'Appeal Resolved',            'Appeal decision issued.'),
  ('demo_permit_issued',  'Demolition Permit Issued',   'Demo permit issued.'),
  ('building_permit_issued','Building Permit Issued',   'Building permit issued.'),
  ('construction_start_observed','Construction Start Observed','Construction activity observed on site.'),
  ('topped_out',          'Topped Out',                 'Structural frame reached full height.'),
  ('co_issued',           'Certificate of Occupancy',   'CO or TCO issued.'),
  ('permit_expired',      'Permit Expired',             'Permit expired without being finaled.'),
  ('project_withdrawn',   'Project Withdrawn',          'Project withdrawn by applicant.'),
  ('ownership_changed',   'Ownership Changed',          'Ownership transferred.'),
  ('developer_changed',   'Developer Changed',          'Developer of record changed.'),
  ('program_revised',     'Program Revised',            'Unit count / program changed from prior version.'),
  ('status_update',       'Status Update',              'General status update (use sparingly).'),
  ('observation',         'Observation',                'Site observation by researcher.');

-- Link event types to their implied stages (second pass, now that stages exist)
UPDATE vocabulary_event_types
SET implies_stage_type_id = (SELECT id FROM vocabulary_stage_types WHERE code = 'pre_application')
WHERE code IN ('pre_app_meeting');

UPDATE vocabulary_event_types
SET implies_stage_type_id = (SELECT id FROM vocabulary_stage_types WHERE code = 'in_review')
WHERE code IN ('application_submitted','application_complete','review_started','comments_issued','revision_submitted','hearing_scheduled','hearing_held');

UPDATE vocabulary_event_types
SET implies_stage_type_id = (SELECT id FROM vocabulary_stage_types WHERE code = 'entitled')
WHERE code IN ('entitlement_approved');

UPDATE vocabulary_event_types
SET implies_stage_type_id = (SELECT id FROM vocabulary_stage_types WHERE code = 'permitted')
WHERE code IN ('building_permit_issued','demo_permit_issued');

UPDATE vocabulary_event_types
SET implies_stage_type_id = (SELECT id FROM vocabulary_stage_types WHERE code = 'under_construction')
WHERE code IN ('construction_start_observed','topped_out');

UPDATE vocabulary_event_types
SET implies_substage_type_id = (SELECT id FROM vocabulary_substage_types WHERE code = 'topped_out')
WHERE code = 'topped_out';

UPDATE vocabulary_event_types
SET implies_stage_type_id = (SELECT id FROM vocabulary_stage_types WHERE code = 'completed')
WHERE code IN ('co_issued');

UPDATE vocabulary_event_types
SET implies_stage_type_id = (SELECT id FROM vocabulary_stage_types WHERE code = 'withdrawn')
WHERE code IN ('project_withdrawn','entitlement_denied');

-- ----------------------------------------------------------------------------
-- Confidence types
-- ----------------------------------------------------------------------------

INSERT OR IGNORE INTO vocabulary_confidence_types (code, label, description) VALUES
  ('high',                'High',                       'Verified against primary source document or official record.'),
  ('medium',              'Medium',                     'Derived from secondary source or corroborated observation.'),
  ('low',                 'Low',                        'Inferred from circumstantial evidence; awaits verification.'),
  ('disputed',            'Disputed',                   'Conflicting sources; requires reconciliation.');

-- ----------------------------------------------------------------------------
-- Relationship types (parcels, external systems)
-- ----------------------------------------------------------------------------

INSERT OR IGNORE INTO vocabulary_relationship_types (code, label, description) VALUES
  ('primary_site',        'Primary Site',               'Primary parcel for the project.'),
  ('secondary_site',      'Secondary Site',             'Additional parcel in the project site.'),
  ('staging',             'Construction Staging',       'Parcel used for construction staging only.'),
  ('easement',            'Easement',                   'Parcel affected by project easement.'),
  ('related_parcel',      'Related Parcel',             'Parcel related to project by ownership or context.');

-- ----------------------------------------------------------------------------
-- Geometry types
-- ----------------------------------------------------------------------------

INSERT OR IGNORE INTO vocabulary_geometry_types (code, label, description) VALUES
  ('apn_parcel',          'APN Parcel',                 'Official assessor parcel polygon.'),
  ('apn_parcel_merged',   'APN Parcel (Merged)',        'Multi-parcel assemblage.'),
  ('apn_parcel_subdivided','APN Parcel (Subdivided)',   'Post-subdivision child parcel.'),
  ('building_footprint',  'Building Footprint',         'Building footprint; may be hand-edited and street-aligned.'),
  ('building_3d',         'Building 3D Extrusion',      'Footprint with height for 3D visualization.'),
  ('site_plan',           'Site Plan',                  'Full project site boundary.'),
  ('centroid_point',      'Centroid Point',             'Project centroid as Point geometry (for mapping).');

-- ----------------------------------------------------------------------------
-- Asset types (facade images, renderings, floor plans)
-- ----------------------------------------------------------------------------

INSERT OR IGNORE INTO vocabulary_asset_types (code, label, description) VALUES
  ('facade_north',        'North Facade',               'North-facing facade image.'),
  ('facade_south',        'South Facade',               'South-facing facade image.'),
  ('facade_east',         'East Facade',                'East-facing facade image.'),
  ('facade_west',         'West Facade',                'West-facing facade image.'),
  ('rendering_exterior',  'Exterior Rendering',         'Exterior rendering or visualization.'),
  ('rendering_interior',  'Interior Rendering',         'Interior rendering.'),
  ('site_photo',          'Site Photo',                 'Site photograph.'),
  ('construction_photo',  'Construction Photo',         'Photograph during construction.'),
  ('floor_plan',          'Floor Plan',                 'Floor plan drawing image.'),
  ('elevation_drawing',   'Elevation Drawing',          'Architectural elevation drawing image.'),
  ('section_drawing',     'Section Drawing',            'Architectural section drawing image.'),
  ('site_plan_image',     'Site Plan Image',            'Site plan drawing image.'),
  ('other',               'Other',                      'Other asset type.');

-- ----------------------------------------------------------------------------
-- Classification types (project tags/flags)
-- ----------------------------------------------------------------------------
-- These are normalized tags rather than custom columns, enabling provenance
-- tracking and easy extension without schema changes.

INSERT OR IGNORE INTO vocabulary_classification_types (code, label, description, is_boolean) VALUES
  ('sb35_eligible',     'SB35 Eligible',              'Project qualifies for SB 35 streamlined ministerial approval.', 1),
  ('sb35_approved',     'SB35 Approved',              'Project approved under SB 35 streamlined process.', 1),
  ('sb330_protected',   'SB330 Protected',            'Project subject to SB 330 Housing Crisis Act protections.', 1),
  ('ab2011_eligible',   'AB2011 Eligible',            'Project qualifies for AB 2011 streamlined approval.', 1),
  ('ab2011_approved',   'AB2011 Approved',            'Project approved under AB 2011.', 1),
  ('uc_project',        'UC Project',                 'University of California development project.', 1),
  ('density_bonus',     'Density Bonus',              'Project utilizes State density bonus law.', 1),
  ('100pct_affordable', '100% Affordable',            'Project is 100% affordable housing.', 1),
  ('historic_resource', 'Historic Resource',          'Site contains designated historic resource.', 1),
  ('ceqa_exempt',       'CEQA Exempt',                'Project is categorically exempt from CEQA.', 1);

-- End of vocabularies_berkeley.sql
