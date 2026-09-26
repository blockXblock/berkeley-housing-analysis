---
title: Model stage classification — 1,098 of 1,099 projects, and two null results
date: 2026-09-26
type: audit
status: open
area: docs/audit
---

# Model stage classification — results

All 1,099 projects classified onto John's seven-rung ladder by `claude-sonnet-5` via the Anthropic
Batch API, reading **only raw Accela rows** — record number, date, status, description. No v2 field
appears in any prompt. Nothing was written to any database; these are files for review.

Script: `scripts/batch_stage_classify.py`. Results: `scratch/2026-09-26/batch_stage*/`.

## Coverage

**1,098 of 1,099.** The first run parsed 1,010; the 89 failures were valid JSON truncated
mid-string because `max_tokens=400` and extended thinking consumed the budget before the answer.
Re-running only those at 2,000 tokens recovered 88, for **27 cents** against $3.13 for the whole
set. One project still unparsed.

## The ladder

| rung | | projects |
|---|---|---|
| 1 | pre_application | 36 |
| 2 | application_submitted | 33 |
| **3** | **application_accepted** | **39** |
| 4 | entitled | 50 |
| 5 | permitted | 127 |
| 6 | under_construction | 29 |
| 7 | completed | 784 |

**Approval track:** 814 ministerial · 226 discretionary · 58 unclear. The ministerial majority is
the single-unit ADU tail, ministerial by state law.

**Rung 3 — the step John asked for: 39 projects, 4,632 units**, split 21 ministerial to 17
discretionary. That is the population whose filed→accepted interval would measure what SB 9 /
SB 35 / SB 330 / SB 684 / AB 2011 are doing to city performance. ⚠ The *interval* still cannot be
computed: the Accela list view carries a filing date and a current status, not transition dates.
Those are on the CapDetail pages — 14,936 capIDs held, ~95 visited.

**Agreement with v2 on completed-versus-not: 1,044/1,098 = 95.1%**, confusion matrix strongly
diagonal. Where it disagrees, 20 projects v2 calls `completed` are placed at pre-application — the
same population as the 71 marked completed with no CO date.

## Two null results, recorded as nulls

Both arms paired on the same 170 projects, verified by comparing meta keys rather than trusting the
seed.

| arm | agreement with v2 |
|---|---|
| no definitions (baseline) | **152/170 = 89.4%** |
| DEFINITIONS on | **152/170 = 89.4%** |
| old TIPS on | 150/168 = 89.3% |

**Definitions changed nothing.** The arms differ on 16 projects and on completed-versus-not every
one falls the same side — neither wins a single case. Direction neutral (+0.19) against the tips'
suppressive −0.24.

**This does not contradict the permit-grain result**, where the parallel session measured
rules-off 199/206 beating rules-on 196/206. The reason is structural: only two of the four
definitions bear on this question. "What counts as a dwelling" determines a unit count, which is
their question. Mine is what stage a project has reached, which does not depend on it. **A null
here is what should have been predicted** — and is worth recording as a null rather than quietly
dropped.

## What the whole exercise established

- **The model reads these records competently cold.** Every attempt to help it — first tips, then
  definitions — was neutral or slightly harmful at this grain.
- **Our hard-won lessons did not transfer.** They were real, but they were lessons about *our*
  failures with regex. Handed to a competent reader as instructions they transmitted our biases:
  the tips pushed rungs systematically down.
- **The measured claim is narrow.** 95.1% agreement with v2 is agreement, not accuracy — v2 is
  wrong often enough that this cannot be read as a score. The honest ground truth is the parallel
  session's 206 human rulings, at permit grain.

⚠ **An earlier claim of 8/8 on an adversarial set is withdrawn** — that prompt named the answer
categories. See `2026-09-25_llm_co_classification_test.md`.
