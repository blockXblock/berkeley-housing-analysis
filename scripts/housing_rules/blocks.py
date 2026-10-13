r"""blocks.py -- Berkeley's street-bounded CITY BLOCKS, with IDs that survive a re-fetch.

THE SINGLE BLOCK CANON. Load blocks through load_city_blocks(); never re-explode the raw layer in a
script. Two copies of "explode, filter, number by row" would disagree the first time one changes.

SOURCE: data/raw/berkeley_gis/city_blocks.geojson (scripts/fetch_berkeley_gis.py). The City publishes
it as 'sde_prod_DBO_Right_Of_Way' -- a misleading name; it is one MultiPolygon whose parts are the
street-enclosed blocks (docs/audit/2026-09-24_berkeley_city_blocks_found.md). NOT BlocksCoB.geojson,
which is Census TIGER 2020 republished.

THE FILTER (MIN_ACRES <= area < MAX_ACRES). The raw layer holds 1,197 parts: a 5,771-acre envelope,
empty slivers, and the blocks. The 2026-09-24 audit filtered to 0.2-60 acres (1,119 blocks). Measured
2026-10-13 against the 62,226 address points, that filter drops REAL blocks:
  - two enclosed areas above 60 acres: the UC campus (177 ac, 114 address points) and the Aquatic
    Park / Bolivar Dr waterfront (107 ac, 24 points);
  - small triangular blocks of 0.11-0.17 ac that carry addresses (one holds 34 points at 1400
    Shattuck Ave).
Every part between 0.084 and 0.1 ac is empty (traffic islands). So the canon keeps 0.1 <= acres <
1000: it drops only the envelope and the empty slivers.

BLOCK IDs. 'B%04d' by row order (city_block_index.py before 2026-10-13) renumbers every later block
when one polygon changes, so a cited ID like the Acheson audit's B0210 silently moves. Instead:
  - MINT: 'CB-' + the first 8 hex of SHA-1 over the polygon's centroid rounded to 1 m in EPSG:32610.
    A new or edited polygon changes only its own ID.
  - CARRY FORWARD: given the previous registry (block_id + a point guaranteed inside each block), a
    new polygon containing exactly one old point INHERITS that ID, so a slight re-digitising that
    moves the centroid does not re-mint. Merged or split blocks re-mint, which is correct: they are
    different blocks.
The registry (block_id, rep_x, rep_y in EPSG:32610) is what makes IDs durable; keep it with the data.

EDGE BLOCKS (kind='edge'). The City layer is street-ENCLOSED land only, so the lots between the last
street and the city limit -- closed off by the Oakland/Albany/Kensington line, not by a street -- have
no polygon. Measured 2026-10-13: 2,597 of 62,226 address points (4%) lay in no block, almost all of
them in that ring. The 5,771-acre "envelope" part is the street-enclosed extent (blocks + streets), so
  edge = city land - envelope - enclosed blocks, exploded, same acre filter.
City land = the union of the Census 2020 blocks (CITY_OUTLINE), used ONLY for the city-limit line,
never as blocks. Streets leaving the city cut the ring into block-sized pieces (median 2.8 ac), but
where none cross, one edge block runs long (a 268-acre hills strip holds 349 address points).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BLOCKS = ROOT / "data/raw/berkeley_gis/city_blocks.geojson"
CRS = 32610            # UTM 10N, metres
ACRE_M2 = 4046.86
MIN_ACRES = 0.1
MAX_ACRES = 1000.0
CITY_OUTLINE = ROOT / "data/processed/berkeley_blocks_2020.geojson"


def mint_block_id(geom) -> str:
    c = geom.centroid
    key = f"{round(c.x)},{round(c.y)}"
    return "CB-" + hashlib.sha1(key.encode()).hexdigest()[:8]


def explode_blocks(path=BLOCKS):
    """Every part of the raw layer, in EPSG:32610, with acres. No filter, no IDs."""
    import geopandas as gpd
    g = gpd.read_file(path).to_crs(CRS).explode(index_parts=False).reset_index(drop=True)
    g["acres"] = g.geometry.area / ACRE_M2
    return g[["acres", "geometry"]]


def load_city_blocks(path=BLOCKS, registry=None, include_edge=True, outline=CITY_OUTLINE):
    """The city blocks (EPSG:32610): block_id, kind ('enclosed' | 'edge'), acres, rep_x, rep_y,
    id_source ('minted' | 'inherited'), geometry. `registry` = a previous registry DataFrame
    (block_id, rep_x, rep_y)."""
    import geopandas as gpd
    import pandas as pd
    raw = explode_blocks(path)
    g = raw[(raw.acres >= MIN_ACRES) & (raw.acres < MAX_ACRES)].copy()
    g["kind"] = "enclosed"
    if include_edge:
        envelope = raw[raw.acres >= MAX_ACRES].geometry.union_all()
        land = gpd.read_file(outline).to_crs(CRS).geometry.union_all()
        e = gpd.GeoDataFrame(geometry=[land.difference(envelope).difference(g.geometry.union_all())],
                             crs=CRS).explode(index_parts=False)
        e["acres"] = e.geometry.area / ACRE_M2
        e = e[e.acres >= MIN_ACRES]
        e["kind"] = "edge"
        g = pd.concat([g, e[["acres", "geometry", "kind"]]])
    g = gpd.GeoDataFrame(g.reset_index(drop=True), geometry="geometry", crs=CRS)
    g["block_id"] = [mint_block_id(x) for x in g.geometry]
    g["id_source"] = "minted"
    if registry is not None and len(registry):
        old = gpd.GeoDataFrame(registry[["block_id"]].rename(columns={"block_id": "old_id"}),
                               geometry=gpd.points_from_xy(registry.rep_x, registry.rep_y), crs=CRS)
        hit = gpd.sjoin(old, g[["geometry"]], predicate="within")
        one = hit.groupby("index_right").filter(lambda d: len(d) == 1)
        g.loc[one.index_right, "block_id"] = one.old_id.values
        g.loc[one.index_right, "id_source"] = "inherited"
    if g.block_id.duplicated().any():
        raise ValueError(f"block_id collision: {g.block_id[g.block_id.duplicated()].tolist()}")
    rp = g.geometry.representative_point()
    g["rep_x"], g["rep_y"] = rp.x.round(1), rp.y.round(1)
    return g[["block_id", "kind", "acres", "rep_x", "rep_y", "id_source", "geometry"]]


def legacy_row_ids(path=BLOCKS):
    """The pre-2026-10-13 'B%04d' IDs (0.2-60 ac filter, numbered by row) -- for the crosswalk only."""
    g = explode_blocks(path)
    g = g[(g.acres > 0.2) & (g.acres < 60)].reset_index(drop=True)
    g["legacy_id"] = ["B%04d" % i for i in range(len(g))]
    return g[["legacy_id", "geometry"]]
