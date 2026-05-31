# APR Pilot Results — v1 vs v2 generator — 2026-05-31

**Goal:** Validate `generate_apr_v2.py` (reads `berkeley_housing_v2.db` via
`v_projects_flat`) against `generate_apr.py` (reads frozen
`berkeley_housing_analysis.db`); classify every diff against the pre-flight key;
recommend adopt / hold. Read-only on DBs; outputs written to `/tmp/apr_pilot/`
(repo `data/apr/` untouched). Does not touch external drives or the Toshiba copy.

---

## Verdict (up front): **DO NOT adopt v2 as canonical yet** — 3 blockers

v2's core mechanics are **sound and more complete** than frozen v1, but it is not
yet a drop-in replacement. Three concrete blockers, all fixable:

1. **v2 cannot produce Table A.** Both runs emitted Table A2 + B but **no Table A**
   — the generator warned it lacks `density_bonus / sb35_flag / sb330_flag /
   ab2011_flag` (need join to `project_classifications`) and `construction_status`
   (needs derivation). This is the compat-view gap from the migration checklist.
   Table A is a required APR table → **hard blocker.**
2. **CO/permitted totals don't reconcile with the validated reference** (below).
3. **A duplicate project record** (2138 Kittredge) needs canonical resolution.

What the pilot **did** prove sound: stage-progression handling, distinct
milestone events, and that v2 is far more current than v1 (esp. 2025). Details
below. The **explorer cutover is independent** of these APR-specific gaps.

---

## Stage 1 — Generation

Both ran clean (no crashes). v1 → Tables A, A2, B. **v2 → A2, B only (no A).**
v1's run printed identical "Stalled: 38 / 5393 units" for both years (a
current-state, not per-year, summary).

## Stage 2/3 — Diffs, classified against the pre-flight key

### Table B (RHNA permitted units)
| Income | v1 | v2 | Δ |
|---|---|---|---|
| Very Low | 319 | 334 | +15 |
| Above Moderate | 960 | **1861** | **+901** |
| **Total** | 1279 | **2195** | **+916** |

→ **Date-enrichment** category: v2 has BP/CO dates v1 lacked, so far more units
count as permitted. *Shared limitation flagged:* Table B is **identical for 2024
and 2025 in BOTH v1 and v2** — neither filters RHNA by year (cumulative summary).

### Table A2 (per-project permitted) — membership
| Year | v1 rows | v2 rows | v2 adds | v2 drops |
|---|---|---|---|---|
| 2024 | 21 | 34 | +17 | 4 (moved → 2025) |
| 2025 | 27 | 57 | +31 | 0 (superset) |

- **2024 drops → 2025** (2538 Durant, 2587 Telegraph, 2902 Adeline): **date
  anchor-semantic** — v2's different event-date anchor reassigns the milestone year.
- **+2 projects** confirmed present: 2328 Channing (2024), 2330 Blake (2025).
- Remaining additions: **date enrichment** (gained a milestone date in-year).

### CO'd units in reporting year (net_units) — the reconciliation problem
| | v1 | v2 | NotebookLM ref |
|---|---|---|---|
| CY2024 | 5 proj / **786** units | 13 proj / **1233** units | ~708 |
| CY2025 | 3 proj / **126** units | 21 proj / **666** units | ~482 |

- **v1 2024 (786) ≈ reference (708)** — v1 well-calibrated for 2024.
- **v1 2025 (126) ≪ reference (482)** — v1 is badly stale for 2025 (frozen April).
- **v2 overshoots both** (1233 vs 708; 666 vs 482). For 2025 v2 is far closer to
  truth than v1; for 2024 it overshoots by ~447 units. **This overshoot is the
  signal to reconcile before adoption.**

v2 CY2024 CO overshoot drivers (net units): 1950 Oxford (300, **UC-flagged** —
candidate **group-quarters exclusion**), 2352 Shattuck (237), 1598 University
(207, *not* UC), 2150 Kittredge (169), 1951 Shattuck (163, co=**2024-01-01**
placeholder), 2099 MLK (72, co=**2024-01-01** placeholder). Mix of legitimate
enrichment + one UC project possibly excludable + month-floored placeholder dates.

## Stage 4 — Targeted tricky projects (v2 handling)

| Project | v2 result | Verdict |
|---|---|---|
| **2555 College** (055 184702000) | **12 units**, **ONE CO** (2025-07-25); appears in **2024** (entitled 2024-04-05) **and 2025** (BP 2025-06-02 + CO) | ✅ Correct stage-progression, not duplication. 12 units (not 11). |
| **2150 Kittredge** (057 202901600) | 169 units, **ONE CO** (2024-03-06), BP 2023-05-11 | ✅ Single CO; distinct from the two 2138 Kittredge records |
| **1701 San Pablo** | entitled **2013-08-08**, BP **2025-11-06** (distinct events) | ✅ Stage-progression represented (entitlement year 2013, not 2023 as hypothesized) |
| **1740 San Pablo** | BP 2025-12-18, no entitlement recorded | ✅ BP-stage only |
| **2138 Kittredge** ⚠️ | **TWO records**: id 113 (73u, Permitted) + id 118 (66u, Entitled) | ⚠️ **Possible base/bonus split or duplicate — needs canonical resolution** |

## Stage 5 — Diff classification tally

| Category | Where | Expected? |
|---|---|---|
| Date enrichment | most A2 additions; +916 Table B units | ✅ yes |
| Date anchor-semantic | 4 projects 2024→2025; 2024-01-01 placeholders | ✅ yes (known) |
| +2 projects | 2328 Channing, 2330 Blake | ✅ yes |
| Status recoding | status column (22→8 vocab) | ✅ yes |
| Group-quarters candidate | 1950 Oxford (UC, 300u) | ⚠️ apply exclusion rule |
| **UNEXPLAINED — investigate** | (a) **no Table A** (tooling gap); (b) **CO total overshoot** vs reference; (c) **2138 Kittredge duplicate** | ❗ the real signal |

### The UNEXPLAINED residual (the signal)
1. **Table A not generated** — `generate_apr_v2.py` can't build it (missing
   classification flags). Tooling/compat-view gap, not data.
2. **CO-total overshoot vs NotebookLM** — v2 CY2024 1233 vs ~708. Needs
   reconciliation: apply group-quarters exclusion (1950 Oxford), scrub
   `2024-01-01` placeholder CO dates, and confirm the other large 2024 COs
   (2352 Shattuck 237, 1598 University 207) are genuine in-year COs v1/PDF missed.
3. **2138 Kittredge** two records (73u + 66u) — resolve to canonical.

---

## Recommendation

**Hold adoption.** v2 is the right direction — structurally matched to v1
(headers identical), correctly models stage-progression and distinct milestone
events, and is markedly more current (v1's 2025 is badly stale: 126 vs ref 482;
v2's 666 is far closer). But before it can be canonical:

1. **Implement Table A in `generate_apr_v2.py`** — extend `v_projects_flat` (or
   join `project_classifications`) to expose `density_bonus`, `sb35/sb330/ab2011`,
   `construction_status` (same view fix the KML migration also needs).
2. **Reconcile CO totals** — apply group-quarters exclusion (rule 1), clean
   `2024-01-01` placeholder dates, and verify the new large 2024 COs are real.
3. **Resolve 2138 Kittredge** duplicate to a canonical record.
4. *(Lower priority, shared with v1)* make Table B year-aware.

Once (1)–(3) are fixed, re-run this pilot; if CY2024 lands near ~708 (with
group-quarters labeled separately) and Table A diffs cleanly, adopt v2.

*Pilot only. Uncommitted. No repoint, no v1 deletion, no DB/script modified.
Outputs in `/tmp/apr_pilot/`.*
