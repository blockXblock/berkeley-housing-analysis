# Can the RHNA progress bar come off hold? (2026-09-30, read-only)

The bar was held because v2 modeled only ~28 projects with a building permit (1,198 units / 13.4% of the 8,934
6th-cycle RHNA, an internal lower bound). v4 now holds the citywide CPRA permit stream (2018 → 2026-07-07).

**Method.** RHNA credit is the building's FIRST building permit on/after 2022-06-30 (CLAUDE.md). Event-grain counts
(one row per unit-carrying permit) put phased buildings in the wrong year — the City dates 2099 MLK (72u) and 2527
San Pablo (63u) by their first permits in 2022; the unit-carrying permits issued in 2023 — and they miss ledger
corrections, because grounded_counts promotes only the FINALED event (Poet's Place reads 1 unit on its permit, Dwight
0). So the count is taken at BUILDING grain: v4 `structures` + `units` (ledger-aware), dated by the earliest
`permit_issued` among each building's `structure_events`.

| Year | Ours, building, first permit | Ours, main permit | City APR | Δ first | Δ main |
|---|---|---|---|---|---|
| 2018 | 390 | 389 | 380 | +10 | +9 |
| 2019 | 363 | 362 | 363 | 0 | −1 |
| 2020 | 609 | 609 | 766 | −157 | −157 |
| 2021 | 617 | 595 | 506 | +111 | +89 |
| 2022 | 899 | 496 | 887 | +12 | −391 |
| 2023 | 268 | 529 | 432 | −164 | +97 |
| 2024 | 720 | 720 | 734 | −14 | −14 |
| 2025 | 547 | 545 | 463 | +84 | +82 |
| 2018–25 | 4,413 | 4,245 | 4,531 | −118 | −286 |

**6th cycle (first permit ≥ 2022-06-30), through 2025: ours 1,938 vs the City's 2,120** (the City's own rows with
BP_ISSUE_DT1 ≥ 2022-06-30): **−182 (−8.6%)**; 21.7% vs 23.7% of 8,934. Through 2026-07-07, ours 2,082 (23.3%).

**Verdict: not yet.** Far better than the held v2 figure, but an 8.6% unexplained gap is too much to publish as
"Berkeley's progress". Known contributors: group quarters the City counts (2100 San Pablo 96u, BP 2020; 2000 Dwight
113 vs our 88, BP 2022 — both before the 6th cycle). **Next:** the same building-level match as the completion audit,
for 6th-cycle permits only, so every unit of the −182 is named. **Income split:** RHNA progress is by income tier; v4
carries affordability for only some projects (the City reports VLI 254 / LI 238 / MOD 105 / above-moderate 1,523), so
a first bar would show the total only.
