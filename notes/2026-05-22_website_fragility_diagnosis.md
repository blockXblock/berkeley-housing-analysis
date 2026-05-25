# Website fragility diagnosis (in progress)

**Date:** 2026-05-22
**Status:** Diagnostic work in progress. Strategic decisions deferred to a fresh session.
**Companion files:**
- notes/2026-05-22_inventory_legacy_db.md
- notes/2026-05-22_script_lineage_inventory.md

## Project goals and staged plan

The Berkeley Housing Pipeline project is building an independent, auditable public database of housing permit data for Berkeley, with a longer-term goal that any high school in California should be able to clone the model and create the same framework for their local city. The success test is whether high-school data science classes can use public Jupyter notebooks to curate and analyze the data, in cooperation with local City planning staff and under a local open data ordinance that ensures the city provides open, accurate data.

The current arc of work is a staged plan:

1. **Stabilize the normalized database (v2).** Resolve contradictions, deprecate competing systems, get to one canonical source of truth.

2. **Consolidate per-project data with quality checks.** Multiple scrapes over many months added data about different aspects of each project (permit info, fees, events, attachments, geometries, classifications). Verify the data for each project is fully imported into v2, and that no scraped data has been omitted in translation.

3. **Revalidate completeness.** For each project and each permit, confirm we have not lost data captured in earlier scrapes. Compare v2's per-project record against the raw scrape files and the v1 database. Surface any gaps.

4. **Complete the Orchestrator for revalidation scraping.** The inspection scraper orchestrator built 2026-05-20 (build_scrape_queue.py + scrape_inspections.py) is the foundation. Extend it to revisit Accela at Berkeley and re-scrape enough data to validate the existing data -- a freshness/integrity loop, not a one-time capture.

5. **Run the Citizen APR for CY 2025.** This is the test of the basic premise. If our independent data can produce a 2025 APR that matches the city's official APR with high accuracy (as the 2024 reconstruction did at 97.4%), the model is validated.

6. **Demonstrate the public framework.** Once data accuracy is demonstrated, the project becomes a template: public Jupyter notebooks, an open data ordinance, and a working example any high school can replicate for their local city.

Today's diagnostic work sits at the start of Stage 1 (stabilize the normalized database). The fragility surfaced on the website is a symptom of Stage 1 not being complete -- three generations of scripts, multiple "single source of truth" claims, and an undeployed v2 exporter all indicate the stabilization step hasn't been finished.

## Why this notes file exists

This session opened intending to build the URL discovery scraper per notes/2026-05-22_url_discovery_design_sketch.md, but pivoted midway when the user surfaced that detailed Accela data (fees, inspections, processing-status timelines) on the website's "Projects" tab has appeared, disappeared, reappeared, and updated over many sessions -- and that CC's repeated rewrites of the Python scripts that produce that data are the suspected cause.

Today's session became a diagnostic pass through the script ecosystem and the legacy database, with the goal of bounding the problem rather than fixing it. Fixing requires fresh-session judgment with all the inventory artifacts in hand and the staged plan above as the frame.

## What was confirmed

### The data is intact

berkeley_housing_analysis.db (frozen since 2026-05-02) contains:
- $14,125,974.51 in fees across 122 distinct permits, 441 fee records (matches all April 2026 figures)
- 2,306 permit_events across 126 distinct permits
- 179 projects with 100% lat/lng coverage and height data
- 1,423 document records
- 184 project_geometries with GeoJSON

Nothing has been lost in the legacy v1 database. It is intact and richer than v2 currently is in some dimensions (fees, events, documents).

See notes/2026-05-22_inventory_legacy_db.md for the full table-by-table breakdown.

Whether all of that data made it into v2 during migration is one of the key Stage 3 (revalidate completeness) questions.

### The script ecosystem has three generations

Per notes/2026-05-22_script_lineage_inventory.md, 36 .py files in scripts/ + scripts/migration/ + analysis/audit_2026-05-16/.

**Generation 1 (March-April 2026, v1-era):**
accela_workflow.py (3,598 lines), extract_fees.py, parse_timeline_data.py, migrate_to_database.py, export_explorer_data.py. Share the worldview that berkeley_housing_analysis.db is canonical and FINAL.csv is the project list.

**Generation 2 (May 2026, v2 migration era):**
migrate_v1_to_v2.py (1,685 lines), import_cpra_2023_2025.py (923 lines), export_explorer_data_v2.py (757 lines, writes to _v2_working.js NOT to explorer_data.js), generate_apr_v2.py, permit_role_classifier.py. Share the worldview that v2 is canonical but the website hasn't been updated.

**Generation 3 (May 2026, audit era):**
8 small read-only scripts in analysis/audit_2026-05-16/. Diagnostic, not productive.

**Plus today's new layer:**
build_scrape_queue.py + scrape_inspections.py from 2026-05-20. Inspection scraping infrastructure, lives in the v2 track and is the foundation for Stage 4 (Orchestrator revalidation).

## The core diagnostic finding

**The website serves data from a v1 export script that hasn't run since April 13, 2026.**

export_explorer_data.py (v1) -> docs/explorer_data.js -> live website. Last modified 2026-04-13.

export_explorer_data_v2.py (v2) -> docs/explorer_data_v2_working.js (note the *_working* suffix). Last modified 2026-05-13. **Not deployed.**

This explains the appear/disappear/reappear pattern: the website is showing whatever the v1 exporter happened to produce on its last run, and field-name drift in v1 between runs caused the recurring breakage. The v2 work in May added a parallel exporter that was never wired to the live page.

Anything CC has done in v2 since April 13 is invisible on the website. That includes the May CPRA imports, the migration work, the audit findings, and all data growth.

In Stage 1 terms: the website is downstream of a Stage 1 that hasn't been completed. Until the database is stabilized, trying to fix the website would be patching symptoms.

## Specific contradictions surfaced

From the script lineage inventory:

1. **Three scripts claim "Single Source of Truth"**: export_explorer_data.py, export_explorer_data_v2.py, migrate_to_database.py.

2. **Database path inconsistencies**: most scripts use databases/berkeley_housing_analysis.db, but extract_fees.py uses data/berkeley_housing.db (different name AND directory), generate_apr.py and parse_timeline_data.py use data/berkeley_housing_analysis.db (same name, different directory).

3. **Parallel v1/v2 systems with unclear primacy.** Both have active scripts. No clear deprecation path.

4. **extract_fees.py drops and recreates permit_fees table on every run.** Running it destroys existing fee data and rebuilds from text files only.

5. **Hardcoded /Users/johngage/berkeley-data paths throughout.** Multiple scripts. Breaks portability.

6. **14 backup versions of FINAL.csv** in data/processed/. The "FINAL" name is misleading.

7. **project_fees.json vs permit_fees table**: different schemas, different sources. migrate_to_database.py reads from the JSON; extract_fees.py writes to the table.

8. **accela_workflow.py is 3,598 lines.** Multi-purpose script with subcommands; technical debt.

Each of these is a Stage 1 (stabilize) blocker. None can be ignored if the goal is one canonical normalized database.

## What's still unknown

### Gaps in today's inventory

1. **modules/ directory was not inventoried.** 7 files visible in the discovery list (address_normalizer.py, config_loader.py, data_loader.py, geocoder.py, report_generator.py, timeline_calculator.py, __init__.py). These are shared library code likely imported by scripts. Could mean the script-level contradictions are partially mitigated by shared logic OR made worse by it. Next session should inventory modules/ first.

2. **update_housing_data.py at repo root** was not analyzed. Single file, no description, possibly a wrapper or "run everything" script.

3. **The 5 untracked test files in experiments/accela_scrape/** (test_fetch.py, test_fetch_v2.py, etc.) are exploratory work -- likely safe to ignore but unconfirmed.

### Open questions for Stage 1 (stabilize)

1. Are extract_fees.py's destructive permit_fees rebuilds the reason for the appearing/disappearing fee data, or is it export-script field drift? Both could be true.

2. Are the data/ and databases/ paths in different scripts resolved to the same file via symlinks, or are they separate files? If separate, are scripts mutating different databases than they read from?

3. Does the modules/ shared library include exporter logic that would let a unified exporter replace both v1 and v2?

### Open questions for Stage 2 (consolidate)

1. Did all $14.1M of fee data make it from v1 into v2 during migration? (Inventory A confirmed v1 has it; v2 contents not yet inventoried for fee aggregates.)

2. Did all 2,306 permit_events make it into v2's project_events table?

3. Did all 1,423 project_documents make it into v2's documents table?

4. Did the 184 project_geometries make it into v2's project_geometries table, given the polygon audit context?

### Open questions for Stage 3 (revalidate completeness)

1. For each project in v2, can we reconstruct its data from the raw scrape files (data/raw/accela_status/*.txt) and verify v2 has everything the scrape captured?

2. Are there any projects where v1 has data that v2 doesn't?

3. Are there scrape files in data/raw/ that were never ingested into either v1 or v2?

## Recommended next session order

1. **Read the three notes files** (this one, the legacy DB inventory, the script lineage inventory) before doing anything else.

2. **Inventory modules/.** Closes the biggest known gap from today. One small Type 1 task.

3. **Inventory v2.** Mirror Inventory A but for v2 -- table-by-table row counts, fee totals, event counts, document counts. Direct comparison against the v1 inventory tells us whether Stage 2 (consolidate) data made it through migration.

4. **From the v2 inventory, decide Stage 1 first move.** Likely candidates:
   - Reconcile the three database paths (symlinks or genuine duplicates?)
   - Identify which scripts are deprecated vs active and move deprecated ones to scripts/archive/
   - Document which exporter is intended as canonical going forward

5. **Do NOT touch the website yet.** Website work is downstream of Stage 1 and Stage 2 completion. Anything done to the website before stabilization will need to be redone.

## Other workstreams that didn't progress today

- **URL discovery scraper** (the original session goal): paused. Browser verification was 4 of 5 test permits done. The master-and-suffix pattern is well-established across 4 permits; one more permit (B2024-00736) would confirm. URL discovery is a Stage 4 dependency (Orchestrator revalidation needs URLs for all in-scope permits).

- **CPRA next batch** (2018-2022 historical): per memory, was expected around 2026-05-20. Not progressed today. This is a Stage 2 input (more raw data to consolidate).

## Discipline observations from this session

This session was characterized by repeatedly revising the synthesis of what was happening:

1. First take: "the data is gone, regression is bad." Wrong -- data is intact.
2. Second take: "rendering code drifted; the fix is rewiring." Partially right but missed strategic context.
3. Third take: "v2 explorer is undeployed, that's the real gap." Better but still incomplete; missed the staged plan, missed modules/, missed the three-generation script structure.

Each revision was driven by user pushback or one more conversation_search. The pattern: chat-Claude generalizes early findings into conclusions, user notices something missed, search reveals more context, synthesis revises.

Honest read: a fresh session should NOT try to absorb today's full trajectory. The three notes files contain the durable findings. Start there, then proceed through the staged plan.
