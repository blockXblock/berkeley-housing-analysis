# REBUILD RESUME — next stage is S2 (build_v2_from_sources)

Read this + `build_v2_from_sources_spec.md` + `forensic_migration_audit.md` before acting. The forensic
arc is RESOLVED and the rebuild is UNDERWAY — you are not re-deciding anything, you are continuing a
gated DAG. S0 and S1 (the two hardest stages) are built, validated, regression-locked, and isolated in
`berkeley_housing_v3.db`. Live `berkeley_housing_v2.db` is byte-identical/untouched and serves as the
cross-check, never the source.

## The verdict already reached (do not re-litigate)
The migration (`migrate_v1_to_v2.py`) copied v1's spreadsheet into a normalized schema and stamped every
value `confidence=high` whether or not evidence backed it; stage came from a v1 status string, units/
completions from text-parsing while structured columns (`UnitsAdded`/`Issuance Date`/`Finaled Date`) sat
unused. Verdict: **(B) re-derive structured-column-first** — build `berkeley_housing_v3.db` from primary
sources, demote v1/FINAL.csv to a cross-check. ~90%+ re-derivable from on-disk structured columns. Three-
direction error: v2 UNDER-counts completions (~568u material), CANNOT represent middle/low affordability
tiers (structural — fix in S5), OVER-asserts upstream stage (fix via event-derivation in S3).

## What is DONE and in v3 (gated, idempotent, regression-locked)
- **S0 — clean key index.** `scripts/build_v2/s0_keys.py` (the permanent key module: `normalize_address`
  → AddressKey with `matches()` type-wildcard relation + `disambiguate_distinct()`; `canonicalize_apn`
  DELEGATES to `housing_rules.to_canonical_apn` — the project APN canon, dashed/Option-B, NOT reimplemented).
  v3 holds `s0_key_index` (895 buildings), `s0_protected_pairs` (3 ADU+main pairs kept distinct via CO-date/
  permit disambiguator), `s0_s8_review_buckets` (5 different-present-type addresses flagged for S8), `s0_meta`.
  Guarded by `test_s0_gate.py` (PASS).
- **S1 — CPRA spine.** `scripts/build_v2/build_s1.py`. v3 holds `s1_projects` (1,120: **435 CREATE/1,102u**
  net-new + **685 ATTACH** to existing v2 ids), `s1_apn_overlap` (11), `s1_s4_unit_reconcile` (6, bidirectional),
  `s1_xaddr_review` (21), `s1_meta`. The **568u Tier-1 completions are materialized** (2001 Fourth 152u, 2503
  Haste collapsed 3-phase→one 55u, 1808 University 44u CREATE not merged into proj307, etc.). Guarded by
  `test_s1_gate.py` (PASS, incl. APN wiring guard + housing-predicate regression).
- **Final housing predicate (S1, hard-won over 3 guard-caught iterations — do NOT simplify):**
  `is_housing = R-occupancy (R-1/2/3) OR units>0 OR ADU-flag`. The units clause recovers mixed-use towers
  (A/B ground-floor OccType, e.g. 3000 San Pablo 78u coded A-2) and U-coded ADUs-with-units; the ADU-flag
  clause recovers ADU=Yes rows with blank units. Garages/commercial with 0 units excluded. Regression-asserted.

## Discipline checks that held all session (keep them)
- Every write: snapshot → read-only preview → acceptance gate (ENFORCED — `--write` aborts on any FAIL,
  not advisory) → STOP for John's go → guarded txn → fresh-connection fingerprint → idempotency re-run.
- Live v2 opened read-only only; sha256 `d6a1a960…` unchanged across S0+S1.
- Anti-drift: each stage is an importable module in `scripts/build_v2/`; key logic lives ONCE
  (`s0_keys`/`housing_rules`), imported everywhere, never inlined. Each gate test includes a
  "fails-if-not-called" wiring guard so a future reimplementation fails the gate.
- **Inspect before tightening** (the S1 predicate lesson): look at the actual data distribution before
  writing any filter, and use a false-negative guard (it caught 3 over-tightens that would have dropped
  real homes — the 78u tower, U-ADUs-with-units, ADU=Yes-blank-units).
- Verify artifacts directly (CC summaries / write-echoes can be wrong — `cat` the file, run the test green
  on REAL logic). An absence is a hypothesis to verify, not a fact.

## NEXT: S2 — materialize dated events (the next gated stage)
Attach dated milestone events to the `s1_projects` spine, each carrying its real source + HONEST
`is_inferred` (0 only if a structured column backs it — NEVER the migration's blanket `is_inferred=0`):
- `building_permit_issued` ← CPRA `Issuance Date` (structured).
- `co_issued` / `permit_finaled` ← CPRA `Finaled Date` (structured). Phase-3 matrix proved dates are
  byte-identical across sources (0/930 disagreements: 123/123 BP, 807/807 finaled) — so structured dates
  are safe to take directly; record corroboration count.
- `entitlement_approved` ← planning `.txt` corpus (`accela_status/*.txt`) — PARTIAL source; flag the gap
  (the ~33 discretionary projects / ~2,253u entitlement-date acquisition queue from the audit).
- Imports `s0_keys`. Build as `scripts/build_v2/build_s2.py` (module) + `test_s2_gate.py` (regression +
  wiring guard). Preview → acceptance gate → STOP → write into v3 (`s2_events`) → fingerprint → idempotency.
- **S2 acceptance gate (suggested):** every event traces to a real source + honest is_inferred; BP/CO dates
  match the structured column (Phase-3 standard); the 568u completions get their CO event with the right
  date; entitlement gaps flagged not asserted; the s1_s4_unit_reconcile / apn_overlap rows untouched.

## The remaining DAG (after S2)
S3 derive stage from events (status-keyed, not the v1 string) · S4 derive units (structured, REV-guarded;
resolve the 6 s1_s4_unit_reconcile disagreements) · S5 affordability (full ELI/VLI/LI/MOD/ABOVE_MOD vocab,
NEVER market=units−vli, below-market gaps → `needs_acquisition` not zeroed; the ~94-project/~6,380u tier
acquisition queue = the harvest backlog, `harvest_affordability.py` exists, 9 projects already cited) ·
S6 confidence = f(source presence) · S7 cycle-scope (wire in `housing_rules`; flag which of the 568u
completions fall in the RHNA reporting window vs prior-cycle — the open A2-comparison question) · S8
reconciliation matrix + v1 cross-check · S9 the A2 (compare to CKAN-mirror oracle).
Build into v3-staging; swap to canonical only on passing all acceptance gates. v2 + migration output remain
the S8 cross-check, preserved.

## Acquisition queue (the off-disk harvest backlog, sized by the audit)
1. Affordability tier breakdowns for ~94 projects (~6,380u) — staff reports / AHCP / deed restrictions.
   (`harvest_affordability.py` is the tool; the 9 cited projects 7/8/10/13/15/17/35/36/119 are the done portion.)
2. Entitlement dates for ~33 discretionary projects (~2,253u) — partial in `accela_status/*.txt`, else acquire.
Everything else (completions, BP ladder, units, clean keys) = re-read of structured columns already on disk.

## Snapshots retained
`keep_snapshot_2026-06-17_pre-s1.db` (+ the S0-era snapshots). v3 = S0+S1. v2 untouched cross-check.
