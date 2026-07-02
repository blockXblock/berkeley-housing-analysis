# ADU-conversion recall batch — 161 permits / +173 units (gated write, John-approved as amended)

**Date:** 2026-07-03 · **Who:** 3-agent description adjudication + CC verify pass; John sample-audited
30 rows (two 15-row batches) and approved with one amendment · **Snapshot:**
`keep_snapshot_2026-07-03_pre-adu-recall.db` (integrity ok).

## What this corrects
The classifier's **RULE 9** deliberately parks "alteration with conversion/legalization language" as
`ambiguous` ("may add a dwelling, inspect") — a designed inspect-queue that was never worked. The
2026-07-03 residual decomposition measured it: the city's Table A2 credited ~159 one-unit addresses
(plus small multis) where our counted set had nothing, and **158/159 existed in our data as finaled
alteration/ambiguous permits**. This write is that inspection, done and applied.

## Method (oracle discipline held throughout)
City rows **ENUMERATED the addresses only**. Every accepted count is grounded in the **permit's own
WorkDescription** (quoted per-row in `corrections/v4/grounded_counts.csv`); the adjudication verdicts
with reasons are preserved at `data/audit/adu_recall_verdicts_2026-07-03.csv`. Three parallel
adjudicators (direction-aware rules: dwelling→office REJECTS, solar-ON-ADU REJECTS, JADU counts,
legalize-non-dwelling REJECTS) → CC verify pass (caught 2: the 1526-6th net-zero office swap; the
0-Latham 1-vs-2 value conflict — both demoted to UNCERTAIN) → John's 30-row audit → **amendment:
2815 Channing net +2** (11-bedroom building "into 3 separate units"; prior unit count unknowable
from text — conservative net per count-once discipline).

## Applied
- **ACCEPT 161 permits / +173 units** (8 multi-unit rows incl. 2002 Addison office→6 units).
  36 rows were `ambiguous` WITH the correct count already stored in UnitsAdded — role promotions at
  equal value (`apply_grounded_counts` relaxed to permit exactly that; any value MISMATCH still halts).
- **UNCERTAIN 12** (John's later eyes; incl. the two CC demotions, a JADU eliminated by its own
  revision, a phase-podium, a reclassification-without-work).
- **no_valid_candidate 20** — city credits with no explaining permit; open city-side questions.
- **Write trace:** ledger append (checksums pinned 165 rows/467 units) → apply_grounded_counts
  (165 rows, 161 promoted, 4 idempotent) → **CO 3,970 → 4,143**; BP 3,945 and events 82,923 unchanged
  → baseline **2026-07-03** APPENDED (gap **+121**, sha a7204d688000e1f7) → JN-E regen (gate PASS)
  → from-raw chain re-validated.

## ⚠ THE SIGN FLIP (read before quoting the number)
**Our CO (4,143) now EXCEEDS the city's (4,022) by +121.** This is coherent, not an error: the two
records disagree in BOTH directions. We now count ~254 units the city's filing lacks (the unfiled
0-San-Pablo GLA 41, CY2025 filing-lag rows ~60, and the ours-more adjudications pending), while the
city holds ~130 we don't (San Pablo 23 held + Acheson-A rehab 37 + the 20 no-candidate rows + small
multis). Open adjudications that could move us DOWN: **1808 University −44** (window-timing — the
city's own 1812-University row describes the 44 as pre-existing) and **2510 Channing −40**
(uninvestigated). The honest public framing: *independent records, line-by-line explained
disagreement* — never "we found more housing than the city."

## Reverse
Restore the snapshot, or delete the 161 ledger rows + demote the promotions (each is a single
finaled-event classification with 'grounded_counts' in its basis_note).
