#!/usr/bin/env python3
"""
List every publicly owned parcel in Berkeley -- City, UC, BUSD, BART, EBMUD, BHA,
County, State, federal -- with zoning, lot area and building area, as the base
table for "could housing go here" and utility-use analysis.

Inputs (databases/berkeley.db)
  addresses_arcgis   OwnerName per address (County address layer; owner names are
                     the ONLY ownership signal we hold -- the parcels layer has none)
  parcels            UseCode, Imps, situs, lat/lon
  taxable_sqft       City lot sqft + taxable building sqft
  parcel_zones       zone_class (12-digit apn_norm key)

Ownership here is FEE ownership as recorded by the County. Missing by construction:
leased land, joint-powers parcels, and street rights-of-way (streets are not
parcels). Public owners all carry assessor use code 0300 (exempt), so use code
says nothing about what is on the lot -- a park, a fire station and a parking lot
look identical. Building sqft > 0 and Imps > 0 are the "something stands here"
signals; "buildable" still needs a facility/park flag we do not have.

Output: data/derived/berkeley_public_owned_parcels.csv  (public agencies -- no
household data, publishable)

Usage:  python -m scripts.tax_incidence.city_owned_parcels
"""

import csv
import os
import re
import sqlite3
from collections import Counter, defaultdict

DB = "databases/berkeley.db"
OUT = "data/derived/berkeley_public_owned_parcels.csv"

# first match wins; patterns run against the upper-cased owner name
OWNER_CLASSES = [
    ("berkeley_housing_authority", r"HOUSING AUTH.*BERKELEY|BERKELEY HOUSING AUTH"),
    ("city_of_berkeley", r"CITY OF BERKELEY|^CITY BERKELEY|BERKELEY CITY OF|REDEVELOPMENT AGENCY.*BERKELEY"),
    ("busd", r"BERKELEY UNIFIED|UNIFIED SCHOOL.*BERKELEY"),
    ("uc_regents", r"REGENTS OF THE UNIV"),
    ("bart", r"RAPID TRANSIT"),
    ("ebmud", r"EAST BAY MUNICIPAL|EBMUD"),
    ("ebrpd", r"EAST BAY REGIONAL PARK"),
    ("peralta_ccd", r"PERALTA COMMUNITY COLLEGE"),
    ("alameda_county", r"^(COUNTY OF ALAMEDA|ALAMEDA COUNTY)"),
    ("state_of_california", r"^STATE OF CALIF|CALTRANS|DEPT OF TRANSPORTATION"),
    ("federal", r"^(UNITED STATES|U ?S ?A?\b|USA\b|US POSTAL)"),
]


def classify(name):
    u = name.upper()
    for cls, pat in OWNER_CLASSES:
        if re.search(pat, u):
            return cls
    return None


def canon():
    from scripts import housing_rules
    return housing_rules.to_canonical_apn


def main():
    to_apn = canon()
    con = sqlite3.connect(DB)

    # owner name per canonical APN; the address layer has several rows per parcel
    owner = {}
    for apn, name in con.execute("SELECT DISTINCT APN, OwnerName FROM addresses_arcgis "
                                 "WHERE APN <> '' AND OwnerName IS NOT NULL AND OwnerName <> ''"):
        cls = classify(name)
        if cls:
            try:
                owner[to_apn(apn, "alameda")] = (cls, name.strip())
            except Exception:
                pass

    zone = dict(con.execute("SELECT apn_norm, zone_class FROM parcel_zones"))

    rows, seen = [], set()
    sql = """SELECT p.APN, p.UseCode, p.SitusAddre, p.Imps, p.Latitude, p.Longitude,
                    t.lotsqft, t.bldsqfttaxable
             FROM parcels p LEFT JOIN taxable_sqft t ON t.county_apn = p.APN"""
    for apn, uc, addr, imps, lat, lon, lot, bld in con.execute(sql):
        c = to_apn(apn, "alameda")
        if c not in owner or apn in seen:
            continue
        seen.add(apn)
        cls, name = owner[c]
        rows.append(dict(owner_class=cls, owner_name=name, apn=apn, apn_normalized=c,
                         situs=(addr or "").strip(), usecode=uc,
                         zone_class=zone.get(c.replace("-", "")),
                         lot_sqft=lot, lot_acres=round((lot or 0) / 43560, 3),
                         bldg_sqft_taxable=bld, imps=imps,
                         has_building=bool((bld or 0) > 0 or (imps or 0) > 0),
                         lat=lat, lon=lon))
    con.close()

    rows.sort(key=lambda r: (r["owner_class"], -(r["lot_sqft"] or 0)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    by = defaultdict(lambda: dict(n=0, acres=0.0, bldg=0.0, built=0))
    for r in rows:
        b = by[r["owner_class"]]
        b["n"] += 1
        b["acres"] += r["lot_acres"]
        b["bldg"] += r["bldg_sqft_taxable"] or 0
        b["built"] += r["has_building"]
    print(f"{'owner_class':28}{'parcels':>8}{'lot_acres':>11}{'bldg_sqft':>12}{'w/ building':>12}")
    for k, b in sorted(by.items(), key=lambda kv: -kv[1]["n"]):
        print(f"{k:28}{b['n']:8}{b['acres']:11.1f}{b['bldg']:12,.0f}{b['built']:12}")
    zc = Counter(r["zone_class"] for r in rows if r["owner_class"] == "city_of_berkeley")
    print("\nCity of Berkeley parcels by zoning:", zc.most_common(10))
    print(f"\nwrote {len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
