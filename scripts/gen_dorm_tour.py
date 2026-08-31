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


def slugify(a):
    return re.sub(r"[^a-z0-9]+", "-", str(a).lower()).strip("-")


def bearing(a, b):
    """Compass bearing from point a to point b, both (lon, lat)."""
    k = math.cos(math.radians(a[1]))
    return (math.degrees(math.atan2((b[0] - a[0]) * k, b[1] - a[1])) + 360) % 360


def spiral(lon, lat, roof, rad, orbit_secs, turns, drop_m, th0):
    """ONE DESCENDING ORBIT, entered from azimuth th0 — never a look-down, never a snap.

    John, 2026-08-30: "eliminate the orbits looking straight down on the buildings ... do one
    orbit, drop the elevation by 20 metres, then rise an additional 25 m."
    And then: "why, after each orbit, does the camera move to the right and look up? can it look
    in the direction of the flight to the next building?"

    Both of those were one bug. Every orbit used to start at azimuth 0 and the legs between
    buildings were hardcoded to heading 270. A full turn ends the camera heading 180, so the
    lift snapped 90 degrees clockwise -- the swing to the right -- and changed tilt at the same
    time, which is the lurch that read as looking up.

    THE FIX IS TO ENTER THE CIRCLE WHERE YOU ARRIVE. A camera sitting at azimuth th0 from the
    building looks back at it on heading (th0 + 180). So entering at th0 = the bearing from this
    building BACK toward wherever the camera came from makes that opening heading exactly the
    direction of travel. The approach, the entry and the first orbit camera all point the same
    way, and there is nothing to snap.

    Returns (legs, end_lon, end_lat, end_alt) — the climb lifts from where the orbit really ended.
    """
    orad = max(rad * 2.2, roof * 1.3, 60.0)
    end_alt = roof + 10.0
    start_alt = end_alt + drop_m
    k = math.cos(math.radians(lat))
    out, n = [], int(48 * turns)
    for j in range(n + 1):
        f = j / n
        e = f * f * (3 - 2 * f)
        th = th0 + 360.0 * turns * f
        alt = start_alt + (end_alt - start_alt) * e
        tilt = 66.0 + 10.0 * e
        out.append(cam(lon + (orad * math.sin(math.radians(th)) / M) / k,
                       lat + (orad * math.cos(math.radians(th)) / M),
                       alt, (th + 180) % 360, tilt, orbit_secs / n,
                       "smooth"))
    th_end = th0 + 360.0 * turns
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
    ap.add_argument("--transit-secs", type=float, default=16.0)
    ap.add_argument("--open-secs", type=float, default=10.0)
    ap.add_argument("--outro-rise", type=float, default=75.0,
                    help="metres the closing swoop climbs (matches the corridor tours' 75 m)")
    ap.add_argument("--outro-secs", type=float, default=12.0)
    ap.add_argument("--outro-hold", type=float, default=8.0,
                    help="seconds held on the final westward view (the corridor tours hold 8 s)")
    ap.add_argument("--turn-secs", type=float, default=9.0,
                    help="seconds to climb 25 m AND swing round to face the next building")
    ap.add_argument("--approach-secs", type=float, default=26.0,
                    help="the opening run from the Campanile to the first building. John asked "
                         "for this to be slower: it had been no leg at all, cutting straight "
                         "from the establishing shot into the first orbit.")
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

    # ORDER IS JOHN'S, NOT THE LATITUDE'S (2026-08-30: "change the order of the last two
    # buildings. do 2556 Haste, then 2400 Bowditch"). A plain north-to-south sort always puts
    # Bowditch before Haste, so the sequence has to be stated. Anything NOT named here -- the
    # next UC tower to get flagged uc_project -- still falls in by latitude, so the tour keeps
    # picking up new projects on its own rather than being frozen to these four.
    ORDER = ["1950 OXFORD", "2200 BANCROFT", "2556 HASTE", "2400 BOWDITCH"]
    def rank(kv):
        for i, head in enumerate(ORDER):
            if head in kv[0]:
                return (0, i, 0)
        return (1, 0, -kv[1][1])          # unlisted: after the named ones, north to south
    picks.sort(key=rank)

    body, lines = [], []
    # Opening: east of the Campanile at 95 m, looking west over the campus.
    ck = math.cos(math.radians(CAMPANILE[1]))
    open_pos = (CAMPANILE[0] + 200 / (M * ck), CAMPANILE[1])
    body.append(cam(open_pos[0], open_pos[1], 95.0, 270.0, 75.0, a.open_secs, "bounce"))
    total = a.open_secs

    prev_pos = open_pos
    for idx, (name, (lon, lat, roof, rad, label)) in enumerate(picks):
        here = (lon, lat)
        k = math.cos(math.radians(lat))
        orad = max(rad * 2.2, roof * 1.3, 60.0)
        # Enter the circle on the side we are arriving from, so the first orbit camera is
        # already looking along the flight path. th0 = bearing from the building back to us.
        th0 = bearing(here, prev_pos)
        travel = (th0 + 180) % 360                      # the direction we are actually going
        entry = (lon + (orad * math.sin(math.radians(th0)) / M) / k,
                 lat + (orad * math.cos(math.radians(th0)) / M))
        # THE RUN IN. A slow leg that arrives exactly at the orbit's first camera, facing the
        # way it is travelling -- the opening one is longer because it sets the film up.
        secs = a.approach_secs if idx == 0 else a.transit_secs
        # BOUNDARY MARKERS. Harmless comments, but they let a post-processor find where each
        # building's segment begins and ends -- which is how the label-visibility prototype
        # knows when to switch a label on and off without re-deriving the flight.
        body.append(f"\t\t\t<!--BUILDING-IN {slugify(name)}-->\n")
        body.append(cam(entry[0], entry[1], roof + 10.0 + a.drop, travel, 70.0, secs))
        total += secs

        legs, elon, elat, ealt = spiral(lon, lat, roof, rad, a.orbit_secs, a.turns, a.drop, th0)
        body += legs
        total += a.orbit_secs

        # THE CLIMB. 25 m, and it turns to face the NEXT building rather than a fixed compass
        # heading, so the camera looks where it is about to fly instead of swinging away.
        if idx < len(picks) - 1:
            nxt = picks[idx + 1][1]
            look = bearing(here, (nxt[0], nxt[1]))
            # TURN THROUGH THE CLIMB, DO NOT SNAP AT THE TOP OF IT. The orbit finishes looking
            # back along the way it came in; the next leg has to look the other way. That turn
            # is wanted -- John asked the camera to face where it is flying -- but done in one
            # leg it was a 103 degree jerk. Spread over the climb it reads as the camera coming
            # round to pick up the next building. Interpolated the short way round, so a turn
            # across due north goes 350 -> 10 rather than the long way through 180.
            end_h = (th0 + 180) % 360
            delta = (look - end_h + 540) % 360 - 180
            n = 10
            for q in range(1, n + 1):
                f = q / n
                e = f * f * (3 - 2 * f)
                body.append(cam(elon, elat, ealt + a.rise * e,
                                (end_h + delta * e) % 360, 76.0, a.turn_secs / n))
            total += a.turn_secs
        else:
            # CLOSING SWOOP. Climb away from the last building and turn to look west, over the
            # campus and the bay behind it -- the reverse of the opening, which came in from the
            # east looking west at the Campanile. Interpolated the short way round like the
            # inter-building turns, and tilting toward the horizon as it rises so the last thing
            # the film does is lift its eyes rather than stare down at a roof.
            end_h = (th0 + 180) % 360
            delta = (270.0 - end_h + 540) % 360 - 180
            n = 14
            for q in range(1, n + 1):
                f = q / n
                e = f * f * (3 - 2 * f)
                body.append(cam(elon, elat, ealt + a.outro_rise * e,
                                (end_h + delta * e) % 360, 76.0 + 6.0 * e,
                                a.outro_secs / n))
            body.append(cam(elon, elat, ealt + a.outro_rise, 270.0, 82.0, a.outro_hold))
            total += a.outro_secs + a.outro_hold
        body.append(f"\t\t\t<!--BUILDING-OUT {slugify(name)}-->\n")
        lines.append(f"    {label[:48]:<48} roof {roof:5.1f} m  r {orad:4.0f} m  "
                     f"{ealt + a.drop:5.0f}->{ealt:4.0f} m  enter {th0:5.1f}deg")
        prev_pos = here

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
