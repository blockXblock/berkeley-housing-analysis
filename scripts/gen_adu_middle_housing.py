#!/usr/bin/env python3
"""gen_adu_middle_housing.py — generate kml/geometry/adu-middle-housing.kml from the derived cohort.

The SECOND geometry layer (the skyline kml/geometry/geometry.kml deliberately omits ADUs). Reads
data/processed/adu_mh_cohort.csv (built by scripts/adu_mh_cohort.py: the fixed-classifier ADU cohort
~93% vs the HCD APR oracle, + the Middle-Housing PLN cohort). Renders type-color-coded extruded
blocks grouped into Google Earth Folders (ADU / Duplex / Triplex / Fourplex), toggleable per type.

v1 footprints: a ~12 m generated square at each parcel centroid. Labels click-to-show (hidden by
default) to avoid a wall of text. Regenerate the cohort first (adu_mh_cohort.py) if the data changed.

Usage:
  python scripts/adu_mh_cohort.py            # (re)build the cohort CSV first
  python scripts/gen_adu_middle_housing.py                 # all ADU+MH citywide
  python scripts/gen_adu_middle_housing.py --street COLLEGE   # corridor subset (tour #4)
"""
import csv, math, argparse, os

COHORT = "data/processed/adu_mh_cohort.csv"
OUT = "kml/geometry/adu-middle-housing.kml"
# type -> (folder label, half-size m, extrude height m, (r,g,b))
TYPES = {
    "adu":      ("ADU",       6.0, 4.0,  (90, 220, 120)),
    "duplex":   ("Duplex",    7.0, 6.0,  (0, 200, 227)),
    "triplex":  ("Triplex",   8.0, 8.0,  (150, 100, 225)),
    "fourplex": ("Fourplex",  9.0, 10.0, (255, 140, 40)),
}
ORDER = ["adu", "duplex", "triplex", "fourplex"]
def col(r, g, b, a=0xbf): return f"{a:02x}{b:02x}{g:02x}{r:02x}"   # KML aabbggrr

def square(lat, lon, d):
    dlat = d / 111320.0
    dlon = d / (111320.0 * math.cos(math.radians(lat)))
    return [(lon-dlon, lat-dlat), (lon+dlon, lat-dlat), (lon+dlon, lat+dlat),
            (lon-dlon, lat+dlat), (lon-dlon, lat-dlat)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--street", help="filter to an address substring (e.g. COLLEGE) for a corridor tour")
    ap.add_argument("--cohort", default=COHORT)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    if not os.path.exists(a.cohort):
        raise SystemExit(f"cohort not found: {a.cohort} — run scripts/adu_mh_cohort.py first")

    rows = list(csv.DictReader(open(a.cohort)))
    if a.street:
        s = a.street.upper()
        rows = [r for r in rows if s in (r.get("addr") or "").upper()]

    styles = ""
    for t in ORDER:
        name, _, _, (r, g, b) = TYPES[t]
        styles += (f'  <Style id="t_{t}"><LineStyle><color>ff{col(r,g,b)[2:]}</color><width>1</width></LineStyle>'
                   f'<PolyStyle><color>{col(r,g,b)}</color></PolyStyle>'
                   f'<IconStyle><scale>0</scale></IconStyle>'
                   f'<LabelStyle><scale>0</scale></LabelStyle></Style>\n')
    folders = {t: [] for t in ORDER}
    for r in rows:
        t = (r.get("type") or "").lower()
        if t not in TYPES: continue
        try: lat, lon = float(r["lat"]), float(r["lon"])
        except (TypeError, ValueError): continue
        _, d, h, _ = TYPES[t]
        ring = " ".join(f"{x:.6f},{y:.6f},{h:.0f}" for x, y in square(lat, lon, d))
        label = (r.get("addr") or r.get("key") or "").strip() or TYPES[t][0]
        folders[t].append(
            f'    <Placemark><name>{label} · {TYPES[t][0]}</name><styleUrl>#t_{t}</styleUrl>'
            f'<Polygon><extrude>1</extrude><altitudeMode>relativeToGround</altitudeMode>'
            f'<outerBoundaryIs><LinearRing><coordinates>{ring}</coordinates></LinearRing>'
            f'</outerBoundaryIs></Polygon></Placemark>')

    body = ""
    for t in ORDER:
        if folders[t]:
            body += f'  <Folder><name>{TYPES[t][0]} ({len(folders[t])})</name>\n' + "\n".join(folders[t]) + "\n  </Folder>\n"
    title = "ADU + Middle Housing" + (f" — {a.street.title()} corridor" if a.street else "")
    kml = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n'
           f'  <name>{title}</name><open>1</open>\n{styles}{body}</Document></kml>')
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w").write(kml)
    counts = {t: len(folders[t]) for t in ORDER if folders[t]}
    print(f"wrote {a.out} — " + " · ".join(f"{TYPES[t][0]} {n}" for t, n in counts.items()))
    if a.street: print(f"  (filtered to '{a.street}')")

if __name__ == "__main__":
    main()
