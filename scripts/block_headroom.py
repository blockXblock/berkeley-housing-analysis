#!/usr/bin/env python3
"""block_headroom.py — MAXIMUM housing headroom by census block: the theoretical zoning-envelope
capacity to ADD units to Berkeley's existing housing, block by block.

Headroom (John's definition) = the maximum number of units that could be ADDED to existing housing
in a block = full zoning-envelope capacity (demolish-and-rebuild to the allowed maximum) − existing
units. This is a CAPACITY / envelope figure, NOT a forecast of what will be built (feasibility is a
separate, calibration-dominated question — see JN-Feasibility). It answers "how much does zoning
allow on top of what's there," which is the ceiling any production estimate sits under.

FOUNDATION (established, not invented here):
  • development_potential (berkeley.db, 41 zones): per-zone base_units_5000sqft, max_stories,
    middle_housing_eligible. Encodes the Middle Housing Ordinance (7,978-N.S., eff. 2026-11-01):
    up to 8 units by-right on a 5,000 sf residential lot (3 stories/35 ft), ALL flatland residential
    EXCEPT high fire-hazard hills (the H-zones carry middle_housing_eligible=0 in the table).
  • parcel_zones (29,024 parcels): apn_norm → zone_class.
  • parcels (berkeley.db): LotSize (sq ft), Latitude/Longitude (→ containing block).
  • berkeley_blocks_2020.geojson (1,522 blocks): existing housing_units (Census 2020), acres.

PER-PARCEL MAX CAPACITY under the current regime, by zone family:
  A) FLAT-DENSITY zones (base_units_5000sqft is set: R-1/R-2/R-2A/MUR=8 [MH by-right]; hillside
     R-2H/R-2AH=2, R-1H/ES-R=1 [MH-restricted, fire]):   cap = base × LotSize/5000   (rounded).
        → For the MH zones this is exactly the 8-per-5,000-sf (=69.7 du/ac) by-right allowance,
          scaling with lot size (a 10,000 sf lot → 16), consistent with block_density_index.py.
  B) DENSITY-BY-LOT zones (base is NULL, "no unit cap," height-governed: R-3/R-4/R-5/R-S/R-SMU/
     R-BMU + all C-* commercial/mixed-use):  cap = LotSize × COVERAGE × max_stories / UNIT_SF.
        → ASSUMPTION-SENSITIVE (calibration-dominated). COVERAGE + UNIT_SF are stated below and are
          the knobs to calibrate. Reported in a SEPARATE column so the soft number never contaminates
          the solid MH number.
  C) NO-HOUSING zones (M/MM/MRD/U/X, max_stories NULL): cap = 0.

block_capacity = Σ parcel cap ;  headroom = max(0, block_capacity − existing_units).
The MAX assumes redevelopment (demolish existing to rebuild to envelope), exactly as John framed it
("or demolish and add multiunits") — so existing units are subtracted at the BLOCK level.

Read-only. Output: data/reference/block_headroom.csv (per block) + data/reference/
neighborhood_headroom.csv (rollup). Run: /opt/miniconda3/envs/jupyter_env/bin/python scripts/block_headroom.py
(or the repo .venv with geopandas).
"""
import sqlite3, warnings
import numpy as np, pandas as pd, geopandas as gpd
warnings.filterwarnings("ignore")

BLOCKS = "data/processed/berkeley_blocks_2020.geojson"
DB = "databases/berkeley.db"
NEIGH = "data/reference/berkeley_neighborhoods.geojson"

# --- STATED ASSUMPTIONS (the knobs) ------------------------------------------------------------
# Middle Housing Ordinance 7,978-N.S. (eff. 2026-11-01) is a FLAT PER-LOT CAP, verified 2026-08-27
# against the ordinance + city/advocacy explainers: up to 8 units by-right on a residential lot, up to
# 12 with the density bonus, plus ADUs (uncounted) — NOT a lot-size-scaling density. So per-lot cap is
# a CONSTANT, not base×lot/5000 (the linear reading fabricated 1,300 units on an 18-ac parcel).
MH_BYRIGHT_CAP = 8            # units/lot by-right on an MH-eligible flatland-residential lot
MH_BONUS_CAP = 12            # units/lot with the state density bonus
COVERAGE = 0.60               # ASSUMED lot coverage for height-governed (R-3+/C-*) massing (SOFT)
UNIT_SF = 1000.0              # ASSUMED gross sf/unit incl. circulation, height-governed zones (SOFT)
SF_PER_5000 = 5000.0
# ------------------------------------------------------------------------------------------------


def apn_key(apn):
    """12-char zone-join key, PARSED FROM THE APN STRING (not the NULL-prone component cols — 3,025
    parcels have a null PARCEL split). book(3)+page(4)+parcel(3)+sub(2), matching parcel_zones.apn_norm.
    Letter-book APNs (48A/48H, ~25) return None — they aren't in the all-numeric parcel_zones anyway.
    Verified 2026-08-27: 98.6% of parcels match parcel_zones via this key (digits-only zfill → 0%)."""
    segs = str(apn).strip().split("-")
    if len(segs) < 3:
        return None
    book, page, parcel = segs[0], segs[1], segs[2]
    sub = segs[3] if len(segs) > 3 else "0"
    if not (book.isdigit() and page.isdigit() and parcel.isdigit() and sub.isdigit()):
        return None
    return f"{int(book):03d}{int(page):04d}{int(parcel):03d}{int(sub):02d}"


def existing_units_est(usecode):
    """Estimate current units on a parcel from the Alameda assessor UseCode (CLAUDE.md: 1xxx=SFR,
    2xxx=small old duplex). Coarse but real; used only to net the ADDABLE units (cap − existing)."""
    return 2 if str(usecode).strip()[:1] == "2" else 1


def parcel_capacity(zone_row, lot_sf, usecode):
    """Max ADDABLE units on one parcel under the current regime. Returns (net_add, family).
    MH-eligible lots use the FLAT by-right cap; height-governed lots use a (soft) massing envelope."""
    base = zone_row["base_units_5000sqft"]
    stories = zone_row["max_stories"]
    ex = existing_units_est(usecode)
    if pd.notna(base):                                   # A) flat-density (small-lot fabric)
        if zone_row["middle_housing_eligible"] == 1:     #    MH-eligible: flat 8-by-right cap
            return max(0, MH_BYRIGHT_CAP - ex), "mh_flat"
        return max(0, int(base) - ex), "restricted_flat"  #   hillside/fire: keep limited base (1-2)
    if pd.notna(stories) and stories > 0:                # B) density-by-lot / commercial (height env.)
        return max(0, lot_sf * COVERAGE * stories / UNIT_SF - ex), "height_governed"
    return 0.0, "no_housing"                             # C) no housing


def build():
    b = sqlite3.connect(DB)
    dp = pd.read_sql("SELECT * FROM development_potential", b).set_index("zone_class")
    pz = pd.read_sql("SELECT apn_norm, zone_class FROM parcel_zones", b)
    # LotSize is empty in the refreshed assessor table (only 73/29k populated) — derive lot area from
    # the parcel geometry instead (the_geom, WGS84; projected to EPSG:26910 for m² → sq ft).
    par = pd.read_sql("SELECT APN, UseCode, Latitude, Longitude, the_geom FROM parcels "
                      "WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL AND the_geom IS NOT NULL", b)
    from shapely import wkt as _wkt
    geom = gpd.GeoSeries([_wkt.loads(g) for g in par.the_geom], crs=4326).to_crs(26910)
    par["LotSize"] = (geom.area.values * 10.7639)   # m² → sq ft
    par = par.drop(columns=["the_geom"])
    # join parcel -> its zone via the segment-padded key parsed from the APN STRING (see apn_key).
    par["apn_norm"] = par.APN.map(apn_key)
    pz["apn_norm"] = pz.apn_norm.astype(str)
    par = par.merge(pz, on="apn_norm", how="left")
    par["LotSize"] = pd.to_numeric(par.LotSize, errors="coerce")

    # per-parcel ADDABLE units (net of estimated existing). 'add' = by-right; 'add_bonus' applies the
    # 12-unit density-bonus cap to MH-eligible lots (others identical to by-right).
    adds, adds_bonus, fams = [], [], []
    dp_d = dp.to_dict("index")
    for _, r in par.iterrows():
        zc = r["zone_class"]; lot = r["LotSize"]; uc = r["UseCode"]
        if pd.isna(zc) or zc not in dp_d or pd.isna(lot) or lot <= 0:
            adds.append(0.0); adds_bonus.append(0.0); fams.append("unknown"); continue
        a, f = parcel_capacity(dp_d[zc], lot, uc)
        adds.append(a); fams.append(f)
        # density-bonus variant: MH-eligible lots ONLY, up to 12 by-right (0 elsewhere — this column
        # isolates the MH lever's bonus scenario, not a whole-block total).
        adds_bonus.append(max(0, MH_BONUS_CAP - existing_units_est(uc)) if f == "mh_flat" else 0)
    par["add"] = adds; par["add_bonus"] = adds_bonus; par["family"] = fams

    # spatial-join parcels -> blocks (point in polygon)
    blk = gpd.read_file(BLOCKS).to_crs(4326)
    if "acres" not in blk: blk["acres"] = blk.ALAND20 / 4046.8564224
    gp = gpd.sjoin(
        gpd.GeoDataFrame(par, geometry=gpd.points_from_xy(par.Longitude, par.Latitude), crs=4326),
        blk[["GEOID20", "geometry"]], predicate="within", how="inner")

    # per-block: addable units by family (each family's sum IS its headroom — netting is per-parcel)
    piv = gp.pivot_table(index="GEOID20", columns="family", values="add", aggfunc="sum", fill_value=0)
    piv["add_bonus_total"] = gp.groupby("GEOID20").add_bonus.sum()
    piv["parcels"] = gp.groupby("GEOID20").APN.nunique()
    blk = blk.merge(piv, on="GEOID20", how="left")
    for c in ["mh_flat", "restricted_flat", "height_governed", "no_housing", "unknown",
              "add_bonus_total", "parcels"]:
        if c not in blk: blk[c] = 0.0
        blk[c] = blk[c].fillna(0)

    # headroom columns (all are ADDABLE units; floor 0 already applied per-parcel)
    blk["headroom_mh_byright"] = blk["mh_flat"].round().astype(int)          # solid, ordinance flat cap
    blk["headroom_mh_bonus"] = blk["add_bonus_total"].round().astype(int)    # MH lever w/ density bonus (12/lot)
    blk["headroom_corridor_est"] = blk["height_governed"].round().astype(int)  # SOFT (height/UC caveat)
    blk["headroom_hillside"] = blk["restricted_flat"].round().astype(int)
    blk["headroom_total"] = (blk[["mh_flat", "restricted_flat", "height_governed"]].sum(axis=1)
                             ).round().astype(int)
    blk["parcels"] = blk["parcels"].astype(int)
    blk["units_per_block"] = blk.housing_units.astype(int)
    return blk


def neighborhood_rollup(blk):
    n = gpd.read_file(NEIGH).to_crs(4326)[["Name", "geometry"]]
    j = gpd.sjoin(blk.assign(geometry=blk.geometry.centroid), n, predicate="within", how="left")
    g = j.groupby("Name").agg(
        blocks=("GEOID20", "nunique"),
        parcels=("parcels", "sum"),
        existing_units=("units_per_block", "sum"),
        acres=("acres", "sum"),
        headroom_mh_byright=("headroom_mh_byright", "sum"),
        headroom_mh_bonus=("headroom_mh_bonus", "sum"),
        headroom_corridor_est=("headroom_corridor_est", "sum"),
        headroom_total=("headroom_total", "sum"),
    ).reset_index()
    g["units_per_block"] = (g.existing_units / g.blocks).round(1)
    g["mh_headroom_per_block"] = (g.headroom_mh_byright / g.blocks).round(1)
    return g.sort_values("headroom_mh_byright", ascending=False)


if __name__ == "__main__":
    blk = build()
    cols = ["GEOID20", "corridor", "acres", "parcels", "units_per_block",
            "headroom_mh_byright", "headroom_mh_bonus", "headroom_corridor_est",
            "headroom_hillside", "headroom_total"]
    cols = [c for c in cols if c in blk.columns]
    blk[cols].to_csv("data/reference/block_headroom.csv", index=False)
    roll = neighborhood_rollup(blk)
    roll.to_csv("data/reference/neighborhood_headroom.csv", index=False)

    tot_ex = int(blk.units_per_block.sum())
    print(f"blocks: {len(blk)}  parcels placed: {int(blk.parcels.sum())}")
    print(f"existing units (census 2020): {tot_ex:,}")
    print(f"MAX ADDABLE (headroom), by lever:")
    print(f"  MH by-right (8/lot flat cap, SOLID):        {int(blk.headroom_mh_byright.sum()):,}")
    print(f"  MH w/ density bonus (12/lot):               {int(blk.headroom_mh_bonus.sum()):,}")
    print(f"  height-governed corridor (SOFT, UC-caveat): {int(blk.headroom_corridor_est.sum()):,}")
    print(f"  hillside/restricted:                        {int(blk.headroom_hillside.sum()):,}")
    print(f"  TOTAL (by-right MH + corridor + hillside):  {int(blk.headroom_total.sum()):,}")
    pd.set_option("display.width", 200, "display.max_rows", 40, "display.max_colwidth", 22)
    print("\nNEIGHBORHOOD ROLLUP (by MH by-right headroom):")
    show = ["Name", "blocks", "existing_units", "units_per_block", "headroom_mh_byright",
            "headroom_mh_bonus", "headroom_corridor_est", "headroom_total"]
    print(roll[[c for c in show if c in roll.columns]].to_string(index=False))
