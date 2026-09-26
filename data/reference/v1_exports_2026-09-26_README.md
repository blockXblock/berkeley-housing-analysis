# v1 exports (2026-09-26)

Rows that existed ONLY in the v1 database (`berkeley_housing_analysis.db`) when it was archived to
`databases/archive/`. Exported read-only, unchanged, so they outlive the file.

- `v1_sfyimby_projects_export_2026-09-26.csv`: 249 rows from the SF YIMBY Berkeley tracker, as
  scraped into v1 (165 matched to a v1 project via `matched_project_id`; those are v1 project ids, not
  verified to equal v2 ids). A SECONDARY source: useful for developer and architect names the city
  record lacks, never a primary count.
- `v1_unmigrated_building_permit_stubs_2026-09-26.csv`: 50 building permits (all B2025-) present in
  v1 but not in v2. No project, no description, no dates; only 9 appear in the raw CPRA files.
  Kept as what an old Accela scrape saw, not as evidence of housing.

Everything else in v1 was verified present in v2 on 2026-09-26 (see
`docs/audit/2026-09-26_machinery_and_schema_audit.md` and the session record in PROGRESS.md).
