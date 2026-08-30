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


def spiral(lon, lat, roof, rad, orbit_secs, turns, drop_m, rise_m):
    """ONE DESCENDING ORBIT — a true spiral, and never a look-down.

    John, 2026-08-30: "eliminate the orbits looking straight down on the buildings ... do one
    orbit, drop the elevation by 20 metres, then rise an additional 25 m to fly to the next."

    The previous shot opened each building with a PLAN VIEW: twelve cameras at tilt 0, circling
    a quarter turn while pointing straight down. It was inherited from gen_building_loop, where
    a standalone clip has to establish the footprint before it means anything. In a continuous
    tour it just reads as an extra rotation over a roof, and four of them made the film crawl.

    What is left is the part that was doing the work: a single turn that descends `drop_m` while
    the camera tilts further up, so the tower resolves from a shape into a mass. The orbit ENDS
    at roof + 10 m, which is where the next leg lifts from.

    Returns (legs, end_lon, end_lat, end_alt) so the transit can rise from where the orbit
    actually finished rather than from a recomputed guess.
    """
    orad = max(rad * 2.2, roof * 1.3, 60.0)
    end_alt = roof + 10.0
    start_alt = end_alt + drop_m
    k = math.cos(math.radians(lat))
    out, n = [], int(48 * turns)
    for j in range(n + 1):
        f = j / n
        e = f * f * (3 - 2 * f)                    # ease in and out of the descent
        th = 360.0 * turns * f
        alt = start_alt + (end_alt - start_alt) * e
        tilt = 66.0 + 10.0 * e                     # 66 deg to 76 deg -- never anywhere near 0
        out.append(cam(lon + (orad * math.sin(math.radians(th)) / M) / k,
                       lat + (orad * math.cos(math.radians(th)) / M),
                       alt, (th + 180) % 360, tilt, orbit_secs / n,
                       "bounce" if j == 0 else "smooth"))
    th_end = 360.0 * turns
    return (out,
            lon + (orad * math.sin(math.radians(th_end)) / M) / k,
            lat + (orad * math.cos(math.radians(th_end)) / M),
            end_alt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="kml/tours/uc-dormitories.kml")
    # SLOWER THAN THE STANDALONE LOOPS (John, 2026-08-29: "make the spirals slower"). The May
    # tour orbited each building in 10 s over four corner positions; gen_building_loop's own
    # defaults are 11/26/22. These are slower again, so the mass of each tower reads.
    ap.add_argument("--orbit-secs", type=float, default=48.0,
                    help="seconds for the single descending orbit at each building")
    ap.add_argument("--turns", type=float, default=1.0)
    ap.add_argument("--drop", type=float, default=20.0,
                    help="metres the camera descends over the orbit (John: 20)")
    ap.add_argument("--rise", type=float, default=25.0,
                    help="metres to climb after the orbit before crossing to the next (John: 25)")
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
    for idx, (name, (lon, lat, roof, rad, label)) in enumerate(picks):
        k = math.cos(math.radians(lat))
        orad = max(rad * 2.2, roof * 1.3, 60.0)
        # APPROACH: come in at the altitude the orbit starts from, so the first orbit camera
        # is a continuation rather than a jump.
        if idx:
            body.append(cam(lon + (orad * 1.8 / M) / k, lat, roof + 10.0 + a.drop,
                            270.0, 70.0, a.transit_secs))
            total += a.transit_secs
        legs, elon, elat, ealt = spiral(lon, lat, roof, rad, a.orbit_secs, a.turns,
                                        a.drop, a.rise)
        body += legs
        total += a.orbit_secs
        # LIFT IN PLACE before crossing -- John asked for the climb to be its own move, so the
        # cut to the next building reads as leaving one and arriving at another, not a drift.
        if idx < len(picks) - 1:
            body.append(cam(elon, elat, ealt + a.rise, 270.0, 70.0, 4.0))
            total += 4.0
        lines.append(f"    {label[:50]:<50} roof {roof:5.1f} m  orbit r {orad:4.0f} m  "
                     f"{ealt + a.drop:5.0f} -> {ealt:4.0f} m")

    stamp = datetime.datetime.now().strftime("%m-%d %H:%M")
    disp = f"UC Berkeley Student Housing · {len(picks)} projects · spirals · {stamp}"
    desc = (f"Every UC housing project flagged uc_project in v2, flown north to south. Opens "
            f"east of the Campanile, then at each site ONE DESCENDING ORBIT: {a.orbit_secs:.0f} s "
            f"for {a.turns} turn, dropping {a.drop:.0f} m to roof + 10 m with the camera tilted "
            f"66-76 degrees throughout -- no look-down. It then climbs {a.rise:.0f} m before "
            f"crossing to the next. UC housing is counted in BEDS, not units. Altitudes "
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
