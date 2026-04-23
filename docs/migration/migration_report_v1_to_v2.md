# Migration Report: v1 → v2

**Executed:** 2026-04-22
**Status:** ✅ COMPLETE (Phase 0-3 Reversible)
**v1 Database:** `databases/berkeley_housing_analysis.db` (unchanged)
**v2 Database:** `databases/berkeley_housing_v2.db` (1.46 MB)

---

## 1. Repo Inventory Summary

### Databases
| Database | Size | Purpose |
|----------|------|---------|
| `berkeley_housing_analysis.db` | 1.0 MB | v1 legacy (174 projects, flat schema) |
| `berkeley_housing_v2.db` | 1.46 MB | v2 normalized (174 projects, 17 tables) |
| `berkeley.db` | 50 MB | Parcels + business licenses |
| `berkeley_housing_map.db` | 56 KB | Datasette deployment |

### Key Scripts Reading Legacy DB
| Script | Tables Used | Compat View Equivalent |
|--------|-------------|------------------------|
| `export_explorer_data.py` | projects, permit_events, permit_fees, project_documents | `v_projects_flat`, `v_project_events`, `v_project_documents` |
| `generate_kml.py` | projects (lat/lon, height, status) | `v_projects_flat`, `v_project_geometries_current` |
| `generate_apr.py` | projects | `v_projects_flat` |

### Schema Files Created
- `schema/core.sql` (28 KB) - 17 tables, 17 vocabulary tables
- `schema/vocabularies_berkeley.sql` (27 KB) - Berkeley-specific seeds
- `schema/views_compat.sql` (19 KB) - 7 compatibility views

---

## 2. Migration Map Summary

### Projects Table (54 columns → normalized)

| v1 Column Group | v2 Tables |
|-----------------|-----------|
| Identity (address, lat, lon) | `projects` |
| Program (units, height) | `project_versions`, `unit_program` |
| Affordability (vli_units) | `unit_program_affordability` |
| Timeline (filed, entitled, bp_issued, co_date) | `project_events` |
| Stakeholders (developer, architect, owner) | `organizations`, `project_participants` |
| Permits | `permits` |
| Geography | `project_geometries` (as GeoJSON) |
| Documents | `documents` |

### Data Quality Issues Found
| Issue | Count | Resolution |
|-------|-------|------------|
| Duplicate addresses | 3 | Appended `(id:N)` suffix |
| Orphan permits (no project) | 3 | Skipped |
| Orphan events (no project) | 12 | Skipped |
| Orphan documents (no project) | 17 | Skipped |
| Negative unit count | 1 | Set to 0 |

### Open Questions Resolved
1. **Bedroom breakdown:** Not available; using placeholder `bedroom_count=1`
2. **APN coverage:** 154/174 (88%) have APN
3. **Document URLs:** 0/1423 have URLs; migrated as `url_status='unknown'`
4. **sfyimby_projects:** Not migrated (kept as side-table)

---

## 3. Files Created/Changed

### Created
| File | Purpose |
|------|---------|
| `schema/core.sql` | Normalized schema (17 tables) |
| `schema/vocabularies_berkeley.sql` | Berkeley vocabulary seeds |
| `schema/views_compat.sql` | 7 compatibility views |
| `docs/migration-plan.md` | 6-phase migration plan |
| `docs/migration/v1_to_v2_column_map.md` | Detailed column mapping |
| `docs/migration/migration_report_v1_to_v2.md` | This report |
| `scripts/migration/migrate_v1_to_v2.py` | Migration script |
| `databases/berkeley_housing_v2.db` | v2 normalized database |

### Unchanged
- `databases/berkeley_housing_analysis.db` (v1 - production, untouched)
- All existing scripts (not modified)

---

## 4. Validation Results

### Count Comparison
| Metric | v1 | v2 | Match |
|--------|---:|---:|:-----:|
| Projects | 174 | 174 | ✅ |
| Total Units | 12,717 | 12,718 | ⚠️ (+1 from -1→0 fix) |
| VLI Units | 968 | 968 | ✅ |
| Permits | 114 | 118 | ✅ (added from building_permits) |
| Events | 2,306 | 2,605 | ✅ (added date column events) |
| Documents | 1,423 | 1,406 | ⚠️ (17 orphans skipped) |

### Integrity Checks
| Check | Result |
|-------|--------|
| Foreign key violations | ✅ None |
| Multiple current versions per project | ✅ None |
| Multiple current geometries per (project, type) | ✅ None |
| Non-proposal versions without source_event_id | ℹ️ 120 (expected - no entitlement event) |
| Duplicate organizations | ✅ None |

### Compatibility Views
| View | Row Count | Status |
|------|----------:|:------:|
| `v_projects_flat` | 174 | ✅ |
| `v_project_permits` | 118 | ✅ |
| `v_project_events` | 2,605 | ✅ |
| `v_project_geometries_current` | 165 | ✅ |
| `v_project_unit_mix` | 174 | ✅ |
| `v_project_affordability` | 164 | ✅ |

---

## 5. Unresolved Questions

### Requires Your Decision

1. **120 projects without source_event_id**: These are projects that don't have an `entitlement_approved` event in the data. Should we:
   - (a) Leave as-is (current)
   - (b) Create synthetic entitlement events from `entitled` date column
   - (c) Change version_type from `entitled` to `proposal` for these

2. **3 duplicate addresses**: Renamed with ID suffix. Should we:
   - (a) Keep renamed (current)
   - (b) Merge the duplicates
   - (c) Mark as different project phases

3. **SB35/SB330/AB2011 flags**: Not directly mapped to v2 schema. Should we:
   - (a) Add to `projects` table as custom columns
   - (b) Store as permit attributes
   - (c) Store as project tags (new table)

4. **is_uc_project flag**: Same question - add as custom column?

---

## Next Steps (Phase 4-6)

### Phase 4: Cutover (When Ready)
```bash
# Archive v1
mv databases/berkeley_housing_analysis.db archived/berkeley_housing_v1_$(date +%Y%m%d).db

# Promote v2
mv databases/berkeley_housing_v2.db databases/berkeley_housing_analysis.db
```

### Phase 5: Update Export Scripts
- Modify `export_explorer_data.py` to use `v_projects_flat`
- Modify `generate_kml.py` to use `v_project_geometries_current`
- Test outputs match

### Phase 6: Documentation
- Write `docs/architecture.md`
- Update `DATABASE_DOCUMENTATION.md`

---

*Migration report generated 2026-04-22*
