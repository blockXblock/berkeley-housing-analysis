# HCD Annual Progress Report (APR) & Berkeley Pipeline

## What is the APR?

California law requires every city and county to submit an **Annual Progress Report (APR)** to the Department of Housing and Community Development (HCD). This report tracks:

- How many housing units were permitted during the year
- Progress toward the city's Regional Housing Needs Allocation (RHNA)
- Affordability breakdown (very low, low, moderate, above moderate income)

## Why It Matters

The APR is how California holds cities accountable for housing production. Cities that don't make progress face:
- Loss of certain funding eligibility
- State oversight of housing approvals
- Public scrutiny of housing policies

## How This Project Helps

Our notebooks help make APR production more **transparent and reproducible**:

### [D4: HCD APR Tables](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/04_reporting/D4_hcd_apr_tables.ipynb)

This notebook:
1. Explains what the APR requires
2. Maps Berkeley's housing data to APR fields
3. Generates an approximation of Table A2 (building activity)
4. Identifies gaps where data is missing

### What We Can Automate

| APR Field | Our Coverage | Notes |
|-----------|--------------|-------|
| Project ID | ✅ 100% | Unique identifier |
| Address | ✅ 100% | Street address |
| APN | ✅ 96.5% | Assessor parcel number |
| Total Units | ✅ 100% | Net new units |
| Unit Category | ✅ Derived | SFD, 2-4, 5+, ADU |
| Tenure | ⚠️ Partial | Owner vs renter |
| Income Categories | ⚠️ Partial | VLI, LI, Mod, Above Mod |
| Key Dates | ⚠️ In Progress | Entitlement, BP, CO |

### What's Hard to Automate

The notebook also explains why full APR automation is challenging:
- Income categories aren't tracked at permit issuance
- Date fields are inconsistent across systems
- The Excel template isn't machine-friendly

## For Students

This is a great example of **real-world data challenges**:
- Data comes from multiple sources
- Standards aren't always followed
- Translation between systems is messy

By understanding these challenges, you learn skills that apply beyond housing data.

## Resources

- [HCD APR Instructions](https://www.hcd.ca.gov/community-development/annual-progress-reports.shtml)
- [Berkeley's Past APRs](https://www.cityofberkeley.info/housing/)
- [D4 Notebook](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/04_reporting/D4_hcd_apr_tables.ipynb)
