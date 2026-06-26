-- ============================================================================
-- Berkeley Housing Pipeline — v4 SCHEMA
-- Architecture: a SOURCED, TYPED, ACTOR-ATTRIBUTED LIFECYCLE EVENT STREAM is the
-- spine (append-only ground truth). All entities (parcels, structures, units,
-- projects, actors) are PROJECTIONS over that stream. Classification, identity,
-- and completion verdicts are REVERSIBLE LABELS written on top of permanent
-- evidence — never gates that delete.
--
-- THE ONE INVARIANT (the anti-vanishing rule):
--   Ingestion is unconditional. Nothing downstream of ingestion may delete a row.
--   Classification writes a LABEL; identity writes a PROJECTION; neither removes
--   evidence. Data can be mislabeled or mis-projected (both detectable, both
--   reversible) — it can never silently vanish.
--
-- City-neutral by design: the lifecycle vocabulary is ABSTRACT; Berkeley is the
-- first ADAPTER, not the template. Other cities map their API events INTO this.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ============================================================================
-- LAYER 0 — PROVENANCE & SOURCES (spans everything; first-class for journalism)
-- ============================================================================

-- Every fact in the DB points back to a source row here. No source => no fact.
CREATE TABLE sources (
    source_id        INTEGER PRIMARY KEY,
    source_kind      TEXT NOT NULL,        -- 'cpra_permit_feed','assessor','accela_inspection','ckan_apr','deed_doc','staff_doc','manual'
    city             TEXT NOT NULL DEFAULT 'Berkeley',
    locator          TEXT,                 -- file path, API endpoint, request id (e.g. CPRA 26-1525)
    retrieved_at     TEXT,                 -- ISO8601 — when WE obtained it (transaction-time anchor)
    source_asof      TEXT,                 -- ISO8601 — the source's own as-of date, if stated
    checksum         TEXT,                 -- integrity (magic-byte / sha)
    notes            TEXT
);

-- Re-runnable ingestion conservation ledger: proves count-in == count-out.
-- This is the SINGLE GUARDED BOUNDARY where vanishing is still possible.
CREATE TABLE ingestion_runs (
    run_id           INTEGER PRIMARY KEY,
    source_id        INTEGER NOT NULL REFERENCES sources(source_id),
    started_at       TEXT NOT NULL,
    rows_in_source   INTEGER NOT NULL,     -- counted at the source
    rows_ingested    INTEGER NOT NULL,     -- events emitted
    rows_rejected    INTEGER NOT NULL DEFAULT 0,
    rejected_detail  TEXT,                 -- WHY each rejected row failed (never silent)
    conserved        INTEGER NOT NULL,     -- 1 iff rows_in_source == rows_ingested + rows_rejected
    classifier_hash  TEXT,
    CHECK (conserved IN (0,1))
);

-- ============================================================================
-- LAYER 1 — THE EVENT STREAM (the spine; append-only ground truth)
-- ============================================================================

-- Abstract, city-neutral lifecycle phases. Berkeley's concrete event types map
-- INTO these (adapters target this vocabulary). Ordered to enable duration/stall.
CREATE TABLE lifecycle_phases (
    phase_code       TEXT PRIMARY KEY,     -- 'CONCEPT','ENTITLEMENT_APPLIED','ENTITLEMENT_APPROVED',
                                           -- 'BP_APPLIED','BP_ISSUED','CONSTRUCTION','INSPECTION',
                                           -- 'COMPLETION','TENURE_SALE','TENURE_LEASE','RENOVATION','DEMOLITION'
    phase_order      INTEGER NOT NULL,     -- canonical sequence position (for stall/velocity math)
    assessment_half  TEXT NOT NULL,        -- 'existing' vs later 'change' (Steinitz framing, optional use)
    description      TEXT
);

-- Abstract event types within phases (still city-neutral). Adapters map concrete
-- city event labels to one of these.
CREATE TABLE event_types (
    event_type_code  TEXT PRIMARY KEY,     -- e.g. 'bp_issued','co_issued','permit_finaled','inspection_passed'
    phase_code       TEXT NOT NULL REFERENCES lifecycle_phases(phase_code),
    is_completion_signal INTEGER NOT NULL DEFAULT 0,  -- feeds completion verdict
    description      TEXT,
    CHECK (is_completion_signal IN (0,1))
);

-- THE SPINE. One row per sourced event. APPEND-ONLY. Never UPDATEd, never DELETEd.
-- Everything else in the schema is a projection or label over this table.
CREATE TABLE events (
    event_id         INTEGER PRIMARY KEY,
    event_type_code  TEXT NOT NULL REFERENCES event_types(event_type_code),
    event_date       TEXT,                 -- ISO8601 world-time the event occurred (NULL = undated-but-attested)
    event_date_precision TEXT,             -- 'day','month','year','unknown' — honesty about date quality
    -- the natural key from the source (e.g. permit number) — NOT an identity claim, just provenance:
    source_record_key TEXT,
    source_id        INTEGER NOT NULL REFERENCES sources(source_id),
    ingestion_run_id INTEGER NOT NULL REFERENCES ingestion_runs(run_id),
    -- raw payload preserved verbatim (never mutated) so re-classification is always possible:
    raw_payload      TEXT,                 -- JSON of the original source row
    -- convenience extracted fields (derived, re-derivable from raw_payload):
    raw_address      TEXT,
    raw_apn          TEXT,
    raw_description  TEXT,
    raw_units        INTEGER,
    created_at       TEXT NOT NULL         -- transaction-time: when WE recorded this event
);
CREATE INDEX idx_events_type   ON events(event_type_code);
CREATE INDEX idx_events_date   ON events(event_date);
CREATE INDEX idx_events_srckey ON events(source_record_key);

-- ============================================================================
-- LAYER 2 — CLASSIFICATION (reversible LABELS on events; never deletes)
-- ============================================================================

-- The verdict layer of ADR-002, generalized. One CURRENT label per event,
-- overwrite-discipline, with the classifier hash as the staleness query.
-- An event the classifier deems irrelevant is LABELED so — never removed.
CREATE TABLE event_classifications (
    event_id         INTEGER NOT NULL REFERENCES events(event_id),
    housing_role     TEXT NOT NULL,        -- 'new_unit','adu','alteration','demolition','subsidiary',
                                           -- 'non_housing','phantom_candidate','ambiguous'
    is_master        INTEGER NOT NULL DEFAULT 0,  -- master construction permit => a structure's identity
    net_units        INTEGER,              -- derived from raw_units/OccType — PROSE-BLIND (never from description)
    classifier_hash  TEXT NOT NULL,        -- staleness query: hash != current => re-run
    classified_at    TEXT NOT NULL,
    basis            TEXT,                 -- 'evidentiary','description','human_override' (never 'ckan')
    basis_note       TEXT,
    PRIMARY KEY (event_id),                -- ONE current label per event (overwrite, idempotent re-run)
    CHECK (is_master IN (0,1))
);

-- Append-only human overrides / contested holds (the DECISIONS layer of ADR-002).
CREATE TABLE classification_decisions (
    decision_id      INTEGER PRIMARY KEY,
    event_id         INTEGER NOT NULL REFERENCES events(event_id),
    decided_by       TEXT NOT NULL,        -- a person (John, a planner) — append-only, never overwritten
    decided_at       TEXT NOT NULL,
    override_role    TEXT,
    rationale        TEXT NOT NULL,
    source_id        INTEGER REFERENCES sources(source_id)
);

-- ============================================================================
-- LAYER 3 — IDENTITY ENTITIES (PROJECTIONS over the stream; re-derivable)
-- ============================================================================
-- These tables are REBUILT by folding the classified event stream. A bad fold is
-- re-run, not re-scraped. None of these "owns" data the events don't already hold.

-- PARCEL — land. Stable internal identity; APNs are time-bounded attributes (ADR-003).
CREATE TABLE parcels (
    parcel_id        INTEGER PRIMARY KEY,  -- stable internal identity; NEVER the APN
    city             TEXT NOT NULL DEFAULT 'Berkeley',
    notes            TEXT
);
CREATE TABLE parcel_identifiers (         -- APNs as time-bounded external labels
    parcel_id        INTEGER NOT NULL REFERENCES parcels(parcel_id),
    apn_raw          TEXT NOT NULL,        -- source-faithful, NEVER mutated
    apn_normalized   TEXT,                 -- canonical (Option-B), for matching only
    valid_from       TEXT,                 -- sourced from recorded map when confirmed
    valid_to         TEXT,
    is_current       INTEGER NOT NULL DEFAULT 1,
    county           TEXT NOT NULL DEFAULT 'Alameda',
    source_id        INTEGER REFERENCES sources(source_id),
    PRIMARY KEY (parcel_id, apn_raw)
);
CREATE TABLE parcel_lineage (             -- splits/merges — CANDIDATE until confirmed vs recorded map
    parent_parcel_id INTEGER NOT NULL REFERENCES parcels(parcel_id),
    child_parcel_id  INTEGER NOT NULL REFERENCES parcels(parcel_id),
    event_type       TEXT NOT NULL,        -- 'sb9_split','merger','lot_line_adj','condo_map','renumber'
    status           TEXT NOT NULL DEFAULT 'candidate',  -- 'candidate' | 'confirmed'
    recorded_map_ref TEXT,
    source_id        INTEGER REFERENCES sources(source_id),
    PRIMARY KEY (parent_parcel_id, child_parcel_id, event_type)
);

-- STRUCTURE — a physical building. Identity = its master construction permit-event.
-- This is the projection that S1.5 was trying to compute via a discriminator;
-- here it's a fold: a structure is the event-stream coherent around one master.
CREATE TABLE structures (
    structure_id     INTEGER PRIMARY KEY,
    master_event_id  INTEGER REFERENCES events(event_id),  -- the New master permit-event (identity)
    building_label   TEXT,                 -- 'North Building','Phase II', etc. (from raw_description)
    structure_type   TEXT,                 -- 'duplex','sfd','multifamily','adu',...
    stories          INTEGER,
    status           TEXT,                 -- derived from the latest classified event
    completed_on     TEXT,                 -- = MAX(completion-signal event_date) over this structure's events
    projection_run_id INTEGER,             -- which fold produced this row (re-derivable)
    notes            TEXT
);
-- which events belong to which structure (the fold result; re-buildable)
CREATE TABLE structure_events (
    structure_id     INTEGER NOT NULL REFERENCES structures(structure_id),
    event_id         INTEGER NOT NULL REFERENCES events(event_id),
    role_in_structure TEXT,                -- 'master','subsidiary','inspection','co',...
    PRIMARY KEY (structure_id, event_id)
);

-- UNIT — a dwelling. Lives in a STRUCTURE (the edge v2/v3 never wired).
CREATE TABLE units (
    unit_id          INTEGER PRIMARY KEY,
    structure_id     INTEGER NOT NULL REFERENCES structures(structure_id),
    unit_count       INTEGER NOT NULL,     -- usually 1; aggregate tail may batch
    tenure           TEXT,                 -- 'owner','renter','unknown'
    affordability_tier TEXT,               -- 'vli','li','mod','above_mod','acutely_low','unknown'
    dr_ndr           TEXT,                 -- deed-restricted / non — from a deed doc if sourced
    source_id        INTEGER REFERENCES sources(source_id)  -- the deed/permit attesting this unit
);

-- PROJECT/DEVELOPMENT — human grouping spanning parcels & structures.
CREATE TABLE projects (
    project_id       INTEGER PRIMARY KEY,
    name             TEXT,                 -- 'Logan Park','Acheson Commons'
    notes            TEXT
);

-- ----- M:N BRIDGES (reality is M:N; never collapse one into another's key) -----
CREATE TABLE structure_parcels (          -- a structure can span parcels (condos)
    structure_id INTEGER NOT NULL REFERENCES structures(structure_id),
    parcel_id    INTEGER NOT NULL REFERENCES parcels(parcel_id),
    is_primary   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (structure_id, parcel_id)
);
CREATE TABLE project_structures (
    project_id   INTEGER NOT NULL REFERENCES projects(project_id),
    structure_id INTEGER NOT NULL REFERENCES structures(structure_id),
    PRIMARY KEY (project_id, structure_id)
);
CREATE TABLE project_parcels (
    project_id INTEGER NOT NULL REFERENCES projects(project_id),
    parcel_id  INTEGER NOT NULL REFERENCES parcels(parcel_id),
    PRIMARY KEY (project_id, parcel_id)
);
-- ADDRESS as a first-class M:N attribute, never an identity key
CREATE TABLE addresses (
    address_id   INTEGER PRIMARY KEY,
    number       TEXT, street TEXT, stype TEXT, unit_suffix TEXT,
    normalized   TEXT
);
CREATE TABLE structure_addresses (
    structure_id INTEGER NOT NULL REFERENCES structures(structure_id),
    address_id   INTEGER NOT NULL REFERENCES addresses(address_id),
    PRIMARY KEY (structure_id, address_id)
);
CREATE TABLE parcel_addresses (
    parcel_id  INTEGER NOT NULL REFERENCES parcels(parcel_id),
    address_id INTEGER NOT NULL REFERENCES addresses(address_id),
    PRIMARY KEY (parcel_id, address_id)
);

-- ============================================================================
-- LAYER 4 — ACTORS (persons & orgs act on every entity; first-class for journalism)
-- ============================================================================
CREATE TABLE actors (
    actor_id     INTEGER PRIMARY KEY,
    actor_kind   TEXT NOT NULL,            -- 'person','organization'
    display_name TEXT NOT NULL,
    role_class   TEXT,                     -- 'city_staff','developer','architect','inspector','owner','applicant'
    notes        TEXT
);
-- THE actor index: who did what to which entity, when. The journalist's primary lens.
-- An action attaches to an EVENT (so its date & provenance come free from the spine).
CREATE TABLE actor_actions (
    action_id    INTEGER PRIMARY KEY,
    actor_id     INTEGER NOT NULL REFERENCES actors(actor_id),
    event_id     INTEGER REFERENCES events(event_id),     -- the action's anchor in the stream
    entity_type  TEXT,                     -- 'parcel','structure','unit','project','permit_event'
    entity_id    INTEGER,
    role         TEXT NOT NULL,            -- 'inspector','plan_checker','applicant','owner_of_record',...
    source_id    INTEGER REFERENCES sources(source_id),
    coverage_note TEXT                     -- e.g. '2% inspection coverage, spot-scrape' — caveat travels WITH the data
);
CREATE INDEX idx_actor_actions_actor ON actor_actions(actor_id);
CREATE INDEX idx_actor_actions_event ON actor_actions(event_id);

-- ============================================================================
-- LAYER 5 — ENRICHMENT (Berkeley-specific; thin/absent for other cities)
-- ============================================================================
CREATE TABLE assessed_values (            -- time-versioned; each refresh closes the prior row
    parcel_id    INTEGER NOT NULL REFERENCES parcels(parcel_id),
    land         REAL, improvements REAL, total_net_value REAL,
    est_annual_tax REAL, effective_rate REAL,
    as_of_date   TEXT NOT NULL,            -- sourced (assessor refresh date)
    valid_to     TEXT,
    source_id    INTEGER REFERENCES sources(source_id),
    PRIMARY KEY (parcel_id, as_of_date)
);
CREATE TABLE geometries (                 -- GeoJSON-as-TEXT for portability
    entity_type  TEXT NOT NULL,           -- 'parcel','structure'
    entity_id    INTEGER NOT NULL,
    geojson      TEXT NOT NULL,
    valid_from   TEXT, valid_to TEXT,
    source_id    INTEGER REFERENCES sources(source_id),
    PRIMARY KEY (entity_type, entity_id, valid_from)
);
-- spatial CONTEXT (the Model-1→Model-4 seam for geodesign; attach point per parcel)
CREATE TABLE parcel_context (
    parcel_id    INTEGER NOT NULL REFERENCES parcels(parcel_id),
    zoning_code  TEXT, allowed_density TEXT, overlay_districts TEXT,
    council_district TEXT, rhna_subarea TEXT, transit_proximity TEXT,
    source_id    INTEGER REFERENCES sources(source_id),
    PRIMARY KEY (parcel_id)
);

-- ============================================================================
-- LAYER 6 — EVALUATION (the oracle comparison; divergence is FIRST-CLASS data)
-- ============================================================================
-- The HCD/CKAN APR mirror — ORACLE ONLY, never a data source. Bitemporal:
-- carries submission-version so the CY2025 double-submission is representable.
CREATE TABLE oracle_apr (
    oracle_row_id    INTEGER PRIMARY KEY,
    reporting_year   INTEGER NOT NULL,
    table_name       TEXT NOT NULL,        -- 'A','A2',...
    submission_version TEXT,               -- world-time vs record-time: which submission
    payload          TEXT,                 -- the city's reported row (JSON)
    source_id        INTEGER NOT NULL REFERENCES sources(source_id)
);
-- Every divergence between our projection and the oracle, CATEGORIZED. Queryable.
CREATE TABLE divergences (
    divergence_id    INTEGER PRIMARY KEY,
    reporting_year   INTEGER,
    our_value        TEXT, oracle_value TEXT,
    entity_type      TEXT, entity_id INTEGER,
    category         TEXT NOT NULL,        -- 'coverage_gap','city_under_report','convention_difference','identity_caveat'
    explanation      TEXT NOT NULL,        -- every divergence is EXPLAINED, never bare
    is_contested     INTEGER NOT NULL DEFAULT 0,  -- only if an INDEPENDENT source disagrees (never city-disagreement)
    independent_source_id INTEGER REFERENCES sources(source_id),
    CHECK (is_contested IN (0,1))
);

-- ============================================================================
-- TEMPORAL / CONSUMER VIEWS — "fold the stream to a date"; consumers read these
-- ============================================================================
-- current structures (the default-facing projection)
CREATE VIEW v_current_structures AS
  SELECT s.* FROM structures s WHERE s.projection_run_id =
    (SELECT MAX(projection_run_id) FROM structures);

-- the APR A2-CO grain: completed units by structure by reporting year (the payoff).
-- Logan Park yields TWO rows here by construction (GROUP BY structure), not a rule.
CREATE VIEW v_apr_a2_co AS
  SELECT st.structure_id,
         CAST(strftime('%Y', st.completed_on) AS INTEGER) AS reporting_year,
         SUM(u.unit_count) AS completed_units
  FROM structures st
  JOIN units u ON u.structure_id = st.structure_id
  WHERE st.completed_on IS NOT NULL
  GROUP BY st.structure_id, reporting_year;

-- NOTE: point-in-time reconstruction ("as of :date") is a parameterized canned
-- query in Datasette over events: replay events WHERE event_date <= :date, then
-- re-fold. Not a stored view (the date is the parameter).
