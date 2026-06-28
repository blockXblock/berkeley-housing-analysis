> **SUPERSEDED — S8 is DONE.** The canonical resume doc is now **`notes/rebuild_resume_S9.md`** (the single
> source going forward; live-DB-grounded). This file is a historical snapshot from when S8 was next. Do not
> rely on it for current counts.

# REBUILD RESUME — next stage is S8 (build_v2_from_sources)

> **CANONICAL resume doc for the rebuild. This is the single source going forward** — chat-Claude no longer
> writes parallel resume docs (two diverging copies was the hazard). Re-read this at the start of the S8
> session, and **re-upload it after any context compression.** Every number below is grounded in the LIVE
> `berkeley_housing_v3.db` (verified 2026-06-17), not just conversation memory — when they disagree, the DB
> wins, so re-query before relying on a count.

Read this + `build_v2_from_sources_spec.md` + `build_v2_lessons.md` before acting. EIGHT gated stages
(S0–S7) built, validated, regression-locked, isolated in `databases/berkeley_housing_v3.db`. Live
`databases/berkeley_housing_v2.db` byte-identical/untouched (**sha256 `d6a1a9603922390c…`**) — it is the S8
cross-check, READ-ONLY, never written. Continuing a gated DAG; verdict (B) re-derive-structured-column-first
is settled — don't re-litigate. The "honesty layer" (provenance + confidence + cycle-scope) is COMPLETE;
S8–S9 USE it to produce the APR comparison.

## DONE and in v3 (gated, idempotent, regression-locked — LIVE counts 2026-06-17)
- **S0 — clean key index.** `s0_keys.py`. `s0_key_index` **895**, `s0_protected_pairs` **3**,
  `s0_s8_review_buckets` **5**.
- **S1 — CPRA spine (corrected).** `s1_projects` **1,385** = **670 CREATE + 715 ATTACH** (Σunits 5,705).
  568u Tier-1 + 265 recovered ADUs (net_units rule). Queues: **`s1_apn_overlap` 13**, `s4_reconcile` 6
  (resolved), **`s1_xaddr_review` 22**.
- **S2 — dated events.** `s2_events` **2,236** = **BP 1,285 + CO 951, ALL is_inferred=0** (structured;
  entitlement none-asserted). `s2_date_reconcile` **3** → S8.
- **S3 — event-derived stage.** `s3_stage` **1,385** = **completed 951 · permitted 340 · pipeline 94**
  (no `entitled` bucket; co↔completed 1:1). `s3_stage_reconcile` **33** → S8 (incl. 14 v1=completed→pipeline).
- **S4 — evidence-reconciled units.** `s4_units` **1,385**. `s4_unit_reconcile_resolved` **6**: 5 RESOLVE_OURS
  + 2352 Shattuck FLAG-S8.
- **S5 — affordability (fabrication stripped + obligation-partitioned).** `s5_affordability` **1,406** =
  **9 cited (pipeline, typed-doc)** + **1,219 market_rate_no_obligation** + **166 needs_acquisition** (75
  obligated harvest-target inside it). 0 market=units−vli.
- **S6 — confidence = f(source presence).** `s6_confidence` **5,549 fact-level rows**. 0 high-without-backing
  (asserted). Confidence VARIES per-building in 1,304/1,385.
- **S7 — cycle-scope (THREE date concepts; housing_rules RE-WIRED).** `s7_cycle` **2,236 event rows**
  (**BP 1,285 + CO 951**). Per event: `reporting_year` · `calendar_cycle` (**5th 1,201 / 6th 1,035** @
  2023-01-31) · `in_projection_period` (**162** events, narrow 2022-06-30→2023-01-30) · `rhna_credit_cycle`
  (building-level, first-BP ≥ 2022-06-30; over `is_first_bp` rows **6th 650 / 5th 635**; **6 CO-only-no-BP →
  NULL flagged**). **94 BP events calendar=5th but credit=6th** (the non-conflation, proven). **0 asserted
  reporting_years.** Added **`rhna_credit_cycle`** to `housing_rules/classifiers.py` (boundary from
  `PROJECTION_PERIODS` 2022-06-30, NOT `RHNA_CYCLES['6th']` 2023-01-31); `test_s7_gate.py` **TRIPLE wiring
  guard asserts all three hr functions CALLED** (not just imported).

Each stage has `test_sN_gate.py` (**all 8 green, s0–s7**) with a fails-if-not-called wiring guard.
Snapshots (refuse-to-clobber): **pre-s2.db … pre-s7.db + pre-s5-obligation.db** (pre-s7 survived its
idempotency re-run sha-identical). Old pre-s1/pre-s1-rerun stale — ignore (deterministic rebuild is recovery).

## THE THREE MUST-NOT-CONFLATE DATE CONCEPTS (S7's standing contract — do not collapse in S8/S9)
One milestone date answers three different questions, each used by a different APR table:

| concept | boundary | function | what it feeds |
|---|---|---|---|
| `calendar_cycle` | 5th/6th @ **2023-01-31** (RHNA_CYCLES, later cycle owns shared date) | `cycle_for_date` | which housing-element cycle a date sits in |
| `in_projection_period` | narrow **2022-06-30 → 2023-01-30** bridge window (bool) | `is_projection_period` | the per-event bridge flag (D5/D6 bp_/co_in_projection_period precedent) |
| `rhna_credit_cycle` | **first-BP ≥ 2022-06-30**, NO upper cap (PROJECTION_PERIODS start) | `rhna_credit_cycle` | which 8-yr allocation a unit's RHNA *credit* counts toward |

- **RHNA credit is earned at building-permit issuance, NOT CO.** First-BP = `MIN(non-subsidiary
  building_permit_issued)` (in v3 each building has ≤1 BP, so MIN is trivial). The 100 / 6 trap below is
  about which milestone exists, not which boundary.
- **Non-conflation, made concrete:** the credit boundary **2022-06-30** ≠ `cycle_for_date`'s **2023-01-31**;
  and `in_projection_period` (narrow window) is NOT the credit filter (credit spans 2022-06-30 → cycle end).
  Proof in the data: **94 BP events are calendar=5th but credit=6th.** (CLAUDE.md:179 makes this load-bearing.)

## FINDINGS so far, kept DISTINCT (→ S8 gathers them into the reconciliation matrix, NOT conflated)
- **Stage over-assertion: 33** (`s3_stage_reconcile`, incl. 14 uncorroborable v1=completed→pipeline).
- **Entitlement-event gap: 757** = missing DATES (acquisition queue), NOT stage over-assertion — keep separate.
- **Unit reconciles:** 5 v2-errors corrected by evidence + **1 multi-building FLAG-S8 (2352 Shattuck)**.
- **Date findings: 3** (`s2_date_reconcile`).
- **Affordability invisible in the built-permit record:** only **9 of 1,385** doc-cited (all pipeline).
- **The multi-building-development CATEGORY (S8 must handle as a pattern, not a one-off):** 2352 Shattuck =
  Logan Park proj179 N/S — one development spanning multiple permits/parcels (North 168u + South 69u = 237).
  How to count a development that is several permits is the general question; per-building MAX under-counts it.
- **NEW from S7 — the 492/503 BP-credit SCOPE question (S8/S9, do NOT force a match):** city reports 6th-cycle
  RHNA **492 (CY2024) / 503 (CY2025)**, a **BP-credit** figure (the memo isn't on disk to quote; resolved by
  the HCD framework + CLAUDE.md:179). Our now-correct-milestone cumulative 6th BP-credit = **421bldg/1,792u
  thru CY2024, 648bldg/2,419u thru CY2025** (by first-BP year: 2022 +78/383u · 2023 +175/627u · 2024
  +168/782u · 2025 +227/627u · 2026 +2/2u). Does NOT reconcile to 492/503 → a **scope/population question**,
  candidate axes: annual-vs-cumulative / affordable-only (VLI+LI+MOD) / net-new-after-demo / coverage
  universe. v3's 2,419u ≫ v2's coverage-limited **1,198u** BECAUSE v3's spine includes the full CPRA
  ADU/infill tail — **v3 is the LESS-coverage-limited basis** for the S9 reconciliation. The validation's job
  is to **surface and characterize** the difference, never to tune our number toward the city's.

## SHARED MODULES (single-sourced, imported, wiring-guarded — anti-drift)
`s0_keys` (address key, APN canon, is_adu) · `housing_predicates` (is_housing, net_units) · `gating.py`
(`snapshot_v3` refuse-to-clobber + `--no-snapshot`; proven on the two-write-one-stage case at S5) ·
**`housing_rules`** (`cycle_for_date` · `is_projection_period` · **`rhna_credit_cycle`** [NEW, S7] +
cycle/projection/tier/streamlining lookups) — the once-orphaned policy module, now wired AND call-guarded.
Corrected unit signal (do NOT revert): `net_units = ua if ua>0; nu if New; min(nu,2) if ADU; else 0`;
building = MAX over permits.

## NEXT: S8 — reconciliation matrix + v1/v2 cross-check
Gather the distinct findings above into ONE auditable matrix (kept distinct, never conflated):
`s2_date_reconcile` 3 + `s3_stage_reconcile` 33 + the unit FLAG-S8 (2352 Shattuck / Logan-Park proj179 N/S
= the multi-building-development CATEGORY) + the **492/503 BP-credit scope question** from S7. Cross-check v3
against the live `berkeley_housing_v2.db` (**READ-ONLY** — it is the cross-check, never written). Build
`build_s8.py` (imports s0_keys + housing_predicates + gating + housing_rules) + `test_s8_gate.py` + wiring
guard (the **fails-if-not-CALLED spy** template from S7). Preview → ENFORCED gate → STOP for John → guarded
write `s8_*` → fresh-connection fingerprint → idempotency (`--no-snapshot`, pre-s8 survives).

## Remaining DAG after S8
**S9 — the A2.** Compare v3's by-cycle completions + BP-credit to the **CKAN-mirror oracle**
(`databases/hcd_apr_mirror.db` = Berkeley's submitted APR) — the payoff: independent reconstruction vs the
city's numbers. **ORACLE GAP (load-bearing):** the mirror has tables `table_a / a2 / d / f / i / k / l` but
**NO Table B** — RHNA progress is ABSENT from the mirror. So the 492/503 cross-check is against the city's
*separately-published* figure (CM memo / dashboard), NOT the mirror; the mirror oracle covers completions
(Table A/A2), not RHNA-credit. Build into v3; swap to canonical only on passing all gates; v2 preserved.

## Acquisition queue (off-disk harvest backlog)
1. **Affordability tiers — the 75 obligated buildings (4,308u)**, large-first (the 27 obligated-completed-≥50u
   = 2,529u is the tightest priority). The 9 cited are done; the 1,219 market_rate_no_obligation need nothing
   (exempt). No floor-area data in v3 (assessor has only Imps$, BuildingAr dropped) → the 10 marginal 3-4u
   stay held until floor-area is acquired or they prove obligated.
2. **Entitlement dates — ~33 discretionary projects / ~2,253u** — the .txt corpus does NOT cover the spine →
   acquire (this is the 757 entitlement-event gap's resolution path).

## QUEUED (anti-drift, noted not done)
Refactor `generate_apr_v2.generate_rhna_progress` to **import `housing_rules.rhna_credit_cycle`** instead of
inlining the 2022-06-30 boundary — S7 now single-sources it in the module (so the generator and the rebuild
can't drift on the credit boundary).

## Discipline (keep it — every stage)
Snapshot (proven) → preview → ENFORCED gate → STOP for John → guarded txn (rowcount checks) → fresh-connection
fingerprint → idempotency (`--no-snapshot`). **Anti-drift:** single-source every concept AND infra helper,
wiring-guarded with a **fails-if-not-CALLED spy** (S7's triple guard is the template — an imported-but-uncalled
function is still an orphan). **VERIFY A ZERO / verify the COUNT against the LIVE DB** (S7's Phase-A "100"
CO-only → actual **6** came from the preview, not the plan; this very note's apn_overlap/xaddr were stale in
the old S7 note — 11/21 → live 13/22). Measure before refactor. Resolve disagreements by EVIDENCE, flag
unresolvable → S8, never default. Demoting confidence ≠ removing fabrication. A populated provenance field is
not proof of provenance — verify what it points at. Not every unknown is a gap (the obligation partition).
**Surface a city-number difference; do not tune toward it.**
