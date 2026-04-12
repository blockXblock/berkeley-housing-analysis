# Berkeley Data Project Inventory
**Generated:** 2026-03-21

## Summary

| Type | Count | Total Size |
|------|-------|------------|
| .db (SQLite) | 21 | ~97 MB |
| .csv | 37 | ~180 MB |
| .json | 21 | ~11 MB |
| .xlsx | 13 | ~224 KB |
| .ipynb | 40 | (notebooks) |
| .py | 12 | ~80 KB |
| .md | 21 | ~82 KB |

---

## Database Files (.db)

### Active Databases (>1KB)

#### databases/berkeley.db (50 MB) - Main database
| Table | Rows |
|-------|------|
| addresses_arcgis | 65,459 |
| corridor_boundaries | 3 |
| corridor_far | 332 |
| corridor_ownership | 332 |
| development_potential | 41 |
| licenses | 13,004 |
| licenses_fts | 13,004 |
| licenses_fts_config | 1 |
| licenses_fts_data | 189 |
| licenses_fts_docsize | 12,970 |
| licenses_fts_idx | 170 |
| parcel_zones | 29,024 |
| parcels | 29,024 |
| parcels_arcgis | 29,024 |
| rent_control | 1,098 |
| zoning_districts | 42 |
| zoning_projects_with_parcels | 154 |

#### databases/berkeley_address_centric.db (14 MB)
| Table | Rows |
|-------|------|
| addresses | 62,226 |
| database_stats | 1 |
| news_coverage | 2,024 |
| projects | 156 |

#### databases/berkeley_data.db (4.1 MB)
| Table | Rows |
|-------|------|
| business_licenses | 13,004 |

#### databases/accela_reports.db (288 KB)
| Table | Rows |
|-------|------|
| active_landuse_v1_2_ActiveLandUse_V1 | 135 |
| active_landuse_v1_ActiveLandUse_V1 | 154 |
| active_landuse_v1_all_ActiveLandUse_V1 | 155 |
| active_zoning_classified | 153 |
| active_zoning_projects | 153 |
| owner_enrichment | 1 |
| permit_pipeline | 0 |
| project_documents | 0 |
| project_planners | 1 |
| record_details | 37 |

#### databases/berkeley_energy_use.db (176 KB)
| Table | Rows |
|-------|------|
| building_energy | 520 |

#### databases/berkeley_housing_analysis.db (164 KB)
| Table | Rows |
|-------|------|
| data_collection_log | 1 |
| permit_events | 58 |
| permit_fees | 12 |
| project_permits | 47 |
| projects | 115 |

#### databases/berkeley_housing_apr.db (84 KB)
| Table | Rows |
|-------|------|
| projects | 115 |

#### databases/housing_projects.db (60 KB)
| Table | Rows |
|-------|------|
| housing_projects | 84 |

#### databases/berkeley_housing_map.db (56 KB)
| Table | Rows |
|-------|------|
| projects | 84 |

#### datasette-deploy/berkeley_address_centric.db (14 MB)
| Table | Rows |
|-------|------|
| addresses | 62,226 |
| database_stats | 1 |
| news_coverage | 2,024 |
| projects | 156 |

#### datasette-deploy/berkeley_housing_map.db (144 KB)
| Table | Rows |
|-------|------|
| news_coverage | 383 |
| permit_applications | 33 |
| projects | 157 |

#### berkeleyshops-audience/audience.db (332 KB)
| Table | Rows |
|-------|------|
| mailchimp_audience | 1,610 |

#### berkeleyshops-audience/archive/audience_2026-03-12.db (320 KB)
| Table | Rows |
|-------|------|
| mailchimp_audience | 1,560 |

### Empty Databases (0 bytes)
- `berkeley_address_centric.db` (root)
- `berkeley_housing_analysis.db` (root)
- `berkeley_housing_apr.db` (root)
- `berkeley_housing_map.db` (root)
- `housing_projects.db` (root)
- `databases/berkeley_housing_pipeline.db`
- `databases/business_corridors.db`
- `databases/housing_pipeline.db`

---

## Jupyter Notebooks (.ipynb)

### 00_orientation/ - Getting Started
| File | Description |
|------|-------------|
| 00A_tour_of_the_pipeline.ipynb | Tour of the pipeline (Colab-ready) |
| 00B_first_notebook_in_colab.ipynb | First notebook in Colab |

### 01_collection/ - Data Collection
| File | Description |
|------|-------------|
| 00_test.ipynb | Test Notebook |
| 00_api_pipeline.ipynb | Berkeley Open Data Analysis Pipeline |
| 01_data_import.ipynb | Berkeley Housing Data Import |
| 02_geocoding.ipynb | Geocoding Housing Projects |
| A1_data_sources_setup.ipynb | A1: Data Sources Setup |
| A2_address_standardization.ipynb | Address standardization (Colab-ready) |
| A3_geocoding_pipeline.ipynb | Geocoding pipeline (Colab-ready) |
| A4_apn_enrichment.ipynb | APN enrichment (Colab-ready) |
| A5_buildingeye_import.ipynb | BuildingEye import (Colab-ready) |
| A6_community_map_import.ipynb | Community map import (Colab-ready) |
| A7_comprehensive_integration.ipynb | Comprehensive integration (Colab-ready) |
| A8_address_centric_database.ipynb | A8: Address-Centric Database |
| A9_apr_timeline_tracking.ipynb | A9: APR Timeline Tracking |
| A9_city_profile_builder.ipynb | City profile builder (Colab-ready) |

### 02_tracking/ - Project Tracking
| File | Description |
|------|-------------|
| B1_lifecycle_tracking.ipynb | Lifecycle tracking (Colab-ready) |
| B2_status_classification.ipynb | Status classification (Colab-ready) |
| B3_progress_indicators.ipynb | Progress indicators (Colab-ready) |

### 03_analysis/ - Analysis
| File | Description |
|------|-------------|
| C0_methods_overview.ipynb | Methods overview (Colab-ready) |
| C1_pipeline_analysis.ipynb | Pipeline analysis (Colab-ready) |
| C2_timeline_analysis.ipynb | Timeline analysis (Colab-ready) |
| C3_proposal_vs_reality.ipynb | Proposal vs reality (Colab-ready) |
| C4_quality_checks.ipynb | Quality checks (Colab-ready) |

### 04_reporting/ - Reporting
| File | Description |
|------|-------------|
| D1_monthly_report_generator.ipynb | Monthly report generator (Colab-ready) |
| D2_dashboard_data_export.ipynb | Dashboard data export (Colab-ready) |
| D3_alerts_monitoring.ipynb | Alerts monitoring (Colab-ready) |
| D4_hcd_apr_tables.ipynb | HCD APR tables (Colab-ready) |

### 05_feasibility/ - Feasibility Analysis
| File | Description |
|------|-------------|
| F1_development_math.ipynb | Development math (Colab-ready) |
| F2_pro_forma_transparent.ipynb | Pro forma transparent (Colab-ready) |

### Root Level
| File | Description |
|------|-------------|
| MASTER_ANALYSIS.ipynb | Berkeley Housing Pipeline - Permitting, Construction, Economic and Neighborhood Outcomes |
| parcels_active_housing_permits.ipynb | Berkeley Parcels × Active Housing Permits |
| permitpipeline.ipynb | Found three spreadsheets in March 2026 analysis |

### archive/notebooks/
| File | Description |
|------|-------------|
| 00_test.ipynb | Test Notebook |
| 01_data_import.ipynb | Berkeley Housing Data Import |
| 02_geocoding.ipynb | Geocoding Housing Projects |
| berkeley_open_data_pipeline.ipynb | Berkeley Open Data Analysis Pipeline |
| MASTER_ANALYSIS.ipynb | Berkeley Housing Pipeline - Master Analysis |
| parcels_active_housing_permits.ipynb | Berkeley Parcels × Active Housing Permits |
| Test-locations-versions.ipynb | Finding errors in JN .ipynb files |

---

## CSV Files

### Core Data (data/processed/)
| File | Rows | Key Columns |
|------|------|-------------|
| housing_projects_FINAL.csv | 118 | id, address_display, apn, owner, net_units, year, status... |
| project_addresses.csv | 84 | address_display, net_units, year |
| unmatched_addresses.csv | 5 | address_display, net_units, status |
| working_berkeley_datasets.csv | 2 | id, name, rows, columns, csv_url, json_url |

### Reference Data (data/reference/)
| File | Rows | Description |
|------|------|-------------|
| alameda_lookup_complete.csv | 563,193 | Full Alameda address lookup |
| alameda_address_lookup_normalized.csv | 497,328 | Normalized addresses |
| alameda_lookup_corrected.csv | 337,638 | Corrected lookup |
| berkeley_address_points.csv | 62,225 | Berkeley address points |
| berkeley_address_points_corrected.csv | 62,225 | Corrected address points |
| berkeley_addresses_with_fields.csv | 62,226 | Addresses with full fields |
| berkeley_parcels.csv | 29,024 | Parcel data |
| rent_control.csv | 1,098 | Rent control properties |
| corridor_far.csv | 332 | Floor area ratios |
| corridor_ownership.csv | 332 | Corridor ownership |
| corridor_boundaries.csv | 3 | Corridor boundaries |

### Raw Data (data/raw/)
| File | Rows | Description |
|------|------|-------------|
| business_licenses_20251115.csv | 13,004 | Business licenses (latest) |
| Business_Licenses_20251114.csv | 13,002 | Business licenses |
| Business_Licenses_20251113 (1).csv | 12,996 | Business licenses |
| Business_Licenses_20251113.csv | 14 | Business licenses (partial) |
| business_Licenses.csv | 100 | Business licenses (sample) |

### Outputs (data/outputs/)
| File | Rows | Description |
|------|------|-------------|
| permits_unit_counts_MANUAL_REVIEW.csv | 227 | Permits needing review |
| accela_collection_checklist.csv | 115 | Collection checklist |
| housing_units_audit_trail.csv | 98 | Unit change audit trail |
| VERIFICATION_by_address_max_units.csv | 84 | Address verification |
| feasibility_scenarios.csv | 9 | Development scenarios |

### Outputs (outputs/)
| File | Rows | Description |
|------|------|-------------|
| gellerman_news_links.csv | 2,024 | News links by project |
| match_results.csv | 207 | Address matching results |
| gellerman_raw.csv | 207 | Gellerman raw data |
| housing_projects_comprehensive.csv | 156 | All projects comprehensive |
| housing_projects_enriched.csv | 115 | Enriched project data |

### Energy Data (energy/)
| File | Rows | Description |
|------|------|-------------|
| beso_energy_5vy5-rwja.csv | 520 | Building energy benchmarks |

### Backups (data/backups/)
| File | Rows | Date |
|------|------|------|
| housing_projects_FINAL_20260320_195539.csv | 115 | 2026-03-20 |
| housing_projects_FINAL_20260222_141633.csv | 84 | 2026-02-22 |

### Mailchimp (berkeleyshops-audience/archive/)
| File | Rows | Description |
|------|------|-------------|
| subscribed_email_audience_export.csv | 1,610 | Subscribed emails |
| cleaned_email_audience_export.csv | 141 | Cleaned emails |
| unsubscribed_email_audience_export.csv | 59 | Unsubscribed |

---

## JSON Files

### Configuration
| File | Size | Description |
|------|------|-------------|
| 00_config/berkeley_config.json | 2.8 KB | Project configuration |
| apr_specification.json | 19 KB | APR specification |
| apr_data_mapping.json | 8.2 KB | APR data mapping |
| databases/metadata.json | 8.3 KB | Database metadata |
| datasette-deploy/metadata.json | 4.2 KB | Datasette metadata |

### Reference Data
| File | Size | Description |
|------|------|-------------|
| data/reference/rent_control.json | 1.1 MB | Rent control data |
| data/reference/corridor_parcels.json | 119 KB | Corridor parcels |
| data/reference/corridor_far.json | 122 KB | Floor area ratios |
| data/reference/corridor_ownership.json | 119 KB | Ownership data |
| data/reference/corridor_ownership_fixed.json | 31 KB | Fixed ownership |
| data/reference/corridor_boundaries.json | 16 KB | Boundaries |

### Raw Data
| File | Size | Description |
|------|------|-------------|
| data/raw/business_licenses_20251115.json | 8.9 MB | Business licenses |
| energy/beso_5vy5-rwja.json | 605 KB | Energy data |

### Outputs
| File | Size | Description |
|------|------|-------------|
| outputs/projects_map.json | 33 KB | Map data |
| data/outputs/service_info.json | 4.3 KB | Service info |
| data/outputs/housing_projects_metadata.json | 2.3 KB | Project metadata |
| data/outputs/berkeley_housing_map_metadata.json | 2.4 KB | Map metadata |
| outputs/summary.json | 692 B | Summary stats |

---

## Excel Files (.xlsx)

### Zoning Reports (zoning_reports/)
| File | Size | Date |
|------|------|------|
| 2026_03_19_ActiveLandUse_V1_all.xlsx | 21 KB | 2026-03-19 |
| 2026_03_19_ActiveLandUse_V1.xlsx | 20 KB | 2026-03-19 |
| 2026_03_19_ActiveLandUse_V1_2.xlsx | 17 KB | 2026-03-19 |
| 2026_03_19_LandUseStatus_V1.xlsx | 7.2 KB | 2026-03-19 |
| 2026-1-14ActiveLandUse_V1.xlsx | 20 KB | 2026-01-14 |
| 2026-1-6_ActiveLandUse_V1.xlsx | 20 KB | 2026-01-06 |
| Zoning_active_projects_ActiveLandUse_V1.xlsx | 21 KB | Active projects |
| ActiveLandUse_V1_All_permits.xlsx | 20 KB | All permits |
| LandUseStatus_V1_OpenAppeal.xlsx | 7.8 KB | Open appeals |
| 6_LandUseStatus_V1.xlsx | 7.8 KB | Land use status |
| LandUseStatus_V1 (2).xlsx | 7.2 KB | Land use status |

### Data Outputs (data/outputs/)
| File | Size | Description |
|------|------|-------------|
| permits_unit_counts_MANUAL_REVIEW.xlsx | 35 KB | Manual review |
| VERIFICATION_by_address_max_units.xlsx | 20 KB | Verification |

---

## Python Files (.py)

### Modules (modules/)
| File | Size | Description |
|------|------|-------------|
| __init__.py | 926 B | Package init |
| report_generator.py | 10 KB | Report generation |
| timeline_calculator.py | 8.2 KB | Timeline calculations |
| address_normalizer.py | 7.9 KB | Address normalization |
| geocoder.py | 7.2 KB | Geocoding utilities |
| data_loader.py | 7.0 KB | Data loading |
| config_loader.py | 2.7 KB | Configuration loading |

### Scripts (scripts/)
| File | Size | Description |
|------|------|-------------|
| accela_workflow.py | 12 KB | Accela workflow automation |
| parse_buildingeye_text.py | 7.4 KB | BuildingEye parsing |
| convert_all_arcgis.py | 1.2 KB | ArcGIS conversion |
| convert_boundaries.py | 761 B | Boundary conversion |

### Root
| File | Size | Description |
|------|------|-------------|
| update_housing_data.py | 15 KB | Housing data updates |

---

## Markdown Files (.md)

### Documentation (docs/)
| File | Size | Description |
|------|------|-------------|
| APR_DATABASE_SCHEMA.md | 9.4 KB | APR database schema |
| PRESENTER_NOTES.md | 9.4 KB | Presenter notes |
| APR_2025_DATA_COLLECTION_CHECKLIST.md | 7.9 KB | Data collection checklist |
| your-city.md | 3.8 KB | Adapting for other cities |
| start-here.md | 2.8 KB | Getting started guide |
| hcd-apr.md | 2.4 KB | HCD APR info |
| methods.md | 2.3 KB | Methodology |

### Research (research/)
| File | Size | Description |
|------|------|-------------|
| clariti/API_Requirements_Berkeley.md | 11 KB | API requirements |
| clariti/research_questions.md | 830 B | Research questions |
| clariti-opengov-comparison/findings.md | 2.9 KB | Comparison findings |
| clariti-opengov-comparison/research_plan.md | 788 B | Research plan |

### Root
| File | Size | Description |
|------|------|-------------|
| README_COURSE.md | 7.1 KB | Course README |
| apr_compliance_checklist.md | 6.1 KB | APR compliance checklist |
| README.md | 4.0 KB | Main README |

### Other
| File | Size | Description |
|------|------|-------------|
| outputs/ANALYSIS_REPORT.md | 1.9 KB | Analysis report |
| data/outputs/ANALYSIS_REPORT.md | 2.0 KB | Analysis report |
| berkeleyshops-audience/README.md | 1.6 KB | Audience README |
| datasette-deploy/README.md | 1.4 KB | Datasette README |
| data/processed/README.md | 568 B | Processed data README |
| session_summaries/session_summary_2026-03-21.md | 7.6 KB | Session summary |
| hello-fly/README.md | 168 B | Hello Fly README |

---

## Directory Structure

```
berkeley-data/
├── 00_config/           # Configuration files
├── 00_orientation/      # Getting started notebooks
├── 01_collection/       # Data collection notebooks
├── 02_tracking/         # Project tracking notebooks
├── 03_analysis/         # Analysis notebooks
├── 04_reporting/        # Reporting notebooks
├── 05_feasibility/      # Feasibility analysis
├── archive/             # Archived files
├── berkeleyshops-audience/  # Mailchimp audience data
├── data/
│   ├── backups/         # Data backups
│   ├── outputs/         # Generated outputs
│   ├── processed/       # Processed data
│   ├── raw/             # Raw data files
│   └── reference/       # Reference data
├── databases/           # SQLite databases
├── datasette-deploy/    # Datasette deployment
├── docs/                # Documentation
├── energy/              # Energy data
├── hello-fly/           # Fly.io deployment
├── modules/             # Python modules
├── outputs/             # Analysis outputs
├── research/            # Research notes
├── scripts/             # Utility scripts
├── session_summaries/   # Session logs
└── zoning_reports/      # Zoning Excel reports
```
