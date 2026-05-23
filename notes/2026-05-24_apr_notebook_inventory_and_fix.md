# APR notebook inventory + path-fix audit (2026-05-24)

**Generated:** 2026-05-23T14:12:29
**Scope:** find every APR-related Jupyter notebook in the repo, audit for the same broken `DB_PATH` issue that affected `scripts/generate_apr.py` (fixed yesterday), and document v1-only assumptions for the Phase D v2 refactor.

## Headline

| metric | value |
|---|---|
| Total notebooks scanned (excluding `.ipynb_checkpoints`) | 44 |
| APR-relevant | 15 |
| With the literal broken-path pattern (`data/berkeley_housing_analysis.db`) | **0** |
| With an effectively-broken path (constructed via string interpolation) | **1** (`notebooks/MASTER_ANALYSIS.ipynb`) |
| Edits applied to .ipynb files | **0** (per the task's 'no logic changes' rule — see §3) |

**Conclusion: no .ipynb edits applied.** The one notebook with a constructed broken path needs a small logic change (separate `db_dir` variable) to fix cleanly, which exceeds the task's path-only edit constraint. Documented for the Phase D refactor.

## 1. Full APR-relevant inventory (15 notebooks)

| category | broken path | v1 db | v2 db | mtime | relative path |
|---|---|---|---|---|---|
| documentation_only | — | — | — | 2026-02-26 | `00_orientation/00A_tour_of_the_pipeline.ipynb` |
| documentation_only | — | — | — | 2026-02-22 | `01_collection/A1_data_sources_setup.ipynb` |
| documentation_only | — | y | — | 2026-02-24 | `01_collection/A3_geocoding_pipeline.ipynb` |
| documentation_only | — | — | — | 2026-02-26 | `01_collection/A4_apn_enrichment.ipynb` |
| primary_apr_generator | — | — | — | 2026-04-13 | `01_collection/A9_apr_timeline_tracking.ipynb` |
| documentation_only | — | — | — | 2026-02-26 | `01_collection/A9_city_profile_builder.ipynb` |
| documentation_only | — | — | — | 2026-02-24 | `03_analysis/C3_proposal_vs_reality.ipynb` |
| documentation_only | — | — | — | 2026-02-26 | `03_analysis/C4_quality_checks.ipynb` |
| documentation_only | — | — | — | 2026-02-27 | `04_reporting/D3_alerts_monitoring.ipynb` |
| primary_apr_generator | — | — | — | 2026-02-26 | `04_reporting/D4_hcd_apr_tables.ipynb` |
| documentation_only | — | y | — | 2026-02-27 | `MASTER_ANALYSIS.ipynb` |
| documentation_only | — | y | — | 2026-02-15 | `archive/notebooks/MASTER_ANALYSIS.ipynb` |
| documentation_only | — | y | — | 2026-04-23 | `notebooks/MASTER_ANALYSIS.ipynb` |
| primary_apr_generator | — | — | — | 2026-05-18 | `notebooks/explore_berkeley_housing.ipynb` |
| documentation_only | — | y | — | 2026-04-13 | `permitpipeline.ipynb` |

Of the 44 total notebooks scanned, 29 had no APR-relevant signal and are excluded from this audit.

## 2. Audit of the 3 `primary_apr_generator` notebooks

### 2a. `04_reporting/D4_hcd_apr_tables.ipynb`

**Mtime:** 2026-02-26 (older but most APR-focused).

- **Path resolution: clean.** Cell 3 finds `ROOT` via `find_project_root()`, loads `CONFIG` from `00_config/berkeley_config.json`, then sets `DATA_DIR = ROOT / CONFIG['paths']['data_dir']` → `data/processed/`. CONFIG's `data_dir` value is `"data/processed"` (verified). Cell 5 loads `housing_path = DATA_DIR / 'housing_projects_FINAL.csv'` → `data/processed/housing_projects_FINAL.csv` (file exists, 82 KB).
- **No SQLite connection.** Reads from CSV only. Self-contained.
- **APR logic:** defines `generate_apr_table_a2(df, year=None)` inline (cell 10). Doesn't import `scripts/generate_apr.py`. Functionally a parallel implementation of A2 generation that operates on a flat CSV.
- **Educational structure:** has Colab badge, learning objectives, table-by-table explanations. Clearly designed for student audience.
- **v1-only assumptions:** the loaded CSV (`housing_projects_FINAL.csv`) is exported from v1's flat schema. Field references in the inline `generate_apr_table_a2` will assume v1 columns (vli_units, density_bonus, etc.). Not v2-aware.

### 2b. `01_collection/A9_apr_timeline_tracking.ipynb`

**Mtime:** 2026-04-13 (most recent of the 3).

- **Path: clean.** `DB_PATH = ROOT / 'databases' / 'berkeley_housing_map.db'` and `ADDRESS_DB = ROOT / 'databases' / 'berkeley_address_centric.db'`. Uses `berkeley_housing_map.db`, NOT `berkeley_housing_analysis.db` — different data source. Both DBs exist.
- Connects via `sqlite3.connect(DB_PATH)` (cell 3).
- Title says "apr timeline tracking" — looks like it tracks the timeline aspect (BP issued → CO issued) but doesn't generate the HCD tables. Probably misclassified as `primary_apr_generator` based on the `apr` keyword in the filename.

### 2c. `notebooks/explore_berkeley_housing.ipynb`

**Mtime:** 2026-05-18 (most recently modified, by far).

- **No DB connections at all.** All references are markdown describing future/eventual DB queries via Datasette.
- This is a tour/orientation notebook, NOT an APR generator. Caught by the keyword scan due to general mentions.
- Should probably be reclassified `documentation_only`.

## 3. The one notebook with an actual (but constructed) broken path

### `notebooks/MASTER_ANALYSIS.ipynb` cell 20

```python
# cell 20 line 3:
db_path = f'{data_dir}/berkeley_housing_analysis.db'
```

Where `data_dir` was set in cell 2:

```python
if IN_COLAB:
    data_dir = '/content'
else:
    data_dir = '/Users/johngage/berkeley-data'
```

**Local resolution:** `db_path = '/Users/johngage/berkeley-data/berkeley_housing_analysis.db'` — file does NOT exist there. Real path is `/Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db`. Same root-cause bug as the `generate_apr.py` issue fixed yesterday.

**Why not fixed in this prompt:** the `data_dir` variable is also used for CSV file paths in cells 7 and 12:

```python
projects_file = f'{data_dir}/housing_projects_final_complete.csv'  # cell 7
df = pd.read_csv(f'{data_dir}/housing_projects_final_complete.csv')  # cell 12
```

Those CSVs (if they exist) would live at the repo root, not under `databases/`. So `data_dir` legitimately conflates two distinct concepts: "CSV directory" (repo root) and "database directory" (`databases/` subdir). The minimal fix that would actually work requires introducing a separate `db_dir` variable — that's a logic change, not a path swap. **Per the task's "only fix the path" constraint, this fix is deferred to the v2 refactor phase.**

**Sibling notebook** `MASTER_ANALYSIS.ipynb` at the repo root uses `db_path = CONFIG['paths']['database']` where CONFIG has `"database": "databases/berkeley_housing_analysis.db"` — correct path resolution. So the root MASTER_ANALYSIS is fine; only the `notebooks/` variant has the issue.

## 4. Other notebooks worth a note

- **`permitpipeline.ipynb`** (root, 2026-04-13): has explicit `'/Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db'` literals (cells 28-30) — correct paths.
- **`01_collection/A3_geocoding_pipeline.ipynb`** (2026-02-24): references `berkeley_housing_v2.db` but only in documentation cells (no actual connection). v2-aware in name only.
- **`MASTER_ANALYSIS.ipynb`** at repo root (2026-02-27): uses CONFIG-based path resolution; correct.
- **`archive/notebooks/MASTER_ANALYSIS.ipynb`** (2026-02-15): older copy in archive; we don't need to fix archive files.

## 5. Canonical APR notebook designation

**`04_reporting/D4_hcd_apr_tables.ipynb` is the canonical candidate.**

Rationale:

- **Most APR-focused.** Named explicitly `D4_hcd_apr_tables`. The file naming convention (`D4_*`) places it in the reporting layer.
- **Educational structure already in place.** Has Colab badge, learning objectives ("Understand the APR / Map local data to APR fields / Generate an APR table / Identify gaps"), and a marked-up table explaining each APR table A/A2/B/C/D. Fits the "high-school-student-friendly" notebook the task description mentioned.
- **Clean path resolution.** Uses `ROOT / CONFIG['paths']['data_dir']` — works locally; also has a graceful fallback for Colab.
- **Self-contained.** Loads CSV, defines APR generator function inline, saves output. No fragile import dependencies on `scripts/generate_apr.py` or other notebooks.
- **Caveat:** older than the recent `explore_berkeley_housing.ipynb`, but the recent one is an orientation tour, not an APR generator. D4 is still the right base.
- **What it needs for the v2 refactor:** the inline `generate_apr_table_a2(df, year=None)` function reads v1 column names from the CSV. After v2 refactor, this should either (a) read from v2 SQLite via the joins described in `notes/2026-05-24_apr_workflow_audit.md`, OR (b) read from a v2-sourced CSV that pre-flattens the data.

## 6. v1-only assumptions documented (for Phase D refactor)

### `D4_hcd_apr_tables.ipynb`

- Reads `data/processed/housing_projects_FINAL.csv` (v1-shape: flat columns including `vli_units`, `density_bonus`, `sb35_flag`, `developer`, etc.)
- Inline `generate_apr_table_a2(df, year)` function assumes v1 column names.
- Will need either a v2-sourced CSV regeneration step OR a refactor to query v2 SQLite directly.

### `notebooks/MASTER_ANALYSIS.ipynb`

- Cell 20 path bug (documented in §3).
- `data_dir` variable conflates CSV directory and database directory — needs separation in any refactor.
- Reads `housing_projects_final_complete.csv` (cells 7, 12) — file may not exist; not verified.

### `MASTER_ANALYSIS.ipynb` (root)

- Uses `CONFIG['paths']['database']` which points at v1 (`databases/berkeley_housing_analysis.db`). CONFIG itself would need a `database_v2` key for v2 awareness.

### `01_collection/A9_apr_timeline_tracking.ipynb`

- Reads from `berkeley_housing_map.db` (separate DB from the v1 analysis DB).
- Not affected by the v1→v2 refactor — uses a different data source.

## 7. Validation

No notebook files were modified. All 44 notebooks remain in their pre-audit state. JSON validity unchanged.

## 8. Confidence: ready for Phase D refactor?

**Yes, with one explicit defer.** The Phase D v2 refactor work should:

1. **Take `D4_hcd_apr_tables.ipynb` as the canonical base.** It has the right structure (Colab-ready, educationally framed, self-contained CSV → DataFrame → APR table pipeline).
2. **Refactor its `generate_apr_table_a2` function to source from v2** — either (a) query v2 SQLite directly via the joins described in `notes/2026-05-24_apr_workflow_audit.md`, or (b) pre-generate a v2-equivalent CSV (`housing_projects_FINAL_v2.csv`) and keep D4's CSV-loading shape intact. Option (b) is the lower-risk path.
3. **Fix `notebooks/MASTER_ANALYSIS.ipynb` cell 20** by separating `db_dir` from `data_dir` (NOT in this prompt's scope).
4. **Update root `MASTER_ANALYSIS.ipynb`'s CONFIG** to add a `database_v2` key once v2 is the canonical source.
5. **Optionally retire `archive/notebooks/MASTER_ANALYSIS.ipynb`** — keep one MASTER_ANALYSIS, not three.

No blockers for Phase D. The notebook layer is in better shape than the script layer was — only one effective path bug, and it requires a small logic refactor rather than a literal path change.
