# Next Session Priming — written 2026-05-28

Read this first. It orients the next session to where things stand and
what to do, without re-deriving context. Full narrative in
`docs/audit/2026-05-28_session_summary.md`; technical detail in
`docs/audit/2026-05-28_adu_diagnostic.md`.

## First action: verify, don't trust

Per "CC summaries can be wrong; verify artifacts" — confirm the git
state before acting on anything below:

```
git log --oneline -5
git status
```

Expected at the start of next session (if nothing changed in between):
- HEAD on `dev` at `22c5864` (fix(d5): REV summation), with `df17e7a`
  (docs(audit): diagnostic) below it, both **on dev, not pushed**.
- `85f95f3` is the pre-fix base.
- Uncommitted in the working tree (see "Pending commit/cleanup" below).

If HEAD differs, reconcile before proceeding — do not assume this doc
is current.

## State at session close (2026-05-28)

**Committed on dev (not pushed):**
- `df17e7a` docs(audit): ADU/REV diagnostic
- `22c5864` fix(d5): master-only co_units aggregation (the REV fix)

**Created on disk, NOT yet committed** (intended as one documentation
bundle commit — "step 7"):
- `data/audit/cy2024_reconciliation/` — matched_pairs.csv (182),
  h_unmatched_t2.csv (8), c_unmatched_t2.csv (974), README.md
- `docs/audit/2026-05-28_session_summary.md`
- `docs/audit/2026-05-28_next_session_priming.md` (this file)

**Collateral to clean up (do NOT commit as-is; decide per item):**
- `data/apr/2024/*.csv`, `apr_2024.json` — overwritten by the v1
  `generate_apr.py` verification run. Likely `git restore` (revert to
  committed state) unless the v1 refresh is wanted.
- `04_reporting/D6_diff_d5_vs_hcd.ipynb` — modified by a prior Phase B
  rerun. Decide whether the rerun output should be committed or reverted.
- Untracked: `2026-05-28.md`, `data/apr/2024/developer_summary_2024.csv`,
  `notes/cc_prompts/` — triage (commit, ignore, or delete).

## Pending commit/cleanup — suggested next steps

1. Decide the documentation-bundle commit scope (the reconciliation
   ledger + the two docs/audit session docs). All four are git-trackable
   (verified not gitignored).
2. Handle the collateral: `git restore data/apr/2024/` to undo the v1
   verification writes; decide on the D6 notebook rerun.
3. Push decision for `dev` (currently 2 fix/doc commits ahead of
   origin/dev) — and whether/when to fast-forward `main` (the deploy
   branch). No push has happened; awaiting explicit go.

## Prioritized work (from the session's outstanding list)

Highest leverage / most defensible first:

1. **Parcel-collapse fix in D5.** Quantified at 28 BP units for CY 2024;
   expected larger for CY 2025. Structural: D5's one-master-per-parcel
   grouping drops sibling New-construction permits. This is the biggest
   remaining systematic undercount. Diagnose blast radius across all
   CY years before designing the fix (Phase A first).

2. **Causes 2 and 3** (deferred in the REV diagnostic): Alteration/
   Demolition masters with cumulative UnitsRemoved (Cause 2); over-broad
   `is_adu = (master.ADU == "Yes")` classification (Cause 3). Candidate
   fix for both: a Work Type filter (count only "New" toward unit
   production). Scope decision needed — affects d5_only composition, not
   bijection cardinality.

3. **Year-routing convention decision.** D5 routes by BP issuance year;
   HCD appears to use entitlement year (6 CO / 4 BP CY2024 units shift).
   Decide and document the convention before it compounds across years.

4. **CY 2025 bijection construction.** CPRA coverage verified complete
   (all 12 months). Mechanically reproducible via the same tiered method
   in `data/audit/cy2024_reconciliation/README.md`. Expect the
   parcel-collapse and REV effects to be larger here.

5. **ABAG ADU income-tier distribution (Q5).** D5 lumps all units into
   ABOVE_MOD; HCD distributes ADUs 30/30/30/10. Separate workstream;
   needed for column-by-column tier reconciliation, not for unit totals.

6. **Methodology page update** describing the audit layer. Methodology
   language was discussed conversationally this session but no draft
   was written to a file. Tomorrow's task is drafting from scratch,
   using the bijection ledger and diagnostic doc as source material.
   No edits to `docs/methodology.html` have been made; the live page
   is the April-23 qualitative version.

7. **v2 cutover** (Datasette serving v2 directly) — separate multi-week
   workstream; not a quick task.

Note on ordering: parcel-collapse fix (1) is listed before CY 2025
bijection (4) on the principle of fix-before-extend. An alternative
sequencing — run the CY 2025 bijection first to quantify the
parcel-collapse blast radius for CY 2025 as input to the fix design
— is also defensible. Decide based on appetite at session start.

## Known-good ground truth (re-usable anchors)

- Berkeley CY 2024 HCD Table A2: **708 net CO units, 731 net BP units**,
  228 rows. Triangulated and agreed across Berkeley's PDF (via
  NotebookLM), the local HCD mirror, and HCD's CKAN API.
- The 7 affordability columns per stage (VLOW/LOW/MOD × DR/NDR +
  ABOVE_MOD) sum exactly to 708 (CO) and 731 (BP). Note the schema typo
  `*_EXTREMELY_INCOME_NDR` (missing "LOW") carried from
  `build_hcd_mirror.py` — not part of the seven.
- D5 post-fix CY 2024: 497 net CO, 231 net BP.
- 4 confirmed under-reports (in `c_unmatched_t2.csv`): 2328 Channing
  (12u), 2512 Regent (9u), 2028 Essex (1u), 707 Cragmont (1u).

## Do-not-touch (stable, published)

- The published CY 2025 Citizen APR (April 2026) stands as-is.
- `docs/methodology.html` — unchanged since 2026-04-23; no quantitative
  claims to retract.
- Explorer and Map remain on v1-derived data (cutover is its own
  workstream).
- No commits to `main`; no website deploy this session.
