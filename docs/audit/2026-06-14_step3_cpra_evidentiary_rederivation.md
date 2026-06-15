# STEP 3 — CPRA-evidentiary re-derivation (verdict-layer write)

**Date:** 2026-06-14 · **Scope:** verdict layer only (evidence untouched) · **Snapshot:** `databases/keep_snapshot_2026-06-14_pre-step3.db` (sha256 `a09f50f8de3676a005ab81ebc19d2961b65b441f6fb38e7cf75a374e0650bf07`)

## What changed
Re-derived the 153 `ambiguous` completion verdicts against **independent CPRA evidence** (CPRA `finaled_date` / v2 inspection events) — never CKAN.

| disposition | count | write |
|---|---|---|
| **rescue → `completes` / `evidentiary`** | **85** | note `CPRA Finaled <date>`; `verdict_by = …@1154b9e+step3_rescue` |
| **minor/subsidiary → `does_not`** | 45 | `description_only`; `verdict_by = …@1154b9e+step3_minor_cleanup` |
| **stay `ambiguous`** (genuinely-uncertain residential → harvest queue) | 23 | untouched |

**Settled verdict distribution:** completes 683 · does_not 113 · ambiguous 23 (= 819).
**Basis:** evidentiary 664 · description_only 154 · human_override 1 · contested 0.
**Evidence layer unchanged:** events 3873 · permits 956 · versions 883 · affordability 890.

## The finaled-date-rescue trap (why scope-awareness mattered)
Naive "any `ambiguous` permit with a `finaled_date`" = 138 — **contaminated**. The Finaled date attaches to *minor scope* (furnace changeout, 400A temp power, demolition, panel upgrade). Finaling a furnace permit is not evidence the housing project completed; bulk-rescuing on the field's presence would re-inject the false completions STEP 1 removed. **Rescue gates on the permit's meaning (net-new dwelling/ADU/unit) AND independent corroboration — not on a date field being non-null.** (Third time this session that "gate on meaning, not on a field's presence" was the correct call.)

## Net public-facing landing (under the staged Option-B view re-point)
726 → **672** counted-completed (**−54** = 13 true false-completions `does_not` + 41 genuinely-unverified `ambiguous` → harvest queue). Verified against the settled verdicts on a temp copy.

## ADU de-CKAN — independence proven
CPRA-only ADU survival = **551 / 553** (only 2 relied on CKAN/inferred → drop by evidence). The set was **not** inflated by the old `table_a2`-seeding. Vs the city: 547 agree (independent corroboration), **2 city-omitted** survivors retained (independence finding), **69 CKAN-only** held as **ingestion-backlog findings — NOT adopted** (pulling them from CKAN would re-leak the oracle).

## contested — deferred (stays 0)
No rule invented. Specifically **not** CPRA-vs-CKAN disagreement (CKAN is the oracle, not an independent source — that would be the role-crossing bug again). `contested` gets assigned later, in post-harvest reconciliation, when genuinely independent third sources (staff reports, AHCPs, inspections) are joined and can actually disagree. The schema state stays ready; assignment waits for real third sources. (This is where proj137's 82-vs-81 and its kind get adjudicated.)

## ACTION ITEM before the 8-year backfill — classifier blind spots
The 85-rescue (up from a 59 regex floor) exposed five patterns the ad-hoc rescue regex missed; these are **likely blind spots in `permit_role_classifier.py` itself** and should be added as candidate rules + self-tests **before** the backfill applies the classifier across 2018–2025:
1. **"Conversion of …"** (noun) is not matched by a verb-only `convert` rule → office/garage/commercial→dwelling conversions slip through.
2. **bare `ADU` / `JADU` / `(N) ADU`** with no creation verb (`505SF ADU`, `(N) ADU addition`).
3. **abbreviations** — `SINGLE FAMILY RES.`, `New Condo` (noun `condo` not in the residence vocabulary).
4. **`in law`** (space) vs hyphenated `in-law`.
5. **leading `Replace` / `Covert`-typo** lines force-bucketed as minor (`Replace garage with second dwelling unit`).

## Pending (separate go required)
- STEP 2 commit: re-point `v_projects_flat` to the **Option-B** gate (DDL staged `/tmp/v_projects_flat_OPTB_STAGED.sql`) against this settled state.
- STEP 5: single republish (explorer regen / push / purge — John's).
- Coverage note: proj176's `B2022-05117` (40-unit) sits outside the 819-classified set — the 8-year backfill resolves this durably by classifying all permits; Option-B is the correct interim gate until then.
