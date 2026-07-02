# The +147 harvest — independent grounding of the held under-count (findings)

**Date:** 2026-07-02 · **Who:** CC (harvester + R2 extraction), per the JN-H map · **Status:** READ-ONLY
findings — no DB write performed; the proposed write below awaits John's gate.

**The held set (JN-E §7 / `corrections/v4/held_items.json`):** three phased-multifamily completions the
city credits (69/55/23) that our WorkDescriptions cannot size. Counting any of them requires the
**building's own documents** — the city APR was only ever the enumerator (oracle-not-source).

## Verdicts

### ✅ B2021-03302 — 2352 Shattuck (South) — **69 GROUNDED**
- **Source:** the architect's tabulation sheet **A.08** ("Proposed Project — Logan Park", Niles Bolton
  Associates / Johnson Lyman), in the **proj179 plan set already in R2**:
  `architect_plans/proj179_2352-shattuck_2019-08-26.pdf` (v2 `documents` id **2138**), page 9.
- **Content:** PHASE II UNIT MIX: 21×1BR + 42×2BR + 6×3BR = **TOTAL UNIT COUNT 69** (123 bedrooms,
  246 beds). The permit's own WorkDescription confirms it is "Phase II of South Building" at 2352 Shattuck.
- **Independence:** count read from document CONTENT; matches the city's 69 but derived without it.
- **⚠ flagged divergence (does not affect this permit):** this sheet shows Phase I (North) = **135** units
  where the June-28 investigation notes said North=168 (168+69=237). North's count is grounded elsewhere
  (its permits carry counts); the divergence is recorded per the doc-content-over-notes rule.

### 🔶 B2018-03422 — 2501-09 Haste ("El Jardin") — CITY'S 55 CONTRADICTED by the building's own record
- **Sources harvested this session (Accela Planning records, anonymous, live-session downloads):**
  - `ZP2018-0091` → **ZAB Staff Report 2018-07-12** + Revised Findings & Conditions (in
    `scratch/2026-07-02/harvest147/`): the project is a **GROUP LIVING ACCOMMODATION** — land-use table
    reads "**dwelling units 0 → 0 (no change)**; group living accommodations → **254** persons"; the 2018
    modification "adds 16 beds … for a total of 254"; a **resident-manager 2-bedroom dwelling** is required
    (condition 12-13) — the exact convention shape of C2-T2's B2021-04949 (40 sleeping + 1 manager = 41).
  - `UP2012-0012` (the parent use permit) → **2016-11-01 RESUB_PLANS** (Jarvis Architects, sheet A0
    "Room Summary REVISED"): **193 rooms / 298 beds** (West 108/108 + East 85/190).
- **The finding:** the city's Table A2 credit of **55 units** matches NOTHING in the building's own record —
  not dwellings (0), not rooms (193), not beds (254 approved / 298 in the 2016 resub). The under-count
  item is therefore **not a simple missing count**: it is a **convention conflict + a possible city-side
  mis-enumeration**. Counting El Jardin under OUR convention (sleeping rooms, convention-flagged) would be
  ~193+manager — grossly different from the city's 55.
- **Disposition: STAYS HELD**, basis upgraded from "no document" to "documents in hand, convention
  adjudication required" — John's call on the GLA counting convention (and whether the city's 55 belongs in
  the ~−150 contested-direction queue instead of the under-count).
- **Internal doc-chain divergences flagged:** 2012 approval → 238 beds; 2016 resub → 298 beds/193 rooms;
  2018 ZAB mod → 254 beds. The 2018 approval is latest-authoritative for beds.

### 🔴 B2016-05139 — 2740 San Pablo — NO DIGITAL DOCUMENTS EXIST (consistent, post-retry)
- Checked: the Building master grid (**empty**), all four REV/DEF sub-record grids (**empty**), the
  Planning-side APN search (only `UP2006-0119`, whose grid is **empty** — paper-era record), and address
  searches incl. the 2730-2750 range (only an unrelated 2023 record).
- Per the harvester rule this is a REAL absence finding for the digital channel: **Accela holds no
  documents for this building.** Routes that remain: a CIC/manual city-records request (CPRA for the
  approved plans), or the building **stays held at 23**.

## Reconciliation impact (proposed, NOT applied)
- Grounding B2021-03302 at 69 supports a **+69** correction (gated write: `new_unit`, `net_units=69`,
  `basis_note=source_document_id 2138 / plan-set A.08 Phase II unit mix`), moving the headline
  **−346 → −277**, and `held_items.json` updated with resolution provenance (the calibration-edit path
  `assert_held` prescribes). **Snapshot → preview → STOP-for-John → guarded write** applies.
- B2018-03422 (55) and B2016-05139 (23) remain HELD; the Haste entry's reason should be updated to the
  convention-conflict basis above (a calibration edit, also gated on John).

## Method notes (fed back to JN-H)
1. **The attachment widget is CONFIRMED module-agnostic** (the JN-H §3 open question): it ran on Building
   records fine — their grids were simply empty.
2. **NEW ROUTING RULE: architect/entitlement documents live on the PLANNING records** (ZP/UP), not the
   B-permit — true for proj179 (ZP2018-0135) and for El Jardin (ZP2018-0091/UP2012-0012). Route
   document harvests Planning-first; use the B-permit only for inspections/status.
3. **Discovery paths that worked:** permit# search (Building + Planning); address search
   (`txtGSNumber_ChildControl0` + `txtGSStreetName`); **APN search** (`txtGSParcelNo`, format
   `054 174402500`) — the APN route found what address search missed.
4. **OCR discipline held:** text-layer-first (free), page-targeted rendering (2 of 36 total pages rendered
   across two plan sets), structured-forms-before-plansets (the 216KB ZAB report beat the 24MB plan set).
   Note Berkeley staff-report PDFs have letter-fragmented text layers — whitespace-squash before regex.
5. **Empty-grid memos (never re-check):** B2018-03422 master + subs; B2016-05139 master + 4 subs;
   UP2006-0119.

## APPLIED (same day — John's go)
The +69 was applied via the RESOLUTION PATH, not a one-shot: `corrections/v4/grounded_counts.csv`
(the adjudication ledger — also the anti-re-derivation memory) + `stage_methods.apply_grounded_counts`
(refuses still-held permits; never overwrites a count; promotes the FINALED event only) + the
`held_items.json` resolution entry. **Write trace:** snapshot `keep_snapshot_2026-07-02_pre-grounded69.db`
(integrity ok, size-matched) → guarded write rowcount==1 → fresh-conn verify: B2021-03302 finaled =
new_unit/master/69 with document provenance in basis_note; **CO 3,676 → 3,745; BP 3,945 and events
82,923 UNCHANGED**. New baseline APPENDED: `reconciliation_baseline_2026-07-02.json` (co 3,745,
gap −277, sha b67f2a597e3dcea0; ledger gained the grounded_counts step). JN-E regenerated (gate PASS);
JN-F gained §5b; **from-raw chain re-validated: rebuild == live == baseline at 3,745, completion-set
0 diffs.** Held under-side is now **+78** (El Jardin convention-conflict + San Pablo no-docs).
Reverse: restore the snapshot, or delete the ledger row + re-demote (the write is a single event's
classification).

## NUMBERUNITS STAGE-1 PASS (same day — John approved the rule with guards)
The structured `NumberUnits` field (present in our raw payloads all along) was swept over the 71
ambiguous finaled events carrying NumberUnits≥3 (2018-2025). Partition record:
`data/audit/numberunits_stage1_2026-07-02.csv`. **Validation:** 14/15 C2 prose-recovered counts agree
with the field; the one divergence (B2018-05067: 22 vs 24) is the field counting DWELLINGS and
excluding live-works — semantics confirmed. **Verdict on the rule:** triage signal + corroborator for
NEW CONSTRUCTION; never an auto-count (for alterations the field means building size — 31 rejects and
2 false-positive "strict proposes" prove it). Stage-2 (classifier lift) DECLINED on this evidence.

**Two genuine recoveries applied via the ledger (+170; CO 3,745 → 3,915; gap −277 → −107):**
- **B2019-05574 — Logan Park NORTH — 135** (plan set A.08 North unit-mix 135 + NumberUnits=135;
  supersedes the stale "North=168" note). Both North phases sat ambiguous/0 — the building was entirely
  uncounted. **This was the bulk of the former ~−150 residual.**
- **B2015-02998 — Acheson Commons Bldg B — 35** (its own WorkDescription "35 NEW RES UNIT" — the C2
  method's blind spot: the role was ambiguous, outside C2's new_unit filter — + NumberUnits=35;
  siblings C=65/D=68 counted with matching NumberUnits).

**Phase-subsidiary adjudications (uncounted BY DESIGN — recorded so no future pass re-proposes):**
B2019-05575 (Logan South Phase I; the counted completion is B2021-03302), B2019-03704 (Logan North
Phase I; counted completion is B2019-05574), B2018-02244 + B2018-02708 (El Jardin excavation/foundation,
each carrying NumberUnits=55 — would have triple-counted the contested 55).

**Write trace:** snapshot `keep_snapshot_2026-07-02_pre-grounded170.db` → apply_grounded_counts
(3 rows, 2 promoted, +69 idempotently verified) → fresh-conn CO 3,915 / BP 3,945 / events 82,923 →
baseline `reconciliation_baseline_2026-07-02b.json` APPENDED (gap −107, sha c2a1d0543e225c14; residual
re-based ~−29) → JN-E regenerated (gate PASS) → from-raw chain re-validated.

## EL JARDIN RESOLVED (same day — CIC session settled the convention)
**Operator evidence (Greystar, "Enclave Apartments"): the quarters have IN-UNIT KITCHENS** — 55 shared
apartments (12 layouts, 2-7 students each), rented by the bed. So the units are **co-living DWELLING
units**, not sleeping rooms — and the apparent 55-vs-193-vs-254 conflict was **three AXES of one
building: 55 apartments / ~193 bedrooms / 254 beds.** The "possible city-side mis-enumeration"
hypothesis is **RETRACTED — the city's 55 was right**; the zoning GLA label described the USE, not the
physical configuration. NOT UC-exempt (city-permitted; the UC affiliation is a financial-aid
classification). Count grounded from CPRA `NumberUnits=55` (permit-stated), convention-flagged
`co_living_apartments`; operator material used ONLY to settle the convention, per the CIC brief.
**Write trace:** snapshot `keep_snapshot_2026-07-02_pre-grounded55.db` → apply_grounded_counts (4 rows,
1 promoted, 3 idempotently verified) → CO **3,915 → 3,970**; baseline `2026-07-02c` APPENDED
(gap **−52**, sha 72fc7b54bc42800b); JN-E regenerated (gate PASS). **Held under-side now +23**
(San Pablo only). Remaining unexplained: −52 + 23 = **~−29** (unchanged — El Jardin was never part of it).
