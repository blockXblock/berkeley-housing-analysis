# Inspection Ingest Design Sketch (2026-05-23)

**Status:** Design complete. Ready for CC build.
**Scope:** Layer A (ingest the 92 inspection JSONs into v2). Layers B (derived views) and C (stage-inference) follow in subsequent workstreams.
**Inputs:** 92 JSON files at `data/raw/accela_inspections/` containing 6,303 inspection records scraped 2026-05-22.
**Output target:** `databases/berkeley_housing_v2.db`.

## Context

On 2026-05-22 we completed scraping inspection histories for 92 Berkeley B-permits via the headless `inspection_scraper.py` framework. The output JSONs were validated today (2026-05-23) by:

1. **Deep reconnaissance** across 71 stratified-sample projects covering 5 unit-count buckets × 4 regulatory categories (with all 22 named-priority projects included). Report: `/tmp/legacy_data_per_project_inventory_2026-05-23.md`.
2. **12 Chrome live-DOM verifications** (2 runs of 6 permits each) confirming JSON↔Accela totals match exactly (12/12). The Chrome runs also surfaced the per-permit result-code distribution headers, confirmed result-code vocabulary, and disproved a stage-correlation hypothesis.

The recon and Chrome work established that:
- Inspection JSONs are the only substantive per-inspection data source. Legacy DB's 208 'Inspection'-stage events are summary-level, not per-event.
- v2.project_events (2,347 rows) has known mixed-provenance issues (105 Jan 1 placeholders, 43 unverified synthesized entitlements, etc.), motivating clean separation of new inspection data into its own table.
- Inspector-string field has 53 distinct values including artifacts ('J', 'E', 'DL', 'A  A'). outreach.db.contacts already has 67+ named city staff for resolution.
- Result-code vocabulary: 6 confirmed values (Approved, Partially Approved, Cancelled, Disapproved, Rescheduled, Site Cancellation); 7th rare value (Approved with Conditions) at 0.1% per recon.
- Per-permit result distribution is a stable project-level signal, varies by contractor/inspector NOT by stage.

## Design decisions (12 banked)

### 1. Schema target

**Decision:** New `inspections` table linked to `permits.id` (Option B from chat discussion).

**Rationale:** v2.project_events has known mixed provenance (placeholder dates, synthesized entitlements). Adding 6,303 clean inspection records into that table would mix high-confidence with low-confidence data. A dedicated table keeps provenance clean and makes inspection-specific queries (stage analysis, distribution per permit, inspector workload) into simple lookups.

**Tradeoff accepted:** Stage analysis queries that need both inspection events and lifecycle events must UNION across `inspections` and `project_events`. Mitigated by Decision 7's derived-views approach.

### 2. Inspector resolution target

**Decision:** Resolve inspector strings against existing infrastructure — `outreach.db.contacts` (29+ city staff entries) plus the already-cleaned `berkeley_housing_analysis.db.permit_events.marked_by` field.

**Rationale:** Both sources already exist and contain validated city staff identities. Past sessions cleaned the worst marked_by artifacts (JO, PFS, MJ-with-suffix). Building a new staff vocabulary from scratch would duplicate this work.

**Implication:** Decision 4 specifies how the cross-DB reference is implemented.

### 3. Inspection table schema

```sql
CREATE TABLE inspections (
  -- Identity
  id                       INTEGER PRIMARY KEY AUTOINCREMENT,
  permit_id                INTEGER NOT NULL REFERENCES permits(id),

  -- Source identity (from Accela)
  accela_inspection_id     TEXT NOT NULL,    -- e.g., '943440'

  -- What kind of inspection
  type_code                TEXT NOT NULL,    -- e.g., 'Building 1030 Anchor Bolt and Hold Down'

  -- Outcome
  result_code_id           INTEGER REFERENCES vocabulary_inspection_result_types(id),
  result_raw               TEXT,              -- verbatim scraped result (preserved if vocab unresolved)

  -- When
  inspected_at             TEXT NOT NULL,    -- ISO datetime: '2025-02-11T16:00:00'
  inspected_date           TEXT GENERATED ALWAYS AS (substr(inspected_at, 1, 10)) STORED,

  -- Who
  inspector_string         TEXT,              -- raw value as scraped
  inspector_contact_id     INTEGER REFERENCES contacts(id),

  -- Provenance mixin (per v2 convention)
  source_system            TEXT NOT NULL DEFAULT 'accela_inspection_scrape_2026-05-22',
  source_url               TEXT,
  asserted_by              TEXT,
  asserted_at              TEXT NOT NULL DEFAULT (datetime('now')),
  confidence_type_id       INTEGER REFERENCES vocabulary_confidence_types(id),

  -- Forensic blob
  raw_json                 TEXT,              -- original JSON record for re-derivation

  UNIQUE(accela_inspection_id, permit_id)
);

CREATE INDEX idx_inspections_permit ON inspections(permit_id);
CREATE INDEX idx_inspections_date ON inspections(inspected_date);
CREATE INDEX idx_inspections_result ON inspections(result_code_id);
CREATE INDEX idx_inspections_inspector ON inspections(inspector_contact_id);
```

**Notes:**
- `inspected_at` combines JSON's `date` (MM/DD/YYYY) and `time` (HH:MM AM/PM) into ISO datetime
- `inspected_date` is a generated column for fast date-only queries
- UNIQUE constraint enables idempotent re-ingest
- raw_json typical size ~200 bytes; total ~1.3MB for 6,303 records

### 4. Cross-database reference resolution: Path B

**Decision:** Replicate `outreach.db.contacts` into v2 as a `contacts` table. v2 owns its references going forward; outreach.db remains source-of-truth for new contact additions with periodic sync.

```sql
-- v2 contacts table (mirror of outreach.db.contacts)
CREATE TABLE contacts (
  id                  INTEGER PRIMARY KEY,
  name                TEXT NOT NULL,
  organization        TEXT,
  role                TEXT,
  email               TEXT,
  phone               TEXT,
  category            TEXT,
  notes               TEXT,
  source              TEXT,
  source_db           TEXT DEFAULT 'outreach.db',  -- where this contact came from
  outreach_db_id      INTEGER,                      -- original outreach.db id
  last_synced_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_contacts_name ON contacts(name);
CREATE INDEX idx_contacts_outreach_id ON contacts(outreach_db_id);
```

**Initial population:** copy all rows from outreach.db.contacts at ingest time. Subsequent sync is a separate workstream.

### 5. raw_json column

**Decision:** Included.

**Cost:** ~1.3MB total for 6,303 records.
**Benefit:** Allows forensic re-derivation if schema interpretation is wrong; supports auditing; enables future field additions without re-scraping.

### 6. Result-code vocabulary

```sql
CREATE TABLE vocabulary_inspection_result_types (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  code                 TEXT NOT NULL UNIQUE,
  display_label        TEXT NOT NULL,
  outcome_category     TEXT NOT NULL,   -- 'pass' | 'fail' | 'no_event'
  description          TEXT,
  is_terminal          BOOLEAN DEFAULT 1,
  created_at           TEXT DEFAULT (datetime('now'))
);

INSERT INTO vocabulary_inspection_result_types
  (code, display_label, outcome_category, description, is_terminal)
VALUES
  ('approved',                 'Approved',                  'pass',     'Inspection passes fully',                                     1),
  ('partially_approved',       'Partially Approved',        'pass',     'Inspection passes with corrections noted but work continues', 1),
  ('approved_with_conditions', 'Approved with Conditions',  'pass',     'Conditional pass requiring follow-up',                        1),
  ('disapproved',              'Disapproved',               'fail',     'Inspection fails; corrections required before re-inspection', 1),
  ('cancelled',                'Cancelled',                 'no_event', 'Inspection cancelled before site visit',                      1),
  ('site_cancellation',        'Site Cancellation',         'no_event', 'Inspector arrived but inspection could not proceed',          1),
  ('rescheduled',              'Rescheduled',               'no_event', 'Inspection moved to later date',                              0);
```

**Design choices:**
- `outcome_category` groups 7 codes into 3 meaningful buckets for stage analysis: `pass` (3 codes), `fail` (1 code), `no_event` (3 codes)
- `is_terminal` distinguishes terminal results (this inspection event is done) from non-terminal (Rescheduled → will re-occur)
- `display_label` is exact-match to Accela UI text (verified via Chrome on 12 permits)

### 7. Dedup strategy: don't dedup at ingest

**Decision:** Inspections and project_events coexist independently. Build derived views (Layer B) that compose them intelligently at query time.

**Rationale:** v2.project_events has known reliability issues (placeholder dates, synthesized entitlements). Algorithmic dedup risks false positives or preserving wrong data. Segregation preserves provenance.

**Implementation hint for Layer B:** views can UNION inspections and project_events with explicit source-priority rules. "Stage transition signals" prefer project_events (lifecycle abstraction). "Inspection events" use inspections directly. "Latest project activity" UNIONs both, preferring more-specific source.

### 8. Stage-inference layer (Layer C)

**Decision:** Build a stage-inference layer that uses inspection signals to validate or correct v2.current_stage_type_id.

**Scope:** Separate from ingest. Probably tomorrow's workstream. Design questions remain open:
- Which `type_code` values signal stage transitions? (e.g., "Building Final" → completed)
- What's the confidence model when inspection signals disagree with current_stage_type_id?
- How do we present disagreements (report flagging, auto-correct, manual review)?

**Why deferred:** Stage-inference has its own design conversation. Inspection ingest produces the data Layer C will reason over.

### 9. Ingest behavior

**9a — Scope:** Test on 12 Chrome-verified permits first, then run all 92.

The 12 Chrome-verified permits:
- B2024-01924, B2019-05574, B2021-02404, B2023-06416, B2024-02966, B2024-03884 (run 1)
- B2024-00143, B2024-05944, B2023-00192, B2022-01332, B2024-02570, B2025-00685 (run 2)

Expected counts (must match Chrome verifications):
- B2024-01924: 404
- B2019-05574: 557
- B2021-02404: 527
- B2023-06416: 288
- B2024-02966: 285
- B2024-03884: 51
- B2024-00143: 348
- B2024-05944: 89
- B2023-00192: 50
- B2022-01332: 26
- B2024-02570: 41
- B2025-00685: 50

Test phase totals: 2,716 inspections across 12 permits.
Full phase target: 6,303 inspections across 92 permits.

**9b — Missing permit_number reference:** Skip with log. Record the permit_number in a `missing_permits.txt` artifact; continue ingest. Recon verified all 92 should match, so any miss is information about a v2 permit gap.

**9c — Unknown result-code:** Insert with result_code_id=NULL, result_raw populated. Don't auto-create vocabulary entries.

**9d — Inspector resolution:** Exact name match only (case-insensitive equality on contacts.name). All others set inspector_contact_id=NULL while preserving inspector_string. Initials and single-letter strings remain unresolved.

### 10. Validation report

After each ingest run (test phase + full phase), produce:

**`notes/2026-05-23_inspection_ingest_report.md`** with 7 sections:

1. Headline counts (total inspections ingested, per-permit table for the 12 test permits with Chrome-verified totals for direct comparison)
2. Result-code distribution (count per code, percentage, matched against Chrome breakdown headers for the 12 verified permits)
3. Inspector resolution stats (auto-resolved count vs unresolved, list of distinct unresolved strings)
4. Unknown result-codes encountered (any result strings outside the 7 known)
5. Missing permit references (permit_numbers that didn't resolve to v2.permits)
6. Time range (earliest and latest inspected_date observed)
7. Sample rows (5 ingested rows with all columns populated)

**`notes/2026-05-23_inspection_ingest_report.json`** with the same data in queryable form.

### 11. Rollback strategy

**Both methods enabled:**

**Method 1 — Pre-ingest snapshot.** Before any DDL or data changes:
```bash
cp databases/berkeley_housing_v2.db databases/keep_snapshot_pre_inspection_ingest_2026-05-23.db
```
Rollback = restore from snapshot.

**Method 2 — Source-system delete.** Every ingested row has `source_system='accela_inspection_scrape_2026-05-22'`. Fast iteration during testing:
```sql
DELETE FROM inspections WHERE source_system='accela_inspection_scrape_2026-05-22';
```

### 12. Commit timing (incremental, 5-commit pattern)

Following yesterday's URL discovery discipline:

- **Commit 1:** Schema additions only — contacts, inspections, vocabulary_inspection_result_types tables created; vocabulary seeded; contacts replicated from outreach.db. No inspection data yet. Push.
- **Commit 2:** Ingest script (data/scripts or scripts/inspection_ingest.py) plus its tests. No data ingested. Push.
- **Commit 3:** 12-permit test phase results — ingest_report.md and .json for the test phase, with Chrome-verification cross-reference. Push.
- **Commit 4:** Full 92-permit ingest results — final ingest_report.md and .json. Push.
- **Commit 5:** Methodology page update, design sketch finalization, any post-ingest cleanups. Push.

## Build sequence

Layer A delivery requires the following CC prompts, run in order. Each is a single bash/python action with clear inputs and outputs.

### CC Prompt 1: Pre-ingest snapshot + schema

```
Task: Phase 1 of inspection ingest — pre-ingest snapshot, then create
3 new tables in v2 + populate vocabulary + replicate contacts.
Type 2 (database writes). Wait for explicit OK before committing.

INPUTS (READ-ONLY):
  - databases/outreach.db (read contacts table)
  - notes/2026-05-23_inspection_ingest_design_sketch.md (this sketch)

OUTPUTS:
  - databases/keep_snapshot_pre_inspection_ingest_2026-05-23.db
  - databases/berkeley_housing_v2.db (modified)
  - /tmp/schema_phase_1_report.md

STEPS:

1. Snapshot: copy berkeley_housing_v2.db to
   keep_snapshot_pre_inspection_ingest_2026-05-23.db.
   Verify sizes match.

2. Create the 3 new tables in v2:
   - contacts (per sketch §4)
   - vocabulary_inspection_result_types (per sketch §6)
   - inspections (per sketch §3)
   plus 4 indexes on inspections.

   Use IF NOT EXISTS guards so re-runs are safe.

3. Seed vocabulary_inspection_result_types with the 7 INSERTs from
   sketch §6.

4. Replicate contacts from outreach.db:
   - ATTACH outreach.db AS source
   - INSERT INTO contacts SELECT ... with appropriate column mapping
   - Set source_db='outreach.db', outreach_db_id=source.id,
     last_synced_at=current timestamp

5. Verify by querying:
   - SELECT COUNT(*) FROM contacts
   - SELECT COUNT(*) FROM vocabulary_inspection_result_types
   - .schema inspections

6. Write /tmp/schema_phase_1_report.md with:
   - Snapshot path and size
   - Tables created (list with row counts)
   - Vocabulary seeded (7 rows; show codes and labels)
   - Contacts replicated (N rows; sample 3)
   - Verify schema matches sketch (note any divergence)

Constraints:
  - Use IF NOT EXISTS; don't drop existing tables.
  - Do NOT touch existing project_events, permits, projects tables.
  - Do NOT commit to git until I confirm OK.
  - Report all SQL executed.

When done, report the schema_phase_1_report.md path and contents.
```

### CC Prompt 2: Ingest script (no data writes yet)

```
Task: Phase 2 of inspection ingest — write the ingest script that
will read the 92 JSONs and write to v2.inspections. Type 1 — write
code only; do NOT run it against the database yet.

INPUTS (READ-ONLY):
  - data/raw/accela_inspections/*.json (92 files)
  - databases/berkeley_housing_v2.db (read schema only)
  - databases/cic_recon_queue.db (read for source_url lookup)
  - notes/2026-05-23_inspection_ingest_design_sketch.md

OUTPUTS:
  - scripts/inspection_ingest.py
  - /tmp/ingest_script_smoke_test.md

The script must:

1. Accept command-line arguments:
   --db PATH (default: databases/berkeley_housing_v2.db)
   --json-dir PATH (default: data/raw/accela_inspections)
   --test-permits CSV (comma-separated permit numbers; if provided,
     only ingest those)
   --report-path PATH (where to write the MD report)
   --json-report-path PATH (where to write the JSON report)
   --dry-run (read but don't write)

2. For each JSON file in --json-dir:
   a. Load and parse
   b. Extract permit_number (filename without .json)
   c. Look up v2.permits.id by permit_number; if not found,
      add to missing_permits list and skip the file
   d. Look up source_url from cic_recon_queue.url_discovery_queue
      where permit_number matches
   e. For each inspection record:
      - Compute inspected_at by combining date + time:
        MM/DD/YYYY + HH:MM AM/PM → ISO datetime
      - Resolve result via vocabulary_inspection_result_types:
        WHERE display_label = result_raw
        If no match: result_code_id=NULL, result_raw=value
      - Resolve inspector via contacts:
        WHERE LOWER(name) = LOWER(inspector_string)
        If no match: inspector_contact_id=NULL, inspector_string preserved
      - Build raw_json from the original record (json.dumps)
      - INSERT OR IGNORE INTO inspections (...) VALUES (...)
        (UNIQUE constraint handles dedup)

3. After all files processed, build report with 7 sections per sketch §10:
   - Headline counts (with expected Chrome-verified counts for test 12)
   - Result-code distribution
   - Inspector resolution stats
   - Unknown result-codes
   - Missing permit references
   - Time range
   - Sample rows (5)

4. Write report to MD + JSON.

5. Smoke-test (no DB writes):
   - python scripts/inspection_ingest.py --dry-run \
       --test-permits B2024-01924
   - Should report parsing of 404 inspections, no DB changes,
     report shows expected counts

6. Write /tmp/ingest_script_smoke_test.md with:
   - Script path and line count
   - Smoke-test output
   - Any anomalies during dry-run

Constraints:
  - Idempotent (INSERT OR IGNORE)
  - Python heredoc style; no bash heredocs
  - Do NOT run against the actual database without --test-permits + my OK
  - Do NOT commit yet

When done, report the script path and smoke-test output.
```

### CC Prompt 3: 12-permit test run

```
Task: Phase 3 — run ingest on 12 Chrome-verified permits as test.
Type 2 (writes to v2). Wait for OK before commit.

INPUTS:
  - scripts/inspection_ingest.py (from Phase 2)
  - The 12 test permits (sketch §9a)

STEPS:

1. Run the ingest with --test-permits flag:
   python scripts/inspection_ingest.py \
     --db databases/berkeley_housing_v2.db \
     --test-permits B2024-01924,B2019-05574,B2021-02404,B2023-06416,B2024-02966,B2024-03884,B2024-00143,B2024-05944,B2023-00192,B2022-01332,B2024-02570,B2025-00685 \
     --report-path notes/2026-05-23_inspection_ingest_report_test12.md \
     --json-report-path notes/2026-05-23_inspection_ingest_report_test12.json

2. After ingest, verify by running these SQL checks:

   a. Total rows ingested should be 2,716:
      SELECT COUNT(*) FROM inspections
      WHERE source_system='accela_inspection_scrape_2026-05-22'

   b. Per-permit counts must match Chrome-verified counts:
      SELECT
        p.permit_number,
        COUNT(*) as ingested_count
      FROM inspections i
      JOIN permits p ON i.permit_id = p.id
      WHERE p.permit_number IN (the 12)
      GROUP BY p.permit_number;

      Expected: B2024-01924=404, B2019-05574=557, ...

   c. Result-code distribution per permit matches Chrome breakdown.
      For each of the 12, compute the per-result counts and compare
      against the Chrome-verified breakdown header. Report any
      discrepancy.

   d. Inspector resolution stats:
      SELECT
        SUM(CASE WHEN inspector_contact_id IS NULL THEN 1 ELSE 0 END) as unresolved,
        SUM(CASE WHEN inspector_contact_id IS NOT NULL THEN 1 ELSE 0 END) as resolved
      FROM inspections
      WHERE source_system='accela_inspection_scrape_2026-05-22';

3. If any discrepancy in (b) or (c), DO NOT proceed to Phase 4.
   Report the discrepancy. We diagnose before continuing.

4. If all checks pass, report:
   - Total rows ingested
   - Per-permit count match status (12/12 or specifics on failures)
   - Result-code distribution match status
   - Inspector resolution stats
   - Report MD path

Do NOT commit yet — wait for OK.
```

### CC Prompt 4: Full 92-permit ingest

```
Task: Phase 4 — full 92-permit ingest. Type 2 (writes).
Requires Phase 3 12-permit test to have passed all verifications.

INPUTS:
  - scripts/inspection_ingest.py (validated in Phase 3)
  - All 92 JSONs at data/raw/accela_inspections/

STEPS:

1. Run full ingest:
   python scripts/inspection_ingest.py \
     --db databases/berkeley_housing_v2.db \
     --report-path notes/2026-05-23_inspection_ingest_report.md \
     --json-report-path notes/2026-05-23_inspection_ingest_report.json

   Expected: ~6,303 records. INSERT OR IGNORE means the 2,716 from
   Phase 3 are already there; this adds the remaining ~3,587.

2. Verify:
   - SELECT COUNT(*) FROM inspections — should be ~6,303
   - SELECT COUNT(DISTINCT permit_id) — should be ~89-92
     (depending on whether any permits had 0 inspections in JSON)

3. Generate final aggregate stats:
   - Total inspections by year (use inspected_date)
   - Total inspections by result_code
   - Total distinct inspector_strings vs resolved vs unresolved
   - Top 10 permits by inspection count

4. Report:
   - Final counts
   - Aggregate stats
   - Report MD + JSON paths

Do NOT commit yet — wait for OK.
```

### CC Prompt 5: Commit and push

```
Task: Phase 5 — commit and push the inspection ingest in 5
incremental commits per sketch §12. Type 2 (git operations).

STEPS:

1. Commit 1: Schema additions
   git add schema/ databases/keep_snapshot_pre_inspection_ingest_2026-05-23.db
   (Note: db files normally gitignored; this snapshot is policy exception?
    Actually no — keep snapshot is local-only per policy. Skip the db.)
   git add notes/2026-05-23_inspection_ingest_design_sketch.md
   git commit -m "feat: inspection ingest design sketch + schema additions

   Adds inspections table, vocabulary_inspection_result_types,
   and contacts replication from outreach.db. Design sketch
   documents the 12 decisions from 2026-05-23 chat session.

   Schema: 3 new tables, 4 indexes, 7 result-code vocabulary rows."

2. Commit 2: Ingest script
   git add scripts/inspection_ingest.py
   git commit -m "feat: inspection ingest script

   Reads data/raw/accela_inspections/*.json (92 files, 6,303 records)
   and populates v2.inspections. Handles vocabulary resolution,
   inspector resolution against contacts table, missing references,
   and unknown result codes per design sketch §9.

   Tested on 12 Chrome-verified permits (Phase 3); full run pending."

3. Commit 3: Test phase report
   git add notes/2026-05-23_inspection_ingest_report_test12.md
   git add notes/2026-05-23_inspection_ingest_report_test12.json
   git commit -m "feat: inspection ingest test phase 12-permit report

   2,716 records ingested. All per-permit counts match Chrome
   verifications. Result-code distributions match Accela breakdowns.
   Inspector resolution: <N> resolved, <M> unresolved."

4. Commit 4: Full ingest report
   git add notes/2026-05-23_inspection_ingest_report.md
   git add notes/2026-05-23_inspection_ingest_report.json
   git commit -m "feat: inspection ingest full 92-permit completion

   6,303 records ingested across <N> projects. Result distribution
   confirms recon findings. Inspector resolution stats: <X> resolved,
   <Y> unresolved (53 distinct strings, mostly initials)."

5. Commit 5: post-ingest cleanups (any needed)
   Methodology page reference to inspection data, README mention, etc.

Each commit pushed to origin/main individually.

Constraints:
  - Wait for explicit OK between commits.
  - Don't combine commits.
  - Don't commit any .db files (policy).
```

## Layer B (derived views) — scope sketch

Not built in this workstream but documented for context:

- View `inspection_outcome_summary` per permit: counts by outcome_category, dominant code, total
- View `inspection_timeline` per project: UNION of inspections + project_events with source_type column for query disambiguation
- View `staff_inspection_workload` per inspector_contact: count, distinct permits, date range

## Layer C (stage-inference) — scope sketch

Not built in this workstream. Open design questions to address tomorrow:

- Which inspection `type_code` values signal stage transitions?
  - Likely: "Building Final" → completed
  - Possibly: "Certificate of Occupancy", "C/O Final" → completed
  - Possibly: "Foundation" → under_construction
  - Need to inventory `type_code` distribution and map signals
- Confidence model when inspection signals contradict v2.current_stage_type_id
- Output format: report flagging disagreements, auto-correct, or proposal-with-review

## Notes and acknowledgments

- Discipline reflection: three retired pattern interpretations during 2026-05-22 and 2026-05-23 inform this design. Cross-method verification (Chrome + CC local computation) corrected each. Decision 8's stage-inference layer should bake this verification pattern into its design.
- The validation framework formalization (deferred per chat) should capture today's lessons: DOM-first preamble, output-to-chat not clipboard, one extraction per Chrome call, no artificial sleep delays, read Accela's own aggregate counters when possible.
- All 12 decisions banked here are revisitable. The sketch is a snapshot of intent; the build may surface implementation choices that refine specific points.
