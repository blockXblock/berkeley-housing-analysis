#!/usr/bin/env python3
"""build_address_block_lookup.py -- every Berkeley street address and parcel -> its city block and street segment.

Two senses of "my block", both answered (John, 2026-10-13):
  BLOCK    the street-bounded land you share with your back-fence neighbors -- housing_rules.blocks
           (City polygons + edge blocks closed by the city limit), stable 'CB-' IDs.
  SEGMENT  your street between the two corners, both sides -- "the 2800 block of Benvenue Ave" -- from
           the City's Street_Centerline, matched on street name + the segment's own address range.

INPUTS (SHA-256 recorded in the provenance sidecar)
  data/reference/berkeley_addresses_with_fields.csv   City address points. latitude/longitude ONLY:
                                                      X_CORD/Y_CORD are Web Mercator.
  data/raw/berkeley_gis/city_blocks.geojson           via housing_rules.blocks
  data/raw/berkeley_gis/Street_Centerline.geojson     segment geometry, names, address ranges
  databases/berkeley.db  parcels                      assessor parcel centroids (Latitude/Longitude)
  data/reference/city_block_registry.csv              previous IDs, carried forward (written back)

OUTPUTS
  docs/data/blocks/address_block_lookup.csv   one row per street address (unit rows collapsed)
  docs/data/blocks/parcel_block_lookup.csv    one row per assessor APN
  docs/data/blocks/city_blocks.geojson        block_id, kind, block_label, acres
  docs/data/blocks/street_segments.geojson    segment_id, segment_label
  docs/data/blocks/provenance.json            inputs + SHA-256, commit, parameters, gates
  docs/data/blocks/address.py                 a VERBATIM republished copy of housing_rules/address.py, so the
                                              browser build of apps/block_units.py (which cannot import
                                              scripts/) normalizes a typed address with THE canon. Never
                                              edit it; rerun this script. Its SHA-256 must equal the source's.
  data/reference/city_block_registry.csv      block_id + interior point: what keeps IDs stable
  data/reference/legacy_block_id_crosswalk.csv  pre-2026-10-13 'B%04d' -> CB- (B0210 -> CB-27b08582)

GATES (anchored to invariants): every input point is inside + nearest + none; every assessor parcel
is accounted for the same way; block IDs unique; the corner-lot pair 1951 Shattuck / 2108 Berkeley Way
on one block. Exits non-zero on failure and writes nothing.

Usage: .venv/bin/python scripts/build_address_block_lookup.py
"""
import datetime, hashlib, json, math, shutil, sqlite3, subprocess, sys
from pathlib import Path

import numpy as np, pandas as pd, geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from housing_rules import blocks as hb                      # noqa: E402  THE block canon
from housing_rules.address import normalize_address         # noqa: E402  THE address canon (not s0_keys)
from housing_rules.apn import to_canonical_apn              # noqa: E402

CANON = ROOT / "scripts/housing_rules/address.py"
ADDR = ROOT / "data/reference/berkeley_addresses_with_fields.csv"
CENTERLINE = ROOT / "data/raw/berkeley_gis/Street_Centerline.geojson"
ASSESSOR = ROOT / "databases/berkeley.db"
REGISTRY = ROOT / "data/reference/city_block_registry.csv"
CROSSWALK = ROOT / "data/reference/legacy_block_id_crosswalk.csv"
OUT = ROOT / "docs/data/blocks"

NEAREST_MAX_M = 30.0     # a point this close to a block (the street side of a front lot line) is that block's
LABEL_BUF_M = 20.0       # half a Berkeley right-of-way plus slack: centerlines this near a block bound it
LABEL_MIN_M = 25.0       # a street must run this far along a block to name it (drops crossing stubs)
SEG_SAME_STREET_M = 60.0 # no segment's range holds the number: nearest segment of the same street within this


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def street_key(name):
    return normalize_address("1 " + str(name))[1]


# Street_Centerline and the address-point layer are two City layers that spell some streets differently.
# Reconciled HERE, for the segment join only -- a layer-to-layer spelling map, not an address rule
# (measured 2026-10-13: 988 addresses had no segment before this, 426 of them on MLK Jr Way).
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
SEGMENT_ALIASES = {"mlkingjr": "martinlutherkingjr", "virginiagdns": "virginiagardens"}


def segment_key(skey):
    """Space-free street key: LEROY == LE ROY, NORTHGATE == NORTH GATE; 'sixty 2nd' -> '62nd'."""
    w = str(skey).split()
    if len(w) >= 2 and w[0] in _TENS and w[1][:1].isdigit():
        w = [f"{_TENS[w[0]] + int(w[1][:-2])}{w[1][-2:]}"] + w[2:]
    k = "".join(w)
    return SEGMENT_ALIASES.get(k, k)


def load_centerlines():
    cl = gpd.read_file(CENTERLINE).to_crs(hb.CRS).explode(index_parts=False).reset_index(drop=True)
    cl["name"] = (cl.STREET_NAME.fillna("").str.title() + " " + cl.STREET_TYPE.fillna("").str.title()).str.strip()
    cl["skey"] = cl.FULLNAME.fillna(cl.name).map(street_key)
    cl["mkey"] = cl.skey.map(segment_key)
    return cl


def block_labels(blocks, cl):
    """'University Ave / Shattuck Ave / ...' -- the streets that bound a block, clockwise from north."""
    ring = blocks[["block_id", "geometry"]].copy()
    ring["geometry"] = ring.geometry.boundary.buffer(LABEL_BUF_M)
    pieces = gpd.overlay(cl[["name", "geometry"]], ring, how="intersection", keep_geom_type=True)
    pieces["len"] = pieces.geometry.length
    b = blocks.set_index("block_id")
    out = {}
    for bid, d in pieces.groupby("block_id"):
        agg = d.dissolve("name", aggfunc={"len": "sum"})
        agg = agg[(agg.len >= LABEL_MIN_M) & (agg.index != "Unnamed")]
        c = b.geometry[bid].centroid
        ang = {n: (math.degrees(math.atan2(g.centroid.x - c.x, g.centroid.y - c.y)) + 360) % 360
               for n, g in agg.geometry.items()}
        names = sorted(ang, key=ang.get)
        lab = " / ".join(names[:6]) + (" / ..." if len(names) > 6 else "")
        if b.kind[bid] == "edge":
            lab = (lab + " / city limit").lstrip(" /")
        out[bid] = lab
    return pd.Series(out, name="block_label")


def segments(cl):
    """Segment IDs (hash of the rounded endpoints, order-free) and labels: the hundred block plus the
    cross streets read off the OTHER centerlines that meet each end."""
    def ends(g):
        cs = list(g.coords)
        return cs[0], cs[-1]
    e = cl.geometry.map(ends)
    cl["segment_id"] = ["SG-" + hashlib.sha1(
        "|".join(sorted(f"{round(x)},{round(y)}" for x, y in pr)).encode()).hexdigest()[:8] for pr in e]
    dup = cl.segment_id.duplicated(keep=False)
    if dup.any():                                   # same endpoints twice (a divided road's two halves)
        cl.loc[dup, "segment_id"] = cl.loc[dup].groupby("segment_id").cumcount().astype(str).radd(
            cl.loc[dup, "segment_id"] + "-")
    pts = gpd.GeoDataFrame({"seg": np.repeat(cl.index.values, 2), "skey": np.repeat(cl.skey.values, 2),
                            "name": np.repeat(cl.name.values, 2)},
                           geometry=gpd.points_from_xy([p[0] for pr in e for p in pr],
                                                       [p[1] for pr in e for p in pr]), crs=hb.CRS)
    pts["end"] = np.tile([0, 1], len(cl))
    near = gpd.sjoin(pts, gpd.GeoDataFrame(pts[["seg", "skey", "name"]], geometry=pts.buffer(1.0)),
                     predicate="within", lsuffix="a", rsuffix="b")
    near = near[(near.seg_a != near.seg_b) & (near.skey_a != near.skey_b) & (near.name_b != "Unnamed")]
    cross = near.groupby(["seg_a", "end"]).name_b.agg(lambda s: " / ".join(sorted(set(s))))
    lo = cl[["F_ADDR", "T_ADDR", "F_ADDL", "T_ADDL"]].replace(0, np.nan).min(axis=1)
    hi = cl[["F_ADDR", "T_ADDR", "F_ADDL", "T_ADDL"]].replace(0, np.nan).max(axis=1)
    labels = []
    for i, r in cl.iterrows():
        h0, h1 = lo[i], hi[i]
        if pd.isna(h0):
            head = r["name"]
        else:
            a, b = int(h0 // 100 * 100), int(h1 // 100 * 100)
            head = f"{a} block of {r['name']}" if a == b else f"{a}-{b} blocks of {r['name']}"
        c = [cross.get((i, 0)), cross.get((i, 1))]
        c = [x for x in c if x]
        labels.append(head + (f", {c[0]} to {c[1]}" if len(c) == 2 else f", at {c[0]}" if c else ""))
    cl["segment_label"] = labels
    cl["lo"], cl["hi"] = lo, hi
    return cl


def assign_segments(addr, cl):
    """addr: GeoDataFrame with house_number, street, geometry. Range match first, then same street nearby."""
    hn = pd.to_numeric(addr.house_number, errors="coerce")
    seg = pd.Series(index=addr.index, dtype=object)
    how = pd.Series("none", index=addr.index, dtype=object)
    for sk, d in addr.groupby(addr.street.map(segment_key)):
        c = cl[cl.mkey == sk]
        if c.empty:
            continue
        for i in d.index:
            h, p = hn[i], d.geometry[i]
            inr = c[(c.lo <= h) & (h <= c.hi)] if not pd.isna(h) else c.iloc[0:0]
            if len(inr):
                seg[i] = inr.segment_id[inr.distance(p).idxmin()]
                how[i] = "address_range"
            else:
                dist = c.distance(p)
                if dist.min() <= SEG_SAME_STREET_M:
                    seg[i] = c.segment_id[dist.idxmin()]
                    how[i] = "nearest_same_street"
    return seg, how


def to_blocks(pts, blocks):
    """Point-in-polygon, then nearest within NEAREST_MAX_M. Returns block_id, match_method, distance_m."""
    j = gpd.sjoin(pts[["geometry"]], blocks[["block_id", "geometry"]], predicate="within", how="left")
    if not j.index.is_unique:
        raise SystemExit("GATE FAIL: a point fell in two blocks -- the block polygons overlap")
    bid, how, dist = j.block_id.copy(), pd.Series("inside", index=pts.index), pd.Series(0.0, index=pts.index)
    miss = bid.isna()
    if miss.any():
        n = gpd.sjoin_nearest(pts.loc[miss, ["geometry"]], blocks[["block_id", "geometry"]],
                              how="left", distance_col="d")
        n = n[~n.index.duplicated()]
        ok = n.d <= NEAREST_MAX_M
        bid[n.index[ok]] = n.block_id[ok]
        how[n.index[ok]], how[n.index[~ok]] = "nearest", "none"
        dist[n.index] = n.d.round(1)
        bid[n.index[~ok]] = np.nan
    return bid, how, dist


def main():
    run = datetime.datetime.now().isoformat(timespec="seconds")
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    reg = pd.read_csv(REGISTRY) if REGISTRY.exists() else None
    blocks = hb.load_city_blocks(registry=reg)
    cl = segments(load_centerlines())
    blocks = blocks.join(block_labels(blocks, cl), on="block_id")
    blocks["block_label"] = blocks.block_label.fillna("")
    print(f"blocks: {blocks.kind.value_counts().to_dict()}; ids {blocks.id_source.value_counts().to_dict()}")

    # --- address points -> block --------------------------------------------------------------
    a = pd.read_csv(ADDR, dtype=str)
    pts = gpd.GeoDataFrame(a, geometry=gpd.points_from_xy(a.longitude.astype(float), a.latitude.astype(float)),
                           crs=4326).to_crs(hb.CRS)
    pts["block_id"], pts["match_method"], pts["distance_m"] = to_blocks(pts, blocks)
    counts = pts.match_method.value_counts().to_dict()

    # one row per street address; unit rows collapse onto it, the base (non-unit) point speaks for it
    num = pts.ST_NUM.astype(float)
    pts["house_number"] = num.map(lambda x: str(int(x)) if x == int(x) else str(x))   # 2765.5 Wallace is real
    pts["base"] = (pts.house_number + " " + pts.DIRPRE.fillna("") + " " + pts.FEANME.fillna("") + " "
                   + pts.FEATYP.fillna("") + " " + pts.DIRSUF.fillna("")).str.split().str.join(" ").str.title()
    pts["street"] = pts.base.str.split(" ", n=1).str[1].map(street_key)
    pts["is_unit"] = pts.UNIT.notna()
    pts["apn_canonical"] = pts.APN.map(lambda x: to_canonical_apn(x, "Alameda"))
    srt = pts.sort_values("is_unit", kind="stable")
    g = srt.groupby("base", sort=False)
    lk = g.first()[["house_number", "street", "FEATYP", "apn_canonical", "block_id", "match_method",
                    "distance_m", "latitude", "longitude", "geometry"]]
    lk["unit_count"] = g.is_unit.sum().astype(int)
    lk["n_apns"] = g.apn_canonical.nunique()
    lk["spans_blocks"] = g.block_id.nunique() > 1
    lk = gpd.GeoDataFrame(lk.reset_index().rename(columns={"base": "address", "FEATYP": "street_type"}),
                          geometry="geometry", crs=hb.CRS)
    apn_nb = pts.dropna(subset=["block_id"]).groupby("apn_canonical").block_id.nunique()
    lk["apn_multi_block"] = lk.apn_canonical.map(apn_nb).fillna(0) > 1
    lk["segment_id"], lk["segment_method"] = assign_segments(lk, cl)
    lk = lk.merge(blocks[["block_id", "kind", "block_label"]].rename(columns={"kind": "block_kind"}),
                  on="block_id", how="left").merge(cl[["segment_id", "segment_label"]], on="segment_id", how="left")
    lk["latitude"] = lk.latitude.astype(float).round(6)
    lk["longitude"] = lk.longitude.astype(float).round(6)

    # --- assessor parcels -> block ------------------------------------------------------------
    con = sqlite3.connect(f"file:{ASSESSOR}?mode=ro", uri=True)
    par = pd.read_sql("select APN, Latitude, Longitude from parcels", con)
    n_par = len(par)
    par["apn_canonical"] = par.APN.map(lambda x: to_canonical_apn(x, "Alameda"))
    has = par.Latitude.notna() & par.Longitude.notna()
    pg = gpd.GeoDataFrame(par[has], geometry=gpd.points_from_xy(par.Longitude[has], par.Latitude[has]),
                          crs=4326).to_crs(hb.CRS)
    pg["block_id"], pg["match_method"], pg["distance_m"] = to_blocks(pg, blocks)
    par = par.join(pg[["block_id", "match_method", "distance_m"]])
    par["match_method"] = par.match_method.fillna("no_coordinates")
    ap = pts.dropna(subset=["block_id"]).groupby("apn_canonical").block_id.agg(lambda s: ";".join(sorted(set(s))))
    par["address_point_blocks"] = par.apn_canonical.map(ap)
    pcount = par.match_method.value_counts().to_dict()

    # --- gates --------------------------------------------------------------------------------
    def block_of(h, s):
        r = lk[(lk.house_number == h) & (lk.street == s)]
        return r.block_id.iloc[0] if len(r) else None
    corner = (block_of(*normalize_address("1951 Shattuck Ave")), block_of(*normalize_address("2108 Berkeley Way")))
    disagree = par.dropna(subset=["block_id", "address_point_blocks"])
    disagree = int((~disagree.apply(lambda r: r.block_id in r.address_point_blocks.split(";"), axis=1)).sum())
    gates = {
        "address_points": dict(input=len(pts), **counts, ok=sum(counts.values()) == len(pts)),
        "assessor_parcels": dict(input=n_par, **pcount, ok=sum(pcount.values()) == n_par),
        "blocks": dict(enclosed=int((blocks.kind == "enclosed").sum()), edge=int((blocks.kind == "edge").sum()),
                       unique_ids=bool(blocks.block_id.is_unique), ok=bool(blocks.block_id.is_unique)),
        "corner_lot_1951_shattuck_2108_berkeley_way": dict(blocks=corner, ok=corner[0] is not None and corner[0] == corner[1]),
        "addresses": len(lk), "ambiguous_keys_without_type": int(lk.duplicated(["house_number", "street"]).sum()),
        "segment_method": lk.segment_method.value_counts().to_dict(),
        "parcel_centroid_vs_address_point_block_disagree": disagree,
        "median_parcels_per_enclosed_block": float(par.merge(blocks[["block_id", "kind"]], on="block_id")
                                                   .query("kind == 'enclosed'").groupby("block_id").size().median()),
    }
    print(json.dumps(gates, indent=2, default=str))
    failed = [k for k, v in gates.items() if isinstance(v, dict) and v.get("ok") is False]
    if failed:
        raise SystemExit(f"GATE FAIL: {failed} -- nothing written")

    # --- write ---------------------------------------------------------------------------------
    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["address", "house_number", "street", "street_type", "unit_count", "apn_canonical", "n_apns",
            "apn_multi_block", "block_id", "block_kind", "block_label", "match_method", "distance_m",
            "spans_blocks", "segment_id", "segment_label", "segment_method", "latitude", "longitude"]
    lk[cols].sort_values(["street", "house_number"]).to_csv(OUT / "address_block_lookup.csv", index=False)
    par[["apn_canonical", "block_id", "match_method", "distance_m", "address_point_blocks"]].sort_values(
        "apn_canonical").to_csv(OUT / "parcel_block_lookup.csv", index=False)
    pub = blocks[["block_id", "kind", "block_label", "acres", "geometry"]].copy()
    pub["acres"] = pub.acres.round(3)
    pub.to_crs(4326).to_file(OUT / "city_blocks.geojson", driver="GeoJSON", COORDINATE_PRECISION=6)
    seg = cl[["segment_id", "segment_label", "geometry"]].copy()
    seg["geometry"] = seg.geometry.simplify(0.5)       # the layer is densified to a vertex every ~2 m
    seg.to_crs(4326).to_file(
        OUT / "street_segments.geojson", driver="GeoJSON", COORDINATE_PRECISION=6)
    blocks[["block_id", "rep_x", "rep_y"]].to_csv(REGISTRY, index=False)
    leg = hb.legacy_row_ids()
    leg["geometry"] = leg.geometry.representative_point()
    gpd.sjoin(leg, blocks[["block_id", "geometry"]], predicate="within", how="left")[
        ["legacy_id", "block_id"]].to_csv(CROSSWALK, index=False)
    shutil.copyfile(CANON, OUT / "address.py")
    if sha256(CANON) != sha256(OUT / "address.py"):
        raise SystemExit("GATE FAIL: the republished address canon differs from its source")
    prov = dict(run=run, script="scripts/build_address_block_lookup.py", head_commit=commit,
                inputs={str(p.relative_to(ROOT)): sha256(p) for p in [ADDR, hb.BLOCKS, CENTERLINE, hb.CITY_OUTLINE, ASSESSOR]},
                params=dict(min_acres=hb.MIN_ACRES, max_acres=hb.MAX_ACRES, nearest_max_m=NEAREST_MAX_M,
                            label_buf_m=LABEL_BUF_M, label_min_m=LABEL_MIN_M, seg_same_street_m=SEG_SAME_STREET_M),
                address_canon_sha256=sha256(CANON), gates=gates)
    (OUT / "provenance.json").write_text(json.dumps(prov, indent=2, default=str))
    print(f"wrote {OUT.relative_to(ROOT)}/ and {REGISTRY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
