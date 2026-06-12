# Pre-Policy ADU Backfill 2018-2022 — SOLID set — 2026-06-03

**Sixth data-modifying operation.** Ingested the pre-policy (2018-2022) ADU/small completions
that are **CKAN-anchored AND primary-permit-confirmed** ("SOLID"). Adds five new completion years.
Pre-write snapshot: `keep_snapshot_2026-06-03_pre-prepolicy-adu-solid.db` (bdadce65).
Canonical after: **`dea44e46`**. Post-write snapshot: `keep_snapshot_2026-06-03_post-prepolicy-adu-solid.db`.
Script: `scripts/prepolicy_adu_solid_2026-06-03.py`.

## Result — pre-policy ADU ramp (net-new CO units)
| Year | parcels | units |
|---|---|---|
| 2018 | 60 | 70 |
| 2019 | 96 | 98 |
| 2020 | 74 | 76 |
| 2021 | 103 | 107 |
| 2022 | 81 | 84 |
| **Total** | **414** | **435** |

Existing years **unchanged**: CY2023=631 · CY2024=709 · CY2025=531 · CY2026=216. Projects 469→883.

## Method — CKAN-anchored + PRIMARY-PERMIT-CONFIRMED (stricter than CY2023 Pass 1)
A parcel is ingested only when **both** hold:
1. **CKAN parcel-pointer:** the city's APR (CKAN mirror) lists an ADU/small (≤4u) completion at the
   parcel that year, and the parcel is not already in v2. CKAN identifies *which* parcels to extract —
   it is **never a data source**; unit/date/coords come from CPRA + Alameda assessor.
2. **Primary-permit confirmation:** a Finaled CPRA permit that is an **ADU-construction / new-structural**
   permit exists for that parcel/year (an actual build, not an alteration). This is the gate CY2023 Pass 1
   did **not** apply.

`WEAK` (CKAN lists it but the best CPRA match is an alteration) and `NONE` (no CPRA permit) are **not**
ingested — they go to the Accela-verification queue (§ below). This avoids letting CKAN's listing alone
assert that a completion happened.

## The ~11 Accela-verification queue (NOT ingested)
For each: *"does a real ADU-build permit exist at this parcel?"* — if confirmed, ingest with provenance;
if not found, it is a **finding** (CKAN lists a completion the permit record doesn't support).
- **Genuine-WEAK (4):** 2434 McGee (admin), 1284 Hearst (electrical panel), 840 Delaware (replace stairs),
  2704 Shasta (owner-obtained MEP permits).
- **NONE (4):** parcels CKAN lists with no matching CPRA permit (2020×2, 2022×2).
- **Borderlines (3):** different question — *"is there a net-new unit at all?"* — 2414 Dana ("enlarge")
  and 1432 Spruce ("raise house") lean EXCLUDE (additions/renos, no explicit unit); 1619 Cornell
  ("remodel+addition+change-of-use") held pending its change-of-use full text.

## Classifier-limitation findings (for the paper)
Three systematic ways naive permit-counting misfires, all surfaced here:
- **(a) ADU=Yes-flag overcount that GROWS with ADU stock.** The CPRA `ADU=Yes` flag means *"parcel has an
  ADU,"* not *"this permit built one."* A `1-per-ADU` net-new rule counts every alteration on an
  existing-ADU parcel (panel upgrade, solar, generator) as a completion — and the error **grows over
  time** as ADU stock accumulates (2022 raw was 183 vs ~84 real; the noise was ~110 alteration permits).
  Naive permit-counting inflates **recent** years worst. (Pairs with the earlier ~2× raw-vs-verified finding.)
- **(b) Alteration-keyword override drops real conversions.** A SUBSIDIARY keyword (remodel, door) can
  override a genuine ADU verb — e.g. "convert garage to habitable [ADU]" dropped on "door"; "remodel
  workshop to in-law unit" dropped on "remodel". Real units lost unless hand-reclaimed.
- **(c) Keyword tail misses build notations.** New-construction written as **"(N)"** (not "new"),
  **"SADU"** (secondary ADU), **"secondary unit"**, or "New `<sqft>` Home" (size between "new" and the
  noun) escapes a literal regex. Six such parcels were hand-reclaimed to SOLID here.

## CONSISTENCY FLAG (documented; decide later — do NOT re-litigate CY2023 yet)
This pre-policy set uses a **stricter rule** (primary-permit-confirmed) than **CY2023 Pass 1**
(CKAN-anchored *without* the permit-confirmation gate). For full cross-year consistency, **CY2023's
ADU set eventually wants the same SOLID-vs-WEAK audit** — otherwise the pre-policy years are held to a
higher evidentiary standard than CY2023. Noted now; deferred.

## Coords / null-coord
12 SOLID parcels lack assessor coords (no map pin until sourced; counts fine) — added to the running
coord-sourcing follow-up.

## Reversal
Canonical `bdadce65` → **`dea44e46`**. Restore: `cp keep_snapshot_2026-06-03_pre-prepolicy-adu-solid.db
databases/berkeley_housing_v2.db`.

## Write-time verification (committed because all passed)
2018-2022 SOLID populated (60/96/74/103/81 parcels) · **triad UNCHANGED** (CY2023=631, CY2024=709,
CY2025=531, CY2026=216) · projects 469→883 (+414) · foreign_key_check=0 · integrity=ok.

*DBs gitignored; this note + the script are tracked. CKAN remained a parcel-pointer, never a source.
Push HELD. The ~11 Accela queue, 2022's 6 majors, and the dashboard/Colab refresh remain parked.*
