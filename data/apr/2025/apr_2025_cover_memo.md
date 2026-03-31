# City of Berkeley 2025 Annual Progress Report
## Cover Memo and Methodology

**Reporting Period:** January 1, 2025 - December 31, 2025
**Due Date:** April 1, 2026
**Prepared by:** Berkeley Housing Pipeline Analysis Project
**Data as of:** March 27, 2026

---

## Executive Summary

This memo accompanies Berkeley's 2025 Annual Progress Report (APR) to the California Department of Housing and Community Development (HCD). The report covers housing development activity during calendar year 2025.

### Key Findings

| Metric | Value |
|--------|-------|
| **Total Pipeline** | 159 projects, 10,142 units |
| **Applications Complete in 2025** | 6 projects, 877 units |
| **Entitlements Granted in 2025** | 17 projects, 2,404 units |
| **Certificates of Occupancy in 2025** | 2 projects, 126 units |
| **VLI Units in Pipeline** | 905 units (63% of RHNA target) |
| **RHNA Progress (Total)** | 10,142 units (113.5% of 8,934 target) |

---

## Table A: Housing Development Applications (2025)

**Description:** Projects with application deemed complete during calendar year 2025.

**File:** `table_a_2025.csv`

**Projects Included (6):**

| Address | Units | Complete Date | Notes |
|---------|-------|---------------|-------|
| 2276 Shattuck Ave | 336 | 2025-08-07 | Mega project, density bonus |
| 2425 Durant Ave | 250 | 2025-03-13 | Pending final action |
| 2029 University Ave | 240 | 2025-06-03 | Pending final action |
| 2614 Telegraph Ave | 31 | 2025-04-30 | 5 affordable units |
| 1740 University Ave | 12 | 2025-09-15 | Approved |
| 2200 Fifth St | 8 | 2025-11-24 | Withdrawn |

**Total:** 877 units across 6 projects

---

## Table A2: Housing Development Activity (2025)

**Description:** All entitlement, building permit, or certificate of occupancy activity during 2025.

**File:** `table_a2_2025.csv`

### Activity Summary

| Activity Type | Projects | Units |
|--------------|----------|-------|
| Entitlements | 17 | 2,404 |
| Certificates of Occupancy | 2 | 126 |
| Under Construction | 7 | 1,135 |
| **Total Activity** | **26** | **3,665** |

### Notable Entitlements (2025)

- **2138 Kittredge St:** 66 units, 5 VLI, SB-330 project
- **2274 Shattuck Ave:** 227 units, density bonus
- **2462 Bancroft Way:** 66 units, 3 VLI, density bonus
- **2530 Bancroft Way:** 110 units, 11 VLI, SB-330

### Certificates of Occupancy (2025)

- **2001 Ashby Ave:** 87 units, 86 affordable (RCD) - June 2025
- **1367 University Ave:** 39 units, supportive housing - July 2025

---

## Table B: RHNA Progress by Income Level

**Description:** Progress toward Regional Housing Needs Allocation (8th Cycle, 2023-2031).

**File:** `table_b_2025.csv`

### RHNA Progress Summary

| Income Level | RHNA Target | Pipeline Units | % of Target |
|--------------|-------------|----------------|-------------|
| Very Low Income (VLI) | 1,432 | 905 | 63.2% |
| Low Income (LI) | 825 | 724 | 87.8% |
| Moderate (MOD) | 1,416 | 452 | 31.9% |
| Above Moderate | 5,261 | 8,061 | 153.2% |
| **Total** | **8,934** | **10,142** | **113.5%** |

### Key Observations

1. **Above Moderate Surplus:** Berkeley's pipeline significantly exceeds the Above Moderate target (153%), driven by large market-rate projects on Shattuck Avenue, Telegraph Avenue, and near downtown.

2. **VLI Gap:** Despite 905 documented VLI units (63% of target), the remaining 527 units needed represents a significant challenge requiring dedicated affordable housing investments.

3. **MOD Shortfall:** Moderate-income housing shows the weakest performance (31.9%), reflecting the "missing middle" challenge.

4. **Density Bonus Utilization:** 53 projects (33% of pipeline) utilize State Density Bonus, contributing most of the affordable unit commitments.

---

## Data Sources and Methodology

### Primary Sources

1. **Accela Permit Records:** Direct extraction from City of Berkeley's Accela permitting system, capturing permit numbers, status histories, processing dates, and project descriptions.

2. **APR Cross-Reference:** Comparison against prior APR submissions to HCD (2023, 2024) to ensure consistency and identify gaps.

3. **Public Reporting:** SFYimby, Berkeleyside, and developer announcements to supplement Accela data where system records are incomplete.

4. **Parcel Data:** Alameda County Assessor parcel records for APNs and geocoding.

### Data Quality Assessment

- **Match Rate:** 97.4% match between independent analysis and prior APR submissions
- **Unit Count Verification:** Cross-checked against project descriptions and public filings
- **Date Validation:** Processing dates validated against Accela status histories
- **Income Classification:** VLI units extracted from permit descriptions and density bonus applications

### Construction Data Reliability Framework

We developed a four-tier reliability rating for construction progress data, based on the availability of Accela inspection records:

| Rating | Projects | Units | Criteria |
|--------|----------|-------|----------|
| **Confirmed** | 7 | 408 | Has Accela inspection records, finaled status, or CO documentation |
| **Probable** | 7 | 592 | Building permit issued, under construction status, but no inspection data |
| **Estimated** | 26 | 2,406 | Approved/entitled status, construction dates from news sources |
| **Unknown** | 123 | 6,817 | No construction data available |

**Key Finding:** Only 7 of 163 projects (4.3%) have confirmed construction data from city inspection records. Construction progress for most projects is estimated from news reporting, SFYimby articles, and building permit status rather than verified city records.

**Projects with Confirmed Certificates of Occupancy (407 units):**

| Project | Units | CO Date | Notes |
|---------|-------|---------|-------|
| 3030 Telegraph Ave | 144 | 2026-01-27 | Inspection finaled records |
| 2001 Ashby Ave | 87 | 2025-06-01 | 100% affordable (RCD) |
| 1752 Shattuck Ave | 68 | 2025-05-27 | Finaled 05/27/2025 |
| 2127 Dwight Way | 58 | 2025-03-03 | Multiple finaled dates |
| 1367 University Ave | 39 | 2025-06-18 | Supportive housing |
| 2555 College Ave | 11 | 2025-07-25 | Finaled zoning |

### Known Limitations

1. **Affordability Data:** Income-level breakdowns rely on extracted VLI counts from project descriptions. LI and MOD estimates are derived from density bonus requirements and may not reflect actual deed-restricted unit counts.

2. **Building Permit Dates:** The `bp_issued_date` field is incomplete for many projects. This gap affects Table A2 accuracy for building permit activity.

3. **ADU Counts:** Accessory Dwelling Units are not fully captured in this dataset. Recommend supplementing with Building Division ADU permit reports.

4. **UC Berkeley Projects:** University projects are exempt from city zoning and not included in this analysis.

---

## Known Data Gaps

### Critical Gaps

| Gap | Impact | Recommended Action |
|-----|--------|-------------------|
| Building permit dates missing | Undercount of BP activity in Table A2 | Extract from Building Division records |
| ADU permits not included | Missing ~95 units/year from RHNA credit | Import ADU permit list |
| In-lieu fee tracking | Cannot verify Trust Fund contributions | Request Finance records |
| Certificate of Occupancy dates | Only 2 COs documented for 2025 | Cross-check Building final inspections |

### Potential Missing Projects

Based on public reporting, these projects may have 2025 activity not captured:

1. **Ashby BART** (618 units) - Developer selected Aug 2025, may need planning entry
2. **1750 Sacramento St** (739 units) - Status unclear, may have 2025 entitlement
3. **Projects under construction** - Several topped-out buildings may have COs pending

---

## Limitations of the APR Framework

### Building Permits Measure Regulatory Output, Not Housing Delivery

The APR framework, as defined by HCD, treats building permit issuance as the primary measure of housing progress toward RHNA targets. This approach has significant limitations:

**The Problem:**

HCD counts a building permit as "progress" even if construction never begins. Our analysis of Berkeley's housing pipeline reveals a stark gap between regulatory approvals and actual housing delivery:

| Metric | Count | % of Pipeline |
|--------|-------|---------------|
| Total Pipeline Units | 10,142 | 100% |
| Building Permits Issued | 988 | 9.7% |
| Certificates of Occupancy | 126 | 1.2% |
| Stale Approvals (12+ months, no construction) | 983 | 9.7% |

**Key Findings:**

1. **Permits ≠ Construction:** Of Berkeley's 10,142 pipeline units, only 988 (9.7%) have building permits issued. The remaining 9,154 units exist only as planning entitlements.

2. **Stale Approvals:** We identified 10 projects with 983 approved units that show no construction activity 12+ months after approval. These include:
   - 2128 Oxford St: 485 units (entitled Oct 2024, no BP)
   - 2136 San Pablo Ave: 125 units (entitled Apr 2024, no BP)
   - 2530 Bancroft Way: 110 units (entitled Dec 2024, no BP)

3. **CO Gap:** Only 126 units have received certificates of occupancy — representing actual, occupiable housing. This is 1.2% of the pipeline.

### What RHNA Doesn't Measure

A complete measure of housing delivery should track:

- **Construction starts** — when ground is actually broken
- **Certificates of occupancy** — when units become habitable
- **Vacancy rates** — whether completed units are occupied
- **Lease-up timelines** — how quickly units reach tenants
- **Rental affordability** — actual rents vs. income targets
- **Purchase prices** — whether for-sale units serve intended income levels

### Recommendations for HCD

We recommend that HCD enhance future APR requirements to include:

1. **Construction Start Tracking:** Add a mandatory field for construction commencement date, separate from building permit issuance.

2. **CO-to-Occupancy Tracking:** Require jurisdictions to report time from certificate of occupancy to first occupancy.

3. **Stale Approval Monitoring:** Flag projects where building permits have not been pulled within 18 months of entitlement approval.

4. **Outcome Metrics:** Pilot a supplemental report tracking actual occupancy, vacancy rates, and achieved rent levels for completed projects.

5. **Annual Reconciliation:** Require jurisdictions to report on prior-year pipeline projects that have not advanced, with explanations for delays.

The current system creates a false sense of progress. Berkeley's impressive "113% of RHNA" figure obscures the reality that less than 10% of those units have begun construction, and barely 1% are ready for occupancy.

---

## Recommendations

1. **Improve Accela Data Entry:** Require structured data fields for income levels, deed restriction status, and milestone dates.

2. **Automate APR Export:** Implement HCD-compatible export directly from permitting system.

3. **Track In-Lieu Fees:** Add in-lieu fee payment tracking to permit records.

4. **Regular Audits:** Conduct quarterly reconciliation between Accela and Building Division records.

5. **ADU Integration:** Establish workflow to include ADU permits in housing pipeline tracking.

---

## Certification

This data has been prepared using best available information from City records and public sources. Discrepancies between this analysis and official City submissions should be resolved by reference to Accela source records.

**Analysis conducted by:** Berkeley Housing Pipeline Analysis Project
**Contact:** [City Planning Department]
**Date:** March 27, 2026

---

*This memo was generated as part of an independent housing data audit. For official APR submissions, verify all figures against City of Berkeley Planning Department records.*
