# Polygon Ingestion Plan (KML → v2 project_geometries)
**Drafted:** 2026-05-07
**Status:** 🟡 PLAN — not yet executed
**Source:** `docs/berkeley_skyline.kml` (canonical, currently v10)
**Target:** `databases/berkeley_housing_v2.db` (`project_geometries` + `structures` tables)

---

## 1. Goal and Scope (Phase 1)

Extract polygons from the canonical KML and load them into v2's `project_geometries` table, with multi-building cases properly split into `structures` rows. Build a **repeatable workflow** so this can be run after each round of polygon edits in Google Earth Pro.

### In scope
- Parse polygons from `docs/berkeley_skyline.kml`
- Match KML placemarks to v2 projects by address
- Handle multi-building cases (Ashby BART 1/2/3, Modera buildings, towers)
- Insert as `project_geometries` rows with provenance and `is_current=1`
- Mark prior centroid-only rows as `is_current=0` where polygons supersede
- Validate against parcel boundaries (Berkeley ArcGIS endpoint) as quality gate
- Flag vertex counts outside expected range as quality concern

### Not in scope (Phase 1)
- Parcel boundary conflict resolution (Phase 2)
- Historical project data error correction (Phase 3)
- PDF architectural drawing ingestion (Phase 4)
- Structural engineering schema for materials/energy/loads (Phase 5)

---

## 2. Source and Target

### Source: `docs/berkeley_skyline.kml`

Currently v10 (commit `9479441` on origin/main). 179 placemarks, 1 top-level Folder ("Housing Projects"). Polygons stored as KML `<Polygon><outerBoundaryIs><LinearRing><coordinates>` with `lon,lat,alt` triples.

Hand-traced polygons exist for approximately 12-15 high-priority projects. The remainder are parcel-derived approximations or single-point centroids extruded to building heights.

### Target tables in v2

| Table | Role |
|-------|------|
| `project_geometries` | One row per polygon, FK to projects, optional FK to structure |
| `structures` | One row per discrete building, FK to projects |
| `vocabulary_geometry_types` | Defines `centroid`, `parcel_polygon`, `building_footprint` etc. |
| `vocabulary_structure_types` | Defines `main`, `tower`, `podium`, `building`, etc. |
| `vocabulary_confidence_types` | Defines confidence levels for provenance |

### Geometry storage format (open question)

SQLite has no native geometry type. Options:

1. **WKT** (Well-Known Text): `POLYGON((-122.26 37.86, ...))` — text, simple, queryable with regex
2. **GeoJSON**: `{"type":"Polygon","coordinates":[[[-122.26, 37.86], ...]]}` — text, web-friendly, JSON-queryable in newer SQLite
3. **SpatiaLite**: SQLite extension with proper geometry types — most powerful, adds dependency

**Decision pending.** Recommendation: GeoJSON for web-friendliness; supported by Datasette for rendering, by Folium for maps, by ArcGIS for queries.

---

## 3. Workflow (Phase 1)

Five-step ingestion pipeline. Designed to be re-run after each KML update.

### Step 1: Parse KML

Read `docs/berkeley_skyline.kml`, extract per-placemark:
- `name` (used for matching)
- `description` (HTML-encoded metadata for verification)
- Polygon coordinates (outer boundary + any inner boundaries)
- Vertex count
- Computed centroid for fallback comparison

Output: in-memory list of placemark records.

Tools: Python `xml.etree.ElementTree` or `fastkml` library.

### Step 2: Match placemarks to projects

For each placemark name:
1. Try exact match on `projects.canonical_address`
2. Try normalized match (uppercase, abbreviation expansion, "St" vs "Street")
3. Detect multi-building suffix (e.g., "Ashby BART 1", "Modera Building D")
4. Map suffixed placemarks to parent project + structure label
5. Flag unmatched placemarks for human review

Output: each placemark either matched (project_id + optional structure_label) or quarantined.

### Step 3: Classify each polygon

For each matched placemark, determine:
- **Geometry type:** `building_footprint` for hand-traced; `parcel_polygon` for parcel-derived; `centroid_extruded` for centroid+height
- **Confidence:** `high` for hand-traced from architectural plans; `medium` for parcel-derived; `low` for centroid approximations
- **Source attribution:** `asserted_by='jgage_handtrace_DATE'` for hand-edits; `asserted_by='parcel_arcgis_DATE'` for parcel-derived

### Step 4: Insert with provenance

For each classified polygon:
1. If a `structures` row is needed (multi-building case), insert it first; capture `structure_id`
2. Mark prior `is_current=1` row for this (project, geometry_type) as `is_current=0` if it would conflict with the unique constraint
3. Insert new `project_geometries` row with `is_current=1`
4. Populate provenance fields

Use a transaction so partial failure rolls back.

### Step 5: Validate

Per-polygon validation checks (all flag warnings, none block insertion):
- **Within Berkeley bounds:** lat 37.84–37.91, lon -122.32 to -122.23
- **Closed polygon:** first vertex = last vertex
- **Reasonable vertex count:** 4–50; outside flags for cleanup
- **Parcel containment:** polygon centroid falls within at least one Berkeley parcel (queries Berkeley ArcGIS at `https://gis.cityofberkeley.info/arcgis3/rest/services/Public/GISPortal/MapServer/1`)
- **Self-intersection:** polygon doesn't cross itself

Aggregate report: per-project pass/fail, list of warnings.

---

## 4. Multi-Building Handling

Some projects have multiple buildings represented as separate KML placemarks.

### Examples

| Project | Buildings | Notes |
|---------|-----------|-------|
| Ashby BART (id 151) | 3 | KML now has "Ashby BART 1/2/3" as separate placemarks (added 2026-05-07) |
| Modera Acheson Commons (id ?) | 4 | "Building D" was a discovery; should be 4 buildings |
| 2400 Bowditch UC dorm (id 1) | Multi-tower | Architectural plans show podium + towers |
| 2200 Bancroft (id ?) | Multiple | Hand-traced plus needs structure split |

### Insertion pattern

For each multi-building case:
1. Insert one `structures` row per building (label = "Building 1" / "Tower A" / "Ashby BART 1" etc., with structure_type from vocabulary)
2. Insert one `project_geometries` row per building, with `structure_id` set
3. Each structure can have its own height, stories, sqft from KML description or future architectural data

The existing project-level centroid stays in `project_geometries` with `structure_id=NULL` and may be marked non-current.

---

## 5. Vertex Cleanup as Recurring Concern

Hand-edited polygons in Google Earth Pro frequently end up with too many vertices — clicking small movements while tracing creates micro-segments. This makes geometry unwieldy and rendering inefficient.

### Symptoms
- Vertex counts in the 100s or 1000s for what should be simple rectangular footprints
- Renders slowly in Earth and other viewers
- Wastes storage in the database

### Workflow strategy
- **Phase 1 (now):** Flag any polygon with >50 vertices in the validation report; do not auto-simplify
- **Phase 2 (future):** Add a Douglas-Peucker simplification pass with a configurable tolerance, applied to polygons that exceed the threshold
- **Phase 3 (future):** Snap vertices to parcel boundaries where appropriate

This must remain optional and reviewable — automated simplification can lose meaningful detail.

---

## 6. Provenance Conventions

Every inserted row populates the provenance mixin:

| Field | Phase 1 default |
|-------|-----------------|
| `asserted_by` | `'kml_ingest_2026-05-07'` plus the editor (e.g., `'jgage_handtrace'` if known per-polygon) |
| `asserted_at` | ISO timestamp of ingestion run |
| `confidence_type_id` | High for hand-traced from architectural plans; Medium for parcel-derived; Low for centroid approximations |
| `source_document_id` | NULL for KML; populated when polygons come from architectural PDFs (Phase 4) |

The KML file itself can be added as a `documents` row before ingestion, providing a `source_document_id` for all polygons in that batch.

---

## 7. Open Questions for Human Decision

| Question | Options | Status |
|----------|---------|--------|
| Geometry storage format | WKT vs GeoJSON vs SpatiaLite | Unresolved |
| When to mark prior centroids non-current | Always vs only when polygon supersedes | Unresolved |
| Multi-building structure labels | "Building 1" vs "Tower A" vs project-specific naming | Per-project decision |
| Vertex-count threshold for cleanup flag | 30, 50, 100, other | Suggested 50 |
| Parcel containment as block vs warning | Block insertion or warn only | Suggested warn only |

---

## 8. CC Task Sections

CC can perform empirical analysis to fill in these sections before the plan goes to execution.

### 8a. KML inventory (CC fills)

Prompt for CC:
> Run `grep -c "<Placemark>" docs/berkeley_skyline.kml` to confirm placemark count.
> Run a Python script to extract every placemark name and vertex count from the file.
> Report: total placemarks, distribution of vertex counts (min/median/max), placemarks with >50 vertices, placemarks with <4 vertices.

Output goes here:
<!-- CC TO FILL: KML inventory results -->

### 8b. Match analysis (CC fills)

Prompt for CC:
> For each placemark name in the KML, query v2: `SELECT id FROM projects WHERE canonical_address = ?`. Count exact matches and unmatched.
> For unmatched placemarks, try uppercase + remove punctuation match. Report remaining unmatched.
> Report: count matched, count multi-building (suffix detected), count quarantined.

Output goes here:
<!-- CC TO FILL: Match analysis results -->

### 8c. Polygon coverage in v2 (CC fills)

Prompt for CC:
> Run: `sqlite3 databases/berkeley_housing_v2.db "SELECT geometry_type_id, COUNT(*) FROM project_geometries GROUP BY geometry_type_id"`.
> Run: `sqlite3 databases/berkeley_housing_v2.db "SELECT vocabulary_geometry_types.code, COUNT(*) FROM project_geometries JOIN vocabulary_geometry_types ON vocabulary_geometry_types.id = project_geometries.geometry_type_id GROUP BY vocabulary_geometry_types.code"`.
> Report current state of geometry types in v2 before ingestion.

Output goes here:
<!-- CC TO FILL: Pre-ingestion v2 geometry coverage -->

### 8d. Multi-building candidate identification (CC fills)

Prompt for CC:
> Read placemark names from `docs/berkeley_skyline.kml`.
> Identify placemarks whose names suggest a multi-building case: contains "Building [A-Z]" or "[1-9]" suffix or "Tower" or "Podium".
> Report list of detected multi-building placemarks.

Output goes here:
<!-- CC TO FILL: Multi-building candidates -->

### 8e. Bounds and sanity checks (CC fills)

Prompt for CC:
> For each polygon in `docs/berkeley_skyline.kml`, compute bounding box.
> Flag any polygons whose bbox is outside Berkeley (lat 37.84–37.91, lon -122.32 to -122.23).
> Flag any polygons that are not closed (first vertex != last vertex).

Output goes here:
<!-- CC TO FILL: Bounds and sanity check results -->

---

## 9. Future Phases (one paragraph each)

### Phase 2: Parcel boundary quality and conflict detection

After Phase 1 polygons are in v2, add a quality gate that checks each polygon against Berkeley parcel boundaries. When a polygon overlaps multiple parcels, flag for review. When parcels themselves have conflicting boundaries (a real GIS issue), follow industry standards from local government GIS practice. Standards research needed: how do Berkeley/Alameda County GIS departments document parcel boundary uncertainty? OGC standards (`gml:dataQuality`)? FGDC metadata? This is research before implementation.

### Phase 3: Historical project data error correction

Older projects in the database have varying data quality — completion dates may be approximate, addresses may have been renumbered, project records may conflate multiple developments. Build a workflow for tracking known errors and corrections with full provenance. Use `is_current` flag patterns from v2 to preserve old assertions while adding corrected ones. Error catalog as a tracked document. Cleanup is ongoing, not a one-shot.

### Phase 4: PDF architectural drawing ingestion

City PDFs containing architectural drawings include footprint geometry, building heights, materials specifications, energy ratings, and other detail. Build an automated workflow:
1. Identify URLs of architectural PDFs in the city's document storage (Accela, etc.)
2. Download via existing `documents` table provenance
3. Use AI tools (Claude API, NotebookLM, or PDF-specific tools) to extract structured data — this is OCR plus understanding plus structuring
4. Store extracted geometry and properties in `structures`, `project_geometries`, and new tables for materials/energy specs

This is research-level work. Standards exist: BIM/IFC for buildings, COBie for facility data, gbXML for energy modeling. Schema design needs domain expertise.

### Phase 5: Structural engineering schema

Storing materials, energy, structural loads, and engineering specifications requires schemas grounded in industry standards. IFC (Industry Foundation Classes) is the open BIM standard. gbXML for energy. Real research needed before designing tables. Adding this without studying standards risks creating bespoke schemas incompatible with broader civic-tech data exchange.

---

## 10. Status and Next Actions

**Status:** Plan drafted. Empirical sections (8a-8e) await CC input.

**Next action:** Hand plan to CC with the prompts in §8 to fill in placeholder sections. Then review filled plan and decide on open questions in §7.

**After empirical fill:** Decide on geometry storage format (§7), draft the actual ingestion script, run on a small test subset before the full 179 placemarks.

---

*Drafted 2026-05-07. Phase 1 of 5.*
