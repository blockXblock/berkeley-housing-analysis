---
title: Seven rungs — and why the acceptance step is the one that measures policy
date: 2026-09-25
type: methodology
status: open
area: docs/methodology
---

# Seven rungs, and the acceptance step

John, 2026-09-25: *"after a permit application is submitted, the city does not accept the
application for a while. when it does, the stage is 'application finaled' or 'application accepted';
then the process of consideration of the permit starts, and ends with 'entitlement' or refusal.
California law is removing city staff from making this decision by implementing 'by rule' or
'ministerial' automatic acceptance if some standards are met; we want to track how this changes city
performance against our historical record."*

That is the sharpest reason yet to carry the step, and it changes what the ladder is *for*.

## The ladder

| rung | name | what it means |
|---|---|---|
| 1 | pre_application | informal enquiry, pre-app meeting, zoning research letter |
| 2 | application_submitted | filed, **not yet accepted** — Incomplete Pending Applicant, Corrections Pending Applicant, resubmittal awaiting review |
| **3** | **application_accepted** | **the city has deemed it complete; consideration begins** |
| 4 | entitled | planning approval granted |
| 5 | permitted | building permit for the housing issued |
| 6 | under_construction | inspections occurring on the housing permit |
| 7 | completed | the housing permit itself Finaled |

Rung 3 was missing from v2's `vocabulary_stage_types`, which collapses rungs 2 and 3 into a single
`in_review`. The *events* already distinguish them — `application_submitted` (type 2) and
`application_complete` (type 3) — so the distinction exists at evidence level and is thrown away at
stage level.

## Why rung 3 is the one that measures policy

**The gap between rung 2 and rung 3 is staff discretion made visible.** An application sits filed but
not accepted for as long as the city takes to accept it. Nothing in the project changes during that
interval; only the city's disposition does.

California is removing that discretion. **SB 9, SB 35, SB 330, SB 684 and AB 2011** push qualifying
projects onto **ministerial** or by-right tracks where acceptance is automatic once objective
standards are met — which is exactly what John watched at Planning Commission for Ashby BART, where
the argument was over objective design standards rather than over whether to approve.

So the measurement that answers "how is this changing city performance" is:

    submitted -> accepted   interval, discretionary vs ministerial, by year
    accepted  -> entitled   interval, discretionary vs ministerial, by year

Neither is derivable from a stage field. Both need rung 3 as a dated event, which is why the
classifier returns **(rung, track)** as a pair rather than a stage alone.

## The track flag

Every project also gets `ministerial` / `discretionary` / `unclear`. Markers present in the Planning
corpus as of 2026-09-25:

| marker | records |
|---|---|
| SB 330 | 120 |
| SB 35 | 19 |
| SB 684 | 15 |
| SB 9 | 12 |
| by-right | 7 |
| ministerial | 4 |
| AB 2011 | 4 |

Plus every ADU and JADU, which are ministerial by state law and are the bulk of the single-unit
cohort.

## What the evidence will and will not support

**Thin, and it must be said plainly.** Only **39** Planning records carry an explicit
`Application Complete` status, against **69** reading `Incomplete Pending Applicant`. v2 holds
`application_complete` events for just **69 projects** and `application_submitted` for **180**. So a
first pass will infer rung 3 from sequence — an incomplete status followed by a resubmittal followed
by review — more often than it reads it directly.

That is acceptable for a *distribution* and not acceptable for a *duration*. Measuring the
submitted→accepted interval needs real dates on both ends, and the honest position is that we can
currently do that for the ~69 projects with genuine `application_complete` events and no more.
**Widening it is what the un-ingested Accela Planning stream is for — 1,715 housing development
records, 2018–2026, never loaded.**

⚠ Do not publish an interval trend until that ingest exists. A trend computed on 69 projects,
selected by whichever ones happened to get a clean status, would be a selection artefact wearing the
clothes of a policy finding.

---

## The ministerial shift is visible in the DISPOSITION VOCABULARY, not in a duration

Added 2026-09-26 from the CapDetail harvest (`docs/audit/2026-09-26_capdetail_harvest.md`). The two
paths through Berkeley's Planning module publish workflows of a different *shape*, and the difference
is not speed — it is whether the workflow contains a step that can refuse.

**Ministerial — `ZCBP`, Zoning Certificate for Building Permit** (46 records measured):

    Completeness Review  ->  Zoning Certificate  ->  Case Closed

Three tasks. The disposition on all 46 is **`Complete`** (plus `Issued`/`Completed` on Case Closed).
There is no approval, no denial, no hearing, no continuance — **no disposition in the vocabulary that
can go the other way.** That is what "by rule" looks like in a workflow table: the task exists to be
discharged, not decided.

**Discretionary — `DRCP`, Design Review Committee Preliminary** (107 records measured):

    Completeness Review  ->  Staff Report  ->  DRC Meeting  ->  Case Closed   (+ public notification)

277 Completeness Review dispositions across 107 records — **2.6 per record.** The vocabulary has
moving parts: `Incomplete Pending Applicant` **114**, `Resubmittal Pending Staff` **56**,
`Continued off Calendar` **27**, `Approved` 154, `Application Complete` 90.

### What this means for measuring the shift

**The discretionary cost is ITERATION, not a single slow decision.** 114 `Incomplete Pending
Applicant` plus 56 `Resubmittal Pending Staff` over 107 records means the applicant is sent away and
returns, repeatedly, *before the application is even accepted*. That is the cost the by-right reforms
target, and it is a count from the city's own record rather than an anecdote.

**So the instrument is a vocabulary share, not a duration:** what fraction of housing moves from a
record type whose vocabulary CONTAINS `Incomplete Pending Applicant` to one that does not. That is
cleaner than a stopwatch, needs no model, and cannot be gamed by a record being closed quickly.

**Honest caveat — do NOT compare their durations.** A `ZCBP` is a zoning clearance attached to a
building permit; a `ZP` is a discretionary land-use approval. They are not the same decision, so
"ministerial is faster" from these two populations would be a category error. Comparing their
**vocabularies** is fair; comparing their **clocks** is not. The legitimate before/after is the same
record type over time, or the same project type moving between paths.
