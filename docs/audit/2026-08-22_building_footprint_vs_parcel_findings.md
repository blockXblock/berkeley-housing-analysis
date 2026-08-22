# Building footprints vs. parcels — three findings in the tour geometry

**Date:** 2026-08-22 · **Branch:** `dev` · **Status:** diagnostic complete, read-only (no DB or KML writes)
**Thread:** KML geometry / flyover tours / building footprints (`notes/2026-08-16_geometry_tours_handoff.md`)

The tours are meant to tell a **"drumbeat vs tower"** story — the carpet of small ADU/Middle-Housing
projects against the few big buildings. That story is carried entirely by two visual quantities:
**how big each polygon is** and **how tall it is extruded**. Both are wrong in ways that flatten the
distinction. This records what is wrong, the evidence, and one path that was tested and rejected.

---

## Finding 1 — 76% of the "building footprints" are the parcel boundary

Measured every polygon in `kml/geometry/geometry.kml` against the county parcel containing its centroid
(`data/raw/berkeley_taxparcels_2026-08-12.geojson`, 28,870 features; centroid-in-polygon; areas by
equirectangular shoelace about each ring's own latitude).

> **139 of 184 polygons match their parcel area to within 7% — most to within 1%.**

**v2 already records this and the KML generator discards it.** `vocabulary_geometry_types` distinguishes
`apn_parcel` from `building_footprint`, and `project_geometries` currently holds:

| geometry type | current rows |
|---|---|
| `apn_parcel` | **157** |
| `synthetic_polygon` | 11 |
| `building_footprint` | **9** |

`generate_kml.py` reads `geometry_type_id` and then extrudes all of them identically. **This is a rendering
defect, not a data defect** — the database is not lying about provenance; the KML pipeline drops it.

The 9 real footprints are all `kml_import_2026-05-18` — hand-traced in Google Earth over aerial imagery and
ingested back. They are the hero towers (2400 Bowditch, 2556 Haste, 2200 Bancroft, 1950 Oxford,
1974 Shattuck, 2065 Kittredge), 5–7 vertices, with real heights (98 m, 85 m, 80 m). Three of them carry
**two** footprints for their North/South towers — the correct parcel→many-buildings model. That is the
quality bar; hand-tracing simply does not scale to 184.

### Worked case — 2740 Shasta Rd
Polygon area **38,472 sf** = the parcel polygon area **to the square foot** (assessor `LotSize` 38,060).
It is APN `60-2469-7`, a 0.87-acre irregular hillside lot; the 19 vertices are the lot's edges following
the road and contours. What actually stands there is a **single-family house, built 1949** (`UseCode 1100`,
1 unit, 5 beds). We extrude the entire 0.87-acre lot to 10.5 m, so it renders as a three-story block
covering nearly an acre of the Berkeley hills. It also carries a **zero-length segment** (duplicate vertex)
and appears **twice** as byte-identical placemarks.

**Simplifying that outline is the wrong fix** — it yields a tidier version of a shape that should not be
there. The complexity is the symptom; lot-substituted-for-building is the defect.

### This unifies the existing footprint fix-list
The "OVERSIZED" flags in `data/reference/tabulation_footprints.csv` are not trace errors. They are
**exactly `1 / lot_coverage`**:

| | tabulation (building) | ours (lot) | ratio | 1/coverage |
|---|---|---|---|---|
| 2920 Shattuck | 10,232 sf | 19,519 sf | **1.91** | **1.92** |
| 2190 Shattuck | 19,767 sf | 20,126 sf | 1.02 | 1.01 |

2920 is the lot, against an architect-stated 52% coverage. 2190 "passed" after being replaced with its
parcel only because its coverage is **99%** — there, lot ≈ building. The "UNDERSIZED" flags are a different
failure: 2601 San Pablo's tabulation implies a 28,778 sf lot but we matched a 3,669 sf parcel — a
**multi-parcel assembly** where one piece was picked.

> **Consequence for the hand-off:** §5 step 2 ("regenerate base polygons from county parcels") is inverted.
> 76% *already are* the parcel. Regenerating would change almost nothing downtown and would actively
> re-affirm the error in the hills. **Parcel-substitution is only safe at high lot coverage.**

---

## Finding 2 — 39% of extrusion heights are a migration placeholder rendered as data

`generate_kml.py:227` sets `height_m = 10.5  # Default 3 stories`. **72 of the 176 described placemarks
(41%) sit at exactly 10.5 m**, and **71 projects carry `height_stories = 3.0` asserted by
`migration_v1_to_v2_20260507`** — a migrated value with no primary source. The placemark text says
`(height estimated from units)` while displaying "Stories: 3" as though it were a measurement.

Five of those are real mid-rises drawn three stories tall:

| project | address | units | drawn as |
|---|---|---|---|
| proj135 | 2150 Kittredge St | 169 | 3 stories |
| proj136 | 1951 Shattuck Ave | 163 | 3 stories |
| proj137 | 2000 University Ave | 82 | 3 stories |
| proj96 | 2099 M L King Jr Way | 72 | 3 stories |
| proj91 | 2009 Addison St | 45 | 3 stories |

All Completed, all with `height_feet` NULL. **This damages the drumbeat/tower read more directly than any
footprint error** — genuine mid-rises are rendered as drumbeat.

### Related: descriptions are stale because the relabeler only rewrites `<name>`
`relabel_geometry_from_v2.py` rewrites `<name>` and never touches the `<description>` CDATA, so the two
now disagree. 1136 Keith: name says "1 units · Completed"; description says "Units: **0** … Status:
**In Review**". Four placemarks show `Units: 0` against a DB count > 0, including 2009 Addison (45u) and
2099 MLK (72u). Three placemarks do not address-match the DB at all. The description is what a viewer
reads in the Earth Pro popup.

### Also: the "184 towers" set is not towers
It is a mixed cohort including many 0–1 unit projects (1136 Keith, 705 Arlington, 576 San Luis Rd,
2740 Shasta). This matters for open decision §3.2 (184 vs 1,060) — the 184 is not currently a clean
"just the big ones" set.

---

## Finding 3 — REJECTED: deriving footprints from City taxable square footage

### The idea
UrbanSim's `SqFtProForma` — which we reimplemented in `scripts/v4/build_jn_feasibility.py:167` — encodes a
closed identity:

> `building_sqft = lot_sqft × coverage × stories`, so **`footprint = building_sqft ÷ stories`**

Know any two, get the third. It is the same identity the architect Tabulation Form uses
(Lot Area × Lot Coverage → footprint). `building_sqft` is **0 of 895 populated** in v2, but the City
publishes it: `data.cityofberkeley.info` resource **`9a47-nj4i`** (Taxable Square Footage, 29,167 rows,
already used and validated by `scripts/tax_incidence/derive_rate_schedule.py:62` — exact to the square foot
on 35 of 37 bill parcels).

### The test
Joined `9a47-nj4i` to all 184 by canonical APN (`housing_rules.to_canonical_apn`). The join is excellent:
**100% APN-resolved, 88% matched, 76% with nonzero sqft, 41% nominally derivable.**

Then validated the derived footprints against the 9 architect tabulation forms:

| address | status | tabulation | derived | error |
|---|---|---|---|---|
| 1974 Shattuck | Entitled | 24,973 sf | **138 sf** | 0.01× |
| 2190 Shattuck | In Review | 19,767 sf | 1,600 sf | 0.08× |
| 2920 Shattuck | In Review | 10,232 sf | 856 sf | 0.08× |
| 3000 Shattuck | Entitled | 9,173 sf | 234 sf | 0.03× |
| 2420 Shattuck | In Review | 6,783 sf | 332 sf | 0.05× |
| 2733 San Pablo | In Review | 12,337 sf | 965 sf | 0.08× |

**Wrong by 12×–100×, on six of six testable cases.** The identity is sound; the input is wrong.

### Why — two structural reasons, both fatal
1. **Taxable sqft describes the building standing TODAY**, which for a pipeline project is the building
   about to be demolished. 1974 Shattuck is a 599-unit, 28-story proposal; the taxable sqft is the small
   existing building, so `sqft ÷ 28` = 138 sf. Split by whether the building exists, derived lot coverage
   runs **median 0.45 for built** vs **0.10 for proposed**, with 50 of 61 proposed cases under 0.25.
2. **"Taxable" is a tax quantity, not a physical one.** Affordable housing carries the welfare exemption,
   UC is exempt outright, and new completions sit in the **1–2 year reassessment lag** already documented
   in `CLAUDE.md` for `Imps`. Hence 2200 Bancroft (550 units) → coverage 0.03; 2427 San Pablo (78 units) →
   0.07. **The dataset systematically undercounts exactly the projects the tours are about.**

### What survives
Seven buildings — built, taxable, non-exempt — with believable coverage 0.55–0.93: 2072 Addison (0.93),
2440 Shattuck (0.81), 2480 Bancroft (0.79), 2650 Telegraph (0.62), 1773 Oxford (0.61), 1698 University
(0.60), 2555 College (0.55). **Seven of 184 is not a plan.**

> **Do not re-attempt this.** `bldsqfttaxable` is unusable as a physical building measure for pipeline
> projects. Physical sources for physical questions.

---

## The standing check

A building footprint must be **strictly inside** its parcel, and

> **`polygon_area ÷ parcel_area` must be < ~0.95** — because that ratio *is* lot coverage.

This is the test that flagged 2740 Shasta at 1.00 and correctly passed 2190 Shattuck at 0.99 (a genuine
99%-coverage downtown tower). Where a tabulation form exists, assert the ratio against the architect's
stated coverage — that is what resolved 2920 Shattuck's 1.91 to `1/0.52`.

**Anchor note (per `CLAUDE.md`):** anchor to the *invariant* (a footprint sits inside its lot; coverage is
bounded) — not to a frozen count of flagged buildings, which legitimately moves as footprints are corrected.

---

## Corrected plan — split by whether the building exists

| cohort | source | why |
|---|---|---|
| **Proposed / pipeline** | architect **Tabulation Form** area + site plan; inset the parcel polygon to the tabulated area | the only source describing the building that will exist |
| **Built** (Completed / UC) | aerial-derived footprints (Microsoft Building Footprints, OSM, or LiDAR) | imagery of the actual building exists |
| **Neither** | keep the parcel, render **flat as a site, never extruded** | honest: "a site in review" is real information; a fake building is not |

### The harvest headroom
The current harvester (`scripts/harvest_tabulation_footprints.py`) selects documents whose **title** matches
`%Tabulation%` or `%1.E%` — which is why it finds only **9**. But `documents` holds **121 `plan_set` PDFs
with `r2_url` populated, across 33 distinct projects** (111 of the 121 belong to proposed projects; 40
proposed projects have some r2 document). Plan sets are large — 66 to 1,430 pages — and the tabulation form
is an **interior page**, not the title. Parsing plan-set interiors is a multi-fold expansion using documents
already in hand — no acquisition required.

## Next steps
1. **Extend the tabulation harvest into plan-set interiors** (in progress) — the scalable path for pipeline towers.
2. **Make `generate_kml.py` respect `geometry_type_id`** — parcels flat, footprints extruded. Highest-value single fix.
3. **Commit the parcel-vs-building survey as a standing check** with the coverage-ratio invariant.
4. **Fix the five placeholder heights** (proj135/136/137/96/91) from their plan sets.
5. **Make `relabel_geometry_from_v2.py` rewrite descriptions**, not just names.
6. Dedup `geometry.kml` (2740 Shasta ×2; 2099 MLK under two spellings) and the `kml/geometry/` version sprawl.

## Reproduction
- Survey + diagnostics were run read-only; scripts in the session scratchpad, to be committed as
  `scripts/survey_footprint_vs_parcel.py` (step 3).
- Sources: `kml/geometry/geometry.kml` · `data/raw/berkeley_taxparcels_2026-08-12.geojson` ·
  `databases/berkeley_housing_v2.db` (`v_projects_flat`, `project_geometries`, `project_versions`,
  `documents`) · `data.cityofberkeley.info/resource/9a47-nj4i.json`.
