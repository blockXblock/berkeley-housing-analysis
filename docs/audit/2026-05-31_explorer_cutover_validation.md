# Explorer v2 Cutover Validation — 2026-05-31

**Goal:** Determine whether berkeleybuild.com can be cut over to current v2 data.
Read-only; v2 output generated to `/tmp/explorer_v2_test.js`. Repo, external
drives, and the Toshiba copy untouched.

---

## Headline: **the explorer cutover already happened — on 2026-05-13**

This corrects my own earlier finding. The v2 migration checklist
(`2026-05-31_v2_migration_checklist.md`) inferred from *script paths* that the
explorer was "still on V1, needs cutover." Inspecting the **deployed artifact**
proves otherwise:

- Commit **`52b87c0` (2026-05-13): "deploy: switch production Explorer to v2 data"**
- `docs/explorer_data.js` is **identical on `dev` and `main`** (hash `0e693c9…`)
  → the live GitHub Pages site (main) **already serves v2 data**.
- Live file header: `Auto-generated from berkeley_housing_v2.db, 2026-05-13`.

**So the cutover question is moot — it's done.** The real question is whether to
**refresh** the 18-day-old export and fix data-quality artifacts. The migration
checklist's script-path inference was wrong; the deployed file is the truth.

## Stage 1 — v2 export runs clean

`export_explorer_data_v2.py` ran with **no missing-column warnings** (unlike the
APR generator). It does the `project_classifications` joins the APR generator
skipped, emitting the full front-end field set. 181 projects, 14,071 units.

## Stage 2/5 — Front-end compatibility: **PROVEN (identical schema)**

Live (May 13) vs fresh (May 31) v2 export, parsed structurally:

| | Live | Fresh |
|---|---|---|
| Projects | 181 | 181 (same ids) |
| Fields/project | **52** | **52** |
| Fields only in one | none | none |
| Projects only in one | none | none |

**The field schemas are identical** — every name the front-end reads is present
in both. No renames, nothing missing. Front-end compatibility isn't a risk: the
live site already renders this exact schema. **A refresh cannot break the page.**

### A refresh changes only 2 of 181 projects
| id | Field | Live (May 13) | Fresh (May 31) | Read |
|---|---|---|---|---|
| 34 | status / co_date / pipeline_stage | Completed / 2025-01-15 | **Entitled / None** | ⚠️ regressed from Completed→Entitled, **lost CO date** — verify this is a correction, not data loss |
| 179 | app_filed/complete, permits, num_permits | mostly null / 1 permit | 2019 dates / 5 permits | enrichment (gained 2019 permit history) |

## Stage 3 — Diffs classified
The live↔fresh diff is tiny: id34 (status/date change — **investigate**) and
id179 (date enrichment). No date-format, +2-row, or schema diffs (both already
contain all 181 incl. the +2). The big v1-vs-v2 differences don't apply here
because **the live site is already v2.**

## Stage 4 — Data-quality artifacts ALREADY on the public map

These exist in **both** the live and fresh exports (project sets identical), so
they are **pre-existing public-facing issues**, not refresh regressions:

1. **104 Jan-1 placeholder dates** — `app_filed`/`co_date`/`construction_start`
   ending in `-01-01` (year known, day unknown), displaying as real dates. E.g.
   1951 Shattuck `co_date=2024-01-01`, 3030 Telegraph `construction_start=2024-01-01`.
   Public site renders these as "January 1" — misleading.
2. **+2 projects render broken** — `id183 2328 Channing` and `id184 2330 Blake`:
   **`units=0` AND `latitude=None`** → **cannot be placed on the map**; show as
   0-unit, unmappable entries. Worst public-facing artifact.
3. **2138 Kittredge appears TWICE** — `id113` (73u) and `id118` literally labeled
   **"2138 KITTREDGE St (id:118)"** (66u). The disambiguation suffix is visible
   to the public; looks like a broken duplicate.
4. **6 negative `processing_days`** — `1701 San Pablo = -3798`, `2001 Ashby
   = -700`, `2902 Adeline = -593` (app_complete before app_filed). Absurd if shown.
5. **4 UC student-housing projects, ~2,156 beds-as-units** — 2400 Bowditch (750),
   2556 Haste (556), 2200 Bancroft (550), 1950 Oxford (300). **All flagged
   `is_uc_project=true`** (distinguishable in data — front-end *can* label them),
   but `units` carries beds. Per the group-quarters rule, confirm the front-end
   labels rather than silently blends these.
6. 35 projects with null/zero units (incl. the +2) → render as "0 units."

## Stage 6 — Verdict & recommendation

**Structural compatibility: YES — already proven and already live.** There is no
cutover to perform and no front-end blocker; the site has run v2 data since May 13.

**Refresh: SAFE.** Regenerating from current v2.db changes only 2 of 181 projects
and cannot alter the schema. **One thing to verify first:** id34's change
(Completed → Entitled, CO date removed) — confirm that's a real correction before
publishing a refresh that downgrades a "Completed" project.

**Recommendation: refresh is low-risk and ready, but fix the public-facing
data-quality artifacts first (they're already live and a refresh won't fix them):**

- **P1 (visibly broken):** the **+2 unmappable projects** (units=0, lat=None) and
  the **2138 Kittredge "(id:118)" duplicate** — these look broken to any visitor.
- **P2 (misleading):** the **104 Jan-1 placeholder dates** (display as real dates)
  and **6 negative processing_days**.
- **P3 (methodology):** confirm the front-end **labels the 4 UC/student-housing
  projects** (2,156 beds) distinctly rather than blending beds into unit totals.

None of these block a refresh; they're pre-existing live issues worth a cleanup
pass. The cutover itself is **complete and validated**.

*Validation only. Uncommitted. No explorer.html change, no repoint, no deletion.
v2 output in `/tmp/explorer_v2_test.js`; repo tracked files untouched.*
