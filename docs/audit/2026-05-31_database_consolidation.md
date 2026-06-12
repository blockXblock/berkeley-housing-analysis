# Database Inventory & Consolidation Analysis — 2026-05-31

**Scope:** Read-only diagnostic of all SQLite databases on the internal drive
(`~/berkeley-data` + sibling dirs). No database modified, moved, or deleted.
Does not touch external drives or the running Toshiba copy.

**Motive:** The April 2026 architecture review counted **12** databases; disk
reality is **39** — a 3.25× drift to explain and resolve into keep/merge/retire.

---

## The single most important finding

**The "39 databases" is not 39 schemas — it's ~6 canonical databases plus 21
dated backup snapshots and a handful of duplicate/derived exports.** The 12→39
drift is almost entirely **backup-snapshot hygiene** (every pre-change checkpoint
in May left a timestamped `.db` behind: 9 `berkeley_housing_v2_*`, 5
`cic_recon_queue*`, 3 `databases/backups/*`, 2 `analysis_pre_*`), **not
architectural sprawl.** Secondary finding: the **v2 normalized schema — declared
"abandoned" on Apr 30 — is in fact materialized and active** (45 tables, grown
from the 34-table design).

---

## Stage 1 — Enumeration (39 confirmed)

| Location | Count | What |
|---|---|---|
| `databases/` | 29 | canonical + 9 v2 snapshots + 5 cic snapshots + 0-byte berkeley_v2.db |
| `databases/backups/` | 3 | pre-change snapshots (May 19) |
| `berkeley-data/` (scattered) | 5 | business_licenses.db, data/processed/pipeline.db, data/outreach/outreach.db, 2× berkeleyshops-audience |
| `datasette-deploy/` | 2 | live Datasette copies (map + address_centric) |

All gitignored except `data/outreach/outreach.db` (tracked). Sibling dirs
(`~/berkeley_data`, `~/berkeley-data-staging`, etc.) contained **no** `.db` files.

## Stage 3 — Producers/consumers (script references)

Active (referenced by code): `berkeley_housing_analysis.db` (20),
`berkeley_housing_v2.db` (14), `cic_recon_queue.db` (12), `hcd_apr_mirror.db` (5),
`outreach.db` (2). **Everything else has zero script references** — backups,
snapshots, `berkeley_data.db`, `berkeley_address_centric.db`,
`berkeley_energy_use.db`, prototypes — all orphaned at the code level.

## Stage 4 — Mysteries resolved

- **(a) v2 schema:** materialized in `berkeley_housing_v2.db` — 45 tables / 9
  views / 72 indexes / 20 vocab tables / 2 audit tables. Exceeds the 34-table
  design (organic growth, per PROGRESS.md). *Idx note: 72 counts auto-indexes;
  PROGRESS's "46" likely counts explicit `CREATE INDEX` only.*
- **(b) berkeley_v2.db:** 0 bytes, no producer/consumer, gitignored → orphaned
  empty file from a likely wrong-path connect. **RETIRE.**
- **(c) live Datasette** (`berkeley-housing.fly.dev`): serves
  `datasette-deploy/berkeley_housing_map.db` + `berkeley_address_centric.db`
  (Dockerfile CMD). Both **stale (Mar 30)** — refresh-from-canonical needed.
  *(Separately, `berkeleybuild.com` GitHub Pages is static `explorer_data.js`
  generated from the analysis/v2 DBs — a different public surface.)*

---

## Stage 5 — Consolidation recommendation (all 39)

### KEEP — canonical / active (6)

| DB | Size | tables/rows | Producer→Consumer | Why |
|---|---|---|---|---|
| `databases/berkeley.db` | 52M | 17 / 193,871 | reference | Master parcel/address/license authority + FTS |
| `databases/berkeley_housing_v2.db` | 2.0M | 45 / 6,408 | v2 scripts (14) | Materialized normalized pipeline — emerging canonical |
| `databases/berkeley_housing_analysis.db` | 1.2M | 10 / 5,000 | analysis scripts (20) | v1 pipeline, still load-bearing; phasing into v2 |
| `databases/hcd_apr_mirror.db` | 1.4M | 8 / 3,080 | build_hcd_mirror (5) | HCD oracle (table_a/a2/d) |
| `databases/cic_recon_queue.db` | 200K | 4 / 411 | recon scrapers (12) | Active reconciliation/scrape queue |
| `data/outreach/outreach.db` | 61K | 7 / 177 | outreach scripts (2) | Contacts; git-tracked |

### KEEP — deployment / derived (3)

| DB | Size | Note |
|---|---|---|
| `datasette-deploy/berkeley_housing_map.db` | 458K | **LIVE** Datasette source — but STALE (Mar 30); refresh |
| `datasette-deploy/berkeley_address_centric.db` | 14M | **LIVE** Datasette source — STALE; holds unique `news_coverage` (2,024) |
| `databases/berkeley_address_centric.db` | 14M | Build master for the above; materialized but holds news_coverage |

### KEEP — intentional archival (3)

| DB | Size | Note |
|---|---|---|
| `databases/berkeley_housing_apr.db` | 84K | Frozen APR regulatory snapshot (don't update) |
| `databases/keep_snapshot_cic_recon_queue_2026-05-23.db` | 200K | `keep_snapshot` = deliberate keep |
| `databases/keep_snapshot_pre_inspection_ingest_2026-05-23.db` | 2.0M | `keep_snapshot` = deliberate keep (v2 state) |

### KEEP — separate project (1)

| DB | Size | Note |
|---|---|---|
| `berkeleyshops-audience/audience.db` | 340K | Mailchimp audience (1,610) — different project, out of housing scope |

### MERGE — into `berkeley.db` (3)

| DB | Size | Folds into | Reasoning |
|---|---|---|---|
| `databases/berkeley_data.db` | 4.1M | berkeley.db.licenses | business_licenses(13,004) already in berkeley.db |
| `business_licenses.db` (root) | 4.1M | berkeley.db.licenses | licenses(12,882) — third copy of the same data |
| `databases/berkeley_energy_use.db` | 176K | berkeley.db | BESO building_energy(520) — standalone civic dataset, no refs |

### INVESTIGATE (2)

| DB | Size | Question |
|---|---|---|
| `data/processed/pipeline.db` | 139K | projects(163) matches deployed map.db — build intermediate or stale (Mar 31)? Likely regenerable→retire |
| `databases/accela_reports.db` | 288K | Accela staging w/ empty tables (Mar 20); superseded by cic_recon_queue workflow? |

### RETIRE (21)

| Group | DBs | Reasoning |
|---|---|---|
| Empty | `berkeley_v2.db` | 0 bytes, orphaned |
| Superseded prototypes | `housing_projects.db` (84), `berkeley_housing_map.db` (84, old) | replaced by current pipeline/deploy |
| Stale project archive | `berkeleyshops-audience/archive/audience_2026-03-12.db` | superseded by audience.db |
| **v2 snapshots (9)** | `berkeley_housing_v2_{apr22_baseline, pre_cpra_import, pre_description_backfill, pre_fees, pre_recon, after_date_fixes, after_fix_a, before_permit_role_5cat, pre_kml_import}.db` | dated pre-change checkpoints; superseded by live v2 + 2 keep_snapshots |
| analysis snapshots (2) | `berkeley_housing_analysis_pre_{parcel_import, schema_alignment}_2026-04-25.db` | pre-change checkpoints |
| `databases/backups/` (3) | `*_pre_2352shattuck_*`, `*_pre_classification_*` | pre-change checkpoints (May 19) |
| cic snapshots (3) | `cic_recon_queue_pre_{15_b_permits, inspection_run, url_discovery}_2026-05-22.db` | pre-change checkpoints |

---

## Summary

| Disposition | Count |
|---|---|
| **KEEP** | 13 (6 canonical + 3 deploy/derived + 3 archival + 1 separate-project) |
| **MERGE** | 3 (→ berkeley.db) |
| **INVESTIGATE** | 2 |
| **RETIRE** | 21 (17 backup/snapshots + 4 empty/superseded) |

### Proposed end-state (the consolidated set)

A **5-database core**, matching the PROGRESS.md architecture:
1. `berkeley.db` — parcel/address/license/energy authority (after MERGE of 3)
2. `berkeley_housing_v2.db` — normalized pipeline (absorbing v1 analysis.db over time)
3. `hcd_apr_mirror.db` — HCD oracle
4. `cic_recon_queue.db` — working reconciliation queue
5. `outreach.db` — contacts (tracked)

Plus: 2 Datasette deploy copies (**refresh from canonical**), 3 intentional
archival snapshots, 1 separate-project DB. Retiring 21 reclaims clutter and
removes the snapshot ambiguity. **`berkeley_housing_analysis.db` (v1) stays until
v2 fully absorbs it** — both export scripts (`export_explorer_data.py` v1 and
`_v2`) still exist, so the migration is mid-flight.

### Caveats (not smoothed)
- Dispositions are evidence-based (size, schema, refs, dates), **not** an
  instruction to delete — consolidation actions need explicit go-ahead.
- "Backups → RETIRE" assumes the live DB + 2 keep_snapshots suffice; confirm
  none of the 17 snapshots holds a state you want frozen before deleting.
- INVESTIGATE items (pipeline.db, accela_reports.db) need John's knowledge of
  whether they're live build steps.
- v1→v2 cutover is the real open architectural decision, beyond this inventory.

*Diagnostic only. Uncommitted — review before commit.*
