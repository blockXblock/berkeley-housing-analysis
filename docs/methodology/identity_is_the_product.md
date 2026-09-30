# Identity is the product

**Durable principle.** Established 2026-09-26, from the CapDetail harvest
(`docs/audit/2026-09-26_capdetail_harvest.md`). Measurements below are dated observations against
`berkeley_housing_v2.db`; the principle is the invariant, the counts are not.

## The principle

**A city action's date is worth little without the identity of the action it belongs to.** An event
that says *"an application was deemed complete on 2024-04-18"* but not **which application** cannot
be checked, cannot be corrected, and cannot be selected. It can only be aggregated — and an
aggregate over actions silently promotes one action to speak for all of them.

So when a project-level date is derived by `MIN()` or `MAX()` over events of a type, that is not an
algorithm choice. **It is the symptom of a lost referent.** The fix is never to pick the other end;
it is to restore the identity, after which the date is *selected* rather than reduced.

## How it was found

`v_projects_flat` has no `app_complete` column; the served site computes one in
`export_explorer_data_v2.py:165-169`, taking `MAX(event_date)` per event type (`application_submitted`
was corrected to `MIN` in 2026-07-10; `app_complete` and `entitled` were left at `MAX`).

Arguing about which end to use produced two failures pointing in opposite directions, both real:

- **MAX** — `proj5`, 2425 Durant, three `application_complete` events. MAX gives **2025-12-26**, which
  is *after* the project was entitled on 2025-10-09. Rung 3 cannot follow rung 4.
- **MIN** — the reason MAX was chosen (recorded 2026-07-10): MIN surfaced a **prior project's**
  approval at the same address, 3030 Telegraph's 2017 event.

Both are the same defect. MAX promotes the latest sibling record's review; MIN promotes the earliest
action at the address, which may belong to something else entirely. Neither is a rule about dates —
each is a guess standing in for an identification nobody could make.

## The measurement that settles it

Does each `application_complete` event say which city action it was? (An event counts as identified
if it carries a `permit_id`, a `document_id`, or a record number in `summary`.)

| | identifies the action | anonymous |
|---|---|---|
| **has a date** | 60 | **100** |
| **no date** | 96 | 4 |

We hold **dates without identity** and **identity without dates**, and almost nothing with both.
That is why an aggregate was unavoidable: you cannot select the right action from a set whose members
do not say what they are.

Identification rate by rung tells you exactly where the problem lives:

| rung | events identifying which action | |
|---|---|---|
| `co_issued` | 801 / 813 | 99% |
| `building_permit_issued` | 326 / 343 | 95% |
| `application_submitted` | 768 / 966 | 80% |
| `entitlement_approved` | 428 / 662 | 65% |
| `application_complete` | 156 / 260 | 60% |

**CO and BP are healthy because they hang off a `permit_id`** — a permit is a thing with a number, so
the event inherits an identity for free. The two weak rungs are the **Planning-side** ones, where
nothing played that role. The aggregation problem is not distributed randomly; it is concentrated
exactly where identity was never captured.

## Identity is lost at capture, not only in migration

Of the 100 anonymous dated `application_complete` events, 58 came from
`migration_v1_to_v2_20260507`. The rest were recorded by hand, attributed to named planners —
`Desiree Dougherty`, `Katrina Lapira`, `Samella Stover`, `M`. Those captures **preserved the person
and dropped the record.**

That is the more instructive failure. A careful human, reading the city's own page, wrote down the
date and who signed it and did not write down which record they were looking at. The identity was
available and was not kept, because a date plus a name *feels* like a complete observation. It is
not addressable.

## A worked example, scored against a known answer

`proj140` — 2136 San Pablo, 125 units — already held **two** anonymous `Application Complete`
events. The harvest names both:

| v2 holds | signed by | which record, per CapDetail |
|---|---|---|
| 2021-04-28 | Desiree Dougherty | **DRCP2021-0002** — the *design review's* completeness review |
| 2021-08-27 | Sharon Gong | **ZP2021-0046** — the *Zoning Permit's*, i.e. the application |

Both are real city actions on the same project. Neither row in v2 says which is which. With identity
restored, the three rules can be scored:

- **MIN** → 2021-04-28. **Wrong.** That is a design review being deemed complete, not an application.
- **MAX** → 2021-08-27. **Right, by accident.** Nothing about "latest" made it pick the Zoning
  Permit; it happened to be last. At a site with a later design-review-final — which the harvest
  finds routinely — MAX is wrong too.
- **Selection** → 2021-08-27, because `ZP` is the primary application. **Right for a reason,** and it
  stays right as more sibling records arrive.

The selected date *agrees with what v2 already held*, which is the point: the method reproduces a
known-good value rather than inventing one. What it adds is that the value now has a reason.

## Roles have to be classified, and the names mislead

Selection needs to know which record is the application, so the record type must be classified —
`scripts/housing_rules/planning_record.py` (canonical, tested; not a per-script copy). Writing it,
`Structural Alteration Permit` was mapped to `primary_application`, because the name reads like a
permit in its own right. The preview then selected `LMSAP2024-0003` as a project's application.
Every one of the 18 such records carries the **`LMSAP`** prefix: *Landmarks* Structural Alteration
Permit, a Landmarks Preservation Commission approval for work on a designated landmark. It would
have written a landmarks review as a project's acceptance date.

The lesson is narrow and worth keeping: **a record type's NAME is not its role**, and the
record-number prefix often carries the disambiguating information the name has lost. An unrecognised
type returns `unknown` rather than a guess, so a new city record type surfaces as a gap instead of
being silently bucketed.

## Absence is not data either

The same discipline applies to nothing-found. **Pre-Application records publish no workflow
dispositions** — now the COMPLETE population: **272 of 272**, with `divProcessingTable` confirmed
RENDERED and empty on every one, plus three spot-checks (`PLN2018-0048`, `PLN2020-0001`,
`PLN2016-0037`) on fresh sessions with a 30-second wait. All **8 of 8** `Appeal` records likewise.
So rung 1 has no dated city actions to select from, only a filing date and a status — a real limit,
worth stating rather than filling. (This claim was first written at 244/244 with 28 records still
unfetched, and said so; the distinction between "measured so far" and "measured" is the section's
whole point.) So rung 1 has no
dated city actions to select from, only a filing date and a status. That is a real limit, and it is
worth stating rather than filling.

But an empty result is only evidence once it has been looked for properly. `DRCP2015-0002` was
captured empty and a refetch returned **5** tasks (*"2597 Telegraph DR for 10 units bldg."*). So
verified absences are kept in an **append-only ledger with their evidence** (the wait used, and
whether the table actually rendered), never inferred from a blank page. Recorded absence is
skippable; assumed absence is a false negative waiting to be believed.

## The rule

1. **One event per city action**, carrying the record it happened on. A date with no referent is not
   evidence; it is an assertion.
2. **Project-level rung dates are SELECTED, not reduced** — the action on the project's own primary
   application, not an extremum over every action at the address.
3. **Where the primary record is unknown, say so.** "Unknown with provenance" (working rule 1) is the
   honest output; a `MIN` or a `MAX` is a fabricated one wearing a function call.
4. **Do not resolve an aggregation dispute by changing the aggregation.** If MIN and MAX give
   materially different answers, that difference is a report that identity is missing. Fix that.
5. **Capture the referent even when it feels redundant.** Record number, task name, and date
   together; the staff name is the least load-bearing of the four and was the one that survived.

## The smell to catch

Any project-level date produced by aggregating over events of a type — `MIN(event_date)`,
`MAX(event_date)`, "most recent", "first" — is a candidate lost referent. Ask which specific city
action the number is supposed to name. If the answer cannot be given from the row, the number is a
guess, and no choice of aggregate improves it.

## Why this reframes the CapDetail harvest

The harvest was started to measure an interval (filed to accepted, rung 3 of
`docs/methodology/seven_rungs_and_the_ministerial_shift.md`). The interval is real and worth having.
But its more valuable product is **identity**: each disposition arrives as *this record, this task,
this due date the city set itself, this date it was actually marked, this signature* — 1,746 records
of city actions that each know what they are.

That is what makes the Planning rungs addressable instead of aggregable, and it is the same
conclusion CLAUDE.md reaches from the other direction when it says the real fix for the
mod-after-BP anomalies is **ingesting the missing entitlement events**, not adjusting aggregation
semantics.

It is also the argument for the v4 direction resumed 2026-09-26: an event stream where every action
keeps its referent, rather than columns that have already collapsed. ADR-002's three-layer guard
says the same thing about verdicts — EVIDENCE append-only, VERDICT overwritable, DECISIONS
append-only — which only works if each piece of evidence can be pointed at.

## Related

- `docs/audit/2026-09-26_capdetail_harvest.md` — the harvest, and the four traps in getting the data
- `docs/methodology/seven_rungs_and_the_ministerial_shift.md` — the ladder these dates hang on
- `docs/audit/architecture_decisions.md` — ADR-002's evidence/verdict/decision separation
- `docs/methodology/what_we_can_and_cannot_count.md` — coverage limits vs identity limits

## Postscript: the same defect in the CHECKS, not just the data

Three monitoring mistakes in one session, all mine, all the same shape as the one this document is
about — a check whose output cannot be traced back to what it was supposed to be watching:

1. **Too sparse to distinguish.** A progress filter matching only hundred-boundaries went 30 minutes
   with no event at 23s/record. Silence from a monitor is indistinguishable from silence from a dead
   process, so "no news" carried no information at all.
2. **Two watchers, one log.** Every event arrived twice, which makes a duplicate look like a second
   occurrence.
3. **A filter on a CUMULATIVE counter.** `failed=[2-9]` against a running total: once the count
   reached 2 it matched *every subsequent line forever*. The alert stopped meaning "something failed"
   and started meaning "something failed once, a while ago."

The third is the sharpest. **An alert must match a state CHANGE, not a state.** A predicate over a
monotonic total is true forever after it first trips, so it degrades from a signal into a constant —
and a constant is what a broken check looks like from the outside.

This is the mirror of CLAUDE.md's *anchor checks to what stays true, not to what legitimately moves*.
That rule keeps a gate from firing falsely as data legitimately changes. This one keeps an alert from
firing eternally once a counter has moved. Both fail the same way in the end: **a check that cannot
distinguish its own signal from its own background is not a check**, and the damage is the same as a
date with no referent — you are left holding an output you cannot trace to a cause.

Worth stating because the instinct on seeing a noisy alert is to narrow the pattern, and on seeing a
silent one to widen it. Neither is the fix. The fix is to ask what transition the check is supposed to
witness, and match that.

**And then I did it again, one message after writing the paragraph above.** The "fix" for mistake 3
was to raise the threshold — `failed=[3-9]` instead of `failed=[2-9]` — which is still a predicate
over a cumulative counter, so it began matching every line the moment the count reached 3. Raising a
threshold on a monotonic total does not repair the shape; it only postpones it.

The working fix was to **stop watching the counter at all**: match the progress boundary and the
terminal states, and read failures from the artifact (`verify_capdetail_complete.py`) rather than
from an alert. The count is in every progress line anyway.

This is recorded because the sequence is the useful part: naming a defect precisely, in writing,
and reproducing it minutes later on the same system. Knowing the rule did not help; the rule had to
be built into the thing. Which is the document's whole argument — a principle that lives only in
prose has no referent either, and gets re-derived wrong on next contact.
