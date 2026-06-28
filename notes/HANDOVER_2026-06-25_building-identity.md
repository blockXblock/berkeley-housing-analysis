# HANDOVER — Berkeley Housing Pipeline, building-identity / S1.5 (2026-06-25, end of session)

**To:** the next chat-Claude. **From:** chat-Claude, end of a long S1.5 session.
**Read this first, then the files in §"WHAT TO READ" — in that order — BEFORE proposing anything.**

---

## THE ONE LESSON THAT MATTERS MOST (read twice)

This session spiralled. I repeatedly **re-derived decisions John had already made** — permit-is-identity
(June 18), contested-needs-independent-sources (June 17) — and kept proposing work that was already done
or already settled. John corrected it three times. The correction, verbatim in spirit:

> **Inventory the STATE first, then act. Stop generating from the *logic* of the problem — the logic keeps
> re-inventing decisions already made. When you recommend an action, SEARCH PAST CHATS to check whether it
> was already done or already decided.**

So: **do not design from first principles. Read the state. Search before recommending.** The decisions
below are SETTLED — your job is to align to them and execute the next concrete step, not re-litigate them.
If you find yourself constructing an elaborate model or "discovering" that address/APN aren't enough — STOP,
that's the spiral; it's already known and solved.

---

## WHERE WE ARE (the settled state)

### The problem
Berkeley's housing record collapses multi-building developments into one address-keyed row (e.g. Logan
Park / 2352 Shattuck = North 135u + South 69u, collapsed to one building with the wrong completion year).
S1.5 is the building-identity fix that splits these correctly so the v3-vs-city comparison (S9) is right.

### The settled identity decision (June 18 — DO NOT re-derive)
**A building = its New master construction permit. Address and APN are ATTRIBUTES (M:N), never the key.**
- Two distinct New masters = two buildings, whether they share an address or a parcel.
- The discrimination (the hard part): distinguish **phased permits of ONE building** (Phase I + Phase II →
  one building, consolidate) from **two distinct buildings** (two masters → two buildings) — using
  **permit descriptions / building-labels** ("North Building"/"South Building", "Phase I/II"), NOT APN.

### Why APN-routing is DEAD (proven this session)
`split_multibuilding` (the written-but-unwired rule in build_s1.py) groups by **APN** — and APN-routing is
**wrong even for the one case it was meant to fix**. 2352's South building filed its Phase I permit
(B2019-05575) under the **pre-split parent APN 018-05** (before child APN 041-00 existed). APN-grouping
misroutes that 2023 permit onto North → North gets co_issued 2023-08-08 → reproduces the exact Frankenstein
bug S1.5 exists to fix. **The correct discriminator is the building-label, not the APN.** (Proven: the
Stage-1 preview showed North landing 2023, not 2022.)

### The inspection finding (settles the architecture, but NOT a tool you need now)
The Accela inspection scrape (557 inspections on B2019-05574 = 2352 North; 146 on B2019-05575 = South)
**independently proves permit-identity is right** — each permit has its own coherent sequence terminating
at the right date (North 2022-01-14, South 2023-08-08) even under the shared parent APN. **BUT the decisive
sub-finding: those inspection-final dates AGREE EXACTLY with CPRA's Finaled-Date — North's correct 2022
date was in CPRA all along.** S2 just MAX-collapses it by grouping on address. **So the fix is permit-keyed
grouping + phase-consolidation, NOT a harvest, NOT a new signal.** Inspections corroborate; they don't
resolve.

### THE MEASUREMENT that sets the next step (read `contested_set_measurement.md`)
Of the 36 collapse developments, measured against the existing S9 answer key:
- **8 resolve by master-grouping ALONE** (cottage-courts: 1444/1446 5th where 4 masters = 4 city buildings).
- **6 are PHASED** (2352, 1173 Hearst, 1516 Carleton, 1310 Haskell, 1811 63rd, 812 Page) where
  #masters ≠ #city-buildings → need **phase-consolidation by label** (free, from descriptions).
- **22 are city-silent** (no answer key — 4 city-collapsed + 17 reported-no-CO + 1 absent).
- **The bottleneck is phase/label-consolidation logic — NOT missing data, NOT harvest.** Harvesting 73
  more permits would only CORROBORATE dates already in CPRA, and (being per-permit) would corroborate the
  over-split rather than fix it. **Harvest is a confidence layer, not the resolver. Defer it.**

---

## THE DECISION POINT (where the session ended — John has NOT yet chosen)

The proposed next move, which John was about to decide:
**Build the resolver = master-permit grouping + phase/label-consolidation; check the ~14 granular cases
against the existing `s9_city_building_breakout` answer key. NO harvest.**

John's open question on the table (he chose to pause before answering): is **phase-consolidation by label
reliable enough** to be the resolver? (Can "North Building"/"South Building"/"Phase I/II" be parsed robustly
from WorkDescription? Its weight should be parse-reliability-adjusted.) Resolve THIS before building.

**Do not assume a path. Ask John, or if he's directed the build, start with the reliability check on label
parsing FIRST (the same "read the live data before designing" discipline that caught the APN-routing bug).**

---

## THE STATE INVENTORY (read `state_inventory.md` — the ground truth, don't re-derive)
- **Harvester:** idle/exhausted. Queue DRAINED (92 done, 0 pending). Scope was only completed+under-
  construction v2 permits. 37/1385 buildings have inspections, **as JSON files, UNJOINED to any DB**.
  Extending it = a real re-scoped harvest, not resuming.
- **S9:** the you-vs-CITY comparison ALREADY EXISTS and is current (`s9_*` in v3: scorecard net +288, the
  14-dev `s9_city_building_breakout` answer key, 17 reported-pending, 1 coverage gap, 36 identity-caveats).
  **This is oracle-comparison, NOT contested.**
- **Contested:** the state does NOT exist and is **correctly empty** (June-17 decision). No independent-
  source layer is joined (inspections unjoined/2%, staff reports/AHCPs not collected). `permits.
  completion_verdict` is 3-valued (completes 732 / does_not 106 / ambiguous 157) — `ambiguous` is
  single-source uncertainty, **NOT** contested. Do not conflate "we differ from the city" with "contested"
  — that's the role-crossing/circularity bug. The city APR is the ORACLE, never an independent source.

---

## WHAT TO READ (in this order, before acting)

1. **This handover** (you're here).
2. **`notes/rebuild_resume_S9.md`** — the canonical rebuild resume doc (the single source; re-read after any
   compaction). Has the "NEXT: S1.5" pointer.
3. **`notes/s1_5_v1_design.md`** (committed, sha 41e8090f) — the S1.5 design spec. **NOTE: its APN-routing
   mechanism is SUPERSEDED** (proven wrong this session). Its four-site re-key surface (S1→S2→S4/S6,
   S3/S5/S7/S8 inherit), gate discipline, held-queues, and the §7b SB9/lineage roadmap are still valid.
   Read it knowing the *routing* is replaced by label-consolidation, not APN.
4. **`scratch/2026-06-25/contested_set_measurement.md`** — THE measurement that sets the next step (8 clean
   / 6 phased / 22 city-silent; bottleneck = phase-consolidation, not harvest). **Most important for "what next".**
5. **`scratch/2026-06-25/state_inventory.md`** — current ground truth (harvester drained, S9 exists,
   contested correctly empty). **Read so you don't re-propose done work.**
6. **The probabilistic-model design** (`building_identity_probabilistic_model.md`, in /mnt/user-data/outputs
   or wherever John filed it) — a FULLER alternative (mint building_id + confidence from weighted signals).
   It's a real design but **the measurement showed it's NOT needed for the core fix** (grouping+labels
   suffices for the checkable cases). Keep as the scaling option; don't build it without John choosing it.
7. **CLAUDE.md** — the standing rules (two-agent workflow, gating discipline, oracle-only mirror, etc.).
8. **Live code only if building:** `build_s2.py` (the S2 chokepoint — read this session; the re-key is TWO
   coupled edits: load_spine smap + build_events STEP-2 grouping; and the CO-date fixes itself via
   per-building MAX once routing is correct). `build_s4.py`/`build_s6.py` bucket-joins (carry a coupled
   verdict-flip FLAG_S8→resolved, not a mechanical key-swap — still need a live read before editing).

---

## THE WORKFLOW (unchanged — respect it)
Two agents + John: **chat-Claude** (you) plans, fact-checks, writes "FOR CC" prompts — **never edits the
repo**. **CC** (Claude Code) does all filesystem/DB/git ops. **John** owns ALL irreversible ops (writes,
commits to public, pushes). Discipline every stage: snapshot-refuse-to-clobber → preview → ENFORCED gate →
STOP for John → guarded write → fresh-connection fingerprint → idempotency. **Verify-a-zero / verify-the-
count against the LIVE DB.** CKAN/city mirror = ORACLE only, never a source. Surface city differences,
never tune toward them. One task type per CC prompt. **Search past chats before recommending an action.**

---

## CONCRETE NEXT STEP (if John says go)
1. **Resolve the open question first:** is label/phase parsing reliable? Have CC profile the WorkDescription
   text across the 6 phased + the 8 clean cases — what label/phase vocabulary actually appears
   ("North/South Building", "Phase I/II", "Bldg A", "Building 1"), how consistently, how parseable. This is
   a READ-ONLY reliability check, the precondition for trusting label-consolidation as the resolver.
2. **Then** design the resolver: master-permit grouping + phase-consolidation-by-label → check the ~14
   granular vs `s9_city_building_breakout` → only THEN consider harvest as optional corroboration.
3. Build it as the additive `s1_5` stage (materialize building_id → {permit-families} routing so S2
   CONSUMES it, never re-derives — per the design spec's anti-drift note), gated, STOP-for-John before any write.

**Do not start by building. Start by reading the five docs above and confirming the state with John.**
