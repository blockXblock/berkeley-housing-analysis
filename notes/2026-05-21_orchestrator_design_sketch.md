# Inspection scraper orchestrator — design sketch

**Date:** 2026-05-21
**Status:** Design only. Build next session.
**Depends on:** experiments/accela_scrape/playwright_inspections_poc.py (committed 2026-05-21)

## Goal

Autonomous scraper that processes a queue of Accela permits, extracts
inspection records via Playwright (POC-proven), and writes JSON files to
a staging directory. Separate ingest step (later) writes to v2 database
with provenance.

## Scope of first production run

Completed and under_construction projects only:
- 37 completed projects + 6 under_construction = 43 projects
- Estimated ~80-120 permits across those projects
- Estimated total inspection rows: 4,000-15,000 (varies widely by project size)
- Estimated total run time: 5-10 hours at POC pace of ~4 min/permit + delays

Rationale: These projects directly affect APR. Verifying them first lets us
generate a defensible 2025 APR before HCD publishes the citys version in June.

## Components

### 1. Queue table

Lives in databases/cic_recon_queue.db (separate from v2 to avoid corruption risk).

Schema:

```sql
CREATE TABLE scrape_queue (
  id INTEGER PRIMARY KEY,
  permit_id INTEGER NOT NULL,
  permit_number TEXT NOT NULL,
  project_id INTEGER NOT NULL,
  project_address TEXT,
  capid_triplet TEXT,
  url TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  last_attempt_at TEXT,
  error_message TEXT,
  inspections_count INTEGER,
  output_file TEXT,
  created_at TEXT NOT NULL,
  succeeded_at TEXT
);
```

Status values: pending / running / succeeded / failed / skipped.

### 2. Queue builder — scripts/build_scrape_queue.py

- Reads v2 to find permits for completed + under_construction projects
- For each permit, derives the Accela URL from permit_number (or stored
  capid_triplet)
- Inserts into scrape_queue with status=pending
- Idempotent (skips permits already in queue, allows re-runs to add new
  permits)

### 3. Orchestrator — scripts/scrape_inspections.py

Main loop:

1. Read next pending permit from queue
2. Mark running
3. Invoke Playwright extraction (refactored POC as importable function)
4. On success:
   - Write JSON to data/raw/accela_inspections/{permit_number}.json
   - Mark succeeded with inspections_count and output_file
5. On failure:
   - Increment attempts, store error_message
   - Mark failed (or back to pending if attempts < 3)
6. Sleep 10-30 seconds (randomized to avoid pattern detection)
7. Loop

Stop conditions:
- Queue empty (all permits done)
- MAX_RUNTIME exceeded (e.g., 8 hours per single invocation)
- 5 consecutive failures (likely Accela blocking; stop and alert)
- Manual interrupt

### 4. Ingest — scripts/ingest_inspections.py (deferred)

After orchestrator produces JSON files, separate script reads them and
writes to v2. Schema design for v2 inspections table is its own task.

For first orchestrator run: skip ingest. Just produce JSON. Inspect manually.

## Prerequisites surfaced during design

These come up during build:

1. **Refactor POC into reusable module.** Currently
   experiments/accela_scrape/playwright_inspections_poc.py is a script with
   hardcoded URL. Needs to be a function accepting (permit_number, url) and
   returning (inspections_list, errors_list, metadata).

2. **Permit URL derivation.** v2 has permit_number but may not have
   capid_triplet (the URL components like DUB19/00000/00KIJ). Need a one-time
   mapping step. The 4 permits added for 2352 Shattuck (yesterdays work)
   have source_url stored; not sure about others.

3. **Failure mode classification.** Different failures need different
   responses:
   - Network blip (transient): retry
   - Accela returning login wall (regression): stop and alert
   - Permit doesnt exist (data issue): mark skipped, dont retry
   - Inspection tab empty (no inspections yet): mark succeeded with count=0
   - Captcha or rate limiting: stop entire run

4. **Logging.** Per-permit log entries persistent for next-day diagnosis.
   Probably a logs/ directory with date-stamped files.

## Scope estimate for next session build

- Refactor POC into module: 30-60 min
- Build queue table + queue builder: 30-60 min
- Build orchestrator main loop: 60-90 min
- First end-to-end test on 5 permits: 30 min
- Document findings: 30 min

Total: 3-4 hours focused work. One session if smooth, two if not.

## What we should NOT try to do next session

- Dont build the full ingest pipeline at the same time
- Dont try to handle every edge case (some failures will surface; document
  and skip)
- Dont auto-classify primary vs subsidiary (separate workstream)
- Dont try to make it run unattended for days (start with single-batch runs
  we verify in the morning)
- Dont add authentication (POC proved anonymous works)

## Open architecture decisions for later

These can wait until ingest phase:

1. **Inspections table schema in v2.** Probably a new table linked to permits.
   Fields: inspection_id (Accela), permit_id (FK to v2 permits),
   type_code, type_label, scheduled_date, actual_date, result,
   inspector_initials, raw_json, plus provenance fields.

2. **Deduplication on re-scrape.** When we re-scrape a permit later, do we
   replace the inspection rows or upsert by inspection_id? Probably upsert.

3. **First_inspection_observed and final_inspection_passed events.** The
   vocabulary additions from 2026-05-20 anticipated this. Ingest can
   generate project_events rows automatically from inspection data.

4. **Primary vs subsidiary classification.** Inspection data may help
   distinguish primary permits (lots of construction inspections) from
   subsidiary (just one or two signage/electrical inspections). Could
   inform automated classification.

## Files (to be created next session)

- databases/cic_recon_queue.db (new)
- scripts/build_scrape_queue.py (new)
- scripts/scrape_inspections.py (new)
- data/raw/accela_inspections/{permit_number}.json (output)
- logs/scrape_inspections_YYYYMMDD.log (output)
- Possibly: experiments/accela_scrape/inspection_scraper.py (refactored
  POC as module)

## Reference

- POC script: experiments/accela_scrape/playwright_inspections_poc.py
- POC validation notes: notes/2026-05-21_playwright_poc_validated.md
- Original Accela reconnaissance: notes/2026-05-19_accela_pipeline_recon.md
- Inspection-as-civic-record vision: notes/2026-05-19_inspection_data_as_civic_record.md
