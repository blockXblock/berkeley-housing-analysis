# CY2021 CO — Multi-Source Audit (City PDF · State CKAN · Accela · CPRA) — 2026-06-05

**Read-only analysis. No canonical DB touched.** Reconciles Berkeley's CY2021 Certificate-of-Occupancy
(CO) record across **four sources** and records what each can and cannot establish. *(Supersedes the
earlier PDF-vs-CKAN-only draft of this file — the CPRA and Accela passes materially revised the
conclusions, especially the "PDF total = 275" reading, now understood to be inflated.)*

## Sources
1. **City PDF (primary filing):** `2022-08-16 - Final - CY 2021 APR (Housing Element) - Berkeley_0.pdf`
   (berkeleyca.gov; saved at `~/berkeley-data-staging/pdf/2022-08-16_CY2021_APR_Berkeley.pdf`).
   Table A2 **Column 12** = "# of Units issued Certificates of Occupancy."
2. **State CKAN (verification target):** `hcd_apr_mirror.db` `table_a2` (pulled 2026-05-26; confirmed
   == live HCD endpoint). **Never a data source.**
3. **Accela** (Chrome scrape by John): the city permit portal.
4. **CPRA** (primary permits): `data/raw/cpra-downloads/BP_Annual Permit Report-2018-2022.xlsx` +
   `…2023-2025.xlsx` — Finaled dates, unit counts, work type, straight from the permit record.

## 1. proj887 (Logan Park South, 69u) — RE-VERIFIED ✅ SOLID
The Accela "not found" was a **search artifact**, not a bad ingest. The analyst tried `B2019-04100`
(a different permit, which resolves to 2950 Linden). Our ingest was keyed on **B2021-03302**, which
CPRA confirms unambiguously:

| Field | CPRA (B2021-03302) |
|---|---|
| Address | **2352 Shattuck Ave** |
| APN | **055 189504100** (South parcel) |
| Description | *"Phase II of **South Building**: … Super Structure, MEP, landscaping … Eight-story mixed-use"* |
| Units | **69** · Finaled **2023-08-08** · Work Type New |

proj887 rests on a clean primary match. It is a **CY2023** completion (as recorded). **CY2023 = 701
stands, unaffected.**

## 2. CY2021 "majors" — only TWO are genuine 2021 completions
Looked up in CPRA by address **and** APN:

| Project | Claimed | CPRA permit | Units | Finaled | Verdict |
|---|--:|---|--:|---|---|
| **2628 Shattuck** | 78u | B2019-01950 "Phase II superstructure, 6-story mixed-use" | **78** | **2021-07-16** | ✅ **Genuine CY2021** — all sources agree (PDF=CKAN=CPRA=78) |
| **2580 Bancroft** | 117u | B2019-00478 "Phase II, new 8-story 117-unit building" | **117** | **2021-11-29** | ✅ **Genuine CY2021** — city-PDF-omitted; CKAN's **122 overstates by 5** |
| **2023 Shattuck** | 48u | B2020-03911 "new 7-story, 48 units" | 48 | **2023-08-16** | ⚠️ **MIS-YEARED → CY2023**, not 2021 |
| **1173 Hearst** | 18u | B2020-02941/-02942 (2 duplexes) + B2020-02975 (SFR remodel) | ~4 net-new | **2023** (remodel 2022-12-12) | ⚠️ **CY2023, ~4u** — 18u figure unsupported by primary data |
| **3020 San Pablo** | 29u | B2015-00694 "Phase II of III, 5-story" | — | *no final in CPRA* | ❌ **UNVERIFIABLE** — legacy 2015 permit below CPRA's 2018 horizon |

Notes:
- **2628 Shattuck:** Phase I foundation B2019-01150 Finaled 2021-02-03; Phase II superstructure
  (the 78 units) Finaled 2021-07-16. The PDF's CO date (2/3/2021) is the Phase-I final; CKAN/CPRA
  use the Phase-II final — same project, same 78 units, genuine 2021.
- **2580 Bancroft:** absent from the city's own CY2021 PDF (full-text searched), present in CKAN at
  122. CPRA settles it at **117** (permit-stated, `UnitsAdded=117`). CKAN's +5 is unexplained overcount.
- **3020 San Pablo:** do **not** conflate with 3000 San Pablo (B2020-04316, 78u, Finaled 2023-06-05 =
  proj168, a CY2023 project). 3020 is a separate, older parcel (053 163400401) with no finaled permit
  in the CPRA window.

## 3. The PDF-inflation mechanism (from the Accela/permit scrape)
The city PDF's Column-12 figures are frequently **gross building totals, not net-new units** — it
systematically **overstates**. Confirmed cases where PDF > CKAN, and the **permit record sides with
CKAN's (lower) net-new figure**:

| Address | PDF col-12 | CKAN / net-new |
|---|--:|--:|
| 1812 University | 44 | 2 (gross 44-unit building; net-new 2 after replacement) |
| 2597 Telegraph | 14 | 10 |
| 1632 Prince | 7 | 1 |
| 2813 Channing | 8 | 2 |

This is the same signal as the parcel-join **DISAGREE** bucket below: wherever the two diverge, the PDF
is high because it counts the whole building. **Consequence: the PDF column-12 hand-sum (275) is itself
inflated** — it is *not* a clean "true total," contrary to this file's earlier draft.

### PDF↔CKAN parcel join (by 12-digit `apn_norm`, 117 parcels)
| Bucket | Parcels | Note |
|---|--:|---|
| AGREE | 77 | shared consistent core |
| DISAGREE | 8 | PDF gross > CKAN net-new (the inflation cases above) |
| PDF only | 4 | 82u — incl. 1812 University (44, gross) + 2510 Channing (36) |
| CKAN only | 28 | 149u — incl. **2580 Bancroft (122)** + 27 one-unit ADUs |

Totals: PDF col-12 = **275** (inflated), CKAN deduped = **323** (raw rows 331), v2 = **107** (ADU-scope).

## 4. Conclusion — no single source yields a clean CY2021 total
Every source is individually defective: the **PDF** inflates (gross-not-net) and its total cell is a
broken `#VALUE!`; **CKAN** drops real completions (omits 1812 University's building, 2510 Channing) and
overcounts others (2580 Bancroft 122-vs-117); **Accela** can't see pre-2022 records; and **CPRA** has a
hard 2018 horizon. What *is* verified:
- **(a) the PDF-inflation mechanism** — gross building totals, not net-new; permit sides with CKAN.
- **(b) the 2580 Bancroft omission** — a 117-unit 2021 completion missing from the city's own PDF.
- **(c) most "missing majors" were mis-attributed years, not missing data** — 2023 Shattuck and
  1173 Hearst are CY2023; 3020 San Pablo is pre-horizon legacy.

**CY2021's verifiable major surface = 2628 Shattuck (78u) + 2580 Bancroft (117u) = 195u**, both
primary-permit-confirmed (Finaled 2021-07-16 and 2021-11-29). The rest dissolve into other years or
outside-our-data. Neither major is in v2 yet — they are the deferred **2021-majors** scope gap (v2's
CY2021 = 107 remains ADU-only).

## 5. Methodological note — CPRA beats Accela for older years
**Accela portal coverage thins markedly pre-2022.** Three records Accela could not surface were
resolved cleanly from **CPRA** (which reaches back to 2018): 2628 Shattuck (B2019-01950), Logan Park
South (B2021-03302), and the 1173 Hearst structures (B2020-029xx). **For any pre-2022 verification,
CPRA is the primary source of record; treat Accela "not found" as non-dispositive for older permits.**

## 6. ⚑ CY2023 follow-up (separate check — flagged, not actioned)
2023 Shattuck (48u, Finaled 2023-08-16) and 1173 Hearst (~4u net-new, Finaled 2023) surfaced here as
*mis-yeared 2021 majors* but are genuine **CY2023** completions. **Verified read-only: neither is in v2**
(by address or APN). So they are **additions, not already in CY2023 = 701** — ingesting 2023 Shattuck
alone would raise CY2023 by **+48u**. Recommend a dedicated CY2023 majors-completeness pass (gated,
primary-confirmed) before relying on 701 as final. *(2628 Shattuck and 2580 Bancroft are likewise
absent from v2 — the CY2021 deferred majors.)*

## Artifacts (read-only outputs)
- `data/apr/2021/cy2021_pdf_table_a2_col12_co.csv` — 95 non-zero Column-12 CO rows from the PDF.
- `data/apr/2021/cy2021_pdf_vs_ckan_co_reconciliation.csv` — parcel-level PDF↔CKAN join (117 parcels).
