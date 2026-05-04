# Post-v8-KML Snapshot — 2026-05-03

Captures DB state after May 3 morning session. 179 projects, 14,070 units.

## Session changes since morning baseline:

- People's Park L-shape recovered to project_geometries (project 177, building_footprint type)
- 5 May 2 inserts now have geometries (Modera 178 synthetic, Logan Park 179 + Kittredge 180 + Blake 181 + Addison 182 apn_parcel)
- 8 no_coords projects recovered with parcel polygons (173, 166, 172, 176, 175, 168, 169, 174)
- Project 127 (2820 San Pablo) resolved with SFYIMBY data — Cork-Mayo developer, Studio KDA architect, 1 unit, mixed_use_minimal_housing category
- Project 167 (Poet's Place, 2435 San Pablo) provisional synthetic with city APR APN 056 192802001
- Color scheme flipped to convention (Completed=green, Under Construction=blue)
- UC override changed from gold to purple
- Line-weight channel added by geometry source (1pt synthetic, 1.5pt parcel, 2.5pt hand-traced)
- Pipeline_stage backfilled for 178-182

## Findings logged in data_quality_followups.md:

- 2 duplicate-project pairs (25/115, 113/118) — needs resolution
- 3 projects deferred from KML (115, 118, 167)
- 3 polygon issues from spot-check (2435 San Pablo, 2131 University, 2680 Bancroft)
- parcel data refresh needed (Aug 2019 file misses post-2019 completions including Modera)
- city_apr_2025_table_a2.csv discovered as fresher APN source

## Tables Exported

| Table | Rows |
|-------|------|
| projects | 179 |
| project_geometries | 180 |
| sfyimby_projects | 249 |
| permit_events | 2,306 |
| project_documents | 1,423 |
| permit_fees | 441 |
| project_permits | 114 |
| building_permits | 94 |
| vocabulary_geometry_types | 9 |
| data_collection_log | 1 |

## Restoration

```bash
for f in *.csv; do sqlite-utils insert <new.db> ${f%.csv} $f --csv; done
```

Verify schema.sql matches target database schema before restoring.
