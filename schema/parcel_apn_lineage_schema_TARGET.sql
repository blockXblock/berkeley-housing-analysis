-- parcel_apn_lineage_schema_TARGET.sql
--
-- TARGET (end-state) schema for the parcel-identity model — ADR-003's full model,
-- made STATEWIDE-GENERAL per the multi-county replicability goal (a JN that runs in
-- any California county). This is the DOCUMENTED TARGET; the MVP (see the _MVP file)
-- builds a populatable subset of this and grows into it as data sources arrive.
--
-- Design principles (ADR-003 + statewide generality):
--  1. APNs are EXTERNAL, TIME-BOUNDED identifiers — NOT the parcel's identity.
--  2. The internal parcel_id is the durable identity.
--  3. Lineage is RECORDED (parent/child events from maps/deeds) — never inferred
--     from APN string patterns (BOE: a split of parcel 2 may yield 9 and 10, not 2A/2B).
--  4. Geometry and identifiers are versioned by date/source; assessor history is
--     APPENDED (roll-year snapshots), never overwritten.
--  5. Store RAW (source-faithful) AND NORMALIZED (matching key) values.
--  6. AUTHORITY-SCOPED everything: an APN is unique only WITHIN its assessing
--     authority (county). The key is (county, apn_normalized), never apn_normalized
--     alone. to_canonical_apn(raw, county) dispatches per-county format rules.
--  7. NO jurisdiction is hardcoded in a table NAME or required column set — a new
--     county/city is DATA (new rows + a source-adapter config), never a schema change.

PRAGMA foreign_keys = ON;

-- ===========================================================================
-- AUTHORITY REGISTRY — the per-jurisdiction generality layer
-- One row per assessing/recording authority. The APN-format rules, source
-- endpoints, and overlay vocabulary for a county/city live HERE (referenced by
-- the source-adapter config), so adding a county is a registry row, not code.
-- ===========================================================================

CREATE TABLE IF NOT EXISTS jurisdictions (
    jurisdiction_id     INTEGER PRIMARY KEY,
    jurisdiction_type   TEXT NOT NULL
        CHECK (jurisdiction_type IN ('county', 'city', 'special_district')),
    name                TEXT NOT NULL,          -- 'Alameda', 'Berkeley', 'Oakland', 'San Diego'
    state               TEXT NOT NULL DEFAULT 'CA',
    -- For counties: the assessing AUTHORITY whose APNs scope uniqueness.
    -- For cities: the parent county whose assessor numbers their parcels.
    parent_county       TEXT,                   -- e.g. Berkeley/Oakland -> 'Alameda'
    -- APN-format descriptor for to_canonical_apn(raw, county): segment widths /
    -- separators / max sub-depth. Stored as JSON-in-TEXT for portability.
    -- apn_format: the per-county canonicalization + VALIDATION descriptor that
    -- to_canonical_apn(raw, county) and the enforcement trigger BOTH read. Must carry
    -- STRUCTURE, per-segment CHARACTER CLASS (APNs are alphanumeric in the general case —
    -- BOE: numeric OR alphanumeric; letter suffixes on subdivided/condo/amended parcels),
    -- separators, canonical length, and the validation PATTERN. NOT just segment widths.
    --   Alameda = {"structure":"book-page-parcel-sub","segment_widths":[3,4,3,2],
    --              "char_class":"alphanumeric","separators":["-"," "],"total_length":12,
    --              "pattern":"^[0-9A-Z]{12,14}$"}   (25/30007 carry a book letter, e.g. 48A/48H)
    --   SF (future) = {"structure":"block-lot", ...}  -- different structure AND char-class
    apn_format          TEXT,
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (jurisdiction_type, name, state)
);

CREATE INDEX IF NOT EXISTS idx_jurisdictions_name ON jurisdictions(name);
CREATE INDEX IF NOT EXISTS idx_jurisdictions_parent ON jurisdictions(parent_county);

-- ===========================================================================
-- CORE PARCEL IDENTITY
-- ===========================================================================

CREATE TABLE IF NOT EXISTS parcels (
    parcel_id               INTEGER PRIMARY KEY,
    -- The assessing AUTHORITY (county) that scopes this parcel's APN uniqueness.
    assessing_county        TEXT NOT NULL DEFAULT 'Alameda',
    -- The local jurisdiction (city) for planning/permitting context.
    jurisdiction            TEXT,               -- 'Berkeley', 'Oakland', ...
    current_apn_raw         TEXT,               -- source-faithful (hyphens/zeros preserved)
    current_apn_normalized  TEXT,               -- matching key (digits, segment structure, VARIABLE length)
    status                  TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','retired','split','merged','superseded','unknown')),
    created_by_event_id     INTEGER,
    retired_by_event_id     INTEGER,
    valid_from              DATE,
    valid_to                DATE,
    notes                   TEXT,
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by_event_id) REFERENCES parcel_events(event_id),
    FOREIGN KEY (retired_by_event_id) REFERENCES parcel_events(event_id)
);

-- AUTHORITY-SCOPED uniqueness: the same normalized digit-string in two counties
-- is two different parcels. Uniqueness is (county, normalized), NEVER normalized alone.
-- (Partial: only the CURRENT active APN must be unique per authority; retired
--  parcels may share a prior number across eras, handled via parcel_identifiers.)
CREATE UNIQUE INDEX IF NOT EXISTS idx_parcels_authority_apn_current
    ON parcels(assessing_county, current_apn_normalized)
    WHERE current_apn_normalized IS NOT NULL AND status = 'active';

CREATE INDEX IF NOT EXISTS idx_parcels_apn_norm
    ON parcels(assessing_county, current_apn_normalized);
CREATE INDEX IF NOT EXISTS idx_parcels_status       ON parcels(status);
CREATE INDEX IF NOT EXISTS idx_parcels_jurisdiction ON parcels(jurisdiction);

-- ===========================================================================
-- IDENTIFIERS — APNs (current + prior eras), addresses, local IDs — time-bounded
-- ===========================================================================

CREATE TABLE IF NOT EXISTS parcel_identifiers (
    parcel_identifier_id    INTEGER PRIMARY KEY,
    parcel_id               INTEGER NOT NULL,
    assessing_county        TEXT NOT NULL DEFAULT 'Alameda',  -- scopes apn uniqueness
    identifier_type         TEXT NOT NULL
        CHECK (identifier_type IN (
            'apn','prior_apn','situs_address','mailing_address',
            'city_parcel_id','permit_system_parcel_id','source_row_id','other')),
    identifier_raw          TEXT NOT NULL,        -- source-faithful, NEVER mutated
    identifier_normalized   TEXT,                 -- matching key (for apn/prior_apn)
    source_name             TEXT,
    source_url              TEXT,
    source_file             TEXT,
    source_record_id        TEXT,
    valid_from              DATE,
    valid_to                DATE,
    is_current              INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0,1)),
    confidence              TEXT DEFAULT 'observed'
        CHECK (confidence IN ('observed','inferred','manual_review','unknown')),
    notes                   TEXT,
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parcel_id) REFERENCES parcels(parcel_id)
);

CREATE INDEX IF NOT EXISTS idx_pi_parcel        ON parcel_identifiers(parcel_id);
CREATE INDEX IF NOT EXISTS idx_pi_type_value    ON parcel_identifiers(identifier_type, identifier_raw);
-- AUTHORITY-SCOPED normalized lookup (the join key for matching APNs across sources):
CREATE INDEX IF NOT EXISTS idx_pi_norm_scoped   ON parcel_identifiers(assessing_county, identifier_type, identifier_normalized);
CREATE INDEX IF NOT EXISTS idx_pi_current       ON parcel_identifiers(parcel_id, identifier_type, is_current);

-- ===========================================================================
-- PARCEL EVENTS — recorded lineage (SB 9 split, merger, lot-line, condo, renumber)
-- Lineage comes from the RECORDED MAP/DEED, not APN strings. Our crosswalk
-- string-matches enter as confidence='inferred', status='candidate' until confirmed.
-- ===========================================================================

CREATE TABLE IF NOT EXISTS parcel_events (
    event_id            INTEGER PRIMARY KEY,
    assessing_county    TEXT NOT NULL DEFAULT 'Alameda',
    event_type          TEXT NOT NULL
        CHECK (event_type IN (
            'sb9_split','parcel_split','parcel_merger','lot_line_adjustment',
            'condo_map','subdivision_map','assessor_correction','apn_renumber',
            'geometry_update','other')),
    -- candidate (our inference) vs confirmed (against the recorded map)
    status              TEXT NOT NULL DEFAULT 'candidate'
        CHECK (status IN ('candidate','confirmed','rejected')),
    confidence          TEXT DEFAULT 'inferred'
        CHECK (confidence IN ('observed','inferred','manual_review','unknown')),
    event_date          DATE,
    effective_roll_year TEXT,
    recording_date      DATE,
    recording_number    TEXT,                   -- the authoritative confirm source
    map_reference       TEXT,
    city_case_number    TEXT,
    county_case_number  TEXT,
    permit_number       TEXT,
    evidence            TEXT,                   -- JSON: the converging signals (for candidates)
    source_name         TEXT,
    source_url          TEXT,
    source_file         TEXT,
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pe_type    ON parcel_events(event_type);
CREATE INDEX IF NOT EXISTS idx_pe_status  ON parcel_events(status);
CREATE INDEX IF NOT EXISTS idx_pe_date    ON parcel_events(event_date);
CREATE INDEX IF NOT EXISTS idx_pe_recnum  ON parcel_events(recording_number);
CREATE INDEX IF NOT EXISTS idx_pe_citecase ON parcel_events(city_case_number);

CREATE TABLE IF NOT EXISTS parcel_event_links (
    parcel_event_link_id    INTEGER PRIMARY KEY,
    event_id                INTEGER NOT NULL,
    parcel_id               INTEGER NOT NULL,
    relationship            TEXT NOT NULL
        CHECK (relationship IN (
            'parent','child','merged_from','merged_to',
            'adjusted_before','adjusted_after','renumbered_from','renumbered_to','affected')),
    apn_at_event_raw        TEXT,
    apn_at_event_normalized TEXT,
    area_sqft_at_event      REAL,
    notes                   TEXT,
    FOREIGN KEY (event_id)  REFERENCES parcel_events(event_id),
    FOREIGN KEY (parcel_id) REFERENCES parcels(parcel_id)
);

CREATE INDEX IF NOT EXISTS idx_pel_event  ON parcel_event_links(event_id);
CREATE INDEX IF NOT EXISTS idx_pel_parcel ON parcel_event_links(parcel_id);
CREATE INDEX IF NOT EXISTS idx_pel_rel    ON parcel_event_links(relationship);
CREATE UNIQUE INDEX IF NOT EXISTS idx_pel_unique
    ON parcel_event_links(event_id, parcel_id, relationship);

-- ===========================================================================
-- GEOMETRY VERSIONS — boundaries change on split; keep the history
-- ===========================================================================

CREATE TABLE IF NOT EXISTS parcel_geometry_versions (
    geometry_version_id     INTEGER PRIMARY KEY,
    parcel_id               INTEGER NOT NULL,
    apn_at_capture_raw      TEXT,
    geometry_wkt            TEXT,               -- WKT for SQLite portability (GeoJSON-as-TEXT alt OK)
    geometry_source         TEXT,
    geometry_source_url     TEXT,
    geometry_source_file    TEXT,
    srid                    INTEGER DEFAULT 4326,
    area_sqft               REAL,
    valid_from              DATE,
    valid_to                DATE,
    captured_at             TEXT,
    is_current              INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0,1)),
    notes                   TEXT,
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parcel_id) REFERENCES parcels(parcel_id)
);

CREATE INDEX IF NOT EXISTS idx_pgv_parcel   ON parcel_geometry_versions(parcel_id);
CREATE INDEX IF NOT EXISTS idx_pgv_current  ON parcel_geometry_versions(parcel_id, is_current);
CREATE INDEX IF NOT EXISTS idx_pgv_validity ON parcel_geometry_versions(valid_from, valid_to);

-- ===========================================================================
-- ASSESSOR SNAPSHOTS — county facts, APPENDED by roll-year (history preserved)
-- General across counties (source_name identifies which assessor).
-- ===========================================================================

CREATE TABLE IF NOT EXISTS assessor_parcel_snapshots (
    assessor_snapshot_id    INTEGER PRIMARY KEY,
    parcel_id               INTEGER,
    assessing_county        TEXT NOT NULL DEFAULT 'Alameda',
    apn_raw                 TEXT NOT NULL,
    apn_normalized          TEXT,
    roll_year               TEXT,
    situs_address           TEXT,
    owner_name              TEXT,
    mailing_address         TEXT,
    land_value              INTEGER,
    improvement_value       INTEGER,            -- the BUILT signal (Imps>0)
    total_net_value         INTEGER,            -- taxable (after exemptions)
    exemption_amount        INTEGER,            -- assessed - net (signed; the subsidy story)
    use_code                TEXT,
    tax_rate_area           TEXT,
    sale_date               DATE,
    transfer_date           DATE,
    lot_area_sqft           REAL,
    -- as-of provenance (the extract date is the currency marker, NOT a per-parcel field)
    snapshot_as_of          DATE,
    source_name             TEXT NOT NULL DEFAULT 'Alameda County Assessor',
    source_url              TEXT,
    source_file             TEXT,
    source_record_id        TEXT,
    ingested_at             TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes                   TEXT,
    FOREIGN KEY (parcel_id) REFERENCES parcels(parcel_id)
);

CREATE INDEX IF NOT EXISTS idx_aps_parcel   ON assessor_parcel_snapshots(parcel_id);
CREATE INDEX IF NOT EXISTS idx_aps_apn_norm ON assessor_parcel_snapshots(assessing_county, apn_normalized);
CREATE INDEX IF NOT EXISTS idx_aps_roll     ON assessor_parcel_snapshots(roll_year);

-- ===========================================================================
-- LOCAL-JURISDICTION SNAPSHOTS — planning/zoning/overlay facts, GENERAL
-- (renamed from berkeley_parcel_snapshots — a city name in a table name is the
--  Alameda-by-default trap). Local GIS OVERLAYS vary by city, so they are stored
--  KEY-VALUE (attribute_type/attribute_value) rather than fixed Berkeley columns
--  — another city's overlays are just different attribute_type values, no schema change.
-- ===========================================================================

CREATE TABLE IF NOT EXISTS local_jurisdiction_parcel_snapshots (
    local_snapshot_id       INTEGER PRIMARY KEY,
    parcel_id               INTEGER,
    jurisdiction            TEXT NOT NULL,      -- 'Berkeley', 'Oakland', ...
    apn_raw                 TEXT,
    apn_normalized          TEXT,
    situs_address           TEXT,
    -- Stable cross-city fields kept as columns (every city has these):
    zoning_district         TEXT,
    general_plan_land_use   TEXT,
    local_land_use          TEXT,
    snapshot_date           DATE,
    source_name             TEXT,               -- e.g. 'City of Berkeley'
    source_url              TEXT,
    source_file             TEXT,
    source_record_id        TEXT,
    ingested_at             TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes                   TEXT,
    FOREIGN KEY (parcel_id) REFERENCES parcels(parcel_id)
);

CREATE INDEX IF NOT EXISTS idx_ljs_parcel       ON local_jurisdiction_parcel_snapshots(parcel_id);
CREATE INDEX IF NOT EXISTS idx_ljs_jurisdiction ON local_jurisdiction_parcel_snapshots(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_ljs_zoning       ON local_jurisdiction_parcel_snapshots(zoning_district);

-- Per-jurisdiction GIS overlays (creek/seismic/fire/historic/...) — KEY-VALUE so
-- a new city's overlay set is data, not new columns.
CREATE TABLE IF NOT EXISTS local_parcel_overlays (
    local_parcel_overlay_id INTEGER PRIMARY KEY,
    local_snapshot_id       INTEGER NOT NULL,
    jurisdiction            TEXT NOT NULL,
    attribute_type          TEXT NOT NULL,      -- 'creek_overlay','seismic_hazard','fire_district','historic_status',...
    attribute_value         TEXT,
    source_name             TEXT,
    notes                   TEXT,
    FOREIGN KEY (local_snapshot_id) REFERENCES local_jurisdiction_parcel_snapshots(local_snapshot_id)
);

CREATE INDEX IF NOT EXISTS idx_lpo_snapshot ON local_parcel_overlays(local_snapshot_id);
CREATE INDEX IF NOT EXISTS idx_lpo_type     ON local_parcel_overlays(jurisdiction, attribute_type);

-- ===========================================================================
-- PROJECT ↔ PARCEL bridge (a project spans parcels; a parcel splits mid-project)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS project_parcel_links (
    project_parcel_link_id  INTEGER PRIMARY KEY,
    project_id              TEXT NOT NULL,
    parcel_id               INTEGER,
    apn_raw                 TEXT,
    apn_normalized          TEXT,
    relationship            TEXT NOT NULL DEFAULT 'project_site'
        CHECK (relationship IN (
            'project_site','primary_site','secondary_site','former_site',
            'new_child_site','offsite_improvement','unknown')),
    valid_from              DATE,
    valid_to                DATE,
    source_name             TEXT,
    source_url              TEXT,
    source_file             TEXT,
    notes                   TEXT,
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parcel_id) REFERENCES parcels(parcel_id)
);

CREATE INDEX IF NOT EXISTS idx_ppl_project ON project_parcel_links(project_id);
CREATE INDEX IF NOT EXISTS idx_ppl_parcel  ON project_parcel_links(parcel_id);
CREATE INDEX IF NOT EXISTS idx_ppl_apn     ON project_parcel_links(apn_normalized);

-- ===========================================================================
-- HELPER VIEWS
-- ===========================================================================

CREATE VIEW IF NOT EXISTS current_parcel_apns AS
SELECT
    p.parcel_id,
    p.assessing_county,
    COALESCE(p.current_apn_raw, pi.identifier_raw)               AS apn_raw,
    COALESCE(p.current_apn_normalized, pi.identifier_normalized) AS apn_normalized,
    p.jurisdiction,
    p.status,
    p.valid_from,
    p.valid_to
FROM parcels p
LEFT JOIN parcel_identifiers pi
    ON pi.parcel_id = p.parcel_id
   AND pi.identifier_type = 'apn'
   AND pi.is_current = 1
WHERE p.status = 'active';

CREATE VIEW IF NOT EXISTS parcel_lineage_edges AS
SELECT
    e.event_id, e.event_type, e.status, e.confidence, e.event_date,
    parent.parcel_id           AS parent_parcel_id,
    parent.apn_at_event_raw    AS parent_apn,
    child.parcel_id            AS child_parcel_id,
    child.apn_at_event_raw     AS child_apn,
    e.recording_number, e.map_reference, e.city_case_number, e.source_url
FROM parcel_events e
JOIN parcel_event_links parent
    ON parent.event_id = e.event_id
   AND parent.relationship IN ('parent','merged_from','renumbered_from','adjusted_before')
JOIN parcel_event_links child
    ON child.event_id = e.event_id
   AND child.relationship IN ('child','merged_to','renumbered_to','adjusted_after')
WHERE parent.parcel_id <> child.parcel_id;

-- ===========================================================================
-- NOTES ON STATEWIDE GENERALITY (the why, for future county adapters)
-- ===========================================================================
-- * No table or required column hardcodes a city/county — jurisdiction is DATA.
-- * APN uniqueness is (assessing_county, apn_normalized) everywhere. The same
--   normalized string in two counties is two parcels.
-- * to_canonical_apn(raw, county) reads the county's apn_format from `jurisdictions`
--   — adding a county is a registry row + a source-adapter config, NOT schema change.
-- * Local GIS overlays are key-value (local_parcel_overlays) — a new city's overlay
--   vocabulary is new attribute_type values, not new columns.
-- * Lineage is candidate→confirmed; confirmation needs the recorded-map/recorder
--   source (a per-county harvest adapter), which the model labels honestly rather
--   than pretending a string-match is fact.
