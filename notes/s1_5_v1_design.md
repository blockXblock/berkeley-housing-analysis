# S1.5 v1 — Building-identity split (DESIGN SPEC, design-only; nothing runs)

**Status:** design for review → then a gated build. Chat-Claude produced this; CC builds from it
under the standing gating discipline. **Verify every count against the LIVE v3 before relying on it.**

**One-line summary:** enable the validated `split_multibuilding` rule (splits exactly **1** building —
2352 Shattuck/Logan Park — on the current spine), widen `_RB_INCL` by one line, re-key the **three**
downstream sites that re-derive identity from the address-tuple (S2, S4, S6) so the split doesn't
re-collapse, re-run the pipeline S1→S9, and surface everything the rule does **not** resolve into
named held-queues. **This is the largest write in the project: it re-executes the gated DAG from S1
onward with new building grain.** Treat accordingly — stage-by-stage gates, each preview showing only
the localized delta.

---

## 1. SCOPE — what v1 does and does NOT do

### v1 DOES
1. **Enable the split rule.** Uncomment `split_multibuilding` so 2352 Shattuck splits into North
   (135u, APN …018-05) + South (69u, APN …041-00). Spine **1385 → 1386** (+1 building).
2. **Widen `_RB_INCL`** (one line) to include the housing nouns the include-list currently lacks
   (`duplex|triplex|fourplex|town ?house|town ?home|cottage|sfd|single ?family|accessory dwelling`).
3. **Re-key the 3 downstream sites** (S2 chokepoint, S4 + S6 bucket-joins) from address-tuple to
   `building_id`, so a split building stays split through S2–S8.
4. **Re-run the pipeline S1→S9** with the new grain, each stage gated; update gate checkpoints.
5. **Create named held-queue tables** for everything the rule doesn't resolve (§5).

### v1 does NOT (each is named future work, §7)
- **Does NOT split the 35 single-unit-per-building clusters** (out of the rule's ≥2-units-per-APN
  scope — they need a *different* future rule, not this one).
- **Does NOT split 1173 Hearst** (a lineage lot-split + MAX-collapse; held, see §5).
- **Does NOT relax `distinct_years`** (the conservative dual-axis test stays; no current case needs it).
- **Does NOT build lineage-aware splitting** (the SB 9 / lot-split future work; §7).
- **Does NOT fix the general MAX-vs-SUM collapse** beyond the one case the rule handles.

**The honest scope statement:** *v1 resolves 1 of the 36 collapse developments (2352 Shattuck),
proves the re-key machinery on that one validated case, and surfaces the other 35 + 1173 in named
queues that say why each is held and what would resolve it. It is a minimal, safe first deployment
of a pipeline-wide re-key — not the building-identity problem solved.*

---

## 2. THE FOUR EDIT SITES (the re-key surface, from the live-code keying inventory)

> ⚠ **Verify against live code before editing.** This spec is written against CC's keying digest
> (`scratch/2026-06-25/s1.5_rekey_keying_surface.md`) + `build_s1.py`/`build_s0.py`/`s0_keys.py` read
> directly. The S2 `load_spine` smap (≈L79) and the S4/S6 bucket-joins are the load-bearing spots —
> CC must re-read them in the live tree and confirm the shape before implementing.

### Site 1 — S1 (`build_s1.py`): enable split + widen include
- **Uncomment** `# spine = split_multibuilding(spine)` (the validated rule).
- **Widen `_RB_INCL`** (one regex line) to add the housing nouns above.
- **Decision for the build (recommend additive — now strengthened by the S2 routing finding):** the
  split stage should **materialize the `building_id → {permits, canon_apns}` routing** it computes (write
  `s1_5_projects` + a permit-assignment table), so S2 *consumes* the routing rather than re-deriving it
  (see Site 2 — re-derivation risks drift from the split's own assignment). Option (b): a thin `s1_5`
  step reads `s1_projects`, applies `split_multibuilding`, writes `s1_5_projects` **plus the explicit
  permit→building_id map**, and S2–S8 re-point to it. This **preserves S1 byte-stable** AND eliminates
  the routing-drift risk. Option (a) (modify S1 in place) re-validates S1's gate and still leaves S2 to
  re-derive routing — **less safe**. **Recommend (b).**

### Site 2 — S2 (`build_s2.py`): THE chokepoint — re-key permit→building (TWO coupled edits)
> **Read against the LIVE `build_s2.py` (done).** The re-key is **two coupled changes**, not one — fix
> either alone and the grouping re-collapses what the map separates.

- **Current — the collision (confirmed in code):** `load_spine()` builds `smap` as a **dict
  comprehension** `{(number,street,stype) → building_id}`. After a split, the two Shattuck
  `building_id`s share one 3-tuple → **the second silently overwrites the first** (one split building
  vanishes from the map). Then `build_events()` STEP 2 groups every permit row by
  `key=(k.number,k.street,k.stype)` and looks up `smap[key]` **once per group** → both buildings'
  permits land on the one surviving `building_id`. That is the re-collapse, mechanically.

- **Fix — BOTH must change together:**
  1. **`load_spine`** must stop collapsing — expose APN-aware identity (e.g. `smap` maps the 3-tuple →
     a *list* of `(building_id, canon_apns)`, or a 4-tuple `(number,street,stype,apn) → building_id` for
     split buildings with a 3-tuple fallback for un-split).
  2. **`build_events` STEP-2 grouping** must route each permit to its sub-building **by the permit's
     canon-APN** (available as `r.ParcelNumber → canonicalize_apn`), matching whatever `load_spine` now
     exposes. **If only `load_spine` is fixed and the grouping key stays the 3-tuple, the grouping
     re-merges them downstream of the map** — they are coupled.

- **⚠ Orphan-routing must match the split EXACTLY.** `split_multibuilding` routes a permit to its
  APN's sub-building, but permits whose APN is *not* a real-build APN go to `big` (the largest
  sub-building). S2's re-keyed grouping **must replicate this identical routing** — otherwise a
  building's *units* (from the split) and its *events* (from S2) attach to different buildings. **This
  is the strongest argument for the additive-stage approach (Site 1, option b):** have the split stage
  **materialize** the `building_id → {permits}` (and `→ {canon_apns}`) routing it computes, and have S2
  **consume that mapping** rather than re-deriving the routing. Re-derivation risks drift from the
  split; consumption cannot drift. **Recommend: materialize the routing in S1.5, S2 reads it.**

- **The CO-year bug fixes itself through this routing (the mechanism).** S2's `co_issued` =
  `max(b['final'])` over the building's master permits. Collapsed 2352's `max` picks the *latest* final
  across BOTH buildings → South's 2023 stamped on North's 135u (the bug). **Once permits route correctly,
  North's group → `max` = its real 2022 CO; South's group → 2023.** No separate CO fix needed — but it
  is **contingent on correct routing**, which is exactly why the routing must not drift (above).
- **Un-split buildings are unaffected** (one building per bucket → APN routing never triggers).

### Site 3 — S4 (`build_s4.py`): re-key the unit-reconcile joins
- **Current:** `s1_s4_unit_reconcile` / `s4_unit_reconcile_resolved` join on `bucket`. After a split,
  **`bucket` is no longer 1:1 with a building.**
- **Fix:** join on `building_id` instead of `bucket`.

### Site 4 — S6 (`build_s6.py`): re-key the verdict-read
- **Current:** reads S4 verdicts keyed by `bucket` (≈L35).
- **Fix:** read by `building_id`.

### Inherit-for-free (no edit): S3, S5, S7, S8, S9
- All already key on `building_id` (FK-keyed) and follow automatically once S1+S2 are correct.
- **S9 already keys on `building_id`** (`GROUP BY building_id`) → the scorecard re-reflects the split
  on re-run with no code change (the iterated scorecard is free).

---

## 3. `_RB_INCL` WIDENING — interaction with 1173 (verify in preview)

The widening makes 1173 Hearst's parent duplexes pass `_is_realbuild`, giving 1173 **2 realbuild APNs**
(013-00 @ 2u, 088-00 @ 2u) — so it becomes split-**eligible**. **But it must STILL NOT split**, because:
- `distinct_units` = **False** (both 2u), and
- `distinct_years` = **False** (013 CO-year {2023}; child 088 has no CO → year set not distinct).

→ **The preview gate MUST assert 1173 stays HELD (not split) after the widening.** This is the safety
check on the widening. If 1173 ever flips to a split, STOP — the conservative test has been defeated.

**Net effect of the widening:** split *count* stays **1** (only 2352). 1173 moves from "invisible to
the rule (1 realbuild APN)" to "seen but held (2 realbuild APNs, blocked by the dual-axis test)" — it
becomes the **first real member of the same-units/same-year blind-spot queue** (previously empty). That
is the *correct, more honest* state, and it gives the future `distinct_years`/CO-sub-model work a
concrete first test case.

---

## 4. GATE CHECKPOINT SHIFTS (each `test_sN_gate.py` updated; verify deltas in preview)

The split is localized to 2352 + the +1 building. Every other row should be **unchanged** — the gates
exist to prove exactly that (any stage whose preview shows more than the 2352-localized delta is a bug).

| stage | checkpoint (current) | expected after S1.5 | nature of change |
|---|---|---|---|
| S1 | `s1_projects` 1385 | **1386** | +1 building (2352 → North+South) |
| S2 | `s2_events` 2236 | **2236** (re-distributed) | 2352's events split across 2 building_ids; **count likely stable, grouping changes** — verify |
| S3 | `s3_stage` 1385 / completed 951 | **1386** / completed **952** | South building gets its own completed stage |
| S4 | `s4_units` 1385 | **1386** | North 135 + South 69 as 2 rows (was 1 collapsed) |
| S4 | `s4_unit_reconcile_resolved` 6 (incl. 2352 FLAG_S8) | **5 or re-typed** | 2352's `FLAG_S8` may resolve once split — verify its disposition |
| S5 | `s5_affordability` 1406 | **1407** (+1 needs_acquisition) | South building's affordability row |
| S6 | `s6_confidence` 5549 | **+fact rows** for the new building | per-fact confidence for South |
| S7 | `s7_cycle` 2236 | **2236** (re-distributed) | North's CO → 2022, South's CO → 2023 (the bug fix); verify the year reassignment |
| S8 | `s8_reconciliation` 90; `multi_building_development` 1 (2352) | **2352 finding resolves/re-types** | the held multi-building finding for 2352 is now *resolved by split* — update its disposition |
| S9 | scorecard, breakout, caveats | **2352 line corrects**: 135@2022 + 69@2023 | the iterated scorecard (free; S9 re-reads building_id) |

**The headline scorecard change:** 2352 moves from the collapsed `135@2023` Frankenstein to the correct
`North 135@2022 + South 69@2023`. This shifts the **2022 and 2023** per-year deltas (recall the current
scorecard's 2022 −149 / 2023 +129 swing is *the Logan-Park-class artifact* — this split is what corrects
part of it). **The net +288 may move slightly**; whatever it becomes is the *more correct* number.
Re-validate against `s9_city_building_breakout` (the answer key: city reports exactly North 135@2022 +
South 69@2023 — our split should now MATCH it).

---

## 5. HELD QUEUES (named tables — surface, never silently drop)

### `s1_5_single_unit_clusters` — the 35 out-of-scope cases
- The 35 left-collapsed developments (cottage courts / same-parcel single-unit clusters: 1444/1446 5th,
  the Haskells, 908 Cedar, 1516 Carleton, etc.).
- **Why held:** each building is a *single* unit on its APN → fails the rule's ≥2-units-per-APN gate.
  These are out of *this* rule's scope, not a conservative miss.
- **What resolves them:** a future per-APN-single-dwelling split rule (§7). Until then, the development
  stays collapsed and **flagged** (already in `s9_identity_caveat` as pending).

### `s1_5_lineage_review` — 1173 Hearst (one entry, one honest line)
- **1173 Hearst = a building-identity case:** genuinely ~3 buildings / ~6 units, recorded as 2u, via
  **MAX-collapse** of the two 013-00 duplexes + a **lineage lot-split** (parent 057-2086-013-00 →
  child 057-2086-088-00, **candidate** lineage).
- **Why held:** (a) the MAX-collapse is the general building-identity problem this rule's conservative
  test doesn't resolve here (same units, child has no CO year); (b) the lineage is candidate-not-fact, so
  lineage-aware splitting can't run on it yet.
- **What resolves it:** confirmed parcel lineage + lineage-aware splitting (§7) + the CO-sub-model
  (`distinct_years` relaxation). 1173 is the **first test case** for that future work.

### Documented design constraint (not a table) — the phantom-parent hazard
- The rule is **lineage-blind**: it peer-groups APNs with no parent→child notion. A defunct *parent*
  APN whose pre-split permit is itself `_is_realbuild` ≥2u would be peer-grouped as a **phantom
  building**. **Not present on the current spine** (the `_is_realbuild` filter happens to drop the
  defunct parents), but SB 9 churn makes it increasingly likely.
- **Constraint for the future lineage-aware rule:** it MUST drop defunct parent APNs (collapse
  parent→child lineage) before grouping, never peer-group them.

### Note on the one split (honest mechanism)
- **2352 Shattuck splits correctly, validated against the city's per-building figures** (North 135@2022
  + South 69@2023, = `s9_city_building_breakout`). **NOTE:** the rule reached this via lineage-blind APN
  peer-grouping that *coincidentally* matches the parent→child reality here. **This is NOT evidence the
  rule handles lineage** — 1173 (held) shows the same blindness producing a wrong result. The correct
  mechanism (lineage-aware splitting on confirmed lineage) is future work.

---

## 6. EXECUTION & GATING (the discipline — this is the big write)

**S1.5 = re-execute the gated DAG from S1 with the identity fix.** Enabling the split in S1 invalidates
the downstream stages (idempotent DROP+rebuild reading the new spine), so S2→S9 re-run. Each stage:

```
snapshot_v3('<stage>')  (refuse-to-clobber)
  → PREVIEW (read-only): show the delta vs current — EXPECT only the 2352-localized change + the +1 building
  → ENFORCED gate: assert no UNEXPECTED change (any stage showing more than the expected delta = STOP)
  → STOP for John  → guarded write  → fresh-connection fingerprint  → idempotency (--no-snapshot)
```

- **One snapshot per stage** with a distinct tag (`pre-s1.5-s2`, … so each rollback point is preserved).
- **The preview is the safety net:** because the split is localized, every stage's preview should show a
  *small, explainable* delta. A stage that changes broadly is re-merging or mis-attaching — STOP.
- **Wiring guards** (fails-if-not-CALLED spy) stay green at every stage.
- **`disambiguate_distinct` reuse:** S2's APN-disambiguation should reuse the existing
  `disambiguate_distinct` / protected-pair machinery where applicable (anti-drift) — **but note its known
  shared-CO-date misfire** (1222 66th class); confirm it isn't exercised wrongly here (2352's two
  buildings have distinct CO years, so it's safe for this case).
- **John owns every write.** No autonomous chain — gate-by-gate.

**Acceptance gates before S1.5 is "done" (all must hold):**
1. Spine 1385→1386; **exactly** 2352 split; **0** other buildings split (zero false splits).
2. 1173 **split-eligible after widening but HELD** (not split) — the dual-axis test still blocks it.
3. North 135@2022 + South 69@2023 in `s7_cycle` (the CO-year bug fixed). **Mechanism: S2's per-building
   `max(final)` over correctly-routed permits — assert North's `co_issued` event date is 2022 and
   South's is 2023 specifically (not just "2 events"). This is the direct test that routing is correct.**
4. S9 scorecard's 2352 line **matches `s9_city_building_breakout`** (our split = the city's breakout).
5. Every other building's rows **unchanged** across S2–S8 (conservation — the localized-delta proof).
6. S2–S8 gates green with updated checkpoints; idempotency re-run reproduces (run A == run B).
7. The 3 held-queues populated and counted (35 / 1 / documented-constraint); 36-set still sums.
8. **`s1_5_meta.lineage_involved_buildings` emitted** — the running count of spine buildings involving a
   `parcel_lineage` APN (the SB 9 trigger gauge, §7b). Currently ~4; tracked every run.

---

## 7b. APN-SPLIT ROBUSTNESS ROADMAP (the SB 9 / middle-housing trajectory)

**Direct answer to "is v1 robust against future APN changes?": NO — v1 defers lineage-aware splitting
deliberately. But the architecture supports it, the blocker is explicit, and the first test case is
named.** This section makes that honestly visible rather than buried.

### Why this matters and grows
Middle-housing law (SB 9 and successors) explicitly enables **lot splits** — one parcel becomes two,
and new units are built on the children. In the permit feed this appears as **one development with
permits against multiple APNs across time** (the pre-split parent + the post-split children). This is
the *signature pattern* of the new housing era, and it will **increase in frequency**. A pipeline that
can't track parent→child APN lineage will progressively under- or mis-count exactly the housing the new
laws produce.

### What v1 has (the substrate — robustness is *possible*)
- **`building_id` = stable internal identity, decoupled from APN** (ADR-003). When a parcel splits and
  APNs change, the building's identity does not move. *This is the foundational requirement, and it's met.*
- **`parcel_lineage` exists** (27 parent→child pairs / 53 APNs) — the table that would drive lineage-aware
  grouping.
- **1173 Hearst is surfaced** in `s1_5_lineage_review` as the **named first test case**, with the
  phantom-parent hazard documented as a design constraint.

### What v1 lacks (the rule — robustness is *not built*)
- `split_multibuilding` is **lineage-blind**: it peer-groups APNs with no parent→child notion (confirmed
  empirically). It cannot correctly handle a lot-split; it either under-splits (1173) or, in a future
  case, could peer-group a defunct parent as a phantom building.

### The blocker (why v1 correctly does NOT build it)
**`parcel_lineage`'s pairs are CANDIDATES, not confirmed facts** (the standing rule: candidate until
confirmed vs a recorded county map). Building lineage-aware splitting on unconfirmed lineage would
violate "never build identity on a guess" — the project's core discipline. So lineage-aware splitting is
**blocked on lineage confirmation**, which is an off-disk **data-acquisition** task, not a coding task.

### The forced sequence
1. **v1 (now):** defer lineage; hold 1173; leave the hooks. *(this spec)*
2. **Lineage confirmation** *(prerequisite, off-disk):* confirm the `parcel_lineage` candidates against
   the recorded Alameda County parcel map → candidates become facts. **This is the real gate.**
3. **Lineage-aware split rule** *(the capability):* consume *confirmed* lineage; collapse parent→child;
   drop defunct parent APNs (the phantom-parent constraint); group children as the buildings the split
   created. **First test case: 1173 Hearst.** Keep single-sourced with `disambiguate_distinct` /
   `split_multibuilding` (don't fork the matching philosophy).

### The trigger metric (added to v1 — the running gauge)
**v1's gate emits a running count: how many spine buildings involve a `parcel_lineage` APN
(parent or child).** Currently ~4 of 36 collapse cases. **This number is the gauge of how urgent
lineage-aware splitting is becoming.** Re-emitted on every pipeline run, it converts "SB 9 will matter
someday" into a measured trend: when it crosses from a handful into tens, lineage-aware splitting moves
from "deferred" to "next." Surface it in `s1_5_meta` (e.g. `lineage_involved_buildings = N`) so the
trend is tracked, not rediscovered each session.

---


1. **Single-unit-cluster split rule** — a per-APN-single-dwelling identity rule for the 35 cottage-court
   / same-parcel clusters (the bulk of the 36). The biggest remaining building-identity piece.
2. **Lineage-aware splitting** (SB 9 / middle-housing driven) — **see §7b for the full roadmap, blocker,
   sequence, and trigger metric.** Summary: blocked on `parcel_lineage` confirmation (candidates→facts
   vs the county map); first test case 1173 Hearst; the gauge is the running `lineage_involved_buildings`
   count in `s1_5_meta`.
3. **CO-sub-model / `distinct_years` relaxation** — distinguish same-year distinct buildings (1222 66th
   class) via a richer CO model; fix `disambiguate_distinct`'s shared-CO-date misfire **and**
   `split_multibuilding`'s `distinct_years` requirement **together** (they share the philosophy — keep
   single-sourced).
4. **`_is_realbuild` prose-filter** — the widening fixes the include-list nouns; the prose include/exclude
   logic remains brittle (it reads `WorkDescription`). Lower priority (net_units is prose-blind, so the
   *spine units* are safe — confirmed), but worth a future audit.

---

## 8. WHAT THIS DESIGN ASSUMES / VERIFICATION DEBTS

- **S2's re-key is now designed against the LIVE `build_s2.py`** (read 2026-06-25): the `load_spine`
  smap collision + `build_events` STEP-2 grouping + the `max(final)` CO mechanism + the
  `split_multibuilding` orphan-routing-to-`big` are all confirmed in code. The remaining S2 debt is only
  the *implementation choice* (materialized routing — Site 1 option b), not a reading gap.
- **S4 and S6 bucket-joins** are designed against the keying digest, not a full read. Lower-risk than S2
  (the fix is a mechanical `bucket → building_id` join swap), but CC should read the live `s4`/`s6`
  bucket-join lines before editing — same discipline.
- **The checkpoint deltas** (§4) are predictions; the previews are the source of truth. Where a predicted
  count differs from the preview, the **preview wins** — investigate the difference, don't force the number.
- **`s2_events` and `s7_cycle` counts** are predicted *stable* (re-distribution, not addition) — verify;
  if they change, understand why before proceeding.
- **2352's `FLAG_S8` / `multi_building_development` disposition** (S4/S8) should *resolve* once split —
  confirm the finding re-types from `held_flagged` to `resolved_by_split` rather than lingering.
