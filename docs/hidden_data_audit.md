# Hidden Data Audit
**Generated:** 2026-03-21

This audit examines three databases that may contain underutilized data.

---

## 1. berkeley_housing_analysis.db (164 KB)

### Summary
**This database contains rich timeline data not available elsewhere!**

Contains 5 tables with permit workflow events, cross-referenced permits, and fee payment records.

### Table Schemas

#### projects (115 rows)
Standard project data imported from housing_projects_FINAL.csv with additional fields:
- `density_bonus`, `density_bonus_pct`, `vli_units_extracted`
- `sb35_flag`, `sb330_flag`, `ab2011_flag` (state law flags)
- `tenure`, `size_category`

#### permit_events (58 rows) - **HAS DATES!**
```sql
CREATE TABLE permit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    address TEXT,
    permit_number TEXT,
    stage TEXT,              -- 'Application Submittal', 'Zoning Review', 'Fire Review', etc.
    action TEXT,             -- 'Plan Distribution', 'Corrections', 'Approved', 'Finaled'
    event_date TEXT,         -- ISO format YYYY-MM-DD  <-- ACTUAL DATES!
    assigned_to TEXT,        -- Staff name
    marked_by TEXT,          -- Who marked the action
    comment TEXT,
    stage_status TEXT,       -- 'Complete', 'Active', 'Pending'
    source TEXT DEFAULT 'accela',
    permit_type TEXT
)
```

**Sample Data:**
| address | permit_number | stage | action | event_date |
|---------|--------------|-------|--------|------------|
| 1750 SACRAMENTO St | B2025-05534 | Application Submittal | Plan Distribution | 2025-12-03 |
| 1750 SACRAMENTO St | B2025-05534 | Plan Distribution | Pending Payment | 2025-12-03 |
| 1750 SACRAMENTO St | B2025-05534 | Plan Distribution | Route | 2025-12-16 |
| 1750 SACRAMENTO St | B2025-05534 | Building and Safety Review | Assigned | 2025-12-18 |
| 1750 SACRAMENTO St | B2025-05534 | Building and Safety Review | Corrections | 2026-01-13 |

**This is permit workflow timeline data!** Tracks each stage/action with dates.

#### project_permits (47 rows) - **PERMIT CROSS-REFERENCES**
```sql
CREATE TABLE project_permits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    permit_number TEXT NOT NULL,
    permit_type TEXT,         -- 'Planning', 'Building'
    permit_module TEXT,
    address TEXT,
    filed_date TEXT,          -- <-- FILING DATES!
    status TEXT,
    status_date TEXT,
    is_primary INTEGER DEFAULT 0,
    permit_year INTEGER,
    permit_sequence INTEGER,
    permit_prefix TEXT        -- 'PLN', 'B', 'ZP'
)
```

**Sample Data:**
| permit_number | permit_type | address | filed_date | is_primary |
|--------------|-------------|---------|------------|------------|
| PLN2024-0010 | Planning | 1750 SACRAMENTO St | 2024-02-20 | 1 |
| PLN2025-0054 | Planning | 1750 SACRAMENTO St | 2025-08-08 | 0 |
| B2025-05534 | Building | 1750 SACRAMENTO St | 2025-12-03 | 0 |

**Links projects to ALL their permits** (planning + building) with filing dates.

#### permit_fees (12 rows) - **ACTUAL FEE PAYMENTS**
```sql
CREATE TABLE permit_fees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    permit_number TEXT,
    invoice_number TEXT,
    amount REAL,              -- <-- DOLLAR AMOUNTS!
    payment_date TEXT,        -- <-- PAYMENT DATES!
    fee_type TEXT,
    source TEXT DEFAULT 'accela'
)
```

**Sample Data:**
| permit_number | invoice_number | amount | payment_date |
|--------------|----------------|--------|--------------|
| ZP2020-0104 | 447985 | $377.50 | 2020-10-30 |
| ZP2020-0104 | 449778 | $51,204.00 | 2020-12-18 |
| ZP2020-0104 | 473291 | $5,770.00 | 2021-07-21 |
| ZP2024-0162 | 584670 | $1,750.00 | 2024-12-13 |
| ZP2024-0182 | 589573 | $5,012.50 | 2025-01-16 |

**Actual fee payment history!** Can calculate total fees paid per project.

### Recommended Actions
1. **Use permit_events for timeline analysis** - calculate permit processing times
2. **Build permit fee totals per project** - show true cost of approvals
3. **Link project_permits to enable permit number lookups**

---

## 2. berkeley_address_centric.db (14 MB)

### Summary
Contains 156 projects from multiple sources. **41 projects exist ONLY in news coverage and are NOT in housing_projects_FINAL.csv!**

### projects Table Schema
```sql
CREATE TABLE projects (
    project_id INTEGER,
    address_id REAL,
    address_display TEXT,
    net_units REAL,
    status TEXT,
    data_source TEXT,         -- 'official_permit', 'media_reported', 'both'
    has_official_permit INTEGER,
    has_media_coverage INTEGER,
    latitude REAL,
    longitude REAL,
    primary_news_source TEXT
)
```

### Data Source Breakdown
| Source | Count |
|--------|-------|
| official_permit | 65 |
| media_reported | 41 |
| both | 50 |

### The 41 Media-Only Projects (NOT in housing_projects_FINAL.csv)

These are projects reported in news but without official permits yet:

| Address | Primary News Source | Notes |
|---------|-------------------|-------|
| **North Berkeley BART station** | | Major BART housing development |
| **Peoples Park** | | UC Berkeley student housing |
| **Golden Gate Fields** | | Massive waterfront development |
| **UC Berkeley Innovation Zone** | | Research campus |
| **Spenger's Parking Lot** | | Mixed-use redevelopment |
| **Berkeley Ferry/Pier Project** | | Waterfront amenity |
| **Gilman Forge Development** | | Industrial area redevelopment |
| **theLAB Life Sciences campus** | | Steel Wave project |
| **Ashby** | | BART station housing |
| **The Gateway** | | Major project |
| 2099 Martin Luther King | SFYimby | |
| 2037 Kala Bagai Wy | SFYimby | |
| 130-134 Berkeley Square | | |
| Upper Hearst | | UC Berkeley |
| Bechtel Engineering Center | | UC Berkeley |
| Heathcock Hall | | UC Berkeley |
| 2450-2480 Shattuck Ave. | | |
| 1708 Harmon St | SFYimby | |
| 2001 Ashby | Berkeleyside | |
| 2538 Durant | SFYimby | |
| 2439 Durant | Berkeleyside | |
| Channing and Ellsworth Parking Garage | | |
| 1207 Tenth St | SFYimby | |
| 3132 Martin Luther King | | |
| 1822-1828 San Pablo | | |
| 1931-1941 San Pablo | | |
| 2136-2154 San Pablo | | |
| 2959 San Pablo | SFYimby | |
| 3000 San Pablo | SFYimby | |
| 700 Grayson St | Berkeleyside | |
| 742 Grayson St | Berkeleyside | |
| 805 Jones St | SFYimby | |
| Aquatic Fourth Street | | |
| 1050 Monroe St | SFYimby | |
| New UC Undergraduate Building | | UC Berkeley |
| 2344 Fulton St | SFYimby | |
| Evans Hall Replacement | | UC Berkeley |
| New Parking Garage | | UC Berkeley |
| New beach volleyball courts | | UC Berkeley |

### Recommended Actions
1. **Track these media-reported projects** - they represent pipeline projects before permits filed
2. **Monitor for permit filings** - when permits appear, link to existing records
3. **Consider separate "future pipeline" view** combining all sources

---

## 3. accela_reports.db (288 KB)

### Summary
Contains classified zoning projects with housing type categorization. Includes applicant/owner contact information.

### record_details Table (37 rows)
```sql
CREATE TABLE record_details (
    permit_number TEXT PRIMARY KEY,
    record_status TEXT,
    address TEXT,
    description TEXT,
    applicant_name TEXT,      -- <-- CONTACT NAMES
    applicant_company TEXT,   -- <-- COMPANY NAMES
    applicant_email TEXT,     -- <-- EMAIL ADDRESSES
    owner_name TEXT,          -- <-- PROPERTY OWNERS
    attachment_count INTEGER,
    planner_name TEXT,
    planner_email TEXT,
    scraped_date TEXT
)
```

**Sample Data:**
| permit_number | address | applicant_company | owner_name |
|--------------|---------|-------------------|------------|
| ZP2020-0104 | 1914 FIFTH St | Trachtenberg Architects | JAMESTOWN PREMIER BERKELEY GRO |
| ZP2021-0158 | 130 BERKELEY Sq | Studio KDA | BERKELEY STATION PARTNERS LLC |
| ZP2022-0046 | 3000 SHATTUCK Ave | Trachtenberg Architects | 3000 SHATTUCK AVENUE LLC |

**Has applicant and owner contact info!** Useful for developer/owner analysis.

**No application/hearing/approval dates** - only `scraped_date` when data was collected.

### active_zoning_classified Table (153 rows)
```sql
CREATE TABLE active_zoning_classified (
    Permit_Number TEXT,
    Description TEXT,
    Address TEXT,
    Record_Status TEXT,
    Permit_Type TEXT,
    is_housing_production INTEGER,  -- 0 or 1
    housing_type TEXT,              -- Classification category
    estimated_units INTEGER,
    has_density_bonus INTEGER,
    has_adu INTEGER,
    adds_bedrooms INTEGER,
    is_conversion INTEGER,
    is_sb330 INTEGER
)
```

### Housing Type Classification
| Housing Type | Count |
|-------------|-------|
| Non-Housing | 91 |
| Major Housing (5+ units) | 32 |
| Small Housing (1-4 units) | 12 |
| Residential Addition | 5 |
| Bedroom Addition | 5 |
| Conversion to Housing | 4 |
| ADU | 4 |

**57 projects are classified as housing production** (is_housing_production=1)

### Large Housing Projects with Classifications
| Permit | Address | Units | Density Bonus | SB330 |
|--------|---------|-------|---------------|-------|
| ZP2024-0058 | 2700 SHATTUCK Ave | 276 | No | Yes |
| ZP2020-0104 | 1914 FIFTH St | 257 | Yes | No |
| ZP2024-0181 | 2029 UNIVERSITY Ave | 240 | Yes | No |
| ZP2022-0171 | 2601 SAN PABLO Ave | 223 | Yes | No |
| ZP2022-0116 | 2920 SHATTUCK Ave | 221 | Yes | No |
| ZP2024-0182 | 2029 UNIVERSITY Ave | 160 | Yes | No |
| ZP2024-0074 | 1581 UNIVERSITY Ave | 158 | Yes | Yes |
| ZP2024-0131 | 2115 KITTREDGE St | 148 | Yes | No |
| ZP2024-0077 | 2847 SHATTUCK Ave | 136 | Yes | Yes |
| ZP2022-0149 | 2420 SHATTUCK Ave | 132 | Yes | No |

### Classification Logic
The `housing_type` classification appears to be based on:
- **Major Housing (5+ units)**: Projects with 5+ estimated_units
- **Small Housing (1-4 units)**: Projects with 1-4 units
- **ADU**: Accessory dwelling unit projects
- **Bedroom Addition**: Projects adding bedrooms (adds_bedrooms=1)
- **Residential Addition**: General residential additions
- **Conversion to Housing**: is_conversion=1
- **Non-Housing**: All other zoning applications (fences, wireless antennas, etc.)

### Recommended Actions
1. **Use record_details for developer analysis** - who is building what
2. **Track density bonus and SB330 usage** - state law compliance
3. **Link to permit_events for full project timelines**

---

## Summary: Untapped Data Opportunities

### High-Value Hidden Data Found

| Database | Hidden Data | Potential Use |
|----------|-------------|---------------|
| berkeley_housing_analysis.db | **Permit workflow timeline dates** | Calculate processing times by stage |
| berkeley_housing_analysis.db | **Fee payment amounts with dates** | Total fees paid per project |
| berkeley_housing_analysis.db | **Permit cross-references** | Link planning → building permits |
| berkeley_address_centric.db | **41 media-only projects** | Early pipeline tracking |
| accela_reports.db | **Applicant/owner contacts** | Developer analysis |
| accela_reports.db | **Housing type classifications** | Filter housing vs non-housing |

### Recommended Integration

1. **Join berkeley_housing_analysis.db tables** to housing_projects_FINAL.csv for full timeline data
2. **Create "expanded pipeline" view** combining official permits + media-reported projects
3. **Build fee summary per project** from permit_fees table
4. **Track permit processing times** from permit_events dates
