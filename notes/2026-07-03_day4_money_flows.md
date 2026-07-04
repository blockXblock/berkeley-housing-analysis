# Day 4 — Money flows to the city: fees, then taxes (mayor-prep)

Frame: **a building pays the city once at the counter, then every year after completion.**
Everything below is derived from primary data on disk (CPRA valuations, current assessor roll)
except where marked MODELED or ACQUISITION. The city's budget open dataset is expenses-only and
ends FY2016 — no revenue lines (another portal-quality exhibit); fee/tax-share actuals are in
CPRA Request 1–2.

## One-time: the counter (permit + plan-check fees)

- **Permitted construction valuation (real, from the feed, base permits by issuance year):**
  2018 $190M · 2019 $208M · 2020 $280M · 2021 $292M · **2022 $338M (peak)** · 2023 $260M ·
  2024 $218M · 2025 $223M. Berkeley permits roughly **a quarter-billion dollars of construction a
  year**, and fees are a formula on this base (Master Fee Schedule).
- MODELED, clearly labeled: at an illustrative 2% effective fee rate that's **$4–7M/yr** in
  building fees; the actual rate/actuals arrive with the CPRA fee ledger. The deck shows the
  valuation series (real) with the fee line flagged as modeled-pending-actuals.
- Caveat: valuations are *declared* — ADU permits show a median declared valuation of just
  $10,000 (garage conversions, lowballing) — so fee revenue skews almost entirely to the big
  projects.

## Recurring: the roll (property tax, forever after completion)

- **The 40+ unit completions since 2018 alone added $857M of assessed improvements** to the
  current roll (27 of 30 matched at parcel prefix). At the 1% base levy that is **≥$8.6M/year of
  new property tax, every year** — before parcel taxes, before land-value growth, before
  turnover.
- Specimens for the deck: 2580 Bancroft **$137.6M** · 1500 San Pablo **$85.8M** · 1951 Shattuck
  **$70.4M** (≈$704k/yr at 1% from one building) · 2150 Kittredge $60.2M · 2035 Blake $60.1M.
- **The $0 rows are honest, and both mechanisms are documented:** (1) *reassessment lag* — 2025–26
  completions (3030 Telegraph, 2001 Ashby) not yet posted (the 1–2 year lag we verified on
  proj136); (2) **welfare exemption** — nonprofit affordable projects (2012 Berkeley Way) pay no
  property tax by design: *affordable housing pays in homes, not taxes* — worth saying out loud
  in the deck. Both mean $8.6M/yr is an UNDERCOUNT of the eventual market-rate flow.
- **Parcel taxes (mechanism, ACQUISITION for rates):** Berkeley's voter-approved parcel taxes
  (library, parks, EMS, schools) are per-square-foot — every new square foot pays them annually;
  exact per-building figures once the current rate schedule + taxable-sqft join is done (the
  portal's Taxable Square Footage dataset is the base).
- **Transfer tax (mechanism):** among the state's highest municipal transfer taxes (≈1.5%, 2.5%
  above the Measure P threshold — rates to be confirmed against the current code before the deck
  quotes them); hits at first sale and every turnover.

## The contrast slide: a tower vs an ADU

- **1951 Shattuck (163u):** ~$70.4M assessed improvements → ≈$704k/yr at the 1% base alone, plus
  parcel taxes on the whole envelope, plus fees on a large declared valuation.
- **A median ADU:** declared valuation $10k → trivial fees; assessed increment small →
  tens-to-hundreds of $/yr.
- **Reading it honestly, both directions:** towers fund the city (a corridor building ≈ a
  thousand ADUs, fiscally); ADUs add homes at near-zero fiscal footprint AND near-zero commercial
  impact. Different instruments for different goals — the fiscal case and the neighborhood case
  point at different lanes, which is exactly why a portfolio (corridor + fabric) beats either
  simplistic story.

## Reconciliation targets (the oracle discipline, money edition)

1. CPRA fee ledger (Request 1/2) vs the modeled fee line — the modeled number gets replaced or
   graded.
2. City budget revenue actuals (permit revenue line; property-tax receipts) vs the derived
   series — the budget becomes the oracle, same method as the APR.
3. County AB-8 allocation: the City's actual share of the 1% levy (ACQUISITION — do not invent).
