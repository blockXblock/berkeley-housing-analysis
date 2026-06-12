# Berkeley Housing — Data-Journalist Demo Prep (next-session priming) — 2026-06-07

**How to use this doc:** It primes a fresh assistant session for the data-journalist demo.
If your assistant has filesystem access (Claude Code, or Perplexity with a connector), read it
in place. If it's a web chat without filesystem access (e.g. claude.ai), paste the contents in.
Either way, the rule below holds: **orient and verify before building.**

---

## ORIENT (read first, in order)
1. `~/berkeley-data/CLAUDE.md` — project map + the non-negotiable working rules.
2. Persistent memory (`MEMORY.md` + `berkeley-housing-pipeline-state.md`) — current state. As of
   the last session: canonical DB `databases/berkeley_housing_v2.db` at SHA **0e9a8aab**;
   `project_stages` = 1,768 rows (per-project pipeline timeline: submitted / deemed_complete /
   entitled / permitted / completed, tagged `[pipeline]` and `[censored-for-duration]`); `dev`
   branch ~12 commits ahead of origin, **PUSH HELD**.
3. `docs/audit/` — the dated change-notes are the real record (the `2026-06-*` docs are the latest
   arc). `PROGRESS.md` may be stale; prefer `git log` + the audit docs.

**Verify-before-characterize.** This project has repeatedly been bitten by stale records and silent
query failures (a "fix" claimed-committed-but-absent; an empty result from a stderr-suppressed bad
query misread as "data missing"). Check claims against live code/DB/files with a *valid* query.
Never read an empty result as proof of absence.

## THE GOAL
A demo for **data journalists** proving we built an **independent, queryable** database of Berkeley
housing from **primary sources** (CPRA permits + Alameda assessor; CKAN/HCD is the verification
target, never a source). The demo must let a journalist:
1. **Query deep per-project data** (Datasette-style) and turn plain-English questions into SQL.
2. **Follow links from each project to the ORIGINAL PDF documents** submitted to the city (APR
   filings, CPRA permit reports, Accela planning scrapes, site-by-site exhibits).
3. **Run AI tools on those PDFs** (extract / summarize / answer questions from the source docs).
4. Get answers to a **catalog of example questions**, and compose new ones from text.
5. See **`.kml` Google Earth tours** of each project's geometry, **labeled from our DB** with:
   owner, developer, architect, builder, inspector, city planner, and pipeline status.

## FIRST TASK — read-only READINESS ASSESSMENT (not a build)
For each capability, report HAVE / PARTIAL / MISSING, grounded in the actual repo:
- **DB / Datasette / NL→SQL:** what's in v2 (`v_projects_flat`, `project_stages`, `permits`,
  `project_events`, `project_participants`/roles); what's already served (`datasette-deploy/` on
  Fly.io; berkeleybuild.com from `main`/`docs`); whether NL→SQL is wired anywhere.
- **PDF corpus + per-project links (likely the weak point — verify, don't assume):** inventory the
  PDFs we hold (`~/berkeley-data-staging/pdf/` APRs; `data/raw/cpra-downloads/`;
  `data/raw/accela_status/`; `berkeley-data/site-by-site/`; `zoning_reports/`) and CHECK whether the
  DB links each project to its specific source documents (is there a documents table /
  `project_events.document_id` path / permit→file mapping?).
- **AI-on-PDFs:** what extraction tooling exists (we've used `pdftotext` + PyMuPDF this arc); what a
  journalist-facing version needs.
- **KML label data — confirm per-field coverage today:** owner (assessor `OwnerName` in
  `databases/berkeley.db addresses_arcgis`); developer/architect/owner (`project_participants` roles
  in v2); planner/inspector names (Accela `permit_events` in V1 `berkeley_housing_analysis.db`,
  `assigned_to`/`marked_by`, and the `accela_status` scrapes); pipeline status (`project_stages`).
  Report which of the 7 fields we can actually populate per project.
- **KML pipeline:** what exists (`docs/kml_versions/`, the hand-edited Earth Pro footprints, any
  flyover), and how labels would be generated from the DB.

**Deliverable:** a per-capability readiness table (HAVE / PARTIAL / MISSING) with specific gaps, then
a proposed demo build plan for John's review. **Do NOT build or write yet.**

## STANDING RULES (from CLAUDE.md — keep them)
Read-only by default. Snapshot before any canonical-DB write → preview → STOP for John's go-ahead →
transactional verify-or-rollback; derived layers (`project_stages` etc.) must keep the CO completion
fingerprint **byte-identical** (CY2023=701, 2024=709, 2025=531, 2026=216). CKAN/HCD is the
verification target, never a data source. Never commit/push without instruction; `dev` only; push is
**HELD**. Diagnostic/change-note docs land in `docs/audit/`. Never log into Accela or enter passwords
(John does the Chrome scraping; give him APN/permit numbers to search).

## OPEN THREADS carried in (from the last session)
- 2435 San Pablo (+41u CY2025) major — adjudicated INCLUDE, **not yet ingested** (gated add pending).
- HCD-mirror **CY2025 doubling** — diagnosed (474 rows = 2×237 live; source-side draft+final),
  surgical re-pull preview ready, **not executed**.
- 26 `accela_status` PS files **unmatched-by-APN** — need project creation before their front-half
  can load.
- 2920 Shattuck (221u) / 2601 San Pablo (223u) entitlements **pending at source** — re-scrape when
  decided.
- D5 ADU fixes (Causes 1/2/3) are **committed** (`22c5864`, `9592159`); the proposed last-finaled-REV
  variant was **rejected** (empirically a regression — REVs restate down-to-zero, never marginal-up).
- The **held push** (`dev` ~12 ahead of origin).
```
