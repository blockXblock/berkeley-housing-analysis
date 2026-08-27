#!/usr/bin/env python3
"""control_points_roundtrip.py — make a hand-drawn corridor path EDITABLE in Google Earth.

THE PROBLEM (John, 2026-08-26): a control-point file drawn as a GE Path is ONE Placemark
holding ONE LineString. Its vertices are not objects -- nothing in the KML draws a marker at
each one -- so Earth shows a bare line and the vertices appear only as edit handles, only in
edit mode, and only if you selected the Placemark rather than its identically-named folder.
Editing them by drag is fiddly and destructive: with the edit dialog open, a click on empty
map APPENDS a vertex.

THE FIX: explode the path into one numbered Point placemark per vertex. A pushpin is visible
without edit mode, is dragged on its own, and survives Save Place As. Then rebuild the path
from the pins -- ORDER COMES FROM THE NAME (01, 02, ...), never from file order, because Earth
rewrites the order as you edit.

  python scripts/control_points_roundtrip.py --explode "kml/tours/control_points/Shattuck Path S-N.kml"
  ... drag pins in Earth, right-click the folder -> Save Place As -> overwrite the EDITABLE file ...
  python scripts/control_points_roundtrip.py --rebuild "kml/tours/control_points/Shattuck Path S-N EDITABLE.kml"

--rebuild writes back to the ORIGINAL path file, so gen_corridor_tour.py's cp- hash changes and
every tour built from it announces a new build. Regenerate the tours afterwards; editing the
control points alone changes no flight.
"""
import argparse, os, re

HDR = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       '<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n')


def read_vertices(path):
    x = open(path, encoding="utf-8", errors="replace").read()
    pms = re.findall(r"<Placemark>.*?</Placemark>", x, re.S)
    pins = []
    for pm in pms:
        if "<Point>" not in pm:
            continue
        nm = re.search(r"<name>([^<]*)</name>", pm)
        c = re.search(r"<coordinates>\s*([^<]*?)\s*</coordinates>", pm, re.S).group(1).split(",")
        pins.append(((nm.group(1) if nm else ""), float(c[0]), float(c[1])))
    if pins:
        # ORDER BY NAME, NOT FILE ORDER -- Earth reorders placemarks as they are edited.
        pins.sort(key=lambda p: p[0])
        return [(lon, lat) for _, lon, lat in pins]
    ls = re.search(r"<LineString>.*?</LineString>", x, re.S)
    if not ls:
        raise SystemExit(f"{path}: no Point placemarks and no LineString")
    cs = re.search(r"<coordinates>\s*(.*?)\s*</coordinates>", ls.group(0), re.S).group(1).split()
    return [(float(t.split(",")[0]), float(t.split(",")[1])) for t in cs]


def explode(src):
    v = read_vertices(src)
    dest = src[:-4] + " EDITABLE.kml"
    name = os.path.basename(dest)[:-4]
    out = [HDR, f"\t<name>{name}</name>\n\t<open>1</open>\n",
           '\t<Style id="cp"><IconStyle><scale>1.2</scale><Icon><href>'
           'http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href></Icon>'
           '<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/></IconStyle>'
           '<LabelStyle><scale>1.0</scale></LabelStyle></Style>\n',
           # the line is REFERENCE ONLY, and is styled so it cannot be mistaken for the pins
           '\t<Style id="ref"><LineStyle><color>ff00ffff</color><width>2</width></LineStyle></Style>\n',
           '\t<Placemark><name>path (reference — do not edit)</name><styleUrl>#ref</styleUrl>'
           "<LineString><tessellate>1</tessellate><coordinates>"
           + " ".join(f"{lon!r},{lat!r},0" for lon, lat in v)
           + "</coordinates></LineString></Placemark>\n",
           "\t<Folder>\n\t\t<name>control points (drag these)</name>\n\t\t<open>1</open>\n"]
    for i, (lon, lat) in enumerate(v, 1):
        out.append(f'\t\t<Placemark><name>{i:02d}</name><styleUrl>#cp</styleUrl>'
                   f"<Point><coordinates>{lon!r},{lat!r},0</coordinates></Point></Placemark>\n")
    out.append("\t</Folder>\n</Document>\n</kml>\n")
    open(dest, "w", encoding="utf-8").write("".join(out))
    print(f"wrote {dest}\n  {len(v)} numbered pins + a reference line")
    return dest


def rebuild(edited):
    v = read_vertices(edited)
    dest = edited.replace(" EDITABLE.kml", ".kml")
    if not os.path.exists(dest):
        raise SystemExit(f"no original path file at {dest}")
    x = open(dest, encoding="utf-8", errors="replace").read()
    coords = " ".join(f"{lon!r},{lat!r},0" for lon, lat in v)
    new = re.sub(r"(<LineString>.*?<coordinates>\s*)(.*?)(\s*</coordinates>)",
                 lambda m: m.group(1) + coords + m.group(3), x, flags=re.S)
    if new == x:
        print("no change — the pins match the stored path")
        return
    open(dest, "w", encoding="utf-8").write(new)
    print(f"rebuilt {dest} from {len(v)} pins\n"
          f"  NOW REGENERATE: gen_corridor_tour.py for every tour built from this file, "
          f"then build_tour_package.py --all")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--explode"); ap.add_argument("--rebuild")
    a = ap.parse_args()
    if a.explode:
        explode(a.explode)
    elif a.rebuild:
        rebuild(a.rebuild)
    else:
        raise SystemExit("usage: --explode <path.kml> | --rebuild <path EDITABLE.kml>")
