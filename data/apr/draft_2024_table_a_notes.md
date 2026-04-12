# Draft 2024 APR Table A Notes

**Generated:** 2026-03-21
**Source:** housing_projects_FINAL.csv (118 projects total, 39 in 2024)

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total 2024 Projects | 39 |
| Approved | 5 |
| Pending | 34 |
| Disapproved | 0 |
| Total Proposed Units | 3,508 |
| VLI Units (deed-restricted) | 88 |
| LI Units (deed-restricted) | 35 |
| MOD Units (deed-restricted) | 41 |
| Above Moderate Units | 3,344 |
| Density Bonus Projects | 16 |
| SB 35 Projects | 0 |

## Data Limitations

### Critical Missing Data

1. **APP_SUBMIT_DT (Application Submission Date)**
   - Column is empty for all rows
   - Source data does not include application submission/complete dates
   - **Action Required:** Cross-reference with Accela permit system to obtain dates

2. **Income Unit Counts**
   - VLI/LI/MOD extracted from description text via regex patterns
   - Only 15 of 118 projects had extractable income unit counts
   - Many Density Bonus projects mention affordability % but not exact unit counts
   - **Action Required:** Manual review of descriptions, or obtain from permit records

3. **Deed Restriction Status**
   - All affordable units assumed to be deed-restricted (DR columns)
   - No data distinguishing DR vs NDR units
   - **Action Required:** Verify with affordability covenant records

### Assumptions Made

1. **Status Mapping**
   - All non-Approved statuses mapped to "Pending" per APR requirements
   - No projects mapped to "Disapproved" (Berkeley data doesn't track denials)
   - See `data/reference/apr_status_mapping.json` for complete mapping

2. **Unit Categories**
   - Used source `unit_category` field (SFD, SFA, 2-4, 5+, ADU)
   - Defaulted to 5+ for projects with 5+ units if not specified

3. **Tenure**
   - Used source `tenure` field
   - Defaulted to "Renter" for 5+ unit projects, "Owner" for smaller

4. **Above Moderate Calculation**
   - `ABOVE_MOD_INCOME = TOT_PROPOSED_UNITS - (VLI + LI + MOD)`
   - May overstate market-rate if income extraction missed affordable units

### Projects Needing Manual Review

The following 2024 projects have Density Bonus but no extracted income units:

| Address | Permits | Net Units | Notes |
|---------|---------|-----------|-------|
| 2276 SHATTUCK Ave | ZP2024-0067 | 336 | Description mentions "56 units dedicated to VLI" |
| 2700 SHATTUCK Ave | ZP2024-0058 | 276 | SB330, no affordability details |
| 2029 UNIVERSITY Ave | ZP2024-0181+ | 240 | Description mentions 18 VLI + 18 MOD |
| 2720 SAN PABLO Ave | ZP2024-0076 | 113 | Description mentions 10 VLI + 6 MOD |
| 2109 VIRGINIA St | ZP2024-0066 | 131 | Description mentions 11 VLI + 9 MOD |
| 2847 SHATTUCK Ave | ZP2024-0077 | 132 | Description mentions 14% VLI |

### Files Generated

1. `data/apr/draft_2024_table_a.csv` - Draft APR Table A submission
2. `data/reference/apr_status_mapping.json` - Status value mapping
3. `data/processed/income_extraction_audit.csv` - Income extraction audit trail

## Next Steps

1. Obtain application submission dates from Accela permit records
2. Manually verify income unit counts for Density Bonus projects
3. Cross-reference with building permit records for any projects that received CO
4. Submit via HCD Connect portal by April 1, 2026

## Column Reference

| APR Column | Source Field | Transformation |
|------------|--------------|----------------|
| JURIS_NAME | (constant) | "Berkeley" |
| CNTY_NAME | (constant) | "Alameda" |
| YEAR | year | Filtered for 2024 |
| APN | apn | Direct |
| STREET_ADDRESS | address_display | Direct |
| JURS_TRACKING_ID | permits | Direct |
| UNIT_CAT | unit_category | Mapped to allowed values |
| TENURE | tenure | Direct |
| APP_SUBMIT_DT | (missing) | Needs Accela lookup |
| VLOW_INCOME_DR | (extracted) | From description regex |
| LOW_INCOME_DR | (extracted) | From description regex |
| MOD_INCOME_DR | (extracted) | From description regex |
| ABOVE_MOD_INCOME | (calculated) | net_units - affordable |
| TOT_PROPOSED_UNITS | net_units | Direct |
| TOT_APPROVED_UNITS | net_units | Only if status="Approved" |
| APPLICATION_STATUS | status | Mapped via apr_status_mapping.json |
| APP_SUBMITTED_SB35 | sb35_flag | True→"Yes", else "No" |
| DENSITY_BONUS_RECEIVED | density_bonus | True→"Yes", else "No" |
