# Berkeley Housing Pipeline — Session Summary
## March 20-21, 2026

---

## What We Accomplished

### 1. Parcel Database (berkeley.db — 50 MB)
- **29,024 parcels** from ArcGIS MapServer with APN, owner, assessed values, coordinates, use codes
- **65,459 addresses** matched at 99.9% via normalized APN join
- **29,003 parcels zoned** (99.8%) via spatial lookup against 42 zoning districts
- **Development potential table**: 41 zones mapped with middle housing + density bonus rules
- **Master view `parcels_full`**: joins parcels + zones + addresses + development potential

### 2. Active Zoning Projects (accela_reports.db)
- **153 active zoning projects** ingested from Accela Excel reports
- **57 classified as housing production** (~3,100 units)
- **37 major housing projects scraped live** from Accela detail pages:
  - Applicant, owner, description, status for each
  - Attachment lists read from iframe
  - One planner extracted (Sharon Gong for ZP2024-0058)
- **Building permit cross-reference proven**: ZP2024-0033 → B2022-04242

### 3. Data Merge
- **3 new Approved projects** found and added to housing_projects_FINAL.csv:
  - ZP2023-0107: 2462 Bancroft, 66 units
  - ZP2024-0033: 2317 Channing, 22 units  
  - ZP2024-0114: 2138 Kittredge, 66 units
- **Canonical dataset now: 118 projects, 5,624 units**
- APNs filled for all 3 via alameda_lookup_complete.csv

### 4. Vision 2050 Website
- Published at https://berkeley2050.github.io/guide/vision2050-docs.html
- 8 official City documents organized, linked to JupyterBook

---

## Key Findings

### Data Sources
| Source | Status | Notes |
|--------|--------|-------|
| Accela Zoning (Planning tab) | ✅ Working | Requires login for reports; search works |
| Accela Building (Building tab) | ✅ Working | No login needed for search; 10 results/page |
| Berkeley Open Data (Socrata) | ⚠️ No building permits dataset | `ydr8-5enu` was Chicago's, not Berkeley's |
| BuildingEye | ⚠️ Limited | Map interface only, no clean API, returns 500 on POST |
| GIS Building Safety Layer | ❌ Stale | Data only through 2015 (1992-2015, 8,302 records) |
| Berkeley Open Data Catalog | ✅ Working | Business Licenses and Parcels available |

### Berkeley's Building Permit Data Gap
Berkeley does NOT publish building permit data through:
- Socrata / Open Data portal (no dataset exists)
- GIS MapServer (frozen at 2015)
- BuildingEye API (no programmatic access)

**Only source: Accela web portal** (aca-prod.accela.com/BERKELEY), which requires:
- Manual search (10 results per page, pagination)
- Or Chrome automation (proven workflow)

### Network/IP Notes
- Your IP address is 162.233.200.44 (AT&T fiber)
- Berkeley Open Data WAF blocks this IP for SOME datasets (Building Permits, 311, Fire) but allows others (Business Licenses, Parcels)
- The building permits dataset ID `ydr8-5enu` turned out to be **Chicago's dataset**, not Berkeley's — Berkeley has NO building permits on Socrata
- Accela portal works fine from this IP
- BuildingEye homepage loads but API returns 500 errors on data queries
- The Socrata catalog API works; individual dataset access varies by dataset

---

## Canonical Data Sources

### PRIMARY: housing_projects_FINAL.csv
- Location: `/Users/johngage/berkeley-data/data/processed/housing_projects_FINAL.csv`
- Records: 118 projects
- Units: 5,624
- Columns: 25 (including APR-oriented fields)
- APN coverage: 117/118
- VLI extracted: 115/118

### SPATIAL: berkeley.db
- Location: `/Users/johngage/berkeley-data/databases/berkeley.db`
- Key tables: parcels_arcgis (29,024), addresses_arcgis (65,459), parcel_zones (29,024), development_potential (41)
- Master view: parcels_full

### PERMITS: accela_reports.db
- Location: `/Users/johngage/berkeley-data/databases/accela_reports.db`
- Key tables: active_zoning_classified (153), record_details (37)
- Schema ready: project_documents (0), project_planners (1), permit_pipeline (0)

### REFERENCE: alameda_lookup_complete.csv
- Location: `/Users/johngage/berkeley-data/data/reference/alameda_lookup_complete.csv`
- Records: 563,193 addresses with APN, lat/lng

---

## APR Compliance Status

| APR Field | Status | Source |
|-----------|--------|--------|
| APN | ✅ 117/118 | alameda_lookup + parcels_arcgis |
| Address | ✅ 118/118 | housing_projects_FINAL.csv |
| Tracking ID | ✅ 118/118 | permit numbers |
| Unit count | ✅ 118/118 | extracted from descriptions |
| Unit category | ✅ derivable | from unit counts + descriptions |
| Tenure | ⚠️ partial | derivable (5+ = Renter default) |
| VLI units | ⚠️ 115/118 | extracted from descriptions |
| Income breakdown (DR/NDR) | ❌ missing | need Density Bonus statements from Accela PDFs |
| Building permit dates | ❌ missing | need Accela Building tab scraping |
| CO dates | ❌ missing | need "Finaled" status from building permits |
| SB35/SB330/AB2011 flags | ⚠️ partial | derivable from descriptions |
| Density bonus | ⚠️ partial | many descriptions mention it |
| Entitlement dates | ❌ missing | in Accela attachment PDFs |

---

## Databases to Deprecate

These .db files appear corrupted or superseded:
- `housing_projects.db` (empty tables)
- `berkeley_housing_map.db` (empty tables)  
- `berkeley_housing_analysis.db` (empty tables)
- `berkeley_housing_apr.db` (empty tables)
- `berkeley_address_centric.db` (empty tables)
- `berkeley_housing_pipeline.db` (empty)
- `business_corridors.db` (empty)
- `housing_pipeline.db` (empty)

Consider moving to `archive/databases/` to avoid confusion.

---

## Next Steps (Priority Order)

### 1. Building Permit Scraping (Tables B & D)
- Search Accela Building tab for each of the 6 Approved/Pending Final projects
- Cross-reference zoning permits → building permits by address
- Extract Issued/Finaled dates
- Search for "ADU" permits in 2024-2025

### 2. Affordability Data from Accela PDFs
- Download "Complete Letter" and "Density Bonus Eligibility Statement" PDFs via Safari
- Extract VLI/LI/MOD unit counts and deed restriction status
- Extract planner names from signature blocks

### 3. Consolidate Databases
- Archive empty/broken .db files
- Update `datasette-deploy/berkeley_housing_map.db` to match FINAL.csv
- Consider single `berkeley_master.db` with all tables

### 4. APR Report Generator
- Build D4_hcd_apr_tables.ipynb (skeleton exists)
- Use apr_specification.json for field validation
- Generate Tables A, A2, B from available data

---

## Accela Scraping Workflow (Proven)

### Zoning Permits (requires login)
1. Navigate to Planning tab
2. Search by permit number
3. Extract: status, address, applicant, owner, description
4. Click Attachments → read iframe for document list
5. Download small PDFs via Safari for planner/affordability extraction

### Building Permits (no login needed)
1. Navigate to Building tab  
2. Search by street number + name (or date range)
3. Extract: date, permit number, type, status, address, description
4. "Finaled" status = Certificate of Occupancy
5. Cross-reference with zoning permit by address

---

## Key People / Contacts

- **Isaiah Stackhouse** (Trachtenberg Architects): 16 projects, ~2,098 units
- **Sharon Gong** (Senior Planner): sgong@cityofberkeley.info, (510) 981-7429
- **Jordan Klein**: Planning and Development Director
- **Steve Heaton** (Laconia Development): 2029 University projects (240+160 units)

---

## RHNA Context (6th Cycle, 2023-2031)

| Income Level | RHNA | Through 2024 | Remaining |
|-------------|------|-------------|-----------|
| Very Low | 2,446 | 160 | 2,286 |
| Low | 1,408 | 67 | 1,341 |
| Moderate | 1,416 | 83 | 1,333 |
| Above Moderate | 3,664 | 1,344 | 2,320 |
| **Total** | **8,934** | **1,654** | **7,280** |

Berkeley has permitted 18.5% of its RHNA allocation after 2 years of the 8-year cycle.
