-- structures.sql
-- Multi-building support for berkeley_housing_v2
-- Phase A: Schema-only (no data migration)
-- Created: 2026-05-04

--------------------------------------------------------------------------------
-- VOCABULARY: Structure Types
--------------------------------------------------------------------------------

CREATE TABLE vocabulary_structure_types (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT
);

INSERT INTO vocabulary_structure_types (code, label, description) VALUES
  ('main', 'Main Building', 'Primary or sole structure on the project site'),
  ('tower', 'Tower', 'High-rise tower, often part of a podium-tower configuration'),
  ('podium', 'Podium', 'Low-rise base structure, typically with parking or retail'),
  ('building', 'Building', 'Generic building designation (e.g., Building A, Building B)'),
  ('house', 'House', 'Single-family or small multi-family residential structure'),
  ('addition', 'Addition', 'Addition to an existing structure'),
  ('accessory_dwelling', 'ADU', 'Accessory dwelling unit');

--------------------------------------------------------------------------------
-- STRUCTURES TABLE
-- Physical characteristics only; units live in unit_program
--------------------------------------------------------------------------------

CREATE TABLE structures (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  structure_type_id INTEGER REFERENCES vocabulary_structure_types(id),
  stories INTEGER CHECK (stories IS NULL OR stories >= 0),
  height_feet REAL CHECK (height_feet IS NULL OR height_feet >= 0),
  height_meters REAL CHECK (height_meters IS NULL OR height_meters >= 0),
  building_sqft INTEGER CHECK (building_sqft IS NULL OR building_sqft >= 0),
  status TEXT,
  completed_at TEXT,
  notes TEXT,
  -- Provenance mixin
  source_document_id INTEGER REFERENCES documents(id),
  asserted_by TEXT,
  asserted_at TEXT,
  confidence_type_id INTEGER REFERENCES vocabulary_confidence_types(id),
  -- Timestamps
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (project_id, label)
);

CREATE INDEX idx_structures_project_id ON structures(project_id);

--------------------------------------------------------------------------------
-- SCHEMA EXTENSIONS
--------------------------------------------------------------------------------

-- Link geometries to specific structures (optional; NULL = project-level)
ALTER TABLE project_geometries
  ADD COLUMN structure_id INTEGER REFERENCES structures(id);

-- Track beds per unit type (for UC dorms: beds != units)
ALTER TABLE unit_program
  ADD COLUMN beds_per_unit INTEGER CHECK (beds_per_unit IS NULL OR beds_per_unit >= 0);
