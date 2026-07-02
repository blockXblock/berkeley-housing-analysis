# The PDF↔CKAN completeness sweep (CY2018-2025) — the adjudicated city record takes shape

**Date:** 2026-07-03 · **Who:** background agent (validated extractor) + CC · **Read-only.**
Artifacts: `data/audit/pdf_ckan_sweep_2026-07-03.csv` (155 divergent/only rows, all years);
extractor promoted to `scripts/v4/apr_pdf_a2_extract.py` (fitz words + rotation-matrix correction +
APN-banded rows + per-page-slice column mapping; Excel column-slice page groups merged by row index).

## Validation
All four CY2021 anchors PASS (1812 University B2014-05786 CO 44 @8/31/2021; 2510 Channing 36;
2628 Shattuck 78 @2/3/2021; Bancroft absent). **The June-5 "hand-sum 275" anchor is itself
SUPERSEDED: correct CY2021 PDF CO = 295** — the hand-captured artifact missed 21 one-unit ADU rows on
the last page, each independently confirmed by CKAN with identical dates (append-only correction owed
to the June-5 doc). CY2023 = 715 ✓.

## The shape of the divergence (CO buckets)
**CY2022, 2024, 2025 reconcile PERFECTLY (0 diverge / 0 only-rows). CY2023 has one row — a city
print defect (3038 Benvenue: printed total cell = 0, income column = 1).** The divergence is
concentrated in the EARLY filings:
- **CY2018:** the PDF's A2 is ENTITLEMENTS-ONLY (BP/CO blank in print) → CKAN_ONLY 64 rows/229u is
  structural, incl. the biggest single row anywhere: **2001 Fourth St 152u (B2016-03894, our C2-T1
  building) — in CKAN, absent from the city's own PDF.**
- **CY2019:** CKAN_ONLY 24/225u (2539 Telegraph 70, 2124 Bancroft 50, 2526 Durant 44, 2740 San Pablo
  23 — the held one! — 2013 Second 19) + print milestone-column inversions (CO dates in ENT column).
- **CY2021:** exactly the June-5 audit's picture: PDF_ONLY 80u (Overture 44 + Den 36); CKAN_ONLY 128u
  (Bancroft 122); DIVERGE = the gross-vs-net trio.
- City print defects found where income columns carry units the total cell omits — incl.
  **2501 Haste (El Jardin): the CY2020 PDF DOES carry the 55 (income col, date 8/19/2020, = CKAN)** —
  the city filed it consistently in both sources; one more corroboration of our grounded 55.

## The convergence (PRELIMINARY — next session computes it precisely)
The adjudicated city record ≈ CKAN (4,022) + PDF-only CO rows CKAN lacks (~84u: Overture 44 + Den 36
+ four small rows) ≈ **4,106 — vs our 4,103.** Two independent reconstructions of eight years of
housing completions, landing within a handful of units, with every remaining difference named
(gross-vs-net trio, the Bancroft-family +5s, San Pablo 23 held, Acheson-A convention). To finalize:
per-row union arithmetic, the San Pablo CY2019 CKAN row's bearing on its hold, and a baseline that
records the adjudicated city figure alongside the CKAN one.

## Caveats (agent's, honest)
Extractor reads the printed col-12 total (city sometimes leaves it 0/blank while income columns carry
units — that class needs income-column sums to fully resolve); CY2019 print has data-entry inversions;
2022 BP 882-vs-887 unadjudicated (Bancroft-family); per-address attribution inside multi-address APN
groups is CKAN's.
