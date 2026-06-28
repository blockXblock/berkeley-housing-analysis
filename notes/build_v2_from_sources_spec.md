# build_v2_from_sources — REBUILD SPECIFICATION (design only, nothing runs)

**Purpose.** Re-derive v2's factual content from primary-source **structured columns**, replacing the migration's
"copy v1's spreadsheet and stamp it `high`" method. Verdict (B) from the forensic audit: ~90%+ of wrong/missing
values are re-derivable from on-disk structured sources; the disease is *coverage* + *fabricated confidence*, both
cured by construction here. This is the largest write in the project's history — it deserves stage-by-stage gating,
not a single big run.

**Non-negotiable principles (the inversions of the migration's three flaws + the confidence lie):**
1. **Structured columns are the source of truth, never parsed prose.** `UnitsAdded`/`NumberUnits`, `Issuance Date`,
   `Finaled Date`, `Work Type`, `Occupancy Class`, `Status` — read the column, never the `WorkDescription` text.
2. **Status-keyed, not match-or-drop.** A building's existence and stage are established by its own structured
   status + dated events, not by whether it matches a pre-existing project. Net-new buildings are CREATED by rule,
   never gated on a whitelist.
3. **Confidence = f(source presence), never a constant.** Every fact-bearing row's confidence is computed from what
   actually backs it. No unconditional `high`. No `is_inferred=0` on copied-without-evidence data.
4. **Absence is flagged, never fabricated.** A tier we can't source becomes `needs_acquisition`, never `market` by
   subtraction. A date we don't have is NULL+flagged, never asserted.
5. **v1/FINAL.csv is ONE cross-check among several, never the spine.**
6. **Everything sized in units, gated, snapshotted, fingerprinted. John owns every write.**

---

## SOURCE INVENTORY (what the rebuild reads — all on disk unless flagged)

| source | content | role | on disk? |
|---|---|---|---|
| CPRA `BP_Annual Permit Report-*.xlsx` (2018-22, 2023-25) | ~30,764 unique permits; structured `Work Type`, `Status`, `Finaled/Issuance Date`, `UnitsAdded`, `NumberUnits`, `OccType`, address, APN | **PRIMARY SPINE** | ✅ |
| `R2_R3_permits_2023_2025.tsv` (1,573 rows) | building permits w/ status+occupancy+date | corroborating + coverage | ✅ |
| `accela_status/*.txt` (91 planning) | Processing Status events incl. entitlement dates | entitlement-date source | ✅ partial |
| `accela_status/building/*.txt` (40) | B-permit status (sparse/stub) | corroborating | ✅ low-yield |
| inspection JSONs (92) | inspection histories (completion corroboration) | corroborating (new `inspections` table) | ✅ |
| Alameda County parcels | authoritative current APN/geometry | APN corroboration (never re-point) | ✅ |
| city A2 / CKAN mirror | Berkeley's *submitted* APR | the ORACLE to compare against (never an input to v2) | ✅ |
| harvested affordability forms (DBE/AHCP/Tabulation) | document-cited income tiers | the affordability acquisition target | partial (9 done) |
| v1 `projects` / FINAL.csv | the old spreadsheet | **CROSS-CHECK ONLY** — flag where it disagrees | ✅ |

---

## THE DAG (stage order is a hard dependency chain)

```
S0  build clean parcel/address key index        ──┐
S1  ingest CPRA structured permits (spine)         │
S2  materialize dated events from structured cols  │ (D-before-C contract lives across S0/S3)
S3  derive stage from events (status-keyed)        │
S4  derive units from structured columns           │
S5  derive affordability (honest tiers + flags)    │
S6  compute confidence = f(source presence)        │
S7  cycle-scope every milestone (RHNA window)      │
S8  reconciliation matrix + cross-check vs v1      ──┘
S9  the A2 view/notebook reads the result
```

Each stage is an independently-gated write (snapshot → preview → STOP → guarded txn → fingerprint).
The build is **idempotent**: re-running a stage reproduces the same result (no append-on-rerun).

---

## STAGE CONTRACTS

### S0 — CLEAN KEY INDEX (the D contract — MUST run before any matching)
The migration injected `(id:N)` into both `canonical_address` AND `normalized_address`, defeating dedup. Before any
building can be matched or created, build a clean key:
- **Address key:** strip `(id:N)`, fold ordinals (1st↔First), normalize St/Ave/abbrev, uppercase, collapse whitespace.
- **APN key:** canonical Alameda County APN, **corroborating only — never a match-or-drop gate** (APN drift is real:
  2503 Haste CPRA `055-1875-045` vs city `055-1875-004`).
- **Permit-family key:** `extract_master_permit` — collapse `-REV/-DEF/phase` suffixes to the master.
- **Protect the 3 real ADU+main pairs** (D found these): a >1-hit APN that is a genuine ADU+main must NOT merge —
  disambiguate by CO-date / unit-count, never collapse.
- **Output:** a key index mapping every building to (clean_address, canon_APN, permit_family), with the 3 protected
  pairs explicitly whitelisted-as-distinct. **Deliverable before S1 matching.**

### S1 — CPRA SPINE INGEST (status-keyed, not match-or-drop)
- Read the CPRA structured columns. A building enters v2 if it has a residential `OccType` (R-1/R-2/R-3) /
  Residential|Mixed-Use SubType and any real permit — **regardless of whether a pre-existing project matches.**
- **ATTACH if** the clean key index hits an existing project (S0); **CREATE** a new project otherwise. (This is the
  inversion of the ~2-project whitelist — CREATE is the rule, not the exception.)
- **Trade/alteration/non-residential permits stay OUT** (the 18,940 alterations are remodels — correctly excluded).
  The exclusion is by structured `Work Type`/`OccType`, not by prose.

### S2 — MATERIALIZE DATED EVENTS (from structured columns)
- `building_permit_issued` ← `Issuance Date` column. `permit_finaled`/`co_issued` ← `Finaled Date` column.
  `entitlement_approved` ← planning `.txt` / accela_status (the partial source; flag the gap).
- **Every event carries its real source** (`source_type`, `source_document_id` where applicable) and **honest
  `is_inferred`** (0 only if a structured column backs it; 1 + flag otherwise). NO blanket `is_inferred=0`.
- Phase 3 finding: where 2 sources cover a date they're byte-identical (0/930 disagreements) — so dates are safe to
  take from the structured column; record corroboration count.

### S3 — DERIVE STAGE (status-keyed from events, the B fix)
- Stage is **computed from the dated events**, never from a v1 string: `co_issued`→completed; `building_permit_issued`
  (no CO)→permitted/under_construction; `entitlement_approved` (no BP)→entitled; none→pre_application/pipeline.
- **No `map_status_to_stage` string dict.** v1's status becomes a *cross-check* (S8): flag where derived stage
  disagrees with v1's claim, don't trust v1.
- Projects with NO milestone evidence (the 84) → stage `unknown`/flagged, never asserted.

### S4 — DERIVE UNITS (structured columns; avoid the REV trap)
- `total_units` ← structured `UnitsAdded` (net) on the **master** permit, else `NumberUnits`. **Never WorkDescription
  prose.** (A found units were actually sound — M1's scalar agreed with CPRA — but the rebuild sources them correctly
  by construction so the agreement is guaranteed, not lucky.)
- **REV double-count guard:** use master-permit `UnitsAdded` only; never sum REV sub-permits (the raw feed has 401
  masters / 33,260u where naive summing double-counts).
- Cross-check the proj15-class leak: `total_units` must equal the unit_program sum; flag any residual.

### S5 — DERIVE AFFORDABILITY (honest tiers — the A fix, the core repair)
- **Full income vocabulary**: ELI/VLI/LI/MOD/ABOVE_MOD — NOT the migration's 2-bucket VLI/ABOVE_MOD ceiling.
- **Never `market = units − vli`.** Market/above-mod is only what a source states.
- Tiers come from **document-cited sources** (the harvested DBE/AHCP/Tabulation forms — the 9 already done, cited
  high). Where no source exists for a project's below-market tiers → the below-market slice is **`needs_acquisition`**
  (flagged, counted as unknown), never zeroed and never asserted-as-market.
- This converts the ~3,964–6,380 structurally-zeroed below-market units + the 11,488u fabricated-market into an
  explicit, honest acquisition queue (~94 projects / ~6,380u) instead of false data.

### S6 — CONFIDENCE = f(SOURCE PRESENCE) (kills the fabricated `high`)
- Computed, never constant: `high` only if a real source document/structured column backs the value; `medium` if
  corroborated by a secondary source; `low`/`needs_review` if single-source or inferred; `needs_acquisition` if absent.
- Retroactively this means the migration's 11,183u high-conf-uncited affordability + 757 unsupported stage claims get
  their *honest* confidence — most drop to low/needs_acquisition until sourced.

### S7 — CYCLE-SCOPE (the RHNA-window fix — required for the HCD comparison)
- Tag every milestone event with its **RHNA cycle / projection-period** (wire in the orphaned `housing_rules` logic,
  validated against its statute citations — don't improvise the boundaries).
- **Critical for the ~568u finding:** a completion Finaled 2018-07-31 (2001 Fourth St) may be a *prior cycle* and
  correctly absent from the *current* A2. The rebuild must flag, per recovered completion, whether its CO falls in the
  reporting window being compared to HCD — so "568u missing" resolves into "X in-window (a real A2 gap) vs Y
  prior-cycle (correctly absent)." **This is the open question from the audit; S7 answers it.**

### S8 — RECONCILIATION MATRIX + v1 CROSS-CHECK
- For every fact, record how many independent sources corroborate it (the multi-source principle). Agreements = high
  confidence; disagreements = findings (city error / scrape error / real discrepancy), surfaced not smoothed.
- **v1/FINAL.csv enters HERE, as a cross-check only:** flag every place the rebuild disagrees with v1 — those are
  either migration errors (expected) or rebuild bugs (investigate). v1 never overrides a sourced value.

### S9 — THE A2 (consumes the rebuilt, cycle-scoped, honestly-confident data)
- The A2 view/notebook reads dated events + cycle scope + honest tiers. Reports completed-CY / permitted-CY /
  entitled-CY by income tier, in-window only, with cited-vs-needs_acquisition split. Compare to the CKAN-mirror oracle.

---

## GATING & VALIDATION (per stage)
- Snapshot `keep_snapshot_<date>_pre-<stage>.db` → read-only **preview** of the full insert/update plan (rowcounts,
  units-at-stake, sample diffs) → **STOP for John's go** → guarded transaction (per-statement rowcount + verify-or-
  rollback) → independent fingerprint read-back asserting the stage's expected deltas.
- **Parallel-build safety:** build into a fresh `berkeley_housing_v3.db` (or a staging schema), validate end-to-end
  against the oracle, and only swap it in as canonical once it passes — so the live v2 is never half-rebuilt. The old
  v2 + the migration output become the *cross-check* (S8), preserved, not destroyed.
- **Acceptance gates before swap:** (1) dates byte-identical to structured sources where present (Phase-3 standard);
  (2) units = unit_program sums (no proj15 leak); (3) zero unconditional-high confidence rows; (4) every below-market
  gap flagged needs_acquisition not zeroed; (5) the ~568u completions present and cycle-tagged; (6) the 3 ADU pairs
  intact; (7) A2 reconciles to the oracle within an explainable, documented delta.

## WHAT THIS DOES NOT DO (kept honest)
- Does not invent affordability tiers it can't source → `needs_acquisition` queue (~94 proj / ~6,380u).
- Does not acquire entitlement dates not on disk → flagged queue (~33 proj / ~2,253u, partial in .txt).
- Does not re-point APNs on drift → flags 36 proj/1,198u + 33 proj/1,528u for review, never auto-corrects.
- Does not publish any number (incl. the ~568u) until it is written-and-fingerprinted in the rebuilt DB.

## EXECUTION ORDER (next session)
S0 (clean key) → S1 (spine) → S2 (events) → S3 (stage) → S4 (units) → S5 (affordability) → S6 (confidence) →
S7 (cycle) → S8 (reconcile) → S9 (A2). Each gated. Build into v3-staging; swap only on passing all 7 acceptance
gates. The acquisition queue (S5/S7 flags) becomes the harvest backlog — `harvest_affordability.py` already exists
for it; the 9 cited projects are the done portion.
