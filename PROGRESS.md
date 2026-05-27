# Berkeley Civic Data Infrastructure — Progress

**Purpose:** Regenerable session-state artifact. The authoritative latest state for resumption after compaction or a break.

**Audience:** Future-me, chat-Claude reading as session context. Optimize for fast re-orientation, not narrative completeness.

**Prior version:** `PROGRESS_legacy_2026-04-30.md` (renamed; kept verbatim for reference)

---

## Project state (as of 2026-05-27)

- **Branch:** `dev`, up to date with `origin/dev` at `f7e7ec8`
- **Working tree:** clean of tracked changes; ~55 untracked files pending triage (see Open follow-ons §4)
- **Recent commits:** see "Recent commits" section below
- **What's verified:** D5 (CPRA-first APR) and D6 (D5↔HCD diff) committed and re-validated; HCD CKAN mirror validated against NotebookLM PDF reading (CY 2022/2023/2024 match to the unit); CY 2024 APR cross-check confirms CY 2025 patterns are anomalies, not systematic
- **What's in flight:** waiting on Planning Module CPRA fulfillment from Berkeley (filed 2026-05-26, statutory ack by ~June 5); D7 (Table A diff) scaffolding to begin when fulfillment arrives
- **Repo metrics:** v2 schema currently 45 tables / 46 indexes / 9 compat views (originally designed at 34/36/9 — organic growth)

---

## Architecture decisions banked

- **One master `berkeley.db` long-term** for parcels, addresses, zoning, business licenses. `berkeley_housing_analysis.db` (v1) and `berkeley_housing_v2.db` (v2 normalized) continue as working pipeline DBs and will eventually be absorbed
- **Alameda County is the authoritative parcel source.** City of Berkeley's parcel layer is a clipped copy. Polygons are approximate (±~1m), not legal surveys
- **GitHub Pages → Cloudflare Pages migration deferred**
- **v2 normalized schema:** 34 tables / 36 indexes / 9 backward-compatibility views as the original design intent (current state: 45 tables, 46 indexes, 9 views per organic growth). Vocabulary tables replacing hardcoded enums. Provenance mixin (`source_document_id`, `asserted_by`, `asserted_at`, `confidence_type_id`) on all fact-bearing tables
- **GeoJSON-as-TEXT for portability.** No SpatiaLite, no WKT. Parsed by `shapely.shape(json.loads(geojson))` on read
- **Reference data versioning** via `is_current` / `superseded_by` pattern (parcels, addresses, project_status)
- **Per-field provenance** via `project_status_history` + `manual_overrides` pattern (decision made; partially implemented)
- **CKAN is the oracle** for what Berkeley actually submitted to HCD. **PDFs are the submission medium.** **CPRA-derived D5 is the independent reproduction.** When numbers diverge, CKAN row-level data is the ground truth; PDF column totals may apply different counting rules
- **Master-permit-only unit counts.** Berkeley populates `UnitsAdded` on every REV sub-permit with the **project's cumulative unit total**, NOT the marginal delta. Summing across master + REVs double-counts (10× for a 9-REV project). Use `master.UnitsAdded - master.UnitsRemoved` only

---

## Active CPRA requests

- **Planning Module entitlement data 2018-2025** — filed 2026-05-26 to City of Berkeley. **Unblocks D7** (Table A diff). Statutory acknowledgment by ~June 5; full response or 14-day-extension notification by ~June 19
- **Mayor re Accela API access / Clariti contract / Open Data** — drafted in `docs/letters/`, not sent
- **HCD re HCD↔Berkeley correspondence** — drafted, not sent

---

## Key findings banked

- **Berkeley `UnitsAdded` REV semantics: cumulative, not marginal.** Every REV sub-permit carries the project's running cumulative unit count. D5's original Cell 7 summation logic double-counted; corrected in commit `2c3b575` (D6 notebook commit). See `notes/research_threads/` and D5's Bug-fix markdown cell
- **HCD CY 2025 doubling:** 240 exact A2 duplicates; 16 of 32 Table A rows duplicated. Characterized as **submission-level error** (Berkeley submitted twice; HCD load appended), not systematic methodology. Dedup logic in `scripts/build_hcd_mirror.py` handles A2; same methodology applies to Table A
- **2029 University density-bonus split.** ZP2024-0181 (240 units, bonus version) and ZP2024-0182 (160 units, base version) appear as separate Table A rows in CY 2025. Base+bonus splitting is **not Berkeley's standard practice** and appears specific to CY 2025. v2.projects already de-duplicates such pairs to the bonus version
- **CY 2024 APR cross-check confirms CY 2025 patterns are anomalies, not systematic.** See `notes/2026-05-26_cy2024_apr_crosscheck.md`
- **One REV pattern divergence flagged:** 1951 Shattuck `B2021-04893-REV14` appears to use **marginal-delta** REV ("add 7 additional units to the original 156"); needs CKAN cross-check to characterize whether genuinely marginal at source or a PDF-annotation artifact
- **Berkeley acknowledges reissuance double-counting** as a known APR issue (City Manager memo page 5, March 2025); HCD permits it conditional on annotation
- **Berkeley has no Socrata building-permits dataset.** Accela web portal is the only live source. Hence the CPRA-and-scrape strategy
- **~20-30 hand-edited Google Earth building footprints**, NOT the previously-assumed 5. Preservation snapshot at `docs/kml_versions/keep_snapshot_2026-05-01.kml`. Polygon audit pending
- **HCD mirror validated against NotebookLM PDF audit:** CY 2022/2023/2024 match to the unit (716, 828, 708 respectively); CY 2025 dedup matches within 1 unit (481 vs NotebookLM's 482). CY 2021 PDF was unparseable; CKAN fills the gap. Establishes HCD as a trustworthy oracle
- **D5↔HCD diff (D6) results:** 5 of 9 spot-checks land in `in_both_clean`. 4 real divergences characterized: net vs gross (2538 Durant: D5 net=71 vs HCD gross=83), stage attribution (2067 University: D5 BP-year vs HCD CO-year), ADU counting (0 Virginia: D5=2 incl. ADU vs HCD=1), pre-CPRA-window misses (2556 Telegraph, 1698 University)

---

## Open follow-ons (prioritized)

1. **Build CY 2024 D5-equivalent** — programmatic verification of the visual cross-check in `notes/2026-05-26_cy2024_apr_crosscheck.md`. CPRA BP data 2018-2025 already in repo; copy-and-adapt of the D5 notebook
2. **Row-level check of 1951 Shattuck B2021-04893 / REV14** against CKAN and CPRA BP data — characterize whether this REV is genuinely marginal at source or a PDF-annotation artifact (would partially invalidate the "cumulative semantics" rule if marginal cases exist)
3. **D7 scaffolding for when Planning Module CPRA fulfillment arrives** — Table A diff: CPRA Planning data → D7 → HCD Table A. Same shape as D5→D6
4. **Untracked working-tree triage** — sort into commit / gitignore / delete buckets:
   - `analysis/audit_2026-05-16/` (schema and valuation audit artifacts)
   - `scripts/processing_status_scraper.py`, `scripts/record_status_scraper.py` (Accela scrapers)
   - `scripts/generate_apr_v2.py` + `.backup_pre_v2_migration`
   - `experiments/accela_scrape/`, `experiments/cesium/`, `experiments/maplibre/`
   - `docs/letters/` (CPRA drafts)
   - `notebooks/06_polygon_cleanup/`, `notebooks/audit/`, `notebooks/generate_tour.ipynb`
   - `notes/2026-05-18_*` through `notes/2026-05-23_*` (session notes)
   - `research/open-policy/`
   - Daily log markdown files (`2026-05-26.md`, `Daily log started 2026-05-02.md`)
   - `*.bak` and `*.backup_*` files
   - `logs/`
5. **Day-11 CPRA nudge template** — if Berkeley goes silent past ~June 5

### Older follow-ons carried forward from PROGRESS_legacy

6. **Promote ~20-30 hand-edited Google Earth polygons** to `manual_polygon` rows. Preservation snapshot exists at `docs/kml_versions/keep_snapshot_2026-05-01.kml`. Polygon audit pending
7. **APN normalization across `berkeley.db` and `berkeley_housing_analysis.db`.** Three formats in use; blocks cross-DB joins. See Conventions below. Estimated 2-4 hours
8. **Consolidate active databases.** Merge `berkeley_housing_analysis.db` tables into `berkeley.db` per architectural decision. Estimated 8-12 hours. Deferred until APN normalization complete
9. **2740 SHASTA duplicate** — two project rows; need to determine canonical
10. **5 remaining SKIP_NO_MATCH addresses** — Accela lookup workflow
11. **Investigate `.txt` scrape captures for DB integration** — many .txt files were created during scraping; may contain richer narrative content (owner intent, controversy, design notes) than structured DB columns
12. **Join `news_coverage` (2,024 rows) to projects** via address-regex matching pass

---

## Discipline rules (carried forward)

1. **CC summaries can be wrong; verify artifacts** (file existence, command output) before asserting they exist or contain claimed content
2. **Never commit/push without explicit instruction;** dev only, no push without "approved"
3. `/tmp/` first, **promote after verification**
4. **Validate logic as a script, then package as a notebook.** Same pattern used for D5 and D6
5. **CKAN is the oracle** for what Berkeley actually submitted; PDFs are the submission; CPRA-derived D5 is the independent reproduction
6. **Don't extrapolate from single cases to column totals** without row-level data support (the "595 lesson" — claimed PDF correction didn't reduce cleanly from row-level data)
7. **`.ipynb` editing via Python json module**, never sed/awk. Validate JSON parses after every edit
8. **Track 1 (path-only fix) vs Track 2 (logic refactor) separation.** Fix the symptom now; carry the refactor as its own task
9. **Tool selection:** Execution / filesystem / DB queries → Claude Code (CC). Design conversations / multi-step planning / catching reasoning errors → chat-Claude. The two AIs do NOT share state — PROGRESS.md is the bridge

---

## KML and video tour state

### Canonical KML

- `docs/berkeley_skyline.kml` — canonical KML loaded into Earth Pro; regenerated from `project_geometries` table, not hand-edited
- `docs/geometry.kml` — stable URL exposed on site (per commit `9c6bfbc`, May 16)
- Generator: `scripts/generate_kml.py` — rewritten 2026-04-25 to read from `project_geometries`. Reads polygons with status-based styling (color by pipeline stage); silently excludes projects without coordinates; KML coord order is `lon,lat,alt`
- `docs/kml_versions/` — historical archive
- `docs/kml_versions/keep_snapshot_2026-05-01.kml` — **preservation snapshot** of Earth Pro state at the time the polygon discrepancy was discovered (20-30 hand-edited footprints, not 5 as previously assumed)

### Tour KMLs

`docs/tours/` contains the working tour set. Inventory as of 2026-05-27:

| file | role |
|---|---|
| `berkeley-overview-tour.kml` | Broad overview tour |
| `berkeley-tour-45sec-rebuilt.kml`, `berkeley-housing-pipeline-tour-45sec.kml`, `205sec.kml`, `longer.kml`, `longerv2.kml` | Duration-targeted variants |
| `berkeley-tour-telegraph-shattuck-cedar.kml` | Telegraph/Shattuck/Cedar corridor |
| `berkeley-tour-extended-dramatic.kml` | Extended scenic narrative |
| `downtown-berkeley-tour.kml` | Downtown core |
| `Berkeley Housing Pipeline - 3D Skyline.kml`, `Berkeley Skyline` | Skyline visualizations |
| `Adeline-Shattuck-s2n`, `Elmwood-Downtown`, `Dormitory`, `Over-200` | Themed tours |
| `tour-edit-1950-oxford-2026-05-03.kml` | Specific-site tour edit |
| `README.md` | Tour-set documentation (review for current authoritative tour list) |

### Past video output

- **17-largest-private-projects flyby video** added as first homepage video (commit `e0b813d`)
- **UC Berkeley Dormitories video** — regenerated and updated (commit `3aab19c`, May 16)
- **YouTube channel:** @BuildBerkeley2050 (per session notes)

### Research thread: temporal flyby imagery

See `notes/research_threads/temporal_flyby_imagery.md` (8.5 KB, May 25). Captures the concept for KML tours that display **different imagery layers per site** over a fixed sequence:
- Time-lapse (Google Earth Historical 2010 / 2015 / 2020 / today)
- Design-vs-reality (architect rendering vs current build)
- Permitting-lifecycle (existing → demolition → construction → finished)
- Modular construction (prefab module arrival/lift)
- Regional comparison (same project type across Berkeley/Oakland/Albany)
- Civic controversy (sites that drew significant public comment)

Proposed schema addition: `project_visual_assets` table with `project_id`, `source_type_id` (vocabulary), `date_observed`, `file_path`/`url`, `geometry_hint`, provenance mixin. Activation deferred to Phase D refactor.

### Google Earth Pro state caveats

- Hand-edited polygons in "My Places" are **not version-controlled** — only the preservation snapshot at `docs/kml_versions/keep_snapshot_2026-05-01.kml` captures them
- The "Proj-2" folder previously vanished from Earth Pro (preservation concern still active)
- People's Park's hand-traced L-shaped footprint was overwritten by the full Alameda County parcel polygon during a KML regeneration — known incident
- Network link to `berkeley_skyline.kml` may be stale after regeneration; refresh in Earth Pro after each regenerate

### Open work in this area (intersects "Open follow-ons" §6)

- Promote the 20-30 hand-edited polygons to `manual_polygon` rows in `project_geometries` — preserves them in the DB rather than relying on Earth Pro local state
- Polygon audit comparing keep_snapshot against current Earth Pro state to identify any further changes since May 1
- Featured-project polygon refinement for tour stops (hand-trace 10-20 buildings vs parcel polygon as ground reference; round-trip into `project_geometries`)

### Past knowledge about generating video tours — methodology snapshot

1. **Sequence stays fixed across tours; imagery selection varies.** A given list of project stops (e.g., "17 largest private projects") can render different thematic tours by swapping imagery layer per stop.
2. **Camera moves authored in KML** (`<gx:Tour>` elements). Tour KMLs in `docs/tours/` are the working set.
3. **Recorded in Earth Pro via screen capture**, optionally with voiceover.
4. **Encoded and embedded on berkeleybuild.com** with downloadable KMLs for advanced users.
5. **Optional in-browser exploration** via Cesium or MapLibre embed (experiments under `experiments/cesium/` and `experiments/maplibre/`).
6. **The bug to avoid:** regenerating the canonical KML overwrites hand-traced footprints in Earth Pro's My Places (the People's Park incident). Always check keep_snapshot before regeneration.

---

## Conventions worth remembering

### APN formats

| Source | Format | Example |
|---|---|---|
| `berkeley_housing_analysis.db.projects` | 12-digit space-separated | `058 214901904` |
| `berkeley_parcels.csv` | Hyphenated, variable-width | `58-2149-19-4` |
| `berkeley.db.parcels` | Hyphenated | `16-1428-2-2` |
| `berkeley.db.addresses_arcgis.apn_norm` | No separator | `055182901100` |
| Business license records | `ZZZZZZZZZZZZZ` | Placeholder for mobile/various |
| CPRA `Parcel Number` | 12-digit space-separated | `055 183500901` (matches v2) |
| HCD CKAN `APN` field | 12-digit space-separated | `055 183500901` (matches v2/CPRA) |

**Normalization rule:** Strip all non-digits to get canonical 12-digit form. Both `058 214901904` and `58-2149-19-4` normalize to `058214901904`. APN is `book(3)-page(4)-parcel(N)-subparcel(N)` per Alameda County convention.

### Geometry formats

| Context | Format | Coordinate order |
|---|---|---|
| `project_geometries.geojson` column | GeoJSON TEXT | `[lon, lat]` (GeoJSON standard) |
| KML output | KML coordinates | `lon,lat,alt` (same as GeoJSON) |
| Shapely parsing | `shapely.shape(json.loads(geojson))` | n/a |

### Special cases — UC Berkeley projects

These intentionally have no APN (UC land is not in the county parcel system). They fall back to `synthetic_footprint` or `manual_polygon` geometry sources.

- 2400 BOWDITCH St
- 2556 HASTE St
- 2200 BANCROFT Way
- 1950 OXFORD St

### Date scoping in CPRA BP fulfillments

CPRA `BP_Annual Permit Report-*.xlsx` files are scoped by `Finaled Date`, NOT by `Submittal Date`. A permit filed in 2014 that finalled in 2025 appears in the 2023-2025 file, not in 2018-2022.

### Header row in CPRA XLSXs

6 banner rows + 1 blank + **header at row 8**. `pd.read_excel(..., header=7)`.

---

## Housing pipeline data snapshot

*A snapshot. For current numbers, query `databases/berkeley_housing_v2.db` directly or rebuild D5/D6.*

| metric | value | as of |
|---|---|---|
| v2.projects total | 181 | 2026-05-24 inventory |
| v2.permits total | 244 | 2026-05-24 inventory |
| v2.project_events | 2,347 | 2026-05-24 inventory |
| v2.fees | 441 | 2026-05-24 inventory |
| v1.projects total | 179 | 2026-05-24 inventory |
| CPRA permits 2018-2025 (XLSX) | 30,764 unique | 2026-05-26 |
| CPRA permits in 2023-2025 file | 14,149 rows | 2026-05-26 |
| CPRA permits in 2018-2022 file | 18,053 rows | 2026-05-26 |
| Berkeley rows in HCD CKAN table_a2 | 1,930 (post-dedup) | 2026-05-26 |
| Berkeley rows in HCD CKAN table_a | 369 | 2026-05-26 |
| D5 distinct housing projects (CPRA-derived) | 4,078 | 2026-05-26 |
| D6 diff rows in_both_clean | 13.2% [needs re-check] | 2026-05-26 |

---

## Recent commits (last 10)

```
f7e7ec8 notes(d6): CY 2024 APR cross-check confirms CY 2025 doubling is anomaly
2c3b575 feat(d6): D5↔HCD diff notebook for Table A2 (CY 2018-2025)
d706c9d feat(hcd): build_hcd_mirror.py — reproducible HCD APR mirror from CKAN
f9409c9 feat(apr): D5 CPRA-first APR notebook — produces Table A2 CY2018-2025
cb4ad7d data: add Berkeley CPRA BP fulfillment 2018-2025 + README
644fa05 docs(co-rule): normalize transcript references; add 4 Chrome verification files
f940ecd docs(co-rule): v2 master-permit rule + 10-point verification record
af3dca8 merge: catch dev up to main (May 19-22 work)
ea9d245 docs(apr): add notebook inventory — D4 confirmed canonical
d337133 docs(apr): add baseline run report — Track 1 result
```

Pull current via `git log --oneline -10` for fresher state.

---

## How to resume

- **New chat-Claude session:** paste this PROGRESS.md plus any specific task context
- **Next session priority:** pick from "Open follow-ons" above
- **If Planning Module CPRA fulfillment has arrived:** jump to #3 (D7 scaffolding)
- **If a recent commit's content is unclear:** run `git show <hash>` for full diff; commit messages are descriptive
- **For methodology questions:** see `output/D6/methodology_notes.md` (auto-regenerated by running the D6 notebook)
- **For the HCD mirror:** rebuild via `python scripts/build_hcd_mirror.py` (it's gitignored)
- **For D5/D6 outputs:** rebuild via the notebooks (outputs gitignored)

---

## Recent decisions log

*Most recent first. Carrying forward April entries from PROGRESS_legacy.*

### 2026-05-26 — D6 commits and methodology revisions

- **D5 Cell 7 CO_units bug fixed** — was summing UnitsAdded across master + REVs (double-counted because Berkeley populates cumulative not marginal). Corrected to use master only. See commit `f9409c9` Cell 7 bug-fix markdown
- **D6 (D5↔HCD diff notebook) committed** as `04_reporting/D6_diff_d5_vs_hcd.ipynb` — outputs gitignored
- **D6 methodology framing finalized as Option B** — drop specific 755/595 numbers, document patterns (base+bonus pairs, CY 2025 doubling) without claiming a derivation that doesn't reduce cleanly from row-level data
- **Planning Module CPRA filed** to City of Berkeley

### 2026-05-25 — HCD mirror + validation

- **HCD CKAN mirror created** via `scripts/build_hcd_mirror.py`. All 12 APR tables pulled; 8 have Berkeley data; mirror is gitignored (regenerable). See commit `d706c9d`
- **NotebookLM PDF audit cross-validates HCD CKAN mirror** — CY 2022/2023/2024 match to the unit; CY 2025 within 1 unit. Establishes HCD as a trustworthy oracle
- **CY 2025 doubling characterized** as a Berkeley submission-level error (draft + final both loaded), 240 exact duplicates in A2 and 16 of 32 duplicates in A. Dedup logic added to `build_hcd_mirror.py`

### 2026-05-24 — Database inventory and forensic diagnostic

- **Full database inventory** (12 → 40 .db files; 28 mostly snapshots/backups + 2 zero-byte path-confusion stubs identified). 3 fossils safely deleted in commit `01032cd`
- **Data-trust history note** committed at `notes/2026-05-24_data_trust_history.md`; documents three CC data-damage incidents and the defensive posture they justify

### 2026-04-30 (carried forward from PROGRESS_legacy)

- **Featured projects polygon approach:** 10-20 hand-traced footprints for tour features; remaining ~150 keep parcel-polygon or synthetic fallback
- **Parcel data authority confirmed:** Alameda County is authoritative; City of Berkeley is a clipped derivative
- **Architecture review committed:** "One master DB, many tables" model. `berkeley.db` will absorb `berkeley_housing_analysis.db` tables over time
- **Per-field provenance pattern selected:** `project_status_history` + `manual_overrides` over fully attribute-level facts table
- **Database inventory completed:** 12 databases catalogued

### 2026-04-25 (carried forward from PROGRESS_legacy)

- **Schema migration completed:** v1 → v2-style structure with versioning and 9-type geometry vocabulary
- **150 parcel polygons imported** into `project_geometries` from `berkeley_parcels.csv`
- **0 LE ROY APN recovered** as `058 224402501` via Accela investigation
- **`generate_kml.py` rewritten** to read from `project_geometries` table instead of flat CSV
- **NICAR tutorial button** merged dev → main and deployed

---

## Appendix A: File locations quick reference

```
~/berkeley-data/
├── PROGRESS.md                          # This file (regenerable session-state artifact)
├── PROGRESS_legacy_2026-04-30.md        # Prior version, preserved verbatim
├── databases/                           # All .db files gitignored
│   ├── berkeley.db                      # Master (50MB) — parcels/addresses/zoning/licenses
│   ├── berkeley_housing_analysis.db     # Active v1 housing pipeline (1.1MB, 179 projects)
│   ├── berkeley_housing_v2.db           # Active v2 normalized (1.9MB, 181 projects, 244 permits, 45 tables, 9 views)
│   ├── hcd_apr_mirror.db                # HCD CKAN mirror (regenerable via scripts/build_hcd_mirror.py)
│   ├── cic_recon_queue.db               # Scrape queue (URL discovery + scrape + record/processing status)
│   ├── accela_reports.db                # Staging
│   ├── berkeley_housing_apr.db          # Frozen APR snapshot
│   ├── berkeley_address_centric.db      # Materialized view (deferred decision)
│   ├── berkeley_energy_use.db           # BESO data
│   └── backups/, *_pre_*.db             # Pre-operation snapshots
├── data/
│   ├── raw/
│   │   ├── cpra-downloads/              # Berkeley CPRA BP fulfillments 2018-2025 (XLSX + README)
│   │   ├── accela_inspections/          # 92 JSONs, 6,303 inspection records
│   │   ├── accela_record_status/        # 107 permits
│   │   ├── accela_processing_status/    # 107 permits
│   │   └── accela_url_discovery/        # 102 permits
│   ├── reference/                       # alameda_lookup_complete.csv, berkeley_parcels.csv, etc.
│   ├── processed/                       # FINAL.csv and downstream
│   └── apr/2025/                        # v1 baseline APR outputs
├── 04_reporting/
│   ├── D4_hcd_apr_tables.ipynb          # Canonical APR notebook (v1, pre-refactor)
│   ├── D5_apr_from_cpra.ipynb           # CPRA-first APR (committed f9409c9)
│   └── D6_diff_d5_vs_hcd.ipynb          # D5↔HCD Table A2 diff (committed 2c3b575)
├── output/
│   ├── D5/                              # gitignored; rebuild via D5 notebook
│   └── D6/                              # gitignored; rebuild via D6 notebook (includes methodology_notes.md)
├── scripts/
│   ├── build_hcd_mirror.py              # HCD CKAN mirror builder
│   ├── generate_apr.py                  # v1 APR generator
│   ├── generate_kml.py                  # KML generator from project_geometries
│   ├── permit_role_classifier.py        # Permit role classifier
│   ├── record_status_scraper.py         # Accela record_status (untracked)
│   ├── processing_status_scraper.py     # Accela processing_status (untracked)
│   └── README.md
├── docs/
│   ├── berkeley_skyline.kml             # Canonical KML
│   ├── geometry.kml                     # Stable site URL
│   ├── kml_versions/                    # Archive + keep_snapshot_2026-05-01.kml
│   ├── tours/                           # Tour KMLs (see KML section above)
│   ├── methodology/                     # Methodology docs
│   ├── migration/                       # v1→v2 migration plan + report
│   ├── letters/                         # CPRA drafts (untracked)
│   └── database_architecture_review_2026-04-30.md
├── notes/
│   ├── 2026-05-24_data_trust_history.md
│   ├── 2026-05-24_apr_workflow_audit.md
│   ├── 2026-05-26_cy2024_apr_crosscheck.md
│   ├── research_threads/temporal_flyby_imagery.md
│   └── chrome_verifications/2026-05-25/
└── analysis/audit_2026-05-16/           # Schema + valuation audit artifacts (untracked)
```

---

## Appendix B: Key table schemas

### v1: `berkeley_housing_analysis.db.projects` (58 columns)

| column | type | notes |
|---|---|---|
| `id` | INTEGER | Primary key |
| `address_display` | TEXT | Canonical display address |
| `apn` | TEXT | Format: `058 214901904` |
| `units` | INTEGER | Total unit count |
| `status` | TEXT | Pipeline status |
| `latitude` / `longitude` | REAL | WGS84 |
| `permits` | TEXT | Comma-separated permit numbers |
| `is_uc_project` | INTEGER | 1 if UC Berkeley project |
| `filed` / `entitled` / `bp_issued` / `co_date` | TEXT | Stage dates (sparse) |
| `developer` / `architect` | TEXT | Sparse |
| `vli_units` / `density_bonus` / `sb35_flag` / `sb330_flag` / `ab2011_flag` | INTEGER | Streamlining/affordability flags |

### v2: `berkeley_housing_v2.db.projects` (11 columns)

| column | type | notes |
|---|---|---|
| `id` | INTEGER | PK |
| `city_id` | INTEGER | FK → cities |
| `canonical_address` | TEXT | Authoritative address |
| `canonical_name` | TEXT | Project name (sparse) |
| `normalized_address` | TEXT | For matching |
| `latitude` / `longitude` | REAL | WGS84 |
| `current_version_id` | INTEGER | FK → project_versions |
| `current_stage_type_id` | INTEGER | FK → vocabulary_stage_types |
| `created_at` / `updated_at` | TEXT | Provenance |

### v2: `berkeley_housing_v2.db.permits` (17 columns)

| column | type | notes |
|---|---|---|
| `id` | INTEGER | PK |
| `project_id` | INTEGER | FK → projects |
| `permit_number` | TEXT | e.g., `B2021-02225` |
| `permit_type_id` / `permit_status_type_id` | INTEGER | FK → vocabulary |
| `filed_date` / `issued_date` / `finaled_date` / `expires_date` | TEXT | Dates (filed: 119/244 populated; finaled: 60/244) |
| `valuation` | REAL | Job valuation |
| `source_url` / `description` / `notes` | TEXT | |
| `source_system` / `source_permit_id` | TEXT | Provenance |

### v2: `berkeley_housing_v2.db.project_geometries`

| column | type | notes |
|---|---|---|
| `id` | INTEGER | PK |
| `project_id` | INTEGER | FK |
| `geometry_type_id` | INTEGER | FK → vocabulary (8 types: apn_parcel, building_footprint, manual_polygon, synthetic_footprint, etc.) |
| `geojson` | TEXT | GeoJSON polygon, `[lon, lat]` order |
| `height_meters` / `base_elevation_meters` | REAL | |
| `is_current` | INTEGER | 1 if active version |
| `superseded_by` | INTEGER | FK to replacement geometry |
| Provenance mixin: `source_document_id`, `asserted_by`, `asserted_at`, `confidence_type_id` | | |

### `berkeley.db.parcels` (Alameda County source)

| column | type | notes |
|---|---|---|
| `APN` | TEXT | Format: `16-1428-2-2` |
| `SitusAddre` | TEXT | Situs address (truncated ArcGIS name) |
| `the_geom` | TEXT | GeoJSON geometry |
| `Latitude` / `Longitude` | TEXT | Stored as text, needs cast |

### HCD CKAN `table_a2` (mirrored at `databases/hcd_apr_mirror.db`)

70 columns mirroring HCD's APR Table A2 spec exactly. Key columns:

- Identity: `JURIS_NAME`, `CNTY_NAME`, `YEAR`, `APN`, `STREET_ADDRESS`, `JURS_TRACKING_ID`, `UNIT_CAT`, `TENURE`
- Entitlement income breakdown: `*_INCOME_DR`/`*_INCOME_NDR` for 7 income tiers + `ABOVE_MOD_INCOME`, plus `ENT_APPROVE_DT1`
- BP income breakdown: `BP_*` parallel set + `BP_ISSUE_DT1`
- CO income breakdown: `CO_*` parallel set + `CO_ISSUE_DT1`
- Misc HCD fields: `APPROVE_SB35`, `DENSITY_BONUS_*`, `EXTR_LOW_INCOME_UNITS`, `INFILL_UNITS`, `DEM_DES_UNITS`, etc.
- HCD-geocoded: `LATITUDE`, `LONGITUDE`, `STD_ADDRESS`, `SCORE`

All columns stored as TEXT; caller-side numeric casting required.

**Known quirks:**
- HCD's column-name typo: `EXTREMELY_INCOME_NDR` (missing "LOW") — handle this in any unit-summation logic
- Table I has `JURISDICITON` (HCD's typo for `JURISDICTION`)
- Table F has `JURISDICTION_NAME` (not `JURISDICTION`)

---

*End of PROGRESS.md — Regenerate by re-running the resumption checklist after substantive work.*
