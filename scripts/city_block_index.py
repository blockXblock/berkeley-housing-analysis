#!/usr/bin/env python3
"""city_block_index.py — density and floor-area index on Berkeley's REAL city blocks.

Supersedes the block half of block_density_index.py, which used CENSUS tabulation blocks.
Those are not street-enclosed blocks: they merge across streets and split on tract lines, so
their size varies 14.8x between p10 and p90 against 3.3x for real blocks. Per-ACRE figures
were unaffected (district totals are partition-independent); per-BLOCK figures were not.
See docs/audit/2026-09-24_berkeley_city_blocks_found.md.

INPUTS
  data/raw/berkeley_gis/city_blocks.geojson   City of Berkeley, via scripts/fetch_berkeley_gis.py
      ⚠ published as 'sde_prod_DBO_Right_Of_Way'; one MultiPolygon of 1,197 parts, of which one
        is a 5,771-acre envelope and some are slivers. FILTERED to 0.2-60 acres -> 1,119 blocks.
  data/raw/overture_buildings_berkeley_2026-08-19.parquet   62,651 footprints, WKT, 71% with height
  databases/berkeley.db  addresses_arcgis (LotSqft/BldgSqft/UseCode/OwnerName per APN)
  data/raw/rent_board/... (rent-board units -- rent-CONTROLLED only, a biased sample, not a census)

WHAT IS AND IS NOT TRUSTWORTHY HERE
  - BldgSqft is TOTAL FLOOR AREA, not footprint. Verified: 1,057 parcels exceed their lot area and
    2047 Allston reads 203,789 sf on a 10,670 sf lot. So parcel FAR = BldgSqft / LotSqft is a real
    FAR -- but its TAIL IS JUNK. 12 parcels read FAR>5 and five are UseCode 9500 institutional
    parking or unit-suffixed fractional interests where the lot is a share and the floor area is
    the whole building. NEVER calibrate an achievable-FAR ceiling from the observed maximum.
  - Overture gives true 2D FOOTPRINT, so block coverage is MEASURED, not assumed.
  - implied_stories = floor_area / footprint is a CHECK on both, not a published figure.

Usage: .venv/bin/python scripts/city_block_index.py
"""
import os, sqlite3, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, geopandas as gpd
from shapely import wkt as shapely_wkt

BLOCKS = "data/raw/berkeley_gis/city_blocks.geojson"
OVT    = "data/raw/overture_buildings_berkeley_2026-08-19.parquet"
DB     = "databases/berkeley.db"
NEIGH  = "data/reference/berkeley_neighborhoods.geojson"
OUT    = "data/derived/city_block_index.geojson"
M2SF   = 10.7639
AC     = 4046.86


def load_blocks():
    g = gpd.read_file(BLOCKS).to_crs(32610).explode(index_parts=False).reset_index(drop=True)
    g["acres"] = g.geometry.area / AC
    n0 = len(g)
    g = g[(g.acres > 0.2) & (g.acres < 60)].reset_index(drop=True)   # drop envelope + slivers
    g["block_id"] = ["B%04d" % i for i in range(len(g))]
    print(f"  blocks: {n0} parts -> {len(g)} after the 0.2-60 acre filter")
    return g[["block_id", "acres", "geometry"]]


def load_footprints():
    d = pd.read_parquet(OVT)
    d = d[d.wkt.notna()].copy()
    g = gpd.GeoDataFrame(d, geometry=d.wkt.map(shapely_wkt.loads), crs=4326).to_crs(32610)
    g["foot_sf"] = g.geometry.area * M2SF
    g = g[(g.foot_sf > 60) & (g.foot_sf < 2_000_000)]
    print(f"  footprints: {len(g):,} usable, {g.height.notna().mean()*100:.0f}% with height")
    return g[["foot_sf", "height", "num_floors", "geometry"]]


def load_parcels():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    p = pd.read_sql("""select apn_norm, U_X, U_Y, LotSqft, BldgSqft, UseCode, OwnerName
                       from addresses_arcgis where U_X is not null and apn_norm is not null
                       group by apn_norm""", con)
    num = lambda s: pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce")
    p["lot_sf"], p["floor_sf"] = num(p.LotSqft), num(p.BldgSqft)
    own = p.OwnerName.fillna("").str.upper()
    p["owner_class"] = np.select(
        [own.str.contains("CHURCH|PRESBY|CATHOLIC|TEMPLE|PARISH|MINISTR|CONGREGAT|EPISCOPAL|LUTHERAN|METHODIST|BAPTIST"),
         own.str.contains("REGENTS|UNIVERSITY OF CALIF"),
         own.str.startswith("CITY OF BERKELEY"),
         own.str.contains("SCHOOL DIST|UNIFIED"),
         own.str.contains("BART|RAPID TRANSIT"),
         own.str.contains("STATE OF CALIF|UNITED STATES|COUNTY OF ALAMEDA|POSTAL SERV")],
        ["religious", "uc_regents", "city", "school_district", "bart", "other_government"],
        default="private")
    g = gpd.GeoDataFrame(p, geometry=gpd.points_from_xy(p.U_X, p.U_Y), crs=32610)
    print(f"  parcels: {len(g):,} geocoded")
    return g


def main():
    print("building the city-block index\n")
    blocks, foot, parc = load_blocks(), load_footprints(), load_parcels()

    # footprints -> blocks by intersection area (a building can straddle; assign by overlap)
    fb = gpd.overlay(foot[["foot_sf", "height", "geometry"]], blocks[["block_id", "geometry"]],
                     how="intersection", keep_geom_type=True)
    fb["piece_sf"] = fb.geometry.area * M2SF
    fa = fb.groupby("block_id").agg(footprint_sf=("piece_sf", "sum"),
                                    buildings=("piece_sf", "size"),
                                    median_height_m=("height", "median"))

    # parcels -> blocks by point-in-polygon
    pb = gpd.sjoin(parc, blocks[["block_id", "geometry"]], how="inner", predicate="within")
    pa = pb.groupby("block_id").agg(parcels=("apn_norm", "size"),
                                    lot_sf=("lot_sf", "sum"),
                                    floor_sf=("floor_sf", "sum"))
    own = (pb.groupby(["block_id", "owner_class"]).size().unstack(fill_value=0)
             .rename(columns=lambda c: "n_" + c))

    b = blocks.set_index("block_id").join([fa, pa, own]).fillna(
        {"footprint_sf": 0, "buildings": 0, "parcels": 0, "lot_sf": 0, "floor_sf": 0})
    b["block_sf"]  = b.acres * AC * M2SF
    b["coverage"]  = (b.footprint_sf / b.block_sf).clip(0, 1)
    b["far_block"] = b.floor_sf / b.block_sf
    b["implied_stories"] = np.where(b.footprint_sf > 0, b.floor_sf / b.footprint_sf, np.nan)

    nb = gpd.read_file(NEIGH).to_crs(32610)[["Name", "geometry"]]
    b = gpd.GeoDataFrame(b.reset_index(), geometry="geometry", crs=32610)
    b = gpd.sjoin(b, nb, how="left", predicate="within").drop(columns="index_right")

    os.makedirs("data/derived", exist_ok=True)
    b.to_crs(4326).to_file(OUT, driver="GeoJSON")

    print(f"\n  wrote {OUT}: {len(b):,} blocks")
    print(f"\n  {'metric':22}{'median':>10}{'p25':>9}{'p75':>9}{'p95':>9}")
    for c, lab in [("acres", "block acres"), ("parcels", "parcels/block"),
                   ("coverage", "footprint coverage"), ("far_block", "block FAR"),
                   ("implied_stories", "implied stories")]:
        s = b[c].replace([np.inf, -np.inf], np.nan).dropna()
        print(f"  {lab:22}{s.median():>10.2f}{s.quantile(.25):>9.2f}{s.quantile(.75):>9.2f}{s.quantile(.95):>9.2f}")
    print(f"\n  blocks with any institutional parcel: "
          f"{int((b[[c for c in b.columns if c.startswith('n_') and c != 'n_private']].sum(axis=1) > 0).sum()):,}")


if __name__ == "__main__":
    main()
