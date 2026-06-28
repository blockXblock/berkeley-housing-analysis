# C3 ADU-tail — ancillary double-count demotion (audit record)

**Date:** 2026-06-28
**Who:** CC, gated + confirmed by John (premise verified: city counts each ADU once — the double-count is
OUR-pipeline-only; `scratch/2026-06-28/city_apr_grain_probe.py`).
**What:** On 16 ADU parcels, an **ancillary permit** (solar / meter / panel / service-upgrade) had been
mis-classified `new_unit=1`, double-counting the ADU. Demote each ancillary → `housing_role=subsidiary` +
`net_units=0`, recording the ADU it belongs to. **17 demotions / −17 CO** (15 parcels × −1 + `055-1840-007`
× −2 two solar permits). The real ADU permit on each parcel is **UNTOUCHED**.
**Why:** C3 ADU-tail of the four-corrections reconciliation. The classifier over-promoted "solar/meter **for
ADU**" permits to units; the city's APR never counts these (it's a unit-creating-permit rollup), so this
correction converges our count toward the city's already-correct one.

## Protection guard (re-confirmed from WorkDescription before write)
Every demotion target re-checked: **has ancillary language (solar/meter/panel/service/kW/amp) AND NO
dwelling-creation language** (construct/build/convert-garage-to + ADU/dwelling). **0 targets tripped the
guard** (none read as a dwelling). 055-1840-007 specifically verified: the two solar permits demote, the
"Two (2) new 1,000 sf detached ADU" (net 2) kept.

## The 16 parcels — (ancillary DEMOTED → ADU KEPT)
| APN | DEMOTE (→subsidiary/0) | why ancillary | KEEP (real ADU, untouched) |
|---|---|---|---|
| 052-1433-010 | B2024-03488 | "Adding **Meter** for ADU" | B2023-04866 (480 sf detached ADU) |
| 052-1519-022 | B2021-01046 | "4.080 KW DC **Solar**" | B2019-04125 (New 1200 sf ADU) |
| 052-1569-017 | B2022-01617 | "upgrade the main **service panel**" | B2021-00091 (693 SF detached ADU) |
| 052-1571-016 | B2024-00296 | "Upgrade electrical main **panel**" | B2022-05864 (Build new detached ADU) |
| 053-1602-021 | B2024-01867 | "Upgrade main **service panel**" | B2023-03018 (New 2-story detached ADU) |
| 053-1673-026 | B2023-00087 | "PV **solar** panels" | B2019-03475 (new ADU 466sqft) |
| 055-1840-007 | B2024-05764 | "PV **solar** panels" | B2024-01193 (Two new 1,000sf detached ADU, net 2) |
| 055-1840-007 | B2024-05765 | "PV **solar** panels" | B2024-01193 (same — both solars demoted) |
| 055-1840-009 | B2024-02847 | "Main **service** upgrade … meter" | B2021-01738 (New 1000 sq ft ADU) |
| 056-1919-025 | B2023-05267 | "3.2kW … **load center**" | B2021-01939 (New 572 SqFt ADU) |
| 056-1924-016 | B2022-03712 | "upgrade main **service** electrical panel" | B2020-04487 (new detached 390sf ADU) |
| 058-2153-028 | B2024-04931 | "200A 2 **meter**" | B2023-03870 (735 SqFt HUD Manufactured ADU) |
| 060-2423-031 | B2023-00349 | "2.00 kW **solar**" | B2021-01537 (450 SqFt detached studio ADU) |
| 061-2574-002 | B2020-02136 | "dual **meter**" | B2019-02858 (New 750 Sq ft detached ADU) |
| 061-2612-013 | B2025-04521 | "main house electrical **service** upgrade" | B2024-04779 (Construct new ADU) |
| 062-2849-004 | B2024-05515 | "Upgrade main **service panel** … meter" | B2024-01121 (new ADU manufactured housing) |
| 064-4295-012 | B2022-04142 | "Upgrade … **meter** 100→200A" | B2021-03087 (basement to new ADU) |

Each demoted permit's `basis_note` was annotated: *"C3-tail: ancillary (solar/meter/panel/service)
subsidiary to ADU `<keep>` (src c3_adu_tail_review.csv)"* — so the ancillary→ADU relationship is in-DB
(query: `basis_note LIKE '%C3-tail%'`).

## Layer / discipline
ADR-002 VERDICT layer; **housing_role change**. Only each ancillary permit's finaled master event touched
(role→subsidiary, net_units→0, basis_note annotated). The 16 real ADU permits untouched; no other permit.
Single transaction, rowcount==1 per target, all-or-nothing.

**Snapshot (pre-write):** `databases/keep_snapshot_2026-06-28_pre-c3-tail.db` (integrity `ok`, size-matched).
**sha:** pre `12a7d7440128e8e3` → post **`cd88b5f5a417864d`**.

## Verification trace
- Pre-write fingerprint: 17/17 targets confirmed currently `new_unit`/master/net≥1 finaled.
- STEP 3: 17/17 rowcount==1 → COMMITTED. STEP 4 (fresh conn): all 17 → subsidiary/0, all 16 paired ADUs
  still new_unit/≥1 → PASS. STEP 5 idempotency: re-run changed **0 rows**.
- STEP 6 real before/after:

| CY | before | +C3t | after | city | Δ after |
|---|---|---|---|---|---|
| 2020 | 338 | −1 | 337 | 405 | −68 |
| 2022 | 601 | −2 | 599 | 828 | −229 |
| 2023 | 628 | −4 | 624 | 716 | −92 |
| 2024 | 824 | −3 | 821 | 708 | +113 |
| 2025 | 594 | −6 | 588 | 492 | +96 |
| **TOT** | **3939** | **−17** | **3922** | **4022** | **−100** |

Cumulative CO **3,939 → 3,922 (−83 → −100 vs city)** — as predicted. The gap deepens because this removes
*pipeline-only* over-counts (the city never had them); the residual −100 is genuine (recall + C4 timing).

## Reverse (undo)
Restore `databases/keep_snapshot_2026-06-28_pre-c3-tail.db`, or per-permit (all 17 were new_unit/net=1):
```sql
UPDATE event_classifications SET housing_role='new_unit', net_units=1
WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key IN
 ('B2024-03488','B2021-01046','B2022-01617','B2024-00296','B2024-01867','B2023-00087','B2024-05764',
  'B2024-05765','B2024-02847','B2023-05267','B2022-03712','B2024-04931','B2023-00349','B2020-02136',
  'B2025-04521','B2024-05515','B2022-04142') AND event_type_code='permit_finaled') AND is_master=1;
```
(basis_note annotation is cosmetic; snapshot restore reverts it fully.)

## Reconciliation now
3,066 baseline + C2 +1,036 (done) − C3 Shattuck −163 (done) − C3 ADU-tail −17 (done) = **3,922 vs city
4,022 (−100)**. Remaining: C3 review/protect tail (the 7 protect + 8 review parcels — John's per-row call,
~3 confirmed pairs to keep, ~4 likely additional ancillary), and C4 (BP reporting-year). The 052-1519-022
city-side anomaly (city CO=2 for a single ADU) is a separate one-off to check.

*Not committed to git. v4 mutation only; this record is the audit trail.*
