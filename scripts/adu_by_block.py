#!/usr/bin/env python3
"""adu_by_block.py — count ADUs per census block and validate against the HCD APR oracle.

Assigns the derived ADU cohort (data/processed/adu_mh_cohort.csv) and the APR's official ADU list
to 2020 Census blocks (TIGER, downloaded on first run), then reports the per-block distribution and
how well our count tracks the APR (correlation, exact matches, mean abs diff). Census blocks are the
unique-block-number answer (15-digit GEOID); they close on ANY feature (streets/water/boundary), so
incomplete-street-perimeter blocks aren't a problem. NOTE: block-level parity is capped by parcel-
centroid geocoding precision — the APR's own points are better, but the APR is the oracle, never a
data source. Requires geopandas + shapely.
"""
import geopandas as gpd, pandas as pd, sqlite3, requests, io, zipfile, os, warnings, sys
warnings.filterwarnings("ignore")
SCR = os.environ.get("ADU_BLOCK_CACHE", "scratch/adu_block_cache")
os.makedirs(SCR, exist_ok=True)
SHP = f"{SCR}/tl_2020_06001_tabblock20.shp"

def blocks_gdf():
    if not os.path.exists(SHP):
        url = "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/06_CALIFORNIA/06001/tl_2020_06001_tabblock20.zip"
        zipfile.ZipFile(io.BytesIO(requests.get(url, timeout=180, headers={"User-Agent": "Mozilla/5.0"}).content)).extractall(SCR)
    return gpd.read_file(SHP).to_crs(4326).cx[-122.335:-122.225, 37.84:37.91]

def assign(df, blocks):
    g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326)
    return gpd.sjoin(g, blocks[["GEOID20", "geometry"]], predicate="within", how="left").dropna(subset=["GEOID20"]).groupby("GEOID20").size()

def main():
    blocks = blocks_gdf()
    ours = pd.read_csv("data/processed/adu_mh_cohort.csv")
    ours = ours[ours.type == "ADU"]
    ours_per = assign(ours, blocks)
    con = sqlite3.connect("databases/hcd_apr_mirror.db")
    apr = pd.read_sql("SELECT DISTINCT APN,LATITUDE lat,LONGITUDE lon FROM table_a2 WHERE UNIT_CAT='ADU' AND LATITUDE!='' GROUP BY APN", con)
    apr["lat"] = pd.to_numeric(apr.lat, errors="coerce"); apr["lon"] = pd.to_numeric(apr.lon, errors="coerce")
    apr_per = assign(apr.dropna(), blocks)
    cmp = pd.DataFrame({"apr": apr_per, "ours": ours_per}).fillna(0).astype(int)
    print(f"ADUs mapped:  ours={int(ours_per.sum())}  APR={int(apr_per.sum())}")
    print(f"blocks with >=2 ADUs (ours): {(ours_per>=2).sum()}   max on a block: {int(ours_per.max())}")
    print(f"vs APR:  correlation={cmp.apr.corr(cmp.ours):.3f}  exact-match={int((cmp.apr==cmp.ours).sum())}/{len(cmp)}  mean-abs-diff={(cmp.apr-cmp.ours).abs().mean():.2f}")
    ours_per.rename("adus").to_csv("data/processed/adu_by_block.csv")
    print("  per-block counts -> data/processed/adu_by_block.csv")

if __name__ == "__main__":
    main()
