#!/usr/bin/env python3
"""
Score every single-family parcel's Prop 13 position against its own block, and
aggregate to block level for the neighbor-vs-neighbor map.

Inputs (all in databases/berkeley.db)
  parcels          Alameda assessor: TotalNetValue (net AV), UseCode, lat/lon
  parcels_arcgis   HOEX (homeowner exemption -> owner-occupied signal)
  taxable_sqft     City taxable building sqft (the base of the per-sqft parcel taxes)
  data/derived/berkeley_parcel_tax_rate_schedule_2025-26.json  (derive_rate_schedule.py)

WHY NO PURCHASE DATE
There is none. LatestDocumentDate is last-recorded-document recency (refinances
and liens reset it) and was retracted as a tenure proxy 2026-08-14. Under Prop 13
assessed value IS the purchase clock, so the benefit is measured directly:

  market_ref   = p90 of AV/sqft among the parcel's block-mates (recent sales set it)
  discount     = 1 - (AV/sqft) / market_ref          0 = at market, 0.8 = assessed at 20%
  benefit_usd  = max(0, market_ref*sqft - AV) * ad_valorem_rate   (per year)

The block is the APN book-page (first two segments); a block with fewer than
MIN_BLOCK single-family parcels falls back to its book (ref_level = 'book').

PRIVACY (docs/methodology/berkeley_property_tax_structure.md)
Parcel-level rows carry a household's assessed value. They are written to
scratch/ (gitignored) by default; only the block aggregates (n >= MIN_BLOCK) go
to data/derived/ and are publishable.

Usage:  python -m scripts.tax_incidence.score_prop13 [--parcel-out PATH]
"""

import argparse
import csv
import json
import os
import sqlite3
import statistics
from collections import defaultdict
from datetime import date

DB = "databases/berkeley.db"
SCHEDULE = "data/derived/berkeley_parcel_tax_rate_schedule_2025-26.json"
BLOCK_OUT = "data/derived/berkeley_prop13_by_block_2025-26.csv"
PARCEL_OUT_DEFAULT = f"scratch/{date.today().isoformat()}/prop13_parcels_2025-26.csv"

# single-family lots: plain SFR + SFR with a second unit / ADU (County legend,
# scratch/2026-09-14/usecodes.tsv). 1150 is "Historical residential", NOT an ADU code.
SFR_CODES = {"1100": "sfr", "1200": "sfr_2nd_unit", "1201": "sfr_jadu",
             "2501": "sfr_adu_attached", "2502": "sfr_adu_detached",
             "2541": "sfr_adu_attached", "2542": "sfr_adu_detached"}
UNITS = {"sfr": 1, "sfr_2nd_unit": 2, "sfr_jadu": 2, "sfr_adu_attached": 2, "sfr_adu_detached": 2}
MIN_BLOCK = 8        # block-mates needed for a block-level market reference
MIN_SQFT = 400       # below this the sqft is a shed/error, not a house
MIN_AV = 20_000      # below this the AV is a placeholder, not an assessment
P_MARKET = 0.90      # percentile of block AV/sqft taken as the at-market level
BANDS = [(0.75, "under_25pct"), (0.50, "25_50pct"), (0.25, "50_75pct"), (-9, "near_market")]


def block_key(apn):
    return "-".join(apn.split("-")[:2])


def book_key(apn):
    return apn.split("-")[0]


def pct(vals, p):
    s = sorted(vals)
    return s[min(len(s) - 1, int(len(s) * p))]


def band(d):
    for lo, name in BANDS:
        if d > lo:
            return name


def load(con):
    sql = """SELECT p.APN, p.UseCode, p.TotalNetValue, p.Latitude, p.Longitude,
                    a.HOEX, t.bldsqfttaxable, t.lotsqft
             FROM parcels p
             LEFT JOIN parcels_arcgis a ON a.APN = p.APN
             LEFT JOIN taxable_sqft t ON t.county_apn = p.APN
             WHERE p.UseCode IN (%s)""" % ",".join("?" * len(SFR_CODES))
    out, seen = [], set()
    for apn, uc, av, lat, lon, hoex, sqft, lot in con.execute(sql, list(SFR_CODES)):
        if apn in seen:            # parcels carries 12 duplicate-APN rows
            continue
        seen.add(apn)
        try:
            hoex = float(hoex or 0)
        except ValueError:
            hoex = 0.0
        out.append(dict(apn=apn, usecode=uc, cls=SFR_CODES[uc], av=av or 0.0,
                        lat=lat, lon=lon, hoex=hoex > 0, sqft=sqft or 0.0, lot=lot or 0.0,
                        block=block_key(apn), book=book_key(apn)))
    return out


def score(parcels, sched):
    av_rate = sched["ad_valorem_rate_all_berkeley_TRAs"]
    per_sqft = sched["per_sqft_total"]
    flat = sched["flat_total"]
    per_unit = sched.get("per_dwelling_unit_total", 0)

    usable = [p for p in parcels if p["sqft"] >= MIN_SQFT and p["av"] >= MIN_AV]
    by_block, by_book = defaultdict(list), defaultdict(list)
    for p in usable:
        p["av_sqft"] = p["av"] / p["sqft"]
        by_block[p["block"]].append(p["av_sqft"])
        by_book[p["book"]].append(p["av_sqft"])

    scored = []
    for p in usable:
        if len(by_block[p["block"]]) >= MIN_BLOCK:
            ref, level, n = pct(by_block[p["block"]], P_MARKET), "block", len(by_block[p["block"]])
        else:
            ref, level, n = pct(by_book[p["book"]], P_MARKET), "book", len(by_book[p["book"]])
        p["market_ref_av_sqft"] = ref
        p["ref_level"], p["ref_n"] = level, n
        p["discount"] = 1 - p["av_sqft"] / ref
        p["band"] = band(p["discount"])
        p["benefit_usd"] = max(0.0, ref * p["sqft"] - p["av"]) * av_rate
        p["county_av_tax"] = p["av"] * av_rate
        p["city_sqft_tax"] = per_sqft * p["sqft"] + flat + per_unit * UNITS[p["cls"]]
        scored.append(p)
    skipped = len(parcels) - len(scored)
    return scored, skipped


def block_aggregates(scored):
    groups = defaultdict(list)
    for p in scored:
        if p["ref_level"] == "block":
            groups[p["block"]].append(p)
    rows = []
    for b, ps in sorted(groups.items()):
        r = [p["av_sqft"] for p in ps]
        rows.append(dict(
            block=b, n_sfr=len(ps),
            lat=round(statistics.fmean(float(p["lat"]) for p in ps if p["lat"]), 6),
            lon=round(statistics.fmean(float(p["lon"]) for p in ps if p["lon"]), 6),
            market_ref_av_sqft=round(ps[0]["market_ref_av_sqft"]),
            median_av_sqft=round(statistics.median(r)),
            av_sqft_max_over_min=round(max(r) / min(r), 1),
            median_discount=round(statistics.median(p["discount"] for p in ps), 3),
            share_under_25pct=round(sum(p["band"] == "under_25pct" for p in ps) / len(ps), 3),
            share_near_market=round(sum(p["band"] == "near_market" for p in ps) / len(ps), 3),
            share_hoex=round(sum(p["hoex"] for p in ps) / len(ps), 3),
            benefit_usd_total=round(sum(p["benefit_usd"] for p in ps)),
            median_county_av_tax=round(statistics.median(p["county_av_tax"] for p in ps)),
            median_city_sqft_tax=round(statistics.median(p["city_sqft_tax"] for p in ps)),
            county_tax_max_over_min=round(max(p["county_av_tax"] for p in ps) / min(p["county_av_tax"] for p in ps), 1),
            city_tax_max_over_min=round(max(p["city_sqft_tax"] for p in ps) / min(p["city_sqft_tax"] for p in ps), 1),
        ))
    return rows


def summary(scored, skipped, blocks):
    blk = [p for p in scored if p["ref_level"] == "block"]
    d = [p["discount"] for p in blk]
    print(f"single-family parcels: {len(scored) + skipped:,}  scored: {len(scored):,}  "
          f"(skipped {skipped}: sqft<{MIN_SQFT} or AV<{MIN_AV})")
    print(f"block-referenced: {len(blk):,} on {len(blocks)} blocks (>= {MIN_BLOCK});  "
          f"book-referenced fallback: {len(scored) - len(blk):,}")
    print(f"median parcel assessed at {100 * (1 - statistics.median(d)):.0f}% of its block market level")
    for _, name in BANDS:
        n = sum(p["band"] == name for p in blk)
        print(f"  {name:14}{n:7,} ({100 * n / len(blk):.0f}%)")
    print(f"implied ad-valorem Prop 13 benefit: ${sum(p['benefit_usd'] for p in blk) / 1e6:.0f}M/yr  "
          f"(mean ${statistics.fmean(p['benefit_usd'] for p in blk):,.0f}/parcel)")
    ho = [p["discount"] for p in blk if p["hoex"]]
    nho = [p["discount"] for p in blk if not p["hoex"]]
    print(f"HOEX owner-occupied median discount {100 * statistics.median(ho):.0f}% (n={len(ho):,}); "
          f"non-HOEX {100 * statistics.median(nho):.0f}% (n={len(nho):,})")
    ratio = [b["av_sqft_max_over_min"] for b in blocks]
    print(f"within-block AV/sqft max/min: median {statistics.median(ratio):.1f}x, p90 {pct(ratio, .9):.0f}x")
    ct = [p["county_av_tax"] for p in blk]
    st = [p["city_sqft_tax"] for p in blk]
    print(f"county AV tax   p10 ${pct(ct, .1):,.0f}  median ${pct(ct, .5):,.0f}  p90 ${pct(ct, .9):,.0f}  "
          f"(p90/p10 {pct(ct, .9) / pct(ct, .1):.1f}x)")
    print(f"city sqft taxes p10 ${pct(st, .1):,.0f}  median ${pct(st, .5):,.0f}  p90 ${pct(st, .9):,.0f}  "
          f"(p90/p10 {pct(st, .9) / pct(st, .1):.1f}x)")


def write_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parcel-out", default=PARCEL_OUT_DEFAULT,
                    help="parcel-level CSV (household AV -- keep OUT of the repo; default scratch/)")
    args = ap.parse_args()
    if args.parcel_out.startswith(("data/", "docs/")):
        raise SystemExit("refusing: parcel-level AV rows must not land in a tracked dir")

    sched = json.load(open(SCHEDULE))
    con = sqlite3.connect(DB)
    parcels = load(con)
    con.close()
    scored, skipped = score(parcels, sched)
    blocks = block_aggregates(scored)
    summary(scored, skipped, blocks)

    write_csv(args.parcel_out, scored,
              ["apn", "usecode", "cls", "block", "sqft", "lot", "av", "av_sqft", "market_ref_av_sqft",
               "ref_level", "ref_n", "discount", "band", "benefit_usd", "county_av_tax", "city_sqft_tax",
               "hoex", "lat", "lon"])
    write_csv(BLOCK_OUT, blocks, list(blocks[0].keys()))
    print(f"\nwrote {len(scored):,} parcel rows -> {args.parcel_out}  (local only)")
    print(f"wrote {len(blocks)} block rows  -> {BLOCK_OUT}  (publishable, n >= {MIN_BLOCK})")


if __name__ == "__main__":
    main()
