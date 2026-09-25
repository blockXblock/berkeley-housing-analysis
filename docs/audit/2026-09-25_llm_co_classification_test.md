---
title: LLM CO-classification test — harness built, blocked on model access, one finding already
date: 2026-09-25
type: audit
status: open
area: docs/audit
---

# Can a model read raw Accela records and say whether a project is built?

John asked for this test using Simon Willison's `llm` CLI. The harness is built
(`scripts/llm_co_classify_test.py`) and **cannot run**: the OpenAI key on this machine has no
credits, there is no Anthropic key, no `llm-anthropic` plugin, and no ollama.

**I cannot stand in for the model.** I investigated every one of these cases today, so I know the
answers. A test whose grader knows the answer is not a test. That has to wait for a model that has
not seen the investigation.

## What the harness does

Eight projects, chosen **adversarially** — they are the cases that beat our regexes today, not a
random sample:

| project | truth | why it is hard |
|---|---|---|
| 1914 Fifth St (257u) | **not built** | finals are a DEMO and a PARKING LOT + beer garden |
| 2420 Shattuck (132u) | **not built** | final is a pizza restaurant fit-out |
| 2587 Telegraph (52u) | **not built** | under construction; leasing office, no BP finaled |
| 2902 Adeline (54u) | **not built** | under construction; inspected 2026-09-22 |
| 1598 University (207u) | **not built** | 678 inspections, no CO |
| 2538 Durant (83u) | **not built** | 443 inspections, no CO |
| 3030 Telegraph (144u) | **built** | genuinely completed 2026 |
| 2131 University (Acheson) | **built** | 4 buildings, all four permits finaled |

The model sees **only raw Accela rows** — record number, date, status, description, address. No unit
counts, nothing from v2, no hint which cases are hard. It returns strict JSON and is graded
automatically. Ground truth is v2's verdict-driven `co_issued_date`, **corrected by John's direct
knowledge of the sites**, which outranks the database where they disagree.

## The finding that does not need a model

Before asking whether a model can find the answer, ask whether the answer is **present**. It is —
and a one-line question separates 7 of the 8:

> **Is there a `Finaled` record whose description mentions housing?**

| project | truth | signal |
|---|---|---|
| 1914 Fifth | not built | no ✓ |
| 2420 Shattuck | not built | no ✓ |
| 2587 Telegraph | not built | no ✓ |
| 2902 Adeline | not built | no ✓ |
| 1598 University | not built | no ✓ |
| 3030 Telegraph | built | **YES** ✓ |
| Acheson | built | **YES** ✓ |
| 2538 Durant | not built | **YES** ✗ |

**7 of 8, from one line.** And 2538 Durant is the case where our own ground truth is weakest — v2
stages it `completed` with no CO date, 443 inspections running to 2026-05.

**This is the diagnosis, and it is not flattering.** Our production code asked *"is any permit
finaled?"* — which is how a demolition, a parking lot and a pizza restaurant were read as housing
completions. The right question was *"is a HOUSING permit finaled?"*. The evidence was in the
records the whole time. We were reading the wrong field of it.

## What this implies about the rearchitecture

It supports John's thesis, but for a subtler reason than "models are better at text". The precondition
for any method — LLM, heuristic or relational — is that the signal exists in the source. **It does.**
Our failure was not missing data and not the storage model; it was asking a question the data could
not answer and treating the result as though it could.

That reframes the LLM's job. It is not there to find signal we lack. It is there to **ask the right
question of each record** — which is exactly what defeated the regexes: quote marks in
`"ACHESON COMMONS" - BUILDING "C"`, a dated log prefix before the real scope, a contractor's note
about a temp power pole at the end of a 56-unit building's description.

## To run it

One of:
- add credits to the OpenAI account (`llm -m gpt-4o`), or
- `llm install llm-anthropic` and set an Anthropic key, or
- install ollama and run a local model

Then: `python3 scripts/llm_co_classify_test.py --model <model>`

It writes per-project prompt bundles and `results.json` with a pass/fail per case, so the comparison
is reproducible and the grading is not a matter of opinion.
