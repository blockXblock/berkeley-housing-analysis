#!/usr/bin/env python3
"""gen_tour_control_points.py — CANDIDATE control points for a corridor flyover.

THE WORKFLOW THIS SERVES (established by the Shattuck N->S flight):
  1. Control points are hand-placed in Google Earth Pro and exported as a KML.
     "Shattuck Control Points.kml" holds FOUR: N-Shattuck-North/South, S-Shattuck-North/South
     -- two straight runs, because Shattuck jogs at ~37.870.
  2. The flight is INTERPOLATED between them. Verified: the tour's first camera matches control
     point #1 to ten decimal places, and 86 of its 112 waypoints sit within 25 m of a
     control-point segment (median offset 4.9 m). The other 26 are the two tower orbits.
  => No road dataset is needed. The human eye on real imagery beats any centreline source, and
     MORE CONTROL POINTS = MORE FIDELITY on a curving street.

This script only proposes a STARTING SET for John to drag onto the true centreline. Candidates
are derived from the housing that fronts the corridor: bin by latitude, take the median
longitude of nearby buildings, and place a point per bin. Buildings front the street, so their
median longitude tracks the roadway -- approximately, which is the point. They are candidates.

Output per corridor: kml/tours/control_points/<Corridor> Control Points CANDIDATE.kml
READ-ONLY on all sources.
"""
import math, os, re, sqlite3

OUT_DIR = "kml/tours/control_points"
ADU_KML = "kml/geometry/adu-middle-housing.kml"
GEOM_KML = "kml/geometry/geometry.kml"

# corridor: (address LIKE pattern, approx lon for the initial filter, south lat, north lat, n bins)
# corridor: (LIKE pattern, approx lon, south lat, north lat, n bins, direction, endpoint anchors)
# EXTENTS ARE THE CIVIC ONES JOHN SPECIFIED, not merely where housing happens to sit -- the
# generated bins only span the housing, so explicit ANCHORS pin each end of the real corridor.
# Anchor latitudes are approximate; drag them in Earth Pro like any other candidate.
CORRIDORS = {
    # A: the length of San Pablo, north to south (Albany line -> Oakland line)
    "San Pablo": ("%SAN PABLO%", -122.2955, 37.8495, 37.8800, 6, "N->S",
                  [("North-end-Albany-line", -122.2976, 37.8878),
                   ("South-end-Oakland-line", -122.2933, 37.8460)]),
    # B: the length of Adeline, north to south, STARTING A BLOCK NORTH of Shattuck/Adeline
    "Adeline":   ("%ADELINE%",   -122.2690, 37.8420, 37.8580, 4, "N->S",
                  [("North-start-block-N-of-Shattuck", -122.2683, 37.8607),
                   ("South-end-Oakland-line", -122.2726, 37.8408)]),
    # C: the length of Telegraph, SOUTH TO NORTH, from just before the Oakland line to Bancroft
    "Telegraph": ("%TELEGRAPH%", -122.2585, 37.8455, 37.8695, 6, "S->N",
                  [("South-start-before-Oakland-line", -122.2596, 37.8478),
                   ("North-end-Bancroft", -122.2589, 37.8686)]),
}
CRUISE_M = 20.0          # standard cruise altitude, per John 2026-08-24


def dist_m(lon1, lat1, lon2, lat2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(h))


def adu_points():
    pts = []
    for pm in re.findall(r"<Placemark>.*?</Placemark>", open(ADU_KML, errors="replace").read(), re.S):
        m = re.search(r"<coordinates>\s*(-?[\d.]+),(-?[\d.]+)", pm)
        if m:
            pts.append((float(m.group(1)), float(m.group(2))))
    return pts


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    c = sqlite3.connect("databases/berkeley_housing_v2.db"); c.row_factory = sqlite3.Row
    adus = adu_points()

    for name, (pat, lon0, south, north, nbins, direction, anchors) in CORRIDORS.items():
        # every housing point that fronts this corridor: tracked projects by address, plus ADUs
        # within 120 m of the rough corridor line (they carry no parsable address in the KML)
        pts = []
        for r in c.execute("""select address_display,total_units,latitude,longitude
                              from v_projects_flat
                              where upper(address_display) like ? and latitude is not null""", (pat,)):
            if south <= r["latitude"] <= north:
                pts.append((r["longitude"], r["latitude"], r["total_units"] or 0))
        for x, y in adus:
            if south <= y <= north and dist_m(lon0, y, x, y) < 120:
                pts.append((x, y, 0))
        if not pts:
            print(f"{name}: no housing found"); continue

        # bin by latitude; the median longitude per bin tracks the roadway
        lo, hi = min(p[1] for p in pts), max(p[1] for p in pts)
        edges = [lo + (hi-lo)*i/nbins for i in range(nbins+1)]
        cps = []
        for i in range(nbins):
            band = [p for p in pts if edges[i] <= p[1] <= edges[i+1]]
            if not band:
                continue
            lons = sorted(p[0] for p in band)
            cps.append((lons[len(lons)//2], (edges[i]+edges[i+1])/2, len(band)))
        # pin the real corridor ends, which the housing bins do not reach
        for anm, ax, ay in anchors:
            cps.append((ax, ay, -1))
        cps.sort(key=lambda p: -p[1])                       # north -> south
        if direction == "S->N":
            cps.reverse()                                   # Telegraph runs south to north

        pm = []
        for i, (x, y, n) in enumerate(cps, 1):
            pm.append(f"""	<Placemark>
		<name>{name.replace(' ','')}-CP{i:02d}</name>
		<description><![CDATA[CANDIDATE control point {i} of {len(cps)} · {'CORRIDOR END ANCHOR (approximate — drag onto the real endpoint)' if n < 0 else f'median longitude of {n} housing points in this latitude band'} · DRAG ME onto the true street centreline · cruise {CRUISE_M:.0f} m]]></description>
		<styleUrl>#m_ylw-pushpin</styleUrl>
		<Point><gx:drawOrder>1</gx:drawOrder>
			<coordinates>{x:.13f},{y:.13f},0</coordinates></Point>
	</Placemark>""")
        kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
	<name>{name} Control Points CANDIDATE</name>
	<description><![CDATA[CANDIDATES ONLY — generated by scripts/gen_tour_control_points.py.
Drag each point onto the true centreline of {name} in Google Earth Pro, add points where the
street bends, delete any that are wrong, then save over this file. Order is {direction} — the flight follows
this order, so reordering the placemarks reorders the flight.]]></description>
	<Style id="s_ylw-pushpin"><IconStyle><scale>1.1</scale>
		<Icon><href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href></Icon>
		<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/></IconStyle></Style>
	<StyleMap id="m_ylw-pushpin">
		<Pair><key>normal</key><styleUrl>#s_ylw-pushpin</styleUrl></Pair>
		<Pair><key>highlight</key><styleUrl>#s_ylw-pushpin</styleUrl></Pair></StyleMap>
	<Folder><name>{name} Control Points</name><open>1</open>
{chr(10).join(pm)}
	</Folder>
</Document>
</kml>
"""
        path = f"{OUT_DIR}/{name} Control Points CANDIDATE.kml"
        open(path, "w").write(kml)
        span = dist_m(cps[0][0], cps[0][1], cps[-1][0], cps[-1][1])
        print(f"{name:12} {len(cps)} control points · {len(pts):>3} housing points · "
              f"{span/1000:.2f} km ({span/1609:.2f} mi) · -> {path}")


if __name__ == "__main__":
    main()
