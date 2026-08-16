#!/usr/bin/env python3
"""
Parse Alameda County secured property-tax bill PDFs (the portal's "Internet Copy"
print) into structured records.

parse(path) -> dict with:
    apn, tax_year, tracer, tra
    av_lines{agency: {rate, amount}}, av_rate_total, av_tax_total
    fixed{line_item: amount}, fixed_total
    land, improvements, gross_av, homeowners_exemption, net_av
    base_tax_total, amount_billed, late_penalty

APN and tax year are read from the PDF BODY, never the filename.

Requires `pdftotext` (poppler). Install: brew install poppler

PRIVACY: bill PDFs are a specific household's assessed value, payment dates and
delinquency history. They are public record, but this repo publishes to
berkeleybuild.com -- keep the PDFs OUTSIDE the repo (default ~/Desktop/Alameda).
Only de-identified, derived structure belongs in version control.

Run standalone for a single parcel's multi-year series:
    python -m scripts.tax_incidence.parse_bills <dir-of-pdfs> <out-dir>
"""

import csv
import glob
import os
import re
import subprocess
import sys

SRC = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/Desktop/Alameda")
OUT = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/Desktop/Alameda/frame")

MONEY = r"-?\$?\(?-?([\d,]+\.\d{2})\)?"   # bills write negatives as "-$7,000.00"


def money(s):
    if s is None:
        return None
    neg = "-" in s or "(" in s
    v = float(re.sub(r"[^\d.]", "", s))
    return -v if neg else v


def text_of(path):
    return subprocess.run(["pdftotext", "-layout", path, "-"],
                          capture_output=True, text=True).stdout


def parse(path):
    t = text_of(path)
    if "Secured Property Tax Statement" not in t:
        return None
    b = {"file": os.path.basename(path)}

    m = re.search(r"Tax Year:\s*(\d{4}-\d{4})", t)
    if not m:
        return None
    b["tax_year"] = m.group(1)
    b["apn"] = (re.search(r"Parcel Number:\s*([0-9A-Z-]+)", t) or [None, None])[1]
    b["tracer"] = (re.search(r"Tracer Number:\s*(\d+)", t) or [None, None])[1]
    b["tra"] = (re.search(r"Tax-Rate Area:\s*([\d-]+)", t) or [None, None])[1]

    # ---- ad-valorem rate breakdown -------------------------------------------
    av_section = t.split("Tax-Rate Breakdown")[1].split("Fixed Charges")[0]
    b["av_lines"] = {}
    for name, rate, amt in re.findall(
            rf"^\s*([A-Z][A-Z0-9 /&.'()-]+?)\s+(\d+\.\d+)%\s+{MONEY}\s*$",
            av_section, re.M):
        name = name.strip()
        if name.startswith("TOTAL AD VALOREM"):
            b["av_rate_total"], b["av_tax_total"] = float(rate), money(amt)
        else:
            b["av_lines"][name] = {"rate": float(rate), "amount": money(amt)}

    # ---- fixed charges --------------------------------------------------------
    fx_section = t.split("Fixed Charges and/or Special Assessments")[1]
    fx_section = fx_section.split("Tax Computation Worksheet")[0]
    b["fixed"] = {}
    for name, amt in re.findall(
            # name may START with a digit ("2018 STORM WATER") but must contain a letter;
            # some district lines carry a leading "*" footnote marker
            rf"^\s*\*?\s*((?=[A-Z0-9 ]*[A-Z])[A-Z0-9][A-Z0-9 /&.'()-]+?)"
            rf"\s+(?:[abc]\s+)?[\d()-]{{7,}}\s+{MONEY}\s*$",
            fx_section, re.M):
        b["fixed"][name.strip()] = money(amt)
    m = re.search(rf"Total Fixed Charges and/or Special Assessments\s+{MONEY}", t)
    b["fixed_total"] = money(m.group(1)) if m else None

    # ---- valuation worksheet --------------------------------------------------
    for key, pat in [
        ("land", rf"^\s*LAND\s+{MONEY}"),
        ("improvements", rf"^\s*IMPROVEMENTS\s+{MONEY}"),
        ("total_real_property", rf"^\s*TOTAL REAL PROPERTY\s+{MONEY}"),
        ("gross_av", rf"^\s*GROSS ASSESSMENT & TAX\s+{MONEY}"),
        ("homeowners_exemption", rf"^\s*HOMEOWNERS EXEMPTION\s+{MONEY}"),
        ("net_av", rf"^\s*TOTAL AD VALOREM TAX\s+{MONEY}\s+\d+\.\d+%"),
    ]:
        m = re.search(pat, t, re.M)
        b[key] = money(m.group(1)) if m else None
    if b.get("homeowners_exemption") and b["homeowners_exemption"] > 0:
        b["homeowners_exemption"] = -b["homeowners_exemption"]

    m = re.search(rf"Ad Valorem Tax plus Special Assessments\s+{MONEY}", t)
    b["base_tax_total"] = money(m.group(1)) if m else None
    m = re.search(rf"Total Amount Billed.*?\n(?:.*?\n)*?\s*{MONEY}\s*$",
                  t.split("Tax-Rate Breakdown")[0], re.M)
    amts = re.findall(MONEY, t.split("Tax-Rate Breakdown")[0])
    b["amount_billed"] = max((money(a) for a in amts), default=None)
    b["late_penalty"] = (round(b["amount_billed"] - b["base_tax_total"], 2)
                         if b["amount_billed"] and b["base_tax_total"] else None)
    return b


def main():
    bills = [x for x in (parse(p) for p in sorted(glob.glob(os.path.join(SRC, "*.pdf")))) if x]
    bills.sort(key=lambda x: x["tax_year"])
    os.makedirs(OUT, exist_ok=True)

    # ---- long form -------------------------------------------------------------
    with open(os.path.join(OUT, "bill_series_long.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tax_year", "layer", "line_item", "rate_pct", "amount"])
        for b in bills:
            for k, v in b["av_lines"].items():
                w.writerow([b["tax_year"], "ad_valorem", k, v["rate"], v["amount"]])
            for k, v in sorted(b["fixed"].items()):
                w.writerow([b["tax_year"], "fixed_charge", k, "", v])

    # ---- wide form -------------------------------------------------------------
    cols = ["tax_year", "tracer", "land", "improvements", "gross_av",
            "homeowners_exemption", "net_av", "av_rate_total", "av_tax_total",
            "fixed_total", "base_tax_total", "amount_billed", "late_penalty",
            "fixed_share_pct", "n_fixed_items"]
    with open(os.path.join(OUT, "bill_series_wide.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for b in bills:
            b["fixed_share_pct"] = (round(b["fixed_total"] / b["base_tax_total"] * 100, 1)
                                    if b["fixed_total"] and b["base_tax_total"] else None)
            b["n_fixed_items"] = len(b["fixed"])
            w.writerow(b)

    # ---- console summary --------------------------------------------------------
    print(f"parsed {len(bills)} bills: {bills[0]['tax_year']} .. {bills[-1]['tax_year']}\n")
    print(f"{'year':<10}{'net AV':>11}{'AV rate':>9}{'ad val':>10}{'fixed':>11}"
          f"{'TOTAL':>11}{'fixed%':>8}{'items':>6}")
    for b in bills:
        print(f"{b['tax_year']:<10}{b['net_av'] or 0:>11,.0f}{b['av_rate_total'] or 0:>8.4f}%"
              f"{b['av_tax_total'] or 0:>10,.0f}{b['fixed_total'] or 0:>11,.0f}"
              f"{b['base_tax_total'] or 0:>11,.0f}{b['fixed_share_pct'] or 0:>7.1f}%"
              f"{b['n_fixed_items']:>6}")

    f, l = bills[0], bills[-1]
    n = len(bills) - 1
    def cagr(a, z):
        return ((z / a) ** (1 / n) - 1) * 100 if a and z else 0
    print(f"\n{n}-year change  ({f['tax_year']} -> {l['tax_year']}):")
    for lbl, k in [("net AV", "net_av"), ("ad-valorem tax", "av_tax_total"),
                   ("FIXED charges", "fixed_total"), ("TOTAL tax", "base_tax_total")]:
        print(f"   {lbl:<16} ${f[k]:>10,.0f} -> ${l[k]:>10,.0f}   "
              f"{(l[k]/f[k]-1)*100:>+7.1f}%   CAGR {cagr(f[k], l[k]):>5.2f}%/yr")

    # ---- city GO bond rate history ---------------------------------------------
    print("\nCITY OF BERKELEY GO bond rate (the levy Measure U adds to):")
    for b in bills:
        v = b["av_lines"].get("CITY OF BERKELEY")
        if v:
            print(f"   {b['tax_year']}  {v['rate']:.4f}%  = ${v['rate']*1000:>6,.2f} per $100k"
                  f"   ${v['amount']:>8,.2f} on this parcel")

    # ---- fixed-charge line items: first/last appearance --------------------------
    seen = {}
    for b in bills:
        for k in b["fixed"]:
            seen.setdefault(k, []).append(b["tax_year"])
    print(f"\n{len(seen)} distinct fixed-charge line items across the 12 years")
    new = [(k, v[0]) for k, v in seen.items() if v[0] != bills[0]["tax_year"]]
    print(f"   {len(new)} first appear after {bills[0]['tax_year']}:")
    for k, y in sorted(new, key=lambda x: x[1]):
        amt = next((b["fixed"][k] for b in reversed(bills) if k in b["fixed"]), 0)
        print(f"     {y}  {k:<22} latest ${amt:>9,.2f}")
    gone = [(k, v[-1]) for k, v in seen.items() if v[-1] != bills[-1]["tax_year"]]
    if gone:
        print(f"   {len(gone)} discontinued:")
        for k, y in sorted(gone, key=lambda x: x[1]):
            print(f"     last seen {y}  {k}")

    print(f"\n-> {OUT}/bill_series_wide.csv")
    print(f"-> {OUT}/bill_series_long.csv")


if __name__ == "__main__":
    main()
