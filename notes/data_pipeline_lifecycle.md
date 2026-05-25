# Data pipeline lifecycle

**Status:** Conceptual reference. Pipeline is partially built as of 2026-05-21. Updates expected as remaining components ship.
**Last reviewed:** 2026-05-22

## Why this document exists

Yesterday's session built the inspection scraper orchestrator (commit 2556481 plus follow-on commits). Today is building URL discovery. As these pieces snap together, the question of "how does a CPRA dataset arriving three months from now flow through the pipeline" became implicit and worth capturing explicitly.

Without this document, every future "what should I run when new data arrives?" question is re-derived from the notes files of individual sessions. Capturing the lifecycle once removes that overhead.

## The data sources feeding v2

Berkeley Housing Pipeline's v2 database (berkeley_housing_v2.db) holds permits, projects, inspections, and provenance from multiple upstream sources. Three are operational; the fourth is partially built and arriving via today's work.

The sources in roughly chronological order:

1. **CPRA responses.** California Public Records Act requests returning permit data as PDFs (or sometimes spreadsheets) from the city's planning/building departments. Manually parsed into v2. Source identifier in v2: source_system='cpra'. CPRA data gives permit_number, dates, valuation, and descriptions, but typically NOT Accela URLs or capID triplets.

2. **Direct Accela scraping (legacy).** A small number of v2's permits were scraped directly from Accela earlier in the project (14 of 103 in-scope B-permits as of yesterday). These have source_system='accela'. Of those 14, only 2 captured the source_url at scrape time. The other 12 lost their URLs in ingestion.

3. **Alameda County parcel data.** Authoritative parcel polygons linked to projects by APN. Source_system varies. Doesn't produce permit-level data directly, but anchors projects to real geographic boundaries.

4. **Inspection records via the new orchestrator (in build).** For permits with a known Accela CapDetail URL, the inspection orchestrator scrapes inspection history into JSON-staging files at data/raw/accela_inspections/{permit_number}.json. A future ingest step will write these into v2 inspection tables (schema pending).

Each source has its own quirks: CPRA is manual and lossy on URLs. Accela scraping is automated but blocked on missing URLs for most permits. Parcel data is the cleanest but doesn't contain permit content. No single source is complete.

## The "URL discovery" workstream and why it exists

Accela uses two identifier systems: the human-facing permit_number (e.g., "B2019-05574") that appears in CPRA documents and city correspondence, and an internal capID triplet (e.g., "DUB19-00000-00KIJ") that determines the CapDetail URL. There is no algorithmic mapping between them. To open a permit's record on Accela's website, you need the capID. Most of v2's permits arrived via CPRA without capture of the capID.

URL discovery is the workstream that maps permit_number to capID by searching Accela's CapHome.aspx with the permit number and extracting the capID from the result URL. It is specifically a backfill task — making it possible for the inspection orchestrator to open and scrape permits whose URLs were lost (or never captured) when v2 was first populated.

URL discovery is Accela-specific. A city using Clariti, Tyler EnerGov, or any other permit system would not need this exact workstream, though similar mismatches between human-facing IDs and internal URL keys do appear in other systems.

URL discovery is also a one-pass operation per permit. Once you know B2019-05574's capID is DUB19-00000-00KIJ, you don't need to re-derive it. The capID is stable for the life of the record.

## The lifecycle of new data arriving

When a new CPRA dataset arrives (or any new permits land in v2 from any source), the pipeline operates as follows:

**1. Ingest.** CPRA-specific ingestion writes new permit rows into v2.permits. Existing rows may be updated if the new dataset contains more recent information. This step is outside the scope of the scraping infrastructure; it's its own workflow that exists mostly already.

**2. Queue rebuild.** scripts/build_scrape_queue.py runs against v2, finds in-scope B-permits, and populates the scrape queue. It is idempotent: existing rows are not touched, only new permits are added. Rows are classified by URL availability: 'pending' if the permit already has a usable source_url, 'pending_url_discovery' if it doesn't.

**3. URL discovery on new pending_url_discovery rows.** The URL discovery orchestrator (built today, after this notes file) processes rows with status='pending_url_discovery'. For each, it searches Accela, extracts the capID, captures core fields (dates, valuation), and writes a JSON-staging file. A separate ingest step writes the URL and fields back to v2.permits.

**4. Queue rebuild (again).** After URL ingestion, build_scrape_queue runs again. Permits whose URLs are now known move from 'pending_url_discovery' to 'pending'. The queue is now refreshed.

**5. Inspection scraping.** The inspection orchestrator (scripts/scrape_inspections.py) processes rows with status='pending', calling the scraper module per permit and writing JSON to data/raw/accela_inspections/. Each succeeded permit's queue row moves to 'succeeded'.

**6. Inspection ingest (future).** A scripts/ingest_inspections.py script (not yet built) will read the JSON files and write inspection records into v2. After this step, v2 holds the inspection data and the JSON files become archival.

This 6-step lifecycle is the normal flow when new data arrives. Steps 1, 2, and 4 are cheap. Step 3 (URL discovery) is bounded by how many new permits need URLs; for a typical CPRA batch this is tens to low hundreds of permits, taking 1-3 hours. Step 5 (inspection scraping) is the longest, at ~4 minutes per permit.

## What needs re-running vs. what's once-and-done

A permit's lifecycle has stages where data is captured once and others where data evolves over time. Knowing which is which is important for deciding when to re-scrape.

**Once-and-done per permit:**
- URL discovery (capID is stable for the record's life)
- filed_date, issued_date (these don't change once recorded)

**Evolves over time:**
- finaled_date (gets set when construction completes)
- valuation (sometimes revised mid-project)
- inspections (grow continuously during construction)
- permit status text on Accela (changes over project lifecycle)

This distinction means: URL discovery on a permit is permanent; inspection scraping is recurring. A permit scraped today for its inspections may need re-scraping in 3 months to capture additional inspections that occurred in the interim.

The current inspection orchestrator treats status='succeeded' as terminal — a succeeded permit is not re-scraped. This is the right design for the first pass, but the queue will eventually need extension to support periodic re-scraping. Likely additions:

- A last_scraped_at field separate from succeeded_at
- A re-stage operation that flips selected succeeded rows back to 'pending' for refresh
- Possibly a recurrence schedule per permit (e.g., active permits re-scraped monthly, completed ones quarterly, finaled ones annually)

These are deliberately deferred until URL discovery completes and v2 has its first full inspection backfill. After that the re-scrape design has real data to inform it.

## What this document is not

This is not a runbook. Procedural steps for running each component live in the README of each component (or will, when ingest is built). Don't add command-line examples or specific paths here; they go stale faster than the lifecycle does.

This is not a schema reference. v2's table structures and the queue's structure live with the code. Reference them from there, not from here.

This is not a roadmap. It describes what exists and how the pieces relate, not what should be built next. Roadmap decisions live in per-session notes files.

## When to update this document

Update when:
- A new data source is added (a new source_system value in v2)
- A new workstream is added (e.g., when ingest scripts ship)
- The "what evolves over time" list changes (new fields, new recurrence requirements)

Don't update for:
- Specific commit hashes or session-level details (those go in per-session notes)
- Bug fixes or refactors that don't change the data flow
- Schema changes (those go with the schema)
