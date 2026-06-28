# Building a database from raw sources — lessons (the course spine)

A student-facing teaching note, one per stage of the `build_v2_from_sources` rebuild. This is **not**
the forensic audit (`forensic_migration_audit.md` is the technical record) — it is the *distillation*:
for someone building a DB from primary sources, what is the transferable lesson, and what trap does
each stage illustrate?

Every stage follows the same shape: **Concept · Trap · Method · Guard · Example.** The recurring
meta-lesson: *build the checks, not just the code — the guard is where the learning lives.*

---

## S0 — the clean join key

- **Concept:** A join key must be normalized, and normalization is harder than it looks. Everything
  downstream (matching, dedup, attaching events) rides on it; get the key wrong and every later stage
  inherits the error.
- **Trap:** The migration baked a disambiguator **into** the key — it wrote `(id:N)` into both the
  `canonical_address` and `normalized_address` fields to make duplicates unique. That *defeats the very
  dedup the key exists for*: two records of the same building no longer share a key.
- **Method:** **One** canonical key function, imported everywhere (never re-implemented inline). Strip
  parentheticals, fold ordinals, canonicalize street types, and make the match a *relation* (not naive
  string equality) so "missing the street type" still matches but two different types don't.
- **Guard:** Validate the key against **known duplicate pairs** (must collapse) AND run a **false-MERGE
  scan** (must NOT collapse two genuinely different buildings). Check both directions — a key that
  collapses everything passes "do dups merge?" while silently destroying the data.
- **Example:** The **type-wildcard**: `2820 San Pablo` ↔ `2820 San Pablo Ave` must collapse (absent
  type), but `Shattuck Ave` ≠ `Shattuck Way` must stay distinct (two real different streets). And the 3
  **ADU+main-house pairs** on one parcel: same address, but kept distinct by **CO-date + permit**, not by
  the address string — because the address can't tell them apart, only the evidence can.

---

## S1 — selecting your population

- **Concept:** *How you decide what's IN your dataset is itself a source of error* — often the biggest
  one. A selection rule is a filter, and a filter has two failure modes, not one.
- **Trap:** The migration used **match-or-drop** — a permit only entered the DB if it matched an
  *already-known* project; net-new buildings "fell on the floor." Worse, it read unit counts by
  **text-parsing the work description** while the structured `UnitsAdded` column sat unused. Result:
  **568 units of real, finaled, multi-family housing silently dropped** — the city's record showed them,
  ours didn't, and nothing flagged it.
- **Method:** **Status-keyed CREATE-by-rule from STRUCTURED columns.** A building enters because its own
  structured status says it's housing — not because it matched something we already had, and not from
  prose. CREATE is the default; ATTACH only on strong identity (permit-family / address).
- **Guard:** **Inspect the real data distribution before writing the filter**, and use a **false-negative
  guard**: ask both "what did I wrongly KEEP?" and "what did I wrongly DROP?" The second question is the
  one people forget.
- **Example:** The **predicate saga** — three iterations, each caught by the guard:
  1. *Loose* (`SubType=Residential`) → leaked **51 zero-unit garages/commercial** into the dataset.
  2. *OccType-only* (`R-1/2/3`) → dropped a real **78-unit mixed-use tower** (coded `A-2 Assembly` for
     its ground floor) and **~14 ADUs** (coded `U` accessory).
  3. *Correct* (`R-occupancy OR units>0 OR ADU-flag`) → keeps the towers and ADUs, excludes the garages.
  The lesson a student remembers: **don't write a filter from your ASSUMPTIONS about the data — look at
  it, then guard both directions.**

---

## Interlude — the predicate-correction chain (S1 auditing itself, before S2)

Building S2 forced a re-examination of S1's own predicates and surfaced a chain of lessons that are
the heart of the course. The headline: **even the corrected rebuild made a milder version of the
migration's own error**, and the discipline is what caught it.

1. **The recurring trap — "New only" / "UnitsAdded only" is too narrow for Berkeley housing.** ADUs are
   coded `Addition`/`Alteration` with their count in `NumberUnits`, not `UnitsAdded`. This same trap
   appeared **three times** (S1 spine membership, S2 event filter, S1's unit signal). *When the same
   trap recurs, that is the signal to extract the concept to a shared, single-sourced definition* —
   duplicated logic re-makes the same mistake independently.

2. **Same column, different meanings — read structured columns PER CONTEXT, not uniformly.**
   `NumberUnits` = new units on a `New` permit, the (capped) ADU count on an ADU permit, but the
   **EXISTING-stock count** on a plain alteration ("kitchen remodel, units 1-6" → nu=6). Reading it
   uniformly gives you either an under-count (ignore it → miss 265 ADUs) or a **4,239-unit over-count**
   (add it everywhere → count existing housing as new). The rule (`net_units`): `ua` if present; else
   `nu` if New; else `min(nu,2)` if ADU; else 0.

3. **Row-recognition vs event-creation are different concepts needing different predicates.**
   `is_housing` (broad: "is this a housing row", for grouping) ≠ `net_units`/housing-creating (narrow:
   "did this permit create a dwelling", for spine + events). A garage-demolition permit on an ADU
   project is a housing *row* but not a dwelling-creating *event*. Don't conflate them.

4. **Measure before you refactor.** Before unifying duplicated logic, *measure whether the copies
   agree*. Here they didn't — one read was a silent dead branch. The measurement revealed a latent bug;
   blind "it's just a refactor" unification would have hidden or propagated it. Aligning duplicated
   logic is **either free (safe unify) or a gated change (hidden bug) — and you must know which first.**

5. **A clean result can hide a dead branch.** The first corrected preview showed **"+0 ADUs"** — not
   because there were none, but because `str(numpy.True_)` is `'true'`, not `'yes'`, so a bare
   `== 'yes'` check silently disabled the ADU branch. **When a fix shows "no change," verify it RAN.**
   A type mismatch disables a branch silently, and a disabled branch passes every test because it never
   executes. (Fix: one `is_adu()` reader normalizing bool/numpy-bool/string, imported everywhere.)

6. **The rebuild audited itself.** S1 — the *corrected* reconstruction — carried a milder version of the
   migration's exact sin: reading the unit signal too narrowly, silently dropping **265 real ADU
   dwellings (~312u, 223 completed)**. The false-negative safety check caught it. **Even a careful
   reconstruction must verify its own output with the same rigor it applies to the source it replaces.**

---

## S2 — milestones as evidence

- **Concept:** A milestone (permitted, completed, entitled) is a **dated event with a source and an
  honest inference flag** — not a status label carried forward.
- **Trap:** the migration set a project's stage from a v1 status string and stamped `is_inferred=0` /
  `confidence=high` on everything, evidence or not — so the DB couldn't tell a sourced fact from a guess.
- **Method:** every event = `(type, date, source, is_inferred)`; `is_inferred=0` is a *promise* a
  structured column backs it. BP ← `Issuance Date`, CO ← `Finaled Date` (the permit-finaled date; CPRA
  has no CO column — derivation recorded). Entitlement dates aren't a clean field → **flag
  `needs_acquisition`, never invent**.
- **Guard:** cross-source corroboration (CPRA vs v2 permit dates — disagreements are S8 *findings*, the
  rebuild uses the structured source); per-milestone sanity (the completion date must come from the
  housing-creating permit, not a later sign/TI permit).
- **Example:** 1950 Addison — taking MAX-finaled over *all* permits gave 2024-01-29 (a later ancillary
  permit); the real completion is 2022-08-09 (the New permit). Fix: date the milestone from the
  housing-creating permit only (the same `net_units` predicate as S1).

**The three lessons S2 crystallized:**

1. **Same missing data, two responses.** The migration and the rebuild faced the *identical* gap —
   entitlement dates aren't in the permit feed. The migration **asserted** an entitlement/stage it
   didn't have (757 projects stamped entitled+ with no event, `confidence=high`). The rebuild **flags**
   the gap (`entitlement_approved`, date=NULL, `needs_acquisition`) and **invents nothing**. Same
   absence; one fabricated, one disclosed. *The difference between a trustworthy DB and an untrustworthy
   one is what each does when the data isn't there.*

2. **Mark provenance PER SOURCE, not uniformly.** `is_inferred=0` is a *promise a structured column
   backs this value* — it must be earned. BP ← `Issuance Date` and CO ← `Finaled Date` earn it
   (`is_inferred=0`); entitlement from *parsed .txt status* does **not** (`is_inferred=1`, no date). The
   migration's sin was one blanket confidence for everything; the rebuild's discipline is a confidence
   *computed from the actual source*. (And the CPRA-vs-v2 date disagreements are *persisted* as S8
   findings — the rebuild uses the structured source and records the conflict, never lets v2 veto it.)

3. **Verify a zero.** S2's entitlement coverage came back **0** — a suspicious number. We didn't accept
   it: of 91 `.txt` files only 12 have a parseable address, only 4 are "Approved", and **none of those 4
   sit at a spine building** — real no-overlap, not a broken join. *A zero is a hypothesis, not a result.
   Confirm whether it's "genuinely none" or "the join silently failed" — they look identical until you
   check.* (Cf. the "+0 ADUs" dead branch in the interlude: a zero that meant a bug, not an absence.)

---

## S3 — stage is derived, not declared

- **Concept:** A lifecycle stage is a CONCLUSION you compute from evidence (the dated events), not a
  label you carry forward. A building can only reach a stage an event justifies; absent evidence, the
  honest floor is "pipeline".
- **Trap:** the migration set stage from a v1 status STRING and stamped it `confidence=high` — 757
  projects claimed "entitled+" with no event behind the claim.
- **Method:** `co_issued`→completed, `building_permit_issued`(no CO)→permitted, `entitlement_approved`
  (no BP)→entitled, none→pipeline. v1's status enters ONLY as a cross-check (S8); where derived ≠ v1, we
  record the disagreement and trust the EVENTS.
- **Guard:** assert **0 asserted stages** (every non-pipeline stage names its justifying event) and
  `co_issued ↔ completed` is 1:1. The reconcile table persists every v1 disagreement.
- **Example:** 14 projects where v1='completed' but the events give 'pipeline' — v2 completions the
  independent rebuild cannot corroborate (proj465 739 Channing, proj728 1118 Oxford). Real S8 findings.

**Two lessons S3 crystallized:**

1. **Don't conflate two findings that share a number.** The audit's "757 entitled+ with no entitlement
   event" *sounds* like 757 over-asserted stages. It isn't. Re-derived from events: **668 of the 757 are
   event-backed at permitted/completed** (v1 merely *under-stated* "entitled"), 80 are entitled-not-built,
   and only **~9** are stage-unsupported. So there are **two distinct findings**: (A) ~33 stage labels
   genuinely unsupported by any event → S8 over-assertion queue; (B) 757 missing entitlement *events/dates*
   → the S2 acquisition queue. Same input, two findings — measure each, name each, never merge them.

2. **Your verification step can destroy what it verifies.** The S1 idempotency RE-RUN — a *check* that
   the write reproduces — **clobbered its own pre-write snapshot**, because the write used a fixed tag and
   the re-run called `--write` again, overwriting the rollback point with the already-written state. *A
   verification must be NON-MUTATING with respect to the state it protects.* Fix: one shared `gating.py`
   `snapshot_v3` that refuses to overwrite an existing rollback point, plus a `--no-snapshot` flag the
   idempotency re-run uses. (Same anti-drift discipline as the key/APN/predicate: the snapshot helper had
   *two* copies that drifted — one definition, imported everywhere.)

---

## S4 — resolving disagreements by evidence, not by source-preference

- **Concept:** When two sources disagree on a value, the answer is not "trust source A" or "trust source
  B" — it's *find out WHY they differ*, and write the value the evidence corroborates. The disagreement
  is bidirectional (sometimes A is right, sometimes B), so any fixed preference is a coin-flip dressed as
  a rule.
- **Trap:** "default to CPRA" (or "default to v2") — a source-preference policy that's wrong half the
  time and hides the real story (a data gap vs a development-granularity difference vs a self-contradiction
  are three different findings, not one).
- **Method:** for each of the 6 unit disagreements, read the *structured per-permit-family `net_units`*
  and ask what produced each side's number. Resolve to the corroborated value; where the evidence can't
  resolve it, FLAG + HOLD — never average or guess.
- **Guard:** the source-disagreement rule — **write a value only where corroborated.** And the canonical
  must equal the single-sourced derivation (`net_units`) for every building: 0 internal leak (the
  proj15-class total-vs-sum leak can't exist when units are single-sourced).
- **Example — the 6, each a different story:**
  - **v2 under-counts** (1500 San Pablo 159 vs structured 170; 739 Channing modeled only *"Building B"*
    4u of a 14u project — the per-permit-vs-per-project gap, resolved in our favor).
  - **v2 null/data-gap** (2328 Channing, 2330 Blake stored 0 against structured 13 / 6).
  - **v2 self-contradiction** (2317 Channing stored 22 while v2's *own* description says "17 apartments"
    — the structured permit and v2's own prose both say 17; the stored 22 is the error).
  - **genuinely unresolvable → FLAG, don't guess** (2352 Shattuck / Logan Park: a *multi-building*
    development whose 3 permit-families don't cleanly aggregate; v2's 237 is the development total, our
    per-building MAX is 135 — held at 135, flagged to S8 for the multi-building modeling, no number invented).

---

## S5 — affordability, or: a citation to the wrong document is not a citation

- **Concept:** A value is "sourced" only if it points at a *real source*. Affordability tiers come from
  document-cited evidence — and what matters is the document's TYPE, not merely that a document id exists.
- **Trap (two-layered):** the migration (a) couldn't represent middle tiers — a 2-bucket VLI/ABOVE_MOD
  ceiling — and fabricated market-rate by `market = units − vli`; then (b) it *laundered* that fabrication
  by "citing" it to a document — but the document was the **CPRA permit report itself** (an untyped stub),
  for **704 projects**. A `source_document_id NOT NULL` check would import all 704 as cited affordability,
  re-laundering the fakes the rebuild exists to kill.
- **Method:** full vocabulary (ELI/VLI/LI/MOD/ABOVE_MOD); key on **document TYPE** (`density_bonus_application`
  / `affordable_housing_agreement`), not the NULL-check; above-mod is *only* ever a source-stated tier,
  never derived; below-market gaps → `needs_acquisition`.
- **Guard:** **remove the fabricated value, don't just demote its confidence** — a low-confidence fabricated
  number is still fabricated. Assert **0 present tier rows from a stub/null doc**, **0 ABOVE_MOD without a
  source** (no subtraction), and tier-sum reconciles to the canonical s4_units (no silent gap).
- **Example:** the 704 stub "citations" → `needs_acquisition` (values gone, not demoted-but-present); the 9
  genuine DBE/AHA docs fold at confidence=high, **incl. MOD tiers (proj8/15/35 = 8/9/34)** the 2-bucket
  model could never hold. The honest headline this surfaces: **affordability is invisible in the
  built-permit record** — every one of the 1,385 built buildings is `needs_acquisition`, and the only real
  tier data is for 9 *entitled* projects. That's the transparency-ordinance argument, now structural in the
  data: you can rebuild *how much* got built from public permits, but not *who it's for*.

**Cross-cutting lesson:** *demoting confidence ≠ removing a fabrication*, and *a citation to the wrong
document type is not a citation*. Provenance is about the SOURCE, checked at its type — not the mere
presence of a foreign key.

**S5 follow-on — partition `needs_acquisition` by OBLIGATION before harvesting:**
- *Not every unknown is a gap.* Of the 1,385 built buildings flagged `needs_acquisition`, **1,219 (1-2u
  SFR/ADU/duplex) have no inclusionary obligation at all** (below Berkeley's BMC 23.328 5,000-sqft / ~5-unit
  threshold) → reclassified **`market_rate_no_obligation`**, a KNOWN regulatory state. That shrinks the
  real harvest backlog from 1,385 to **75 obligated buildings (4,308u)** — *most of the "missing data" was
  never owed in the first place.* Scope the harvest at the obligated set, large-first.
- *A classification from a proxy gets a proxy's confidence.* `market_rate_no_obligation` is derived from a
  UNIT proxy for a FLOOR-AREA threshold (no sqft data exists) → recorded `confidence='derived'`,
  `basis='derived: below inclusionary threshold (unit proxy)'`, never high. (The input S6 needs.)
- *Guard the dangerous direction.* The safe error is leaving a small building flagged (harvest confirms no
  obligation); the dangerous one is reclassifying an OBLIGATED building as market-rate (hiding a real gap).
  So only the **clearly** sub-threshold 1-2u reclassify; the **10 marginal 3-4u** and **81 zero-unit
  (count unknown)** are HELD `needs_acquisition`. When uncertain, hold.
- *The snapshot fix paid off, concretely:* this was a SECOND write to the s5 table. With a distinct
  `pre-s5-obligation` tag and the refuse-to-clobber helper, we now hold BOTH `pre-s5.db` (pre-affordability)
  and `pre-s5-obligation.db` (pre-reclassification) — two clean, distinct rollback points. Exactly the
  two-writes-to-one-stage case the fix was built for.

---

## S6 — confidence is earned, computed per fact

- **Concept:** Confidence is a *conclusion from evidence*, computed **per fact**, never a constant. A
  building has separate confidence for its unit count, its stage, its dates, and its affordability —
  because the backing differs for each.
- **Trap:** the migration's original sin, in one field — it stamped `confidence=high` on *everything*,
  sourced or guessed, so the database could not tell a fact from a fabrication. (Every earlier stage's bug
  — fabricated tiers, asserted stages, blind-copied units — was *licensed* by that one blanket-high.)
- **Method:** map each fact mechanically from what S2-S5 recorded. **high** = a structured column / typed
  document / evidence-based resolution / dated event backs it; **medium** = a reasoned proxy (the
  `market_rate_no_obligation` unit-proxy); **low** = no source / a flagged cross-source conflict / an
  honest floor (pipeline, needs_acquisition, FLAG-S8). No fact is high by default.
- **Guard:** **assert 0 facts at `high` without a real backing** — the regression lock that makes the
  migration's blanket-high *structurally impossible*. Every `high` must trace to a named backing.
- **Example:** one building reads `units=high · stage=high · dates=high · affordability=medium`; another
  reads `units=low (0-unit) · stage=low (pipeline)`. The affordability fact alone spans **9 high / 1,219
  medium / 166 low** — three evidence states, three tiers. Confidence varies across facts in **1,304 of
  1,385 buildings.**

**Cross-cutting lesson (the spine of the whole rebuild):** *confidence is a function of recorded evidence,
not a vibe and not a default.* The migration's failure wasn't any single wrong value — it was that it
**couldn't tell you which values to trust.** S6 is where the rebuild earns the opposite: every fact says,
mechanically, how well it's backed — so a reader (or the A2, or a journalist) knows exactly where the data
is solid and where it's a flagged gap. That distinction is the entire point of building from sources.

---

## S7 — three date concepts, and re-wiring an orphaned module without re-orphaning it

- **Concept:** A single completion/permit date answers *three different questions*, each used by a
  different APR table — and the naive `cycle_for_date` conflates them. S7 tags every dated milestone with
  all three, kept as distinct columns: **`reporting_year`** (calendar year of the event — Table A/A2
  by-year), **`calendar_cycle`** (5th/6th by the 2023-01-31 boundary), **`in_projection_period`** (the
  narrow 2022-06-30→2023-01-30 bridge window, a bool), and **`rhna_credit_cycle`** (which 8-year
  allocation the unit's RHNA progress counts toward).
- **The load-bearing non-conflation:** RHNA *credit* is earned at **building-permit issuance, not CO**, and
  the credit boundary is **first-BP ≥ 2022-06-30** (the projection start, no upper cap) — which is NOT
  `cycle_for_date`'s 2023-01-31 (the planning-period start), and NOT `is_projection_period` (the narrow
  window). Proof the columns stay distinct: **94 BP events are calendar_cycle=5th but rhna_credit_cycle=6th**
  (projection-credited). Collapse any two of these and you misreport.
- **Wrong milestone caught in validation:** the first pass compared *CO* completions in the projection
  window (68/437u) to the city's reported 492/503 — but 492/503 is a **BP-credit** figure. Switching to the
  BP milestone is necessary; the magnitude still doesn't reconcile (our cumulative 6th BP-credit
  421/1,792u thru CY2024, 648/2,419u thru CY2025) → a **scope/population question for S8/S9, not a number
  to tune toward.** The validation's job is to *surface* the difference, never to force a match.
- **Re-orphaning is the real risk:** `housing_rules` was a single-sourced policy module that had been
  **imported nowhere that mattered** — a silent orphan. Re-wiring it means more than `import`: a binding
  that is never *called* is still orphaned. So the gate's **triple wiring guard spies on all three
  functions and asserts each was invoked** (cycle_for_date 2236× · is_projection_period 2236× ·
  rhna_credit_cycle 1285×) — not merely that the names resolve.
- **Add the missing rule TO the module, don't inline it:** `rhna_credit_cycle` didn't exist as a named
  function (the 2022-06-30 boundary was inlined in `generate_apr_v2.py`). Per the anti-drift rule it was
  **added to `housing_rules/classifiers.py`** (sourcing the boundary from `PROJECTION_PERIODS`, not
  `RHNA_CYCLES`) — which now single-sources a boundary the generator duplicates (queued: refactor the
  generator to import it).
- **"Verify a zero" caught a mislabel:** Phase A reported **100** CO-only buildings; the preview surfaced
  the event-grounded truth — **6** (a CO row, no BP → credit NULL). The 100 had folded in **94 buildings
  with no dated event at all** (pipeline/no-milestone), which correctly never enter `s7_cycle`. The count
  you assert must be the count the data actually produces.

**Cross-cutting lesson:** *one field can carry several questions, and a single-sourced rule is only
single-sourced if it's actually called.* S7 is two disciplines at once — refusing to collapse three
genuinely-different date semantics into one, and re-attaching an orphaned policy module so tightly that a
test would fail the instant it drifts back to silence.

---

## S8 — gather, don't re-derive; the exact-count lock; one subject can be two findings

- **Concept:** A reconciliation matrix is *synthesis*, not a fresh pass. Every build stage already flagged
  its disagreements into a `_reconcile`/`_overlap`/`_review` table; S8 GATHERS them into one durable,
  auditable artifact (`s8_reconciliation`, 90 findings, 10 distinct finding_types), copying each row's
  basis rather than recomputing it. The whole job is to collect *all* of them, distinctly.
- **The load-bearing check is the EXACT-COUNT:** gathered `date_reconcile`==`s2_date_reconcile`(3),
  `stage_reconcile`==`s3_stage_reconcile`(33), `unit_reconcile`==`s4_unit_reconcile_resolved`(6),
  `apn_overlap`(13), `xaddr_review`(22) — re-queried against the live source tables so an **off-by-N
  catches a dropped or double-gathered finding.** (The 11→13 / 21→22 stale-number catch from the resume
  note is exactly why this is asserted against the *live* tables, not carried-forward constants.)
- **Distinct finding_types, never one bucket:** date / stage / unit / apn / xaddr / multi_building /
  measurement_basis / rhna_scope / entitlement_gap / crosscheck stay separate. The entitlement-DATE gap
  (acquisition) is NOT the same as stage over-assertion (the 33); a date reconcile is not a unit reconcile.
  Flattening them would hide which kind of problem each is.
- **One subject, two finding_types ≠ double-count:** 2352 Shattuck (Logan Park / proj179) appears as a
  `unit_reconcile` (held_flagged — its 135-vs-237 unit disagreement) AND a `multi_building_development`
  (category_pattern — the reusable "a development spans N permits; per-building MAX under-counts" finding).
  Two aspects of one subject, deliberately. A v3 scan (v2_total > 1.3× per-building MAX) confirmed the
  pattern has exactly **1** member — so "1" is a verified scan result, not an assumption.
- **A disposition can encode honesty the data can't:** the UC residences carry `pending_uc_conversion`,
  a disposition DISTINCT from `needs_acquisition`. `needs_acquisition` = we don't know the size;
  `pending_uc_conversion` = we KNOW the size (in beds, sourced) and refuse to assert a fabricated
  bed→unit number — only UC's authoritative conversion is missing. `units=NULL` here is a *refusal*, not
  a gap. (And because none of the 4 UC residences are in the CPRA spine, **0** v3 units were ever at-risk
  — the matrix documents a v2-vs-v3 difference, it doesn't change v3.)
- **Wiring proven by what's CALLED *and* what isn't:** the guard spies that `housing_rules.cycle_for_date`
  (date-reconcile cycle-shift annotation) and `s0_keys.normalize_address` (xaddr proximity annotation) are
  actually invoked — and that `housing_predicates.net_units` is **deliberately NOT called**, because
  re-deriving units would violate "gather, don't re-derive." Here, *not* calling a single-sourced function
  is the correct behavior, and the design says so explicitly.

**Cross-cutting lesson:** *the reconciliation matrix is where the rebuild's honesty becomes auditable* —
not by resolving every disagreement, but by gathering every one, in its own category, with its evidence,
so a reader can see exactly what differs from the migration and how each difference was disposed. Counting
them exactly is the discipline that proves none was quietly dropped.
