# Load 2 — Pipeline Front-Half (parsed from accela_status scrapes) — 2026-06-06

**Twelfth data-modifying operation.** Loaded 18 front-half stage rows parsed from the collected ZP
Processing-Status `.txt` scrapes in `data/raw/accela_status/`. **These are PIPELINE / IN-REVIEW data,
not completion-timeline data** — tagged distinctly so the duration analysis treats them correctly.
Pre-snapshot `keep_snapshot_2026-06-06_pre-load2-pipeline.db` (**6ed8e01c**). Canonical after:
**`0e9a8aab`**. Post-snapshot `keep_snapshot_2026-06-06_post-load2-pipeline.db`.

## What was loaded — 18 rows, 15 projects, source='planning_scrape', confidence='high'
- **15 `deemed_complete`** (Application-Complete dates) + **3 `entitled`** (real decision dates).
- Coverage after: deemed_complete 10→**25**, entitled 69→**72** (submitted unchanged at 179 — all 15
  already had a submitted date).

### Tagging scheme (in the `note` field, machine-filterable)
- **`[pipeline]`** (15 deemed_complete rows): in-review projects with no entitlement decision yet. Note
  carries Record Status. These populate the **front-of-pipeline / stock view**, NOT completed-project
  timelines. Mostly no CO.
- **`[censored-for-duration]`** (3 entitled rows: 2317 Channing/proj117 2024-12-12, 3035 Colby/proj82
  2025-11-13, 2298 Durant/proj26 2025-10-30): recently entitled, **not yet permitted/completed**. The
  duration analysis must **EXCLUDE / censor-handle** these — counting recent in-flight projects in the
  entitled→permitted median biases it downward (survivorship trap). Filter on `note LIKE '[censored%'`.

`confidence='high'` reflects date accuracy (real scraped milestones); the censor flag is a
duration-handling note, not a quality flag.

## Why this is NOT the "29 entitled" tranche expected
Parsing the 74 Processing-Status files (two formats: numbered `| Marked as: X | On: DATE` and
`Stage:` / `Marked as X on DATE`) showed the inventory's "29 unloaded entitled" was wrong: **only 6
files carry any decision date; just 3 are new + APN-matched.** Most are **in-review pipeline records**
(Staff Decision ACTIVE/TBD/no-entries), so only deemed_complete is available.

- **2920 Shattuck (221u, proj8)** and **2601 San Pablo (223u, proj7)** — both **Record Status "In
  Review"**, loaded as **deemed_complete-only** (2022-12-15 / 2023-11-17), entitled=none. Neither has a
  CO; they are mid-pipeline, not completions.
- **1914 Fifth (257u)** — **excluded**: its scrape is a **Zoning Research Letter (pre-application)**,
  not an entitlement.
- **26 of 74 files unmatched to v2 by APN — HELD** (need project creation; out of scope).

## Verification (committed because all passed)
rows 1,750→**1,768** (+18) · existing 1,750 rows survive · FK=0 · integrity=ok · CHECK-violations=0 ·
**CO completion fingerprint byte-identical** (CY2023=701, 2024=709, 2025=531, 2026=216; 2018-22
unchanged). project_stages is not referenced by `v_projects_flat`; completion logic untouched.

## Reversal
Restore: `cp keep_snapshot_2026-06-06_pre-load2-pipeline.db databases/berkeley_housing_v2.db`.

*Push held. Combined with Load 1, project_stages now carries front-half for the 10 completed majors
(timeline) + 15 in-review pipeline projects (stock/front-of-pipeline). The 2920/2601 entitlements
remain pending at the source — re-scrape when decided.*
