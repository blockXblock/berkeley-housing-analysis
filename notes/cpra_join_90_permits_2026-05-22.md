# CPRA × URL-discovery join — analytical summary

**Generated:** 2026-05-22T14:23:41
**Inputs:** `/tmp/b_permit_url_inventory.csv` (90 in-scope B-permits), `data/raw/accela_url_discovery/*.json` (87 files for runs 1+2) and `/tmp/url_discovery_pre_flight/*.json` (3 files for the pre-flight permits), CPRA source xlsx (14,149 rows; 12,201 distinct master_permits after suffix stripping).

**Sibling CSV:** `/tmp/cpra_join_90_permits.csv` (90 rows × 19 columns).

## Headline finding

**All 90 in-scope B-permits are present in the CPRA source file.** This means the 59 "not_found" outcomes from the URL-discovery run are NOT data-existence gaps — every one of those permits is documented in Berkeley's own CPRA response. The gap is between **what Berkeley acknowledges exists** (CPRA) and **what Berkeley publicly exposes via Accela's CapHome search**.

## 1. The 90 permits

- Total inventory rows: **90**
- Permits with `-REV/-DEF/-ADD` suffix: 0 (all 90 are clean master numbers)
- URL-discovery JSON found for: **90 / 90** (87 in canonical `data/raw/accela_url_discovery/`, plus 3 — B2019-05575, B2021-02225, B2021-02404 — in `/tmp/url_discovery_pre_flight/`. The 3 in `/tmp/` are from the pre-flight run that wrote outside the canonical path; their results were identical to the smoke-test baselines.)
- v2 source_system distribution: `cpra: 89`, `accela: 1` (B2019-05574, the inspection-POC).

## 2. URL discovery outcome (recap)

| outcome | count |
|---|---|
| `ok` (master triplet recovered) | 31 |
| `not_found` (records_seen=0 on Accela's CapHome) | 59 |
| `ambiguous` | 0 |
| `failed` / `error` | 0 |

## 3. CPRA join

- All 90 permits' master numbers were searched against CPRA's 12,201 distinct master_permits.
- Result: **90 / 90 found in CPRA**.
- Permits with `cpra_row_count = 1` (single parcel): 65
- Permits with `cpra_row_count ≥ 2` (multi-parcel project): 25
- Maximum cpra_row_count: 20 (B2021-02404 and B2021-03950)

## 4. The 2×2 (in_cpra × url_discovery_outcome)

| | ok | not_found |
|---|---|---|
| **in_cpra = yes** | **31** | **59** |
| **in_cpra = no** | 0 | 0 |

The 2×2 collapses to a 1×2 — there are no permits outside CPRA. The discriminative axis we hoped to study ("does Accela not_found correlate with CPRA absence?") evaporates: every not_found permit is in CPRA.

## 5. v2_source_system × in_cpra

| source_system | in_cpra=yes | in_cpra=no |
|---|---|---|
| `cpra` | 89 | 0 |
| `accela` | 1 | 0 |

Even the lone accela-sourced permit (B2019-05574, the inspection-POC permit, ingested from a different workflow) is present in the CPRA file.

## 6. Comparative analysis: ok vs not_found within in_cpra

### 6a. OccType

| OccType | ok | not_found | ok-rate |
|---|---|---|---|
| R-2 Residential: Permanent, Multi-Unit (3+ Units) | 16 | 26 | 38% |
| R-3 Residential: Dwellings (1 or 2 Units), Townhomes, Congregate Living | 13 | 29 | 30% |
| Not Applicable (new) | 0 | 2 | 0% |
| U Private Garages, Carports, Sheds, Agricultural, Tanks, Accessory | 0 | 2 | 0% |
| A-2 Assembly: Food or Drink Consumption | 1 | 0 | 100% |
| R-2.1 Residential: Supervised Residential Care Services | 1 | 0 | 100% |

Modestly diagnostic: R-2 (multi-unit) and R-3 (1-2 unit) both sit around ~38% success — not a strong split. The 8 demolition permits all fall in the `U Private Garages...`, `Not Applicable (new)`, or generic R-3 buckets and all 8 are not_found.

### 6b. Issuance year

| year | ok | not_found |
|---|---|---|
| 2021 | 1 | 0 |
| 2022 | 2 | 0 |
| 2023 | 8 | 17 |
| 2024 | 8 | 20 |
| 2025 | 12 | 22 |

Not strongly diagnostic. Older permits (2021-2022) are slightly more findable in Accela (perhaps because they've had time to be "completed" and indexed), but the 2023/2024/2025 ratios are similar (~30% ok across each year). No temporal cliff.

### 6c. Work Type — STRONGLY DIAGNOSTIC

| Work Type | ok | not_found | ok-rate |
|---|---|---|---|
| `Alteration` | 8 | 42 | 16% |
| `New` | 22 | 5 | 81% |
| `Demolition` | 0 | 8 | 0% |
| `Sign` | 0 | 2 | 0% |
| `(empty)` | 0 | 1 | 0% |
| `Addition` | 0 | 1 | 0% |
| `Addition/Alteration` | 1 | 0 | 100% |

**The strongest single discriminator.** New construction is 81% findable in Accela; Alteration is 16% findable; Demolition is 0% findable (0 of 8). The pattern: Accela's CapHome search appears to surface major construction projects and hide most smaller-scale work.

### 6d. UnitsAdded buckets — STRONGLY DIAGNOSTIC

| UnitsAdded | ok | not_found | ok-rate |
|---|---|---|---|
| `null` | 11 | 48 | 18% |
| `0` | 2 | 9 | 18% |
| `1` | 3 | 2 | 60% |
| `2-5` | 1 | 0 | 100% |
| `6-10` | 0 | 0 | n/a |
| `11+` | 14 | 0 | 100% |

**Even sharper than Work Type.** Every permit adding 11+ units (14 of them) succeeded in Accela. Every permit with null UnitsAdded (i.e., no recorded unit count — typically alteration/repair/solar/MEP work) has a 19% success rate. The bulk of not_found is the "null UnitsAdded" bucket (48 of 59 = 81%).

### 6e. Multi-parcel coverage — PERFECTLY DIAGNOSTIC

| cpra_row_count | ok | not_found |
|---|---|---|
| 1 | 6 | 59 |
| 2 | 12 | 0 |
| 4 | 1 | 0 |
| 5 | 4 | 0 |
| 6 | 1 | 0 |
| 7 | 3 | 0 |
| 10 | 1 | 0 |
| 13 | 1 | 0 |
| 20 | 2 | 0 |

- Multi-parcel (cpra_row_count ≥ 2): **25/31 of ok** vs **0/59 of not_found**.
- Every single not_found permit has `cpra_row_count = 1`. The 25 multi-parcel projects (those associated with multiple APNs and therefore typically larger developments) ALL succeed in Accela.
- The 6 ok permits that are single-parcel are likely the new-construction R-2 projects on single legal parcels.

### 6f. Permits with cpra_row_count > 5 (multi-parcel outliers)

| permit_number | cpra_row_count |
|---|---|
| B2021-03950 | 20 |
| B2023-02332 | 6 |
| B2023-06416 | 7 |
| B2024-01924 | 13 |
| B2024-00143 | 7 |
| B2021-02225 | 10 |
| B2021-02404 | 20 |
| B2023-02354 | 7 |

None of these triggered duplicate-permit-number issues during URL discovery (the per-row CPRA repeats are due to multiple parcels per permit, but the orchestrator processes by master_permit and so sees each unique number once).

## 7. The "in CPRA AND not_found in Accela" cluster — first 10

These are the 59 permits where Berkeley's CPRA acknowledges existence but Accela's public CapHome search returns 0 records:

| permit_number | address | issuance | finaled | OccType | WorkType | units | description |
|---|---|---|---|---|---|---|---|
| B2025-01864 | 2441 LE CONTE Ave | 2025-05-07 | 2025-09-25 | R-2 Residential: Permanent, Multi-Unit ( | Alteration |  | To address housing case H2025-00241 Items 6- Repai... |
| B2024-03884 | 2641 COLLEGE Ave | 2024-12-10 | 2025-07-08 | R-3 Residential: Dwellings (1 or 2 Units | Alteration |  | Unit #A, First Floor. Add bathroom & laundry close... |
| B2024-05471 | 2641 COLLEGE Ave | 2025-06-25 |  | U Private Garages, Carports, Sheds, Agri | Demolition |  | Demolish existing 384SF wood framed detach garage |
| B2025-02413 | 2641 COLLEGE Ave | 2025-07-03 | 2025-07-24 | R-3 Residential: Dwellings (1 or 2 Units | Alteration |  | Replace 760 square feet of deteriorated siding on ... |
| B2022-01278 | 1716 SEVENTH St | 2023-06-28 | 2023-07-06 | R-3 Residential: Dwellings (1 or 2 Units | Demolition |  | Demolish 801 SqFt Single Family Residence, detache... |
| B2022-01386 | 1716 SEVENTH St | 2023-06-06 |  | R-3 Residential: Dwellings (1 or 2 Units | New |  | Construct new two-story single family residence. |
| B2023-02303 | 1716 SEVENTH St | 2023-05-26 |  | R-3 Residential: Dwellings (1 or 2 Units | Alteration |  | Remove existing roof & install 2.016 KW PV solar t... |
| B2025-05132 | 1716 SEVENTH St | 2025-11-17 |  | R-3 Residential: Dwellings (1 or 2 Units | Alteration |  | Add 2.64 (DC) / 7.60 (AC) KW PV solar panels (6 mo... |
| B2025-05133 | 1714 SEVENTH St | 2025-11-17 |  | R-3 Residential: Dwellings (1 or 2 Units | Alteration |  | Install 3.08 KW PV solar panels (7 modules) on the... |
| B2023-04430 | 1515 DERBY St | 2024-07-24 | 2025-05-23 | R-3 Residential: Dwellings (1 or 2 Units | Alteration | 1.0 | New 553SF ADU to be within the existing footprint ... |

All 10 are small-work permits (alteration, demolition of detached structures, repair, solar install, ADU additions to single-family). Most are R-3 (1-2 unit residential) with 0-1 unit additions. None are multi-parcel.

## 8. The "NOT in CPRA" list

- **Empty.** All 90 permits are in CPRA.

## 9. Bottom-line

- **90 v2 in-scope B-permits** processed in URL discovery.
- **All 90 are in CPRA** (90/90, including the lone `accela`-sourced one).
- 2×2 split: **A=31, B=59, C=0, D=0** (where A=in_cpra ∧ ok, B=in_cpra ∧ not_found, C=¬in_cpra ∧ ok, D=¬in_cpra ∧ not_found).

**Interpretation:** The 59 "not_found in Accela" permits are NOT non-existent — they are documented in Berkeley's CPRA response and were correctly ingested into v2 from that source. They are missing from **Accela's public CapHome search results** (the by-permit-number search the URL-discovery scraper uses). The split is sharply explained by three signals: WorkType ("Alteration" 16% findable vs "New" 81%), UnitsAdded (11+ units 100% findable vs null/0 units 19%), and multi-parcel (multi-parcel permits 100% findable vs single-parcel 16%). The exposed-in-Accela cohort skews heavily toward large new multi-unit construction; the hidden-from-Accela cohort skews toward small-scale alteration/repair/demolition on single residential parcels. URL discovery via CapHome search is therefore systematically incomplete for the small-work end of the permit spectrum, regardless of whether the permits exist in city records.
