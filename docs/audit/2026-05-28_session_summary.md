# Session Summary — 2026-05-28

## Starting state

The continuation prompt for this session described yesterday's work
as including an ADU unit-counting bug fix and a scope filter on D5,
both nominally completed. Pre-session verification of the git log
revealed HEAD at 85f95f3 ("notes(hcd): document HCD mirror table
coverage gaps"), with no commits after for the claimed fixes. Per
the project discipline rule "CC summaries can be wrong; verify
artifacts," the session began with the recognition that both fixes
were pending, not landed.

## What was diagnosed

See `docs/audit/2026-05-28_adu_diagnostic.md` for the full technical
diagnostic. In summary: four issues, three causally connected:

- Cause 1 (primary, fixed): REV cumulative-vs-marginal summation
- Cause 2 (deferred): Alteration/Demolition master cumulative UnitsRemoved
- Cause 3 (deferred): Over-broad ADU parcel-flag classification
- Q5 (separate workstream): ABAG income-tier methodology gap

## What was fixed

Cause 1 fix: master-only co_units aggregation. Verified across all
56 CY 2024 masters with ≥2 finaled REVs that Berkeley's data
convention is cumulative restatement on every family row including
the master. Smoke tests passed exactly. Cross-year impact
concentrated in CY 2024 (−6,001 net co_units) and CY 2025 (−5,233);
older cycles essentially unchanged.

Commits:
- df17e7a: docs(audit): add ADU/REV diagnostic for 2026-05-28 session
- 22c5864: fix(d5): correct cumulative-restatement REV summation in co_units

Both on dev, not pushed at session close.

## What was built (new artifact)

A row-level bijection between Berkeley's CY 2024 HCD Table A2
submission (228 rows) and D5's CY 2024 output (1,156 master permits).

Construction in two tiers:
- Tier 1 (tracking ID equality): 174 HCD rows matched
- Tier 2 (APN equality, current then prior): 8 more matched
- Final: 182 matched HCD rows, 8 truly unmatched (all zero-unit
  entitlement-stage tracking IDs)

Unit accounting (every HCD unit located):

| bucket                    | CO  | BP  |
|---------------------------|-----|-----|
| Tier 1 tracking ID match  | 534 | 695 |
| Tier 2 APN match into C_1 | 166 | 4   |
| Multi-row same APN CY2024 | 2   | 28  |
| Year-shifted to other CY  | 6   | 4   |
| No CPRA presence anywhere | 0   | 0   |
| **total**                 | 708 | 731 |

Artifacts saved at `data/audit/cy2024_reconciliation/`.

## What was identified for later fix

**Parcel-collapse undercounting in D5 (28 BP units in CY 2024).**
When a parcel has multiple independent New-construction permits
(separate structures, not REV/DEF children of one master), D5's
one-master-per-parcel grouping keeps only the highest-units master
and demotes siblings. Examples: 805 Jones (3 structures, 2 units
each), 2421 Fifth (2 structures), 1330/1340 Haskell (2 structures
each). Structural limit of grouping logic; separate fix workstream.

**Year-routing convention divergence.** D5 routes by BP issuance
year; HCD evidently uses entitlement year. Effect: 6 CO and 4 BP
units in CY 2024 land in adjacent years in D5. Small in absolute
terms but methodologically important. Convention decision deferred.

**4 confirmed under-reports (23 net units).** From D5's CY 2024
output, 4 specific permits appear in CPRA-released data but do not
appear in any year of Berkeley's HCD submission:

- 2328 Channing Way (12 units, 5+ category)
- 2512 Regent Street (9 units, 5+ category, CO-only)
- 2028 Essex Street (1 unit, ADU)
- 707 Cragmont Avenue (1 unit, SFD, CO-only)

Confirmed via tracking ID, APN, and address cross-checks. Persist
in the c_unmatched_t2 residual set.

## What was verified about prior work

**v1's `scripts/generate_apr.py`** runs cleanly today against
`databases/berkeley_housing_analysis.db` (1.18 MB, modified 2026-05-
03). It produces a 21-project highlight reel: 786 CO units (5
projects), 550 BP units (7 projects), 945 entitled units (9
projects). The apparent closeness of 786 to HCD's 708 is partly
coincidental — v1 includes 1950 Oxford (300 units, RHNA-exempt UC
project) that Berkeley excludes from its submission; subtracting
that gives 486, similar to D5's 497. v1 is a curated-projects
tracking tool, not a row-level APR reproduction tool.

**The published `methodology.html`** at berkeleybuild.com (committed
2026-04-23, last redeployed 2026-05-27) is a qualitative framing
page. It carries no specific quantitative claims, no reference to
the 97.4% match described in earlier conversational records, and no
mention of v1, v2, D5, CPRA, or specific unit counts. The page
describes the project's approach with appropriate caveats.

**The published CY 2025 Citizen APR** (April 2026, distributed to
~50 recipients) stands as published. It described Berkeley's
housing pipeline: 169 projects, 11,235 units, 12.4% RHNA progress,
$14.1M fees. Today's work does not change or supersede this
publication; it builds a complementary audit layer.

**CY 2025 CPRA coverage** is complete: 4,195 issued permits and
3,689 finaled permits in CY 2025, distributed across all 12 months,
no taper at year-end. The April 2026 CPRA fulfillment captured the
entire calendar year. CY 2025 bijection construction is feasible
whenever scheduled; no new CPRA request blocks it.

## What was NOT changed

- No commits to main (dev only)
- No website deploy
- No edits to docs/methodology.html
- The published CY 2025 Citizen APR stands as it was published
- The Explorer and Map remain on v1-derived data

## Discipline rules that earned their keep today

- "CC summaries can be wrong; verify artifacts" — caught at session
  start; the claimed REV fix wasn't actually committed
- "Phase A before Phase B" — read-only diagnostic produced the data
  that made the Cause 1 fix decision clean
- "Triangulate ground truth" — Berkeley PDF (NotebookLM), HCD mirror,
  and HCD CKAN API all agreed exactly on 708 CO / 731 BP
- "conversation_search before reconstructing context" — applied
  belatedly when prompted; revealed the published CY 2025 Citizen
  APR and v1's actual scope, both initially missed
- "Pre-flight check before commit" — CC caught a dangling reference
  to a not-yet-written diagnostic doc and stopped the commit until
  the doc landed first

## Outstanding work — captured for future sessions

- Methodology page update describing audit layer (drafted, not deployed)
- Parcel-collapse fix in D5 (28 BP units quantified, larger in CY 2025)
- Year-routing convention decision and documentation
- Causes 2 and 3 fixes (Work Type filter on ADU classification)
- ABAG ADU income-tier distribution (Q5)
- CY 2025 bijection construction (CPRA coverage verified complete)
- v2 cutover (Datasette serving v2 directly — separate multi-week workstream)
- Collateral writes from today's verification runs need cleanup:
  - data/apr/2024/*.csv, apr_2024.json (from v1 generate_apr.py run)
  - 04_reporting/D6_diff_d5_vs_hcd.ipynb (prior Phase B rerun output)
  - Untracked: 2026-05-28.md, data/apr/2024/developer_summary_2024.csv,
    notes/cc_prompts/

## Next session priorities

See `docs/audit/2026-05-28_next_session_priming.md`.
