# The −52 gap, fully decomposed — the "~−29 residual" was a NET, not a thing

**Date:** 2026-07-03 · **Who:** CC (read-only analysis; no writes) · **Inputs:** live v4 (CO 3,970,
baseline `2026-07-02c`) × the CKAN mirror (`table_a2`, city CO 4,022). Artifacts:
`scratch/2026-07-03/{parcel_deltas,address_deltas,city_only_rows,ours_only_rows}.csv`.

## Method
Per-parcel unit-delta join: both sides keyed by `to_canonical_apn(APN,'Alameda')` with normalized-address
fallback, then address-level netting (collapses same-building different-APN pairs, e.g. the Enclave's
city `-004` vs permit `-045` sub-parcels). **Deltas sum to the gap exactly: +293 city-more / −241
ours-more = −52.** ⚠ Method lesson: the county key is CASE-SENSITIVE (`'Alameda'`, not `'alameda'`) and
my first pass silently degraded to address-only matching by swallowing the raise — the canon function
was never at fault. (Also true of the 2026-07-02 Stage-1 phase-guard; its two proposals were
independently verified by direct queries, so no damage.)

## CITY-MORE (+293): dominated by a SYSTEMATIC ADU-conversion recall gap
- **159 addresses × +1u** (+ a tail of 2-4u cases ≈ +60 more): city credits a completed unit; we count 0.
  **Probe result: 158/159 EXIST in our data with finaled permits — classified `alteration`** (garage/
  basement/in-law conversions and legalizations). NOT a coverage gap (1 address truly absent). This is
  the classifier's conversion→ADU recall gap, previously guessed at "~4" and separately suspected in the
  `v4_adu_flag_nonhousing_role` bijection bucket — it is real and ~160-220 units over 2018-2025.
- **Acheson Bldg A rehab (2131 University, +37, CY2022):** city counts the historic rehab's 37 units; we
  classified `alteration/0` (rehabilitation of existing building). Genuine adjudication: were the units
  uninhabitable/vacant pre-rehab (city's net-new framing) or occupied stock? B2015-02995, NumberUnits=37.
- **2002 Addison +7 (2018) · 2580 Bancroft city 122 vs ours 117 (+5)** · misc 2-4u rows.
- **2740 San Pablo +23 = the HELD item** ✓ (accounted, not unexplained).

## OURS-MORE (−241): four big buildings + 2024-25 timing singles
- **1808 University −44 (B2014-05786, the dedup47 building):** city credits it NOWHERE in 2018-2025.
  Window-timing suspect: a B2014 permit whose building likely CO'd pre-2018 (before the A2 window);
  our counted "finaled 2021" event may be an administrative re-final. ADJUDICATE (could be a legitimate
  −44 window correction on our side).
- **0 San Pablo −41 (B2021-02423, the C2-T2/multifam group-living):** city reports it nowhere — the
  city did NOT file the GLA it elsewhere files (Enclave!). City-side inconsistency on the GLA convention;
  our count stands (convention-flagged); document as city-under.
- **2510 Channing −40 (B2019-01789):** we count 40, city zero. UNINVESTIGATED — adjudicate.
- **1367 University −39 (B2022-04366, finaled 2025):** city 2025 filing lag (mirror pulled 2026-06-17).
  TIMING, expected to self-resolve at the next mirror refresh.
- **~20 single-ADU rows finaled 2024-2025:** same city-filing-lag class.
- Known convention deltas: 2556 Telegraph 22v24 (live-work), 739 Channing 17v22, 1601 Oxford 34v37.

## What this means
The reconciliation's remaining distance is NOT a mystery number; it is two named workstreams:
1. **ADU-conversion recall calibration** (the big one): review the ~160 alteration-classified finaled
   permits at city-credited addresses (C2-style: description-grounded, curated into a calibration file,
   applied via the ledger/method path). This would move our CO UP by ~+160-220 — and with the four
   big adjudications possibly moving us DOWN (−44 window, etc.), the endpoint is a reconciliation
   explained line-by-line in BOTH directions, not merely a small net.
2. **Four big-building adjudications:** 1808 University (window), 2510 Channing (what is it?),
   Acheson A rehab (+37 convention), plus the city-side documentation of 0-San-Pablo's 41.
**Doctrine note:** the city rows only ENUMERATE which of our alteration permits to review; every
recount must ground in the permit's own description/documents (the C2/grounded_counts discipline).
