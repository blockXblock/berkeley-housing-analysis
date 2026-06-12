# Logan Park South Building + 1367 University Fixes — 2026-06-04

**Seventh data-modifying operation.** Two fixes, both **primary-permit-confirmed from CPRA** (no
Accela needed), found while re-deriving the city-vs-ours reconciliation after a chain of query-bug
retractions. Pre-write snapshot: `keep_snapshot_2026-06-04_pre-logansouth-1367fix.db` (dea44e46).
Canonical after: **`02f3cfa9`**. Post-write snapshot: `keep_snapshot_2026-06-04_post-logansouth-1367fix.db`.
Script: `scripts/fixes_logan_south_1367univ_2026-06-04.py`.

## Result
| Year | before | after |
|---|---|---|
| **CY2023** | 631 | **700** (+69 Logan Park South Building) |
| CY2024 | 709 | 709 |
| CY2025 | 531 | 531 (1367 University already counted; data-quality only) |
| CY2026 | 216 | 216 |
| 2018-2022 | 70/98/76/107/84 | unchanged |

## FIX 1 — Logan Park SOUTH Building: a real 2023 completion we were MISSING
**The settled reading (after two wrong framings — see §"Retraction" below).** Logan Park is **two
buildings on two parcels**:
- **North Building** (APN …01805, proj179): finaled **2022** (B2019-05574 Phase II 2022-01-14 135u;
  B2019-03704 Phase I 2022-10-06). Correctly pre-cycle, uncounted.
- **South Building** (APN **…04100**): permit **B2021-03302** *"Phase II of South Building: Structural
  Super Structure, MEP, landscaping,"* **69 units, Finaled 2023-08-08** (CPRA status: Finaled) — a
  genuine 2023 completion that was **absent from v2 entirely.**

Ingested as a new project (proj887): co_issued 2023-08-08, 69u, classified PRIMARY (major structural),
primary-permit-confirmed. **69u is permit-stated** (B2021-03302 `NumberUnits=69`), not CKAN-derived.
**Coords NULL** — APN …04100 is not in the Alameda assessor extract (flagged; no map pin, counts fine).

## FIX 2 — 1367 University (proj158): "Withdrawn" was a label bug, not an over-count
proj158 was stage **Withdrawn** yet counted in CY2025 with a CO — which looked like a possible 39u
over-count. CPRA settles it: **B2022-04366** *"Construction of a 9665-SF four-story 39-unit congregate
residence,"* **Finaled 2025-05-06** (status: Finaled). The "Withdrawn" came from Accela **"Auto-Closed"**
status events (2023-09-14, 2025-04-24) — automatic record-closures, **not an actual withdrawal** —
followed by Finaled + CO. So it **is** completed; our count was correct. Fixes (data-quality only, no
count change):
- **stage Withdrawn (8) → Completed (6)**.
- **dropped the stray co event** (2025-06-18, no permit backing, city_portal); kept the permit-backed
  **2025-05-06** (B2022-04366). CY2025 stays 531; we are legitimately ahead of the city (which has 1367
  University as BP-only in 2023).

## Retraction — the Logan Park finding flipped twice; the permit record settled it
The 69u at 2352 Shattuck went through three framings; **only the third is correct:**
1. ❌ *"CKAN overstates CY2023 by ~69u — Logan Park mis-yeared to 2023, actually 2022."* (Pass-2 note.)
2. ❌ *"Retract — the city reports Logan Park in 2022."* (Based on an **APN-only query** that matched the
   North parcel …01805 and missed the South parcel …04100.)
3. ✅ **"We *understated* CY2023 by 69u — the Logan Park South Building (APN …04100, B2021-03302, Finaled
   2023-08-08) is a genuine 2023 completion we lacked. The city is correct."**

Lesson reinforced: characterize only after the **primary permit record** is checked. The intermediate
"CKAN data errors (2190/2155/2157)" were also retracted — they were a SQL bug summing date columns
(`169 units + 2021 date → 2190`), not HCD's data.

## Reversal
Canonical `dea44e46` → **`02f3cfa9`**. Restore: `cp keep_snapshot_2026-06-04_pre-logansouth-1367fix.db
databases/berkeley_housing_v2.db`.

## Write-time verification (committed because all passed)
CY2023=700 · CY2024=709 · CY2025=531 · CY2026=216 · 2018-2022 unchanged · South Building 2023-08-08/69u/
Completed · 1367 University 2025-05-06/39u/Completed · projects 883→884 · FK=0 · integrity=ok.

*Push held. The reconciliation now shows broad agreement with HCD: CY2023 within 4u (1 MLK held + 3
Rule-C), CY2024 −3 (Rule-C), CY2025 we're legitimately ahead, 2018-2022 our ADU baseline (scope).*
