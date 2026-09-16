# Bond map — Friedman's comments (2026-09-15) and the six bases of a Berkeley tax bill

**Status:** working note. Captures an email exchange that otherwise lives only in Gmail, the
response already built (uncommitted), and a new finding: every non-service line on a Berkeley
single-family tax bill is now derivable per parcel from tables we hold.

## 1. The email (Gmail thread `1a0a6d4c1ebdc604`, "New version of Bond Incidence map")

John sent `berkeleybuild.com/maps/bond_incidence.html` to the McGrath group (Wallman, Kromer,
McGrath, glomax, Friedman) 2026-09-15 13:53. Eric Friedman replied twice:

**14:07** — (a) the City's "$22 per $100k average" framing hides the real bill; (b) an un-modelled
lever: every parcel removed from the roll (small sites, TOPA) shifts debt onto the rest — the
City's projected AV growth must exceed its model just to cover that; (c) on his own bill the
measure is ~3.5%; **suggest showing the increase as a percentage, and consider using "Berkeley
extras" as the denominator rather than the whole bill.**

**14:40** — the voter's real question is *"how much more am I giving to this specific body, and
have they earned it?"* His bill, $12,404.02:

| denominator | +$311 (40-yr, tranched) | +$420 (our 30-yr figure) |
|---|---|---|
| entire property-tax bill | +2.5% | +3.4% |
| all City of Berkeley levies ($2,945.90) | +10.6% | +14.3% |
| existing City GO-bond tax ($302.84) | +102.7% | +138.7% |

**Correction to our map:** the $67/$100k "today's-base" rate spreads total debt service over
30 years; the City's structure is ~40 years, $100M tranches every 5 years, $15.2M average
annual debt service → on today's base **≈ $49/$100k**, not $67.

glomax (14:18): bond-market rates have risen since the City's figure; costs likely higher.

## 2. What was built in response (2026-09-15, UNCOMMITTED)

- `scripts/viz/bond_tranches_svg.py` → `docs/maps/bond_tranches.svg`: three panels on one time
  axis — debt service by tranche (hatched = interest), the AV base (today's vs the growth the
  advertised rate implies; the wedge = who the City assumes will pay), and rate per $100k on each
  base. Everything derives from `data/baselines/measure_u_reconciliation_baseline_*.json`.
- `scratch/2026-09-15/instrument_table.md`: GO vs Mello-Roos vs SRF/I-Bank vs revenue bonds vs
  assessment district vs EIFD — approval, base, cost vs GO.
- Sent to Wallman 18:51 with an 8-point "weaknesses" outline (thread `1a0a7d81e23f4d31`).

**Not yet done on the map:** the percentage-of-bill display with a selectable denominator, and
reconciling $67 → $49 (add the 40-yr/tranched rate as the honest "today's base" figure).

## 3. NEW FINDING — the bases of a Berkeley tax bill, and what we can derive per parcel

Re-ran the 37 FY2025-26 bills (`scratch/2026-09-16/third_base_test.txt`; parcel-level output
stays out of the repo per the privacy rule). The old "~$1,170 not modelled" residual was
**three lot-area charges plus two service fees**, not a mystery base. Full decomposition:

| base | items | rate (FY25-26) | per-parcel input we hold | derivable? |
|---|---|---|---|---|
| **assessed value** | 1% + 6 debt levies | 1.2323% | `berkeley.db.parcels.TotalNetValue` | ✓ |
| **building sqft** | 11 (BSEP, library, parks, fire, streets, …) | $1.93635/sqft | `taxable_sqft.bldsqfttaxable` | ✓ 35/37 exact |
| **lot sqft, continuous** | CLEAN STORM WATER | $0.00911/sqft (CV 0.000) | `taxable_sqft.lotsqft` | ✓ |
| **lot sqft, tiered** | EBMUD WETWEATHER | <5,000: $159.90 · 5–10k: $249.72 · >10k: $570.70 | `taxable_sqft.lotsqft` | ✓ |
| | 2018 STORM WATER | <10,000: $60.74 · ≥10k: $73.44 | same | ✓ |
| **per dwelling unit** | CSA Paramedic, Vector, Haz Waste | $55.12/unit (LOW confidence, 1 obs) | `parcel_facts.units` (28.5k non-null) | ✓ w/ caveat |
| **flat per parcel** | AC Transit VV, Peralta E, street light 2018, SFBRA AA, EBRPD, EB Trail, CSA lead | $202.52 | — | ✓ |
| **use category** | mosquito ×2, vector asmt | $11.20 (SFR) / $12.20 (SFR+2nd unit) | `UseCode` | ✓ (tiny) |
| **service fee — NOT a tax** | ZERO WASTE SRVCS (garbage cart) | $544–$1,214 by cart size | household choice; no dataset | ✗ |
| **service fee** | CITY ST LIGHTING | $12–20 by lighting zone | district roll not held | ✗ (tiny) |

Reconciliation: with the two service fees set aside, **35/37 bills within $1** of the printed
fixed-charge total. Median single-family bill by share: **ad valorem 64% · building-sqft taxes
30% · lot-area charges 3% · flat/per-unit 2% · garbage+lighting 3%.**

So: **yes, we can break every Berkeley parcel's bill down by base** — AV, building sqft, lot
sqft, units, flat, use-category — from `berkeley.db` alone, for single-family parcels. This is
what makes Friedman's "City levies" denominator computable per parcel (the City-only subset is
the 5 City per-sqft taxes + Clean Storm Water + 2018 Storm Water + street light + City's share
of the debt levies).

**Caveats to carry:** (1) rates validated on SFR only — several per-sqft taxes carry different
non-residential rates, and stormwater is by land-use/impervious class for non-SFR; (2) per-unit
rests on one duplex; (3) the two "MISS" parcels are the same two whose City sqft ≠ anchor sqft.

## 4. What the map text can clarify now (draft wording)

**"Your bill has six bases, and this bond lands on only one."** *A Berkeley property-tax bill is
not one tax. About 64% of a typical single-family bill is levied on assessed value (the Prop 13
number: purchase price + 2%/yr). About 30% is levied on the square footage of your building —
the base Berkeley's own schools, library, parks, fire and street taxes use. A few percent is
levied on lot area (stormwater, EBMUD wet weather), per dwelling unit, or as a flat charge, and
your garbage cart rides on the bill too. Measure U is levied entirely on the first base — the
one that varies 14× between neighbors on the same block — so it lands on the layer the City
itself has avoided for a decade of parcel taxes.*

**"$22, $35, $49, $67 — which is it?"** *All four are the same $300M. $22.14 is the City's
40-year average, on a base it projects will roughly double. $35 is the City's disclosed peak
(FY2040-41). $49 is the City's own average debt service ($15.2M/yr) divided by TODAY's $30.8B
base. $67 is the total debt service spread over 30 years on today's base — the upper bound. The
map defaults to $49 [once changed]. A rate per $100k is a quotient, not a price: the money to be
raised is fixed; the rate moves with the base.*

**Percent, not dollars (Friedman's denominators).** *For any parcel: bond ÷ whole bill · bond ÷
all City of Berkeley levies · bond ÷ existing City GO-bond tax. The first says "can I afford
it"; the second and third say "how much more am I handing this specific body."* — computable
per parcel from §3; the popup can show all three.

**Parcels leaving the roll.** *Every parcel that becomes tax-exempt (public acquisition, TOPA
land trusts, small-sites) shifts its share of the fixed debt service onto everyone else. The
City's growth projection does not model this.* — statement only; we have no count yet. The
372 publicly owned parcels (`data/derived/berkeley_public_owned_parcels.csv`) are the baseline
for a future "exempt AV" figure.

## 5. Next steps (in order)
1. Commit `bond_tranches_svg.py` + svg (John eyeballs first).
2. Generator: add `rate_today_40yr` (≈$49) to the baseline + rate toggle; relabel $67 as
   the 30-yr upper bound.
3. Generator: per-parcel bill decomposition (six bases) → popup shows bond as % of whole bill /
   City levies / existing GO tax. Needs `taxable_sqft.lotsqft`, `parcel_facts.units`, and the
   City-only subset of the rate schedule tagged in the JSON.
4. Fold the lot-area tiers + Zero Waste finding into `derive_rate_schedule.py` and
   `docs/methodology/berkeley_property_tax_structure.md` (retire the "$1,170 unmodelled" line).
5. Sample 3+ duplexes/triplexes for the per-unit rates; 3+ apartment bills for non-SFR rates.
