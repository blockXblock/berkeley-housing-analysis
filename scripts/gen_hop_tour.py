#!/usr/bin/env python3
"""gen_hop_tour.py — a survey flight that hops between scattered projects.

WHY NOT A CORRIDOR TOUR. The corridor tours follow a drawn street. A set like "every private
project over 200 units" is not on one street -- it is scattered across the city -- so the flight
has to be a ROUTE THROUGH POINTS rather than a path. And a full descending orbit at each, as the
dorm tour does, would run 20 minutes for fifteen sites. This gives each one a quarter-turn arc:
enough to read the mass and let the label settle, then away to the next.

THE ROUTE is greedy nearest-neighbour from the southernmost site. That is not the shortest
possible tour, but it never doubles back on a neighbour it has already passed, which is what
reads as aimless from the air. The last hop or two can be long once the near ones are used up --
unavoidable without solving a travelling-salesman problem for a film nobody will measure.

It emits BUILDING-IN/OUT markers, so svg_label_tour.py treats each arc as an orbit: one label on
screen, tucked under the roofline, moving every leg.

  python scripts/gen_hop_tour.py --min-units 200 --exclude-agency --out kml/tours/private-200.kml
"""
import argparse, datetime, math, os, re, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_building_loop import buildings as site_buildings

M = 111320.0
DB = "databases/berkeley_housing_v2.db"


def slugify(a):
    return re.sub(r"[^a-z0-9]+", "-", str(a).lower()).strip("-")


def bearing(a, b):
    k = math.cos(math.radians(a[1]))
    return (math.degrees(math.atan2((b[0] - a[0]) * k, b[1] - a[1])) + 360) % 360


def metres(a, b):
    k = math.cos(math.radians(a[1]))
    return math.hypot((b[0] - a[0]) * k * M, (b[1] - a[1]) * M)


def cam(lon, lat, alt, hdg, tilt, dur, mode="smooth"):
    return (f"\t\t\t<gx:FlyTo>\n\t\t\t\t<gx:duration>{dur:.2f}</gx:duration>\n"
            f"\t\t\t\t<gx:flyToMode>{mode}</gx:flyToMode>\n\t\t\t\t<Camera>\n"
            f"\t\t\t\t\t<longitude>{lon:.10f}</longitude>\n\t\t\t\t\t<latitude>{lat:.10f}</latitude>\n"
            f"\t\t\t\t\t<altitude>{alt:.1f}</altitude>\n\t\t\t\t\t<heading>{hdg:.2f}</heading>\n"
            f"\t\t\t\t\t<tilt>{tilt:.1f}</tilt>\n\t\t\t\t\t<roll>0</roll>\n"
            f"\t\t\t\t\t<altitudeMode>relativeToGround</altitudeMode>\n"
            f"\t\t\t\t</Camera>\n\t\t\t</gx:FlyTo>\n")


def picks(a):
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    q = """SELECT f.address_display a, f.total_units u,
             (SELECT 1 FROM project_classifications pc JOIN vocabulary_classification_types v
                ON v.id = pc.classification_type_id WHERE pc.project_id = f.project_id
                AND v.code IN ('uc_project','bart_project')) agency
           FROM v_projects_flat f JOIN projects p ON p.id = f.project_id
           WHERE p.merged_into_id IS NULL AND f.total_units >= ?"""
    rows = [r for r in c.execute(q, (a.min_units,))]
    if a.exclude_agency:
        rows = [r for r in rows if not r["agency"]]
    B = site_buildings()
    out = []
    for r in rows:
        head = " ".join(str(r["a"]).upper().split()[:2])
        hit = [(k, v) for k, v in B.items() if head in k]
        if hit:
            out.append((max(hit, key=lambda kv: kv[1][3]), r["u"]))
        else:
            print(f"  not drawn in geometry.kml, skipped: {r['a']}")
    # de-duplicate sites that share an address key
    seen, uniq = set(), []
    for (k, v), u in out:
        if k not in seen:
            seen.add(k); uniq.append((k, v, u))
    return uniq


def route(sites):
    """Greedy nearest-neighbour from the southernmost."""
    left = list(sites)
    cur = min(left, key=lambda s: s[1][1])
    left.remove(cur)
    order = [cur]
    while left:
        cur = min(left, key=lambda s: metres((order[-1][1][0], order[-1][1][1]), (s[1][0], s[1][1])))
        left.remove(cur); order.append(cur)
    return order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-units", type=int, default=200)
    ap.add_argument("--exclude-agency", action="store_true", help="drop UC and BART projects")
    ap.add_argument("--out", default="kml/tours/private-200.kml")
    ap.add_argument("--name", default="Berkeley's largest private housing projects")
    ap.add_argument("--arc", type=float, default=11.0, help="seconds for the quarter-turn at each")
    ap.add_argument("--hop", type=float, default=13.0, help="seconds between sites")
    ap.add_argument("--rise", type=float, default=75.0, help="closing swoop climb")
    a = ap.parse_args()

    sites = route(picks(a))
    print(f"  {len(sites)} sites, south to north by nearest neighbour")

    body, lines, total = [], [], 0.0
    prev = None
    for i, (key, v, units) in enumerate(sites):
        lon, lat, roof, rad, label = v
        orad = max(rad * 2.2, roof * 1.1, 70.0)
        # fly at the building's own scale, never so high the label leaves the flight line
        alt = max(roof * 0.75, 45.0)
        th0 = bearing((lon, lat), prev) if prev else 200.0
        k = math.cos(math.radians(lat))
        body.append(f"\t\t\t<!--BUILDING-IN {slugify(key)}-->\n")
        entry = (lon + (orad * math.sin(math.radians(th0)) / M) / k,
                 lat + (orad * math.cos(math.radians(th0)) / M))
        body.append(cam(entry[0], entry[1], alt, (th0 + 180) % 360, 72.0, a.hop if prev else 6.0,
                        "bounce" if i == 0 else "smooth"))
        # a quarter turn: enough to read the mass without the cost of a full orbit
        n = 14
        for j in range(1, n + 1):
            th = th0 + 90.0 * (j / n)
            body.append(cam(lon + (orad * math.sin(math.radians(th)) / M) / k,
                            lat + (orad * math.cos(math.radians(th)) / M),
                            alt, (th + 180) % 360, 74.0, a.arc / n))
        body.append(f"\t\t\t<!--BUILDING-OUT {slugify(key)}-->\n")
        total += (a.hop if prev else 6.0) + a.arc
        lines.append(f"    {units:>5} units  {label.splitlines()[0][:52]}")
        prev = (lon, lat)

    # closing swoop, matching the corridor tours: climb and look west
    lon, lat, roof, rad, _ = sites[-1][1]
    k = math.cos(math.radians(lat))
    for j in range(1, 15):
        e = (j / 14) ** 0.6
        body.append(cam(lon, lat, max(roof * 0.75, 45.0) + a.rise * e, 270.0, 76.0 + 6 * e, 12.0 / 14))
    body.append(cam(lon, lat, max(roof * 0.75, 45.0) + a.rise, 270.0, 82.0, 8.0))
    total += 20.0

    stamp = datetime.datetime.now().strftime("%m-%d %H:%M")
    disp = f"{a.name} · {len(sites)} projects · {stamp}"
    kml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">\n'
           f'<Document>\n\t<name>{disp}</name>\n'
           f'\t<description><![CDATA[Every project of {a.min_units}+ units'
           f'{" excluding UC and BART" if a.exclude_agency else ""}, visited south to north by '
           f'nearest neighbour. A quarter-turn arc at each rather than a full orbit, so fifteen '
           f'sites fit in one film. Camera-only: run build_tour_package.py to splice the '
           f'geometry.]]></description>\n'
           f'\t<gx:Tour>\n\t\t<name>{disp}</name>\n\t\t<gx:Playlist>\n'
           + "".join(body) + '\t\t</gx:Playlist>\n\t</gx:Tour>\n</Document>\n</kml>\n')
    open(a.out, "w").write(kml)
    print(f"  wrote {a.out}")
    print(f"  {len([b for b in body if '<gx:FlyTo>' in b])} legs, {total/60:.1f} min")
    for l in lines: print(l)


if __name__ == "__main__":
    main()
