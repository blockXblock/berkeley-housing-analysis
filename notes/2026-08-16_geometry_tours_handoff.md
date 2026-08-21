# Hand-off — KML geometry, flyover tours & building footprints (for the next CC)

**Written:** 2026-08-16. **For:** a Claude Code session dedicated to the KML geometry / tour / footprint
thread. **Repo:** `~/berkeley-data` (git, branch `dev`; deploys to berkeleybuild.com). **Read `CLAUDE.md`
and `PROGRESS.md` first** (dev-only, snapshot-before-write, John owns all pushes/deploys). Everything below
is committed on `dev`, nothing pushed.

---

## 0. The goal
Re-record Berkeley's building **flyover tours** with the **newest, cleaned-up geometry** — accurate base
polygons and **readable labels** — and tell the **"drumbeat vs tower" story**: the steady carpet of small
projects (ADUs / Middle Housing) vs the few big towers. John records the final videos in Google Earth Pro
(Movie Maker) → the YouTube channel that feeds berkeleybuild.com.

## 1. The pipeline (how the pieces fit)
- **Canonical geometry:** `kml/geometry/geometry.kml` — **184 towers**, hand-edited extruded footprints,
  labels from `berkeley_housing_v2.db`. Served copy: `docs/geometry.kml` (republish after any change).
- **The drumbeat geometry:** `kml/geometry/adu-middle-housing.kml` — **876** ADU/Middle-Housing footprints
  (all ~1 story). Generator: `scripts/gen_adu_middle_housing.py`.
- **Camera-only tours:** `kml/tours/*.kml` — `<gx:Tour>` flight paths, NO polygons.
- **Packages (DERIVED):** `scripts/build_tour_package.py` splices a tour's `<gx:Tour>` into the canonical
  geometry → ONE self-contained `kml/tours/packages/<tour>__geom-<sha>.kml`. **`build_tour_package.py --all`
  regenerates every package.** NEVER hand-edit a package. Open a package in Google Earth Pro → play → record.
- **Served catalog:** `docs/tours.json` (generator `scripts/build_tours_manifest.py`, scans `kml/tours/`).
  Carries per-tour `flyto_legs`, `duration_s`, `package`, `needs_rerecord`, `video`, `canonical_geometry`.
- **KML source lives in `kml/` (tracked); `docs/` is the web-serve target** (per CLAUDE.md media rule).

## 2. What's DONE (commits on dev)
- **Tours deduped 18 → 11** (`c2a0cca`): removed 3 dup versions of "Longer Corridors" (kept `longerv2`),
  4 older UC-Dormitory versions (kept v5 = the `(4)` file, longest at 65s), and the older `Rebuilt-45s`.
  Cleaned two titles. `tours.json` in sync (0 broken, 0 orphans). The 11 kept tours (longest→shortest):
  Large Projects Orbit (528s) · Shattuck centerline (444s) · Longer Corridors (216s) · Adeline-Shattuck
  (146s) · Extended Dramatic (134s) · UC Dormitory (65s) · Elmwood-Bancroft-Shattuck (64s) · Pipeline 45s
  (62s) · Telegraph-Shattuck-Cedar (51s) · 15-sec Flyover (15s) · 10-sec Downtown (10s).
- **Restyle prototypes** (`aa9bde3`): `scripts/prototype_geometry_style.py` → **height-tiered translucent
  polygons** (drumbeat teal <8m / mid amber / tower red >25m) + **LOD-gated labels** (a Point at the
  building top with `<LabelStyle>` + `<Region>/<Lod>` so names fade in only when zoomed in; long names
  shortened). Two prototypes in `kml/geometry/prototypes/`: `proto_A_towers_10.kml` (10 tallest towers) and
  `proto_B_all_projects.kml` (**1,060** = 874 ADU/small + 132 mid + 54 towers — the drumbeat+towers view).
- **Footprint provenance + 2190 fix** (`00db399`, `0dcc28d`): see §4.
- **Landmark year-by-year KML** (`b7d6839`, `690d364`) — SEPARATE deliverable, not the tour skyline:
  `scripts/build_landmark_kml.py` → `kml/timeline/berkeley_landmarks_buildout.kml` (181 City landmarks,
  each a `<TimeSpan>` beginning at its true build year → Google Earth time-slider animates the build-out) +
  a `<gx:Tour>` auto-fly (13 stops, ~1.5 min). Plays in Google Earth Pro.

## 3. OPEN DECISIONS (John was evaluating the prototypes — get his call)
1. **Label color:** tier-colored (red/amber/teal) vs **white** (safer over aerial imagery). Prototype uses
   tier-colored; John to decide after viewing in Earth Pro.
2. **Canonical set for the tours:** keep the **184-tower skyline**, or move to the **full 1,060** (drumbeat
   + towers), or keep both as switchable layers. This drives the "just the big ones" vs "all projects" story.

## 4. Footprint accuracy — findings + fix-list
- **Hand-traces are mostly clean:** a spatial survey vs county parcels found **179/184 fine**, ~5 suspects.
- **Authority chain (settled):** the county **parcel** = the *lot* (clean GIS, but building sits inside it);
  the **architect site-plan PDF** = the authoritative *building* footprint for proposed/pipeline towers
  (most of ours), but it's a drawing → needs georeferencing; **aerial/LiDAR** for already-built. The
  architect **Tabulation Form 1.E** carries footprint *numbers* as machine-readable text (Lot Area × Lot
  Coverage → footprint).
- **2190 Shattuck FIXED** (`0dcc28d`): hand-trace was oversized/tapered (21,393sf, exceeded the lot) →
  replaced with the parcel rectangle (**20,127sf**, height preserved), matching the tabulation (lot 19,967,
  99% coverage). Validator now scores it 1.02 (ok).
- **2276 Shattuck is CORRECT as-is** — genuinely non-rectangular BY DESIGN (facade-retention project on an
  angled Shattuck/Bancroft corner lot; confirmed in the plan set). Do NOT "square it up."
- **Tabulation validator** (`0dcc28d`): `scripts/harvest_tabulation_footprints.py` →
  `data/reference/tabulation_footprints.csv`. Parses the 9 Tabulation Forms in v2 and cross-checks vs the
  hand-traces. **Priority fixes:** **2920 Shattuck** (trace 1.91× the architect footprint — way oversized)
  and **2601 San Pablo** (trace 0.20× — a tiny-box error, like **2955 Shattuck** from the survey). ⚠ Only
  **9/184** towers have a form; the geo-match is by address, so **spot-check the extreme flags** before
  editing (verify we matched the right building).
- **Data bug to fix (not geometry):** `geometry.kml`'s 2276 label says **336 units**; the plan set says
  **134**. Worth reconciling the label source (`relabel_geometry_from_v2.py`, from `v_projects_flat`).

## 5. NEXT STEPS (recommended order)
1. **Get John's two decisions** (§3: label color, 184 vs 1,060).
2. **Regenerate base polygons from county parcels** for the bulk skyline (clean, fast, kills hand-trace
   drift including subtle tapers) via `taxparcels` by canonical APN; **hand-refine only the hero towers**
   from their architect PDFs where lot ≠ building. Spot-check + fix 2920, 2601, 2955 first.
3. **Apply the restyle** (`prototype_geometry_style.py` logic) to the full canonical `geometry.kml`
   (tiered polygons + LOD labels), not just the 10-building prototype.
4. **Dedup the geometry version sprawl** in `kml/geometry/` (v5/v7/v8/v9, `Skyline`, `Berkeley-Skyline`,
   `docs__berkeley_skyline`, etc. — same cleanup we did for tours) + remove the stray `.DS_Store`.
5. **Republish** `docs/geometry.kml` + **`build_tour_package.py --all`** → fresh packages (new geom sha).
6. **Re-record** the 11 tours in Earth Pro Movie Maker → YouTube; update `tours.json` `video`/`needs_rerecord`.
- Consider **saving the footprint survey as a script** (§4's spatial check was run inline, not yet saved).
- The **architect PDFs** are on R2 (`documents.r2_url` in v2.db) — `pdftotext` + `pymupdf` both work locally;
  the Read tool renders PDF pages as images to view site plans.

## 6. Key files
- Geometry: `kml/geometry/geometry.kml` (canonical 184) · `adu-middle-housing.kml` (876) · `docs/geometry.kml`
- Tours: `kml/tours/*.kml` (11) · `kml/tours/packages/` · `docs/tours.json`
- Scripts: `scripts/build_tour_package.py` · `build_tours_manifest.py` · `prototype_geometry_style.py` ·
  `harvest_tabulation_footprints.py` · `build_landmark_kml.py` · `gen_adu_middle_housing.py` ·
  `relabel_geometry_from_v2.py` · `generate_kml.py`
- Prototypes: `kml/geometry/prototypes/{proto_A_towers_10, proto_B_all_projects, proto_footprint_compare}.kml`
- Data: `data/reference/tabulation_footprints.csv` · `data/raw/berkeley_taxparcels_2026-08-12.geojson` (parcel polygons) · `databases/berkeley.db` (parcel lat/lon)

## 7. Env & discipline
- Python: `/opt/miniconda3/envs/jupyter_env/bin/python`. PDF tools: `pdftotext`, `pymupdf`.
- APN joins: `housing_rules.to_canonical_apn(raw,"alameda")`.
- `geometry.kml` is the **hand-edited canonical** — edit it surgically; packages are DERIVED (regenerate,
  never hand-edit). git is the snapshot. `dev` only; **John owns all pushes/deploys**.
