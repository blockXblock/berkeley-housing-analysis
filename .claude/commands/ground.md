---
description: STOP — verify against the repo/DB/git before proceeding (John's brake on racing ahead)
---

STOP. John has invoked /ground because you are (or appear to be) acting on memory, summaries, or
momentum instead of the repository's ground truth. This project's history shows exactly how that
fails: Logan South was investigated four times because knowledge lived in prose; the residual chase
re-typed a fourth copy of a matcher that already had committed implementations; a "new" harvest
re-derived counts sitting in our own NumberUnits field.

Before your next substantive action:

1. **Name the claim you were about to act on** — state it in one sentence.
2. **Check whether it's already been done or answered.** In order:
   - `git log --oneline` + `git grep` for the relevant symbols/permits/addresses
   - `docs/audit/` (dated analytical records), `corrections/v4/` (the calibration + adjudication
     ledgers — `grounded_counts.csv` is the anti-re-derivation memory), `PROGRESS.md`
   - the live DBs (read-only queries beat recollection)
   - existing machinery: `scripts/housing_rules/` (to_canonical_apn, normalize_address, classify),
     `scripts/v4/stage_methods.py`, the committed notebooks — IMPORT, don't re-type
3. **Report what you found** — "already done in X (date, commit)" or "verified absent, proceeding" —
   with the receipts, BEFORE resuming.

CLAUDE.md's standing rule applies: *verify artifacts, never trust a summary — count rows, check
dates, ls the actual path.* An empty grep is not absence; a prose note is not ground truth.
