# REBUILD RESUME — next stage is S5 (build_v2_from_sources)

Read this + `build_v2_from_sources_spec.md` + `build_v2_lessons.md` before acting. FIVE gated stages (S0–S4)
built, validated, regression-locked, isolated in `berkeley_housing_v3.db`. Live `berkeley_housing_v2.db`
byte-identical/untouched (sha256 `d6a1a960…`), the S8 cross-check. Continuing a gated DAG; verdict (B)
re-derive-structured-column-first is settled — don't re-litigate.

## DONE and in v3 (gated, idempotent, regression-locked — verify against live DB before building)
- **S0 — clean key index.** `s0_keys.py` (normalize_address + matches() type-wildcard + disambiguate_distinct;
  canonicalize_apn→housing_rules.to_canonical_apn; is_adu). `s0_key_index` 895, `s0_protected_pairs` 3,
  `s0_s8_review_buckets` 5. `test_s0_gate.py`.
- **S1 — CPRA spine (corrected).** `build_s1.py` + `housing_predicates.py` (is_housing, net_units).
  `s1_projects` **1,385** = 670 CREATE/1,383u + 715 ATTACH. 568u Tier-1 + 265 recovered ADUs. Queues:
  `s1_apn_overlap` 11, `s1_s4_unit_reconcile` 6 (now resolved in S4), `s1_xaddr_review` 21. `test_s1_gate.py`.
- **S2 — dated events.** `build_s2.py`. `s2_events` **2,236** (BP 1,285 + CO 951 is_inferred=0 structured;
  entitlement 0 — real no-overlap). `s2_date_reconcile` 3 (CPRA-vs-v2 finaled-date → S8). `test_s2_gate.py`.
- **S3 — event-derived stage.** `build_s3.py`. `s3_stage` **1,385** (completed 951 · permitted 340 ·
  entitled 0 · pipeline 94), 0 asserted, co↔completed 1:1. `s3_stage_reconcile` 33 (v1 disagreements → S8,
  incl. 14 v1=completed→pipeline). 265 ADUs: 154 completed/108 permitted/3 pipeline. `test_s3_gate.py`.
- **S4 — evidence-reconciled units.** `build_s4.py`. `s4_units` **1,385** (canonical = net_units; re-derives
  nothing). `s4_unit_reconcile_resolved` 6: 5 RESOLVE_OURS by structured evidence (1500 SanPablo→170,
  739 Channing→14, 2328 Channing→13, 2317 Channing→17, 2330 Blake→6 — v2 was under-count/null-gap/self-
  contradiction each time) + **2352 Shattuck → FLAG-S8** (Logan Park multi-building, held at 135, NOT guessed
  to 237). `test_s4_gate.py`.

## TWO FINDINGS so far, kept distinct (do not conflate)
- Stage over-assertion: 33 (s3_stage_reconcile, incl. 14 uncorroborable completions) → S8.
- Entitlement-event gap: 757 = missing entitlement DATES (acquisition), NOT stage over-assertion (668
  event-backed, 80 not-in-spine, 9 truly unsupported).
- Plus: unit reconciles (5 v2-errors corrected, 1 multi-building flagged) + 3 date findings (s2_date_reconcile).

## SHARED MODULES (single-sourced, imported, wiring-guarded)
`s0_keys` (address key, APN canon, is_adu) · `housing_predicates` (is_housing, net_units) · `gating.py`
(snapshot_v3 — shared, refuse-to-clobber + --no-snapshot for idempotency). Corrected unit signal (do NOT
revert): `net_units = ua if ua>0; nu if New; min(nu,2) if ADU; else 0`; building = MAX over permits.

## NEXT: S5 — affordability (the harvest-backlog stage; connects to the document-citation work)
Re-derive affordability tiers HONESTLY — the structural fix for the migration's 2-bucket VLI/ABOVE_MOD
ceiling and its `market = units − vli` fabrication:
- **Full income vocabulary:** ELI / VLI / LI / MOD / ABOVE_MOD — not the migration's 2 buckets.
- **NEVER `market = units − vli`.** Above-mod/market is only what a source states.
- **Tiers from document-cited sources** (the harvested DBE/AHCP/Tabulation forms). The 9 already cited at
  confidence=high: proj 7/8/10/13/15/17/35/36/119 (these are the DONE portion — fold them in).
- **Below-market gaps → `needs_acquisition`** (flagged, counted as unknown) — NEVER zeroed, NEVER asserted-
  as-market. This formalizes the ~94-project/~6,380u tier acquisition queue (the harvest backlog;
  `harvest_affordability.py` is the tool).
- **THE LEAK GUARD (handed up from S4):** affordability tier-sum MUST equal the S4 canonical unit total per
  building (the proj15-class 110-vs-131 leak check lands HERE — S4 deferred it to S5). Gate must assert
  tier-sum == s4_units total (or the difference is the explicitly-flagged needs_acquisition slice).
- Build `build_s5.py` (imports s0_keys + housing_predicates + gating) + `test_s5_gate.py` + wiring guard.
  Preview → ENFORCED gate → STOP → write `s5_affordability` → fingerprint → idempotency (--no-snapshot,
  real rollback via shared gating).
- S5 gate (suggested): full-vocab tiers; no market-by-subtraction; the 9 cited folded in at confidence=high
  with source_document_id; below-market gaps flagged needs_acquisition not zeroed; tier-sum == s4_units (or
  flagged delta); Tier-1/265-ADU unit totals unchanged; s0–s4 untouched.

## Remaining DAG after S5
S6 confidence = f(source presence) (kills the migration's fabricated `high`) · S7 cycle-scope (wire
housing_rules; flag which of the 951 completions + 265 ADUs fall in the RHNA reporting window vs prior-cycle
— the open A2-comparison question) · S8 reconciliation matrix + v1 cross-check (gathers s2_date_reconcile 3
+ s3_stage_reconcile 33 + the 2352 Shattuck/Logan-Park + proj179 N/S split multi-building category) · S9 the
A2 (vs CKAN-mirror oracle). Build into v3; swap to canonical only on passing all gates; v2 preserved.

## Acquisition queue (off-disk harvest backlog — S5 formalizes #1)
1. Affordability tiers ~94 projects/~6,380u (staff reports/AHCP/deed restrictions; harvest_affordability.py;
   9 cited done — 7/8/10/13/15/17/35/36/119).
2. Entitlement dates ~33 projects/~2,253u — .txt corpus does NOT cover the spine → needs acquisition.

## Discipline (keep it)
Snapshot (functional now) → preview → ENFORCED gate → STOP for John → guarded txn → fingerprint →
idempotency (--no-snapshot). Anti-drift: single-source every concept AND infrastructure helper, wiring-
guarded. VERIFY A ZERO (clean/empty/"no change" results were repeatedly measurement bugs this session — a
dead type-branch, a mis-based diff, a clobbered snapshot — not real findings; confirm the check RAN).
Measure before refactor. Resolve source disagreements by EVIDENCE (why they differ), flag the unresolvable
→ S8, never default to a source. An absence is a hypothesis to verify.

## Snapshots
Clean rollback points: pre-s2.db, pre-s3.db, pre-s4.db (shared gating, refuse-to-clobber). The old
pre-s1/pre-s1-rerun are stale/clobbered — ignore; deterministic rebuild is the recovery path.

## Multi-building category (note for S8)
2352 Shattuck (Logan Park, 3 permit-families) + the queued proj179 N/S split = a CATEGORY: developments
spanning multiple buildings/permits where per-building MAX under-counts. S8 should handle as a pattern (how
to count a multi-building development — per building vs development total), not as one-offs.
