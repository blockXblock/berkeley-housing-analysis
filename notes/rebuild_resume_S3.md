# REBUILD RESUME — next stage is S3 (build_v2_from_sources)

Read this + `build_v2_from_sources_spec.md` + `build_v2_lessons.md` before acting. The forensic arc is
RESOLVED; the rebuild is UNDERWAY. THREE gated stages (S0, S1, S2) are built, validated, regression-locked,
and isolated in `berkeley_housing_v3.db`. Live `berkeley_housing_v2.db` is byte-identical/untouched
(sha256 `d6a1a960…`) and serves as the S8 cross-check, never a source. You are continuing a gated DAG,
not re-deciding anything.

## Verdict (do not re-litigate)
(B) re-derive structured-column-first into v3; demote v1/v2/migration output to a cross-check. The
migration copied v1's spreadsheet, stamped everything `confidence=high`, set stage from a v1 status string,
parsed prose for units while structured columns sat unused. Three-direction error: UNDER-counts completions
(fixed in S1), CANNOT represent middle/low affordability tiers (S5), OVER-asserts upstream stage (S3 fixes).

## DONE and in v3 (gated, idempotent, regression-locked — verify against live DB before building)
- **S0 — clean key index.** `scripts/build_v2/s0_keys.py` (the key module: `normalize_address`→AddressKey
  with `matches()` type-wildcard relation + `disambiguate_distinct()`; `canonicalize_apn` DELEGATES to
  `housing_rules.to_canonical_apn`; `is_adu(value)`→bool handling all type variants). Tables: `s0_key_index`
  895, `s0_protected_pairs` 3, `s0_s8_review_buckets` 5, `s0_meta`. Guarded by `test_s0_gate.py`.
- **S1 — CPRA spine (CORRECTED this session).** `scripts/build_v2/build_s1.py` + the extracted shared
  `housing_predicates.py` (`is_housing`, `net_units`). Tables: `s1_projects` **1,385** = **670 CREATE/1,383u**
  + **715 ATTACH**; `s1_apn_overlap` 11; `s1_s4_unit_reconcile` 6; `s1_xaddr_review` 21; `s1_meta`. The
  568u Tier-1 completions materialized; **+265 ADU dwellings (~312u, 223 completed) recovered** this session
  (they were silently dropped because their count lives in `NumberUnits`, not `UnitsAdded`). Guarded by
  `test_s1_gate.py` (incl. NumberUnits-ADU, min(nu,2) cap, existing-stock-stays-out, is_adu type variants).
- **S2 — dated events.** `scripts/build_v2/build_s2.py`. Table: `s2_events` **2,236** (BP 1,285 + CO 951,
  all `is_inferred=0` structured CPRA columns; entitlement 0 events — real no-overlap; schema enforces
  `is_inferred=1`/no-date for any entitlement that appears). `s2_date_reconcile` 3 (CPRA-vs-v2 finaled-date
  findings for S8: B2018-03576, B2019-01241, B2020-03494, each w/ both dates). Guarded by `test_s2_gate.py`.

## The corrected unit signal (S1 — hard-won, regression-locked, do NOT revert)
`net_units(permit) = ua if ua>0; nu if Work Type=New; min(nu,2) if ADU=Yes; else 0` · `building = MAX over
permits`. WHY each clause: `ua` is the explicit net-add; `nu`-on-New is a new building (all units new);
`min(nu,2)`-on-ADU is the ADU/JADU capped against property-unit contamination (16 cases had nu=24/82/92);
`else 0` because on an ALTERATION `nu` is the EXISTING building's unit count, NOT new units (a naive "ua
else nu" would wrongly add 4,239u of existing stock). Same column (`NumberUnits`), different meaning per
context — read it per context, never uniformly.

## Discipline that held (keep it)
- Every write: snapshot → read-only preview → ENFORCED acceptance gate (--write aborts on FAIL) → STOP for
  John's go → guarded txn → fresh-connection fingerprint → idempotency re-run. Live v2 read-only only.
- Anti-drift: each load-bearing concept defined ONCE in a shared module, imported everywhere, with a
  "fails-if-not-called" wiring guard in the gate test. Shared so far: `s0_keys` (address key, APN canon,
  is_adu), `housing_predicates` (is_housing, net_units). Three such surfaces caught this session by
  CONSOLIDATION revealing silent divergence — extract shared, don't reimplement inline.
- Measure before you refactor; verify a zero (a clean "0" or "no change" may be a dead branch/type bug, not
  a real result); inspect data distribution before writing a filter; false-negative guard (check both: what
  did I wrongly keep AND wrongly drop). An absence is a hypothesis to verify.

## NEXT: S3 — derive stage from events (the direct fix for the migration's 757 over-asserted stages)
Stage is COMPUTED from the s2_events, never from a v1 status string:
- `co_issued` → completed
- `building_permit_issued` (no CO) → permitted / under_construction
- `entitlement_approved` (no BP) → entitled
- none → pre_application / pipeline
- Imports s0_keys + housing_predicates. Build `build_s3.py` (module) + `test_s3_gate.py` (regression +
  wiring guard). Preview → ENFORCED gate → STOP → write `s3_stage` into v3 → fingerprint → idempotency.
- S3 acceptance gate (suggested): every stage traces to the event(s) that justify it (no asserted stage);
  the 568u completions + 265 recovered ADUs land at `completed` (they have CO events); projects with only
  BP→permitted, only entitlement→entitled, none→pipeline; CROSS-CHECK against v1's stage string and FLAG
  disagreements (expected: ~757 projects v1 called entitled+ with no event — those drop to their honest
  event-derived stage) — the flag set IS the proof the migration over-asserted; record it, don't trust v1.
- NOTE the entitlement gap: projects with a BP/CO but no entitlement event are NOT "missing a stage" — they
  derive completed/permitted from BP/CO; entitlement absence is the acquisition gap (S2), not an S3 problem.

## Remaining DAG after S3
S4 units + resolve the 6 s1_s4_unit_reconcile disagreements (bidirectional: e.g. 2352 Shattuck v2 higher) ·
S5 affordability (full ELI/VLI/LI/MOD/ABOVE_MOD vocab, NEVER market=units−vli, below-market gaps →
needs_acquisition not zeroed; the ~94-project/~6,380u tier acquisition queue = the harvest backlog,
`harvest_affordability.py` exists, 9 projects already cited) · S6 confidence = f(source presence) · S7
cycle-scope (wire `housing_rules`; flag which completions fall in the RHNA reporting window vs prior-cycle —
the open A2-comparison question; the 568u + 265 ADUs need cycle-tagging) · S8 reconciliation matrix + v1
cross-check (incl. the 3 s2_date_reconcile findings + the S3 stage-disagreement flags) · S9 the A2 (compare
to CKAN-mirror oracle). Build into v3; swap to canonical only on passing all gates; v2 preserved as cross-check.

## Acquisition queue (off-disk harvest backlog)
1. Affordability tier breakdowns ~94 projects / ~6,380u (staff reports / AHCP / deed restrictions;
   `harvest_affordability.py` is the tool; 9 cited projects 7/8/10/13/15/17/35/36/119 are the done portion).
2. Entitlement dates ~33 discretionary projects / ~2,253u — the .txt corpus does NOT cover the spine's
   entitlements (confirmed this session: 91 files, 4 approvals, 0 at spine buildings) → needs acquisition.

## Snapshots
`keep_snapshot_2026-06-17_pre-s2.db`, `…_pre-s1-rerun.db` (+ earlier). v3 = S0+S1(corrected)+S2. v2 untouched.

## This session's arc (for context)
Opened to do S2; S2-prep audited S1's foundation and found a latent 265-ADU under-count (the migration's own
"read structured signal too narrowly" error, in the rebuild). Fixed S1's unit signal (context-aware
NumberUnits), the type bug that hid it (str(numpy.True_)≠'yes' dead branch), and the four-way is_adu drift
surface → all regression-locked. Then S2 landed clean with honest per-source provenance and the entitlement
gap flagged not fabricated. Three foundation corrections + one stage, all caught read-only.
