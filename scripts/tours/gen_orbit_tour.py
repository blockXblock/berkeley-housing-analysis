#!/usr/bin/env python3
"""gen_orbit_tour.py — a low orbit around every Elmwood/Claremont FUTURE site (John, 2026-10-23).

THE SHOTS, as John asked for them:
  1. OPEN looking toward the Claremont Hotel, with the Wells Fargo lot (2711 Ashby Pl) in the centre
     and the 7-Eleven (north) and the post office (south) at the sides of the frame. The camera is low
     enough that the hotel sits near the top. The heading is the bearing from the lot to the hotel
     (about 76 degrees, east-northeast), so the hotel is centred left to right.
  2. ORBIT several times around the FUTURE sites on College Ave (zone C-E; --zone, John 2026-10-23: "make
     orbit just around the College avenue structures"), not Claremont & Ashby. The centre is the mean of
     those sites; the radius clears the farthest one by --clear metres.
  3. END over Russell St at Benvenue, looking straight east along Russell: the 7-Eleven on the left,
     2901 College on the right, the Claremont Hotel at the far end.

ALTITUDE stays 200-300 ft (61-91 m) throughout; 2026-10-23 redo: 30 ft lower everywhere and the opening
camera closer to the Wells Fargo lot (372 -> 250 m), so every keyframe is a Camera with
altitudeMode relativeToGround (height above the ground UNDER THE CAMERA), not a LookAt, whose camera
height follows the ground at the point looked at. The aim assumes flat ground, so where the hills
rise east of Claremont Ave the orbit's centre can drift a few degrees in the frame.

Camera-only: load with geometry.kml, college-elmwood.kml, college-opportunity-sites.kml and
elmwood-labels.kmz.

  python3 -m scripts.tours.gen_orbit_tour --out kml/tours/elmwood-orbit.kml
"""
import argparse, datetime, json, math
from xml.sax.saxutils import escape

SUMMARY = "data/derived/opportunity_sites_summary.json"
WELLS_FARGO = (37.857331, -122.252475)       # the lot's centroid, from the summary
HOTEL = (37.8594506, -122.2420517)           # Claremont Resort & Club, OSM way 41745855
RUSSELL_BENVENUE = (37.858320, -122.254405)  # City street-segment node
RUSSELL_CLAREMONT = (37.859006, -122.244575)
FT = 0.3048

KX = 111320.0 * math.cos(math.radians(37.858))
KY = 111320.0


def bearing(a, b):
    return math.degrees(math.atan2((b[1] - a[1]) * KX, (b[0] - a[0]) * KY)) % 360


def back_off(p, heading, d):
    """The point d metres behind p, for a camera at p's far side looking along heading."""
    h = math.radians(heading)
    return (p[0] - d * math.cos(h) / KY, p[1] - d * math.sin(h) / KX)


def camera(lat, lon, alt, heading, tilt, dur, mode="smooth"):
    return (f"\t\t\t<gx:FlyTo><gx:duration>{dur:.2f}</gx:duration><gx:flyToMode>{mode}</gx:flyToMode>\n"
            f"\t\t\t\t<Camera><longitude>{lon:.7f}</longitude><latitude>{lat:.7f}</latitude><altitude>{alt:.1f}</altitude>"
            f"<heading>{heading % 360:.2f}</heading><tilt>{tilt:.2f}</tilt><roll>0</roll>"
            f"<altitudeMode>relativeToGround</altitudeMode></Camera>\n\t\t\t</gx:FlyTo>\n")


def wait(s):
    return f"\t\t\t<gx:Wait><gx:duration>{s:.2f}</gx:duration></gx:Wait>\n"


def aim(target, alt, heading, dist):
    """Camera dist metres behind target at alt, its centre ray landing on target (flat ground)."""
    lat, lon = back_off(target, heading, dist)
    return lat, lon, alt, heading, 90 - math.degrees(math.atan2(alt, dist))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="College Ave orbit · FUTURE sites")
    ap.add_argument("--open-dist", type=float, default=250.0, help="m from the Wells Fargo lot")
    ap.add_argument("--open-alt", type=float, default=76.2, help="m above ground (250 ft)")
    ap.add_argument("--alt", type=float, default=76.2, help="orbit height above ground, m (250 ft)")
    ap.add_argument("--clear", type=float, default=150.0, help="orbit radius beyond the farthest site, m")
    ap.add_argument("--zone", default="C-E", help="orbit only the FUTURE sites in this zone (C-E = College Ave); 'all' for every site")
    ap.add_argument("--turns", type=float, default=3.0)
    ap.add_argument("--secs", type=float, default=150.0, help="orbit duration")
    ap.add_argument("--end-alt", type=float, default=70.1, help="m above Russell St (230 ft)")
    ap.add_argument("--end-tilt", type=float, default=80.0)
    a = ap.parse_args()
    for alt in (a.open_alt, a.alt, a.end_alt):
        assert 200 * FT <= alt <= 300 * FT, f"altitude {alt} m is outside 200-300 ft"

    sites = [(d["lat"], d["lon"]) for d in json.load(open(SUMMARY)) if d["kind"] == "future" and a.zone in ("all", d["zone"])]
    c = (sum(s[0] for s in sites) / len(sites), sum(s[1] for s in sites) / len(sites))
    far = max(math.hypot((s[0] - c[0]) * KY, (s[1] - c[1]) * KX) for s in sites)
    radius = far + a.clear

    h_open = bearing(WELLS_FARGO, HOTEL)
    h_end = bearing(RUSSELL_BENVENUE, RUSSELL_CLAREMONT)
    sweep = (h_end - h_open) % 360 + 360 * round(a.turns)     # finish facing east along Russell
    step = 3.0
    n = int(round(sweep / step))
    dur = a.secs / n

    body = [camera(*aim(WELLS_FARGO, a.open_alt, h_open, a.open_dist), 0.1, "bounce"), wait(8)]
    body.append(camera(*aim(c, a.alt, h_open, radius), 8))     # glide out to the orbit, same heading
    for i in range(1, n + 1):
        body.append(camera(*aim(c, a.alt, h_open + sweep * i / n, radius), dur))
    end_lat, end_lon = RUSSELL_BENVENUE
    body.append(camera(end_lat, end_lon, a.end_alt, h_end, a.end_tilt, 10))
    body.append(wait(10))
    total = 0.1 + 8 + 8 + a.secs + 10 + 10

    stamp = datetime.datetime.now().strftime("%m-%d %H:%M")
    name = escape(f"{a.name} · {stamp}")
    open(a.out, "w").write(f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
	<name>{name}</name>
	<description><![CDATA[Generated by scripts/tours/gen_orbit_tour.py. Opens on the Wells Fargo lot looking toward the Claremont Hotel (heading {h_open:.0f}); orbits {round(a.turns)} times around {len(sites)} FUTURE sites (centre {c[0]:.5f},{c[1]:.5f}, radius {radius:.0f} m) at {a.alt / FT:.0f} ft; ends over Russell at Benvenue looking east (heading {h_end:.0f}). Camera-only: load with geometry.kml, college-elmwood.kml, college-opportunity-sites.kml and elmwood-labels.kmz.]]></description>
	<gx:Tour>
		<name>{name}</name>
		<gx:Playlist>
{"".join(body)}		</gx:Playlist>
	</gx:Tour>
</Document>
</kml>
""")
    print(f"wrote {a.out}: open heading {h_open:.1f}, orbit centre {c[0]:.6f},{c[1]:.6f} radius {radius:.0f} m, "
          f"{n} steps over {sweep:.0f} deg, end heading {h_end:.1f}; {total:.0f} s")


if __name__ == "__main__":
    main()
