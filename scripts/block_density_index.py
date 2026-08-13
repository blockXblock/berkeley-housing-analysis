#!/usr/bin/env python3
"""block_density_index.py — Berkeley block-by-block housing-density index + corridor comparison.

The durable, re-runnable core of the 2026-08 corridor-density investigation (JN-M). Existing
housing stock = Census 2020 PL 94-171 (population P1_001N, housing units H1_001N) joined to TIGER
2020 block geometry on GEOID20; recent adds = our fixed-classifier ADU cohort. Density = units per
LAND acre (ALAND20). Corridors are defined at the city's own boundaries (College = Dwight→Alcatraz,
matching the Corridors Zoning Update); College is split East/West of the avenue centerline.

Inputs (committed, small — the reproducible base):
  data/processed/berkeley_blocks_2020.geojson   (1,522 Berkeley blocks: GEOID20, pop, housing_units,
                                                 ALAND20, acres, dua, ppa)
  data/processed/adu_mh_cohort.csv              (our geocoded ADU cohort)
  databases/berkeley.db                          (parcels: SitusAddre/Lat/Lon — corridor street match)

Heavy raw inputs (NOT committed; documented for provenance — re-fetch to rebuild the geojson):
  Census 2020 PL: www2.census.gov/.../California/ca2020.pl.zip  (76 MB; P1_001N seg1 field[5],
                  H1_001N seg2 field[-3]; SUMLEV 750 blocks; verified vs Berkeley pop 124,321)
  TIGER 2020:     tl_2020_06001_tabblock20.shp (Alameda blocks) + tl_2020_06_place20 (Berkeley bound)

Zoning caps (indicative "vs zoned", from CZU Existing Conditions Report; per-parcel zoning itself is
NOT here — Berkeley zoning is form-based, and the per-parcel layer is harvested via Accela ACA, not
Socrata, which WAF-blocks us): R-1≈8.7, R-2≈17, R-2A=26.4 du/ac; R-3/R-4/commercial = no du/ac cap.

Usage:  python scripts/block_density_index.py           # rebuild index + print corridor comparison
        from scripts.block_density_index import build    # -> GeoDataFrame with corridor tags
"""
import sqlite3, re, json, warnings
import numpy as np, pandas as pd, geopandas as gpd
warnings.filterwarnings("ignore")

BLOCKS = "data/processed/berkeley_blocks_2020.geojson"
COHORT = "data/processed/adu_mh_cohort.csv"
PARCELS_DB = "databases/berkeley.db"
# city-documented corridor boundary latitudes (verified from parcel situs): Dwight 37.866, Alcatraz 37.851
DWIGHT, ALCATRAZ = 37.866, 37.851
# CURRENT regime = the Middle Housing Ordinance (7,978-N.S., effective 2026-11-01 [Nov 1 2025]): up to
# 8 units by-right on a typical 5,000 sf residential lot (3 stories / 35 ft), applies to ALL primarily-
# residential Berkeley EXCEPT high fire-hazard hill areas. This SUPERSEDES the old R-1/R-2/R-2A/R-3/R-4
# du/ac caps (8.7/17/26/…), which are obsolete — do NOT benchmark against them.
MH_BYRIGHT_DU_AC = 8.0 / (5000.0 / 43560.0)   # ≈ 69.7 du/ac (8 units / 5,000 sf lot), by-right
# corridors whose fabric is primarily residential (MH-applicable); University/Telegraph are commercial
# corridors with their own standards, so the MH residential allowance is not the right benchmark there.
MH_RESIDENTIAL = {"College (Elmwood)", "Solano", "Adeline"}

def _f(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def _street(addr):
    m = re.match(r"\s*\d+[A-Z]?\s+(.*)", str(addr).upper())
    if not m: return ""
    return re.sub(r"\b(AVE|AVENUE|ST|STREET|WAY|BLVD|RD|DR|PL|CT|LN|TER|CIR)\b.*$", "", m.group(1)).strip()

def _college_spine(bd):
    """linear fit lon = f(lat) from College Ave parcels (the avenue centerline in Elmwood)."""
    pts = [(_f(la), _f(lo)) for _, la, lo in bd.execute(
        "SELECT SitusAddre,Latitude,Longitude FROM parcels WHERE UPPER(SitusAddre) LIKE '% COLLEGE%' AND Latitude IS NOT NULL")]
    pts = [(la, lo) for la, lo in pts if la and lo and 37.848 < la < 37.872]
    m, b = np.polyfit([p[0] for p in pts], [p[1] for p in pts], 1)
    return (lambda lat: m * lat + b)

def build():
    """Return the Berkeley block GeoDataFrame with corridor tags + ADU adds (EPSG:4326)."""
    blk = gpd.read_file(BLOCKS).to_crs(4326)
    if "acres" not in blk:  blk["acres"] = blk["ALAND20"] / 4046.8564224
    if "dua" not in blk:    blk["dua"] = blk["housing_units"] / blk["acres"]
    blk["clon"] = blk.geometry.centroid.x
    blk["clat"] = blk.geometry.centroid.y

    bd = sqlite3.connect(PARCELS_DB)
    clon = _college_spine(bd)
    # College corridor = blocks within 250 m of the avenue, Dwight->Alcatraz; split E/W of centerline
    blk["d_spine"] = (blk.clon - blk.clat.map(clon)).abs() * 111320 * np.cos(np.radians(blk.clat))
    blk["corridor"] = None
    coll = (blk.d_spine <= 250) & (blk.clat <= DWIGHT) & (blk.clat >= ALCATRAZ)
    blk.loc[coll, "corridor"] = "College (Elmwood)"
    blk["college_side"] = np.where(coll, np.where(blk.clon > blk.clat.map(clon), "East", "West"), None)
    # other corridors by parcel street-name -> containing block
    par = pd.read_sql("SELECT SitusAddre,Latitude,Longitude FROM parcels WHERE Latitude IS NOT NULL", bd)
    par["s"] = par.SitusAddre.map(_street)
    gp = gpd.sjoin(gpd.GeoDataFrame(par, geometry=gpd.points_from_xy(par.Longitude, par.Latitude), crs=4326),
                   blk[["GEOID20", "geometry"]], predicate="within", how="inner")
    for key, label in {"UNIVERSITY": "University", "ADELINE": "Adeline",
                       "TELEGRAPH": "Telegraph", "SOLANO": "Solano"}.items():
        ids = set(gp.loc[gp.s == key, "GEOID20"])
        blk.loc[blk.corridor.isna() & blk.GEOID20.isin(ids), "corridor"] = label

    if "adu_adds" not in blk:
        adu = pd.read_csv(COHORT); adu = adu[adu.lat.notna()]
        gadu = gpd.sjoin(gpd.GeoDataFrame(adu, geometry=gpd.points_from_xy(adu.lon, adu.lat), crs=4326),
                         blk[["GEOID20", "geometry"]], predicate="within", how="inner")
        blk = blk.merge(gadu.groupby("GEOID20").size().rename("adu_adds"), on="GEOID20", how="left")
        blk["adu_adds"] = blk["adu_adds"].fillna(0).astype(int)
    return blk

def corridor_summary(blk):
    """Per-corridor derived figures (du/ac, pop/ac, ADU/ac, % of indicative zoned cap)."""
    rows = []
    def agg(mask, name, extra=None):
        s = blk[mask]; hu = s.housing_units.sum(); ac = s.acres.sum(); dua = hu / ac
        res = name.strip() in MH_RESIDENTIAL
        r = dict(cohort=name, blocks=int(len(s)), acres=round(ac, 1), units=int(hu),
                 du_per_ac=round(dua, 2), ppl_per_ac=round(s["pop"].sum() / ac, 2),
                 adu_adds=int(s.adu_adds.sum()), adu_per_ac=round(s.adu_adds.sum() / ac, 3),
                 # headroom under Middle Housing: existing density as a share of the ~70 du/ac by-right
                 # allowance (residential corridors only; N/A on commercial corridors)
                 pct_of_mh=(round(100 * dua / MH_BYRIGHT_DU_AC, 1) if res else None))
        if extra: r.update(extra)
        rows.append(r)
    for c in ["College (Elmwood)", "Telegraph", "Adeline", "University", "Solano"]:
        agg(blk.corridor == c, c)
    # College East/West split
    agg((blk.corridor == "College (Elmwood)") & (blk.college_side == "West"), "  College West")
    agg((blk.corridor == "College (Elmwood)") & (blk.college_side == "East"), "  College East")
    agg(blk.corridor.isna(), "Rest of Berkeley")
    agg(blk.GEOID20.notna(), "ALL Berkeley")
    return pd.DataFrame(rows)

def figures(blk):
    """The load-bearing derived figures, for the baseline gate (derive, never hardcode)."""
    s = corridor_summary(blk).set_index("cohort")
    g = lambda k, f="du_per_ac": float(s.loc[k, f])
    return {
        "n_blocks": int(len(blk)),
        "total_housing_units": int(blk.housing_units.sum()),
        "total_pop": int(blk["pop"].sum()),
        "citywide_du_per_ac": round(float(blk.housing_units.sum() / blk.acres.sum()), 2),
        "citywide_median_block_dua": round(float(blk.dua.median()), 2),
        "college_elmwood_du_per_ac": g("College (Elmwood)"),
        "college_west_du_per_ac": g("  College West"),
        "college_east_du_per_ac": g("  College East"),
        "college_elmwood_adu_adds": int(s.loc["College (Elmwood)", "adu_adds"]),
        "college_east_adu_adds": int(s.loc["  College East", "adu_adds"]),
        "college_west_adu_adds": int(s.loc["  College West", "adu_adds"]),
        # current-regime benchmark: Middle Housing by-right allowance + College-Elmwood's utilization
        "mh_byright_du_per_ac": round(MH_BYRIGHT_DU_AC, 1),
        "college_elmwood_pct_of_mh": round(100 * g("College (Elmwood)") / MH_BYRIGHT_DU_AC, 1),
    }

if __name__ == "__main__":
    blk = build()
    pd.set_option("display.width", 170)
    print(corridor_summary(blk).to_string(index=False))
    print("\nfigures:", json.dumps(figures(blk), indent=2))
