#!/usr/bin/env python3
"""
Model the full Berkeley property tax stack across every single-family parcel.

Inputs
  data/derived/berkeley_parcel_tax_rate_schedule_2025-26.json  (derive_rate_schedule.py)
  City of Berkeley Taxable Square Footage  (data.cityofberkeley.info 9a47-nj4i)
  databases/berkeley.db parcels            (Alameda assessor, net assessed value)

Why this works without sampling more bills: the City publishes taxable square
footage for all ~29k parcels, and the derived schedule converts square footage
into dollars. So the flat layer -- which appears in no dataset -- becomes
computable citywide from two published sources plus a schedule validated
against 37 real bills.

WHAT THIS IS FOR
The point of the exercise is the DISPERSION comparison. Assessed value spans
~15x across Berkeley single-family homes because of Prop 13 vintage. The
per-square-foot parcel taxes span far less, because they track building size
rather than purchase date. So the two layers distribute burden very differently,
and a measure levied purely ad valorem (Measure U) lands entirely on the
dispersed one. Everything here exists to quantify that.

LOWER BOUND: ~12 charges sit on some third base (EBMUD wet weather, storm water,
vector/mosquito, CSA paramedic) and are NOT modelled. See not_modelled in the
schedule -- median ~$1,225/parcel. Every total here understates by about that.

Usage:  python -m scripts.tax_incidence.model_citywide
"""

import csv
import json
import os
import sqlite3
import statistics
import subprocess
import sys

SCHEDULE = "data/derived/berkeley_parcel_tax_rate_schedule_2025-26.json"
DB = "databases/berkeley.db"
OUT_SUMMARY = "data/derived/berkeley_sfr_tax_by_decile_2025-26.csv"
CITY_SQFT_API = "https://data.cityofberkeley.info/resource/9a47-nj4i.json?$limit=50000"
SFR_USECODE_PREFIX = "1"

# Measure U (Nov 2026, $300M GO) rates per $100k AV, for incidence comparison
MEASURE_U = {"advertised_40yr_avg": 22.14, "stated_peak_2040_41": 35.00}


def canon():
    sys.path.insert(0, "scripts")
    import housing_rules
    return housing_rules.to_canonical_apn


def main():
    sched = json.load(open(SCHEDULE))
    per_sqft = sched["per_sqft_total"]
    # single-family parcels are one dwelling unit, so the per-unit charges apply once.
    # For multi-unit parcels this term scales with unit count.
    flat = sched["flat_total"] + sched.get("per_dwelling_unit_total", 0)
    av_rate = sched["ad_valorem_rate_all_berkeley_TRAs"]
    to_apn = canon()

    raw = subprocess.run(["curl", "-s", "--max-time", "120", CITY_SQFT_API],
                         capture_output=True, text=True).stdout
    city = {}
    for r in json.loads(raw):
        k = to_apn(r["apn"], "alameda")
        if k:
            city[k] = float(r["bldsqfttaxable"] or 0)
    print(f"city taxable-sqft rows: {len(city):,}")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT APN, TotalNetValue FROM parcels "
                       "WHERE UseCode LIKE ? AND TotalNetValue > 0 AND Imps > 0",
                       (SFR_USECODE_PREFIX + "%",)).fetchall()
    con.close()

    p = []
    for r in rows:
        s = city.get(to_apn(r["APN"], "alameda"))
        if not s or s <= 0:
            continue
        av = r["TotalNetValue"]
        adval = av * av_rate
        parcel_tax = s * per_sqft + flat
        p.append({"av": av, "sqft": s, "adval": adval, "flat": parcel_tax,
                  "total": adval + parcel_tax})
    p.sort(key=lambda x: x["av"])
    n = len(p)
    print(f"modelled {n:,} of {len(rows):,} single-family parcels ({n/len(rows)*100:.1f}% joined)")
    print(f"LOWER BOUND: excludes ~${sched['not_modelled']['median_residual_per_parcel']:,.0f}/parcel\n")

    med = lambda g, k: statistics.median(x[k] for x in g)                      # noqa: E731
    q = lambda k, f: sorted(x[k] for x in p)[int(n * f)]                       # noqa: E731

    hdr = ["decile", "median_av", "median_sqft", "ad_valorem", "parcel_taxes",
           "total", "flat_share_pct", "pct_of_av"] + [f"measure_u_{k}" for k in MEASURE_U]
    out = []
    print(f"{'decile':<8}{'median AV':>12}{'sqft':>7}{'ad val':>9}{'parcel tax':>12}"
          f"{'TOTAL':>10}{'flat%':>7}{'%of AV':>8}")
    for d in range(10):
        g = p[n * d // 10:n * (d + 1) // 10]
        row = [d + 1, round(med(g, "av")), round(med(g, "sqft")), round(med(g, "adval"), 2),
               round(med(g, "flat"), 2), round(med(g, "total"), 2),
               round(med(g, "flat") / med(g, "total") * 100, 1),
               round(med(g, "total") / med(g, "av") * 100, 3)]
        row += [round(med(g, "av") / 1e5 * r, 2) for r in MEASURE_U.values()]
        out.append(row)
        print(f"{d+1:<8}{row[1]:>12,}{row[2]:>7,}{row[3]:>9,.0f}{row[4]:>12,.0f}"
              f"{row[5]:>10,.0f}{row[6]:>6.0f}%{row[7]:>7.2f}%")

    print(f"\nDISPERSION p90/p10 -- the finding:")
    disp = {}
    for k, lbl in [("av", "assessed value"), ("adval", "ad-valorem tax"),
                   ("flat", "parcel taxes"), ("total", "TOTAL tax")]:
        disp[k] = q(k, 0.90) / q(k, 0.10)
        print(f"   {lbl:<16}{disp[k]:>6.1f}x")
    print("   -> the flat layer COMPRESSES; Measure U is levied entirely on the dispersed one.")

    os.makedirs(os.path.dirname(OUT_SUMMARY), exist_ok=True)
    with open(OUT_SUMMARY, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(hdr)
        w.writerows(out)
    print(f"\n-> {OUT_SUMMARY}")
    return {"n": n, "dispersion": disp,
            "aggregate_adval": sum(x["adval"] for x in p),
            "aggregate_flat": sum(x["flat"] for x in p)}


if __name__ == "__main__":
    main()
