# Session coordination — this maps/data session ⇄ B2050BIS (Berkeley-2050 Bond Issue Support)

**Written:** 2026-08-14/15. **Why:** two Claude Code sessions are working the same repo on branch `dev` at the
same time — **B2050BIS** (bond-measure analysis + website) and **this session** (parcel data + interactive
maps). This is the agreed division of responsibility so we don't edit each other's files or clobber shared
state. John coordinates; either session should read this before touching a shared file.

---

## The seam: two layers, one interface

**This session owns the DATA + MAP layer. B2050BIS owns the ANALYSIS + CONTENT layer.** Neither edits the
other's files.

| Layer | Owner | Files (owner edits; other only reads) |
|---|---|---|
| Parcel data | **maps session** | `scripts/build_parcel_facts.py`, `databases/parcel_facts.db` |
| Maps / web visuals | **maps session** | `scripts/gen_bond_incidence.py`, `gen_yearbuilt_timelapse.py`, `gen_ownership_map.py`, `docs/maps/*` |
| Bond analysis / reconciliation | **B2050BIS** | `scripts/v4/build_jn_measure_u.py`, `notebooks/v4/JN-MeasureU.ipynb`, `data/baselines/measure_u_*.json` |
| Argument / site narrative / claims | **B2050BIS** | `notes/2026-08-15_bond_measure_u_*.md`, website copy |

## The interface — two contracts (derive, never hardcode across the boundary)

1. **Official figures flow B2050BIS → maps.** `data/baselines/measure_u_reconciliation_baseline_2026-08-15.json`
   is the **single source of truth** for every official/derived bond number (principal, `avg_rate_100k`
   22.14, `peak_rate_100k` 35, `rate_today_100k` 70.09, `base_avg_multiple` 2.37, debt service, tranches).
   **The map READS that file** and must never hardcode an official number. *Implemented 2026-08-15:*
   `gen_bond_incidence.py` now reads the baseline and offers a **rate toggle** (today's-base $70 / city peak
   $35 / city avg $22.14) with the base-growth reconciliation note — closing B2050BIS's §2 "Map TODO."
2. **Parcel facts flow maps → B2050BIS.** `databases/parcel_facts.db` (built by `build_parcel_facts.py`) is
   the single source of truth for per-parcel facts (owner, type, use bucket, landmark-corrected build year,
   assessed value, address, lat/lon), canonical-APN keyed. B2050BIS's JN should read `parcel_facts.db` for
   parcel joins instead of re-reading `berkeley.db` raw, so owner/assessed values match everywhere.

So: **B2050BIS's baseline is authoritative for the bond; the maps session's parcel_facts is authoritative
for the parcels.** If a number needs to change, it changes at its source of truth, and the other side
re-reads it — no divergent copies.

## Shared-file protocol (collision avoidance)

- **`PROGRESS.md`** — append-only; each entry **tagged with the session name**; **never edit the other
  session's entry.** (This session tags "maps"; B2050BIS should tag "B2050BIS".)
- **`berkeley.db` / `parcel_facts.db`** — read-only shared. The maps session owns the *build* of
  `parcel_facts.db`. (`databases/` is gitignored → both are local build artifacts; regenerate from scripts.)
- **`data/baselines/`** — each session owns its own baseline files; don't edit another session's baseline.
- **Design doc** `notes/2026-08-14_structure_history_open_data_design.md` — maps session owns; B2050BIS reads.

## Branching (John's call)

Standing rule is **`dev` only, no push without John**. The cleanest fix for two concurrent sessions is a
separate local branch per session off `dev`, merged by John — but that bumps the dev-only convention, so
it's **flagged for John's decision**, not adopted unilaterally. If we stay single-branch on `dev`, the
file-ownership table above + small, frequent, single-purpose commits keep us clear of each other. Neither
session pushes, merges, touches `main`, or rewrites history — all of that is John's.

## Status / open handoffs

- ✅ **Rate-toggle map** delivered (reads B2050BIS baseline) — their §2 Map TODO is closed.
- ✅ **Inline parcel card** on all three maps (owner · built · use · assessed) from `parcel_facts.db`.
- ↔ **Suggested for B2050BIS:** point the JN's parcel joins at `parcel_facts.db`; if you want more official
  figures surfaced on the map (e.g. a "combined with existing GO debt $44.13" mode), add them to the
  baseline and tell the maps session — the map will read them.
- 📍 Health-check: the maps session's four artifacts (`bond_incidence.html` + `_data.json`,
  `berkeley_construction_timelapse.html`, `berkeley_ownership.html`) are present and committed under
  `docs/maps/` — they resolve when `docs/` is served.
