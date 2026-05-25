# Session close — 2026-05-22

## Headline

Built the URL discovery workstream from scratch and reached **100% coverage** (105/105) on the canonical url_discovery_queue. Ran the inspection orchestrator on all 92 permits with a known URL — all 92 succeeded, ~6,300 inspection records harvested. Completed a three-part CPRA audit (source structure, ingestion code, 90-permit join). Five commits on `main`; three live scraper bug fixes; two confidently-wrong pattern interpretations retired by widened-sample empirical evidence.

## State at end of session

### Repo (main)

Today's 5 commits, oldest first:

| hash | description |
|---|---|
| `c445955` | URL discovery: queue builder, scraper, orchestrator (3 new tracked files, 1,785 lines) |
| `0ad3190` | CPRA audit notes (2026-05-22): source, ingestion, gap analysis (5 files) |
| `3196360` | URL discovery workstream notes (2026-05-22): build, fix, run reports (16 files) |
| `c6c4899` | Ignore `data/raw/accela_url_discovery/` scraper output (.gitignore +3 lines) |
| `f295154` | Evening workstreams (2026-05-22): inspection scraping + 15 B-permits (4 notes) |

HEAD: `f295154 Evening workstreams (2026-05-22)`. Not pushed; remote sync status unchanged from session open.

### Canonical databases

| db | size | mtime | sha256 | state |
|---|---|---|---|---|
| `databases/cic_recon_queue.db` | 90,112 B | 2026-05-22 23:26:13 | `31b7010cee372086449f73001b8e16ddc60a3e577070c596c579c4c4c3f3b7b9` | url_discovery_queue: **105 succeeded**; scrape_queue: **92 succeeded** |
| `databases/berkeley_housing_v2.db` | 1,994,752 B | 2026-05-21 16:21:04 | `6df7156c96be356ff2631ec83ebe925aa01f6b0ddf04b4bdf0b2a625456affbe` | **unchanged today** (last touched by yesterday's KML import) |

Backups created today (3, all of `cic_recon_queue.db` at different states):

- `databases/cic_recon_queue_pre_url_discovery_2026-05-22.db` (17:11, 32 KB — pre-promotion of url_discovery_queue table)
- `databases/cic_recon_queue_pre_inspection_run_2026-05-22.db` (17:35, 61 KB — pre-scrape_queue UPDATE to flip 90 rows to pending)
- `databases/cic_recon_queue_pre_15_b_permits_2026-05-22.db` (23:13, 86 KB — pre-insert of evening's 15 B-permits)

All gitignored per standing policy. Restoring is one `cp` away.

### Data on disk

- `data/raw/accela_url_discovery/`: **102 JSONs** (90 from the main URL discovery run + 15 from the evening B-permit run + the B2025-05247 retry overwrote in place). Plus 3 in `/tmp/url_discovery_pre_flight/` for the smoke-test trio whose canonical-output run produced different files; both exist on this machine.
- `data/raw/accela_inspections/`: **92 JSONs** from tonight's inspection orchestrator run. Total ~6,300 inspection records.
- Both directories gitignored.
- `logs/`: per-permit log files for every run today (URL discovery 2026-05-22 runs + inspection 2026-05-22 runs). Gitignored.

### Notes committed today

**25 notes files** touched across the three notes-related commits (`0ad3190`, `3196360`, `f295154`):

- 5 CPRA audit: source inventory, source structural audit, ingestion audit, 90-permit join MD + CSV
- 16 URL discovery: build reports (5), run reports (5), fix reports (3), diagnostic deep-dives (2), promotion audit (1)
- 4 evening: scrape_queue update, overnight candidate analysis, 15-B-permit insert, 15-B-permit run

All named `*_2026-05-22.md` or `*_2026-05-22.csv` for date-stamping.

## Workstreams completed today

### URL discovery (built from scratch)

- **90 in-scope B-permits** (the day's main cohort): 90/90 succeeded via the queue → orchestrator → discover_url path
- **15 additional B-permits** in permitted-stage projects (evening's extension): 14/15 first attempt; **B2025-05247 failed on a transient Accela 502 Bad Gateway**, recovered on retry (master triplet `DUB25-00000-00QH2`)
- **Cumulative: 105/105 = 100%**

Three scraper bugs surfaced and fixed during the day, in order:

1. **Pagination loop** — handle multi-page results-list for permits with many sub-records (B2021-02404 had 20 records / 2 pages)
2. **Auto-redirect detection** — recognize Accela's single-result auto-navigate to CapDetail (B2022-01278 was the diagnosis case; B2019-05575 the backward-compat anchor)
3. **Polling loop wrapping the auto-redirect signals** — handle the ASP.NET UpdatePanel timing race that caused B2023-02303 to be 3/4 flaky in headless

Plus an orchestrator-side fix (commit b is mid-day, not separately tagged): the consecutive-failures counter was treating `not_found` as a failure, halting the run prematurely on `not_found` clusters. Fixed to count only true `failed`.

Two pattern-based interpretations retired by widened empirical evidence:

1. *"Accela hides single-parcel small-work permits"* — wrong. All such permits are auto-redirected to CapDetail; the scraper couldn't recognize the destination until the fix.
2. *"Alteration permits aren't indexed in CapHome's search"* — wrong, same root cause. After the fix, Alteration permits succeed at the same rate as everything else.

### Inspection orchestrator (run outside CC by user)

- **92 permits processed** (1 from yesterday's pre-flight + 90 newly URL-discovered + 1 from this morning's ZP2018-0135 test)
- Runtime: **88.9 min** (5,330s)
- All 92 succeeded
- Inspection-count distribution per permit: min **0** (ZP2018-0135-style — Planning module CapDetail page has no inspection table), avg **68.5**, max **601** (a new outlier exceeding yesterday's 557 for B2019-05574)
- **~6,300 total inspection records** harvested

### CPRA audit (three-part read-only)

- **Part 1: source-file structural inventory** — `BP_Annual Permit Report.xlsx`, 14,149 rows, 26 columns (22 data + 3 spacers + 1 legitimately-empty Completed Date), single sheet, Post Date range 1/1/2023–12/31/2025, all rows B-prefix (Building module only, by design)
- **Part 2: ingestion script audit** — the 98.8% reduction (14,149 → ~174 cpra-tagged v2 permits) is intentional via project-matching filter; 7 source columns are loaded by `cpra_dedup` but discarded by `import_cpra_2023_2025.py` (Submittal Date / OccType / SubType / ADU / Detached / UnitsAdded / source-system-specific fields); `INSERT OR IGNORE` on `permits.permit_number` is a no-op because the column has no UNIQUE constraint — the real safety is the post-insert validation step
- **90-permit join** — every one of the 90 in-scope B-permits is in CPRA (90/90), validating the ingestion path. The 2×2 of (in_cpra × url_discovery_outcome) collapsed to a 1×2 with C=D=0. Source has 2,644 ADU='Yes' rows in 2023-2025.

## Pending workstreams (for tomorrow or beyond)

1. **Inspection ingest workstream** — read 92 inspection JSONs (~6,300 records) into v2. Design decisions still pending from yesterday's session-open: where do inspection records live (project_events with a new 'inspection' type? new `inspections` table? JSON blob on permits?), provenance mixin, dedup, supersession, master vs sub-record handling. Effort: ~1-2 days of design + build + ingest.

2. **CPRA backfill (UPDATE-only Type 2)** — populate the 7 discarded source columns (filed_date from Submittal Date, OccType, UnitsAdded, SubType, ADU, Detached, etc.) for the 174 cpra-sourced v2 permits. Doesn't hit Accela; pure local transform. Effort: ~1-2 hours build + ~15 min runtime. Would resolve the long-standing `filed_date = 1/90` data-quality finding from the B-permit URL inventory.

3. **ADU catalog (Type 1)** — lightweight CPRA-only catalog of the 2,644 ADU='Yes' rows from the 2023-2025 source. ~30 min Type 1 inventory. Future extension: URL discovery + inspection scraping if a higher-fidelity per-permit dataset is needed.

4. **Inspection scraping for the 15 newly-URL'd B-permits** — the 15 from tonight's URL discovery have master triplets but haven't been inspection-scraped yet. ~15-30 min runtime via the same `scrape_inspections.py` orchestrator that ran tonight on the 92. Smallest natural follow-up.

5. **Update `notes/2026-05-22_url_discovery_design_sketch.md`** — the sketch was the spec for the URL discovery workstream and was already updated mid-day to reflect the master-and-suffix model. Should now reflect the final story: 100% recovery on the full 90-permit cohort + 15-permit extension, the three bug fixes, and the two retired reframings.

6. **Minor cleanups:**
   - 3 of 105 `url_discovery_queue.output_file` values point at `/tmp/url_discovery_pre_flight/` (the smoke-test trio). Canonical JSONs exist for those permits in `data/raw/accela_url_discovery/`; queue pointers are stale.
   - Project 163's `'0 PARKER St'` placeholder address — resolvable from B2025-00820's scraped CapDetail page (per user note during the evening run). Worth fixing during ingest.
   - 2740 Shasta Rd duplicate KML placemark excluded yesterday — still pending review.
   - 5 v2 projects with no KML polygon (yesterday's KML import follow-up).
   - Dharma University project — create-from-KML workstream still pending.

## Discipline reflections worth carrying forward

Today's prompts to CC retired two confidently-wrong pattern interpretations:

1. *"Accela hides single-parcel small-work permits"* — surfaced from the Part 4 CPRA join's finding that all 59 not_found permits had `cpra_row_count=1`. The correlation was real; the causal story was wrong.
2. *"Alteration permits aren't indexed in CapHome's search"* — surfaced from the post-fix batch-of-5 verdict where 2/5 recovered and the 3 failures were all Alteration. Again the correlation was real; the cause was the auto-redirect timing race plus single-shot signal check.

Both were corrected by:
- **Cross-method verification** (user's manual browser test for B2022-01278 surfaced the auto-redirect behavior; B2023-02303 4-run diagnostic surfaced the timing flakiness)
- **Widened sample sizes** (the full 57-permit rerun retired the WorkType pattern; the 5-stubborn-permit rerun retired the residual flakiness theory)

The discipline that saved us: when CC produces a sharply-explained correlation suggesting a causal mechanism, that's the moment to **look for cross-method verification, not the moment to lock in.** Today's late-day prompts to CC also got better at this — explicitly asking for evidence-based hypotheses, not pattern-based interpretations. The B2023-02303 diagnostic prompt's "form an evidence-based hypothesis, not a pattern-based interpretation" callout produced the correct timing-race answer on the third diagnostic.

Worth building this awareness into future prompt design.

## Architectural understanding confirmed today

The Berkeley Housing Pipeline has two complementary data sources, each documenting what the other doesn't well:

- **Accela's CapHome** surfaces all in-scope B-permits via public search when the scraper is properly built (today's 105/105 result corrects the prior misinterpretation that some categories of permit are unreachable).
- **CPRA** documents all permits comprehensively, including the 7 columns (Submittal Date, OccType, UnitsAdded, SubType, ADU, Detached, plus source_url-equivalent context) that the current v2 ingestion path does not capture.

The original *"city redaction"* and *"alteration not indexed"* hypotheses were both wrong; pattern correlations turned out to be downstream effects of scraper-side bugs (single-result auto-redirect handling gap, ASP.NET UpdatePanel timing race).

All 90 in-scope B-permits' inspection histories are now collected (92 JSONs total including the inspection-POC B2019-05574 and the Planning-module ZP2018-0135 test). ~6,300 inspection records are ready for ingest into v2 — the workstream isn't built yet; design decisions pending.

15 additional B-permits in *permitted* stage now have URL discovery completed. Their inspection scraping is the natural next quick run, ~15-30 min.

## Numbers in one place

| metric | value |
|---|---|
| Commits today | 5 |
| Tracked files added today | 3 code + 25 notes + 0 db = 28 |
| URL discovery success rate | **105/105 = 100%** |
| Inspection scraping runs today | 1 (92 permits, ~88.9 min) |
| Total inspection records harvested | ~6,300 |
| Scraper bugs fixed | 3 (pagination, auto-redirect, polling) |
| Pattern-based interpretations retired | 2 |
| Backups created | 3 (all of cic_recon_queue.db) |
| v2 modifications | 0 (unchanged from 2026-05-21) |
