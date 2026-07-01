# v4 curriculum: ALIGNMENT, not rebuild (2026-07-01, preliminary verdict)

**Status:** verdict captured before the deep JN2/JN3/JN6b read (see "To confirm"). Anchors spot-checked
this pass, not full-read.

## Verdict
The v4 curriculum question is **ALIGNMENT, not rebuild.** The existing `notebooks/curriculum/` (JN0–JN6b)
already teaches the behavioral approach; it needs to be brought current + one identity upgrade, not rewritten.

## Why it's alignment (the curriculum already made the entity→behavior turn — for STAGE)
- **JN4 (`JN4_events_stage.ipynb`) already teaches the core lesson: "derive the stage, don't assert it"** —
  builds dated events from structured date columns, derives stage (completed/permitted/pipeline) purely from
  DATES, never from a status string. It even teaches from the **real failure** (the 14-building migration bug:
  'completed' asserted from a v1 status string with no event behind it). *(Anchor confirmed: JN4 contains
  "derive the stage / don't assert.")*
- It **imports the REAL production functions** (`is_housing`, `net_units`, `normalize_address`,
  `extract_master_permit`) — not teaching copies.
- **So the curriculum is NOT a failed v2-entity-identification course.** It made the behavioral turn for stage.

## The actual gap — the curriculum is ONE conceptual generation behind the v4 spine
1. **Identity discriminator is address, not permit-family.** JN2 (`JN2_address_key.ipynb`) / JN3 group buildings
   by `normalize_address` (address = building identity). This session's **building-identity layer established
   address/APN is the WRONG discriminator** — buildings are **permit-family-keyed**, address a low-weight
   corroborator. So JN2/JN3 teach an identity model v4 superseded. *(Anchor: JN2's filename is literally
   "address_key.")*
2. **Numbers are v2/v3-era** (e.g. 951/340/94 stage distribution), **not v4** (82,923 events, 3,676 CO
   reconciliation).
3. **It rebuilds its own spine inline** (re-runs JN1–JN3) rather than **reading the v4 event-stream**.

## The opportunity — turn the gap into the central teaching device
The **address-key-as-identity should become the DELIBERATELY-PLANTED LIMITATION** the student later
rediscovers. **JN6b already does "rediscover the limitation you planted earlier."** Teach the student John's
REAL path: **address key → hit the wall (same building, 3 permits; phased records) → earn the permit-family /
event-stream reframe.** The curriculum's one-generation-behind status becomes its pedagogy, not its flaw —
the student re-lives the building-identity turn this project actually made.

## Verdict, actionable
**ALIGN** — (a) bring data/spine current (read the v4 event-stream; v4 numbers); (b) upgrade identity from
address → permit-family — **AND reframe address-key as the planted failure** the student rediscovers.
**NOT a rebuild.**

## To confirm (deep read, next)
- **JN2/JN3:** does JN3 actually group by `normalize_address`? (confirms gap #1's exact locus)
- **JN6b:** is the already-planted limitation *building-identity-related*, or something else? (determines
  whether the reframe reuses JN6b's existing planted-limitation slot or adds one)
- Note: active rewrite prototypes already exist in `scratch/jn{2,3,4,6b}_rewrite/` — check whether they've
  begun this alignment.
