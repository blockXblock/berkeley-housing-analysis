# Morning Baseline Snapshot — 2026-05-03

First-ever CSV export of berkeley_housing_analysis.db. Captures state at start of morning session, after May 2 audit work.

## Contents

- **179 projects, 14,070 units total**
- Includes May 2 inserts: Modera Acheson Commons (205u), Logan Park (237u), 2065 Kittredge (189u), 2015 Blake (168u), 2072 Addison (66u)
- Includes May 2 fixes: 4 missing unit counts (+486u), project_category column, 1507 Josephine and 2705 Benvenue housing-loss flags
- sfyimby_projects: 10 records flipped to matched=True per May 2 reconciliation

## Tables Exported

| Table | Rows |
|-------|------|
| projects | 179 |
| sfyimby_projects | 249 |
| permit_events | 2,306 |
| project_documents | 1,423 |
| permit_fees | 441 |
| project_geometries | 165 |
| project_permits | 114 |
| building_permits | 94 |
| vocabulary_geometry_types | 9 |
| data_collection_log | 1 |

## Restoration

```bash
for f in *.csv; do sqlite-utils insert <new.db> ${f%.csv} $f --csv; done
```

Verify schema.sql matches target database schema before restoring.

## Context

See `data/raw/accela_research/2026-05-02_modera_and_sfyimby_candidates.md` for the journalism context behind the May 2 additions.
