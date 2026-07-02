# Berkeley Housing Pipeline — PROGRESS (current state)

**Purpose:** The live current-state snapshot. Read this first (after `CLAUDE.md`) at session start. Updated at the end of every gated step (see *State-update discipline* in `CLAUDE.md`). This file is canonical; auto-loaded memory is a hint, not ground truth — verify against the DB / `git log`.

---

## 2026-07-02 — ⭐ REPRODUCIBILITY GAP CLOSED — REVIEWED + COMMITTED (fef0539..2fd168d)
**Review (8-angle multi-agent + adversarial verify, 14 CONFIRMED findings, ALL FIXED before commit):**
the one-shot→method lift had weakened every rc==1 halt to `rc<=1` (typo'd calibration would silently
no-op) → now **verify-or-halt**; C2 checksums (15/907 + exact T2 values) re-pinned via
`corrections/v4/calibration_checksums.json`; HELD_147/B2020-03895 externalized to `held_items.json`
(calibration, never code); C3-tail now PROTECT-verifies **before** demoting + all methods rollback-on-
failure; dedup: NULL-payload differ detection, keeper-survival guard (the old one was provably vacuous),
CO-neutrality assert, unmatched-hold HALT, temp-TABLE single pass; C2→C-multifamily order coupling now
ENFORCED (bump halts if run out of order); classifier-hash recipe lifted to
`housing_rules.permit_role.classifier_hash()` (== live's 743edfb626399efc); **JN-C latent bugs fixed**
(_norm NameError silently degraded the harvest-queue R2 bridge to all-'unknown'; output path broke
under parameterization); JN-F gained a **§7b structural gate vs live** (events + completion-set).
**Re-validated post-hardening:** fresh chain gate PASS · JN-F idempotent re-run PASS (exercises the
rc==0 verify paths) · negative tests PASS (typo'd permit + order violation both HALT) · smoke + 16+9.
**Commits:** `fef0539` (classifier_hash) · `98f4d6a` (calibration files) · `ea4fbfe` (stage_methods +
JN-B/JN-F) · `f54ee9d` (JN-C param + fixes) · `2fd168d` (gitignore). Follow-ups (deferred, small):
JN-E imports stage_methods metrics (drift risk noted); consolidate the 4 inline live-DB guards; ro()
proliferation. All notebook chain state below stands.
**The from-raw pipeline is now real: `raw xlsx → JN-A → JN-B (dedup) → JN-C (classify) → JN-F
(corrections)` reproduces the corrected live state EXACTLY** — validated twice (methods, then the
notebook chain): CO 3,676 ✓ · BP 3,945 ✓ · events 82,923 == live ✓ · **per-permit counted-completion
set == live, 0 diffs both directions** ✓ · pre-corrections CO 3,066 independently reproduced ✓.
Chain runtime ~18s (nbclient, `/opt/miniconda3/envs/jupyter_env/bin/python` — the notebook toolchain env).
- **NEW (uncommitted, for John's review):** `scripts/v4/stage_methods.py` (THE importable stage-method
  module — dedup / classify-recipe / 5 correction methods / held-asserts; aa6ded0 lift discipline);
  `scripts/v4/build_jn_{b,f}.py` → `notebooks/v4/JN-B_event_dedup.ipynb` + `JN-F_corrections.ipynb`
  (text-sandwiched, viz'd, baseline-gated, hold-not-apply encoded); calibration
  `corrections/v4/event_dedup_holds.json` (tier-2 holds externalized — the B2014-05786 hold is what
  makes a rebuild land event-identical to live).
- **CHANGED (uncommitted):** `build_jn_c.py` — JN-C target PARAMETERIZED (env `JN_C_DB_PATH`, default
  = the JN-A throwaway) + LIVE-DB REFUSAL guard (the documented wipe hazard, same pattern as JN-A
  d3a3077); its role-dist viz now reads the parameterized target. `JN-C_classify.ipynb` regenerated.
- **Validation harness (scratch, stays):** `scratch/2026-07-02/rebuild_from_raw_driver.py` (methods)
  + `notebook_chain_driver.py` (the 4-notebook chain) + `v4_stage_methods.py` (superseded by the
  promoted `scripts/v4/stage_methods.py`).
- **Hazard status shrunk:** JN-A/JN-B/JN-C/JN-F all now default to a throwaway rebuild target and
  REFUSE the live DB — the "never run JN-A/JN-C against live" hazard is enforced by code, not memory.
- **HELD unchanged:** +147 (Accela-blocked) · C1-phantom (never-apply) · B2020-03895 · JN-B tier-2/3.
- **Next:** John review → commit; then the +147 Accela harvest or curriculum deep-read.

## 2026-07-02 — dev↔main RECONCILED + assessed-value DEPLOYED
- **dev pushed** through the triage commits; then **`origin/main` merged into dev (`a33681c`)** — the 11
  "main-only" curriculum commits were double-committed duplicates of dev commits (trees verified identical);
  the only genuinely main-only content was `docs/data-science-curriculum.html` + the index card (already live).
  The handover's "curriculum is MAIN-ONLY" was STALE. ⚠ the merge-commit message says "content no-op" —
  slightly wrong (those 2 files came in); recorded here, message left unamended.
- **dev → main merged (fast-forward to `a33681c`) + pushed = the ASSESSED-VALUE DEPLOY** (John's go, CC ran it).
  Deploy surface verified pre-merge: only `explorer.{html,js}` + regenerated `explorer_data.js`/`_v2_working.js`
  + inert audit/methodology markdown. **No cherry-pick needed** (supersedes the old 3-commit cherry-pick plan).
- **🟢 OPS FACT (John, this session): NO Cloudflare purge is ever needed** — Cloudflare picks up the GitHub
  change automatically. The "purge explorer files" step in older handovers is obsolete. Note: origin serves
  `cache-control: max-age=14400`, so propagation can take minutes–hours; verify with a marker grep
  (`curl -s https://berkeleybuild.com/explorer.js | grep -c assessedCoverage`), don't purge.
- **main == dev == `a33681c`** at deploy time; branches fully unified going forward. Preference: deploy
  small/feature-scoped main merges from now on, not 100-commit batches.
- **⚠ DEPLOY NOT LIVE YET — GitHub Pages deployment backend WEDGED (server-side).** 5 deploy attempts
  (4 legacy + 1 workflow) all die identically: build OK, artifact OK (106MB), deployment created, then
  `deployment_queued` forever → 10-min timeout. NOT our content (diff is inert text + explorer files;
  branch policy fine; env protection fine). **Switched Pages to WORKFLOW build type** (`4b5b649`,
  `.github/workflows/pages.yml`, static verbatim docs/ upload — behavior-identical, no Jekyll).
  Site meanwhile serves the June-23 build (stale but healthy). **6 failures total** — incl. after
  explicitly CANCELLING the two zombie deployments (both returned the undocumented EMPTY status `""`
  from GET /pages/deployments/{sha} — strong server-side-limbo evidence for the ticket). All our-side
  levers exhausted (content/artifact/branch-policy/env-protection/pipeline-switch/zombie-cancel).
  **RESOLVED-CAUSE: GitHub confirmed Pages DEGRADED (status yellow) 2026-07-02 9:54 AM PT** — their
  incident, not us; NO support ticket needed. Auto-retry armed (background: poll status → on green,
  `gh workflow run "Deploy Pages"` → verify propagation).
  Overnight self-heal retry: `gh workflow run "Deploy Pages"` then
  `curl -s https://berkeleybuild.com/explorer.js | grep -c assessedCoverage` (>0 = live).

## 2026-07-01 — working-tree triage (CC session)
- **🔴 FIXED: HEAD was import-broken** — `52c79b4` committed `__init__.py`/`test_s7_gate.py` consuming
  `rhna_credit_cycle` but never the function's source; every commit June-28→July-01 raised ImportError
  on `import housing_rules` at clean checkout. Source committed `de5da7e` (smoke + 16+9 tests pass).
- **Housekeeping committed:** June-13 affordability-corrections rows (`85fb2bc`); shake APN-canon
  re-run outputs (`6f6eea6`); oracle-independence methodology doc (`4e238a4`); `permits_clean.{csv,parquet}`
  gitignored as derived cache (`52ff00e`); D6/D7 timestamp-only churn reverted. Tree clean.
- **CY2025 double-submission evidence preserved** (`35487ad`, `data/audit/hcd_ckan_snapshot_2026-06-16/`):
  the 2026-06-16 CKAN vintage (table_a2 CY2025 = 126 rows) vs the 2026-05-26 mirror (474) documents the
  city's double-submission + upstream dedup. John: current reporting is live-queryable from CKAN; the
  snapshots exist ONLY as evidence of the mistake. ⚠ When the mirror is next re-pulled, the JN-E city-side
  totals may move → append a new timestamped baseline, don't edit.

## Where we are (2026-06-27) — CLASSIFIER LIFTED · ADU BIJECTION · SCORER · APR SIZING

**▶ Read `notes/TECHNICAL_HANDOVER_2026-06-27.md` (on-disk truth) + chat-Claude's `HANDOVER_2026-06-27.md`
(strategy).** Today's arc, dev HEAD = **`aa6ded0`** (UNPUSHED; `dev` ahead of origin by 1).

**✅ CLASSIFIER LIFT (committed aa6ded0, tested).** The v4 `classify` + vocab + tests were lifted out of
the build_jn_c cell-string into **`scripts/housing_rules/permit_role.py`** (importable; `housing_rules.classify`).
`test_permit_role.py` = 16 vocab + 9 deflation anchors, **25/25 pass**. Behavior-identical proven at lift-time
(0 mismatches / 85,793 events); role dist UNCHANGED (alteration 64,739 · subsidiary 9,597 · ambiguous 7,403 ·
new_unit 2,964 · demolition 920 · non_housing 170). Consumers re-pointed (build_jn_c imports+renders;
build_jn_d imports; harden_relabel imports). Also fixed: `occurred_at`→`event_date`; build_jn_c `/home/claude`
output path. ⚠ the proof harness (`scratch/.../permit_role_identity_proof.py`) is now stale (notebook imports,
no longer defines) — durable re-verify = the 25 tests + the role-dist query.

**✅ ADU BIJECTION + 584 (verified, scratch).** JN-D engine (`scripts/v4/build_jn_d.py`, committed) — HCD-anchored
ADU bijection, **5 HARD asserts pass: 842 / 649 / 839(99.6% match) / 584 hardened / band 531-584**. The 584 =
description-corroborated ADUs the v4 ADU-FLAG missed — but ⚠ the v4 ROLE classifier did NOT miss them: all
584 are already `new_unit` with net_units set (442 finaled, ~457 already counted). So the "584 relabel" is a
PHANTOM, not a recall gap — see the corrected four-corrections note below. 3 genuinely missing from v4.

**✅ TWO-AXIS SCORER + 5 DECISIONS (prototype, NOT persisted).** Built two independent implementations
(JN `prototype_score_v2.py` + CC `_v2_cc.py`; reconciled ρ=0.90 adu / 0.85 new_housing), then the merged
**`prototype_score_v3.py` (current)**. Settled decisions: (D1) keep explicit medium band; (D2) weak-only
converts floor to LOW; (D3) pre-2017 statutory terms ('second unit' etc.) count only behind a creating-context
guard; (D4) regressions hold (strong-ADU+new_unit high/high, big buildings 23 low/1 high, bound adu≤new_housing
→ forbidden corner empty). Trunk = new_housing_conf (Imps oracle); branch = adu_conf (HCD+footprint oracles,
footprint positive-only ≥2 — never dissent). **No D5 / persisted scorer / notebook yet.**

**🔑 FOUR-CORRECTIONS APR RECONCILIATION — ⚠ C1 CORRECTED (phantom) + C2 DONE.** Full-APR v4-vs-city
baseline: cumulative **CO 3,066 vs city 4,022 (−956 before C2)**; **BP 4,911 vs 4,531 (+380)**.
- **C2 multifamily count-gap = +1,036 CO — ✅ DONE (commit `5d8fcdd`, both tranches):** 20 buildings (big
  apartments 159/152/107/81/78u…); T1 15 permits/907 dwelling, T2 5 permits/129 convention-flagged
  (live-work+sleeping). Gated reversible writes; audit `docs/audit/2026-06-28_c2_tranche{1,2}_write.md`.
  **This was the real lever.**
- **C1 584 ADU relabel = ❌ PHANTOM — NOT a correction (verified 2026-06-28).** The 584 are ALREADY
  new_unit masters with net_units set, already contributing **~457 to the 3,066 baseline**. The sizing's
  "+457" was `net_units()` computed on already-counted permits, mis-reported as an addition → a C1 write
  would **DOUBLE-COUNT**. **WHY:** the hardening pass re-ran the SAME `classify` JN-C already materialized,
  so its "584 new_unit" were already-correct classifications, not relabel targets. *Lesson: a relabel
  queue built by re-running the committed classifier finds confirmations, not gaps.* (`scratch/2026-06-28/c1_relabel_review.py`.)
- **C3 phantom-master Shattuck = −163 CO — ✅ DONE.** 1951 Shattuck `057-2046-001-00`: two 163u permits
  were one 12-story/179,680-GSF/163-unit building in two phases. **Phase 2 (B2021-04893) → subsidiary to
  Phase 1 master (B2019-05608)**; CY2024 326→163. Audit `docs/audit/2026-06-28_c3_shattuck_write.md`.
- **C3 ADU-tail = −17 CO — ✅ DONE.** 16 ADU parcels where an **ancillary** permit (solar/meter/panel/
  service) was mis-counted `new_unit=1` → demoted to subsidiary/0 (17 demotions; 055-1840-007 had 2 solars).
  **Protection guard held** (0 dwellings demoted); **3 genuine ADU-pairs PROTECTED**. Audit
  `docs/audit/2026-06-28_c3_adu_tail_write.md`.
- **🏙 KEY ARCHITECTURAL INSIGHT — the ADU ancillary double-count is OURS, not the city's.** The city's APR
  (`hcd_apr_mirror` `table_a2`) is a **curated unit-creating-permit rollup** — ancillary solar/meter permits
  never become rows, so each ADU is counted once. Verified: our 16 ancillary parcels appear ONCE in city
  data (CO=real count). Our exposure = unconditional all-permits ingestion + classifier over-promoting
  "solar/meter for ADU" → new_unit. NOT a city-side error. (`scratch/2026-06-28/city_apr_grain_probe.py`.)
- **C-multifamily over-collapse = −199 CO — ✅ DONE.** 3 phased multifamily buildings double-counted (both
  foundation/podium phase AND completion as new_unit): 057-2025-013 (−81), 055-1819-001 (−78), 056-1928-019
  (−40, group-living; **reconciles C2-T2** — B2021-04949's 41 re-homed to completion B2021-02423). Demoted the
  foundation phases → subsidiary/0, kept completions. Protection guard held; PROTECT set (056-1945 B&C 8u,
  052-1516 3 SFRs) EXCLUDED. Audit `docs/audit/2026-06-28_c_multifamily_collapse_write.md`.
- **🏗 KEY INSIGHT — phased multifamily is the SYSTEMATIC both-directions error.** The classifier handles
  multi-phase big buildings inconsistently: sometimes BOTH phases→new_unit (over-count, −199 fixed here),
  sometimes the completion phase→ambiguous (under-count, +147 held). Same root cause, opposite signs, ~±175
  each → they largely offset, which is why the net looked like only −100. The fix is one rule: **one building,
  one count, at the unit-bearing completion phase.**
- **C4 BP reporting-year ≈ net-zero** (~67% year-shuffle, ~33%/+380 true excess) — alignment, not magnitude. pending.
- **Reconciliation NOW (C2 + C3 + C-multifamily done):** 3,066 + C2 1,036 − Shattuck 163 − ADU-tail 17 −
  C-multifamily 199 = **3,723 vs city 4,022 (−299).** Full decomposition of the original gap:
  **~689 permit#-mismatch NOISE** (net-zero — city credits same parcel, different ID) · **±phase-handling
  CORRECTED** (−199 over done; **+147 under HELD for Accela**) · **~4 ADU recall** · **~−150 residual** =
  genuine under-count (real housing city counts that we don't) for the contested-direction investigation.
  The OVER-collapse *deepens* the headline (−100→−299) **on purpose** — it strips real pipeline double-counts
  the city never had; the held +147 under would bring it to ~−152.
- **⚖ PRINCIPLE (load-bearing):** we do **NOT adopt city counts for buildings we can't independently size.**
  The +147 under-count buildings have NO unit count in our WorkDescriptions (that's why they're `ambiguous`) →
  counting them needs an **Accela/architect-plan pull (HARVESTER)**, not adopting the city's number. CKAN is
  reconcile-target only; city-silence is never proof, city-count is never our source.
- **CAPSTONE = full-APR reproduction.** Remaining: +147 UNDER (Accela-blocked) · C4 BP realign · C3
  review/protect tail · ~−150 residual contested-direction adjudication.

**Deferred / NOT done (carried forward):** **C3 review/protect tail** (per-parcel, John's call): ~4
likely-additional ancillary double-counts mis-flagged protect (053-1600-027, 053-1689-006, 060-2429-002,
061-2611-023) + **8 REVIEW** parcels + **3 confirmed real pairs to KEEP** (052-1542-008, 055-1906-015,
057-2018-007); B2020-03895 (#3, still pending); **C4 BP reporting-year map**; **C2/C3 mini-cleanup (gated):**
9 finaled masters within the 584 at net_units 0/NULL + 2 stored-vs-desc mismatches (B2023-02975 12/11,
B2024-00819 2/1); **OPEN — the REAL ADU recall gap** lives in OTHER bijection buckets
(`v4_adu_flag_nonhousing_role` 328…), not yet sized; **one-off — 052-1519-022 city anomaly** (city CO=2 for
a single ADU — the lone possible city-side double); curriculum notebooks; June-25 parcel-identity model
(ADR-003); capacity JN; discrepancy-framing; **push dev**.

**▶ CURRICULUM (v4 alignment) — read `notes/curriculum_development/2026-07-01_v4_alignment_not_rebuild.md`.**
Verdict: **align, not rebuild** — the curriculum already teaches behavioral (JN4 derive-the-stage, imports real
functions); the gap is it's one generation behind (address-as-identity vs v4 permit-family; v2/v3 numbers;
rebuilds its own spine). Reframe address-key as the deliberately-planted limitation the student rediscovers.
⚠ **Active rewrite prototypes already exist in `scratch/jn{2,3,4,6b}_rewrite/`** — the deep-read must check
THOSE, not just the published `notebooks/curriculum/` (they may already reflect the v4 turn).

**Building-identity layer (2026-06-29) — DESIGNED + prototype-validated + harvest-calibrated, NOT yet built
as a committed module:** permits are facts; buildings are synthetic-keyed, confidence-scored CLAIMS linked
many:many to permits (spec `notes/v4/building_identity_layer_spec.md`; prototype `scripts/v4/building_identity_prototype.py`;
harvest `scripts/v4/building_identity_calibration_harvest.py`). Validated 9/9 known cases; calibrated across
the full population (low grouping-conf 364→2, 0 erasures, housing-formation untouched). **Next session:**
- **build the REAL layer as a committed module** (buildings + permit_building + grouping_log tables) — current is prototype/scratch.
- **doc graduation:** when the layer is BUILT, its design graduates to a settled ADR at
  `docs/audit/<date>_ADR-004_building_identity.md` — that's the consolidation point. The in-flight spec
  stays at `notes/v4/building_identity_layer_spec.md` until then (don't relocate now; moving breaks
  PROGRESS + the two handover citations written this session).
- **~104 genuine-hard adjudication set** for John: **47 count-relevant ties** (unit-bearing phased buildings)
  + **28 cross-APN** (re-platted/multi-parcel — which signal wins) + **25 large-cluster** + **4 unlabeled-residual**.
- **291 unitless-xref cosmetic-tie rule pending** (low-stakes: no count rides on them; resolve by base/earliest-as-representative).
- **JN-A ingestion dedup patch** (`scratch/2026-06-29/proposed_jn_a_dedup_fix.py`) — ADOPT before next CPRA re-pull.
- **BP 4,911 re-verify at PERMIT-level** (distinct issued), not event-level (event-dedup exposed ~1,430 inflation).
- **held for review:** `B2022-00032` canonical-description (WorkDescription differs across the two files) + the **12 different-date finaled** cases (possible legit re-finals, not dupes).
- **still standing:** +147 Accela harvest (UNDER side), −150 residual, C3 review-tail.

**⚠ LESSON (ghost-doc) — docs authored in chat-Claude's `/mnt/user-data/outputs` are NOT in the repo unless
John bridges them.** A `building_identity_probabilistic_model.md` was cited in two handovers as if persisted;
it never existed on disk (sandbox-only). Handovers must NOT cite sandbox paths as persisted — cite a bridged,
on-disk path or mark "(unbridged sandbox draft)". Refs corrected 2026-06-29 to point to the real artifacts.

**⚠ LESSON (deploy-state decay) — PROGRESS deploy-state entries must be VERIFIED against origin
(`git ls-remote` / `merge-base --is-ancestor`), never carried from memory.** The "a525a3a staged &
awaiting push" note was stale ~2 weeks: its content had already shipped to origin/main via another path
(the curriculum merges) and origin/main had moved off the staged base — yet PROGRESS still said "staged,
clean FF, awaiting push." Deploy state decays SILENTLY (another branch ships your content, the remote
moves, a /tmp worktree is purged). Re-verify before trusting any staged/pending-deploy note — same family
as the ghost-doc lesson: memory is a hint, the remote is ground truth.

**⚠ HAZARD (run-audit 2026-07-01) — JN-A and JN-C are DESTRUCTIVE to the corrected v4 DB. NEVER run them
against the live `berkeley_housing_v4.db`.** JN-A re-ingests → rebuilds `events` to **pre-dedup 85,793**
(JN-A does NO dedup by design); JN-C `DELETE FROM event_classifications` + re-INSERT → **wipes the
C2/C3/C-multifamily/dedup47 corrections**. Running either erases the 3,676 corrected state. Run JN-A/JN-C
**only against a snapshot** (for a from-scratch test), never the live DB. **Safe-to-run-live (read-only):
JN-E · JN-D-viz · JN-H · verify_jn_a** (JN-D engine is read-only too but heavy + makes a GIS network call).
Also: **`verify_jn_a_conservation.py` has the only hardcoded absolute paths** (`/Users/johngage/…` DB + FEED)
— would break off John's machine; worth parameterizing (the generators are portable via `expanduser`).

**⚠ REPRODUCIBILITY GAP (run-audit 2026-07-01) — the notebooks are NOT a complete from-raw pipeline.** From
raw, the chain reaches only **base-state** (JN-A → 85,793 pre-dedup; JN-C → ~3,066-era classification). The
corrections that reach **82,923 / 3,676** (event-dedup + C2/C3/C-multifamily/dedup47) live as **OUT-OF-NOTEBOOK
scratch scripts + `docs/audit/*` gated writes** — JN-E **references** them in its §3 ledger prose and
**reconciles the result, but does NOT apply them.** So the reconciliation is **reproducible-given-the-
corrected-DB, NOT reproducible-from-raw-through-notebooks.**
- **IMPLICATION (every-city goal):** to make the notebooks a complete from-raw pipeline (what a second city
  needs), fold the dedup + corrections **into the notebook lineage** — e.g. a **JN-B dedup stage** + a
  **JN-corrections stage** between JN-A and JN-E, or promote the gated scripts into the documented lineage —
  with the deliberately-**HELD** items (the **+147**) encoded as **hold-not-apply**. This is characterized
  **next-tier work, NOT a defect** in the current Berkeley result (which is correct and gated).

**v4 DB mutation ledger (6 gated writes, all reversible, snapshots in `databases/keep_snapshot_*`):**
C2-T1 (+907) · C2-T2 (+129) · C3-Shattuck (−163) · C3-tail (−17) · C-multifamily (−199) · dedup47 (−47).
Net CO 3,066 → **3,676 vs city 4,022 (−346, dedup-clean)**. Post-write sha `6389e612ac0c6b04`. DB is
gitignored; the `docs/audit/2026-06-{28,29}_*` records are the durable trail (permits/values/reverse SQL/snapshots).
- **dedup47 (2026-06-29):** 4 permits had DUPLICATE finaled-new_unit-master events (CPRA two-file overlap +
  within-file dups; v4 deduped permit KEYS but not EVENTS). Collapsed to one each (B2014-05786 −44 + 3×−1).
  The −47 removes a masking over-count; **phase collapses verified clean** (distinct permits, single finaled
  events). Audit `docs/audit/2026-06-29_dedup47_write.md`.
- **event-dedup (2026-06-29, structural/CO-neutral):** in-place removed **2,870** cross-file duplicate milestone
  events (events 85,793 → 82,923; CO unchanged 3,676; 30,764 permits all retained; 0 orphans). 3 tiers: AUTO 2,870 ·
  REVIEW-HOLD 3 (B2014-05786 cosmetic + B2022-00032 WorkDescription-differs) · DIFFERENT-DATE 12 (possible
  re-finals, held). Audit `docs/audit/2026-06-29_event_dedup_write.md`. **BP must be counted PERMIT-level**
  (distinct issued = 30,511 vs event-level ~31,941 pre-dedup; confirm the 4,911 figure uses distinct permits).
  **DURABLE ingestion fix (dedup at JN-A cell 17) PROPOSED for review, NOT executed** — `scratch/2026-06-29/proposed_jn_a_dedup_fix.py`.

---

## Where we are (2026-06-26) — v4 REBUILD UNDERWAY

**▶ READ `notes/v4/HANDOVER_v4_2026-06-26.md` FIRST.** The project has pivoted to the **v4 event-stream
rebuild** (see `RESUME_chat-claude_v4.md` for the settled architecture). The S1–S9 / G1 / G2 work below
is the v3-era lineage — still valid as prior research and the comparison target, but v4 is the live track.

**✅ JN-A DONE, COMMITTED, PUSHED (cbcdeee).** Unconditional CPRA ingestion → event stream: 85,793 events
from 32,202 rows, four-axis (submittal 32,202 / issuance 31,940 / finaled 21,650 / completed 1),
conserved, independent verifier PASS. Schema `schema/v4/schema_v4.sql` committed (27 tables). v3 untouched.

**✅ JN-C PASS 1 BUILT, RUNS CLEAN, COMMITTED.** Reversible housing-role classifier (#1 housing/non-housing
+ #2 master-collapse on permit family; #3 phantom-master DEFERRED). Writes only `event_classifications`
(reversible) + a harvest-queue CSV. 16 vocabulary tests pass (anchored to real prior-research cases).
Generator: `scripts/v4/build_jn_c.py` (SOURCE OF TRUTH — regenerate, never hand-edit the .ipynb).
- Role dist: alteration 64,739 · subsidiary 9,597 · ambiguous 7,403 · new_unit 2,964 · demolition 920 ·
  non_housing 170.
- Units-vs-v3: CY2024 837 vs 708 (overshoot 129) · CY2025 559 vs 497 · 8-yr 2,868 vs 4,310 (below).
- Size bands (1/2-4/5-19/20-99/100+): 640/405 · 26/53 · 4/51 · 26/1,492 · 6/867.
- Harvest queue 1,954 inconclusive; all need Accela (37 R2 docs map elsewhere).

**✅ CLASSIFIER LIFTED to an importable home (2026-06-27) — drift-pattern fix, COMMITTED (dev, unpushed).**
The v4 `classify` + vocab + 16 tests were trapped as cell-strings inside `build_jn_c.py` (un-importable;
every consumer exec-extracted from the notebook). Lifted verbatim to **`scripts/housing_rules/permit_role.py`**
(June-7 architecture; June-18 drift audit). New `housing_rules/test_permit_role.py` (16 vocab + 9 deflation,
anchored). `__init__` re-exports `classify, net_units`. Consumers re-pointed to import: `build_jn_c.py`
(imports + renders via `inspect`, + fixed its hardcoded `/home/claude/` output path), `build_jn_d.py`
(import + positional adapter; also fixed `occurred_at`→`event_date` and added `UnitsRemoved`),
`scratch/.../harden_relabel.py`. **Proven:** behavior-identical old-vs-new over all 85,793 events (0 mismatches);
role distribution UNCHANGED after regenerate+execute; JN-D's five HARD asserts pass (842/649/839/584/531-584)
importing cleanly. Proof harness: `scratch/2026-06-27/permit_role_identity_proof.py`.

**OPEN (live work — see handover):**
1. DEFLATION fix APPROVED, not implemented: confident SFR/ADU with blank UnitsAdded → 1 (single-dwelling
   only; multifamily-blank → flag, not guess). 640 projects→405 units proves the undercount. Likely most
   of the 8-yr shortfall vs v3.
2. INFLATION check (after #1): the 20-99 band's 1,492 units / 26 projects — real distinct buildings or
   REV double-count? (CY2024 u/bldg 8.0, CY2022 6.2 are big-project years where REV-inflation hides.)
3. v4↔HCD ADU bijection (recon done): only v4 (724 permits) & HCD (`table_a2.UNIT_CAT='ADU'`, 1,160
   addresses) have a real ADU determination; v3/v2 don't. HCD has MORE — same direction as deflation.
   Build with canonical-APN join (`to_canonical_apn`, 3-layer), address-from-payload, match-rate-first,
   NO address-collapse (the ADU-pair protection rule), HCD oracle-only.

**DEFERRED:** harvest-resolution notebook (R2 PDFs + Accela HARVESTER, sweep can be fast/aimed); #3
phantom-master discriminator (permit-family + building-label); the SALVAGE conversation (re-point
Explorer + curriculum + APR work at the v4 spine — migration, not abandonment).

---

## Where we are (2026-06-18)

**▶ LATEST SESSION — read `notes/HANDOFF_2026-06-18.md` FIRST.** It captures the post-S8 work not yet folded into the entries below: the **S9 v3-vs-city scorecard (LOCKED, +301)** in `docs/projects/2026-06-17 - Round One.md`; the **building-identity finding** (S1 collapses multi-building developments — 14 cases, 12 same-parcel; APN is not the fix; `build_s1.py` has an UNWIRED split rule; needs an S2–S8 re-key = the proposed "S1.5" stage); the **structures-layer + imagery-corroboration** scoping; the **v2 entity-model survey** (49 tables); and the **curriculum (JN1–JN6b) + R2 hosting + permits_clean exports**. v3/v2 untouched since S8.

**✅ REBUILD S8 DONE — reconciliation matrix (`build_v2_from_sources`, gated write to `berkeley_housing_v3.db`).** Snapshot `keep_snapshot_2026-06-17_pre-s8.db` (refuse-to-clobber, survived idempotency re-run sha-identical `f3eae3cd`). **`s8_reconciliation` = 90 findings across 10 DISTINCT finding_types** — SYNTHESIS (gather, never re-derive): every gathered row copies its basis from a live `_reconcile`/`_overlap`/`_review` source. **Exact-count lock (the drop/double-gather check, re-queried vs LIVE source tables): date_reconcile 3 · stage_reconcile 33 · unit_reconcile 6 · apn_overlap 13 · xaddr_review 22** — all == source. Synthesized: **multi_building_development 1** (2352 Shattuck/proj179, scan-verified single member) · **measurement_basis 4** (UC beds-vs-units) · rhna_scope_question 1 · entitlement_date_gap 1 (soft pointers) · crosscheck_summary 6. **`pending_uc_conversion` = 3 / `needs_acquisition` = 0** (UC beds-only get the DISTINCT disposition — size known in beds, only UC's conversion missing; ad hoc 550/750/556 rejected; 0 v3 units at-risk since no UC residence is in the CPRA spine). **2352 Shattuck appears as BOTH `unit_reconcile` AND `multi_building_development`** (two aspects, not a double-count). VERIFY: integrity ok, idempotent (90), basis copied (nothing re-derived), **wiring guard CALL-spied** (cycle_for_date 6× + normalize_address 44× invoked; net_units deliberately NOT called — gather, not re-derive), Tier-1 568, **live v2 byte-identical (sha `d6a1a960`)**, s0–s7 untouched. All 9 gates (s0–s8) green.
- **NEW finding recorded — UC beds-vs-units measurement basis:** v2 carried **2,628** bed-derived "units" across the 4 UC residences (550/772/750/556), 3 via an ad hoc bed→unit conversion (the same fabrication class as market=units−vli). v3 excludes all 4 (UC exempt from CPRA). proj170 Anchor House has a sourced unit figure (244 apartments, doc 2178) + 772 beds; 165/171/177 hold beds-only (`pending_uc_conversion`).
- **Acquisition queue (added):** UC's official bed→unit conversion / unit counts for 165/171/177.
- **NEXT: S9** — the A2: compare v3's by-cycle completions + BP-credit to the CKAN-mirror oracle (`hcd_apr_mirror.db` = Berkeley's submitted APR). ORACLE GAP: the mirror has NO Table B (RHNA progress absent), so the 492/503 cross-check is soft/text vs the city's separately-published figure. Resume note: `notes/rebuild_resume_S9.md`.

**✅ REBUILD S7 DONE — cycle-scope (`build_v2_from_sources`, gated write to `berkeley_housing_v3.db`).** Snapshot `keep_snapshot_2026-06-17_pre-s7.db` (refuse-to-clobber, survived the idempotency re-run sha-identical). **`s7_cycle` = 2,236 event rows** (1,285 BP + 951 CO), one per `s2_events` BP/CO milestone, tagging the **THREE independent date concepts** the naive `cycle_for_date` conflates: `reporting_year` (Table A/A2 by-year) · `calendar_cycle` (5th/6th @ 2023-01-31) · `in_projection_period` (narrow 2022-06-30→2023-01-30 bool, 162 events) · `rhna_credit_cycle` (building-level, first-BP ≥ 2022-06-30, no cap). **Non-conflation proven: 94 BP events are calendar=5th but credit=6th** (projection-credited). 0 asserted reporting_years (all from is_inferred=0 dates); `is_first_bp` exactly one per BP-building (650 6th / 635 5th credit); **6 CO-only-no-BP → credit NULL flagged** (the 94 no-event pipeline buildings aren't tagged — no event to tag; this corrected Phase A's mislabeled "100"). **S9 cross-check SURFACED, not forced:** cumulative 6th BP-credit 421bldg/1,792u (thru CY2024) · 648/2,419u (thru CY2025) vs city 492/503 — BP is the right milestone (was CO), magnitude doesn't reconcile → S8/S9 scope/population question. VERIFY: integrity ok, idempotent (re-run identical 2,236), Tier-1 568 unchanged, **live v2 byte-identical (sha `d6a1a960…`)**, s0–s6 untouched.
- **`housing_rules` RE-WIRED (the orphaned policy module) + EXTENDED:** added **`rhna_credit_cycle(first_bp_date)`** to `classifiers.py` (sourcing the 2022-06-30 boundary from `PROJECTION_PERIODS`, NOT `RHNA_CYCLES['6th']`=2023-01-31 — the CLAUDE.md:179 non-conflation). `test_s7_gate.py` carries a **TRIPLE wiring guard that spies on all three functions and asserts each is CALLED** (cycle_for_date 2236× · is_projection_period 2236× · rhna_credit_cycle 1285×), not merely imported. All 8 gates (s0–s7) green; smoke test green.
- **QUEUED (anti-drift, noted not done):** refactor `generate_apr_v2.generate_rhna_progress` to **import `housing_rules.rhna_credit_cycle`** instead of inlining the 2022-06-30 boundary (S7 now single-sources it).
- **NEXT: S8** (reconciliation matrix — gathers s2_date_reconcile 3 + s3_stage_reconcile 33 + 2352 Shattuck/Logan-Park + the 492/503 scope question), then **S9** (the A2 vs CKAN-mirror oracle). Resume note: `notes/rebuild_resume_S8.md`.

**✅ G2 DONE — independent-APR narrative (`5cf130f`).** `docs/audit/2026-06-16_G2_independent_apr_narrative.md` — the public/policy story, every claim traceable to a G1 number. Five-point spine: cross-validation (695 matched; 1,119 gap dissolves into 1,223 reconcilable modeling diff, 49u real coverage); proj158 omission (solid; ADUs flagged ambiguous); honest 49u ADU-tail boundary; NOT-more-accurate + full decomposition table; the affordability open-data finding (773 city affordable CO units from deed-restriction docs outside the permit feed = the transparency-ordinance argument). Inflation claim presented as tested-and-withdrawn. NEXT: G2 fronts the JN series.

**✅ G1 DONE — APR reconciliation engine (ours vs city), `c88ef7c`.** `scripts/reconcile_apr_vs_city.py` (read-only: v2 + hcd_apr_mirror; mirror now a legit comparison source). Lineage-aware join (city files prior-APN; we hold current+prior via parcel_lineage), milestone-aligned (CO↔CO), year-aligned (2018-2025). **4 buckets:** MATCHED 695 projects · OURS-ONLY 5/43u (genuine omissions incl. **proj158 39u**) · CITY-ONLY 60rows/656u (49 ADU-tail + 607 re-plats) · AFFORDABILITY-DETAIL (city 773 affordable CO units tier×DR/NDR vs our ~0 = the open-data finding). **GAP fully decomposed to the unit** (city 4,514 − ours 3,395 = 1,119): +607 re-plat artifacts + 616 per-permit/split granularity + 49 ADU-tail − 110 deltas − 43 omissions. **AIRTIGHT CHECK: the "city inflates via multi-counting" claim is REFUTED** — multi-rows are distinct permits/split-children (verified), our model collapses them = OUR under-granularity, not city over-count. **Framing: NOT "more accurate than the city"** — cross-validate on the bulk + caught omissions + honest ADU-tail boundary + affordability open-data finding. Quality bounded by lineage completeness (607 re-plat chunk shrinks as the crosswalk's held re-plats land). NEXT: G2 narrative.

**✅ Q1 DONE — HCD APR (A/A2/B) from v2, exact-column fidelity + v2-path harness (`2a8a7fe`).** `scripts/apr_hcd.py` + `04_reporting/Q1_apr_hcd_from_v2.ipynb`. Reads v2 + housing_rules ONLY (read-only; the CKAN mirror is the column-schema TARGET, never a data source). A2 = the income-tier×DR/NDR×milestone matrix, reshaped from v2. **VALIDATED:** A2 columns = mirror `table_a2` EXACTLY (69/69); matrix CO-cells = 3,611 = all-time CO; cumulative reconciles (703/702, tiles 625/612/530/216, RHNA 1,198/234 VLI). **HARNESS PROVEN:** same tool on a different v2 (pre-ingest snapshot) → 672/2,619, same 69-col structure (the Q2 acceptance test); schema-tolerant (pre-MVP v2 runs, PRIOR_APN degrades to blank). **HONEST data state:** DR/NDR 0% on completions → NDR-default(flagged in NOTES); tier coverage ~36% → uncategorized→ABOVE_MOD(flagged); ACUTELY_LOW/FIN_ASSIST/demo absent → blank-with-provenance. NEXT: G1+G2 (city-comparison) build on this. (World B from the rebuild test: v2 NOT reproducible-from-raw — the corrections-as-declarative-seed Layer-2 is the prereq before "a student runs it from raw".)

**✅ PARCEL-IDENTITY MVP WRITTEN (ADR-003) — commit `a94b8e6`, snapshot `keep_snapshot_2026-06-16_pre-apn-lineage.db`.** The gated write ran + verified.
- **DB now has:** `parcels.apn_raw` (source-faithful, preserved = legacy `apn`) + `parcels.apn_normalized` (Option-B structure-preserving canonical) + `assessing_county`; the county-scoped enforcement **triggers** (live, REJECT A-form `057204600100` / raw / lowercase / dup, ACCEPT B + 48A-alphanumeric); the **`parcel_lineage`** table = **28 candidates** (25 `apn_renumber` from the Phase-2 re-points + 2 `condo_map`[proj179 N/S] + 1 `subdivision_map`[Acheson 178]); the `parcel_apn_prior_current` APR view. **proj178 held:** `apn_normalized=NULL`, `apn_raw` keeps the 4-APN cell (Acheson split deferred to lineage-confirmation).
- **The 25 Phase-2 crosswalk re-points are NOW candidate `apn_renumber` lineage** (status='candidate' until confirmed vs a recorded county map) — not standalone re-points anymore.
- **CANON = Option B** (`to_canonical_apn` emits it): structure-preserving, `057-2046-001-00`, canonical_separator `-` + pattern in `APN_FORMATS['Alameda']`. **All 4 consumers centralized on the ONE function** (per-script canon copies deleted, grep-clean). VERIFY under B (consistent both sides): materialize 672/$1.93B, export 895/672, shake 6/6 + stale_apn 33, fingerprint 888 (apn_raw=888 preserved, B-pattern 887 + 1 NULL), 703/895/672 UNCHANGED, integrity ok.
- **NEXT (lineage growth):** confirm candidates vs a recorded county map (the harvest source = open decision); apply proj179 N/S split (2 project_parcels + materialize multi-parcel SUM) + Acheson 178; promote MEDIUM/LOW crosswalk candidates. **Grow MVP→TARGET additively** (parcel_identifiers time-history, parcel_events, time-versioned geometry — `schema/parcel_apn_lineage_schema_TARGET.sql`).
- **ALSO PENDING (John, unrelated):** assessed-value front-end render + deploy (export→promote→push→purge; aggregate $1.57B→$1.93B on regen); classify exempt set (proj91 vs proj523).
- **Refs:** ADR-003 `docs/audit/2026-06-16_ADR-003_parcel_identity_model.md`; schema `schema/parcel_apn_lineage_schema_{MVP,TARGET}.sql`; migration `scripts/migrate_parcel_identity_mvp.py`; SB-9 rule `classifiers.sb9_countable_units` (lot-split-only=0 units). **GENERALITY GUARD (don't regress):** APNs are ALPHANUMERIC (even Alameda has 25 letter-APNs 48A/48H — never digits-only); the trigger enforces Alameda's REGISTERED B pattern (attributed, county-scoped), county #2 = a registry row not code.

**PARCEL_CROSSWALK Phase 2 — 25 HIGH re-points applied + lineage table (earlier gated write).** Snapshot `keep_snapshot_2026-06-16_pre-crosswalk-high.db`. Commit `fb6a158`.
- **NEW `parcel_crosswalk` table** (prior_apn→current_apn, relationship_type, confidence, evidence, provenance) + **25 HIGH re-points** (4-source convergence). VERIFY: 703/units/895 UNCHANGED, all 25 resolve to BUILT parcels, 0 orphans, integrity ok.
- **CORRECTION mid-write:** original 31→**25**. The assessor canon was COMPONENT-based (BOOK/PAGE/PARCEL/SUB_PARCEL), but those columns are often NULL even when the APN string has the full number (`59-2325-38` → PARCEL=SUB=NULL → component-canon collapsed distinct parcels to `...000`, colliding + false-flagging). **Fixed: authoritative assessor canon now from the APN STRING (segment-parse)** in `build_parcel_crosswalk.py` + `materialize_assessed_value.py`. 6 of the 31 were FALSE_STALE (stored APN already valid; buggy index couldn't see it). FALSE_STALE 3→13.
- **Coverage effect:** re-ran materialize (canon-fixed) → `project_assessed_value` **640→672 rows (91%→96%)**, $1.93B TNV; all 25 flip "pending"→real value (proj895 $99.2M, proj135 $75.8M…); 9 de-list blind-spots. ⚠ the front-end aggregate ($1.57B→$1.93B) updates on the next export regen (deploy).
- **HELD (separate review):** 10 MEDIUM (proj179 N/S split, 512/552/740/751 condo/dedup, Imps=0 lag), 12 LOW (Acheson 900/901/904/905 + proj380/467 address-renumber re-plats), Acheson umbrella 178 split.
- **DETECTOR CANON FIXED (`2773e27`):** folded APN-string canon into `shake_detectors.py` (closes the bug across all 3 consumers). Re-run: **stale_apn 71→33** (25 re-points + 13 false-stale + 5 bad_format drop out; 33 remaining = genuine held MEDIUM/LOW), calibration 6/6, HIGH still reserved (1 shadows), bad_format→0.
- **proj179 (Logan Park) INVESTIGATED — it's a 1→many SPLIT, evidence CONCLUSIVE (held, no write):** entitlement ZP2018-0135 "237 units, Phase I (South) + Phase II (North)"; B2019-05574 = North Building (finaled 2022-01-14 = the co), B2019-05575/proj887(merged,69u) = South Building; two parcels at 2352 Shattuck — **55-1895-41 North $103.7M + 55-1895-42 South $52M** (combined assessed $177.6M, net taxable $178M, est tax $2.22M/yr; North 168u + South 69u = 237). → map proj179 to BOTH (relationship_type='split'); **⚠ proj179 becomes the FIRST multi-parcel COMPLETED project → the assessed-value materialization (currently primary-parcel-only) must SUM multi-parcel** before this re-point, else it undercounts. Awaiting John's go.

**ASSESSED-VALUE / PROPERTY-TAX FEATURE — fact table materialized + wired into both read-paths (earlier).** Gated DB write (snapshot `keep_snapshot_2026-06-16_pre-assessed-value.db`). Commits `4398095` (table+machinery) + `45617b2` (wiring).
- **`project_assessed_value` fact table — 640 rows** (completed projects with a usable assessed value: parcel joins refreshed `berkeley.db` + Imps>0). Per-row: land, imps, assessed_value (=land+imps), total_net_value (net taxable), exemption_amount (raw/unclamped), as_of_date 2026-02, effective_rate_used 0.0125, est_annual_ad_valorem_tax, source, computed_at. **Machinery** `scripts/materialize_assessed_value.py` (idempotent, re-run each assessor refresh). VERIFY: TNV **$1.569B** reconciles, assessed $1.656B, est-tax $19.6M/yr, exemptions 422 +ve / 205 ~0 / 13 −ve / 2 TNV=0; FK clean; idempotent.
- **Decisions:** exemption stored RAW (−ve = roll carries fixtures/personal-property beyond land+imps); **"tax-exempt" display ONLY off `total_net_value=0`** (never the sign); rate = **1.25% ad-valorem APPROXIMATION** (excludes Berkeley flat parcel levies → real bill higher), labeled as such everywhere; **completed-only** (pipeline omitted — declared construction value is a different measure, queued separately).
- **Wired (3 verified steps):** `v_projects_flat` LEFT JOIN (+5 cols; 895/703 unchanged; durable DDL `schema/v_projects_flat_current.sql`) → `export_explorer_data_v2.py` (emits the 6 assessed fields incl. `assessed_tax_exempt`) → `generate_shattuck_label_overlay.py` (`label_text` branches: value/exempt/pending/omit; proj136 → "$85.3M assessed · ~$1.07M/yr", proj179 → "pending", pipeline → omit).
- **FRONT-END RENDER DONE (`5530ff3`, dev only):** per-project expanded-row line (value / tax-exempt / pending / omit branching) + civic aggregate panel ($1.57B net taxable · ~$19.6M/yr est. ad-valorem) + honest 91%-coverage badge. Verified: proj136 $85.3M/$1.07M-yr, proj91/523 Tax-exempt (not "affordable"), proj179 pending, UC/pipeline omitted; JS valid, div 521/521.
- **QUEUED follow-ups:** (1) **classify the exempt set** (proj91 45u affordable vs proj523 1u institutional) BEFORE any journalist-facing "affordable=subsidized" story — store fact now, classify interpretation later. (2) **DEPLOY** — must **re-run the export** so served `explorer_data.js` carries the assessed fields (else the render shows "pending" for all), then promote + push + Cloudflare purge (John's). (3) **coverage 91%→~98% after the parcel crosswalk** (the 53 stale-APN + 9 lag gain rows then). (4) PARKED: pipeline "declared construction value" as a separate labeled feature. ⚠ pre-existing: `schema/views_compat.sql` v_projects_flat copy is stale/drifted (documented).

**ITEM 3 DONE — `scripts/shake_detectors.py` built, calibrated, full-run + findings triaged (earlier).** Deterministic read-only anomaly detector (commits `f4ce9f1` + `c52c61e`; 13 checks, 3-layer APN crosswalk, all FP-filters calibrated — 6/6 known-truth assertions pass). Full run → `data/audit/shake_findings_2026-06-16_full.json`. **Read-only throughout; findings are a triage queue, John decides writes.**
- **PRIORITY 1 — the 6 HIGH built_vs_vacant completions VERIFIED GENUINELY BUILT (the 703 STANDS).** proj134/158/161/174/299/358 (all 2025 COs reading assessor `Imps=$0`) EACH have a **City-FINALED `completes/evidentiary` building permit** (158=B2022-04366 39u congregate finaled 2025-05-06; 134=B2022-05880 8-story 28u; 161=B2023-02975 12u; 174=B2023-02354 5-story 24u after demo B2023-03067; 299=B2021-04892 4u; 358=B2023-06296 ADU conversion). **NONE unbuilt** — `Imps=$0` is **assessor reassessment lag** (parcels last touched 2017-2025 pre/mid-construction; new-build reassessment lags 1-2yr > the detector's 270-day window; proj174 = demo→rebuild dropped Imps to 0). **proj158's city-omission claim STANDS** (the 39u building is real + finaled). NEW CLAUDE.md rule: a finaled permit is the built-signal that overrides `Imps=$0`.
- **PRIORITY 2 — the bulk (66 stale_apn + ~40 stage_skip∩stale_apn + the housing blind-spots) is ONE re-platting root cause → the `parcel_crosswalk` job, NOT piecemeal.** CONFIRMED: proj179 (Logan Park, stored APN absent) resolves to blind-spot parcel **`55-1895-41` ($103.7M built)**; Acheson umbrella proj178/900-905 → the `57-2046-8-x` split parcels (incl. blind-spot 2125 University); 740/751/349 (1444-1446 Fifth), 512/552 → re-platted/split current parcels. The crosswalk's prior-APN→current-parcel lineage **simultaneously** clears stale_apn, makes built_vs_vacant pass, and de-lists the blind-spots. Queued as its own session.
- **PRIORITY 3 — 1 shadow_candidate** (APN `055183001400` + 3u, **proj54/proj62**, no two-permit/two-CO evidence) → genuine dedup candidate (NOT a protected ADU pair) → the merged_into_id dedup discipline, low priority.
- **PRIORITY 4 — cleanup queue:** 11 stage_skip genuine completed-no-BP, 10 monotonicity ordering, 35 address house#-discrepancy, 5 bad-format APN — as capacity allows.
- **Caveats recorded in the findings:** 363 collided canonical keys / 2,677 collapsed parcels (sibling-Imps risk tagged); co_only cohort = 713 (measured); LatestDocumentDate is a recording date. CLAUDE.md: UseCode is a weak housing signal (Imps-magnitude is the proxy); finaled-permit overrides Imps=$0.
- **Detector tuning APPLIED 2026-06-16 (committed):** built_vs_vacant now weights a City-finaled `completes` permit ABOVE the assessor `Imps` reading — completion WITH a finaled permit + `Imps=$0` → `assessor_lag_finaled` / `assessor_lag_demo_rebuild` (low); WITHOUT a finaled permit + not-recent → HIGH. Re-run result: the 6 (134/158/161/174/299/358) all dropped to **low** (174/208 tagged demo→rebuild); **built_vs_vacant now has ZERO HIGH**; the only HIGH anywhere is the 1 shadow_candidate (proj54/62). Demo→rebuild sub-case (`Imps` demo-zeroed, distinct from pure lag, both = built) recorded in CLAUDE.md.

**RHNA-CREDIT METHOD FIXED (backend) + RHNA PROGRESS BAR HELD (front-end) — earlier.** Two-part per John's Decision 1+2. No DB write (generator query + generated artifacts + front-end source only). **Committed to `dev` (`c3e2179` + comment-cleanup `440aa8c`); the RHNA fix + CY2023 are now already live on `origin/main`** (rode in via the curriculum merges; a525a3a abandoned-redundant 2026-06-29 — see *Site / publish state*).
- **Decision 1 — method fixed in `scripts/generate_apr_v2.py` (`generate_rhna_progress`):** RHNA credit now computed from **FIRST building-permit issuance** (`MIN(event_date)` over non-subsidiary `building_permit_issued` events from `project_events`) **+ the `>= 2022-06-30` projection-period boundary** + UC exclusion — replacing the old `v_projects_flat.bp_issued_date` (MAX, no boundary) query that wrongly flipped 5th-cycle-first-permitted projects to 6th on a later revision. **Result: 1,198 units / 234 VLI / 28 projects = 13.4%** (was 1,671 / 320 / 18.7%). Verified: direct query == generator output == regenerated JSON. By-year first-BP: CY2022=62, CY2023=436, CY2024=569, CY2025=131. **⚠ COVERAGE-LIMITED / INTERNAL** — tracked-project BPs only, NOT Berkeley's full ADU/infill permit stream.
- Regenerated `data/apr/{2021..2026}/apr_<y>.json` — semantic diff vs committed is **ONLY** `rhna_credit` (1671→1198, 18.7→13.4, vli 320→234); every other table byte-identical. Copied in surgically (no collateral file churn).
- **Decision 2 — front-end de-misframed (don't publish a coverage-limited / completions-as-RHNA bar):**
  - `docs/explorer.html`: the "RHNA Progress (6th cycle)" **progress bar + %** HELD → replaced with an honest note (target 8,934; underlying measures reported directly as raw counts; no combined "% toward goal" because RHNA credit is BP-earned and our permit coverage is incomplete). Removed the "RHNA progress is measured by completions: ~X%" clause from the APR-tab Key Finding.
  - `docs/explorer.js`: unwired `stat-rhna-completions` / `stat-rhna-pct` / `rhna-progress-bar` / `stat-apr-rhna-pct` (retired `rhnaCompletions`); **kept the CO tiles** (`stat-co-2023..2026`) and the BP panel. JS syntax OK.
  - **KEPT trustworthy:** net-new-CO annual tiles, 703 completions, all-time CO 3,611, BP-issued raw counts.
- **BP PANEL DE-MISFRAMED (John approved):** the "Building Permits Issued (RHNA Credit)" panel — the worst instance (a specific FALSE coverage claim on a journalist-facing tool) — fixed in BOTH `explorer.html` and `explorer_v2.html`: (1) **removed** the false **"captures 83% of city's reported BPs"** note (reality ~28 tracked projects, a small fraction not 83%); (2) **relabeled** "Building Permits Issued (RHNA Credit)" → **"Building Permits Issued — Among Tracked Projects"** + dropped the ✓ + added a coverage-limited subtitle; (3) **kept the raw counts** with a coverage note (BP = subset of city volume / not a complete RHNA figure / CO counts from the complete feed). Verified: no "83%" or "RHNA Credit" live text remains in either file; div balance intact (513/513, 499/499).
- **QUEUED (scope only, don't build):** full city BP-stream acquisition (Berkeley open-data building-permits / Accela BP export incl. the ADU/infill tail) — the prerequisite to ever publish a trustworthy RHNA-progress bar.
- **DONE → SHIPPED:** `c3e2179`/`440aa8c` + CY2023 `a07147c` are **live on `origin/main`** (carried in via the curriculum merges; the RHNA bar is HELD on the live site). The a525a3a staging merge was **abandoned-redundant** 2026-06-29 (see *Site / publish state*).

**R1 COMPLETE — assessor refreshed + re-founded audit + 10 verified re-points (earlier).** The Feb-2026 refresh dissolved the staleness: re-ran the stale-APN audit against current data — **23 of 43 Class-2 "assessor-lagged" RESOLVED** to real built parcels (11 of those = permanent corner-lot dual-address). The earlier rollback proved OVER-CONSERVATIVE (the re-points were right, just unverifiable against 2019 data); with current data they verify. **Gated write (snapshot `keep_snapshot_2026-06-16_pre-reapply.db`): re-applied 10 re-points, all verified against Feb-2026 Imps:**
- **TIER 1 (9):** proj37/98/481/492/493/513 (built condos $130K–$1.07M), **proj899 → 55-1822-9-1 = the $60.1M 82-unit building** (orig APN lacked the `-1` sub-parcel), proj4/55 (In-Review, correct-parcel-vacant-pending).
- **TIER 2 (1):** proj511 → 59-2326-29 ($649K built sibling; the old re-point had picked the vacant 30).
- VERIFY: 8 resolve BUILT + 2 In-Review-correct, 703/units UNCHANGED, integrity ok.
- **DEFERRED (not written, isolated for follow-up):**
  - **proj512/552 — resolve-via-permit:** address has MORE built condo parcels (4/3) than recorded units (2/2) → possible UNIT-COUNT UNDERCOUNT; condo-parcels ≠ dwelling-units → resolve from the permit's dwelling count, hold parcel assignment (source-disagreement rule).
  - **proj358 — recent-lag** (co 2025-05-30, ~6wk): self-resolves when County records it; recheck in months. NOT re-plat.
  - **proj139 — PIPELINE** (status mislabeled "Completed" but co=None, bp 2024-10/entitled 2025-10, under construction); vacant parcel correct (not built yet). NOT re-plat.
  - **proj349 — re-plat/investigate** (co 2019 but parcel vacant in current data → genuine) + the **15 orphaned** (Acheson Bldg B/umbrella proj900/178, completed-2022 proj901/904/905, etc.) → the **crosswalk queue** (prior-APN/split-merge lineage, own session).

**ASSESSOR REFRESH COMPLETE — berkeley.db.parcels now Feb-2026 current (earlier today).** R1 minimal refresh: pulled 29,131 Berkeley parcels from data.acgov.org (Alameda Open Data Hub Parcels, `services5.arcgis.com/ROBnTHSNjoZ2Wm1P/.../Parcels/FeatureServer/0`, modified Feb 2026). Snapshot `keep_snapshot_2026-06-16_pre-assessor-refresh.db`. Phase-1 gate confirmed proj136 (APN 57-2046-1) **Imps $70.4M = BUILT** vs our stale 0/vacant. Geometry pulled WGS84 (outSR=4326), projection-verified (proj136 centroid 37.87280,-122.26811 = the confirmed corner). **Rebuilt parcels + parcels_arcgis** (B3 columns preserved; **BuildingAr DROPPED → Imps>0 is the built-signal**; bonus BOOK/PAGE/PARCEL/SUB_PARCEL pre-split + Land/Imps/TotalNetValue + LatestDocumentDate; corridor+LotSize carried forward by APN). **Other tables PRESERVED** (zoning_districts 42, corridor_boundaries 3, development_potential 41, parcel_zones 29024, rent_control 1098, licenses 13004 — all unchanged). **v2.parcels.apn UNTOUCHED** (primary). VERIFY PASS: 94% Imps>0, integrity ok, **cross-walk now DETERMINISTIC** via BOOK/PAGE/PARCEL (proj136 component-build 057204600100 == v2.parcels.apn). BuildingAr-drop gated: only display-use in 1 notebook, no logic → clean.
- CLAUDE.md updated: refreshed-Feb-2026, DATE_UPDAT-is-sparse-last-change (not snapshot date), Imps-is-built-signal (not LatestDocumentDate), corner-lot dual-address PERMANENT (refresh doesn't fix), guard shrinks to County's processing lag.
- **NEXT (held for John's review):** re-found the stale-APN audit against the refreshed reference — how many of the 43 Class-2 "assessor-lagged" now resolve to real parcels (the measure of what the refresh dissolved). **QUEUED (own session):** parcel_crosswalk (prior-APN + split/merge lineage) — the durable re-platting fix; refresh gives it a current baseline + BOOK/PAGE/PARCEL + LatestDocumentDate to diff against. Harvester sub-record fix still queued. ⚠ minor: parcel_zones still links the old 29024 set (preserved as-is; a future re-derive updates it).

**APN AUDIT ROLLED BACK — root cause found: berkeley.db was a ≤2019 ArcGIS cache (earlier today).** John's manual find on proj136 (stored APN `057204600100` IS the correct 1951 Shattuck corner lot, which the assessor addresses as "2108 Berkeley Way / vacant") exposed that the Item-2-A stale-APN audit was founded on a **2019-08-26 assessor snapshot, ~5 yr stale** — so every post-2019 building reads vacant/mis-addressed, and "address↔APN mismatch" was a FALSE-FLAG, not a wrong APN. **Phase-B gated write (snapshot `keep_snapshot_2026-06-15_pre-apn-rollback.db`):**
- **Rolled back ALL 15 APN re-points** to their original stored APNs (the method was unreliable → revert all its outputs to PRIMARY data). **Kept only 2 affirmatively-justified:** proj902 (Acheson Bldg D, documented re-plat 010→011-01) + proj839 (stored `2030 Bancroft` genuinely wrong-area vs `2662 Hilgard`).
- **proj136: lat/lon FIXED** (37.87284184,-122.2680886 — was wrongly copied from 1950 Shattuck across the street); **APN unchanged** (`057204600100` correct, triple-confirmed: stored + John's manual + corner-lot LotSize 17,497).
- VERIFY ALL PASS: 15 restored to original, 902/839 stand, proj136 APN unchanged + marker corrected, **703/units UNCHANGED** (APNs/lat-lon don't touch counts), integrity ok.
- **CLAUDE.md updated:** the 2019-snapshot root cause + the corrected stale-APN classes (mismatch = FLAG-FOR-REVIEW never auto-re-point; only documented re-plats safe; stored APN is PRIMARY).
- **2 follow-on tasks queued (NOT this write):** (1) **HARVESTER FIX** (engineering) — `harvest_plansets` scrapes the MASTER's attachments only, never iterates `url_discovery`'s REV/DEF sub-records → **misses revision docs on every multi-rev project** (ZP + B); plus drop the ZP-assert + use module=Building + relax the >5MiB filter for B-permits. proj136's REV14 PDF→R2 waits on this. (2) **ACQUISITION:** refresh `berkeley.db` from a CURRENT Alameda assessor snapshot → dissolves the whole "assessor-lagged" set + lets the APN audit be re-founded on data that postdates construction.

**DEDUP MERGES #2 COMPLETE — 3 merges from permit evidence; B-permit harvester PROVEN (earlier).** Verified the Building-module harvester is the ORIGINAL/proven engine (url_discovery defaults module=Building; inspection_scraper/test_fetch all Building; the ZP plan-set *document* engine is the later extension — CC's earlier "B-adaptation deferred" was backwards). Validated end-to-end: `discover_url('B2021-04893')` → CapDetail gave Work Location `1951 Shattuck`, "12-story 179,680 GSF", Finaled. Permit WorkDescriptions resolved the dedup queue; merged (snapshot `keep_snapshot_2026-06-15_pre-dedup2.db`, merged_into_id discipline, FK re-point-before-retire):
- **544←852** (1157 Francisco): proj852's B2021-02937 = "accessory building + hot tub" (NOT a dwelling) → subsidiary; permit+doc+CO-event re-pointed to 544.
- **179←887** (2352 Shattuck): proj887 = "Phase II South Building" of **Logan Park** (proj179, 237u, ZP2018-0135) → shadow; permit+doc re-pointed; 887's own wrong parcel 871 dropped.
- **113←118** (2138 Kittredge): proj118 = `(id:118)` de-dup artifact → absorbed. **⚠ UNIT COUNT 73-vs-66 UNRESOLVED** — neither had a B-permit for the units; the **ZP/entitlement doc settles it** (flagged for the ZP/Planning harvest, NOT the B-permit batch). Kept 113's 73 provisionally.
- **PROTECTED 751/740** (1444 Fifth): permits prove **Building C (1,990sf SFD) + Building D (1,712sf SFD)** = two real dwellings, distinct COs — another shadow-rule save (the collision-hold was right).
- VERIFY ALL PASS: 703 / units UNCHANGED, survivor co_dates unchanged (CO events safe — linked to ambiguous permits, view-filtered), absorbed dropped, evidence re-pointed (544←accessory permit, 179←phase-II permit), 0 orphans, ADU pairs+751/740 intact, integrity ok.
- **NEXT (b):** Class-2 parcel batch (~6 high-value: proj136/901/900/904/905/898 + 178 umbrella) — discover→CapDetail→**parcel-section read** (the APN that resolves the re-point; proj136 = "is 2108 Berkeley Way the right corner lot or NULL-until-assessed?") + building-final + PDF→R2. Harvester proven, ready. Dedup queue now CLEAR (544/852, 179/887, 113/118 done; 751/740 protected).

**APN RE-POINT COMPLETE (Item 2-A write) — 17 of 19 Class-1 re-pointed; Acheson block UNBLOCKED (earlier).** Snapshot `keep_snapshot_2026-06-15_pre-apn-repoint.db`. Per-project in-place UPDATE of the primary parcel APN (rowcount==1, all parcels exclusive). **A new-APN collision check held 2 of the 19** (would have collided with an existing project's parcel): **proj887** (2352 Shattuck South) → APN already used by **proj179** (North/South two-building OR shadow — review); **proj751** (`1444 Fifth [B2019-01349]`) → already used by **proj740** (shadow/dedup — the `[B...]` suffix is a de-dup artifact). Both → dedup/review queue. **17 written + VERIFIED:** all 17 new APNs resolve in the assessor, project_parcels intact, **703/units UNCHANGED** (APN doesn't touch completion), integrity ok. **Acheson Bldg D proj902 → `057 204601101` (57-2046-11-1, 2111 University) — now joins the assessor; block-sweeps can see it.** proj839 book-change (055→058) confirmed exclusive + written. proj136 stays Class-2 (harvest).
- **NEXT:** Class-2 harvest approach (43 targets incl. proj136 + Acheson umbrella 178/Bldg-B 900 — build the B-permit harvester vs CIC batch); then Item 3 (`scripts/shake_detectors.py`). **Dedup/review queue now:** 113/118, 544/852, **proj887/179**, **proj751/740**.

**STALE-APN AUDIT COMPLETE (Item 2-A, read-only/staged) — full class surveyed, two-class split (earlier).** Deterministic cross-DB audit of all 892 projects' primary APN vs the Alameda assessor. **Found the naive "strip non-digits" cross-walk is broken** (gave 890/892 false-dead); needs 3 normalization layers (assessor hyphen→12-digit segment-pad, v2's own inconsistent apn storage, address ordinal-word↔number + tolerance). After proper normalization: **830 CLEAN · 19 CLASS-1 (exact-address re-points, SAFE to stage) · 43 CLASS-2 (harvest/permit-doc)**. Staged → `data/staging/stale_apn_audit_2026-06-15.json`.
- **CLASS 1 (re-platted, address-resolvable — stage re-points):** incl. **Acheson Bldg D proj902** (`2111 University`→`57-2046-11-1`), proj887 (2352 Shattuck, BA25k), proj139, + small westside infill. The **exact house number** is the safe discriminator (re-plats keep the number; wrong-parcel matches drift).
- **CLASS 2 (HARVEST-queue — permit-doc only):** incl. **proj136** (1951 Shattuck — only near-match is the too-small 1950 Shattuck *across the street*, the trap the audit kept almost falling into), **Acheson umbrella proj178 + Bldg B proj900** (re-plat renumbered, no exact match), proj901 (142u), the big In-Review/Entitled (proj1 739u, proj151 Ashby BART 618u, proj4, proj17, proj20-22), + odd "0 X" addresses. **43 targets → "many" → per the decision rule, worth BUILDING the B-permit harvester adaptation** (vs piecemeal CIC).
- CLAUDE.md updated: the 3-layer cross-walk fix + the two-class stale-APN distinction + "never blanket-re-point by nearest-address" rule. proj136 wrong-APN re-point HELD (correctly Class-2).
- **NEXT:** decide Class-1 re-point write (gated; Acheson Bldg D + the 18 others) + the Class-2 harvest approach (build harvester vs CIC batch); then build Item 3 (`scripts/shake_detectors.py`, all 8 years — the stale-APN check baked in as a standing detector). Holds: 113/118, 544/852.

**DEDUP MERGE COMPLETE — 4 phantom shadows merged, armed 72u double-count defused (earlier today).** Shake-the-DB calibration (4-family agent hunt, CY2024 + 2 blocks) found the armed shadows; merged with a NEW standing mechanism. Snapshot `keep_snapshot_2026-06-15_pre-dedup.db`. **Added `projects.merged_into_id`** (soft-retire/dedup-provenance field) + filtered `v_projects_flat WHERE merged_into_id IS NULL`. Merged FK-re-point-before-retire: **96←138** (2099 MLK, armed 72u — proj96 real, proj138 stub/phantom; re-pointed 138's construction_start, dropped stub CO), **25←115** (2455 Telegraph), **127←162** (2820 San Pablo), **86←109** (2740 Shasta empty). **PROTECTED (the discipline's big catch): ADU pairs 624/869, 645/880, 362/888 — two real permits + two distinct COs = two real buildings (main+ADU), NOT shadows; merging would have erased 3 real ADUs.** VERIFY ALL PASS: 703 / 625-612-530-216 / RHNA 3611 **UNCHANGED** (absorbed weren't counted), survivors present, absorbed dropped from view, 6 ADU records intact, 0 orphan FKs, integrity ok. CLAUDE.md updated with the SHADOW-vs-ADU rule, `merged_into_id` soft-retire method, APN-stability caveat, structural facts (`units_affected` 100% NULL → D6 impossible from events; CO-only cohort 185-279+280-899 → funnel meaningless), consolidated UC rule.
- **NEXT:** Item 2 (Acheson re-point 178/900/902 → 57-2046-8-4/-9/-11-1 + full stale-APN class audit + proj136 wrong-APN re-point); then build Item 3 (deterministic `scripts/shake_detectors.py`, all 8 years, findings file). **HOLDS for John's decision:** 113/118 (2138 Kittredge units 73-vs-66 + state conflict), 544/852 (1157 Francisco — subsidiary-vs-2nd-unit). View/structural fixes queued: bp_issued_date materialization gap, proj126 status mislabel, proj183/184 is_primary.

**UNITS=0 SWEEP COMPLETE on dev (latest) — 41 undercounted units recovered.** Surveyed the full class of counted-completed projects with `total_units`=0/NULL: **4** projects, ALL classified **FIX** (real completions miscounted as 0 — none legitimately-zero, none net-loss). Snapshot `keep_snapshot_2026-06-15_pre-units0-sweep.db`. Set `project_versions.total_units` (the field `v_projects_flat` reads, per the proj170 lesson) + `unit_program`/affordability where present, cited to each completes-permit WorkDescription:
- **proj900** (2145 University, Acheson Bldg B, B2015-02998 "35 NEW RESIDENTIAL UNITS") → **35**. Represented via `project_versions` only, matching sibling **proj902** (Acheson Bldg D, 68u, also no unit_program) — avoids asserting a market tier on an Acheson building likely carrying inclusionary BMR.
- **proj465** (739 Channing, B2019-02831 "Building B: 4 Unit Apartment Building") → **4**.
- **proj208** (469 Kentucky, B2023-04389 new SFR + JADU; B2023-04472 demolished the existing SFR) → **1 NET** (JADU is the +1; rebuilt SFR replaces the demolished one — HCD net-new).
- **proj94** (2145 Grant, B2019-01597 "Add new home on the rear of lot") → **1** (purely net-new; no demo/offset on the parcel — confirmed).
- **VERIFY:** per-year NON-UC CO units rose — CY2021 312 (+1), CY2022 695 (+35), CY2023 **625** (+4), CY2025 **530** (+1); CY2024 612 / CY2026 216 unchanged. **Project COUNT 703 UNCHANGED** (already-counted projects gaining units). **RHNA completed 3570→3611** (+41, city projects, RHNA-counted). units=0 query now returns **0** remaining.
- ⚠ Affordability tiers for proj465/proj900 are placeholder/untiered (no BMR split data; ABOVE_MOD defaulted only where `unit_program` rows existed: proj94/208/465) — the TOTALS are solid; tier splits deferred (same broader tier-completeness gap). Prior-sweep's 486 units (Kittredge 169/Shattuck 163/Univ 82/MLK 72) already populated, not in this set.

**ANCHOR HOUSE (proj170) BED-COUNT CORRECTION + primary-source citation (earlier today).** Added the **Anchor House FAQ** (capitalstrategies.berkeley.edu/anchor-house-faq) as v2 `documents` id **2178**, under a NEW vocab type **`official_source`** (id 24 — first of a class of authoritative primary-source pages). Corrected proj170 from the bogus `300` (a ratio-estimate placeholder, "neither beds nor apartments") to the cited **772 beds / 244 apartments** (47 studio + 30 2BR + 3 3BR + 164 4BR). Snapshot `keep_snapshot_2026-06-15_pre-anchor-house-doc.db`. The write touched **3 fields** (`project_versions.total_units`, `unit_program.unit_count`, `unit_program_affordability` ABOVE_MOD — all 300→772, cited to doc 2178); **the verify caught that the first pass missed `project_versions.total_units`** (the field `v_projects_flat` actually reads — the `SUM(unit_count)` in the view is only for income tiers), fixed in a corrective transactional write. Effects: explorer proj170 **300→772**, **pipeline 16,572→17,044** (+472, UC counted in pipeline); **RHNA completed STILL 3,570** and **explorer 2024 STILL 612** (proj170 UC-excluded from RHNA — the exclusion is robust to the data value); tiers==total (772). ABOVE_MOD tier flagged NOMINAL (UC isn't above-mod housing; set only for tiers==total, never enters an RHNA figure). UC-exclusion rule now carries its PRIMARY-SOURCE *why* in the `generate_apr_v2.py` `UC_EXCLUDE` comment ("UC Regents approve + UC issues its own building permit").
- ⚠ **KNOWN DISPLAY ISSUE (deferred, must not be lost):** the explorer renders proj170 as "772 **units**" — it should read "772 **beds**". Data is correct; the display needs **UC-aware beds-labeling** (`is_uc_project` → "beds"). Its own task — the completion of this correction.
- ⚠ **OTHER UC TOWERS (165/171/177 = 550/750/556) are also beds-mislabeled-as-units placeholders** ("Bedroom distribution unknown; placed as 1BR"). They're UNDER CONSTRUCTION (no CO) so they don't affect completed counts — flag for the SAME beds-correction + own capital-strategies official_source citation LATER (not this write).

**UC-EXCLUSION FIX COMPLETE on dev (earlier today) — APR now obeys the documented rule.** UC student housing is exempt from city permitting and does NOT count toward the 8,934 RHNA allocation; the explorer applied this, `generate_apr_v2.py` did not. Added a flag-based `uc_project` exclusion (via `project_classifications`, NEVER a hardcoded id — `UC_EXCLUDE` constant, single definition) to all **5 RHNA-counting queries** (Table A2 CO-issued, RHNA completed, RHNA bp/credit, Table B, developer summary); the **PIPELINE total is left unfiltered** (UC belongs in the pipeline). Script commit `edff054` (snapshot `keep_snapshot_2026-06-15_pre-uc-exclusion.db`, DB byte-identical — script-only). **Acceptance GATE PASS:** Table A2 2024 **912→612** (count 86→85, proj170 dropped), other years unchanged (2023=621/2025=529/2026=216); **RHNA completed 3870→3570** (−300 exactly = proj170's 300 beds); **pipeline 16572 unchanged** (UC retained); Table B RHNA-credit **1671 unchanged** (proves no UC-BP slipped — the 3 dormant UC towers 550/750/556u can't silently count later). **Explorer↔APR now AGREE per year (621/612/529/216).** Only completed UC = proj170; the other 3 (165/171/177) have no CO. ⚠ Note: explorer's **703** completed-project tracker still counts proj170 as a built project (units excluded); APR Table A2 excludes it entirely (count 85) — deliberate tracker-vs-RHNA-accounting split, not a bug. **PENDING (John):** the dev→main deploy merge `77459e4` predates this fix → must be **re-merged** to carry `edff054` + the UC-regen before push. _(SUPERSEDED 2026-06-16: `edff054` is on `origin/main` `7e445a3` — re-merged + pushed.)_

**DEV↔MAIN RECONCILIATION COMPLETE on dev (earlier today).** A cherry-pick to `main` aborted on structural divergence; both branches had moved from merge-base `1bcddba`. Read-only survey (`docs/audit/2026-06-15_dev_main_divergence_survey.md`) found: the canonical DB is **untracked/shared**, so no data work was ever at risk — only scripts + generated outputs. main's 15 dev-lacking commits classified; **the 3 contested files all resolve to dev**: `export_explorer_data_v2.py` is a strict **superset** (main's full income-tiers + dev's co_date/status), `explorer.js` already carried main's `6b6b6bd` R2-first block (c1), and `generate_apr_v2.py` has the `2024-01-01` stub-guard main lacks (c2 — earlier reversed-diff call corrected). New shared bug found+fixed: **c3 RHNA stub-leak (line 368)** — proj137/138's `2024-01-01` stubs inflated the headline RHNA completed total; guarded → **4024→3870 (−154)**.
- **7 commits on dev (none pushed):** `320f5c1` reconcile(c1 explorer.js + media rule) · `cd01b64` docs(survey+harvest audit) · `91c0a62` cleanup(mp4 → YouTube) · `9d170c1` kml(geometry/tour source) · `bd1b69a` chore(gitignore scratch) · `6eab22b` fix(RHNA L368) · regen(this commit).
- **Full regen + 5-point verify PASS** (snapshot `keep_snapshot_2026-06-15_pre-rhna-line368-fix.db`, DB byte-identical after read-only regen): **(1)** explorer published **703** (902 projects, 2 stubs excluded) · **(2)** full tiers render (proj36 vli16/mkt136=152, proj8 vli22/mod8/mkt212=242) · **(3)** **75 r2.dev** doc links displayed via c1 (82 url-linked of 2039) · **(4)** Table-A2 2024 excludes proj137/138 (co_issued_in_year=86) · **(5)** RHNA **3870** in every regenerated `apr_*.json`.
- **PENDING (John):** the dev→main merge (dev wins the 3 scripts, regenerate generated files; survey confirms nothing-else-main-only) + push/Cloudflare purge. Media rule recorded in CLAUDE.md (mp4→YouTube/untracked; KML source→tracked).

**INGESTION channel loaded (D8) — 38 feed-resident completions appended.** EVIDENCE-layer append (snapshot `keep_snapshot_2026-06-15_pre-ingest.db` sha `67c63383`): +38 permits, +17 new projects, +38 co_events, +17 versions; counted-completed **674 → 705 (+31)** (7 existing-links already counted). ~698 units incl. Acheson Commons + the 44/50/70/82/117/142-unit buildings. Non-circular: selected by feed Finaled-date + own description classifies completes (`112cb03`), never CKAN. 21 existing-links APN-verified (0 mismatch); 18 DECISIONS-holds intact; evidentiary basis from feed Finaled, note "CPRA Finaled <date>". The held REV (B2022-01742-REV01) correctly excluded (master already in v2 — double-count trap).
- **STEP-6 proof: match ROSE every year (2018 89→91, 2019 84→91, 2020 90→92, 2021 83→91, 2022 79→88, 2025 91→93), gap shrank.** we-have/city-lacks +1 in 2021/2025 = year-attribution (NOT over-ingestion). **ACCEPTED by John 2026-06-15** — feed Finaled-date is the truth; re-dating to the city's year would be the circularity the whole session guarded against. The ingest STANDS.
- **Phase-4 findings logged from this ingest:**
  - COUNTING-CONVENTION (cycle-boundary year-attribution): **B2016-02230** (056193502800, new SFR — our feed-finaled 2021-04-21 vs city CY2022); **B2023-04389** (062294502800, new 3-story SFR — our feed-finaled 2025-12-11 vs city CY2024). Same real completion, adjacent-year disagreement.
  - CITY-UNDER-REPORT (independence finds — city's APR lacks ENTIRELY): **APN 057207300500 / B2022-04366** = a **39-unit** building (CO 2025-05-06) the city omits — the headline result; and **proj83 SFR** (063298803800). Both evidence-backed on our side, absent from CKAN.

**3-item pass (2026-06-15):**
- **ITEM 1 (DONE, written):** appended `+ passed final building inspection` to the **5** retry-corroborated buildings (snapshot `keep_snapshot_2026-06-15_pre-append5.db` sha `49e6b5bb`); count 705 unchanged; **9/10 large buildings now dual-source** (B2014-02844 the lone single-source).
- **ITEM 2 (STAGED on dev `2dd3434` — push/purge are John's):** regen → **published 703** (raw view 705, 2 stubs rejected), CO stat == map markers == 703 (coherent). Explorer diff: committed-stale 672 → **703 (+31)**. APR 2023/2024/2025 regenerated (per-year refined by feed-finaled MAX-co_date: 100/86/98). **Prose audit CLEAN** (no hardcoded completion number in served HTML; the explorer_data.js hits are data values, not prose). The committed `docs/explorer_data.js` now reflects 703. **Live site still shows old number until John pushes + purges.** _(SUPERSEDED 2026-06-16: this stage was pushed via `77459e4`→`7e445a3`; `origin/main` now serves 703 — see the current *Site / publish state* above.)_
- **ITEM 3 (PARTIAL stage — manifest skeleton ready, PDF pull needs a build):** target list refined to **6 genuine "is-it-a-dwelling" conversions + the kitchen-REV** (dropped proj13-restaurant + proj90-subpanel). Staging dir `~/berkeley-data-staging/pdfs/permits/` + skeleton `data/staging/r2_manifest.csv` (7 rows, all PENDING). **B-permit discovery confirmed working** (probe found capID). BUT the proven doc-harvest engine (`harvest_plansets.py`) is **ZP/Planning-tuned** (asserts ZP, plan-keyword+>5MiB) — the B-permit plans/CO pull needs `harvest_record` adapted to `module_hint='Building'` + B-permit attachment selection (the iframe/download mechanism generalizes; discovery proven). **Did NOT fake a harvest with the wrong-tuned engine** — the actual PDF pull is a focused next build. Then John runs `upload_harvest_to_r2.py` (his creds).

**Approved bundle WRITTEN (2026-06-15, snapshot `keep_snapshot_2026-06-15_pre-bundle.db` sha `7254011f`):** A) 4 large buildings got `+ passed final building inspection <date>` basis-notes (142/117/68/14u; verdict unchanged). D1) proj83 version units 0→1 (data-error fix). D2) ingested proj154's real master **B2021-02905** (87 affordable units, completes/evidentiary, completion 2025-02-24 via finaled deferred-submittal) → proj154 now counts via a real permit, **OUTLIER resolved**. D3) flagged 5 `@2024-01-01` events `event_date_precision='year'` (the 51 `@2025-01-01` were already flagged). Count **705 unchanged** (proj154 already counted); ACCURACY CY2025 we-have/city-lacks **stayed 3 — no over-claim**; 18 holds intact; +1 permit/+1 event.
**Harvester retry DONE: 5/6 newly corroborated** (discovery worked — earlier no-capID was transient) — B2016-00895(82u,2022-04-20), B2019-01950(78u,2021-07-16), B2016-03471(70u,2019-09-30), B2016-04483(50u,2019-11-15), B2017-01850(10u,2021-11-10). B2014-02844(44u) still no building-final. **Combined 9/10 large buildings inspection-corroborated.** These 5 basis-note appends are **STAGED, not written** (need John's nod — same trivial pattern as the approved A 4).

**HARVEST extraction (2026-06-15, read-only/staged — superseded by the writes above for A/D1/D2/D3).**
- **A) Large-building inspection corroboration**: harvested 10 ingested big buildings. **4/10 have a passed BUILDING-final (staged basis-note add, not written)**: B2019-03862 (142u, 2022-09-21), B2019-00478 (117u, 2021-10-05), B2015-03005 (68u Acheson-D, 2022-03-04), B2018-02291 (14u, 2022-05-13). 1 scraped-no-bldg-final (B2014-02844 44u, 106 insp — retry). **5 discovery-failed (no-capID, old B2016/17 permits)**: B2016-00895, B2019-01950, B2016-03471, B2016-04483, B2017-01850 — retry harvester.
- **B) PDF-to-R2 — BLOCKED: R2 credentials not in CC env (John owns R2 uploads).** Staged 8 scope-unresolved garage/storage/conversion permits needing a plans/CO PDF (proj256/262/421/437/796/481 + 2 non-housing). John runs the harvester PDF-to-R2 (or provides creds).
- **C) Held REV B2022-01742-REV01**: master IS in v2 (proj256, ambiguous garage→workspace, **NOT counted** — its co suppressed). The REV adds a kitchen = a MODIFICATION of an existing-uncounted project, not a standalone completion. Not a double-count (proj256 uncounted), but ingesting it = a scope call (is garage+kitchen a dwelling?). **John decides.**
- **D1) 2025 independence finds — BOTH GENUINE (not doubling):** proj83 SFR (B2024-02570, completes/evidentiary, inspection-confirmed 2025-11-10) and **proj158 39-unit congregate (B2022-04366, completes/evidentiary, finaled 2025-05-06)** — city has these parcels at EARLIER milestones (2024/2023) but **never as a CO**. Headline city-omission finds. ⚠ proj83 version units=0 (data error, should be 1).
- **D2) proj154 (87-unit, counted via NULL-permit CO)**: its real master **B2021-02905 IS in the feed** (not in v2, with finaled DEF/REV subs 2025-02-24) → **ingestible** to give proj154 a real completes permit; master itself lacks a clean feed finaled-date. **John: ingest the master?**
- **D3) date-stub precision**: propose `event_date_precision='year'` on **56 unflagged stubs** (51 @2025-01-01 + 5 @2024-01-01, mostly `application_submitted`). Staged, not written.

**Verdict layer — 8-year backfill COMPLETE.**
- All **956 permits classified** by `permit_role_classifier @ 112cb03`; verdict+basis materialized into the existing `permits` columns (no new schema).
- Distribution: **completes 693 · does_not 106 · ambiguous 157**. Basis: **evidentiary 671 · description_only 284 · human_override 1** (≈97% of completes evidentiary).
- **Counted-completed = 674** (`v_projects_flat.co_issued_date`, verdict-driven); **published = 672** (explorer/APR reject the `2024-01-01` migration stub). **CY2023/2024/2025 = 103/86/94.**
- **18 DECISIONS-layer holds preserved** (12 human-holds, 5 harvester-inspection, 1 proj34 human_override `@1154b9e`). `verdict_by`: 938 `@112cb03` + tagged holds; zero stale.
- Evidence layer untouched throughout: events 3873 / permits 956 / versions 883 / affordability 890.
- Rollback: `keep_snapshot_2026-06-15_pre-8yr-backfill.db`.

**Classifier — Phase-1 hardening done & verified.**
- `112cb03` (committed dev): sixth-pass FIX-E (ADU/conversion/abbreviation blind-spots) + Phase-1 trade/demo/minor leads + demo-then-build pre-check. **85/85 self-tests**, AGENT-1-VERIFY independent PASS (0 real completions lost, 0 false admitted across 823).

**Sweep — Phase 2-MONITOR FULL 2018-2025 tuned pass COMPLETE (8 detectors, read-only).** Thresholds confirmed; ran across all 8 years.
- **ACCURACY**: match 79-94%/yr, **all sub-90 = categorized COVERAGE gap not correctness** (we-have/city-lacks=0 in 7/8 years; 100% evidentiary every year). 2025 has +2 we-have/city-lacks (NEW — investigate).
- **D8 channel-split (the acquisition list)**: 99 missing completions 8-yr = **69 INGESTION (in feed, load) + 30 ACQUIRE (CPRA request)**. ~70% closes by loading the feed. Completion-match gap is consistent (NOT collapsing in recent years); the housing-permit backlog grows (137→964) but is mostly under-construction/un-matched, not completed.
- **PLACEHOLDER**: stubs concentrate 2024(46)/2025(51) — recent entitlement-date placeholders (NEW pattern). **D5**: 0-2/yr (consistent). **OUTLIER (de-noised)**: 0 except 2025 proj154 (counted, no completes sibling — NEW). **D6**: 0 all years — structurally under-powered (CPRA vs description NOT independent; needs assessor). **D7/DEPENDENCY**: 103 mis-binned / 0 stale.
- **NEW patterns (older-year blind spots)**: (1) 2025 +2 city-lacks-we-have; (2) 2024-25 stub concentration; (3) proj154 no-completes-sibling; (4) D6 non-independence.
- **Calibration calibration (2018-2019 detail)** retained in git history.
- **D7-SCOPE**: 103 planning records (ZP/PLN/DRCF) mis-binned in the completion-ambiguous set → **real harvest queue = 54 B-permits** (26 terse-candidate + 28 genuine-uncertain), not 157.
- **PLACEHOLDER**: 91 year-precision event-date stubs (51 `@2025-01-01`, 40 `@2024-01-01`) + 33 zero-unit projects. (CO count already rejects the 2 CO stubs; the rest are entitlement/Table-A date-quality.)
- **ACCURACY** (vs CKAN reconcile-target): CY2018 **89%**, CY2019 **84%** — gap is **entirely COVERAGE** (we-have/city-lacks = 0; city-has/we-lack = 7/17), **100% evidentiary** on our side. Below-90 = a categorized coverage finding, not a correctness failure.
- **D5-TEMPORAL**: 13 ordering violations, mostly the `2025-01-01` entitlement-stub class (cross-confirms PLACEHOLDER); 2-3 genuine (proj91, proj161).
- **D8-COMPLETENESS** (parse corrected & complete): both feed files parsed (header @ `PermitNumber` row, stdlib) → **30,764 unique B-permits** (sanity confirmed). Per-year **RAW gap** ~3,600/yr (mostly non-housing) vs **HOUSING gap** (UnitsAdded>0/ADU/new-dwelling): 137(2018)→964(2024), growing. **D8↔ACCURACY CONFIRM** by APN: the city-has/we-lack completion gap self-categorizes — 14/24 (2018-19) = **ingestion-backlog** (permit already in feed, load it), 10/24 = **acquire** (absent from feed → pre-window CPRA). = the Phase-4 acquisition list, derived. (Feed dates are Excel serials — convert on any future ingest.) 13 orphan completions; Table B absent from mirror (known).
- **OUTLIER**: too loud — fires on expected main+subsidiary mixed-verdict and the bimodal ADU+tower size tail. **Needs tuning.**
- **DEPENDENCY**: 0 stale-source fires + the **`housing_rules` false-absent meta-catch** (a builder almost recomputed canonical cycle/tier logic inline off `ls scripts/housing_rules.py` — it's a package dir, committed `7165f3b`). First recorded DEPENDENCY catch.
- **D6-CONSISTENCY**: under-powered for SFR/ADU years (no multi-unit description counts; assessor lacks reliable unit counts).

**Site / publish state (2026-06-16) — verified against `git ls-remote`.**
- Completion display **derives from `co_date`** (`export_explorer_data_v2.py`); CO stat == map markers by construction. Non-v2 export sequestered. **Published completion count = 703** (raw view 705, 2 migration stubs rejected). The committed `docs/explorer_data.js` is **current with the DB** (regen diff = timestamp-only; **895 markers**, dedup'd).
- **`origin/main` = `d50a510` (verified `git ls-remote` 2026-06-29)** carries the 703 publish +
  income-tiers/R2 links + **the RHNA-honesty + CY2023 fix** (RHNA bar HELD live — `origin/main:docs/explorer.js`
  has the "RHNA progress BAR HELD" marker; `440aa8c` rode in via the curriculum merges) + the **Data Science
  Curriculum** (`539173b` + ~9). **The live site is NOT overclaiming RHNA — already fixed.**
- **~~a525a3a staged deploy~~ ABANDONED 2026-06-29 — REDUNDANT.** Its RHNA + CY2023 payload is **already
  on `origin/main`** (440aa8c is an ancestor of main). Also stale/non-FF (main moved `7e445a3→d50a510`); the
  `/tmp/berkeley-main-deploy` worktree is **gone** (purged). **Nothing to push or purge for a525a3a.**
- **Assessed-value/property-tax explorer feature — READY ON DEV, deploy-to-main PENDING (John):**
  - **dev feature-complete:** `45617b2` (export wiring + `v_projects_flat`) + `5530ff3` (render,
    `docs/explorer.{html,js}`) + `62d2554` (data: 672 assessed values in BOTH `explorer_data_v2_working.js`
    + served `explorer_data.js`). All on dev, **none on `origin/main`.**
  - **⚠ PIPELINE GOTCHA (cost a 3-round discovery — recorded so it isn't re-learned):**
    `export_explorer_data_v2.py` hardcodes `BASE_DIR=/Users/johngage/berkeley-data` and writes
    **`docs/explorer_data_v2_working.js`** (a STAGING file), **NOT** the served `docs/explorer_data.js`.
    Promotion to served = a **MANUAL hand-copy** (`_v2_working.js` → `explorer_data.js`), no automated step.
    ⟹ **worktree-hostile** (the script always writes the main tree) and **"regen" alone does NOT update the
    served file — you must copy.** (CLAUDE.md elides this: it says `explorer_data.js` "generated by
    export_explorer_data_v2.py", omitting the `_v2_working.js` staging + hand-copy.) **`62d2554` already did the
    promote+commit → NO fresh regen needed for this deploy** (data exists, committed, on dev).
  - **DEPLOY PATH (John, when ready):** cherry-pick the **3** commits (`45617b2`, `5530ff3`, `62d2554`) onto
    current `main` (`d50a510` — preserves curriculum, conflict-free per the divergence check) → `push origin
    main` → **Cloudflare purge `explorer.html` + `explorer.js` + `explorer_data.js`**. **NO regen step** (data
    is in 62d2554). **Verify-live:** a completed project shows a `$` assessed value, the civic aggregate
    renders, pipeline/UC projects show blank (correct by design — assessed is completed-only).
  - **⚠ 5 unrelated dirty WIP files on dev** (D6/D7 notebooks, `classifiers.py`, `v2_corrections_seed.csv`,
    `shake_findings_…_full.json`) — **NOT part of this deploy, leave untouched.** They blocked an in-place
    `checkout main` this session; still need their own disposition (stash/commit/discard) someday.
- **⚠ DIVERGENCE (reconcile before any dev→main):** curriculum (`539173b` + ~9) is **MAIN-ONLY** (never merged
  back to dev); **dev** has the 3-commit assessed-value feature (`45617b2`+`5530ff3`+`62d2554`) + this session's v4/docs/notes (not served). `dev→main` is
  **non-FF and would LOSE the curriculum** — don't blind-push. Fix: merge `origin/main` into `dev` so dev is the
  superset again, then dev→main is a clean FF.

---

## Next steps (current queue, 2026-06-16)
0. **DEPLOY (John):** assessed-value/property-tax feature is **READY ON DEV** (3 commits `45617b2`+`5530ff3`+`62d2554`; data committed, **no regen needed**). Cherry-pick the 3 onto `main` (d50a510, conflict-free) → push → purge `explorer.{html,js}` + `explorer_data.js`. See *Site / publish state* for the pipeline gotcha + verify-live. (a525a3a abandoned-redundant; the dev↔main curriculum divergence is a SEPARATE hygiene item — **NOT a blocker** for this cherry-pick.)
1. **`parcel_crosswalk`** (prior-APN + split/merge lineage) — the **durable re-platting fix**; absorbs the **15 orphaned APNs** (Acheson Bldg B/umbrella proj900/178, completed-2022 proj901/904/905, proj349 re-plat) + gives APN-joins a stable identity. R1's refreshed assessor + BOOK/PAGE/PARCEL + LatestDocumentDate is the baseline to diff against. Own session.
2. **Full-city-BP-stream acquisition** (Berkeley open-data/Accela BP feed incl. the ADU/infill tail) — **the prerequisite for a trustworthy RHNA progress bar** (currently HELD; tracked-project BP credit is coverage-limited at 1,198/13.4%).
3. **HARVESTER sub-record fix** — `harvest_plansets` scrapes only the MASTER's attachments, never iterates `url_discovery`'s REV/DEF sub-records → misses revision docs on multi-rev projects (ZP + B); also drop the ZP-assert, use module=Building, relax the >5MiB filter for B-permits. proj136 REV14 PDF→R2 waits on this.
4. ~~**Item 3 — `scripts/shake_detectors.py`**~~ **DONE 2026-06-16** (built, calibrated, full-run, triaged — see top entry). Findings file `data/audit/shake_findings_2026-06-16_full.json` is the standing triage queue; re-run any time (read-only). Most findings route to the `parcel_crosswalk` (#1 queue item).
5. **proj512/552 unit-count via permit** — address has more built condo parcels (4/3) than recorded units (2/2); resolve dwelling count from the permit, hold parcel assignment (source-disagreement rule).
6. **Small view/data fixes:** `bp_issued_date` materialization gap; proj126 status mislabel; proj183/184 `is_primary`.
- **Downstream deliverable (after correctness clears):** the per-year APR↔CKAN reconciliation (generate_apr_v2 → diff vs CKAN read-only target → categorize COVERAGE / CITY-UNDER-REPORT / COUNTING-CONVENTION), built on the D7 bijection.

## Parked
- Optimizer watchers (ACQUISITION-YIELD) — next sweep.
- **5-project pre-window CPRA request** (proj175/481/505/525/555 — `B2016/2017` permits the harvester can't reach).
- **proj117 / proj32 (the two 0-inspection harvester extractions)** — **RETRY THE HARVESTER FIRST** (per the new CLAUDE.md rule: no-capID/0-result is often transient — the 2026-06-15 retry resolved 5/6). Only escalate to CIC if a retry still returns 0. Low priority, uncounted either way.
- Exclude the **103 D7 planning records** from the completion harvest queue (queue hygiene).

## Open decisions / risks
- **a525a3a ABANDONED (redundant)** — its RHNA/CY2023 content already shipped to `origin/main` via the curriculum merges. Open deploy item is now `5530ff3` (property-tax) + the dev↔main reconciliation — see *Site / publish state*.
- **OUTLIER threshold un-tuned** — fires on expected patterns; calibrate before the full run.
- **D6 needs a third independent unit source** — assessor unit counts unreliable; D6 weak in SFR years.
- **Year-precision entitlement date stubs** (51 `@2025-01-01` + 40 `@2024-01-01` events) — data-quality issue on the Table-A/cycle side, not yet addressed; affects cycle-segmentation precision.
- **`contested` basis deferred (0)** — awaits post-harvest reconciliation with genuinely-independent third sources (staff reports / AHCPs / inspections); never from CKAN-disagreement (circularity).

---
*Prior narrative PROGRESS retained in git history (rewritten as a current-state snapshot 2026-06-15; current-state sections — top, Site/publish state, Next steps, Open decisions — reconciled 2026-06-16 to the actual git/deploy + RHNA state. The dated entries below the top are a historical log; their point-in-time numbers, e.g. the 674/672/705 ingest-era counts, are NOT current — current published = 703.)*
