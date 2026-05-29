# CY 2024 Reconciliation Ledger

Row-level bijection between Berkeley's CY 2024 HCD Table A2 
submission (228 rows, 708 CO units, 731 BP units) and D5's CY 2024 
output derived from Berkeley's CPRA-released building permit data 
(1,156 master permits).

Constructed 2026-05-28. See docs/audit/2026-05-28_adu_diagnostic.md
for the bug fix that preceded this construction. Session context 
in docs/audit/2026-05-28_session_summary.md.

## Files

- `matched_pairs.csv` (182 rows): HCD rows matched to D5 permits.
  Columns include match_tier (tier_1_tracking_id or 
  tier_2_apn_current/tier_2_apn_prior), units_agree flags, and 
  side-by-side unit counts.

- `h_unmatched_t2.csv` (8 rows): HCD rows with no CPRA building
  permit presence in any year. All carry zero permitted units
  (entitlement-stage ZP/PLN tracking IDs).

- `c_unmatched_t2.csv` (974 rows): D5 CY 2024 master permits with
  no HCD CY 2024 match. Contains the 4 confirmed under-reports
  (2328 Channing Way, 2512 Regent St, 2028 Essex St, 707 Cragmont
  Ave) plus other CPRA permits not in Berkeley's HCD submission.

## Unit accounting

Berkeley's HCD CY 2024 Table A2 submission contains 708 net CO
units and 731 net BP units. The bijection accounts for these as:

| bucket                    | CO  | BP  |
|---------------------------|-----|-----|
| Tier 1 tracking ID match  | 534 | 695 |
| Tier 2 APN match into C_1 | 166 | 4   |
| multi-row same APN CY2024 | 2   | 28  |
| year-shifted              | 6   | 4   |
| no CPRA presence          | 0   | 0   |
| **total**                 | 708 | 731 |

The 28 BP units in "multi-row same APN" are the parcel-collapse
undercount in D5: HCD splits multi-structure parcels into separate
rows; D5 collapses to one master and reports only its units.
Examples: 805 Jones (3 structures, 2 units each), 2421 Fifth 
(2 structures), 1330 and 1340 Haskell (2 structures each). 
Structural bug for future fix.

## Construction methodology

The bijection is constructed in two iterations:

**Tier 1: tracking ID equality.** HCD's Local Jurisdiction Tracking 
ID matched against D5's permit number, with normalization for 
prefix (B-, ZP-, PLN-), case, and whitespace. 174 of 228 HCD rows 
matched in Tier 1.

**Tier 2: APN equality.** Remaining 54 HCD rows matched first by 
current APN, then by prior APN, against the full CPRA permit corpus
(32,202 rows across all years). 8 of 54 matched into D5's CY 2024 
output (1951 Shattuck via B2021-04893 → B2019-05608 contributing 
163 CO units is the canonical recovery). Remaining 46 split into:
- 20 multi-row same APN in D5 CY 2024 (parcel-collapse residual)
- 18 with CPRA presence in another year (year-routing divergence)
- 8 with no CPRA building permit presence anywhere (entitlement-stage)

## Limitations

- HCD reports affordability tier breakdowns (7 columns per stage);
  D5 produces totals only. Tier breakdowns require ABAG 30/30/30/10
  distribution for ADUs and deed-restriction tracking from planning
  records (deferred).
- D5's year-routing uses BP issuance year; HCD's may use 
  entitlement year. The 6 CO / 4 BP year-shifted units reflect 
  this divergence. Convention decision deferred.
- Causes 2 and 3 from the REV diagnostic (Alteration/Demolition 
  cumulative UnitsRemoved, over-broad ADU parcel-flag 
  classification) are not addressed in current D5 output. They 
  affect d5_only set composition but not bijection cardinality.

## Reproducibility

The construction is mechanical. From the HCD mirror and CPRA permit
corpus, the matching is well-defined per the tiered rules above.
The matched_pairs.csv preserves the match_tier column, so each pair
can be re-derived independently.

Future iterations may add Tier 3 (prior APN with cross-year 
search), Tier 4 (fuzzy address with street-number-exact gating), 
and may extend to other CY years. Each iteration must remain 
injective: no HCD row mapped to two CPRA permits, no CPRA permit 
reused.
