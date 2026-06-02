# Berkeley Housing Development Analysis

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/blockXblock/berkeley-housing-analysis/HEAD?labpath=MASTER_ANALYSIS.ipynb)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/MASTER_ANALYSIS.ipynb)

> Interactive analysis of housing development projects in Berkeley, CA (2020-2026)

## Reproduce Berkeley's Official APR (one click)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/DEMO_apr_vs_hcd_colab.ipynb)
&nbsp;**← Reproduce the CY2024 / CY2025 housing completion counts from primary-source data**

A self-contained, auditable notebook: it fetches two small published completion extracts
(`data/public/*.csv`) and **derives** Berkeley's certificate-of-occupancy counts live —
**CY2024 = 709**, **CY2025 = 532** net-new units (private; UC student housing excluded as
group quarters per HCD) — then compares them against the city's submitted figures from the
state CKAN portal. No install, no local data. Only the derived extracts are published; the
full canonical pipeline database stays private.

## Quick Start

**Run in Browser (No Installation):**
Click the Binder badge above (takes 2-3 min first time)

**Or Run Locally:**
```bash
cd /Users/johngage/berkeley-data
jupyter lab MASTER_ANALYSIS.ipynb
```

## Directory Structure (Consolidated Feb 2026)

```
berkeley-data/
├── MASTER_ANALYSIS.ipynb      # Complete end-to-end analysis
├── 00_config/
│   └── config.yaml            # Master configuration
├── 01_collection/             # Stage A: Data acquisition
│   ├── 00_api_pipeline.ipynb  # API connections (main working notebook)
│   ├── A1_data_sources_setup.ipynb
│   ├── A2_address_standardization.ipynb
│   └── A3_geocoding_pipeline.ipynb
├── 02_tracking/               # Stage B: Permit lifecycle
│   ├── B1_lifecycle_tracking.ipynb
│   ├── B2_status_classification.ipynb
│   └── B3_progress_indicators.ipynb
├── 03_analysis/               # Stage C: Analysis
│   ├── C1_pipeline_analysis.ipynb
│   ├── C2_timeline_analysis.ipynb
│   └── C3_proposal_vs_reality.ipynb
├── 04_reporting/              # Stage D: Reports & dashboards
│   ├── D1_monthly_report_generator.ipynb
│   ├── D2_dashboard_data_export.ipynb
│   └── D3_alerts_monitoring.ipynb
├── data/
│   ├── raw/                   # Downloaded CSVs
│   ├── processed/             # Cleaned data (housing_projects_FINAL.csv)
│   ├── reference/             # Lookup tables (Alameda addresses)
│   └── outputs/               # Visualizations, reports
├── databases/                 # SQLite databases
│   └── berkeley.db            # Master database
├── modules/                   # Python library
└── archive/                   # Old directory structure
```

## What's Inside

- **203 housing projects** totaling **9,000 net new units**
- **100% geocoded** using Alameda County GIS address points
- **Interactive maps** color-coded by project size
- **SQL database** with analysis queries
- **4-stage pipeline:** Collection → Tracking → Analysis → Reporting

## Pipeline Stages

| Stage | Notebooks | Status |
|-------|-----------|--------|
| A: Data Collection | `01_collection/` | ⚠️ Business licenses API works; permits blocked |
| B: Timeline Tracking | `02_tracking/` | ✅ Lifecycle tracking implemented |
| C: Analysis | `03_analysis/` | 📝 Needs expansion |
| D: Reporting | `04_reporting/` | 📝 Needs expansion |

## Interactive Map

Projects color-coded by size:
- 🔴 200+ units (Large)
- 🟠 100-199 units (Medium-Large)
- 🔵 50-99 units (Medium)
- 🟢 20-49 units (Small-Medium)
- ⚪ <20 units (Small)

**Live Map:** https://berkeley-housing.fly.dev/

## Data Refresh

**Current Data:** January 2026

Berkeley's Open Data Portal restricts API access (WAF returns 403). Workarounds:
1. Manual CSV download from BuildingEye
2. Contact Berkeley Planning: planning@berkeleyca.gov
3. Monitor Clariti API rollout (city's new system)

## Related Resources

- **Obsidian Docs:** `/Users/johngage/Obsidian/Berkeley-Housing-Project`
- **Research Vault:** `/Users/johngage/berkeley-housing-research`
- **GitHub:** https://github.com/blockXblock/berkeley-housing-analysis
- **Contact:** [BuildBerkeley.online](https://buildberkeley.online)

## Technical Stack

- Python 3.8+ / pandas / folium / SQLite
- Jupyter notebooks
- Datasette (web deployment)
- Fly.dev (hosting)

## License

**Public Domain** - Free to use for research, education, civic engagement, or journalism

---

**Note:** Community project analyzing public data. Not affiliated with the City of Berkeley.
