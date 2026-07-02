# The Overture retraction + the comparison-target finding (CKAN is provably incomplete)

**Date:** 2026-07-03 (evening) · **Trigger:** John's NotebookLM pass over the city APR PDFs surfaced a
CY2021 row my adjudication had ruled out · **Class:** honest-retraction + a /ground lesson at the
adjudication layer.

## 1. The retraction
The same-day window-attribution of **B2014-05786 (The Overture, 1808-1812 University, 44u)** is
**RETRACTED**. The CY2021 city APR PDF (p20; APN 057 201602000; tracking **B2014-05786**) credits
**CO 44 units on 8/31/2021** — the city counted the building in-window, on exactly our permit-finaled
grain, date, and permit number. My "city credits it nowhere in 2018-2025" premise was true of the
**CKAN mirror**, not of the **city**: the CKAN copy is missing the row — a defect the
**2026-06-05 multi-source audit had already documented, naming this building AND The Den.**
`window_attributions.json` now carries the retraction (mechanism kept, list empty); baseline
2026-07-03c drops the adjustment. The physical early-occupancy evidence (built 2016-17: listings, the
2017 TI permit) stays recorded but is moot for the comparison — both records agree at 2021-08-31/44.
Streetview note (John): the building presents an entrance at 1801 University at Grant — one more
address alias for the family (1801/1808/1812 University; APNs -020 and -021-01).

## 2. Permit-family correspondence with the APR narrative (John's question)
Same permit numbers, yes — the city's rows and ours cite the same family:
| APR narrative (NotebookLM) | Our permit record | Verdict |
|---|---|---|
| CO Final 44u **8/31/2021** | **B2014-05786** permit_finaled **2021-08-31**, 44u | EXACT match (permit#, date, count) |
| "CO Phase 1, 2u, 5/22/2020" | B2019-05321 permit_ISSUED 2020-05-22 (2 studios) | Same row; the APR's 2020 entry is its **BP** milestone — NotebookLM mislabeled it CO |
| "Duplicate completion 2u, 9/2/2025" | B2019-05321 permit_finaled 2025-09-02 | **Not a duplicate** — the real CO of the conversion (BP 2020 → CO 2025 is one project across years, which is how Table A2 works) |
| Entitlement 44u, 7/11/2019 | (mirror: ZP2018-0201, ENT 2019-09-16) | City-side entitlement family; dates differ between PDF and CKAN |
| "BP issued 2u, 06/24/2019" | no matching event (B2019-05321 submitted 2019-12-09) | unmatched; likely a PDF/reading artifact |
NotebookLM's "systemic redundant reporting" for this building is mostly **milestone-column structure**
(the same project legitimately appears in BP-year and CO-year rows), not redundancy — but its core
timeline is real and led straight to the CKAN hole.

## 3. THE COMPARISON-TARGET FINDING (the durable one)
The June-5 audit's conclusion now binds the whole reconciliation: **no single city source yields a
clean total.** The CKAN mirror — our reconcile-target, the source of "city 4,022" — **drops real
completions** (CY2021 PDF-only rows: 82u incl. The Overture 44 and The Den 36) **and inflates others**
(2580 Bancroft 122 vs permit-stated 117 — which exactly explains our +5 Bancroft delta). The PDF
inflates differently (gross-not-net in Column 12). **Consequences:**
- "**vs city 4,022**" carries false precision; the honest unit of comparison is the **per-row
  adjudication ledger** we have been building — totals are summaries, not truths.
- The Den divergence is now fully explained: city PDF credited **36 @ CY2021** (CofO grain, CKAN
  dropped the row); we count 0 until its completion permit finals (permit-final grain), 40 when it
  does. Grain difference + CKAN hole + a 36-vs-40 count divergence to note — the demote stands.
- The baseline gains a `city_target_defects` documented entry; a **CY-by-CY PDF↔CKAN completeness
  sweep** (extending June-5's CY2021 work to 2018-2025) is the queued work item that would replace
  the CKAN-only city total with an adjudicated one.

## 4. The /ground lesson (second instance, sharper)
Yesterday's adjudications verified against the MIRROR while a month-old audit doc
(`2026-06-05_cy2021_apr_pdf_vs_ckan_co.md`) had already: named both buildings, established the
PDF-vs-CKAN divergence class, and adjudicated Bancroft's +5. The /ground checklist gains teeth from
this: **"check docs/audit/" means grep for the SUBJECT (address/permit), not just the topic.**
Also corrected (append-only) in the June-5 doc itself: its "1812 University net-new 2" line conflated
the conversion permit with the building; the family nets 44 + 2.
