# Pencil-out, Phase A: the "Entitled 3+ yrs, inactive" cohort and what inputs we hold

2026-10-25 · read-only investigation · no DB writes, no notebook · for John's review before Phase B

## 1. The definition (used as is)

- Label on the home page: `docs/index.html:406` and `:536` ("Entitled 3+ yrs, inactive").
- The stage behind it is **`Entitled but Inactive`**, set in `scripts/export_explorer_data_v4.py:127-131`:
  v4 `v_projects.status = 'entitled'` AND `entitled_date < today − 1095 days` AND the latest dated event on
  any of the project's records (`v_project_timeline`) is also older than 1095 days (John, 2026-10-20).
- The cut is relative to the export date, so the list moves daily. This report uses the **published export,
  `docs/explorer_data.js`, generated 2026-10-20 15:31**. Re-running the export today could add projects
  approved 2023-10-21 through 2023-10-25.

**Result: 106 projects, 1,133 units.** 19 projects have 5 or more units (1,052 units); 57 have 1–4 units;
30 have 0 net units (additions, conversions). A pro forma only makes sense for the 19. The other 87 are
small infill and are left out of Phase B unless you say otherwise.

## 2. Before any finance: 5 of the 19 are not stalled entitlements (161 of the 1,052 units)

| Project (anchor) | Units | What the records show | Source |
|---|---:|---|---|
| 1740 San Pablo (ZP2017-0014) | 48 | Superseded by PLN2020-0049, 54-unit 100% affordable; BP B2022-05881 issued | v4 `v_projects`; CPRA permit row |
| 2510 Channing (ZP2017-0003) | 36 | Built as ZP2018-0061, 40 units, **Completed** (BP B2018-01337) | v4 `v_projects`; CPRA |
| 2542 Durant (ZP2016-0172) | 32 | Same parcel 055-1876-021-01 now ZP2022-0097 "2538 Durant", 83 units under construction | v4; assessor situs 2538 Durant |
| 3000 Shattuck (ZP2015-0229) | 23 | Replaced by ZP2022-0046, 166 units, entitled 2023 (parcel sold 2025-05-13) | v4; assessor |
| 2236 Channing (ZP2017-0015) | 22 | Office→3 units in an existing building; 22 is the building total, net new = 3 | planning description |

Three more need checking before they are evaluated:
- **1200 San Pablo (ZP2017-0191, 57u):** a later 104-unit approval at the same address (ZP2019-0192, entitled
  2020-11-12) is marked Withdrawn. Which approval is alive is unclear.
- **824 University (ZP2015-0021, 48u):** the parcel (situs 814 University) carries $16.5M of improvements and
  46,369 taxable sq ft, with an EV-charging permit in 2022. Either the entitlement covers part of an occupied
  site or something was built. Land basis is not usable until this is resolved.
- **1155 Hearst (ZP2016-0028, 18u):** a ZAB "APPROVED" action is dated 2025-06-12 (heading "Action Calendar"),
  which would make it active. It may be a minutes-parse misattribution. (Separately: zab_action rows under
  ZP2021-0210 carry headings "1235 Tenth Street" and "2000 San Pablo", and ZP2018-0112's carries "1835 San
  Pablo", so the `record_cited` mapping in `zab_actions_2026-10-06.jsonl` has some noise.)

These are project-identity errors in the build (successor projects not linked to the entitlement they
replaced), not something to patch here. Fixing them belongs to the projects stage of the v4 chain rebuild.

Unit counts that disagree with the City's own description: 2015 Blake 219 in v4 vs "155 + 6 = 168 units" in
the planning description; 1708 Harmon 80 vs 82.

## 3. Coverage table (the 19)

have = usable value in hand · partial = value exists but incomplete, in prose only, or needs aggregation ·
missing = no value. "derive" = construction type inferred from stories.

| Project | Units | Stories | Gross SF | Unit mix | Constr. type | BP valuation | Fees | Land basis | R2 drawings | Affordable / DB count | Status |
|---|---:|---|---|---|---|---|---|---|---|---|---|
| 2015 Blake | 219 (168?) | have 8 / 88 ft | missing | missing | derive (8 st: I or III/I, ambiguous) | missing | partial | partial | have (successor ZP2022-0178: tab form + 3 plan sets) | partial (DB, no count) | evaluate |
| 3031 Telegraph | 110 | have 6 / 69 ft | **have 98,338** | missing | derive | missing | partial | partial (condo common parcel = $0; 23 condo parcels to sum) | missing (2 listed on Accela) | partial (7 VLI, prose) | evaluate |
| 1835 San Pablo | 95 | have 6 | missing | missing | derive | missing | partial | have (AV $2.79M, sold 2018-04) | missing (0 listed) | partial (DB, no count) | evaluate |
| 1708 Harmon | 80 (82?) | have 5 | missing | missing | derive | missing | partial | partial (exempt, no transfer) | have (affordability form) | **have** (21 ELI + 58 VLI, A032) | 100% affordable: subsidy-gap model, not market |
| 1201 San Pablo | 66 | have 6 | missing | missing | derive | missing | partial | have (AV $1.25M, sold 2019-01) | missing (2 listed) | partial (5 VLI, prose) | evaluate |
| 1200 San Pablo | 57 | have 6 / 66 ft | missing | missing | derive | missing | missing | have (AV $2.55M, sold 2017-08) | missing (0 listed) | missing | identity check |
| 2198 San Pablo | 56 | have 6 | partial (in R2 tab forms) | partial (in R2 tab forms) | derive | missing | partial | have (AV $975k, sold 2020-02) | **have** (3 tab forms, 8 application sets, 2 plan sets) | missing | evaluate |
| 824 University | 48 | have 5 / 57 ft | missing | missing | derive | missing | partial | partial ($16.5M improvements on parcel) | missing (0 listed) | missing | identity check |
| 1740 San Pablo | 48 | — | — | — | — | — | — | — | — | — | superseded |
| 1820 San Pablo | 44 | have 5 (façade + 3 floors) | missing | missing | partial (façade retention) | missing | partial | have (AV $2.77M, **sold 2026-03-30**) | missing (6 listed incl. RESUB plans) | partial (4 VLI, prose) | evaluate |
| 2210 Harold | 38 | have 7 / 75 ft | missing (lot 5,953 sf in prose) | partial (135 bedrooms / 38 units, prose) | derive | missing | missing | partial (AV $1.18M, sold 2008: stale) | missing (0 listed) | missing | evaluate |
| 2435 Haste | 37 | have 8 | missing | missing | derive (8 st ambiguous) | missing | partial | partial (AV $499k, sold 1993: stale) | missing (4 listed incl. APP PKT) | partial (DB, no count) | evaluate (demolishes 8 units) |
| 2510 Channing | 36 | — | — | — | — | — | — | — | — | — | built |
| 2542 Durant | 32 | — | — | — | — | — | — | — | — | — | superseded |
| 3000 Shattuck | 23 | — | — | — | — | — | — | — | — | — | superseded |
| 2236 Channing | 22 | — | — | — | — | — | — | — | — | — | conversion, net 3 |
| 1155 Hearst | 18 | missing | missing | missing | missing | missing | partial | missing (no parcel linked) | missing (0 listed) | partial (DB: 5 bonus units) | identity check |
| 2018 Blake | 12 | have 6 | partial (in R2 tab forms) | partial (in R2 tab forms) | derive | missing | missing | have (AV $1.21M, sold 2021-11) | **have** (2 tab forms, 5 plan sets) | partial (1 VLI, prose) | evaluate |
| 1915 Berryman | 11 | have 4 | missing | missing | derive (Type V) | missing | missing | have (AV $2.27M incl. existing 3-unit bldg, sold 2022-03) | missing (0 listed) | partial (3 LI, prose) | evaluate |

Where each "have" lives:
- Units, stories, height, gross SF, parking: v4 `v_projects` (`proposed_units`, `height_stories`, `height_feet`,
  `building_sqft`, `parking_spaces`).
- Planning descriptions (prose counts): `events.raw_payload.description` on `planning_filed`; published as
  `description` in `docs/explorer_data.js`.
- Fees: v4 `v_projects.planning_fees_paid`. These are **planning-application fees only** (no BP, so no building
  or impact fees recorded). Impact fees (affordable-housing mitigation fee etc.) will have to come from the
  City fee schedule, which makes them an ASSUMPTION row, not a RECORD row.
- Land: v4 `assessed_values` (2026-02-01 roll) + `parcel_area`; transfer date from `berkeley.db.parcels.LatestDocumentDate`.
- Drawings: v4 `documents` (R2, `pub-2cee…r2.dev/architect_plans/…`); file names listed on Accela: `v_project_attachments`.
- Affordability: v4 `v_projects.affordability_evidence` (structure rulings) and `funding`.

Two inputs are missing for the whole cohort, by construction:
- **Declared construction valuation.** No BP was issued, and no BP application was found at any of the 19
  parcels in the CPRA rows (`JobValuation` checked on every `permit_submitted` / `permit_issued`).
- **Sale price.** No source holds one. The assessor gives the transfer *date* only. Under Prop 13 the land
  AV resets to the price at transfer, so AV is a fair basis for recent transfers (1820 SP 2026, 1915 Berryman
  2022, 2018 Blake 2021, 2198 SP 2020) and a stale one for old holdings (2435 Haste 1993, 2210 Harold 2008).

## 4. Recommendation

**Evaluable after one harvest: 11 market-rate / density-bonus projects (745 units, or 694 if 2015 Blake is 168).** 2015 Blake,
3031 Telegraph, 1835 SP, 1201 SP, 2198 SP, 1820 SP, 2210 Harold, 2435 Haste, 2018 Blake, 1915 Berryman, plus
1200 SP once its identity is settled. With the inputs held today only 3031 Telegraph has gross SF. Every other
project would have to estimate SF from units × an assumed unit size, which is the guess you said not to make.
As things stand, most would come out `insufficient_data`.

**1708 Harmon** (100% affordable senior, City HTF funding) needs a subsidy-gap model, not market NOI → residual
land value. It is not a "doesn't pencil" stall in the market sense.

**Out:** the 5 superseded, built or conversion projects (§2). 824 University and 1155 Hearst stay out until
their identity is resolved.

**Worth harvesting next, in order:**
1. **ZAB staff reports** for the approval hearings already in v4 `zab_action` (we hold the minutes, not the
   reports). Berkeley's staff report carries a project-data table: lot area, gross floor area, units by
   bedroom count, affordable units by tier, height, parking. One PDF per project fills gross SF, unit mix and
   affordable counts for all 11.
2. **Accela attachments already listed but not downloaded**: tabulation forms and APP PCKTs for 3031
   Telegraph, 2435 Haste, 1820 SP, 1201 SP, 2015 Blake. Then **list attachments** for the six 2015–2019
   records showing 0 (1835 SP, 1200 SP, 824 University, 2210 Harold, 1155 Hearst, 1915 Berryman). Following
   the harvester rule, an empty list is not proof of absence until retried.
3. **Read the R2 tabulation forms we already hold** (2198 SP, 2018 Blake, 2015 Blake successor). No harvest
   needed.
4. **Assessor polygons for the 3031 Telegraph condo parcels and the 2015 Blake merged site**, summed for land
   basis.

**A record-derived cost cross-check for Phase B.** Declared `JobValuation` on *issued* BPs for comparable
5–8 story Berkeley buildings is a RECORD benchmark to set beside the Terner hard-cost assumptions (e.g.
2538 Durant B2023-02332: $16.44M / 83 units; 1740 SP B2022-05881: $11.55M / 54 units). Permit valuations
usually understate true hard cost, so this would be a floor, not a replacement.

**Existing work to reuse:** `05_feasibility/F2_pro_forma_transparent.ipynb` already has a Terner-based
podium pro forma and a Berkeley land-value surface from recent-transfer AVs (2026-09-08). Phase B's
assumptions file should take its values from there with their citations, not start over.
