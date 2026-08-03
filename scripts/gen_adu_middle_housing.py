#!/usr/bin/env python3
"""gen_adu_middle_housing.py — generate kml/geometry/adu-middle-housing.kml.

The SECOND geometry layer (the skyline kml/geometry/geometry.kml deliberately omits ADUs —
<1% of them are modeled there). This one is DERIVED from v2 and REGENERABLE: it renders the
ADU + middle-housing fabric as small, type-color-coded extruded blocks, grouped into Google
Earth Folders (ADU / duplex / triplex / fourplex) so each type can be toggled independently.

Type = net unit count:  1 = ADU · 2 = duplex · 3 = triplex · 4 = fourplex.

v1 footprints: a ~12 m generated square at each project's v2 lat/lon (651/663 ADUs are
geocoded). UPGRADE PATH: real parcel polygons (berkeley.db.the_geom, point-in-polygon or
address join) + the fuller v4 ADU cohort (~2,881 vs v2's 663). Labels are click-to-show
(hidden by default) to avoid a wall of text over hundreds of parcels.

Usage:
  python scripts/gen_adu_middle_housing.py                 # all ADU+MH citywide
  python scripts/gen_adu_middle_housing.py --street COLLEGE   # corridor subset (tour #4)
"""
import sqlite3, math, argparse, os

DB = "databases/berkeley_housing_v2.db"
OUT = "kml/geometry/adu-middle-housing.kml"
# type -> (label, half-size m, extrude height m, (r,g,b))
TYPES = {
    1: ("ADU",       6.0, 4.0, (90, 220, 120)),
    2: ("Duplex",    7.0, 6.0, (0, 200, 227)),
    3: ("Triplex",   8.0, 8.0, (150, 100, 225)),
    4: ("Fourplex",  9.0, 10.0, (255, 140, 40)),
}
def col(r, g, b, a=0xbf): return f"{a:02x}{b:02x}{g:02x}{r:02x}"   # KML aabbggrr

def square(lat, lon, d):
    dlat = d / 111320.0
    dlon = d / (111320.0 * math.cos(math.radians(lat)))
    pts = [(lon-dlon, lat-dlat), (lon+dlon, lat-dlat), (lon+dlon, lat+dlat),
           (lon-dlon, lat+dlat), (lon-dlon, lat-dlat)]
    return pts

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--street", help="filter to an address substring (e.g. COLLEGE) for a corridor tour")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    con = sqlite3.connect(DB)
    q = ("SELECT address_display, total_units, latitude, longitude "
         "FROM v_projects_flat WHERE total_units BETWEEN 1 AND 4 "
         "AND latitude IS NOT NULL AND longitude IS NOT NULL")
    args = []
    if a.street:
        q += " AND UPPER(address_display) LIKE ?"; args.append(f"%{a.street.upper()}%")
    rows = con.execute(q, args).fetchall()
    con.close()

    # styles + folders per type
    styles = ""
    for u, (name, _, _, (r, g, b)) in TYPES.items():
        styles += (f'  <Style id="t{u}"><LineStyle><color>ff{col(r,g,b)[2:]}</color><width>1</width></LineStyle>'
                   f'<PolyStyle><color>{col(r,g,b)}</color></PolyStyle>'
                   f'<IconStyle><scale>0</scale></IconStyle>'
                   f'<LabelStyle><scale>0</scale></LabelStyle></Style>\n')  # label click-to-show
    folders = {u: [] for u in TYPES}
    counts = {u: 0 for u in TYPES}
    for addr, units, lat, lon in rows:
        u = int(units)
        if u not in TYPES: continue
        name, d, h, _ = TYPES[u]
        ring = " ".join(f"{x:.6f},{y:.6f},{h:.0f}" for x, y in square(lat, lon, d))
        folders[u].append(
            f'    <Placemark><name>{addr} · {name}</name><styleUrl>#t{u}</styleUrl>'
            f'<Polygon><extrude>1</extrude><altitudeMode>relativeToGround</altitudeMode>'
            f'<outerBoundaryIs><LinearRing><coordinates>{ring}</coordinates></LinearRing>'
            f'</outerBoundaryIs></Polygon></Placemark>')
        counts[u] += 1

    body = ""
    for u, (name, *_ ) in TYPES.items():
        if not folders[u]: continue
        body += (f'  <Folder><name>{name} ({counts[u]})</name>\n'
                 + "\n".join(folders[u]) + "\n  </Folder>\n")
    title = "ADU + Middle Housing" + (f" — {a.street.title()} corridor" if a.street else "")
    kml = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n'
           f'  <name>{title}</name><open>1</open>\n{styles}{body}</Document></kml>')
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w").write(kml)
    tot = sum(counts.values())
    print(f"wrote {a.out} — {tot} units: " + " · ".join(f"{TYPES[u][0]} {counts[u]}" for u in TYPES))
    if a.street: print(f"  (filtered to '{a.street}')")

if __name__ == "__main__":
    main()
