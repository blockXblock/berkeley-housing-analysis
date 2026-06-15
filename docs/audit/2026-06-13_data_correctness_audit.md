# Berkeley Housing v2 — Data-Correctness Audit (read-only ground truth)

**Date:** 2026-06-13 · **Authority:** live `databases/berkeley_housing_v2.db` (not docs/summaries) · **No writes, no fixes.**
Severity legend: 🔴 critical (corrupts APR output) · 🟠 high (stale/inferred-as-verified) · 🟡 medium (localized) · ⚪ note/limitation.

---

## A. SCHEMA GROUND TRUTH
- **A1.** Objects: **46 tables, 9 views, 48 indexes**.
- **A2.** vs the 34-table April baseline → **~12 tables added**: `permits`, `project_events` (with `implies_stage_type_id`), `project_classifications`, `project_stages`, `project_geometries`, `project_addresses`, `project_participants`, `fees`, `structures`, `_quarantine_documents`, `_quarantine_duplicate_addresses`, `_audit_low_confidence`, `_audit_migration_log`. ⚪ **No `inspections` table exists** despite 92 inspection JSONs on disk (see J).
- **A3. Empty / suspicious tables:** 🟡 `people` = **0** (participants link to `organizations` instead — 56 orgs / 112 participants), `external_system_links` = 0, `project_assets` = 0, `project_bundles` = 0, `_audit_migration_log` = 0. Core tables healthy: projects 885, project_versions 883, unit_program 883, unit_program_affordability 890, project_events 3869, permits 954, documents 2039, parcels 871.
- ⚪ **885 projects vs 883 versions / 883 unit_program** — 2 projects lack a current version or unit_program row (minor; worth a targeted check).

## B. SOURCE-OF-TRUTH vs PUBLISHED (staleness)
- **B4. `v_projects_flat` is a LIVE VIEW** ✓ — reflects today's writes (proj35 VLI34/MOD34/384, proj36 152, proj13 14/118). No materialization lag.
- **B5. 🟠 Published Datasette is STALE & a separate artifact.** `datasette-deploy/` serves **`berkeley_address_centric.db` (Feb 27 2026)** and **`berkeley_housing_map.db` (Mar 30 2026)** — **~3.5 months old**, predating the April v2 migration *and* all affordability/stage work. It is **not** v2 served live; it is a separately-built artifact with **no rebuild script found** in `datasette-deploy/`. Anything linked to a journalist from this deploy shows pre-v2 data.
- **B6. "What must rebuild after a v2 write" checklist:**
  | consumer | source | last regen | state |
  |---|---|---|---|
  | `v_projects_flat` (view) | v2 live | n/a | ✅ current |
  | `generate_apr_v2.py` output | v2 via v_projects_flat (live) | on-run | ✅ current when run |
  | `docs/explorer_data.js` (site) | `export_explorer_data_v2.py` → v2 | published main `6de6dd3` today | ✅ current (dev local copy 11:11 trails the working.js — cosmetic) |
  | **Datasette deploy dbs** | unknown build | **Feb/Mar 2026** | 🟠 **STALE ~3.5mo** |
  | KML tours | manual/export | Jun 9–10 | 🟡 likely stale vs today |
  | D5 APR (`D5_apr_from_cpra.ipynb`) | **CPRA xlsx/csv directly** | notebook-run | ⚪ different source axis (see G/H) |
- **B7. APR generator:** `generate_apr_v2.py` → `DB_PATH = databases/berkeley_housing_v2.db`, reads **v_projects_flat LIVE** ✓. 🟠 **But there are TWO APR paths**: `generate_apr_v2.py` (from v2) **and** `D5_apr_from_cpra.ipynb` (from CPRA directly, 53 CPRA refs). They can diverge; `D6_diff_d5_vs_hcd` exists to diff D5 vs HCD — implying **D5/CPRA, not v2, may be the operative APR**. If so, **today's v2 affordability/stage work does not feed the APR at all.** ← needs an explicit decision on which is authoritative.

## C. STAGE / MILESTONE CORRECTNESS (classifier axis)
- **C8.** ✅ Confirmed: stage = materialized `projects.current_stage_type_id` (the view just reads it); milestone dates in `v_projects_flat` use a **negative "NOT permit_classified_subsidiary" filter only** — no positive `completes_project` test, no `is_inferred` filter, no `is_evidentiary_co_event()`. `permit_role_classifier.py` is imported **only by 6 one-off audit scripts in `analysis/audit_2026-05-16/`** — **not** the live export/APR.
- **C9. CO event population (775):** 13 stubs · **140 evidentiary→completes_project** · **35 evidentiary→does_not_complete (the bug)** · **587 ambiguous**. 🔴 **605 projects** marked `completed`/`under_construction` rest on non-completes evidence; **34 are in the curated pipeline (id≤189)**: `27,53,63,64,70,71,79,84,87,88,90,91,92,102,105,111,124,126,135,136,137,138,139,153,165,170,175,177,178,185,186,187,188,189`. proj79 CO = *"ROOF MOUNTED PHOTOVOLTAIC"*; proj153 UC rests on a Photovoltaic BP + a permit-less stub.
- **C10. is_inferred rates:** 🔴 `co_issued` **91.4%** inferred (708/775) · `entitlement_approved` 0.4% (1/283) · `building_permit_issued` 0% · `permit_finaled` 0% (n=2). **CO is the rotten milestone; BP & entitlement are source-verified.**

## D. INTERNAL CONSISTENCY
- **D11.** ✅ **0** tier-sum-vs-total_units mismatches (all current versions balance).
- **D12. 🟡 units-vs-stories outliers** (placeholder `height_stories`): proj1 (739u/8st=92/floor), **proj154 (87u/1 story)**, **proj123 (74u/1 story)**, proj135 (169/3), proj136 (163/3), proj177 (556/12). The 1-story rows are almost certainly missing/placeholder height.
- **D13. 🟠 proj15 leak LIVE:** `total_units=110` but **unit_program unit_mix sums to 131**, affordability sums to 110 — a 21-unit internal disagreement (only such project).
- **D14. 🔴 stage decoupled from milestones:** **731** `completed`/`under_construction` projects have **no `bp_issued_date`**; **744** `entitled`+ projects have **no `entitlement_approved` event**. (D14b: 0 projects with a CO date but stage < completed — direction consistent.) Stage is overwhelmingly migration-asserted, not event-backed.
- **D15. 🟠 confidence ≠ evidence:** **105** affordability rows are `confidence=high` but `source_document_id IS NULL` (inferred-as-verified); plus **704** rows are `confidence=medium` cited to **untyped stub documents**. (D15b: 0 cited-but-low — the flag write was clean.)

## E. PROVENANCE / DUPLICATE / CONTAMINATION
- **E16. 🟡 permit-string contamination:** proj2 **`ZP2023-00401974`** (id 105) = `ZP2023-0040` + `1974` concatenated — **still present**. The other 45 "non-standard" permits are **valid alt prefixes** (DRCF/ZCBP/DRSL/REV01), not contamination.
- **E17. 🟠 duplicate projects hidden by address corruption:** proj115 address = **`2455 TELEGRAPH Ave (id:115)`**, proj118 = **`2138 KITTREDGE St (id:118)`** — the `(id:NNN)` suffix is baked into **both `canonical_address` AND `normalized_address`**, disguising the dup and defeating address-dedup. **10 shared-APN project pairs** are the true dup set: `25/115, 54/62, 86/109, 96/138, 113/118, 162/127, 362/888, 544/852, 624/869, 645/880`.
- **E18. ⚪ inconclusive:** no permit_number links to >1 project; permits carry no own address, so single mislinks (the proj152↔164 pattern) are **not detectable by this method** — needs an address-bearing permit source.
- **E19.** ✅ **Zero broken FKs** (affordability→unit_program, source_document_id→documents, events→projects, permits→projects all clean). 75 docs carry `r2_url` — **404-liveness not network-checked** (⚪ limitation).

## F. APR-READINESS (the 186 pipeline projects)
- ~**57** have a BP `issued_date` in `permits`; **55** have a *verified* `building_permit_issued` event; **44** have a `finaled_date`; **103** are **pre-permit / planning-only** (no entitlement/BP/CO).
- 🔴 **A year-scoped A2 cannot be produced safely today:** the completed-row signal is 91% inferred and unclassified (solar/demo COs leak through), and every *cited-affordable* project is pre-permit. We can place a project in *entitled-year* reasonably, but **permitted-year** needs the permit→event materialization (see J) and **completed-year** needs evidentiary classification.

## G. CPRA CORPUS
- **G22.** CPRA **is** ingested → **827 permits** (`source_system='cpra'`) of 954 total (others: 85 accela, 36 planning, 5 building, 1 v1). 832 are `building_permit` type; **847/954 carry a `description`** (good for the classifier). ⚪ Could not re-count the source xlsx (no `pandas`/`openpyxl` in venv) — documented corpus is ~32,202 rows / 30,764 unique; **only 827 made it into v2**, i.e. ingestion is **selective to permits matching a tracked project** — the rest of the city-wide corpus is unused.
- **G23. ⚪ dedup not independently re-verified** (xlsx unreadable here); v2 holds 954 distinct permit *rows*, consistent with unique-permit (not raw-row) counting.
- **G24. ⚪ CPRA↔Accela reconciliation not run** (deferred — needs a permit-number join + field compare; both sources are present so it's doable).
- **G25.** 🟠 **D5 reads CPRA directly**; `generate_apr_v2.py` reads v2. Conflict-resolution / precedence between the two APR paths is **undocumented** — silent precedence risk.

## H. HOUSING_RULES CYCLE-CLASSIFIERS
- **H26.** 🟠 `scripts/housing_rules/` is imported by **nothing** (orphaned, same drift as the classifier).
- **H27/28.** 🔴 **No cycle columns** (`bp_cycle`, `co_cycle`, `*_in_projection_period`) exist in `project_events` or `permits` — RHNA projection-period logic is **not materialized and not applied**. Any current A2 counts years **flat**, not scoped to the 6th-cycle projection window — so it is **not comparing the same time-window as HCD's A2**.

## I. DRIFT AUDIT (orphaned-but-claims-active)
🟠 Confirmed orphaned from the live pipeline (code present, nothing in export/APR imports it):
- `permit_role_classifier.py` — only 6 audit-only importers (May 16), docstring claims export uses it (**false**).
- `scripts/housing_rules/` — 0 importers.
- `scripts/build_scrape_queue.py`, `scripts/build_url_discovery_queue.py` — 0 importers.
This is the recurring meta-pattern: components built, then disconnected, while summaries imply they're active.

## J. RAW-CORPUS-vs-v2 INGESTION (acquisition vs ingestion)
- **J30. Raw corpus on disk:** `accela_status/` **91 .txt** (planning, 1.4 MB) · `accela_status/building/` **40 .txt** (appear sparse/stub — sample showed address-only) · **`R2_R3_permits_2023_2025.tsv` = 1573 rows of rich building data** (Date / Permit# `ESR-…` / Status / Address / Occupancy Class) · `R2_permits…tsv` · 2 CPRA xlsx · **92 inspection JSONs** · 102 url-discovery JSONs.
- **J31/32. In v2 vs on disk:**
  - 🔴 **`R2_R3` building tsv (1573 permits w/ status+occupancy+date): NOT ingested** — 0 of its `ESR-…` permits appear in v2 (`source_system='building'` = only 5).
  - 🔴 **92 inspection JSONs: NOT ingested** — there is no `inspections` table (first-inspection / final-inspection-passed evidence is therefore unavailable).
  - building `B_*.txt` (40): appear to be near-empty stubs (sample = address line only) — low yield.
- **J33. Pipeline (id≤189) milestone data we HAVE vs INGESTED:** permits table already holds a **BP `issued_date` for 57** and **`finaled_date` for 44** pipeline projects — **but only ~32 surface as `building_permit_issued` events** in `v_projects_flat`. 🔴 **The permit *rows* carry dates the *event* layer never materialized.**
- **J34. VERDICT — it is BOTH, ingestion-first:**
  1. **Ingestion gap (cheap, high-yield):** materialize `building_permit_issued` / `permit_finaled` events **from existing permit rows** (57 BP / 44 Finaled dates already in v2, with descriptions) → would lift verified-BP pipeline coverage from ~32 to ~57 and give 44 classifiable Finaled candidates **with zero new harvesting**.
  2. **Ingestion gap #2:** parse the **R2_R3 building tsv (1573 rows)** + the **92 inspection JSONs** already on disk.
  3. **Acquisition gap (real but smaller):** a dedicated **Building-tab CO/Finaled harvester** is still needed for projects with *no* permit row at all and to get authoritative new-construction Finaled status — but **close the ingestion gaps first**; they recover most of the BP signal and much of the Finaled signal before any new scraping.

---

## TOP CONTRADICTIONS, RANKED
1. 🔴 **Stage is fiction at scale:** 744 "entitled+" with no entitlement event, 731 "completed/UC" with no BP date; CO milestones 91% inferred; 605 completions rest on non-new-construction permits (solar/demo). **The APR completed/permitted rows are not milestone-backed.**
2. 🔴 **RHNA cycle scoping absent** (H27/28) — counts aren't projection-period-scoped, so they don't align to HCD's window even if milestones were clean.
3. 🟠 **Two APR sources (v2 vs CPRA) with undocumented precedence** (B7/G25) — today's v2 work may not even reach the published APR.
4. 🟠 **Published Datasette ~3.5 months stale** (B5) — separate artifact, no rebuild script.
5. 🟠 **Milestone data is on disk but un-ingested** (J) — 57 BP / 44 Finaled dates in permit rows not surfaced as events; 1573-row building tsv + 92 inspection JSONs unparsed.
6. 🟠 **Inferred-as-verified:** 105 high-confidence-uncited affordability rows + 704 cited-to-stub-doc rows (D15).
7. 🟠 **Duplicate projects hidden by `(id:NNN)` address corruption** (E17) — 10 shared-APN pairs; address field itself polluted.
8. 🟡 **proj15 131-vs-110 unit leak** (D13); 🟡 proj2 `ZP2023-00401974` concatenation (E16); 🟡 1-story placeholder heights (D12).
9. 🟠 **Drift meta-pattern** (I): classifier + housing_rules + queue builders all orphaned while assumed active.

## MINIMUM TO A TRUSTWORTHY, HCD-COMPARABLE A2 (no fixes proposed here — scope only)
1. Decide the **single authoritative APR path** (v2 vs CPRA) and wire it.
2. **Materialize BP/CO events from permit rows** + ingest the building tsv + inspections (J34 #1–2).
3. **Re-wire the classifier** (graded: filter the 35 does_not_complete now; flag 587 ambiguous) so completions are evidentiary.
4. **Add RHNA cycle/projection-period scoping** (housing_rules) to the milestone layer.
5. Resolve the **10 APN-duplicate pairs** and un-corrupt the `(id:NNN)` addresses.
6. Rebuild the **Datasette artifact** from current v2.
Until 1–4 hold, any A2 we publish inherits the stage-inference, contamination, and cycle-scope bugs above.

## LIMITATIONS OF THIS AUDIT (not verified here)
- CPRA xlsx row counts / dedup not re-counted (no pandas/openpyxl) — relied on v2-side counts.
- CPRA↔Accela field reconciliation (G24) not run.
- r2_url 404-liveness (E19) not network-checked.
- "34-table April baseline" mapping (A2) inferred from current schema, not the original DDL.
