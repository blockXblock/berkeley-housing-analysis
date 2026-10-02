---
title: Acheson Commons — verified defects on block B0210
date: 2026-09-25
type: audit
status: open
area: docs/audit
---

# Acheson Commons (block B0210) — verified defects

Reported by a parallel session, **independently verified here against the data**. Three findings
confirmed, one attribution corrected, three measurements corrected. Nothing written.

## The block

**B0210** in `data/derived/city_block_index.geojson` — University / Walnut / Berkeley Way /
Shattuck. 2.031 acres, 8,220 m², bbox 116×94 m, 16 vertices, 8 buildings, 5 parcels, coverage 0.85,
far_block 1.32. Cite the `block_id`; do not re-derive from the raw MultiPolygon.

⚠ Canonical block source is **`data/raw/berkeley_gis/city_blocks.geojson`** (published under the
misleading layer name `sde_prod_DBO_Right_Of_Way`), exploded and filtered to 0.2–60 acres.
**Not** `row.geojson`, and **not** `BlocksCoB.geojson`, which is Census TIGER and gives a block
1.67× too large — the exact error `city_block_index.py` was written to end.

## A. One malformed APN, and it is the duplication mechanism

`parcels` id 159 (proj178, 2131 University Ave) stores **four APNs comma-joined in one field** —
`057-2046-008-03, 057-2046-008-02, 057-2046-006-00, 057-2046-010-00` — with `apn_normalized` NULL.
It is the **only** row in `parcels` containing a comma in `apn`: a singleton, not a class.
Already recorded in CLAUDE.md under ADR-003 as "proj178 Acheson held (apn_normalized=NULL)".

`057204600802` also exists as its own parcel row (2145 University), so an APN resolver finds the
standalone row rather than the blob and creates a new project instead of matching 178.

**Attribution corrected:** proj900 and proj902 were created **2026-06-15T10:07:56**, three months
before the 2026-09-25 CPRA ingest (which created ids ≥ 920; pre-ingest max was 919). Their permits
carry no 2025-2026 CPRA `source_url`. The mechanism is real; the cause is an earlier load.

**Arithmetic:** 178 (205u) + 900 (35u) + 902 (68u) = **308 units for a 205-unit development.**

## B. 102 units of Finaled permits absent — and out of reach of the CPRA feed

| permit | building | units | in v2 |
|---|---|---|---|
| B2015-02995 | Bldg A, 2131 University | 37 | **NO** |
| B2015-02998 | Bldg B, 2145 University | 35 | proj900 |
| B2015-03000 | Bldg C, 1900 Walnut | 65 | **NO** |
| B2015-03005 | Bldg D, 2111 University | 68 | proj902 |
| B2023-00417 | 2101 University, +1 unit at roof | 1 | **NO** |

⚠ **CORRECTED 2026-09-25 — I got this wrong, and the error mattered.** I first wrote that none of
the five is in the CPRA feed, "verified by membership test." I tested **one of five** feed files and
stated a whole-corpus negative. A parallel session caught it. Re-tested across every
`BP_Annual*.xlsx`:

| permit | in feed? | file |
|---|---|---|
| B2015-02995 | **YES** | `BP_Annual Permit Report-2018-2022.xlsx` (+ its rerun) |
| B2015-02998 | **YES** | same |
| B2015-03000 | **YES** (`UnitsAdded=65`, clean) | same |
| B2015-03005 | **YES** | same |
| B2023-00417 | no | absent from all five |

**So these are an INGEST job, not a records request.** The records have been in the repo since May.
`ingest_cpra_2026.py` reads only the 2025-2026 file, so the 2018-2022 and 2023-2025 windows have
never passed through it. Bldg C carries a clean `UnitsAdded=65`, so no classifier or units-fallback
question arises for it at all — it is purely unlinked.

**The gap is far larger than this block.** Across all five files: 32,897 unique permits, 1,213
classified `new_unit`, **321 of those absent from v2, and 177 of the 321 are FINALED** — completed
buildings — carrying roughly **836 units**. The largest are 163u (B2019-05608), 152u (B2016-03894),
107u (B2016-05125) and 81u (B2022-01111). ⚠ That unit total is an upper bound: several are phases of
one building ("Phase 1 of 2", "Phase 3") and a few are classifier false positives, so it must be
de-duplicated per building before anyone quotes it.

**Also: the five files are 55% duplicate rows** — 72,445 rows for 32,897 unique permit numbers,
because the 2018-2022 and 2023-2025 reruns republish their whole windows. De-duplicate on permit
number before counting anything.

Bldg C's caption is `"ACHESON COMMONS" - BUILDING "C"`, not `ACHESON BLDG C`, so a caption grep
misses it.

## C. Geometry — a superseded point, not a live conflict

proj178 holds two geometries. The v1 Point is **`is_current=0`**, superseded 2026-05-18 with the
note *"Superseded by polygon import per polygon_ingestion_plan.md §4"*. Only the `kml_import`
polygon is current: 781 m², height 21 m, 5 vertices, styleUrl `#style_Completed_synthetic1`.

Measurements corrected: the point sits **55 m** from the polygon centroid (not 38), and the polygon
is **10%** of B0210 (not 12%). "Synthetic" is in its own style name — it was never a claimed
footprint.

## What must NOT be done

CLAUDE.md's SHADOW vs ADU-PAIR rule: two distinct real permits with two distinct CO dates are two
real buildings — **PROTECT, never merge**. Acheson has four distinct permits with four distinct
finals, so proj900 and proj902 are real buildings, not shadows. **Merging them into 178 is ruled
out.**

What is *not* settled is whether 178's 205 should be reduced to Bldg A's 37 while 900/902 carry
their own. That is a gated write and John's call. John reports Bldg D (2109/2111) is a different
building and project, which is consistent with the rule.

## Address aliasing (reported, not independently checked)

John reports 2125/2129/2131/2135 University are storefronts plus the main door of **one** building
(Bldg A), and 2109/2111 are one six-story building with the numbers running **backwards**. v2 holds
only 2111, 2119, 2131 and 2145 of the nine. LMSA2019-0001 gives the City's own project-site
footprint: *"1979-1987 Shattuck, 2102-2113 University, 2125-2145 University and 1922-1930 Walnut"*.

---

## Follow-on: one real bug found, two reported ones that were not

Chasing the wider gap with the parallel sessions produced one genuine defect of mine and two claims
that did not survive checking.

**REAL — the `NumberUnits` fallback over-counted on non-new work.** `NumberUnits` is TOTAL units in
the building, a safe stand-in for `UnitsAdded` only on genuinely NEW construction where the whole
building is the addition. On an alteration it is the building's size: an ADU converted inside a
single-family house reads `NumberUnits=2` when the net gain is 1. Measured across all five files,
**85 rows would have over-counted by roughly 85 units.** Fixed — the fallback now requires a
new-construction `Work Type`; non-new work falls to the documented floor of 1 and is flagged.
Five regression cases pass, including the ADU-conversion and carport-conversion shapes.

**NOT REAL — `B2016-05125` is not a mechanical permit.** Reported as "a MECHANICAL permit carrying
107 units", a false positive. It is `Work Type='New'`, `OccType='R-2 Residential: Permanent,
Multi-Unit (3+ Units)'`, and the description reads: *"2/15/19 - mechanical permit issued. | 7 story
Apartment Building containing 107 Dwelling units. 5 stories of Type IIIA over 2 stories of Type IA
podium."* The mechanical note is a **log prefix**; the permit is a real 107-unit building and 107 is
the right answer. The truncated description is what misled.

⚠ **This trap is general.** Many descriptions in this feed open with a dated log line — *"3/12/18 -
Electrical permit issued"*, *"6/25/18 - Mechanical permit issued"* — before the actual scope. My own
first instinct was to veto on mechanical/electrical keywords, which would have killed genuine ADU
conversions. **Never classify from a truncated description in this feed.**

**ALREADY HANDLED — the solar rows.** `B2024-05765`, `B2023-06165` and `B2025-05719` were reported as
needing a filter before anyone quotes a total. All three are already refused by the existing
non-dwelling veto (`VETOED-nondwelling`). No new filter is needed for them.

## Where the missing-permit total actually stands

A parallel session measured the split (130 permits / 546 units on their filter, against my 177 /
~836 — different `Finaled` predicates, so treat the SPLIT as the finding, not either total):

- **~50 permits / ~97 units on parcels v2 already holds** — a link gap. Two-thirds of it is
  Acheson Bldg C at 65u; most of the rest is solar rows my veto already drops.
- **~80 permits / ~449 units on parcels v2 has never seen** — genuinely unseen buildings.
- only **5 of 130** mention a phase at all.

**So the inflation is NOT mainly phase double-counting**, which both of us assumed at first. Most of
the recoverable content is real, on parcels v2 does not hold, which makes a wider ingest **project
creation rather than permit attachment** — a larger job than "attach the missing permits".

## Feed schema note

All five files carry the same 26 columns, header on row 7, with **spaces in the field names** —
`Finaled Date`, `Parcel Number`, `Work Type`, not `FinaledDate`/`APN`/`WorkType`.

---

## My own veto had the same trap — and it was refusing a 56-unit building

The parallel session's warning that **description-based vetoes in this feed are unsafe by
construction** applies to my `NOT_DWELLING` guard, and I tested it against my own code rather than
assuming it did not. It does.

**14 permits, 222 units, all `Work Type = 'New'`, were being refused** because something incidental
appeared in the description:

| permit | units | why it was refused |
|---|---|---|
| B2016-05821 | **56** | *"New 5 story, 30,890 Sq. ft., 56 dwelling units…"* then *"**Geovanni Cortez from Power Plus added Temp power pole."* — matched "temp power" |
| B2016-03894 | 152 | *"Phase 3: Structural for wood frame portion…"* |
| B2018-01153 | 1 | log prefix *"Issued temporary power pole only."* then *"Construction of new Single Family Residence"* |
| B2018-03533 | 1 | log prefix *"Issued trade (EMP) permits."* then *"New construction of detached ADU"* |
| B2021-02227 | 1 | *"993 SF detached ADU. **Solar under B2021-05613**"* — matched a cross-reference |

**The fix: the structured field outranks the prose.** Where `Work Type` says new construction, the
permit creates a building and incidental description text cannot override it. The veto now applies
only to non-new work — which is where solar, re-roofs and service upgrades actually live. The three
solar rows it was written for are all `Alteration`, so it still catches them. Vetoes 54 → 40.

**⚠ The fix is not free, and should not be reported as though it were.** Re-admitting the
new-construction rows lets two questionable ones back in: **B2024-04235** (*"Temp power- 100 amp for
single family home"*, `Work Type 'New'` — the city filed the temp-power permit under the new-build
project) and **B2016-03894** (a Phase 3 permit that will collide with its siblings). Both are the
per-building dedupe's job, not the veto's. Net: 14 real buildings recovered, ~2 rows that the
dedupe must then resolve.

**The durable lesson, which now has three independent instances today:** in this feed a description
is *narrative appended over time* — dated log lines, contractor notes, cross-references to other
permits — while `Work Type`, `OccType` and `UnitsAdded` are *structured fields*. Read the structured
field first and use the description only to break ties it cannot. Every classification error found
today ran the other way round.
