# Two adjudications, one batch: The Overture (window-attributed) + The Den (phase demote)

**Date:** 2026-07-03 · **Who:** CC adjudication (local records + Accela + web corroboration), John's go
("go, run 2510 Channing and batch both") · **Snapshot:** `keep_snapshot_2026-07-03_pre-windowbatch.db`.
These were the two largest ours-more rows in the 2026-07-03 residual decomposition (−44 and −40) —
same symptom (we count, city doesn't), OPPOSITE root causes.

## 1. The Overture (B2014-05786, 1808-1812 University, 44u) — WINDOW ATTRIBUTION, stays counted
**Finding:** our completion grain (permit-FINALED, 2021-08-31) lags the building's real completion by
~5 years. Evidence (5 convergent, in `corrections/v4/window_attributions.json`): issued 2016-01-21;
listings say built 2016 (Trulia/Zillow, "The Overture"); our own TI permit B2017-05238 (2017-12) fits
out "empty space @ 1812 University — The Overt[ure]"; the city credits the 44 NOWHERE in Table A2
2018-2025 (checked by APN and address — its 1812-University rows track only the 2-studio conversion);
the city's 2025 filing calls it "existing … with 44 dwelling units." The city presumably credited it
in CY2016/17 (pre-mirror). **Treatment:** the building stays FULLY COUNTED (real housing; nothing
demoted); the new `window_attributions.json` calibration + JN-E §11b subtract it from OUR side of the
2018-25 COMPARISON only. Gold-standard capstone (optional): the CY2016/17 city APR PDF.

## 2. The Den (B2019-01789, 2510 Channing, 40u) — COUNT-ONCE phase demote, −40
**Finding:** the 40 was counted on the FOUNDATION permit's final ("Phase I of II: Concrete work incl.
foundation", finaled 2021-10) while the unit-bearing completion **B2018-01337 ("Phase II of II:
Superstructure … 8 story mixed use") has NEVER finaled** — though the building is real, built 2020,
occupied and leasing ("The Den", 8-story student housing). The city credits no CO either (its row
tracks B2018-01337's BP) — **both records apply the same wait-for-final grain once we fix our phase
attribution.** **Treatment:** calibration row appended to `c_multifamily_collapse.csv` (demote
B2019-01789 → subsidiary/0, keep B2018-01337); the count RETURNS AUTOMATICALLY when B2018-01337
finals in a future CPRA pull. This is the standing C-multifamily rule, fourth instance.

## Write trace
apply_c_multifamily (4 rows: 1 changed, 3 idempotent, bump verified-already) → **CO 4,143 → 4,103**;
BP 3,945 / events 82,923 unchanged → baseline **2026-07-03b** APPENDED (raw gap **+81**;
**window-adjusted comparison (4,103−44) vs 4,022 = +37**; sha 3a7bea4f22f2d793) → JN-E gained §11b
(derives the same-period comparison from the calibration) + regenerated (gate PASS) → from-raw chain
re-validated. Checksums: c_multifamily 4 rows; window_attributions 1 permit/44u.

## Reconciliation state after this batch
Raw: **4,103 vs 4,022 (+81)** · same-period: **+37** · held: San Pablo 23 · named-open: Acheson-A +37
(convention), 12 UNCERTAINs, 20 no-candidate city rows, CY2025 filing-lag rows (~60u, self-resolving).
Every line has a name; the +37 same-period figure is dominated by the city's own gaps (the unfiled
0-San-Pablo GLA 41).

## Reverse
Restore the snapshot; or delete the Den row from c_multifamily_collapse.csv + re-promote
B2019-01789's finaled master to new_unit/40, and delete window_attributions.json (comparison-only).
