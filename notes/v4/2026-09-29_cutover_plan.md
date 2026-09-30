---
title: "v2 → v4 cutover plan: one canonical database"
date: 2026-09-29
type: plan
status: proposed (awaiting John)
---

# v2 → v4 cutover plan: one canonical database

**Goal (John, 2026-09-29):** v4 is the one canonical database. Every publisher reads v4; v2 is archived
read-only like v1. Source: two read-only inventories run 2026-09-29 (publisher field map; 380-script census).

## Where things stand
- v4 holds the **evidence**: 147,232 events (CPRA permits, 47,411 inspections, 10,713 planning records/tasks),
  model-read classifications, 29,127 parcels, assessed values, owners, 306 documents.
- v4 holds **no entities**: structures, projects, units, addresses and geometry all have 0 rows.
- **20 publishers** read v2 (Explorer, APR, Datasette, pipeline-state, players, tours/KML, JN-N), plus about 20
  analysis readers (JN-J/K/L/MeasureU, apr_hcd, fee harvesters, height extractors, gates, press notebook).
- **The v4 build itself still reads v2 in places** (JN-C's has-docs bridge, `llm_permit_effect.py` fill-ins,
  and several harvest queue builders). v2 cannot be archived until the build stops reading it.

## Phases (each ends verified; DB writes are gated on John)
0. **Simplify (no DB write).** Sequester the 40 ARCHIVE_NOW scripts (list in the inventory) with SystemExit
   banners; notebooks go to `archive/notebooks/`. Re-run gates and the housing_rules smoke test.
1. **Cut the build loose from v2.** Re-point JN-C's has-docs bridge to v4 `documents`, the
   `llm_permit_effect` fill-ins to v4 events, and the queue builders to v4.
2. **Buildings.** Write the structures fold into v4 (`structures`, `structure_events`, `structure_parcels`).
   The fold and baseline exist; the write step is new. Gated.
3. **Projects.** A project = a primary planning application plus the structures it produced, or an
   application alone (entitled, not built). Code needed: the join (scratch prototype exists), `capdetail_select`
   re-pointed at v4, `planning_record.milestones`, `planning_scope_rulings`. Open: 25 large structures with no
   approval in the harvest. Load the 44 newly included records first.
4. **Sourced attributes.** Addresses (events + CapDetail, via the address canon), coordinates (`berkeley.db`
   by APN), geometry (`kml/`), applicants (CPRA 26-1972 planning log, on disk), parcel lineage (2 → 53),
   heights (re-point the existing extractors), pathway flags (density bonus/SB 330/SB 35/AB 2011, a model read).
5. **Ledgers applied in the build.** Affordability and UC/BART rulings → units and flags (new apply code;
   grounded_counts already applies). Seven affordability projects are still unsourced.
6. **Publisher views in v4.** Include a v2-project-id → v4 crosswalk so Explorer links, the JSON overlays,
   KML labels and fee CSVs keep resolving. Re-point publishers one at a time, diffing each output
   against its v2 version. Replace the hand-made public Datasette DB with a generator.
7. **Archive v2** read-only, with v2-only data exported. The v3 curriculum keeps a frozen copy (it reads v2).

## Decisions for John
1. **v2 data with no primary source:**
   - 39 developers + 31 architects from v1
   - 35 architects from SF YIMBY
   - 14 Panoramic reconstructions
   - 19 hand project names
   - 168 heights
   - 441 fee rows
   - UC/BART coordinates

   Options: carry into a v4 ledger marked "carried from v2, unsourced" and re-source over time, or drop.
   Never carry the ~414 unit counts chosen through the CKAN parcel pointer.
2. The v1 course notebooks linked from public pages: leave them in place with a warning, or change the links first.
3. `jev_stage_classify.py` / `stage_classify_7rung.py`: John held them "until the CapDetail harvest lands".
   It has landed. Sequester?
4. Fees: re-harvest from CapDetail/AgencyCounter (CARRY + EXPAND), or carry the v1 rows meanwhile.
