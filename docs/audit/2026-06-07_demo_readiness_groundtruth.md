# Data-Journalist Demo — Verified Readiness Ground Truth — 2026-06-07

**Read-only assessment run by Claude Code against the live repo** (canonical `berkeley_housing_v2.db`
SHA **0e9a8aab**), to ground the demo planning in facts rather than memory. Pairs with the priming
prompt `docs/audit/2026-06-07_journalist_demo_prep.md`. Nothing was modified.

## Readiness: HAVE / PARTIAL / MISSING (verified)

| Capability | State | Ground truth |
|---|---|---|
| **1. DB + Datasette + NL→SQL** | **PARTIAL** | v2 = 46 tables / 9 views. Datasette **is** deployed (`datasette-deploy/`, Fly) but serves **export artifacts** `berkeley_housing_map.db` + `berkeley_address_centric.db`, **not full v2** (no `project_stages`/`documents`/participants). berkeleybuild.com = 5 static files in `docs/`. **NL→SQL not wired anywhere found.** |
| **2. Per-project PDF links** | **PARTIAL — scaffolding built, content empty** | Purpose-built **`documents` table: 1,979 docs → 747 projects** (cols: `project_id`, `title`, `permit_number`, `document_type_id`, hosting cols `ia_url`/`r2_url`/`drive_url`/`source_url`, `ocr_text_path`, `sha256`, `page_count`). **But only 7/1,979 have any URL; `url_status`: 1,268 "unknown"; filenames live in `notes`.** Links exist; hosted/retrievable files do not. |
| **3. AI-on-PDFs** | **MISSING (layer empty)** | `documents.ocr_text_path`=0, `sha256`=0, `page_count`=0. No OCR/text layer. Tooling ad-hoc only (`pdftotext`, PyMuPDF). |
| **4. KML label fields (7)** | **5 of 7 have data (scattered); 2 thin** | See corrected source map below. |
| **5. KML tours + geometry** | **HAVE (geometry/tours); label-wiring PARTIAL** | **55 `.kml`** on disk (`docs/geometry.kml`, `docs/tours/*`, skyline) + flyover **videos** (`docs/videos/*.mp4`). V1 `berkeley_housing_analysis.db` also has `project_geometries`/`project_map`. DB-driven labels not yet wired. |

## CAP 4 — corrected label-field source map (the key revision)
Earlier "4 missing" was too pessimistic. Most "missing" fields are **collected-but-not-in-v2**, not
absent. v2's `vocabulary_role_types` has all 21 roles defined; only 3 are populated.

| Field | In v2 `project_participants`? | Where the data actually lives | Verdict |
|---|--:|---|---|
| **owner** | 29 (`owner_current`) | + `accela_reports.db record_details.owner_name` (37) + `owner_enrichment` + assessor `OwnerName` (all parcels, by APN) | **HAVE (broad)** |
| **developer** | 39 (`developer_of_record`) | v2 | **HAVE** |
| **architect** | 44 (`architect_design`) | v2 | **HAVE** |
| **city planner** | 0 (`staff_planner` empty) | **`accela_reports.db record_details.planner_name`/`_email` (37) + `project_planners` resolver + `outreach.db (data/outreach/) staff_mailing` (67 staff, name/email/domain) + V1 `permit_events.marked_by`/`assigned_to` + `.txt` scrapes ("By: …")** | **COLLECTED, not in v2** |
| **status** | full | `project_stages` / `v_projects_flat` | **HAVE** |
| **builder (GC)** | 0 (`general_contractor` empty) | not in CPRA columns; `record_details.applicant_company` (37) is only a proxy | **THIN — needs new extraction** |
| **inspector** | 0 (no rows) | only inside V1 `permit_events` building events / `.txt` scrapes; not parsed to a clean field | **THIN — needs new extraction** |

**Implication:** CAP 4 is mostly a **consolidation/migration job** (pull planner/owner/applicant from
`accela_reports.db` + the 67-staff roster + scrapes into v2 `project_participants`), not a collection
job. Only **builder + inspector** need genuinely new extraction (CPRA contractor field / building
inspection records).

### Supporting stores found (verified)
- **`databases/accela_reports.db`** — party/staff store: `record_details` (37 rows:
  applicant/owner/planner name+email+company), `project_planners`, `owner_enrichment`; plus
  scaffolded-but-empty `permit_pipeline` (`applicant_name/company/owner_name/current_planner`) and
  `project_documents` (`planner_extracted/planner_email_extracted`).
- **`data/outreach/outreach.db`** — `staff_mailing` = **67 city staff** (name/email/domain) →
  planner/inspector name resolver.
- **V1 `databases/berkeley_housing_analysis.db`** — `permit_events` (assigned_to/marked_by planner
  names), `project_documents`, **`sfyimby_projects`** (construction-start), `project_geometries`,
  `project_map`, `building_permits`, `permit_fees`.
- **Accela raw = `.txt`, not JSON** (0 JSON under `data/raw/accela_status`; the scrapes are per-record
  Processing-Status dumps; 117 contain a party/staff term). *Format/path difference, not absence.*

## The 3 real build gaps
1. **Document content layer (CAP 2+3):** catalog done (1,979 docs/747 projects); missing =
   **fetch → host (IA/R2/Drive) → populate URL cols → OCR into `ocr_text_path`.** 7/1,979 hosted today.
2. **NL→SQL + a v2-backed Datasette (CAP 1):** deep-query demo needs Datasette on **v2** (with
   `documents`, `project_stages`, participants), not the current export DBs, plus a text-to-SQL layer.
3. **Builder + inspector labels (CAP 4):** the only two label fields with no existing data source.

## Why verify-before-characterize matters here (worked example)
2109 Virginia St (proj15, ZP2024-0066): v2 stores `height_stories = 2` — **wrong**; that's the
existing 2-story commercial being demolished. The planning entitlement is a **new 8-story, 131-unit**
building (developer Panoramic Interests, architect Trachtenberg, owner American Commonwealth
Associates). Unit count (131) is right; story count is a captured-the-wrong-structure error. Any
label/demo surface drawing from v2 fields must expect this class of error and validate against the
source document.
