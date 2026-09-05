#!/usr/bin/env python3
"""reconcile_tour_geometry.py — for a self-contained tour, compare its footprints against the
canonical geometry and v2, and say which to keep.

WHY. panoramic-kennedy-legacy.kml carries its own 23 polygons. Eight of those buildings ALSO exist
in kml/geometry/geometry.kml, and the two disagree -- on 2026-09-05 the tour drew 2274 Shattuck at
100 m where the canonical file had 59.5 m. Hand-drawn geometry and generated geometry drift, and
without a comparison nobody knows which one a tour is flying.

THE ARBITER IS v2, NOT EITHER FILE. Roof height is checkable: v2 carries height_feet, or
height_stories at the project's 3.5 m/storey convention. Measured against that, the canonical
geometry was right on all eight buildings to 0.0 m and the tour was wrong on all eight, by 3.5 to
40.5 m. So the rule is not "prefer canonical because it is canonical" -- it is "prefer whichever
matches v2", and canonical wins because it is generated FROM v2.

POSITION IS DIFFERENT, AND THE TOUR CAN BE RIGHT. On the same day John flew the tour and moved
three footprints by 56-200 m, and each move was corroborated by assessor improvement values that
the generated geometry had never consulted. A hand correction against the imagery beats a
coordinate the pipeline inherited. So position and height are reconciled SEPARATELY.

  python3 scripts/reconcile_tour_geometry.py --tour panoramic-kennedy-legacy
  python3 scripts/reconcile_tour_geometry.py --tour panoramic-kennedy-legacy --adopt-heights
"""
import argparse, math, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_svg_labels as G
from gen_building_loop import buildings, placemark_name

M_PER_STOREY = 3.5      # the project's own convention


def v2_height_m(r):
    if r is None:
        return None
    if r["height_feet"]:
        return float(r["height_feet"]) * 0.3048
    if r["height_stories"]:
        return float(r["height_stories"]) * M_PER_STOREY
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", required=True, help="tour stem in kml/tours/ carrying its own polygons")
    ap.add_argument("--adopt-heights", action="store_true",
                    help="rewrite the tour's polygon altitudes to the value v2 implies, for every "
                         "building v2 knows. Position is NEVER touched -- see the module docstring.")
    a = ap.parse_args()

    path = f"kml/tours/{a.tour}.kml"
    tour, canon = buildings(path), buildings()
    v2 = {G.normkey(r["address_display"]): r for r in G.rows(False)}

    print(f"  {a.tour}: {len(tour)} footprints\n")
    print(f"  {'building':26} {'tour':>7} {'canon':>7} {'v2':>7}  {'pos Δ':>7}  verdict")
    print(f"  {'-'*26} {'-'*7} {'-'*7} {'-'*7}  {'-'*7}  {'-'*26}")
    fixes, only_here, agree = [], 0, 0
    for k in sorted(tour):
        t = tour[k]
        ck = next((c for c in canon if G.normkey(c) == G.normkey(k)), None)
        r = v2.get(G.normkey(k))
        vh = v2_height_m(r)
        if ck is None and vh is None:
            only_here += 1
            continue
        c = canon[ck] if ck else None
        d = (math.hypot((c[0]-t[0])*math.cos(math.radians(t[1]))*111320, (c[1]-t[1])*111320)
             if c else None)
        if vh is None:
            verdict = "v2 has no height"
        elif abs(t[2]-vh) < 0.5:
            verdict = "tour matches v2"; agree += 1
        else:
            verdict = f"tour off by {t[2]-vh:+.1f} m — v2 says {vh:.1f}"
            fixes.append((k, t[2], vh))
        print(f"  {k[:26]:26} {t[2]:6.1f}m {(f'{c[2]:6.1f}m' if c else '      -')} "
              f"{(f'{vh:6.1f}m' if vh else '      -')}  {(f'{d:6.0f}m' if d is not None else '     -')}  {verdict}")

    print(f"\n  {agree} match v2 · {len(fixes)} disagree · {only_here} known only to this tour")
    if only_here:
        print(f"  (those {only_here} have no independent check — the tour is their only source)")

    if fixes and a.adopt_heights:
        s = open(path, errors="replace").read()
        out, n = [], 0
        for chunk in re.split(r"(<Placemark>.*?</Placemark>)", s, flags=re.S):
            if chunk.startswith("<Placemark>") and "<Polygon>" in chunk:
                k = placemark_name(chunk)
                hit = next((f for f in fixes if f[0] == k), None)
                if hit:
                    new = f"{hit[2]:.1f}"
                    chunk = re.sub(r"(-?\d+\.\d+),(-?\d+\.\d+),[\d.]+",
                                   lambda m: f"{m.group(1)},{m.group(2)},{new}", chunk)
                    n += 1
            out.append(chunk)
        open(path, "w").write("".join(out))
        print(f"\n  ADOPTED: {n} footprint(s) re-cut to the height v2 implies. Positions untouched.")
    elif fixes:
        print(f"\n  re-run with --adopt-heights to re-cut those {len(fixes)} to v2's height")


if __name__ == "__main__":
    main()
