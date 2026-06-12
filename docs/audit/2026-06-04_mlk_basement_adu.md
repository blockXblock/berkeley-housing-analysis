# 2210 MLK Basement ADU — Held Item Resolved — 2026-06-04

**Eighth data-modifying operation.** Resolved the last held reconciliation item (2210 MLK), a
1-row gated add, **primary-permit-confirmed from CPRA** (no Accela needed). Pre-write snapshot:
`keep_snapshot_2026-06-04_pre-mlk-basement.db` (02f3cfa9). Canonical after: **`0371c3be`**.
Script: `scripts/add_mlk_basement_adu_2026-06-04.py`.

## The resolution — it was two ADUs, not a year-disagreement
2210 MLK (APN 057 201800700) has **two distinct ADUs on one parcel** (the Logan Park pattern):
- **Detached rear ADU** — B2020-01827, *"New 5-bed 831 sf ADU, detached, at the rear,"* **Finaled
  2025-03-26**, 1u. Already in v2 as **proj362** (CY2025). Correct — kept exactly as-is.
- **Basement ADU** — B2020-02346, *"New 985 sf 5-bed 2-bath ADU at existing basement,"* **Finaled
  2023-01-11**, 1u. The city counted this in CY2023; **it was absent from v2.** Ingested as **proj888**
  (co_issued 2023-01-11, classified PRIMARY, parcel reused id 349, coords from assessor).

So the "year-disagreement" (CKAN 2023-01-11 vs our 2025-03-26) **dissolves**: both dates were correct,
for different units. We had only the 2025 detached ADU; we were **missing the 2023 basement ADU**. The
APN lookup (not the failed address search) surfaced the second permit.

## Result
**CY2023 700 → 701.** CY2024=709, CY2025=531, CY2026=216, 2018-2022 unchanged. **No held items remain
for 2023-2025.** CY2023 vs CKAN 704 = **−3, a pure Rule-C net-new-vs-reported delta.**

## Reversal
Canonical `02f3cfa9` → **`0371c3be`**. Restore: `cp keep_snapshot_2026-06-04_pre-mlk-basement.db
databases/berkeley_housing_v2.db`.

## Write-time verification (committed because all passed)
CY2023=701 · CY2024=709 · CY2025=531 · CY2026=216 · 2018-2022 unchanged · basement ADU proj888
2023-01-11/1u/Completed · proj362 unchanged (2025-03-26) · projects 884→885 · FK=0 · integrity=ok.

*Push held. 2023-2025 now fully reconciled to agreement + the 3u Rule-C convention; no held items.*
