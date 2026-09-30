---
title: "\"Built Year by Year\" — is 25,471 true, and what is missing?"
date: 2026-09-25
type: audit
status: open
area: docs/audit
---

# "Built Year by Year" — 25,471 parcels

**Is the number true?** Yes. `docs/maps/berkeley_construction_data.json` holds exactly **25,471
features**. The source is `data/raw/berkeley_taxparcels_2026-08-12.geojson` — 28,870 parcels, of
which **25,428** carry `YearBuilt > 0`; the landmark-correction layer accounts for the small
difference.

**Does it capture governmental, religious, city or utility structures? No — barely at all.**

| owner type | on the map | total | excluded |
|---|---|---|---|
| individual | 18,230 | 19,857 | **8.2%** |
| trust | 5,716 | 6,372 | 10.3% |
| investor | 1,062 | 1,603 | 33.7% |
| **institutional** | **227** | **702** | **67.7%** |

Named public owners, parcels actually on the map:

| owner | on map / total |
|---|---|
| **San Francisco BART District** | **0 / 19 — 0%** |
| **East Bay Municipal Utility District** | **0 / 14 — 0%** |
| **East Bay Regional Park District** | **0 / 31 — 0%** |
| **Regents of the University of California** | **1 / 52 — 2%** |
| City of Berkeley | 22 / 197 — 11% |
| Berkeley Unified School District | 5 / 36 — 14% |
| religious-named owners (church/temple/parish/…) | 64 / 101 — 63% |

**Why:** `YearBuilt` is an *assessor* field, recorded as part of valuing taxable improvements.
Tax-exempt public property is not assessed the same way, so it carries no build year and drops out.
Religious parcels fare better (63%) because many sit on ordinarily-assessed lots.

So the map is a map of **private Berkeley**. BART stations, the EBMUD reservoirs, the regional
parks, essentially all of UC, and seven-eighths of the City's own buildings are simply not on it.

## A second, larger problem: the data stops in 2016

`YearBuilt` runs **1850 – 2016**. There is nothing after 2016 — the last full year present is 2016
with 19 parcels, and the 2010s total just 124. **The slider, however, runs to 2026.** A reader drags
it through the last ten years and watches nothing appear, which silently asserts that Berkeley built
nothing in the decade this entire site is about. The corridor projects, the 2,000+ units completed
since 2017, 1951 Shattuck's 163 units — none of it is there.

The page's existing caption already discloses the ADU limitation and the excluded count ("3,399
parcels have no build date"). It does **not** disclose either of the two findings above.

## Fix applied to the copy (not deployed)

- **Homepage card** now reads *"25,471 private parcels, 1850–2016"* rather than an unqualified
  "25,471 parcels by build date".
- **Map caption** now states the 2016 cut-off and that public land is largely absent.

Neither is a data fix. The real remedies are separable:
1. **Extend past 2016** — our own `co_issued_date` layer covers 2017-2026 and could be appended as
   a distinct series, clearly marked as a different source from the assessor's `YearBuilt`.
2. **Public structures** would need a non-assessor source (City facilities inventory, UC capital
   records, BART/EBMUD asset registers). Not currently held.
