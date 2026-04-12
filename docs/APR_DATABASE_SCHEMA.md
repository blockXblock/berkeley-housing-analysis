# HCD Annual Progress Report - Database Schema

## Purpose
Track housing project timelines to automate California HCD Annual Progress Report (APR) generation.

## Data Sources

### Primary Sources
1. **Berkeley Accela Citizen Portal** - https://aca-prod.accela.com/BERKELEY/
   - Building permits (since 1993, digitized since 2015)
   - Permit status, dates, inspection history

2. **Berkeley Building Eye** - https://berkeley.buildingeye.com/
   - Visual permit map with CSV export
   - Building and planning permits

3. **City of Berkeley Open Data** (when available)
   - Permit records
   - Planning applications

### Secondary Sources
4. **Alameda County Assessor** - APN lookups, property details
5. **Existing Gellerman data** - Project metadata, news coverage
6. **Our geocoded addresses** - 62,226 Berkeley addresses with APNs

---

## New Database Tables

### 1. `permit_applications`
Tracks each permit application from submission to completion.

```sql
CREATE TABLE permit_applications (
    permit_id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES projects(project_id),
    address_id INTEGER REFERENCES addresses(address_id),

    -- Identifiers (APR fields 1-4)
    apn TEXT,                           -- APR Field 1 (required)
    street_address TEXT,                -- APR Field 2 (required)
    project_name TEXT,                  -- APR Field 3 (optional)
    local_tracking_id TEXT,             -- APR Field 4 - permit number

    -- Permit Type
    permit_type TEXT,                   -- 'building', 'planning', 'use_permit', 'design_review'
    permit_subtype TEXT,                -- 'new_construction', 'addition', 'remodel', etc.

    -- Timeline Dates (APR fields 5-9)
    date_submitted DATE,                -- APR Field 5
    date_deemed_complete DATE,          -- APR Field 6
    date_entitlement_issued DATE,       -- APR Field 7
    date_building_permit_issued DATE,   -- APR Field 8
    date_certificate_occupancy DATE,    -- APR Field 9

    -- Current Status
    current_status TEXT,                -- 'submitted', 'under_review', 'approved', 'issued', 'final', 'expired'

    -- Metadata
    data_source TEXT,                   -- 'accela', 'building_eye', 'manual'
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_permit_project ON permit_applications(project_id);
CREATE INDEX idx_permit_address ON permit_applications(address_id);
CREATE INDEX idx_permit_status ON permit_applications(current_status);
CREATE INDEX idx_permit_dates ON permit_applications(date_building_permit_issued, date_certificate_occupancy);
```

### 2. `permit_timeline_events`
Granular tracking of each milestone/status change.

```sql
CREATE TABLE permit_timeline_events (
    event_id INTEGER PRIMARY KEY,
    permit_id INTEGER REFERENCES permit_applications(permit_id),

    event_type TEXT NOT NULL,           -- 'submitted', 'complete', 'review', 'revision', 'approved', 'issued', 'inspection', 'final'
    event_date DATE NOT NULL,
    event_description TEXT,

    -- Processing metrics
    days_since_previous INTEGER,        -- Days since last event
    reviewer_department TEXT,           -- 'Planning', 'Building', 'Fire', 'Public Works'

    data_source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_event_permit ON permit_timeline_events(permit_id);
CREATE INDEX idx_event_date ON permit_timeline_events(event_date);
CREATE INDEX idx_event_type ON permit_timeline_events(event_type);
```

### 3. `affordability_tracking`
Income category tracking for APR reporting.

```sql
CREATE TABLE affordability_tracking (
    affordability_id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES projects(project_id),
    permit_id INTEGER REFERENCES permit_applications(permit_id),

    -- APR Fields 10-14: Units by Income Category
    units_acutely_low INTEGER DEFAULT 0,    -- <15% AMI (new AB 3093)
    units_extremely_low INTEGER DEFAULT 0,  -- 15-30% AMI (new AB 3093)
    units_very_low INTEGER DEFAULT 0,       -- 30-50% AMI
    units_low INTEGER DEFAULT 0,            -- 50-80% AMI
    units_moderate INTEGER DEFAULT 0,       -- 80-120% AMI
    units_above_moderate INTEGER DEFAULT 0, -- >120% AMI (market rate)

    -- APR Field 15: Tenure
    tenure TEXT,                            -- 'rental', 'ownership', 'mixed'

    -- APR Fields 16-18: Affordability Mechanism
    deed_restricted BOOLEAN DEFAULT FALSE,
    affordability_term_years INTEGER,       -- Length of affordability covenant
    funding_source TEXT,                    -- 'LIHTC', 'local_bonds', 'inclusionary', etc.

    -- Verification
    verified_date DATE,
    verification_source TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_afford_project ON affordability_tracking(project_id);
```

### 4. `apr_submissions`
Track our APR generation history.

```sql
CREATE TABLE apr_submissions (
    submission_id INTEGER PRIMARY KEY,
    reporting_year INTEGER NOT NULL,        -- e.g., 2024

    -- Submission details
    submission_date DATE,
    submitted_to TEXT DEFAULT 'HCD',

    -- Summary statistics
    total_projects INTEGER,
    total_units INTEGER,
    units_entitled INTEGER,
    units_permitted INTEGER,
    units_completed INTEGER,

    -- RHNA Progress
    rhna_very_low_target INTEGER,
    rhna_very_low_progress INTEGER,
    rhna_low_target INTEGER,
    rhna_low_progress INTEGER,
    rhna_moderate_target INTEGER,
    rhna_moderate_progress INTEGER,
    rhna_above_moderate_target INTEGER,
    rhna_above_moderate_progress INTEGER,

    -- File references
    apr_file_path TEXT,                     -- Path to generated APR Excel file

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Views for APR Generation

### `apr_table_a2_view`
Ready-to-export view matching HCD Table A2 format.

```sql
CREATE VIEW apr_table_a2_view AS
SELECT
    pa.apn AS "APN",
    pa.street_address AS "Street Address",
    pa.project_name AS "Project Name",
    pa.local_tracking_id AS "Local Jurisdiction Tracking ID",
    strftime('%m/%d/%Y', pa.date_submitted) AS "Date Application Submitted",
    strftime('%m/%d/%Y', pa.date_deemed_complete) AS "Date Deemed Complete",
    strftime('%m/%d/%Y', pa.date_entitlement_issued) AS "Date Entitlement Issued",
    strftime('%m/%d/%Y', pa.date_building_permit_issued) AS "Date Building Permit Issued",
    strftime('%m/%d/%Y', pa.date_certificate_occupancy) AS "Date Certificate of Occupancy",
    COALESCE(af.units_very_low, 0) AS "Very Low Income Units",
    COALESCE(af.units_low, 0) AS "Low Income Units",
    COALESCE(af.units_moderate, 0) AS "Moderate Income Units",
    COALESCE(af.units_above_moderate, 0) AS "Above Moderate Income Units",
    af.tenure AS "Tenure",
    CASE WHEN af.deed_restricted THEN 'Yes' ELSE 'No' END AS "Deed Restricted",
    af.affordability_term_years AS "Term of Affordability (Years)",
    af.funding_source AS "Funding Source"
FROM permit_applications pa
LEFT JOIN affordability_tracking af ON pa.permit_id = af.permit_id
WHERE pa.date_building_permit_issued IS NOT NULL
   OR pa.date_certificate_occupancy IS NOT NULL
   OR pa.date_entitlement_issued IS NOT NULL
ORDER BY pa.date_building_permit_issued DESC;
```

### `permit_processing_times`
Analytics view for processing time analysis.

```sql
CREATE VIEW permit_processing_times AS
SELECT
    pa.permit_id,
    pa.street_address,
    pa.permit_type,
    pa.date_submitted,
    pa.date_deemed_complete,
    pa.date_building_permit_issued,
    pa.date_certificate_occupancy,
    julianday(pa.date_deemed_complete) - julianday(pa.date_submitted) AS days_to_complete,
    julianday(pa.date_building_permit_issued) - julianday(pa.date_deemed_complete) AS days_to_permit,
    julianday(pa.date_certificate_occupancy) - julianday(pa.date_building_permit_issued) AS days_to_final,
    julianday(pa.date_certificate_occupancy) - julianday(pa.date_submitted) AS total_days
FROM permit_applications pa
WHERE pa.date_submitted IS NOT NULL;
```

---

## Data Collection Workflow

### Phase 1: Scrape Existing Data
1. **Building Eye Export** - Download CSV of all permits, parse dates
2. **Accela Portal** - Search by address for each known project, extract timeline
3. **Cross-reference** - Match to our existing 157 projects

### Phase 2: Ongoing Updates
1. **Weekly scrape** - Check for new permits and status changes
2. **Alert system** - Flag projects that advance to new milestones

### Phase 3: APR Generation
1. **Filter by year** - Select permits with activity in reporting year
2. **Export to Excel** - Match HCD template format
3. **Validation** - Check required fields, income category documentation

---

## Example Queries

### Projects permitted in 2024
```sql
SELECT * FROM permit_applications
WHERE strftime('%Y', date_building_permit_issued) = '2024';
```

### Average processing time by permit type
```sql
SELECT
    permit_type,
    AVG(days_to_permit) as avg_days_to_permit,
    COUNT(*) as permit_count
FROM permit_processing_times
GROUP BY permit_type;
```

### RHNA progress summary
```sql
SELECT
    SUM(units_very_low) as very_low_units,
    SUM(units_low) as low_units,
    SUM(units_moderate) as moderate_units,
    SUM(units_above_moderate) as above_moderate_units,
    SUM(units_very_low + units_low + units_moderate + units_above_moderate) as total_units
FROM affordability_tracking af
JOIN permit_applications pa ON af.permit_id = pa.permit_id
WHERE pa.date_certificate_occupancy IS NOT NULL;
```
