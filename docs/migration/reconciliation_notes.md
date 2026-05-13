# Migration Reconciliation Notes

**Migration Date:** 2026-05-07T16:38:14.449895

---

## 1. Unit Count Delta (+1)

**Source:** One project (ID in audit log) had `-1` units in v1.

**Resolution:** Converted to `0` during migration.

**Rationale:** The v2 schema enforces `total_units >= 0` as a CHECK constraint. A negative unit count is semantically invalid. The most conservative fix is to set it to 0 (unknown/not specified) rather than guess the intended value.

**Audit Trail:** This fix is logged in the reconciliation_notes and the _audit_low_confidence table.

## 2. Orphan Documents (17 Skipped)

**Source:** 17 documents in v1 `project_documents` table had `project_id` values that do not exist in the v1 `projects` table.

**Resolution:** Quarantined to `_quarantine_documents` table.

**Rationale:** These documents cannot be properly migrated without a valid project association. Rather than dropping them silently, they are preserved in a quarantine table for manual review and potential reattachment.

**Next Steps:**
- Review quarantined documents to identify correct project associations
- For documents that genuinely have no parent project, decide whether to:
  - Delete permanently
  - Create a placeholder 'orphan documents' project
  - Archive to a separate documents table without project FK

## 3. Extra Permits (+4)

**Source:** v2 permits come from two v1 tables:
- `project_permits`: Planning permits
- `building_permits`: Building/construction permits

**Resolution:** Both sources are combined, with deduplication by permit_number.

**Rationale:** The building_permits table contains permits not present in project_permits (typically issued later in the project lifecycle). Combining both sources gives a more complete permit history.

## 4. Extra Events (+299)

**Source:** v2 events come from two sources:
1. **Date columns on projects table:** filed, complete, entitled, bp_issued, co_date, construction_start, demolition_permit_date, field_survey_date
2. **permit_events table:** Legacy event log

**Resolution:** Both sources are migrated as project_events.

**Rationale:** The date columns contain significant milestone events that were not always captured in permit_events. By creating events from both sources, we get a more complete timeline. Duplicates are acceptable because they may have different details or precision.

---

*Generated 2026-05-07T16:38:14.449895*
