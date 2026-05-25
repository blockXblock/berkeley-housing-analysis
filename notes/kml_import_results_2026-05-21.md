# KML → v2 Geometry Import Results (v2 — Schema Fix)

**Generated:** 2026-05-21T15:31:15.556927
**Transaction Status:** COMMIT

---

## 1. Working Database

| Item | Value |
|------|-------|
| Source DB | `databases/berkeley_housing_v2.db` |
| Working DB | `/tmp/berkeley_housing_v2_kml_import.db` |
| Source SHA256 | `97d978b60534ab82629cd18104906fc11a5eb8b1846662c0a383fb243a6bfce6` |
| Working SHA256 (pre-write) | `97d978b60534ab82629cd18104906fc11a5eb8b1846662c0a383fb243a6bfce6` |

## 2. Schema Fix Applied

**Old index (dropped):**
```sql
CREATE UNIQUE INDEX idx_one_current_geometry
ON project_geometries(project_id, geometry_type_id)
WHERE is_current = 1
```

**New index (created):**
```sql
CREATE UNIQUE INDEX idx_one_current_geometry
    ON project_geometries(project_id, geometry_type_id, COALESCE(structure_id, 0))
    WHERE is_current = 1

```

## 3. Vocabulary Row Status

| code | id | status |
|------|-----|--------|
| synthetic_polygon | 8 | inserted |

## 4. style_source → geometry_type_id Mapping

| style_source | geometry_type_id | code |
|--------------|------------------|------|
| parcel | 1 | apn_parcel |
| synthetic | 8 | synthetic_polygon |
| footprint | 4 | building_footprint |

## 5. Confidence Mapping

| style_source | confidence_type_id | code |
|--------------|-------------------|------|
| footprint | 1 | high |
| parcel | 2 | medium |
| synthetic | 3 | low |

## 6. Import Worklist Summary

| Metric | Value |
|--------|-------|
| Total placemarks | 184 |
| Imported | 179 |
| Skipped | 5 |

## 7. Multi-Part Projects

| Project ID | Address | Placemark Count |
|------------|---------|-----------------|
| 151 | Ashby BART | 3 |
| 165 | 2200 BANCROFT Way | 2 |
| 171 | 2400 BOWDITCH St | 2 |
| 177 | 2556 HASTE St | 2 |

### Structures Created

| structure_id | project_id | label | height_meters |
|--------------|------------|-------|---------------|
| 1 | 171 | North | 85.3 |
| 2 | 171 | South | 45.0 |
| 3 | 177 | Main | 40.2 |
| 4 | 177 | South | 35.0 |
| 5 | 165 | North | 79.5 |
| 6 | 165 | South | 36.0 |
| 7 | 151 | Building 1 | 24.0 |
| 8 | 151 | Building 2 | 24.0 |
| 9 | 151 | Building 3 | 24.0 |

## 8. Centroid Supersession

| Metric | Value |
|--------|-------|
| Centroids superseded (is_current=0) | 174 |

## 9. Verification Results

| Check | Expected | Actual | Passed |
|-------|----------|--------|--------|
| 7d-a: Structures inserted | 9 | 9 | ✓ |
| 7d-b: Geometries inserted | 179 | 179 | ✓ |
| 7d-c: Centroid rows demoted (is_current=0) | ~174 | 174 | ✓ |
| 7d-d: Centroid rows remaining current | ~5 | 5 | ✓ |
| 7d-e: Total is_current=1 rows | 184 | 184 | ✓ |
| 7d-f: Project 171 multi-part consistency | 2 structures, 2 geometries | 2 structures, 2 geometries | ✓ |
| 7d-f: Project 177 multi-part consistency | 2 structures, 2 geometries | 2 structures, 2 geometries | ✓ |
| 7d-f: Project 165 multi-part consistency | 2 structures, 2 geometries | 2 structures, 2 geometries | ✓ |
| 7d-f: Project 151 multi-part consistency | 3 structures, 3 geometries | 3 structures, 3 geometries | ✓ |
| 7d-g: Geometry 180 structure label | North | North | ✓ |
| 7d-g: Geometry 356 structure label | South | South | ✓ |
| 7d-g: Geometry 181 structure label | Main | Main | ✓ |
| 7d-g: Geometry 357 structure label | South | South | ✓ |
| 7d-g: Geometry 182 structure label | North | North | ✓ |
| 7d-g: Geometry 358 structure label | South | South | ✓ |
| 7d-g: Geometry 353 structure label | Building 1 | Building 1 | ✓ |
| 7d-g: Geometry 354 structure label | Building 2 | Building 2 | ✓ |
| 7d-g: Geometry 355 structure label | Building 3 | Building 3 | ✓ |
| 7d-h: Spot-check geometry 184 (parcel) | Valid Polygon, ~5 vertices, closed | Polygon, 5 vertices, closed=True | ✓ |
| 7d-h: Spot-check geometry 187 (parcel) | Valid Polygon, ~5 vertices, closed | Polygon, 5 vertices, closed=True | ✓ |
| 7d-h: Spot-check geometry 186 (synthetic) | Valid Polygon, ~5 vertices, closed | Polygon, 5 vertices, closed=True | ✓ |
| 7d-h: Spot-check geometry 191 (synthetic) | Valid Polygon, ~5 vertices, closed | Polygon, 5 vertices, closed=True | ✓ |
| 7d-h: Spot-check geometry 180 (footprint) | Valid Polygon, ~5 vertices, closed | Polygon, 5 vertices, closed=True | ✓ |

**All verifications passed:** Yes

## 10. Post-Commit Summary

| Metric | Value |
|--------|-------|
| Total project_geometries rows | 358 |
| Total structures rows | 9 |
| Total vocabulary_geometry_types rows | 8 |

### project_geometries by Type and Status

| code | is_current | count |
|------|------------|-------|
| apn_parcel | 1 (current) | 159 |
| building_footprint | 1 (current) | 9 |
| centroid_point | 0 (superseded) | 174 |
| centroid_point | 1 (current) | 5 |
| synthetic_polygon | 1 (current) | 11 |

## 11. Skipped Placemarks

| Placemark | Skip Reason |
|-----------|-------------|
| 2740 Shasta Rd · In Review | Excluded: project 86 (2740 SHASTA Rd) - duplicate needs review |
| 2740 Shasta Rd · In Review | Excluded: project 86 (2740 SHASTA Rd) - duplicate needs review |
| Dharma University | No matched project |
| Innovation Zone - North - Bakar | No matched project |
| Innovation Zone - South | No matched project |

## 12. Anomalies / Warnings

(none)
