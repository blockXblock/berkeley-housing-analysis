#!/usr/bin/env python3
"""
Compare Berkeley's staffing, pay, overtime and pension costs with the other
13 Alameda County cities.

SOURCE: California State Controller, Government Compensation in California (GCC),
2024 City raw export -- https://gcc.sco.ca.gov/reports/rawexport.aspx
The site is behind a WAF that refuses curl and scripted navigation; the ZIP must be
downloaded manually in a browser. It is ~96MB unzipped and does NOT belong in the
repo -- pass its path as argv[1].

    python -m scripts.compensation.compare_alameda_cities /path/to/2024_City.csv

THREE TRAPS THIS SCRIPT EXISTS TO AVOID
---------------------------------------
Each of these produced a badly wrong answer on the first pass.

1. `IncludesUnfundedLiability` IS NOT RELIABLE. Berkeley reports False, but its
   safety plans show pension contributions of 103-128% of regular pay -- impossible
   as normal cost -- and at an identical formula (2.7%@55) Berkeley shows 31.6%
   against Pleasanton's 14.3% under the same flag. Berkeley's per-employee median
   (38% of regular pay) sits with Oakland's (46%, flag True), not with Hayward's or
   Fremont's (8%, flag False). Berkeley's figures plainly INCLUDE unfunded liability.
   Taking the flag at face value makes Berkeley look like a 3.3x outlier against its
   nominal peer group; correctly grouped it is mid-pack. This script therefore
   assigns the reporting convention EMPIRICALLY (see infer_ual_convention) and
   reports the flag alongside it.

2. POSITION STRINGS ARE NOT COMPARABLE RAW. Berkeley prefixes every position with a
   job-class code and suffixes a shift schedule -- "8019 Police Officer",
   "8113 Firefighter 56". Matching on the raw string silently drops Berkeley from
   every cross-city job comparison, which reads as "no data" rather than an error.

3. HEADCOUNT PER CAPITA IS A SERVICE-MIX ARTIFACT. 21% of Berkeley's full-time staff
   sit in Health, Housing & Community Services (187), Berkeley Public Library (78)
   and the Rent Board (21) -- functions most Alameda cities do not run at all (county
   health, county library district, no rent board). Comparing raw staff-per-1,000
   measures what a city DOES, not how efficiently it does it.

FT PROXY: GCC rows are one per position held during the year, including part-year and
part-time. RegularPay >= $60,000 approximates full-time. It is a proxy, not an FTE count.

SCOPE: compensation only. This says nothing about total budget, capital spending, or
whether operating costs crowd out infrastructure -- that needs budget data, not GCC.
"""

import collections
import csv
import json
import os
import re
import statistics
import sys

COUNTY = "Alameda"
FT_THRESHOLD = 60000
OUT = "data/derived/alameda_city_compensation_2024.json"

JOB_CLASSES = {
    "police_officer": r"^police officer$",
    "police_sergeant": r"^police sergeant$",
    "firefighter": r"^fire ?fighter$",
}
# Berkeley departments most Alameda cities do not operate
BERKELEY_ONLY_DEPTS = {"HHCS", "BPL", "RB"}


def num(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "NA") else 0.0
    except ValueError:
        return 0.0


def norm_position(p):
    """Strip Berkeley's job-class prefix and shift suffix so classes match across cities."""
    p = re.sub(r"^\s*\d{3,5}\s+", "", p.strip())
    p = re.sub(r"\s+\d+(\.\d+)?\s*$", "", p)
    return re.sub(r"\s+", " ", p).strip().lower()


def dept_prefix(r):
    return r["DepartmentOrSubdivision"].split("-")[0].split(" ")[0].upper()


def infer_ual_convention(city_rows):
    """Decide EMPIRICALLY whether reported pension contributions include unfunded
    liability, rather than trusting IncludesUnfundedLiability.

    Employer NORMAL COST for CalPERS plans tops out well under ~35% of pay even for
    rich safety formulas. A city whose median full-time employee shows a defined-benefit
    contribution above that is reporting UAL as well."""
    ft = [r for r in city_rows if num(r, "RegularPay") >= 100000]
    if not ft:
        return None, None
    ratios = [num(r, "DefinedBenefitPlanContribution") / num(r, "RegularPay")
              for r in ft if num(r, "RegularPay") > 0]
    med = statistics.median(ratios) * 100
    return ("includes_ual" if med > 25 else "normal_cost_only"), med


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/2024_City.csv")
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8-sig", errors="replace"))
            if r["EmployerCounty"] == COUNTY]
    by = collections.defaultdict(list)
    for r in rows:
        by[r["EmployerName"]].append(r)
    print(f"{COUNTY} county city rows: {len(rows):,}   cities: {len(by)}")

    out = {}
    for c, rs in by.items():
        ft = [r for r in rs if num(r, "RegularPay") >= FT_THRESHOLD]
        pop = max((num(r, "EmployerPopulation") for r in rs), default=0)
        reg = sum(num(r, "RegularPay") for r in rs)
        conv, med_ratio = infer_ual_convention(rs)
        special = [r for r in ft if dept_prefix(r) in BERKELEY_ONLY_DEPTS] if c == "Berkeley" else []
        out[c] = {
            "population": pop, "rows": len(rs), "ft_proxy": len(ft),
            "ft_per_1000": round(len(ft) / pop * 1000, 2) if pop else None,
            "ft_per_1000_excl_special": (round((len(ft) - len(special)) / pop * 1000, 2)
                                         if special else None),
            "total_wages": round(sum(num(r, "TotalWages") for r in rs), 2),
            "wages_per_capita": round(sum(num(r, "TotalWages") for r in rs) / pop, 2) if pop else None,
            "median_ft_regular_pay": round(statistics.median(
                [num(r, "RegularPay") for r in ft]), 2) if ft else None,
            "overtime_pct_of_regular": round(
                sum(num(r, "OvertimePay") for r in rs) / reg * 100, 2) if reg else None,
            "db_pension_pct_of_regular": round(
                sum(num(r, "DefinedBenefitPlanContribution") for r in rs) / reg * 100, 2) if reg else None,
            "ual_flag_reported": rs[0]["IncludesUnfundedLiability"],
            "ual_convention_inferred": conv,
            "ual_inference_median_pct": round(med_ratio, 1) if med_ratio else None,
        }

    print("\nUAL REPORTING CONVENTION — reported flag vs empirical inference")
    print(f"  {'city':<14}{'flag':>7}{'inferred':>20}{'median DB % of pay':>20}")
    for c, v in sorted(out.items(), key=lambda x: -(x[1]["ual_inference_median_pct"] or 0)):
        mismatch = "  <-- FLAG DISAGREES" if (
            (v["ual_flag_reported"] == "True") != (v["ual_convention_inferred"] == "includes_ual")
        ) else ""
        print(f"  {c:<14}{v['ual_flag_reported']:>7}{v['ual_convention_inferred']:>20}"
              f"{v['ual_inference_median_pct']:>19}%{mismatch}")

    print("\nPENSION as % of regular pay — grouped by INFERRED convention")
    for conv in ("includes_ual", "normal_cost_only"):
        g = {c: v for c, v in out.items() if v["ual_convention_inferred"] == conv}
        vals = [v["db_pension_pct_of_regular"] for v in g.values()]
        print(f"  {conv}  (median {statistics.median(vals):.1f}%)")
        for c, v in sorted(g.items(), key=lambda x: -x[1]["db_pension_pct_of_regular"]):
            print(f"     {c:<14}{v['db_pension_pct_of_regular']:>7.1f}%"
                  + ("   <<< BERKELEY" if c == "Berkeley" else ""))

    print("\nMATCHED JOB CLASSES — base pay and overtime")
    classes = {}
    for lbl, pat in JOB_CLASSES.items():
        p = re.compile(pat)
        rec = {}
        for c, rs in by.items():
            m = [r for r in rs if num(r, "RegularPay") >= FT_THRESHOLD
                 and p.match(norm_position(r["Position"]))]
            if len(m) >= 8:
                base = statistics.median(num(r, "RegularPay") for r in m)
                ot = statistics.median(num(r, "OvertimePay") for r in m)
                rec[c] = {"n": len(m), "median_base": round(base, 2),
                          "median_overtime": round(ot, 2),
                          "ot_pct_of_base": round(ot / base * 100, 1)}
        classes[lbl] = rec
        print(f"\n  {lbl}")
        for c, v in sorted(rec.items(), key=lambda x: -x[1]["median_base"]):
            print(f"     {c:<14}n={v['n']:>4}  base ${v['median_base']:>9,.0f}"
                  f"  OT ${v['median_overtime']:>8,.0f}  OT/base {v['ot_pct_of_base']:>5.1f}%"
                  + ("   <<< BERKELEY" if c == "Berkeley" else ""))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"source": "CA State Controller GCC 2024 City raw export",
               "county": COUNTY, "ft_threshold": FT_THRESHOLD,
               "caveats": {
                   "ual_flag": "IncludesUnfundedLiability is unreliable; convention inferred empirically",
                   "ft_proxy": f"RegularPay >= ${FT_THRESHOLD:,} approximates full-time; not an FTE count",
                   "service_mix": "raw staff-per-capita reflects WHAT a city does; Berkeley runs "
                                  "health/library/rent-board functions most peers do not",
                   "scope": "compensation only -- says nothing about total budget or capital spending"},
               "cities": out, "job_classes": classes},
              open(OUT, "w"), indent=1)
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
