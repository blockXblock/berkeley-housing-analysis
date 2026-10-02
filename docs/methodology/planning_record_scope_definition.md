# What makes a Berkeley Planning record a housing-development record

**Status: ADOPTED by John, 2026-09-28.** The machine-readable text is
`housing_rules.reading_rules.PLANNING_SCOPE`; every reading stamps it alongside HCD's
`DEFINITIONS`, so any figure traces to the exact wording that produced it.

This is the definition a model reads against when deciding which of Berkeley's Accela **Planning**
records belong to the housing pipeline. It exists because the regex that did that job kept failing,
and the failures were all of one kind.

## Why we are replacing a pattern with a definition

A regular expression over a record's prose can only match the words we thought of. Three measured
misses, each a real project:

| record | what it said | why the pattern missed it |
|---|---|---|
| `ZP2022-0046` | 3000 Shattuck, 10 stories, **166 dwellings** | `\bdwelling\b` cannot match the plural |
| (several) | **townhouses**; "a **two-unit** building" | the noun and the spelled-out count were absent |
| `PLN2026-0185` | "the Ashby BART **TOD development** proposal" | no word in it was a housing word |

`PLN2026-0185`, filed 2026-09-18, is the **first city filing for Berkeley's largest pipeline project**
— 618 units on the BART station block — and the filter did not see it. Each fix was a new word added
after a project was found by hand. The vocabulary of English is not closable, so every such pattern is
a **floor that looks like a census**, and it fails by silent omission: nothing errors, a project is
simply absent.

The project has already made this move once and it worked. The regex permit-role classifier was
retired on 2026-09-28 in favour of **model-read evidence stored with provenance**
(`housing_rules.permit_effect`, reading `data/derived/permit_effect_evidence_2026-09-26_hcd.json`).
Two facts from that file are the argument for doing it again: Jev read all **32,897** permits, and on
the **5,773** that needed reasoning Jev and Sonnet **disagreed 2,625 times**. A regex would have
silently returned one answer for all 2,625 and told us nothing.

**What is NOT changing.** Regex is right for *form* — machine-generated syntax with a closed
vocabulary — and it has not failed there: the `DEV` record-number prefix, the APN structure check, the
`-REV`/`-DEF` permit suffix. Those stay. Regex is wrong for *meaning*, in prose people wrote. Model
for meaning, regex for form.

## The definition

**A housing development project** is the term California's own reporting regime uses, so adopting its
definition makes an independently built count comparable to the city's, row for row — the same reason
John adopted HCD's unit definitions for permits on 2026-09-26.

> **Gov. Code § 65589.5(h)(2)** (Housing Accountability Act), as amended effective 2026-01-01
> (SB 838, Stats. 2025 Ch. 789) — verified against leginfo 2026-09-28:
>
> "Housing development project" means a use consisting of any of the following:
> **(A)** Residential units only.
> **(B)** Mixed-use developments consisting of residential and nonresidential uses, where at least
> **two-thirds** of the new or converted square footage is designated for residential use and there is
> no hotel or motel component; or at least 50 percent residential with 500 or more net new units; or
> at least 50 percent residential with 500 or more units plus demolition or conversion of 100,000+
> square feet of nonresidential space.
> **(C)** Transitional housing or supportive housing.
> **(D)** Farmworker housing, as defined in Health and Safety Code § 50199.7(h).

This is also the definition SB 330 preliminary applications operate on (§ 65941.1), which is why
Berkeley's own SB 330 and SB 35 filings can be tested against it directly.

**What counts as a unit** is not restated here. It is already adopted, from HCD's APR FAQ, in
`scripts/housing_rules/reading_rules.py` (`DEFINITIONS`): separate living quarters; ADUs and JADUs are
units; dormitories and student-restricted housing are group quarters, not units; senior housing that
consists of separate living quarters is units. The reading run stamps both texts, so any figure can be
traced to the exact wording that produced it.

## What the model returns

Four classes, not a boolean. A boolean would hide the middle, and the middle is where the errors live.

- **`housing_development`** — the record is an application, or a step in one, for a project meeting
  § 65589.5(h)(2).
- **`housing_adjacent_not_development`** — housing is present but the record is not a development
  application: a Zoning Research Letter *asking whether* residential use is permitted (an inquiry, not
  an application); a landmarks review of windows on an existing apartment building.
- **`not_housing`** — commercial, institutional, signage, telecommunications, a bronze sculpture at a
  BART station.
- **`unknown`** — the record's own text does not say enough to decide. **Required, and never a polite
  way of guessing.** CLAUDE.md rule 1: where the primary source is silent, the answer is unknown with
  provenance.

Per record it also returns `units_stated` (the number the record's own text states, or null — never
inferred from an address or a neighbouring project), a one-sentence `reason` **quoting the words it
relied on**, and its confidence. The store mirrors `permit_effect`: model version, the definitions
stamp, the prompt hash, and the reason, so every inclusion is auditable in plain English and a
re-reading is a new evidence file with a new hash rather than an edit.

## What it may read, and may not

Only what the city published on that record: **Description, Project Name, Record Type, work location**.

Not the HCD/CKAN mirror — that is the verification target, and using it as an input is the circularity
bug. Not the other projects at the same address, which is how a conflation becomes a fact.

## Berkeley's own vocabulary

Local terms a reader outside the building cannot be expected to know. This section defines words; it
must not grow into advice about how to read the data — a 2026-09-26 control showed reading tips added
nothing and pushed the model toward crediting less.

- **TOD** — transit-oriented development. In Berkeley's records it appears for housing on transit
  agency land (Ashby BART, North Berkeley BART).
- **"50 percent schematic plans"** — a **design-completion milestone**, i.e. drawings half finished.
  It is **not** an affordability share. `PLN2026-0185` says exactly this, and reading an affordability
  figure out of it would manufacture the confirmation that Ashby BART's "50% affordable" claim has
  never actually received. Both sides are pinned as tests in
  `scripts/housing_rules/test_planning_filter.py`.
- **ZR / Zoning Research Letter** — a question put to staff about what a site allows. An inquiry, not
  an application.
- **1.E** — Berkeley's unit tabulation form. It states unit counts and **never** states affordability.
- **LMSAP** — a *Landmarks* Structural Alteration Permit. The name reads like a standalone building
  permit and is not one; all 18 are landmarks approvals.
- **ZCBP** — zoning clearance for a building permit; ministerial.
- **DRC / DRCP / DRCF** — Design Review Committee records: companion reviews, not the application.

## What this definition does not decide

- **The record's role** — primary application vs ministerial clearance vs pre-application vs companion
  review. That stays `housing_rules.planning_record.role()`, a lookup over a closed record-type
  vocabulary: form, not meaning.
- **Rung-3 dates.** Which record's Completeness Review speaks for a project is a selection over
  identity, not a scope question (`docs/methodology/identity_is_the_product.md`).

## How the result will be checked

The regex queue of **1,856** records is a **floor**, so the two directions are not symmetric and must
be reviewed differently:

- **Model-only additions** (the model says housing, the regex missed it) — every one is a candidate
  real miss, like `PLN2026-0185`. Reviewed by hand; expected to be tens, not hundreds.
- **Regex-only** (the regex matched, the model says not housing) — each is either a model error or a
  regex false positive. Reviewed by hand; a model error here is the one that would *shrink* our
  coverage, so this side gets the stricter look.
- **Jev vs Sonnet disagreement** on the same record is recorded, never averaged, and is where the
  second read earns its cost.

Nothing is written into any database from this reading. It produces an evidence file; a gated write is
a separate step, and re-running the already-applied planning ingest with a corrected scope remains a
data decision for John (CLAUDE.md: a data error is a new gated write, not a re-run).

## The mixed-use question, and how it was settled

The definition above is the statutory one. It is **broader than what we have been collecting**: by
§ 65589.5(h)(2)(B) a mixed-use building qualifies at two-thirds residential *square footage*, which a
record's prose usually does not state. So a mixed-use record will often be honestly `unknown` on the
two-thirds test while plainly being a housing project by its unit count. Two ways to go:

1. **Statutory strictness** — unknown whenever the two-thirds test cannot be evaluated. Defensible,
   and it will mark many real housing projects unknown.
2. **Units-stated sufficiency (recommended)** — a record that states dwelling units is
   `housing_development` even when the square-footage split is unstated, with the unmet test recorded
   in the reason. This matches what HCD's APR actually collects (units, not square footage) and keeps
   "unknown" meaning *we cannot tell if this is housing*, rather than *we cannot tell the mix*.

**John ruled 2 on 2026-09-28, verbatim "2".** Units-stated sufficiency is what
`reading_rules.PLANNING_SCOPE` encodes: *"A record is not disqualified for failing to state what it
never had to state."* Where the two-thirds test could not be evaluated, the model must say so in its
reason, so the untested condition stays visible instead of being quietly assumed.
