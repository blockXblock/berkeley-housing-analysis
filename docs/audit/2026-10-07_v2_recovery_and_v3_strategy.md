# v2 → v4 recovery audit, and the v3 rebuild strategy (2026-10-07)

Read-only review for John ("review that we recovered all useful data from v2 into v4; review strategy for v3
rebuild"). Script: `scratch/2026-10-07_v2_audit/audit_v2_to_v4.py`. Live v4 = 097f76a2; v2 read-only.

## Part 1 — Has v4 recovered everything useful in v2?

**Yes for every source-backed table; the residue is either unsourced in v2 or a known v4 open item.** The
2026-10-01 project-level audit (1,046 of 1,099 matched; fees, attachment lists, drawn outlines, historic ledger
carried) is now extended field by field and table by table.

### Tables — all carried, most much larger in v4
| v2 table | v2 rows | v4 home | v4 rows |
|---|---|---|---|
| inspections | 47,413 | `inspection` events | 47,411 |
| documents held in R2 (with SHA-256) | 305 | `documents` | **305 of 305 by hash** |
| documents that are attachment titles (`*.txt` captures) | ~1,200 | `attachment_listed` events | 2,908 |
| documents from `cpra` (permit rows filed as documents) | 704 | the CPRA permit events | (all) |
| organizations / project_participants | 898 / 1,023 | `v_project_people` | 4,452 names / 12,741 rows |
| project_assessed_value | 672 | `v_projects.assessed_value` | 1,518 |
| project_geometries | 351 | `geometries` | 29,138 |
| parcel_lineage / crosswalk | 28 / 25 | `parcel_lineage` | 5,352 |
| fees | 441 | `fees_recorded` events | 2,221 |
| classification sb330_protected | 15 | `pathways` (sb330_preliminary) | 15 of 15 |
| classification uc_project / bart_project | 4 / 2 | classification rulings R001–R006 | all |

### Projects — 42 of v2's 1,099 have no v4 counterpart
* 29 have no milestone in v2 at all; 12 are 1–4 unit records (8 "completed", 4 "permitted") whose permits v4 reads
  as alterations, not new units (the 2026-10-01 decision on v2's single-unit "ADU" rows).
* **Ashby BART (v2 151, 618u, no City record)** — IS in v4 as `PLN2026-0185` (pre-application, 0 Adeline, filed
  2026-09-18); the crosswalk could not match a v2 row with no record. Not a loss.
* 2131 University (v2 178, 205u umbrella) — deliberately not migrated (Acheson Commons A–D are v4's buildings).
* 1700 Sacramento, 3020 San Pablo — resolved 2026-10-01 (unsourced / expired unissued).
* **1710 University (ZP2021-0127, 16u in v2)** — the Planning record exists ("Construct 4-story, mixed-use building
  for non-profit religious education and living spaces", Incomplete Pending Applicant since 2021); the housing
  filter reads "living spaces" as not dwellings. Borderline (likely group quarters); John's call.
* 2428 Milvia (8u) — no City record in v2; unsourced.

### Fields — where v2 has a value and the matched v4 project does not
| field | projects (5+ units) | what it is |
|---|---|---|
| total_units | 26 (21) | proposed units of in-review / entitled projects (e.g. Morse Block 336, ZP2024-0162 117) — v4's units reading left them unanswered. **Open item:** read them from the Planning description, the ZAB minutes item ("144 dwelling units") or the staff report — never copied from v2. |
| height_stories / height_feet | 28 (8) / 5 (4) | same: the ZAB minutes and descriptions state stories and feet. Re-derive. |
| density_bonus (classification) | 9 of 52 matched | v4 reads pathways from Planning text only; **the ZAB minutes state "utilizing a State Density Bonus"** — a new source for a re-read. |
| architect | 15 (15) | v2's names came from the v1 curated sheet; v4 names architects only from plan title blocks and the attribution ledger. Re-derive from plan sets / staff reports where held. |
| owner_current / planning_applicant | 35 (18) / 30 (12) | owner of record joins by parcel (v4 matches fewer of the new/re-platted parcels); applicant from the Planning record's contact block. Check the parcel join for these 35. |
| vli/li units | 7 / 4 | v1-migrated affordability (deliberately not migrated: unsourced) and 4 historic-ledger rows. |
| entitled_date | 6 (4) | v2 dates with no City task behind them; e.g. ZP2015-0177 (v4: "Case Closed — Approved" 2017-05-03 but no decision task). Review. |
| co_issued_date / bp | 4 / 1 | **2100 San Pablo (ZP2016-0034, 96u in v2):** its permit B2019-03689 is a "New 4-story mixed-use building containing Residential Care Facility" — v4's HCD reading does not count it as housing units. A definition question for John, not a loss. ZP2020-0102's "2024-01-01" is a placeholder date. |
| filed_date | 102 (3) | the UC external projects (no City filing) and ADU rows: not applicable. |

**Nothing source-backed is stranded in v2.** The open items above are re-derivations v4 can make from sources it now
holds (the ZAB minutes in particular), not data to copy. v2 can be archived read-only; the v2 crosswalk for old
Explorer links keeps working from the archived copy.

## Part 2 — The v3 rebuild: strategy

**What v3 is today.** Two different things share the name:
1. **The v3 database** (`databases/berkeley_housing_v3.db`, built 2026-06-25 by `scripts/build_v2/` S0–S9): a staged
   rebuild with per-stage gates and a scorecard against the City's APR. **Every builder stage S0–S8 opens v2**
   (S0 keys and S1 units from `v_projects_flat`, S3–S6 from v2's events/versions, S8's cross-check is v2 itself),
   so it is a *v2-assisted* rebuild, not a from-sources one. Only `JN-BerkeleyOpenData` still reads it.
2. **The curriculum** (`notebooks/curriculum/` JN00–JN8, on the site): rebuilds the record inline from the CPRA
   spreadsheets — it does **not** read v2 or v3 — and grades it against the HCD filing. It imports v3's
   `s0_keys.normalize_address` (CLAUDE.md's "decoy" canon) and the regex-era `is_housing` / `net_units`; JN7
   already re-keys buildings to permit families.

**Recommendation: freeze the v3 database; align the curriculum to v4 (the 2026-07-01 verdict, updated).**
1. **Do not rebuild the v3 database.** v4 is the from-sources build v3 set out to be. Keep v3 frozen as the research
   record of the identity turn. Before v2 is archived, point `scripts/build_v2/` at the archived v2 path so v3 stays
   reproducible, and say plainly in its README that it is v2-assisted.
2. **Curriculum — keep the students' path, change what they are graded against.**
   * JN1–JN5 stay as they are pedagogically: students build an address key, a regex housing rule, an event stage.
     The address key and the regex rule become the **planted limitations** (as JN6b/JN7 already do for identity).
   * Add the **v4 comparison**: after JN5, students compare their rebuild with v4's published record (the public
     mirror / Datasette), project by project, and find where address keys and regexes fail — the 1951/1955 Shattuck
     aliases, phased permits, the "dwellings" plural, the residential-care definition.
   * JN7 moves from `s0_keys.normalize_address` to `housing_rules.address.normalize_address` and introduces the
     model-read `permit_effect` as the answer to "what does this permit do", measured against the student's regex.
   * Numbers in the prose come from v4 (generated, never typed), so they move with the record.
3. **New modules v4 now makes possible** (optional, later): time-to-approval (Planning tasks, Letters of Compliance,
   the ZAB minutes — "the City's workflow says staff; the Board's minutes say otherwise"), the Rent Board registry,
   public funding. These are the best teaching material the project has produced: each is a case where one source
   contradicts another and a primary record settles it.
4. **Order:** archive v2 (with the build_v2 path change) → JN7 canon swap + v4 comparison cell → JN0a–JN6b numbers
   generated from v4 → optional modules.

**Decisions for John:** (a) freeze the v3 database rather than rebuild it; (b) the curriculum compares students'
rebuild against v4 rather than v2/v3; (c) the three definition questions above (2100 San Pablo residential care,
1710 University "living spaces", the 26 projects whose proposed units v4 should re-read).

## John's decisions (2026-10-07: "yes on the three calls")
1. **2100 San Pablo** — v4's reading stands: a Residential Care Facility is not counted as housing units.
2. **1710 University** — v4's reading stands: "religious education and living spaces" stays outside the housing scope.
3. **Re-reads** — v4 re-reads proposed units, heights and density bonus for the projects v2 had and v4 lacks, from the
   ZAB minutes items and the City's own descriptions (a new evidence file; never copied from v2).
**v2 archived read-only the same day** → `databases/archive/berkeley_housing_v2.db` (SHA-256 9cec330e943e1596…,
unchanged by the move); `scripts/build_v2/` S0–S8 and the Explorer crosswalk re-pointed (crosswalk identical: 1,057).
