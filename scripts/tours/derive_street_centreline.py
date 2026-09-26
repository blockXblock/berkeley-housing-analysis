#!/usr/bin/env python3
"""derive_street_centreline.py — control points WITHOUT Google Earth.

WHY: placing control points by hand needs Earth Pro, and Earth Pro on an 8 GB Mac runs out of
application memory with the geometry loaded (it happened, and the unsaved work was lost because
Temporary Places is discarded on quit). The manual step is the fragile one, so remove it.

THE METHOD: a street is the GAP BETWEEN THE PARCEL ROWS that face it.

CRITICAL: THE SEARCH LINE MUST FOLLOW THE STREET, NOT A FIXED LONGITUDE. San Pablo runs
DIAGONALLY -- its housing shifts from -122.29497 in the north to -122.28669 in the south, some
700 m of drift. A fixed-longitude search locked onto a different street's gap and produced a
centreline 590 m from the actual buildings, confidently and silently. So the local corridor
longitude at each latitude is now derived FROM THE HOUSING ITSELF (the buildings front the
street, so they trace it), and the parcel-gap search runs around that moving line. For each latitude slice
along a corridor, take the furthest-east edge of the west-side parcels and the furthest-west
edge of the east-side parcels; the centreline is the midpoint of that gap. Validated on
Telegraph: median derived gap 19 m against an actual right-of-way of roughly 24 m.

NOISE, AND HOW IT IS REJECTED: cross-streets, parking lots and corner parcels produce
implausible gaps (negative where parcels straddle the assumed line, or 80 m+ at an
intersection). Slices outside MIN_GAP_M..MAX_GAP_M are dropped, and the surviving longitudes
are smoothed with a rolling median so a single odd parcel cannot pull the line sideways.

The result is still CANDIDATE geometry -- accurate to a few metres, which is well inside the
roadway, but it should be eyeballed once in Earth Pro before a final recording.

Output: kml/tours/control_points/<Corridor> Control Points DERIVED.kml
READ-ONLY on all sources.
"""
import json, math, os, statistics

PARCELS = "data/raw/berkeley_taxparcels_2026-08-12.geojson"
OUT_DIR = "kml/tours/control_points"
MIN_GAP_M, MAX_GAP_M = 8.0, 45.0      # a plausible Berkeley arterial right-of-way
SLICE_DEG = 0.00035                    # ~39 m of latitude per slice
SMOOTH = 5                             # rolling-median window (slices)

# corridor: (address LIKE, south lat, north lat, direction, n control points to emit)
CORRIDORS = {
    "San Pablo": ("%SAN PABLO%", 37.8460, 37.8878, "N->S", 10),
    "Adeline":   ("%ADELINE%",   37.8408, 37.8607, "N->S",  8),
    "Telegraph": ("%TELEGRAPH%", 37.8478, 37.8686, "S->N", 10),
}


def corridor_spine(pattern, south, north):
    """(lat, lon) samples tracing the street, taken from the housing that fronts it.
    Buildings front the street, so their coordinates ARE the street's path -- which a fixed
    longitude is not, for any diagonal street."""
    import sqlite3
    c = sqlite3.connect("databases/berkeley_housing_v2.db")
    pts = [(r[1], r[0]) for r in c.execute(
        "select longitude, latitude from v_projects_flat where upper(address_display) like ? "
        "and latitude is not null and latitude between ? and ? order by latitude",
        (pattern, south, north))]
    return pts


def lon_at(spine, lat):
    """Local corridor longitude at a latitude, by linear interpolation along the spine."""
    if not spine:
        return None
    if lat <= spine[0][0]:
        return spine[0][1]
    if lat >= spine[-1][0]:
        return spine[-1][1]
    for i in range(len(spine)-1):
        a, b = spine[i], spine[i+1]
        if a[0] <= lat <= b[0]:
            f = (lat - a[0]) / (b[0] - a[0]) if b[0] != a[0] else 0
            return a[1] + (b[1] - a[1]) * f
    return spine[-1][1]


def rings(g):
    return [g["coordinates"]] if g["type"] == "Polygon" else (
        g["coordinates"] if g["type"] == "MultiPolygon" else [])


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    gj = json.load(open(PARCELS))
    feats = []
    for f in gj["features"]:
        for poly in rings(f["geometry"]):
            r = poly[0]
            xs = [p[0] for p in r]; ys = [p[1] for p in r]
            feats.append((sum(xs)/len(xs), sum(ys)/len(ys), min(xs), max(xs)))

    for name, (pattern, south, north, direction, ncp) in CORRIDORS.items():
        spine = corridor_spine(pattern, south, north)
        if len(spine) < 2:
            print(f"{name}: too few housing points to trace the corridor"); continue
        band = [p for p in feats if south <= p[1] <= north
                and abs(p[0] - lon_at(spine, p[1]))*88000 < 220]
        pts, rejected = [], 0
        lat = south
        while lat < north:
            lon0 = lon_at(spine, lat + SLICE_DEG/2)     # the street MOVES; follow it
            sl = [p for p in band if lat <= p[1] < lat + SLICE_DEG]
            west = [p for p in sl if p[0] < lon0]
            east = [p for p in sl if p[0] >= lon0]
            if west and east:
                w_edge = max(p[3] for p in west)
                e_edge = min(p[2] for p in east)
                gap = (e_edge - w_edge) * 88000
                if MIN_GAP_M <= gap <= MAX_GAP_M:
                    pts.append(((w_edge + e_edge)/2, lat + SLICE_DEG/2))
                else:
                    rejected += 1
            lat += SLICE_DEG
        if len(pts) < 3:
            print(f"{name}: only {len(pts)} usable slices — skipped"); continue

        # rolling median on longitude: one odd parcel must not pull the line sideways
        lons = [p[0] for p in pts]
        sm = []
        for i in range(len(lons)):
            w = lons[max(0, i-SMOOTH//2): i+SMOOTH//2+1]
            sm.append(statistics.median(w))
        pts = [(sm[i], pts[i][1]) for i in range(len(pts))]
        pts.sort(key=lambda p: -p[1])
        if direction == "S->N":
            pts.reverse()

        # thin to ncp evenly spaced control points, always keeping both ends
        idx = [round(i*(len(pts)-1)/(ncp-1)) for i in range(ncp)]
        cps = [pts[i] for i in sorted(set(idx))]

        pm = []
        for i, (x, y) in enumerate(cps, 1):
            pm.append(f"""	<Placemark>
		<name>{name.replace(' ','')}-CP{i:02d}</name>
		<description><![CDATA[DERIVED from the gap between the parcel rows facing {name}
(midpoint of west-parcel east edge and east-parcel west edge, rolling-median smoothed).
Accurate to a few metres. Check once in Earth Pro before a final recording.]]></description>
		<styleUrl>#m_ylw-pushpin</styleUrl>
		<Point><gx:drawOrder>1</gx:drawOrder><coordinates>{x:.13f},{y:.13f},0</coordinates></Point>
	</Placemark>""")
        kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
	<name>{name} Control Points DERIVED · {len(cps)} points · {direction}</name>
	<description><![CDATA[Derived from county parcel geometry, no Google Earth required.
Flight order is {direction} — the order of these placemarks IS the flight order.]]></description>
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
        path = f"{OUT_DIR}/{name} Control Points DERIVED.kml"
        open(path, "w").write(kml)
        spread = (max(p[0] for p in pts) - min(p[0] for p in pts)) * 88000
        print(f"{name:12} {len(cps)} points from {len(pts)} slices ({rejected} rejected) · "
              f"lateral spread {spread:.0f} m · {direction} · -> {path}")


if __name__ == "__main__":
    main()
