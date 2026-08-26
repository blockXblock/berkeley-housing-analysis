#!/usr/bin/env python3
"""add_orbit_vertices.py — insert a path vertex at the closest point to each orbit target.

WHY (John's insight, 2026-08-26): every orbit bug in this thread had one shape -- the building
was detected MID-SEGMENT, so the manoeuvre had to be inserted at a point the camera had already
passed. Retrospective detection forces a retrospective correction, which is how we got the
backward jump, two broken fillets, and the retreat.

A vertex AT each building inverts that. The manoeuvre keys to a point the flight is ARRIVING at,
so it is emitted before the camera gets there -- forward by construction. It also makes the
corridor bend naturally toward each tower instead of running dead straight past it.

This is fully automatic: no hand-editing in Google Earth. Re-run it whenever the orbit list
changes and it rebuilds the vertices from the current geometry.

Usage:
  python scripts/add_orbit_vertices.py IN.kml OUT.kml --orbit "3000 SHATTUCK,2920 SHATTUCK"
"""
import argparse, math, re

GEOM = "kml/geometry/geometry.kml"


def buildings():
    out = {}
    for pm in re.findall(r"<Placemark>.*?</Placemark>", open(GEOM, errors="replace").read(), re.S):
        ad = re.search(r"<b>([^<]*)</b><br/>", pm)
        po = re.search(r"<Polygon>.*?</Polygon>", pm, re.S)
        if not (ad and po):
            continue
        cs = re.search(r"<coordinates>\s*(.*?)\s*</coordinates>", po.group(0), re.S).group(1)
        r = [tuple(float(x) for x in q.split(",")[:2]) for q in cs.split()][:-1]
        if len(r) < 3:
            continue
        out[ad.group(1).upper().strip()] = (sum(p[0] for p in r)/len(r),
                                            sum(p[1] for p in r)/len(r))
    return out


def read_path(path):
    t = open(path, errors="replace").read()
    ls = re.search(r"<LineString>.*?<coordinates>\s*(.*?)\s*</coordinates>", t, re.S)
    if ls:
        return t, [tuple(float(x) for x in c.split(",")[:2]) for c in ls.group(1).split()], True
    pts = []
    for pm in re.findall(r"<Placemark>.*?</Placemark>", t, re.S):
        m = re.search(r"<Point>.*?<coordinates>\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", pm, re.S)
        if m:
            pts.append((float(m.group(1)), float(m.group(2))))
    return t, pts, False


def closest_on_segment(p, a, b):
    """(distance_m, point, t) of the closest point on segment a-b to p."""
    k = math.cos(math.radians(p[1])); M = 111320.0
    ax, ay = (a[0]-p[0])*k*M, (a[1]-p[1])*M
    bx, by = (b[0]-p[0])*k*M, (b[1]-p[1])*M
    dx, dy = bx-ax, by-ay
    L2 = dx*dx + dy*dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, -(ax*dx + ay*dy)/L2))
    cx, cy = ax + dx*t, ay + dy*t
    return math.hypot(cx, cy), (p[0] + cx/(k*M), p[1] + cy/M), t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile"); ap.add_argument("outfile")
    ap.add_argument("--orbit", required=True)
    ap.add_argument("--snap", type=float, default=25.0,
                    help="if a vertex is already this close, use it instead of inserting")
    a = ap.parse_args()

    src, V, is_line = read_path(a.infile)
    B = buildings()
    print(f"path: {len(V)} vertices")

    for frag in [x.strip().upper() for x in a.orbit.split(",") if x.strip()]:
        hits = [(k, v) for k, v in B.items() if frag in k]
        if not hits:
            print(f"  !! not in geometry: {frag}"); continue
        name, c = hits[0]
        # already have a vertex close enough?
        dv = [(math.dist((c[0]-v[0])*math.cos(math.radians(v[1]))*111320/1, 0) if False else
               closest_on_segment(c, v, v)[0], i) for i, v in enumerate(V)]
        near = min(dv)
        if near[0] <= a.snap:
            print(f"  {name[:26]:28} vertex {near[1]} already {near[0]:.0f} m away — kept")
            continue
        best = None
        for i in range(len(V)-1):
            d, pt, t = closest_on_segment(c, V[i], V[i+1])
            if best is None or d < best[0]:
                best = (d, pt, i, t)
        d, pt, i, t = best
        V.insert(i+1, pt)
        print(f"  {name[:26]:28} inserted vertex after {i} at {d:.0f} m from the centroid")

    coords = " ".join(f"{x:.13f},{y:.13f},0" for x, y in V)
    if is_line:
        out = re.sub(r"(<LineString>.*?<coordinates>)\s*.*?\s*(</coordinates>)",
                     lambda m: m.group(1) + coords + m.group(2), src, count=1, flags=re.S)
    else:
        out = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n'
               f'<name>{a.outfile.split("/")[-1].replace(".kml","")}</name>\n'
               '<Placemark><name>corridor</name><LineString><tessellate>1</tessellate>\n'
               f'<coordinates>{coords}</coordinates></LineString></Placemark>\n'
               '</Document></kml>\n')
    open(a.outfile, "w").write(out)
    print(f"wrote {a.outfile}: {len(V)} vertices")


if __name__ == "__main__":
    main()
