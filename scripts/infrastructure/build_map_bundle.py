#!/usr/bin/env python3
"""Compact all retrieved infrastructure into one small JSON payload for a
self-contained map page. Coordinates -> integers at 1e-5 deg (~0.9 m), then
delta-encoded per line. No basemap: the city is drawn from its own infrastructure."""
import json, collections, re, sys, os

# usage: build_map_bundle.py [snapshot_date] [out_path]
DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-08-30"
OUT  = sys.argv[2] if len(sys.argv) > 2 else f"scratch/infrastructure/map_bundle_{DATE}.json"
D = "data/raw/infrastructure"
def load(n): return json.load(open(f"{D}/{n}_{DATE}.geojson"))

# integer grid over Berkeley
S = 100000.0
def q(lon, lat): return (round(lon * S), round(lat * S))

def lines(feats, decade_of=None, simplify_tol=0):
    """-> list of [decade_or_-1, x0, y0, dx, dy, dx, dy, ...]"""
    out = []
    for f in feats:
        g = f.get("geometry")
        if not g: continue
        paths = [g["coordinates"]] if g["type"] == "LineString" else \
                (g["coordinates"] if g["type"] == "MultiLineString" else [])
        dec = decade_of(f["properties"]) if decade_of else -1
        for path in paths:
            pts = [q(c[0], c[1]) for c in path]
            ded = [pts[0]]
            for p in pts[1:]:
                if p != ded[-1]: ded.append(p)
            if len(ded) < 2: continue
            if simplify_tol:                      # drop near-collinear middles
                keep = [ded[0]]
                for i in range(1, len(ded) - 1):
                    ax, ay = keep[-1]; bx, by = ded[i]; cx, cy = ded[i+1]
                    cross = abs((bx-ax)*(cy-ay) - (by-ay)*(cx-ax))
                    if cross > simplify_tol: keep.append(ded[i])
                keep.append(ded[-1]); ded = keep
            enc = [dec, ded[0][0], ded[0][1]]
            for i in range(1, len(ded)):
                enc += [ded[i][0] - ded[i-1][0], ded[i][1] - ded[i-1][1]]
            out.append(enc)
    return out

def points(feats, pick=None):
    out = []
    for f in feats:
        g = f.get("geometry"); p = f["properties"]
        if g and g.get("coordinates"): lon, lat = g["coordinates"][:2]
        elif p.get("LONGITUDE") and p.get("LATITUDE"): lon, lat = p["LONGITUDE"], p["LATITUDE"]
        else: continue
        if pick and not pick(p): continue
        out.append(q(lon, lat))
    flat = []
    for x, y in out: flat += [x, y]
    return flat

def dec_from_int(field, lo=1850):
    def g(p):
        y = p.get(field)
        return (y // 10) * 10 if isinstance(y, int) and lo <= y <= 2026 else -1
    return g
def dec_from_str(field):
    def g(p):
        m = re.search(r'(\d{4})', str(p.get(field) or ""))
        y = int(m.group(1)) if m else None
        return (y // 10) * 10 if y and 1850 <= y <= 2026 else -1
    return g

L = load("berkeley_streetlights")["features"]

# --- Berkeley envelope, taken from the streetlights (definitively in-city).
# The PG&E gas layer the City republishes is REGIONAL (it reaches the Central
# Valley); only the features touching Berkeley belong on a Berkeley map.
_x, _y = [], []
for f in L:
    g = f.get("geometry"); p = f["properties"]
    if g and g.get("coordinates"): _x.append(g["coordinates"][0]); _y.append(g["coordinates"][1])
    elif p.get("LONGITUDE"): _x.append(p["LONGITUDE"]); _y.append(p["LATITUDE"])
BX0, BX1, BY0, BY1 = min(_x), max(_x), min(_y), max(_y)
PAD = 0.004
def touches_berkeley(f):
    g = f.get("geometry")
    if not g: return False
    c = g["coordinates"]
    pts = c if g["type"] == "LineString" else [q for path in c for q in path]
    return any(BX0-PAD <= q[0] <= BX1+PAD and BY0-PAD <= q[1] <= BY1+PAD for q in pts)

gas_all = load("berkeley_pge_gas_pipelines")["features"]
gas_berk = [f for f in gas_all if touches_berkeley(f)]
print(f"gas: {len(gas_berk)} of {len(gas_all)} features touch Berkeley (layer is regional)")

bundle = {
  "meta": {"retrieved": DATE, "scale": S,
           "source": "City of Berkeley ArcGIS (gis.cityofberkeley.info); PG&E gas + EBMUD water layers as republished by the City"},
  "poles_wood":  points(L, lambda p: p.get("POLEMAT") == "Wood"),
  "lights_city": points(L, lambda p: p.get("POLEMAT") != "Wood"),
  "gas":   lines(gas_berk, dec_from_str("YR_INSTALL"), 20),
  "water": lines(load("berkeley_ebmud_water_mains")["features"],  dec_from_int("INSTALLATI"), 20),
  "sewer": lines(load("berkeley_sanitary_sewer_mains")["features"], None, 20),
  "storm": lines(load("berkeley_storm_sewer_mains")["features"],  None, 20),
}
uud = []
for f in load("berkeley_underground_utility_districts")["features"]:
    g = f.get("geometry")
    if not g: continue
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    for poly in polys:
        r = [q(c[0], c[1]) for c in poly[0]]
        ded = [r[0]] + [p for i, p in enumerate(r[1:]) if p != r[i]]
        if len(ded) < 3: continue
        enc = [ded[0][0], ded[0][1]]
        for i in range(1, len(ded)): enc += [ded[i][0]-ded[i-1][0], ded[i][1]-ded[i-1][1]]
        uud.append(enc)
bundle["uud"] = uud

xs, ys = [], []
for k in ("poles_wood", "lights_city"):
    v = bundle[k]; xs += v[0::2]; ys += v[1::2]
bundle["meta"]["bbox"] = [min(xs), min(ys), max(xs), max(ys)]
bundle["meta"]["gas_note"] = ("PG&E gas layer is regional; clipped to features "
                              "touching Berkeley (%d of %d)" % (len(gas_berk), len(gas_all)))

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
json.dump(bundle, open(OUT, "w"), separators=(",", ":"))
print(f"wrote {OUT}  {os.path.getsize(OUT)/1e6:.2f} MB")
for k, v in bundle.items():
    if k == "meta": continue
    n = len(v)//2 if k in ("poles_wood","lights_city") else len(v)
    verts = sum((len(e)-1)//2 for e in v) if isinstance(v[0], list) else n
    print(f"  {k:12s} {n:6d} features, {verts:8d} vertices")
