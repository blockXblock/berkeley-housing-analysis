# Project Status & Inactive Detection — Methodology

**Created:** 2026-05-13
**Last updated:** 2026-05-14 (subsidiary permit misattribution finding)
**Purpose:** Document how the Berkeley Housing Pipeline defines project status
categories and detects "inactive" projects (entitled or permitted but not progressing).

---

## Status categories

The Berkeley Housing Pipeline tracks 10 status categories for each project,
mapped from v2's normalized stage vocabulary plus two derived "inactive" states:

### Workflow stages (from v2 `vocabulary_stage_types`)

| Status | v2 stage_code | Definition |
|--------|---------------|------------|
| Pre-Application | `pre_application` | Applicant in pre-submittal conversation with Planning |
| Under Review | `in_review` | Application submitted, City review in progress |
| Entitled | `entitled` | Zoning entitlement approved, no building permit yet |
| Building Permits Filed | `permitted` | Building permit application filed |
| Under Construction | `under_construction` | Construction observed in progress |
| Completed | `completed` | Certificate of Occupancy issued |
| Stalled | `stalled` | Explicitly marked as stuck |
| Withdrawn | `withdrawn` | Application withdrawn by applicant |

### Derived inactive states

Two additional statuses are computed at query time from event history,
not stored in v2:

| Status | Definition |
|--------|------------|
| Entitled but Inactive | Stage = entitled, no building permit issued, latest entitlement > 36 months ago |
| Permitted but Inactive | Stage = permitted, no construction observed, latest building permit issued > 24 months ago |

---

## Empirical basis for thresholds

The "inactive" thresholds (36 months for entitlement, 24 months for permits)
were chosen based on observed Berkeley pipeline durations measured from
v2 event data:

### Filed → Application Complete

Sample size: 63 projects with both events
- Average: 115 days (~4 months)
- Range observed: 0 to 489 days

### Application Complete → Entitled

Sample size: 45 projects with both events
- Average: 279 days (~9 months)
- Range observed: 9 to 1,087 days

### Entitled → Building Permit Issued

Sample size: 22 projects (excluding corrupted dates and negative-duration outliers)
- Average: 791 days (~26 months)
- Typical range: 100-700 days (3-23 months)
- Outliers: 2,000+ days indicate genuinely stalled projects

**Threshold choice: 36 months for "Entitled but Inactive"**

This sits clearly beyond the typical 3-23 month range. Projects exceeding
36 months without a building permit application represent real outliers,
not "slow but normal" progressions.

### Building Permit → Certificate of Occupancy

Sample size: 36 projects with both events
- Average: 379 days (~12.5 months)
- Range observed: 4 to 2,893 days

This is the full bp_issued → co_issued duration. The bp_issued →
construction_start sub-segment is shorter but not directly measured because
many projects lack a construction_start_observed event.

**Threshold choice: 24 months for "Permitted but Inactive"**

A 24-month gap between permit issuance and observable construction activity
is unusual. This threshold is somewhat conservative; further analysis with
2018-2022 CPRA data (expected ~2026-05-20) may refine it.

---

## Detection logic for inactive states

In `scripts/export_explorer_data_v2.py`'s `get_projects()` function:

```python
# Compute cutoff dates at script run time
cutoff_24mo = today - timedelta(days=730)   # ~24 months
cutoff_36mo = today - timedelta(days=1095)  # ~36 months

# For each project:

# Permitted but Inactive: permit > 24 months old, no construction observed
if stage_code == 'permitted':
    has_construction = bool(construction_start or topped_out or co_date)
    if not has_construction and bp_issued and bp_issued < cutoff_24mo:
        status = 'Permitted but Inactive'

# Entitled but Inactive: entitlement > 36 months old, no building permit
if stage_code == 'entitled':
    if not bp_issued and entitled and entitled < cutoff_36mo:
        status = 'Entitled but Inactive'
```

Key properties:
- **Time-based and observable.** Only uses dates already in v2; no manual
  classification required.
- **No claim about cause.** "Inactive" describes observable state — no project,
  no permit, no construction — without claiming the project is abandoned,
  stalled by an external factor, or paused intentionally.
- **Reversible.** When a project takes action (files for permit, starts
  construction), its observable state changes and it drops out of the
  inactive bucket on the next script run.
- **Conservative.** Both thresholds are beyond the 75th percentile of
  observed Berkeley durations. False positives (projects flagged that are
  actually progressing normally) should be rare.

---

## Data quality work (2026-05-13)

In addition to defining status categories and inactive detection, this date
included systematic data quality work captured in
`scripts/migrations/2026-05-13_date_corrections.sql`. Four corrections were
applied to v2:

### Date corrections (3 verified projects)

Three projects had corrupted event dates from the v1→v2 migration:

| Project | Issue | Verified value via Chrome Claude / Accela |
|---------|-------|-------------------------------------------|
| 179 (2352 Shattuck) | Entitlement date stored as bare "2018" | 2019-10-24 (Staff Decision by Sharon Gong) |
| 140 (2136 San Pablo) | Application date = 2024-01-01 placeholder | 2021-03-18 (ZP2021-0046 filed) |
| 149 (2198 San Pablo) | Application date = 2024-01-01 placeholder | 2018-05-31 (ZP2018-0112 filed) |

Of 7 originally-flagged "corrupted" projects, only these 3 needed correction.
The other 4 (projects 34, 113, 126, 129) had valid "BP-before-entitlement"
event sequences representing amendments, preliminary permits, or
demolition-then-rebuild — not corruption.

### Fix A: algorithmic stage correction (38 projects)

The v1→v2 migration left 58 projects with `current_stage_type_id` that
disagreed with their event history. Fix A auto-advanced 38 of these where
events showed progress (e.g., CO issued but stage still "in_review"):

| Transition | Projects affected |
|------------|------------------:|
| in_review → completed | 18 |
| in_review → entitled | 9 |
| in_review → permitted | 5 |
| entitled → permitted | 4 |
| entitled → completed | 3 |
| under_construction → completed | 3 |
| Other forward moves | misc |

Preserved (not auto-modified):
- `stalled` and `withdrawn` stages (manual classifications)
- `pre_application` (manual classification, no automatic equivalent)
- 6 "regression" cases where current stage was MORE advanced than events
  justified — these were not auto-downgraded because they may represent real
  progress without recorded events. Flagged for individual investigation.

**Net effect on status distribution:**
- Under Review: 110 → 78
- Completed: 17 → 38 (more than doubled)
- Withdrawn: 1 → 8
- Permitted: 7 → 14

### Step C: placeholder date flagging (105 events)

The v1→v2 migration defaulted year-only dates to January 1 (e.g., a project
filed "sometime in 2024" became "2024-01-01"). These 105 events were not
re-dated (because correct dates are unknown without Accela lookup), but
were flagged so they're not treated as authoritative:

- `event_date_precision = 'year'`
- `source_type = 'migration_inferred'`

Year distribution:
- 2020: 1, 2021: 6, 2022: 7, 2023: 4, 2024: 52, 2025: 33, 2026: 2

### Step D: deduplication (138 documents, 447 events)

The v1→v2 migration imported from overlapping source files (e.g., both
`1598_UNIVERSITY.txt` and `ZP2022-0011_1598_UNIVERSITY_Ave.txt`) without
deduplication. Roughly 10% of documents and 22% of events were duplicates.

Dedup rules (conservative — preserved legitimately distinct entries):
- **Documents:** DELETE where (project_id, title, published_date) matched —
  kept lowest id per group
- **Events:** DELETE where (project_id, event_date, event_type_id, summary,
  observed_by) matched — kept lowest id per group

Example: Project 152 (1598 University) had 72 documents (36 unique × 2 from
source-file duplication). Now correctly shows 36.

Same date events with different observers, different summaries, or different
event types were preserved as distinct entries — only exact matches were
removed.

Final v2 state after Step D: 181 projects, 2,340 events, 1,275 documents.

### Subsidiary permit misattribution (discovered 2026-05-14, project 34)

Investigation of project 34 (2680 Bancroft Way) revealed a systematic
data quality issue not captured by Fix A: **CO events on subsidiary
trade permits are being attributed to the main development project**,
incorrectly advancing its stage to "completed".

Project 34 has two permits:
- ZP2024-0029 — main entitlement (approved 2025-06-13)
- B2024-00543 — voluntary seismic retrofit on the existing Bancroft
  Hotel structure (finaled 2025-01-15)

The B2024-00543 permit finalization generated a `co_issued` event in
v2. Fix A interpreted this as completion of the proposed 79-unit
development. In fact, no main building permit has been filed yet; the
project is in early pre-construction.

**Manual correction applied 2026-05-14:**
- Project 34 stage reverted: completed → entitled
- The co_issued event for B2024-00543 has been retained but flagged in
  its `summary` field with a note: "[SUBSIDIARY: seismic retrofit on
  existing Bancroft Hotel, not new development completion]"
- Migration: `scripts/migrations/2026-05-14_project_34_correction.sql`

**Systemic implication:**

v2's schema does not distinguish primary development permits from
subsidiary trade permits (seismic retrofits, electrical, plumbing,
mechanical, voluntary renovations on existing structures). All
building permits share the same `permit_type` and produce comparable
events. Fix A's stage-advancement logic cannot tell the difference.

This means the "completed in 2025" count (originally 23 projects with
CO events) is likely **overstated**. Project 34 was one such error;
others probably exist in the same list. Each requires individual
Accela verification to determine whether the CO event corresponds to
the main development or to a subsidiary permit.

**22 projects from the 2025 completion list still need verification.**
They are listed for future audit in the project tracker; verification
will use Chrome Claude / Accela case lookup per project.

**Recommended schema enhancement (deferred until pattern confirmed
across multiple projects):**

Add a `permit_role` column to the `permits` table distinguishing:
- `primary_development` — the main building permit for the new structure
- `subsidiary_trade` — electrical, plumbing, mechanical, seismic, etc.
- `existing_structure` — work on a pre-existing building on the parcel

Fix A's logic would then advance stage only when CO events are tied to
permits with `permit_role = 'primary_development'`. This is a real
structural fix but is premature absent evidence the pattern is
widespread. The 22-project audit will determine whether the schema
enhancement is justified.

**Honest assessment:**

Fix A produced a real improvement (38 projects had stale stages
corrected), but applied uniformly to all CO events without permit-role
distinction. Project 34's misclassification is the first clear example
of a systematic gap. Until the audit completes and the schema
enhancement decision is made, the "Completed" status on the public
Explorer should be treated as approximate, not authoritative.

---

## Data limitations

### What can be reliably detected

- Projects with verified entitlement events but no subsequent permit events
- Projects with verified permit events but no subsequent construction events

### What cannot be reliably detected

- **Projects with informal "next steps" not captured in v2** (e.g., owner
  in negotiation with developer, financing in progress) — these would still
  appear "inactive" though the project is moving
- **Projects where v2 is missing events** due to CPRA scope gaps (some
  Berkeley building permits weren't in the 2023-2025 CPRA delivery; see
  `docs/methodology/cpra_lessons_learned_2026-05-11.md`)
- **Projects with placeholder dates** — 105 events still have year-only
  precision (date set to Jan 1 of correct year, but actual month/day unknown).
  These are flagged with `event_date_precision='year'` but exact dates
  require Accela verification.

### Sample size caveat

These thresholds were chosen from observed durations in 22-63 projects per
transition. As v2 ingests additional CPRA data (notably the 2018-2022 request,
expected ~2026-05-20), distributions may shift. Thresholds should be
re-validated periodically against the growing dataset.

---

## Future work

1. **Verify the 105 placeholder dates via Chrome Claude / Accela.** Currently
   flagged with `event_date_precision='year'` but actual filing/decision
   dates unknown for the month/day portion.

2. **Investigate the 6 "regression" stage cases** where v2's current_stage is
   more advanced than events justify. May indicate missing events that need
   to be backfilled from Accela.

3. **Audit 22 remaining "2025 completion" projects** for subsidiary permit
   misattribution (see "Subsidiary permit misattribution" section above).
   Each project where v2 records a 2025 co_issued event needs verification
   that the event corresponds to the primary development permit, not a
   subsidiary trade permit. Project 34 (2680 Bancroft) was the first
   confirmed case; others probably exist. If 5+ misattributions are found,
   implement the `permit_role` schema enhancement.

4. **Re-evaluate thresholds after 2018-2022 CPRA arrival.** Larger sample size
   may justify tightening or loosening the 24/36 month thresholds.

5. **Add 90th and 95th percentile reporting to the methodology.** Currently
   we have averages and ranges; explicit percentiles would inform thresholds
   more precisely.

6. **Differentiate "inactive" sub-types.** Currently "Entitled but Inactive"
   could mean:
   - SB-330 vesting period still active (years remain until vesting expires)
   - Applicant pulled back voluntarily
   - Financing failed
   - Market conditions changed

   v2 doesn't distinguish these — but better source data could.

7. **APR scope methodology (separate document).** This methodology covers
   status detection. A companion document defining what projects qualify as
   APR-reportable (Census housing-unit definition, GLA exceptions, hotel
   conversion rules) is needed — to be drafted as a separate methodology entry.

---

*Methodology documented 2026-05-13. Empirical basis from v2 data as of that
date (181 projects, 2,340 events, 1,275 documents — post-deduplication).
Thresholds are honest judgment calls informed by observed durations, not
arbitrary defaults.*
