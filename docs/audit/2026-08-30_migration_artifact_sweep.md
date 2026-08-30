# Migration-artifact sweep of v2 — 2026-08-30

**Why.** Every data error found on 29 August came from a `migration_v1_to_v2` row whose
figures nobody had checked against a source: People's Park's 1,100 (its own description said
1,113), Bancroft's 253 ft (the Regents say 263), and two unit counts that were placeholders
the rows themselves described as *"placed as 1BR for schema compliance."* If one family of
fields went unchecked, others did. Read-only sweep, no writes.

## Exposure

| | count |
|---|---|
| `project_versions` total | 905 |
| asserted by `migration_v1_to_v2_20260507` | 174 |
| …of those, with **no source document** | 172 |
| **active projects resting on an unsourced migration version** | **167** |

Every other assertion source in the table (the CPRA permit feeds, the CKAN parcel-pointer
ingest, yesterday's UC harvest) carries a source document. The migration cohort is the
exception, and it is where all four of yesterday's errors lived.

## Finding 1 — `filed_date` is year-precision more often than not, and the view hides it

**93 of 169 non-null `filed_date`s fall on 1 January** (55%), clustered in 2024 (28) and
2025 (49). Applications are not filed on New Year's Day.

The database is honest about this. All 99 such `application_submitted` events carry
`event_date_precision = 'year'` and `source_type = 'inferred'`, asserted by the migration.
Non-Jan-1 application events are `exact`. v2 knows exactly which dates it only knows to the
year.

**`v_projects_flat.filed_date` drops that precision.** It renders a year-precision event as
`2025-01-01`, indistinguishable from a date known to the day, and nothing downstream can tell
the difference. The view does not expose `event_date_precision` at all.

### It reaches the public, and it is visibly wrong

`export_explorer_data_v2.py` computes `processing_days = (entitled_date − filed_date).days`
and publishes it. Of 55 projects carrying that figure, **13 (24%) derive it from a
year-precision filed date**, each carrying up to ±364 days of error on a number the site
presents as fact — under a homepage promise of "the full permit timeline — when it was filed,
when it was approved."

**Four are impossible and are live on berkeleybuild.com now**, in the served
`docs/explorer_data.js`:

| project | filed | entitled | published processing_days |
|---|---|---|---|
| proj153 1701 San Pablo Ave | 2024-01-01 | 2013-08-08 | **−3,798** |
| proj143 2902 Adeline St | 2024-01-01 | 2022-05-18 | −593 |
| proj158 1367 University Ave | 2024-01-01 | 2023-03-13 | −294 |
| proj159 2403 San Pablo Ave | 2025-01-01 | 2024-05-06 | −240 |

All four have a Jan-1 filed date. A project entitled eleven years before it was filed is not a
rounding problem; it is a number that should never have been computed.

**Proposed fix (needs John's go-ahead — it changes a view and the served export).**
Surface `filed_date_precision` in `v_projects_flat`, and have the export refuse to compute
`processing_days` from anything but an exact date. Suppressing an unsupportable number is
better than publishing it: 13 projects lose a duration they never really had, and the other 42
keep one that means something. A negative duration must never be publishable regardless.

## Finding 2 — records whose description contradicts their own field

The check that caught People's Park, run across all 894 versions carrying a description:
parse every unit figure in the prose and compare with `total_units`, allowing for component
breakdowns that sum to the total, demolished units, and beds-versus-units.

Thirteen survive. Most are explainable and worth stating so:

- **proj165 2200 Bancroft** — 583 units vs 1,625 beds. Both correct; UC counts beds. Not an error.
- **proj905 2340 Fifth St** — the description covers "Building A" of three; 14 is the project.
- **proj120 2274 Shattuck (227 vs 299)**, **proj8 2920 Shattuck (221 vs 242)**, **proj121 2100
  Milvia (201 vs 205)** — prose names the base count and mentions a State Density Bonus, which
  raises it. The field is probably the approved figure and the description the application.
  Stale prose rather than a wrong number, but neither is sourced.

**One is a direct contradiction and is the strongest candidate for a real error:**

> **proj34, 2680 Bancroft Way.** `total_units = 79`. Its description reads: *"Conversion of the
> Bancroft Hotel into a residential building, with 15 dwelling units and 22 Group Living
> Accommodation rooms **for a total of 37 units**."*

The prose states a total explicitly, and it is not the field's. That is the People's Park shape
exactly — and there, the description was right. 2680 Bancroft has no source document, so this
needs a primary source (the use permit or the tabulation form) before either number is trusted.

## What this does not cover

Height and square-footage fields, affordability splits, and the `status_code`/stage
materialisation were not swept. The same reasoning applies to them: unsourced migration values
that nobody has checked.

## Recommendation, in order

1. **Stop publishing the four negative durations.** They are live and indefensible.
2. Expose date precision in the view so no consumer can mistake a year for a day.
3. Verify proj34 against its use permit.
4. Then decide whether the remaining 167 unsourced projects warrant a harvest campaign like
   the UC one, or whether it is enough to mark them low-confidence until something touches them.
