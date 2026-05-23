# APR workflow audit (2026-05-24)

**Generated:** 2026-05-23 (reconstructed from disk artifacts)
**Author:** Claude Code, under John's direction
**Scope:** consolidate the state of the APR-match workstream — databases, generator script, HCD spec gap analysis, CofO finding, stage-mismatch findings — and recommend the Track 1 / Track 2 path forward.

This note reconstructs an earlier in-conversation audit that was never persisted to disk. All numbers are re-queried from the canonical databases on disk and cross-referenced against the same-day baseline run and yesterday's record_status + processing_status reports.

---

## Section 1 — Database readiness summary

Three databases participate in the APR-match workflow. Their readiness is asymmetric: v1 is the only one `scripts/generate_apr.py` reads, but v2 + cic_recon_queue together carry the data that justifies refactoring.

### 1a. Comparison table

| dimension | **v1: `berkeley_housing_analysis.db`** | **v2: `berkeley_housing_v2.db`** | **`cic_recon_queue.db`** |
|---|---|---|---|
| Role | Legacy flat schema; current APR source | Canonical normalized schema | Scrape-state staging |
| Tables | 11 | 45 | 4 |
| Projects | 179 (flat) | 181 (normalized via `projects` + `project_versions`) | n/a |
| Permits | 94 in `building_permits`; 114 in `project_permits` | 244 in `permits` | 107 (record_status & processing_status); 105 (url_discovery); 92 (scrape) |
| Events / lifecycle | 2,306 in `permit_events` | 2,347 in `project_events` | n/a |
| Fees | 441 in `permit_fees` (aggregate level) | 441 in `fees` | n/a |
| Documents | 1,423 in `project_documents` | 1,275 in `documents` (some quarantined) | n/a |
| Geometries | 184 in `project_geometries` | 358 in `project_geometries` (post-KML import) | n/a |
| Affordability | columns on `projects` flat row (`vli_units`, `density_bonus`, etc.) | `unit_program` (179) + `unit_program_affordability` (175) | n/a |
| Stage vocabulary | string columns: `status`, `pipeline_stage`, `construction_substage` | `vocabulary_stage_types` (8 codes), `current_stage_type_id` on `projects` | n/a |
| Authoritative permit state | none — `accela_status` field present but stale | none stored | **`record_status_queue` (107) — authoritative** |
| Workflow / CofO data | none | none | **`processing_status_queue` (107) — authoritative** |
| Used by `generate_apr.py`? | **yes** (path fixed today) | no | no |

### 1b. v2 stage distribution (current state)

```
in_review:          78
completed:          37
entitled:           34
permitted:          14
withdrawn:           8
under_construction:  6
pre_application:     3
stalled:             1
                  ----
                   181
```

The 37 `completed` projects are the cohort against which yesterday's record_status mismatches are computed — 12 of those 37 projects have at least one permit Accela still calls `Issued` (see §5).

### 1c. cic_recon_queue.db detail

All four queues are at 100% completion:

| queue | rows | succeeded | populated by |
|---|---|---|---|
| `url_discovery_queue` | 105 | 105 (100%) | 2026-05-22 URL discovery run |
| `scrape_queue` | 92 | 92 (100%) | 2026-05-22 inspection scrape |
| `record_status_queue` | 107 | 107 (100%) | 2026-05-23 record_status scrape |
| `processing_status_queue` | 107 | 107 (100%) | 2026-05-23 processing_status scrape |

**record_status_queue distribution (107 permits):**
- Finaled 63 (58.9%)
- Issued 37 (34.6%)
- Closed Expired 6 (5.6%)
- Approved 1 (0.9%) — the lone Planning record (ZP2018-0135)

**processing_status_queue active workflow stages (54 permits with any active stage):**
- `Inspection` 42 — dominant active stage (39% of all 107)
- The remaining 12 are CofO-Review-stage combinations across the 9 named CofO stages (see §4). One outlier: `Consolidated Comments` (1 permit, B2023-02332 at 2538 Durant).

### 1d. Readiness verdict per database

| db | ready for APR? | why |
|---|---|---|
| v1 | **yes (today)** | `generate_apr.py` path-fix done; baseline written; outputs current at 2026-05-23 14:03 |
| v2 | **no (script-side)** | No script reads it for APR generation yet; refactor pending |
| cic_recon_queue | **yes (queryable)** | 100% scraped; ready to join into v2 once Track 2 starts |

---

## Section 2 — `scripts/generate_apr.py` state

### 2a. The path-fix done today

```diff
- DB_PATH = BASE_DIR / 'data' / 'berkeley_housing_analysis.db'
+ DB_PATH = BASE_DIR / 'databases' / 'berkeley_housing_analysis.db'
```

Single-character class change at line 26 (`data` → `databases`). No other modifications. Verified in current file: `DB_PATH = BASE_DIR / 'databases' / 'berkeley_housing_analysis.db'` at line 26; single connection point at line 438 (`conn = sqlite3.connect(DB_PATH)`).

### 2b. Structure

- **538 lines**, 9 functions, single sqlite3 connection
- Imports: `argparse`, `sqlite3`, `json`, `csv`, `datetime`, `pathlib`
- Functions: `generate_table_a`, `generate_table_a2`, `generate_table_b`, `generate_developer_summary`, `generate_rhna_progress`, `generate_adu_summary`, `generate_stalled_projects`, `write_csv`, `main`
- All queries are `FROM projects` against the v1 flat 58-column table

### 2c. v1-only assumptions baked in

Every query in the script depends on the flat-schema shape of v1:

1. **Income breakdowns** read directly from `projects.vli_units` (and computes Low / Mod / AboveMod by inference). v2 stores these in the normalized `unit_program_affordability` table (175 rows) — different join shape entirely.
2. **Stage labels** read from `projects.status`, `projects.pipeline_stage`, `projects.construction_substage`. v2 uses `current_stage_type_id` joined to `vocabulary_stage_types` (8-code vocabulary).
3. **Dates** (filed, entitled, bp_issued, co_date) read from `projects` columns directly. v2 has these distributed across `permits` (`filed_date`, `issued_date`, `finaled_date`) and `project_events`.
4. **Stalled flag** reads from `projects.is_stalled`. v2 has `stalled` as a stage code (1 project today) — semantically different.
5. **Developer / architect / APN / valuation / density bonus** all read as columns on `projects`. v2 puts these in `project_participants` (organizations + people), `project_parcels`, individual permit valuations, and (for density bonus) `project_classifications`.
6. **No permit-level state**. The script never asks Accela "is this permit Finaled?" — it just trusts v1's `projects.accela_status` column, which is stale and lacks granularity. The new `record_status_queue` is the corrective.
7. **No CofO workflow awareness**. The script uses `projects.co_date` directly. Yesterday's CofO finding (§4) means this field is meaningless for the typical Berkeley housing project — it should be derived from the CofO Review stages or master permit Finaled date.

**Implication for Track 2:** the refactor is not a search-and-replace. Every query needs to be rewritten against v2's normalized shape, and the derivation rules for stage / CO date / affordability counts need to be re-expressed in v2 vocabulary. This is the bulk of the Track 2 work.

### 2d. What the script produces today

Today's outputs (all written 2026-05-23 14:03 via the path-fixed v1 script):

| file | rows | mtime |
|---|---|---|
| `data/apr/2025/table_a_2025.csv` | 6 | 14:03 |
| `data/apr/2025/table_a2_2025.csv` | 27 | 14:03 |
| `data/apr/2025/table_b_2025.csv` | 5 (RHNA categories) | 14:03 |
| `data/apr/2025/developer_summary_2025.csv` | 11 | 14:03 |
| `data/apr/2025/stalled_2025.csv` | 38 | 14:03 |
| `data/apr/2025/apr_2025.json` | full structured dump | 14:03 |

Headline numbers in `notes/2026-05-24_apr_baseline_run_report.md`:
- Table A: **6 projects, 744 units**
- Table A2: **27 projects, 2,982 units** (18 entitled / 1 BP / 8 CO)
- Table B RHNA: **1,279 / 8,934 = 14.3%** (VLI 17.9%, Low 0%, Mod 0%, AboveMod 20.6%)
- Pipeline: 14,070 units
- Stalled: 38 projects (5,393 units)

---

## Section 3 — HCD APR specification gap analysis

### 3a. The spec itself (`apr_specification.json`)

Source: HCD 2025-2026 spec, legal basis Gov Code §65400, April 1 deadline.

**Tables defined:** A, A2, B, C, D, E, F, G, H (9 tables total).

**Income categories (6):** Acutely Low (ALI, 0-15% AMI; new per AB 3093), Extremely Low (ELI, 15-30%), Very Low (VLI, 30-50%), Low (LI, 50-80%), Moderate (MOD, 80-120%), Above Moderate (AM, >120%).

**Unit categories (6):** SFD, SFA, 2-4, 5+, ADU, MH.

**Tenure types (2):** Owner, Renter.

**Recent legislation referenced:** AB 879 (2017), SB 35 (2017), SB 6 (2022), AB 2011 (2022), SB 423 (2023), AB 3093 (2024 — income-category expansion), AB 2580 (2024).

**Table A2 is the field-heaviest table** with the full income × stage matrix (VLI/LI/MOD/AM × Ent/BP/CO + bools + density-bonus fields). That's where our coverage gap is concentrated.

### 3b. Coverage summary (`apr_data_mapping.json` — Table A2 focus)

The data-mapping JSON evaluates 28 Table A2 fields against the v1-equivalent source CSV (`housing_projects_FINAL.csv`):

| status | count | meaning |
|---|---|---|
| **direct** | 5 | Field maps 1:1 from a v1 column |
| **derivable** | 7 | Field can be computed from existing data with derivation logic |
| **partial** | 1 | Field is present but coverage is incomplete (APN: 3 / 115 records) |
| **missing** | 15 | No source field; needs to be sourced from elsewhere |
| **Total** | **28** | required Table A2 fields evaluated |

**Direct mappings (5):** YEAR, STREET_ADDRESS, JURS_TRACKING_ID, NOTES, plus one income/tenure field where coverage was already present.

**Derivable (7):** UNIT_CAT (from net_units + description), ABOVE_MOD_INCOME (= total - VLI - LI - MOD), EXTR_LOW_INCOME_UNITS (parse description), APPROVE_SB35 (parse description), DENSITY_BONUS_TOTAL (parse description), and two more from description-parsing.

**Partial (1):** APN — 3 of 115 v1 records have an APN; 112 records need backfill from Alameda County parcel data (`data/reference/alameda_lookup_complete.csv`).

**Missing (15):** the four income-tier × deed-restriction crosstab pairs (VLOW_INCOME_DR, VLOW_INCOME_NDR, LOW_INCOME_DR, LOW_INCOME_NDR, MOD_INCOME_DR, MOD_INCOME_NDR — 6 cells), TENURE, ENT_APPROVE_DT1, BP_ISSUE_DT1, CO_ISSUE_DT1, JURIS_NAME (trivially derivable as constant), CNTY_NAME (same), PRIOR_APN, PROJECT_NAME, and one further field.

### 3c. The 4 critical gaps (from `apr_data_mapping.json.critical_gaps`)

1. **Income Category Breakdown (VLI/LI/MOD/AM by deed-restriction status).** Cannot track RHNA progress without these. Solution: parse descriptions, cross-reference Berkeley Housing Department affordability records, manual review for large projects.
2. **APN (Assessor Parcel Number).** Required for state reporting. Solution: match addresses to Alameda County parcel data (`data/reference/alameda_lookup_complete.csv` already on disk).
3. **Permit Stage Dates** (entitlement, BP issuance, CO). Cannot determine which year to report activity. Solution: extract from permit system, BuildingEye, or Clariti when available. **Largely solved by the URL discovery + inspection scrape from 2026-05-22, plus today's record_status + processing_status queues.**
4. **Tenure (Owner/Renter).** Required field. Solution: default most multi-family to Renter, parse descriptions for ownership mentions.

### 3d. What v2 + cic_recon_queue change about the gaps

The mapping JSON was written 2026-02-22, before the 2026-05 data-foundation work. With current state:

| gap | v2 coverage | cic_recon_queue coverage | net status |
|---|---|---|---|
| Income categories | `unit_program_affordability` (175 rows) | n/a | **Closes gap 1 for projects covered by v2** |
| APN | `parcels` (171) + `project_parcels` (177) | n/a | **Closes gap 2 for the 177 projects with parcel links** |
| Permit stage dates | `permits.filed_date / issued_date / finaled_date` | record_status + processing_status add authoritative permit + workflow state for the 107 scraped permits | **Closes gap 3 for 107 permits; v2's permit dates cover more (244 permits)** |
| Tenure | not explicitly modeled in v2 schema; would derive from `vocabulary_tenure_types` (8 codes) at query time | n/a | Partial — needs derivation rule |

So the Track 2 refactor isn't just a schema swap; it's also a coverage-expansion opportunity. The 4 critical gaps shrink materially when sourced from v2.

---

## Section 4 — CofO workflow finding (the central new datum)

**Source:** `notes/2026-05-23_processing_status_scrape_report.md` + Perplexity-confirmed Berkeley policy (per yesterday's session-close note).

### 4a. The finding

Berkeley does not issue traditional Certificates of Occupancy as a single document. Instead, Accela's processing workflow contains **9 distinct CofO-named stages** — each owned by a different department:

1. **Zoning CofO Review**
2. **Fire CofO Review**
3. **Public Works CofO Review**
4. **Traffic CofO Review**
5. **Design CofO Review**
6. **Toxics CofO Review**
7. **Inspector CofO Review**
8. **Inspector Final CofO Review**
9. **Certificate of Occupancy** (a final wrapper stage)

These appear in the `processing_status_queue.active_stage_names` column as the active workflow position for permits between Inspection-complete and Finaled. The inspector-signed final inspection card serves as the closing artifact; there is no separate CofO PDF for most projects.

### 4b. The derivation rule (canonical for Track 2)

The CO_date to report on HCD APR Table A2 is derived from three tiers:

1. **If the permit has CofO Review stages marked `complete` in processing_status:**
   `CO_date = max(stage_complete_date)` over rows where `stage_name LIKE '%CofO%' AND stage_state = 'complete'`
2. **Else if `record_status = 'Finaled'`:** (the small-alteration / no-CofO-workflow case)
   `CO_date = master permit's Finaled date` (i.e., `permits.finaled_date` for the project's master permit)
3. **Else:**
   `CO_date = NULL` — project is not yet completed.

### 4c. Why this matters for APR-match

- Today's v1 baseline reports 8 CO-issued projects (`table_a2_2025.csv`). This used `projects.co_date` from the v1 flat row.
- v1's `co_date` was hand-populated and may diverge from the derivation rule above.
- Track 2 should produce a CO_date via the derivation rule for every project in `processing_status_queue` (107 permits → 100+ projects) and compare against v1's `co_date`. Divergences become explicit "city used X, we derive Y" rows in the comparison report.

### 4d. Coverage of the derivation rule today

| tier | applicable permits today | source |
|---|---|---|
| Tier 1 (CofO workflow complete) | 0 of 107 — yesterday's scrape found CofO stages **active**, not complete | `processing_status_queue` |
| Tier 2 (master permit Finaled, no CofO workflow) | 63 of 107 (Finaled record_status) | `record_status_queue` |
| Tier 3 (NULL — not yet completed) | 44 of 107 (Issued / Closed Expired / Approved) | `record_status_queue` |

The active-CofO-stage permits are mid-workflow. Tier-1 will fill in as those workflows complete; for the 2026 APR cycle we mostly rely on tier 2.

---

## Section 5 — The 18 v2.completed-but-Issued mismatches

Per `notes/2026-05-23_record_status_scrape_report.md` (confirmed by re-querying `record_status_queue`):

- 84 permits sit under v2-stage=`completed` projects
- **18 of those 84** have Accela `record_status = 'Issued'` — i.e., v2 says completed but Accela says permit is still active
- These 18 span **12 distinct projects**

### 5a. The 12 affected projects

| project_id | address | mismatched permits | notes |
|---|---|---|---|
| 53 | 2641 College Ave | B2024-05471 | single permit |
| 63 | 1716 Seventh St | B2022-01332, B2022-01386 | 2 permits |
| 64 | 1515 Derby St | B2025-02754 | single permit |
| 79 | 1111 Allston Way | B2025-01202 | single permit |
| 83 | 1136 Keith Ave | B2024-03997 | single permit |
| 88 | 705 Arlington Ave | B2024-01528, B2025-04937 | 2 permits |
| 92 | 3036 Regent St | B2023-03832 | single permit |
| 129 | 1614 Sixth St | B2024-04504, B2024-06099 | 2 permits |
| 139 | 2538 Durant Ave | B2023-02332, B2024-06011 | 2 permits; B2023-02332 in active `Consolidated Comments` review |
| 152 | 1598 University Ave | B2024-00587, B2024-01924, B2024-05740 | **3 permits** — most cleanly mis-categorized |
| 172 | 2650 Telegraph Ave | B2024-03280 | single permit |
| 176 | 2440 Shattuck Ave | B2024-05368 | single permit |

### 5b. Cross-reference with processing_status active stages

All 18 of these permits have an active workflow stage in `processing_status_queue` — i.e., the workflow is still running, not stalled or complete:
- 17 of 18 are in active `Inspection` stage
- 1 of 18 (B2023-02332, 2538 Durant REV09) is in active `Consolidated Comments` review

This is consistent across two independent scrapes (record_status_queue says `Issued`; processing_status_queue shows active stage). The mismatch is real and not a scrape artifact.

### 5c. APR impact

For Track 2's APR generation:
- Currently v1 reports these 12 projects as `completed` and may credit them as CO units in Table A2.
- After Track 2's CO-derivation rule (§4b) is applied:
  - Permits with `record_status = 'Issued'` and active workflow → **tier 3 → CO_date = NULL → not credited as CO**
- So Track 2 will likely *reduce* the CO-credited project count vs the v1 baseline.

Whether that reduction is the right answer for HCD APR purposes is a project-level judgment call: HCD wants units that have "completed construction" — and some of these projects may have substantially completed but not yet closed out all sub-permits. The audit's responsibility is to surface the divergence, not to silently auto-correct.

---

## Section 6 — Track 1 / Track 2 recommendation

The work splits cleanly into two tracks.

### Track 1 — DONE (today)

**Goal:** Fix the immediately-broken path, regenerate the v1 baseline, capture comparison anchor numbers.

**Deliverables:**
1. ✅ One-line fix to `scripts/generate_apr.py` DB_PATH (verified at line 26).
2. ✅ Re-run against v1; six output files written 2026-05-23 14:03.
3. ✅ Baseline report at `notes/2026-05-24_apr_baseline_run_report.md`.
4. ✅ Notebook inventory at `notes/2026-05-24_apr_notebook_inventory_and_fix.md` confirms no other notebooks need a literal path fix (1 notebook has a constructed-path bug requiring a logic refactor; out of scope for Track 1).
5. ✅ This audit (Track 1's documentation completion).

**Outcome:** v1 baseline is published and quotable. Any Track 2 regeneration can be compared to these numbers as the reference point.

### Track 2 — PENDING (next session)

**Goal:** Refactor APR generation to source from v2 + cic_recon_queue, evolving the canonical notebook (`04_reporting/D4_hcd_apr_tables.ipynb`) into a self-contained citizen-APR pipeline.

**Pre-requisites (already done):**
- v2 schema is stable; 181 projects ingested.
- record_status_queue (107) + processing_status_queue (107) are populated and authoritative.
- CofO derivation rule documented (§4b above).
- 18 v2.completed-but-Issued mismatches enumerated (§5).
- Canonical APR notebook identified: `04_reporting/D4_hcd_apr_tables.ipynb` (per notebook inventory).

**Open work (Track 2):**

1. **Extract city's CY 2025 Table A** from `/Users/johngage/berkeley-data-staging/pdf/2026-03-27  Housing Element and General Plan Annual Progress Reports.pdf` (note: two spaces in filename). Table A2 was extracted in February (`data/raw/city_apr_2025_table_a2.csv`, 236 rows × 24 cols); Table A still pending. Tabula or pdfplumber pass.

2. **Build the v2 query layer.** Re-express each of `generate_apr.py`'s 9 functions as v2-native queries:
   - `generate_table_a` → query `projects` + `unit_program` + `project_events` (filed events in CY 2025)
   - `generate_table_a2` → query `projects` + `unit_program_affordability` + `permits` + derived CO_date (§4b)
   - `generate_table_b` → aggregate by `vocabulary_income_categories` × CY 2025 BP issuance
   - `generate_developer_summary` → query `project_participants` + `organizations` where role is developer
   - `generate_rhna_progress` → reuse table_b output
   - `generate_adu_summary` → query `unit_program` where unit_category is ADU
   - `generate_stalled_projects` → query `projects` where `current_stage_type_id` matches `stalled` (only 1 project in v2 today; semantically different from v1's `is_stalled` flag — needs reconciliation)

3. **Apply the CofO derivation rule** for every project with a permit in `processing_status_queue` (107 → 100+ projects). Surface tier-1 / tier-2 / tier-3 CO_date for each. Flag the 18 mismatches from §5 explicitly.

4. **Evolve `04_reporting/D4_hcd_apr_tables.ipynb`** into the citizen-APR notebook. Per the notebook inventory, D4 is the canonical base (Colab-ready, educationally framed, CONFIG-driven paths). Two options for sourcing v2 data:
   - **(a) Direct SQLite queries** — D4 starts querying v2 directly. Higher risk of join complexity in a student-facing notebook.
   - **(b) Pre-generated v2 CSV** (`housing_projects_FINAL_v2.csv`) — keep D4's CSV-loading shape, generate the v2-equivalent CSV via a separate script. Lower risk; recommended.

5. **Project-by-project comparison** against the city's APR PDF. For each project in either dataset, classify MATCH / MISSING_OURS / MISSING_CITY / VALUE_DIVERGE / STAGE_DIVERGE. For non-MATCH rows, document the why (bad data ours / bad data city / methodological / unknown).

6. **Iterate.** Target ≥90% MATCH on project ID + unit count (±2) + stage. Document divergences for the remaining 10%.

7. **Match-quality verdict + cover memo.** If we hit ≥90%, write up the methodology and publish.

### Track 2 sequencing recommendation

Do step 1 (Table A extract) and step 4(b) (v2-equivalent CSV generation script) **in parallel** at the start of the next session — they don't depend on each other. Then steps 2, 3 feed into step 4. Step 5 follows. Steps 6 and 7 are the iteration loop.

### Things explicitly NOT in Track 2 scope

- Inspection ingest into v2 (the 6,303 inspection records). Per the session-close, this is deferred — APR-match doesn't need it.
- CPRA backfill of the 7 discarded source columns. Deferred.
- ADU catalog from CPRA's 2,644 ADU-flagged rows. Separate workstream.
- Fixing `notebooks/MASTER_ANALYSIS.ipynb` cell 20 path bug. Deferred (requires logic refactor; see notebook inventory §3).
- Layer C stage re-inference at scale (formal). The APR-match work *is* the first stage-inference exercise; formal Layer C comes after.

---

## Appendix — file references

- `scripts/generate_apr.py` (538 lines, path-fixed line 26)
- `databases/berkeley_housing_analysis.db` (v1, source for current script)
- `databases/berkeley_housing_v2.db` (v2, target for refactor)
- `databases/cic_recon_queue.db` (record_status_queue + processing_status_queue)
- `apr_specification.json` (HCD spec, 9 tables, 6 income cats, 6 unit cats)
- `apr_data_mapping.json` (Table A2 gap analysis: 5 direct / 7 derivable / 1 partial / 15 missing of 28 fields)
- `data/apr/2025/*.csv` + `apr_2025.json` (today's v1 baseline outputs)
- `data/raw/city_apr_2025_table_a2.csv` (236 rows × 24 cols, extracted from city PDF)
- `notes/2026-05-23_record_status_scrape_report.md` (the 18-mismatch detail)
- `notes/2026-05-23_processing_status_scrape_report.md` (the 9 CofO stages detail)
- `notes/2026-05-23_inspection_ingest_design_sketch.md` (deferred workstream)
- `notes/2026-05-23_session_close.md` (yesterday's primary-goal framing)
- `notes/2026-05-24_apr_baseline_run_report.md` (today's baseline)
- `notes/2026-05-24_apr_notebook_inventory_and_fix.md` (canonical-notebook identification)
- City APR PDF: `/Users/johngage/berkeley-data-staging/pdf/2026-03-27  Housing Element and General Plan Annual Progress Reports.pdf` (two spaces between date and "Housing")
