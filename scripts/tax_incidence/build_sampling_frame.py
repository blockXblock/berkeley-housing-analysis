#!/usr/bin/env python3
"""
Build a stratified sampling frame of Berkeley single-family parcels for manual
property-tax-bill lookup (Alameda County property tax portal).

WHY THIS DESIGN
---------------
Goal: measure absolute dollars paid in property tax by different kinds of Berkeley
residents, to ground the Measure U ($300M GO bond, Nov 2026) incidence analysis.

The bill has two layers:
  (a) AD VALOREM  -- 1.2323% of net AV. Already known for all 27,618 parcels
                     from berkeley.db, so it needs no sampling.
  (b) FIXED CHARGES / parcel taxes -- $12,081 on the reference bill (57% of total).
                     Set by ordinance, mostly per square foot of IMPROVEMENTS or
                     flat per parcel. NOT in any dataset. This is what we sample for.

Stratification variable = ASSESSED VALUE, held against a fixed LOT-SIZE band.
  Under Prop 13 the factored base year value grows <=2%/yr, so
      AV ~= purchase price x 1.02^(years since last reassessment).
  AV therefore *is* the Prop 13 clock -- a direct read on time-since-reassessment,
  which is the variable that drives the tax difference we want to show.

  We deliberately DO NOT stratify on parcels.LatestDocumentDate. That field is
  last-recorded-DOCUMENT recency, not ownership date; refinances and liens reset it
  with no change of owner. (Retracted as a tenure proxy 2026-08-14; ownership map
  relabelled in commit 586c3ae.) See the contamination check printed below: if it
  were purchase date, mean AV would rise monotonically with document year. It does not.

  LotSize is held roughly constant because it is the one size-related field that is
  independent of Prop 13 vintage. berkeley.db has NO building square footage --
  which is the second reason to sample: each bill INVERTS to give building sqft,
  since the per-sqft parcel taxes (BSEP, library, parks, fire) are charge = rate x sqft.
  Sampled bills therefore calibrate the rate schedule AND recover building size,
  after which the fixed-charge layer can be modelled across all 27,618 parcels
  without further lookups.

OUTPUT (kept OUT of the git repo -- third-party addresses; public record, but the
repo publishes to berkeleybuild.com):
    ~/Desktop/Alameda/frame/sampling_frame.csv     -- parcels to look up
    ~/Desktop/Alameda/frame/matched_pairs.csv      -- same-block like-for-like pairs
"""

import csv
import os
import sqlite3

DB = "/Users/johngage/berkeley-data/databases/berkeley.db"
OUT = os.path.expanduser("~/Desktop/Alameda/frame")

# FY2025-26 Berkeley ad-valorem rate, from the county TRA table (TRA 13-000, all
# six Berkeley TRAs identical) and confirmed against the reference bill.
AV_RATE = 0.012323
MEASURE_U = {"advertised_avg_22_14": 22.14, "stated_peak_35": 35.00, "todays_base_67_30": 67.30}

SFR = ("1100", "1150")           # single-family; 1100 n=15,820, 1150 n=43 (reference parcel)
BANDS = [                        # (label, lot_min, lot_max) -- lot sqft
    ("modal_4500_6500", 4500, 6500),
    ("large_10000_18000", 10000, 18000),   # band containing the reference parcel (13,700)
]
STRATA = [(0, 10), (10, 25), (25, 50), (50, 75), (75, 90), (90, 100)]
PER_STRATUM = 3
REFERENCE_APN = "53-1695-26"


def lot_int(s):
    if not s:
        return None
    try:
        return int(str(s).replace(",", "").strip())
    except ValueError:
        return None


def pct(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        f"""SELECT APN, SitusAddre, UseCode, Land, Imps, TotalNetValue, LotSize,
                   Latitude, Longitude, LatestDocumentDate
            FROM parcels
            WHERE UseCode IN ({','.join('?' * len(SFR))})
              AND TotalNetValue > 0 AND Imps > 0
              AND Latitude IS NOT NULL AND Longitude IS NOT NULL""",
        SFR,
    ).fetchall()

    parcels = []
    for r in rows:
        lot = lot_int(r["LotSize"])
        if not lot:
            continue
        try:                       # Latitude/Longitude are TEXT in this table
            lat, lon = float(r["Latitude"]), float(r["Longitude"])
        except (TypeError, ValueError):
            continue
        d = dict(r)
        d["lot_sqft"] = lot
        d["Latitude"], d["Longitude"] = lat, lon
        d["av_per_lot_sqft"] = r["TotalNetValue"] / lot
        parcels.append(d)

    print(f"SFR universe (UseCode {'/'.join(SFR)}, Imps>0, lot parsed): {len(parcels):,}\n")

    # ---- contamination check: is LatestDocumentDate a purchase-date proxy? --------
    print("LatestDocumentDate contamination check")
    print("  If it were purchase date, mean AV would rise monotonically with year")
    print("  (most recent purchase = most recently reassessed = highest AV).\n")
    byyr = {}
    for p in parcels:
        y = (p["LatestDocumentDate"] or "")[:4]
        if y.isdigit() and int(y) >= 2014:
            byyr.setdefault(y, []).append(p["TotalNetValue"])
    prev, inversions = None, 0
    for y in sorted(byyr, reverse=True):
        vals = byyr[y]
        m = sum(vals) / len(vals)
        flag = ""
        if prev is not None and m > prev:
            flag = "  <-- INVERSION (older docs assessed HIGHER)"
            inversions += 1
        print(f"   {y}  n={len(vals):>5,}  mean AV ${m:>10,.0f}{flag}")
        prev = m
    print(f"\n  {inversions} inversions across {len(byyr)} years -> field is NOT purchase date.")
    print("  Stratifying on AV instead.\n")

    # ---- stratified frame --------------------------------------------------------
    frame = []
    for label, lo, hi in BANDS:
        band = [p for p in parcels if lo <= p["lot_sqft"] <= hi]
        if not band:
            continue
        avs = sorted(p["TotalNetValue"] for p in band)
        print(f"Band {label}: n={len(band):,}  AV p10 ${pct(avs,10):,.0f}  "
              f"median ${pct(avs,50):,.0f}  p90 ${pct(avs,90):,.0f}  "
              f"spread {pct(avs,90)/pct(avs,10):.1f}x")

        for p_lo, p_hi in STRATA:
            v_lo, v_hi = pct(avs, p_lo), pct(avs, p_hi)
            bucket = sorted((p for p in band if v_lo <= p["TotalNetValue"] <= v_hi),
                            key=lambda x: x["TotalNetValue"])
            if not bucket:
                continue
            # deterministic, representative picks: evenly spaced within the stratum
            picks = [bucket[int((len(bucket) - 1) * f)] for f in (0.25, 0.50, 0.75)][:PER_STRATUM]
            for p in picks:
                frame.append({**p, "band": label, "stratum": f"p{p_lo}-{p_hi}"})

    # always include the reference parcel (12 years of bills already identified)
    ref = next((p for p in parcels if p["APN"] == REFERENCE_APN), None)
    if ref:
        frame.append({**ref, "band": "reference", "stratum": "anchor"})

    # dedupe, preserving order
    seen, uniq = set(), []
    for p in frame:
        if p["APN"] not in seen:
            seen.add(p["APN"])
            uniq.append(p)

    os.makedirs(OUT, exist_ok=True)
    cols = ["band", "stratum", "APN", "SitusAddre", "UseCode", "lot_sqft",
            "Land", "Imps", "TotalNetValue", "av_per_lot_sqft",
            "est_ad_valorem_fy26"] + [f"measure_u_{k}" for k in MEASURE_U] + [
            "LatestDocumentDate", "Latitude", "Longitude",
            "BILL_fixed_charges_TO_FILL", "BILL_total_TO_FILL", "BILL_bldg_sqft_derived"]
    path = os.path.join(OUT, "sampling_frame.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for p in uniq:
            av = p["TotalNetValue"]
            row = {**p,
                   "av_per_lot_sqft": round(p["av_per_lot_sqft"], 1),
                   "est_ad_valorem_fy26": round(av * AV_RATE, 2)}
            for k, rate in MEASURE_U.items():
                row[f"measure_u_{k}"] = round(av / 100000 * rate, 2)
            w.writerow(row)
    print(f"\n-> {path}  ({len(uniq)} parcels to look up)")

    # ---- matched same-block pairs -------------------------------------------------
    # ~0.003 deg latitude ~= 330m. Group parcels into cells; within a cell find the
    # widest AV spread among similar lot sizes. This is the like-for-like exhibit:
    # comparable houses, comparable block, very different tax.
    cells = {}
    for p in parcels:
        if not (3500 <= p["lot_sqft"] <= 8000):
            continue
        key = (round(p["Latitude"] / 0.003), round(p["Longitude"] / 0.004))
        cells.setdefault(key, []).append(p)

    pairs = []
    for key, members in cells.items():
        if len(members) < 4:
            continue
        members.sort(key=lambda x: x["TotalNetValue"])
        lo_p, hi_p = members[0], members[-1]
        # require genuinely similar lots so the comparison is like-for-like
        if abs(lo_p["lot_sqft"] - hi_p["lot_sqft"]) > 800:
            continue
        ratio = hi_p["TotalNetValue"] / lo_p["TotalNetValue"]
        if ratio >= 4.0:
            pairs.append((ratio, lo_p, hi_p, len(members)))
    pairs.sort(key=lambda x: -x[0])

    ppath = os.path.join(OUT, "matched_pairs.csv")
    with open(ppath, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ratio", "n_in_cell",
                    "lowAV_APN", "lowAV_addr", "lowAV_lot", "lowAV_av", "lowAV_ad_valorem",
                    "highAV_APN", "highAV_addr", "highAV_lot", "highAV_av", "highAV_ad_valorem"])
        for ratio, a, b, n in pairs[:25]:
            w.writerow([round(ratio, 2), n,
                        a["APN"], a["SitusAddre"], a["lot_sqft"], round(a["TotalNetValue"]),
                        round(a["TotalNetValue"] * AV_RATE, 2),
                        b["APN"], b["SitusAddre"], b["lot_sqft"], round(b["TotalNetValue"]),
                        round(b["TotalNetValue"] * AV_RATE, 2)])
    print(f"-> {ppath}  ({min(len(pairs),25)} of {len(pairs)} qualifying pairs)")

    if pairs:
        ratio, a, b, n = pairs[0]
        print(f"\n   widest like-for-like pair ({ratio:.1f}x, same ~330m cell, lots "
              f"{a['lot_sqft']:,} vs {b['lot_sqft']:,} sqft):")
        print(f"     AV ${a['TotalNetValue']:>10,.0f} -> ad valorem ${a['TotalNetValue']*AV_RATE:>8,.2f}/yr")
        print(f"     AV ${b['TotalNetValue']:>10,.0f} -> ad valorem ${b['TotalNetValue']*AV_RATE:>8,.2f}/yr")
        print("   Both pay the SAME flat parcel-tax stack (~$12k on the reference bill),")
        print("   which is what the sampled bills will confirm.")

    con.close()


if __name__ == "__main__":
    main()
