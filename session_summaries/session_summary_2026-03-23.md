# Berkeley Housing Pipeline — Session Summary
## March 23, 2026

---

## What We Accomplished

### 1. Data Collection & Enrichment
- **Started**: 118 projects, 5,624 units
- **Ended**: 134 projects, 8,065 units (+43% units)
- **Collected 24 Accela permit files** via Claude in Chrome sidebar
- **Imported 174 permit events** with timeline dates, fees, and workflow stages
- **Extracted building heights** for 43 projects (new columns: height_stories, height_feet)
- **Discovered 2128 Oxford** (456 units, Berkeley's tallest approved building) — completely missing from all databases

### 2. Tooling Built
- **`save` and `save_batch` commands** added to accela_workflow.py — parses Accela Processing Status text and inserts into permit_events database
- **`discover` command** added — generates permit range URLs and finds gaps in permit sequences
- **7-format parser** — handles original Accela text, 4 markdown variants, pipe-delimited, and building permit list format
- **CopyClip batch script pattern** — paste_all.sh workflow for efficiently saving multiple clipboard entries to named files

### 3. 2024 APR Comparison
- **94% coverage** of city's 39-project Table A (up from ~84%)
- **Only 2 projects truly missing** (2 units total)
- **Found 3 projects (885 units) potentially missing from city's APR** — significant research finding
- **Year mismatch diagnosis**: 4 projects filed in 2023 but deemed complete in 2024 — cohort_filed vs cohort_complete distinction
- **20 extra projects** in our data analyzed and categorized

### 4. Root Cause Analysis
- **Circular dependency problem identified**: accela_workflow.py only generated URLs for known projects
- **35% gap rate in ZP2023 permits** — random gaps in permit sequences
- **13 missing projects** traced to scraping gaps (never downloaded from Accela)
- **All 13 subsequently collected** and imported

### 5. Staleness Analysis
- **19 projects (1,464 units) potentially stalled** (>12 months inactive)
- **17 of 19 had no data** (not truly stalled, just not scraped)
- **2128 Oxford** identified as genuinely stalled (approved Sept 2024, no construction activity)

### 6. Research Proposal Drafted
- Outreach letter to Terner Center (Moira O'Neill) and Possibility Lab (Amy Lerman)
- Proposes: student-powered data validation, open data ordinance, vendor API requirements, Datasette infrastructure
- Key evidence: 3 projects (885 units) potentially missing from city's 2024 APR

---

## Key Findings

### APR Vocabulary Refined
| Term | Definition | HCD Equivalent |
|------|-----------|----------------|
| cohort_filed | Year permit number was issued | No HCD equivalent |
| cohort_complete | Year application deemed complete | Table A year |
| cohort_entitled | Year entitlement was granted | Table A2 Section 4 year |
| cohort_permitted | Year building permit was issued | Table A2 Section 5 year |
| cohort_built | Year CO was issued | Table A2 Section 6 year |
| cohort_pipe | All projects active in a given year | No HCD equivalent (superset) |

### New Dates Identified for Pipeline Tracking
1. **Application filed date** — when applicant first submits (not tracked by HCD)
2. **Application deemed complete date** — HCD Table A (APP_SUBMIT_DT)
3. **Entitlement date** — HCD Table A2 Section 4
4. **Building permit issued date** — HCD Table A2 Section 5 (RHNA credit)
5. **Construction start date** — not in any paper trail; needs field monitoring
6. **Certificate of Occupancy date** — HCD Table A2 Section 6
7. **Project stall/suspension** — no official status; detectable via inactivity

### Data Sources Proven
| Source | Method | Value |
|--------|--------|-------|
| Accela Planning tab | Claude in Chrome sidebar | Record Info, Processing Status, Fees, Attachments |
| Accela Building tab | Manual search | Building permits, demolition permits, CO status |
| HCD Open Data (data.ca.gov) | CSV download | Official APR Tables A, A2 for comparison |
| Berkeley APR PDF | Web fetch + extraction | City's narrative and summary tables |
| berkeley.db | SQLite queries | Parcels, addresses, zoning, development potential |
| accela_reports.db | SQLite queries | Classified zoning projects, applicant contacts |
| berkeley_housing_analysis.db | SQLite queries | Permit events, permit cross-refs, fees |

### Workflow Discoveries
- **Claude in Chrome sidebar** is the fastest way to scrape Accela — reads DOM directly, handles iframe content, copies to clipboard automatically
- **pbpaste in Terminal** is faster than TextEdit for saving clipboard to files
- **CopyClip + paste_all.sh** pattern enables batch saving from clipboard history
- **Claude Code + Chrome integration** (claude --chrome) connects but has a March 20 bug preventing automated browser control
- **Street corridor searches** in Accela discover projects filed under non-ZP permit types (DRCF, LMSAP, PLN)
- **Standardize Chrome sidebar output format** upfront to avoid parser proliferation

---

## Canonical Data Sources (Updated)

### PRIMARY: housing_projects_FINAL.csv
- Location: `/Users/johngage/berkeley-data/data/processed/housing_projects_FINAL.csv`
- Records: **134 projects**
- Units: **8,065**
- Columns: 27 (added height_stories, height_feet)
- APN coverage: ~130/134
- Backups: 4 versions (2026-02-22, 2026-03-20, 2026-03-22, 2026-03-23)

### TIMELINE: berkeley_housing_analysis.db
- permit_events: **174+ events** across 24 permits
- project_permits: 47+ cross-references
- permit_fees: 12+ fee records

### REFERENCE: City's 2024 APR
- data/reference/city_apr_2024_table_a.csv
- data/reference/city_apr_2024_table_a2.csv (if extracted)
- PDF: /Users/johngage/berkeley-data/pdf/2025-03-28 Housing Element and General Plan Annual Progress Reports.pdf

### ACCELA RAW: data/raw/accela_status/
- 24 text files with Record Info, Processing Status, Fees, Attachments
- Format: mixed (7 parser formats supported)

---

## Next Steps (Priority Order)

### 1. Build Research Explorer Website
- Interactive dashboard with project table, timeline visualization, skyline chart
- Comparison view: our data vs city's APR
- Deploy to GitHub Pages or as standalone HTML

### 2. Build 2025 APR
- Filter FINAL.csv for cohort_complete=2025
- Collect Processing Status for all 2025 projects via Chrome sidebar
- Search Accela Building tab for building permits and COs issued in 2025
- Collect ADU building permits for 2025 (not in zoning permit data)
- Apply ABAG ADU affordability methodology (30/30/30/10)

### 3. Download Density Bonus PDFs for Income Data
- Use attachment lists to identify which projects have Density Bonus Eligibility Statements
- Download via Safari for top 20 projects by unit count
- Extract VLI/LI/MOD unit counts with Claude Code

### 4. Street Corridor Discovery Sweep
- Search Accela Planning tab by street name for: Shattuck, University, San Pablo, Telegraph, Durant, Bancroft, Oxford, Adeline, Solano, Ashby, MLK
- Catch projects filed under non-ZP permit types

### 5. Fix Claude Code + Chrome Integration
- Wait for fix to March 20 bug (extension v1.0.63)
- Once working: automated Accela scraping loop

### 6. Send Research Proposal
- Update with v3 comparison numbers
- Send to Possibility Lab (Amy Lerman) and Terner Center (Moira O'Neill)

---

## Technical Notes

### Parser Formats Supported (accela_workflow.py)
1. Original Accela text: "Marked as Approved on 04/11/2024 by Sharon Gong"
2. Markdown with stage headers and bold dates
3. Markdown table with stage column
4. Markdown bullet/arrow format
5. Pipe-delimited: "Due: date | Assigned: name | Marked as: action"
6. Entry-based: "Entry N: Due DATE | Assigned X | Marked as ACTION"
7. Building permit list format

### Key People
- **Sharon Gong** — Senior Planner, lead on multiple major projects
- **Isaiah Stackhouse** — Trachtenberg Architects, 16+ projects
- **Jordan Klein** — Planning and Development Director
- **Mark Rhoades** — Rhoades Planning Group, 2128 Oxford and 1974 Shattuck
- **Amy Lerman** — Executive Director, Possibility Lab
- **Moira O'Neill** — Terner Center researcher, SF APR analysis

### RHNA Context
| Income Level | RHNA | Through 2024 | Remaining |
|-------------|------|-------------|-----------|
| Very Low | 2,446 | 160 | 2,286 |
| Low | 1,408 | 67 | 1,341 |
| Moderate | 1,416 | 83 | 1,333 |
| Above Moderate | 3,664 | 1,344 | 2,320 |
| **Total** | **8,934** | **1,654** | **7,280** |

Berkeley has permitted 18.5% of RHNA after 2 of 8 years.
Our pipeline tracks 8,065 units — 90% of total RHNA — but most are still in planning/entitlement.
