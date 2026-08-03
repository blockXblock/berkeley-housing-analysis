#!/usr/bin/env python3
"""compare_geometry.py — diff two building-geometry KMLs building-by-building.

A raw text diff on KMLs is noise (coordinate reformatting, reordering). This matches
buildings by their <name> label and reports what actually changed:
  - buildings ADDED / REMOVED between the two files
  - footprints RESHAPED (different vertex count — e.g. your rectangle simplification)
  - footprints MOVED (same vertex count but coordinates shifted > threshold)
  - unchanged

Usage:
  python scripts/compare_geometry.py A.kml B.kml            # A = old, B = new
  python scripts/compare_geometry.py A.kml B.kml --threshold-m 2.0
  python scripts/compare_geometry.py A.kml B.kml --show all # list every building, not just changes
"""
import re, sys, math, argparse, os

def parse(path):
    """name -> list[(lon,lat)] footprint vertices (first Polygon per Placemark)."""
    t = open(path, encoding="utf-8", errors="ignore").read()
    out = {}
    for pm in re.findall(r"<Placemark\b.*?</Placemark>", t, re.S):
        m = re.search(r"<name>(.*?)</name>", pm, re.S)
        name = re.sub(r"\s+", " ", m.group(1)).strip() if m else "(unnamed)"
        poly = re.search(r"<Polygon\b.*?</Polygon>", pm, re.S)
        if not poly:
            continue
        c = re.search(r"<coordinates>(.*?)</coordinates>", poly.group(0), re.S)
        if not c:
            continue
        verts = []
        for tok in c.group(1).replace("\n", " ").split():
            if "," in tok:
                lon, lat = tok.split(",")[:2]
                verts.append((float(lon), float(lat)))
        if verts:
            out.setdefault(name, verts)   # first polygon wins if a name repeats
    return out

def centroid(v):
    return (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v))

def meters(a, b):
    """distance in metres between two (lon,lat)."""
    latm = 111320.0
    lonm = 111320.0 * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot((a[0] - b[0]) * lonm, (a[1] - b[1]) * latm)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old"); ap.add_argument("new")
    ap.add_argument("--threshold-m", type=float, default=1.0,
                    help="centroid shift (metres) to count a footprint as MOVED (default 1.0)")
    ap.add_argument("--show", choices=["changes", "all"], default="changes")
    ap.add_argument("--match", choices=["centroid", "name"], default="centroid",
                    help="how to pair buildings: 'centroid' (geometry, label-agnostic — DEFAULT, "
                         "robust to relabeling) or 'name' (exact label match)")
    ap.add_argument("--match-radius-m", type=float, default=25.0,
                    help="centroid-match: max metres to consider two footprints the same building")
    a = ap.parse_args()
    for p in (a.old, a.new):
        if not os.path.exists(p): sys.exit(f"not found: {p}")

    A, B = parse(a.old), parse(a.new)
    reshaped, moved, unchanged = [], [], []

    if a.match == "name":
        added = [(n,) for n in sorted(set(B) - set(A))]
        removed = [(n,) for n in sorted(set(A) - set(B))]
        pairs = [(n, n) for n in (set(A) & set(B))]
    else:
        # greedy nearest-centroid pairing (label-agnostic): match closest OLD/NEW footprints first
        ca = {n: centroid(v) for n, v in A.items()}
        cb = {n: centroid(v) for n, v in B.items()}
        cand = sorted((meters(ca[na], cb[nb]), na, nb)
                      for na in A for nb in B if meters(ca[na], cb[nb]) <= a.match_radius_m)
        usedA, usedB, pairs = set(), set(), []
        for d, na, nb in cand:
            if na in usedA or nb in usedB: continue
            usedA.add(na); usedB.add(nb); pairs.append((na, nb))
        added = [(nb,) for nb in B if nb not in usedB]
        removed = [(na,) for na in A if na not in usedA]

    for na, nb in pairs:
        va, vb = A[na], B[nb]
        label = nb if na == nb else f"{nb}   (was: {na})"
        if len(va) != len(vb):
            reshaped.append((label, len(va), len(vb)))
        else:
            d = meters(centroid(va), centroid(vb))
            (moved if d > a.threshold_m else unchanged).append((label, d))
    added = sorted(added); removed = sorted(removed)

    print(f"OLD  {a.old}   ({len(A)} buildings)")
    print(f"NEW  {a.new}   ({len(B)} buildings)")
    print("-" * 70)
    print(f"  added:     {len(added)}")
    print(f"  removed:   {len(removed)}")
    print(f"  reshaped:  {len(reshaped)}  (vertex count changed)")
    print(f"  moved:     {len(moved)}  (> {a.threshold_m} m)")
    print(f"  unchanged: {len(unchanged)}")
    def dump(title, rows, fmt):
        if rows:
            print(f"\n{title}:")
            for r in rows: print("   " + fmt(r))
    dump("ADDED (only in NEW)", added, lambda r: r[0])
    dump("REMOVED (only in OLD)", removed, lambda r: r[0])
    dump("RESHAPED (old→new vertices)", sorted(reshaped, key=lambda r: -abs(r[1]-r[2])),
         lambda r: f"{r[1]:>3} → {r[2]:<3}  {r[0]}")
    dump("MOVED (centroid shift)", sorted(moved, key=lambda r: -r[1]),
         lambda r: f"{r[1]:6.1f} m  {r[0]}")
    if a.show == "all":
        dump("UNCHANGED", sorted(unchanged), lambda r: f"{r[1]:6.2f} m  {r[0]}")

if __name__ == "__main__":
    main()
