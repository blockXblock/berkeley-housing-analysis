# dev ↔ main Divergence Survey — 2026-06-15

**Purpose:** Read-only reconciliation survey performed after a cherry-pick to
`main` aborted on structural divergence (worktree cleaned, nothing published).
Both `dev` and `origin/main` had moved independently. This documents exactly
what each branch has that the other lacks, so a merge preserves **both** dev's
work (verdict layer / ingest / regen) **and** main's work (affordability
corrections, plan-set R2 links, explorer fixes, repro notebooks) — clobbering
neither.

**No merge/rebase/push was performed.** This is the survey + the reconciliation
recipe it produced.

---

## Branch geometry

| ref | commit |
|---|---|
| `dev` (HEAD) | `e840f55` |
| `origin/main` | `6ef5bb3` |
| **merge-base** | **`1bcddba`** |

Both diverged from `1bcddba`. `main` had earlier merged `dev` at `d0672e6`,
then both continued independently.

---

## The decisive fact: the canonical DB is NOT git-tracked

`databases/berkeley_housing_v2.db` is **working-tree only — one physical file,
shared by both branches.** Consequence:

- **All *data* work is branch-independent and co-present in the one DB:** dev's
  verdict layer + 38-permit ingest, the **75 `documents.r2_url`** plan-set
  links (main's "surfaced" work), and the affordability tier data.
- **Git divergence can only clobber two things: *scripts* and *generated
  outputs*.** No data is at risk from any git operation; worst case a regen
  restores a generated file.

A commit being **absent from dev's history** ≠ its **content being absent from
dev's tree** — most of main's commits reached dev's tree by other paths (the
`d0672e6` merge, identical edits, or DB-resident data).

---

## main's 15 commits dev lacks — classified

Legend: **(a)** already in dev's tree · **(b)** DB-resident/generated → regen ·
**(c)** main-only file change a merge must preserve.

| Commit | Subject | Files | Verdict |
|---|---|---|---|
| `6ef5bb3` | evidentiary CO dates + Bucket-2 | explorer_data.js + working.js (generated) | **(b)** regen — precedence in `v_projects_flat` + dev's export |
| `6de6dd3` | proj35/proj13 affordability | generated only | **(b)** regen (DB-resident) |
| `160190d` | full VLI/MOD tiers + proj36/8 | **export_v2.py** + generated | **(a)** script already in dev / **(b)** regen output |
| `c219831` | run-2 plan-set links (34 docs) | generated only | **(b)** regen (75 DB `r2_url`) |
| `6b6b6bd` | R2-linked plan sets first in panel | **docs/explorer.js (+5/-1)** | **(c)** → resolved (see c1) |
| `1331c0a` | 22 plan-set R2 links | generated only | **(b)** regen |
| `d0672e6` | Merge dev (proj15, provenance, audit) | 04_reporting/corrections/data/audit… | **(a)** all identical in dev |
| `cf6bad1`/`91911bb`/`808d1cc`/`92734d7` | Shattuck tour videos | docs/index.html | **(a)** identical in dev |
| `269d5fe`/`7f0936b` | Colab repro | README/notebooks/data/public | **(a)** identical in dev |
| `b730529` | UC beds / completions-RHNA / private-only | explorer.html + explorer.js | **(a)** html identical; js rework in dev |
| `a6edbf9` | bp/co milestones from v_projects_flat | export_v2.py + generated | **(a)** confirmed in dev (L192/L201) / **(b)** regen output |

**Net:** only `6b6b6bd` and `160190d`/`a6edbf9` (scripts) needed scrutiny; all
resolved to dev (below). Everything else is already in dev (a) or regenerates
from the shared DB (b).

---

## The three contested files — all resolve to dev

### `export_explorer_data_v2.py` — dev is a strict SUPERSET
dev already contains main's `160190d` full-tier affordability block
(`eli/vli/li/mod/market_units`, the `GROUP BY vic.code` query, all five output
fields) **and** `a6edbf9`'s bp/co-from-`v_projects_flat` sourcing (L192/L201),
**plus** dev's own additions main lacks:
- `validate_co_date` rejects only the `2024-01-01` migration stub (main still
  wrongly rejected all pre-2020 dates, dropping 145 genuine 2018–2019
  completions);
- the co_date→status derivation block (ADR-001: completion display derives from
  the validated CO date, not the materialized stage).

The only `main..dev` removals are inside `validate_co_date` — the intended fix,
not a loss. **dev wins; no graft.**

### c1 — `docs/explorer.js` — already grafted (uncommitted)
main's `6b6b6bd` "R2-linked-first, never-truncate" block
(`docsLinked/docsUnlinked/docsShown/docsHidden`) was **already present in dev's
working tree as an uncommitted change**, byte-identical to main
(`index d2f7080`), and **coexists with `b730529`'s 96-line panel rework** (which
is in the dev commit) — `6b6b6bd` supplies `docsShown`/`docsHidden`; `b730529`'s
render consumes them. **Action: commit the existing change; nothing to graft.**

### c2 — `scripts/generate_apr_v2.py` — dev is CORRECT, main is BUGGY
**(Corrects a reversed-diff misread earlier in the session.)** Definitive
count: **dev has the `2024-01-01` stub-guard 3× (L134/L139/L142); main has it
0×.** proj137 (82u) and proj138 (72u) carry *only* the `2024-01-01` stub (no
entitled/bp date). Without the guard they surface as phantom CY2024 "CO Issued"
in Table A2 — main's behavior. dev correctly excludes them. **dev wins; no
graft.**

---

## c3 — NEW shared bug (NOT a merge issue): line-368 RHNA stub leak

A **4th** `co_issued_date` site the Table-A2 guard doesn't cover — the RHNA
"Completed units" summary (`generate_apr_v2.py` L368), filter
`co_issued_date IS NOT NULL AND != ''` with **no stub-guard, identical on both
branches**. It counts proj137/138's stub units in the headline RHNA total:

| RHNA completed-units total | units |
|---|---|
| WITH stub (current, both branches) | **4024** |
| WITHOUT stub (guarded) | **3870** |

→ a **154-unit overcount** (82 + 72). VLI unaffected (both stubs are 0 VLI).
**Fix: a separate gated one-liner** adding the guard to L368 to match the three
Table-A2 guards — not part of the dev/main merge.

---

## Reconciliation recipe

1. `export_explorer_data_v2.py` → **dev wins** (superset). No action.
2. `docs/explorer.js` → **commit** the uncommitted c1 change (already in dev).
3. `generate_apr_v2.py` → **dev wins** (has the stub-guard; main lacks it).
4. **Generated files** (`explorer_data.js`, `*_working.js`, `data/apr/*`) →
   **regenerate** from dev's scripts against the shared DB; do **not**
   hand-merge.
5. `CLAUDE.md` / `PROGRESS.md` / audit docs / classifier / staging → dev's
   (session-current).
6. **c3** line-368 RHNA fix → separate gated commit, applied **before** the
   regen so the regenerated APR carries RHNA = 3870.

**Verify after regen:** 705/703 explorer count · full income tiers / proj36-8
rendering · 75 `r2_url` links displayed (via c1) · Table A2 excludes
proj137/138 · RHNA total = 3870 (down 154).

Only `6b6b6bd`'s explorer.js block was ever main-only-file work, and it was
already in dev's tree — so **no main-only work is dropped** by taking dev's
scripts and regenerating the outputs.
