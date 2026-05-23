# Post-fix full-rerun characterization (57 permits)

**Generated:** 2026-05-22T16:48:37
**Scope:** reset all 57 still-not_found permits to pending and re-ran the orchestrator with the auto-redirect-fix scraper. No polling loop added. No scraper modifications. Goal: characterize the recovery pattern at scale before deciding whether to add polling.

## Outcome at a glance

- Permits processed: **57 / 57** (clean completion, queue empty at end)
- **Succeeded: 52** (91% recovery rate)
- Still not_found: 5
- Errors: 0
- Cloudflare / login-walls: 0
- Total runtime: **688.9s (~11.5 min)** — faster than the 15-25 min estimate
- All 52 recoveries used the **`single_result_redirect`** path; 0 via results_list

## 1. Final queue distribution

| status | count |
|---|---|
| `succeeded` | 85 |
| `not_found` | 5 |
| `ambiguous` | 0 |
| `failed` | 0 |
| `pending` | 0 |
| **TOTAL** | **90** |

Cumulative across all runs: 31 pre-fix succeeded + 2 batch-of-5 + 52 this run = **85 of 90 (94.4%)** v2 in-scope B-permits have a verified Accela master triplet. **5 of 90 (5.6%) remain not_found.**

JSON files in `data/raw/accela_url_discovery/`: **87** (unchanged at 87; the 57 not_found JSONs were overwritten in place — 52 with new master content, 5 with refreshed not_found content). Per-permit logs in `logs/` for today: **87**.

## 2. Per-permit table (full 57)

| permit | found | match_path | records_seen | triplet | related | duration | WorkType | year |
|---|---|---|---|---|---|---|---|---|
| B2022-01278 | True | `single_result_redirect` | 1 | `DUB22-00000-009C4` | 0 | 14.92s | Demolition | 2023 |
| B2022-05181 | True | `single_result_redirect` | 1 | `DUB22-00000-00MDT` | 0 | 11.67s | Alteration | 2023 |
| B2022-05525 | True | `single_result_redirect` | 1 | `DUB22-00000-00N69` | 0 | 5.93s |  | 2023 |
| B2022-06060 | True | `single_result_redirect` | 1 | `DUB22-00000-00OKY` | 0 | 5.6s | Alteration | 2023 |
| B2023-00192 | True | `single_result_redirect` | 1 | `DUB23-00000-001UU` | 0 | 5.58s | New | 2024 |
| B2023-00401 | False | `results_list` | 0 | `(none)` | 0 | 5.43s | Alteration | 2023 |
| B2023-00595 | True | `single_result_redirect` | 1 | `DUB23-00000-005HB` | 0 | 6.08s | Alteration | 2023 |
| B2023-00675 | True | `single_result_redirect` | 1 | `DUB23-00000-00649` | 0 | 5.58s | Alteration | 2023 |
| B2023-01578 | True | `single_result_redirect` | 1 | `DUB23-00000-00CK5` | 0 | 5.56s | Alteration | 2023 |
| B2023-01880 | True | `single_result_redirect` | 1 | `DUB23-00000-00DU1` | 0 | 5.2s | Demolition | 2024 |
| B2023-02115 | True | `single_result_redirect` | 1 | `DUB23-00000-00EGB` | 0 | 5.6s | Alteration | 2023 |
| B2023-02303 | True | `single_result_redirect` | 1 | `DUB23-00000-00EYO` | 0 | 10.0s | Alteration | 2023 |
| B2023-03067 | True | `single_result_redirect` | 1 | `DUB23-00000-00H5J` | 0 | 5.46s | Demolition | 2023 |
| B2023-03256 | True | `single_result_redirect` | 1 | `DUB23-00000-00HNO` | 0 | 5.64s | Sign | 2024 |
| B2023-03308 | True | `single_result_redirect` | 1 | `DUB23-00000-00HT2` | 0 | 12.59s | Alteration | 2023 |
| B2023-03611 | True | `single_result_redirect` | 1 | `DUB23-00000-00IP2` | 0 | 10.24s | Alteration | 2023 |
| B2023-04430 | True | `single_result_redirect` | 1 | `DUB23-00000-00KXX` | 0 | 10.79s | Alteration | 2024 |
| B2023-04569 | True | `single_result_redirect` | 1 | `DUB23-00000-00LEH` | 0 | 11.09s | Alteration | 2023 |
| B2023-04586 | True | `single_result_redirect` | 1 | `DUB23-00000-00LFL` | 0 | 5.58s | Alteration | 2023 |
| B2023-05865 | True | `single_result_redirect` | 1 | `DUB23-00000-00OYG` | 0 | 10.76s | Alteration | 2023 |
| B2023-06274 | True | `single_result_redirect` | 1 | `DUB23-00000-00Q9N` | 0 | 6.54s | Alteration | 2024 |
| B2023-06442 | True | `single_result_redirect` | 1 | `DUB23-00000-00R90` | 0 | 5.9s | Demolition | 2024 |
| B2023-06443 | True | `single_result_redirect` | 1 | `DUB23-00000-00R94` | 0 | 5.75s | Demolition | 2024 |
| B2024-00736 | False | `results_list` | 0 | `(none)` | 0 | 5.6s | Alteration | 2024 |
| B2024-01572 | True | `single_result_redirect` | 1 | `DUB24-00000-00DFO` | 0 | 5.07s | Alteration | 2024 |
| B2024-01602 | True | `single_result_redirect` | 1 | `DUB24-00000-00DJW` | 0 | 5.92s | New | 2024 |
| B2024-01659 | False | `results_list` | 0 | `(none)` | 0 | 5.56s | Sign | 2024 |
| B2024-01841 | True | `single_result_redirect` | 1 | `DUB24-00000-00ELN` | 0 | 5.48s | Alteration | 2024 |
| B2024-01853 | True | `single_result_redirect` | 1 | `DUB24-00000-00ENA` | 0 | 5.59s | Alteration | 2024 |
| B2024-02120 | True | `single_result_redirect` | 1 | `DUB24-00000-00FJR` | 0 | 5.7s | New | 2024 |
| B2024-02569 | False | `results_list` | 0 | `(none)` | 0 | 5.59s | Demolition | 2024 |
| B2024-03280 | True | `single_result_redirect` | 1 | `DUB24-00000-00J8T` | 0 | 4.97s | Alteration | 2024 |
| B2024-03794 | True | `single_result_redirect` | 1 | `DUB24-00000-00L0E` | 0 | 5.49s | Alteration | 2025 |
| B2024-03884 | True | `single_result_redirect` | 1 | `DUB24-00000-00LC1` | 0 | 5.57s | Alteration | 2024 |
| B2024-03997 | True | `single_result_redirect` | 1 | `DUB24-00000-00LSA` | 0 | 5.65s | Alteration | 2024 |
| B2024-05208 | True | `single_result_redirect` | 1 | `DUB24-00000-00QEH` | 0 | 5.06s | Alteration | 2024 |
| B2024-05368 | True | `single_result_redirect` | 1 | `DUB24-00000-00QYF` | 0 | 5.93s | Alteration | 2024 |
| B2024-05470 | True | `single_result_redirect` | 1 | `DUB24-00000-00RB9` | 0 | 5.53s | Alteration | 2025 |
| B2024-05972 | True | `single_result_redirect` | 1 | `DUB24-00000-00TI4` | 0 | 4.97s | Alteration | 2025 |
| B2025-00388 | True | `single_result_redirect` | 1 | `DUB25-00000-004HH` | 0 | 5.55s | Demolition | 2025 |
| B2025-00605 | True | `single_result_redirect` | 1 | `DUB25-00000-0071Z` | 0 | 5.05s | Alteration | 2025 |
| B2025-00685 | False | `results_list` | 0 | `(none)` | 0 | 5.29s | Alteration | 2025 |
| B2025-00875 | True | `single_result_redirect` | 1 | `DUB25-00000-00AJM` | 0 | 5.06s | New | 2025 |
| B2025-00897 | True | `single_result_redirect` | 1 | `DUB25-00000-00ALT` | 0 | 5.73s | Alteration | 2025 |
| B2025-01202 | True | `single_result_redirect` | 1 | `DUB25-00000-00CY8` | 0 | 10.49s | Alteration | 2025 |
| B2025-01864 | True | `single_result_redirect` | 1 | `DUB25-00000-00FNL` | 0 | 6.26s | Alteration | 2025 |
| B2025-02211 | True | `single_result_redirect` | 1 | `DUB25-00000-00H51` | 0 | 5.21s | Alteration | 2025 |
| B2025-02220 | True | `single_result_redirect` | 1 | `DUB25-00000-00H69` | 0 | 5.12s | Alteration | 2025 |
| B2025-02413 | True | `single_result_redirect` | 1 | `DUB25-00000-00HX7` | 0 | 5.6s | Alteration | 2025 |
| B2025-02754 | True | `single_result_redirect` | 1 | `DUB25-00000-00J41` | 0 | 5.67s | Alteration | 2025 |
| B2025-03049 | True | `single_result_redirect` | 1 | `DUB25-00000-00K9K` | 0 | 5.64s | Alteration | 2025 |
| B2025-03189 | True | `single_result_redirect` | 1 | `DUB25-00000-00KQP` | 0 | 5.52s | Alteration | 2025 |
| B2025-03320 | True | `single_result_redirect` | 1 | `DUB25-00000-00L3N` | 0 | 5.21s | Alteration | 2025 |
| B2025-04805 | True | `single_result_redirect` | 1 | `DUB25-00000-00PFJ` | 0 | 5.59s | Addition | 2025 |
| B2025-04937 | True | `single_result_redirect` | 1 | `DUB25-00000-00PRL` | 0 | 5.58s | Alteration | 2025 |
| B2025-05132 | True | `single_result_redirect` | 1 | `DUB25-00000-00Q72` | 0 | 5.51s | Alteration | 2025 |
| B2025-05133 | True | `single_result_redirect` | 1 | `DUB25-00000-00Q73` | 0 | 6.04s | Alteration | 2025 |

## 3. Distribution counts

| outcome | count |
|---|---|
| `found=True` via `single_result_redirect` | 52 |
| `found=True` via `results_list` | 0 |  (0 in this run; the 5 results_list rows below are all not_found fallbacks)
| `found=False` (still not_found) | 5 |
| `ambiguous=True` | 0 |
| `errors[]` non-empty | 0 |

Every single success in this run took the `single_result_redirect` path. The fix is doing the work: 52 permits that Accela auto-redirects to CapDetail on a single-result search are now caught by signal 1 (page.url) or signal 2 (form action).

## 4. Cross-tabs against CPRA attributes

### 4a. WorkType × outcome

| WorkType | ok | not_found | ok-rate |
|---|---|---|---|
| Alteration | 39 | 3 | 92% |
| Demolition | 6 | 1 | 85% |
| New | 4 | 0 | 100% |
| Sign | 1 | 1 | 50% |
| (empty) | 1 | 0 | 100% |
| Addition | 1 | 0 | 100% |

**The WorkType pattern from Part 4 / batch-of-5 has effectively evaporated.** All 3 prior "Alteration ⇒ not_found" failures recovered. The remaining 5 not_found are spread across 3 WorkTypes (Alteration, Demolition, Sign) with no category dominating.

### 4b. Issuance year × outcome

| year | ok | not_found |
|---|---|---|
| 2023 | 15 | 1 |
| 2024 | 17 | 3 |
| 2025 | 20 | 1 |

Year is not a discriminator — failures spread across 2023 (1), 2024 (3), 2025 (1).

### 4c. UnitsAdded × outcome (bucketed)

| bucket | ok | not_found |
|---|---|---|
| `null` | 42 | 5 |
| `0` | 8 | 0 |
| `1` | 2 | 0 |

All 5 not_found have null UnitsAdded — but so do 42 of 52 succeeded. This is the dominant case in the data, not a discriminator.

### 4d. Project (address) × outcome

All 5 not_found permits are at **5 distinct addresses** (2440 SHATTUCK Ave, 1109 COWPER St, 2099 M L KING JR Way, 1136 KEITH Ave, 411 VASSAR Ave). No project clustering.

## 5. Status of the 3 prior batch-of-5 "Alteration" failures

| permit | prior outcome | this run outcome | new triplet |
|---|---|---|---|
| B2023-02303 | not_found (batch-of-5) | **succeeded** (10.0s) | DUB23-00000-00EYO |
| B2024-03884 | not_found (batch-of-5) | **succeeded** (5.57s) | DUB24-00000-00LC1 |
| B2023-04430 | not_found (batch-of-5) | **succeeded** (10.79s) | DUB23-00000-00KXX |

**All 3 recovered.** This conclusively retires the "Alteration permits aren't indexed in Accela's CapHome search" hypothesis from the earlier batch-of-5 report (Part 4 / batch-of-5 conclusions). The prior failures were timing flakiness, not category-level blocks. The original "Alteration 16% findable" pattern in the CPRA-join report was an artifact of the auto-redirect bug that has now been fixed for the cases the signals catch.

## 6. The 5 stubborn permits

| permit | WorkType | OccType | UnitsAdded | year | address | description |
|---|---|---|---|---|---|---|
| B2023-00401 | Alteration | U Private Garages, Carports, Sheds, | (null) | 2023 | 2440 SHATTUCK Ave | Install 400amp temp power meter for construction p... |
| B2024-00736 | Alteration | R-3 Residential: Dwellings (1 or 2  | (null) | 2024 | 1109 COWPER St | Kitchen & Bath Remodel, addition of 2 skylights, n... |
| B2024-01659 | Sign | R-2 Residential: Permanent, Multi-U | (null) | 2024 | 2099 M L KING JR Way | Installation of sign |
| B2024-02569 | Demolition | R-3 Residential: Dwellings (1 or 2  | (null) | 2024 | 1136 KEITH Ave | Demolish Single Family Residence & foundation. (Se... |
| B2025-00685 | Alteration | R-3 Residential: Dwellings (1 or 2  | (null) | 2025 | 411 VASSAR Ave | Remove & replace windows & exterior doors, same si... |

Characteristics:
- **5 distinct addresses** — no project clustering.
- **3 WorkTypes** (3 Alteration, 1 Demolition, 1 Sign) — no work-type clustering.
- **3 years** (2023, 2024, 2025) — no temporal clustering.
- **All have null UnitsAdded** — but so do 42 of 52 succeeded; not a discriminator.
- **All 5 ran cleanly**: `errors[]` empty, no exceptions, no Cloudflare. They just didn't trip the auto-redirect signals at check time.
- **Per-permit duration for the 5**: range 5-12s — all completed in the normal scraper time budget. Not timeouts.
- **B2023-02303 was 3/4 flaky** in the diagnostic run and recovered this time. By analogy, some or all of the 5 stubborn permits may be in the same flakiness bucket — running the same 5 again, some would likely recover.

Two hypotheses for the remaining 5 (NOT investigated in this prompt):

- **Hypothesis: residual timing-race.** Same mechanism as B2023-02303 — the auto-redirect signals had not propagated at the check point for these specific runs. Each permit would likely have a per-attempt success rate <100% but >0; the 5 here are simply the ones that happened to lose the race on this run. A polling-loop fix or a 1-2 retry-per-permit would likely recover most of them.
- **Hypothesis: genuinely absent.** Some permits may truly not be searchable via CapHome's by-permit-number search in any state. Could be very recent additions still propagating, or could be excluded by some Accela filter. Manual browser verification would distinguish from the timing hypothesis.

Either way, the impact is tiny: 5 of 90 (5.6%). The total recoverable set has gone from 31 (auto-redirect bug present) → 85 (auto-redirect fix in place).

## 7. Verdict

**PASS — substantial recovery (52 of 57 in this run = 91%); 85 of 90 cumulative = 94%).** No errors, no Cloudflare, no halts. The auto-redirect fix is doing the work; all 52 recoveries used the new single_result_redirect path. Pattern in the remaining 5 not_found is sparse and consistent with residual timing flakiness rather than category-level Accela index gaps.

Key reframings established by this run:

1. The Part 4 finding that "all 59 not_found permits are cpra_row_count=1" was a true description of the data but **the causal interpretation** (Accela doesn't index single-parcel small-work permits) was wrong. The real cause was the auto-redirect bug, which manifested as not_found on every single-parcel-single-record permit until the fix was applied. After the fix, 52 of those same 59 permits succeed.
2. The batch-of-5 verdict ("Alteration permits aren't in CapHome's index") was wrong for similar reasons. All 3 of the Alteration permits that failed in that small sample succeed in this rerun. Sample-size bias plus the not-yet-fully-characterized auto-redirect timing race led to a confident-but-incorrect pattern read.
3. The "narrow findings can produce wrong conclusions" discipline rule from the session opener has now been validated twice in a row: once by yesterday's URL discovery work overall, and once by this rerun specifically.

Next-step recommendation (informational only, not taken in this prompt):

- Add a polling loop to the auto-redirect signal checks (per the B2023-02303 diagnostic's suggestion). This would likely recover most or all of the 5 stubborn permits and harden the scraper against transient slow-render conditions in production runs.
- Alternatively, accept 94.4% as the recovery rate and move on. Five permits is a small enough residual that manual lookup would be a viable fallback.
