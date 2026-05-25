# Inventory: berkeley_housing_analysis.db

## Database used

- **Path:** /Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db
- **File size:** 1,183,744 bytes (1.1 MB)
- **Modified:** 2026-05-03 20:24

## All tables

| Table | Row Count |
|-------|-----------|
| building_permits | 94 |
| data_collection_log | 1 |
| permit_events | 2306 |
| permit_fees | 441 |
| project_documents | 1423 |
| project_geometries | 184 |
| project_permits | 114 |
| projects | 179 |
| sfyimby_projects | 249 |
| vocabulary_geometry_types | 9 |

### Table schemas

**building_permits:**
```sql
CREATE TABLE building_permits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    permit_number TEXT NOT NULL UNIQUE,
    permit_type TEXT,
    address TEXT,
    status TEXT,
    filed_date TEXT,
    finaled_date TEXT,
    job_value TEXT,
    description TEXT,
    owner TEXT,
    applicant TEXT,
    source TEXT DEFAULT 'accela',
    imported_at TEXT DEFAULT (datetime('now')),
    source_file TEXT
)
```

**data_collection_log:**
```sql
CREATE TABLE data_collection_log (
    id INTEGER PRIMARY KEY,
    collection_date TEXT DEFAULT (datetime('now')),
    source TEXT,
    projects_updated INTEGER,
    events_added INTEGER,
    notes TEXT
)
```

**permit_events:**
```sql
CREATE TABLE permit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    address TEXT,
    permit_number TEXT,
    stage TEXT,
    action TEXT,
    event_date TEXT,
    assigned_to TEXT,
    marked_by TEXT,
    comment TEXT,
    stage_status TEXT,
    source TEXT DEFAULT 'accela',
    imported_at TEXT DEFAULT (datetime('now')),
    permit_type TEXT,
    source_file TEXT,
    UNIQUE(permit_number, stage, action, event_date)
)
```

**permit_fees:**
```sql
CREATE TABLE permit_fees (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    permit_number TEXT,
    address TEXT,
    fee_type TEXT,
    fee_description TEXT,
    amount REAL,
    date TEXT,
    source TEXT DEFAULT 'accela',
    FOREIGN KEY (project_id) REFERENCES projects(id)
)
```

**project_documents:**
```sql
CREATE TABLE project_documents (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    title TEXT,
    filename TEXT,
    url TEXT,
    document_type TEXT CHECK(document_type IN ('city_attachment', 'staff_report',
        'zab_resolution', 'density_bonus', 'eir', 'news_article', 'photo',
        'field_survey', 'research', 'other')),
    source TEXT,
    date_added TEXT DEFAULT (date('now')),
    notes TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
)
```

**project_geometries:**
```sql
CREATE TABLE project_geometries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    geometry_type_id INTEGER NOT NULL REFERENCES vocabulary_geometry_types(id),
    geojson TEXT NOT NULL,
    height_meters REAL,
    base_elevation_meters REAL,
    source_document_id INTEGER,
    version_label TEXT,
    edited_by TEXT,
    edit_notes TEXT,
    is_current INTEGER NOT NULL DEFAULT 1,
    superseded_by INTEGER REFERENCES project_geometries(id),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
)
```

**project_permits:**
```sql
CREATE TABLE project_permits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    permit_number TEXT NOT NULL UNIQUE,
    permit_type TEXT,
    permit_module TEXT,
    address TEXT,
    filed_date TEXT,
    status TEXT,
    status_date TEXT,
    is_primary INTEGER DEFAULT 0,
    source TEXT DEFAULT 'accela',
    imported_at TEXT DEFAULT (datetime('now')),
    permit_year INTEGER,
    permit_sequence INTEGER,
    permit_prefix TEXT
)
```

**projects:**
```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    address_display TEXT,
    units INTEGER,
    status TEXT,
    permits TEXT,
    filed TEXT,
    complete TEXT,
    entitled TEXT,
    bp_issued TEXT,
    co_date TEXT,
    height_stories INTEGER,
    height_feet INTEGER,
    is_uc_project INTEGER DEFAULT 0,
    construction_status TEXT,
    developer TEXT,
    architect TEXT,
    description TEXT,
    latitude REAL,
    longitude REAL,
    processing_days INTEGER,
    density_bonus INTEGER DEFAULT 0,
    vli_units INTEGER DEFAULT 0,
    apn TEXT,
    owner TEXT,
    accela_status TEXT,
    accela_status_date TEXT,
    construction_start TEXT,
    estimated_completion TEXT,
    sb35_flag INTEGER,
    sb330_flag INTEGER,
    ab2011_flag INTEGER,
    total_fees REAL,
    app_packet_mb REAL,
    construction_method TEXT,
    field_survey_date TEXT,
    field_survey_notes TEXT,
    demolition_permit_date TEXT,
    demolition_start_date TEXT,
    inspection_count INTEGER,
    first_inspection_date TEXT,
    last_inspection_date TEXT,
    final_inspection_date TEXT,
    density_bonus_pct REAL,
    construction_data_reliability TEXT,
    is_stalled INTEGER DEFAULT 0,
    fee_count INTEGER DEFAULT 0,
    unit_category TEXT,
    tenure TEXT,
    project_size TEXT,
    created_at TEXT,
    updated_at TEXT,
    bp_filed_date TEXT,
    total_units REAL,
    year INTEGER,
    pipeline_stage TEXT,
    construction_substage TEXT,
    coord_source TEXT,
    project_category TEXT DEFAULT 'housing_addition'
)
```

**sfyimby_projects:**
```sql
CREATE TABLE sfyimby_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address_raw TEXT,
    address_clean TEXT,
    project_name TEXT,
    units INTEGER,
    units_raw TEXT,
    status TEXT,
    date_raw TEXT,
    date_parsed TEXT,
    matched_project_id INTEGER,
    match_confidence TEXT
)
```

**vocabulary_geometry_types:**
```sql
CREATE TABLE vocabulary_geometry_types (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    description TEXT
)
```

## Tables of particular interest

### permit_events

- **Total row count:** 2,306
- **Date range:** 1998-11-24 to 2026-03-26
- **Distinct permits:** 126

**Distinct stage values (top 20):**

| stage | count |
|-------|-------|
| Unknown | 391 |
| Completeness Review | 357 |
| Inspection | 208 |
| Case Closed | 171 |
| Consolidated Comments | 156 |
| Application Processing | 121 |
| Public Works Review | 103 |
| Zoning Review | 89 |
| Building and Safety Review | 85 |
| PSC Review | 67 |
| Fire Review | 60 |
| CEQA Determination | 57 |
| Appeal | 46 |
| ness Review | 44 |
| Staff Decision | 44 |
| Issuance | 17 |
| Plan Distribution | 16 |
| Public Hearing | 14 |
| Application Processing [COMPLETE] | 13 |
| Stage: Case Closed | 12 |

**Sample rows:**

| id | permit_number | stage | action | event_date |
|----|---------------|-------|--------|------------|
| 686 | (empty) | Appeal | Hearing Notice | 2024-10-01 |
| 709 | (empty) | Appeal | No Appeal | 2025-01-21 |
| 694 | (empty) | Appeal | No Appeal | 2025-10-15 |
| 685 | (empty) | Appeal | No Appeal Filed | 2024-10-16 |
| 688 | (empty) | Appeal | Notice of Decision | 2024-10-01 |

Note: Some rows have empty permit_number values.

### permit_fees

- **Total row count:** 441
- **Sum of amounts:** $14,125,974.51
- **Distinct permits with fees:** 122
- **Distinct projects with fees:** 57

**Sample rows:**

| id | permit_number | fee_type | amount |
|----|---------------|----------|--------|
| 1 | B2024-01268 | (empty) | 2,192,720.87 |
| 2 | B2024-05944 | (empty) | 1,469,330.41 |
| 3 | B2024-05944 | (empty) | 1,467,705.41 |
| 4 | B2023-06416 | (empty) | 1,259,375.39 |
| 5 | B2021-02905 | (empty) | 965,120.98 |

Note: fee_type column is unpopulated in sample rows.

### projects

- **Total row count:** 179
- **Projects with lat/lng:** 179 (100%)
- **Projects with height_stories:** 179 (100%)

**Sample rows:**

| id | address_display | units | status | latitude | longitude | height_stories |
|----|-----------------|-------|--------|----------|-----------|----------------|
| 1 | 1750 SACRAMENTO St | 739 | Under Review | 37.874312 | -122.282959 | 8 |
| 2 | 2276 SHATTUCK Ave | 336 | In Review | 37.867738 | -122.268240 | 18 |
| 3 | 2700 SHATTUCK Ave | 359 | In Review | 37.859780 | -122.267828 | 15 |
| 4 | 1914 FIFTH St | 257 | Under Review | 37.868230 | -122.299296 | 15 |
| 5 | 2425 DURANT Ave | 117 | Pending Final Action | 37.867951 | -122.260142 | 20 |

### project_permits

- **Total row count:** 114

**Sample rows:**

| id | project_id | permit_number | permit_type | status |
|----|------------|---------------|-------------|--------|
| 1 | 133 | ZP2022-0135 | Planning | In Review |
| 2 | 1 | B2025-05534 | Building | In Review |
| 3 | 134 | DRCF2023-0005 | Other | In Review |
| 4 | 2 | LMSAP2024-0005 | Other | In Review |
| 5 | 127 | P2022-0038 | Other | In Review |

### Other tables containing 'document', 'event', 'fee', 'status', etc.

**project_documents:**
- Schema: see above
- Row count: 1,423
- Contains city attachments, staff reports, and other document references

**project_geometries:**
- Schema: see above
- Row count: 184
- Contains GeoJSON geometries with height data

**vocabulary_geometry_types:**
- Schema: see above
- Row count: 9
- Reference table for geometry type codes

**data_collection_log:**
- Row count: 1
- Single entry: 2026-02-24, "1750 Sacramento St - initial collection"

## Comparison to claims from April 2026 conversations

### Claim 1: "$14.1M in total fees, 122 projects with fees, 308+ fee records"

**Query:**
```sql
SELECT SUM(amount), COUNT(DISTINCT permit_number), COUNT(*) FROM permit_fees;
```

**Actual:** $14,125,974.51 total fees, 122 distinct permits, 441 fee records.

**Verdict:** MATCHES on fee total (~$14.1M) and permit count (122). Fee record count EXCEEDS claim (441 vs 308+). Note: the claim said "122 projects" but the query shows 122 distinct permits and only 57 distinct project_ids. The "122" likely referred to permits, not projects.

### Claim 2: "674+ permit events across 24+ permits"

**Query:**
```sql
SELECT COUNT(*), COUNT(DISTINCT permit_number) FROM permit_events;
```

**Actual:** 2,306 events across 126 distinct permits.

**Verdict:** FAR EXCEEDS claim. Data grew significantly since April (674 -> 2,306 events; 24 -> 126 permits). This is consistent with continued data collection after the April conversation.

### Claim 3: "2,294 events embedded into the explorer's DATA.events"

The explorer_data.js file would contain a snapshot. The database currently has 2,306 events.

**Verdict:** NEARLY MATCHES. Database has 2,306, which is close to the 2,294 figure. Small difference likely from events added between the export and the final database state.

## Open questions

1. **Empty permit_number in permit_events.** Sample rows show some permit_events records with empty permit_number values. These events may be project-level rather than permit-level, or may represent incomplete data collection.

2. **Empty fee_type in permit_fees.** The fee_type column appears unpopulated in sample rows. Fee categorization may have been deferred or the scraper didn't capture this field.

3. **Duplicate/overlapping tables.** Both `building_permits` (94 rows) and `project_permits` (114 rows) exist. The schema differences suggest they served different purposes:
   - building_permits: detailed permit info including job_value, description, owner
   - project_permits: permit-project linkage with parsed fields (permit_year, permit_sequence, permit_prefix)

   Unclear whether these are complementary or redundant.

4. **sfyimby_projects table.** 249 rows of external data with matched_project_id foreign key. Purpose: cross-referencing against SFYIMBY's housing tracker. Some rows may have NULL matched_project_id indicating unmatched projects.

5. **data_collection_log has only 1 entry.** Despite 2,306 events and extensive data, only one collection session was logged (2026-02-24). Either logging was inconsistent or most collection happened before logging was implemented.

6. **"ness Review" stage value.** Appears to be a truncated or malformed stage name (44 occurrences). Likely "Completeness Review" with leading characters stripped during parsing.

7. **project_documents.url field.** 1,423 document records exist. Unknown whether URLs are still valid or point to session-bound Accela links that have expired.

8. **Relationship to v2 database.** This database (berkeley_housing_analysis.db) appears to be the "v1" or "analysis" database, separate from berkeley_housing_v2.db. Column names and structures differ. Migration status between the two is unclear.
