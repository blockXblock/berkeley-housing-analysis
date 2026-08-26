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
    """Control points in DOCUMENT ORDER — that order is the flight order.

    Accepts BOTH shapes Google Earth Pro produces:
      * PUSHPINS  — a Placemark per point, each with a <Point><coordinates>lon,lat,alt.
      * A PATH    — one Placemark whose <LineString><coordinates> holds the whole polyline.
        The Path tool ("Add > Path") is far the better way to draw a corridor: you click
        along the street once per bend instead of opening a properties dialog per pushpin,
        and every vertex is a control point, so a curving street traces exactly.

    A KMZ is a zip containing doc.kml; it is unpacked transparently, because Earth Pro's
    Save Place As defaults to KMZ and that has already cost us one round trip.
    """
    if path.lower().endswith(".kmz"):
        import zipfile
        with zipfile.ZipFile(path) as z:
            inner = next(n for n in z.namelist() if n.lower().endswith(".kml"))
            t = z.read(inner).decode("utf-8", "replace")
    else:
        t = open(path, errors="replace").read()

    pts = []
    for pm in re.findall(r"<Placemark>.*?</Placemark>", t, re.S):
        nm = re.search(r"<name>([^<]*)</name>", pm)
        label = nm.group(1) if nm else ""
        ls = re.search(r"<LineString>.*?<coordinates>\s*(.*?)\s*</coordinates>", pm, re.S)
        if ls:                                   # a PATH: every vertex is a control point
            for i, tok in enumerate(ls.group(1).split()):
                c = tok.split(",")
                if len(c) >= 2:
                    pts.append((float(c[0]), float(c[1]), f"{label}-v{i+1:02d}"))
            continue
        m = re.search(r"<Point>.*?<coordinates>\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", pm, re.S)
        if not m:                                # tolerate a bare <coordinates> with no <Point>
            m = re.search(r"<coordinates>\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", pm)
        if m:
            pts.append((float(m.group(1)), float(m.group(2)), label))
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



def side_of_path(a, b, target):
    """Which side of the flight direction does the target lie on?
    +1 = RIGHT of travel, -1 = LEFT. Cross product of the heading vector with the
    vector to the target, in a local flat frame. Kept for reporting; the orbit
    DIRECTION is decided by orbit_direction_cw() below."""
    k = math.cos(math.radians(a[1]))
    hx, hy = (b[0]-a[0])*k, (b[1]-a[1])
    tx, ty = (target[0]-a[0])*k, (target[1]-a[1])
    cross = hx*ty - hy*tx
    return -1 if cross > 0 else 1          # cross>0 means target is LEFT of heading


def orbit_direction_cw(entry_deg, flight_hdg_deg):
    """CONTINUE IN THE DIRECTION OF FLIGHT out of the tangent point (John, 2026-08-26).

    A point on the circle is centre + r*(sin th, cos th) in (east, north), so INCREASING th
    runs clockwise. Its tangent is d/dth = (cos th, -sin th). The flight heading vector is
    (sin h, cos h). Their dot product is sin(h - th): positive means clockwise carries the
    camera ONWARD along its current heading, negative means it would double back.

    This is the general form of "right -> clockwise, left -> anticlockwise" -- it yields the
    same answer for a path passing beside a building, but stays correct where the side test
    is ambiguous, e.g. a path aimed nearly at the centroid."""
    return math.sin(math.radians(flight_hdg_deg - entry_deg)) > 0


def circle_entry_angle(a, b, centre, radius_m):
    """Where does the segment a->b first cross the circle of radius_m about centre?
    Returns the BEARING FROM THE CENTRE to that crossing, in degrees, or None.

    Entering the orbit at the point where the flight path actually MEETS the circle is
    what makes it smooth: the camera arrives on the circle already travelling along it,
    instead of cutting to an arbitrary start angle and back again."""
    k = math.cos(math.radians(centre[1]))
    M = 111320.0
    ax, ay = (a[0]-centre[0])*k*M, (a[1]-centre[1])*M
    bx, by = (b[0]-centre[0])*k*M, (b[1]-centre[1])*M
    dx, dy = bx-ax, by-ay
    A = dx*dx + dy*dy
    if A == 0:
        return None
    B = 2*(ax*dx + ay*dy)
    C = ax*ax + ay*ay - radius_m*radius_m
    disc = B*B - 4*A*C
    if disc < 0:
        return None                        # the segment never reaches the circle
    r = math.sqrt(disc)
    for t in sorted(((-B - r)/(2*A), (-B + r)/(2*A))):
        if 0.0 <= t <= 1.0:
            px, py = ax + dx*t, ay + dy*t
            return (math.degrees(math.atan2(px, py)) + 360) % 360   # bearing from centre
    return None


def seg_perp_m(p, a, b):
    """Perpendicular distance in metres from p to the segment a-b."""
    k = math.cos(math.radians(p[1])); M = 111320.0
    ax, ay = (a[0]-p[0])*k*M, (a[1]-p[1])*M
    bx, by = (b[0]-p[0])*k*M, (b[1]-p[1])*M
    dx, dy = bx-ax, by-ay
    L2 = dx*dx + dy*dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, -(ax*dx + ay*dy)/L2))
    return math.hypot(ax + dx*t, ay + dy*t)


def polar(centre, pt):
    """(radius_m, bearing_deg) of pt relative to centre."""
    k = math.cos(math.radians(centre[1]))
    e = (pt[0]-centre[0])*k*111320.0
    n = (pt[1]-centre[1])*111320.0
    return math.hypot(e, n), (math.degrees(math.atan2(e, n)) + 360) % 360


def from_polar(centre, r_m, th_deg):
    k = math.cos(math.radians(centre[1]))
    r = math.radians(th_deg)
    return (centre[0] + (r_m*math.sin(r)/111320.0)/k,
            centre[1] + (r_m*math.cos(r)/111320.0))


def spiral(centre, r0, th0, r1, th1, alt0, alt1, tilt0, tilt1, hdg0, steps, secs,
           face_at_end=True):
    """Sweep from (r0,th0) to (r1,th1) about a centre, easing radius, altitude and tilt.

    WHY A SPIRAL AND NOT A TANGENTIAL FILLET: these corridors run 25-40 m from their towers
    while the orbit radius is 55 m or more, so the flight is INSIDE the circle at closest
    approach. There is no tangential entry from inside a circle -- every fillet attempt had
    to double back to reach the rim (measured: 25 waypoint-turns over 90 degrees). A spiral
    simply grows the radius while it sweeps, so the camera eases outward onto the orbit
    without ever reversing.
    """
    out = []
    dth = ((th1 - th0 + 540) % 360) - 180
    for j in range(1, steps+1):
        f = j/steps
        e = f*f*(3-2*f)
        th = th0 + dth*f
        r = r0 + (r1-r0)*e
        lon, lat = from_polar(centre, r, th)
        face = (th + 180.0) % 360.0
        if face_at_end:
            dh = ((face - hdg0 + 540) % 360) - 180
            hdg = (hdg0 + dh*e) % 360
        else:
            hdg = face
        out.append((lon, lat, alt0 + (alt1-alt0)*e,
                    hdg, tilt0 + (tilt1-tilt0)*e, secs/steps))
    return out


def orbit_waypoints(centre, radius_m, alt, start_deg, clockwise, steps, secs,
                    cruise_alt, ramp_frac=0.18):
    """One full circle, entered and left at start_deg.

    - direction follows which side the building is on, so the camera turns TOWARD it
    - the camera looks at the centroid throughout
    - altitude and tilt EASE between cruise and orbit values over the first and last
      ramp_frac of the circle, so there is no step change at the join
    """
    out = []
    k = math.cos(math.radians(centre[1]))
    for j in range(steps + 1):
        f = j / steps
        th = start_deg + (360.0 * f) * (1 if clockwise else -1)
        rad = math.radians(th)
        lon = centre[0] + (radius_m*math.sin(rad)/111320.0)/k
        lat = centre[1] + (radius_m*math.cos(rad)/111320.0)
        heading = (th + 180.0) % 360.0                  # face the centroid
        # ease altitude/tilt in and out so the join is continuous
        if f < ramp_frac:
            e = f/ramp_frac
        elif f > 1-ramp_frac:
            e = (1-f)/ramp_frac
        else:
            e = 1.0
        e = e*e*(3-2*e)                                  # smoothstep
        a = cruise_alt + (alt - cruise_alt)*e
        tilt = 88.0 + (72.0 - 88.0)*e
        out.append((lon, lat, a, heading, tilt, secs/steps))
    return out


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
    ap.add_argument("--orbit-dir", choices=["continue","flip"], default="continue",
                    help="continue = sweep the way the flight is already going; "
                         "flip = the opposite sense (John's proposal, 2026-08-26)")
    ap.add_argument("--cruise", type=float, default=25.0,
                    help="cruise altitude in metres above ground (default 25)")
    a = ap.parse_args()

    cruise = a.cruise          # explicit, not a mutated global
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

    # TRUE closest approach of the whole path to each target. Measuring against only the
    # current segment gave 275 m for 2550 Shattuck -- the orbit triggered on a segment far
    # from the building, so 'closest' was nonsense. This is per-target, over every segment.
    closest_m = {}
    for nm, (bx, by, _r, _rad) in targets:
        closest_m[nm] = min(seg_perp_m((bx, by), cps[i][:2], cps[i+1][:2])
                            for i in range(len(cps)-1))

    body, total = [], 0.0
    # establishing shot: from the first point, looking down the corridor
    hdg0 = bearing(cps[0][:2], cps[1][:2])
    body.append(flyto(cps[0][0], cps[0][1], cruise, hdg0, a.tilt, 0.10, "bounce"))

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
            # ORBIT CHECK COMES FIRST. Emitting the cruise waypoint before testing for the circle
            # crossing flew the camera PAST the tangent point and then jumped it BACKWARDS onto
            # the entry -- a 133-157 degree reversal on every orbit (measured, 6 of 6 on Shattuck,
            # 2026-08-26). The entry lies between prev and this waypoint, so the orbit must be
            # emitted BEFORE we advance to it.
            for name, (blon, blat, roof, rad) in targets:
                if name in orbited:
                    continue
                # TANGENT RADIUS (John, 2026-08-26): use the path's OWN closest approach as the
                # orbit radius wherever it is safe. Then the flight is tangent to the circle by
                # construction -- the camera is already at orbit radius when it arrives, the
                # spiral has no radius to make up, and the 'detect, retreat, advance' vanishes.
                # Enlarged only as far as the building itself demands (1.35x its own radius).
                dmin = closest_m[name]
                # a hair MORE than the closest approach: at exactly tangent the line/circle
                # discriminant is ~0 and the crossing test misses it entirely (2655 Shattuck
                # silently lost its orbit). 3% + 1 m keeps it effectively tangent while
                # guaranteeing a detectable crossing.
                # rad is the CIRCUMRADIUS of the footprint (furthest vertex from the
                # centroid) -- we treat the building as a CIRCLE in plan, not a sphere; the
                # extrusion height plays no part in it. A 1.35x circumradius orbit still let the
                # camera clip the extruded mass, because a long thin footprint fills far more of
                # the frame than its circumradius suggests and the near plane cuts into it.
                # 2.2x with a 60 m floor keeps the whole tower in shot.
                orad = max(dmin*1.03 + 1.0, rad*2.2, 60.0)
                # ENTER WHERE THE PATH ACTUALLY MEETS THE CIRCLE, not at an arbitrary angle.
                prev = (A[0] + (B[0]-A[0])*((s-1)/n), A[1] + (B[1]-A[1])*((s-1)/n))
                entry = circle_entry_angle(prev, (lon, lat), (blon, blat), orad)
                if entry is None:
                    continue
                alt = roof + ORBIT_CLEARANCE_M
                # turn TOWARD the building: right-hand targets clockwise, left-hand anticlockwise
                side = "right" if side_of_path(A, B, (blon, blat)) > 0 else "left"
                r_now, th_now = polar((blon, blat), (lon, lat))
                # The sweep must continue the flight from th_now, the camera's ACTUAL bearing
                # from the building -- not from `entry`, the bearing where the straight line
                # crossed the circle. Those differ, and choosing the direction from `entry` sent
                # the spiral backwards whenever they disagreed. That was the residual retreat.
                cw = orbit_direction_cw(th_now, hdg)
                if a.orbit_dir == "flip":
                    cw = not cw
                # sgn MUST be derived AFTER cw is final. It was computed from the earlier
                # `entry`-based cw and never updated, so the th_now retreat fix claimed in
                # e3003d1 was a NO-OP: the console printed the corrected direction while the
                # geometry kept using the old one. That is why the retreat survived the fix.
                sgn = 1 if cw else -1
                bsec = a.orbit_secs * 0.30
                LEAD = 80.0                        # degrees swept while easing onto the rim
                th_rim = th_now + sgn*LEAD
                # EASE THE DIRECTION IN, not just the radius. The spiral's first step already
                # runs tangentially around the building, which is 43-54 deg off the flight
                # heading -- so the camera swerved that far in ONE waypoint (cruise step 43.6 m
                # at 3 deg, then orbit step 4.0 m at 43 deg). No reversal, but it reads as one.
                # For the first stretch we blend each spiral position against where the camera
                # would have been had it just carried straight on, so the turn is spread out.
                sp = spiral((blon, blat), max(r_now, 8.0), th_now, orad, th_rim,
                            cruise, alt, a.tilt, 72.0, hdg, 16, bsec)
                k3 = math.cos(math.radians(lat)); hr3 = math.radians(hdg)
                travel = a.speed * (bsec/16)            # metres the camera covers per step
                EASE = 8                                 # steps over which to fold the turn in
                for j, w in enumerate(sp):
                    if j < EASE:
                        e = (j+1)/EASE
                        e = e*e*(3-2*e)
                        straight = (lon + ((travel*(j+1))*math.sin(hr3)/111320.0)/k3,
                                    lat + ((travel*(j+1))*math.cos(hr3)/111320.0))
                        w = (straight[0] + (w[0]-straight[0])*e,
                             straight[1] + (w[1]-straight[1])*e,
                             w[2], w[3], w[4], w[5])
                    body.append(flyto(*w)); total += w[5]
                # the orbit proper
                for j in range(1, 31):
                    th = th_rim + sgn*(360.0 - 2*LEAD)*(j/30)
                    q = from_polar((blon, blat), orad, th)
                    body.append(flyto(q[0], q[1], alt, (th+180) % 360, 72.0, a.orbit_secs/30))
                    total += a.orbit_secs/30
                # ease back IN to the corridor, releasing on the cruise heading
                th_end = th_rim + sgn*(360.0 - 2*LEAD)
                for w in spiral((blon, blat), orad, th_end, max(r_now, 8.0), th_end + sgn*LEAD,
                                alt, cruise, 72.0, a.tilt, hdg, 12, bsec, face_at_end=False):
                    body.append(flyto(w[0], w[1], w[2], w[3], w[4], w[5])); total += w[5]
                orbited.add(name)
                print(f"  orbit: {name}  roof {roof:.1f} m -> {alt:.1f} m, r {orad:.0f} m, "
                      f"enter {entry:.0f}deg, {'CW' if cw else 'CCW'} (building {side})")
            # now advance along the corridor
            body.append(flyto(lon, lat, cruise, hdg, a.tilt, dur))
            total += dur

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
           f'Cruise {cruise:.0f} m; orbits at roof + {ORBIT_CLEARANCE_M:.0f} m, derived from the '
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
