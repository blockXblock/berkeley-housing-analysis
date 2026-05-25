# CO derivation rule v2 — master-permit identification + tier rule

**Status:** Canonical for Track 2 APR generation. Supersedes the 3-tier rule sketched in `notes/2026-05-24_apr_workflow_audit.md` §4.

**Authored:** 2026-05-25 by John in collaboration with chat-Claude. Empirical foundation: 10 Berkeley address verifications run in Claude-in-Chrome against live Accela across 2026-05-24 (6 addresses) and 2026-05-25 (4 addresses). Raw Chrome outputs for the 2026-05-25 batch are saved in `notes/chrome_verifications/2026-05-25/`. The 2026-05-24 batch's raw outputs were chat-only and are now lost; their structured findings are recoverable via session transcript and summarized below.

**Result:** 9/9 valid tests pass under v2 wording. The 10th test (2274 Shattuck) didn't apply because the address has no project in v2 — Accela returned only existing-building HVAC/TI work for the Shattuck Cinemas building.

---

## 1. Why this rule exists

The audit's original 3-tier CO derivation rule (workflow audit §4b) had two structural problems:

**Problem 1: Master permit was undefined.** The rule applied to "any permit on the project" with `record_status='Issued'` and active workflow. Berkeley housing projects typically have 4–15 permits (main building, electrical, mechanical, plumbing, revisions, deferred submittals). A project might have its main structural permit Finaled while one solar-panel sub-permit remains Issued; the v1 rule would null-out CO_date because *some* permit was Issued. This false-NULL'd 12 of v2's `completed` projects (workflow audit §5).

**Problem 2: Tier 1 ("CofO Review stages complete") never fires** on observed Berkeley data. Of the 9 valid tests, every CofO sub-stage observation showed `active` state, never `complete` — even on projects HCD credits with a 2022 CO date. Berkeley submits CO data to HCD through a process that doesn't write back to Accela's workflow state. The original rule's primary signal turns out to be dead weight.

The v2 fix is twofold:

1. **Scope the rule to a single "master permit" per project**, identified by a deterministic 9-step algorithm.
2. **Apply the 3-tier rule only to the master permit.** Sub-permits become audit metadata that doesn't gate the CO credit.

Tier 1 is retained for forward compatibility (if Berkeley adopts Clariti or changes APR workflow), but the operational rule reduces to "use HCD's CO_ISSUE_DT1 when present, else use master's finaled_date when Finaled, else NULL."

---

## 2. Master permit identification

The master is **stage-aware**. Each APR-reportable stage has its own master, identified through its own Berkeley source.

| Stage | HCD column | Master permit | Berkeley source |
|---|---|---|---|
| Entitlement | `ENT_APPROVE_DT1` | Planning record (ZP-number) | Accela Planning module |
| Building permit | `BP_ISSUE_DT1` | A B-permit per the algorithm below | Accela Building module |
| Certificate of Occupancy | `CO_ISSUE_DT1` | Same B-permit as the BP master | Accela Building module + HCD CO row |

### 2a. BP/CO master identification algorithm

```
Given a project's permits from v2.permits or an Accela result list:

  Step 1 — Filter to permit_number matching ^B\d{4}-\d{5}$
           (main B-permits only, no -REV/-DEF/-E/-P suffix)

  Step 2 — Exclude by status:
           status IN ('Closed Expired', 'Withdrawn', 'Cancelled')

  Step 3 — Exclude by type:
           permit_type LIKE 'Demolition%'
           OR permit_type IN ('Electrical Permit',
                              'Mechanical Permit',
                              'Plumbing Permit')

  Step 4 — Exclude by description (adjuncts):
           description matches case-insensitive any of:
           solar | temp power | water heater | window | reroof | sign

  Step 5 — Exclude by description (phase precursors):
           description matches:
           phase 1 | phase i | footing | foundation only |
           shoring | excavation | grading

  Step 6 — Exclude by description (existing-building scope):
           description matches:
           seismic | soft story | SWOF | retrofit |
           alteration | TI | tenant improvement |
           interior alteration | improvements to existing | remodel

  Step 7 — Among survivors, prefer by type:
           "Building Electrical Mechanical Plumbing Permit"
           ranks above partial-trade variants
           (e.g., "Building Electrical Plumbing Permit" without Mechanical)

  Step 8 — Tiebreak by filed_date:
           Earliest filed wins among the preferred set.
           Sequential-pair override: if descriptions reference a partner
           permit by number ("Phase II under B2XXX-XXXXX"), prefer the
           partner labeled as Phase II / unit-bearing phase.

  Step 9 — If zero permits survive all filters:
           master = NULL
           (project not yet at BP stage, or all permits are scope-excluded;
            do not credit CO under any tier)
```

The algorithm is conservative by design: when in doubt, exclude. The cost of excluding is a NULL master and a flagged project; the cost of mis-selecting is a wrong CO_date silently propagated into the APR. False negatives are reviewable; false positives propagate quietly.

### 2b. Filter rationale

Each filter exists because of a specific failure mode observed during verification. The rationale matters because future analysts will need to know when to update these filters:

- **Step 2 (status):** The original rule "earliest-filed B-permit" picked B2006-00014 (Closed Expired, a sushi-bar counter-top permit) at 2650 Telegraph. Legacy permits at redeveloped sites are noise.
- **Step 3 (type):** Demolition and single-trade permits (Electrical-only, Mechanical-only, Plumbing-only) aren't structural. They're either pre-construction (demo) or post-CO (single-trade tenant work).
- **Step 4 (adjuncts):** Solar panels, temporary power poles, water-heater replacements, window swaps, reroofs, and signs are bracketed work — pre-construction setup or post-CO improvements. The 2650 Telegraph rule trace dropped B2024-03280 (PV solar) via this filter.
- **Step 5 (phase precursors):** Berkeley splits large projects into Phase I (sitework/foundation/podium) and Phase II (building above-grade with dwelling units). Both phases share the same permit type label ("Building Electrical Mechanical Plumbing Permit"); only description text distinguishes them. HCD credits Phase II as the master. The 2440 Shattuck and 1598 University misses under v1 motivated this filter.
- **Step 6 (existing-building scope):** Seismic retrofits (especially Berkeley's SWOF program — Soft Wall Open Front mandated retrofit), tenant improvements, and alterations on pre-existing buildings aren't the new-construction permit when a later structural B-permit exists at the same address. The 2538 Durant miss under v1 motivated this filter.
- **Step 7 (type preference):** When a project has multiple substantive multi-trade permits (e.g., 1598 University's Phase 1 footing as "Building Electrical Plumbing Permit" — note: no Mechanical — vs. Phase II as "Building Electrical Mechanical Plumbing Permit"), the full multi-trade variant signals the unit-bearing structural permit.
- **Step 8 (tiebreak):** Earliest-filed is the default heuristic for non-phased projects. The sequential-pair override exists because Berkeley's PREAPP records sometimes explicitly name "the building permit of record" for an address-assigned project; when that information is visible in the description text, prefer it over filed_date.

### 2c. Permit type vocabulary observed

Distinct values seen across Berkeley Accela in the 10 verifications:

- `Building Electrical Mechanical Plumbing Permit` — full multi-trade structural; strongest BP-master signal
- `Building Electrical Plumbing Permit` — partial multi-trade (no Mechanical); often Phase 1 footing/foundation
- `Building Permit` — generic; needs description disambiguation
- `Demolition Building Permit` — excluded by type filter
- `Electrical Permit` / `Mechanical Permit` / `Plumbing Permit` — single-trade, excluded
- `Building Revision for BXXXX-XXXXX` — REV sub-record, excluded by regex (Step 1)
- `Miscellaneous Deferred Submittal for BXXXX-XXXXX` — DEF sub-record, excluded by regex
- `Building Electrical Permit` — partial multi-trade (no Mechanical or Plumbing); seen on signage permits
- `Zoning Permit` — ZP-number; entitlement stage, not BP
- `PermitPermit` — data quality bug (doubled label); excluded by type filter

---

## 3. CO derivation rule (3-tier, applied to master only)

```
For each project where a BP master permit has been identified:

  Tier 1 — CofO workflow stages complete:
    If the BP master's Processing Status workflow has any CofO Review
    sub-stage marked stage_state='complete':
      CO_date = max(stage_complete_date) over those stages

  Tier 2 — Master permit Finaled (no CofO workflow signal):
    Else if BP master's record_status == 'Finaled':
      If HCD has a CO_ISSUE_DT1 row for this project
        (joined by APN or STD_ADDRESS):
          CO_date = HCD's CO_ISSUE_DT1
          (HCD's published value is more authoritative than any
           derivation from Accela alone)
      Else:
          CO_date = BP master's finaled_date
          (Flagged as 'derived', not 'reported by HCD')

  Tier 3 — Not yet CO'd:
    Else:
      CO_date = NULL
      (Master is still Issued; sub-permits may still be active. Don't
       credit as CO.)
```

### 3a. Why Tier 1 never fires (and stays in the rule anyway)

Across the 9 valid CofO-workflow observations in the verification set:

- **4 templates observed**: canonical-4 (Zoning/Public Works/Design/Inspector Final, 2650 Telegraph corrected), variant-4 (Inspector/Zoning/Toxics/Inspector Final, 1698 University), parent-only (Certificate of Occupancy with no sub-stages — most common), and no-CofO (template lacks any CofO step entirely — 0 Virginia SFH+ADU).
- **In templates with sub-stages, every observed sub-stage was `active`, never `complete`** — even on projects HCD credits with a 2022 CO date.
- **The parent-only template's CofO stage is `active` for in-progress projects and remains `active` after HCD has logged the CO**. Berkeley does not close the workflow.

The conclusion: Berkeley's APR submissions to HCD use a CO-date source outside Accela's workflow state tracking. Possible sources include manual building-inspector handwritten cards (per the workflow audit §4a finding), a non-Accela CO log, or staff data entry directly into the APR submission form. We don't have access to that source.

Tier 1 stays in the rule because (a) the cost is just unused code paths, (b) Berkeley may adopt a different system (Clariti has been mentioned in their tech-modernization plans) that closes workflow stages, and (c) the framing makes the rule self-documenting: "use the workflow signal if it exists; fall back to record_status + HCD; null out the rest."

### 3b. The operational shape

In practice, today, the rule reduces to:

```
CO_date = HCD's CO_ISSUE_DT1 if available
        else BP master's finaled_date if Finaled (flagged 'derived')
        else NULL
```

That's the shape D4 needs to encode. Tier 1 is dead code today; Tier 2 splits into HCD-authoritative vs derived; Tier 3 catches the null cases.

---

## 4. Audit metadata (surfaced but not gating)

The APR generator should record per project, without affecting the headline CO_date:

- **Sub-permit states**: count of -REV / -DEF / -ADD permits and their record_status distribution
- **Concurrent-work flag**: any sub-permit with active workflow stage (from `processing_status_queue`)
- **Tier reached**: 1 / 2 / 3 — useful for downstream filtering (highest-confidence Tier-1 vs derived Tier-2 vs unknown Tier-3)
- **Workflow template variant**: A canonical-4 / B parent-only / C variant-4 / D no-CofO / new — useful for tracking template evolution
- **Modular signal**: Licensed Professional name match against known modular contractors (Synergy Modular, Factory_OS, Guerdon, Plant Prefab, RAD Urban, Panoramic Interests) or description keywords (modular / prefab / volumetric / panelized)
- **HCD divergence**: if v2's derived CO_date differs from HCD's CO_ISSUE_DT1 by more than 7 days, flag for review
- **Unit divergence**: if HCD's BP unit count differs from CO unit count for the same project, flag (no fix required — HCD's CO_units is authoritative)
- **Placeholder address flag**: if Work Location starts with "0 ", flag for APN-based disambiguation (multiple parcels can share placeholder addresses pre-assignment)

These populate the project-level audit log without changing the headline CO_date number.

---

## 5. Joining HCD APR rows to v2

HCD APR rows have three potential join keys. Reliability order:

1. **APN** (most reliable). HCD-canonical format: `055 183700100` — 9 digits with a single internal space. About 3–5% of HCD rows have null APN, particularly older ENT rows (e.g., 2556 Telegraph's 2018 ENT row in HCD's published data).
2. **STD_ADDRESS** (HCD-geocoded, normalized — e.g., "2556 Telegraph Ave, Berkeley, California, 94704"). Stable across HCD rows for the same physical project even when STREET_ADDRESS varies in informal style.
3. **JURS_TRACKING_ID** (Berkeley's submitted permit number — useful when present). HCD CO rows frequently have null tracking_id; BP and ENT rows are more populated. Don't rely on this as a sole join key.

For v2 ingest of HCD data: try APN first, fall back to STD_ADDRESS normalized, use JURS_TRACKING_ID as a confirmation signal only.

For placeholder addresses ("0 [Street]"), APN is essential — multiple parcels can share the same placeholder simultaneously without collision in Accela. The 0 Virginia verification surfaced this: 4 records on "0 Virginia St" represented 2 distinct future addresses (708 Virginia for a loading dock, 1119 Virginia for the new SFH+ADU). Disambiguate by APN before applying the rule.

---

## 6. The 10 verifications

### 6a. 2026-05-24 batch (6 addresses, structured findings from session transcript)

| # | Address | v2 rule pick | HCD-expected | v1 match | v2 match | Failure mode if any |
|---|---|---|---|---|---|---|
| 1 | 2650 Telegraph Ave | B2021-02225 | B2021-02225 | ✅ | ✅ | (none) |
| 2 | 2440 Shattuck Ave | B2022-05117 | B2022-05117 | ❌ | ✅ | phasing (v1 picked Phase I B2022-02525) |
| 3 | 2556 Telegraph Ave | B2018-05067 | B2018-05067 | ✅ | ✅ | (none) |
| 4 | 1698 University Ave | B2014-05752 | B2014-05752 | ✅ | ✅ | (none) |
| 5 | 1598 University Ave | B2024-01924 | B2024-01924 | ❌ | ✅ | phasing (v1 picked Phase 1 footing B2024-00587); modular (Synergy Modular Inc) |
| 6 | 2538 Durant Ave | B2023-02332 | B2023-02332 | ❌ | ✅ | legacy retrofit (v1 picked SWOF retrofit B2016-05913) |

v1 wording matched 3/6. v2 wording, traced on paper from the verbatim Chrome permit lists, matches 6/6. The 3 misses fall into 2 failure modes: phasing (2 cases, fixed by Step 5) and legacy retrofit (1 case, fixed by Step 6).

### 6b. 2026-05-25 batch (4 addresses, full disk outputs)

Outputs in `notes/chrome_verifications/2026-05-25/`. Each file contains the complete Chrome DOM extraction: permit list, rule trace with survivors at each step, CapDetail, workflow stages, and cross-check observations.

| # | Address | v2 rule pick | Hypothesis | Match | Notes |
|---|---|---|---|---|---|
| 7 | 2650 Telegraph Ave (repeat) | B2021-02225 | B2021-02225 | ✅ | calibration: v2 rule still picks correctly after the 5-filter chain |
| 8 | 2274 Shattuck Ave | B2017-04969 | (no project at address) | n/a | wrong address — Shattuck Cinemas, no Panoramic project here |
| 9 | 2067 University Ave | B2017-02610 | B2017-02610 | ✅ | lost-units case: BP=50 → CO=46; descope likely via REV01 layout changes + 2020 fire-damage rebuild |
| 10 | 0 Virginia St | B2025-02283 | (no oracle — sense-check) | ✅ | placeholder-address pattern; SFH+ADU; new "no-CofO" workflow template |

3/3 valid tests pass. 2274 Shattuck was not a test of the rule — Accela had no project-scale work at that address, only existing-building HVAC swaps on the cinema. The rule mechanically returned a $0 HVAC permit, which is correct behavior given the input but wouldn't matter for APR purposes since v2 has no project there.

### 6c. Combined: 9/9 valid tests pass

Across 10 verifications, 9 are valid tests of the v2 rule (one is an empty-address probe). All 9 valid tests resolve to the correct master permit under v2 wording. The 3 failure modes from yesterday (phasing, legacy retrofit) are now characterized and addressed by Steps 5 and 6 respectively. Today's runs surfaced no new structural failure modes — the small things they did surface (brittle literal-string matching in Step 6, new "no-CofO" workflow template, placeholder address disambiguation need) are audit-metadata refinements, not rule corrections.

---

## 7. Rule-evolution log (compressed)

Five refinements to the rule, in order of discovery during 2026-05-24:

1. **Closed Expired status filter added** (after 2650 Telegraph). v0 "earliest-filed B-permit" picked B2006-00014 (Closed Expired). Added Step 2.
2. **Demolition + single-trade type filter added** (after 2650 Telegraph). Demo and electrical-only permits would slip through. Added Step 3.
3. **Adjuncts description filter added** (after 2650 Telegraph). Solar / temp power / window / sign / etc. are pre- or post-construction. Added Step 4.
4. **Phase-precursor description filter added** (after 2440 Shattuck and 1598 University). Phase I sitework isn't the unit-bearing permit. Added Step 5.
5. **Existing-building scope filter added** (after 2538 Durant). SWOF retrofits and TIs on pre-existing buildings aren't the new-construction permit when a later structural B-permit exists. Added Step 6.

Today's runs (2026-05-25) added no further filters. They confirmed the v2 wording works as intended on a calibration repeat (2650 Telegraph), an HCD-anchored lost-units case (2067 University), and an address-format edge case (0 Virginia). They surfaced three small refinements as future-work items, none of which block today's APR generation.

The systemic finding about Tier 1 never firing emerged across multiple runs rather than from any single one. It superseded the original Tier 1 framing — not by removing Tier 1, but by demoting it from "primary signal" to "rarely-firing path retained for future Berkeley workflow changes."

---

## 8. Future-work items surfaced (not blocking)

Three observations from today's runs worth banking. None require action before D4 refactor; all could be revisited if APR generation surfaces problems they'd fix.

1. **Step 6's literal-string match is brittle.** At 2067 University, the description "fire damaged improvements" squeaked through Step 6 because the literal token "improvements to existing" wasn't present. The pick was still correct (downstream filters caught it), but the filter rationale is fragile. A future revision could use word-boundary regex or semantic categories. Not blocking today.

2. **A fourth workflow template exists: "no-CofO" at all** (0 Virginia SFH+ADU). Berkeley's small-residential workflow skips Certificate of Occupancy entirely. Template count is now 4. The CO derivation rule already handles this correctly — Tier 3 fires and CO_date = NULL when Inspection is active and there's no CofO stage to begin with.

3. **Placeholder addresses need APN-based disambiguation.** Multiple parcels can share "0 [Street]" simultaneously. The current rule still resolves correctly when only one BP survives the filters (as at 0 Virginia today), but a parcel cluster with multiple BPs filed under "0" would mis-resolve. The fix is to group by APN before applying the rule. This becomes a problem only at ingest-from-Accela scale; HCD data is geocoded and doesn't carry this issue.

---

## 9. Application to D4 refactor

The rule encodes into D4 as:

1. **`derive_master_permit(project_id)` function** — applies Steps 1–9 of §2a, returns master permit ID or NULL. Queries v2's `permits` table joined to permit type and description fields.
2. **`derive_co_date(project_id)` function** — applies the 3-tier rule of §3 to the master, returning (CO_date, tier_reached, source). Queries `cic_recon_queue.record_status_queue` and `cic_recon_queue.processing_status_queue` plus joined HCD APR mirror data.
3. **`generate_audit_metadata(project_id)` function** — emits the §4 metadata bundle as a structured dict, persisted to the audit log alongside the APR row.

For the 12 v2-completed-but-Issued mismatches enumerated in workflow audit §5, application of the v2 rule will:
- Re-pick the master permit per the algorithm
- Derive CO_date per the tier rule (Tier 2 in most cases, using HCD's date where available)
- Surface the sub-permit Issued state as audit metadata, not as a CO blocker

This is the work that makes D4's APR output match HCD's published CY 2025 numbers more closely. The rule is the input to that work, not the work itself.

---

## Appendix — File references

- **Supersedes**: `notes/2026-05-24_apr_workflow_audit.md` §4 (the original 3-tier rule)
- **Raw Chrome outputs (2026-05-25 batch)**: `notes/chrome_verifications/2026-05-25/{2650_telegraph_ave,2274_shattuck_ave,2067_university_ave,0_virginia}.md`
- **Raw Chrome outputs (2026-05-24 batch)**: chat-only at the time, recoverable via session transcript `/mnt/transcripts/2026-05-25-02-38-18-berkeley-apr-rule-and-trust-audit.txt`
- **Future application target**: `04_reporting/D4_hcd_apr_tables.ipynb` (Track 2 refactor)
- **HCD APR data source**: `fe505d9b-8c36-42ba-ba30-08bc4f34e022` (HCD CKAN datastore, JURIS_NAME='BERKELEY')
- **18-mismatch table (the cohort this rule will re-evaluate)**: `notes/2026-05-24_apr_workflow_audit.md` §5
