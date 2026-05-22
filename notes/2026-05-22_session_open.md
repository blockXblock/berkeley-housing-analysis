# Session open — 2026-05-22

Continuing from 2026-05-21 (commits ff63fb9 through 8b7b65f, all pushed
to origin/main).

## Required reading, in order

1. notes/2026-05-21_session_close.md
   - Yesterday's headline (KML polygon import to canonical v2)
   - Yesterday's loose ends
   - The 4 commit hashes from yesterday's work

2. notes/2026-05-22_url_discovery_design_sketch.md
   - The master-and-suffix model (updated 2026-05-21)
   - The discover_url return shape with related_records[]
   - Master Identification Rule

3. notes/hand_copied_capids_2026-05-21.md
   - 3 verified master triplets + the addendum for B2019-05574
   - Reference for the orchestrator's working URL pattern

After reading, stop and report your understanding before acting.

## Today's planned shape: two sessions

### Morning: orchestrator runs at scale

Goal: produce 30-80 JSON files in data/raw/accela_inspections/,
one per v2 permit with a usable URL. Validates the orchestrator at
scale, surfaces any Cloudflare or stability issues, builds a real
queue of inspection data to feed afternoon's ingest work.

Steps (likely):
  1. Type 1 inventory: count v2 permits with non-null source_url, group
     by source_system (cpra/accela/planning/building) and stage
     (completed/under_construction). Decide whether the URL-bearing set
     is meaningfully large.
  2. Type 2 queue build: insert URL-bearing v2 permits into
     databases/cic_recon_queue.db.scrape_queue. Status = pending.
  3. Type 2 orchestrator run: invoke scripts/scrape_inspections.py
     with --limit set to a conservative batch size first (e.g., 5),
     then scale up if no Cloudflare issues.
  4. Throughout: monitor for Cloudflare blocks. If a block hits,
     STOP, wait 15-30 min, resume.

Risk to track: anti-detection. 2-10s sleep between permits keeps
the orchestrator under most rate limits, but a 50-permit run is
~30-60 minutes of continuous Chromium activity.

### Afternoon: ingest design + build

Goal: design and build scripts/ingest_inspections.py, which reads
JSON files from data/raw/accela_inspections/ and writes findings
to v2 with proper provenance and idempotency.

Five design decisions to resolve before building:

  1. Where do inspection records live in v2?
     - Option A: project_events with a new 'inspection' event_type
       (clean, but each permit can add 100s of events)
     - Option B: New 'inspections' table parallel to project_events
       (clean separation; requires schema add)
     - Option C: JSON blob on permits row (trivial; not queryable)

  2. Provenance mixin: asserted_by = 'accela_scrape_YYYY-MM-DD',
     asserted_at, confidence_type_id = high. Plus source_document_id
     handling (probably NULL or a new approach).

  3. Dedup / idempotency: how to identify a same-inspection across
     re-runs. Probably (permit_id, inspection_id_from_accela)
     unique key.

  4. Supersession: when an inspection's status changes between runs,
     do we UPDATE or mark old is_current=0 and INSERT new? v2's
     pattern suggests the latter for fact tables.

  5. Master vs sub-record: today's orchestrator scrapes master only.
     Sub-record handling is deferred (URL discovery isn't built yet).
     But ingest design should anticipate sub-records exist and have
     a clear "this is master, these are siblings" structure when
     they arrive.

After decisions: Type 2 build of ingest_inspections.py. Test on
the one JSON file already present (B2019-05574.json, 557 inspections).
Then test on the JSON files from morning's runs. Verify v2 reflects
the new state.

## Known starting state

- Canonical v2: databases/berkeley_housing_v2.db
  SHA256: not recorded (was 97d978b6... before the 2026-05-21
  polygon import; post-import SHA not captured)
- Pre-import backup: databases/berkeley_housing_v2_pre_kml_import_2026-05-21.db
  SHA256: 97d978b60534ab82629cd18104906fc11a5eb8b1846662c0a383fb243a6bfce6
- Queue: databases/cic_recon_queue.db
  Contains 1 succeeded row (B2019-05574, 557 inspections,
  2026-05-21 17:53 PT) + 90 pending_url_discovery rows
- JSON output: data/raw/accela_inspections/B2019-05574.json (117 KB)
  Now gitignored.
- Working DB: /tmp/berkeley_housing_v2_kml_import.db
  Disposable; identical to canonical post-promotion.

## Discipline rules (carry forward)

1. CC summaries can be confidently wrong. Verify artifacts directly.
2. Set wider numeric caps than seem necessary; CC narrows on its own.
3. Never commit or push without explicit instruction.
4. One shape per prompt (Type 1 / Type 2 / Type 3). Never combine.
5. Multi-line content via python heredocs (python3 << 'PYEOF'),
   not bash heredocs.
6. Output files to /tmp/ first. Move to notes/ or scripts/ after
   explicit verification.
7. Narrow findings can produce wrong conclusions. Resist drawing
   broad conclusions from narrow evidence.
8. If a server is launched (Datasette, orchestrator), foreground it
   and let the user stop with Ctrl-C. Do not background.

## What I want from you (chat-Claude) at session start

Read the three required files. Confirm understanding in one
paragraph. Then wait for the first specific task. Do NOT freelance.

## Loose ends still open from yesterday

- Dharma University: housing project, exists in KML, not in v2.
  Needs create-project workstream.
- 2740 Shasta Rd (project 86): 2 duplicate-looking KML placemarks
  excluded from polygon import. Needs investigation.
- 5 v2 projects with no KML polygon: which 5? Type 1 follow-up.
- CC environmental: auto-update fixed (sudo chown was needed). v2.0.76
  had interrupt-on-input bug; v2.1.147 doesn't. Worth re-checking
  in ~1 week.

## Stage 1 status (from yesterday)

- Polygon migration gap: CLOSED.
- Database path inconsistencies: not yet addressed.
- Deprecated scripts identification: not yet addressed.
- Canonical exporter documentation: not yet addressed.

Today's work is at the Stage 4 boundary (Orchestrator revalidation).
Stage 1 cleanup remains pending; ingest work today touches v2 schema
and so partially overlaps Stage 1, but is primarily Stage 4
infrastructure.
