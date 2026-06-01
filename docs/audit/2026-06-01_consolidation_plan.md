# Database Consolidation Plan — Phase 1 (PROPOSE) — 2026-06-01

**Read-only proposal. Nothing moved.** Turns the facts in
`2026-06-01_data_landscape_examination.md` into a reviewed disposition for all
40 DB files. **Phase 2 executes only the NOW batch**, after John approves this
table; the DEFERRED batch waits for a separate pass after the write-arc
(permit-fix `cb2ba32` + CPRA ADU ingestion) is pushed-stable.

## Split rule (per John, 2026-06-01)
- **NOW** = inert dead-weight with zero reversal-point value, untouched by the
  active write-arc → archive/retire in Phase 2.
- **DEFERRED** = reversal points / safety nets (all `*_pre_*` snapshots,
  `backups/`, keep_snapshots, incl. V1 analysis snapshots) → keep in place until
  the permit-fix + ADU ingestion are pushed-stable, then a later pass archives them.
- **KEEP-IN-PLACE** = canonical / special-purpose / operational → never archived.

## Archive layout (filesystem move inside `~/berkeley-data`; DBs are gitignored)
```
archive/
  retired/    # empty/corrupt
  orphans/    # stale, referenced by no production script
  snapshots/  # dated v2/v1 *_pre_* states  (DEFERRED pass)
  backups/    # databases/backups/* + keep_snapshots  (DEFERRED pass)
  README.md   # tracked in git; logs every move (see spec below)
```
- **`archive/*.db` stays gitignored** — `.gitignore:15 *.db` covers it
  (`git check-ignore` confirms `archive/snapshots/test.db` is ignored). The
  `archive/README.md` **is** tracked (the audit record).
- **Space note:** copy-then-remove momentarily doubles a file (~100 MB total
  across all DBs — trivial; this saga began with disk pressure, so noted).

---

## Disposition table — all 40 files

### KEEP-IN-PLACE (10) — never archived
| file | sha8 | family | disposition | evidence |
|---|---|---|---|---|
| `databases/berkeley_housing_v2.db` | 4ad50088 | V2-NORM | **CANONICAL-KEEP** | THE canonical housing DB; unique current schema+content hash; permit-fix landed here; read by `generate_apr_v2`/`export_explorer_data_v2` |
| `databases/berkeley.db` | 44244ba2 | PARCEL | **CANONICAL-KEEP** | Alameda assessor, 29,024 parcels; independent coords/geometry (`apn_norm`); licenses superset (13,004) |
| `databases/hcd_apr_mirror.db` | 959a110d | OTHER | **CANONICAL-KEEP** | CKAN **verification target** (never a source); used by comparison; label as verify-target |
| `databases/berkeley_housing_analysis.db` | c8166db4 | V1-FLAT | **CANONICAL-KEEP** | frozen V1 ancestor / migration provenance root; lineage |
| `databases/accela_reports.db` | 765c0553 | ACCELA | **CANONICAL-KEEP** | Accela staging; used |
| `databases/cic_recon_queue.db` | b5666b0c | OTHER | **CANONICAL-KEEP** | operational reconciliation queue; used |
| `databases/berkeley_address_centric.db` | 51cc0262 | OTHER | **SPECIAL-KEEP** | Datasette build-master (news_coverage etc.); paired with deploy copy |
| `datasette-deploy/berkeley_address_centric.db` | 51cc0262 | OTHER | **SPECIAL-KEEP** | served by Datasette (Dockerfile CMD reads this dir); not redundant — deploy needs its own copy |
| `datasette-deploy/berkeley_housing_map.db` | acc0b7dc | V1-FLAT | **SPECIAL-KEEP** | served by Datasette (163 rows); **FLAG: stale 2026-03-30, refresh from canonical** |
| `data/outreach/outreach.db` | 6092836e | OTHER | **SPECIAL-KEEP** | distinct outreach purpose (7 tables); used |

### ARCHIVE / RETIRE — **NOW batch (10)** — Phase 2 executes these
| file | sha8 | disposition | dest | evidence |
|---|---|---|---|---|
| `databases/berkeley_v2.db` | (0-byte) | **RETIRE** (do first) | `archive/retired/` | 0 bytes, EMPTY; **no script references it** (verified) |
| `databases/housing_projects.db` | bdeeca14 | ARCHIVE-orphan | `archive/orphans/` | prototype, Dec 2025, 1 table; no script ref |
| `databases/berkeley_housing_map.db` | d934dd10 | ARCHIVE-orphan | `archive/orphans/` | **old 84-row export; orphan confirmed** (Dockerfile serves the `datasette-deploy/` copy, not this path) |
| `databases/berkeley_energy_use.db` | 35b59018 | ARCHIVE-orphan | `archive/orphans/` | BESO 520 rows, Jan 2026; no script ref |
| `databases/berkeley_housing_apr.db` | c2bd4366 | ARCHIVE-orphan | `archive/orphans/` | frozen APR snapshot Feb 2026; no script ref |
| `berkeleyshops-audience/audience.db` | 25000b6c | ARCHIVE-orphan | `archive/orphans/` | separate (shops mailing) project; not housing |
| `berkeleyshops-audience/archive/audience_2026-03-12.db` | 3f9e62a8 | ARCHIVE-orphan | `archive/orphans/` | older copy of the above |
| `business_licenses.db` | 5aeec946 | ARCHIVE-orphan | `archive/orphans/` | 12,882 licenses ⊂ `berkeley.db.licenses` (13,004) — **superset confirmed** |
| `databases/berkeley_data.db` | 27baf30f | ARCHIVE-orphan | `archive/orphans/` | 13,004 business_licenses = `berkeley.db.licenses` — **data preserved in berkeley.db** |
| `data/processed/pipeline.db` | 61e8e076 | ARCHIVE-orphan | `archive/orphans/` | V1, 163 proj, Mar 2026; no production script ref |

### ARCHIVE — **DEFERRED batch (20)** — later pass, after write-arc pushed-stable
| file | sha8 | disposition | dest | evidence / reason deferred |
|---|---|---|---|---|
| `keep_snapshot_2026-06-01_pre-permit-fix.db` | 6df7156c | SNAPSHOT-KEEP→defer | `archive/backups/` | **reversal point for unpushed `cb2ba32`** — retain until pushed |
| `keep_snapshot_pre_inspection_ingest_2026-05-23.db` | 6df7156c | ARCHIVE (dup)→defer | `archive/backups/` | exact dup of the above; defer with the chain |
| `keep_snapshot_cic_recon_queue_2026-05-23.db` | b5666b0c | ARCHIVE (dup)→defer | `archive/backups/` | exact dup of live `cic_recon_queue.db` |
| `databases/backups/…analysis_pre_2352shattuck_20260519` | c8166db4 | ARCHIVE→defer | `archive/backups/` | exact dup of `analysis.db`; reversal point |
| `databases/backups/…v2_pre_2352shattuck_20260519` | e8a30119 | ARCHIVE→defer | `archive/backups/` | exact dup of `…before_permit_role_5cat` |
| `databases/backups/…v2_pre_classification_20260519` | 13cd9d1d | ARCHIVE→defer | `archive/backups/` | reversal point |
| `…v2_apr22_baseline.db` | 608c7e68 | ARCHIVE→defer | `archive/snapshots/` | earlier v2 (40-table) state |
| `…v2_pre_cpra_import_2026-05-11.db` | 08ae9a8b | ARCHIVE→defer | `archive/snapshots/` | prior v2 state |
| `…v2_pre_description_backfill_2026-05-12.db` | 8c8c40b7 | ARCHIVE→defer | `archive/snapshots/` | prior v2 state |
| `…v2_pre_fees_2026-05-12.db` | 314de9d2 | ARCHIVE→defer | `archive/snapshots/` | prior v2 state |
| `…v2_pre_recon_2026-05-12.db` | 2430f27d | ARCHIVE→defer | `archive/snapshots/` | prior v2 state |
| `…v2_after_date_fixes_2026-05-13.db` | eab35623 | ARCHIVE→defer | `archive/snapshots/` | prior v2 state |
| `…v2_after_fix_a_2026-05-13.db` | 1aa3c1d8 | ARCHIVE→defer | `archive/snapshots/` | prior v2 state |
| `…v2_before_permit_role_5cat_2026-05-15.db` | e8a30119 | ARCHIVE→defer | `archive/snapshots/` | prior v2 state |
| `…v2_pre_kml_import_2026-05-21.db` | 97d978b6 | ARCHIVE→defer | `archive/snapshots/` | prior v2 state (content = pre-fix snapshot) |
| `…analysis_pre_parcel_import_2026-04-25.db` | 7e223a8d | ARCHIVE→defer | `archive/snapshots/` | V1 snapshot (content-id w/ next) |
| `…analysis_pre_schema_alignment_2026-04-25.db` | e0eb4719 | ARCHIVE→defer | `archive/snapshots/` | V1 snapshot (`7136a5a6` content twin) |
| `cic_recon_queue_pre_15_b_permits_2026-05-22.db` | e2df0939 | ARCHIVE→defer | `archive/snapshots/` | queue reversal point |
| `cic_recon_queue_pre_inspection_run_2026-05-22.db` | 6cc8416c | ARCHIVE→defer | `archive/snapshots/` | queue reversal point |
| `cic_recon_queue_pre_url_discovery_2026-05-22.db` | 2efdbab7 | ARCHIVE→defer | `archive/snapshots/` | queue reversal point |

**HOLD-AMBIGUOUS: none remaining** — the `berkeley_housing_map.db` conflict was
resolved read-only (db/ path = orphan → NOW; deploy path = SPECIAL-KEEP).

---

## Count summary & before/after
| Category | Count |
|---|---|
| KEEP-IN-PLACE (canonical 6 + special 4) | 10 |
| ARCHIVE/RETIRE — **NOW** (1 retire + 9 orphan) | 10 |
| ARCHIVE — **DEFERRED** (reversal points) | 20 |
| **Total** | **40** |

- **After Phase 2 (NOW batch):** `databases/` etc. go **40 → 30 files in place**
  (10 KEEP + 20 DEFERRED still present), **10 moved to `archive/`**. Canonical
  `berkeley_housing_v2.db` untouched (`4ad50088`).
- **After the later DEFERRED pass** (post-push): 30 → **10 KEEP-IN-PLACE**, 30 archived.

## Phase 2 per-file procedure (NOW batch only; for John's method review)
```
1. mkdir -p archive/<retired|orphans>/
2. cp <file> archive/<dir>/           # copy first — original still in place
3. shasum -a256 <file> and the copy → MUST match; if mismatch, STOP
4. only on match: rm <original>       # verified twin now in archive/
   (0-byte berkeley_v2.db: sha of empty is deterministic; it has no refs → retire)
5. append to archive/README.md + console table: src, dest, sha256, ts
Order: (a) 0-byte RETIRE first (flow test) → (b) the 9 orphans.
Do NOT touch: any KEEP-IN-PLACE, any DEFERRED file, datasette-deploy/ copies.
```
After execution: re-run Stage-1 inventory (confirm 30 remain, the right ones);
grep production `DB_PATH`s (confirm nothing archived was referenced); confirm
canonical sha = `4ad50088`; write the executed log here; commit audit docs +
`archive/README.md`; **HOLD the push** for John.

## archive/README.md spec (carried with the archive)
Per archived file: original path, sha256, schema-family, origin (filename/git
log where determinable), why archived (orphan/empty/superseded), and the
recover line (`cp archive/<dir>/<file> <original-path>`). States plainly that
**every archived DB is a verified copy and fully recoverable**.

---
*Phase 1 only — nothing moved. Awaiting John's approval of this table before any
Phase 2 archive move. DEFERRED batch executes in a later pass after the
permit-fix + ADU ingestion are pushed-stable.*
