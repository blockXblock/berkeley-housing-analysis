-- parcel_apn_lineage_schema_MVP.sql
--
-- MVP SUBSET of the TARGET parcel-identity model (see _TARGET.sql).
-- Principle: build ONLY what Alameda-only data can POPULATE today; structure it
-- so it GROWS into the target additively (no redesign). Each MVP piece is a strict
-- subset of a target table, so promotion later = add columns/tables, not migrate.
--
-- WHAT THE MVP FIXES NOW (today's real problems):
--   * the APN storage mess (raw vs normalized; hyphens/spaces/none)  -> apn_raw + apn_normalized
--   * crosswalk-as-fact vs crosswalk-as-guess                        -> parcel_lineage (candidate)
--   * APR Prior/Current APN deliverable                              -> apn_raw history + lineage
--   * SB 9 unit inflation                                            -> classifier rule (housing_rules)
--
-- WHAT THE MVP DEFERS (grow into the target when data/need arrives):
--   * parallel parcels table          -> we EXTEND existing v2 parcels, don't fork
--   * parcel_identifiers full history  -> MVP keeps current-era only on parcels
--   * parcel_geometry_versions         -> v2 geometry stays as-is for now
--   * dual assessor/local snapshot history (roll-year) -> single current snapshot stays
--   * full event/link richness         -> one flat parcel_lineage table (subset)
--   * multi-county DATA                -> columns carry county='Alameda' now; adapters later
--
-- IMPORTANT: this assumes the EXISTING v2 `parcels` table (parcel_id = parcels.id,
-- the one FK is project_parcels.parcel_id). We ADD columns to it, not replace it.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- 1. EXTEND existing v2 parcels: raw + normalized + authority scope
--    (apn_raw = the preserved original stored value, NEVER mutated;
--     apn_normalized = to_canonical_apn(apn_raw, assessing_county), VARIABLE length)
--    NOTE: SQLite ALTER ADD COLUMN can't add CHECK/UNIQUE to existing tables;
--    enforcement is via the trigger below + a partial unique index.
-- ---------------------------------------------------------------------------

ALTER TABLE parcels ADD COLUMN apn_raw TEXT;                 -- source-faithful, preserved
ALTER TABLE parcels ADD COLUMN apn_normalized TEXT;          -- matching key (digits, variable length)
ALTER TABLE parcels ADD COLUMN assessing_county TEXT NOT NULL DEFAULT 'Alameda';

-- AUTHORITY-SCOPED uniqueness on the normalized key (the statewide-correct key).
-- Same normalized string in two counties = two parcels, so scope by county.
CREATE UNIQUE INDEX IF NOT EXISTS idx_parcels_authority_apn
    ON parcels(assessing_county, apn_normalized)
    WHERE apn_normalized IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_parcels_apn_norm_lookup
    ON parcels(assessing_county, apn_normalized);

-- ENFORCEMENT (the teeth): reject anything not matching the ASSESSING COUNTY's
-- REGISTERED apn_normalized pattern.
-- *** THIS IS ALAMEDA'S REGISTERED PATTERN, NOT A UNIVERSAL CANONICAL-APN RULE ***
-- Alameda's MEASURED canonical = Option B (STRUCTURE-PRESERVING): book3-page4-parcel3-sub2
-- joined by "-", UPPERCASE ALPHANUMERIC (e.g. 057-2046-001-00, 48A-7075-015-00). Registered as
-- ^[0-9A-Z]{3}-[0-9A-Z]{4}-[0-9A-Z]{3,}-[0-9A-Z]{2,}$ in housing_rules.APN_FORMATS['Alameda'] +
-- the TARGET jurisdictions.apn_format. ALPHANUMERIC not digits-only (25/30,007 carry a book
-- letter 48A/48H); STRUCTURE-PRESERVING not fixed-concat (keeps segment boundaries -> robust to
-- variable-width / different-structure counties; Option A's concat overflowed + lost boundaries).
-- SQLite GLOB can't express {3,}, so we validate the FIXED book3-page4- prefix + char-class
-- (alnum + the one canonical hyphen) + length 15-17 (canonical 15 = 3-1-4-1-3-1-2; +2 future-sub
-- margin), which admits variable parcel/sub and rejects A-concat/raw/lowercase. When county #2
-- arrives, ITS predicate is DERIVED FROM ITS registered format, never copied from Alameda.
-- apn_raw is intentionally unconstrained (source-faithful).
CREATE TRIGGER IF NOT EXISTS trg_parcels_apn_normalized_canonical_ins
BEFORE INSERT ON parcels
FOR EACH ROW
WHEN NEW.apn_normalized IS NOT NULL
     AND NEW.assessing_county = 'Alameda'              -- Alameda's registered B pattern below
     AND NOT (
         NEW.apn_normalized GLOB '[0-9A-Z][0-9A-Z][0-9A-Z]-[0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z]-*-*'  -- book3-page4-...-...
         AND NEW.apn_normalized NOT GLOB '*[^0-9A-Z-]*'         -- only uppercase alnum + the canonical hyphen
         AND length(NEW.apn_normalized) BETWEEN 15 AND 17)      -- 3-4-3-2 = 15 (+2 future-sub margin)
BEGIN
    SELECT RAISE(ABORT, 'apn_normalized must match Alameda registered pattern book3-page4-parcel3-sub2 hyphenated (e.g. 057-2046-001-00)');
END;

CREATE TRIGGER IF NOT EXISTS trg_parcels_apn_normalized_canonical_upd
BEFORE UPDATE OF apn_normalized ON parcels
FOR EACH ROW
WHEN NEW.apn_normalized IS NOT NULL
     AND NEW.assessing_county = 'Alameda'
     AND NOT (
         NEW.apn_normalized GLOB '[0-9A-Z][0-9A-Z][0-9A-Z]-[0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z]-*-*'
         AND NEW.apn_normalized NOT GLOB '*[^0-9A-Z-]*'
         AND length(NEW.apn_normalized) BETWEEN 15 AND 17)
BEGIN
    SELECT RAISE(ABORT, 'apn_normalized must match Alameda registered pattern book3-page4-parcel3-sub2 hyphenated (e.g. 057-2046-001-00)');
END;

-- ---------------------------------------------------------------------------
-- 2. parcel_lineage — the MVP subset of TARGET parcel_events + parcel_event_links.
--    One flat table (parent->child per row) instead of the event+links pair.
--    Bootstrap: the 25 Phase-2 crosswalk re-points (renumber, candidate) + the
--    held splits (proj179 N/S, Acheson umbrella) as candidate sb9_split/condo_map.
--    NOTHING is authoritative until status='confirmed' against a recorded map.
--    Promotion to target: this table's rows fan out into parcel_events(+links).
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS parcel_lineage (
    parcel_lineage_id   INTEGER PRIMARY KEY,
    assessing_county    TEXT NOT NULL DEFAULT 'Alameda',
    parent_parcel_id    INTEGER,                -- v2 parcels.id (NULL if parent unknown/external)
    child_parcel_id     INTEGER,                -- v2 parcels.id
    parent_apn_raw      TEXT,                   -- the prior APN (for APR Prior-APN field)
    child_apn_raw       TEXT,                   -- the current APN (for APR Current-APN field)
    parent_apn_normalized TEXT,
    child_apn_normalized  TEXT,
    event_type          TEXT NOT NULL DEFAULT 'apn_renumber'
        CHECK (event_type IN (
            'sb9_split','parcel_split','parcel_merger','lot_line_adjustment',
            'condo_map','subdivision_map','assessor_correction','apn_renumber','other')),
    -- candidate (our inference) vs confirmed (recorded map) vs rejected
    status              TEXT NOT NULL DEFAULT 'candidate'
        CHECK (status IN ('candidate','confirmed','rejected')),
    confidence          TEXT NOT NULL DEFAULT 'inferred'
        CHECK (confidence IN ('observed','inferred','manual_review','unknown')),
    evidence            TEXT,                   -- JSON: the converging signals (exact_address+book_page+imps_scale...)
    event_date          DATE,
    recording_number    TEXT,                   -- the future confirm source (recorder)
    map_reference       TEXT,
    source_name         TEXT,
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_parcel_id) REFERENCES parcels(id),
    FOREIGN KEY (child_parcel_id)  REFERENCES parcels(id)
);

CREATE INDEX IF NOT EXISTS idx_pl_parent ON parcel_lineage(parent_parcel_id);
CREATE INDEX IF NOT EXISTS idx_pl_child  ON parcel_lineage(child_parcel_id);
CREATE INDEX IF NOT EXISTS idx_pl_status ON parcel_lineage(status);
CREATE INDEX IF NOT EXISTS idx_pl_type   ON parcel_lineage(event_type);
CREATE INDEX IF NOT EXISTS idx_pl_parent_norm ON parcel_lineage(assessing_county, parent_apn_normalized);
CREATE INDEX IF NOT EXISTS idx_pl_child_norm  ON parcel_lineage(assessing_county, child_apn_normalized);

-- ---------------------------------------------------------------------------
-- 3. Helper view: APR Prior-APN / Current-APN per parcel (the deliverable).
--    Confirmed lineage gives an authoritative prior; candidate is labeled as such.
-- ---------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS parcel_apn_prior_current AS
SELECT
    p.id                        AS parcel_id,
    p.assessing_county,
    p.apn_raw                   AS current_apn,
    p.apn_normalized            AS current_apn_normalized,
    pl.parent_apn_raw           AS prior_apn,
    pl.parent_apn_normalized    AS prior_apn_normalized,
    pl.event_type               AS lineage_event,
    pl.status                   AS lineage_status,      -- 'candidate' vs 'confirmed' (honesty)
    pl.confidence               AS lineage_confidence
FROM parcels p
LEFT JOIN parcel_lineage pl
    ON pl.child_parcel_id = p.id
   AND pl.status IN ('candidate','confirmed');

-- ===========================================================================
-- GROWTH PATH (how the MVP becomes the TARGET — additive, no redesign):
--   parcels.apn_raw/apn_normalized   -> already target-shaped (rename county col only)
--   parcel_lineage                   -> fan out to parcel_events + parcel_event_links
--   (single current snapshot)        -> add assessor_parcel_snapshots roll-year history
--   (v2 geometry)                    -> add parcel_geometry_versions time-history
--   (county='Alameda' columns)       -> add jurisdictions registry + more county rows
--   local overlays                   -> add local_jurisdiction_parcel_snapshots + overlays KV
-- Each is an ADD, not a migrate — the MVP columns/keys are already target-compatible.
-- ===========================================================================
