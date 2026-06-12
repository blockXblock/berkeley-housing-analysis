# P1 Public-Facing Artifacts — Root-Cause Diagnosis — 2026-05-31

**Scope:** Read-only diagnosis of the two P1 artifacts from the explorer cutover
validation. **No data, DB, or script modified.** Does not touch external drives
or the Toshiba copy. Fixes are *recommended, not executed.*

---

## P1a — The +2 projects render broken (units=0, lat=None)

**Projects:** id183 (2328 Channing Way), id184 (2330 Blake St).

### Root cause: permit-only stubs, never enriched
Both are **stub records auto-created on 2026-05-12 from a single building-permit
event** — nothing more:

| id | Address | project_versions | project_events | geometry |
|---|---|---|---|---|
| 183 | 2328 Channing Way | **none** | 1: "Building Permit Issued: **B2022-05957**" (2024-09-05) | none |
| 184 | 2330 Blake St | **none** | 1: "Building Permit Issued: **B2025-00168**" (2025-07-30) | none |

`v_projects_flat` derives units/name/dates from the project's **current version
→ unit_program**; with **no `project_versions` row**, every such field is NULL.
Status "Permitted" comes solely from the BP event. No geometry row → no lat/lon.
These were created by a permit/CPRA import that found a BP for an address not yet
in the project set, inserted a minimal project + event, and **never backfilled**
units, a version, or geometry.

### Is the missing data available elsewhere? — Coordinates YES, units NO
**Coordinates already exist in `berkeley.db` parcels** (exact match by address):

| Project | APN | lat | lon |
|---|---|---|---|
| 2328 Channing Way | 55-1883-27 | 37.86624612 | -122.26192712 |
| 2330 Blake St | 55-1832-26-1 | 37.86356536 | -122.26137212 |

**Units are NOT in v1** (these projects don't exist in `berkeley_housing_analysis.db`)
— they'd come from the building-permit/CPRA source records (B2022-05957 /
B2025-00168), which carry unit counts.

### Classification & recommended fix
- **Coordinates → DATA CONNECTION.** Geocode from `berkeley.db` parcels by APN/
  address — the data is already on disk; nothing to acquire.
- **Units → DATA CONNECTION or light DATA ENTRY.** Pull unit counts from the BP/
  CPRA permit records the events reference; create a `project_version` +
  `unit_program` row so `v_projects_flat` surfaces them.
- **Front-end stopgap:** until enriched, **suppress projects with `latitude IS
  NULL`** from the map (don't render broken/0-unit pins) rather than display them.

Not stubs-with-no-data-anywhere (case a) and not fully-ingestible-as-is — they're
**case (b): real permitted projects whose coordinates exist on disk and whose
units exist in the permit source, but neither was connected into v2.**

---

## P1b — 2138 Kittredge appears twice (id113 / id118)

### Root cause: two v1 records for ONE parcel, kept through migration
Both records are the **same physical project** — the v2 dedup didn't collapse them:

| | id113 | id118 |
|---|---|---|
| Address | 2138 KITTREDGE St | 2138 KITTREDGE St "(id:118)" |
| **APN** | **057 202901500** | **057 202901500** (same parcel) |
| Units | **73** (5 VLI + 68 Above-Mod) | **66** (5 VLI + 61 Above-Mod) |
| Status | **Permitted** | **Entitled** |
| filed / entitled | 2024-09-05 / 2025-10-20 | 2024-09-05 / 2025-10-20 (same) |
| Building permit | **B2024-04964 (issued 2024-10-16)** | none |
| Events | BP-track | Accela entitlement-track (App Complete, Corrections) |
| Classifications | sb330=1, density_bonus=1 | sb330=1, density_bonus=1 |
| Provenance | migrated v1→v2 2026-05-07 | migrated v1→v2 2026-05-07 |

**Same APN, same filed/entitled dates, same VLI count (5), same flags, both
migrated from v1 the same day.** They are not adjacent parcels and not a clean
accidental duplicate — they are **one project captured at two stages**:
- **id118 = entitlement-stage** record, 66 units — **matches the City's 2138
  Kittredge 2025 Table A2 (66 units)** from the NotebookLM work.
- **id113 = permit-stage** record, 73 units, carrying the **actual issued
  building permit** (B2024-04964). The 66→73 delta is a unit increase between
  entitlement and permit (revision or density-bonus adjustment).

This is the **base/bonus-split-style pattern** PROGRESS.md says v2 "already
de-duplicates to the bonus version" — but here **both survived as separate
`project_id`s**, so it's a **dedup gap**, surfacing as a visible duplicate
(complete with the "(id:118)" disambiguation label) on the public map.

### Classification & recommended fix
- **MERGE to canonical** (not a front-end-only fix): collapse 113 + 118 into one
  project with stage-progression. **id113 (Permitted, 73u, has the issued BP) is
  the more current/authoritative record** → keep as canonical; preserve id118's
  entitlement-stage data (66u) as historical/version. The front-end then shows
  **one** 2138 Kittredge entry.
- *Caveat for APR:* if reporting compares to the City, the City counted **66 at
  entitlement** — keep that traceable so the APR can reconcile (the 73 is the
  later as-permitted count).
- Investigate why the v2 dedup missed this pair (same APN + same dates should be
  a dedup signal) to prevent recurrence.

---

## Summary

| Artifact | Root cause | Fix type | Recommended (not executed) |
|---|---|---|---|
| **183/184** broken pins | Permit-only stubs; no version/geometry | **Data connection** (+ light entry) | Geocode lat/lon from `berkeley.db`; pull units from BP/CPRA; add a version. Stopgap: hide `lat IS NULL` from map |
| **2138 Kittredge** dup | Two v1 records (one parcel, two stages) survived migration; dedup gap | **Merge to canonical** | Keep id113 (permitted, 73u) canonical; preserve id118 (entitled, 66u) as history; fix dedup |

*Diagnosis only. No data, database, or script modified. Uncommitted — review
before any fix.*
