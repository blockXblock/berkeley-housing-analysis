#!/usr/bin/env python3
"""gen_bond_incidence.py — PROTOTYPE lead visual for the Berkeley bond op-ed.

Question: what would a new $300M city bond cost each property owner, and how unequally?
A GO bond is repaid by an ad-valorem debt-service rate = annual_debt_service / total_assessed_value.
Per parcel: cost = rate x assessed_value. Because assessed value is acquisition-based (Prop 13,
frozen +2%/yr until sale), an ad-valorem bond falls FAR harder on recent buyers than long-held owners
for the SAME house. The alternative — a flat parcel tax — is uniform per parcel. This map lets a
narrator explore both, parcel by parcel.

DATA (all in-hand, read-only): databases/berkeley.db parcels — TotalNetValue (assessed value = base),
Latitude/Longitude, situs address, LatestDocumentDate. ⚠ LatestDocumentDate is the LAST RECORDED
DOCUMENT of any kind (sale, REFINANCE, trust transfer) — NOT years owned. Calibrated on 2811 Benvenue
(owned since 1988, last doc 2021 = a refi/trust recording, not a sale). The map's 3rd mode shows this
honestly as "recording recency" (a refi/financial-activity signal). TRUE years-owned needs the deed
index with document type (Phase-2 acquisition). The ad-valorem incidence itself does NOT depend on it —
it rests on assessed value, which is the real Prop-13 base.

HONESTY RAILS: (1) Assessed value != market value (Prop 13) — this is the point, not a bug, but the
AV distribution is NOT a wealth distribution. (2) Exemptions (homeowner's $7k, nonprofit, veteran) are
NOT modeled in v1 — the base is gross TotalNetValue. (3) The bond's annual debt service assumes 30yr
@ 5% level payments — an explicit, adjustable assumption printed below. (4) This uses TOTAL citywide AV
as the district base; the exact figure must be validated against the county tax-rate book + actual
bills before publication. Directionally honest; not a certified rate.

ADDED 2026-09-15 (three upgrades, all DERIVED from tables already in hand):
  (a) PROP 13 POSITION per single-family lot — the parcel's AV/sqft vs its own block's p90 (scoring imported
      from scripts/tax_incidence/score_prop13.py; sqft = berkeley.db.taxable_sqft, the City's own base). Shows
      neighbor-vs-neighbor: the same bond, the same street, a 30x spread. Block rings from
      data/derived/berkeley_prop13_by_block_2025-26.csv (n>=8 blocks only).
  (b) TRUE SALES 2023-2025 from parcel_facts.db.ownership_transfers (County Ownership Transfer List, a 2-yr
      rolling window) — replaces "recorded-doc recency" as the recent-buyer signal. Sales BEFORE 2023 are
      simply outside the window: "not sold since 2023" != "long-held".
  (c) SQFT-BASED ALTERNATIVE: the same $ raised per taxable building sqft (how Berkeley's own parcel taxes are
      levied), alongside the flat-per-parcel alternative.
Output: docs/maps/bond_incidence.html (+ _data.json). Serve to view (file:// blocks the streamed fetch).
"""
import sqlite3, json, os, sys, warnings
import pandas as pd, numpy as np

# ---- bond assumptions (explicit, adjustable) ----
PRINCIPAL = 300_000_000      # $300M
TERM_YEARS = 30
INTEREST = 0.05
OUT = "docs/maps/bond_incidence.html"
DATA = "docs/maps/bond_incidence_data.json"   # streamed sibling (serve; file:// blocks the fetch)

# ---- Owner-name publication ----
# DECISION 2026-08-16 (John, informed — see PROGRESS.md): PUBLISH ALL owner names, Chronicle-style, on the
# public bond map. Individual names (incl. ~6,300 family trusts) and corporate/institutional names all ship.
# This flag is a DORMANT one-switch reversal: set True to name-shape-redact PERSONAL names (keeping
# corporate/institutional), e.g. to honor an individual opt-out — a config change, not a re-derivation.
REDACT_PERSONAL_NAMES = False
import re
_ENTITY = re.compile(r"\b(LLC|L\.L\.C|INC|CORP|CORPORATION|COMPANY|LTD|LP|L\.P|LLP|PARTNER|ASSOC|PROPERT|HOLDING|"
                     r"VENTURE|CAPITAL|REALTY|MANAGEMENT|INVEST|ENTERPRISE|GROUP|DEVELOPMENT|UNIVERSITY|REGENTS|"
                     r"CITY OF|COUNTY|STATE OF|CHURCH|SCHOOL|DISTRICT|FOUNDATION|CONGREGATION|TEMPLE|SOCIETY|"
                     r"INSTITUTE|COOPERATIVE|CO-OP|MINISTRIES|DIOCESE|PARISH|HOUSING AUTH|AUTHORITY|COMMISSION|"
                     r"HOSPITAL|BANK|ASSN|ASSOCIATION|NATIONAL|FEDERAL|& CO)\b")
def _display_owner(name):
    if not REDACT_PERSONAL_NAMES or not name:
        return name
    return name if _ENTITY.search(str(name).upper()) else "(individual owner — name withheld)"

def main():
    db = sqlite3.connect("databases/berkeley.db")
    p = pd.read_sql("SELECT APN,Latitude,Longitude,Land,Imps,TotalNetValue,SitusStree,SitusStr_1,"
                    "LatestDocumentDate,UseCode FROM parcels", db)
    for c in ["Latitude", "Longitude", "Land", "Imps", "TotalNetValue"]:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    p = p[(p.TotalNetValue > 0) & p.Latitude.between(37.8, 37.95) & p.Longitude.between(-122.35, -122.2)].copy()
    yr = pd.to_datetime(p.LatestDocumentDate, errors="coerce").dt.year
    # 1900-01-01 is the county's NULL placeholder -> treat as unknown tenure, not "126 yr"
    p["tenure"] = (2026 - yr).where(yr.between(1901, 2026)).clip(0, 99)
    p["addr"] = (p.SitusStree.fillna("").astype(str).str.strip() + " " +
                 p.SitusStr_1.fillna("").astype(str).str.strip()).str.strip()

    # ---- inline parcel card from parcel_facts.db (owner + use + build year) ----
    # propinfo.acgov.org (assessor/tax record) can't be deep-linked and hides owner names, so we show the
    # county-record facts INLINE in the popup. Built by scripts/build_parcel_facts.py.
    from scripts.housing_rules import to_canonical_apn
    p["capn"] = p.APN.apply(lambda a: to_canonical_apn(a, "alameda") if pd.notna(a) else None)
    pf = pd.read_sql("SELECT capn, owner_name, owner_type, use_bucket, build_year, owner_occupied FROM parcel_facts",
                     sqlite3.connect("databases/parcel_facts.db"))
    p = p.merge(pf.drop_duplicates("capn"), on="capn", how="left")
    p["owner_occupied"] = p.owner_occupied.fillna(0).astype(int)

    # ---- (a) Prop 13 position: IMPORT the scorer, never re-derive (scripts/tax_incidence/score_prop13.py) ----
    from scripts.tax_incidence import score_prop13 as sp
    sched = json.load(open(sp.SCHEDULE))
    scored, _ = sp.score(sp.load(db), sched)
    p13 = pd.DataFrame([{"APN": r["apn"], "p13_disc": r["discount"], "p13_ref": r["ref_level"],
                         "p13_ben": r["benefit_usd"]} for r in scored])
    p = p.merge(p13, on="APN", how="left")
    blk = pd.read_csv("data/derived/berkeley_prop13_by_block_2025-26.csv")
    # taxable building sqft (City base for the per-sqft parcel taxes)
    sq = pd.read_sql("SELECT county_apn AS APN, bldsqfttaxable AS sqft, lotsqft AS lot FROM taxable_sqft WHERE county_apn IS NOT NULL", db)
    p = p.merge(sq.drop_duplicates("APN"), on="APN", how="left")
    un = pd.read_sql("SELECT capn, units FROM parcel_facts", sqlite3.connect("databases/parcel_facts.db"))
    p = p.merge(un.drop_duplicates("capn"), on="capn", how="left")

    # ---- (b) true sales: latest County-recorded ownership transfer per parcel (2023-2025 window) ----
    tr = pd.read_sql("SELECT capn, substr(transfer_date,1,4) AS sold_yr, transfer_value FROM ownership_transfers "
                     "WHERE transfer_date >= '2023'", sqlite3.connect("databases/parcel_facts.db"))
    tr["transfer_value"] = pd.to_numeric(tr.transfer_value, errors="coerce")
    tr = tr.sort_values(["capn", "sold_yr"]).groupby("capn").agg(sold_yr=("sold_yr", "max"),
                                                                    sold_val=("transfer_value", "max")).reset_index()
    p = p.merge(tr, on="capn", how="left")
    # VERIFIED 2026-09-15: transfers WITH a recorded value sit at market (median 98% of block p90 AV/sqft);
    # transfers WITHOUT one are indistinguishable from unsold parcels (43% vs 40%) -- trust / parent-child /
    # inter-family changes of ownership that do not reassess. Only PRICED transfers count as a sale;
    # unpriced ones are kept separately as "ownership transfer, not a market sale".
    p["xfer_yr"] = pd.to_numeric(p.sold_yr, errors="coerce").fillna(0).astype(int)
    p["sold_yr"] = p.xfer_yr.where(p.sold_val.fillna(0) > 0, 0)

    # ---- OFFICIAL figures: single source of truth is B2050BIS's reconciliation baseline (CONTRACT: the map
    #      READS official numbers, never hardcodes them). Fallback to the 5%/30yr assumption if it's absent. ----
    import glob
    BASELINE = sorted(glob.glob("data/baselines/measure_u_reconciliation_baseline_*.json"))[-1]
    OFF = {}
    if os.path.exists(BASELINE):
        _b = json.load(open(BASELINE)); OFF = {**_b.get("official", {}), **_b.get("derived", {})}

    # ---- the levy math (today's-base rate reconciled to the baseline; else 5%/30yr) ----
    tot_av = p.TotalNetValue.sum()
    rate = (OFF["rate_today_100k"] / 1e5) if OFF.get("rate_today_100k") else \
           (PRINCIPAL * INTEREST / (1 - (1 + INTEREST) ** -TERM_YEARS)) / tot_av
    annual = rate * tot_av                                                # peak-year debt service on TODAY's base
    n = len(p)
    p["cost_av"] = (rate * p.TotalNetValue).round(0)                      # ad-valorem annual cost (today's-base rate)

    # ---- (d) the SIX BASES of a Berkeley bill, per single-family parcel (IMPORTED: scripts/tax_incidence/decompose.py).
    #      Gives the three denominators a voter needs (E. Friedman, 2026-09-15): the whole bill, the City of Berkeley's
    #      own levies, and the existing City GO-bond tax. Single-family only -- non-SFR rates differ. Bill EXCLUDES the
    #      garbage-cart and street-lighting service fees (not taxes, not derivable). ----
    from scripts.tax_incidence import decompose as DC
    sched_dc = DC.load_schedule()
    sfr = p.use_bucket.eq("residential_sf") & p.sqft.gt(0) & p.lot.gt(0)
    dc = [DC.decompose(av, sqf, lt, u, sched_dc, build_year=(by if pd.notna(by) else None)) if ok else None
          for ok, av, sqf, lt, u, by in zip(sfr, p.TotalNetValue, p.sqft.fillna(0), p.lot.fillna(0), p.units.fillna(1), p.build_year)]
    p["bill"] = [d["bill"] if d else 0 for d in dc]
    p["city_levies"] = [d["city_levies"] if d else 0 for d in dc]
    p["city_go"] = [d["city_go"] if d else 0 for d in dc]
    bill_shares = pd.DataFrame([{k: d[k] / d["bill"] for k in ("ad_valorem", "building_sqft", "lot_sqft", "per_unit", "flat", "use_category")}
                                for d in dc if d]).median()
    cost_flat = round(annual / n)                                          # flat parcel-tax annual cost
    p["delta"] = cost_flat - p.cost_av        # >0: flat costs you MORE (low-AV long-held); <0: flat cheaper
    # (c) same $ raised on taxable building sqft -- the base Berkeley's own parcel taxes use
    rate_sqft = annual / p.sqft.fillna(0).sum()
    p["cost_sq"] = (rate_sqft * p.sqft.fillna(0)).round(0)
    p["delta_sq"] = p.cost_sq - p.cost_av      # >0: a sqft tax costs you MORE than ad valorem

    # ---- headline stats (DERIVED, printed + injected — never hardcoded in the HTML) ----
    # NOTE: `tenure` here is YEARS SINCE LAST RECORDED DOCUMENT (refi/transfer/sale), NOT years owned.
    # We do NOT compute a "recent-buyer vs long-held" cost ratio off it — that would mislabel refinancers
    # as recent buyers (retracted 2026-08-14 after 2811 Benvenue, owned since 1988, showed as 5 yr).
    recent5 = float((p.tenure < 5).mean() * 100)      # % of parcels with a recording in the last 5 yr (the refi wave)
    blkref = p[p.p13_ref == "block"]
    sold = p[p.sold_yr > 0]
    stats = {
        # (a) Prop 13 position (single-family lots, block-referenced)
        "p13_n": int(len(blkref)), "p13_blocks": int(len(blk)),
        "p13_med_pct": round(100 * (1 - blkref.p13_disc.median()), 0),
        "p13_under25": round(100 * (blkref.p13_disc > 0.75).mean(), 1),
        "p13_spread_med": round(blk.av_sqft_max_over_min.median(), 1),
        "p13_benefit_m": round(blkref.p13_ben.sum() / 1e6, 0),
        # (b) true sales 2023-2025
        "sold_n": int(len(sold)), "sold_pct": round(100 * len(sold) / n, 1),
        "xfer_n": int(((p.xfer_yr > 0) & (p.sold_yr == 0)).sum()),
        "sold_med": round(sold.cost_av.median(), 0), "unsold_med": round(p[p.sold_yr == 0].cost_av.median(), 0),
        "sold_sfr_med": round(sold[sold.use_bucket == "residential_sf"].cost_av.median(), 0),
        "unsold_sfr_med": round(p[(p.sold_yr == 0) & (p.use_bucket == "residential_sf")].cost_av.median(), 0),
        # (c) sqft alternative
        "rate_sqft": round(rate_sqft, 4), "sq_med": round(p.loc[p.sqft > 0, "cost_sq"].median(), 0),
        "base_b": tot_av / 1e9, "annual_m": annual / 1e6, "rate_100k": rate * 100_000,
        "n": n, "med_av": p.cost_av.median(), "p10": p.cost_av.quantile(.10), "p90": p.cost_av.quantile(.90),
        "flat": cost_flat, "ineq": p.cost_av.quantile(.90) / max(p.cost_av.quantile(.10), 1),
        "recent5": recent5,
        "rate_today": round(OFF.get("rate_today_100k", rate * 1e5), 1),
        # today's-base AVERAGE: the City's own $15.2M avg debt service / today's base -- the apples-to-apples
        # counterpart of the City's $22.14 average (rate_today is the PEAK counterpart of its $35 peak)
        "rate_today_avg": round(OFF.get("rate_today_avg_100k", rate * 1e5), 1),
        "city_go_rate": OFF.get("existing_city_go_rate_100k", DC.CITY_GO_BOND_RATE * 1e5),
        "bill_n": int(sfr.sum()),
        "bill_pct_med": round(100 * (p.loc[sfr, "cost_av"] / p.loc[sfr, "bill"]).median(), 1),
        "city_pct_med": round(100 * (p.loc[sfr, "cost_av"] / p.loc[sfr, "city_levies"]).median(), 1),
        "go_pct_med": round(100 * (p.loc[sfr, "cost_av"] / p.loc[sfr, "city_go"]).median(), 1),
        "bill_shares": {k: round(100 * v) for k, v in bill_shares.items()},
        "rate_peak": OFF.get("peak_rate_100k", 0), "rate_avg": OFF.get("avg_rate_100k", 0),
        "base_mult": round(OFF.get("base_avg_multiple", 0), 2), "peak_fy": OFF.get("peak_first_fy", 0),
        # who pays: owner-occupied share of the bond. READ the gated figure from B2050BIS's baseline
        # (owner_occupied_share_pct, derived from the same $7k-exemption definition) so map + site show ONE
        # number; fall back to computing it if the baseline is absent.
        "oo_share": round(OFF.get("owner_occupied_share_pct",
                          100 * p.loc[p.owner_occupied == 1, "cost_av"].sum() / p.cost_av.sum()), 1),
        "n_parcels": n, "flat_lit": round(OFF.get("flat_parcel_cost", cost_flat)),
        # concentration + top-1% composition (from B2050BIS baseline)
        "top1": round(OFF.get("top1_share_pct", 0), 1), "top10": round(OFF.get("top10_share_pct", 0), 1),
        "bottom50": round(100 - OFF.get("top50_share_pct", 0), 1), "apt_share": round(OFF.get("apt_share_pct", 0), 1),
        "tier1": (OFF.get("tier_composition_av_pct", {}) or {}).get("1", {}),
        "tier1_entry": OFF.get("tier_entry_av", {}).get("1", 0) if OFF.get("tier_entry_av") else 0,
        "tier1_sfr_n": (OFF.get("tier_composition_count", {}) or {}).get("1", {}).get("single_family", 0),
    }
    print(f"tax base (total AV): ${stats['base_b']:.2f}B over {n:,} parcels")
    print(f"today's-base rate (from baseline) = ${stats['rate_100k']:.0f}/$100k -> ${stats['annual_m']:.1f}M/yr peak DS; "
          f"city advertises ${stats['rate_avg']}/avg, ${stats['rate_peak']}/peak (base {stats['base_mult']}x today)")
    print(f"ad-valorem annual cost: median ${stats['med_av']:.0f}, p10 ${stats['p10']:.0f}, "
          f"p90 ${stats['p90']:.0f}  ({stats['ineq']:.0f}x spread)")
    print(f"flat parcel tax (same $): ${cost_flat}/parcel (uniform)")
    print(f"recorded a document in last 5yr (refi/transfer/sale): {recent5:.0f}% of parcels")
    print(f"Prop 13: {stats['p13_n']:,} SFR lots on {stats['p13_blocks']} blocks; median assessed at "
          f"{stats['p13_med_pct']:.0f}% of block market; {stats['p13_under25']}% under 25%; "
          f"block max/min median {stats['p13_spread_med']}x; benefit ${stats['p13_benefit_m']:.0f}M/yr")
    print(f"sold 2023-25: {stats['sold_n']:,} parcels ({stats['sold_pct']}%); median bond cost sold "
          f"${stats['sold_med']:.0f} vs not-sold ${stats['unsold_med']:.0f} (SFR: ${stats['sold_sfr_med']:.0f} vs ${stats['unsold_sfr_med']:.0f})")
    print(f"sqft alternative: ${rate_sqft:.4f}/sqft -> median ${stats['sq_med']:.0f}/yr")

    def _s(v): return "" if pd.isna(v) else str(v)
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(x, 5), round(y, 5)]},
              "properties": {"v": int(av / 1000), "c": int(c), "d": int(d), "t": int(t) if pd.notna(t) else -1,
                             "a": a, "own": _s(_display_owner(ow)), "ot": _s(otp), "ub": _s(ub),
                             "yb": int(yb) if pd.notna(yb) else 0, "oo": int(oo),
                             "sq": int(sqf) if pd.notna(sqf) else 0, "ds": int(dsq) if pd.notna(dsq) else 0,
                             "pd": round(float(pdisc), 2) if (pd.notna(pdisc) and pref == "block") else -9,
                             "pb": int(pben) if pd.notna(pben) else 0,
                             "sy": int(sy), "sv": int(sv) if (pd.notna(sv) and sv > 0) else 0,
                             "xy": int(xy) if not sy else 0,
                             "bl": int(bl), "cl": int(cl), "cg": int(cg)}}
             for x, y, av, c, d, t, a, ow, otp, ub, yb, oo, sqf, dsq, pdisc, pref, pben, sy, sv, xy, bl, cl, cg in zip(
                 p.Longitude, p.Latitude, p.TotalNetValue, p.cost_av, p.delta, p.tenure, p.addr,
                 p.owner_name, p.owner_type, p.use_bucket, p.build_year, p.owner_occupied,
                 p.sqft, p.delta_sq, p.p13_disc, p.p13_ref, p.p13_ben, p.sold_yr, p.sold_val, p.xfer_yr,
                 p.bill, p.city_levies, p.city_go)]
    blk_feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(r.lon, 5), round(r.lat, 5)]},
                  "properties": {"b": r.block, "n": int(r.n_sfr), "sp": float(r.av_sqft_max_over_min),
                                 "md": float(r.median_discount), "u25": float(r.share_under_25pct),
                                 "ben": int(r.benefit_usd_total), "ct": int(r.median_county_av_tax),
                                 "st": int(r.median_city_sqft_tax)}} for r in blk.itertuples()]

    import geopandas as gpd
    el = gpd.read_file("data/reference/berkeley_neighborhoods.geojson").to_crs(4326)
    elb = json.loads(el[el.Name.astype(str).str.contains("lmwood", case=False)][["geometry"]].to_json())

    js_stats = json.dumps({k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in stats.items()})
    html = """<!doctype html><html><head><meta charset="utf-8"><title>What a $300M bond costs each owner</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<style>body,html,#map{margin:0;height:100%;font-family:system-ui}
.panel{position:absolute;top:12px;left:12px;width:340px;background:rgba(255,255,255,.95);padding:12px 15px;border-radius:8px;box-shadow:0 1px 8px rgba(0,0,0,.35);font-size:13px}
.panel h3{margin:0 0 6px} .panel button{font-size:12px;padding:5px 9px;margin:2px 3px 2px 0;cursor:pointer;border:1px solid #999;background:#fff;border-radius:5px}
.panel button.on{background:#111;color:#fff;border-color:#111}
.big{font-size:22px;font-weight:700} .sub{color:#555;font-size:11px}
#legend{margin-top:8px} .sw{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:5px;vertical-align:middle}
.cap{color:#444;font-size:11px;margin-top:8px;line-height:1.35}
.stat{background:#f4f4f4;border-radius:6px;padding:7px 9px;margin-top:8px;font-size:12px}
.tag{background:#111;color:#fff;border-radius:6px;padding:8px 11px;margin:-2px 0 8px;font-size:12.5px;line-height:1.35}
.who{background:#fff7ec;border:1px solid #f0d8b0;border-radius:6px;padding:8px 10px;margin-top:8px;font-size:11.5px;line-height:1.4}</style></head>
<body><div id="map"></div>
<div class="panel">
<div class="tag">🔎 Every dot is a parcel — click it for its <b>property tax, owner, and bond cost</b>. Find where you live.</div>
<h3>Measure U — a new $300M city bond</h3>
<div class="sub">Levied on <b>$__BASE__B</b> of assessed value. The city advertises <b>$__AVG__ per $100k</b> average / <b>$__PEAK__</b> peak — on a base it projects will roughly double. On <i>today's</i> base the same bond is <b>$__TAVG__</b> average / <b>$__RATE__</b> peak. Costs below are annual dollars per parcel — toggle the rate. <a href="#" onclick="document.getElementById('why').style.display='block';return false">Which rate is right? →</a></div>
<div style="margin:8px 0 2px"><b>Color each parcel by:</b></div>
<div>
<button id="b_c" class="on" onclick="mode('c')">Annual $ cost</button>
<button id="b_b" onclick="mode('b')">% of your tax bill</button>
<button id="b_o" onclick="mode('o')">Owner-occupied vs rental</button>
<button id="b_d" onclick="mode('d')">Flat / sqft vs ad-valorem</button>
<button id="b_p" onclick="mode('p')">Prop 13 vs neighbors</button>
<button id="b_s" onclick="mode('s')">Sold 2023–25</button>
<button id="b_t" onclick="mode('t')">Recorded-doc recency</button></div>
<div id="alts" style="margin:4px 0 2px;display:none"><span class="sub">compare ad-valorem with:</span>
<button id="a_flat" class="on" onclick="setAlt('flat')">flat per parcel</button>
<button id="a_sq" onclick="setAlt('sq')">per building sqft</button></div>
<div id="dens" style="margin:4px 0 2px;display:none"><span class="sub">bond as a % of:</span>
<button id="d_bill" class="on" onclick="setDen('bill')">whole tax bill</button>
<button id="d_city" onclick="setDen('city')">City of Berkeley levies only</button></div>
<div id="rates" style="margin:6px 0 2px"><span class="sub">rate:</span>
<button id="r_tavg" class="on" onclick="setRate(S.rate_today_avg)">today avg $__TAVG__</button>
<button id="r_today" onclick="setRate(S.rate_today)">today peak $__RATE__</button>
<button id="r_avg" onclick="setRate(S.rate_avg)">city avg $__AVG__</button>
<button id="r_peak" onclick="setRate(S.rate_peak)">city peak $__PEAK__</button></div>
<div id="legend"></div>
<div class="stat" id="stat"></div>
<div class="cap" id="cap"></div>
<div class="who" id="who"></div><div style="margin-top:8px;font-size:11px"><a href="https://www.sfchronicle.com/projects/2025/ca-property-map/" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:none">↗ Compare: SF Chronicle statewide owner map</a></div></div>
<div id="why" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:20" onclick="if(event.target===this)this.style.display='none'"><div style="background:#fff;max-width:1000px;margin:3vh auto;padding:16px 20px;border-radius:10px;max-height:94vh;overflow:auto;font-size:13px;line-height:1.45">
<div style="float:right"><button onclick="document.getElementById('why').style.display='none'">close ✕</button></div>
<h3 style="margin:0 0 6px">$__AVG__, $__PEAK__, $__TAVG__, $__RATE__ — which is it?</h3>
<p>All four are the <b>same $300M bond</b> with the same debt service. They differ only in <b>which year</b> and <b>which tax base</b> you divide by. A rate per $100k is a quotient, not a price: the dollars to be raised are fixed; the rate moves with the base.</p>
<table style="border-collapse:collapse;margin:6px 0 10px"><tr><th></th><th style="padding:3px 10px;text-align:left">City's projected base<br><span style="font-weight:400;color:#666">grows ~__MULT__× from future sales + new construction</span></th><th style="padding:3px 10px;text-align:left">Today's base<br><span style="font-weight:400;color:#666">$__BASE__B, the parcels that exist now</span></th></tr>
<tr><td style="padding:3px 10px"><b>average year</b></td><td style="padding:3px 10px">$__AVG__ <span style="color:#666">(the City's advertised figure)</span></td><td style="padding:3px 10px">$__TAVG__</td></tr>
<tr><td style="padding:3px 10px"><b>peak years</b> (all three tranches outstanding)</td><td style="padding:3px 10px">$__PEAK__ <span style="color:#666">(the City's disclosed peak, from FY__PEAKFY__)</span></td><td style="padding:3px 10px">$__RATE__</td></tr></table>
<p>The City's numbers are lower only because they assume owners who do not yet exist — future buyers reassessed to purchase price, and new construction — will carry roughly half of it. If the base grows as projected, a long-held owner's rate drifts <i>down</i> each year and newcomers make up the difference. If it does not, the rate is the right-hand column.</p>
<img src="bond_tranches.svg" alt="Measure U: debt service by tranche, the assessed-value base, and the rate per $100k on each base" style="width:100%;height:auto;border:1px solid #eee;border-radius:6px">
<p style="color:#666;font-size:11.5px">Every number is derived from the City's official figures (Resolution 72,338-N.S. Exhibit B) and the Alameda County assessor roll; figure generated by <code>scripts/viz/bond_tranches_svg.py</code>. Direct link: <a href="bond_tranches.svg">bond_tranches.svg</a></p>
</div></div>
<script>
const S=__STATS__;
let FEATS={features:[]}, MODE='c', RATE=S.rate_today_avg, ALT='flat', DEN='bill';
const usd=x=>'$'+Math.round(x).toLocaleString();
// cost = assessed value × rate/$100k. v = AV/1000, so cost = v × rate_per_100k / 100. Rate is selectable.
const costExpr=r=>['step',['*',['get','v'],r/100],'#2c7fb8',200,'#7fcdbb',500,'#fec44f',1000,'#fd8d3c',2500,'#e31a1c'];
// bond ÷ denominator, in %. bl = whole bill (ex garbage/lighting service fees), cl = City of Berkeley levies; 0 = not a single-family parcel (grey)
const pctExpr=(r,k)=>['case',['<=',['get',k],0],'#d9d9d9',['step',['*',100,['/',['*',['get','v'],r/100],['get',k]]], ...(k=='bl'?['#2c7fb8',2,'#7fcdbb',3,'#fec44f',4,'#fd8d3c',6,'#e31a1c']:['#2c7fb8',8,'#7fcdbb',12,'#fec44f',16,'#fd8d3c',25,'#e31a1c'])]];
const LB='<div><span class="sw" style="background:#2c7fb8"></span>&lt;2% of the bill</div><div><span class="sw" style="background:#7fcdbb"></span>2–3%</div><div><span class="sw" style="background:#fec44f"></span>3–4%</div><div><span class="sw" style="background:#fd8d3c"></span>4–6%</div><div><span class="sw" style="background:#e31a1c"></span>6%+</div><div><span class="sw" style="background:#d9d9d9"></span>not a single-family parcel</div>';
const LBc='<div><span class="sw" style="background:#2c7fb8"></span>&lt;8% more to the City</div><div><span class="sw" style="background:#7fcdbb"></span>8–12%</div><div><span class="sw" style="background:#fec44f"></span>12–16%</div><div><span class="sw" style="background:#fd8d3c"></span>16–25%</div><div><span class="sw" style="background:#e31a1c"></span>25%+</div><div><span class="sw" style="background:#d9d9d9"></span>not a single-family parcel</div>';
const DELTA=['step',['get','d'],'#b2182b',-400,'#ef8a62',-100,'#f7f7f7',100,'#67a9cf',400,'#2166ac']; // red=flat costs you MORE
const TEN=['step',['get','t'],'#e31a1c',5,'#fd8d3c',15,'#fec44f',30,'#74add1',60,'#4575b4'];
const DSQ=['step',['get','ds'],'#b2182b',-400,'#ef8a62',-100,'#f7f7f7',100,'#67a9cf',400,'#2166ac']; // red = sqft tax costs you MORE
// pd = 1 - (AV/sqft)/(block p90 AV/sqft); -9 = not a scored single-family lot (grey)
const P13=['case',['<',['get','pd'],-1],'#d9d9d9',['step',['get','pd'],'#2c7fb8',0.25,'#7fcdbb',0.5,'#fec44f',0.75,'#e31a1c']];
const SOLD=['case',['>',['get','sy'],0],['match',['get','sy'],2023,'#fd8d3c',2024,'#e31a1c',2025,'#99000d','#cfd8dc'],['>',['get','xy'],0],'#9e9ac8','#cfd8dc'];
const BLK=['step',['get','sp'],'#74add1',10,'#fec44f',30,'#fd8d3c',60,'#e31a1c'];
const LP='<div><span class="sw" style="background:#2c7fb8"></span>near market (assessed &gt;75% of block level)</div><div><span class="sw" style="background:#7fcdbb"></span>50–75%</div><div><span class="sw" style="background:#fec44f"></span>25–50%</div><div><span class="sw" style="background:#e31a1c"></span>under 25% — deep Prop 13</div><div><span class="sw" style="background:#d9d9d9"></span>not a scored single-family lot</div><div style="margin-top:4px"><span class="sw" style="background:#fff;border:2px solid #e31a1c"></span>block ring (zoom in to see): highest/lowest AV per sqft on the block (blue &lt;10× → red 60×+); click a ring</div>';
const LS='<div><span class="sw" style="background:#99000d"></span>sold 2025</div><div><span class="sw" style="background:#e31a1c"></span>sold 2024</div><div><span class="sw" style="background:#fd8d3c"></span>sold 2023</div><div><span class="sw" style="background:#9e9ac8"></span>ownership transfer 2023–25 with NO price (trust / family — not a market sale)</div><div><span class="sw" style="background:#cfd8dc"></span>no County-recorded transfer in the window</div>';
const LQ='<div><span class="sw" style="background:#2166ac"></span>sqft tax cheaper for you (high value per sqft)</div><div><span class="sw" style="background:#f7f7f7;border:1px solid #ccc"></span>about the same</div><div><span class="sw" style="background:#b2182b"></span>sqft tax costs you MORE (big building, low assessed value)</div>';
const CAPp='Each single-family lot\\'s assessed value per sqft against the TOP of its own block (p90 ≈ recent-sale level). Same street, same bond: the house assessed at 20% of its neighbor pays one-fifth the bond. Sqft is the City\\'s taxable square footage. Blocks with fewer than 8 single-family lots are grey. <b>Assessed value is NOT wealth</b> — a deep discount means an old purchase, not a poor household.';
const CAPs='Parcels with a County-recorded ownership transfer AND a recorded price in 2023–2025 (Assessor Ownership Transfer List, a two-year rolling window) — the actual recent buyers, reassessed to purchase price, so they pay the most per house. Transfers with no price (purple) are trust / parent-child / inter-family changes that do NOT reassess — verified: they sit at the same assessed level as unsold parcels. Not-sold-in-window ≠ long-held: sales before 2023 are outside the window.';
const CAPq='Same $300M raised on TAXABLE BUILDING SQFT ('+'$'+S.rate_sqft.toFixed(2)+'/sqft/yr) — the base Berkeley\\'s own voter-approved parcel taxes use. Red = you would pay MORE under a sqft tax (big house, low assessed value); blue = LESS. Tracks building size, not purchase date.';
const LC='<div><span class="sw" style="background:#2c7fb8"></span>&lt;$200/yr</div><div><span class="sw" style="background:#7fcdbb"></span>$200–500</div><div><span class="sw" style="background:#fec44f"></span>$500–1,000</div><div><span class="sw" style="background:#fd8d3c"></span>$1,000–2,500</div><div><span class="sw" style="background:#e31a1c"></span>$2,500+ /yr</div>';
const LD='<div><span class="sw" style="background:#2166ac"></span>flat tax cheaper for you (high-value)</div><div><span class="sw" style="background:#f7f7f7;border:1px solid #ccc"></span>about the same</div><div><span class="sw" style="background:#b2182b"></span>flat tax costs you MORE (long-held/low-value)</div>';
const LT='<div><span class="sw" style="background:#e31a1c"></span>&lt;5 yr (recent sale/refi/transfer)</div><div><span class="sw" style="background:#fd8d3c"></span>5–15</div><div><span class="sw" style="background:#fec44f"></span>15–30</div><div><span class="sw" style="background:#74add1"></span>30–60</div><div><span class="sw" style="background:#4575b4"></span>60+ (no recording in decades)</div>';
const CAPb=()=>DEN=='bill'
 ?'Measure U as a share of the parcel\\'s WHOLE current tax bill (ad valorem + every parcel tax; garbage-cart and street-lighting service fees excluded — not taxes). Single-family parcels only: the parcel-tax rates are validated on single-family bills. A bill has six bases — assessed value (~'+S.bill_shares.ad_valorem+'%), building sqft (~'+S.bill_shares.building_sqft+'%), lot area, dwelling units, flat, use category — and this bond lands entirely on the first.'
 :'Measure U as a share of what the parcel already pays to the <b>City of Berkeley itself</b> — its existing GO-bond levy ($'+S.city_go_rate+'/$100k), its 8 per-sqft taxes (parks, library, fire, streets, paramedic, disabled access), stormwater and street-light charges. Not schools, county, BART, AC Transit, Peralta, EBMUD. The voter\\'s question: how much MORE am I handing this specific body?';
const CAPd='Same $300M raised as a FLAT parcel tax ('+usd(S.flat)+'/parcel). Red = you would pay MORE under a flat tax (long-held, low assessed value); blue = LESS (recent, high value). A flat tax shifts burden onto long-held owners.';
const CAPt='Years since the LAST RECORDED DOCUMENT (sale, refinance, transfer) — NOT years owned. The red 2020-22 bulge is the pandemic refinance wave (2811 Benvenue, owned since 1988, shows as 2021 from a refi/trust recording). A financial-activity signal, not tenure.';
const OO=['match',['get','oo'],1,'#1a9850','#e34a33'];
const LO='<div><span class="sw" style="background:#1a9850"></span>owner-occupied (has $7k homeowner\\'s exemption)</div><div><span class="sw" style="background:#e34a33"></span>rental / non-owner-occupied / commercial</div>';
const CAPo='Owner-occupied (green) vs everything else (red), flagged by the $7,000 homeowner\\'s exemption — a FLOOR (some owner-occupiers never file). Tax on rentals & commercial is largely passed through to tenants, so renters bear it indirectly.';
function rateLbl(){return RATE==S.rate_avg?'city avg $'+S.rate_avg:RATE==S.rate_peak?'city peak $'+S.rate_peak:RATE==S.rate_today_avg?"today\\'s base, avg $"+Math.round(S.rate_today_avg):"today\\'s base, peak $"+Math.round(S.rate_today);}
function rateNote(){
 if(RATE==S.rate_today_avg) return 'TODAY\\'S-BASE AVERAGE ($'+Math.round(S.rate_today_avg)+'/$100k): the City\\'s own average annual debt service divided by today\\'s base — the apples-to-apples counterpart of its advertised $'+S.rate_avg+', which assumes a ~'+S.base_mult.toFixed(1)+'× larger future base. Peak years (all three tranches outstanding) are $'+Math.round(S.rate_today)+'.';
 if(RATE==S.rate_avg) return 'City-advertised AVERAGE ($'+S.rate_avg+'/$100k). It looks low only because it is levied on a projected ~'+S.base_mult.toFixed(1)+'× larger FUTURE base (Prop-13 growth from future sales + new construction). The same debt service on today\\'s base is $'+Math.round(S.rate_today)+'.';
 if(RATE==S.rate_peak) return 'City-disclosed PEAK ($'+S.rate_peak+'/$100k, first applying FY'+S.peak_fy+'-41). Still levied on a larger future base than today\\'s.';
 return 'TODAY\\'S-BASE PEAK ($'+Math.round(S.rate_today)+'/$100k): the years all three $100M tranches are outstanding, on today\\'s base — the counterpart of the City\\'s $'+S.rate_peak+' peak, which assumes a larger future base. Average over the life: $'+Math.round(S.rate_today_avg)+'.';
}
function stat(m){
 const f=RATE/S.rate_today;
 if(m=='c') return '<span class="big">'+usd(S.med_av*f)+'/yr</span> median parcel · '+rateLbl()+'<br>range '+usd(S.p10*f)+' – '+usd(S.p90*f)+' ('+Math.round(S.ineq)+'× spread for the same bond)';
 if(m=='b'){const g=Math.round(100*RATE/S.city_go_rate); return DEN=='bill'
   ?'<span class="big">'+(S.bill_pct_med*f).toFixed(1)+'%</span> of the median single-family tax bill · '+rateLbl()+'<br>('+S.bill_n.toLocaleString()+' single-family parcels; whole bill excl. garbage & lighting fees)'
   :'<span class="big">'+(S.city_pct_med*f).toFixed(1)+'%</span> more to the City of Berkeley, median single-family parcel · '+rateLbl()+'<br>and <b>'+g+'%</b> more City GO-bond tax than today\\'s — for every parcel, because both are levied on assessed value';}
 if(m=='o') return '<span class="big">'+S.oo_share+'%</span> of the bond falls on owner-occupied homes<br>the other '+(100-S.oo_share).toFixed(1)+'% is on rentals & commercial — largely tenant-borne via pass-through';
 if(m=='d'&&ALT=='sq') return '<span class="big">'+usd(S.sq_med)+'/yr</span> median parcel on a sqft base<br>vs ad-valorem median '+usd(S.med_av)+' — a sqft tax tracks building size, not purchase date';
 if(m=='d') return '<span class="big">'+usd(S.flat_lit)+'/yr</span> flat, every parcel<br>vs ad-valorem median '+usd(S.med_av)+' — a flat tax is blind to value';
 if(m=='p') return '<span class="big">'+S.p13_med_pct+'%</span> — the median house is assessed at '+S.p13_med_pct+'% of its own block\\'s market level<br>'+S.p13_under25+'% are under 25%; within a typical block the spread is <b>'+S.p13_spread_med+'×</b> ('+S.p13_n.toLocaleString()+' lots, '+S.p13_blocks+' blocks; ≈ $'+S.p13_benefit_m+'M/yr of ad-valorem tax not levied)';
 if(m=='s') return '<span class="big">'+S.sold_n.toLocaleString()+'</span> parcels sold at a recorded price 2023–25 ('+S.sold_pct+'%; another '+S.xfer_n.toLocaleString()+' changed hands with no price — not sales)<br>median bond cost, single-family: <b>'+usd(S.sold_sfr_med)+'/yr</b> if bought since 2023 vs '+usd(S.unsold_sfr_med)+' if not';
 return '<span class="big">'+Math.round(S.recent5)+'%</span> of parcels recorded a document in the last 5 years (the refi wave) — a financial-activity signal, <b>not</b> years owned';
}
function mode(m){ MODE=m;
 for(const k of ['c','b','o','d','p','s','t']) document.getElementById('b_'+k).className = k==m?'on':'';
 document.getElementById('rates').style.display = (m=='c'||m=='b')?'block':'none';
 document.getElementById('dens').style.display = m=='b'?'block':'none';
 document.getElementById('alts').style.display = m=='d'?'block':'none';
 map.setPaintProperty('pts','circle-color', m=='c'?costExpr(RATE):m=='b'?pctExpr(RATE,DEN=='bill'?'bl':'cl'):m=='o'?OO:m=='d'?(ALT=='sq'?DSQ:DELTA):m=='p'?P13:m=='s'?SOLD:TEN);
 map.setLayoutProperty('blk','visibility', m=='p'?'visible':'none');
 map.setPaintProperty('pts','circle-opacity', m=='s'?['case',['>',['get','sy'],0],1,['>',['get','xy'],0],0.7,0.25]:0.9);
 map.setPaintProperty('pts','circle-stroke-opacity', m=='s'?['case',['>',['get','sy'],0],1,0.15]:1);
 document.getElementById('legend').innerHTML = m=='c'?LC:m=='b'?(DEN=='bill'?LB:LBc):m=='o'?LO:m=='d'?(ALT=='sq'?LQ:LD):m=='p'?LP:m=='s'?LS:LT;
 document.getElementById('cap').innerHTML = m=='c'?('Ad-valorem: each parcel pays rate × its assessed value. <i>'+rateNote()+'</i>'):m=='b'?CAPb():m=='o'?CAPo:m=='d'?(ALT=='sq'?CAPq:CAPd):m=='p'?CAPp:m=='s'?CAPs:CAPt;
 document.getElementById('stat').innerHTML = stat(m);
}
function setDen(d){ DEN=d; document.getElementById('d_bill').className=d=='bill'?'on':''; document.getElementById('d_city').className=d=='city'?'on':''; mode('b'); }
function setAlt(a){ ALT=a; document.getElementById('a_flat').className=a=='flat'?'on':''; document.getElementById('a_sq').className=a=='sq'?'on':''; mode('d'); }
function setRate(r){ RATE=r;
 document.getElementById('r_today').className=(Math.abs(r-S.rate_today)<1e-9)?'on':'';
 document.getElementById('r_tavg').className=(Math.abs(r-S.rate_today_avg)<1e-9)?'on':'';
 document.getElementById('r_peak').className=(r==S.rate_peak)?'on':'';
 document.getElementById('r_avg').className=(r==S.rate_avg)?'on':'';
 if(MODE=='c'||MODE=='b') mode(MODE);
}
(function(){ var w='<b>Who actually pays.</b> The bond is levied on <b>'+S.n_parcels.toLocaleString()+' taxable parcels</b> — not on Berkeley\\'s ~124,000 residents. Roughly 45,000 are UC students who rent or live in dorms and own no parcel; renters bear property tax only indirectly, through rent. The top 10% of parcels carry <b>'+S.top10+'%</b> of the bond; the bottom half pays <b>'+S.bottom50+'%</b>.';
 if(S.tier1&&S.tier1.apartments_mixed!==undefined) w+=' And the biggest payers are <b>not homeowners</b>: the top 1% (parcels over $'+(S.tier1_entry/1e6).toFixed(1)+'M assessed) are <b>'+Math.round(S.tier1.apartments_mixed)+'% apartment buildings, '+Math.round(S.tier1.commercial_industrial)+'% commercial, '+Math.round(S.tier1.institutional)+'% institutional</b> — just '+S.tier1_sfr_n+' single-family homes. Apartments alone are <b>'+S.apt_share+'%</b> of the bond, passed through to renters.';
 document.getElementById('who').innerHTML=w; })();
const map=new maplibregl.Map({container:'map',center:[-122.273,37.871],zoom:12.3,
 style:{version:8,sources:{c:{type:'raster',tiles:['https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'],tileSize:256,attribution:'Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap contributors'}},layers:[{id:'bg',type:'raster',source:'c'}]}});
map.on('load',()=>{
 map.addSource('el',{type:'geojson',data:__ELB__});
 map.addLayer({id:'elw',type:'line',source:'el',paint:{'line-color':'#111','line-width':1.5,'line-dasharray':[2,2]}});
 map.addSource('p',{type:'geojson',data:'bond_incidence_data.json'});
 map.addLayer({id:'pts',type:'circle',source:'p',paint:{'circle-radius':['interpolate',['linear'],['zoom'],11,1.8,15,5],'circle-color':costExpr(S.rate_today_avg),'circle-opacity':0.9,'circle-stroke-color':'rgba(20,20,20,0.9)','circle-stroke-width':['interpolate',['linear'],['zoom'],11,0.6,15,1.2]}});
 map.addSource('b',{type:'geojson',data:__BLK__});
 map.addLayer({id:'blk',type:'circle',source:'b',minzoom:13.5,layout:{visibility:'none'},paint:{'circle-radius':['interpolate',['linear'],['zoom'],11,7,15,26],'circle-color':'rgba(0,0,0,0)','circle-stroke-color':BLK,'circle-stroke-width':['interpolate',['linear'],['zoom'],11,1.5,15,3]}});
 map.on('click','blk',e=>{const b=e.features[0].properties;
   new maplibregl.Popup().setLngLat(e.lngLat).setHTML('<b>Block '+b.b+'</b> — '+b.n+' single-family lots'
     +'<br>highest / lowest assessed $ per sqft: <b>'+b.sp.toFixed(0)+'×</b>'
     +'<br>median lot assessed at '+Math.round(100*(1-b.md))+'% of block market; '+Math.round(100*b.u25)+'% under 25%'
     +'<br>ad-valorem tax not levied on this block: ≈ '+usd(b.ben)+'/yr'
     +'<br>median county AV tax '+usd(b.ct)+' · median city sqft taxes '+usd(b.st)).addTo(map);});
 fetch('bond_incidence_data.json').then(r=>r.json()).then(d=>{FEATS=d;}); mode('c');
 map.on('click','pts',e=>{const p=e.features[0].properties,a=p.a||'(address unavailable)';
   const t=p.t<0?'unknown':(2026-p.t)+' ('+p.t+' yr ago)';
   const q=encodeURIComponent(a+' Berkeley CA');
   new maplibregl.Popup().setLngLat(e.lngLat).setHTML(
     '<b>'+a+'</b>'
     +(p.own?'<br>owner: '+p.own+(p.ot?' <span style="color:#777">('+p.ot+')</span>':''):'')
     +(p.yb?'<br>built: '+p.yb:'')+(p.ub?' &middot; '+p.ub.replace(/_/g,' '):'')
     +(p.oo?'<br><span style="color:#1a9850">owner-occupied</span> (homeowner\\'s exemption)':'<br><span style="color:#c0392b">rental / non-owner-occupied</span>')
     +'<br>assessed value: '+usd(p.v*1000)
     +'<hr style="margin:5px 0;border:none;border-top:1px solid #ddd">'
     +'your Measure U bond cost: <b>'+usd(p.v*RATE/100)+'/yr</b> <span style="color:#777">('+rateLbl()+')</span>'
     +'<br>if it were a flat parcel tax: '+usd(S.flat_lit)+'/yr'
     +(p.sq?'<br>if it were a sqft tax: '+usd(p.v*RATE/100+p.ds)+'/yr <span style="color:#777">('+p.sq.toLocaleString()+' taxable sqft)</span>':'')
     +(p.bl>0?'<br>Measure U = <b>'+(100*p.v*RATE/100/p.bl).toFixed(1)+'%</b> of this parcel\\'s tax bill · <b>'+(100*p.v*RATE/100/p.cl).toFixed(1)+'%</b> more to the City of Berkeley · <b>'+Math.round(100*p.v*RATE/100/p.cg)+'%</b> more City GO-bond tax <span style="color:#777">(bill ≈ '+usd(p.bl)+', of which City ≈ '+usd(p.cl)+'; garbage & lighting fees excluded)</span>':'<br><span style="color:#777">percent-of-bill shown for single-family parcels only</span>')
     +(p.pd>-1?'<br>Prop 13: assessed at <b>'+Math.round(100*(1-p.pd))+'%</b> of this block\\'s market level — ≈ '+usd(p.pb)+'/yr of ad-valorem tax not levied':'')
     +(p.sy?'<br><b>sold '+p.sy+' for '+usd(p.sv)+'</b> (County ownership transfer)':(p.xy?'<br>ownership transfer '+p.xy+', no recorded price — trust / family, not a market sale':''))
     +'<br>last recorded document: '+t
     +'<br><a href="https://www.google.com/maps/search/?api=1&query='+q+'" target="_blank" rel="noopener">Street view ↗</a>'
     +' &middot; <a href="https://www.sfchronicle.com/projects/2025/ca-property-map/?search='+encodeURIComponent(a+', Berkeley')+'" target="_blank" rel="noopener" data-addr="'+encodeURIComponent(a+', Berkeley')+'" onclick="try{navigator.clipboard.writeText(decodeURIComponent(this.dataset.addr))}catch(e){}" title="Opens the Chronicle owner map; the address is copied to your clipboard so you can paste it into the search box.">SF Chronicle ↗</a>'+' &middot; <a href="https://app.regrid.com/us/ca/alameda/berkeley" target="_blank" rel="noopener" data-addr="'+encodeURIComponent(a+', Berkeley')+'" onclick="try{navigator.clipboard.writeText(decodeURIComponent(this.dataset.addr))}catch(e){}" title="Opens Regrid Berkeley parcel map; address copied to clipboard, paste into the search box for free parcel data (APN, sale price, assessed value, building).">Regrid ↗</a>'
     ).addTo(map);});
 map.on('mouseenter','pts',()=>map.getCanvas().style.cursor='pointer');
 map.on('mouseleave','pts',()=>map.getCanvas().style.cursor='');
});
</script></body></html>""".replace("__ELB__", json.dumps(elb)).replace("__BLK__", json.dumps({"type": "FeatureCollection", "features": blk_feats})).replace("__STATS__", js_stats) \
        .replace("__ANNUAL__", f"{stats['annual_m']:.1f}").replace("__BASE__", f"{stats['base_b']:.0f}") \
        .replace("__RATE__", f"{stats['rate_100k']:.0f}").replace("__TAVG__", f"{stats['rate_today_avg']:.0f}") \
        .replace("__MULT__", f"{stats['base_mult']:.1f}").replace("__PEAKFY__", f"{stats['peak_fy']}") \
        .replace("__PEAK__", f"{stats['rate_peak']:.0f}").replace("__AVG__", f"{stats['rate_avg']:.0f}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"type": "FeatureCollection", "features": feats}, open(DATA, "w"))
    open(OUT, "w").write(html)
    print(f"\nwrote {OUT} ({round(len(html)/1024)} KB) + {DATA} ({round(os.path.getsize(DATA)/1e6,1)} MB)")

if __name__ == "__main__":
    main()
