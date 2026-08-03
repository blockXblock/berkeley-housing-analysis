# Tour roadmap — next-session queue (2026-07-22)

John's next-step direction: build more tours sliced different ways. Each note below flags the
**data feasibility** so the next session can act, not re-scope.

## 1. Tours by specific architect
- **Source:** architect names live in the plan sets (e.g. **David Trachtenberg** = NX Ventures'
  Regal + Panoramic's buildings; harvest_affordability / plan-set metadata). Check whether v2 has
  an `architect` field on `project_versions`/documents; if not, extract from plan-set title blocks
  or research per building.
- Feasible for tracked (2013+) projects; older buildings (e.g. Panoramic's 1990s) need research.

## 2. Tours by building age
- **⚠ DATA GAP:** the assessor DB (`berkeley.db`) has **no YearBuilt / age field** (verified
  2026-07-22 — no height/stories/year columns). "By age" needs an external source:
  **Census ACS year-built**, or for new construction use **CO/permit dates** (v2 has these).
  For historic buildings, BAHA/landmark records. Resolve the source before building.

## 3. Tours by neighborhood or block
- **Feasible now:** parcel geometry + addresses in `berkeley.db` / v2. Group by block
  (APN book-page) or neighborhood polygon. Straightforward camera sweep per group.

## 4. 🎯 ADU + middle housing along College Ave
- **Feasible from existing data:** ADU cohort (**2,881 ADUs**, CO-year data, v4) + middle-housing
  **ZCMH** records (the ordinance's dedicated record type, 28 records since 2025-11). Filter both
  to the **College Ave corridor** (address LIKE '%COLLEGE%' + geocode to the street). Extruded
  blocks color-coded ADU vs duplex vs 4-plex. This is the most ready-to-build of the set.

## 5. 🎯 Every parcel with enough area for an ADU / duplex / 4-plex
- **Biggest build — a CAPACITY model, not just a tour.** Needs:
  - **Lot area (sqft)** per parcel — CHECK whether `berkeley.db` carries lot area/dimensions
    (it has `Land` $ value; unclear if it has area). If not, pull Alameda assessor lot-size or
    parcel-geometry area (compute from `the_geom` polygon).
  - **Berkeley zoning rules** encoded: min lot area for ADU (ministerial statewide), **SB9**
    duplex/lot-split thresholds, and the **Middle Housing ordinance** 4-plex criteria (BMC).
  - Output: classify each of the 29,131 parcels by what it could legally add, then a tour/map
    highlighting the capacity. Pairs naturally with the per-capita production analysis + the
    mayor deck ("here's the latent capacity"). Substantial; scope as its own JN + tour.

## Ready-to-build order (recommended)
**#4 (College Ave ADU+middle housing)** first — data's in hand. Then **#3 (block/neighborhood)**.
**#1 (architect)** after confirming the architect data source. **#2 (age)** and **#5 (capacity)**
are gated on resolving a data source (year-built; lot-area + zoning rules) — flag before starting.

## ⚠️ CAVEAT — the skyline geometry does NOT include ADUs (verified 2026-08-02)
`kml/geometry/geometry.kml` (184 buildings) is a **curated skyline of significant projects**,
not a building inventory: **82 are 50+ units; only 17 are ADU-scale (1-unit)**. Against **663**
one-unit projects in v2 and **~2,881 ADUs** in the v4 CO cohort, the skyline models **<1% of
ADUs** (and most middle housing). So tours #4 (College Ave ADU+MH) and #5 (capacity) **CANNOT be
built from geometry.kml** — they need ADU/MH locations from v2/v4 + assessor parcels.

## DECISION — two-layer geometry (2026-08-02)
Add a **second, GENERATED geometry file** alongside the hand-edited skyline:
- **`kml/geometry/geometry.kml`** — hand-edited **skyline** (184 majors). CANONICAL for major-building tours (#1, #3).
- **`kml/geometry/adu-middle-housing.kml`** — **GENERATED** from v4 ADU cohort + **ZCMH** middle-housing
  records + assessor parcel polygons (`berkeley.db.the_geom`), **type-color-coded** (ADU / duplex /
  triplex / fourplex). Derived + regenerable via a generator script (NOT hand-edited). Small footprints:
  use the parcel polygon extruded low, or a generated ~8m marker where no footprint.
- **Composing for a tour:** load skyline-only, ADU/MH-only, or **both**. To keep self-contained packages,
  add a `--geometry <file>` (or `--geometry a.kml,b.kml` to merge) option to `build_tour_package.py`.
  For **College Ave (#4)**, the generator emits a **corridor-filtered subset**.
- Keep ADU + middle housing in ONE file with type-coded styles (simpler than two files; a tour colors by type).

*(Major-building tours splice `kml/geometry/geometry.kml`; ADU/MH tours splice the generated
`adu-middle-housing.kml`; both use extruded type-colored blocks per the panoramic-kennedy-legacy
pattern; John records in OBS.)*
