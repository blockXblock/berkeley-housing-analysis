# Next Session Priming — written 2026-05-29

Read this first. It orients the next session to where things stand and
what to do, without re-deriving context. Full narrative in
`docs/audit/2026-05-29_session_summary.md`; technical detail in
`docs/audit/2026-05-29_parcel_collapse_diagnostic.md` and
`docs/audit/2026-05-29_causes_2_3_diagnostic.md`.

## First action: verify, don't trust

Per "CC summaries can be wrong; verify artifacts" — confirm the git state
before acting on anything below:

```
git log --oneline -3
git status
```

Expected at session start (if nothing changed in between):
- **HEAD on `dev` at `17719b4`** (`feat(d7): regenerate reconciliation
  ledgers post Cause 2/3 fix`).
- **`origin/dev` at `17719b4`** (today's three pushes are synchronized).
- **`main` at `e62543a`** — **19 commits behind `dev`** (deferred FF
  decision: 13 from yesterday's session close + 6 from today).
- Working tree should hold only standing collateral: D6 notebook M, D7
  notebook M, `data/apr/2024/*` M, and three untracked items
  (`2026-05-28.md`, `data/apr/2024/developer_summary_2024.csv`,
  `notes/cc_prompts/`).

If HEAD differs, reconcile before proceeding — do not assume this doc is
current.

## Tomorrow's three tracks, in priority order

### Track 1 — Repository cleanup (the size workstream)

Forensic findings give precise targets. Phase B should:

- **Remove `docs/berkeley-flyover.mp4.backup-2026-05-03` from tree**
  (73 MB, accidentally tracked because `.backup-` suffix escapes
  `*.mp4` gitignore) + add an explicit `.gitignore` rule for `*.backup-*`
  or similar.
- **`git gc --aggressive`** — one-time consolidation. Current state:
  3,020 loose objects, 0 packs. Estimated on-disk savings: ~10–15%
  (modest, since the bulk content is already-compressed video/PDF).
- **Identify canonical alameda lookup CSV** (probably
  `alameda_lookup_complete.csv`, 59 MB). Move the other two
  (`address_lookup_normalized.csv` 51 MB, `lookup_corrected.csv` 35 MB)
  out of tree and out of history. Estimated savings: ~145 MB tracked +
  ~145 MB history.
- **Externalize `docs/videos/*.mp4`** (100 MB tracked) and
  **`site-by-site/*.pdf`** (120 MB tracked) to the existing R2/IA mirror
  infrastructure (pattern from the `pdf/` directory).
- **`git filter-repo`** to remove dead `berkeley-flyover.mp4` historical
  versions (258 MB across 5 dead blobs) and other large dead blobs
  surfaced by the top-30 analysis.
- **Verify clone size before/after**. Target trajectory:
  553 MB → ~150 MB → eventually ~50 MB after full externalization.

Reference: `docs/audit/2026-05-29_session_summary.md` "Forensic findings
from the repo-size investigation" section.

**History rewrite is safe given today's traffic data**: 492 clones from
176 unique cloners but only 1 unique web visitor in the last 14 days =
predominantly bot traffic; human cost of invalidating clones is
negligible.

### Track 2 — Path portability + dependencies (W1 + W2)

Three notebooks (D5/D6/D7 setup cells) plus ~5 active scripts plus
README line 15 plus `00_config/config.yaml` line 31. **Adopt the
`build_hcd_mirror.py` pattern**:
`REPO_ROOT = Path(__file__).resolve().parent.parent` (scripts), or
equivalent walk-up for notebooks (`Path.cwd()` ascend until a marker
file is found). Verify D5 produces byte-identical output post-fix.

**Add `openpyxl` to `requirements.txt`** — currently missing; D5's
`pd.read_excel(*.xlsx)` would fail on a fresh install with ImportError.
Pin Python ≥3.10 (notebooks were last run on 3.12.8; nothing in code
requires that exact version). Optionally prune legacy entries
(matplotlib/folium/plotly/sqlite-utils/tabulate) not used by the D-series
— harmless either way.

Reference: this morning's Phase A inventory report
(see session summary's "Forensic findings" section for the catalog).

### Track 3 — CPRA SQLite conversion + new getting-started page

**Schema design locked**: single `permits` table, snake_case column
names, `PermitNumber` as primary key, indexes on `parcel_number` /
`issuance_date` / `finaled_date` / `work_type` / `adu`, ISO 8601
dates, `source_file` provenance column, drop the 3 `Unnamed` spacer
columns (3, 12, 16) from CPRA xlsx.

- **CSV committed as canonical** (`data/raw/cpra-csv/cpra_permits.csv`)
  — single source of truth, version-controllable, diffable.
- **SQLite gitignored and rebuilt locally** (`databases/cpra_permits.db`).
- **Build script** `scripts/build_cpra_db.py` reads CSV → SQLite (mirrors
  `build_hcd_mirror.py`'s structure: REPO_ROOT derivation, `--rebuild`
  flag, idempotent transactions, atomic table swap).
- **Conversion script** `scripts/convert_cpra_xlsx_to_csv.py` reads Excel
  → CSV (one-time + future updates when CPRA delivers new files).

**Then the new public page**: `docs/citizen_apr.html` with —
- Project introduction
- Methodology summary
- The actual numbers (CY 2024: D5 643/576 vs HCD 708/731; CY 2025: 525/329
  vs 481/444)
- The 4 confirmed under-reports
- Gap accounting
- Clone-and-run instructions for journalists
- Links to D5/D6/D7 in the repo
- Hypothetical Accela API examples (or link to the Track 4 doc)

### Track 4 (lower priority) — Hypothetical Accela API document

`docs/audit/hypothetical_accela_api.md`. SQLite dialect, scope Table A2,
inline data-gap flags, include speculation marked as such. Drafted
against post-Cause-2/3 final state. ~90 minutes if Tracks 1-3 leave time;
otherwise the next session.

## Known-good ground truth (re-usable anchors)

- **Berkeley CY 2024 HCD Table A2**: 708 net CO, 731 net BP, 228 rows.
  Triangulated and agreed across Berkeley's PDF (NotebookLM), local HCD
  mirror, and HCD's CKAN API.
- **D5 post-all-fixes CY 2024**: 643 CO, 576 BP. Gaps: 65 CO (9%) /
  155 BP (21%) from HCD.
- **D5 post-all-fixes CY 2025**: 525 CO, 329 BP. Note: **D5 slightly
  exceeds HCD's CY 2025 CO of 481** by 44 units — worth examining as a
  potential D5 over-count or year-routing artifact when CY 2025 bijection
  is constructed.
- **8-year aggregate**: D5 = 2,604 CO / 3,296 BP; HCD = 4,011 / 4,509.
  Pre-CY 2024 years are not yet end-to-end validated; remaining gap
  reflects bijection coverage, not necessarily a recoverable systematic
  fix.
- **4 confirmed under-reports**: 2328 Channing (12u), 2512 Regent (9u),
  2028 Essex (1u), 707 Cragmont (1u).
- **The published April 2026 Citizen APR** (169 projects, 11,235 units,
  12.4% RHNA progress, $14.1M fees) stands as published.
- **`docs/methodology.html`** unchanged since 2026-04-23; the new
  `citizen_apr.html` supplements it rather than replacing.
- **CPRA xlsx schema**: 26 columns, header row 7 (0-indexed), sheet
  name `BP_Annual Permit Report`. Both files share the same schema; 23
  meaningful columns + 3 `Unnamed` spacers. D5 reads via
  `pd.read_excel(..., header=7)` (D5 Cell 4).
- **`build_hcd_mirror.py` is the portability template**: uses
  `REPO_ROOT = Path(__file__).resolve().parent.parent`, idempotent
  per-table atomic swap, `--rebuild` / `--db-path` CLI flags, no
  hardcoded user path.

## Do-not-touch

- **`main`** (e62543a, 19 behind dev — deliberate; FF decision deferred).
- **`docs/methodology.html`** — qualitative page, supplemented by the new
  `citizen_apr.html`, not replaced.
- **Standing collateral in working tree**: D6 notebook M, D7 notebook M,
  `data/apr/2024/*` M, untracked `2026-05-28.md`,
  `data/apr/2024/developer_summary_2024.csv`, `notes/cc_prompts/`. Leave
  alone unless explicitly in scope.
- **The published CY 2025 Citizen APR** (April 2026) stands as-is.
- **Explorer and Map** remain on v1-derived data (cutover is its own
  workstream).

## Today's discipline rules (carry forward)

1. CC summaries can be wrong; verify artifacts before acting.
2. Diagnostic docs precede the fix commits that reference them.
3. Regression test baselines update in the same commit as the code they
   test.
4. Predictions are imprecise; actual pipeline measurements are
   authoritative.
5. Same-year gating essential for sibling rules (Durant temp-power
   inheritance pattern).
6. `git checkout <ref> -- <path>` stages the file in the index, not just
   the working tree.
7. Always `git diff --cached --name-only` before every commit.
8. Visible correction (forward-revert) over silent rewrite for
   committed-but-unpushed mistakes.
9. Phase A read-only investigation precedes Phase B implementation.
10. Working tree standing collateral — leave alone unless explicitly in
    scope.
