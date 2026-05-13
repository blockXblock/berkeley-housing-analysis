-- addresses.sql
-- Project address history for berkeley_housing_v2
-- Phase B follow-up: append-only history table for addresses that change over time
-- Use case: city renumbering (e.g., 1701 → 1717 San Pablo Ave), parcel subdivision,
-- original-application addresses superseded by built addresses
-- Created: 2026-05-08

--------------------------------------------------------------------------------
-- PROJECT ADDRESSES TABLE
-- One row per address ever associated with a project, with full history
--------------------------------------------------------------------------------

CREATE TABLE project_addresses (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  address TEXT NOT NULL,                          -- as displayed
  normalized_address TEXT,                        -- standardized form for matching
  is_current INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0,1)),
  start_date TEXT,                                -- when this address became active
  end_date TEXT,                                  -- when this address was superseded
  change_reason TEXT,                             -- 'city_renumbering', 'original_application',
                                                  -- 'parcel_subdivision', 'migrated_from_v1', etc.
  -- Provenance mixin
  source_document_id INTEGER REFERENCES documents(id),
  asserted_by TEXT,
  asserted_at TEXT,
  confidence_type_id INTEGER REFERENCES vocabulary_confidence_types(id),
  notes TEXT,
  -- Timestamps
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- One current address per project (allows zero for projects without a canonical address)
CREATE UNIQUE INDEX idx_one_current_address_per_project
  ON project_addresses(project_id)
  WHERE is_current = 1;

CREATE INDEX idx_project_addresses_project_id
  ON project_addresses(project_id);

CREATE INDEX idx_project_addresses_normalized
  ON project_addresses(normalized_address);

CREATE INDEX idx_project_addresses_address
  ON project_addresses(address);
