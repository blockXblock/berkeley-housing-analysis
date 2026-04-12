# Consolidation Summary - 2026-03-23

## Overview

This consolidation merged permit event data from Accela into the master housing projects database.

## Final Results

| Metric | Value |
|--------|-------|
| **Total Projects** | 134 |
| **Total Units** | 8,065 |
| **New Projects Added** | 10 |
| **New Units Added** | 1,196 |

## New Projects Added

| ID | Permit | Address | Units | Status |
|----|--------|---------|-------|--------|
| 125 | ZP2023-00401974 | Shattuck | 599 | Approved |
| 126 | ZP2022-0115 | 2427 San Pablo | 78 | Approved |
| 127 | P2022-0038 | 2820 San Pablo | 0 | Unknown |
| 128 | ZP2023-0123 | 2833 Seventh St | 3 | Approved |
| 129 | ZP2024-0008 | 1614 Sixth St | 3 | Approved |
| 130 | ZP2024-0014 |  1048 Keith St | 0 | Approved |
| 131 | ZP2024-0116 | 811 Cedar | 0 | Approved |
| 132 | ZP2024-0129 | 1627 Jaynes St | 0 | Approved |
| 133 |  ZP2022-0135 | 2128 Oxford St | 485 | Approved |
| 134 | DRCF2023-0005 | 2480 Bancroft Way | 28 | Approved |

## Status Breakdown

| Status | Count |
|--------|-------|
| Under Review | 40 |
| Approved | 22 |
| Incomplete Pending Applicant | 18 |
| In Review | 17 |
| Corrections Pending Applicant | 17 |
| Pending Final Action | 12 |
| Pending | 3 |
| Resubmittal Pending Staff | 2 |
| Resubmittal Pending Review | 1 |
| On Hold | 1 |
| Unknown | 1 |

## Data Sources

- **permit_events table**: 174 events from 24 Accela text files
- **Text files**: `data/raw/accela_status/*.txt`
- **Coordinates**: `databases/berkeley.db` (parcels_arcgis)

## Processing Notes

- 10 new projects added from unmatched permits in permit_events
- 4 permits added to existing projects
- 1 status update (2680 BANCROFT: Incomplete Pending Applicant → Approved)
- Projects enriched with unit counts, descriptions from text files
- Height, density bonus, SB330, AB2011 flags extracted from descriptions

## Files Modified

- `data/processed/housing_projects_FINAL.csv` - Master projects file
- Backup: `data/processed/housing_projects_FINAL_backup_20260323_150028.csv`
