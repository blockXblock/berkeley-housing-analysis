# CY 2024 APR Cross-Check — Notes

**Date:** 2026-05-26
**Author:** JG
**Context:** Follow-on to D6 (`04_reporting/D6_diff_d5_vs_hcd.ipynb`)
**Status:** Visual cross-check of Berkeley's submitted CY 2024 APR PDF; row-level reproduction (D5-equivalent for CY 2024) not yet built

---

## Purpose

Test whether the CY 2025 application-stage double-counting patterns documented in D6 reflect a systematic Berkeley reporting practice or are anomalies specific to the CY 2025 submission.

Patterns to check for in CY 2024:

1. Density-bonus projects appearing as base+bonus pairs (cf. 2029 University ZP2024-0181 + ZP2024-0182 in CY 2025)
2. Within-PDF arithmetic doubling — column totals reflecting summed-then-dedup gap (cf. 471 dedup vs 755 reported in CY 2025 Table A)
3. Exact row-pair duplication in Tables A and A2 (cf. 240 A2 dupes, 16/32 Table A rows in CY 2025)

## Source

Berkeley's CY 2024 Housing Element APR, submitted to HCD on March 21, 2025. Reviewed via the City Manager's March 28, 2025 memo to City Council, which includes:

- Attachment 1: Tables A (39 applications, 3,832 proposed units), A2 (new construction / entitled / permits / completed unit detail), B (RHNA progress), D (program implementation), K (tenant preference)
- Attachment 2: 2024 General Plan APR

## Findings

### 1. No base+bonus pair splitting in Table A

Every density-bonus project in CY 2024 Table A appears as a single ZP application carrying the project's full unit count (base + density-bonus units combined). Specifically verified:

| Address | ZP # | Total Units (Table A) |
|---|---|---|
| 1974 Shattuck | ZP2023-0040 | 599 |
| 2274 Shattuck | ZP2023-0079 | 227 |
| 2100 Milvia | ZP2023-0163 | 201 |
| 2037 Durant | ZP2023-0064 | 74 |
| 2462 Bancroft | ZP2023-0107 | 66 |
| 2530 Bancroft | ZP2023-0126 | 110 |

2274 Shattuck — which appears in the CY 2025 doubling pattern the following year — uses single-row treatment here. The 2029 University style of splitting one density-bonus project across two ZP application rows (one for base allocation, one for bonus allocation) is **not** the Berkeley default.

### 2. Table A summary arithmetic reconciles

Row-level sum of the seven income-category columns equals reported summary row total (3,832 proposed units). No within-PDF column-total doubling of the CY 2025 magnitude observed.

### 3. A2 does not show the exact-duplicate pattern

Visual inspection finds no row-pair duplications in A2. The A2 entitled total (2,037) matches the Units-by-Structure-Type 5+/SFD/ADU/2-to-4 totals in the affordability summary table.

### 4. One REV pattern divergence noted (flag for follow-up)

1951 Shattuck appears in A2 with parent permit B2021-04893 (163 units, full project, permits issued 10/24/24) plus a separate row B2021-04893-REV14 (7 additional units, 4/26/24). The REV row has the explicit note: *"Permit Revision to add 7 additional units to the original 156."*

This is a **marginal-delta REV treatment**, inconsistent with the cumulative-REV semantics D5/D6 documented for Berkeley's general practice (every REV sub-permit carries the project's running cumulative unit count). Suggests REV reporting is not internally consistent across projects.

**Action item:** row-level check of 1951 Shattuck against the CKAN mirror and the underlying CPRA BP data to characterize whether this REV is genuinely marginal-counted at source or whether Berkeley reported it differently in the APR than the CPRA data shows. If genuinely marginal, this is a case where the standard D5 REV-handling logic (master-permit-only) would *under*-count, not over-count.

### 5. City acknowledgment of reissuance double-counting

Page 5 of the City Manager's memo, section heading **"AUDITING BERKELEY'S RHNA NUMBERS"**:

> "Discrepancies are inherent to the annual APR process. Permits may be resubmitted and reissued, which can result in a change in the number of units or double-counting of units. When asked by staff about how to report reissued building permits, HCD responded that reporting each reissuance is permissible as long as it is noted as a reissuance in the report."

Berkeley acknowledges in writing that reissuance-driven double-counting is a known APR issue, and that HCD's guidance permits it conditional on annotation. This is material for the public-interest argument on the Planning Module CPRA and for any methodology page discussion of why independent reproduction is necessary.

### 6. Recurring HCD-prepopulated data discrepancy

Page 4 footnote 3 acknowledges that Table 4 in the memo (in-memo RHNA progress) ≠ Table B in the APR (in-APR RHNA progress) for 2023 numbers because the HCD-supplied prepopulated file contained a discrepancy the City could not edit. Same pattern as observed in CY 2025. Suggests a recurring HCD ↔ Berkeley data-handoff failure mode independent of the doubling issue.

## Headline numbers (for D7 reference)

- 39 applications submitted, 3,832 proposed units — Berkeley's largest entitlement pipeline year on record per the memo (vs. 25/2,224 in 2023, 26/1,324 in 2022)
- 1,235 units entitled from CY 2024 applications; 2,037 total units entitled in CY 2024 from applications of any date
- 731 building permits issued; 708 units completed (CO issued)
- 102 ADU permits, 91 ADU COs
- 83% of approved 5+ projects used State Density Bonus (per General Plan APR, page 5 of memo)

## Conclusion

The CY 2025 doubling pattern is most parsimoniously characterized as a **submission-level error** (Berkeley submitted twice; HCD load appended) rather than a methodological practice. The 2029 University base+bonus split appears specific to CY 2025 as well, though whether that split represents independently a Berkeley error or a one-off legitimate filing of two ZP applications under density-bonus law is a separate question that the Planning Module CPRA fulfillment should resolve.

CY 2024 verification supports the existing D6 framing that CY 2025 divergences are anomalies, not systematic patterns.

## Limitations

This cross-check is a **visual review** of Berkeley's submitted PDF, not an independent reproduction. A CPRA-derived CY 2024 APR (D5-equivalent for 2024) has not yet been built. The CPRA BP fulfillment data covers 2018-2025, so the inputs exist; constructing a CY 2024 reproduction is queued as a sibling to D5 and would programmatically verify the visual findings here.

The 1951 Shattuck REV observation in particular is from a single PDF row without CKAN cross-check; treat as a flag, not a conclusion.

## Related artifacts

- Source PDF: `data/raw/cpra-downloads/2025-03-28___Housing_Element_and_General_Plan_Annual_Progress_Reports.pdf` (or wherever the CY 2024 APR PDF was filed in the repo)
- D6 notebook: `04_reporting/D6_diff_d5_vs_hcd.ipynb`
- HCD mirror: `databases/hcd_apr_mirror.db`
- Planning Module CPRA: filed 2026-05-26 (see CPRA tracking log)
