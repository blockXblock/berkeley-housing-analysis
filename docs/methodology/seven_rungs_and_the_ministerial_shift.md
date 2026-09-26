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
