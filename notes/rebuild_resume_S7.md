> **SUPERSEDED — S7 is DONE.** The canonical resume doc is now **`notes/rebuild_resume_S8.md`** (the single
> source going forward; live-DB-grounded). This file is a historical snapshot from when S7 was next; some of
> its carry-forward counts are stale (e.g. apn_overlap 11 / xaddr 21 → live **13 / 22**). Do not rely on it.

# REBUILD RESUME — next stage is S7 (build_v2_from_sources)

Read this + `build_v2_from_sources_spec.md` + `build_v2_lessons.md` before acting. SEVEN gated stages
(S0–S6) built, validated, regression-locked, isolated in `berkeley_housing_v3.db`. Live
`berkeley_housing_v2.db` byte-identical/untouched (sha256 `d6a1a960…`), the S8 cross-check. Continuing a
gated DAG; verdict (B) re-derive-structured-column-first is settled — don't re-litigate. The "honesty
layer" (provenance + confidence) is now COMPLETE; S7–S9 USE it to produce the APR comparison.

## DONE and in v3 (gated, idempotent, regression-locked — verify against live DB before building)
- **S0 — clean key index.** `s0_keys.py`. `s0_key_index` 895, `s0_protected_pairs` 3, `s0_s8_review_buckets` 5.
- **S1 — CPRA spine (corrected).** `build_s1.py` + `housing_predicates.py`. `s1_projects` **1,385** = 670
  CREATE/1,383u + 715 ATTACH. 568u Tier-1 + 265 recovered ADUs. Queues: apn_overlap 11, s4_reconcile 6
  (resolved), xaddr_review 21.
- **S2 — dated events.** `s2_events` **2,236** (BP 1,285 + CO 951, is_inferred=0 structured; entitlement 0
  real no-overlap). `s2_date_reconcile` 3 → S8.
- **S3 — event-derived stage.** `s3_stage` **1,385** (completed 951 · permitted 340 · entitled 0 · pipeline
  94), 0 asserted, co↔completed 1:1. `s3_stage_reconcile` 33 → S8 (incl. 14 v1=completed→pipeline). 265
  ADUs: 154 completed/108 permitted/3 pipeline.
- **S4 — evidence-reconciled units.** `s4_units` **1,385** (canonical=net_units). `s4_unit_reconcile_resolved`
  6: 5 RESOLVE_OURS + 2352 Shattuck FLAG-S8.
- **S5 — affordability (fabrication stripped + obligation-partitioned).** `s5_affordability`: **9 cited**
  (typed-doc, high, pipeline, MOD tiers proj8/15/35) · **1,219 market_rate_no_obligation** (1-2u, proxy-
  derived: below the 5,000-sqft / unit-proxy inclusionary threshold, basis recorded) · **166
  needs_acquisition** (75 obligated harvest-target + 10 marginal 3-4u + 81 zero-unit). The migration's 704
  "citations" pointed at the PERMIT FEED itself — values GONE (not imported, not demoted). 0
  market=units−vli.
- **S6 — confidence = f(source presence).** `s6_confidence` **5,549 fact-level rows** (per building ×
  fact_type: units/stage/dates/affordability). 0 high-without-backing (asserted — migration's blanket-high
  is structurally impossible). Distribution: units 1,303 high/82 low · stage 1,274/111 · dates 1,288/97 ·
  affordability 9 high/1,219 medium/166 low. Confidence VARIES per-building in 1,304/1,385. Tiers: high
  (structured/typed-doc/evidence-resolution) · medium (reasoned proxy, e.g. market_rate_no_obligation) ·
  low (no source/flagged-conflict/honest floor).

Each stage has `test_sN_gate.py` (all 7 green) with a fails-if-not-called wiring guard.

## FINDINGS so far, kept distinct (→ S8 gathers them)
- Stage over-assertion: 33 (incl. 14 uncorroborable completions). Entitlement-event gap: 757 = missing
  DATES (acquisition), NOT stage over-assertion. Unit reconciles: 5 v2-errors corrected + 1 multi-building
  flagged (2352 Shattuck). Date findings: 3. **Affordability invisible in the built-permit record:** only 9
  of 1,385 doc-cited (all pipeline); the transparency-ordinance argument made structural.

## SHARED MODULES (single-sourced, imported, wiring-guarded)
`s0_keys` (address key, APN canon, is_adu) · `housing_predicates` (is_housing, net_units) · `gating.py`
(snapshot_v3 — refuse-to-clobber + --no-snapshot; PROVEN on the two-write-same-table case at S5). Corrected
unit signal (do NOT revert): `net_units = ua if ua>0; nu if New; min(nu,2) if ADU; else 0`; building = MAX
over permits.

## NEXT: S7 — cycle-scope (the RHNA reporting-window question)
Tag each completion/event with which RHNA cycle / APR reporting year it falls in — the open A2-comparison
question. Wire in `housing_rules` (the orphaned cycle-aware classifier — import it, wiring-guarded, the
anti-drift discipline; this is the "re-orphan its own components" risk the rebuild must NOT repeat).
- The QUESTION: which of the 951 completions + 265 ADUs fall in the CURRENT RHNA reporting window vs a
  PRIOR cycle? (e.g. 2001 Fourth Finaled 2018 may be prior-cycle — its CO date predates the current cycle.)
  Berkeley's APR Table A reports completions BY reporting year; a completion only counts in the year its CO
  issued. So S7 assigns each completion its reporting year from the s2_events CO date.
- Likely: a `cycle`/`reporting_year` derived from the CO/finaled date (s2_events), using housing_rules'
  cycle boundaries. The 568u Tier-1 + 265 ADUs each get tagged; some 2018-era completions are prior-cycle.
- Build `build_s7.py` (imports s0_keys + housing_predicates + gating + housing_rules) + `test_s7_gate.py`
  + wiring guard (MUST assert housing_rules is actually called — it's the orphaned module being re-wired).
  Preview → ENFORCED gate → STOP → write `s7_cycle` → fingerprint → idempotency (--no-snapshot).
- S7 gate (suggested): every completion tagged a reporting year from its CO date (no asserted year); the
  cycle boundaries match housing_rules (cite them); the by-year completion counts are sensible; flag which
  Tier-1/ADU completions are prior-cycle vs current; housing_rules actually wired (guard); facts unchanged;
  s0–s6 untouched.

## Remaining DAG after S7
S8 reconciliation matrix + v1 cross-check (gathers s2_date_reconcile 3 + s3_stage_reconcile 33 + the 2352
Shattuck/Logan-Park + proj179 N/S multi-building CATEGORY — handle multi-building as a pattern, how to count
a development spanning multiple permits) · S9 the A2 (compare v3's by-cycle completions to the CKAN-mirror
oracle = Berkeley's submitted APR; this is the payoff — the independent reconstruction vs the city's numbers).
Build into v3; swap to canonical only on passing all gates; v2 preserved.

## Acquisition queue (off-disk harvest backlog)
1. Affordability tiers: the **75 obligated** buildings (4,308u) — `harvest_affordability.py`, large-first
   (the 27 obligated-completed-≥50u = 2,529u is the tightest priority). The 9 cited are done; the 1,219
   market_rate_no_obligation need nothing (exempt). NOTE: no floor-area data in v3 (assessor has only Imps$,
   BuildingAr dropped) — the 10 marginal 3-4u stay held until floor-area is acquired or they prove obligated.
2. Entitlement dates: ~33 discretionary projects / ~2,253u — .txt corpus does NOT cover the spine → acquire.

## Discipline (keep it)
Snapshot (functional, proven) → preview → ENFORCED gate → STOP for John → guarded txn → fingerprint →
idempotency (--no-snapshot). Anti-drift: single-source every concept AND infra helper, wiring-guarded
(S7 RE-WIRES the orphaned housing_rules — guard that it's actually called, or it re-orphans). VERIFY A ZERO
(this session a clean/empty result was repeatedly a measurement bug — dead type-branch, mis-based diff,
clobbered snapshot, over-strict 0-unit test; confirm the check RAN). Measure before refactor. Resolve
disagreements by EVIDENCE, flag unresolvable → S8, never default. Demoting confidence ≠ removing fabrication.
A populated provenance field is not proof of provenance — verify what it points at. Not every unknown is a
gap (the obligation partition).

## Snapshots
Clean rollback points: pre-s2.db … pre-s6.db + pre-s5-obligation.db (shared gating, refuse-to-clobber;
two-write-same-table proven at S5). Old pre-s1/pre-s1-rerun stale — ignore; deterministic rebuild is recovery.
