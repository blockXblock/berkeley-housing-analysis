-- Migration 001: Add Timeline Tracking Fields
-- Purpose: Enable tracking of project start and end dates
-- Created: 2026-02-23
-- Datasette-compatible: Yes (facets, foreign keys, views)

-- ============================================================
-- PART 1: Add date columns to housing_projects table
-- ============================================================
-- Note: SQLite stores dates as TEXT in ISO-8601 format (YYYY-MM-DD)
-- Datasette will recognize these as dates for filtering

-- First permit submission date (project start)
ALTER TABLE housing_projects ADD COLUMN first_filed_date TEXT;  -- DATE as TEXT for Datasette

-- Zoning permit approval date
ALTER TABLE housing_projects ADD COLUMN zoning_approved_date TEXT;

-- Building permit issuance date
ALTER TABLE housing_projects ADD COLUMN building_permit_date TEXT;

-- Construction start date (first inspection or ground-breaking)
ALTER TABLE housing_projects ADD COLUMN construction_start_date TEXT;

-- Certificate of Occupancy date (project end)
ALTER TABLE housing_projects ADD COLUMN co_issued_date TEXT;

-- Is project completed? (0=No, 1=Yes for SQLite boolean)
ALTER TABLE housing_projects ADD COLUMN is_completed INTEGER DEFAULT 0;

-- Last status update date (for tracking staleness)
ALTER TABLE housing_projects ADD COLUMN last_status_date TEXT;

-- Data source for dates (facetable in Datasette)
ALTER TABLE housing_projects ADD COLUMN date_source TEXT;

-- Total days from filing to completion (calculated, for Datasette sorting)
ALTER TABLE housing_projects ADD COLUMN total_days INTEGER;

-- ============================================================
-- PART 2: Create permit_events table for detailed timeline
-- ============================================================
-- Datasette features: facets on permit_type, event_type, status
-- Foreign key to housing_projects enables automatic linking

CREATE TABLE IF NOT EXISTS permit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Link to housing project (Datasette will show as clickable link)
    project_id INTEGER REFERENCES housing_projects(id),

    -- Address for display and matching (denormalized for Datasette usability)
    address TEXT,

    -- Permit identification
    permit_number TEXT NOT NULL,          -- e.g., ZP2024-0067, BP2024-1234
    permit_type TEXT,                      -- 'Zoning', 'Building', 'Demolition', 'CO', 'Business'

    -- Event details
    event_type TEXT NOT NULL,             -- 'filed', 'approved', 'issued', 'denied', 'expired', 'appealed', 'finaled'
    event_date TEXT NOT NULL,             -- ISO-8601 format YYYY-MM-DD

    -- Status at time of event (facetable)
    status TEXT,
    status_detail TEXT,                   -- Additional status info

    -- Description/notes
    description TEXT,
    assigned_to TEXT,                     -- Planner or inspector name

    -- Data provenance (facetable for tracking data sources)
    source TEXT DEFAULT 'buildingeye',    -- Where this data came from
    source_url TEXT,                      -- Link to original record
    imported_at TEXT DEFAULT (datetime('now')),

    -- Prevent duplicate events
    UNIQUE(permit_number, event_type, event_date)
);

-- Indexes for common queries and Datasette performance
CREATE INDEX IF NOT EXISTS idx_permit_events_project ON permit_events(project_id);
CREATE INDEX IF NOT EXISTS idx_permit_events_permit ON permit_events(permit_number);
CREATE INDEX IF NOT EXISTS idx_permit_events_date ON permit_events(event_date);
CREATE INDEX IF NOT EXISTS idx_permit_events_type ON permit_events(permit_type);
CREATE INDEX IF NOT EXISTS idx_permit_events_event ON permit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_permit_events_address ON permit_events(address);

-- ============================================================
-- PART 3: Create view for project timeline summary
-- ============================================================
-- Datasette: This view provides a dashboard of project timelines
-- Users can sort by days_to_completion to find fastest/slowest projects

CREATE VIEW IF NOT EXISTS project_timeline_summary AS
SELECT
    hp.id,
    hp.address_display,
    hp.apn,
    hp.net_units,
    hp.status,
    hp.year,
    hp.project_size_category,
    hp.latitude,
    hp.longitude,

    -- Timeline dates (Datasette date filtering)
    hp.first_filed_date,
    hp.zoning_approved_date,
    hp.building_permit_date,
    hp.construction_start_date,
    hp.co_issued_date,
    CASE WHEN hp.is_completed = 1 THEN 'Yes' ELSE 'No' END AS completed,

    -- Calculated durations (in days) - sortable in Datasette
    CAST(JULIANDAY(hp.zoning_approved_date) - JULIANDAY(hp.first_filed_date) AS INTEGER) AS days_to_zoning_approval,
    CAST(JULIANDAY(hp.building_permit_date) - JULIANDAY(hp.zoning_approved_date) AS INTEGER) AS days_zoning_to_building,
    CAST(JULIANDAY(hp.co_issued_date) - JULIANDAY(hp.building_permit_date) AS INTEGER) AS days_construction,
    CAST(JULIANDAY(hp.co_issued_date) - JULIANDAY(hp.first_filed_date) AS INTEGER) AS days_total,

    -- Event counts from permit_events
    (SELECT COUNT(*) FROM permit_events pe WHERE pe.project_id = hp.id) AS event_count,
    (SELECT MAX(event_date) FROM permit_events pe WHERE pe.project_id = hp.id) AS last_event_date,

    -- Days since last activity (for identifying stalled projects)
    CAST(JULIANDAY('now') - JULIANDAY(
        COALESCE(
            (SELECT MAX(event_date) FROM permit_events pe WHERE pe.project_id = hp.id),
            hp.last_status_date,
            hp.first_filed_date
        )
    ) AS INTEGER) AS days_since_activity

FROM housing_projects hp;

-- ============================================================
-- PART 4: Create view for permit event timeline
-- ============================================================
-- Datasette: This view shows all permit events in chronological order
-- Facet by permit_type, event_type, or source

CREATE VIEW IF NOT EXISTS permit_timeline AS
SELECT
    pe.id,
    pe.project_id,
    pe.address,
    pe.permit_number,
    pe.permit_type,
    pe.event_type,
    pe.event_date,
    pe.status,
    pe.description,
    pe.assigned_to,
    pe.source,

    -- Link to project details
    hp.net_units,
    hp.year AS project_year,

    -- Days since previous event for same permit (workflow duration)
    CAST(JULIANDAY(pe.event_date) - JULIANDAY(
        LAG(pe.event_date) OVER (PARTITION BY pe.permit_number ORDER BY pe.event_date)
    ) AS INTEGER) AS days_since_previous

FROM permit_events pe
LEFT JOIN housing_projects hp ON pe.project_id = hp.id
ORDER BY pe.event_date DESC;

-- ============================================================
-- PART 5: Create view for stalled projects alert
-- ============================================================
-- Datasette: Quick view of projects needing attention

CREATE VIEW IF NOT EXISTS stalled_projects AS
SELECT
    hp.id,
    hp.address_display,
    hp.net_units,
    hp.status,
    hp.year,
    hp.first_filed_date,
    hp.last_status_date,
    CAST(JULIANDAY('now') - JULIANDAY(
        COALESCE(hp.last_status_date, hp.first_filed_date)
    ) AS INTEGER) AS days_inactive,
    hp.latitude,
    hp.longitude
FROM housing_projects hp
WHERE hp.is_completed = 0
  AND JULIANDAY('now') - JULIANDAY(
        COALESCE(hp.last_status_date, hp.first_filed_date)
      ) > 180
ORDER BY days_inactive DESC;

-- ============================================================
-- PART 6: Create view for completed projects
-- ============================================================

CREATE VIEW IF NOT EXISTS completed_projects AS
SELECT
    hp.id,
    hp.address_display,
    hp.net_units,
    hp.year,
    hp.first_filed_date,
    hp.co_issued_date,
    CAST(JULIANDAY(hp.co_issued_date) - JULIANDAY(hp.first_filed_date) AS INTEGER) AS days_to_completion,
    hp.latitude,
    hp.longitude
FROM housing_projects hp
WHERE hp.is_completed = 1
ORDER BY hp.co_issued_date DESC;
