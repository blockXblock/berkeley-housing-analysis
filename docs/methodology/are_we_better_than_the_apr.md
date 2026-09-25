---
title: Are we better than the APR? — and why "17 of 1,099" is the wrong number
date: 2026-09-25
type: methodology
status: open
area: docs/methodology
---

# Are we better than the APR?

**No, and HCD should not replace it with this.** What follows is the argument against our own
project, then the narrower case for what it is actually worth, then a diagnosis of the "17 of 1,099"
figure — which turns out to be measuring something incoherent.

---

## First: what a "gate" means here

Used throughout these notes, and it is a specific procedure, not a mood:

1. **Snapshot** — copy the database to `keep_snapshot_<date>_pre-<change>.db`, confirm size and
   `PRAGMA integrity_check`.
2. **Read-only preview** — open the database `mode=ro` and print exactly what the write *would*
   do: row counts, per-record changes, anything ambiguous listed by name. No writes are possible,
   because the connection cannot make them.
3. **STOP** — a human reads the preview and says go or no. This is the gate proper. Everything
   before it is preparation; everything after it is execution.
4. **Transactional write with verify-or-rollback** — `BEGIN`, apply, then re-count and re-check
   inside the same transaction. Any mismatch → `ROLLBACK` and report. Nothing half-applied.
5. **Fresh-connection fingerprint** — reopen the file and re-verify from scratch, trusting nothing
   held in memory.

On 2026-09-25 the gate rolled back three times on real defects before anything was committed, and a
fourth write was blocked by the permission layer. That is the mechanism working. It is also the
reason none of the day's six defects reached the public site.

---

## The case against us

**The APR knows things we structurally cannot.**

| | v2 | APR (2025 CO rows) |
|---|---|---|
| any affordability tier | **42 of 1,099 (3.8%)** | **206 of 206 (100%)** |
| tenure (own / rent) | **no column at all** | 100% |
| unit category | not modelled | 100% |

Affordability is the entire point of RHNA, and we have it for 4% of projects. This is not an
engineering gap. Primary sources are silent on tenure and income mix, and our own rule 1 forbids
filling them from CKAN. The city has them because it **asks the applicant**. We cannot ask anyone.

**We infer a great deal.** 27.5% of our events are `is_inferred`. 26.7% of completion verdicts rest
on `description_only` — reading prose. Each is an attack surface, and on one day six of them opened:
an ingest that read 1 of 5 feed files; a veto that dropped a 56-unit building over the phrase "temp
power"; a units fallback that over-counted by ~85; two projects marked complete that are a parking
lot and a pizza restaurant; "Auto-Closed" read as withdrawn, putting 214 units on the site as dead;
and a first build that moved five projects' completion years, one from 2018 to 2026.

**Not one was caught by the system.** They were caught by a human who knows the sites and by an
adversarial peer session. The APR's crudeness is partly a feature: a milestone snapshot has almost
no inference in it, so it has far fewer places to be wrong.

**And the APR is a legal instrument.** Statutory definitions, comparable across 539 California
jurisdictions and across years, enforceable by decertification. Replacing it with a bespoke model
destroys the property that makes it useful — that Berkeley's number means what Fremont's means.

## The narrower case for us

- **Stage transitions and durations.** The APR is snapshots; we can say how long a project waited.
- **An evidence trail per assertion** — which permit, which inspection, which verdict, at which
  classifier hash.
- **Reconciliation, which is the real product.** We found genuine APR defects: 2001 Ashby and 2000
  Dwight each appear **twice** in its 2025 completions, and 2425 Durant is a documented cross-year
  double-count. We also found completions it omits entirely — 2001 Ashby 87u, 2000 Dwight 113u,
  1367 University 39u.

That only works *because* we are independent of it. **An audit layer that becomes the system of
record stops being an audit layer.**

---

## Why "17 of 1,099" is the wrong number

It looks like a catastrophic failure of a year's data capture. It is not. It is a denominator
error, three times over.

### 1. Two-thirds of our "projects" entered through the exit door

**707 of 1,099 (64%) have a completion event and nothing before it.** They are ADUs and small
infill ingested *from* CPRA finaled records. They have one stage because that is the door they came
in through — not because the earlier stages were missed. 639 of the 707 are single-unit.

### 2. Most projects legally have no entitlement stage

**842 of 1,099 (77%) are one unit.** An ADU is **ministerial** — by state law it receives no
discretionary entitlement. Requiring `entitlement_approved` of it asks for a step that does not
exist. Only 5 of 842 one-unit projects have one, and those 5 are more likely errors than successes.

### 3. The largest projects are exempt from city permitting altogether

| project | units | city BPs in Accela |
|---|---|---|
| 2200 Bancroft Way | **1,625** | **0** |
| 2400 Bowditch St | **1,500** | **0** |
| 2556 Haste St | **1,113** | **0** |
| 1950 Oxford St (Anchor House) | **772** | **0** |
| Ashby BART | **618** | **0** |

UC approves its own projects and issues its own building permits; BART likewise. **2200 Bancroft is
under construction with zero city building permits, correctly.** These 5,010+ units can never
complete a city-permit chain, and counting them in the denominator guarantees failure.

### The honest denominator

| cohort | projects | full chain |
|---|---|---|
| all projects | 1,099 | 17 — **2%** |
| 5+ units (an ADU has no entitlement stage) | 145 | 16 — 11% |
| …excluding UC / agency-exempt | 141 | 16 — 11% |
| **…and completed (an unbuilt project cannot have a CO)** | **43** | **12 — 28%** |

**28%, not 1.5%.** Still not good. But a completely different diagnosis.

## Would eight more years of building permits fix it?

**No — and the data says why.** Of 88 projects of 20+ units with no BP event:

- **41 already have an issued or finaled BP sitting in the Accela data we hold.** That is a
  **linkage** failure, not a records failure. More records cannot fix it; a join can.
- **47 have no issued BP because the project is entitled and has not started.** The permit does not
  exist. No archive contains it.

And among the 43 completed multi-unit non-exempt projects, the weakest link is not the building
permit at all — **30 lack an entitlement event**, against 22 lacking a BP. Entitlements live in the
Accela **Planning** module, which we have **never ingested**: 1,715 housing development records,
2018–2026, sitting unread.

## So is the fundamental idea wrong?

No. Three narrower things are wrong, and each is fixable:

1. **The metric was defined over the wrong population.** "Full chain" is a coherent question for a
   discretionary, city-permitted, multi-unit, completed project. It is incoherent for an ADU, for a
   UC tower, and for anything still in review. **Report chain completeness on the 43, not the
   1,099**, and say what was excluded and why.
2. **We ingested the pipeline backwards.** We loaded completions first, because CPRA hands you
   completions. That is why 64% of projects begin at the end. The entitlement side was always the
   harder half and it is still not loaded.
3. **We confused a missing link with a missing record.** 41 of 88 large projects have their permit
   in data we already hold. That is an afternoon of joining, not a year of acquisition.

**The narrow corridor was real, and it was this:** we optimised for the data that arrived in
spreadsheets, and built a stage model finer than the evidence we had chosen to collect. The model
is not too ambitious. The collection was too convenient.
