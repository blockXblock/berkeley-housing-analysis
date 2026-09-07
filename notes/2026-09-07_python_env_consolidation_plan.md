# Python environment consolidation — migration plan (DRAFT, not executed)

**Date:** 2026-09-07 · **Status:** proposal, awaiting John's go-ahead · **Nothing has been changed.**

> **Rev 2 (same day).** John challenged the version pinning. Two corrections, both measured:
> (a) rev 1 never examined the **Python** version at all — a gap, now closed as **D5**;
> (b) rev 1's claim that the code is pandas-2.x-dependent was **asserted, not measured, and is
> false** — see §1.5. **D1 flips from "pin pandas 2.3.x" to "target pandas 3.0.5."**

---

## 1. Current state (measured, not assumed)

Three environments exist; the repo actively uses two.

| | `.venv` (repo) | `jupyter_env` (conda) | `base` (conda) |
|---|---|---|---|
| Path | `~/berkeley-data/.venv` | `/opt/miniconda3/envs/jupyter_env` | `/opt/miniconda3` |
| Python | 3.12.8 | 3.12.8 | 3.12.1 |
| Installed pkgs | 114 | 239 | 248 |
| pandas / numpy | **3.0.5** / 2.5.1 | **2.3.3** / 2.3.5 | 2.2.3 / 1.26.4 |
| Referenced by | 16 scripts | 14 scripts | 0 scripts |

Two more Python installs exist and were missed in rev 1:
**`scratch/2026-09-04/svgvenv/`** (a stray venv, **Python 3.14.0**, CairoSVG work) and the
Homebrew system interpreter (**3.14.0**). So the machine already runs 3.14 successfully.

**The split tracks nothing.** `scripts/block_headroom.py:37-38` documents *both*, and its
`.venv` note is factually wrong (claims geopandas; `.venv` has none). The only real
asymmetry is `boto3` in `.venv` vs geo/PDF/datasette in `jupyter_env` — an accident of
install history, not a design.

### 1.1 Finding A — the real dependency surface is 29 packages, not 239

An AST scan of every `.py` and `.ipynb` in the repo (excluding `.venv`, `.git`, `archive`,
`scratch`), filtering stdlib and local modules, yields the complete third-party set:

```
143 pandas      36 IPython     32 nbformat    28 matplotlib   26 plotly
 22 requests    21 numpy       18 geopandas   18 pyarrow      14 playwright
 11 shapely      7 openpyxl     5 fitz(pymupdf) 4 bs4          4 folium
  4 botocore     4 sodapy       3 PIL          2 boto3         2 pyproj
  2 fuzzywuzzy   1 ipywidgets   1 browser_cookie3  1 nbconvert  1 rapidfuzz
  1 seaborn      1 dotenv       1 mpl_toolkits 1 lxml
```

**Both current envs are ~85% ballast.** Confirmed vestigial (zero import sites repo-wide):
`duckdb`, `sqlite-utils`, `nbclient`, and the entire TensorFlow/Keras stack (~30 packages —
its only mention is pip *output text* inside `archive/notebooks/berkeley_open_data_pipeline.ipynb`).
`tabula-py` is never imported; the apparent hits were `tabulate` and the word "tabular."

Note `pyarrow` has **18 import sites** and is **absent from `.venv`** — so `.venv` cannot
open `data/raw/overture_buildings_berkeley_2026-08-19.parquet` today.

### 1.2 Finding B — conda is not doing conda's job

Splitting `jupyter_env` by install channel:

- **104 packages from conda channels** — all base runtime or Jupyter plumbing
  (`python`, `openssl`, `sqlite`, `libpng`, `freetype`, `blas`/`libopenblas`, `pillow`,
  `ipython`, `tornado`, `pyzmq`, `zlib`).
- **135 packages from PyPI** — and *every* domain package is here: `geopandas`, `shapely`,
  `pyproj`, `pyogrio`, `pyarrow`, `datasette`, `pymupdf`, `matplotlib`, `sodapy`.

The historic justification for conda in this stack was GDAL/PROJ binaries for geopandas.
**That justification is already gone in this very env** — `pyogrio` (the modern wheel-based
GDAL binding) came from PyPI. There is no conda-native dependency to migrate.

### 1.3 Finding C — the import story is broken in the same way the env story is

- `scripts/__init__.py` **exists**, so `scripts` is a package and
  `python -m scripts.housing_rules.test_smoke` runs (verified — passes).
- But **92 of 218 scripts** call `sys.path.insert`/`append` to reach siblings, and
  **45 import `housing_rules` flat** (plus flat sibling imports: `s0_keys` ×17,
  `gating` ×9, `cpra_dedup` ×9, `gen_building_loop` ×9, `housing_predicates` ×8,
  `gen_svg_labels` ×6).
- **This is a live dual-identity hazard**, not just untidiness: the same code is reachable
  as `housing_rules` *and* `scripts.housing_rules`, which Python treats as two distinct
  module objects with separate state. Two copies of a classifier whose hash is load-bearing
  (ADR-002 `completion_verdict_by`) is a correctness risk, not a style complaint.

`scripts/v4/`, `scripts/migration/`, `scripts/finance_curriculum/` have **no `__init__.py`**.

### 1.4 Blast radius of the conda path

14 scripts hardcode `/opt/miniconda3/envs/jupyter_env/bin/python`. **13 are `Run:` banner
comments in docstrings** — inert. Exactly one is a runtime dependency:

- **`scripts/gen_measure_u_site.py:690`** globs
  `/opt/miniconda3/envs/jupyter_env/lib/python3.1*/site-packages/plotly/package_data/plotly.min.js`.
  This *will* break on migration.

Also carrying the path: `PROGRESS.md:2225`, `notes/2026-08-14_bond_maps_handoff.md:178`,
`notes/2026-08-16_geometry_tours_handoff.md:99`, `notes/v4/HANDOVER_2026-07-02.md:59`,
`MASTER_ANALYSIS.ipynb` kernelspec (all other notebooks use generic `python3`), and ~10
permission entries in `.claude/settings.local.json` (these merely stop matching → extra
prompts; cosmetic).

**No cron/launchd job** references either env. **No consumer outside this repo** references
`jupyter_env` (bounded search: `~` to depth 4, excluding Library/Trash/miniconda — *not*
exhaustive; see §7).

### 1.5 Finding D — the code is NOT version-dependent (measured)

Rev 1 asserted the code "was written against pandas 2.x" and implied fragility. That was
never measured. Measuring it across all **196 pandas-importing files**, excluding every
venv, `site-packages`, and `archive/`:

| pandas 3.0 breaking pattern | files |
|---|---|
| `inplace=True` | **0** |
| `applymap` (removed in 3.0) | **0** |
| `fillna(method=)` | **0** |
| `iteritems` | **0** |
| `is_categorical_dtype` / `is_sparse` / `is_datetime64tz_dtype` | **0** |
| `astype(object)` / `dtype == object` | **0** |
| chained assignment `df[...][...] = ` | **0** (all apparent hits were plain dict-of-dict) |
| `.values` attribute | 27 — **still valid in 3.0** |
| removed-stdlib imports (py3.13/3.14 "dead batteries") | **0** |
| real `distutils` imports | **0** |

Every alarming hit in the first pass was **vendored `pip`/`cffi` code inside
`scratch/2026-09-04/svgvenv/`**, not our code. *(Method note: the first scan used unquoted
`--include=*.py`, which the shell glob-expanded, returning spurious zeros. Re-run with
quoted globs and explicit venv exclusion.)*

Note also `.venv` **already runs pandas 3.0.5 today** for the scrapers — 3.0 is partly
proven in-repo.

### 1.6 Finding E — the newest stack works, verified by execution

Not inference; actually run.

1. **Resolution.** All 27 packages resolve clean on **3.12, 3.13 and 3.14** — identical
   131-package sets, pandas 3.0.5, numpy 2.5.3.
2. **Install.** Full stack installed into a throwaway **Python 3.14.0** venv: **OK**.
3. **Imports.** All 27 modules import — `geopandas`, `shapely`, `pyproj`, `pyarrow`,
   `playwright`, `pymupdf`, `sodapy`, `browser_cookie3`, `folium`, `seaborn`, `lxml`:
   **zero failures**.
4. **Real project data** under 3.14 + pandas 3.0.5:
   - `data/raw/overture_buildings_berkeley_2026-08-19.parquet` → 62,651 × 12 **OK**
     *(this is the file `.venv` cannot open today — no pyarrow)*
   - `v_projects_flat` → 909 × 38 **OK**
   - geopandas reproject 5,000 parcels EPSG:4326 → 3310 **OK**
5. **Benchmark**, `berkeley.db.parcels`, 29,134 rows, identical query and string ops
   (APN upper/replace/contains — what this repo does constantly):

   | | load | deep memory | string ops |
   |---|---|---|---|
   | pandas 2.3.3 (today's generators) | 0.49s | **36.2 MB** | 0.023s |
   | pandas 3.0.5 (candidate) | 0.21s | **16.1 MB** | 0.009s |

   **56% less memory, ~2.3x faster load, ~2.6x faster string ops.** The memory reduction is
   attributable specifically to pandas 3.0's Arrow-backed string dtype; the speed figures
   combine the pandas and interpreter changes and should not be attributed to either alone.

---

## 2. Target state

**One uv-managed `.venv` at the repo root**, declared by `pyproject.toml` + `uv.lock`, with
the repo installed editable so `housing_rules` resolves without `sys.path` surgery.

**Python 3.14.0 · pandas 3.0.5 · numpy 2.5.3** — the newest, not the oldest (§1.5, §1.6).

Rationale for venv+uv over conda: §1.2 (no conda-native deps), plus `uv` is already
installed (`~/.local/bin/uv`, v0.11.8) and a lock file fixes drift you already have —
`requirements.txt` lists 14 packages against real envs of 114 and 239.

### 2.1 Why a lock file here specifically

CLAUDE.md's *derive-and-compare-against-a-timestamped-baseline* discipline makes floating
dependency resolution a real hazard: a JN figure could move because pandas moved, firing a
gate on correct data. That is precisely the "a stale check erodes trust in checking itself"
failure the project's own rules warn about. Pinning is not ceremony here; it is the same
principle applied one layer down.

---

## 3. Phases

Each phase is independently verifiable and reversible. **Old environments stay untouched
until Phase 5.**

### Phase 0 — Baseline capture *(do this first; it is the safety net)*

The one step most migrations skip and then regret.

1. Freeze both envs: `pip freeze` → `data/baselines/env_freeze_venv_2026-09-07.txt` and
   `..._jupyter_env_2026-09-07.txt`.
2. Under **`jupyter_env` as it stands today**, run the load-bearing generators and hash
   their outputs: `export_explorer_data_v2.py`, `generate_apr_v2.py`,
   `gen_pipeline_state_page.py`, `gen_measure_u_site.py`, `block_headroom.py`, and the
   `scripts/v4/build_jn_*.py` set.
3. Record to `data/baselines/env_migration_baseline_2026-09-07.json` — per-artifact
   SHA-256, row counts, git SHA, both env freezes.

**Exit gate:** the baseline file exists and every listed generator ran clean.

### Phase 1 — Build the new env beside the old one *(no switch)*

1. Author `pyproject.toml` from the §1.1 measured set — **not** from either `pip freeze`.
2. `uv lock` → `uv sync` into **`.venv-new`**. Nothing points at it yet.
3. Verify: import all 29 packages; `python -m scripts.housing_rules.test_smoke` and
   `test_permit_role` pass; confirm `playwright` sees the existing browser cache at
   `~/Library/Caches/ms-playwright` (should need no re-download); register `ipykernel`.

**Exit gate:** clean resolve, both test modules pass. **Verify here, don't assume:** wheel
availability on py3.12/arm64 for `geopandas`, `pyproj`, `shapely`, `pymupdf`, `sodapy`,
`browser_cookie3`. Evidence says fine (all are already PyPI-installed in `jupyter_env`),
but confirm rather than assert.

### Phase 2 — Reproduce the baseline under the new env *(the real gate)*

Re-run every Phase-0 generator under `.venv-new`. Diff outputs against the recorded hashes.

**Any diff is diagnosed, never accepted.** This is where a pandas behavior change surfaces.
Per CLAUDE.md: a legitimate change appends a new timestamped baseline; it does not edit the
old one.

**Exit gate:** byte-identical outputs, or each diff explained and a new baseline appended.

### Phase 3 — Fix the import story *(separate gated step — see §4)*

Editable install makes `scripts` importable from any cwd. Then rewrite the 92 `sys.path`
sites to one canonical import form (decision D2 below).

Safety net is thin — two smoke-test modules — so the **Phase-0 golden outputs are the actual
net.** Re-run Phase 2's comparison after the rewrite.

### Phase 4 — Retire the stale references

1. **`gen_measure_u_site.py:690`** — replace the hardcoded glob with
   `importlib.util.find_spec("plotly")`. *(The one genuine code fix.)*
2. 13 `Run:` banners → the new interpreter.
3. `MASTER_ANALYSIS.ipynb` kernelspec → the repo kernel.
4. `PROGRESS.md:2225` + the 3 handover notes in `notes/`.
5. `requirements.txt` → a pointer to `pyproject.toml` (or delete; it is already fiction).
6. Fix the wrong `.venv`-has-geopandas claim at `block_headroom.py:37-38`.
7. Refresh `.claude/settings.local.json` permission entries.
8. `swap: .venv → .venv-old`, `.venv-new → .venv`.

### Phase 5 — Decommission *(not before one full working cycle)*

Keep `jupyter_env` and `.venv-old` in place until the consolidated env has run a real cycle
(an APR/explorer regeneration + a harvest + a JN rebuild). Only then remove.

---

## 4. Sequencing constraint (important)

**Do not combine Phase 2 and Phase 3.** If the env swap and the import rewrite land
together and an output diff appears, the diff is uninterpretable — you cannot tell whether
pandas moved or an import now resolves to different code. Env first (zero code change),
imports second.

This corrects my earlier framing to John: the two problems share a *root cause*, but they
must not share an *execution step*.

---

## 5. Decisions — **SETTLED 2026-09-07** (John: "take all your recommendations, D1 through D7")

| | Decision | **Settled as** |
|---|---|---|
| **D1** | pandas version | **3.0.5**, staged via 2.3.3 (see sequencing below) |
| **D2** | canonical import form | **`from scripts.housing_rules import ...`** — no file moves, no CLAUDE.md canonical change |
| **D3** | PEP 723 for `scratch/` one-offs | **Adopt, hybrid** — inline `# /// script` + `uv run` for standalone throwaways only |
| **D4** | vestigial stack | **Drop** TensorFlow/Keras (~30 pkgs), `duckdb`, `tabula-py`, `sqlite-utils` — all zero import sites |
| **D5** | Python version | **3.14.0** |
| **D6** | `fitz` → `pymupdf` | **Rename**, 5 sites, folded into Phase 3 |
| **D7** | `fuzzywuzzy` → `rapidfuzz` | **Migrate** the 2 sites; `fuzzywuzzy` then leaves the dependency set entirely |

**D1 × D5 compatibility — verified, not assumed.** The staged pandas plan requires 2.3.3 to
run on 3.14, which is not obvious (pandas 2.3.3 predates Python 3.14). Tested: resolves on
3.12/3.13/3.14 and a **cp314 wheel installs and imports OK**. The two-step is viable.

**Revised staging** (D1 + D5 interact — the baseline is captured on py3.12.8/pandas 2.3.3):
- **Phase 2** — py**3.14** + pandas **2.3.3** vs the Phase-0 baseline. Changes env manager
  *and* interpreter, both plumbing-level; expects **byte-identical** output. This isolates
  pandas *out*.
- **Phase 2b** — bump pandas to **3.0.5**. Now pandas is the **only** variable, so any diff
  is attributable and diagnosable, and a legitimate change appends a new baseline.

*Phase 2 is deliberately not a pure single-variable test; the two confounds it does carry
(conda→uv, 3.12→3.14) are plumbing that should not move numerics. Pandas, which can, is
isolated alone in 2b.*

Rationale for each decision retained below.

### 5.1 Rationale (as decided)


**D1 — pandas 3.0.5 (recommended), reached in two steps.**
Rev 1 recommended pinning 2.3.x on a code-fragility argument that measurement does not
support (§1.5: zero breaking-pattern hits). The capability case for 3.0 is strong and
specific to this repo: **Arrow-backed strings by default**, on data that is overwhelmingly
strings — APNs, addresses, permit descriptions, owner names, 29k parcels, 85k events, plus
fuzzy address matching. Measured: **56% memory reduction** (§1.6). 3.0 also makes
**copy-on-write mandatory**, deleting the entire `SettingWithCopyWarning` class of silent
wrong-data bugs — aligned with this project's gated-write discipline. And it requires
`pyarrow`, which is needed anyway (18 import sites + the Overture parquet).

*What survives of rev 1's caution is sequencing, not compatibility:* build the new env at
**pandas 2.3.3** first so Phase 2 can prove byte-identical output against the Phase-0
baseline, **then** bump to 3.0.5 in Phase 2b where a diff is expected and diagnosed. Two
`uv lock` runs, not two projects. Do not change interpreter + pandas major + env manager +
imports in one step.

**D2 — canonical import form.** Settled: **(a) `from scripts.housing_rules import ...`.**
No file moves, no CLAUDE.md canonical-fact change, works immediately with an editable
install of the repo root, and `python -m scripts.housing_rules.test_smoke` already works
today. **Consequence:** `scripts/v4/`, `scripts/migration/` and `scripts/finance_curriculum/`
currently lack `__init__.py` and must gain one in Phase 3 for `packages.find` to map them.
*Rejected alternative:* move `scripts/housing_rules/` → repo-root `housing_rules/`. Semantically cleaner (it
  is a library, not a script), but it *changes a CLAUDE.md canonical fact* — which that file
  says should be rare and deliberate. Defensible; needs an explicit call.

**D3 — adopt PEP 723 for `scratch/` one-offs?** → *Recommend yes, as a hybrid.*
Genuinely standalone throwaways get an inline `# /// script` dependency header and run via
`uv run`, so they stay reproducible years later without env archaeology. The committed
library and generators use the one locked env. This is the piece of Simon Willison's actual
practice that fits this repo; blanket PEP 723 does not, because 92 files depend on shared
local modules.

**D4 — delete the vestigial stack?** TensorFlow/Keras (~30 pkgs), `duckdb`, `tabula-py`,
`sqlite-utils` have zero import sites. Dropping them from the new env is the default; flag
if any is wanted for future work.

**D5 — Python 3.14, 3.13 or stay 3.12?** → *Recommend **3.14.0**.*
Verified by execution, not inference (§1.6): full install, all 27 imports, real parquet +
SQLite + geopandas work. The machine already runs 3.14 elsewhere (`svgvenv`, Homebrew).
Gains: substantially better error messages and REPL — worth real weight given CLAUDE.md
describes v3 as "the curriculum's world" where students rebuild the pipeline. Free-threading
is **not** a reason here: the bottleneck is I/O and Playwright is already async.
Fall back to 3.13 only if a Phase-1 workload surfaces something the smoke test missed.

**D6 — `fitz` → `pymupdf` import rename?** 5 import sites. PyMuPDF now emits
`The 'fitz' API is deprecated ... Use 'import pymupdf' instead` on every run. Trivial,
mechanical, and best folded into Phase 3.

**D7 — `fuzzywuzzy` → `rapidfuzz`?** 2 import sites. `fuzzywuzzy` is deprecated upstream in
favour of `rapidfuzz` (already a dependency, 1 site). My §1.6 resolve/install test **used
rapidfuzz and omitted fuzzywuzzy** — so fuzzywuzzy on 3.14 is *unverified*. Either migrate
the 2 sites or add fuzzywuzzy to the Phase-1 gate. Flagging because I made the substitution
silently in testing.

---

## 6. Explicitly out of scope

- **`datasette-deploy/`** — has its own `requirements.txt` (`datasette==0.65.2`,
  `datasette-cluster-map`), `Dockerfile`, `runtime.txt` (python-3.12.0) for Fly.io. This is
  **correctly isolated already**. Do not fold it in.
- **conda `base`, `tilblog`, `video-transcript`** — other projects. Untouched.
- **Deleting miniconda** — not proposed. `jupyter_env` survives Phase 5 as a fallback until
  explicitly retired.

---

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| pandas 2→3 behavior change silently moves a published figure | **Low** (was High) | §1.5 measured **zero** breaking-pattern hits across 196 files; `.venv` already runs 3.0.5; D1's two-step keeps Phase 2 interpretable; Phase-0 golden outputs catch it regardless |
| 92-file import rewrite with only 2 smoke-test modules as coverage | **High** | Phase-0 baseline is the real net; Phase 3 is separately gated and re-runs Phase 2 |
| `gen_measure_u_site.py:690` hardcoded conda path breaks the site build | Medium | Known and fixed in Phase 4.1 |
| A geo/PDF wheel unavailable on py3.14 arm64 | **Resolved** | §1.6: full install + all 27 imports + real parquet/SQLite/geopandas verified on 3.14.0. Exception: `fuzzywuzzy` untested — see D7 |
| An outside-repo consumer of `jupyter_env` exists | Low | Search was **bounded** (depth 4, `~`), so absence is not proof; §Phase 5 keeps the env alive as mitigation |
| Playwright browsers need re-download | Low | Cache is env-independent (`~/Library/Caches/ms-playwright`); Phase-1 verifies |
| `.claude` permission entries stop matching | Cosmetic | Extra prompts until Phase 4.7 |

---

## 8. Effort

- Phases 0–2 (env consolidation, no code change): **~1 session.** Low risk, fully reversible.
- Phase 3 (import rewrite, 92 files): **~1 session, mechanical but wide.** The genuine risk.
- Phases 4–5: **~half a session** plus a soak period.

**Phases 0–2 are worth doing on their own merits even if Phase 3 is deferred indefinitely.**
They are separable, and Phase 0's baseline is useful independent of any migration.

---

## Appendix A — draft `pyproject.toml` (not yet written to disk)

Derived from the §1.1 measured import set, with D4 exclusions and D7's rapidfuzz
substitution applied. **`pandas` is the one pin that changes between Phase 1 and Phase 2b.**

```toml
[project]
name = "berkeley-data"
version = "0.1.0"
description = "Independent reconstruction of Berkeley's housing-production pipeline"
requires-python = ">=3.14"
dependencies = [
  # core
  "pandas==2.3.3",   # Phase 1/2 pin -> becomes pandas==3.0.5 at Phase 2b (D1)
  "numpy==2.5.3",
  "pyarrow",
  # viz
  "matplotlib", "seaborn", "plotly",
  # geo
  "geopandas", "shapely", "pyproj", "folium",
  # fetch / parse
  "requests", "beautifulsoup4", "lxml", "openpyxl", "pymupdf", "pillow",
  "playwright", "browser-cookie3", "sodapy", "python-dotenv",
  # match
  "rapidfuzz",                  # D7: replaces fuzzywuzzy
  # cloud
  "boto3",
  # notebook toolchain
  "nbformat", "nbconvert", "ipykernel", "jupyterlab", "ipywidgets",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["scripts*"]
```

**Deliberately absent** (D4, zero import sites): `tensorflow`, `keras`, `duckdb`,
`tabula-py`, `sqlite-utils`, `fuzzywuzzy`.
**Not a Python dependency:** Playwright's browser binaries — cache is shared and
env-independent (`~/Library/Caches/ms-playwright`); Phase 1 verifies rather than re-downloads.
**Out of scope:** `datasette-deploy/` keeps its own pinned `requirements.txt` (§6).
