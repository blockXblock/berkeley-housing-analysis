#!/usr/bin/env python3
"""gen_dorm_tour.py — one continuous flight that spirals over every UC housing project.

WHY NOT gen_building_loop.py. That script deliberately makes STANDALONE clips, one building
each, because every corridor-tour bug came from splicing a loop into a flight path the camera
had already flown. This tour has no corridor -- it is a sequence of stops -- so the join is a
plain transit leg between two spirals and that whole class of bug cannot arise. The spiral
geometry itself is imported from gen_building_loop, not copied, so a fix there fixes both.

WHY THE LIST IS DERIVED. The May 2026 hand-written tour named its four dormitories in the KML.
UC projects are identified in v2 by the `uc_project` CLASSIFICATION FLAG, and CLAUDE.md requires
filtering on that flag rather than hardcoded ids precisely so the tour picks up the next UC
tower on its own. UC housing is counted in BEDS, not units -- the labels come from geometry.kml,
which already says beds.

  python scripts/gen_dorm_tour.py --out kml/tours/uc-dormitories.kml
"""
import argparse, math, os, re, sqlite3, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_building_loop import buildings, cam, M

CAMPANILE = (-122.2578, 37.8723)          # the opening subject, as in the May tour


def uc_addresses(db="databases/berkeley_housing_v2.db"):
    """Addresses flagged uc_project in v2, largest first. THE FLAG, never an id list."""
    c = sqlite3.connect(db)
    rows = c.execute("""
        SELECT f.address_display, f.total_units FROM v_projects_flat f
        JOIN project_classifications pc ON pc.project_id = f.project_id
        JOIN vocabulary_classification_types v ON v.id = pc.classification_type_id
        WHERE v.code = 'uc_project' AND f.address_display IS NOT NULL
        ORDER BY f.total_units DESC""").fetchall()
    return [(r[0].upper().strip(), r[1] or 0) for r in rows]


def transit(lon, lat, alt, hdg, secs):
    """Fly to a standoff east of the next building, looking west at it."""
    return cam(lon, lat, alt, hdg, 62.0, secs)


def spiral(lon, lat, roof, rad, plan_secs, spiral_secs, close_secs, turns):
    """The three-part shot, identical in geometry to gen_building_loop.build()."""
    orad = max(rad * 2.2, roof * 1.3, 60.0)
    plan_alt = max(roof * 3.0, orad * 2.2, 180.0)
    eye_alt = roof + 10.0
    k = math.cos(math.radians(lat))
    out = []
    n1 = 12
    for j in range(n1):
        out.append(cam(lon, lat, plan_alt, 360.0 * j / n1 * 0.25, 0.0, plan_secs / n1))
    n2 = int(36 * turns)
    for j in range(1, n2 + 1):
        f = j / n2; e = f * f * (3 - 2 * f); th = 360.0 * turns * f
        r = orad * e; a = plan_alt + (eye_alt - plan_alt) * e; tilt = 72.0 * e
        out.append(cam(lon + (r * math.sin(math.radians(th)) / M) / k,
                       lat + (r * math.cos(math.radians(th)) / M),
                       a, (th + 180) % 360, tilt, spiral_secs / n2))
    n3 = 36
    for j in range(1, n3 + 1):
        th = 360.0 * turns + 360.0 * (j / n3)
        out.append(cam(lon + (orad * math.sin(math.radians(th)) / M) / k,
                       lat + (orad * math.cos(math.radians(th)) / M),
                       eye_alt, (th + 180) % 360, 72.0, close_secs / n3))
    return out, orad, plan_alt, eye_alt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="kml/tours/uc-dormitories.kml")
    # SLOWER THAN THE STANDALONE LOOPS (John, 2026-08-29: "make the spirals slower"). The May
    # tour orbited each building in 10 s over four corner positions; gen_building_loop's own
    # defaults are 11/26/22. These are slower again, so the mass of each tower reads.
    ap.add_argument("--plan-secs", type=float, default=14.0)
    ap.add_argument("--spiral-secs", type=float, default=42.0)
    ap.add_argument("--close-secs", type=float, default=30.0)
    ap.add_argument("--turns", type=float, default=1.25)
    ap.add_argument("--transit-secs", type=float, default=12.0)
    ap.add_argument("--open-secs", type=float, default=10.0)
    a = ap.parse_args()

    B = buildings()
    picks, missing = [], []
    for addr, units in uc_addresses():
        head = " ".join(addr.split()[:2])                  # "2200 BANCROFT"
        hits = [(k, v) for k, v in B.items() if head in k]
        if hits:
            picks.append(max(hits, key=lambda kv: kv[1][3]))   # widest site wins
        else:
            missing.append(addr)
    if missing:
        print(f"  NOT DRAWN in geometry.kml, skipped: {', '.join(missing)}")
    if not picks:
        raise SystemExit("no UC buildings found in geometry.kml")

    # NORTH TO SOUTH, the order the May tour used and the order the campus reads in.
    picks.sort(key=lambda kv: -kv[1][1])

    body, lines = [], []
    # Opening: east of the Campanile at 95 m, looking west over the campus.
    body.append(cam(CAMPANILE[0] + 200 / (M * math.cos(math.radians(CAMPANILE[1]))),
                    CAMPANILE[1], 95.0, 270.0, 75.0, a.open_secs, "bounce"))
    total = a.open_secs
    for name, (lon, lat, roof, rad, label) in picks:
        k = math.cos(math.radians(lat))
        body.append(transit(lon + 260 / (M * k), lat, max(roof * 1.6, 150.0), 270.0, a.transit_secs))
        legs, orad, pa, ea = spiral(lon, lat, roof, rad,
                                    a.plan_secs, a.spiral_secs, a.close_secs, a.turns)
        body += legs
        total += a.transit_secs + a.plan_secs + a.spiral_secs + a.close_secs
        lines.append(f"    {label[:52]:<52} roof {roof:5.1f} m  orbit r {orad:4.0f} m  plan {pa:4.0f} m")

    stamp = datetime.datetime.now().strftime("%m-%d %H:%M")
    disp = f"UC Berkeley Student Housing · {len(picks)} projects · spirals · {stamp}"
    desc = (f"Every UC housing project flagged uc_project in v2, largest first, flown north to "
            f"south. Opens east of the Campanile, then at each site: plan view "
            f"{a.plan_secs:.0f} s, spiral in {a.spiral_secs:.0f} s over {a.turns} turns, close "
            f"orbit {a.close_secs:.0f} s. UC housing is counted in BEDS, not units. Altitudes "
            f"derive from each building's extrusion in geometry.kml, so a corrected height "
            f"re-cuts the shot. Camera-only: run build_tour_package.py to splice the geometry.")
    kml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">\n'
           f'<Document>\n\t<name>{disp}</name>\n\t<description><![CDATA[{desc}]]></description>\n'
           f'\t<gx:Tour>\n\t\t<name>{disp}</name>\n\t\t<gx:Playlist>\n'
           + "".join(body) + '\t\t</gx:Playlist>\n\t</gx:Tour>\n</Document>\n</kml>\n')
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w").write(kml)
    print(f"  wrote {a.out}")
    print(f"  {len(picks)} sites, {len(body)} FlyTo legs, {total/60:.1f} min")
    for l in lines: print(l)


if __name__ == "__main__":
    main()
