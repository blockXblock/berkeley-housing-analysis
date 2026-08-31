#!/usr/bin/env python3
"""gen_street_labels.py — street-name signposts for a corridor flyover.

WHY NOT THE ROADS LAYER (John, 2026-08-26): Google Earth ties road LABELS to the road LINES —
one layer, no sub-toggle — so switching on street names paints the yellow road overlay across
every shot. Custom label placemarks give the names without the paint, and let us choose the
font size, the colour, the altitude and WHICH streets appear.

THE LABEL-ONLY TRICK: a Placemark needs an icon for its label to render reliably, so each one
points at a 1x1 transparent PNG. <IconStyle><scale>0</scale> alone drops the label in Earth Pro.
The PNG sits beside the KML and is referenced relatively, so the file must travel with it.

FONT SIZE is <LabelStyle><scale>, and it MULTIPLIES Earth's own setting at
Tools > Options > 3D View > "Icon/Label Size". Both matter: scale 2.0 against a Small global
setting still reads small.

CROSS STREETS ARE DERIVED, NOT LISTED. A street is a crossing of this corridor when its address
points fall on BOTH sides of the path — that alone rejects the parallel streets a
distance-only test would drag in. The label goes at the point on the path closest to the
crossing street's nearby points, i.e. the intersection.

  python scripts/gen_street_labels.py "kml/tours/control_points/Shattuck Path S-N.kml" \
      --name Shattuck --out kml/tours/labels/shattuck-street-labels.kml --scale 2.0 --alt 20
"""
import argparse, csv, math, os, re, collections

M = 111320.0
ADDR = "data/reference/berkeley_addresses_with_fields.csv"
TYPE = {"AV": "Ave", "ST": "St", "WY": "Way", "BL": "Blvd", "DR": "Dr",
        "CT": "Ct", "PL": "Pl", "RD": "Rd", "LN": "Ln", "TR": "Ter"}


def path_of(cp):
    """Accept BOTH control-point shapes this project uses.

    A hand-drawn Google Earth Path is one Placemark holding a LineString. Everything
    derive_street_centreline.py emits -- Adeline, Bancroft, Oxford, San Pablo, Telegraph,
    University -- is instead a folder of numbered Point placemarks, and so is the
    College-Bancroft route. Reading only the LineString silently excluded six of the seven
    corridors from ever getting street signs.
    """
    x = open(cp, encoding="utf-8", errors="replace").read()
    ls = re.search(r"<LineString>.*?</LineString>", x, re.S)
    if ls:
        cs = re.search(r"<coordinates>\s*(.*?)\s*</coordinates>", ls.group(0), re.S).group(1)
        return [(float(t.split(",")[0]), float(t.split(",")[1])) for t in cs.split()]
    pins = []
    for pm in re.findall(r"<Placemark>.*?</Placemark>", x, re.S):
        pt = re.search(r"<Point>.*?<coordinates>\s*([^<]*?)\s*</coordinates>", pm, re.S)
        nm = re.search(r"<name>([^<]*)</name>", pm)
        if pt:
            c = pt.group(1).split(",")
            pins.append(((nm.group(1) if nm else ""), float(c[0]), float(c[1])))
    if not pins:
        raise SystemExit(f"{cp}: no LineString and no Point placemarks")
    # order by NAME, not file order -- Earth reshuffles placemarks as they are edited
    pins.sort(key=lambda q: q[0])
    return [(lon, lat) for _, lon, lat in pins]


def project(p, path):
    """(distance_m, signed_side_m, point_on_path, chainage_m) for the nearest segment."""
    k = math.cos(math.radians(p[1]))
    best = None
    run = 0.0
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        ax, ay = (a[0] - p[0]) * k * M, (a[1] - p[1]) * M
        bx, by = (b[0] - p[0]) * k * M, (b[1] - p[1]) * M
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = max(0.0, min(1.0, -(ax * dx + ay * dy) / L)) if L else 0.0
        cx, cy = ax + t * dx, ay + t * dy
        d = math.hypot(cx, cy)
        seg = math.sqrt(L)
        if best is None or d < best[0]:
            side = (dx * (-cy) - dy * (-cx)) / seg if L else 0.0
            best = (d, side, (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), run + t * seg)
        run += seg
    return best


def label(name, lon, lat, alt, style):
    return (f'\t<Placemark><name>{name}</name><styleUrl>#{style}</styleUrl>'
            f"<Point><altitudeMode>relativeToGround</altitudeMode>"
            f"<coordinates>{lon!r},{lat!r},{alt}</coordinates></Point></Placemark>\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("control_points")
    ap.add_argument("--name", required=True, help="the corridor's own street, excluded from crossings")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=1.5,
                    help="LabelStyle scale (font size). Dropped from 2.0 when the building "
                         "labels went to 2.0 on two lines -- street names must stay BELOW the "
                         "buildings, which are the subject.")
    ap.add_argument("--alt", type=float, default=20.0, help="metres above ground")
    ap.add_argument("--reach", type=float, default=80.0, help="how far off the path to look for a street")
    ap.add_argument("--spread", type=float, default=200.0,
                    help="max along-corridor spread of a street's nearby points; above this it is parallel, not crossing. MEASURED on Shattuck: true crossings 59-139 m (Bancroft 59, Center 59, Blake 92, University 115, Parker 129, Vine 139), parallels 675-708 m (Walnut, Henry). 200 separates them cleanly; 90 was cutting University and Parker out.")
    # AMBER, NOT WHITE (John, 2026-08-30: "different style or color for street names ...
    # sometimes hard to see which label is for which building"). Street signs and building
    # labels were both plain white at similar sizes, so the eye had nothing to sort them by.
    # A warm amber reads as signage and lets the white building labels sit in front of it.
    ap.add_argument("--colour", default="ff50c4ff", help="KML aabbggrr (default amber)")
    ap.add_argument("--every", type=float, default=400.0, help="metres between repeats of the corridor's own name")
    ap.add_argument("--own-mult", type=float, default=1.25,
                    help="corridor-name scale as a multiple of --scale. STREET SIGNS ARE CONTEXT AND THE "
                         "BUILDINGS ARE THE SUBJECT (John, 2026-08-26), so keep --scale * --own-mult BELOW the "
                         "building label scale set by set_label_scale.py.")
    a = ap.parse_args()

    path = path_of(a.control_points)
    pts = collections.defaultdict(list)
    with open(ADDR, encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            try:
                lon, lat = float(r["longitude"]), float(r["latitude"])
            except (TypeError, ValueError):
                continue
            if r.get("FEANME"):
                pts[(r["FEANME"], r.get("FEATYP", ""))].append((lon, lat))

    own = a.name.upper()
    rows = []
    for (nm, ty), ps in pts.items():
        if nm.upper() == own:
            continue
        near = [(project(p, path), p) for p in ps]
        near = [(pr, p) for pr, p in near if pr[0] < a.reach]
        if len(near) < 2:
            continue
        sides = [pr[1] for pr, _ in near]
        # BOTH SIDES is necessary but NOT sufficient: Walnut runs parallel to Shattuck and
        # close to it, and its 221 nearby address points straddle the path wherever the path
        # bends. The discriminator is SPREAD ALONG the corridor -- a cross street meets it at
        # ONE place, a parallel street smears down its whole length.
        if not (min(sides) < -8 and max(sides) > 8):
            continue
        chain = [pr[3] for pr, _ in near]
        if max(chain) - min(chain) > a.spread:
            continue
        best = min(near, key=lambda x: x[0][0])
        rows.append((best[0][2], f"{nm.title()} {TYPE.get(ty, ty.title())}".strip()))
    rows.sort(key=lambda r: r[0][1])

    body = [label(nm, pt[0], pt[1], a.alt, "cross") for pt, nm in rows]

    # the corridor's own name, repeated along the run so it is on screen throughout
    k = math.cos(math.radians(path[0][1]))
    run, prev = 0.0, path[0]
    own_lbl = [label(a.name, path[0][0], path[0][1], a.alt, "own")]
    for q in path[1:]:
        run += math.hypot((q[0] - prev[0]) * k * M, (q[1] - prev[1]) * M)
        if run >= a.every:
            own_lbl.append(label(a.name, q[0], q[1], a.alt, "own"))
            run = 0.0
        prev = q

    icon = ('<Icon><href>transparent-1x1.png</href></Icon>'
            '<hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>')
    out = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n'
           f"\t<name>{a.name} street labels · scale {a.scale} · {a.alt:.0f} m</name>\n\t<open>1</open>\n"
           f'\t<Style id="cross"><IconStyle><scale>0.4</scale>{icon}</IconStyle>'
           f"<LabelStyle><scale>{a.scale}</scale><color>{a.colour}</color></LabelStyle></Style>\n"
           f'\t<Style id="own"><IconStyle><scale>0.4</scale>{icon}</IconStyle>'
           f"<LabelStyle><scale>{round(a.scale * a.own_mult, 3)}</scale><color>{a.colour}</color></LabelStyle></Style>\n"
           + "".join(own_lbl) + "".join(body) +
           "</Document>\n</kml>\n")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(out)
    png = os.path.join(os.path.dirname(a.out), "transparent-1x1.png")
    print(f"wrote {a.out}\n  {len(rows)} cross streets + {len(own_lbl)} '{a.name}' markers, "
          f"cross-street scale {a.scale}, corridor-name scale {round(a.scale * a.own_mult, 3)}, "
          f"{a.alt:.0f} m above ground")
    print(f"  icon dependency: {png} {'OK' if os.path.exists(png) else 'MISSING — label may not render'}")
    for pt, nm in rows:
        print(f"    {pt[1]:.5f}  {nm}")


if __name__ == "__main__":
    main()
