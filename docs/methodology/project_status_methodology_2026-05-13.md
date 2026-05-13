# Project Status & Inactive Detection — Methodology

**Created:** 2026-05-13
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

Sample size: 61 projects with both events
- Average: 115 days (~4 months)
- Range observed: 0 to 489 days

### Application Complete → Entitled

Sample size: 45 projects with both events
- Average: 279 days (~9 months)
- Range observed: 9 to 1,087 days

### Entitled → Building Permit Issued

Sample size: 22 projects (excluding corrupted dates and negative-duration outliers)
- Typical range: 100-700 days (3-23 months)
- Outliers: 2,000+ days indicate genuinely stalled projects (6+ years between
  entitlement and permit application)

**Threshold choice: 36 months for "Entitled but Inactive"**

This sits clearly beyond the typical 3-23 month range. Projects exceeding
36 months without a building permit application represent real outliers,
not "slow but normal" progressions.

### Building Permit → Certificate of Occupancy

Sample size: 36 projects with both events
- Average: 379 days (~12 months)
- Range observed: 4 to 2,893 days

This is the full bp_issued → co_issued duration. The bp_issued →
construction_start sub-segment is shorter but not directly measured because
many projects lack a construction_start_observed event.

**Threshold choice: 24 months for "Permitted but Inactive"**

A 24-month gap between permit issuance and observable construction activity
is unusual. This threshold is somewhat conservative; further analysis with
2018-2022 CPRA data (expected ~2026-05-20) may refine it.

---

## Detection logic

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

## Data limitations

### What can be reliably detected

- Projects with verified entitlement events but no subsequent permit events
- Projects with verified permit events but no subsequent construction events

### What cannot be reliably detected

- **Projects that have informal "next steps" not captured in v2** (e.g., owner
  in negotiation with developer, financing in progress) — these would still
  appear "inactive" though the project is moving
- **Projects where v2 is missing events** due to CPRA scope gaps (some
  Berkeley building permits weren't in the 2023-2025 CPRA delivery; see
  `docs/methodology/cpra_lessons_learned_2026-05-11.md`)
- **Projects with corrupted event dates** (a small number show event sequences
  out of chronological order, suggesting v1→v2 migration data quality issues
  — observed in projects 34, 113, 126, 129, 140, 149, 179 as of 2026-05-13)

### Sample size caveat

These thresholds were chosen from observed durations in 22-61 projects per
transition. As v2 ingests additional CPRA data (notably the 2018-2022 request,
expected ~2026-05-20), distributions may shift. Thresholds should be
re-validated periodically against the growing dataset.

---

## Future work

1. **Re-evaluate thresholds after 2018-2022 CPRA arrival.** Larger sample size
   may justify tightening or loosening the 24/36 month thresholds.

2. **Add 90th and 95th percentile reporting to the methodology.** Currently
   we have averages and ranges; explicit percentiles would inform thresholds
   more precisely.

3. **Investigate corrupted event dates** (projects 34, 113, 126, 129, 140,
   149, 179). Some have negative event-to-event durations, suggesting v2
   migration errors that should be fixed.

4. **Differentiate "inactive" sub-types.** Currently "Entitled but Inactive"
   could mean:
   - SB-330 vesting period still active (years remain until vesting expires)
   - Applicant pulled back voluntarily
   - Financing failed
   - Market conditions changed
   v2 doesn't distinguish these — but better source data could.

5. **Consider an "Inactive 12+ months" mid-tier.** Between "Entitled" and
   "Entitled but Inactive" might be useful for some analyses.

---

*Methodology documented 2026-05-13. Empirical basis from v2 data as of that
date (181 projects, 2,787 events). Thresholds are honest judgment calls
informed by observed durations, not arbitrary defaults.*
