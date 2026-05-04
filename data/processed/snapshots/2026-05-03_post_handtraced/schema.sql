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
    co_date TEXT
, height_stories INTEGER, height_feet INTEGER, is_uc_project INTEGER DEFAULT 0, construction_status TEXT, developer TEXT, architect TEXT, description TEXT, latitude REAL, longitude REAL, processing_days INTEGER, density_bonus INTEGER DEFAULT 0, vli_units INTEGER DEFAULT 0, apn TEXT, owner TEXT, accela_status TEXT, accela_status_date TEXT, construction_start TEXT, estimated_completion TEXT, sb35_flag INTEGER, sb330_flag INTEGER, ab2011_flag INTEGER, total_fees REAL, app_packet_mb REAL, construction_method TEXT, field_survey_date TEXT, field_survey_notes TEXT, demolition_permit_date TEXT, demolition_start_date TEXT, inspection_count INTEGER, first_inspection_date TEXT, last_inspection_date TEXT, final_inspection_date TEXT, density_bonus_pct REAL, construction_data_reliability TEXT, is_stalled INTEGER DEFAULT 0, fee_count INTEGER DEFAULT 0, unit_category TEXT, tenure TEXT, project_size TEXT, created_at TEXT, updated_at TEXT, bp_filed_date TEXT, total_units REAL, year INTEGER, pipeline_stage TEXT, construction_substage TEXT, coord_source TEXT, project_category TEXT DEFAULT 'housing_addition');
CREATE TABLE sqlite_sequence(name,seq);
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
    permit_type TEXT, source_file TEXT,
    UNIQUE(permit_number, stage, action, event_date)
);
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
        );
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
            imported_at TEXT DEFAULT (datetime('now'))
        , source_file TEXT);
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
    );
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
    );
CREATE TABLE project_documents (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    title TEXT,
    filename TEXT,
    url TEXT,
    document_type TEXT CHECK(document_type IN ('city_attachment', 'staff_report', 'zab_resolution', 'density_bonus', 'eir', 'news_article', 'photo', 'field_survey', 'research', 'other')),
    source TEXT,
    date_added TEXT DEFAULT (date('now')),
    notes TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
CREATE TABLE data_collection_log (
    id INTEGER PRIMARY KEY,
    collection_date TEXT DEFAULT (datetime('now')),
    source TEXT,
    projects_updated INTEGER,
    events_added INTEGER,
    notes TEXT
);
CREATE VIEW apr_rhna_progress AS
SELECT
    'BERKELEY' as jurisdiction,
    CAST(year AS INTEGER) as year,
    SUM(CASE WHEN vli_units > 0 THEN vli_units ELSE 0 END) as very_low_income_units,
    0 as low_income_units,
    0 as moderate_income_units,
    SUM(CAST(units AS INTEGER)) - SUM(CASE WHEN vli_units > 0 THEN vli_units ELSE 0 END) as above_moderate_units,
    SUM(CAST(units AS INTEGER)) as total_units,
    COUNT(*) as project_count
FROM projects
GROUP BY year
ORDER BY year
/* apr_rhna_progress(jurisdiction,year,very_low_income_units,low_income_units,moderate_income_units,above_moderate_units,total_units,project_count) */;
CREATE VIEW apr_streamlining AS
SELECT
    CAST(year AS INTEGER) as year,
    SUM(CASE WHEN sb35_flag = 1 THEN 1 ELSE 0 END) as sb35_projects,
    SUM(CASE WHEN sb35_flag = 1 THEN CAST(units AS INTEGER) ELSE 0 END) as sb35_units,
    SUM(CASE WHEN sb330_flag = 1 THEN 1 ELSE 0 END) as sb330_projects,
    SUM(CASE WHEN sb330_flag = 1 THEN CAST(units AS INTEGER) ELSE 0 END) as sb330_units,
    SUM(CASE WHEN ab2011_flag = 1 THEN 1 ELSE 0 END) as ab2011_projects,
    SUM(CASE WHEN ab2011_flag = 1 THEN CAST(units AS INTEGER) ELSE 0 END) as ab2011_units,
    SUM(CASE WHEN density_bonus = 1 THEN 1 ELSE 0 END) as density_bonus_projects,
    SUM(CASE WHEN density_bonus = 1 THEN CAST(units AS INTEGER) ELSE 0 END) as density_bonus_units
FROM projects
GROUP BY year
ORDER BY year
/* apr_streamlining(year,sb35_projects,sb35_units,sb330_projects,sb330_units,ab2011_projects,ab2011_units,density_bonus_projects,density_bonus_units) */;
CREATE VIEW apr_unit_categories AS
SELECT
    CAST(year AS INTEGER) as year,
    unit_category,
    tenure,
    COUNT(*) as project_count,
    SUM(CAST(units AS INTEGER)) as total_units
FROM projects
GROUP BY year, unit_category, tenure
ORDER BY year, unit_category
/* apr_unit_categories(year,unit_category,tenure,project_count,total_units) */;
CREATE VIEW project_map AS
SELECT
    id,
    address_display,
    apn,
    permits,
    CAST(units AS INTEGER) as units,
    CAST(year AS INTEGER) as year,
    status,
    unit_category,
    tenure,
    CASE 
        WHEN sb330_flag = 1 THEN 'SB330'
        WHEN ab2011_flag = 1 THEN 'AB2011'
        WHEN sb35_flag = 1 THEN 'SB35'
        ELSE 'Standard'
    END as streamlining,
    CASE WHEN density_bonus = 1 THEN 'Yes' ELSE 'No' END as density_bonus,
    latitude,
    longitude
FROM projects
WHERE latitude IS NOT NULL
/* project_map(id,address_display,apn,permits,units,year,status,unit_category,tenure,streamlining,density_bonus,latitude,longitude) */;
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
);
CREATE TABLE IF NOT EXISTS "vocabulary_geometry_types" (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);
CREATE INDEX idx_geometries_project ON project_geometries(project_id);
CREATE INDEX idx_geometries_type ON project_geometries(geometry_type_id);
CREATE UNIQUE INDEX idx_one_current_geometry
ON project_geometries(project_id, geometry_type_id)
WHERE is_current = 1;
