# Post-mortem: what the architecture got wrong, and what now stops it

**2026-09-28.** Written from one long working session (2026-09-26/27) in which several long-standing
faults were found *with evidence*, and in which I reproduced most of them myself within hours of
writing them down. That second part is the finding: **prose did not hold.** So every lesson below
names the mechanism that now enforces it, or says plainly that none exists yet.

## Read this first — one command replaces this document

```
.venv/bin/python -m scripts.gates.run_gates
```

Today it prints:

```
 DEFECT GATES -- red means broken and fixable
   FAIL  canon uniqueness    one implementation per canonical rule
   FAIL  join keys           a key must identify ONE thing
   PASS  event referent      a dated event must name its source action

 STATUS GAUGES -- red means unfinished, NOT a defect; never weaken these to go green
   OPEN  store convergence   one store, or a maintained fork?
```

Nobody has to remember the lessons; the gates fail when they are broken.

**The two halves are deliberately separate, and that separation is load-bearing.** A DEFECT gate
asserts something that should never be true — red means broken, green is the normal state, chase it. A
STATUS gauge reports how far a long piece of work has got — red means unfinished, may stay red for
months, and **is not a task**. Only defect gates set the exit code.

They were mixed in the first version of this file, and that was a design error of exactly the kind
catalogued below: a red light nobody can fix invites someone to weaken the check so the board looks
clean. `store convergence` cannot go green without building v4's entity layer. If it ever reads DONE
without that having happened, the check was weakened, not satisfied.

**"Green" must always mean the defect is gone, never that the test got easier.** Every instance in the
table below where I made something pass — a floor lowered, a regex widened, a threshold raised — was
this failure in miniature.

---

## Your question: are we on the path to v4?

**No.** Not by anyone's decision — by drift. `gate_store_focus` measures it:

```
v4 substrate: 89,108 events · entity layer: projects=0 structures=0 units=0 parcels=0 addresses=0
v2 (serving):  1,106 projects · 7,043 events
live scripts reading: v2=86  v4=18  v3=14
```

**v4 has a foundation and no building on it.** Every entity table above `events` is empty. v4 cannot
serve anything, so it cannot replace v2, so work continues in v2 — which widens the gap it was
supposed to close.

On **2026-09-26 both directions advanced in the same day**: v4's event layer was rebuilt from pinned
sources (89,108 events), while three separate writes went into v2 (18 planning events, 289 rung-3
events, 4 addresses). Each was correct alone. Together they are the focus loss, and nothing was
watching for it.

**v3 is the clearest symptom:** 14 live scripts still read it; its database is a 2.6 MB stub next to a
19 MB v2 and a 140 MB v4. It was never finished and never retired. It is not an "undefined stage" — it
is a defined stage that was abandoned mid-execution, and the abandonment was never recorded as a
decision.

### Your frame, and where it breaks

You divide the world into **the data store** and **the use of data to represent reality**. That is the
right cut, and the project broke at the seam:

- **the store** went v1 → v2 → (v3) → v4, each a fresh start rather than a migration;
- **the representation layer** — 15 published pages, 73 notebooks, 253 live scripts — was built against
  v2 and never moved.

So each store rewrite had to leave v2 intact, which meant v2 kept accruing fixes, which made the next
rewrite harder. `docs/explorer_data.js`, what the public actually sees, was generated **2026-09-08** and
does not contain any correction made since.

**A store rewrite with 86 scripts pointed at the old store is not a migration. It is a fork.**

---

## How focus was lost — the mechanism, not the mood

Four rewrites in eighteen months were not four failures of resolve. Each was a **correct diagnosis
answered at the wrong layer**:

| the real defect | what was built instead | why it did not settle it |
|---|---|---|
| v1's flat table could not hold a project's history | v2's 46-table normalised schema | the grain was still the *project*, an entity the sources never name |
| v2's projects conflate buildings and mis-attribute dates | v3, a clean stage pipeline | it produced a parallel store with no consumers, so nothing tested it |
| v3 could not settle entity identity either | v4, re-grounded on the event stream | events were ingested; **entities were never built**, so the question was deferred, not answered |

The pattern: **when a model of reality fails, a new store gets built.** But the store was rarely the
problem — the *unit of account* was. Yesterday's buildings stage is the first work that changed the
unit (permit → structure) instead of the container, and it needed no new database: v4's `structures`
table has been sitting there, empty, since June, with the answer in its own schema comment
(`master_event_id -- the New master permit-event (identity)`).

---

## The lessons, each with its enforcing mechanism

| # | Lesson | Evidence it was needed | Mechanism that now enforces it |
|---|---|---|---|
| 1 | **A dated event must name the action it came from.** Without a referent it can only be aggregated, and an aggregate promotes the wrong action. | 100 of v2's dated `application_complete` events named no record. MIN chose a prior project's application; MAX chose a design review three years later. Both wrong, differently. | **`scripts/gates/gate_referent.py`** — per-rung floors on the share of dated events that identify their source, set from measurement. Fails on regression. |
| 2 | **One implementation per canonical rule.** | "Never a per-script copy" has been in CLAUDE.md since June in bold. Four address normalizers were consolidated in July; by September there were two again, and I imported the *wrong* one while believing I was obeying the rule. | **`scripts/gates/gate_canon_uniqueness.py`** — fails on any live definition outside the canon module. Currently FAILS: address key in 3 places, housing filter in **5**. |
| 3 | **A join key must identify one thing.** | `"0 <street>"` is a real city convention for an unnumbered parcel that several APNs share; keyed literally it manufactured 4 false conflations. Hours after fixing that, my own write set `normalized_address` to the street alone — the same wildcard, in an indexed column. | **`scripts/gates/gate_join_keys.py`** — no numberless key where a number exists, one convention per matching column, every APN in canon form, no project with two current addresses. Currently FAILS on mixed conventions (722 pipe / 379 space). |
| 4 | **Verify the delta, not the total.** | An ingest verified `COUNT(*) WHERE observed_by=…` against *this run's* insert count. It passed at 287==287 and then rolled back a correct 2-row incremental run because 289 ≠ 2. I had made and documented the same error earlier the same day. | **Partly.** All three 2026-09-26 ingest scripts now capture a `before` count and assert `after == before + n`, with the reason in a comment. **No gate checks new scripts for the pattern.** |
| 5 | **Absence is data only when recorded with evidence.** | `DRCP2015-0002` was cached as "0 workflow tasks" and would have been skipped forever; a refetch returned 5. 278 Pre-Applications genuinely publish none — that is a finding, not a gap. | **In the harvester only** (`harvest_capdetail.py`: a page counts as done only if it contains workflow text; verified absences go to an append-only ledger with the wait used and whether the table rendered). **Not generalised, no gate.** |
| 6 | **The unit of account is the structure, not the permit or the "project".** | Logan Park South is one 69-unit building with two phase permits; per-permit counting doubles it. Acheson Commons is four buildings at one address; address-based grouping merges them. 19 v2 projects merge separate applications. | **`scripts/v4/build_structures.py`** + **`housing_rules/building_label.py`** (27 pinned tests). Folds 1,189 masters into 1,187 structures; removes 109 units of double-counting. **Preview only — never written to v4.** |
| 7 | **A check that cannot distinguish its own signal from its background is not a check.** | Three monitor failures in one session: a filter too sparse to tell silence from a dead process; two watchers double-reporting; a predicate over a *cumulative* counter that fired forever once it tripped. I documented the third and reproduced it minutes later. | **None.** This is a discipline about writing checks, and nothing enforces it. The nearest thing is that gates now print their own inputs (`gate_store_focus` prints the counts it judges). |
| 8 | **Classification and grouping are different jobs.** | The buildings stage reads `is_master`/`net_units` as *input* from `event_classifications` or a model evidence file, and only groups. That is why retiring the regex classifier does not change it. | **Structurally, by interface** — `build_structures.py --evidence` takes labels from outside. **No gate**, but the separation is now hard to violate by accident. |
| 9 | **A prose rule in CLAUDE.md does not hold.** | Every one of lessons 1–5 was written down before it was broken, most of them by me, some within the hour. | **This whole directory.** `scripts/gates/` exists because documentation was tried first and measurably failed. |
| 10 | **A number must travel with its caveats.** | An applicant-vs-city clock split (84/16) is trivially misread as "applicants cause the delay", when the city writes both labels and applicant time is largely real redesign work. | **`scripts/clock_decomposition.py`** prints its caveats as part of its own output, so a screenshot carries them. **Pattern not generalised.** |

**Unenforced, and worth saying out loud: lessons 4, 5, 7 and 10 have no gate.** Three rely on a habit
and one on a single script. Those are the gaps a rebuild should close first.

---

## What a rebuild should do differently

1. **Build the entity layer on v4 before touching v2 again.** `structures` first — it is specified,
   empty, and the fold exists. Then `projects` as *groups of structures*, not as a primary thing.
2. **Migrate consumers, not data.** 86 scripts read v2. Until that number falls, nothing has migrated.
   Make it a tracked number; `gate_store_focus` already prints it.
3. **Never two live stores.** If v2 must keep serving during a cutover, it should be *generated* from
   v4 and never hand-written. Yesterday's three v2 writes were correct and still made things worse.
4. **Retire v3 explicitly**, in writing, as a decision — or finish it. Fourteen scripts currently read
   a stub.
5. **Every rule ships as an importable module with tests, or it does not exist.** Six such modules now
   exist (`apn`, `address`, `permit_role`, `planning_record`, `planning_filter`, `building_label`,
   `address_points`) with 105 pinned cases. That is the pattern; the gate enforces the uniqueness.
6. **Regenerate the representation layer from the store, on a schedule, with a gate.** The public site
   is three weeks stale and nobody noticed, because no check looks.

## Known defects still live in v2 (found, not yet fixed)

| defect | size | status |
|---|---|---|
| `cpra_master_permits_log_2026_ingest` wrote 78 events using a filter with the same plural bug | 78 events | found by `gate_canon_uniqueness` on its first run; unfixed |
| `normalized_address` holds two conventions | 722 pipe / 379 space | unfixed; needs a decision, not a script |
| 19 projects conflate separate applications | 19 projects | reported; fix belongs to the buildings stage |
| proj151 "Ashby BART" (618 units) has an APN 1.5 km from its own coordinates | 1 project, the largest | flagged, never auto-re-pointed (rule 4) |
| `entitlement_approved` referent rate is 25% | 286 dated events | the worst rung; floor recorded so it cannot silently worsen |
| `docs/explorer_data.js` generated 2026-09-08 | the whole public site | stale; the `application_complete` fix is in the exporter but unregenerated |
