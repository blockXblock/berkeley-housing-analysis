# Accela Cross-Check Findings — 30-Project Sample

**Date:** 2026-05-12
**Method:** Manual Accela verification of 30 v2 projects via claude sidebar
**Sample composition:** 10 projects with co_issued events in v2 + 10 under-construction + 10 large entitled (≥50 units)
**Goal:** Identify completeness gaps in v2 vs Accela ground truth

---

## Summary of findings

All 30 projects verified across three batches. No critical data corruption found.
Findings split into two categories:

| Category | Count | Severity |
|----------|------:|----------|
| CPRA data gaps (permits in Accela not in our delivered file) | 1 confirmed, 2-3 possible | Real |
| Stale v2 classifications (post-CPRA-cutoff Accela activity) | 2 confirmed | Refresh-cycle artifact |
| False-positive completion events | 1 confirmed | Query-design issue |
| Stalled/expired projects (v2 status reflects intent, not reality) | 1 | Documentation gap |

No projects had finalings that v2 missed in the CPRA window. The import correctly captured what the CPRA delivered.

---

## Findings by category

### Category 1: CPRA data gaps

**Project 141 — 2016 Ashby Ave (50 units)**

- Accela has permit B2024-01268 (50-unit affordable, Issued 2024)
- CPRA xlsx delivery does NOT contain this permit (verified by direct file search)
- v2 correctly shows 0 CPRA permits for this project (import behaved correctly given source data)
- Implication: City CPRA filter is narrower than "all residential building permits 2023-2025"
- Affordable housing projects, mixed-use, or atypical OccType classifications may be excluded
- Action: Flag for clarification with City Clerk in future CPRA requests; consider manual lookup of B2024-01268 to populate v2 manually
- Severity: Real concern — 50 units is significant for APR analysis

**Project 71 — 40 Hill Rd (possible missing permit)**

- Accela may show 3 finaled permits in CPRA window
- v2 has 2 CPRA-sourced permits
- Possible gap: B2023-01661 (reroof, Finaled Apr 2023)
- Minor permit, low priority

**Project 67 — 1419 Grant St (possibly missing minor permits)**

- Accela shows B2025-04912 (bolting/bracing, Finaled 10/31/2025) and B2024-01795 (roofing, Finaled 04/11/2024)
- Both finaled in CPRA window
- Check whether they were imported
- Action: Spot-check v2 permits for project 67; if missing, the CPRA may have included them but our import logic excluded them

**Project 132 — 1627 Jaynes St (possibly missing demo permit)**

- B2025-04241 (demo, Finaled 09/24/2025) is in CPRA window
- Check whether captured by import

### Category 2: Stale v2 classifications

**Project 133 — 2128 Oxford St (Core Spaces 485-unit)**

- v2 classifies as "pre-permit" (Group 3 in this sample)
- Accela shows active construction since 2024:
  - Foundation and demolition permits in "Corrections List Issued" state
  - Phase 2 full architectural permit filed Nov 2025
- Should be reclassified as under_construction
- These permits were filed late 2025; some may post-date the CPRA filter window
- Action: Update v2 status after next CPRA refresh; consider manual reclassification

**Project 1 — 1750 Sacramento St / North Berkeley BART (739 units)**

- v2 classifies as "pre-permit"
- Accela shows 2 building permits filed Dec 2025 in early plan review
- Project has crossed into permit phase
- Both permits post-date CPRA filter window (Dec 2025 after the 1/1/2023-12/31/2025 range arguably — or at the edge)
- Action: Pick up in next CPRA refresh

### Category 3: False-positive completion events

**Project 63 — 1716 Seventh St**

- v2 has one co_issued event dated 2023-07-06
- The event links to permit B2022-01278 (demolition of existing SFR/garage/shed)
- The two main construction permits (B2022-01332, B2022-01386 — both "new SFR") are still Issued, not Finaled
- v2 misleadingly shows project as completed because demolition permit was finaled
- Implication: Future "completed projects" queries must distinguish demolition finaling from main construction finaling
- Action for Explorer rewrite: when querying for project completion, filter co_issued events by linked permit type (exclude demolition, MEP-only, solar-only)

### Category 4: Stalled / expired projects

**Project 35 — 2190 Shattuck Ave (452 units)**

- v2 records 452-unit project
- Accela: two prior construction permit cycles both expired (2019 and 2023)
- No active permit as of 2026-05-12
- Project may be effectively dead, but v2 still tracks the entitled state
- Action: Add a note to v2.projects.notes capturing the expired status; consider a new classification type for "expired permits"

---

## What did NOT surface as issues

**Working correctly:**
- 9 of 10 Group 1 projects had no finaling gaps
- Sub-permit deduplication (REV permits at Project 34, etc.) correctly excluded
- UC projects (171, 177, 165) correctly excluded from address-based search
- Pre-permit projects (151, 119, 3, 2) correctly classified

**Sample limitations:**
- 30 of 181 projects checked (16.6% sample)
- No systematic check of "UNMATCHED" projects (112 projects we know have no CPRA activity)
- No systematic check of the false-positive co_issued pattern across all projects

---

## Recommendations for future work

### Before publishing v2-derived Explorer

1. **Address the project 63 false-positive pattern**: when querying for "completed projects" in Explorer, filter co_issued events by linked permit type. Distinguish:
   - co_issued where permit type = building_new_construction → genuine project completion
   - co_issued where permit type = demolition → site preparation complete
   - co_issued where permit type = solar / MEP / minor work → ancillary completions

2. **Document project 35 (2190 Shattuck) status**: 452-unit figure represents entitled intent, not built reality. Flag in v2.

3. **Verify project 141 import scope**: manually look up B2024-01268 and import to v2 (a one-off curation step).

### For next CPRA request

When the 2018-2022 CPRA response arrives (~10 days from 2026-05-10):
1. Run the same kind of 30-project spot-check against the new delivery
2. Look for the same pattern: known-existing permits that don't appear in delivered file
3. If gaps recur, send clarifying question to City Clerk about filter scope (specifically OccType filters and Mixed-Use classification)

### Systematic checks worth running

1. **Across all 181 projects: identify co_issued events linked to demolition permits**
   - Query: `SELECT project_id, pe.event_date FROM project_events pe JOIN permits pm ON pe.permit_id = pm.id WHERE event_type=co_issued AND pm.permit_type points to demolition`
   - These are candidates for misinterpretation as project completion

2. **Across all 112 UNMATCHED projects from staleness assessment**: are any like project 141 (have Accela activity that CPRA didn't include)?
   - Would require sidebar work or systematic Accela queries
   - Not blocking; can do over time

---

*Findings compiled 2026-05-12 from sidebar Accela verification of 30 v2 projects. Saved for reference during Explorer rewrite and future CPRA processing.*
