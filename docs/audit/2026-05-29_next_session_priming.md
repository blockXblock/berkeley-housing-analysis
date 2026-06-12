# Next Session Priming — written 2026-05-29, revised 2026-05-30 morning

Read this first. It orients today's session to where things stand and what to do, without re-deriving context. Full narrative in `docs/audit/2026-05-29_session_summary.md`; technical detail in `docs/audit/2026-05-29_causes_2_3_diagnostic.md` and `docs/audit/2026-05-29_parcel_collapse_diagnostic.md`.

## First action: verify, don't trust

Per "CC summaries can be wrong; verify artifacts" — confirm the git state before acting on anything below:
git log --oneline -5
git status

Expected at start of today's session:
- HEAD on dev at cc38a99 (docs(audit): session summary and next-session priming)
- dev = origin/dev (fully synced after yesterday's 4 pushes)
- main at e62543a, 20 commits behind dev (deferred fast-forward)
- Working tree: only standing collateral (D6 notebook M, D7 notebook M, data/apr/2024/* M, three untracked items)

If HEAD differs, reconcile before proceeding — do not assume this doc is current.

## Architecture decision revised this morning

Yesterday's Track 3 plan landed on **CSV-canonical, SQLite-derived** for CPRA data. After reviewing past project conversations and Simon Willison's Datasette publication patterns, this is reversed: **SQLite is canonical and committed; Datasette-published via existing Fly.io infrastructure; CSV is an auxiliary export.**

Rationale: the project's outreach pitch explicitly promises Datasette and SQL access for data journalists. The Fly.io deployment infrastructure already exists (used for the household inventory and the berkeleyshops-audience system). The `datasette-publish-fly` plugin is installed. Datasette Lite gives journalists zero-install browser access via WebAssembly. CSV-canonical would have inserted a build step between clone and use — exactly the friction Simon's pattern is designed to eliminate.

Track 2 (path portability + dependencies) folds into Track 3 because the D5/D6/D7 update to read SQLite is itself the portability fix.

## Today's tracks, in priority order

### Track 3 — CPRA SQLite as canonical, Datasette-published (highest priority, absorbs Track 2)

**Architecture:** SQLite canonical and committed. CSV auxiliary export (also committed for grep/Excel access). Excel originals stay in `data/raw/cpra-downloads/` for provenance. SQLite gets Datasette-published via Fly.io.

**Three access paths for users:**

1. **Datasette Lite** (zero install) — URL of the form `https://lite.datasette.io/?url=https://raw.githubusercontent.com/blockXblock/berkeley-housing-analysis/main/databases/cpra_permits.db` runs Datasette in the journalist's browser via WebAssembly.
2. **Fly.io deployed Datasette** (stable URL) — e.g., `cpra.berkeleybuild.com` or `berkeley-cpra.fly.dev`. Persistent, faster than Lite for large queries.
3. **Local clone** — `git clone` + `datasette databases/cpra_permits.db --metadata datasette-deploy/metadata.json`.

**Schema:** single `permits` table, snake_case column names, `permit_number` as primary key, indexes on `parcel_number` / `issuance_date` / `finaled_date` / `work_type` / `adu`, ISO 8601 strings for dates, `source_file` and `ingestion_timestamp` provenance columns, drop the 3 `Unnamed` spacer columns (3, 12, 16) from Excel originals.

**Build pattern mirrors `build_hcd_mirror.py`:**
- `scripts/build_cpra_db.py` reads Excel → produces SQLite + CSV export
- Uses `REPO_ROOT = Path(__file__).resolve().parent.parent` for portability
- Idempotent with atomic table swap
- `--rebuild` flag for full drop-and-rebuild

**.gitignore exception needed:**
*.db
!databases/cpra_permits.db

The HCD mirror remains gitignored and rebuildable via `scripts/build_hcd_mirror.py`; only the CPRA permits SQLite gets the exception, because it represents the canonical CPRA response and is the file Datasette serves.

**Path portability folded in:** The D5/D6/D7 update to read SQLite instead of Excel is itself the portability fix. sqlite3 needs no openpyxl, and the relative-path `databases/cpra_permits.db` works from a clean clone. Hardcoded ROOT paths in D5/D6/D7 setup cells get the `Path(__file__)` treatment in the same change set. README line 15's hardcoded path gets fixed. `requirements.txt` gets openpyxl added (still needed for the Excel-to-SQLite build script) plus Python ≥3.10 pin.

**metadata.json defines canned queries.** Four tiers:

- **Tier 1 (CPRA-only):** new units by year, ADU production by year, large projects (5+ units), demolitions by year, average valuation per unit, submittal-to-issuance time, single-family vs. multifamily by year. ~8 queries.
- **Tier 2 (CPRA joined with parcels/zoning):** ADU production by council district, units completed in commercial zones by year, pipeline by zoning district, density bonus projects, cumulative units by district. Requires bringing a parcels table into the database with `apn` + `council_district` + `zoning_code`. ~5 queries.
- **Tier 3 (cross-domain, roadmap):** beds by council district (needs bed-count data), sales tax revenue by zone (needs CDTFA data), affordability tier breakdown (needs Density Bonus Eligibility Statements). Document as roadmap.
- **Tier 4 (reconciliation against HCD):** projects in CPRA not in any year of HCD submission, CY 2024 reconciliation summary showing our reproduction vs. Berkeley's submission. Makes the audit work directly visible. ~2-3 queries.

Each canned query becomes a clickable named URL endpoint in Datasette and a worked example in the new public page.

**Implementation sequence for today:**

1. Architecture-decision doc — `docs/audit/2026-05-30_cpra_architecture.md` capturing the locked decisions above
2. `scripts/build_cpra_db.py` — Excel → SQLite + CSV
3. `.gitignore` exception for `databases/cpra_permits.db`
4. Run the build; verify SQLite has expected row counts, schema, indexes
5. `datasette-deploy/metadata.json` with Tier 1, 2, and 4 canned queries
6. D5/D6/D7 update to read SQLite (portability folded in)
7. README.md line 15 fix + requirements.txt update
8. Verify D5 produces byte-identical output post-fix (regression check)
9. Deploy to Fly.io
10. Verify the deployed Datasette renders metadata, executes canned queries

### Track 4 — New public page `docs/citizen_apr.html`

After Track 3's SQLite and Datasette deployment land. Page contents:
- Project introduction
- Methodology summary
- CY 2024 numbers: D5 643 CO / 576 BP vs HCD 708 / 731 (9% / 21% gap)
- CY 2025 numbers: D5 525 / 329 vs HCD 481 / 444
- The 4 confirmed under-reports (2328 Channing, 2512 Regent, 2028 Essex, 707 Cragmont)
- Gap accounting at row level
- Three access paths from Track 3 with clickable links
- Canned query examples with explanations
- Clone-and-run instructions for journalists (assumes git unfamiliarity)
- Links to D5/D6/D7 in the repo

### Track 1 — Repository cleanup (lower priority, defer if Tracks 3+4 fill the day)

Per yesterday's forensic findings (`docs/audit/2026-05-29_session_summary.md`):
- Remove `docs/berkeley-flyover.mp4.backup-2026-05-03` from tree + gitignore (73 MB)
- `git gc --aggressive` (3,020 loose objects, 0 packs currently)
- Identify canonical alameda lookup CSV; gitignore or externalize the other two (145 MB)
- Externalize `docs/videos/*.mp4` and `site-by-site/` PDFs to existing R2/IA mirror infrastructure
- Optionally `git filter-repo` to remove dead `berkeley-flyover.mp4` historical versions (258 MB)
- Target: clone size 550 MB → ~150 MB

History rewrite safe per yesterday's clone-traffic analysis (176 cloners but 1 web visitor = predominantly bots).

### Track 5 (lowest priority) — Hypothetical Accela API document

`docs/audit/hypothetical_accela_api.md`. SQLite dialect. Scope to Table A2. Inline data-gap flags. Include speculation marked as such. Drafted against post-Cause-2/3 final state. The canned queries from Track 3 become this doc's worked examples.

## Known-good ground truth (re-usable anchors)

- Berkeley CY 2024 HCD Table A2: 708 net CO, 731 net BP, 228 rows
- D5 post-all-fixes CY 2024: 643 CO, 576 BP
- D5 post-all-fixes CY 2025: 525 CO, 329 BP (note: D5 slightly exceeds HCD's CY 2025 CO of 481 — worth examining)
- Published April 2026 Citizen APR (169 projects, 11,235 units, 12.4% RHNA) stands as-is
- `docs/methodology.html` unchanged since 2026-04-23; the new `citizen_apr.html` supplements it
- 4 confirmed under-reports: 2328 Channing (12u), 2512 Regent (9u), 2028 Essex (1u), 707 Cragmont (1u)

## Do-not-touch

- main (e62543a, 20 behind dev — deliberate)
- `docs/methodology.html` (qualitative page, supplemented by new page not replaced)
- Standing collateral in working tree (D6 notebook, D7 notebook, data/apr/2024/*, three untracked items)

## Standing rules for CC

1. CC summaries can be wrong; verify artifacts before acting
2. Diagnostic docs precede the fix commits that reference them — never "forthcoming companion commit"
3. Regression test baselines update in the same commit as the code they test
4. Predictions are imprecise; actual pipeline measurements are authoritative
5. Same-year gating essential for sibling rules (Durant temp-power inheritance pattern)
6. `git checkout <ref> -- <path>` stages the file in the index, not just the working tree
7. Always `git diff --cached --name-only` before every commit
8. Visible correction over silent rewrite for committed-but-unpushed mistakes
9. Phase A read-only investigation precedes Phase B implementation
10. Working tree standing collateral — leave alone unless explicitly in scope
11. For load-bearing code, byte-accurate edits. For markdown docs we authored, whole-file rewrites are fine.
