# REBUILD RESUME — next stage is S6 (build_v2_from_sources)

Read this + `build_v2_from_sources_spec.md` + `build_v2_lessons.md` before acting. SIX gated stages (S0–S5)
built, validated, regression-locked, isolated in `berkeley_housing_v3.db`. Live `berkeley_housing_v2.db`
byte-identical/untouched (sha256 `d6a1a960…`), the S8 cross-check. Continuing a gated DAG; verdict (B)
re-derive-structured-column-first is settled — don't re-litigate.

## DONE and in v3 (gated, idempotent, regression-locked — verify against live DB before building)
- **S0 — clean key index.** `s0_keys.py` (normalize_address + matches() type-wildcard + disambiguate_distinct;
  canonicalize_apn→housing_rules.to_canonical_apn; is_adu). `s0_key_index` 895, `s0_protected_pairs` 3,
  `s0_s8_review_buckets` 5. `test_s0_gate.py`.
- **S1 — CPRA spine (corrected).** `build_s1.py` + `housing_predicates.py` (is_housing, net_units).
  `s1_projects` **1,385** = 670 CREATE/1,383u + 715 ATTACH. 568u Tier-1 + 265 recovered ADUs. Queues:
  `s1_apn_overlap` 11, `s1_s4_unit_reconcile` 6 (resolved in S4), `s1_xaddr_review` 21. `test_s1_gate.py`.
- **S2 — dated events.** `build_s2.py`. `s2_events` **2,236** (BP 1,285 + CO 951 is_inferred=0 structured;
  entitlement 0 — real no-overlap). `s2_date_reconcile` 3 (CPRA-vs-v2 finaled-date → S8). `test_s2_gate.py`.
- **S3 — event-derived stage.** `build_s3.py`. `s3_stage` **1,385** (completed 951 · permitted 340 ·
  entitled 0 · pipeline 94), 0 asserted, co↔completed 1:1. `s3_stage_reconcile` 33 (→ S8, incl. 14
  v1=completed→pipeline). 265 ADUs: 154 completed/108 permitted/3 pipeline. `test_s3_gate.py`.
- **S4 — evidence-reconciled units.** `build_s4.py`. `s4_units` **1,385** (canonical = net_units).
  `s4_unit_reconcile_resolved` 6: 5 RESOLVE_OURS (1500 SanPablo→170, 739 Channing→14, 2328 Channing→13,
  2317 Channing→17, 2330 Blake→6 — v2 under-count/null-gap/self-contradiction) + 2352 Shattuck → FLAG-S8
  (Logan Park multi-building, held 135). `test_s4_gate.py`.
- **S5 — affordability (fabrication stripped).** `build_s5.py`. `s5_affordability` **1,406** = 1,385
  needs_acquisition (built-spine, tier unknown) + 21 cited tier rows (9 projects × VLI/MOD/ABOVE_MOD).
  The migration's 704 "citations" pointed at the PERMIT FEED itself (untyped stub) — their fabricated
  tier values are GONE (not imported, not demoted). Only 9 genuine (density_bonus_application ×8 +
  affordable_housing_agreement ×1=proj35), all PIPELINE, reconciling to planned totals. MOD tiers
  (proj8/15/35) now representable (the 2-bucket fix). `test_s5_gate.py` asserts the no-fabrication guard.

## FINDINGS so far, kept distinct (do not conflate)
- Stage over-assertion: 33 (s3_stage_reconcile, incl. 14 uncorroborable completions) → S8.
- Entitlement-event gap: 757 = missing entitlement DATES (acquisition), NOT stage over-assertion.
- Unit reconciles: 5 v2-errors corrected + 1 multi-building flagged (2352 Shattuck) → S8. Date findings: 3.
- **Affordability is invisible in the built-permit record:** 0 of 1,385 built buildings have a genuine
  affordability source; the only tier data is for 9 entitled projects. The transparency-ordinance argument
  made structural — you can reconstruct how much housing got built from permits, but not who it's for.

## SHARED MODULES (single-sourced, imported, wiring-guarded)
`s0_keys` (address key, APN canon, is_adu) · `housing_predicates` (is_housing, net_units) · `gating.py`
(snapshot_v3 — refuse-to-clobber + --no-snapshot). Corrected unit signal (do NOT revert):
`net_units = ua if ua>0; nu if New; min(nu,2) if ADU; else 0`; building = MAX over permits.

## NEXT: S6 — confidence = f(source presence)
Compute EVERY fact's confidence from what actually backs it; retire the migration's blanket `high`. This is
the direct fix for the migration stamping confidence=high on inferred/fabricated data.
- The RULE: confidence is a function of the evidence behind each fact — e.g. structured-column-backed +
  multi-source-corroborated = high; single structured source = medium; inferred/needs_acquisition = low.
  Define the tiers precisely against what each stage already recorded (S2 is_inferred, S5 basis=cited vs
  needs_acquisition, the reconcile flags).
- Likely a fact-level confidence applied across the stages (unit count, stage, dates, affordability tier),
  derived from: is the value structured-column-backed? corroborated by ≥2 sources? cited to a real typed
  doc? or inferred/flagged? NEVER a constant.
- Build `build_s6.py` (imports s0_keys + housing_predicates + gating) + `test_s6_gate.py` + wiring guard.
  Preview → ENFORCED gate → STOP → write `s6_confidence` → fingerprint → idempotency (--no-snapshot).
- S6 gate (suggested): 0 facts at confidence=high without real backing (the migration's exact bug — assert
  it can't recur); confidence distribution is sensible (the 9 cited affordability = high, the 1,385
  needs_acquisition = low, structured units/dates = high, the 33 reconcile-flagged stages = low/flagged);
  no blanket-constant confidence; unit totals unchanged; s0–s5 untouched.

## Remaining DAG after S6
S7 cycle-scope (wire housing_rules; flag which of the 951 completions + 265 ADUs fall in the RHNA reporting
window vs prior-cycle — the open A2-comparison question; e.g. 2001 Fourth Finaled 2018 may be prior-cycle) ·
S8 reconciliation matrix + v1 cross-check (gathers s2_date_reconcile 3 + s3_stage_reconcile 33 + the 2352
Shattuck/Logan-Park + proj179 N/S multi-building CATEGORY) · S9 the A2 (vs CKAN-mirror oracle = Berkeley's
submitted APR). Build into v3; swap to canonical only on passing all gates; v2 preserved as cross-check.

## Acquisition queue (off-disk harvest backlog)
1. Affordability tiers: ~704+ built/pipeline projects need genuine harvesting (their current "affordability"
   was fabricated stub-citations, now stripped to needs_acquisition by S5). The REAL backlog is built-
   project affordability (the 951 completed / ~4,310u of the A2 population) — a DIFFERENT population than the
   9 entitlement-doc pipeline projects. `harvest_affordability.py` is the tool; the 9 cited are done.
2. Entitlement dates: ~33 discretionary projects / ~2,253u — the .txt corpus does NOT cover the spine
   (91 files, 4 approvals, 0 at spine buildings) → needs acquisition.

## Discipline (keep it)
Snapshot (functional) → preview → ENFORCED gate → STOP for John → guarded txn → fingerprint → idempotency
(--no-snapshot). Anti-drift: single-source every concept AND infrastructure helper, wiring-guarded. VERIFY
A ZERO (clean/empty/"no change"/0-result is a hypothesis to verify — this session a clean result was
repeatedly a measurement bug: a dead type-branch, a mis-based diff, a clobbered snapshot, an over-strict
test on 0-unit buildings; confirm the check RAN and the zero is real). Measure before refactor. Resolve
source disagreements by EVIDENCE, flag the unresolvable → S8, never default to a source. Demoting confidence
≠ removing a fabrication (S5 lesson — don't carry fabricated values at low confidence; exclude them).
A populated provenance field is not proof of provenance — verify what it points at (the 704 stubs).

## Snapshots
Clean rollback points: pre-s2.db … pre-s5.db (shared gating, refuse-to-clobber). Old pre-s1/pre-s1-rerun are
stale/clobbered — ignore; deterministic rebuild is the recovery path.

## VERIFY-A-ZERO ran hot this session (the through-line)
Every clean-looking empty/zero result was checked, not trusted, and split between real findings (entitlement
no-overlap — real; the 81 zero-unit buildings — genuinely non-dwelling) and hidden bugs (the +0-ADU dead
type-branch; the mis-based 265-delta diff; the systemically-clobbered snapshots). Not accepting a zero at
face value is why S2–S5 + the S1 foundation correction all landed correct.
