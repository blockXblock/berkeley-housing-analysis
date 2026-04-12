# Scraping Gap Root Cause Analysis

**Generated:** 2026-03-21
**Issue:** 13 projects in Berkeley's 2024 APR submission are missing from our data

---

## Executive Summary

| Root Cause | Projects | Units |
|------------|----------|-------|
| **Never Downloaded from Accela** | 13 | 1,263 |
| Permit Number Mismatch | 1 | 1 |

**Primary Finding:** Our data collection workflow has a **circular dependency** - we only scrape Accela for projects already in our database. We have no mechanism to discover new projects from Accela.

---

## Data Collection Architecture Analysis

### Current Workflow (`scripts/accela_workflow.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT WORKFLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. generate command                                            │
│     ├─ Reads FROM: databases/berkeley_housing_analysis.db      │
│     │              └── projects table (115 rows)                │
│     │                                                           │
│     └─ Outputs: Collection URLs for KNOWN projects only        │
│                                                                  │
│  2. parse command                                               │
│     └─ Parses copied Processing Status text                    │
│                                                                  │
│  3. save command                                                │
│     └─ Saves events to permit_events table                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
   ╔═════════════════════════════════════════════════════════════╗
   ║  CIRCULAR DEPENDENCY PROBLEM                                 ║
   ║                                                              ║
   ║  We can only collect data for projects we already know!     ║
   ║  New projects filed in Accela are never discovered.         ║
   ╚═════════════════════════════════════════════════════════════╝
```

### Source of `projects` Table

The `generate` command queries:
```python
cursor.execute("""
    SELECT id, address_display, net_units, permits, status
    FROM projects
    ORDER BY net_units DESC
""")
```

This table is populated from `housing_projects_FINAL.csv`, which itself was built from:
- Manual data entry
- Previous Accela scrapes
- News/media sources

**No automated discovery of new Accela permits exists.**

---

## Evidence: Where Each Missing Project Fell Out

### Search Results Summary

| Data Source | Missing Permits Found |
|-------------|----------------------|
| zoning_reports/*.xlsx (11 Excel files) | **0 of 13** |
| accela_reports.db (all tables) | **0 of 13** |
| berkeley_housing_analysis.db | **0 of 13** |
| data/processed/*.csv (43 files) | **0 of 13** |

### Per-Project Analysis

| # | Permit | Address | Units | Where It Fell Out |
|---|--------|---------|-------|-------------------|
| 1 | ZP2023-0040 | 1974 SHATTUCK Ave | 599 | **Never in any Accela export** |
| 2 | ZP2023-0079 | 2274 SHATTUCK Ave | 227 | **Never in any Accela export** |
| 3 | ZP2023-0163 | 2100 MILVIA St | 201 | **Never in any Accela export** |
| 4 | ZP2023-0126 | 2530 BANCROFT Way | 110 | **Never in any Accela export** |
| 5 | ZP2023-0064 | 2037 DURANT Ave | 74 | **Never in any Accela export** |
| 6 | ZP2024-0070 | 2442 HASTE St | 36 | **Never in any Accela export** |
| 7 | ZP2022-0115 | 2427 SAN PABLO Ave | 8 | **Never in any Accela export** |
| 8 | ZP2024-0008 | 1614 SIXTH St | 2 | **Never in any Accela export** |
| 9 | ZP2022-0038 | 2820 SAN PABLO Ave | 1 | **Never in any Accela export** |
| 10 | ZP2023-0123 | 2833 SEVENTH St | 1 | **Never in any Accela export** |
| 11 | ZP2024-0014 | 1048 KEITH Ave | 1 | **Never in any Accela export** |
| 12 | ZP2024-0116 | 811 CEDAR St | 1 | **Never in any Accela export** |
| 13 | ZP2024-0129 | 1627 JAYNES St | 1 | **Never in any Accela export** |

### Permit Mismatch Case (0 PARKER St)

| Field | Our Data | City's APR |
|-------|----------|------------|
| Permit | ZP2022-0063 | ZP2024-0100 |
| Year | 2022 | 2024 |
| Status | Incomplete Pending Applicant | Approved |

**Explanation:** We have an older permit for this address. The city reported a newer follow-up permit that supersedes it.

---

## Permit Number Coverage Analysis

### What We Have vs. What's Missing

| Year | Permits in Our Data | Missing from City APR |
|------|--------------------|-----------------------|
| ZP2022 | 12 | 2 (16% gap) |
| ZP2023 | 11 | 6 (35% gap) |
| ZP2024 | 28 | 6 (18% gap) |

### Sample ZP2023 Permits

| In Our Data | Missing |
|-------------|---------|
| ZP2023-0008 | ZP2023-0040 |
| ZP2023-0058 | ZP2023-0064 |
| ZP2023-0063 | ZP2023-0079 |
| ZP2023-0070 | ZP2023-0123 |
| ZP2023-0089 | ZP2023-0126 |
| ZP2023-0090 | ZP2023-0163 |
| ZP2023-0095 | |
| ZP2023-0096 | |
| ZP2023-0099 | |
| ZP2023-0107 | |
| ZP2023-0155 | |

**Pattern:** We have random gaps in permit number sequences. This indicates we only collected permits for projects we already knew about, not a systematic scrape of all permits.

---

## Excel Export Analysis

### Files Examined

| File | Rows | Missing Permits Found |
|------|------|----------------------|
| 2026-1-6_ActiveLandUse_V1.xlsx | ~150 | 0 |
| 2026-1-14ActiveLandUse_V1.xlsx | ~150 | 0 |
| 2026_03_19_ActiveLandUse_V1.xlsx | ~150 | 0 |
| 2026_03_19_ActiveLandUse_V1_2.xlsx | ~135 | 0 |
| 2026_03_19_ActiveLandUse_V1_all.xlsx | ~155 | 0 |
| ActiveLandUse_V1_All_permits.xlsx | ~154 | 0 |
| Other .xlsx files | varies | 0 |

**Conclusion:** The missing permits were never exported from Accela. Our Excel exports appear to be filtered views, not complete permit lists.

---

## Related Data We DO Have

### Address/Parcel Data Exists

All 13 missing addresses exist in our parcel data:

| Address | Found In |
|---------|----------|
| 1974 SHATTUCK | parcels_arcgis, addresses_arcgis, business_licenses |
| 2274 SHATTUCK | parcels_arcgis, addresses_arcgis |
| 2100 MILVIA | parcels_arcgis, addresses_arcgis, business_licenses |
| 2530 BANCROFT | parcels_arcgis, addresses_arcgis, business_licenses |
| ... | ... |

**We have the locations, just not the zoning permits filed there.**

### No Building Permits Found

Searched all databases for B-prefix permits at missing addresses:
- **0 building permits found** for any of the 13 missing projects
- This confirms these are planning-stage projects that haven't reached building permits yet

---

## Root Causes

### Primary: No Discovery Mechanism

```
Current State:
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Accela ACA     │────▶│ Manual download  │────▶│  Excel file      │
│   (web portal)   │     │ (human clicks)   │     │  (filtered)      │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                                           │
                                                           ▼
                         ┌──────────────────┐     ┌──────────────────┐
                         │ housing_projects │◀────│ Import script    │
                         │ _FINAL.csv       │     │ (manual)         │
                         └──────────────────┘     └──────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ accela_workflow  │
                         │ generate         │
                         └──────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Only scrape      │
                         │ KNOWN projects   │
                         └──────────────────┘
```

### Secondary: Filtered Excel Exports

The Accela "Active Land Use" report appears to use filters that exclude some permits. We don't have documentation of what filters are applied.

### Tertiary: No Quality Check

No process exists to compare our data against official city APR submissions to identify gaps.

---

## Recommended Fixes

### Fix 1: Add Accela Discovery Command (New)

Create a new `discover` command that pulls ALL active zoning permits:

```python
def discover_new_permits():
    """
    Scrape Accela's permit list page to discover NEW permits
    not already in our database.

    Steps:
    1. Navigate to Accela ACA permit search
    2. Search for all ZP* permits in date range
    3. Compare against known permits in our DB
    4. Generate URLs for NEW permits only
    """
```

**Implementation Options:**
- **Option A:** Use Selenium to scrape the public search results
- **Option B:** Request API access from City of Berkeley IT
- **Option C:** Weekly manual export of ALL permits (no filters)

### Fix 2: Systematic Permit Number Collection

Instead of searching by address (which requires knowing the project first), search by permit number sequence:

```python
def collect_permit_range(year, start_seq, end_seq):
    """
    Collect all permits in a range, e.g. ZP2024-0001 through ZP2024-0200
    """
    for seq in range(start_seq, end_seq + 1):
        permit = f"ZP{year}-{seq:04d}"
        # Check if permit exists in Accela
        # If yes and not in our DB, add to collection queue
```

### Fix 3: APR Reconciliation Process

After each APR filing deadline (April 1):

```python
def reconcile_with_city_apr(year):
    """
    1. Download city's official APR Table A from HCD
    2. Compare permit numbers against our database
    3. Flag permits in city APR but missing from our data
    4. Queue missing permits for collection
    """
```

### Fix 4: Unfiltered Excel Exports

When exporting from Accela:
1. Remove ALL filters before exporting
2. Export ALL record statuses (not just "Active")
3. Document the export date and filter settings
4. Save with timestamp: `YYYY-MM-DD_ActiveLandUse_UNFILTERED.xlsx`

### Fix 5: Permit Linking

For addresses with multiple permits (like 0 PARKER St):

```python
def link_related_permits(address):
    """
    Find all permits at an address and link them:
    - Base permit (earliest)
    - Amendment permits
    - Follow-up permits
    """
```

---

## Immediate Action Items

### Priority 1: Scrape Missing Permits Now

Run for each missing permit:
```bash
# Use Accela web search to find and export processing status
# Then import:
python scripts/accela_workflow.py save \
    --db databases/berkeley_housing_analysis.db \
    --permit ZP2023-0040 \
    --address "1974 SHATTUCK Ave" \
    --file /path/to/processing_status.txt
```

**Permits to collect:**
1. ZP2023-0040 (1974 SHATTUCK - 599 units)
2. ZP2023-0079 (2274 SHATTUCK - 227 units)
3. ZP2023-0163 (2100 MILVIA - 201 units)
4. ZP2023-0126 (2530 BANCROFT - 110 units)
5. ZP2023-0064 (2037 DURANT - 74 units)
6. ZP2024-0070 (2442 HASTE - 36 units)
7. ZP2022-0115 (2427 SAN PABLO - 8 units)
8. ZP2024-0008 (1614 SIXTH - 2 units)
9. ZP2022-0038 (2820 SAN PABLO - 1 unit)
10. ZP2023-0123 (2833 SEVENTH - 1 unit)
11. ZP2024-0014 (1048 KEITH - 1 unit)
12. ZP2024-0116 (811 CEDAR - 1 unit)
13. ZP2024-0129 (1627 JAYNES - 1 unit)

### Priority 2: Request Unfiltered Export

Contact Berkeley Planning to request:
- Complete list of all ZP permits filed 2022-2025
- Include ALL statuses (not just active)
- Include permit number, address, description, filed date, status

### Priority 3: Implement APR Reconciliation

Add to data pipeline:
```bash
# After each APR filing
python scripts/reconcile_apr.py --year 2024
```

---

## Files

| File | Purpose |
|------|---------|
| `scripts/accela_workflow.py` | Current collection workflow (lines 30-46 show circular dependency) |
| `data/reference/city_apr_2024_table_a.csv` | City's official 2024 submission |
| `data/apr/missing_projects_diagnosis.md` | Per-project diagnosis |
| `docs/scraping_gap_root_cause.md` | This document |
