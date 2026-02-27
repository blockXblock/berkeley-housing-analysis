# Berkeley Housing Data Science Course

**Educational notebooks for civic data analysis**

## Mission

Build a complete, replicable data science course for analyzing city housing and permitting data. Students learn to:

- Collect data from multiple government sources (APIs, manual downloads, GIS)
- Clean, standardize, and geocode addresses (100% success rate)
- Track projects through the complete permit pipeline
- Analyze bottlenecks and produce actionable insights
- Generate compliance reports for HCD and local agencies
- Understand housing production metrics and feasibility

---

## Course Structure

```
01_collection/      → A-Series: Data Collection (5 notebooks)
02_tracking/        → B-Series: Timeline Tracking (3 notebooks)
03_analysis/        → C-Series: Analysis (3 notebooks)
04_reporting/       → D-Series: Reporting (3 notebooks)
05_feasibility/     → F-Series: Feasibility (2 notebooks)
```

---

### A-Series: Data Collection (`01_collection/`)
**Skills:** API usage, web scraping, manual workflows, geocoding

| Notebook | Description |
|----------|-------------|
| **A1_data_sources_setup** | Berkeley Open Data, Accela portal, manual downloads |
| **A2_address_standardization** | Clean messy addresses for geocoding |
| **A3_geocoding_pipeline** | 100% success using Alameda County lookup (563K addresses) |
| **A4_apn_enrichment** | Match projects to Assessor Parcel Numbers (APN) |
| **A5_buildingeye_import** | Design review and permit timeline data |

**Real-world learning:** APIs often blocked, manual workflows required, importance of data quality

---

### B-Series: Timeline Tracking (`02_tracking/`)
**Skills:** Event modeling, status classification, progress metrics

| Notebook | Description |
|----------|-------------|
| **B1_lifecycle_tracking** | Proposal → Permit → Construction → Occupancy |
| **B2_status_classification** | Standardize inconsistent permit statuses |
| **B3_progress_indicators** | Detect stalled projects, predict completion |

**Key insight:** Berkeley projects average 30-42 months from proposal to completion

---

### C-Series: Analysis (`03_analysis/`)
**Skills:** Pipeline analysis, statistical methods, comparative analysis

| Notebook | Description |
|----------|-------------|
| **C1_pipeline_analysis** | Housing production trends, geographic patterns |
| **C2_timeline_analysis** | Identify approval bottlenecks, seasonal patterns |
| **C3_proposal_vs_reality** | Compare approved vs built units |

**Current data:** 115 projects, 5,470 units in pipeline, 40 under review

---

### D-Series: Reporting (`04_reporting/`)
**Skills:** Automated reporting, compliance documentation, monitoring systems

| Notebook | Description |
|----------|-------------|
| **D1_monthly_report_generator** | HCD-compliant housing element reports |
| **D2_dashboard_data_export** | Datasette deployment, public data access |
| **D3_alerts_monitoring** | Track stalled projects (180+ days inactive) |

**Output:** Live database at https://berkeley-housing.fly.dev/

---

### F-Series: Feasibility Analysis (`05_feasibility/`)
**Skills:** Financial modeling, development economics, policy analysis

| Notebook | Description |
|----------|-------------|
| **F1_development_math** | Construction costs, financing, ROC calculations |
| **F2_pro_forma_transparent** | Full pro forma with IRR, policy scenarios |

**Purpose:** Understand why projects succeed or fail financially (Terner Center "Making It Pencil" framework)

---

## Data Sources

### Official City Data
- Berkeley Open Data Portal (business licenses work, permits blocked by WAF)
- Accela Planning Portal (zoning, design review)
- Building Department records (permits, inspections)
- GIS parcel data

### External Data
- Alameda County Assessor (geocoding, ownership)
- Eric Gellerman's Housing Map (203 community-tracked projects)
- BuildingEye (design review details)
- California HCD (state requirements)

### Data Quality
| Metric | Value |
|--------|-------|
| Permitted projects | 115 |
| Community-reported projects | 203 |
| Geocoding success | 100% |
| Total units in pipeline | 5,470 |
| APN coverage | 96.5% |

---

## Running the Course

### Prerequisites
```bash
conda create -n berkeley-housing python=3.11
conda activate berkeley-housing
pip install -r requirements.txt
```

### Complete Pipeline
```bash
# A-series: Collect data
jupyter notebook 01_collection/A1_data_sources_setup.ipynb
# → A2 → A3 → A5

# B-series: Track timelines
jupyter notebook 02_tracking/B1_lifecycle_tracking.ipynb
# → B2 → B3

# C-series: Analyze patterns
jupyter notebook 03_analysis/C1_pipeline_analysis.ipynb
# → C2 → C3

# D-series: Generate reports
jupyter notebook 04_reporting/D1_monthly_report_generator.ipynb
# → D2 (creates database) → D3

# F-series: Understand economics
jupyter notebook 05_feasibility/F1_development_math.ipynb
# → F2
```

### Quick Start (Google Colab)
Every notebook has a Colab badge - click to run in browser, no installation needed.

Visit: https://blockxblock.github.io/berkeley-housing-analysis/

---

## Educational Philosophy

### Real-World Challenges
- APIs blocked by firewalls → Learn manual workflows
- Messy address data → Learn data cleaning
- Inconsistent statuses → Learn standardization
- Missing data → Learn imputation strategies

### Transparency
- Complete code (no black boxes)
- Documented decisions
- Failed approaches shown
- Real limitations acknowledged

### Reproducibility
- Version-controlled
- Timestamped outputs
- Dependencies documented
- Data lineage tracked

---

## Adapting for Your City

Replace Berkeley-specific elements:

1. **Data sources** (A-series)
   - Your city's open data portal
   - Your permit system (Accela, CityGov, etc.)
   - Your GIS/parcel data

2. **Geocoding** (A3)
   - Your county's address database
   - Or use Census TIGER geocoding
   - Or Google Maps API (paid)

3. **Status codes** (B2)
   - Map your city's permit statuses
   - Customize classification logic

4. **Reporting** (D-series)
   - Your state's housing requirements
   - Your local metrics

**Core methodology transfers to any jurisdiction!**

---

## Output Products

### For Students
- 16 complete notebooks (A-F series)
- Real civic data experience
- Portfolio-ready project
- Deployed live database

### For Cities
- Automated monthly reports
- HCD compliance documentation
- Pipeline monitoring dashboard
- Public transparency tools

### For Communities
- Live project tracking
- Stalled project alerts
- Housing production metrics
- Development economics education

---

## Live Resources

| Resource | URL |
|----------|-----|
| Code Repository | https://github.com/blockXblock/berkeley-housing-analysis |
| Live Database | https://berkeley-housing.fly.dev/ |
| Course Website | https://blockxblock.github.io/berkeley-housing-analysis/ |

---

## Contributing

This is an open educational resource. Improvements welcome:
- Additional data sources
- Better analysis techniques
- More visualizations
- Other city examples
- Bug fixes

**Goal:** Help every city track and understand its housing pipeline.

---

**Last Updated:** February 2026
**Berkeley Data:** Current through Feb 24, 2026
**Notebooks:** 16 (A1-A5, B1-B3, C1-C3, D1-D3, F1-F2)
