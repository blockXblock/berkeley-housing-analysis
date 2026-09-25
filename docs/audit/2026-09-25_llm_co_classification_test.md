---
title: LLM CO-classification test — harness built, blocked on model access, one finding already
date: 2026-09-25
type: audit
status: open
area: docs/audit
---

# Can a model read raw Accela records and say whether a project is built?

## RESULT: 8 / 8, every one at high confidence

Run 2026-09-25 with `llm -m claude-sonnet-5` (Simon Willison's `llm` CLI, plugin `llm-anthropic`).
Full output in `scratch/2026-09-25/llm_co_test/results.json`.

**Sonnet got every case right, including the one a keyword heuristic gets wrong.** It saw only raw
Accela rows — no unit counts, nothing from v2, no hint which cases were hard — and returned a
judgment plus *what was actually finaled*, which is the field that matters.

| project | truth | model | what it said was finaled |
|---|---|---|---|
| 1914 Fifth (257u) | not built | **not built** | "Demolition of old warehouse/retail building and site work (utilities, paving, **parking lot**, landscaping)" |
| 2420 Shattuck (132u) | not built | **not built** | "**Restaurant tenant improvements (Giovanni's/Edel)** and a re-roof/demo of interior finishes" |
| 2587 Telegraph (52u) | not built | **not built** | "Only the demolition permit was Finaled; the main construction permits remain **Issued**" |
| 2902 Adeline (54u) | not built | **not built** | "main building permit B2021-04232 still under construction … through 2026" |
| 1598 University (207u) | not built | **not built** | "Demolition of prior structures and temporary shoring/excavation work **only**" |
| **2538 Durant (83u)** | not built | **not built** | "**Demolition of old apartment building**, solar PV, minor utility/seismic; the main 83-unit permit remains Issued" |
| 3030 Telegraph (144u) | built | **built** | "Main building permit B2023-06416 for the 5-story, 144-unit mixed-use building" |
| Acheson (205u) | built | **built** | "Rehabilitation of Acheson Building A into 37 residential units … B2015-02995" |

**2538 Durant is the decisive one.** The one-line heuristic below answers *"is there a Finaled record
that mentions housing?"* and says **yes** — because the finaled permit is the **demolition of an old
apartment building**. Housing words, demolition permit. Sonnet read *which* permit was finaled,
saw it was a demolition, and noticed the 83-unit construction permit was still `Issued`. No keyword
rule makes that distinction. It required reading.

It also volunteered permit numbers it was never asked for (B2023-06416, B2015-02995, B2021-04232,
B2023-02332), which makes every judgment auditable against the source row.

⚠ **n = 8, adversarially chosen.** This shows the method survives the cases that beat our regexes.
It does not establish a rate over 32,897 permits, and it was not run blind against a random sample —
that is the next test, not this one.

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
