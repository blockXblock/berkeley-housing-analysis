# Data Quality Followups

Records in `berkeley_housing_analysis.db` needing manual research.

---

## 2903 ADELINE St

| Field | Value |
|-------|-------|
| **Permit** | ZP2025-0006 |
| **Current units** | 0 |
| **Current category** | housing_addition |
| **Status** | Corrections Pending Applicant |

**What we know:**
- Description: "Use Permit with Public Hearing to legalize conversion of an existing commercial space into residential use"
- This is an after-the-fact permit to legalize an existing commercial-to-residential conversion

**What we need to find out:**
- How many residential units were created?
- Is this a single unit (SFR/ADU) or multiple units?

**Where to look:**
- Accela permit ZP2025-0006
- Search: https://aca.cityofberkeley.info/CitizenAccess/ for permit details and application documents

---

## Berkeley Parcel Data Refresh (High Priority)

| Field | Value |
|-------|-------|
| **Current source** | `data/reference/berkeley_parcels.csv` |
| **Date range** | 2004-05-10 to 2019-08-26 |
| **Rows** | 29,003 unique parcels |

**Problem:**
The current parcel reference file is dated August 2019. Projects completed or subdivided after this date have missing or incorrect APN matches:

- **Modera Acheson Commons (project 178):** 4 APNs not found (057-2046-008-03, -008-02, -006-00, -010-00). Adjacent parcels 057 204600804 and 057 204601101 exist at related addresses, suggesting post-construction parcel renumbering.
- Other recent completions may be similarly affected.

**Impact:**
- Projects use synthetic fallback rectangles instead of actual parcel polygons
- KML visualization less accurate for 2019+ completions

**Action required:**
1. Download current parcel data from Alameda County Assessor or City of Berkeley GIS
2. Re-run parcel import for projects with `geometry_type_id = 9` (synthetic_footprint)
3. Specifically re-match Modera APNs after refresh

**Source options:**
- Alameda County GIS: https://www.acgov.org/acdata/
- City of Berkeley Open Data: https://data.cityofberkeley.info/

---

## Duplicate Projects Discovered May 3 2026 (High Priority)

Two pairs of duplicate projects identified during KML regeneration:

| Address | Project A | Permit A | Project B | Permit B | Same APN |
|---------|-----------|----------|-----------|----------|----------|
| 2455 Telegraph Ave | 25 | PLN2025-0066 | 115 | ZP2026-0015 | 055 187502900 |
| 2138 Kittredge St | 113 | ZP2026-0006 | 118 | ZP2024-0114 | 057 202901500 |

Each pair shares the same APN but has different permit numbers and likely different dates. The geometry table's `superseded_by` column was pointing across duplicate projects, suggesting the duplication originated from the matching script that links projects to the parcel import.

**Resolution options for next session:**
1. Determine which member of each pair is canonical (older permit? newer? both valid phases?)
2. Decide whether to merge (combine info, drop one) or keep separate (mark relationship)
3. Audit remaining 177 projects for similar duplicates by APN: which APNs appear on multiple project rows?
4. Investigate why the duplicates were created — likely a matching-script bug that re-imports SFYIMBY entries against existing projects without de-duplication

**Affected today:** Projects 115 and 118 are excluded from KML v8 because their geometry rows were incorrectly cross-referencing the other project's data. Their parcel polygons exist in berkeley_parcels.csv but unification needs to happen first.

---

## Pending KML Inclusions

Three projects deliberately excluded from KML v8 (2026-05-03) pending resolution:

| Project | Address | Issue | Path to Resolution |
|---------|---------|-------|-------------------|
| 115 | 2455 Telegraph Ave | Duplicate of project 25 | Resolve duplicate-project issue above |
| 118 | 2138 Kittredge St | Duplicate of project 113 | Resolve duplicate-project issue above |
| 167 | 2435 San Pablo Ave | Synthetic geometry only | Refresh parcel data to get APN 056 192802001 polygon |

**Note:** Project 167 IS included in KML v8 with a provisional synthetic rectangle at interpolated coordinates. Projects 115 and 118 are fully excluded until duplicate resolution.

---

## Polygon Improvements Identified During May 3 Spot-Check

### 2680 Bancroft Way (Bancroft Hotel) — Polygon Overlaps Adjacent Parcel

Current polygon (13-vertex apn_parcel from April 25 import) extends ~40m east to cover 2300 College Ave at the College/Bancroft corner. Per spot-check 2026-05-03:

- **2680 Bancroft** = the Bancroft Hotel (historic, permit to reconfigure into residences)
- **2660 Bancroft** = parking lot (possibly with permit)
- **2300 College** = separate building at College/Bancroft corner

**Likely causes (need to verify):**
1. The assessor parcel really does span Bancroft + College corner — polygon technically correct but visually misleading
2. The parcel polygon is wrong (wrong APN matched, or wrong shape)
3. There's a separate project at 2300 College that should be its own DB entry

**Resolution path next session:**
1. Look up APN(s) for 2680 Bancroft and 2300 College at Berkeley GIS / Alameda Assessor
2. If one parcel: hand-trace the Bancroft Hotel building footprint and round-trip into project_geometries (using People's Park pattern from earlier today)
3. If separate parcels: import the correct parcel polygon for the hotel
4. Either way: investigate whether 2300 College has its own permit history that should be a separate project record

---

### Hand-Traced Footprints Progress (Updated 2026-05-03 evening)

**Completed:**
- ✓ 1950 Oxford St (project 170) — done 2026-05-03 evening
- ✓ 1974 Shattuck Ave (project 119) — done 2026-05-03 evening
- ✓ 2200 Bancroft Way (project 165) — done 2026-05-03 evening
- ✓ 2065 Kittredge St (project 180) — done 2026-05-03 evening

**Priority queue (iconic projects needing hand-traced footprints):**
1. **2400 Bowditch St (project 171)** — Next: tomorrow morning. See section below.
2. 2128 Oxford St / The Hub — UC project, complex site
3. 2190 Shattuck Ave / The Joseph — distinctive tower shape
4. Modera buildings — await parcel data refresh first (synthetic fallbacks due to 2019 parcel data)

### Systematic Polygon Spot-Check Needed

May 3 random spot-check of 6 projects found 3 with visible polygon issues (50%):
- **2435 San Pablo** (synthetic placement)
- **2131 University** (synthetic size)
- **2680 Bancroft** (parcel overlap)

**Future session priority:** Open KML in Google Earth and spot-check every placemark systematically. ~15 sec per project × 177 = ~45 min of focused review.

**Output:** A complete inventory of geometries that:
- Pass (no action needed)
- Need refinement (adjust position, size, or rotation)
- Need full replacement (wrong parcel, hand-trace required)

---

## Tomorrow's First Task — Fix 2400 Bowditch Polygon

| Field | Value |
|-------|-------|
| **Project ID** | 171 |
| **Address** | 2400 Bowditch St |
| **Units** | 750 |
| **Height** | 26 stories |
| **Status** | Pre-Application |
| **Type** | UC Berkeley project (Anna Head West site) |

**Issue identified during v9 evening spot-check:**
Current geometry is a synthetic 20m square placeholder. This is UC Berkeley's largest proposed student housing project (750 beds) and needs an accurate footprint for the KML visualization.

**Resolution plan:**
1. Obtain architect site plan from UC Capital Projects or SFYIMBY coverage
2. Hand-trace building footprint in Google Earth Pro
3. Export KML, round-trip into project_geometries using established workflow
4. Regenerate as KML v10
5. Estimated time: 20-30 min

---

## Tour Video Deployment (Next-Session Task)

Compressed Campanile-Adeline-Shattuck tour video is staged at:
`docs/kml_versions/campanile-adeline-shattuck-compressed.mp4` (69 MB, 4 Mbps, yuv420p, 30fps, faststart enabled)

Source recording at 186 MB also at:
`docs/kml_versions/campanile-adeline-shattuck.m4v`

**Tomorrow's deployment steps:**
1. Watch compressed video in QuickTime; compare to source. Verify quality acceptable for home-page embed.
2. If acceptable: back up existing `docs/berkeley-flyover.mp4`, replace with compressed file (using existing filename so HTML doesn't change).
3. Move 186 MB source recording to `data/raw/tour_recordings/` (do NOT commit — too large for GitHub).
4. Add `data/raw/tour_recordings/*.m4v` to `.gitignore`.
5. Commit, push origin dev.
6. Verify deployment on berkeleybuild.com (Cloudflare auto-deploys from GitHub).

**Future scaling consideration:**
10-20 tours at ~70 MB each = 700 MB–1.4 GB in repo history. Investigate Cloudflare R2 or Cloudflare Stream as alternative video hosting before scaling beyond 5 tours.

---

## KML Generator MultiPolygon Bug

| Field | Value |
|-------|-------|
| **File** | `scripts/generate_kml.py` |
| **Function** | `parse_geojson_coords()` (lines 48-67) |
| **Severity** | Low (no current data affected) |

**Problem:**
The `parse_geojson_coords()` function extracts only the first polygon's exterior ring from MultiPolygon geometries:

```python
elif geom_type == 'MultiPolygon':
    # Use first polygon's exterior ring
    return geom['coordinates'][0][0]  # ← Only first polygon!
```

For true multi-parcel assemblages (e.g., a project spanning 4 separate parcels stored as one MultiPolygon), only the first parcel would render in the KML.

**Current impact:**
Diagnostic run 2026-05-03 found:
- 149 MultiPolygon geometries in database
- **0 with more than 1 polygon** — all are single-polygon MultiPolygons (artifact of WKT→GeoJSON conversion)
- No data loss in current KML output

**Affected projects (if any added in future):**
None currently. But if multi-building projects like Modera are later stored as true MultiPolygons with multiple sub-polygons, they would render incompletely.

**Fix (when needed):**
Rewrite `parse_geojson_coords()` to iterate all polygons and emit multiple `<coordinates>` blocks, or restructure to emit multiple `<Placemark>` elements per project.

---

# Resolved Items

## 2820 San Pablo ✓

**Resolved:** 2026-05-03

| Field | Before | After |
|-------|--------|-------|
| **units** | 0 | 1 |
| **status** | Unknown | Entitled |
| **pipeline_stage** | Unknown | Entitled |
| **project_category** | housing_addition | mixed_use_minimal_housing |
| **developer** | (none) | Cork-Mayo Investments |
| **architect** | (none) | Studio KDA |

**Research source:** SFYIMBY 2024-11-14

**Summary:** Two-building mixed-use project at 2820 San Pablo Ave + 2821 10th Street. Building 1 (2821 10th St): 2-story office/R&D/light manufacturing + garage. Building 2 (2820 San Pablo): 4-story, one single-family dwelling + offices/R&D. Total 15,195 sf.

**Note:** Introduced new `project_category` value `mixed_use_minimal_housing` for projects that are primarily commercial with token housing (1-2 units). This avoids misleading counts when reported alongside large apartment projects.
