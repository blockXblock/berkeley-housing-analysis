# permits_clean — the post-ingest permit feed (CSV + parquet)

**What this is:** the **clean, typed, deduplicated** form of Berkeley's CPRA building-permit feed — i.e.
the dataframe you get *after* the curriculum's JN1 ingest step. A notebook (or another city's analyst)
that wants to **skip JN1** loads this and starts at JN2.

**Ships alongside — not instead of — the raw `.xlsx`.** The raw export (`data/raw/cpra-downloads/
BP_Annual Permit Report-*.xlsx`) is kept on purpose: its messiness (header on row 8, sparse `Unnamed:`
columns, everything-as-text, `MM/DD/YYYY`-vs-ISO dates) **is** JN1's lesson. `permits_clean` is for the
rungs/cities that don't need that lesson.

| file | size | format |
|---|---|---|
| `permits_clean.csv` | 7.95 MB | text, dates as `YYYY-MM-DD` |
| `permits_clean.parquet` | 2.15 MB | typed columnar (smaller, faster; needs `pyarrow`) |

Both carry **identical values** — parquet just preserves dtypes natively and compresses.

## What "clean" means here (the exact JN1 logic, made honest)

1. **Source:** both raw `.xlsx` files, read with `header=7` (the real column row), null-`PermitNumber`
   rows dropped.
2. **Columns selected (14)** — the structured set the pipeline actually reads (never prose for facts;
   `WorkDescription` kept as *context* only):
   `PermitNumber, StreetNumber, StreetName, StreetType, ParcelNumber, WorkType, OccType, ADU,
   UnitsAdded, NumberUnits, WorkDescription, IssuanceDate, FinaledStatus, FinaledDate`.
   (Column names are normalized to the no-space form the notebooks rename to — e.g. `Work Type`→`WorkType`,
   `Parcel Number`→`ParcelNumber`. `OccType` and `ADU` are included because `is_housing`/`net_units` need
   them.)
3. **Typing applied:**
   - `IssuanceDate`, `FinaledDate` → real dates. **The `MM/DD/YYYY`-vs-ISO mixed-format fix is applied**
     (issuance was `MM/DD/YYYY`, finaled was ISO datetime; both parsed via `pd.to_datetime`). CSV renders
     them as `YYYY-MM-DD`; parquet as `datetime64`.
   - `UnitsAdded`, `NumberUnits` → nullable integers (`Int64`).
   - all other fields → trimmed strings.
4. **Dedup applied:** **32,202 raw rows → 30,764 rows, one per `PermitNumber`.** A permit can appear in
   both files (e.g. `B2019-05575`, finaled-status blank in the 2018–2022 file, finaled `2023-08-08` in
   the 2023–2025 file). The kept row is the **most-complete record per permit** — the one with the
   **latest `FinaledDate`** (so the completion date is never lost to a stale earlier row).

## What this is NOT

- **Not the spine.** It is still **per-permit** (30,764 permits), not per-building. JN3 builds the
  building spine (1,385) from it. A clone using `permits_clean` runs JN2 (keys) → JN3 (spine, `net_units`)
  → JN4–JN6 unchanged.
- **Not a substitute for the shared modules.** It carries no logic — `net_units`, `is_housing`,
  `normalize_address`, `cycle_for_date` still come from the real modules (`housing_predicates`, `s0_keys`,
  `housing_rules`).

## Fidelity check (it really is "where JN1 ends")

Loading `permits_clean.parquet` and running the pipeline reproduces the canonical results exactly:

> spine = **1,385** buildings · completions = **951** — identical to JN3/JN4 built from the raw feed.

## Regenerate

Deterministic from the raw `.xlsx`; re-run the generator (read-only on the canonical DBs) any time the
raw feed is refreshed. Requires `pyarrow` for the parquet output (`pip install pyarrow`).
