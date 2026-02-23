# APR Compliance Checklist for Berkeley Housing Data

**Generated:** 2026-02-22
**Current Data:** 115 projects, 5,470 units
**Target:** California HCD Annual Progress Report (APR) Tables A, A2, B

---

## Critical Gaps (Must Fix for APR Compliance)

### 1. Income Category Breakdown
**Status:** MISSING
**Impact:** Cannot calculate RHNA progress without income categorization
**Fields Needed:**
- [ ] `vli_units_dr` - Very Low Income with Deed Restriction
- [ ] `vli_units_ndr` - Very Low Income without Deed Restriction
- [ ] `li_units_dr` - Low Income with Deed Restriction
- [ ] `li_units_ndr` - Low Income without Deed Restriction
- [ ] `mod_units_dr` - Moderate Income with Deed Restriction
- [ ] `mod_units_ndr` - Moderate Income without Deed Restriction
- [ ] `above_mod_units` - Above Moderate Income
- [ ] `eli_units` - Extremely Low Income (subset of VLI)

**Action Items:**
1. [ ] Parse project descriptions for affordability mentions
2. [ ] Cross-reference with Berkeley Housing Dept. affordability database
3. [ ] Review density bonus applications (contain affordable unit counts)
4. [ ] Manual review for 17 large projects (100+ units)

### 2. APN (Assessor Parcel Number)
**Status:** Only 3 of 115 records have APN
**Impact:** Required field for state reporting
**Fields Needed:**
- [ ] `apn` - Current Assessor Parcel Number

**Action Items:**
1. [ ] Match addresses to `alameda_lookup_complete.csv` (563K addresses)
2. [ ] Extract APN column during geocoding process
3. [ ] Update `update_housing_data.py` to include APN lookup

### 3. Tenure Type (Owner/Renter)
**Status:** MISSING
**Impact:** Required field for APR
**Fields Needed:**
- [ ] `tenure` - "Owner" or "Renter"

**Action Items:**
1. [ ] Default 5+ unit projects to "Renter"
2. [ ] Default SFD/ADU to "Owner" unless rental mentioned
3. [ ] Parse descriptions for "rental", "for-rent", "ownership"

---

## High Priority Gaps

### 4. Permit Stage Dates
**Status:** MISSING
**Impact:** Cannot determine reporting year for multi-year projects
**Fields Needed:**
- [ ] `entitlement_date` - Date zoning/use permit approved
- [ ] `building_permit_date` - Date building permit issued
- [ ] `certificate_of_occupancy_date` - Date CO issued

**Action Items:**
1. [ ] Extract dates from BuildingEye downloads
2. [ ] Query Berkeley permit API when unblocked
3. [ ] Add date parsing to data pipeline

### 5. Unit Category
**Status:** Derivable but not implemented
**Impact:** Required for APR
**Fields Needed:**
- [ ] `unit_category` - SFD, SFA, 2-4, 5+, ADU, MH

**Action Items:**
1. [ ] Classify based on net_units: 1=check description, 2-4='2-4', 5+='5+'
2. [ ] Parse descriptions for "ADU", "accessory dwelling", "single family"
3. [ ] Add classification logic to pipeline

---

## Medium Priority Gaps

### 6. Streamlining Flags
**Status:** Derivable from descriptions
**Fields Needed:**
- [ ] `sb35_approved` - SB 35 streamlining flag
- [ ] `sb330_project` - SB 330 application flag
- [ ] `ab2011_project` - AB 2011 ministerial flag

**Action Items:**
1. [ ] Regex search descriptions for "SB 35", "SB35", "SB 330", etc.
2. [ ] Add boolean flags to data model

### 7. Density Bonus Information
**Status:** Partially derivable
**Fields Needed:**
- [ ] `density_bonus_received` - Yes/No
- [ ] `density_bonus_units` - Number of bonus units
- [ ] `density_bonus_incentives` - Description of incentives

**Action Items:**
1. [ ] Parse descriptions for "density bonus"
2. [ ] Extract percentage and unit counts

---

## Low Priority / Optional Fields

### 8. Project Name
**Status:** MISSING (optional field)
**Action:** Could extract from descriptions or leave blank

### 9. Prior APN
**Status:** MISSING (optional field)
**Action:** Only needed if parcel was subdivided/merged

---

## Data Quality Issues

### Issue 1: Inconsistent Status Values
**Current values:** Under Review, In Review, Corrections Pending Applicant, etc.
**APR values:** Approved, Pending, Disapproved
**Action:** Create mapping table for status normalization

### Issue 2: Year Field as Float
**Current:** 2024.0
**Required:** 2024 (integer)
**Action:** Convert in export process

### Issue 3: Missing Old Units for 4 Records
**Impact:** Minor - affects net unit calculation
**Action:** Review records where old_units is null

---

## Recommended Schema Updates

Add these columns to `housing_projects_FINAL.csv`:

```python
new_columns = {
    # Required for APR
    'apn': 'text',
    'tenure': 'text',  # Owner, Renter
    'unit_category': 'text',  # SFD, SFA, 2-4, 5+, ADU, MH

    # Income breakdown
    'vli_units_dr': 'integer',
    'vli_units_ndr': 'integer',
    'li_units_dr': 'integer',
    'li_units_ndr': 'integer',
    'mod_units_dr': 'integer',
    'mod_units_ndr': 'integer',
    'above_mod_units': 'integer',
    'eli_units': 'integer',

    # Permit dates
    'entitlement_date': 'date',
    'building_permit_date': 'date',
    'co_date': 'date',

    # Streamlining flags
    'sb35_approved': 'boolean',
    'sb330_project': 'boolean',
    'ab2011_project': 'boolean',
    'density_bonus_received': 'boolean',
    'density_bonus_units': 'integer'
}
```

---

## Next Steps

1. **Immediate:** Add APN lookup from alameda_lookup_complete.csv
2. **This week:** Parse descriptions to extract affordability info
3. **This month:** Obtain permit dates from BuildingEye/city records
4. **Ongoing:** Build APR export function for Datasette

---

## Datasette Integration

Create APR-formatted views in SQLite:

```sql
-- Table A2 format view
CREATE VIEW apr_table_a2 AS
SELECT
    'BERKELEY' as JURIS_NAME,
    'Alameda' as CNTY_NAME,
    CAST(year AS INTEGER) as YEAR,
    apn as APN,
    address_display as STREET_ADDRESS,
    permits as JURS_TRACKING_ID,
    unit_category as UNIT_CAT,
    tenure as TENURE,
    -- Income fields (0 until populated)
    COALESCE(vli_units_dr, 0) as VLOW_INCOME_DR,
    ...
FROM projects;
```

---

## Sources

- [HCD APR Instructions](https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/housing-element-annual-progress-report-instructions.pdf)
- [HCD APR Forms](https://www.hcd.ca.gov/apr/forms)
- [California Open Data APR Dataset](https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year)
