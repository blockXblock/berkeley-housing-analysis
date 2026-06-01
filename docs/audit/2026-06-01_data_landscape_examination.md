# Data Landscape Examination — 2026-06-01

**Read-only, fact-gathering only.** Complete inventory of all data stores + raw-
source provenance across the main repo and three sibling directories. **No
dispositions decided, nothing merged/archived/deleted/ingested.** Every finding
shows its reproducing command. Reported per stage.

---

## SCOPE — four directories

Command:
```
for d in berkeley-data berkeley-data-staging berkeley-housing-research berkeley-permit-pipeline; do
  du -sh ~/$d; (cd ~/$d && git status -sb | head -1); find ~/$d -maxdepth 2 -mindepth 1; done
```

| Dir | Exists | Size | Git | Top-level character |
|---|---|---|---|---|
| `~/berkeley-data` | yes | **1.8 G** | repo, branch `dev`, **ahead of origin/dev by 1** | main project: `databases/`, `data/`, notebooks (00–05), `scripts/`, `analysis/`, `archive/`, `experiments/`, `berkeleyshops-audience/`, `business_licenses.db` |
| `~/berkeley-data-staging` | yes | **689 M** | **not a git repo** | `video/` (m4v tour clips), `pdf/` (APR PDFs, plan sets, transparency ordinance) — media only |
| `~/berkeley-housing-research` | yes | **427 M** | repo, branch `main`, up to date w/ origin | Quartz docs site: `content/`, `datasets/`, `quartz/`, `node_modules/`, `ClaudeCode_Claude_dialogue`, `APR/` |
| `~/berkeley-permit-pipeline` | yes | **596 K** | **not a git repo** | Obsidian vault: per-project `.md` notes (Sacramento/Shattuck/Durant/University), `ActiveLandUse_V1*.xlsx` (3 files), schema notes |

First read: DBs/raw permit data likely concentrate in `~/berkeley-data` (+ maybe
`berkeley-housing-research/datasets`); the other two siblings are media (staging)
and notes/xlsx (permit-pipeline). Stages 1 & 4 verify.

---

## Stage 1 — Database file inventory

Command:
```
find ~/{4 dirs} \( -iname '*.db' -o -iname '*.sqlite' -o -iname '*.sqlite3' \) \
  -not -path '*/node_modules/*' -not -path '*/.git/*' | sort
# per file: stat size/mtime; shasum -a 256; sqlite3 PRAGMA integrity_check
```

- **40 DB files total — ALL in `~/berkeley-data`. Zero `.db/.sqlite*` in the three sibling dirs.**
- **Integrity: 39 `ok`, 1 EMPTY** — `databases/berkeley_v2.db` (0 bytes, 2026-05-30).
- Locations: `databases/` (29), `databases/backups/` (3), scattered in repo (5: `business_licenses.db`, `data/outreach/outreach.db`, `data/processed/pipeline.db`, 2× `berkeleyshops-audience`), `datasette-deploy/` (2), `keep_snapshot_2026-06-01_pre-permit-fix.db` (1, new this session).
- `berkeley_housing_v2.db`: now 2,011,136 B, mtime **2026-06-01** (post permit-fix; sha `4ad50088…`).

### Exact-duplicate pairs (identical SHA-256)
| sha (first16) | files |
|---|---|
| `51cc0262371fa9cc` | `databases/berkeley_address_centric.db` ≡ `datasette-deploy/berkeley_address_centric.db` (deploy copy = source) |
| `6df7156c96be356f` | `keep_snapshot_2026-06-01_pre-permit-fix.db` ≡ `keep_snapshot_pre_inspection_ingest_2026-05-23.db` (v2 unchanged May23→Jun1 pre-fix) |
| `b5666b0c37057483` | `cic_recon_queue.db` ≡ `keep_snapshot_cic_recon_queue_2026-05-23.db` (queue unchanged since May23) |
| `c8166db410e3f05d` | `databases/berkeley_housing_analysis.db` ≡ `backups/…analysis_pre_2352shattuck_20260519…` (v1 frozen) |
| `e8a301191e5fa719` | `…v2_before_permit_role_5cat_2026-05-15` ≡ `backups/…v2_pre_2352shattuck_20260519…` (identical v2 snapshots) |

Full per-DB rows (size/mtime/sha/integrity) are in the Stage 9 master table.

---

## Stage 2 — Schema fingerprint + family grouping

Command:
```
# per non-empty DB:
sqlite3 "$f" "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY name" | shasum -a256   # schema hash
# family by signature tables (project_versions+unit_program=V2; projects+permit_events=V1; parcels_arcgis=PARCEL; active_zoning=ACCELA)
```

| Family | Count | Members (abridged) |
|---|---|---|
| **OTHER** | 17 | address_centric (×2), berkeley_data, energy, housing_apr, housing_map, hcd_apr_mirror, cic_recon_queue (×5), outreach, audience (×2), business_licenses, housing_projects |
| **V2-NORMALIZED** | 14 | live `berkeley_housing_v2.db` + 11 dated v2 snapshots + 2 keep_snapshots |
| **V1-FLAT** | 6 | `berkeley_housing_analysis.db` (+backup, 2 pre-* snapshots), `data/processed/pipeline.db`, `datasette-deploy/berkeley_housing_map.db` |
| **PARCEL** | 1 | `berkeley.db` (Alameda assessor, 17 tables) |
| **ACCELA-REPORTS** | 1 | `accela_reports.db` (10 tables) |

**Identical-schema groups** (same schema hash; content compared in Stage 3):
- `2360b635…` — 6 v2 snapshots (45-table schema, May 13–21)
- `b8b39579…` — `keep_snapshot_2026-06-01_pre-permit-fix` ≡ `keep_snapshot_pre_inspection_ingest_2026-05-23` (45-table, **pre-permit-fix v2 schema**)
- `432b7ce2…` (2) and `15816c60…` (2) — earlier 43-table v2 schemas
- `b7bf7cc1…` — analysis.db ≡ its backup (V1)
- `a4605d53…`, `5b2d6a33…` — cic_recon_queue live/snapshots
- `fa3d911a…` — address_centric ≡ deploy copy

**Key finding:** the **live `berkeley_housing_v2.db` schema hash (`5e988c8…`) is unique** — it diverged from all 45-table snapshots because this session's permit-fix modified the `v_projects_flat` view (the `NOT EXISTS` subsidiary exclusion). Confirms the schema change is present in the live DB and absent from every snapshot.

---

## Stage 3 — Content fingerprint (within family)

Command:
```
# V2: SELECT COUNT(*) projects; COUNT(*) project_events; from v_projects_flat: COUNT, SUM(total_units), COUNT(co_issued_date)
#     content hash = shasum of `SELECT project_id,total_units,status_label,co_issued_date FROM v_projects_flat ORDER BY project_id`
# V1: projects COUNT, SUM(units), COUNT(co_date); hash of `SELECT id,units,status FROM projects ORDER BY id`
```

### V2-NORMALIZED (content side-by-side)
| DB | proj | events | units | CO | content-hash |
|---|---|---|---|---|---|
| **`berkeley_housing_v2.db` (live)** | 181 | 2453 | 14071 | **20** | `857cadfb…` (unique) |
| `…apr22_baseline` (Apr 22) | 174 | 2605 | 12718 | 15 | `865efa7e…` |
| `…pre_cpra_import` (May 11) | 179 | 2611 | 14071 | 15 | `e1adef1c…` |
| `…pre_fees` (May 12) | 181 | 2787 | 14071 | 41 | `33e26de1…` |
| `…after_date_fixes` (May 13) | 181 | 2787 | 14071 | 41 | `e5d69954…` |
| `…before_permit_role_5cat` (May 15) | 181 | 2340 | 14071 | 41 | `270d5791…` |
| `…pre_kml_import` (May 21) | 181 | 2347 | 14071 | 40 | **`430b2691…`** |
| `keep_snapshot_pre_inspection_ingest` (May 23) | 181 | 2347 | 14071 | 40 | **`430b2691…`** |
| `keep_snapshot_2026-06-01_pre-permit-fix` | 181 | 2347 | 14071 | 40 | **`430b2691…`** |

- **Lineage:** 174 proj (Apr 22) → 179 (May 11) → **181/14071 units stable from May 12 on**. CO-date count: 15 → 41 → 40 → **20 (live, post permit-fix)**.
- **3 states are content-identical** (`430b2691…`): May 21 = May 23 = my Jun 1 pre-fix snapshot → **v2 content was unchanged May 21 → Jun 1 (pre-fix)**.
- **Live v2 is uniquely divergent** — CO count 40→20, the permit-fix subsidiary exclusion. (No canonical judgment — numbers only.)

### V1-FLAT
| DB | proj | units | CO | content-hash |
|---|---|---|---|---|
| `berkeley_housing_analysis.db` | 179 | 14070 | 15 | `694df172…` |
| `…analysis_pre_parcel_import` (Apr 25) | 174 | 12717 | 15 | **`7136a5a6…`** |
| `…analysis_pre_schema_alignment` (Apr 25) | 174 | 12717 | 15 | **`7136a5a6…`** |
| `data/processed/pipeline.db` | 163 | (no units col) | — | (empty) |
| `datasette-deploy/berkeley_housing_map.db` | 163 | 10223 | 6 | `725cdb2a…` |

- The two Apr-25 V1 backups are **content-identical** (`7136a5a6…`).
- V2 live (181 / 14071 u) vs V1 `analysis.db` (179 / 14070 u): v2 = +2 projects, +1 unit (the known +2).

### PARCEL — `berkeley.db`
`parcels=29024; distinct apn_norm=29003; addresses_arcgis=65459`

---

## Stage 4 — Raw Accela/permit source files (the substrate)

Command:
```
find ~/{4 dirs} -iname '*FINAL*.csv'   # source-of-truth
find ~/berkeley-data/data/raw -type d   # scrape subtrees
find ... -iname '*.xlsx' | grep -iE 'permit|annual|cpra|landuse'
```

| Group | Location | Count / size | Coverage | Structure |
|---|---|---|---|---|
| **Per-permit Accela status dumps** | `data/raw/accela_status/` | **157 `.txt`, 1.4 M** | mtime 2026-03-22 → 05-16 | per-permit text, e.g. `ZP2022-0019_2555_COLLEGE_Ave.txt` (`=== PLANNING PERMIT ===` / `PERMIT:` / `ADDRESS:`) |
| Other Accela subtrees | `data/raw/{accela_record_status, accela_processing_status, accela_inspections, accela_research, accela_url_discovery}` | part of 165 `.txt` total in `data/raw` | — | scrape variants |
| Corridor scans | `data/raw/corridor_scans/` | 8 `.txt`, 60 K | — | corridor-level scans |
| **FINAL.csv — v1 canonical hand-curated input** | `data/processed/housing_projects_FINAL.csv` | **184 rows, 41 cols** | mtime 2026-04-11 | `id,address_display,apn,owner,net_units,…,slug,latitude,longitude,tenure,sb35_flag,…` |
| FINAL.csv backups (growth history) | `data/processed/`, `data/backups/` | ~14 dated backups | rows grow **104 (Feb 22) → 135 → 154 → 179 → 184** | snapshots of the curated list |
| **CPRA permit deliverables** | `data/raw/cpra-downloads/` | 2 `.xlsx`, **6.5 M** | 2018–2025, mtime 2026-05-27 | `BP_Annual Permit Report-{2023-2025, 2018-2022}.xlsx` (32,202 rows total — see prior CPRA verify) |
| Zoning ActiveLandUse exports | `zoning_reports/` (12) + **`berkeley-permit-pipeline/` (3)** | ~15 `.xlsx` | Dec 2025 – Mar 2026 | `ActiveLandUse_V1*.xlsx` / `LandUseStatus_V1*.xlsx` |

**Ambiguities / oddities flagged (read-only):**
- A backup named literally **`housing_projects_FINAL_backup_$(date +%Y%m%d_%H%M%S).csv`** (153 rows) — an **un-expanded shell variable** in the filename (a backup script bug). Not resolvable read-only beyond noting it.
- `data/raw` is 303 M but the `.txt` are only ~1.5 M — the bulk is non-text (videos/images in `tour_video/`, `google_earth_audit/`), not permit substrate.
- ActiveLandUse exports exist in **both** the main repo and the `berkeley-permit-pipeline` sibling (overlap assessed in Stage 7).

---

## Stage 5 — Data lineage (raw → script → table)

Command: `grep -rln <raw-file> scripts/ ; grep -noE 'INSERT INTO|to_sql|DB_PATH' <ingest-script>`

```
housing_projects_FINAL.csv  ──migrate_to_database.py──►  berkeley_housing_analysis.db (projects)
accela_status/*.txt         ──accela_workflow.py────────►  berkeley_housing_analysis.db (permit_events, building_permits, project_permits)
   (parsed by parse_timeline_data.py, parse_attachments.py, extract_fees.py, add_heights.py)
CPRA BP_Annual*.xlsx         ──cpra_dedup.py + import_cpra_2023_2025.py──►  berkeley_housing_v2.db (projects, project_events, parcels)
berkeley_housing_analysis.db ──migration/migrate_v1_to_v2.py──►  berkeley_housing_v2.db
CKAN/HCD APR                 ──build_hcd_mirror.py──────►  hcd_apr_mirror.db   [VERIFICATION TARGET, not a source]
```

So the canonical-candidate `berkeley_housing_v2.db` lineage = **FINAL.csv + Accela `.txt` scrapes → V1 → migrated to V2, then enriched by CPRA xlsx**. All primary-source; `hcd_apr_mirror.db` is fed by CKAN purely as the comparison target.

**Un-ingested raw files (captured, no production script loads them):**
- **`ActiveLandUse_V1*.xlsx` / `LandUseStatus_V1*.xlsx`** (zoning exports, ~15 files) — read **only by exploratory notebooks** (`permitpipeline.ipynb`, `MASTER_ANALYSIS.ipynb`), **not ingested into any DB by a script**. The scan-level analogue of the un-ingested ADU data. *(Listed, not ingested.)*
- **Cannot determine read-only** whether all 157 `accela_status/*.txt` were individually ingested vs partially — `accela_workflow.py save_batch` processes a directory, but per-file coverage isn't verifiable without running it. Flagged as an ambiguity.

---

## Stage 6 — Usage map (which DB the live outputs open)

Command: `grep -nE "DB_PATH|connect\(" <script>`

| Consumer | Opens | Writes/Reads |
|---|---|---|
| `migrate_to_database.py`, `accela_workflow.py`, `generate_apr.py`, `generate_kml.py` | `berkeley_housing_analysis.db` (V1) | read+write |
| `import_cpra_2023_2025.py`, `generate_apr_v2.py`, `export_explorer_data_v2.py` | **`berkeley_housing_v2.db`** (V2) | read (v2) / write (cpra import) |
| `build_hcd_mirror.py` | `hcd_apr_mirror.db` | write (CKAN) |
| Datasette deploy (Dockerfile) | `datasette-deploy/{berkeley_housing_map, berkeley_address_centric}.db` | serve |
| Live `docs/explorer_data.js` | produced by `export_explorer_data_v2.py` from **`berkeley_housing_v2.db`** | (per prior explorer-cutover audit: committed `52b87c0`, May 13) |

**Orphans (referenced by NO script — from prior consolidation analysis):** `berkeley_data.db`, `berkeley_energy_use.db`, `housing_projects.db`, `berkeley_housing_map.db` (the old 84-row one), `business_licenses.db`, `pipeline.db`, the `berkeleyshops-audience` DBs, and all dated `*_pre_*` / backup snapshots. (Disposition deferred — not judged here.)

---

## Stage 7 — Sibling-directory assessment

Command: per sibling, inventory + `shasum -a256` compare vs `~/berkeley-data`.

**`~/berkeley-permit-pipeline`** (596 K, **not a git repo**, loose Obsidian vault) —
*appears to hold UNIQUE data worth examining further:*
- 12 Obsidian project-research `.md` notes (`2029 University.md`, `Repository of Project Data.md`, `Database Schema for Permit Numbers.md`, `How to capture Project Data.md`), mtime **2026-02-23 → 03-04 (stale)**.
- `ActiveLandUse_V1_2026_3_19.xlsx` is **checksum-UNIQUE** (same byte size as `zoning_reports/2026_03_19_ActiveLandUse_V1.xlsx` but a different hash — not a duplicate).

**`~/berkeley-housing-research`** (427 M, **git repo `main`, synced to origin**) —
*appears to hold UNIQUE documentation:*
- 19 Quartz `content/*.md` (mtime 2026-01-23 → 02-22, stale), `ClaudeCode_Claude_dialogue/` (design-decision transcripts), `APR/`. Not present in `berkeley-data/docs` by name.
- **Cannot determine read-only:** `datasets/` listed empty (or unreadable in sandbox); `du` on subtrees returned blank (sandbox). The 427 M is dominated by regenerable `node_modules/`.

**`~/berkeley-data-staging`** (689 M, **not a git repo**, loose media) —
*appears to hold UNIQUE large source media:*
- 13 files: APR PDFs (`2023-03-29-APR2022.pdf` 5.8 M, `…Packet.pdf`, `…Reports.pdf`) and a **142 MB `Shattuck.pdf` plan set** (the 2190 Shattuck architectural drawings — matches the Apr-30 cross-directory survey's "141 MB plan set"). mtime 2026-04-13 → 05-01.
- These are large primary documents; not duplicated in `berkeley-data` by size/checksum. *Per-file checksum vs every berkeley-data file not exhaustively run — but distinctive sizes indicate uniqueness.*

**Plain statements (per the brief):**
- permit-pipeline → **unique** (project notes + a unique ActiveLandUse export); loose files, stale.
- housing-research → **unique** (Quartz docs + Claude dialogues); active git repo, content stale; `datasets/` undeterminable read-only.
- staging → **unique** (APR PDFs + 142 M plan set); loose media, stale.
- **No DBs in any sibling** (Stage 1). Nothing pulled in or archived — assessment only.

---

## Stage 8 — Reconcile against the prior 39-DB analysis

Command: `diff` current `dblist.txt` (40) vs basenames in `2026-05-31_database_consolidation.md` (39).

- **Net change since the prior doc: +1.** Prior = 39 DBs; now = 40.
- **The single genuinely-new file = `databases/keep_snapshot_2026-06-01_pre-permit-fix.db`** (mtime 2026-06-01) — created **this session** before the permit-fix.
- **No dispositions were EXECUTED.** Every RETIRE/MERGE candidate from the prior doc still exists on disk (`housing_projects.db`, `berkeley_housing_map.db`, `berkeley_data.db`, `…apr22_baseline.db`, the 0-byte `berkeley_v2.db`, etc.). The prior doc's KEEP 13 / MERGE 3 / INVESTIGATE 2 / RETIRE 21 were **recommendations only**.
- **In-place modification:** the live `berkeley_housing_v2.db` changed (permit-fix) — same path, new sha/schema/content (Stages 1–3).
- *Reconciliation note:* a name-by-name grep flagged 18 DBs as "not in prior doc," but those are **aggregate-naming artifacts** — the prior doc enumerated the v2/cic snapshots and `backups/` in groups, not individually. Cross-referenced to its group counts, all 39 are accounted for; only the June-1 snapshot is new.
- **Raw-file layer is new to this examination:** the prior doc was DB-only. The FINAL.csv lineage, the 157 Accela `.txt` scrapes, the CPRA `.xlsx`, and the ActiveLandUse exports (Stages 4–5) were not inventoried there.

---

## Stage 9 — Master table + factual summary (no judgments)

### Master DB table (all 40; `used?` = referenced by ≥1 production script)

| path | size (B) | mtime | sha8 | integ | family | tbls | used? |
|---|---|---|---|---|---|---|---|
| berkeleyshops-audience/archive/audience_2026-03-12.db | 327,680 | 2026-03-12 | 3f9e62a8 | ok | OTHER | 1 | · |
| berkeleyshops-audience/audience.db | 339,968 | 2026-03-12 | 25000b6c | ok | OTHER | 1 | · |
| business_licenses.db | 4,153,344 | 2026-05-02 | 5aeec946 | ok | OTHER | 1 | · |
| data/outreach/outreach.db | 61,440 | 2026-04-04 | 6092836e | ok | OTHER | 7 | Y |
| data/processed/pipeline.db | 139,264 | 2026-03-31 | 61e8e076 | ok | V1-FLAT | 4 | · |
| db/accela_reports.db | 294,912 | 2026-03-20 | 765c0553 | ok | ACCELA-REPORTS | 10 | Y |
| db/backups/…analysis_pre_2352shattuck_20260519 | 1,183,744 | 2026-05-19 | c8166db4 | ok | V1-FLAT | 10 | · |
| db/backups/…v2_pre_2352shattuck_20260519 | 1,892,352 | 2026-05-19 | e8a30119 | ok | V2-NORMALIZED | 45 | · |
| db/backups/…v2_pre_classification_20260519 | 1,892,352 | 2026-05-19 | 13cd9d1d | ok | V2-NORMALIZED | 45 | · |
| **db/berkeley.db** | 52,449,280 | 2026-03-19 | 44244ba2 | ok | PARCEL | 17 | **Y** |
| db/berkeley_address_centric.db | 14,610,432 | 2026-02-27 | 51cc0262 | ok | OTHER | 4 | Y |
| db/berkeley_data.db | 4,296,704 | 2025-11-15 | 27baf30f | ok | OTHER | 1 | · |
| db/berkeley_energy_use.db | 180,224 | 2026-01-06 | 35b59018 | ok | OTHER | 1 | · |
| **db/berkeley_housing_analysis.db** | 1,183,744 | 2026-05-03 | c8166db4 | ok | V1-FLAT | 10 | **Y** |
| db/…analysis_pre_parcel_import_2026-04-25.db | 1,048,576 | 2026-04-25 | 7e223a8d | ok | V1-FLAT | 8 | · |
| db/…analysis_pre_schema_alignment_2026-04-25.db | 1,155,072 | 2026-04-25 | e0eb4719 | ok | V1-FLAT | 10 | · |
| db/berkeley_housing_apr.db | 86,016 | 2026-02-22 | c2bd4366 | ok | OTHER | 1 | · |
| db/berkeley_housing_map.db | 57,344 | 2025-12-22 | d934dd10 | ok | OTHER | 1 | Y |
| **db/berkeley_housing_v2.db** | 2,011,136 | **2026-06-01** | 4ad50088 | ok | V2-NORMALIZED | 45 | **Y** |
| db/…v2_after_date_fixes_2026-05-13.db | 1,892,352 | 2026-05-13 | eab35623 | ok | V2-NORMALIZED | 45 | · |
| db/…v2_after_fix_a_2026-05-13.db | 1,892,352 | 2026-05-13 | 1aa3c1d8 | ok | V2-NORMALIZED | 45 | · |
| db/…v2_apr22_baseline.db | 1,515,520 | 2026-05-07 | 608c7e68 | ok | V2-NORMALIZED | 40 | · |
| db/…v2_before_permit_role_5cat_2026-05-15.db | 1,892,352 | 2026-05-15 | e8a30119 | ok | V2-NORMALIZED | 45 | · |
| db/…v2_pre_cpra_import_2026-05-11.db | 1,630,208 | 2026-05-11 | 08ae9a8b | ok | V2-NORMALIZED | 43 | · |
| db/…v2_pre_description_backfill_2026-05-12.db | 1,683,456 | 2026-05-12 | 8c8c40b7 | ok | V2-NORMALIZED | 43 | · |
| db/…v2_pre_fees_2026-05-12.db | 1,732,608 | 2026-05-12 | 314de9d2 | ok | V2-NORMALIZED | 43 | · |
| db/…v2_pre_kml_import_2026-05-21.db | 1,892,352 | 2026-05-21 | 97d978b6 | ok | V2-NORMALIZED | 45 | · |
| db/…v2_pre_recon_2026-05-12.db | 1,724,416 | 2026-05-12 | 2430f27d | ok | V2-NORMALIZED | 43 | · |
| **db/berkeley_v2.db** | **0** | 2026-05-30 | (0-byte) | **EMPTY** | EMPTY | 0 | · |
| **db/cic_recon_queue.db** | 200,704 | 2026-05-23 | b5666b0c | ok | OTHER | 4 | **Y** |
| db/cic_recon_queue_pre_15_b_permits_2026-05-22.db | 86,016 | 2026-05-22 | e2df0939 | ok | OTHER | 2 | · |
| db/cic_recon_queue_pre_inspection_run_2026-05-22.db | 61,440 | 2026-05-22 | 6cc8416c | ok | OTHER | 2 | · |
| db/cic_recon_queue_pre_url_discovery_2026-05-22.db | 32,768 | 2026-05-22 | 2efdbab7 | ok | OTHER | 1 | · |
| **db/hcd_apr_mirror.db** | 1,437,696 | 2026-05-26 | 959a110d | ok | OTHER | 8 | **Y** *(verify target)* |
| db/housing_projects.db | 61,440 | 2025-12-14 | bdeeca14 | ok | OTHER | 1 | · |
| db/keep_snapshot_2026-06-01_pre-permit-fix.db | 1,994,752 | **2026-06-01** | 6df7156c | ok | V2-NORMALIZED | 45 | · (new this session) |
| db/keep_snapshot_cic_recon_queue_2026-05-23.db | 200,704 | 2026-05-23 | b5666b0c | ok | OTHER | 4 | · |
| db/keep_snapshot_pre_inspection_ingest_2026-05-23.db | 1,994,752 | 2026-05-23 | 6df7156c | ok | V2-NORMALIZED | 45 | · |
| datasette-deploy/berkeley_address_centric.db | 14,610,432 | 2026-02-27 | 51cc0262 | ok | OTHER | 4 | Y |
| datasette-deploy/berkeley_housing_map.db | 458,752 | 2026-03-30 | acc0b7dc | ok | V1-FLAT | 4 | Y |

### Factual rollup
- **0-byte / corrupt:** 1 — `db/berkeley_v2.db` (0 bytes; integrity EMPTY). No corrupt DBs; 39/40 `integrity_check=ok`.
- **Exact-duplicate file pairs (sha256):** 5 — see Stage 1 (address_centric≡deploy; snapshot pairs; analysis≡backup; two identical v2 snapshots).
- **Content-identical despite different filenames:** v2 states `pre_kml`(May21) ≡ `keep_snapshot_pre_inspection`(May23) ≡ `keep_snapshot_2026-06-01_pre-permit-fix` (content hash `430b2691…`, Stage 3).
- **Schema families:** OTHER 17 · V2-NORMALIZED 14 · V1-FLAT 6 · PARCEL 1 · ACCELA-REPORTS 1 (Stage 2).
- **Usage-orphans (no script):** all `*_pre_*`/backup snapshots, `berkeley_data.db`, `berkeley_energy_use.db`, `housing_projects.db`, `berkeley_housing_apr.db`, audience (×2), `business_licenses.db`, `pipeline.db`, the 0-byte `berkeley_v2.db` (Stage 6).
- **Un-ingested raw files:** `ActiveLandUse_V1*.xlsx`/`LandUseStatus_V1*` (read only by notebooks); 157 Accela `.txt` per-file ingestion not verifiable read-only (Stage 5).
- **Lineage:** FINAL.csv + Accela `.txt` → V1 (`migrate_to_database.py`, `accela_workflow.py`); CPRA `.xlsx` → V2 (`import_cpra…`); V1→V2 migration; CKAN→`hcd_apr_mirror` (verify target) (Stage 5).
- **Siblings:** all three hold **unique non-DB content** (permit-pipeline notes+1 unique xlsx; housing-research Quartz docs+dialogues; staging APR PDFs+142 M plan set); **no DBs** in any (Stage 7).
- **New since prior analysis:** +1 DB (`keep_snapshot_2026-06-01_pre-permit-fix.db`); live v2 modified in place; no dispositions executed (Stage 8).

### Ambiguities unresolved read-only
1. Per-file ingestion status of the 157 `accela_status/*.txt` (would require running `accela_workflow.py`).
2. `berkeley-housing-research/datasets/` listed empty / `du` blank in sandbox — content undetermined.
3. The `housing_projects_FINAL_backup_$(date…)` filename (literal un-expanded variable) — origin script not pinned down.
4. Exhaustive per-file checksum of sibling media vs `berkeley-data` not run (uniqueness inferred from distinctive sizes/names).

---
*Read-only examination. No merge/archive/delete/ingest/schema-change performed. No
keep/merge/retire/canonical decisions made — that is the separate next step.*








