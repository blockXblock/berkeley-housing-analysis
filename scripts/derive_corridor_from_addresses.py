#!/usr/bin/env python3
"""derive_corridor_from_addresses.py — control points for any named street, from its addresses.

WHY A SECOND DERIVATION. derive_street_centreline.py finds a street as the GAP between the
parcel rows facing it, which is more accurate but needs the parcel geojson and a hand-tuned
corridor entry. This is the cheap general one: addresses sit on BOTH sides of a street, so the
MEDIAN address position across a slice tracks the roadway. Accurate to a few metres -- CANDIDATE
geometry, same caveat derive_street_centreline.py carries. Drag the pins in Earth via
control_points_roundtrip.py --explode if the flight sits off the crown.

AXIS MATTERS. A north-south street is sliced by latitude and yields a median LONGITUDE per slice;
an east-west street is the transpose. Slicing the wrong way returns one meaningless point.

  python scripts/derive_corridor_from_addresses.py --street ASHBY --axis ew \
      --name "Ashby" --out "kml/tours/control_points/Ashby Control Points DERIVED.kml"
"""
import argparse, csv, statistics

ADDR = "data/reference/berkeley_addresses_with_fields.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--street", required=True, help="FEANME as it appears in the address file")
    ap.add_argument("--axis", choices=["ns", "ew"], required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--slice", type=float, default=0.0012, help="slice size in degrees along the run")
    ap.add_argument("--min-per-slice", type=int, default=4)
    ap.add_argument("--reverse", action="store_true", help="emit in the opposite direction")
    a = ap.parse_args()

    pts = []
    for r in csv.DictReader(open(ADDR, encoding="utf-8", errors="replace")):
        if (r.get("FEANME") or "").upper() != a.street.upper():
            continue
        try:
            pts.append((float(r["longitude"]), float(r["latitude"])))
        except (TypeError, ValueError):
            pass
    if len(pts) < 8:
        raise SystemExit(f"only {len(pts)} address points for {a.street} — cannot derive a line")

    run, cross = (1, 0) if a.axis == "ns" else (0, 1)
    lo, hi = min(p[run] for p in pts), max(p[run] for p in pts)
    spine = []
    y = lo
    while y < hi:
        band = [p[cross] for p in pts if y <= p[run] < y + a.slice]
        if len(band) >= a.min_per_slice:
            m = statistics.median(band)
            spine.append((m, y + a.slice / 2) if a.axis == "ns" else (y + a.slice / 2, m))
        y += a.slice
    if len(spine) < 2:
        raise SystemExit(f"{a.street}: {len(spine)} slices survived — wrong --axis, or too sparse")
    spine.sort(key=lambda p: p[run])
    if a.reverse:
        spine.reverse()

    body = "".join(
        f'\t\t<Placemark><name>{a.name[:3].upper()}{i:02d}</name><styleUrl>#m_ylw-pushpin</styleUrl>'
        f"<Point><coordinates>{lon!r},{lat!r},0</coordinates></Point></Placemark>\n"
        for i, (lon, lat) in enumerate(spine, 1))
    open(a.out, "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n'
        f"\t<name>{a.name} Control Points DERIVED · {len(spine)} points</name>\n\t<open>1</open>\n"
        '\t<Style id="s_ylw-pushpin"><IconStyle><scale>1.1</scale><Icon>'
        '<href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href></Icon></IconStyle></Style>\n'
        '\t<StyleMap id="m_ylw-pushpin"><Pair><key>normal</key><styleUrl>#s_ylw-pushpin</styleUrl></Pair>'
        '<Pair><key>highlight</key><styleUrl>#s_ylw-pushpin</styleUrl></Pair></StyleMap>\n'
        f"\t<Folder><name>{a.name}</name><open>1</open>\n{body}\t</Folder>\n</Document>\n</kml>\n")
    print(f"wrote {a.out}\n  {len(spine)} points from {len(pts)} addresses, "
          f"{'S->N' if a.axis=='ns' else 'W->E'}{' reversed' if a.reverse else ''}: "
          f"{spine[0][1]:.4f},{spine[0][0]:.4f} -> {spine[-1][1]:.4f},{spine[-1][0]:.4f}")


if __name__ == "__main__":
    main()
