---
title: What changes on the website — published (2026-09-08) vs regenerated (2026-09-25)
date: 2026-09-25
type: audit
status: open
area: docs/audit
---

# Published vs regenerated

`docs/explorer_data.js` on the live site was generated **2026-09-08**. This is the diff against a
fresh run of `export_explorer_data_v2.py` after today's work.

**Nothing is published yet.** The export writes `docs/explorer_data_v2_working.js` by design;
promoting it is a deliberate `cp` that the deploy gate checks separately.

## Totals

| | published | regenerated | |
|---|---|---|---|
| projects | 909 | **1,099** | +190 |
| events | 3,914 | **5,548** | +1,634 |
| total units | 19,669 | **19,956** | +287 |
| **documents** | **2,254** | **2,254** | **0** |
| staff | 85 | 89 | +4 |
| timeline months | 49 | 62 | +13 |
| city APR comparison rows | 760 | 779 | +19 |

## Document links — the thing to be careful about

**Zero lost, zero changed.** 2,254 documents across **790 projects** in both. Verified three ways:
per-project counts diffed in both directions, orphan check against `projects`, and the export's own
document query. `documents` links to projects directly through `documents.project_id`; the ingest
only ever inserted projects, so nothing could be detached.

## Status — what a visitor sees

| status | published | regenerated | |
|---|---|---|---|
| Building Permits Filed | 11 | **124** | +113 |
| Completed | 703 | **767** | +64 |
| Under Construction | 68 | **77** | +9 |
| Permitted but Inactive | 1 | **15** | +14 |
| Entitled | 33 | 30 | −3 |
| Under Review | 69 | 67 | −2 |
| **Withdrawn** | **5** | **0** | **−5** |
| Pre-Application | 16 | 16 | |
| Entitled but Inactive | 3 | 3 | |

**Withdrawn falls to zero.** Those five were the Auto-Closed mis-mapping. Four are under
construction: 2902 Adeline (54u), 2127 Dwight (58u), 2587 Telegraph (52u), 2016 Ashby (50u).

**"Permitted but Inactive" 1 → 15** is the existing rule (permit >24 months old, no construction)
applied to newly-created projects. ⚠ Read with care: for the six with 2024 permits, "inactive" may
reflect **our** lack of inspection coverage rather than a stalled site. The label is honest about
what we observe, not about what is happening.

## Completions by year

| year | published | regenerated | |
|---|---|---|---|
| 2022 | 84 proj / 695u | 84 / 695 | **unchanged** |
| 2023 | 100 proj / 625u | 100 / 625 | **unchanged** |
| 2024 | 86 proj / 1,384u | 86 / 1,384 | **unchanged** |
| 2025 | 98 proj / 530u | **117 / 588** | +19 proj, +58u |
| 2026 | **2 proj / 216u** | **47 / 271** | **+45 proj, +55u** |
| all-time | 703 / 4,383u | **767 / 4,496u** | +64 proj, +113u |

**No historical revision.** 2022–2024 are byte-identical; every change is 2025–2026, which is
exactly where the un-ingested CPRA feed was missing.

## APR Table A2 (same generator, run against both databases)

| year | before | after | |
|---|---|---|---|
| 2024 | 108 proj / 2,368u | 132 / 2,402 | +24 proj, +34u |
| 2025 | 124 proj / 3,191u | 233 / 3,367 | +109 proj, +176u |
| 2026 | 10 proj / 1,738u | 104 / 1,878 | +94 proj, +140u |

2024 moves despite completions being unchanged because Table A2 counts **any** milestone —
entitlement, BP or CO — and the ingest added 2024 building-permit events.

**Table A remains 0 rows**, as it has been: `generate_table_a()` runs `WHERE NULL LIKE ?`. That is
the separate deemed-complete work, not a regression.

## Spot checks against the live file

| project | published | regenerated |
|---|---|---|
| 2902 ADELINE St (54u) | Withdrawn | **Under Construction** |
| 2016 ASHBY Ave (50u) | Withdrawn | **Under Construction** |
| 2127 DWIGHT Way (58u) | Withdrawn | **Under Construction** |
| 2587 TELEGRAPH Ave (52u) | Withdrawn | **Under Construction** |
| 1914 FIFTH St (257u) | Under Review | Under Review ✓ |
| 2420 SHATTUCK Ave (132u) | Under Review | Under Review ✓ |
| 3030 TELEGRAPH Ave (144u) | Completed | Completed |
| 2455 TELEGRAPH Ave (68u) | Under Review | Under Review |
| 2955 SHATTUCK Ave (74u) | Under Review | Under Review |

## Deploy gate

All content checks pass — legend appears once and names every stage, no duplicated video, every
referenced local asset present, catalog consistent. The only failure is **"something is staged
[0 files]"**: the gate is written to run against a staged deploy and nothing is staged yet.

## To publish

    cp docs/explorer_data_v2_working.js docs/explorer_data.js

Then stage, re-run the gate, and deploy. **John's call.**

### Other served pages that go stale with it

These read v2 or its exports and write **directly into `docs/`** — they have no working-file guard,
so running them publishes immediately. Not run here.

| page | generator | what is now stale |
|---|---|---|
| `docs/index.html` | hand-edited card | Explorer card says **"all 909 projects"** → 1,099 |
| `docs/pipeline-state.html` | `gen_pipeline_state_page.py` | state 5 reads **703 projects** → 767; state 2 **"5,441 units"**; the five-state SVG |
| `docs/players.html` | `gen_players_page.py` | 21 developers / 15 architects / 840 owners |

A deploy that promotes the explorer data without regenerating these leaves the site internally
inconsistent — the map would show 1,099 projects while the card beside it says 909. **Regenerate
all of them in one pass, then run the gate once.**
