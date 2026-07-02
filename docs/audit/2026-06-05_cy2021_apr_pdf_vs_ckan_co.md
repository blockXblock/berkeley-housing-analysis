# CY2021 CO — Multi-Source Audit (City PDF · State CKAN · Accela · CPRA) — 2026-06-05

**Read-only analysis. No canonical DB touched.** Reconciles Berkeley's CY2021 Certificate-of-Occupancy
(CO) record across **four sources** and records what each can and cannot establish. *(Supersedes the
earlier PDF-vs-CKAN-only draft of this file — the CPRA and Accela passes materially revised the
conclusions, especially the "PDF total = 275" reading, now understood to be inflated.)*

**Revised 2026-06-06:** §6 rewritten after a CY2023 majors-completeness pass — the earlier
"2023 Shattuck / 1173 Hearst are additions" flag is **retracted** (both are present and counted; the
flag came from a silent query failure), the systematic CPRA↔v2 sweep is recorded, and 2435 San Pablo
(40u GLA) is adjudicated.

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

## 6. CY2023 majors-completeness pass (run 2026-06-06) — flag RETRACTED + systematic sweep

### 6a. ⚠️ RETRACTION — 2023 Shattuck and 1173 Hearst are PRESENT and COUNTED, not additions
An earlier version of this doc flagged 2023 Shattuck (48u) and 1173 Hearst as "verified NOT in v2 →
additions." **That was wrong.** Checked by **APN** (not the errored query), both are already in v2 and
already inside CY2023 = 701:

| Address | APN | v2 project | Units | CO date | In 701? |
|---|---|---|--:|---|:--:|
| 2023 Shattuck | 057 203400800 | **proj 380** | 48 | 2023-08-16 | ✅ yes |
| 1173 Hearst | 057 208601300 | **proj 379** | 2 | 2023-03-15 | ✅ yes |

**Had the gated add proceeded, it would have DOUBLE-COUNTED 2023 Shattuck (+48u erroneously).**

**Why the original flag was wrong — a silent query failure.** The "not in v2" check used
`SELECT … stage FROM v_projects_flat …`, but the view's column is `status_code`/`status_label`, not
`stage`. SQLite errored; with stderr suppressed it returned **zero rows**, which was misread as
"absent." This is the **same failure class as the phantom "2190"** (a SQL artifact mistaken for data):
a malformed query producing a clean-looking but false result. **Lesson reinforced: confirm presence by
APN against a *valid* query before concluding "missing," and never read an empty result from a
stderr-suppressed query as evidence of absence.**

### 6b. Systematic sweep — v2's MAJOR coverage for 2023–2025 is complete
CPRA new-construction permits Finaled 2023–25 (units>0), left-joined to v2 CO by APN: 228 unmatched by
`(apn, permit-year)`, but the split is decisive:

| Class | Total | Majors ≥5u | Small <5u |
|---|--:|--:|--:|
| **WRONG_YEAR** (parcel already has a v2 CO in another year) | 192 | 28 | 164 |
| **APN-ABSENT** (no v2 CO at parcel, any year) | 36 | 2 | 34 |

- **All 28 WRONG_YEAR "majors" are false positives — every one verified already in v2.** They flag only
  because a *secondary* permit (PV solar, standby generator, tenant improvement, deferred submittal) on
  the same parcel finaled in a later year. Spot-checked present: 2150 Kittredge (169u), 1951 Shattuck
  (163u), 3030 Telegraph (144u), 2000 University (82u), 2590 Bancroft (87u), 2100/3000 San Pablo,
  2072 Addison, 2440 Shattuck (40u), …
- **The 2 APN-ABSENT "majors":** (i) **2352 Shattuck "Phase I" (69u, B2019-05575)** — *not additional*;
  it is the same South Building already counted as **proj887** (Phase II, 69u). (ii) **2435 San Pablo**
  — adjudicated below.

**Conclusion: of ~228 new-construction completions, v2 is missing exactly ONE major — 2435 San Pablo
(below). The one-at-a-time finds (Logan Park South, etc.) have been systematically swept; no other
hidden majors.**

### 6c. ADJUDICATION — 2435 San Pablo (CPRA "0 San Pablo", APN 056 192801900) → INCLUDE, 41u, CY2025
- **Permit B2021-02423** (CPRA): *"New 4-story group living accommodations with **40 sleeping units and
  one manager's dwelling unit**,"* **OccType R-2 Residential: Permanent, Multi-Unit (3+ Units)**,
  Work Type New, CO required = Yes, **Finaled 2025-03-20**, val $2.8M.
- **The city's own APR (CKAN, live + mirror) counts it:** real address **2435 San Pablo**,
  **UNIT_CAT "5+" (multifamily), Tenure Renter, 41 units** (BP 2022-08-12; no CO row yet — the city's
  CO filing lags the 2025-03-20 final).
- **Verdict: INCLUDE — this is private permanent multifamily housing, NOT institutional group quarters.**
  Reasoning: the UC exclusions (proj 165/170/171/177) are 300–750-unit university dormitories — *institutional
  group quarters*. 2435 San Pablo is a **private R-2 "Permanent, Multi-Unit" building** that the city
  classifies as **"5+" multifamily** and counts as **41 dwelling units**. "Group Living Accommodations"
  here is the *building type* (SRO/co-living), not a group-quarters exclusion trigger; HCD and the city
  count it as housing. **Count = 41** (40 sleeping units + 1 manager's dwelling), matching the city's BP
  figure. **Year = CY2025** (Finaled 2025-03-20). Genuinely absent from v2 (parcel not loaded).
- **Status: open item — NOT ingested.** If accepted via a gated add, **CY2025 531 → 572**. (We'd be
  ahead of the city's CO filing here, as with 1367 University — permit-confirmed.)

### 6d. Open items — batched as a separate small-completeness pass (held)
- **1173 Hearst 2nd duplex (+2u):** proj 379 holds one duplex (B2020-02942, 2u); the second
  (**B2020-02941, 2u, Finaled 2023-03-06**) is genuinely absent — a real **+2u** micro-gap (CY2023 → 703).
- **34 APN-absent small (<5u):** 2023:5, 2024:11, 2025:18 — genuinely-missing ADUs/duplexes.
- These are the same "small completeness" class and will be scoped as **one gated pass later**, not a
  2u write now. **Sweep blind spot:** *same-parcel second buildings* (Hearst 2nd duplex, Logan Park
  pattern) hide in WRONG_YEAR because the parcel already has a v2 CO — so **true small-miss ≥ 34 plus
  some same-parcel cases.**
- **2435 San Pablo (41u, CY2025)** is the only *major* in the open queue, pending the §6c verdict.

## Artifacts (read-only outputs)
- `data/apr/2021/cy2021_pdf_table_a2_col12_co.csv` — 95 non-zero Column-12 CO rows from the PDF.
- `data/apr/2021/cy2021_pdf_vs_ckan_co_reconciliation.csv` — parcel-level PDF↔CKAN join (117 parcels).

## 2026-07-03 CORRECTION (append-only): the "1812 University net-new 2" line is SUPERSEDED
The §3 inflation-table row reading 1812 University as "net-new 2 after replacement" **conflated two
permits of one family**: the CKAN 2-unit rows track **B2019-05321** (the LATER retail→2-studio
conversion inside the building, BP 2020, CO 2025) — they are NOT the new building's net. The building
itself is **B2014-05786** ("NEW 36,554 SQFT MIXED USE BLDG, 28,095 RES" — The Overture, replacing two
shops): permit-stated 44 units, CO'd 8/31/2021 per this PDF's own p20 row. **Net-new for the family =
44 (new building) + 2 (later conversion) = 46**, not 2. The PDF-only/CKAN-missing finding for this row
STANDS (CKAN lacks the 44-CO row); the net-vs-gross reading of it is corrected. Full permit-family
timeline: docs/audit/2026-07-03_overture_retraction_and_ckan_target.md.
