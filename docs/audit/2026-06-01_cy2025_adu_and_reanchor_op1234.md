# CY2025 ADU Ingest + Re-anchors + Corrected ADU Classification — 2026-06-01

**Third data-modifying operation** on `berkeley_housing_v2.db`. One gated
transactional write (`scripts/write_op1234_cy2025_2026-06-01.py --commit`) covering
four operations under a **single corrected ADU-aware classification rule applied
identically to both CY2024 and CY2025**, so the year-over-year trend is
methodologically uniform.

- **Pre-write snapshot / reversal point:** `databases/keep_snapshot_2026-06-01_pre-cy2025.db`
  (sha `ec4031f6`, integrity ok).
- **Canonical after write:** **`179434a8`** (integrity ok).
- **Post-write snapshot:** `databases/keep_snapshot_2026-06-01_post-cy2025-op1234.db`
  (sha `179434a8`, integrity ok).
- Gate: snapshot → read-only preview → transactional dry-run (BEGIN…rollback,
  numbers validated) → STOP for John → `--commit` with verify-or-rollback.

## Result — APR CO net-units (group-quarters excluded)

| Year | before | **after** | basis |
|---|---|---|---|
| **CY2024** | 709 | **709** | re-verified under the corrected rule (holds — see §4) |
| **CY2025** | 497 | **532** | −3 (2641) −68 (1752) +106 (90 ADUs) |
| **CY2026** | 144 | **216** | +72 (1752 re-anchored, permit-backed) |

## 1. The four operations

- **OP1 — 2641 College (id53): false 3u removed from CY2025.** Permit `B2025-02413`
  was *"replace 760 sf of deteriorated siding on the existing two-story main
  residence"* — an alteration, not new construction. It had been classified PRIMARY
  because the keyword rule read "two story" (describing the **existing** building)
  as a structural signal. Flipped PRIMARY→SUBSIDIARY; its sibling `B2024-03884`
  (add bathroom) was already subsidiary, so 2641 College's `co_issued_date` is now
  **NULL** (correctly out of CY2025).

- **OP2 — 1752 Shattuck (id164): re-anchored CY2025→CY2026, count corrected
  68→72, affordability corrected (see §2).** The only CY2025 "CO" was a manual
  `NO_DESC` event (2025-05-27, no permit). Accela inspection-Finaled dates are
  **05/06/2026 and 05/26/2026** — both 2026. Manual event removed; a permit-backed
  CO event was anchored to `B2023-00774` (*"72-unit, 7-story, mixed-use apartment
  building,"* $10.05M, classified PRIMARY) dated **2026-05-26**. Unit count set to
  **72** (CPRA `NumberUnits=72`; entitlement had been 68). **Flag for the paper:
  2023-permitted, completing 2026 — a pre-Middle-Housing project finishing
  post-policy; NOT policy evidence.**

- **OP3 — 90 CY2025 ADU/small completions ingested (106 net-new units),
  primary-source-only.** Same method as the CY2024 ingest (§ the 2026-06-01 ADU
  change-note): Bucket-A city CO parcels absent from v2, matched to a CPRA permit
  with a 2025 finaled date, units via Rule C (net-new), coords from Alameda
  assessor (`berkeley.db` via `normalize_apn`→`apn_norm`). Honest unknowns with
  provenance: `bedroom_count=NULL`, `tenure_type_id=8` (Unknown),
  `income_category_id=6` (UNKNOWN). CKAN used ONLY to define the Bucket-A target,
  never as a source.

- **OP4 — corrected ADU-aware classification applied to all 185 newly-ingested
  ADU permits** (95 CY2024 + 90 CY2025): **184 PRIMARY, 3 SUBSIDIARY**, plus 2
  re-pick permits PRIMARY. See §3 for the rule; §4 for the 3 dispositions.

## 2. 1752 Shattuck affordability — a data-integrity fix, stated explicitly

Re-anchoring 1752 Shattuck **also corrected an unsourced affordability assertion.**
The record carried `tenure_type_id=1` (Rental) and `income_category_id=5` (Above
Moderate / market-rate), both with **`source_document_id = NULL`** and
`asserted_by = migration_v1_to_v2_20260507` — i.e. **v1→v2 migration defaults, not
primary-sourced.** They also **contradicted the project's own State Density Bonus
designation** (recorded in the migration's version description), which by definition
requires below-market set-aside units — so "all Above-Moderate" cannot be correct.

Per the project's non-negotiable rule (record "unknown with provenance," never
assert what no primary source supports), these were reset to
**`tenure_type_id=8` (Unknown)** and **`income_category_id=6` (UNKNOWN)** with a
provenance note. Only the **unit count (72) is primary-sourced** (permit
`B2023-00774`). **The real tenure/affordability mix lives in the DRCP application
packet — `documents` id 910 (`Reviewed B2023-00774.pdf`, 55 MB) — which has not yet
been extracted.** This is logged, not buried: the 72 units are CO-counted but their
affordability is honestly unknown pending that extraction.

## 3. The corrected ADU-aware classification rule (applied identically to both years)

The original permit-fix keyword rule was built for **major projects** and misfired
on ADU language (it read "convert/legalize/JADU/conversion" as alterations). The
corrected rule, evaluated on each permit in order:

1. **Leading `demolish/demolition` → SUBSIDIARY** (a demo permit is never a
   completion — hard disqualifier, unchanged from the permit fix).
2. **CPRA `ADU = Yes`, OR description contains an ADU-creation verb** — `ADU` /
   `JADU` / `legalize` / `convert … into ADU/dwelling/unit` / garage-conversion /
   `conversion of … into` — **→ PRIMARY.** An ADU conversion or legalization **is**
   a housing completion, not an alteration. (This corrects the inverse of the 2641
   College gap.)
3. **Otherwise fall through to the major-project rule** (structural keywords →
   PRIMARY; alteration keywords solar/window/remodel/etc → SUBSIDIARY;
   valuation ≥ $1M without an alteration keyword → PRIMARY; else AMBIGUOUS).
   The 2 CY2024 `AMBIGUOUS` results (26 Rock Ln — a 457 sf **junior ADU**
   confirmed from full permit text; 1415 Fifth St — multi-building new
   construction) were hand-adjudicated → PRIMARY.

**Applied identically to all 185 permits across both CY2024 and CY2025**, so the
two years are classified by one consistent method and the trend is comparable.

### Honest methodology caveat (known narrow limitation)
The keyword rule can still **misfire when an alteration permit mentions the
existing building's size** (e.g. "…siding on the existing **two-story** residence"
reads as structural). 2641 College (OP1) was exactly this case and was caught by
hand review. This residual ambiguity is disclosed, not hidden; classification is
auditable via the `permit_classified_primary`/`_subsidiary` events
(`event_date='2026-06-01'`) and is reversible.

## 4. CY2024 re-verification — 709 holds, not grandfathered

Because OP4's corrected rule reaches **back** into the already-committed CY2024
ingest, CY2024 was re-counted under the **same** rule rather than grandfathered.
Of the 13 CY2024 ADU permits the old rule wrongly flagged subsidiary:
- **10 are type-(a) real ADUs** (JADU / legalize / conversion) → reclassified
  **PRIMARY**; their units stay counted. **709 unaffected.**
- **3 are type-(b) wrong-permit-picks** (the Rule-C best-permit pick had attached
  an alteration permit as the "completion"), adjudicated individually:
  - **proj190 / 1341 Addison (2u)** — wrong pick was solar `B2024-04970`;
    **re-picked to `B2023-01652`** *"convert single-family home to duplex,"* finaled
    **2024-10-16**. Units kept, provenance corrected.
  - **proj207 / 483 Boynton (1u)** — wrong pick was kitchen/bath remodel
    `B2023-03742`; **re-picked to `B2023-04099`** *"convert basement into JADU,"*
    finaled **2024-06-27**. Units kept, provenance corrected.
  - **proj208 / 469 Kentucky (0u)** — wrong pick was a **demolish** permit; the real
    build (`B2023-04389`) finals 2025-12-11 and is a 0-net-unit SFR→SFR replacement.
    **Removed from CY2024** (demolish is no completion; 0u → no numeric effect).

**Net CY2024 = 709, re-confirmed under the corrected rule.** Both years now rest on
one uniform classification.

## 5. Row deltas / reversal path
- Canonical `ec4031f6` → **`179434a8`**. Projects 276→**366** (+90 ADUs); +90
  parcels / project_versions / unit_program / affordability / permits / CO events;
  +187 classification events (184 primary + 3 subsidiary); OP1/OP2 event edits.
- **Restore:** `cp databases/keep_snapshot_2026-06-01_pre-cy2025.db
  databases/berkeley_housing_v2.db` (sha `ec4031f6`). Post-write reversal point:
  `databases/keep_snapshot_2026-06-01_post-cy2025-op1234.db` (sha `179434a8`).

## Write-time verification (committed only because all passed)
permit-fix intact (2138 Kittredge bp=NULL; DB-level major CY2024=786) · CY2024
excl-UC = **709** · CY2025 excl-UC = **532** · CY2026 excl-UC = **216** · 2641
College CO=NULL · 1752 Shattuck CO=2026-05-26 / 72u / tenure=8 / income=6 · 469
Kentucky CO=NULL · 1341 Addison CO=2024-10-16 via B2023-01652 · 483 Boynton
CO=2024-06-27 via B2023-04099 · projects=366 · foreign_key_check=0 ·
integrity_check=ok.

*DBs gitignored; this note + the script are tracked. CKAN remained the verification
target throughout, never a source. Push HELD for John's review of both change-notes.*
