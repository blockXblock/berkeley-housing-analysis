# Berkeley Housing Pipeline — Project History

Maintained as a single-document narrative of the project from
inception through the present. Intended as orientation for future
sessions (human and Claude) so accumulated context isn't
reconstructed midstream.

## Early 2026: Foundation

Reverse-engineered the City of Berkeley's APR PDF structure
(Tables A, A2, B, C, D). Identified building permits and
Certificates of Occupancy as critical missing data: at this stage,
the project had primarily zoning/planning data. Built the Accela
permit scraping pipeline. Created v1 flat SQLite at
`databases/berkeley_housing_analysis.db` with 174 projects, ~54
columns.

## March-April 2026: First Citizen APR

`scripts/generate_apr.py` produced HCD-format tables from v1's
curated projects:
- Table A (applications complete)
- Table A2 (permitted projects with activity)
- Table B (RHNA progress)

A project-by-project comparison was done against Berkeley's
CY 2024 published APR. The conversational record described the
match as "97.4% accuracy," and specific City errors were flagged
(2029 University double-count, 2425 Durant unit mismatch, others).
The exact methodology and source of the 97.4% figure are not
preserved in any artifact reviewed in the 2026-05-28 session.

What v1 actually produces (verified 2026-05-28):
- CO units: 786 across 5 projects
- BP units: 550 across 7 projects
- Entitled units: 945 across 9 projects

The apparent closeness to HCD's 708 CO is partly an artifact —
v1 includes 1950 Oxford (300 units, RHNA-exempt UC project) that
Berkeley excludes from its submission. v1 is a curated-projects
tracking tool, not a row-level APR reproduction tool.

## April 2026: CY 2025 City APR Comparison

City published CY 2025 APR on 2026-03-27. Project-by-project
comparison surfaced:
- 15 projects in our data not in City's
- 18 projects in City's not in ours (including 1974 Shattuck
  599 units, 2274 Shattuck 227 units, 2100 Milvia 201 units —
  large projects missed)
- Our VLI capture was 18% (the City had density bonus covenants
  we didn't track)

After adding 5 missing major projects (2650 Telegraph, 2000 Dwight,
2440 Shattuck, 1773 Oxford, 1698 University), RHNA credit moved
12.4% → 15.0% (City's: 23.7%). Remaining gap was mostly ADUs and
small projects.

## April 2026: CY 2025 Citizen APR Published

Distributed to ~50 recipients (Possibility Lab, Terner Center,
Berkeleyside, City Council, City Staff, UC Berkeley researchers,
Daily Cal, SFYimby, community organizations). Headline numbers:

- 169 projects, 11,235 units in pipeline
- 12.4% RHNA progress
- $14.1M fees across 121 projects

Live tools went up at blockxblock.github.io:
- `explorer.html` — project explorer with filtering
- `map.html` — geographic visualization
- Downloadable HCD-format spreadsheets

Headline finding: 11,235 units in pipeline (126% of RHNA) but only
1,110 with building permits — entitlement-to-construction gap is
the primary bottleneck.

## Late April 2026: v2 Schema Designed

Normalized v2 designed and migrated:
- 34 core tables, 18 vocabulary tables, 9 backward-compat views, 36 indexes
- Vocabulary tables replacing hardcoded enums
- Provenance mixin (source_document_id, asserted_by, asserted_at,
  confidence_type_id) on fact-bearing tables
- GeoJSON-as-TEXT for portability
- Compat views (`v_projects_flat`) for v1 backward compatibility

174 projects migrated to `berkeley_housing_v2.db`. The
`methodology.html` page was published to berkeleybuild.com on
2026-04-23 — a qualitative framing page with no specific
quantitative claims.

## May 2026: CPRA Era Begins

Two CPRA requests fulfilled by City of Berkeley:
- ~2026-04-20: `BP_Annual Permit Report-2023-2025.xlsx` (14,149
  rows, covering CY 2023-2025)
- 2026-05-20 (NextRequest 26-1368): `BP_Annual Permit Report-
  2018-2022.xlsx` (18,053 rows)

Joint corpus: 32,202 rows / 30,764 unique permits / 1,430
overlapping. This is an order-of-magnitude expansion beyond v1's
174 curated projects. CPRA files first committed to git
2026-05-26 (cb4ad7d).

## Mid-May 2026: Pipeline Regression Discovered

2026-05-20: `scripts/generate_apr.py` discovered pointing at
zero-byte `data/berkeley_housing_analysis.db`. Actual v1 database
is at `databases/berkeley_housing_analysis.db`. The script had
been silently broken for unknown duration.

v2 migration in progress but cutover deferred. Website
(`explorer.html`) continued running on `explorer_data.js`
generated from v1.

## Mid-Late May 2026: D5/D6 Layer Built

A new layer of analytical notebooks built to consume the CPRA
permit stream directly:

- `04_reporting/D5_apr_from_cpra.ipynb`: produces Table A2 from
  CPRA permits, year by year
- `04_reporting/D6_diff_d5_vs_hcd.ipynb`: diffs D5 output against
  the HCD mirror

HCD mirror built via `scripts/build_hcd_mirror.py` against the
California Open Data Portal's HCD APR dataset.

2026-05-27: cycle-aware classifiers added (`scripts/housing_rules/`
package). Cycle-aware columns in D5 (`bp_cycle`, `co_cycle`,
`bp_in_projection_period`, `co_in_projection_period`).
Cycle-segmented analysis in D6.

## 2026-05-28: REV Bug Fix + Bijection Construction

See `docs/audit/2026-05-28_session_summary.md` for full session
detail.

Key outcomes:
- REV cumulative-restatement summation bug fixed (commits df17e7a,
  22c5864 on dev)
- Row-level bijection between Berkeley's CY 2024 HCD Table A2 and
  D5's CY 2024 output constructed
- 100% of HCD's 708 CO and 731 BP units accounted for across
  classified categories
- 4 confirmed CY 2024 under-reports persist after fix
- Parcel-collapse undercounting identified for future fix
- CY 2025 CPRA coverage verified complete

## Architecture as of 2026-05-28

Three layers coexist with different purposes:

**v1 (curated projects layer)** — `databases/berkeley_housing_
analysis.db`, 174 hand-curated projects. `generate_apr.py` produces
a 21-project highlight reel. Source of `explorer_data.js` for the
live website. Not an APR reproduction tool; a project tracking tool.

**v2 (normalized canonical schema)** — `berkeley_housing_v2.db`,
34 tables. Designed for serving via Datasette directly. Pre-cutover;
the website still runs on v1-derived data.

**D5/D6/bijection (audit layer)** — Jupyter notebooks consuming the
raw CPRA permit stream (32,202 rows). Produces row-level
reconciliation ledger against HCD. New as of 2026-05-28.

The three layers will eventually consolidate when v2 cuts over,
with D5/D6 logic moving into v2 views and Datasette queries.
That cutover is a multi-week separate workstream.

## Outstanding work (snapshot at 2026-05-28)

- Methodology page update describing audit layer
- Parcel-collapse fix in D5 (28 BP units quantified for CY 2024)
- Year-routing convention decision
- Causes 2 and 3 fixes (Work Type filter on ADU classification)
- ABAG ADU income-tier distribution (Q5)
- CY 2025 bijection construction
- v2 cutover to Datasette

## Published artifacts (current as of 2026-05-28)

- `berkeleybuild.com/methodology.html` (April 2026, qualitative
  framing, no quantitative claims)
- `berkeleybuild.com/explorer.html` (live, v1-derived data)
- `berkeleybuild.com/map.html` (live)
- CY 2025 Citizen APR distributed to ~50 recipients (April 2026)

## Discipline rules in active use

- "CC summaries can be wrong; verify artifacts"
- "Phase A (read-only) before Phase B (execute)"
- "conversation_search before reconstructing context"
- "Never push to main without explicit instruction"
- "Pre-flight check before commit"
- "Triangulate ground truth"
- "Don't extrapolate from single cases to column totals without
  row-level data support"
