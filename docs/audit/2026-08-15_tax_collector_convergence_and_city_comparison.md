# Why Berkeley's property taxes rose in FY2025-26 — our reconstruction and the County Tax Collector's, compared

**Date:** 2026-08-15 · **Status:** analytical record, supports the Berkeley-2050 / Measure U work
**Code:** `scripts/tax_incidence/` · **Derived data:** `data/derived/berkeley_parcel_tax_rate_schedule_2025-26.json`, `data/derived/berkeley_sfr_tax_by_decile_2025-26.csv` · **Raw:** `data/raw/alameda_tax_rates_2025.json`
**Companion:** `docs/methodology/berkeley_property_tax_structure.md` (method), `notes/2026-08-15_bond_measure_u_city_claims_incidence_v2050.md` (measure analysis)

---

## 1. Two independent reconstructions, same answer

Alameda County Tax Collector Henry C. Levy published a blog, *"City of Berkeley Taxes: Why the Increase?"*, after Berkeley residents complained about their October bills. He worked from **9 parcels** — his own home, two friends', and six APNs volunteered on Nextdoor — and says plainly that it is not a significant sample.

We worked from **37 parcels** drawn by stratified sample across the assessed-value distribution and two lot-size bands, plus a 12-year series for one parcel, plus a model over **16,910 single-family parcels**. Neither effort knew about the other; we found his blog only after deriving the rate schedule.

The two agree on every point where they overlap.

| Finding | Tax Collector (n=9) | This analysis (n=37 + 16,910 modelled) |
|---|---|---|
| BSEP rate | "$0.54 per square foot" | $0.54000 — derived by ratio test, then anchored |
| City parks/landscaping rate | "26.5 cents/sq. foot" | $0.265202 derived independently |
| What the special assessments are levied on | "virtually all special assessments are based on square footage" | 11 of 26 charges share one base with **CV < 0.0022**; anchor reproduces City taxable sqft **exactly on 35 of 37 parcels** |
| Cause of the increase | two Nov-2024 measures + BSEP | `STREET REPAIR 2024` + `LIBRARY RELIEF2024` = $1,659 of a $2,582 one-year rise on the 12-year parcel (64%) |
| Ad-valorem change | "+4.5% for everyone in my sample" | 1.2033% → 1.2323%, +2.4% rate on top of AV growth |
| City GO bond rate | "decreased by 18%" | 0.0609% → 0.0490%, **−19.5%** |
| School bond rate | "increased by 50%" | 0.0780% → 0.1154%, **+47.9%** |
| Who is hit hardest by the rise | "those with larger houses will see their taxes increase faster" | parcel taxes track building size, p90/p10 = 2.8× on sqft, independent of value |

**Where we add something he could not.** His nine parcels were all long-held owners — he says so, and notes that "for a more recent buyer of property... they will likely not experience such a sharp increase this year." Our sample was deliberately stratified across the assessed-value range, so it measures the thing his sample could not: how the burden is distributed, not just how it moved. That is what produces §3 below.

**Where he adds something we could not.** He states that Berkeley taxpayers carry **29 special assessments, more than any other taxpayer in Alameda County**. That is a countywide comparison available to the Tax Collector's office and not reproducible from Berkeley bills alone. We cite it; we do not re-derive it.

**Why the convergence matters for publication.** The rate schedule in this repo was derived from bills with no prior knowledge of any published rate — the ratio test finds which charges share a base, and a single external anchor converts it to dollars. That two of the resulting rates match a sitting county official's independently published figures, and that the implied square footages match the City's own database to the square foot, means the method is not merely internally consistent. A campaign cannot dismiss it as modelling.

---

## 2. Berkeley versus the other 13 Alameda County cities

From `data/raw/alameda_tax_rates_2025.json` (county TRA table, FY2025-26, all 10,000 rate rows; figures are the modal TRA per city, dollars per $100,000 of assessed value).

| City | Total ad valorem | City's own GO levy | Schools |
|---|---|---|---|
| Albany | $1,357 | **$124.50** | $164.70 |
| Oakland | $1,278 | **$120.00** | $90.00 |
| San Leandro | $1,244 | $0 | $180.00 |
| Dublin | $1,238 | $0 | $152.40 |
| **Berkeley** | **$1,232** | **$49.00** | $115.40 |
| Union City | $1,262 | $0 | $170.70 |
| Alameda | $1,213 | $20.00 | $124.80 |
| Piedmont | $1,180 | $20.20 | $91.70 |
| Fremont | $1,174 | $3.20 | $90.80 |
| Hayward | $1,172 | $0 | $90.00 |
| Pleasanton | $1,169 | $0 | $83.30 |
| Emeryville | $1,166 | $47.30 | $51.30 |
| Newark | $1,149 | $0 | $69.10 |
| Livermore | $1,132 | $0 | $47.50 |

**Seven of fourteen Alameda cities levy no city GO bond tax at all.** Berkeley is third of fourteen on its own GO levy, and sixth on total ad valorem.

### The city's C10 claim is accurate — and that is the point

Berkeley's staff materials compare "Berkeley FY26 cumulative GO bond tax $270 vs Oakland $660, Albany $685." Check the ratios against the county's own table:

- Oakland ÷ Berkeley: city says 660/270 = **2.44**; county data says 120.00/49.00 = **2.45**
- Albany ÷ Berkeley: city says 685/270 = **2.54**; county data says 124.50/49.00 = **2.54**

The claim is arithmetically correct, and the $270 implies a benchmark assessed value near $551,000. **Do not attack it as false.** It is true.

The response is that it measures one channel. Berkeley's GO rate is low because Berkeley has financed through **parcel taxes instead of general obligation bonds** — the channel the comparison omits, and the channel in which the County Tax Collector says Berkeley leads all 14 cities with 29 separate assessments. On a real FY2025-26 Berkeley bill the city's own GO levy is $357 while city-levied parcel taxes are $7,045.

So: *Berkeley's GO bond burden is genuinely mid-pack. Berkeley's total local tax burden is not. The measure now proposes to grow the one channel where Berkeley looks restrained, using a comparison that is silent about the channel where it does not.* That is a fair reading, it concedes the city's arithmetic, and it is much harder to rebut than a claim that the numbers are wrong.

---

## 3. What the stratified sample adds: dispersion

Modelled across 16,910 single-family parcels (99.8% of the SFR universe joined to City taxable square footage):

| | p90/p10 spread |
|---|---|
| Assessed value | 14.6× |
| Ad-valorem tax | 14.6× |
| **Parcel taxes** | **2.8×** |
| **Total tax bill** | **5.3×** |

Median houses in deciles 1 through 9 are all roughly 1,600–2,000 sqft and all pay **$3,300–$4,200/yr in parcel taxes regardless of assessed value.** Decile 1 pays 77% of its bill that way; decile 10 pays 18%.

Berkeley's flat layer therefore **compresses** the Prop 13 disparity from 14.6× to 5.3×. **Measure U, being purely ad valorem, is levied entirely on the 14.6× layer.** After a decade of financing through the compressed channel, the city proposes to expand the dispersed one — which widens the spread of who pays rather than tracking it.

### Honesty rails (carry into any published use)

- **"Regressive with respect to assessed value" is not regressive with respect to wealth.** Decile 1's 5.55%-of-AV effective rate is high because AV is frozen by Prop 13 vintage, not because those households are poor. Measured against *market* value the direction reverses. State the denominator explicitly.
- **Single-family only.** Apartments (22.3% of the bond in the companion note) have a different structure and renters bear it via pass-through.
- **All totals are a lower bound** by roughly $1,170/parcel — about 12 charges (EBMUD wet weather, storm water, vector/mosquito) sit on a third base we have not modelled.
- **The advertised $22.14/$100k is a quotient, not a price.** Debt service is fixed; the rate is debt service ÷ assessed base. Run it across the 12-year parcel history and the same obligation costs $90–$230/yr, a 2.55× swing, because the base fell in three of eleven years — once by 23%.

---

## 4. Sources

- Alameda County Tax Collector, *"City of Berkeley Taxes: Why the Increase?"* — https://treasurer.acgov.org/wp-content/uploads/2025/12/Berkeley-Taxes-2025-26.pdf
- Alameda County property tax portal (bills) — https://propertytax.alamedacountyca.gov/
- Alameda County Open Data, Property Tax Rates 2025 (TRA table) — https://data.acgov.org/datasets/8a6a0187bf3148b5a180c4bf6aad8f01_0/about
- City of Berkeley, Taxable Square Footage — https://data.cityofberkeley.info/City-Government/Taxable-Square-Footage/9a47-nj4i
- BUSD Measure H (2024) FAQ, $0.54/sqft — https://www.berkeleyschools.net/bsep-measure-h-frequently-asked-questions/
- Alameda County Auditor-Controller, prior-year tax rate books — https://apps.acgov.org/auditor/tax/ratebooks.htm
