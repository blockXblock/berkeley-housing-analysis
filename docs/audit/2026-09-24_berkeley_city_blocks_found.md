---
title: "Berkeley's real city blocks — found on the second GIS endpoint, under the wrong name"
date: 2026-09-24
type: report
status: record
area: audit
---

# Berkeley's real city blocks

Every block-level figure this project has published rests on **Census tabulation blocks**, which are not
street-enclosed blocks. The City's own block polygons exist. They were not found until today because
they are on a second GIS endpoint that was never swept, filed under a name that describes something else.

## Two endpoints, one swept

| endpoint | layers | status |
|---|---|---|
| `gis.cityofberkeley.info/arcgis/rest/services` | 504 | swept **2026-08-30** (`data/raw/infrastructure/berkeley_arcgis_inventory_2026-08-30.json`) |
| `services1.arcgis.com/IYiCpZoSIq9lAxi8` | 470 | **never swept until 2026-09-24** |

The on-prem sweep was thorough and genuinely has no block polygons — Census blocks, parcels, street
*lines*, narrow streets, nothing enclosing. **This was not a missed layer; it was a missed server.**

## The layer is called `sde_prod_DBO_Right_Of_Way`

Its attributes read `ZONDIST: UNKNOWN`, `Cnt_ZONDIS: 1352`. Its geometry is **1,197 disconnected
polygons** — a dissolved right-of-way would be ONE connected piece with holes. Searching "block" returns
`BlocksCoB`, which is only **Census TIGER 2020 republished** (`GEOID20`, `ALAND20`, `TRACTCE20`).

**It is the blocks.** 697 parts fall between 2 and 4 acres, they contain **16,987 parcels**, and the
median part holds **25 parcels** (p25 17, p75 32) — a Berkeley block.

⚠ The raw layer also contains a **5,771-acre envelope polygon** and slivers. **Filter to roughly
0.2–60 acres** or every total is nonsense. 1,119 real blocks survive that filter.

## It is measurably better than the Census geography

| | blocks | median acres | median rectangularity | p10→p90 spread |
|---|---|---|---|---|
| **City blocks** | **1,119** | 3.22 | **0.952** | **3.3×** |
| Census blocks | 1,524 | 3.60 | 0.906 | **14.8×** |

A street grid produces blocks of similar size. **14.8× variation is the signature of tabulation
geography**, which merges across streets where a street does not cut through and splits on tract
boundaries unrelated to the grid.

## What this invalidates, and what it does not

**SAFE — anything per ACRE.** The Elmwood finding (**12.8 du/acre vs 6.9 non-student Berkeley, 1.85×**)
is district-total units ÷ district-total acres. It does not care how the interior is partitioned.
Corridor du/ac comparisons likewise.

**AFFECTED — anything per BLOCK.** Block choropleths, the units-per-block axis, and the "399-unit
block" (which is ~2 city blocks: College/Benvenue/Hillegass are parallel, Dwight is perpendicular).

**Elmwood has 74 city blocks, not 93.** The 93 in `notes/Elmwood-housing-argument.md` is the Census
count. The `JN-M_corridor_density` baseline gate will catch this and should be re-baselined with a
documented delta, not hand-edited.

## Two more layers worth as much

- **`StreetIntersection` — 1,984 points** with `STREETS` and `STREET1O8`…`STREET8O8`. **This solves
  corner detection.** The address-based method used on the CZU corridor analysis found 7 corners in 198
  College parcels and missed 2887 College and 2701 Webster, both visibly corners.
- **`Street_Centerline` — 3,831 segments** with `STREET_NAME`, address ranges, `LANES` and **`SLOPE`** —
  a physical constraint that survives any zoning change. ⚠ `maxRecordCount` is 2000; a single request
  silently returns 2,000 of 3,831. The fetcher pages.

## Also still open

- **Footprints:** `docs/audit/2026-08-22_building_footprint_vs_parcel_findings.md` found **139 of 184
  tour polygons are the parcel boundary, not the building** (76%). The 62,651 Overture footprints
  (`data/raw/overture_buildings_berkeley_2026-08-19.parquet`, 71% carrying height) are the unapplied fix.
- **Bedrooms:** the Rent Board registry carries `Number of Bedrooms` across 41,279 units — **rent-
  controlled only, a biased sample, not a census.** `structure_history`'s per-unit `bedrooms` was
  designed and never populated.
- **UrbanSim:** `notes/2026-08-14_waddell_outreach.md` asks Paul Waddell directly for his
  assessor→building-attributes pipeline. **Status: open — never sent.**
