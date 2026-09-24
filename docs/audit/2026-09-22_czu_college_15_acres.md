---
title: "College Avenue is 1.5 acres — the number that was public from the start"
date: 2026-09-22
type: report
status: record
area: audit
---

# College Avenue is 1.5 acres

All 27 published Corridors Zoning Update documents fetched (`scripts/fetch_czu_documents.py`,
manifest with sha256 in `data/raw/czu/`). Two findings, and the second is the story.

## 1. The `development_potential` legend — found

The Raimi geodatabase codes (`1A`…`5`) were undecodable from the data and absent from both
the Existing Conditions report and the May 2026 staff report. They are defined on the
**Workshop #2 boards of 20 August 2025**. The number is the category, the letter the subtype:

| code | category | subtypes |
|---|---|---|
| `1A` `1B` | **A. High redevelopment potential** | Vacant or corporate ownership · Real-estate asset |
| `2A` `2B` | **B. Modest** | Corner and large infill sites · Small infill sites |
| `3A` `3B` | **C. Special conditions** | Grocery store · City-owned |
| `4A` `4B` | **D. Very low / none** | Thriving businesses, staging constraints, potential historic significance · Challenging site conditions |
| `5` | not yet resolved — likely the rent-controlled / non-commercial class shown separately on the same board |

**It survives a check against the data.** `1A` parcels carry the largest median lot
(11,188 sf) and 45% show zero units — exactly "vacant or corporate ownership". The earlier
caution against reading the scale in either direction is now lifted: **1 is the highest
potential, 4 the lowest.**

## 2. The consultant's own acreage table, presented publicly on 2025-08-20

| corridor | Total potential (A+B+C) | Very low / none | A. High | B. Modest | C. Special |
|---|---|---|---|---|---|
| **College Ave** | **1.5 ac — 22%** | 5.4 ac — 66% | 1.0 ac — 16% | 0.5 ac — 7% | **0 ac — 0%** |
| North Shattuck | 6.7 ac — 37% | 11.4 ac — 63% | 3.4 ac — 19% | 1.3 ac — 7% | 2.0 ac — 11% |
| Solano Ave | 6.4 ac — 63% | 3.7 ac — 37% | 0.9 ac — 10% | 4.1 ac — 40% | 1.3 ac — 13% |

Source: `2025-08-20_workshop2__boards.pdf`, the display boards from the corridor-specific
community workshop.

**College Avenue has the least redevelopment potential of the three corridors — 22% of its
area, against Solano's 63% — and the consultant said so, on a public board, at the workshop
that triggered the campaign.**

## The two numbers agree

The May 2026 staff report (`2026-05_06_PC_Item 10A_Corridors.pdf`, Table 3) projects, under
the staff-recommended Option 1A:

| | College Ave | Solano | North Shattuck | total |
|---|---|---|---|---|
| projected units | **131** | 442 | 963 | 1,518 |
| on-site affordable (10%) | **13** | 44 | 97 | 152 |

1.5 acres and 131 units are the same statement made twice, ten months apart. Against a
6th-cycle RHNA obligation of **8,934 units** and identified citywide capacity of **19,098**,
College Avenue is **1.5% of the obligation** and the whole three-corridor program is 17%.

## Why this matters

**Neither campaign has been using these numbers.**

- Save Berkeley Shops' March 2026 appeal describes *"8–12 story residential towers"*, later
  *"14 stories"* and *"a 1,400% height increase"*. The staff recommendation is five storeys
  on 1.5 acres yielding 131 units.
- WECAN's College Avenue page names **three sites** — the Webster post office lot, the
  7-Eleven strip mall at Russell, and the Nabolom/Five Little Monkeys corner. That is
  *roughly consistent* with 1.0–1.5 acres, and closer to the record than the opposing claim.

So the defensible finding is not that one side is lying. It is that **Berkeley has spent two
years and a $600,000 consultant contract arguing about 1.5 acres, and the figure was on a
public display board in August 2025.** That is the intuition-without-knowledge thesis with a
document behind it, and it implicates everyone.

## Caveats before publishing

- The acreage table is the **August 2025** analysis; the May 2026 Option 1A geometry may
  differ. Reconcile against the staff report's "10.6 acres likely to redevelop across the
  three corridors" before quoting a single figure.
- `5` is still undecoded; do not label those parcels.
- The AFFH/fair-housing argument is untouched by any of this. Small yield is a rebuttal to a
  supply claim, not to a fairness claim — see `notes/2026-09-22_traffic_campaign_plan.md`.
