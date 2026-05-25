# In-scope B-permit URL inventory

**Generated:** 2026-05-21T16:46:07
**Source DB:** databases/berkeley_housing_v2.db (read-only)
**Scrape root:** data/raw/accela_status/ (depth ≤ 2)
**Scrape files scanned:** 157

## 1. Verified count

- Design sketch said: **90**
- Verified count today: **90**
- Stage breakdown:
  - completed: 82
  - under_construction: 8

### Field-completeness within the in-scope set (verifies what URL discovery would actually backfill)

| field | non-null / 90 |
|---|---|
| filed_date | 1 |
| issued_date | 89 |
| finaled_date | 51 |
| valuation | 89 |
| source_permit_id | 0 |

Implication: of the four CapDetail fields the URL-discovery scraper is sketched to capture (filed_date, issued_date, finaled_date, valuation), only `filed_date` is broadly missing in the in-scope set. `issued_date` and `valuation` are already populated for 89/90 rows; `finaled_date` for 51/90. `source_permit_id` is universally null, so URL discovery is also the natural step to attach Accela's internal capID-triplet to v2.

## 2. Distribution by project

- Distinct projects with ≥1 in-scope B-permit: **35**

### Histogram: B-permits per project

| permits per project | number of projects |
|---|---|
| 1 | 9 |
| 2 | 10 |
| 3 | 8 |
| 4 | 5 |
| 5 | 1 |
| 6 | 2 |

### Full table (project_id, address, stage, B-permit count)

| project_id | address | stage | B-permits |
|---|---|---|---|
| 63 | 1716 SEVENTH St | completed | 6 |
| 83 | 1136 KEITH Ave | completed | 6 |
| 176 | 2440 SHATTUCK Ave | completed | 5 |
| 90 | 576 SAN LUIS Rd | completed | 4 |
| 139 | 2538 DURANT Ave | completed | 4 |
| 150 | 3030 TELEGRAPH Ave | completed | 4 |
| 152 | 1598 UNIVERSITY Ave | completed | 4 |
| 174 | 1773 OXFORD St | completed | 4 |
| 53 | 2641 COLLEGE Ave | completed | 3 |
| 79 | 1111 ALLSTON Way | completed | 3 |
| 88 | 705 ARLINGTON Ave | completed | 3 |
| 129 | 1614 Sixth St | completed | 3 |
| 134 | 2480 Bancroft Way | completed | 3 |
| 147 | 2300 ELLSWORTH St | under_construction | 3 |
| 159 | 2403 SAN PABLO Ave | under_construction | 3 |
| 172 | 2650 TELEGRAPH Ave | completed | 3 |
| 64 | 1515 DERBY St | completed | 2 |
| 71 | 40 HILL Rd | completed | 2 |
| 92 | 3036 REGENT St | completed | 2 |
| 96 | 2099 M L KING JR Way | completed | 2 |
| 111 | 411 VASSAR Ave | completed | 2 |
| 135 | 2150 Kittredge St | completed | 2 |
| 153 | 1701 SAN PABLO Ave | under_construction | 2 |
| 161 | 2555 COLLEGE Ave | completed | 2 |
| 173 | 2000 DWIGHT Way | completed | 2 |
| 179 | 2352 Shattuck Ave | completed | 2 |
| 27 | 2441 LE CONTE Ave | completed | 1 |
| 70 | 3001 BENVENUE Ave | completed | 1 |
| 84 | 2705 BENVENUE Ave | completed | 1 |
| 87 | 1109 COWPER St | completed | 1 |
| 91 | 2009 ADDISON St | completed | 1 |
| 102 | 1246 ROSE St | completed | 1 |
| 105 | 1187 SHATTUCK Ave | completed | 1 |
| 126 | 2427 San Pablo | completed | 1 |
| 137 | 2000 University Ave | completed | 1 |

## 3. Per-permit cross-reference summary

- Permits with capID triplet recoverable from scrape files: **0**
- Permits where permit_number appears in a scrape file but no capID triplet was found: **27**
- Permits with no mention in any scrape file: **63**

**Verified by spot-check on `data/raw/accela_status/B2024-01268_2016_ASHBY.txt`:** scrape files are clipboard-pasted, human-readable Accela record summaries (record number, status, project description, processing status, etc.). They do NOT contain `capID1=…&capID2=…&capID3=…` query parameters or CapDetail URLs. The 0-recovery result is real, not a regex miss. The 27 "mentioned but no capID" matches are permits whose record number appears in a prior session's pasted summary — these summaries are useful for human review but contain no URL data to recover.

### Sample (10): capID recoverable

| permit_number | project_id | address | capid_triplet(s) | file(s) |
|---|---|---|---|---|

### Sample (10): mentioned but no capID

| permit_number | project_id | address | file(s) |
|---|---|---|---|
| B2023-05397 | 129 | 1614 Sixth St | B_1614_SIXTH_St.txt |
| B2024-04504 | 129 | 1614 Sixth St | B_1614_SIXTH_St.txt |
| B2024-06099 | 129 | 1614 Sixth St | B_1614_SIXTH_St.txt |
| B2022-05880 | 134 | 2480 Bancroft Way | B_2480_BANCROFT_Way.txt |
| B2024-01572 | 134 | 2480 Bancroft Way | B_2480_BANCROFT_Way.txt |
| B2024-02120 | 134 | 2480 Bancroft Way | B_2480_BANCROFT_Way.txt |
| B2024-05944 | 147 | 2300 ELLSWORTH St | 2300_ELLSWORTH_St.txt |
| B2025-00388 | 147 | 2300 ELLSWORTH St | 2300_ELLSWORTH_St.txt |
| B2025-02211 | 147 | 2300 ELLSWORTH St | 2300_ELLSWORTH_St.txt |
| B2023-06416 | 150 | 3030 TELEGRAPH Ave | ZP2022-0170_3030_TELEGRAPH_Ave.txt |

### Full list: no mention in any scrape file

| permit_number | project_id | address | filed_date |
|---|---|---|---|
| B2025-01864 | 27 | 2441 LE CONTE Ave |  |
| B2024-03884 | 53 | 2641 COLLEGE Ave |  |
| B2024-05471 | 53 | 2641 COLLEGE Ave |  |
| B2025-02413 | 53 | 2641 COLLEGE Ave |  |
| B2022-01278 | 63 | 1716 SEVENTH St |  |
| B2022-01332 | 63 | 1716 SEVENTH St |  |
| B2022-01386 | 63 | 1716 SEVENTH St |  |
| B2023-02303 | 63 | 1716 SEVENTH St |  |
| B2025-05132 | 63 | 1716 SEVENTH St |  |
| B2025-05133 | 63 | 1716 SEVENTH St |  |
| B2023-04430 | 64 | 1515 DERBY St |  |
| B2025-02754 | 64 | 1515 DERBY St |  |
| B2025-00605 | 70 | 3001 BENVENUE Ave |  |
| B2025-00897 | 71 | 40 HILL Rd |  |
| B2025-03189 | 71 | 40 HILL Rd |  |
| B2023-00192 | 79 | 1111 ALLSTON Way |  |
| B2025-01202 | 79 | 1111 ALLSTON Way |  |
| B2025-03358 | 79 | 1111 ALLSTON Way |  |
| B2022-03783 | 83 | 1136 KEITH Ave |  |
| B2024-02569 | 83 | 1136 KEITH Ave |  |
| B2024-02570 | 83 | 1136 KEITH Ave |  |
| B2024-02712 | 83 | 1136 KEITH Ave |  |
| B2024-03997 | 83 | 1136 KEITH Ave |  |
| B2025-02220 | 83 | 1136 KEITH Ave |  |
| B2023-00595 | 84 | 2705 BENVENUE Ave |  |
| B2024-00736 | 87 | 1109 COWPER St |  |
| B2023-05865 | 88 | 705 ARLINGTON Ave |  |
| B2024-01528 | 88 | 705 ARLINGTON Ave |  |
| B2025-04937 | 88 | 705 ARLINGTON Ave |  |
| B2022-05525 | 90 | 576 SAN LUIS Rd |  |
| B2025-00709 | 90 | 576 SAN LUIS Rd |  |
| B2025-04320 | 90 | 576 SAN LUIS Rd |  |
| B2025-04805 | 90 | 576 SAN LUIS Rd |  |
| B2023-03256 | 91 | 2009 ADDISON St |  |
| B2023-03308 | 92 | 3036 REGENT St |  |
| B2023-03832 | 92 | 3036 REGENT St |  |
| B2021-03950 | 96 | 2099 M L KING JR Way |  |
| B2024-01659 | 96 | 2099 M L KING JR Way |  |
| B2024-01323 | 102 | 1246 ROSE St |  |
| B2023-02115 | 105 | 1187 SHATTUCK Ave |  |
| B2024-05470 | 111 | 411 VASSAR Ave |  |
| B2025-00685 | 111 | 411 VASSAR Ave |  |
| B2023-04586 | 126 | 2427 San Pablo |  |
| B2022-05181 | 135 | 2150 Kittredge St |  |
| B2023-01578 | 135 | 2150 Kittredge St |  |
| B2022-06060 | 137 | 2000 University Ave |  |
| B2023-01880 | 139 | 2538 DURANT Ave |  |
| B2023-02332 | 139 | 2538 DURANT Ave |  |
| B2024-06011 | 139 | 2538 DURANT Ave |  |
| B2025-00875 | 139 | 2538 DURANT Ave |  |
| B2023-06442 | 150 | 3030 TELEGRAPH Ave |  |
| B2023-06443 | 150 | 3030 TELEGRAPH Ave |  |
| B2024-00587 | 152 | 1598 UNIVERSITY Ave |  |
| B2024-01602 | 152 | 1598 UNIVERSITY Ave |  |
| B2024-01924 | 152 | 1598 UNIVERSITY Ave |  |
| B2024-05740 | 152 | 1598 UNIVERSITY Ave |  |
| B2024-02966 | 153 | 1701 SAN PABLO Ave |  |
| B2025-03904 | 153 | 1701 SAN PABLO Ave |  |
| B2024-00143 | 159 | 2403 SAN PABLO Ave |  |
| B2025-03049 | 159 | 2403 SAN PABLO Ave |  |
| B2025-03320 | 159 | 2403 SAN PABLO Ave |  |
| B2024-05368 | 176 | 2440 SHATTUCK Ave |  |
| B2024-05208 | 179 | 2352 Shattuck Ave |  |

## 4. Source_system breakdown

| source_system | count |
|---|---|
| 'cpra' | 89 |
| 'accela' | 1 |

## 5. Date range

### filed_date (sparse — only 1 of 90 has a value)

- Permits with non-null filed_date: **1 of 90** (single value: 2019-12-20)

### issued_date (dense — 89 of 90 have a value)

The far better signal for "when was this permit active." Range computed for reference:

- Permits with non-null issued_date: **89 of 90**
- Oldest issued_date: 2023-01-11
- Newest issued_date: 2025-11-17

## 6. Bottom-line

- In-scope B-permits today: **90**
- URL-recoverable from scrape files (capID triplet found): **0**
- True URL-discovery work remaining: **90**

Note: 27 in-scope permit numbers appear in scrape files, but none of those files contain CapDetail URL/capID data — only human-readable record summaries. Cross-referencing scrape files does not reduce the URL-discovery workload.

---

## Appendix A — Full worklist (every in-scope permit)

| permit_id | permit_number | project_id | address | stage | filed_date | issued_date | source_system | source_permit_id | scrape_file_match | capid_triplet |
|---|---|---|---|---|---|---|---|---|---|---|
| 208 | B2025-01864 | 27 | 2441 LE CONTE Ave | completed |  | 2025-05-07 | cpra |  | none |  |
| 146 | B2024-03884 | 53 | 2641 COLLEGE Ave | completed |  | 2024-12-10 | cpra |  | none |  |
| 147 | B2024-05471 | 53 | 2641 COLLEGE Ave | completed |  | 2025-06-25 | cpra |  | none |  |
| 148 | B2025-02413 | 53 | 2641 COLLEGE Ave | completed |  | 2025-07-03 | cpra |  | none |  |
| 193 | B2022-01278 | 63 | 1716 SEVENTH St | completed |  | 2023-06-28 | cpra |  | none |  |
| 194 | B2022-01332 | 63 | 1716 SEVENTH St | completed |  | 2023-06-06 | cpra |  | none |  |
| 195 | B2022-01386 | 63 | 1716 SEVENTH St | completed |  | 2023-06-06 | cpra |  | none |  |
| 196 | B2023-02303 | 63 | 1716 SEVENTH St | completed |  | 2023-05-26 | cpra |  | none |  |
| 197 | B2025-05132 | 63 | 1716 SEVENTH St | completed |  | 2025-11-17 | cpra |  | none |  |
| 198 | B2025-05133 | 63 | 1716 SEVENTH St | completed |  | 2025-11-17 | cpra |  | none |  |
| 131 | B2023-04430 | 64 | 1515 DERBY St | completed |  | 2024-07-24 | cpra |  | none |  |
| 132 | B2025-02754 | 64 | 1515 DERBY St | completed |  | 2025-07-03 | cpra |  | none |  |
| 119 | B2025-00605 | 70 | 3001 BENVENUE Ave | completed |  | 2025-02-18 | cpra |  | none |  |
| 236 | B2025-00897 | 71 | 40 HILL Rd | completed |  | 2025-03-10 | cpra |  | none |  |
| 237 | B2025-03189 | 71 | 40 HILL Rd | completed |  | 2025-08-25 | cpra |  | none |  |
| 175 | B2023-00192 | 79 | 1111 ALLSTON Way | completed |  | 2024-03-20 | cpra |  | none |  |
| 176 | B2025-01202 | 79 | 1111 ALLSTON Way | completed |  | 2025-03-25 | cpra |  | none |  |
| 177 | B2025-03358 | 79 | 1111 ALLSTON Way | completed |  | 2025-08-12 | cpra |  | none |  |
| 230 | B2022-03783 | 83 | 1136 KEITH Ave | completed |  | 2023-01-11 | cpra |  | none |  |
| 231 | B2024-02569 | 83 | 1136 KEITH Ave | completed |  | 2024-09-25 | cpra |  | none |  |
| 232 | B2024-02570 | 83 | 1136 KEITH Ave | completed |  | 2024-09-27 | cpra |  | none |  |
| 233 | B2024-02712 | 83 | 1136 KEITH Ave | completed |  | 2024-08-07 | cpra |  | none |  |
| 234 | B2024-03997 | 83 | 1136 KEITH Ave | completed |  | 2024-08-14 | cpra |  | none |  |
| 235 | B2025-02220 | 83 | 1136 KEITH Ave | completed |  | 2025-07-23 | cpra |  | none |  |
| 130 | B2023-00595 | 84 | 2705 BENVENUE Ave | completed |  | 2023-02-17 | cpra |  | none |  |
| 174 | B2024-00736 | 87 | 1109 COWPER St | completed |  | 2024-04-05 | cpra |  | none |  |
| 225 | B2023-05865 | 88 | 705 ARLINGTON Ave | completed |  | 2023-11-14 | cpra |  | none |  |
| 226 | B2024-01528 | 88 | 705 ARLINGTON Ave | completed |  | 2025-03-04 | cpra |  | none |  |
| 227 | B2025-04937 | 88 | 705 ARLINGTON Ave | completed |  | 2025-11-04 | cpra |  | none |  |
| 221 | B2022-05525 | 90 | 576 SAN LUIS Rd | completed |  | 2023-02-16 | cpra |  | none |  |
| 222 | B2025-00709 | 90 | 576 SAN LUIS Rd | completed |  | 2025-06-02 | cpra |  | none |  |
| 223 | B2025-04320 | 90 | 576 SAN LUIS Rd | completed |  | 2025-10-27 | cpra |  | none |  |
| 224 | B2025-04805 | 90 | 576 SAN LUIS Rd | completed |  | 2025-10-27 | cpra |  | none |  |
| 185 | B2023-03256 | 91 | 2009 ADDISON St | completed |  | 2024-05-31 | cpra |  | none |  |
| 120 | B2023-03308 | 92 | 3036 REGENT St | completed |  | 2023-06-28 | cpra |  | none |  |
| 121 | B2023-03832 | 92 | 3036 REGENT St | completed |  | 2023-08-02 | cpra |  | none |  |
| 182 | B2021-03950 | 96 | 2099 M L KING JR Way | completed |  | 2023-07-17 | cpra |  | none |  |
| 183 | B2024-01659 | 96 | 2099 M L KING JR Way | completed |  | 2024-07-16 | cpra |  | none |  |
| 213 | B2024-01323 | 102 | 1246 ROSE St | completed |  | 2024-05-03 | cpra |  | none |  |
| 220 | B2023-02115 | 105 | 1187 SHATTUCK Ave | completed |  | 2023-07-07 | cpra |  | none |  |
| 228 | B2024-05470 | 111 | 411 VASSAR Ave | completed |  | 2025-06-23 | cpra |  | none |  |
| 229 | B2025-00685 | 111 | 411 VASSAR Ave | completed |  | 2025-03-13 | cpra |  | none |  |
| 173 | B2023-04586 | 126 | 2427 San Pablo | completed |  | 2023-09-07 | cpra |  | none |  |
| 190 | B2023-05397 | 129 | 1614 Sixth St | completed |  | 2023-12-19 | cpra |  | B_1614_SIXTH_St.txt |  |
| 191 | B2024-04504 | 129 | 1614 Sixth St | completed |  | 2025-08-29 | cpra |  | B_1614_SIXTH_St.txt |  |
| 192 | B2024-06099 | 129 | 1614 Sixth St | completed |  | 2025-08-29 | cpra |  | B_1614_SIXTH_St.txt |  |
| 154 | B2022-05880 | 134 | 2480 Bancroft Way | completed |  | 2023-12-13 | cpra |  | B_2480_BANCROFT_Way.txt |  |
| 155 | B2024-01572 | 134 | 2480 Bancroft Way | completed |  | 2024-08-07 | cpra |  | B_2480_BANCROFT_Way.txt |  |
| 156 | B2024-02120 | 134 | 2480 Bancroft Way | completed |  | 2024-08-01 | cpra |  | B_2480_BANCROFT_Way.txt |  |
| 187 | B2022-05181 | 135 | 2150 Kittredge St | completed |  | 2023-01-13 | cpra |  | none |  |
| 188 | B2023-01578 | 135 | 2150 Kittredge St | completed |  | 2023-05-11 | cpra |  | none |  |
| 184 | B2022-06060 | 137 | 2000 University Ave | completed |  | 2023-06-16 | cpra |  | none |  |
| 150 | B2023-01880 | 139 | 2538 DURANT Ave | completed |  | 2024-08-08 | cpra |  | none |  |
| 151 | B2023-02332 | 139 | 2538 DURANT Ave | completed |  | 2024-09-24 | cpra |  | none |  |
| 152 | B2024-06011 | 139 | 2538 DURANT Ave | completed |  | 2025-05-09 | cpra |  | none |  |
| 153 | B2025-00875 | 139 | 2538 DURANT Ave | completed |  | 2025-07-07 | cpra |  | none |  |
| 158 | B2024-05944 | 147 | 2300 ELLSWORTH St | under_construction |  | 2025-09-04 | cpra |  | 2300_ELLSWORTH_St.txt |  |
| 159 | B2025-00388 | 147 | 2300 ELLSWORTH St | under_construction |  | 2025-08-11 | cpra |  | 2300_ELLSWORTH_St.txt |  |
| 160 | B2025-02211 | 147 | 2300 ELLSWORTH St | under_construction |  | 2025-09-02 | cpra |  | 2300_ELLSWORTH_St.txt |  |
| 122 | B2023-06416 | 150 | 3030 TELEGRAPH Ave | completed |  | 2024-10-15 | cpra |  | ZP2022-0170_3030_TELEGRAPH_Ave.txt |  |
| 123 | B2023-06442 | 150 | 3030 TELEGRAPH Ave | completed |  | 2024-09-19 | cpra |  | none |  |
| 124 | B2023-06443 | 150 | 3030 TELEGRAPH Ave | completed |  | 2024-09-19 | cpra |  | none |  |
| 125 | B2024-03794 | 150 | 3030 TELEGRAPH Ave | completed |  | 2025-01-08 | cpra |  | ZP2022-0170_3030_TELEGRAPH_Ave.txt |  |
| 178 | B2024-00587 | 152 | 1598 UNIVERSITY Ave | completed |  | 2024-07-15 | cpra |  | none |  |
| 179 | B2024-01602 | 152 | 1598 UNIVERSITY Ave | completed |  | 2024-06-05 | cpra |  | none |  |
| 180 | B2024-01924 | 152 | 1598 UNIVERSITY Ave | completed |  | 2024-12-16 | cpra |  | none |  |
| 181 | B2024-05740 | 152 | 1598 UNIVERSITY Ave | completed |  | 2025-01-13 | cpra |  | none |  |
| 200 | B2024-02966 | 153 | 1701 SAN PABLO Ave | under_construction |  | 2025-05-06 | cpra |  | none |  |
| 201 | B2025-03904 | 153 | 1701 SAN PABLO Ave | under_construction |  | 2025-11-06 | cpra |  | none |  |
| 170 | B2024-00143 | 159 | 2403 SAN PABLO Ave | under_construction |  | 2025-06-03 | cpra |  | none |  |
| 171 | B2025-03049 | 159 | 2403 SAN PABLO Ave | under_construction |  | 2025-10-31 | cpra |  | none |  |
| 172 | B2025-03320 | 159 | 2403 SAN PABLO Ave | under_construction |  | 2025-09-26 | cpra |  | none |  |
| 144 | B2023-02975 | 161 | 2555 COLLEGE Ave | completed |  | 2024-04-26 | cpra |  | ZP2022-0019_2555_COLLEGE_Ave.txt |  |
| 145 | B2024-05972 | 161 | 2555 COLLEGE Ave | completed |  | 2025-06-02 | cpra |  | ZP2022-0019_2555_COLLEGE_Ave.txt |  |
| 137 | B2021-02225 | 172 | 2650 TELEGRAPH Ave | completed |  | 2023-08-02 | cpra |  | FULL_2650_TELEGRAPH.txt |  |
| 138 | B2024-01841 | 172 | 2650 TELEGRAPH Ave | completed |  | 2024-11-25 | cpra |  | FULL_2650_TELEGRAPH.txt |  |
| 139 | B2024-03280 | 172 | 2650 TELEGRAPH Ave | completed |  | 2024-11-20 | cpra |  | FULL_2650_TELEGRAPH.txt |  |
| 134 | B2021-02404 | 173 | 2000 DWIGHT Way | completed |  | 2023-08-15 | cpra |  | FULL_2000_DWIGHT.txt |  |
| 135 | B2023-00675 | 173 | 2000 DWIGHT Way | completed |  | 2023-08-25 | cpra |  | FULL_2000_DWIGHT.txt |  |
| 204 | B2023-02354 | 174 | 1773 OXFORD St | completed |  | 2023-11-13 | cpra |  | FULL_1773_OXFORD.txt |  |
| 205 | B2023-03067 | 174 | 1773 OXFORD St | completed |  | 2023-08-15 | cpra |  | FULL_1773_OXFORD.txt |  |
| 206 | B2023-04569 | 174 | 1773 OXFORD St | completed |  | 2023-10-27 | cpra |  | FULL_1773_OXFORD.txt |  |
| 207 | B2023-06274 | 174 | 1773 OXFORD St | completed |  | 2024-11-15 | cpra |  | FULL_1773_OXFORD.txt |  |
| 163 | B2022-05117 | 176 | 2440 SHATTUCK Ave | completed |  | 2023-08-03 | cpra |  | FULL_2440_SHATTUCK.txt |  |
| 164 | B2023-00401 | 176 | 2440 SHATTUCK Ave | completed |  | 2023-03-24 | cpra |  | FULL_2440_SHATTUCK.txt |  |
| 165 | B2023-03611 | 176 | 2440 SHATTUCK Ave | completed |  | 2023-08-31 | cpra |  | FULL_2440_SHATTUCK.txt |  |
| 166 | B2024-01853 | 176 | 2440 SHATTUCK Ave | completed |  | 2024-05-17 | cpra |  | FULL_2440_SHATTUCK.txt |  |
| 167 | B2024-05368 | 176 | 2440 SHATTUCK Ave | completed |  | 2024-11-19 | cpra |  | none |  |
| 244 | B2019-05575 | 179 | 2352 Shattuck Ave | completed | 2019-12-20 |  | accela |  | 2026-05-04_modera_and_8_others.txt |  |
| 162 | B2024-05208 | 179 | 2352 Shattuck Ave | completed |  | 2024-11-22 | cpra |  | none |  |
