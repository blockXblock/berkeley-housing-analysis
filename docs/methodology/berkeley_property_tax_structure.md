# Berkeley property tax structure — the two layers, and how to reconstruct the hidden one

**Durable methodology.** First derived 2026-08-15; code in `scripts/tax_incidence/`.
Dated findings live in `docs/audit/2026-08-15_tax_collector_convergence_and_city_comparison.md`.

## The structure

A Berkeley secured property tax bill has two layers that behave completely differently.

**Layer 1 — ad valorem.** 1.2323% of net assessed value in FY2025-26: the Prop 13 base 1%
plus six voter-approved debt levies. **All six Berkeley TRAs (13-0 … 13-5) carry identical
rates**, so Berkeley is rate-uniform and no parcel→TRA join is needed. Published per TRA by
the county; needs no derivation. `data/raw/alameda_tax_rates_2025.json`.

**Layer 2 — fixed charges.** 26+ separately legislated parcel taxes, **the majority of a
typical Berkeley bill** (57% on the reference parcel). Appears in **no dataset**. Levied on
three different bases:

| base | n (FY2025-26) | total |
|---|---|---|
| per sqft of improvements | 11 | $1.93635/sqft |
| flat per parcel | 6 | $192.52 |
| per dwelling unit | 3 | $55.12/unit |
| some other base — not modelled | ~12 | ~$1,170 median |

## Reconstructing layer 2 without knowing any rate

1. **Flat vs varying.** A charge identical on every sampled parcel is flat-per-parcel.
2. **Ratio test.** If charges A and B are both `rate_i × sqft`, then `A/B` is the *same
   constant on every parcel* whatever sqft is. Group by pairwise-ratio stability; CV < 0.02
   means a shared base. This finds the per-sqft family **with no rate known**, and
   simultaneously excludes charges on some other base. In practice the family separates
   cleanly: CV < 0.0022 for all 11 members, versus > 0.34 for every non-member.
3. **Anchor.** One published rate converts to absolute units. BSEP Measure H (2024) levies
   $0.54/sqft of improvements from 2025-07-01, so `sqft = BSEP_charge / 0.54`.
4. **Validate.** The anchor predicts each parcel's building square footage. Check against the
   **City of Berkeley Taxable Square Footage** dataset (`data.cityofberkeley.info` 9a47-nj4i,
   29,167 rows) — independent, and the source the City is bound by charter to use for these
   assessments. Result: **35/37 exact to the square foot.**

### Separating per-unit from flat requires a multi-unit parcel

Charges levied per *dwelling unit* are indistinguishable from flat-per-parcel in an
all-single-unit sample. They were only identified because the reference parcel (53-1695-26,
assessor UseCode **1150** = single family *with a second unit*) pays exactly 2× on CSA
Paramedic, Haz Waste and Vector Control. **Confidence is LOW — one observation.** Sample
duplexes to confirm before relying on the per-unit split.

## Why this matters analytically

The two layers distribute burden in opposite directions:

- **Assessed value** spans **14.6×** p90/p10 across Berkeley single-family homes, because
  under Prop 13 AV ≈ purchase price × 1.02^(years since reassessment). AV *is* the Prop 13
  clock.
- **Parcel taxes** span only **2.8×**, because they track *building size*, not purchase date.
- **Total tax** therefore spans **5.3×** — the flat layer compresses the Prop 13 disparity.

Any measure levied purely ad valorem lands entirely on the 14.6× layer and widens dispersion.
Any parcel tax lands on the 2.8× layer and compresses it. **This is the single most important
structural fact for evaluating a Berkeley revenue measure**, and it is invisible unless the
fixed-charge layer is reconstructed.

## Traps

- **`LatestDocumentDate` is NOT tenure.** It is last-recorded-*document* recency; refinances
  and liens reset it with no change of owner. Empirically: mean AV by document year shows
  **4 inversions** across 2014–2026 (2024 documents average $1,118,260; 2026 documents
  $861,904). If it were purchase date it would rise monotonically. Retracted as a tenure
  proxy 2026-08-14. **Stratify on AV instead** — it measures the same thing correctly.
- **Assessed value is not a 2% escalator.** On the 12-year reference series AV fell in three
  of eleven years, once by 23.1%, with land and improvements moving in exact 30/70 lockstep
  (whole-parcel revaluation, not construction). So an advertised bond rate of "$X per $100k"
  is a **quotient** — debt service ÷ base — not a price. When the base falls the rate must
  rise to raise the same money.
- **Bill totals ≠ tax.** `Total Amount Billed` includes any 10% delinquency penalty + $10
  cost. Use `Ad Valorem Tax plus Special Assessments` for analysis; `parse_bills.py` splits
  them into `base_tax_total` and `late_penalty`.
- **Effective rate as % of AV is not a wealth-regressivity measure.** Low AV means old
  purchase, not poverty. Against market value the direction reverses. Always state the
  denominator.

## Verification discipline

Every figure reconciles to the bills' own printed totals before use: per-bill
`sum(ad valorem items) == printed AV total`, `sum(fixed items) == printed fixed total`,
`AV + fixed == printed base tax`. 37 bills × 3 checks = 111/111 pass; the 12-year series
passes 36/36. Three parser bugs were found by this check and not by inspection — negative
amounts written `-$7,000.00`, line items beginning with a digit (`2018 STORM WATER`), and a
`*` footnote marker on some district lines. **Reconcile before deriving.**

## Privacy

Bill PDFs carry a household's assessed value, payment dates and delinquency history. Public
record, name-redacted by the county under Gov. Code §6254.21 — but this repo publishes to
berkeleybuild.com. **Keep bill PDFs and parcel-level extracts outside the repo** (default
`~/Desktop/Alameda/`). Only de-identified derived structure — rate schedules, decile
summaries — belongs in version control. For publication, report sampled parcels as
anonymized strata, never by address.
