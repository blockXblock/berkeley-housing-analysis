#!/usr/bin/env python3
"""recolour_class.py — give a named class of buildings its own colour in geometry.kml.

WHY (John, 2026-08-26): the 18 BART joint-development buildings inherited
style_Pre_Application_parcel and rendered SILVER #c0c0c0, so an entire 1,357-unit programme
read as inert background. They are a distinct class -- agency-exempt like UC, self-permitted
outside the city process -- and deserve to be legible as one.

IT CANNOT JUST RECOLOUR THE SHARED STYLE. style_Pre_Application_parcel is also worn by a
non-BART building, so editing it in place would drag an unrelated project along. This mints a
DEDICATED style (plus the _nolabel twin split_label_lod.py needs) and repoints only the matched
placemarks -- both the polygon twin and its label twin.

Colours are given as #rrggbb and converted to KML's aabbggrr, which is byte-reversed and the
single easiest thing to get wrong here.

  python scripts/recolour_class.py --match BART --style-id style_BART_project --colour ff00ff
"""
import argparse, re

GEOM = "kml/geometry/geometry.kml"
ICON = ('<Icon><href>transparent-1x1.png</href></Icon>'
        '<hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>')


def kml_colour(rgb, alpha):
    r, g, b = rgb[0:2], rgb[2:4], rgb[4:6]
    return f"{alpha:02x}{b}{g}{r}"          # aabbggrr, not aarrggbb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", required=True, help="substring of the placemark name")
    ap.add_argument("--style-id", required=True)
    ap.add_argument("--colour", required=True, help="#rrggbb, e.g. ff00ff")
    ap.add_argument("--fill-alpha", type=int, default=128)
    ap.add_argument("--label-scale", type=float, default=3.0)
    ap.add_argument("--file", default=GEOM)
    a = ap.parse_args()
    rgb = a.colour.lstrip("#")
    g = open(a.file, encoding="utf-8", errors="replace").read()

    line, fill = kml_colour(rgb, 255), kml_colour(rgb, a.fill_alpha)
    common = (f"<LineStyle><color>{line}</color><width>1.5</width></LineStyle>"
              f"<PolyStyle><color>{fill}</color></PolyStyle>"
              f'<IconStyle><scale>0.4</scale>{ICON}</IconStyle>')
    new = (f'\t<Style id="{a.style_id}"><LabelStyle><scale>{a.label_scale}</scale></LabelStyle>{common}</Style>\n'
           f'\t<Style id="{a.style_id}_nolabel"><LabelStyle><scale>0</scale></LabelStyle>{common}</Style>\n')
    g = re.sub(r'(<Style id="[^"]+_nolabel">.*?</Style>\n)(?!.*<Style id="[^"]+_nolabel">)',
               lambda m: m.group(1) + new, g, count=1, flags=re.S)

    n = [0, 0]
    def point(m):
        pm = m.group(0)
        nm = re.search(r"<name>([^<]*)</name>", pm)
        if not nm or a.match not in nm.group(1):
            return pm
        poly = "<Polygon>" in pm
        n[0 if poly else 1] += 1
        target = f"{a.style_id}_nolabel" if poly else a.style_id
        return re.sub(r"<styleUrl>#[^<]+</styleUrl>", f"<styleUrl>#{target}</styleUrl>", pm)
    g = re.sub(r"<Placemark>.*?</Placemark>", point, g, flags=re.S)

    defined = set(re.findall(r'<Style id="([^"]+)"', g)) | set(re.findall(r'<StyleMap id="([^"]+)"', g))
    dangling = sorted({u for u in re.findall(r"<styleUrl>#([^<]+)</styleUrl>", g) if u not in defined})
    if dangling:
        raise SystemExit(f"REFUSING TO WRITE — dangling styleUrl(s), Earth would render grey: {dangling[:5]}")
    open(a.file, "w", encoding="utf-8").write(g)
    print(f"{a.file}: '{a.match}' -> #{rgb}  (line {line}, fill {fill})")
    print(f"  repointed {n[0]} polygon placemarks and {n[1]} label placemarks")


if __name__ == "__main__":
    main()
