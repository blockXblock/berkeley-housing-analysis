#!/usr/bin/env python3
"""Do wood (utility) poles avoid the Underground Utility Districts?
UUD polygons are PARCELS, but poles sit in the street right-of-way, so a plain
point-in-polygon undercounts. We report BOTH:
  (a) pole inside a UUD parcel, and
  (b) pole within D metres of a UUD parcel boundary (vertex distance, approximate:
      it slightly OVERSTATES distance-to-polygon, so (b) is a mild undercount).
"""
import json, math, collections
import numpy as np

def load(p): return json.load(open(f"data/raw/infrastructure/{p}"))

lights = load("berkeley_streetlights_2026-08-30.geojson")["features"]
uud    = load("berkeley_underground_utility_districts_2026-08-30.geojson")["features"]

LAT0 = 37.87
M_PER_DEG_LAT = 111132.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(LAT0))

def xy(lon, lat): return (lon * M_PER_DEG_LON, lat * M_PER_DEG_LAT)

# --- pole points (fall back to LATITUDE/LONGITUDE attrs when geometry is null)
pts, mats = [], []
for f in lights:
    g = f.get("geometry"); p = f["properties"]
    if g and g.get("coordinates"): lon, lat = g["coordinates"][:2]
    elif p.get("LONGITUDE") and p.get("LATITUDE"): lon, lat = p["LONGITUDE"], p["LATITUDE"]
    else: continue
    pts.append(xy(lon, lat)); mats.append(p.get("POLEMAT"))
pts = np.array(pts); mats = np.array(mats)
print(f"placeable streetlights: {len(pts)} of {len(lights)}")

# --- UUD rings -> vertex cloud + ring list for point-in-polygon
rings = []
for f in uud:
    g = f.get("geometry")
    if not g: continue
    if g["type"] == "Polygon": rings += g["coordinates"]
    elif g["type"] == "MultiPolygon":
        for poly in g["coordinates"]: rings += poly
rings_xy = [np.array([xy(c[0], c[1]) for c in r]) for r in rings if len(r) >= 4]
verts = np.vstack(rings_xy)
print(f"UUD rings: {len(rings_xy)}, vertices: {len(verts)}")

# --- spatial hash on vertices for nearest-distance
CELL = 100.0
grid = collections.defaultdict(list)
for i, (x, y) in enumerate(verts):
    grid[(int(x // CELL), int(y // CELL))].append(i)
grid = {k: np.array(v) for k, v in grid.items()}

def near_dist(x, y, maxr=200.0):
    best = maxr ** 2
    R = int(maxr // CELL) + 1
    cx, cy = int(x // CELL), int(y // CELL)
    for dx in range(-R, R + 1):
        for dy in range(-R, R + 1):
            idx = grid.get((cx + dx, cy + dy))
            if idx is None: continue
            d = (verts[idx, 0] - x) ** 2 + (verts[idx, 1] - y) ** 2
            m = d.min()
            if m < best: best = m
    return math.sqrt(best)

# --- point in any ring (ray casting), only rings whose bbox contains the point
bboxes = np.array([[r[:,0].min(), r[:,0].max(), r[:,1].min(), r[:,1].max()] for r in rings_xy])
def inside(x, y):
    cand = np.where((bboxes[:,0] <= x) & (x <= bboxes[:,1]) &
                    (bboxes[:,2] <= y) & (y <= bboxes[:,3]))[0]
    for ci in cand:
        r = rings_xy[ci]; c = False
        x1, y1 = r[-1]
        for x2, y2 in r:
            if ((y2 > y) != (y1 > y)) and (x < (x1 - x2) * (y - y2) / (y1 - y2) + x2):
                c = not c
            x1, y1 = x2, y2
        if c: return True
    return False

res = collections.defaultdict(lambda: collections.Counter())
dists = {}
for (x, y), m in zip(pts, mats):
    d = near_dist(x, y)
    ins = inside(x, y)
    res[m]["total"] += 1
    if ins: res[m]["inside_parcel"] += 1
    if d <= 30: res[m]["within_30m"] += 1
    if d <= 60: res[m]["within_60m"] += 1
    dists.setdefault(m, []).append(d)

print(f"\n{'material':12s} {'total':>7s} {'in parcel':>10s} {'<=30m':>8s} {'<=60m':>8s}  {'%<=30m':>7s}")
for m in ["Wood", "Metal", "Fiberglass", "Concrete", "Unknown"]:
    c = res[m]
    if not c["total"]: continue
    print(f"{m:12s} {c['total']:7d} {c['inside_parcel']:10d} {c['within_30m']:8d} "
          f"{c['within_60m']:8d}  {c['within_30m']/c['total']*100:6.1f}%")

print("\nInterpretation check — if UUDs really are pole-free, WOOD should be")
print("markedly LESS likely than METAL to sit inside/near a UUD parcel.")
w = res["Wood"]; mt = res["Metal"]
print(f"  wood  <=30m of a UUD parcel: {w['within_30m']}/{w['total']} = {w['within_30m']/w['total']*100:.1f}%")
print(f"  metal <=30m of a UUD parcel: {mt['within_30m']}/{mt['total']} = {mt['within_30m']/mt['total']*100:.1f}%")
ratio = (w['within_30m']/w['total']) / (mt['within_30m']/mt['total'])
print(f"  wood:metal ratio = {ratio:.2f}  (<1 means wood poles avoid UUDs, as expected)")
