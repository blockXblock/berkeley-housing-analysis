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

## STATUS: JN-A IS DONE (committed cbcdeee, pushed to origin/dev)
The first real ingestion SUCCEEDED. Do NOT re-run JN-A as if it's pending.
- notebooks/v4/JN-A_ingestion.ipynb ran clean on the real feed: 85,793 events from 32,202 rows, all
  four axes at anchor (submittal 32,202 / issuance 31,940 / finaled 21,650 / completed 1), CHECK 1-4
  PASS, conserved=1, independent verifier PASS. Committed cbcdeee with the verifier and the parked
  hard-coded version.
- databases/berkeley_housing_v4.db (114.8 MB) exists, is GITIGNORED, a build artifact — never git add it.
- v3 untouched throughout (sha aa10052c…).
- If you need to re-verify: run scripts/verify_jn_a_conservation.py (read-only) — it independently
  counts the real date columns and checks the known anchors.

## THE IMMEDIATE NEXT THING IS A CONVERSATION, NOT A COMMAND
John and chat-Claude are about to have the SALVAGE conversation: how the existing website (Explorer),
the curriculum (JN1-JN6b), and four months of APR work get re-pointed at the v4 event-stream spine.
The downstream notebooks (JN-B typing, JN-C reversible classifier, JN-D projection/fold) are PLANNED,
NOT BUILT. Do not build or run them until John directs it. Stand by; verify state if asked.

## (historical) THE FIRST RUN'S FINDING — already fixed, for context only
The very first JN-A run mis-mapped 3 of 4 date axes (matched *Status columns before *Date), so only
submittal ingested. Conservation passed anyway (it guards loss, not mis-discovery); the per-axis
anchor check caught it. Fixed via preference-scoring (Date > Status), a CHECK 4 hard anchor halt, and
an independent verifier. The committed notebook is the FIXED version. This is settled — do not re-open.

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
