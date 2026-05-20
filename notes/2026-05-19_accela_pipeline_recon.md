# Accela pipeline reconnaissance and architecture findings

**Date:** 2026-05-19
**Status:** Reconnaissance complete. Architectural conclusion: pipeline must use a headless browser (Playwright). No implementation work tonight.
**Reference test project:** 2352 Shattuck Ave (database ID matching this address); permits ZP2018-0135, DRCF2020-0003, B2019-05574, B2019-05575.

## Goal of tonight's work

Determine the architecture of the freshness pipeline that will update status, completion dates, and event history for our 179 tracked Berkeley housing projects by querying Berkeley's Accela Citizen Access portal.

## Findings summary

1. **URL pattern is stable** — Accela's CapDetail.aspx uses a deterministic `capID1/capID2/capID3` triplet to identify each record. No session token in URLs. Bookmarkable.
2. **Berkeley does not populate Accela's Related Records graph** — ZP2018-0135 shows zero related records despite our database listing 4 permits for the project. Planning permits and building permits exist as orphan records. Joins must be done by address + APN, not by relation traversal.
3. **APN search ≠ address search** — neither is a superset of the other. APN returns historical permits (older years, recent activity); address search catches deferred-submittal child records. Pipeline must union both and dedupe on capID triplet.
4. **Completion signal is "Finaled" status, NOT Certificate of Occupancy date** — Berkeley staff often leave the CofO workflow phase as TBD even for fully completed projects. Trust Record Status = "Finaled" as the build-complete signal.
5. **`requests`-only pipeline is not viable** — Accela serves only ~290KB stripped responses to non-browser HTTP clients, regardless of authentication state. The 3.4MB document a real browser receives requires JavaScript execution. Pipeline must use Playwright or equivalent.
6. **2352 Shattuck data is stale in our database** — project is marked Completed but `co_date` is empty; actual Finaled date on B2019-05574 is 01/14/2022. This is the kind of data-quality issue the pipeline will correct.

## Detailed findings

### URL pattern

Format: `https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module={module}&TabName={module}&capID1={prefix}&capID2={mid}&capID3={suffix}&agencyCode=BERKELEY&IsToShowInspection=`

Examples observed:
- **ZP2018-0135** (Planning): `Module=Planning, capID1=18PLN, capID2=00000, capID3=00808`
- **B2019-05574** (Building): `Module=Building, capID1=DUB19, capID2=00000, capID3=00KIJ`

Observations:
- capID2 appears to be always `00000` in examples seen
- capID1 encodes year + module type (`18PLN`, `19PLN`, `DUB19`, `DUB20`, `14B01`, `09B01`, `07B01` observed). Building module's encoding is opaque ("DUB" prefix doesn't decode obviously to "Building").
- capID3 is a 5-character base-36-ish identifier, sequential per (year, module)
- No session token in URL; session lives entirely in cookies
- Stable across sessions — URL can be bookmarked and revisited

For the pipeline: once captured, the (capID1, capID2, capID3) triplet is a permanent stable identifier per record.

### The Related Records gap

ZP2018-0135's Related Records sub-tab returns "No records found." The "View Entire Tree" panel — which fires an AJAX POST to `/BERKELEY/Cap/CapDetail.aspx/GetBuildCapTree` returning JSON — also returns empty.

Our database lists 4 permits for the project: `ZP2018-0135, DRCF2020-0003, B2019-05574, B2019-05575`. All four exist in Accela (verified via APN search). None are linked in the relation graph.

Reason: Berkeley staff do not wire relation table entries when filing new permits. This is a staff-data-hygiene issue, not a software issue. Captured as a separate observation: `notes/2026-05-19_accela_relation_graph_observation.md`.

Pipeline implication: cannot follow relation links to find a project's permits. Must use parcel/address joining.

### Address vs APN search

Berkeley's Accela Building module exposes both search fields directly:
- Street number + street name (e.g., "2352" + "SHATTUCK")
- Parcel No. (APN, e.g., "055 189501805" — accepts spaces)

Results for 2352 Shattuck / APN 055 189501805:

|  | Address search | APN search | Both |
|---|---|---|---|
| Total results | 37 | 44 | 29 |
| Unique to this method | ~8 | ~15 | — |

Unique-to-address records were mostly the B2021-03302-* deferred-submittal child records (DEF01 through DEF07, REV05) plus B2021-03246 demolition.

Unique-to-APN records included older history (2009, 2014, 2016, 2017, 2018), recent 2024 permits (B2024-05033, B2024-05208), and parallel-project permits not at 2352 Shattuck specifically (B2021-02207, B2021-02218).

Pipeline implication: Must run BOTH searches and union results. Dedupe on (capID1, capID2, capID3) triplet.

Default Accela search date range is 22 years backward from today — appropriate for historical recovery but means a lot of irrelevant historical permits (old electrical work for prior tenants) are returned. Pipeline will need filtering logic to separate "permits relevant to this housing project" from "permits ever filed on this parcel."

### Planning permit (ZP2018-0135) reconnaissance

Page heading: `Record ZP2018-0135: Zoning Permit`
Record Status: `Approved`

Major sections present:
- Record Info menu (collapsed) → Record Details / Processing Status / Related Records / Attachments
- Payments menu (collapsed) → Fees
- Conditions (visible immediately)
- Custom Component (empty for this record)

Processing Status events captured (7 dated workflow events):
- 07/26/2018 — Completeness Review: Incomplete Pending Applicant (Sharon Gong)
- 11/15/2018 — Completeness Review: Incomplete Pending Applicant (Sharon Gong)
- 04/12/2019 — Completeness Review: Application Complete (Sharon Gong)
- 10/08/2019 — CEQA Determination: Negative Declaration Required (Sharon Gong)
- 10/24/2019 — Staff Decision: Approved (Sharon Gong)
- 11/20/2019 — Appeal: No Appeal (Karen Hernandez-Gonzalez)
- 11/20/2019 — Case Closed: Approved (Karen Hernandez-Gonzalez)

Notably absent on this record (because it's a zoning, not building, permit):
- No "Permit Issued" labeled date (closest equivalent is Staff Decision 10/24/2019)
- No Final Inspection date
- No Certificate of Occupancy
- No Inspections sub-tab at all

Fees: $67,872 paid (across 4 pages of paid line items), $4,500 outstanding (two invoices from 2022 and 2023). The outstanding fees on an "approved and closed" project from 2019 are a suspicious data point — possibly indicating the project went on to a building permit but the planning case wasn't fully closed out fiscally.

Attachments: 42 files totaling ~370MB inside an iframe. Document type column uniformly labeled "Archive" (no granular types). Filenames follow a date_TAG convention: `_LTR_WELCOME_`, `_APP_PCKT_`, `_RESUB_`, `_DB_` (density bonus), `_HRE_` (historic resources), `_CORR_`. Each attachment is wired to an ASP.NET `__doPostBack` — no direct GET URL. Downloading requires headless browser interaction with the iframe.

### Building permit (B2019-05574) reconnaissance

Page heading: `Record B2019-05574: Permit`
Record Status: `Finaled`
Description: `Phase II of II - North Building; Structural Super Structure, Architectural Building Close In, Mechanical, Electrical and Plumbing for an Eight story mixed use building with five stories of Type IIIA residential over 3 stories of Type IA mixed use.`
Applicant: Bill Schrader (The Austin Group)
Owner: CA AG LOGAN PARK PROPERTY OWNER

Sub-tabs present:
- Record Info → Record Details / Processing Status / Related Records / Attachments
- Payments → Fees
- Conditions
- **Inspections** (this is new on building permits, absent on zoning permits)

Processing Status events (substantially richer than ZP):
- 12/20/2019 — Application Submittal: Plan Distribution
- 04/06/2020, 05/27/2020, 07/02/2020 — three Resubmittal-Revision cycles
- Multi-discipline reviews: Building and Safety, Zoning, Fire, Environmental Health, Public Works, Toxics, Traffic, Design, PSC
- Each review has Corrections cycles followed by Approved dates with reviewer names
- 09/10/2020 — **Issued** (David Lopez) ← Permit Issued Date
- 01/14/2022 — **Finaled** (MD) ← Final Inspection Complete
- TBD — Certificate of Occupancy phase: never marked complete

Reviewer names captured: Kong Chung (Building and Safety), Sharon Gong (Zoning), Jesus Del Toro (Fire), Viviana Garcia (Toxics), Peter Chun (Traffic), David Lopez (Issuance).

Inspections: **553 inspections across 111 pages of pagination.** Server-rendered HTML in the main page, server-paginated via ASP.NET `__doPostBack`. Each inspection row contains: result, type code (e.g., "Building 1150 Framing", "Electrical 2100 Final"), inspection ID, inspector initials, date+time.

Date range of inspections: late October 2020 to 01/14/2022 — roughly 15 months of construction inspection activity.

The Finaled milestone (01/14/2022) corresponds to the "Approved Electrical 2100 Final Inspection" event by MD at 3:03 PM that day. Five days later (01/19/2022) there's a "Site Cancellation Building 1200 Building Final" entry — likely a duplicate workflow cleanup, not a meaningful inspection event.

Build duration for this project (approximate):
- Filed: 12/20/2019
- Issued: 09/10/2020 (9 months in review)
- Finaled: 01/14/2022 (15 months of construction + inspections)
- Total filing-to-finaled: 25 months

This is concrete data for the "how long does it take to build housing in Berkeley?" question. Aggregating across 179 projects would produce a real distribution.

### The `requests` feasibility investigation

We ran four progressive tests of whether Python `requests` (without a browser) could fetch the full Accela permit detail page content:

| Test | Headers | Auth | Result size | Content unlocked |
|---|---|---|---|---|
| Test 1 | Minimal User-Agent only | None | 290,553 bytes | Shell only |
| Test 2 | Full browser headers + Referer | None | 290,553 bytes | Shell only |
| Test 3 | Same as Test 2 + warmed session (8 cookies) | None | 290,553 bytes | Shell only |
| Test 4 | Full headers + manual cookies (831 chars) | Auth | 293,044 bytes | Record Details (applicant, description) |
| Test 5 | Test 4 + matching Chrome 147 User-Agent + sec-ch-ua | Auth | 293,044 bytes | Same as Test 4 |
| Test 6 | Full Chrome cookie set via browser_cookie3 (998 chars, 10 cookies including HttpOnly) | Auth | 290,553 bytes | Record Details |

Reference: Claude in Chrome (real browser, authenticated): **3,400,000 bytes** with full content including all Processing Status events, all 553 inspections (first page rendered, rest paginated), Fees, Attachments iframe populated.

The progressive testing definitively rules out:
- Header differences as the cause
- Cookie completeness as the cause (10-cookie set including HttpOnly cookies returned same result as 831-char manual set)
- User-Agent string matching as the cause

The 3.1MB gap between scripted fetch (290KB) and real browser fetch (3.4MB) is not explainable by HTTP-level differences. It must be explained by:
- Server-side classification of request as non-browser (TLS fingerprinting, JA3 hash, or similar)
- Required JavaScript execution that signals back to the server before content is sent
- A combination of both

Either way, the pipeline cannot use plain HTTP. It needs JavaScript execution.

### Architectural conclusion

**Pipeline must use a headless browser.** Recommended: Playwright (modern, well-maintained, Python-native, headed or headless mode, automatic cookie management, programmatic navigation, DOM extraction).

Pipeline shape (revised from earlier in the session):

1. **Authenticate once.** Playwright session with stored cookies (either programmatic login or cookie injection from browser_cookie3). Detect expired session and re-authenticate.
2. **Per project:** For each project in our database, run both APN search and address search in the Building module. Union results, dedupe on (capID1, capID2, capID3) triplet. Filter to permits matching the project's date range and type.
3. **Per permit:** Navigate to CapDetail.aspx for each permit. Wait for JS to populate sub-tab content. Extract:
   - Record Status (e.g., "Finaled")
   - Processing Status events (workflow milestones with dates and reviewer names)
   - First-page Inspections (date, type, result, inspector)
   - Fees totals
4. **Snapshot to database.** Update project rows with new status, completion dates, latest inspection sentinel.
5. **Diff against last snapshot.** Detect changes. Trigger inspection-detail pagination only when latest inspection ID has changed.
6. **Attachments:** Separate sub-pipeline, run quarterly. Use Playwright to navigate iframe and click each attachment link, capturing the downloaded file. Mirror to three-tier storage (R2 / IA / Drive).

Estimated cost per refresh cycle:
- Playwright page load: ~3-5 seconds per permit
- 179 projects × ~5 permits average = ~900 page loads
- ~45-75 minutes for full refresh, or 15-25 minutes with parallel browser contexts

Runnable as a daily cron. Smarter version: refresh only projects whose last_checked is older than threshold OR whose APN/address has a new permit not in our database.

### Database fields available for the pipeline

`projects` table fields relevant to freshness:
- `pipeline_stage` (current vocabulary in use; 9 distinct values)
- `accela_status`, `accela_status_date` (last Accela snapshot, 47% populated, vocabulary messy from prior scrapes)
- `co_date` (CO date, 8% populated, often wrong/placeholder)
- `complete` (166 populated but suspiciously uniform — likely a data-integrity flag, not a real completion date)
- `final_inspection_date` (only 4 projects populated)
- `construction_start`, `estimated_completion`
- `permits` (comma-separated permit numbers, 98% populated)
- `apn` (94% populated)
- `processing_days`, `inspection_count`, `is_stalled` flag

New fields likely needed:
- `last_accela_check` (timestamp of most recent successful query)
- `last_accela_check_url` (CapDetail.aspx URL queried)
- `latest_inspection_id` (sentinel for change detection on building permits)
- `finaled_date` (when Record Status became Finaled on the primary building permit)

The existing schema is more mature than the pipeline assumes. Some of these fields (`accela_status`, `accela_status_date`) appear to have been designed for exactly this freshness work.

### Data correction observed for 2352 Shattuck

Our database has 2352 Shattuck marked as Completed with `co_date IS NULL` and `accela_status IS NULL`.

Reality per tonight's reconnaissance:
- B2019-05574 status: Finaled
- B2019-05574 Issued date: 09/10/2020
- B2019-05574 Finaled date: 01/14/2022
- B2019-05575 status: Finaled (companion permit, probably same project structure)

A manual correction could be applied immediately, or it can wait for the pipeline. Either is fine; mentioned here for record.

## Open questions for the next session

1. **Playwright proof-of-concept.** Install and verify that loading the CapDetail URL with stored cookies returns the full 3.4MB response with all populated content. Should be ~30 minutes of work, validates the architectural decision.

2. **Inspection parsing.** Write a BeautifulSoup or lxml parser that extracts Processing Status events from a populated CapDetail HTML. Test against the 2352 Shattuck B-permit. The HTML structure is known; the parser is reusable for all permits.

3. **Search workflow automation.** Drive Playwright through the APN+address search workflow. Verify it returns the expected set of permits per project.

4. **Pagination handling.** Test that Playwright can drive the ASP.NET pagination postback on Inspections without breaking on the ViewState/ACA_CS_FIELD rotation.

5. **Rate limiting and politeness.** Add delays between requests. Determine what triggers Accela's WAF or rate-limit response. Polite pipeline first; speed second.

6. **Cookie persistence and session lifetime.** How long does an Accela session last? When does it expire? What's the re-login workflow?

7. **Database schema migration.** Add new fields (last_accela_check, latest_inspection_id, finaled_date) via the v2 migration framework. Decide whether to add an `inspections` table for individual inspection records (separate workstream — see `notes/2026-05-19_inspection_data_as_civic_record.md`).

8. **Authentication automation.** Move from manual cookie extraction to programmatic login (POST to Accela's login form) OR ongoing browser_cookie3 + scheduled cron. Decision depends on session lifetime.

## What was NOT done tonight (deferred)

- Implementation of any actual pipeline code
- Playwright proof-of-concept (just architectural decision)
- Database schema changes
- Inspection parser
- Manual correction of 2352 Shattuck record
- Examination of any other project beyond 2352 Shattuck

All deferred to future sessions. The architectural foundations are in place.

## Files generated this session

In `experiments/accela_scrape/`:
- `test_fetch.py` — initial fetch test, two URLs (uncommitted, contains no credentials)
- `test_fetch_v2.py` — three header variations (uncommitted)
- `test_fetch_authenticated.py` — manual-cookies test (uncommitted)
- `test_fetch_authenticated_v2.py` — Chrome 147 User-Agent test (uncommitted)
- `test_fetch_browser_cookie3.py` — full cookie set test (uncommitted)
- `response_*.html` files — saved fetch responses, ~290KB-293KB each (uncommitted, no sensitive data)
- `cookies.txt` — manual cookie copy used for authenticated tests (SENSITIVE, should be added to .gitignore before any commits)

In `notes/`:
- `notes/2026-05-19_accela_relation_graph_observation.md` (saved earlier in session)
- `notes/2026-05-19_accela_pipeline_recon.md` (this file)
- `notes/2026-05-19_inspection_data_as_civic_record.md` (companion document)
