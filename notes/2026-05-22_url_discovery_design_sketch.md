# URL discovery scraper — design sketch

**Date:** 2026-05-22
**Status:** Design only. Build next session.
**Depends on:**
- experiments/accela_scrape/inspection_scraper.py (the proven Playwright pattern this scraper will mirror)
- scripts/build_scrape_queue.py (the queue builder this scraper unblocks)
- databases/berkeley_housing_v2.db (the target of the eventual ingest step)

## Goal

Resolve Accela CapDetail URLs for the 90 in-scope B-permits in v2 that currently have no source_url. Output a JSON-staging file per permit; a separate ingest step (also new) writes back to v2.

When complete: the queue builder rerun will reclassify those 90 rows from 'pending_url_discovery' to 'pending', and the inspection orchestrator can run against the full queue.

## Scope of first production run

90 B-permits in scope (completed + under_construction projects in v2, B-prefix, no source_url today). Per the inventory in /tmp/v2_gap_bounding.md from 2026-05-21, these are spread across roughly 30 distinct projects (a 2026-05-21 verification in /tmp/b_permit_url_inventory.md confirmed the 90 count and located 35 distinct projects).

**Important correction (2026-05-21 browser verification).** The original design assumed each permit-number search returns 1 result. Reality is different: a permit-number search returns the *master* record plus its *sub-records* (REV## revisions, DEF## deferred submittals). Three permits were verified manually:

| permit_number | result count | master capID triplet | status |
|---|---|---|---|
| B2019-05575 | 3 | DUB19-00000-00KIL | Finaled |
| B2021-02225 | 10 | DUB21-00000-00EMR | Finaled |
| B2021-02404 | 20 | DUB21-00000-00EZS | Finaled |

So the search will routinely return many results per query; the scraper must identify the master deterministically (see "Master Identification Rule" below) rather than blindly clicking the first hit.

Estimated run time (revised): search submission per permit is unchanged (~30s), but each result page now requires parsing N records and visiting the master CapDetail page; based on the three verified permits, ~10 records per permit on average × ~5s per record adds ~50s per permit. Total ~80s per permit × 90 permits = **~2 hours**. Original estimate was 1-1.5h assuming 1 record per permit; revised to ~2h based on master-and-suffix discovery. Still substantially faster than inspection scraping because there's no pagination.

## What this scraper does NOT do (deliberate non-scope)

- Does NOT search Accela by address. Address search returns multiple permits per project, which would require fuzzy permit-number matching to map results back to v2. Tractable but a separate workstream; address-based search would also surface the 42 missing entitlement permits in scrape files, which is its own gap. Today: permit-number only.

- Does NOT pull subsidiary permit information. CapDetail pages expose related/sub-records (e.g., a building permit's electrical sub-permit). Useful for primary-vs-subsidiary classification but out of scope for URL discovery.

- Does NOT write to v2 directly. JSON staging only. The ingest step is a separate workstream (see "Open architecture decisions" below).

- Does NOT update entitlement permits (ZP, PLN, DRCF, DRCP). Those 90 in-scope permits are all B-prefix.

## Components

### 1. Queue table addition

Extend databases/cic_recon_queue.db with a new table:

```sql
CREATE TABLE url_discovery_queue (
  id INTEGER PRIMARY KEY,
  permit_id INTEGER NOT NULL,
  permit_number TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  last_attempt_at TEXT,
  error_message TEXT,
  output_file TEXT,
  created_at TEXT NOT NULL,
  succeeded_at TEXT
);
```

Status values: pending / running / succeeded / failed / not_found / ambiguous.

Note: separate table from scrape_queue. Different workflow, different failure modes, different stop conditions. Keep them decoupled.

### 2. Queue builder — scripts/build_url_discovery_queue.py

- Reads v2 to find in-scope B-permits without source_url
- For each, inserts into url_discovery_queue with status=pending
- Idempotent (INSERT OR IGNORE on permit_id, same pattern as build_scrape_queue.py)
- CLI args mirror build_scrape_queue.py

### Master Identification Rule

> **Master identification:**
> The master record is the one whose displayed permit_number exactly equals the search query. Sub-records have a suffix matching the regex `/-(?:REV|DEF)\d{2}$/` on the displayed permit_number.
>
> Sub-record types observed in verification:
> - `REV##` = building revision
> - `DEF##` = deferred submittal
>
> **capID year drift:** the master's `capID1` reflects its filed year; sub-records may have later years (e.g., a `DUB21` master with `DUB24`/`DUB25` sub-records filed in subsequent project phases). The scraper must therefore not assume sub-record capID1 prefixes match the master's prefix.

The scraper applies this rule to disambiguate the master from its sub-records before any field extraction. If zero records on the results page have a displayed permit_number that exactly equals the search query, the result is `found=false` (no master). If exactly one matches, that record is the master and the rest are sub-records. If more than one record has a displayed permit_number that exactly equals the search query, the result is `ambiguous=true` (should not happen for B-permits but worth handling defensively).

### 3. URL discovery scraper — experiments/accela_scrape/url_discovery_scraper.py

Public function:

```python
def discover_url(
    permit_number: str,
    *,
    headless: bool = True,
    max_runtime_seconds: int = 120,
    debug_dir: pathlib.Path | None = None,
) -> dict:
    """
    Discover the Accela CapDetail URL and core fields for a permit,
    plus any related sub-records (REV / DEF) tied to the same master.

    Returns a dict shaped like:

        {
          "permit_number": "B2021-02404",
          "search_url": "...",
          "found": true,
          "ambiguous": false,
          "master": {
            "permit_number_displayed": "B2021-02404",
            "capid_triplet": "DUB21-00000-00EZS",
            "capid1": "DUB21",
            "capid2": "00000",
            "capid3": "00EZS",
            "capdetail_url": "...",
            "filed_date": "...",
            "issued_date": "...",
            "finaled_date": "...",
            "valuation": "..."
          },
          "related_records": [
            {
              "permit_number_displayed": "B2021-02404-REV01",
              "record_type": "REV",            # REV | DEF
              "capid_triplet": "DUB24-00000-XXXXX",
              "capid1": "DUB24",
              "capid2": "00000",
              "capid3": "XXXXX",
              "capdetail_url": "...",
              "filed_date": "...",
              "issued_date": "...",
              "finaled_date": "...",
              "valuation": "..."
            },
            ...
          ],
          "errors": [],
          "metadata": {"records_seen": 20, ...}
        }

    `found=false` means no record matched the search query.
    `ambiguous=true` means more than one record on the results page
    has a displayed permit_number that exactly equals the search query
    (treated as a hard stop; do not pick).
    """
```

Flow:
1. Navigate to Accela CapHome.aspx with permit-number search query
2. Submit search
3. Parse result page (apply the Master Identification Rule):
   - 0 records have displayed permit_number == query -> `found=False`, `ambiguous=False`, no master, no related_records
   - exactly 1 record matches -> that record is the **master**; all other records on the page are candidates for `related_records` if their displayed permit_number matches `^{query}-(?:REV|DEF)\d{2}$`
   - 2+ records match the exact query -> `found=True`, `ambiguous=True`; return without selecting (the ingest step or manual review decides)
4. Click into the master record. On its CapDetail page, extract:
   - capID1, capID2, capID3 from the URL (build `capid_triplet = capID1-capID2-capID3`)
   - filed_date, issued_date, finaled_date (look for labels like "File Date", "Issued Date", "Finaled Date" in record details)
   - valuation (look for "Total Job Valuation" or similar)
5. For each related sub-record on the results page, either:
   - capture the capID triplet from the results-page link/href without clicking through (cheap; preferred for the first run), or
   - visit each sub-record's CapDetail page to capture full fields (more expensive; defer to a later enrichment pass)
   The first-run strategy is "triplet only, no click-through" — this keeps total runtime near the ~80s/permit estimate above and avoids combinatorial growth on permits with 20+ sub-records.
6. Return the dict; caller writes JSON

Anti-detection: the orchestrator (next component) handles sleep delays between permits. The scraper itself doesn't sleep.

### 4. URL discovery orchestrator — scripts/run_url_discovery.py

Mirrors scripts/scrape_inspections.py:
- Reads pending from url_discovery_queue
- Invokes discover_url() per permit
- Writes JSON to data/raw/accela_url_discovery/{permit_number}.json
- Updates queue status
- Logs to logs/url_discovery_YYYYMMDD_{permit_number}.log
- Sleep 2-10s between permits
- Stop conditions: queue empty, --limit, --max-runtime-seconds, 5 consecutive failures, Ctrl-C

Status mapping from scraper result:
- found=True, ambiguous=False, all fields populated -> 'succeeded'
- found=True, ambiguous=True -> 'ambiguous' (write JSON for review)
- found=False -> 'not_found' (permanent, do not retry)
- exception -> 'failed' (transient; retry up to 3 attempts)

### 5. Ingest — scripts/ingest_url_discovery.py (separate workstream)

After the orchestrator produces JSON files, this script reads them and writes back to v2. Schema design pending. Likely operations:
- UPDATE permits SET source_url=?, source_permit_id=? WHERE id=?
- UPDATE permits SET filed_date=?, issued_date=?, finaled_date=?, valuation=? WHERE id=? AND <field> IS NULL (don't overwrite existing data)
- Provenance entries for each updated field
- Handle 'ambiguous' rows (probably skip with a log entry pending manual review)
- Handle 'not_found' rows (probably mark in v2 with a flag like permits.not_in_accela = TRUE, schema TBD)

Schema for the v2 not_in_accela flag is its own decision. Don't include in first ingest run; just skip not_found rows in v2 writes and log them for manual investigation.

## Prerequisites surfaced during design

1. **Accela permit-number search behavior.** We assume the CapHome permit-number search returns 1 result for known permits. Should verify manually before building — pick 3 of the 90 in-scope permits, search by number in a browser, confirm 1-result behavior.

2. **Field labels on CapDetail pages may vary.** Different permit types may use different field labels (e.g., "File Date" vs "Application Date"). The scraper should look for several variants per field rather than one exact match. First scraper run will surface variants; iterate.

3. **Date format on Accela.** Probably MM/DD/YYYY based on the inspection scraper's experience, but worth verifying — v2 stores dates as ISO 8601 (YYYY-MM-DD). The ingest step does the conversion, not the scraper.

4. **Valuation format.** Accela likely shows valuation as "$1,234,567" or similar with currency formatting. The scraper extracts the string; the ingest step parses to numeric.

## Available but deferred enrichment fields

While on the CapDetail page, these fields are also visible and could be captured at near-zero marginal scraper cost. NOT in scope for the first URL discovery run, but noted so they're not forgotten:

- Permit description (often a one-line summary of work covered)
- Expiration date (expires_date in v2)
- Applicant name and/or contractor
- Permit status text (Issued / Finaled / Expired / etc.)
- Sub-records (subsidiary permits linked to this one — relevant for primary-vs-subsidiary classification)

Reason for deferring: each new field has marginal cost in scraper parsing (small), ingest logic (medium), and provenance tracking (medium). The minimum viable URL discovery is URLs + core dates + valuation. Everything else is enrichment for a future workstream.

## Scope estimate for build session

- Refactor planning (manually verify search behavior on 3 permits in a browser): 15-30 min
- Refactor POC if needed for search flow (probably similar to inspection POC but new): 60-90 min — OR skip POC and go straight to module if the search flow is straightforward
- Build queue table + queue builder: 30 min
- Build URL discovery scraper module: 60-90 min
- Build orchestrator: 30-60 min (mostly copying scrape_inspections.py structure)
- End-to-end test on 5 permits: 30 min
- Document findings: 30 min

Total: 4-6 hours focused work. Probably one session if smooth, two if the search flow has surprises.

## What we should NOT try to do next session

- Don't build the ingest step at the same time as the scraper. JSON staging only, same discipline as today.
- Don't try to handle ambiguous matches automatically. Log them, write the JSON, let the ingest step (or manual review) decide later.
- Don't try to pull every CapDetail field. Stay in scope.
- Don't add authentication. Anonymous worked for inspections; should work for URL discovery too. Verify in browser first.
- Don't try to update v2 even for "easy" cases.

## Open architecture decisions for later

1. **Ingest schema for v2 URL/date/valuation updates.** Probably straightforward UPDATEs guarded by IS NULL conditions, with provenance entries per updated field.

2. **v2.permits.not_in_accela flag (or equivalent).** Where do we record "this permit number doesn't exist in Accela"? Could be a new boolean column, or a provenance entry with source='accela' and value='not_found'. TBD.

3. **Ambiguous match resolution.** Some permit numbers may return multiple Accela records (e.g., revisions). How to disambiguate? Probably manual for now; could be automated by picking the highest capID or the most recent filed_date.

4. **Whether to update v2 fields for permits where Accela disagrees.** E.g., v2 has issued_date='2023-04-15' from CPRA, Accela has '2023-04-17'. Don't overwrite; log the discrepancy.

5. **When URL discovery becomes obsolete.** If/when v2 starts getting freshly-scraped Accela data with URLs at ingestion time, this workstream stops being needed for new permits. The 90 permits in today's queue are a backfill task; future permits ideally won't need backfilling.

6. **Sub-record ingest in v2.** The URL discovery scraper now captures master + sub-record triplets. v2's current schema has one row per permit_number, which conflates the master. A separate decision is needed about whether to: (a) one row per Accela record (master + REV/DEF as siblings), (b) one row per master with a separate sub_records table, or (c) one row per master with sub-record capIDs in a JSON column. Defer until URL discovery has run on enough permits to see the sub-record volume distribution.

## Files (to be created next session)

- scripts/build_url_discovery_queue.py (new)
- experiments/accela_scrape/url_discovery_scraper.py (new)
- scripts/run_url_discovery.py (new)
- data/raw/accela_url_discovery/{permit_number}.json (output)
- logs/url_discovery_YYYYMMDD_{permit_number}.log (output)
- Possibly scripts/ingest_url_discovery.py (deferred; separate session after URL discovery runs successfully)

## Reference

- Today's orchestrator commit: 2556481 (will be different hash by next session — search log for "Build inspection scraper orchestrator")
- The session that built it: notes/2026-05-21_orchestrator_built.md
- The pattern this sketch mirrors: notes/2026-05-21_orchestrator_design_sketch.md
- Field discovery starting point: data/outputs/accela_collection_checklist.csv (112 CapHome search URLs already constructed for various Berkeley addresses)

## References (added 2026-05-21 update)

- **Hand-copied capID triplets from 2026-05-21 browser verification:** `/tmp/hand_copied_capids_2026-05-21.md` (3 verified master triplets — B2019-05575 / B2021-02225 / B2021-02404 — plus sub-record counts and a tentative CapDetail URL template). Sibling CSV at `/tmp/hand_copied_capids_2026-05-21.csv`.
- **In-scope inventory verifying the 90-permit count:** `/tmp/b_permit_url_inventory.md` (generated 2026-05-21). Confirms 90 in-scope B-permits across 35 distinct projects; documents that 0 capID triplets are recoverable from existing `data/raw/accela_status/` scrape files (those files are clipboard-pasted human-readable record summaries with no URL/capID data).
- **Source chat for the verification work:** "Building the Berkeley Housing orchestrator from design sketch" (last activity 2026-05-21 evening). The 4th of 5 verification permits attempted in that chat is not captured in either file; only 3 fully-verified triplets are recorded.
