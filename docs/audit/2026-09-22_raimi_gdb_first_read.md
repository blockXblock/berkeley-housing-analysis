---
title: "Raimi corridors geodatabase — first read (CPRA #26-2367)"
date: 2026-09-22
type: report
status: record
area: audit
---

# Raimi corridors geodatabase — first read

First analysis of `data/raw/corridors/raimi_corridors.gdb` (CPRA #26-2367, retrieved 2026-09-21).
Read-only; nothing joined, nothing written. `.venv/bin/python` + `pyogrio`.

## Headline: three of the eight layers are the corridors. The famous one isn't.

**`Parcels_Opportunity_Sites_OpOnly` (258 parcels) is CITYWIDE, not the corridors.**
Its 63 fields are almost entirely Alameda **assessor attributes** (APN, situs, owner, mailing
address, `Land`, `Imps`, `UseCode`, `YearBuilt`) plus `OZ_*` join keys. **There are no capacity
fields in it at all** — no allowed units, no proposed height or FAR. The `README.md` in that
directory describes it as "opportunity sites + capacity attributes"; that is wrong and should
be corrected.

Where those 258 parcels actually are:

| ZIP | area | parcels | share |
|---|---|---|---|
| 94708 | **North hills** | **64** | **24.8%** |
| 94704 | Downtown / Southside | 62 | 24.0% |
| 94702 | West Berkeley | 45 | 17.4% |
| 94710 | West Berkeley flats | 33 | 12.8% |
| 94707 | North Berkeley / Solano | 17 | 6.6% |
| 94703 | South / Central | 13 | 5.0% |
| 94709 | North Shattuck | 12 | 4.7% |
| 94705 | **Elmwood / Claremont** | **7** | **2.7%** |

Top streets: **San Pablo 34, Shattuck 29, University 28** — the corridors Berkeley already
upzoned — then Cragmont, Summit, Hill, Keeler, Arlington, Keith, which are **hill streets**.

**The three contested corridors (College/Elmwood, North Shattuck, Solano) are 36 of 258 — 14%.
The hills alone are 25%.** Two years of public argument have been about roughly a seventh of
the city's own opportunity-site inventory.

*(Consistent with the AFFH framing, which directs upzoning at the highest-resource
neighbourhoods — and the hills are the highest-resource. It is not a contradiction. It is
simply not where the fight went.)*

## The corridor layers, which ARE the three corridors

- **`project_area_parcels_data`** — 495 parcels. College Ave 269 · Shattuck 75 · Solano 62.
  ZIPs 94705 (235), 94709 (95), 94704 (89), 94707 (74). 2,637 existing units.
- **`project_area_parcels_dev_potential`** — 335 parcels, and **this is the soft-site
  prioritisation the CPRA asked for**: a `Corridor` field (College Ave / North Shattuck /
  Solano Ave) and a **`development_potential` grade** with nine values, on 186 graded parcels.

| grade | College | N. Shattuck | Solano | total | acres |
|---|---|---|---|---|---|
| 5 | 17 | 33 | 14 | **64** | 12.9 |
| 2B | 0 | 8 | 22 | 30 | 3.4 |
| 4B | 3 | 8 | 14 | 25 | 2.5 |
| 2A | 3 | 3 | 10 | 16 | 2.5 |
| 4A | **15** | 0 | 1 | 16 | 2.1 |
| 1A | 2 | 5 | 4 | 11 | 3.1 |
| 1B | 4 | 5 | 0 | 9 | 2.4 |
| 3A | 0 | 3 | 5 | 8 | 5.3 |
| 3B | **7** | 0 | 0 | 7 | 0.8 |
| **total** | **51** | **65** | **70** | **186** | 58.3 acres |

⚠ **THE LEGEND IS NOT IN THE DATA.** Nothing in the geodatabase says whether grade 5 is the
highest development potential or the lowest, or what the A/B suffix means. **Do not publish an
interpretation of these grades until the key is found** — it is presumably in the Existing
Conditions or Alternatives Report PDF. Getting the direction backwards would be the single
worst error available here.

Only **10 of 335** parcels carry a `historic_resource` flag.

## The revision trail — 126 of 382 Housing Element sites were reclassified

`housing_element_sites` (382 parcels) carries **five dated snapshots** of each site's
classification: `Sites_4_19`, `Sites_7_25`, `Sites_8_3_`, `Sites_10_1`, `Sites_10_2`.

**126 of 382 parcels changed classification between the first and last.** Most are renames
("Likely_Entitled since 2018" → "Entitled since 2018", 46; "Pipeline_Applied in 21-22" →
"Application under review", 21). But two movements are substantive:

- **13 parcels marked `(NOT INCLUDED)` in the April snapshot were added by October** — 7 as
  "Anticipated", 4 as "Application under review", 1 "Entitled since 2018", 1 "Opportunity_1".
- **6 parcels moved from `Opportunity_1` to `BART Sites`.**

`Units_To_1` (capacity) sums to **14,498 units across the 382 sites**, against a 6th-cycle
RHNA obligation of 8,934 — a 62% buffer. The `Density__1` and `FAR_1` fields are stored as
strings and need parsing before use.

## What this does and does not support

**Supports now:** the geography finding. ZIP and street name are reliable fields, and the
result is robust: the city's own opportunity-site inventory is concentrated in the hills,
downtown and West Berkeley, not in the three corridors under dispute.

**Does NOT support yet:** any "here is what they plan for your block" map of the corridors.
That needs the `development_potential` legend. Find it first.

**Do not trust,** per `CLAUDE.md`: `UseCode` as a housing signal (35.7% of the 258 read as
1xxx single-family, 29.5% as 3xxx multi-family, but the field is unreliable), and the assessor
`Units` field (186 of 258 parcels read 0 units, which reflects sparse population of that
column, not vacancy).

## Next

1. **Find the `development_potential` legend** in the CZU PDFs. Everything corridor-facing
   depends on it.
2. Correct the layer description in `data/raw/corridors/README.md`.
3. Parse `Density__1` / `FAR_1` from string.
4. Join `project_area_parcels_data` to v2 by canonical APN — 495 corridor parcels against our
   own pipeline is a direct check on the consultant's existing-conditions numbers.
