# Berkeley staffing, pay, overtime and pensions vs the other 13 Alameda County cities

**Date:** 2026-08-15 · **Status:** analytical record. **Compensation only — see §5 before using this on the bond.**
**Source:** CA State Controller, Government Compensation in California, 2024 City raw export (17,028 Alameda city rows, 14 cities)
**Code:** `scripts/compensation/compare_alameda_cities.py` · **Derived:** `data/derived/alameda_city_compensation_2024.json`

---

## 1. Three corrections that had to be made first

Every one of these produced a materially wrong answer on the first pass. They are the substance of the method, not footnotes.

**(a) `IncludesUnfundedLiability` is not reliable.** Berkeley reports `False`. But its safety plans show defined-benefit contributions of **103–128% of regular pay** — impossible as normal cost — and at an identical formula (2.7%@55) Berkeley shows **31.6%** against Pleasanton's **14.3%** under the same flag. Berkeley's median full-time employee is at 36.3%, sitting with Oakland (43.1%, flag `True`), not with Hayward (8.3%) or Fremont (5.9%) which share its flag.

Taking the flag at face value makes Berkeley a **3.3× outlier** against a 14.7% peer median. That finding is false. The script now infers the convention empirically and finds the flag disagrees for **Berkeley and Newark**.

**(b) Position strings aren't comparable raw.** Berkeley prefixes every position with a job-class code and appends a shift schedule — `8019 Police Officer`, `8113 Firefighter 56`. Matching raw strings drops Berkeley from *every* cross-city job comparison, and it reads as "no data" rather than as an error.

**(c) Staff-per-capita is a service-mix artifact.** 21% of Berkeley's full-time staff (286 of 1,338) work in Health, Housing & Community Services (187), Berkeley Public Library (78) and the Rent Board (21) — functions most Alameda cities don't run at all.

---

## 2. Staffing

| | FT proxy per 1,000 residents |
|---|---|
| Berkeley, as reported | **10.42** |
| Berkeley, excluding health / library / rent board | **8.20** |
| Oakland | 8.72 |
| Alameda | 6.48 |
| Pleasanton | 5.94 |
| Hayward | 5.03 |
| Fremont | 3.75 |
| San Leandro | 3.59 |

Berkeley has the highest municipal staffing per resident in the county, and it stays high (8.20) even after removing the functions peers don't perform. Berkeley payroll runs **$1,557 per resident** against Fremont's $668 and Hayward's $916.

*Caveat:* the FT proxy is `RegularPay ≥ $60,000`, not an FTE count — GCC rows include part-year and part-time positions.

## 3. Pay and overtime — the surprise

Berkeley pays the **lowest base wage in the county in every matched public-safety class**, and runs the **highest overtime**:

| Police Officer | median base | median OT | OT as % of base |
|---|---|---|---|
| Hayward | $150,723 | $27,695 | 18.4% |
| Newark | $149,466 | $36,340 | 24.3% |
| Fremont | $132,774 | $34,589 | 26.1% |
| *group median* | *$130,742* | | |
| **Berkeley** (n=93) | **$113,860** | **$36,248** | **31.8%** |

Berkeley ranks **12th of 12** on police officer base pay, **8th of 9** on sergeant ($143,394 vs a $168,433 group median), and **6th of 6** on firefighter ($98,275 vs $116,222) — while carrying the highest overtime ratio in two of the three classes (firefighter OT is **49.2%** of base).

That combination — lowest base, highest overtime — is the standard signature of vacancies and mandatory minimum-staffing backfill, not of generous pay. A Berkeley police officer's base plus overtime (~$150k) lands near Hayward's *base alone*.

## 4. Pensions

Compared only within the same inferred reporting convention:

| includes unfunded liability | DB pension as % of regular pay |
|---|---|
| San Leandro | 55.4% |
| **Berkeley** | **49.0%** |
| Oakland | 47.2% |
| Newark | 40.6% |
| Livermore | 39.8% |
| *median* | *47.2%* |

Berkeley is **2nd of 5, essentially at the group median** — not an outlier. The cities reporting normal cost only sit near 14.5%; that number is not comparable to Berkeley's and must never be placed beside it.

---

## 5. What this does and does not support

**Does not support:** "Berkeley overpays its staff." The opposite is true on base pay for public safety, by a wide margin. Any argument built on Berkeley salaries being out of line with peers will be refuted by this data — which is the State Controller's own.

**Does not support:** "operating costs are why there is no capital money." GCC is a **compensation file**. It contains no budget, no revenue, no capital spending. Establishing crowd-out requires the city's own budget documents, and that work has not been done.

**Does support, carefully:** Berkeley runs a **broader service portfolio** than its peers (health, library, rent board — 21% of staff), at **higher headcount per resident** (8.20/1,000 excluding those functions, still above every peer but Oakland), with **the lowest public-safety base pay in the county**, **the highest overtime**, and **pension costs in the high group**. That is a structural cost profile worth asking the city about. It is not, on this evidence, a story about excessive salaries.

**The honest question it raises for the bond:** the lowest base pay in the county combined with the highest overtime suggests a recruitment and retention problem, and pension costs sitting in the same band as Oakland's. Those are ongoing General Fund pressures. Whether they explain the deferred-maintenance backlog that Measure U is meant to address is a budget question this file cannot answer — but it is the right question to put to the city, and the $40.5M of "staffing and implementation resources" inside the $313M program (claim C13 in the companion note) is where the two threads meet.

## 6. Reproducing

The GCC ZIP is behind a WAF that refuses curl and scripted navigation; download it manually from
https://gcc.sco.ca.gov/reports/rawexport.aspx ("2024 City Data"). The CSV is ~96MB and is **not**
committed. Then:

```bash
python -m scripts.compensation.compare_alameda_cities /path/to/2024_City.csv
```

**2025 City Data was not obtained** — only the 2024 file was downloaded. Everything here is FY2024.
