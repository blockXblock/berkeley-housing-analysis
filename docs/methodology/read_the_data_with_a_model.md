---
title: Read the data with a model — what we should have done first
date: 2026-09-25
type: methodology
status: open
area: docs/methodology
---

# Read the data with a model

John, 2026-09-25: *"what fools we have been… his first rule for the data journalist in his San Diego
presentation was to have the model read the data. we, very narrowly stupidly, have been trying to
work on our problem using shell prompts and regex. WE GET VERY BAD MARKS FOR IGNORING WHAT WE KNOW."*

He is right, and the failure is mine more than his. I wrote the regexes. `llm` was already installed
on this machine. I know what models are good at. I reached for `grep` anyway, repeatedly, for a task
that is pure reading comprehension.

## The single project that makes the case

**proj381, 2980 College Ave.** v2 records permit `B2021-04563` as `completion_verdict='does_not'`
with `completion_basis='description_only'` — a keyword call on the permit text. The permit finaled
2023-11-15.

Given the same raw record and nothing else, the model said: *"Conversion of two 2nd-floor office
units into 4 residential units (B2021-04563) was Finaled."* **Built.**

The model is right. v2 is wrong. And **the basis field names the cause: `description_only`.** A
keyword classifier read the description and got it backwards. The blind test found a real defect in
our published data, in a project nobody had flagged, and the defect was caused by the exact method
we were defending.

## The blind test, honestly adjudicated

75 projects, stratified to oversample large ones (25 of 87 at 50+ units; a proportional draw would
have been 58 ADUs). Seeded RNG, no v2 field in any prompt, truth not read until every answer was in.
`claude-sonnet-5` via `llm`.

**Raw agreement with v2: 66/75 = 88%.** That number is not the finding. Adjudicating all nine
disagreements is:

| what it actually was | n | |
|---|---|---|
| **my prompt was ambiguous** | **5** | existing building being altered — "is the housing built?" has two defensible answers |
| **my harness was broken** | 1 | proj932's address is `"SAN PABLO Ave"` with no house number, so it got **zero records**; the model said `confidence: low, "no records available to determine"` — it declined rather than guessed |
| **v2 was wrong** | 1 | proj381 above |
| contested, both defensible | 1 | proj164: model right that the core permit was never Finaled; v2's CO is an inspection-based re-anchor |
| **model outright wrong** | **1** | proj63: its verdict said built, its own stated reason argued the permits remain Issued |

**Of 75 blind cases the model was clearly wrong once.** Four of the nine "failures" were mine.

⚠ **The 5 ambiguous ones are a real finding, not an excuse.** On an existing building with alteration
permits, *"has the housing development been built?"* genuinely has two answers: the building exists
(model), and the proposed project is not finished (v2). That is a defect in my question, and it is
fixable — ask about the *specific proposal*, not the site.

## What the model does that a pattern cannot

From the adversarial 8 (8/8) and this sample:

- **2538 Durant** — the finaled permit is the *demolition of an old apartment building*. Housing
  words, demolition permit. The one-line keyword heuristic says "built"; the model read *which*
  permit finaled and said no.
- **1914 Fifth** — named the finals as *"demolition… and site work (utilities, paving, parking lot,
  landscaping)"*. Our code called it a housing completion.
- **2420 Shattuck** — named the restaurants: *"Restaurant tenant improvements (Giovanni's/Edel)"*.
- It volunteers **permit numbers nobody asked for** — B2023-06416, B2015-02995, B2021-04232 — so
  every judgment is auditable back to a source row and can go through the same gate as any write.

## The rule

**For classifying Accela prose: use a model. Keep grep for locating files and matching exact
structured tokens.**

The structural reason, which is why this was never a close call: in this feed a **description is
narrative appended over time** — dated log lines, contractor notes, cross-references to other
permits — while `Work Type`, `OccType` and `UnitsAdded` are **structured fields**. Every regex defect
today came from reading the prose as if it were a field. A model reads prose as prose.

## What this does NOT license

The model is a better *instrument*, not a replacement for the discipline:

- 88% raw agreement means one in eight needs a human, and the adjudication took real work.
- It was wrong once, and wrong in a specific way worth watching: its **verdict contradicted its own
  reason**. Always capture the reason and check it against the verdict.
- It declines honestly when starved (`confidence: low`), which is worth more than the score — but
  only if the harness actually feeds it. My address key silently passed zero records.
- Everything it produces still goes through snapshot → preview → gate → verify-or-rollback. Six
  defects were caught today *because* proposed writes were diffed against a verifiable prior state.
  A model pipeline without that layer ships them all, confidently, in one pass.
