# Cross-Directory Survey: Berkeley Civic Data Consolidation

**Generated:** 2026-04-30
**Purpose:** Inventory scattered Berkeley data work to inform consolidation into canonical `~/berkeley-data`

---

## Executive Summary

Four directories outside the canonical `~/berkeley-data` contain Berkeley civic data work. Most content is either:
- **Stale duplicates** of data now maintained in `~/berkeley-data`
- **Large media files** (PDFs, videos) that should be archived or moved
- **Valuable documentation** that should be preserved and integrated

**Total size across all four directories:** ~750MB
**Recommended to preserve:** ~150MB (docs + key media)
**Recommended to archive/discard:** ~600MB (duplicates, old exports)

---

## 1. ~/berkeley_data (underscore variant)

**Path:** `/Users/johngage/berkeley_data`
**Total size:** ~12MB
**Last meaningful activity:** December 2025
**Purpose:** Appears to be an early prototype directory, now superseded

### Structure
```
berkeley_data/
├── databases/           # Symlink → ~/berkeley-data/databases
├── data/               # Symlink → ~/berkeley-data/data
├── housing_projects.db  # 60KB, 84 projects (Dec 2025)
├── receipts/           # PDF receipts for data purchases
│   ├── berkeley_parcels_receipt.pdf
│   └── alameda_assessor_receipt.pdf
└── notes.txt           # Early project notes
```

### Key Findings
| Item | Status | Notes |
|------|--------|-------|
| `databases/` symlink | ✓ Points to canonical | No action needed |
| `data/` symlink | ✓ Points to canonical | No action needed |
| `housing_projects.db` | ⚠️ Stale | 84 projects vs 174 in current; superseded by `berkeley_housing_analysis.db` |
| `receipts/` | 📁 Preserve | Proof of data licensing/purchase |
| `notes.txt` | 📁 Review | May contain historical context |

### Recommended Actions
1. **Move** `receipts/` → `~/berkeley-data/docs/receipts/`
2. **Review** `notes.txt` for any useful context, then archive or delete
3. **Delete** `housing_projects.db` (superseded)
4. **Delete** symlinks and directory after migration

---

## 2. ~/berkeley-data-staging

**Path:** `/Users/johngage/berkeley-data-staging`
**Total size:** ~688MB
**Last meaningful activity:** March 2026
**Purpose:** Staging area for large media files not yet integrated

### Structure
```
berkeley-data-staging/
├── project_documents/
│   ├── 2190_shattuck/
│   │   └── 2190_Shattuck_Plans_Full.pdf   # 141MB architectural drawings
│   ├── 2440_shattuck/
│   │   └── plans_v2.pdf                    # 45MB
│   └── [15 other project folders]          # ~200MB total
├── site_tours/
│   ├── downtown_tour_2026-02-15.mp4        # 180MB
│   └── southside_tour_2026-01-22.mp4       # 95MB
├── council_meetings/
│   └── zab_2026-03-14_excerpt.mp4          # 25MB
└── temp/
    └── [various working files]              # ~2MB
```

### Key Findings
| Item | Size | Status | Notes |
|------|------|--------|-------|
| `2190_Shattuck_Plans_Full.pdf` | 141MB | 📁 Valuable | Full architectural set, referenced in project docs |
| `project_documents/` | ~390MB | 📁 Mixed | Some valuable, some duplicates |
| `site_tours/` | 275MB | ⚠️ Large | Useful but storage-heavy; consider external archive |
| `council_meetings/` | 25MB | 📁 Keep | ZAB meeting excerpt, useful reference |
| `temp/` | 2MB | 🗑️ Delete | Working files, no longer needed |

### Recommended Actions
1. **Move** `project_documents/` → `~/berkeley-data/data/project_documents/` (create if needed)
2. **Archive** `site_tours/` to external storage (Google Drive, S3) — too large for working directory
3. **Move** `council_meetings/` → `~/berkeley-data/data/media/council_meetings/`
4. **Delete** `temp/`
5. **Delete** directory after migration

---

## 3. ~/berkeley-housing-research

**Path:** `/Users/johngage/berkeley-housing-research`
**Total size:** ~35MB
**Last meaningful activity:** April 2026
**Purpose:** Quartz-based documentation site with valuable research notes

### Structure
```
berkeley-housing-research/
├── quartz/
│   └── content/
│       ├── Berkeley Data Assets.md          # Comprehensive data source inventory
│       ├── Pipeline Methodology.md          # How housing data is collected
│       ├── Claude Dialogues/
│       │   ├── 2026-03-15_schema_design.md   # Schema discussion transcript
│       │   ├── 2026-04-10_geometry_cleanup.md
│       │   └── 2026-04-22_apr_generation.md
│       └── Project Notes/
│           └── [12 project-specific notes]
├── .quartz-cache/                            # Build cache, can delete
└── package.json                              # Quartz dependencies
```

### Key Findings
| Item | Status | Notes |
|------|--------|-------|
| `Berkeley Data Assets.md` | 📁 **High value** | Lists all Berkeley open data sources with URLs and update frequencies |
| `Pipeline Methodology.md` | 📁 **High value** | Documents data collection workflow |
| `Claude Dialogues/` | 📁 Preserve | Historical context for design decisions |
| `Project Notes/` | 📁 Review | May overlap with project_documents in main repo |
| `.quartz-cache/` | 🗑️ Delete | Regeneratable |
| Quartz site itself | ⚠️ Decision | Keep if publishing publicly; otherwise extract content |

### Recommended Actions
1. **Move** `Berkeley Data Assets.md` → `~/berkeley-data/docs/data_sources.md`
2. **Move** `Pipeline Methodology.md` → `~/berkeley-data/docs/pipeline_methodology.md`
3. **Move** `Claude Dialogues/` → `~/berkeley-data/docs/design_decisions/`
4. **Review** `Project Notes/` — merge useful content into PROGRESS.md or project docs
5. **Delete** `.quartz-cache/`
6. **Decision needed:** Keep Quartz site for public documentation, or archive?

---

## 4. ~/berkeley-permit-pipeline

**Path:** `/Users/johngage/berkeley-permit-pipeline`
**Total size:** ~18MB
**Last meaningful activity:** February 2026
**Purpose:** Obsidian vault with project tracking notes and older data imports

### Structure
```
berkeley-permit-pipeline/
├── .obsidian/                               # Obsidian config
├── Projects/
│   ├── 2190 Shattuck.md                     # Project research notes
│   ├── 2440 Shattuck.md
│   └── [28 other project notes]
├── Data Imports/
│   ├── ActiveLandUse_2025-11-15.xlsx        # Old Accela export
│   ├── ActiveLandUse_2025-12-01.xlsx
│   └── ActiveLandUse_2026-01-10.xlsx        # Most recent
├── Templates/
│   └── Project Template.md
└── README.md
```

### Key Findings
| Item | Status | Notes |
|------|--------|-------|
| `Projects/` | 📁 Review | 30 project notes; may contain research not in database |
| `ActiveLandUse_*.xlsx` | ⚠️ Stale | Superseded by `accela_reports.db`; keep latest for reference |
| `.obsidian/` | 🗑️ Delete | Only needed if continuing Obsidian use |
| `Templates/` | 📁 Review | May inform standardized project documentation |

### Recommended Actions
1. **Review** `Projects/` — extract any research notes not captured in database
2. **Keep** `ActiveLandUse_2026-01-10.xlsx` as historical reference → move to `~/berkeley-data/data/archive/`
3. **Delete** older ActiveLandUse files (superseded)
4. **Archive** or delete Obsidian config (`.obsidian/`)
5. **Decision needed:** Continue using Obsidian for project notes, or consolidate into markdown in main repo?

---

## Comparison to Canonical ~/berkeley-data

| Content Type | Canonical Location | Found Elsewhere | Status |
|--------------|-------------------|-----------------|--------|
| SQLite databases | `databases/` | `berkeley_data/housing_projects.db` | Stale copy |
| Parcel/address CSVs | `data/reference/` | None | ✓ Canonical only |
| Project documents (PDFs) | Not yet organized | `berkeley-data-staging/project_documents/` | **Needs migration** |
| Media (videos) | None | `berkeley-data-staging/site_tours/` | **Needs decision** |
| Data source documentation | `docs/` | `berkeley-housing-research/quartz/` | **Needs migration** |
| Project research notes | None | `berkeley-permit-pipeline/Projects/` | **Needs review** |
| Design decision history | `docs/` (partial) | `berkeley-housing-research/Claude Dialogues/` | **Needs migration** |
| Data purchase receipts | None | `berkeley_data/receipts/` | **Needs migration** |

---

## Recommended Actions Summary

### Immediate (Low Risk)
| Action | Source | Destination | Size |
|--------|--------|-------------|------|
| Delete | `berkeley_data/housing_projects.db` | — | 60KB |
| Delete | `berkeley-data-staging/temp/` | — | 2MB |
| Delete | `berkeley-housing-research/.quartz-cache/` | — | ~5MB |
| Delete | `berkeley-permit-pipeline/ActiveLandUse_2025-*.xlsx` | — | ~3MB |

### Move to Canonical
| Action | Source | Destination | Size |
|--------|--------|-------------|------|
| Move | `berkeley_data/receipts/` | `docs/receipts/` | ~1MB |
| Move | `berkeley-data-staging/project_documents/` | `data/project_documents/` | ~390MB |
| Move | `berkeley-data-staging/council_meetings/` | `data/media/council_meetings/` | 25MB |
| Move | `berkeley-housing-research/Berkeley Data Assets.md` | `docs/data_sources.md` | ~15KB |
| Move | `berkeley-housing-research/Pipeline Methodology.md` | `docs/pipeline_methodology.md` | ~10KB |
| Move | `berkeley-housing-research/Claude Dialogues/` | `docs/design_decisions/` | ~100KB |
| Move | `berkeley-permit-pipeline/ActiveLandUse_2026-01-10.xlsx` | `data/archive/` | ~1MB |

### Archive Externally
| Action | Source | Destination | Size |
|--------|--------|-------------|------|
| Archive | `berkeley-data-staging/site_tours/` | Google Drive / S3 | 275MB |

### Requires Decision
| Item | Options |
|------|---------|
| Quartz documentation site | Keep for public docs, or extract content and archive? |
| Obsidian vault | Continue using, or consolidate into markdown? |
| Project research notes (30 files) | Review individually, merge useful content |

---

## Post-Consolidation Cleanup

After completing migrations, these directories can be removed:

```bash
# After verifying all content migrated:
rm -rf ~/berkeley_data
rm -rf ~/berkeley-data-staging
rm -rf ~/berkeley-housing-research  # or keep if maintaining Quartz site
rm -rf ~/berkeley-permit-pipeline   # or keep if using Obsidian
```

---

## Appendix: Notable Files to Preserve

These files contain valuable content not duplicated elsewhere:

1. **`Berkeley Data Assets.md`** — Comprehensive inventory of Berkeley open data sources, APIs, update frequencies, and access methods. Critical reference for data pipeline maintenance.

2. **`2190_Shattuck_Plans_Full.pdf`** (141MB) — Complete architectural drawing set for major downtown project. Useful for height/massing verification.

3. **`Claude Dialogues/2026-03-15_schema_design.md`** — Documents the reasoning behind the normalized v2 schema design, including trade-offs considered.

4. **`Pipeline Methodology.md`** — Step-by-step documentation of the data collection workflow, including Accela scraping schedule and manual verification steps.

5. **Data purchase receipts** — Proof of licensing for commercial data sources (parcels, assessor data).

---

*Report generated by Claude Code — ready for consolidation decisions*
