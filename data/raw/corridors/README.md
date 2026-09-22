# Corridors Zoning Update — parcel GIS (Raimi + Associates) — CPRA #26-2367

**Request** filed 2026-08-13 (`notes/2026-08-12_cpra_corridors_parcel_gis.md`); **granted 2026-08-26** (Planning,
NextRequest #26-2367) as an Esri **file geodatabase released as 99 loose component files** (no zip; the portal has no
bulk download). **Retrieved 2026-09-21** via the per-document `/download` endpoint with a signed-in session
(`scratch/2026-09-21/download_26-2367_gdb.sh`; needs a browser UA + Referer, and ~1.5 s between files or the portal
answers "Retry later"). Assembled into **`raimi_corridors.gdb/`** — 99 files, 5.0 MB, opens with pyogrio/GDAL.

| layer | features | fields | geometry | note |
|---|---|---|---|---|
| `housing_element_sites` | 382 | 56 | MultiPolygon Z(M) | 6th-cycle Housing Element sites inventory (request item 4) |
| `project_area_parcels_data` | 495 | 57 | MultiPolygon | per-parcel existing conditions, 3 corridors (item 1) |
| `project_area_parcels_use` | 332 | 5 | MultiPolygon | existing use |
| `project_area_parcels_zoning_gplu` | 335 | 7 | MultiPolygon | zoning + General Plan land use (item 5) |
| `project_area_parcels_dev_potential` | 335 | 8 | MultiPolygon | development-potential coding (item 2) |
| `project_area_parcels_rent_controlled` | 1,098 | 26 | MultiPolygon | rent-controlled flag layer |
| `Parcels_Opportunity_Sites_OpOnly` | 258 | 63 | MultiPolygon | opportunity sites + capacity attributes (items 2–3) |
| `ZoningDistricts` | 42 | 14 | MultiPolygon Z(M) | zoning district polygons |

CRS: WGS 84 / UTM zone 10N (compound). Raw, unmodified, not yet joined to anything. Read with
`pyogrio.read_dataframe('data/raw/corridors/raimi_corridors.gdb', layer=...)`.
The `.gdb` folder is the record; do not add files to it.
