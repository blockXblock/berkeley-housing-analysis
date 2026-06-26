# RESUME — Claude Code (CC), v4 rebuild (written 2026-06-26, before the first JN-A run)

**You are CC. You execute filesystem/DB/git operations. John owns all irreversible operations
(commits, pushes, guarded writes). chat-Claude plans and writes your prompts; it cannot see your
disk. If you have just been compacted: read this file, run `git status` and the verify commands
below, and report state to John BEFORE doing anything else. Do not act on a remembered plan.**

---

## WHAT WE ARE DOING
Rebuilding the Berkeley Housing Pipeline as **v4**: a sourced, append-only lifecycle EVENT STREAM as
the spine, with all entities (parcels/structures/units/projects/actors) as reversible PROJECTIONS
over it. The point is that data can be mislabeled or mis-projected (both reversible) but can NEVER
silently vanish. v3 stays live and untouched throughout; v4 is built fresh from raw CPRA sources.

## CURRENT STATE (verify before trusting — run the commands)
```
cd ~/berkeley-data
git status                      # expect: dev branch
git log --oneline -3            # f1a37a8 schema(v4) should be present
# schema (committed, design-only, EMPTY):
ls -l schema/v4/schema_v4.sql   # 27 tables, committed at f1a37a8
# the ingestion notebook (CLEAN — verify no escaping bug):
python3 -c "raw=open('notebooks/v4/JN-A_ingestion.ipynb').read(); b=chr(92); print('bugs:',raw.count(b*4+'s'),raw.count(b*4+'n'),'size:',len(raw))"
#   MUST print:  bugs: 0 0  size: ~39683
#   if it shows any bug or a wildly different size, STOP and tell John — wrong/stale file.
```
- If `notebooks/v4/JN-A_ingestion_v3clean.ipynb` exists, it is a duplicate to be deleted. Run only
  `JN-A_ingestion.ipynb`.
- A superseded hard-coded version lives at `notebooks/v4/_superseded/` — do not run it.
- There is NO `databases/berkeley_housing_v4.db` yet. JN-A creates it fresh.

## THE IMMEDIATE NEXT STEP: run JN-A (the first real ingestion)
JN-A ingests the CPRA BP feed into a fresh `databases/berkeley_housing_v4.db`. It:
- DISCOVERS each file's header row and columns (does not hard-code them) and reports what it found;
- explodes each permit row into one event per present date (submitted/issued/finaled/completed);
- proves conservation (every source row represented; events == sum of date fields; count > floor).

**Run rules:**
- Writes ONLY to a fresh `databases/berkeley_housing_v4.db` (notebook deletes any prior v4 build).
- **v3 is NEVER touched.** No commit, no push, no `git add` of the .db.
- Report: discovery output (both files), per-file + total row counts (~32,202), the four anchors
  (permit_submitted 32,202 / permit_issued 31,940 / permit_finaled 21,650 / permit_completed 1),
  conserved flag (must be 1, events > 30,764), unparseable fields, duplicate-key stats, out-of-window
  count. Then run `scripts/verify_jn_a_conservation.py` and paste its verdict.
- **STOP for John's review. Commit nothing.**

## ABSOLUTE RULES
- **A conservation FAILURE or a discovery HALT is a real FINDING — report it, do NOT modify the
  notebook, the discovery heuristic, or the conservation logic to force a pass.** This is the single
  most important rule. The whole architecture exists to surface loss, not hide it.
- Read-only by default. dev branch only. No push without John's explicit instruction.
- CKAN/HCD mirror is ORACLE-only, never a data source.
- Verify counts/zeros against the LIVE database, not against memory or a summary.
- One task type per action. STOP for John before any irreversible operation.
- Fenced code blocks in chat-Claude's prompts contain only the prompt; commentary stays outside.

## TODAY'S HARD LESSON (carry it)
Hours were lost because a broken notebook sat in the repo while fixes lived elsewhere, and errors
were read past instead of verified against the actual file on disk. Before running anything, confirm
the file you are about to run is the one you think it is (the byte-check above). When something looks
wrong, check WHICH file is actually throwing the error before acting.
