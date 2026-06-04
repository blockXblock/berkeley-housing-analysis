# CY2023 Pass 2 — Major-Project Corrections — 2026-06-03

**Fifth data-modifying operation.** Corrected 4 existing v2 projects with Accela-verified
2023 completions (CY2023 Pass 2), completing the verified portion of CY2023.
Pre-write snapshot: `keep_snapshot_2026-06-03_pre-cy2023-pass2.db` (a5e63b1b).
Canonical after: **`bdadce65`**. Post-write snapshot: `keep_snapshot_2026-06-03_post-cy2023-pass2.db`.
Script: `scripts/cy2023_pass2_corrections_2026-06-03.py`.

## Result
| Year | before | after | note |
|---|---|---|---|
| **CY2023** | 441 | **631** | +190 (4 corrections) |
| CY2024 | 709 | 709 | unchanged |
| **CY2025** | 532 | **531** | **−1: 605 Neilson moved to its true 2023 completion** |
| CY2026 | 216 | 216 | unchanged |

**Note on CY2025 = 531 (was 532):** 605 Neilson's prior co=2025-09-04 (B2022-06065) was a
CPRA wrong-pick; Accela confirms the real ADU completion is 2023-04-20 (B2020-00481). Moving
it to its true year is *more* accurate; CY2025 correctly drops by 1. This supersedes the
published 532 (dashboard / Colab CSVs / earlier audit docs) — those surfaces are now stale and
need a refresh when next deployed.

## The 4 corrections (Accela-verified)
- **3000 San Pablo (proj168):** 29u/In Review → **78u/Completed, CO 2023-06-05** (B2020-04316, 78u permit-stated). Corrects a wrong unit count + stage.
- **2072 Addison (proj182):** Entitled/no-CO → **Completed, CO 2023-07-18** (B2018-04293, 66u, matches CKAN).
- **2009 Addison (proj91):** 0u/no-counted-CO → **45u, CO 2023-04-04** (B2019-02956). **FLAG: 45u is CKAN-derived, not permit-stated** (recorded with a note on the affordability row). The prior 2024-10-11 co event (B2023-03256, an LED-sign permit) stays subsidiary.
- **605 Neilson (proj304):** wrong **2025-09-04 → 2023-04-20** (B2020-00481, 1u ADU). Moves it out of CY2025.

## Documented findings
- **2352 Shattuck / Logan Park (proj179) — CKAN year error:** both structural permits Finaled
  **2022** (Ph II 01/14/2022, Ph I 10/06/2022); no 2023 structural Final exists. CKAN's CY2023
  ~69u is **mis-yeared — Logan Park actually completed 2022** (pre-RHNA-cycle-6, excluded from
  reported years). Left uncounted (co=None). **CKAN overstates CY2023 by ~69u.** (69u CKAN-derived.)
- **2210 MLK (proj362) — HELD:** not in the Accela Building module (legacy/APN-filed); can't
  confirm CKAN-2023 vs its CPRA-backed v2-2025. Left at 2025-03-26 (stays CY2025). Needs a legacy
  permit-DB / APN lookup.

## CY2023 reconciliation
**631** (441 Pass 1 ADU + 190 Pass 2) vs CKAN 704. Gap = ~69u Logan Park (CKAN mis-year, actually
2022) + 1u 2210 MLK (held) + small Rule-C-vs-CKAN deltas. **We are more year-accurate than CKAN.**

## Reversal
Canonical `a5e63b1b` → **`bdadce65`**. Restore: `cp keep_snapshot_2026-06-03_pre-cy2023-pass2.db
databases/berkeley_housing_v2.db`.

## Write-time verification (committed because all passed)
CY2023=631 · CY2024=709 · CY2026=216 · CY2025=531 (605 Neilson moved) · 4 corrections applied
(168/182/91/304) · holds untouched (362/179) · FK=0 · integrity=ok.

*Push held. The pre-policy ADU backfill (2018-2022) builds on this `bdadce65` base.*
