-- ============================================================================
-- housing pipeline: core schema
-- ============================================================================
-- This is the canonical normalized schema for the civic housing permit pipeline
-- framework, Berkeley-first but structured for multi-city adoption via
-- vocabulary tables and a city_id scope on all parcels and projects.
--
-- Design decisions (see docs/architecture.md and docs/migration-plan.md):
--   - SQLite is the single source of truth; exports are generated artifacts
--   - Foreign keys MUST be enabled on every connection (PRAGMA below)
--   - Vocabulary tables replace hardcoded enums throughout
--   - Fact-bearing tables carry a four-column provenance mixin
--   - Versioning uses is_current + partial unique indexes, not triggers
--   - project_stage_spans is a VIEW (see views_compat.sql), not a table
--
-- Insert order (two-pass pattern):
--   Because projects.current_version_id and project_versions.source_event_id
--   reference tables that reference back, initial inserts leave these NULL
--   and a second pass fills them in. See "Insert order" section in the
--   migration plan.
--
-- Enforcement layers:
--   - Schema constraints: FKs, CHECKs, UNIQUE / partial unique indexes
--   - Validation queries (scripts/validate/): rules that are awkward in SQL,
--     including the "non-proposal versions must have source_event_id" rule
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ============================================================================
-- SECTION 1: Cities
-- ============================================================================

CREATE TABLE cities (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL,                    -- e.g. 'berkeley'
  name TEXT NOT NULL,                    -- e.g. 'City of Berkeley'
  state TEXT,                            -- e.g. 'CA'
  country TEXT,                          -- e.g. 'US'
  UNIQUE (slug, state)
);

-- ============================================================================
-- SECTION 2: Vocabulary tables
-- ----------------------------------------------------------------------------
-- Every vocabulary table shares the same shape: id / code / label / description.
-- The "code" is the stable machine identifier; "label" is for display.
-- Other cities fork by editing vocabularies_<city>.sql, not this file.
-- ============================================================================

CREATE TABLE vocabulary_project_version_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_stage_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_substage_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT,
  parent_stage_type_id INTEGER REFERENCES vocabulary_stage_types(id)
);

CREATE TABLE vocabulary_tenure_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_special_population_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_income_categories (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_restriction_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_organization_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_role_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_permit_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_permit_status_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_document_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_event_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT,
  -- Which stage this event typically represents entry into, if any.
  -- Used by the project_stage_spans view to derive timeline bars from events.
  implies_stage_type_id INTEGER REFERENCES vocabulary_stage_types(id),
  implies_substage_type_id INTEGER REFERENCES vocabulary_substage_types(id)
);

CREATE TABLE vocabulary_confidence_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_relationship_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_geometry_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_asset_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

CREATE TABLE vocabulary_classification_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT,
  is_boolean INTEGER NOT NULL DEFAULT 1 CHECK (is_boolean IN (0,1))  -- 1 = flag (true/false), 0 = categorical
);

-- ============================================================================
-- SECTION 3: Projects (stable identity)
-- ----------------------------------------------------------------------------
-- The projects table holds only stable identity. Program facts (units, height,
-- affordability) live on project_versions and its children.
--
-- current_version_id is nullable at insert time (two-pass pattern) and
-- updated after the initial project_version row exists.
-- ============================================================================

CREATE TABLE projects (
  id INTEGER PRIMARY KEY,
  city_id INTEGER NOT NULL REFERENCES cities(id),

  -- Identity
  canonical_name TEXT,                   -- human-friendly name
  canonical_address TEXT NOT NULL,       -- primary street address (as displayed)
  normalized_address TEXT,               -- standardized form for dedupe
  latitude REAL,
  longitude REAL,

  -- Current-state pointers (populated in second pass after version/event rows exist)
  current_version_id INTEGER,            -- FK added below to break circular creation
  current_stage_type_id INTEGER REFERENCES vocabulary_stage_types(id),

  -- Metadata
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

  UNIQUE (city_id, canonical_address)
);

-- ============================================================================
-- SECTION 4: Documents
-- ----------------------------------------------------------------------------
-- Defined early because many fact-bearing tables carry source_document_id FKs.
-- Supports the three-tier mirror pattern: city source, Internet Archive, R2,
-- plus optional Google Drive as a fourth working mirror. See docs/architecture.md.
-- ============================================================================

CREATE TABLE documents (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  document_type_id INTEGER REFERENCES vocabulary_document_types(id),

  title TEXT,
  published_date TEXT,                   -- date on the document itself
  permit_number TEXT,                    -- cross-ref to permits table (not FK: document may predate permit row)

  -- Source (city system of record)
  source_url TEXT,                       -- e.g. Accela / Clariti document link
  source_system TEXT,                    -- 'accela', 'clariti', etc.
  source_document_id_external TEXT,      -- the document's ID in the source system
  url_last_verified TEXT,                -- ISO date; updated by scripts/documents/verify_urls.py
  url_status TEXT CHECK (url_status IN ('active', 'broken', 'moved', 'unknown') OR url_status IS NULL),

  -- Mirrors
  ia_url TEXT,                           -- Internet Archive (permanent)
  r2_url TEXT,                           -- Cloudflare R2 (fast working mirror)
  drive_url TEXT,                        -- Google Drive (optional, human-browsable)

  -- Integrity
  sha256 TEXT,                           -- computed on first fetch; invariant thereafter
  file_size_bytes INTEGER,
  page_count INTEGER,

  -- Extracted content
  ocr_text_path TEXT,                    -- relative path to extracted text bundle

  -- Metadata
  fetched_at TEXT,                       -- ISO datetime of first successful fetch
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_project ON documents(project_id);
CREATE INDEX idx_documents_type ON documents(document_type_id);
CREATE INDEX idx_documents_url_status ON documents(url_status);

-- ============================================================================
-- SECTION 5: Versions & housing program
-- ----------------------------------------------------------------------------
-- project_versions captures the project program at a point in its lifecycle
-- (proposal, entitled, building-permit-set, as-built).
--
-- Key rules:
--   - At most one is_current = 1 row per project (enforced by partial index).
--   - Non-proposal versions must have source_event_id set. This is a validation
--     rule (scripts/validate/check_version_events.py), not a SQL CHECK, because
--     referencing a vocabulary code inside a CHECK is awkward in SQLite.
--   - source_event_id is nullable at insert; set in second pass.
--
-- Provenance mixin is present on this and all child fact tables.
-- ============================================================================

CREATE TABLE project_versions (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  version_label TEXT,                    -- free-form, e.g. "2023 HCD APR entry"
  version_type_id INTEGER NOT NULL REFERENCES vocabulary_project_version_types(id),
  effective_date TEXT,                   -- when this version becomes "active"

  -- Program facts (the things that change between versions)
  total_units INTEGER CHECK (total_units IS NULL OR total_units >= 0),
  building_sqft INTEGER,
  height_stories REAL,
  height_feet REAL,
  parking_spaces INTEGER,

  -- Link to the administrative event that created this version
  source_event_id INTEGER,               -- FK added below (circular with project_events)

  -- Currency
  is_current INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0,1)),

  -- Provenance mixin
  source_document_id INTEGER REFERENCES documents(id),
  asserted_by TEXT,                      -- 'accela_import', 'jgage', 'sharon_gong_email_2025_04'
  asserted_at TEXT,                      -- ISO datetime
  confidence_type_id INTEGER REFERENCES vocabulary_confidence_types(id),

  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- At most one current version per project
CREATE UNIQUE INDEX idx_one_current_version_per_project
ON project_versions(project_id)
WHERE is_current = 1;

CREATE INDEX idx_project_versions_project ON project_versions(project_id);
CREATE INDEX idx_project_versions_type ON project_versions(version_type_id);

CREATE TABLE unit_program (
  id INTEGER PRIMARY KEY,
  project_version_id INTEGER NOT NULL REFERENCES project_versions(id) ON DELETE CASCADE,
  bedroom_count INTEGER NOT NULL CHECK (bedroom_count BETWEEN 0 AND 10),
  tenure_type_id INTEGER NOT NULL REFERENCES vocabulary_tenure_types(id),
  unit_count INTEGER NOT NULL CHECK (unit_count >= 0),
  avg_sqft INTEGER,
  special_population_type_id INTEGER REFERENCES vocabulary_special_population_types(id),
  notes TEXT,

  -- Provenance mixin
  source_document_id INTEGER REFERENCES documents(id),
  asserted_by TEXT,
  asserted_at TEXT,
  confidence_type_id INTEGER REFERENCES vocabulary_confidence_types(id)
);

CREATE INDEX idx_unit_program_version ON unit_program(project_version_id);

-- ----------------------------------------------------------------------------
-- AMI conventions for unit_program_affordability:
--   - ami_min / ami_max express AMI percent bands (e.g. 0-30 for ELI).
--   - When the band is known, both are non-NULL. 0 is a true 0% lower bound.
--   - NULL means the bound is unknown or not specified.
--   - income_category_id is the authoritative categorical value; ami_min/max
--     are the numeric detail that supports it.
-- ----------------------------------------------------------------------------

CREATE TABLE unit_program_affordability (
  id INTEGER PRIMARY KEY,
  unit_program_id INTEGER NOT NULL REFERENCES unit_program(id) ON DELETE CASCADE,
  income_category_id INTEGER NOT NULL REFERENCES vocabulary_income_categories(id),

  ami_min INTEGER CHECK (ami_min IS NULL OR (ami_min >= 0 AND ami_min <= 300)),
  ami_max INTEGER CHECK (ami_max IS NULL OR (ami_max >= 0 AND ami_max <= 300)),

  unit_count INTEGER NOT NULL CHECK (unit_count >= 0),
  restriction_type_id INTEGER REFERENCES vocabulary_restriction_types(id),
  restriction_term_years INTEGER CHECK (restriction_term_years IS NULL OR restriction_term_years >= 0),
  recorded_date TEXT,                    -- when the restriction was recorded against the deed

  -- Provenance mixin
  source_document_id INTEGER REFERENCES documents(id),
  asserted_by TEXT,
  asserted_at TEXT,
  confidence_type_id INTEGER REFERENCES vocabulary_confidence_types(id),

  CHECK (ami_min IS NULL OR ami_max IS NULL OR ami_min <= ami_max)
);

CREATE INDEX idx_affordability_program ON unit_program_affordability(unit_program_id);
CREATE INDEX idx_affordability_category ON unit_program_affordability(income_category_id);

-- ============================================================================
-- SECTION 6: Organizations and people
-- ----------------------------------------------------------------------------
-- organizations.name is NOT unique; real-world firm names drift
-- ("Panoramic" vs "Panoramic Interests" vs "Panoramic Interests LLC").
-- Deduplication happens via normalized_name in import scripts.
-- ============================================================================

CREATE TABLE organizations (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,                    -- display form
  normalized_name TEXT,                  -- lowercase + strip punctuation/corporate suffixes
  organization_type_id INTEGER REFERENCES vocabulary_organization_types(id),
  website TEXT,
  is_nonprofit INTEGER NOT NULL DEFAULT 0 CHECK (is_nonprofit IN (0,1)),
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_organizations_normalized_name ON organizations(normalized_name);

CREATE TABLE people (
  id INTEGER PRIMARY KEY,
  organization_id INTEGER REFERENCES organizations(id),
  full_name TEXT NOT NULL,
  title TEXT,
  email TEXT,
  phone TEXT,
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_people_org ON people(organization_id);

CREATE TABLE project_participants (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  project_version_id INTEGER REFERENCES project_versions(id) ON DELETE CASCADE,
  organization_id INTEGER REFERENCES organizations(id),
  person_id INTEGER REFERENCES people(id),
  role_type_id INTEGER NOT NULL REFERENCES vocabulary_role_types(id),

  start_date TEXT,
  end_date TEXT,
  notes TEXT,

  -- Provenance mixin
  source_document_id INTEGER REFERENCES documents(id),
  asserted_by TEXT,
  asserted_at TEXT,
  confidence_type_id INTEGER REFERENCES vocabulary_confidence_types(id),

  CHECK (organization_id IS NOT NULL OR person_id IS NOT NULL)
);

CREATE INDEX idx_participants_project ON project_participants(project_id);
CREATE INDEX idx_participants_org ON project_participants(organization_id);
CREATE INDEX idx_participants_person ON project_participants(person_id);
CREATE INDEX idx_participants_role ON project_participants(role_type_id);

-- ============================================================================
-- SECTION 7: Permits
-- ============================================================================

CREATE TABLE permits (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

  source_system TEXT NOT NULL,           -- 'accela', 'clariti', 'buildingeye', etc.
  source_permit_id TEXT,                 -- raw id from the source system (may differ from human-facing number)
  permit_number TEXT,                    -- human-facing number
  permit_type_id INTEGER REFERENCES vocabulary_permit_types(id),
  permit_status_type_id INTEGER REFERENCES vocabulary_permit_status_types(id),

  filed_date TEXT,
  issued_date TEXT,
  finaled_date TEXT,
  expires_date TEXT,

  valuation REAL CHECK (valuation IS NULL OR valuation >= 0),
  source_url TEXT,                       -- deep link into Accela / Clariti record

  description TEXT,
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_permits_project ON permits(project_id);
CREATE INDEX idx_permits_number ON permits(permit_number);
CREATE INDEX idx_permits_source ON permits(source_system, source_permit_id);
CREATE INDEX idx_permits_type ON permits(permit_type_id);

-- ============================================================================
-- SECTION 8: Project events (append-only timeline)
-- ----------------------------------------------------------------------------
-- The event log is the narrative spine of the database. Every dated claim
-- about a project lives here: permit issuances, hearings, observations,
-- inferences. Carries confidence + is_inferred so "we observed construction
-- start on 2024-09-12 from a site visit" is distinguishable from
-- "building permit BP-2024-0123 issued 2024-05-10".
-- ============================================================================

CREATE TABLE project_events (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  event_type_id INTEGER NOT NULL REFERENCES vocabulary_event_types(id),

  event_date TEXT,                       -- ISO date (use event_date_precision for fidelity)
  event_end_date TEXT,                   -- for duration events (e.g. public comment period)
  event_date_precision TEXT
    CHECK (event_date_precision IN ('exact','month','quarter','year','estimated') OR event_date_precision IS NULL),

  -- Optional links
  permit_id INTEGER REFERENCES permits(id),
  document_id INTEGER REFERENCES documents(id),

  -- What happened
  summary TEXT,
  details TEXT,
  units_affected INTEGER,
  previous_status_code TEXT,             -- free-form status string at the time (not FK; legacy-friendly)
  new_status_code TEXT,

  -- Provenance
  confidence_type_id INTEGER REFERENCES vocabulary_confidence_types(id),
  is_inferred INTEGER NOT NULL DEFAULT 0 CHECK (is_inferred IN (0,1)),
  source_type TEXT
    CHECK (source_type IN ('city_portal','document','news_article','observation','correspondence','inferred') OR source_type IS NULL),
  source_url TEXT,
  observed_by TEXT,                      -- 'jgage', 'automated_accela_scrape_v1'
  observed_at TEXT,                      -- ISO datetime of the observation

  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_project ON project_events(project_id);
CREATE INDEX idx_events_type ON project_events(event_type_id);
CREATE INDEX idx_events_date ON project_events(event_date);
CREATE INDEX idx_events_permit ON project_events(permit_id);
CREATE INDEX idx_events_document ON project_events(document_id);

-- ============================================================================
-- SECTION 9: Parcels
-- ----------------------------------------------------------------------------
-- Parcels are APN-keyed objects that exist in the county assessor's records.
-- They have their own lifecycle (subdivision, merger) independent of projects.
-- project_parcels is the many-to-many junction: a project site may span
-- multiple parcels, and a parcel may be involved in multiple projects over time.
-- ============================================================================

CREATE TABLE parcels (
  id INTEGER PRIMARY KEY,
  city_id INTEGER NOT NULL REFERENCES cities(id),
  apn TEXT NOT NULL,
  address TEXT,
  lot_sqft INTEGER CHECK (lot_sqft IS NULL OR lot_sqft >= 0),
  geometry_source TEXT,                  -- e.g. 'alameda_assessor_2025_q1'
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (city_id, apn)
);

CREATE INDEX idx_parcels_city ON parcels(city_id);

CREATE TABLE project_parcels (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  parcel_id INTEGER NOT NULL REFERENCES parcels(id),
  relationship_type_id INTEGER REFERENCES vocabulary_relationship_types(id),
  is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0,1)),
  notes TEXT,
  UNIQUE (project_id, parcel_id)
);

CREATE INDEX idx_project_parcels_project ON project_parcels(project_id);
CREATE INDEX idx_project_parcels_parcel ON project_parcels(parcel_id);

-- ============================================================================
-- SECTION 10: Geometry
-- ----------------------------------------------------------------------------
-- Geometries are GeoJSON-as-TEXT, not SpatiaLite. At 174 projects there's no
-- need for spatial indexes, and TEXT storage keeps the DB portable (works in
-- Datasette Lite, diffs cleanly in git).
--
-- Multiple geometries per project are expected: APN parcel (truth), hand-edited
-- building footprint (street-aligned), 3D extrusion with height, etc. Each
-- geometry carries is_current + superseded_by for version tracking.
-- ============================================================================

CREATE TABLE project_geometries (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  geometry_type_id INTEGER NOT NULL REFERENCES vocabulary_geometry_types(id),

  geojson TEXT NOT NULL,                 -- GeoJSON Feature or FeatureCollection
  height_meters REAL,                    -- for 3D extrusion
  base_elevation_meters REAL,            -- for terrain-relative placement

  source_document_id INTEGER REFERENCES documents(id),
  version_label TEXT,                    -- human-friendly version tag
  edited_by TEXT,
  edit_notes TEXT,

  -- Versioning
  is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0,1)),
  superseded_by INTEGER REFERENCES project_geometries(id),

  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- At most one current geometry per (project, type)
CREATE UNIQUE INDEX idx_one_current_geometry
ON project_geometries(project_id, geometry_type_id)
WHERE is_current = 1;

CREATE INDEX idx_geometries_project ON project_geometries(project_id);
CREATE INDEX idx_geometries_type ON project_geometries(geometry_type_id);

-- ============================================================================
-- SECTION 11: Project assets
-- ----------------------------------------------------------------------------
-- Extracted imagery: facade photos, renderings, floor plans, elevation
-- drawings. Often derived from architectural PDFs and pinned to a specific
-- PDF page. Optional link to project_geometries for 3D facade texturing.
-- ============================================================================

CREATE TABLE project_assets (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  asset_type_id INTEGER REFERENCES vocabulary_asset_types(id),

  title TEXT,
  description TEXT,
  file_url TEXT,                         -- local relative path or remote URL
  file_size_bytes INTEGER,
  width_px INTEGER,
  height_px INTEGER,

  -- Provenance
  source_document_id INTEGER REFERENCES documents(id),
  page_number INTEGER,                   -- which page of the source PDF

  -- Optional link to the geometry this asset depicts (e.g. a facade on a building footprint)
  geometry_id INTEGER REFERENCES project_geometries(id),

  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_assets_project ON project_assets(project_id);
CREATE INDEX idx_assets_type ON project_assets(asset_type_id);
CREATE INDEX idx_assets_document ON project_assets(source_document_id);
CREATE INDEX idx_assets_geometry ON project_assets(geometry_id);

-- ============================================================================
-- SECTION 12: Extension points
-- ----------------------------------------------------------------------------
-- These tables are deliberately minimal. They define the shape of future
-- extensions without committing to their details. Most cities will leave
-- them empty initially.
-- ============================================================================

-- Links to external infrastructure systems: water (EBMUD), power (PG&E),
-- telecom, transit, sewer. Populated when cities integrate utility capacity
-- or service data with their housing pipeline.
CREATE TABLE external_system_links (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  system_type TEXT,                      -- 'water', 'power', 'telecom', 'transit', 'sewer'
  system_identifier TEXT,                -- provider's ID for the service or capacity unit
  relationship TEXT,                     -- 'served_by', 'capacity_constrained_by', etc.
  data_source TEXT,                      -- provenance
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_external_links_project ON external_system_links(project_id);

-- AI-ready per-project bundles: manifest + narrative + concatenated OCR,
-- suitable for ingestion into NotebookLM, Claude, Perplexity, or similar.
-- Generated by scripts/bundles/build_project_bundle.py.
CREATE TABLE project_bundles (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  bundle_version INTEGER,
  generated_at TEXT,

  manifest_path TEXT,                    -- JSON listing all docs, geometries, roles
  narrative_path TEXT,                   -- markdown summary
  extracted_text_path TEXT,              -- concatenated OCR of project PDFs
  bundle_url TEXT,                       -- shareable URL (R2, IA, etc.)

  notes TEXT
);

CREATE INDEX idx_bundles_project ON project_bundles(project_id);

-- ============================================================================
-- SECTION 13: Project Classifications / Tags
-- ----------------------------------------------------------------------------
-- Normalized project tags/classifications for regulatory flags (SB35, SB330,
-- AB2011, is_uc_project) and other categorical attributes. Uses provenance
-- mixin for traceability.
--
-- Design decision: Flags like SB35/is_uc_project are NOT custom columns on
-- the projects table. Instead, they are normalized rows here, allowing:
--   - Easy addition of new classification types without schema changes
--   - Full provenance on each flag assertion
--   - Multi-city reuse with different classification vocabularies
-- ============================================================================

CREATE TABLE project_classifications (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  classification_type_id INTEGER NOT NULL REFERENCES vocabulary_classification_types(id),

  -- Value: for boolean flags use '1' (true), '0' or NULL (false/unknown)
  -- For categorical types, use the categorical value string
  value TEXT,

  -- Effective date range (optional)
  effective_date TEXT,
  end_date TEXT,

  -- Provenance mixin
  source_document_id INTEGER REFERENCES documents(id),
  asserted_by TEXT,
  asserted_at TEXT,
  confidence_type_id INTEGER REFERENCES vocabulary_confidence_types(id),

  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,

  UNIQUE (project_id, classification_type_id)
);

CREATE INDEX idx_classifications_project ON project_classifications(project_id);
CREATE INDEX idx_classifications_type ON project_classifications(classification_type_id);

-- ============================================================================
-- SECTION 14: Deferred circular FKs
-- ----------------------------------------------------------------------------
-- These two references form practical (not relational) cycles. We declare them
-- here, after both tables exist, via the ALTER TABLE-less SQLite pattern of
-- leaving them as untyped INTEGER columns above and adding CHECK-by-query
-- in validation. SQLite does not support ALTER TABLE ADD CONSTRAINT FOREIGN KEY,
-- so enforcement for these two is handled in scripts/validate/.
--
-- Specifically, the following rules are enforced by validation queries:
--   1. projects.current_version_id, when non-NULL, must reference
--      a project_versions.id whose project_id equals projects.id.
--   2. project_versions.source_event_id, when non-NULL, must reference
--      a project_events.id whose project_id equals the version's project_id.
--   3. For version_type_id NOT IN (<proposal>), source_event_id MUST be non-NULL.
-- See scripts/validate/check_referential_cycles.py and check_version_events.py.
-- ============================================================================

-- End of core.sql
