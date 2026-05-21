# Orchestrator built — JSON staging pipeline operational

**Date:** 2026-05-21
**Status:** Infrastructure complete and verified end-to-end on one permit. Production runs blocked on URL discovery workstream.
**Builds on:** notes/2026-05-21_orchestrator_design_sketch.md (the workplan executed today), notes/2026-05-21_playwright_poc_validated.md (the POC behind the scraper module).

## What today delivered

Four artifacts:

1. **experiments/accela_scrape/inspection_scraper.py** — refactored from playwright_inspections_poc.py into an importable module exposing one public function:
   ```python
   scrape_inspections(permit_number, url, *, headless=True,
                      max_pages=200, max_unique=1500,
                      max_runtime_seconds=1200,
                      debug_dir=None) -> dict
   ```
   Algorithm unchanged from POC. Verified against B2019-05574: 557 unique inspections, zero duplicates, final_pagination_state='last_page', identical inspection_id set as POC.

2. **databases/cic_recon_queue.db** — new SQLite database with scrape_queue table. Schema follows the design sketch with one documented deviation: `url TEXT` (nullable) instead of `url TEXT NOT NULL`, so rows awaiting URL discovery can exist with status='pending_url_discovery' and url=NULL.

3. **scripts/build_scrape_queue.py** — populates scrape_queue from v2 in-scope B-permits. Idempotent (INSERT OR IGNORE on permit_id). CLI args for --v2-db and --queue-db paths; defaults to $BERKELEY_V2_DB env var or Path.home() based.

4. **scripts/scrape_inspections.py** — orchestrator main loop. Reads pending rows, invokes the scraper module, writes JSON to data/raw/accela_inspections/{permit_number}.json, updates queue status, logs each permit to logs/scrape_inspections_YYYYMMDD_{permit_number}.log. Stop conditions: queue empty, --limit reached, --max-runtime-seconds exceeded, 5 consecutive failures (Accela-blocking signal), Ctrl-C (graceful — current row reverts to pending). Sleep between permits: random 2-10s, always on (--no-sleep flag exists for testing but should never be used in multi-permit runs — exists for anti-detection).

End-to-end test (Step 5 today): orchestrator processed B2019-05574 from queue read through JSON write through queue update with inspections_count=557, status='succeeded'. Set equality of inspection_ids with Step 2 verify run confirmed zero drift.

## Queue state at end of session

- Total in-scope B-permits in queue: 91
- status='succeeded': 1 (B2019-05574, completed today)
- status='pending_url_discovery': 90 (blocked on URL discovery)
- status='pending': 0
- All other statuses: 0

The orchestrator's main loop filters for status='pending' exactly, so today's run won't accidentally re-run B2019-05574 or attempt the 90 URL-blocked rows.

## Queue DB is not in git

databases/cic_recon_queue.db is gitignored (the databases/ directory is excluded wholesale, same as v2's berkeley_housing_v2.db). The queue DB is bookkeeping state, not source-of-truth data, so this is intentional rather than an oversight.

To recreate the queue on another machine or in a fresh clone:

    python3 scripts/build_scrape_queue.py

This rebuilds the queue from current v2 in-scope B-permits. Status flags ('succeeded', 'failed', etc.) from prior runs do NOT carry across rebuilds — the queue starts fresh with all rows in 'pending' or 'pending_url_discovery' status. The authoritative record of which permits have been successfully scraped lives in data/raw/accela_inspections/*.json, not in the queue.

## What's deferred (the URL discovery workstream)

The orchestrator can scrape any B-permit it has a URL for. Today we have 1 URL (the POC permit). The other 90 in-scope B-permits need URL discovery: an Accela search by permit_number to derive the capID triplet, from which a CapDetail URL can be constructed.

Starting point: data/outputs/accela_collection_checklist.csv contains 112 CapHome (search) URLs already constructed — these are search queries by address, not direct permit links. A URL discovery scraper would either:

  (a) Use these search URLs and resolve each to its CapDetail link via the search result page
  (b) Search by permit_number rather than address (cleaner — permit_number maps 1-to-1 to a single record)

(b) is probably simpler. Either way, the URL discovery scraper is a separate Playwright workflow that updates v2's permits.source_url and permits.source_permit_id, then the queue builder re-runs and reclassifies pending_url_discovery rows to pending.

SESSION URL WARNING (carries over from prior recon): some URLs Accela exposes via JavaScript are session-bound and stop working once the session ends. CapDetail URLs with capID1/2/3 are durable (server-side keys, verified by today's anonymous run). Anything that looks like a one-time token (viewID, recordID, document download links) is NOT durable. When the URL discovery scraper extracts URLs, it should construct CapDetail URLs from the capID components using the known template, not save Accela's JavaScript-generated URLs verbatim.

## Other gaps surfaced this session (not for next session, but tracked)

These came up during today's inventory work and are worth noting even though they don't block the URL discovery workstream:

1. **v2 entitlement-permit gap.** 8 of 13 in-scope projects with Accela scrape files have entitlement permits (ZP, PLN, DRCF, DRCP) that exist in scrape files but not in v2. 42 missing entitlement permits across 8 projects. Not relevant to inspection scraping (inspections live on B-permits only) but real v2 completeness gap. See /tmp/v2_gap_bounding.md from this session for the full breakdown.

2. **Default path resolution in the orchestrator.** scripts/scrape_inspections.py uses Path(__file__).parent as the base for default --output-dir and --log-dir. When the script lives in scripts/, this resolves to scripts/data/raw/... and scripts/logs/, which is one level lower than the design sketch intends. For now, always pass --output-dir and --log-dir explicitly when running. Fix: walk up to repo root, or read a BERKELEY_REPO_ROOT env var.

3. **Stale docstring in scripts/scrape_inspections.py.** setup_permit_logger() docstring says "Returns (logger, file_handler)" but the function returns three values (logger, file_handler, log_path). Cosmetic.

4. **Inconsistency in the original POC validation notes.** The first draft of notes/2026-05-21_playwright_poc_validated.md described the pagination fix as Playwright's native page.click(), when the actual fix uses page.evaluate(__doPostBack(...)). The notes file was corrected mid-session. This is captured for posterity because it's the second time this session that notes files written from chat narrative didn't match the actual code. Lesson: notes describing code behavior must be verified against the code itself, not synthesized from chat reports.

5. **JSON output size discrepancy.** Today's orchestrator wrote B2019-05574.json at 117 KB. The POC validation notes report the POC's output was ~327 KB. Same 557 inspections, identical inspection_id set. Difference is likely formatting (debug metadata, extra fields, or pretty-print verbosity in the POC). Not a problem — data is provably identical via set equality — but the POC notes' "~327KB" number is wrong by ~3x. Worth correcting in those notes if revised later.

## Discipline reflections (for the next session)

This session executed 7 main steps (0, 0d, 0e, 1, 2, 3, 4, 5) plus several Type 1 inventory detours (0b, 0c, 0d, 0e) that weren't in the original plan. The detours added ~90 minutes but prevented a wrong assumption (initially "1598 University capIDs will boost our queue from 1 to 7 permits") from propagating into the queue builder.

Three patterns from CC use this session, all in the opening brief but worth restating:

1. CC summaries can be confidently wrong. Verified by reading the actual files at every step. Found one real bug in the queue builder (cursor.rowcount vs queue_conn.total_changes) from reading code, not summary.

2. Narrow findings can produce wrong conclusions. The first URL coverage inventory looked only at v2 and reported "2 of 103 permits have URLs." A second, broader inventory confirmed the conclusion but also surfaced the 42-permit entitlement gap that the narrow query missed.

3. CC's TODO comments are absent because CC didn't make judgment calls during the refactor and orchestrator builds — likely because the prompts spelled out structural choices in advance. This pattern works.

## Next session priorities

In order of dependency:

1. URL discovery scraper. ~99% of today's queue (90 of 91 rows) is blocked on this. Likely a half-day task; uses the same Playwright patterns as the inspection scraper.

2. Re-run scripts/build_scrape_queue.py after URL discovery populates v2. Should reclassify the 90 rows from pending_url_discovery to pending.

3. Run the orchestrator with no --limit. Estimated runtime per the design sketch: 5-10 hours for 91 permits at ~4 min/permit plus 2-10s sleeps. Probably want to chunk this with --limit to confirm behavior at scale before unleashing.

4. Build the ingest step (scripts/ingest_inspections.py). Read JSON files from data/raw/accela_inspections/ and write to v2. This is its own design problem; see the design sketch's "open architecture decisions for later" section.
