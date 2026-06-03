# CY2023 ADU Backfill — Pass 1 (Bucket A) — 2026-06-03

**Fourth data-modifying operation** on `berkeley_housing_v2.db`. Ingested the **103
clean CY2023 ADU/small completions (Bucket A)** from primary sources, adding CY2023
as a new completion year. **Pass 1 of 2** — the 6 CY2023 *major* projects (260u) are
**deferred to a later Accela-gated pass** (see §5).

- **Pre-write snapshot / reversal point:** `databases/keep_snapshot_2026-06-03_pre-cy2023-adu.db`
  (sha `179434a8`, integrity ok).
- **Canonical after write:** **`a5e63b1b`** (integrity ok).
- **Post-write snapshot:** `databases/keep_snapshot_2026-06-03_post-cy2023-adu.db` (sha `a5e63b1b`).
- Reproducible script: `scripts/adu_ingest_cy2023_preview_2026-06-03.py` (DRY by default; `--commit` to write).
- Gate: snapshot → dry-run preview (numbers validated) → STOP for John → `--commit` verify-or-rollback.

## Result — APR CO net-units (group-quarters excluded)
| Year | units | proj | status |
|---|---|---|---|
| **CY2023** | **441** | 103 | **NEW this write** (ADU portion; +260u majors deferred) |
| CY2024 | 709 | 99 | unchanged |
| CY2025 | 532 | 101 | unchanged |
| CY2026 | 216 | 2 | unchanged |

Adding a new year did **not** move the existing triad — verified in-transaction.

## 1. Method (identical to the CY2024/CY2025 ADU ingests)
The 103 Bucket-A parcels are city-reported CY2023 completions absent from v2, **all
present in our CPRA file with 2023 finaled dates** (100% recoverable). Built each
record from primary sources only:
- **APN join** → `normalize_apn` → `berkeley.db` (Alameda assessor) for `Latitude`/
  `Longitude` + `the_geom` polygon + `UseCode`.
- **Units** = CPRA Rule-C net-new (`UnitsAdded` if >0, else 1 for `ADU=Yes`, else `NumberUnits`).
- **co_issued event** dated to the **2023 CPRA finaled date** — these ARE completions
  (CY2023 COs), unlike the application-stage Table A work.
- **Honest unknowns with provenance:** `bedroom_count=NULL`, `tenure_type_id=8` (Unknown),
  `income_category_id=6` (UNKNOWN).
- CKAN used ONLY to define the Bucket-A target, never as a source.

## 2. The 441-vs-444 convention (documented, not a silent gap)
**CY2023 = 441 net-new units (Rule-C), vs CKAN's reported 444.** The 3-unit gap is the
**same net-new-vs-reported convention applied to CY2024 and CY2025** — Rule-C counts
net-new dwellings while CKAN's row figure can differ by a few units. We store the
primary-source Rule-C figure (441); the delta to the city's 444 is explained, not silent.

## 3. Classification — corrected ADU-aware rule, applied in-ingest
**103 PRIMARY / 0 SUBSIDIARY** (no permit rode in unclassified — the lesson from the
CY2025 ADU classification gap). 98 classified PRIMARY by rule; **5 landed AMBIGUOUS and
were hand-adjudicated → PRIMARY** (all real net-new housing; they fell to AMBIGUOUS only
because the 120-char description truncation hid the unit-creating clause — the CY2024
proj245 "junior ADU" pattern):

| Parcel | u | full-text basis |
|---|---|---|
| 1506 Bonita | 2 | "create **2 new lower level units**, R3→R2" |
| 1600 Walnut | 1 | "**construction of a second dwelling unit**" |
| 1462 San Pablo | 1 | "697 SF **HUD/HCD approved Manufactured unit** on permanent foundation" |
| 2980 College | 4 | "convert (2 office units) **into (4) residential units**" |
| 2432 Oregon | 1 | "Convert storage… to create an **attached JADU**" |

No 2641-College-style misclassifications (0 subsidiary) — the corrected rule held.

## 4. Coordinates / null-coord flag
102/103 resolve **lat/lon + the_geom + UseCode**. **1 null-coord (flagged, not blocked):**
`1438 Fifth St` — the Alameda assessor lacks coords for this parcel. This brings the
**accumulated null-coord ADU pins to 4** (1446 Fifth, 2020 Dwight, 2710 College, 1438
Fifth) — a small coord-sourcing follow-up for later, not a blocker; the unit counts fine.

## 5. Deferred — the 6 CY2023 majors (260u), Accela-gated Pass 2
CKAN CY2023 (704u, deduped) = 441u (this ADU backfill) + **260u across 6 major parcels
already in v2 but not recorded as 2023 COs**: 3000 San Pablo (78u, unit/stage mismatch),
2352 Shattuck/Logan Park (69u — the re-anchor destination), 2072 Addison (66u, Entitled),
2009 Addison (45u, 0u/no-CO anomaly), 2210 MLK (1u) + 605 Neilson (1u) (year discrepancies).
These need Accela verification before placement and are **held for Pass 2** (see the
`table-a-reconciliation-state` memory and CY2023-scoping pass). When done, CY2023 → ~701 ≈ CKAN 704.

## 6. Row deltas / reversal path
- Canonical `179434a8` → **`a5e63b1b`**. Projects 366→**469** (+103); +103 each of parcels /
  project_versions / unit_program / affordability / permits / co_issued events / classification events.
- **Restore:** `cp databases/keep_snapshot_2026-06-03_pre-cy2023-adu.db
  databases/berkeley_housing_v2.db` (sha `179434a8`).

## Write-time verification (committed only because all passed)
CY2023 = 103 proj / **441 units** · TRIAD UNCHANGED (CY2024=709, CY2025=532, CY2026=216) ·
classification 103 PRIMARY / 0 subsidiary · projects 366→469 (+103) · foreign_key_check=0 ·
integrity_check=ok · canonical `179434a8`→`a5e63b1b`.

*DBs gitignored; this note + the script are tracked. CKAN remained the verification target,
never a source. Push HELD for John's change-note review. The 6 CY2023 majors stay deferred.*
