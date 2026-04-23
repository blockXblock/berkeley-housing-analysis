# Migration Map: v1 (Flat) → v2 (Normalized)

**Generated:** 2026-04-22
**Source DB:** `databases/berkeley_housing_analysis.db`
**Target Schema:** `schema/core.sql`

---

## Open Questions Resolved

### Q1: Unit program NOT NULL on bedroom_count
**Answer:** Legacy data has NO bedroom breakdown for most projects. Only 22/174 projects mention bedrooms in descriptions.
**Decision:** Use placeholder convention: insert ONE `unit_program` row per project with `bedroom_count = 1` and `notes = 'bedroom distribution unknown; placed as 1BR for schema compliance'`. This preserves total unit counts while flagging data quality gap.

### Q2: APN data in legacy table
**Answer:** 154/174 projects (88%) have APN populated. 20 projects missing APN.
**Decision:** Create parcel rows only for projects with APN. `project_parcels` will be sparse for 20 projects.

### Q3: Documents in legacy
**Answer:** 1,423 rows in `project_documents` but **0 have URLs**. 42 projects have document metadata (title, filename, type) but no actual URLs.
**Decision:** Migrate document metadata to `documents` table. Set `url_status = 'unknown'`, `source_url = NULL`. Document mirroring (Phase 6) will populate URLs later.

### Q4: sfyimby_projects table
**Answer:** 249 rows, 155 matched to projects. Contains supplemental data (project names, raw addresses).
**Decision:** Keep as side-table, do NOT migrate into normalized schema. Can be used for data enrichment later.

---

## Legacy Schema Inventory

### projects table (174 rows, 54 columns)

| Legacy Column | v2 Table | v2 Column | Transform | Notes |
|---------------|----------|-----------|-----------|-------|
| id | projects | id | direct | PK preserved |
| address_display | projects | canonical_address | direct | |
| address_display | projects | normalized_address | UPPER + strip | for dedupe |
| latitude | projects | latitude | direct | 165/174 populated |
| longitude | projects | longitude | direct | 165/174 populated |
| apn | parcels | apn | direct | 154/174 populated |
| status | projects | current_stage_type_id | map to vocabulary | see mapping below |
| pipeline_stage | projects | current_stage_type_id | map to vocabulary | preferred over status |
| units | project_versions | total_units | direct | |
| vli_units | unit_program_affordability | unit_count | split | income_category = 'VLI' |
| height_stories | project_versions | height_stories | direct | |
| height_feet | project_versions | height_feet | direct | |
| developer | organizations + project_participants | | normalize + link | role = developer_of_record |
| architect | organizations + project_participants | | normalize + link | role = architect_design |
| owner | organizations + project_participants | | normalize + link | role = owner_current |
| filed | project_events | event_date | direct | event_type = application_submitted |
| complete | project_events | event_date | direct | event_type = application_complete |
| entitled | project_events | event_date | direct | event_type = entitlement_approved |
| bp_issued | project_events | event_date | direct | event_type = building_permit_issued |
| co_date | project_events | event_date | direct | event_type = co_issued |
| construction_start | project_events | event_date | direct | event_type = construction_start_observed |
| permits | permits | permit_number | parse CSV | split and create permit rows |
| density_bonus | project_versions | (flag) | | use vocabulary for restriction_type |
| sb35_flag | permits | permit_type_id | | if true, create sb35_streamlined permit |
| sb330_flag | (custom field TBD) | | | no direct mapping |
| ab2011_flag | (custom field TBD) | | | no direct mapping |
| is_uc_project | (custom field TBD) | | | keep as project attribute |
| description | project_versions | (notes?) | | preserve in notes |
| tenure | unit_program | tenure_type_id | map | 'Owner'→ownership, 'Renter'→rental |
| total_fees | (derived) | | | sum from permit_fees |
| field_survey_date | project_events | event_date | | event_type = observation |
| field_survey_notes | project_events | details | | |
| demolition_permit_date | project_events | event_date | | event_type = demo_permit_issued |
| construction_substage | project_events | | | create substage observation event |

### Columns NOT migrated (dropped or derived)

| Legacy Column | Reason |
|---------------|--------|
| processing_days | derived from events |
| accela_status | superseded by permit status |
| accela_status_date | migrate to event |
| estimated_completion | low confidence |
| app_packet_mb | metadata, low value |
| construction_method | sparse, low value |
| inspection_count | derived from events |
| first/last/final_inspection_date | migrate to events |
| density_bonus_pct | sparse |
| construction_data_reliability | metadata |
| is_stalled | derived from stage |
| fee_count | derived |
| unit_category | derived |
| project_size | derived |
| created_at | preserve |
| updated_at | preserve |
| year | derived from filed |
| total_units | same as units |
| bp_filed_date | migrate to event |

---

## permit_events table (2,306 rows)

| Legacy Column | v2 Table | v2 Column | Transform |
|---------------|----------|-----------|-----------|
| id | project_events | id | direct |
| project_id | project_events | project_id | direct |
| address | (dropped) | | redundant with project |
| permit_number | project_events | permit_id | lookup from permits table |
| stage | project_events | | parse for event_type |
| action | project_events | event_type_id | map to vocabulary |
| event_date | project_events | event_date | direct |
| assigned_to | project_events | observed_by | direct |
| marked_by | project_events | observed_by | direct |
| comment | project_events | details | direct |
| stage_status | project_events | new_status_code | direct |
| source | project_events | source_type | map 'accela'→'city_portal' |

---

## project_permits table (114 rows)

| Legacy Column | v2 Table | v2 Column | Transform |
|---------------|----------|-----------|-----------|
| id | permits | id | direct |
| project_id | permits | project_id | direct |
| permit_number | permits | permit_number | direct |
| permit_type | permits | permit_type_id | map to vocabulary |
| permit_module | permits | source_system | 'Planning'/'Building' |
| filed_date | permits | filed_date | direct |
| status | permits | permit_status_type_id | map to vocabulary |
| status_date | (event) | | create status_update event |

---

## building_permits table (94 rows)

| Legacy Column | v2 Table | v2 Column | Transform |
|---------------|----------|-----------|-----------|
| id | permits | id | generate new |
| project_id | permits | project_id | direct |
| permit_number | permits | permit_number | direct, dedupe with project_permits |
| permit_type | permits | permit_type_id | map: 'Building Permit' |
| status | permits | permit_status_type_id | map |
| filed_date | permits | filed_date | direct |
| finaled_date | permits | finaled_date | direct |
| job_value | permits | valuation | parse to number |
| description | permits | description | direct |

---

## project_documents table (1,423 rows, 0 with URLs)

| Legacy Column | v2 Table | v2 Column | Transform |
|---------------|----------|-----------|-----------|
| id | documents | id | direct |
| project_id | documents | project_id | direct |
| title | documents | title | direct |
| filename | documents | (notes) | |
| url | documents | source_url | all NULL |
| document_type | documents | document_type_id | map to vocabulary |
| source | documents | source_system | direct |
| date_added | documents | created_at | direct |
| notes | documents | notes | direct |

---

## permit_fees table (441 rows)

This table structure is NOT in the v2 schema. Options:
1. Add `permit_fees` to v2 schema (extension)
2. Store as aggregated data
3. Link fees to permits or events

**Decision:** Keep `permit_fees` as-is in v2. Add to core.sql as extension table.

---

## Status → Stage Type Mapping

| Legacy status | v2 stage_type code |
|--------------|-------------------|
| Pre-Application | pre_application |
| In Review | in_review |
| Under Review | in_review |
| ZAB Review | in_review |
| Pending | in_review |
| Corrections Pending Applicant | in_review |
| Incomplete Pending Applicant | in_review |
| Resubmittal Pending Review | in_review |
| Resubmittal Pending Staff | in_review |
| Amendment Pending | in_review |
| Pending Final Action | in_review |
| On Hold | stalled |
| Approved | entitled |
| Entitled | entitled |
| Developer Selected | entitled |
| Building Permits Filed | permitted |
| Demolition Permits Filed | permitted |
| Demolition Underway | under_construction |
| Under Construction | under_construction |
| Completed | completed |
| Stalled | stalled |
| Withdrawn | withdrawn |
| Unknown | (NULL) |

---

## Permit Action → Event Type Mapping

| Legacy action | v2 event_type code |
|--------------|-------------------|
| Application Submitted | application_submitted |
| Application Complete | application_complete |
| **Application Complete** | application_complete |
| Assigned | review_started |
| Approved | entitlement_approved |
| **Approved** | entitlement_approved |
| Approved w/Conditions | entitlement_approved |
| Approved/Case Closed | entitlement_approved |
| **Pending Final Action** | hearing_held |
| **Corrections - Pending Applicant** | comments_issued |
| **Incomplete Pending Applicant** | comments_issued |
| **Resubmittal - Pending Staff Review** | revision_submitted |
| Appeal to ZAB | appeal_filed |
| Appeal to City Council | appeal_filed |
| **No Appeal** | appeal_resolved |
| **Categorically Exempt** | (CEQA event, not modeled) |
| Auto-Closed | project_withdrawn |

---

## Organization Normalization

| Legacy name | Normalized name | Notes |
|------------|-----------------|-------|
| UC Berkeley Capital Strategies | uc_berkeley_capital_strategies | |
| NX Ventures | nx_ventures | |
| Panoramic Interests | panoramic_interests | |
| Core Spaces | core_spaces | |
| 4Terra Investments | 4terra_investments | |
| CHDC | chdc | Community Housing Dev Corp |
| RCD | rcd | Resources for Community Dev |

---

## Migration Insert Order

1. `cities` (Berkeley seed)
2. All vocabulary tables (from vocabularies_berkeley.sql)
3. `parcels` (from projects.apn)
4. `organizations` (dedupe from projects.developer, architect, owner)
5. `projects` (with current_version_id = NULL)
6. `permits` (from project_permits + building_permits, deduped)
7. `project_parcels` (junction)
8. `project_versions` (one per project, source_event_id = NULL, is_current = 1)
9. `unit_program` (one row per project, bedroom_count = 1 placeholder)
10. `unit_program_affordability` (VLI split from units)
11. `project_events` (from permit_events + date columns)
12. `documents` (from project_documents)
13. `project_participants` (link orgs to projects with roles)
14. `project_geometries` (from lat/lon as centroid_point)
15. **Second pass:** UPDATE projects SET current_version_id
16. **Second pass:** UPDATE project_versions SET source_event_id

---

## Validation Queries

After migration, verify:
- `SELECT COUNT(*) FROM projects` = 174
- `SELECT SUM(total_units) FROM project_versions WHERE is_current = 1` = 12717
- `PRAGMA foreign_key_check` = empty
- No duplicate organizations by normalized_name
- Every project has exactly one current version

---

*Migration map generated 2026-04-22*
