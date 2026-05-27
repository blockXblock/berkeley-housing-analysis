# Session-close note: 2026-05-23

**Session arc:** What started as "ingest the 92 inspection JSONs + analyze stages for 100 projects" became a foundational investigation that surfaced significant findings about Berkeley's permit-state ontology, the v2 schema's implicit assumptions, and the data infrastructure we need before stage analysis can be trustworthy.

**Tomorrow's primary goal:** Reproduce Berkeley's CY 2025 APR from our updated data using a single Jupyter notebook (notebooks/citizen_apr_2025.ipynb evolved from scripts/generate_apr.py). Compare project-by-project against the city's published 2026-03-27 APR PDF. Iterate until the match is close enough to support the claim: *a high school student running this notebook can produce an APR at least as accurate as the city's.* (Detail in Tomorrow's plan section below.)

**Day's substantive output:**
- Deep reconnaissance across 71 stratified-sample projects (37 columns × 71 rows matrix)
- 14 Chrome live-DOM verifications confirming JSON↔Accela parity (all 14 totals matched)
- 12-decision inspection ingest design (sketch committed)
- Stage-vs-inspection cross-check (91 advancing-stage projects)
- record_status scraper built + run on 107 permits (100% success)
- processing_status scraper built + run on 107 permits (results pending at session close)
- Critical CO ontology finding surfaced via user observation + Perplexity research

---

## The CO finding (most significant of the day)

Berkeley's Accela system does not issue separate Certificates of Occupancy. Per user observation + Perplexity research:

- For additions/alterations: the inspector-signed final inspection card *functions as* the CofO
- For new buildings / change of occupancy: a formal CofO PDF *might* exist as an attachment, but inconsistently
- The closest machine-queryable signal is permit-level "Record Status: Finaled" + approved final inspections
- APR submissions requiring a CO date use derived/heuristic dates, not authoritative ones

**Implications for v2:**

1. **The v2 stage `completed` has been implicitly defined as "some permit at this project got Finaled."** But Berkeley housing projects typically have 4-15 permits (main building, electrical, mechanical, plumbing, plus revisions and deferred submittals). v2 has been picking one as the project-defining permit, often the first one finaled, leaving sub-permits that may still be active.

2. **Confirmed empirically with project 139 (2538 Durant):** v2.completed; B2023-02332 (main construction) Record Status = "Issued"; 429 completed inspections + 4 upcoming; latest inspection "Building 1180 Drywall, Site Cancellation" on 2026-05-21. The project is actively under construction, not completed.

3. **Confirmed contrastingly with project 27 (2441 Le Conte):** v2.completed; B2025-01864 Record Status = "Finaled" despite all 3 inspections being "Disapproved." Accela's "Finaled" can apparently signal "process concluded" not "approved final inspection passed." A different ontology issue.

4. **The headline 18 v2.completed-but-Issued mismatches** found by the record_status scrape are real stage errors at the permit level. They span 12 distinct projects, with multi-permit clusters at: 1598 University (3 mismatched permits), 2538 Durant (2), 1614 Sixth St (2), 1716 Seventh St (2), 705 Arlington (2).

**Ontology questions raised — to address tomorrow:**

- Define "project master permit" formally (which permit speaks for the project? probably by Job Value, by inspection count, or by record_type heuristic)
- Define "project state" as a function of master permit state + sub-permit states (4 candidate definitions surfaced)
- Define v2's CO-equivalent semantics for HCD APR reporting (which derived date represents "CO date" given there is no canonical Berkeley CO)
- Document the new vocabulary needed: Berkeley uses "Finaled," "Issued," "Closed Expired," "Approved" record statuses, which don't map cleanly to v2's stage vocabulary

## Today's 12 inspection ingest decisions (still valid; sketch unchanged)

1. New `inspections` table linked to `permits.id`
2. Inspector resolution against existing outreach.db.contacts + cleaned berkeley_housing_analysis.db.permit_events.marked_by
3. Schema as drafted (provenance mixin, generated date column, raw_json forensic blob)
4. Path B — replicate outreach.db.contacts into v2 as `contacts` table
5. raw_json column included
6. Result-code vocabulary: 7 codes, 3 outcome_category groups, is_terminal flag
7. No dedup at ingest against project_events; derived views compose intelligently
8. Stage-inference layer (Layer C) — now needs richer scope given CO finding
9a. Test on 12 Chrome-verified permits first, then run all 92
9b. Skip-with-log on missing permit references
9c. result_code_id=NULL + result_raw on unknown codes
9d. Exact inspector name match only
10. Validation report (MD + JSON, 7 sections)
11. Pre-ingest snapshot + source_system delete capability
12. Incremental commits (5-commit pattern)

**Decision still pending (added based on tonight's record_status work):**
- Should `permit_record_status` be a denormalized column on the inspections table?
- Should record_status_queue be replicated into v2 as `permit_status_observations`?

## Today's discoveries and discipline reflections

### Three retired pattern interpretations this week

1. **"Accela hides single-parcel small-work permits"** (wrong — auto-redirect bug from 2026-05-22)
2. **"Alteration permits aren't indexed"** (same bug, different sample)
3. **"Approved means active construction; Partially Approved means completed"** (wrong — project-level variation, not stage signal; CC's local distribution computation disproved this between Chrome runs)

The pattern: when CC produces a clean correlation suggesting a mechanism, compute the same pattern at scale before locking it in. Today's CC did this proactively for #3.

### Lessons for the validation framework (deferred but real)

Captured during today's Chrome runs for later formalization:

- **DOM-first preamble required on every Chrome prompt.** Without explicit "use DOM not vision" instruction, Chrome will fall back to screenshot-based reading, which is slow and unreliable.
- **One DOM extraction per Chrome call.** Earlier prompts had Chrome doing 41 steps for one inspection record. Wrong scope; should be 1 extraction.
- **Output to chat, not clipboard.** Sandboxed Chrome blocks execCommand copy. Always include "output blocks directly in chat."
- **No artificial sleep delays.** 200+ Accela requests across multiple scrapers showed 0 Cloudflare blocks. Pacing fears were unsupported by evidence.
- **Read Accela's own aggregate counters when verifying scraped totals.** Per-permit breakdown headers are more authoritative than verifying individual rows.
- **Cross-method verification** (Chrome DOM + CC headless HTTP) on project 139 confirmed the same Record_Status="Issued" via two independent paths. This builds confidence.

### Chrome's "sanitizer" issue

Chrome's safety layer blocked output of raw outerHTML containing href/onclick attributes, treating them as sensitive. CC worked around it by reporting structural surrogates ("rowClass=..., img alt=..., src ending in ..."). Worth noting for future Chrome prompts: don't expect raw HTML; ask for structured descriptions of DOM.

## Data infrastructure as of session close

### Established by end of session

| Asset | Location | Status |
|---|---|---|
| `databases/berkeley_housing_v2.db` | canonical | unchanged tonight (snapshot taken pre-record-status-design) |
| `databases/cic_recon_queue.db` | canonical | added record_status_queue (107 rows, 100% succeeded); processing_status_queue (pending) |
| `data/raw/accela_url_discovery/*.json` | 102 files | 100% URL discovery success |
| `data/raw/accela_inspections/*.json` | 92 files | 6,303 inspection records, JSON↔Accela 100% match |
| `data/raw/accela_record_status/*.json` | 107 files | record status per permit (today's work) |
| `data/raw/accela_processing_status/*.json` | ~107 expected | running at session close |
| `notes/2026-05-23_inspection_ingest_design_sketch.md` | committed pending | 12 decisions documented |
| `notes/2026-05-23_record_status_scrape_report.md` | exists | 16.8% stage mismatch finding |
| `notes/2026-05-23_processing_status_scrape_report.md` | pending | scraper running |
| `/tmp/legacy_data_per_project_inventory_2026-05-23.md` | exists | 337-line recon report |
| `/tmp/legacy_data_per_project_matrix_2026-05-23.csv` | exists | 71-row × 28-column |
| `/tmp/stage_vs_inspection_check_2026-05-23.md` | exists | cross-check; 68% headline agreement, 80% among data-rich |
| `/tmp/stage_vs_inspection_matrix_2026-05-23.csv` | exists | 91-project matrix |

### Snapshot taken

`databases/keep_snapshot_pre_inspection_ingest_2026-05-23.db` (only if CC Prompt 1 from the sketch was run — verify tomorrow)

## Tomorrow's plan — PRIMARY GOAL: APR match workflow

The goal of tomorrow's session is concrete and bounded: **reproduce Berkeley's CY 2025 APR from our updated data, project-by-project, with documented explanations for any divergence. Iterate until the match is close enough to claim that a high school student running a single Jupyter notebook could produce an APR at least as accurate as the city's.**

This is not "fix gaps and prepare for CY 2026." This is "use the data we now have, plus the methodology improvements from today, to match the city's most recent published APR — and own any divergences with documented evidence."

### Tomorrow's morning priorities (in order)

**1. Review tonight's accumulated artifacts (~20 min)**
- Read the processing_status scrape report
- Validate CC's "DOM duplicate" dedup logic (audit 3 sample JSONs to confirm duplicates were truly identical, not subtly different)
- Read the session-close note (this document) freshly

**2. Commit accumulated work in 5 increments (~30 min)**
- Inspection ingest design sketch
- Stage-vs-inspection cross-check + record_status report
- record_status_scraper + outputs
- processing_status_scraper + outputs (assuming clean overnight finish)
- Session-close note + permit_api_policy_brief

**3. Inspection ingest (~2-3 hours) — needed as input for APR match**
- Execute CC Prompts 1-5 from the original sketch
- 12-permit test phase verification against Chrome breakdowns
- Full 92-permit ingest
- This makes inspection data queryable in v2 for APR generation

**4. APR-match workflow (the primary deliverable; ~3-4 hours)**

This is the main work. It has 5 sub-steps:

**4.1 Run scripts/generate_apr.py against current v2.** Produces our CY 2025 APR fresh from updated data. Compare numbers to the published 2026-04 Citizen APR (169 projects, 11,235 units, 12.4% RHNA progress) to see how today's foundation work changed things.

**4.2 Extract project-level data from the city's CY 2025 APR PDF.**
Source: `pdf/2026-03-27 Housing Element and General Plan Annual Progress Reports.pdf` (the city's published 2025 APR).
Extract Table A (Applications Complete) and Table A2 (Building Activity), every row, into a CSV we can query.

**4.3 Project-by-project comparison.**
For each project in either dataset, classify:
- **MATCH**: same project, same unit count, same income breakdown, same stage. (Probably the majority.)
- **MISSING_OURS**: project in city's APR, not in ours. (We saw 18 of these in the CY 2024 comparison work.)
- **MISSING_CITY**: project in ours, not in city's. (We saw 15 of these.)
- **VALUE_DIVERGE**: same project, different unit counts or affordability breakdowns.
- **STAGE_DIVERGE**: same project, different stage assignment (the 18 record_status mismatches found today fall here).

For each non-MATCH row, document the *why*: bad data on our side, bad data on city's side, methodological difference, or unknown.

**4.4 Iterate scripts/generate_apr.py into a Jupyter notebook (notebooks/citizen_apr_2025.ipynb).**
Take the existing script as a starting point. Convert into a Jupyter notebook with:
- Cell 1: load v2 + record_status_queue + (when ready) inspections table
- Cell 2: derive project-level stage labels (using record_status for authoritative state)
- Cell 3: derive CO-equivalent dates (using documented heuristic: master permit's Finaled date, or latest Final inspection's Approved date)
- Cell 4: filter for CY 2025 activity (applications complete in 2025, BPs issued in 2025, COs in 2025)
- Cell 5: generate Tables A, A2, B, D in HCD format
- Cell 6: generate the comparison report against city's APR
- Each cell heavily commented so a high school student could follow.

Apply findings from 4.3 to refine the derivation rules in cells 2-3. Re-run.

**4.5 Match-quality verdict.**
Target: 90%+ of CY 2025 projects MATCH on at least: project identification, unit count within ±2, stage assignment. The remaining 10% should be documented divergences with explanations.

If the verdict shows we match well: write up the methodology, publish the notebook to the repo, draft a brief claim ("a high school student could run this notebook and produce an APR at least as accurate as the city's").

If the verdict shows we still diverge significantly: identify the top 3 sources of divergence and address those before iterating again. (Likely top sources: affordability data quality — the 18% VLI capture rate; ADU coverage — only 9 ADUs in v2 vs 2,644 CPRA-flagged; missing big projects we should have caught.)

### Deferred while APR-match is in progress

These remain on the roadmap but are explicitly NOT primary tomorrow:

- CO ontology design discussion (informally addressed via the APR-match's CO-equivalent derivation rule; formal design comes later)
- Layer C stage-inference build (the APR-match work IS the first stage-inference; formal Layer C comes after)
- Master permit definition (addressed pragmatically in the JN; formal vocabulary comes later)
- Processing Status data integration (used as supporting evidence in the JN; full integration later)

### Deferred to subsequent sessions

- Build a Processing Status scraper for ALL v2 permits (not just the 107)
- LLM-assisted parser for the 157 .txt files (still potentially valuable for per-fee detail extraction)
- CPRA backfill UPDATE for 7 discarded source columns
- Lightweight ADU catalog from CPRA
- Inspection scraping for the 15 newly-URL'd "permitted" permits (URL discovery done yesterday; inspection not yet run)
- Validation framework formalization (lessons captured here, framework drafted from them)
- Minor cleanups (3 url_discovery output_file paths in /tmp/, project 163's "0 PARKER" placeholder, 2740 Shasta Rd duplicate KML, 5 projects without polygons)
- Methodology page update: document Berkeley's no-CO reality and the master-permit convention

### Pending workstreams from prior sessions (not blocked, but lower priority)

- v2 events trustworthiness audit (105 Jan 1 placeholders, 43 unverified synthesized entitlements)
- Document attachment workstream (1,423 rows in legacy DB not migrated to v2)

## Honest assessment

**What today delivered:**

- A complete inspection ingest design (12 decisions banked)
- Two new datasets we didn't have: record_status (107 permits) and processing_status (107 permits, pending overnight)
- Validation framework patterns (DOM-first, one-extraction-per-call, no artificial delays, output-to-chat) tested in practice
- The CO ontology insight that reshapes how we think about project state
- Empirical evidence of 18 specific v2.completed-but-Issued mismatches
- A draft policy brief documenting the cost of Berkeley's missing API and proposing Clariti contract terms

**What today did NOT deliver (relative to original morning goal):**

- The inspection ingest itself
- Stage analysis on 100 projects
- A report on stage status / duration / staff interactions

**APR context (corrected mid-session):**

We already published the CY 2025 Citizen APR earlier this year (169 projects, 11,235 units, 12.4% RHNA progress; sent to ~50+ recipients). The CY 2024 work matched HCD almost perfectly. The CY 2025 work showed material divergences from the city's APR (15 projects we had they missed; 18 they had we missed; VLI capture at 18%).

**Tomorrow's APR-match workflow uses today's foundation work to address those divergences and prove that a high school student running a single Jupyter notebook can produce an APR at least as accurate as the city's.** This reframes today's "detail work" — not as sidetrack but as the data foundation needed to match the city's CY 2025 published numbers.

**The reason the original morning goal didn't land:**

The 16.8% stage mismatch finding + the CO ontology insight collectively meant that proceeding to ingest tonight would have built on a foundation we now know is shaky. Better to take the day to surface these issues, build the supporting infrastructure (record_status + processing_status scrapers), and execute the ingest tomorrow with the foundation properly understood — *as the input to the APR-match workflow*.

**Tomorrow's session has substantially better preparation than today's had.** That's a fair trade for not landing the inspection ingest tonight.

---

## Commits accumulated (to push at session close)

If we commit in 5 incremental groups per the design sketch's commit discipline:

1. **Design sketch + recon artifacts:** `notes/2026-05-23_inspection_ingest_design_sketch.md`, `/tmp/legacy_data_per_project_inventory_2026-05-23.md` → move to notes/, `/tmp/stage_vs_inspection_check_2026-05-23.md` → move to notes/, related CSVs
2. **record_status scraper:** `scripts/record_status_scraper.py`, `notes/2026-05-23_record_status_scrape_report.md`
3. **record_status data:** the queue table update is in cic_recon_queue.db (gitignored per policy), but the JSONs at `data/raw/accela_record_status/` should be committed if they're not gitignored. Verify tomorrow.
4. **processing_status scraper:** `scripts/processing_status_scraper.py`, `notes/2026-05-23_processing_status_scrape_report.md` (when complete)
5. **Session-close note:** this document
