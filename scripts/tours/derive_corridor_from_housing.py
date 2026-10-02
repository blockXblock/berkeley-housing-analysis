#!/usr/bin/env python3
"""derive_corridor_from_housing.py — control points straight from the buildings that front a street.

The parcel-gap method (derive_street_centreline.py / derive_corridor_ew.py) works when the
surviving slices span the corridor, but it failed badly on Oxford and Bancroft: the slices that
passed the gap filter clustered in one stretch, so the control points ended up 280-1,036 m from
the actual buildings. Rather than tune that filter, use the far more robust signal -- THE
BUILDINGS THEMSELVES. They front the street, so a line through them tracks it, offset by roughly
half a lot.

This will not be exact. It does not need to be: the flight only has to pass close enough to see
the buildings, and every orbit radius derives from the path's own closest approach anyway. A
hand-drawn Path in Google Earth still beats it -- Shattuck's needed no correction at all -- so
treat this as a usable default, not a finished centreline.

Output: kml/tours/control_points/<Corridor> Control Points DERIVED.kml (or --outdir)
Housing positions from v4 (v4_source: every v4 project's label point) since 2026-10-02.
"""
import argparse, math, os, re, sys

from scripts.tours import v4_source as V

OUT_DIR = "kml/tours/control_points"
M = 111320.0

CORRIDORS = {
    "Oxford":     ("%OXFORD%",     "N->S", 8),
    "Bancroft":   ("%BANCROFT%",   "W->E", 10),
    "University": ("%UNIVERSITY%", "W->E", 10),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corridors", nargs="*")
    ap.add_argument("--outdir", default=OUT_DIR)
    a = ap.parse_args()
    out_dir = a.outdir
    os.makedirs(out_dir, exist_ok=True)
    only = a.corridors or list(CORRIDORS)
    for name in only:
        pat, direction, ncp = CORRIDORS[name]
        word = pat.strip("%")
        pts = [(r["longitude"], r["latitude"]) for r in V.projects()
               if word in (r["address_display"] or "").upper() and r["latitude"] is not None]
        if len(pts) < 3:
            print(f"{name}: too few"); continue
        lons = [p[0] for p in pts]; lats = [p[1] for p in pts]
        ew = (max(lons)-min(lons))*88000 > (max(lats)-min(lats))*M
        pts.sort(key=lambda p: p[0] if ew else -p[1])
        # bin along the corridor, take the median across-axis value in each bin
        lo = pts[0][0] if ew else pts[0][1]
        hi = pts[-1][0] if ew else pts[-1][1]
        edges = [lo + (hi-lo)*i/ncp for i in range(ncp+1)]
        cps = []
        for i in range(ncp):
            a, b = sorted((edges[i], edges[i+1]))
            band = [p for p in pts if a <= (p[0] if ew else p[1]) <= b]
            if not band:
                continue
            across = sorted(p[1] if ew else p[0] for p in band)
            mid = across[len(across)//2]
            along = (a+b)/2
            cps.append((along, mid) if ew else (mid, along))
        if direction in ("E->W", "S->N"):
            cps.reverse()
        pm = []
        for i, (x, y) in enumerate(cps, 1):
            pm.append(f"""	<Placemark>
		<name>{name.replace(' ','')}-CP{i:02d}</name>
		<description><![CDATA[Derived from the median position of the housing fronting {name}.
Approximate -- offset from the true centreline by roughly half a lot. Drag onto the roadway in
Earth Pro, or draw a Path instead (Shattuck's hand-drawn path needed no correction).]]></description>
		<styleUrl>#m_ylw-pushpin</styleUrl>
		<Point><gx:drawOrder>1</gx:drawOrder><coordinates>{x:.13f},{y:.13f},0</coordinates></Point>
	</Placemark>""")
        kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
	<name>{name} Control Points DERIVED · {len(cps)} points · {direction}</name>
	<Style id="s_ylw-pushpin"><IconStyle><scale>1.1</scale>
		<Icon><href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href></Icon></IconStyle></Style>
	<StyleMap id="m_ylw-pushpin">
		<Pair><key>normal</key><styleUrl>#s_ylw-pushpin</styleUrl></Pair>
		<Pair><key>highlight</key><styleUrl>#s_ylw-pushpin</styleUrl></Pair></StyleMap>
	<Folder><name>{name} Control Points</name><open>1</open>
{chr(10).join(pm)}
	</Folder>
</Document>
</kml>
"""
        open(f"{out_dir}/{name} Control Points DERIVED.kml", "w").write(kml)
        print(f"{name:11} {'E-W' if ew else 'N-S'} · {len(cps)} points from {len(pts)} buildings · {direction}")


if __name__ == "__main__":
    main()
