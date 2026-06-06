# CY2021 CO Units — City PDF vs State CKAN Reconciliation — 2026-06-05

**Read-only analysis. No canonical DB touched.** Reconciles the **Certificate of Occupancy (CO)
unit counts** for Berkeley CY2021 between the city's *filed* APR PDF (the primary source) and the
state's *published* CKAN portal (the verification target). They do not match — and each holds
completions the other lacks.

## Sources
- **City PDF (primary):** `2022-08-16 - Final - CY 2021 APR (Housing Element) - Berkeley_0.pdf`
  (fetched from berkeleyca.gov; saved at `~/berkeley-data-staging/pdf/2022-08-16_CY2021_APR_Berkeley.pdf`).
  **Table A2, Column 12** = "# of Units issued Certificates of Occupancy or other forms of readiness."
- **State CKAN (verification target):** `hcd_apr_mirror.db` `table_a2` (pulled 2026-05-26); confirmed
  identical to the **live** HCD CKAN endpoint (resource `fe505d9b-8c36-42ba-ba30-08bc4f34e022`,
  260 rows for 2021 — live == mirror).
- **Our v2 reconstruction:** `berkeley_housing_v2.db` (`0371c3be`), for context.

## Headline numbers
| Source | CY2021 CO units | Basis |
|---|--:|---|
| **City PDF — Table A2 col 12** | **275** | summed manually past the broken total cell (±1 at the ADU tail) |
| State CKAN — deduped by APN | 323 | per-parcel max of `CO_*_INCOME` columns |
| State CKAN — raw rows | 331 | sum across all rows |
| Our v2 (ADU-scope only) | 107 | 2021 majors deferred; not comparable as a total |

**The PDF's own printed total is unusable:** Column 12's total cell renders **`#VALUE!`** (an Excel
formula error). The only way to get the city's CO total is to sum the column by hand — which is what
this analysis does. The column reads, in row order: **1812 University (44), 2628 Shattuck (78),
2510 Channing (36)**, 2597 Telegraph (14), 1632 Prince (7), then a long tail of 1-unit ADUs
(9 rows >1 unit summing 189, plus 86 one-unit rows = 275).

## The two published numbers do not reconcile
PDF **275** vs CKAN deduped **323** — a 48-unit gap that is **not** a simple offset. Joining the two
sets by 12-digit `apn_norm`:

| Bucket | Parcels | Note |
|---|--:|---|
| **AGREE** (same parcel, same units) | 77 | the shared, consistent core |
| **DISAGREE** (same parcel, different units) | 8 | see below |
| **PDF only** (in city PDF, absent from CKAN) | 4 | **82 units**, incl. the two big ones |
| **CKAN only** (in CKAN, absent from city PDF) | 28 | **149 units**, incl. 2580 Bancroft (122) |

### PDF-only — completions the city filed but never reached the state portal (82u)
- **1812 University — 44u** (APN 057 201602000, CO 8/31/2021) — a full ent→BP→CO row in the PDF;
  CKAN has only an unrelated 2-unit 2025 CO at this APN.
- **2510 Channing — 36u** (CKAN: no record at this APN, any year).
- plus 2 one-unit ADUs.

### CKAN-only — in the state data but absent from the city's own PDF (149u)
- **2580 Bancroft — 122u** — **not anywhere in the CY2021 PDF** (full-text searched). This single
  project is the largest CO in CKAN's 2021 set, yet the city's filed document does not contain it.
- 27 additional one-unit ADUs present in CKAN but not the PDF column.

### DISAGREE — same parcel, different counts
| Address | PDF | CKAN |
|---|--:|--:|
| 2597 Telegraph | 14 | 10 |
| 2813 Channing | 8 | 2 |
| 1632 Prince | 7 | 1 |
| 1811 Sixty-Third | 3 | 2 |
| 1412 Harmon | 2 | 1 |
| 2116 Allston | 1 | 2 |
| (two Fifth St ADUs) | 2 | 1 |

## Interpretation
Between the city's **filed PDF** and the state's **published portal**, the CO record was altered:
~82 units of completions present in the city document never made it to CKAN (including a 44-unit
building), a 122-unit project appears in CKAN that is **not in the city's own filing**, and eight
parcels carry different counts. Neither published total is internally reliable — the PDF's is a
broken cell (`#VALUE!`), and CKAN's 323/331 rests on a row set that diverges from the source
document. This is a concrete data-integrity problem in Berkeley's published CY2021 housing numbers,
and it is exactly the class of error this project's independent, primary-source reconstruction
exists to surface.

**Note (verified-before-characterized):** the PDF total (275) is *lower* than CKAN (323), the
opposite of the initial expectation. The driver is 2580 Bancroft (122u, CKAN-only), which more than
offsets the two large PDF-only completions (1812 University 44u + 2510 Channing 36u). Reported as
the data shows, not as anticipated.

## Method & caveats
- **PDF extraction:** PyMuPDF word-coordinate binning. Table A2 is rendered **rotated 90°** (rows run
  along the x-axis; columns are y-bands). Column 12 (CO units) sits at y0≈299.9; anchors verified
  (1812 University→44, 2628 Shattuck→78, 2510 Channing→36). The ±1 uncertainty is a single borderline
  1-unit ADU token at the tail; it does not affect any conclusion.
- **CKAN sum** uses the bug-hardened rule: sum `CO_*_INCOME` columns only (never date columns),
  match by normalized APN. Live == mirror confirmed.
- **CKAN remains the verification target, never a data source.** No CO units, dates, or affordability
  were copied from CKAN into anything. v2 is unchanged.

## Artifacts (read-only outputs)
- `data/apr/2021/cy2021_pdf_table_a2_col12_co.csv` — every non-zero Column-12 CO row from the PDF
  (page, apn_norm, address, co_date, co_units), 95 rows.
- `data/apr/2021/cy2021_pdf_vs_ckan_co_reconciliation.csv` — parcel-level join
  (apn_norm, address, pdf_co, ckan_co, status) across all 117 distinct parcels.
