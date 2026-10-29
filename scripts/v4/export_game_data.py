"""export_game_data.py -- the data file for the "Can it pencil?" game (docs/play/). MACHINERY, read-only.

John, 2026-10-28: "Can we build a BerkeleyBuild game that shows developers looking at parcels all over Berkeley to see
if any might pencil out? or re-examine projects in the pipeline to see if any new laws make a project more profitable
... try playing with the under-construction project at 2800 Telegraph".

The game runs a JavaScript port of scripts/v4/pencil_out.py (docs/play/pencil.js). This file hands it the SAME inputs the
Python model reads -- the assumptions resolved into the three scenarios, the Rent Board rents, the zoning table, each
parcel's inputs from the 2026-10-28 zoned citywide pass, and the pipeline projects' RECORD inputs -- plus the Python
results, so scripts/v4/pencil_js_parity.mjs can check the port reproduces them. Nothing here is a new assumption except where labeled.
"""
import csv, json, sqlite3, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "v4"))
import pencil_out as po          # noqa: E402
import proforma_projects as pp   # noqa: E402

OUT = ROOT / "docs/play/game_data.json"
CITYWIDE = ROOT / "data/derived/pencil_out/citywide_zoned_2026-10-28.csv"
META = ROOT / "data/derived/pencil_out/citywide_zoned_2026-10-28.meta.json"
RESULTS = ROOT / "data/derived/pencil_out/results_2026-10-28.json"
A = po.A

# 2800 Telegraph: RECORD inputs read from the ZAB hearing plan set (2023-04-27), sheets A0.1 (zoning data, unit counts)
# and A0.3B (density bonus table). Not yet in a project_inputs_record_*.csv; a candidate row set for it.
PLAN_2800 = "plan set ZP2022-0107, ZAB hearing set 2023-04-27 (R2 architect_plans/proj146_2800-telegraph-ave_2023-04-27.pdf)"
REC_2800 = {
    "units": ("16", "A0.1 Zoning Code Data: number of dwelling units, proposed w/ density bonus"),
    "gross_floor_area": ("19936", "A0.1: total GSF, proposed w/ density bonus"),
    "stories": ("6", "A0.1: building stories 6 (base 3), height 70'-5\" (base 35')"),
    "lot_area": ("3695", "A0.1: lot area 3,695 sf (A0.3B base table: 3,750)"),
    "unit_mix": ("studio 1; 3BR 10; 4BR 5", "A0.1 Unit Counts: 1 studio, 10 3-bed, 5 4-bed; 51 bedrooms"),
    "affordable": ("VLI 1", "A0.3B Density Bonus Table: 1 VLI unit = 8% of 12 base units -> 27.5% bonus"),
    "commercial_floor_area": ("0", "A0.1: ground level = lobby, bikes, 1 studio; no commercial"),
}
EXTRA_2800 = dict(base_units=12, base_units_source="A0.3B: base project 12 units, 13,748 sf, 3 stories",
                  bonus_table_source="A0.3B: the architect's VLI% -> bonus table (AB 2345): 5% 20, 8% 27.5, 10% 32.5, 15% 50",
                  beds=51)

# BART stations (Tier 1 TOD stops under SB 79) that can reach Berkeley parcels within 1/2 mile. LABELED: station
# centroids (BART GTFS stops); SB 79 measures from the parcel's nearest edge to a pedestrian access point, so a
# centroid-to-centroid distance slightly overstates it. The legal map is MTC's SB 79 map.
BART = [
    dict(name="Downtown Berkeley", lat=37.870104, lon=-122.268133),
    dict(name="North Berkeley", lat=37.873967, lon=-122.283440),
    dict(name="Ashby", lat=37.852803, lon=-122.270062),
    dict(name="Rockridge", lat=37.844702, lon=-122.251371),
    dict(name="El Cerrito Plaza", lat=37.902632, lon=-122.298904),
]

# SB 79 standards, Table 1 of ABAG's "Senate Bill 79 (2025) Summary" (updated 2026-07-01), Gov. Code 65912.157(a)(3)-(6)
SB79 = dict(
    source="ABAG, Senate Bill 79 (2025) Summary, last updated 2026-07-01, Table 1 (Gov. Code 65912.157); effective 2026-07-01",
    tier1=[dict(band="within 200 ft of the station", max_mi=200 / 5280, height_ft=95, du_ac=160, far=4.5),
           dict(band="within 1/4 mile", max_mi=0.25, height_ft=75, du_ac=120, far=3.5),
           dict(band="1/4 to 1/2 mile", max_mi=0.5, height_ft=65, du_ac=100, far=3.0)],
    affordable="11+ units: at least 7% ELI, 10% VLI or 13% LI on site; a higher local inclusionary requirement applies instead",
    density_bonus="SDBL applies on top, with SB 79 density as the base; no extra height beyond SB 79's (except 100% affordable)",
    labor="prevailing wage + skilled and trained workforce above 85 ft",
    exclusions="not on a site whose development demolishes rent-controlled housing occupied in the past 7 years (>2 units); "
               "cities may exclude very high fire zones and local historic sites until the 7th cycle",
)

DENSITY_BONUS = dict(
    vli_pct_to_bonus={5: 20, 6: 22.5, 7: 25, 8: 27.5, 9: 30, 10: 32.5, 11: 35, 12: 38.75, 13: 42.5, 14: 46.25, 15: 50},
    source="Gov. Code 65915(f)(2) as amended by AB 2345 (2020): 5% VLI -> 20%, +2.5 pts per 1% to 11% (35%), "
           "+3.75 pts per 1% to 15% (50%); the 2800 Telegraph plan set's table matches to 15%",
    ab1287_additional_vli_pct_to_bonus={5: 20, 6: 23.75, 7: 27.5, 8: 31.25, 9: 35, 10: 38.75},
    ab1287_source="AB 1287 (eff. 2024-01-01), Gov. Code 65915(v): after the 50% bonus (15% VLI), additional VLI units earn "
                  "an additional bonus; table per City of Los Angeles Planning, 2024-05-16 (data/assumptions/research/"
                  "pencil_out_research_2026-10-25.yaml)",
)


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parcels():
    meta = json.load(open(META))
    rates = {}
    for k, v in meta["euv_rates"].items():
        kind, nb = k.split("|", 1)
        rates[(kind, None if nb == "None" else nb)] = v
    rent_ix = meta["rent_index"]["by_neighborhood"]       # unrounded: the CSV's rent_factor is rounded to 4 places
    res_kinds = {"single_family", "residential_2_4", "residential_5plus"}
    rows, cats = [], {"bucket": [], "nb": [], "district": [], "fire": []}

    def cat(name, v):
        lst = cats[name]
        if v not in lst:
            lst.append(v)
        return lst.index(v)
    for r in csv.DictReader(open(CITYWIDE)):
        kind = "residential" if r["bucket"] in res_kinds else "nonresidential"
        nb = r["neighborhood"] or None
        rate = rates.get((kind, nb)) or rates.get((kind, None))
        b = float(r["building_sf"])
        euv = [round(b * rate[k], 2) for k in ("low", "base", "high")] if rate else [0, 0, 0]
        lat, lon = fnum(r["lat"]), fnum(r["lon"])
        if lat is None:
            continue
        rows.append([r["key"], r["name"], round(lat, 6), round(lon, 6), float(r["lot_sf"]), b,
                     cat("bucket", r["bucket"]), cat("nb", nb), cat("district", r["district"] or None),
                     cat("fire", r["fire_zone"] or None), int(r["landmark"] == "True"), int(r["exempt"] == "True"),
                     int(r["rental_units"]), rent_ix[nb]["factor"] if nb in rent_ix else 1.0, euv,
                     # the Python results, for colouring at load and for the parity test
                     fnum(r["z_in_lieu_base_rent_needed"]), fnum(r["z_on_site_base_rent_needed"]),
                     fnum(r["in_lieu_base_rent_needed"]), fnum(r["z_in_lieu_favorable_rent_needed"]),
                     fnum(r["z_in_lieu_base_best_stories"]), fnum(r["in_lieu_unfavorable_rent_needed"])])
    cols = ["key", "name", "lat", "lon", "lot_sf", "building_sf", "bucket", "nb", "district", "fire", "landmark", "exempt",
            "rental_units", "rent_factor", "euv", "py_z_in_lieu_base", "py_z_on_site_base", "py_in_lieu_base",
            "py_z_in_lieu_favorable", "py_z_in_lieu_base_best_stories", "py_in_lieu_unfavorable"]
    return dict(cols=cols, cats=cats, rows=rows)


def project_inputs(anchor, rec, R, con, asr, record_land, fee_mode):
    """the parsed inputs stalled_project prices, per scenario-independent field, + Python's results for parity."""
    runs = {sc: po.stalled_project(anchor, rec, R, con, asr, po.scenario(sc), use_record_land=record_land, fee_mode=fee_mode)
            for sc in po.SCENARIOS}
    b = runs["base"]
    g = lambda f: rec.get(f, {}).get("value")   # noqa: E731
    out = dict(anchor=anchor, address=rec["address"], fee_mode=fee_mode, record_land=record_land,
               ledger=[dict(field=l["field"], value=str(l["value"]), label=l["label"], source=l["source"]) for l in b["ledger"]])
    if b["verdict"] == "insufficient_data":
        out.update(verdict="insufficient_data", missing=b["missing"])
        return out
    mix = po.parse_mix(g("unit_mix"))
    gross = float(g("gross_floor_area")) if g("gross_floor_area") else None
    net_rec = float(g("net_unit_area")) if g("net_unit_area") else None
    partial = "PARTIAL" in (rec.get("gross_floor_area", {}).get("note") or "")
    out.update(units=int(g("units")), stories=int(g("stories")), lot_sf=float(g("lot_area")), mix=mix,
               gross=None if partial else gross, net_rec=net_rec, commercial=float(g("commercial_floor_area") or 0),
               affordable_text=g("affordable") or "", land=dict(assessed=b["land"]["assessed"],
               recent_transfer=b["land"]["recent_transfer"], partial_site=b["land"]["partial_site"],
               apns=b["land"]["apns"], last_documents=b["land"]["last_documents"]),
               py={sc: dict(gap=runs[sc]["gap"], yoc=runs[sc]["yoc"], need=runs[sc]["rent_mult_needed"],
                            land=runs[sc]["land_basis"], noi=runs[sc]["acct"]["noi"],
                            cost_ex_land=runs[sc]["acct"]["cost_ex_land"]) for sc in po.SCENARIOS})
    ok = {sc: runs[sc]["gap"] >= 0 for sc in po.SCENARIOS}
    out["verdict"] = "pencils" if ok["unfavorable"] else "marginal" if (ok["base"] or ok["favorable"]) else "does_not"
    return out


def parcel_points():
    return {r["name"].upper(): (float(r["lat"]), float(r["lon"])) for r in csv.DictReader(open(CITYWIDE)) if r["lat"]}


def pipeline(R):
    pts = parcel_points()
    con = sqlite3.connect(f"file:{pp.V4}?mode=ro", uri=True)
    asr = sqlite3.connect(f"file:{pp.ASSESSOR}?mode=ro", uri=True)
    loc = {a: (la, lo, st, n, pu) for a, la, lo, st, n, pu in con.execute(
        "SELECT anchor_record, latitude, longitude, status, name, proposed_units FROM v_projects")}
    filed = dict(con.execute("SELECT anchor_record, filed_date FROM v_projects"))
    out = []
    groups = [("stalled", po.RECORD_INPUTS, True), ("built", po.RECORD_INPUTS_BUILT, False)]
    for group, path, record_land in groups:
        for anchor, rec in po.record_inputs(path).items():
            fm = "legacy_ahmf" if group == "stalled" else ("iho_combo" if (filed.get(anchor) or "") >= "2023-04-01" else "legacy_ahmf")
            p = project_inputs(anchor, rec, R, con, asr, record_land, fm)
            la, lo, st, n, pu = loc.get(anchor, (None, None, None, None, None))
            if la is None:                                 # no v4 point: the parcel with the same situs address
                la, lo = pts.get(rec["address"].upper().replace(" AVE", " AVE").strip(), (None, None))
                if la is None:
                    hit = next((v for k, v in pts.items() if k.startswith(rec["address"].upper().split(" ")[0] + " ")
                                and rec["address"].upper().split(" ")[1] in k), (None, None))
                    la, lo = hit
            p.update(group=group, lat=la, lon=lo, v4_status=st, filed=filed.get(anchor))
            out.append(p)
    rec = {"address": "2800 Telegraph Ave",
           **{k: dict(value=v, source=PLAN_2800, locator=loc_, note="") for k, (v, loc_) in REC_2800.items()}}
    p = project_inputs("ZP2022-0107", rec, R, con, asr, True, "legacy_ahmf")
    la, lo, st, n, pu = loc["ZP2022-0107"]
    p.update(group="featured", lat=la, lon=lo, v4_status=st, filed=filed["ZP2022-0107"], **EXTRA_2800,
             story=("Approved 2023-04-27 (ZAB) as 6 stories / 16 units under the State Density Bonus: 1 VLI unit bought a "
                    "27.5% bonus over a 12-unit base, plus waivers for height (70 ft vs 35 ft) and setbacks. Filed "
                    "2022-08-17 with an SB 330 preliminary application, so the pre-2023 affordable housing fee applies. "
                    "The parcel sold in Dec 2025 (assessed $1.2M). Demolition permit B2026-00307 issued 2026-07-28; "
                    "building permit application B2025-05618 is for 18 units, which is the plan set's own row for 2 VLI "
                    "units / 15% / 50% bonus (12 x 1.5 = 18). v4 still shows 'entitled' (no building permit issued)."))
    out.append(p)
    return out


def main():
    R = po.rents()
    scen = {sc: po.scenario(sc) for sc in po.SCENARIOS}
    zs, bonus = po.zoning_standards()
    keep = ("construction_tiers", "floor_to_floor_ft", "unit_size_sf", "retail_shell_cost_per_gsf_2024", "berkeley_fees",
            "bmr_rents_monthly", "construction_financing", "legacy_ahmf_per_unit", "eli_rent_share_of_vli", "height_search",
            "efficiency", "market_rent_multiplier", "exit_cap_rate_today", "yield_spread_over_exit_cap",
            "land_market_per_lot_sf", "soft_costs_ex_fees_ex_financing", "operating_expenses_share_of_egi",
            "price_year", "iho_combination")
    data = dict(
        generated=date.today().isoformat(), assumptions_file=po.ASSUMPTIONS_FILE.name, citywide_file=CITYWIDE.name,
        A={k: A[k] for k in keep},
        consts=dict(esc=po.ESC_2024_TO_PRICE_YEAR, vacancy=pp.VACANCY, retail_rent=pp.RETAIL_RENT,
                    retail_vacancy=pp.RETAIL_VACANCY, retail_expenses=pp.RETAIL_EXPENSES),
        scenarios=scen, R=R,
        zoning=dict(districts={k: {f: v.get(f) for f in ("district", "residential", "ground", "lot_coverage", "max_height_ft",
                                                             "max_stories", "far_max", "density_max", "local_bonus", "source", "note")}
                               for k, v in zs.items()}, state_bonus=bonus),
        bart=BART, sb79=SB79, density_bonus=DENSITY_BONUS,
        parcels=parcels(), pipeline=pipeline(R),
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, open(OUT, "w"), separators=(",", ":"), default=str)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB): {len(data['parcels']['rows']):,} parcels, "
          f"{len(data['pipeline'])} pipeline projects")


# Run: python3 scripts/v4/export_game_data.py && node scripts/v4/pencil_js_parity.mjs
if __name__ == "__main__":
    main()
