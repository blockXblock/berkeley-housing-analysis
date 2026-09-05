#!/usr/bin/env python3
"""gen_building_loop.py — a standalone reveal for ONE building: look down, then spiral in.

WHY STANDALONE. Every failure in the corridor-tour work came from joining a loop to a flight
path: the manoeuvre had to be inserted at a position the camera had already passed, in seven
different disguises. A loop with NO corridor has no join, so that whole class of bug cannot
occur. These clips are meant to be cut into the corridor footage in an editor, which also lets
the length of each building's moment be an editorial choice rather than a geometric one.

THE SHOT (John's spec, 2026-08-26): "vertical spirals and look-down-through-building that shows
the building labels and data".
  1. PLAN VIEW   - high above, camera straight down. The footprint reads as a shape and the
                   placemark label sits legibly beside it.
  2. SPIRAL IN   - descend and tilt up while circling, so the flat plan becomes a solid mass.
  3. EYE LEVEL   - a final turn at roof + clearance, the building filling the frame.

Altitudes derive from the building's own extrusion in geometry.kml, so a corrected height
changes the shot automatically.

Usage:
  python scripts/gen_building_loop.py --address "2190 SHATTUCK" --out kml/tours/loops/2190.kml
  python scripts/gen_building_loop.py --all-over 100 --outdir kml/tours/loops
"""
import argparse, math, os, re

GEOM = "kml/geometry/geometry.kml"
M = 111320.0


def placemark_name(pm):
    """The building's identity, however this KML happens to record it.

    Two conventions are in play and both are legitimate. The canonical geometry.kml puts the
    ADDRESS in a CDATA description as <b>2116 ALLSTON WAY</b><br/>. panoramic-kennedy-legacy.kml
    puts the PROJECT NAME in <name> ("GAIA Building (2001) - 91 units") and the address in a plain
    <description>. Parsing only the first found NOTHING in the second, which is why a
    self-contained tour could not be labelled at all. Address first where it exists, because that
    is what v2 joins on; the project name only when there is no address to be had.

    Lives here rather than in svg_label_tour because both this module and that one need it, and a
    second copy is how the two drift apart -- the same reason normkey moved into gen_svg_labels.
    """
    m = re.search(r"<b>([^<]*)</b><br/>", pm)
    if m:
        return m.group(1).upper().strip()
    m = re.search(r"<description>(?!<!\[CDATA)([^<]+)</description>", pm)
    if m and re.search(r"\d", m.group(1)):
        return m.group(1).upper().strip()
    # The <name> fallback REQUIRES a digit. Without that guard it swept three unaddressed
    # placemarks in the canonical geometry into the site list -- DHARMA UNIVERSITY and two
    # INNOVATION ZONEs -- which had never been label targets and would have become them
    # silently. A generalisation that changes the behaviour of the path it was not written for
    # is a regression, however harmless it looks.
    m = re.search(r"<name>([^<]+)</name>", pm)
    return m.group(1).upper().strip() if m and re.search(r"\d", m.group(1)) else None


def buildings(geom=None):
    """{ADDRESS: (lon, lat, roof_m, circumradius_m, label)} — ONE ENTRY PER SITE.

    `geom` defaults to the canonical geometry.kml. Pass a path to read a SELF-CONTAINED tour
    instead -- panoramic-kennedy-legacy.kml carries its own 23 polygons, none of which are in the
    canonical file, so with the path hardcoded the label engine could not see a single one of them.

    SITES, NOT LAST-WINS (fixed 2026-08-26). This dict used to be built with a plain
    `out[address] = ...` inside the placemark loop, so when several placemarks share one
    address the LAST one in document order silently won. That is not a rare case: it is
    exactly the multi-building projects. 1750 Sacramento St carries all 13 North Berkeley
    BART buildings, so the "1750 Sacramento · 739 units" loop was orbiting *Avalon Walk-up
    E* — a 10.5 m three-storey block at a 14 m radius, 96 m north of the site centre, with
    the eight-storey buildings out of frame entirely. Ashby BART (5 buildings) picked MLK
    Building E and missed the Adeline Tower; 2556 Haste picked the shorter South wing.

    So a shared address is now aggregated into ONE SITE: centroid over the union of every
    ring, roof = the TALLEST member (the shot has to clear the tallest thing in it), radius
    = the circumradius of the union. A one-placemark address behaves exactly as before.
    """
    groups = {}
    order = []
    for pm in re.findall(r"<Placemark>.*?</Placemark>", open(geom or GEOM, errors="replace").read(), re.S):
        ad_s = placemark_name(pm)
        nm = re.search(r"<name>([^<]*)</name>", pm)
        po = re.search(r"<Polygon>.*?</Polygon>", pm, re.S)
        if not (ad_s and po):
            continue
        cs = re.search(r"<coordinates>\s*(.*?)\s*</coordinates>", po.group(0), re.S).group(1)
        ring, roof = [], 0.0
        for tok in cs.split():
            p = tok.split(",")
            ring.append((float(p[0]), float(p[1])))
            if len(p) > 2:
                roof = max(roof, float(p[2]))
        if len(ring) < 4:
            continue
        k = ad_s
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append((ring[:-1], roof, nm.group(1) if nm else ad_s))

    out = {}
    for k in order:
        members = groups[k]
        pts = [p for ring, _, _ in members for p in ring]
        lon = sum(p[0] for p in pts)/len(pts)
        lat = sum(p[1] for p in pts)/len(pts)
        kk = math.cos(math.radians(lat))
        rad = max(math.hypot((p[0]-lon)*kk, (p[1]-lat)) for p in pts) * M
        roof = max(m[1] for m in members)
        out[k] = (lon, lat, roof, rad, site_label(members))
    return out


def site_label(members):
    """A multi-building site must not be titled after one of its buildings.

    Naming the site after its tallest member ("North Berkeley BART: Avalon (8 st)") reads as
    a claim about one building. Use the members' COMMON NAME PREFIX instead — the 13 BART
    names share "North Berkeley BART: ", the two 2556 Haste names share "2556 Haste St · " —
    and say how many buildings are in the shot. A unit count is carried through only when
    every member agrees on it, so it can never be a single wing's number.
    """
    if len(members) == 1:
        return members[0][2]
    names = [m[2] for m in members]
    pre = os.path.commonprefix(names).rstrip()
    pre = re.sub(r"[:·,\-]+$", "", pre).strip() or names[0]
    units = {u.group(1) for u in (re.search(r"(\d+) units", n) for n in names) if u}
    unit_part = f" · {units.pop()} units" if len(units) == 1 else ""
    return f"{pre}{unit_part} · {len(members)} buildings · site"


def cam(lon, lat, alt, hdg, tilt, dur, mode="smooth"):
    return (f"\t\t\t<gx:FlyTo>\n\t\t\t\t<gx:duration>{dur:.2f}</gx:duration>\n"
            f"\t\t\t\t<gx:flyToMode>{mode}</gx:flyToMode>\n\t\t\t\t<Camera>\n"
            f"\t\t\t\t\t<longitude>{lon:.10f}</longitude>\n\t\t\t\t\t<latitude>{lat:.10f}</latitude>\n"
            f"\t\t\t\t\t<altitude>{alt:.1f}</altitude>\n\t\t\t\t\t<heading>{hdg:.2f}</heading>\n"
            f"\t\t\t\t\t<tilt>{tilt:.1f}</tilt>\n\t\t\t\t\t<roll>0</roll>\n"
            f"\t\t\t\t\t<altitudeMode>relativeToGround</altitudeMode>\n"
            f"\t\t\t\t</Camera>\n\t\t\t</gx:FlyTo>\n")


def build(name, lon, lat, roof, rad, label, plan_secs, spiral_secs, close_secs, turns):
    # RADIUS MUST ACCOUNT FOR HEIGHT, NOT JUST PLAN EXTENT (John, 2026-08-26). A circumradius
    # rule alone put 2200 Bancroft -- 79.5 m tall -- at a 60 m orbit, where the camera cranes
    # almost straight up and the tower will not fit the frame. Adding a height term (1.3x) keeps
    # the whole structure in shot: a building roughly fills the vertical field when the orbit
    # radius is a little over its height.
    orad = max(rad*2.2, roof*1.3, 60.0)
    plan_alt = max(roof*3.0, orad*2.2, 180.0)          # high enough that the label sits clear
    eye_alt = roof + 10.0
    k = math.cos(math.radians(lat))
    body = []

    # 1. PLAN VIEW — straight down, holding, so the footprint and label can be read
    n1 = 12
    for j in range(n1):
        hdg = 360.0*j/n1*0.25                # a slow quarter-turn so it is not static
        body.append(cam(lon, lat, plan_alt, hdg, 0.0, plan_secs/n1,
                        "bounce" if j == 0 else "smooth"))

    # 2. SPIRAL IN — descend, tilt up, and swing out to the orbit radius while turning
    n2 = int(36*turns)
    for j in range(1, n2+1):
        f = j/n2
        e = f*f*(3-2*f)
        th = 360.0*turns*f
        r = orad*e                            # from directly overhead out to the rim
        a = plan_alt + (eye_alt-plan_alt)*e
        tilt = 0.0 + (72.0-0.0)*e
        clon = lon + (r*math.sin(math.radians(th))/M)/k
        clat = lat + (r*math.cos(math.radians(th))/M)
        body.append(cam(clon, clat, a, (th+180) % 360, tilt, spiral_secs/n2))

    # 3. EYE LEVEL — one clean turn at the rim with the building filling the frame
    n3 = 36
    start = 360.0*turns
    for j in range(1, n3+1):
        th = start + 360.0*(j/n3)
        clon = lon + (orad*math.sin(math.radians(th))/M)/k
        clat = lat + (orad*math.cos(math.radians(th))/M)
        body.append(cam(clon, clat, eye_alt, (th+180) % 360, 72.0, close_secs/n3))

    total = plan_secs + spiral_secs + close_secs
    disp = f"{label} · loop"
    kml = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">\n'
           f'<Document>\n\t<name>{disp}</name>\n'
           f'\t<description><![CDATA[Standalone building loop, generated by '
           f'scripts/gen_building_loop.py. Plan view {plan_alt:.0f} m -> spiral -> '
           f'{turns:.1f} turns -> eye level {eye_alt:.0f} m at radius {orad:.0f} m. '
           f'Altitudes derive from this building\'s extrusion height ({roof:.1f} m), so a '
           f'corrected height re-cuts the shot. Load alongside geometry.kml.]]></description>\n'
           f'\t<gx:Tour>\n\t\t<name>{disp}</name>\n\t\t<gx:Playlist>\n'
           + "".join(body) +
           f'\t\t</gx:Playlist>\n\t</gx:Tour>\n</Document>\n</kml>\n')
    return kml, total, orad, plan_alt, eye_alt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--address"); ap.add_argument("--out")
    ap.add_argument("--all-over", type=int, help="generate for every building with >= N units")
    ap.add_argument("--outdir", default="kml/tours/loops")
    ap.add_argument("--plan-secs", type=float, default=11.0)
    ap.add_argument("--spiral-secs", type=float, default=26.0)
    ap.add_argument("--close-secs", type=float, default=22.0)
    ap.add_argument("--turns", type=float, default=1.25)
    a = ap.parse_args()
    B = buildings()

    picks = []
    if a.address:
        hits = [(k, v) for k, v in B.items() if a.address.upper() in k]
        if not hits:
            raise SystemExit(f"not found: {a.address}")
        picks = [max(hits, key=lambda kv: kv[1][3])]
    else:
        import sqlite3
        c = sqlite3.connect("databases/berkeley_housing_v2.db")
        units = {(r[0] or "").upper().strip(): (r[1] or 0) for r in
                 c.execute("select address_display,total_units from v_projects_flat")}
        picks = [(k, v) for k, v in B.items() if units.get(k, 0) >= (a.all_over or 0)]
        picks.sort(key=lambda kv: -units.get(kv[0], 0))

    os.makedirs(a.outdir, exist_ok=True)
    for name, (lon, lat, roof, rad, label) in picks:
        kml, total, orad, pa, ea = build(name, lon, lat, roof, rad, label,
                                         a.plan_secs, a.spiral_secs, a.close_secs, a.turns)
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        path = a.out if (a.out and a.address) else f"{a.outdir}/{slug}.kml"
        open(path, "w").write(kml)
        print(f"  {name[:26]:28} roof {roof:>5.1f} m · r {orad:>5.0f} m · "
              f"plan {pa:>4.0f} m -> eye {ea:>5.1f} m · {total:.0f}s -> {path}")
    print(f"\n{len(picks)} loop(s)")


if __name__ == "__main__":
    main()
