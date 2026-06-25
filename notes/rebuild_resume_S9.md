# REBUILD RESUME — next stage is S9 (build_v2_from_sources)

> **CANONICAL resume doc for the rebuild. Single source going forward** — chat-Claude does not write
> parallel resume docs (two diverging copies was the hazard). Re-read this at the start of the S9 session,
> and **re-upload it after any context compression.** Every number below is grounded in the LIVE
> `berkeley_housing_v3.db` (verified 2026-06-17), not just conversation memory — when they disagree, the
> DB wins, so re-query before relying on a count.

Read this + `build_v2_from_sources_spec.md` + `build_v2_lessons.md` before acting. NINE gated stages
(S0–S8) built, validated, regression-locked, isolated in `databases/berkeley_housing_v3.db`. Live
`databases/berkeley_housing_v2.db` byte-identical/untouched (**sha256 `d6a1a9603922390c…`**) — the S8/S9
cross-check substrate, READ-ONLY, never written. Continuing a gated DAG; verdict (B)
re-derive-structured-column-first is settled — don't re-litigate. The honesty layer (provenance +
confidence + cycle-scope + reconciliation) is COMPLETE; **S9 is the payoff: the A2 — v3 vs the city.**

## NEXT: S1.5
NEXT: S1.5 building-identity split — see `notes/s1_5_v1_design.md` (design complete, pre-build).

## DONE and in v3 (gated, idempotent, regression-locked — LIVE counts 2026-06-17)
- **S0 — key index.** `s0_key_index` **895**, `s0_protected_pairs` **3**, `s0_s8_review_buckets` **5**.
- **S1 — CPRA spine.** `s1_projects` **1,385** = 670 CREATE + 715 ATTACH (Σunits 5,705). 568u Tier-1 + 265
  recovered ADUs. Queues: `s1_apn_overlap` **13**, `s1_xaddr_review` **22**.
- **S2 — dated events.** `s2_events` **2,236** = BP 1,285 + CO 951, ALL is_inferred=0. `s2_date_reconcile` **3**.
- **S3 — event-derived stage.** `s3_stage` **1,385** = completed 951 · permitted 340 · pipeline 94 (co↔completed
  1:1). `s3_stage_reconcile` **33** (incl. 14 v1=completed→pipeline).
- **S4 — evidence-reconciled units.** `s4_units` **1,385**. `s4_unit_reconcile_resolved` **6** (5 RESOLVE_OURS
  + 2352 Shattuck FLAG_S8).
- **S5 — affordability.** `s5_affordability` **1,406** = 9 cited + 1,219 market_rate_no_obligation + 166
  needs_acquisition. 0 market=units−vli.
- **S6 — confidence = f(source presence).** `s6_confidence` **5,549** fact rows. 0 high-without-backing.
- **S7 — cycle-scope (THREE date concepts; housing_rules re-wired).** `s7_cycle` **2,236** = BP 1,285 + CO 951.
  Per event: `reporting_year` · `calendar_cycle` (5th 1,201 / 6th 1,035 @ 2023-01-31) · `in_projection_period`
  (162, narrow 2022-06-30→2023-01-30) · `rhna_credit_cycle` (building-level, first-BP≥2022-06-30; over
  `is_first_bp`: 6th 650 / 5th 635; **6 CO-only-no-BP → NULL flagged**). **94 BP calendar=5th but credit=6th.**
  `housing_rules.rhna_credit_cycle` added (boundary from PROJECTION_PERIODS, not RHNA_CYCLES).
- **S8 — reconciliation matrix (synthesis, gather not re-derive).** `s8_reconciliation` **90 findings, 10
  DISTINCT finding_types**, each gathered row's basis COPIED from a live source table:
  - **date_reconcile 3** (==`s2_date_reconcile`; all 3 cross a reporting year, B2018-03576 a 5yr gap that
    also shifts calendar_cycle → `resolved_ours_evidence|s9_year_watch`)
  - **stage_reconcile 33** (==`s3_stage_reconcile`; `held_flagged`, never auto-resolved)
  - **unit_reconcile 6** (==`s4_unit_reconcile_resolved`; 5 resolved_ours_evidence + 1 held_flagged)
  - **apn_overlap 13** · **xaddr_review 22** (==`s1_*`; held_flagged / benign_match)
  - **multi_building_development 1** (2352 Shattuck/proj179; scan v2_total>1.3×MAX found exactly 1 member)
  - **measurement_basis 4** (UC beds-vs-units; see below)
  - **rhna_scope_question 1** + **entitlement_date_gap 1** (soft pointers, not row-materialized)
  - **crosscheck_summary 6** (v2-vs-v3 headline)

Each stage has `test_sN_gate.py` (**all 9 green, s0–s8**) with a fails-if-not-CALLED wiring guard.
Snapshots (refuse-to-clobber): **pre-s2.db … pre-s8.db + pre-s5-obligation.db** (pre-s7/pre-s8 survived
their idempotency re-runs sha-identical). Old pre-s1/pre-s1-rerun stale — ignore.

## THE THREE MUST-NOT-CONFLATE DATE CONCEPTS (S7 contract — do not collapse in S9)
| concept | boundary | function | feeds |
|---|---|---|---|
| `calendar_cycle` | 5th/6th @ **2023-01-31** (RHNA_CYCLES, later cycle owns shared date) | `cycle_for_date` | which cycle a date sits in |
| `in_projection_period` | narrow **2022-06-30 → 2023-01-30** (bool) | `is_projection_period` | per-event bridge flag |
| `rhna_credit_cycle` | **first-BP ≥ 2022-06-30**, no upper cap | `rhna_credit_cycle` | which 8-yr allocation a unit's RHNA credit counts toward |
RHNA credit is at **building-permit issuance, NOT CO**. The 2022-06-30 credit boundary ≠ 2023-01-31; proof: 94 BP events calendar=5th but credit=6th.

## THE UC BEDS-VS-UNITS RULE (S8 measurement_basis — load-bearing for any unit-total work)
The 4 UC residences (`uc_project` classification type 6 in v2 = proj **165/170/171/177**) are measured in
**BEDS**, and UC has an OFFICIAL bed→unit conversion we must use; **our ad hoc conversion is a fabricated
value by our own standard** (same class as market=units−vli). **None are in the v3 CPRA spine** (UC exempt
from city permitting) → **0 v3 units at-risk**. v2 carried **2,628** bed-derived "units" (550/772/750/556).
- **proj170 Anchor House (1950 Oxford):** `sourced_both` — units=**244** apartments (sourced, doc 2178) +
  beds=**772** (sourced). NEVER carry 772-as-units.
- **proj165 / 171 / 177:** `pending_uc_conversion` — beds sourced (**1,625 / ~1,500 / 1,113**), units=NULL.
  This disposition is DISTINCT from `needs_acquisition`: size is KNOWN (beds), only UC's authoritative
  conversion is missing. The ad hoc 550/750/556 are REJECTED, never asserted.

## NEXT: S9 — the A2 (v3 vs the CKAN-mirror oracle = Berkeley's submitted APR)
The payoff: compare v3's by-cycle completions + the cycle-scoped facts to **`databases/hcd_apr_mirror.db`**
(the city's submitted APR; ORACLE / reconcile-target ONLY, NEVER a data source — role-crossing is the
circularity bug). Build `build_s9.py` (imports s0_keys + housing_predicates + gating + housing_rules) +
`test_s9_gate.py` + wiring guard (the fails-if-not-CALLED spy template). Preview → ENFORCED gate → STOP for
John → guarded write `s9_*` → fresh-connection fingerprint → idempotency (`--no-snapshot`, pre-s9 survives).
- **ORACLE GAP (load-bearing):** the mirror has `table_a / a2 / d / f / i / k / l` but **NO Table B** — RHNA
  progress is ABSENT. So the completions comparison runs vs Table A/A2 (CO↔CO, by year), but the **492/503
  BP-credit cross-check is SOFT/text vs the city's separately-published figure**, NOT the mirror.
- **Align like-for-like:** completions↔completions by reporting_year (use `s7_cycle.reporting_year`), tiers
  via `table_a2`'s income×DR/NDR×milestone shape (the Q1/G1 work already proved the 69-col A2 structure).
  NEVER compare v2's 16,808 Σunits to v3's 5,705 (different populations — see crosscheck below).
- **Carry the S8 findings into S9 as watch-items:** the 3 date `s9_year_watch` (a CO's year may differ from
  the city's), the multi_building development-vs-per-building counting, the UC measurement_basis (excluded
  both sides? confirm the city's treatment), and the 492/503 scope question.

## v2-vs-v3 CROSS-CHECK (S8 crosscheck_summary; v2 read-only sha d6a1a960)
| | v2 | v3 | story |
|---|---|---|---|
| projects/buildings | 895 | 1,385 | per-building granularity + ADU-tail |
| completions | 704 | **951** | completions RECOVERED |
| Σ units | 16,808 | 5,705 | **DIFFERENT POPULATIONS** (v2 incl. pipeline towers + UC beds; v3 = built/permitted spine net_units) — never compare these two |
| affordability cited | 704 stub | **9** | fabrication STRIPPED |
| confidence high-without-backing | blanket | **0** | confidence EARNED |
| UC bed-unit basis | 2,628 v2 units | 0 in spine | measurement-basis bucket |

## SHARED MODULES (single-sourced, imported, wiring-guarded — anti-drift)
`s0_keys` · `housing_predicates` (is_housing, net_units — **deliberately NOT called in gather-only stages;
re-deriving would violate "gather, not re-derive"**) · `gating.py` (snapshot_v3 refuse-to-clobber +
`--no-snapshot`) · **`housing_rules`** (cycle_for_date · is_projection_period · rhna_credit_cycle [S7] +
lookups). Wiring guard = the **fails-if-not-CALLED spy** (S7/S8 template).

## Acquisition queue (off-disk harvest backlog)
1. **Affordability tiers — the 75 obligated buildings (4,308u)**, large-first (27 obligated-completed-≥50u =
   2,529u tightest). The 9 cited done; the 1,219 market_rate_no_obligation need nothing. 10 marginal 3-4u
   held until floor-area acquired.
2. **Entitlement dates — ~33 discretionary projects / ~2,253u** (the entitlement-DATE gap; .txt corpus does
   not cover the spine).
3. **UC official bed→unit conversion / unit counts for 165/171/177** (170 resolved at 244; beds all sourced).

## QUEUED (anti-drift, noted not done)
Refactor `generate_apr_v2.generate_rhna_progress` to import `housing_rules.rhna_credit_cycle` instead of
inlining the 2022-06-30 boundary — S7 now single-sources it.

## Discipline (keep it — every stage)
Snapshot (proven) → preview → ENFORCED gate → STOP for John → guarded txn → fresh-connection fingerprint →
idempotency (`--no-snapshot`). **Anti-drift:** single-source every concept AND infra helper, wiring-guarded
with a **fails-if-not-CALLED spy**; and a function deliberately NOT called (net_units in gather-only stages)
is correct behavior the gate asserts too. **VERIFY A ZERO / verify the COUNT against the LIVE DB** (S7's
"100"→6; S8's exact-count vs live source tables caught the 11→13/21→22 staleness class). The reconciliation
matrix's job is to **gather every finding distinctly, count them exactly** (off-by-N = dropped/double-
gathered), not to resolve them. **CKAN mirror = ORACLE only, never a data source (circularity).** Surface a
city-number difference; do not tune toward it. A disposition can encode honesty the data can't
(`pending_uc_conversion` ≠ `needs_acquisition`).
