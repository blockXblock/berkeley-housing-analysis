"""
Decompose a Berkeley single-family property-tax bill into its BASES.

A Berkeley secured bill is not one tax. FY2025-26, validated on 37 single-family bills
(35/37 within $1 of the printed fixed-charge total once the two service fees are set aside;
scratch/2026-09-16/third_base_test.txt, parcel-level output kept out of the repo):

  base                 items                                   share of a median SFR bill
  assessed value       1% + six voter debt levies (1.2323%)    64%
  building sqft        11 City/BUSD parcel taxes                30%
  lot sqft             Clean Storm Water (continuous),          3%
                       EBMUD wet weather + 2018 storm water (tiered)
  per dwelling unit    CSA paramedic, vector, haz-waste          } 2%
  flat per parcel      AC Transit, Peralta, EBRPD, SFBRA, ...    }
  use category         mosquito / vector (~$11)
  SERVICE FEES         Zero Waste (garbage cart, $544-1,214 by cart size) + City street
                       lighting (~$16 by zone): on the bill, NOT taxes, NOT derivable.  3%

Rates: per-sqft / flat / per-unit come from the derived schedule JSON (derive_rate_schedule.py).
The lot-area tiers and use-category amounts were read off the same 37 bills 2026-09-16 and live
here until derive_rate_schedule.py learns lot area (queued). SINGLE-FAMILY ONLY: several
per-sqft taxes carry different non-residential rates and stormwater is by land-use class for
non-SFR parcels, so callers must gate on a residential use code.

Issuer tags answer "how much of my bill goes to the City of Berkeley itself" -- the
denominator a voter needs for "how much MORE am I giving this specific body".
"""
import json

SCHEDULE = "data/derived/berkeley_parcel_tax_rate_schedule_2025-26.json"

# ---- lot-area charges (FY2025-26; from the 37-bill sample, 2026-09-16) ----
CLEAN_STORM_WATER_PER_LOT_SQFT = 0.00911          # City; CV 0.000 across all 37 bills
EBMUD_WET_WEATHER_TIERS = [(5000, 159.90), (10000, 249.72), (None, 570.70)]   # lot < bound -> charge
STORM_WATER_2018_TIERS = [(10000, 60.74), (None, 73.44)]                      # City
CSA_LEAD_ABATEMENT = 10.00                        # County lead-poisoning CSA: residential built BEFORE 1978 (35/37 bills)
USE_CATEGORY = {"sfr": 11.20, "sfr_2nd_unit": 12.20}   # mosquito x2 + vector asmt; tiny

# ---- who levies what (for the "City of Berkeley levies" denominator) ----
CITY_PER_SQFT = {"CITY LANDSCP/PARK", "FIRE/WILDFIRE PREV", "PHYS DISABLED", "CITY LIBRARY SVC",
                 "FIRE/EMG SRVC TAX", "PARAMEDIC SUPPLMNT", "STREET REPAIR 2024", "LIBRARY RELIEF2024"}
CITY_FLAT = {"2018 STREET LIGHT"}
CITY_GO_BOND_RATE = 0.00049        # existing City of Berkeley GO debt levy, $49.00/$100k (TRA 13-0, 2025)
AD_VALOREM_RATE = 0.012323         # 1% + all six debt levies, every Berkeley TRA


def _tier(x, tiers):
    for bound, charge in tiers:
        if bound is None or x < bound:
            return charge
    return tiers[-1][1]


def load_schedule(path=SCHEDULE):
    return json.load(open(path))


def decompose(av, bld_sqft, lot_sqft, units, sched, second_unit=False, build_year=None):
    """Annual $ by base for one single-family parcel. Returns a dict; 'service_fees' is
    deliberately absent (not derivable). 'city_levies' and 'city_go' are the two City-only
    denominators; 'bill' is the whole bill EXCLUDING service fees."""
    units = max(int(units or 1), 1)
    psf = sched["per_sqft_of_improvements"]
    ad_valorem = av * AD_VALOREM_RATE
    bld = bld_sqft * sched["per_sqft_total"]
    lot = (lot_sqft * CLEAN_STORM_WATER_PER_LOT_SQFT + _tier(lot_sqft, EBMUD_WET_WEATHER_TIERS)
           + _tier(lot_sqft, STORM_WATER_2018_TIERS))
    per_unit = sched["per_dwelling_unit_total"] * units
    lead = CSA_LEAD_ABATEMENT if (build_year is None or build_year < 1978) else 0.0
    flat = sched["flat_total"] + lead
    usecat = USE_CATEGORY["sfr_2nd_unit" if second_unit else "sfr"]
    city = (av * CITY_GO_BOND_RATE
            + bld_sqft * sum(psf[k] for k in CITY_PER_SQFT if k in psf)
            + lot_sqft * CLEAN_STORM_WATER_PER_LOT_SQFT + _tier(lot_sqft, STORM_WATER_2018_TIERS)
            + sum(v for k, v in sched["flat_per_parcel"].items() if k in CITY_FLAT))
    return {"ad_valorem": ad_valorem, "building_sqft": bld, "lot_sqft": lot, "per_unit": per_unit,
            "flat": flat, "use_category": usecat,
            "bill": ad_valorem + bld + lot + per_unit + flat + usecat,
            "city_levies": city, "city_go": av * CITY_GO_BOND_RATE}


if __name__ == "__main__":   # smoke: the reference parcel in the methodology doc
    s = load_schedule()
    d = decompose(700178, 1850, 4500, 1, s)
    print({k: round(v) for k, v in d.items()})
