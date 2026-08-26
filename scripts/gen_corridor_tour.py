#!/usr/bin/env python3
"""gen_corridor_tour.py — build a corridor flyover from hand-placed control points.

THE WORKFLOW (recovered from the Shattuck N->S flight, verified 2026-08-24):
control points are placed by hand in Google Earth Pro and the flight is INTERPOLATED between
them. Shattuck used four points; its tour's first camera matches control point #1 to ten
decimal places and 86 of 112 waypoints sit within 25 m of a control-point segment. No road
dataset is involved -- the human eye on real imagery is the source, and more control points
mean more fidelity on a bend.

CAMERA RULES (John, 2026-08-24):
  cruise altitude       20 m  (standard)
  tower orbit altitude  roof height + 10 m, DERIVED from the building's current extrusion in
                        geometry.kml -- never hardcoded, so it follows height corrections.
                        3030 Telegraph was 35 m until its tabulation put it at 19.2 m.

Usage:
  python scripts/gen_corridor_tour.py "kml/tours/control_points/Telegraph Control Points.kml" \
      --name "Telegraph S-to-N" --orbit "3030 TELEGRAPH,2455 TELEGRAPH" --out kml/tours/telegraph-s2n.kml
  --spacing   metres between cruise waypoints (default 40)
  --speed     metres per second (default 12 ~ 27 mph); sets each leg's duration
  --orbit-secs seconds per full orbit (default 16)
"""
import argparse, math, os, re

CRUISE_M = 25.0          # raised from 20 m per John 2026-08-26 -- at 20 m with tilt 88 the
                         # camera sits very low and Earth Pro can render unlit terrain
                         # underside before tiles stream in
ORBIT_CLEARANCE_M = 10.0        # above roof
ORBIT_RADIUS_MULT = 1.9         # orbit radius as a multiple of the building's effective radius
GEOM = "kml/geometry/geometry.kml"
R = 6371000.0


def read_points(path):
    """Control points in DOCUMENT ORDER — that order is the flight order."""
    t = open(path, errors="replace").read()
    pts = []
    for pm in re.findall(r"<Placemark>.*?</Placemark>", t, re.S):
        nm = re.search(r"<name>([^<]*)</name>", pm)
        m = re.search(r"<coordinates>\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", pm)
        if m:
            pts.append((float(m.group(1)), float(m.group(2)), nm.group(1) if nm else ""))
    return pts


def buildings():
    """{ADDRESS: (lon, lat, roof_m, effective_radius_m)} from the canonical geometry."""
    out = {}
    for pm in re.findall(r"<Placemark>.*?</Placemark>", open(GEOM, errors="replace").read(), re.S):
        ad = re.search(r"<b>([^<]*)</b><br/>", pm)
        po = re.search(r"<Polygon>.*?</Polygon>", pm, re.S)
        if not (ad and po):
            continue
        cs = re.search(r"<coordinates>\s*(.*?)\s*</coordinates>", po.group(0), re.S).group(1)
        ring, roof = [], 0.0
        for tok in cs.split():
            p = tok.split(",")
            ring.append((float(p[0]), float(p[1])))
            if len(p) > 2:
                roof = float(p[2])
        if len(ring) < 4:
            continue
        r = ring[:-1]
        lon = sum(p[0] for p in r)/len(r); lat = sum(p[1] for p in r)/len(r)
        k = math.cos(math.radians(lat))
        rad = max(math.hypot((p[0]-lon)*k, p[1]-lat) for p in r) * 111320
        out[ad.group(1).upper().strip()] = (lon, lat, roof, rad)
    return out


def bearing(a, b):
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dl = lon2 - lon1
    y = math.sin(dl)*math.cos(lat2)
    x = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def dist_m(a, b):
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    dp, dl = p2-p1, math.radians(b[0]-a[0])
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(h))


def flyto(lon, lat, alt, hdg, tilt, dur, mode="smooth"):
    return (f"\t\t\t<gx:FlyTo>\n\t\t\t\t<gx:duration>{dur:.2f}</gx:duration>\n"
            f"\t\t\t\t<gx:flyToMode>{mode}</gx:flyToMode>\n\t\t\t\t<Camera>\n"
            f"\t\t\t\t\t<longitude>{lon:.10f}</longitude>\n\t\t\t\t\t<latitude>{lat:.10f}</latitude>\n"
            f"\t\t\t\t\t<altitude>{alt:.1f}</altitude>\n\t\t\t\t\t<heading>{hdg:.2f}</heading>\n"
            f"\t\t\t\t\t<tilt>{tilt:.1f}</tilt>\n\t\t\t\t\t<roll>0</roll>\n"
            f"\t\t\t\t\t<altitudeMode>relativeToGround</altitudeMode>\n"
            f"\t\t\t\t</Camera>\n\t\t\t</gx:FlyTo>\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("control_points")
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--orbit", default="", help="comma-separated address fragments to orbit")
    ap.add_argument("--spacing", type=float, default=40.0)
    ap.add_argument("--speed", type=float, default=12.0)
    ap.add_argument("--orbit-secs", type=float, default=16.0)
    ap.add_argument("--tilt", type=float, default=88.0)
    ap.add_argument("--cruise", type=float, default=CRUISE_M,
                    help="cruise altitude in metres above ground (default 25)")
    a = ap.parse_args()

    global CRUISE_M
    CRUISE_M = a.cruise
    cps = read_points(a.control_points)
    assert len(cps) >= 2, f"need >=2 control points, found {len(cps)}"
    blds = buildings()
    targets = []
    for frag in [x.strip().upper() for x in a.orbit.split(",") if x.strip()]:
        hit = [(k, v) for k, v in blds.items() if frag in k]
        if not hit:
            print(f"  !! orbit target not found in geometry: {frag}")
            continue
        targets.append(max(hit, key=lambda kv: kv[1][3]))     # largest match

    body, total = [], 0.0
    # establishing shot: from the first point, looking down the corridor
    hdg0 = bearing(cps[0][:2], cps[1][:2])
    body.append(flyto(cps[0][0], cps[0][1], CRUISE_M, hdg0, a.tilt, 0.10, "bounce"))

    orbited = set()
    for i in range(len(cps)-1):
        A, B = cps[i][:2], cps[i+1][:2]
        seg = dist_m(A, B)
        hdg = bearing(A, B)
        n = max(1, int(round(seg / a.spacing)))
        for s in range(1, n+1):
            f = s / n
            lon = A[0] + (B[0]-A[0])*f
            lat = A[1] + (B[1]-A[1])*f
            dur = (seg/n) / a.speed
            body.append(flyto(lon, lat, CRUISE_M, hdg, a.tilt, dur))
            total += dur
            # when the cruise passes a target, orbit it once
            for name, (blon, blat, roof, rad) in targets:
                if name in orbited:
                    continue
                if dist_m((lon, lat), (blon, blat)) < 90:
                    alt = roof + ORBIT_CLEARANCE_M
                    orad = max(rad*ORBIT_RADIUS_MULT, 55.0)
                    steps = 24
                    for j in range(steps+1):
                        th = 2*math.pi*j/steps
                        k = math.cos(math.radians(blat))
                        olon = blon + (orad*math.sin(th)/111320)/k
                        olat = blat + (orad*math.cos(th)/111320)
                        # look inward at the building
                        ohdg = (math.degrees(th) + 180) % 360
                        body.append(flyto(olon, olat, alt, ohdg, 72.0, a.orbit_secs/steps))
                        total += a.orbit_secs/steps
                    orbited.add(name)
                    print(f"  orbit: {name}  roof {roof:.1f} m -> altitude {alt:.1f} m, radius {orad:.0f} m")
                    # resume the cruise heading
                    body.append(flyto(lon, lat, CRUISE_M, hdg, a.tilt, 1.5))
                    total += 1.5

    # STAMP THE NAME. Google Earth treats a loaded KML as a SNAPSHOT, not a live link: re-opening
    # a regenerated file leaves the stale copy in the sidebar and gives no hint it is stale. Same
    # trap that let geometry.kml show a May name for months. So the tour SAYS which build it is --
    # generation time plus a hash of the control points it was built from.
    import hashlib, datetime
    cp_hash = hashlib.sha256(open(a.control_points, "rb").read()).hexdigest()[:6]
    stamp = datetime.datetime.now().strftime("%m-%d %H:%M")
    disp = f"{a.name} · {stamp} · cp-{cp_hash}"
    kml = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">\n'
           f'<Document>\n\t<name>{disp}</name>\n'
           f'\t<description><![CDATA[Generated by scripts/gen_corridor_tour.py from '
           f'{os.path.basename(a.control_points)} ({len(cps)} control points). '
           f'Cruise {CRUISE_M:.0f} m; orbits at roof + {ORBIT_CLEARANCE_M:.0f} m, derived from the '
           f'current extrusion height in geometry.kml. Camera-only: load alongside the geometry, '
           f'or run build_tour_package.py to splice.]]></description>\n'
           f'\t<gx:Tour>\n\t\t<name>{disp}</name>\n\t\t<gx:Playlist>\n'
           + "".join(body) +
           f'\t\t</gx:Playlist>\n\t</gx:Tour>\n</Document>\n</kml>\n')
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w").write(kml)
    print(f"wrote {a.out}\n  name: {disp}\n  {len(cps)} control points -> {kml.count('<gx:FlyTo>')} waypoints, "
          f"{total:.0f}s ({total/60:.1f} min)")


if __name__ == "__main__":
    main()
