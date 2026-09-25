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

All five are `Finaled` in the Accela sweep. **None of the five is in the CPRA feed** — verified by
membership test. `BP_Annual Permit Report-2025-2026-07-07.xlsx` covers post-dates 2025-01-01 →
2026-07-07; these finaled in 2022. So the 2026 ingest could not have reached them, and a further
CPRA production covering earlier post-dates is what would.

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
(Bldg A), and 2109/2111 are one six-storey building with the numbers running **backwards**. v2 holds
only 2111, 2119, 2131 and 2145 of the nine. LMSA2019-0001 gives the City's own project-site
footprint: *"1979-1987 Shattuck, 2102-2113 University, 2125-2145 University and 1922-1930 Walnut"*.
