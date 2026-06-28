# REBUILD RESUME — next stage is S4 (build_v2_from_sources)

Read this + `build_v2_from_sources_spec.md` + `build_v2_lessons.md` before acting. The rebuild is UNDERWAY:
FOUR gated stages (S0–S3) built, validated, regression-locked, isolated in `berkeley_housing_v3.db`. Live
`berkeley_housing_v2.db` byte-identical/untouched (sha256 `d6a1a960…`), the S8 cross-check. Continuing a
gated DAG; verdict (B) re-derive-structured-column-first is settled — don't re-litigate.

## DONE and in v3 (gated, idempotent, regression-locked — verify against live DB before building)
- **S0 — clean key index.** `s0_keys.py` (`normalize_address`→AddressKey + `matches()` type-wildcard +
  `disambiguate_distinct()`; `canonicalize_apn`→delegates to `housing_rules.to_canonical_apn`; `is_adu`).
  `s0_key_index` 895, `s0_protected_pairs` 3, `s0_s8_review_buckets` 5. `test_s0_gate.py`.
- **S1 — CPRA spine (corrected).** `build_s1.py` + shared `housing_predicates.py` (`is_housing`, `net_units`).
  `s1_projects` **1,385** = 670 CREATE/1,383u + 715 ATTACH. 568u Tier-1 + **265 recovered ADUs (~312u, 154
  completed)**. Queues: `s1_apn_overlap` 11, `s1_s4_unit_reconcile` 6, `s1_xaddr_review` 21. `test_s1_gate.py`.
- **S2 — dated events.** `build_s2.py`. `s2_events` **2,236** (BP 1,285 + CO 951, is_inferred=0 structured;
  entitlement 0 — real no-overlap, schema enforces is_inferred=1/no-date). `s2_date_reconcile` 3 (CPRA-vs-v2
  finaled-date findings for S8). `test_s2_gate.py`.
- **S3 — event-derived stage.** `build_s3.py`. `s3_stage` **1,385** (completed 951 · permitted 340 ·
  entitled 0 · pipeline 94), 0 asserted, co↔completed 1:1. `s3_stage_reconcile` **33** (v1 stage
  disagreements for S8, incl. 14 v1=completed→pipeline). 265 ADUs stage at 154 completed/108 permitted/3
  pipeline. `test_s3_gate.py`.

## TWO DISTINCT FINDINGS from S3 (do not conflate — this is the precise, defensible framing)
- **A — stage over-assertion (→ s3_stage_reconcile, S8):** 33 stage labels disagree with event-derived
  stage; 14 are v1=completed but no event = uncorroborable completions (proj728 1118 Oxford, proj465/905
  739 Channing, proj698…). The genuine over-assertion.
- **B — entitlement-event gap (→ S2 acquisition queue, SEPARATE):** the audit's 757 "entitled+ no
  entitlement event" decomposes to 668 event-backed (permitted/completed via CO/BP) + 80 entitled-not-in-
  spine + only 9 truly unsupported. So 757 = missing entitlement DATES (acquisition), NOT stage
  over-assertion. The migration over-asserted entitlement EVENTS; its stage LABELS were mostly event-backed.

## SHARED MODULES (single-sourced, imported everywhere, wiring-guarded — anti-drift)
`s0_keys` (address key, APN canon, is_adu) · `housing_predicates` (is_housing, net_units) · **`gating.py`
(snapshot_v3 — NOW SHARED, fixed this session)**. The corrected unit signal (do NOT revert):
`net_units = ua if ua>0; nu if New; min(nu,2) if ADU; else 0` · building = MAX over permits. (`else 0`
because nu on an alteration is EXISTING stock, not new — a naive "ua else nu" adds 4,239u of existing
housing.)

## SNAPSHOT DISCIPLINE — FIXED THIS SESSION (was systemically broken)
All of S0/S1/S2's "pre-" snapshots had been CLOBBERED by their own idempotency re-runs (fixed-tag
snapshot_v3, re-run overwrote the pre-state). The snapshot safety net was non-functional across the whole
rebuild (no data loss — v2 untouched, rebuild deterministic, regression-locked — but rollback points were
gone). FIX: snapshot_v3 extracted to shared `gating.py`, refuses-to-clobber + a `--no-snapshot` flag so the
idempotency re-run can't snapshot. PROVEN at S3: idempotency re-run reproduced 1,385/33 and left a clean
pre-s3.db (s0+s1+s2, no s3). Old clobbered snapshots are stale — do NOT reconstruct them; the deterministic
rebuild IS the recovery path.

## Discipline that held (keep it)
Every write: snapshot (now functional) → preview → ENFORCED gate (--write aborts on FAIL) → STOP for John →
guarded txn → fresh-connection fingerprint → idempotency re-run (with --no-snapshot). Anti-drift: every
load-bearing concept AND infrastructure helper single-sourced + wiring-guarded (the snapshot helper drifted
too — single-source the plumbing, not just the business logic). Verify a zero (clean/empty/"no change"
results were repeatedly measurement bugs — a dead type-branch, a mis-based diff, a clobbered snapshot — not
real findings; always confirm the check RAN). Measure before refactor. False-negative guard both directions.

## NEXT: S4 — units + resolve the s1_s4_unit_reconcile disagreements
Finalize per-building unit counts and resolve the 6 same-address CPRA-vs-v2 disagreements S1 queued:
- The 6 in `s1_s4_unit_reconcile` are BIDIRECTIONAL (e.g. 1500 San Pablo CPRA 170 vs v2 159; 2352 Shattuck
  v2 HIGHER 237 vs CPRA 135; 739 Channing 14 vs 4). For each: which source is right, by what evidence
  (structured column / permit family / the corrected net_units). Don't default to either source — the
  source-disagreement rule: corroborate against a primary source, flag if unresolved.
- Units already come from the corrected `net_units` (S1). S4's job: finalize the canonical unit count per
  building, reconcile the 6, and surface any residual internal disagreement (the proj15-class total-vs-sum
  leak — check none remain).
- Build `build_s4.py` (imports s0_keys + housing_predicates + gating) + `test_s4_gate.py` + wiring guard.
  Preview → ENFORCED gate → STOP → write → fingerprint → idempotency (--no-snapshot). Use the shared,
  fixed gating.snapshot_v3 (real rollback point this time).
- S4 gate (suggested): the 6 reconciled with evidence (or flagged unresolved → S8); Tier-1 568u +
  265 ADUs unchanged unless a reconcile legitimately changes one (show it); no internal total-vs-sum leak;
  s0/s1/s2/s3 untouched.

## Remaining DAG after S4
S5 affordability (full ELI/VLI/LI/MOD/ABOVE_MOD, NEVER market=units−vli, below-market gaps →
needs_acquisition; the ~94-project/~6,380u tier acquisition queue = harvest backlog, `harvest_affordability.py`
exists, 9 cited: 7/8/10/13/15/17/35/36/119) · S6 confidence=f(source) · S7 cycle-scope (wire housing_rules;
flag which of the 951 completions + 265 ADUs fall in the RHNA window vs prior-cycle) · S8 reconciliation
matrix + v1 cross-check (incl. s2_date_reconcile 3 + s3_stage_reconcile 33) · S9 the A2 (vs CKAN oracle).
Build into v3; swap to canonical only on passing all gates; v2 preserved as cross-check.

## Acquisition queue (off-disk harvest backlog)
1. Affordability tiers ~94 projects/~6,380u (staff reports/AHCP/deed restrictions; harvest_affordability.py;
   9 cited done).
2. Entitlement dates ~33 projects/~2,253u — .txt corpus does NOT cover the spine (confirmed: 91 files, 4
   approvals, 0 at spine buildings) → needs acquisition.

## Snapshots
`pre-s3.db` is the one CLEAN rollback point (s0+s1+s2, fixed helper). pre-s1/pre-s1-rerun/pre-s2 are
STALE/clobbered — ignore them; deterministic rebuild is the recovery path.
