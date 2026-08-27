#!/usr/bin/env python3
"""split_label_lod.py — stop distant building labels from churning, without losing the skyline.

THE PROBLEM (John, 2026-08-26): building labels jump and reshuffle when seen from a distance.
Measured along the Shattuck cruise, 125-150 buildings fall within 2 km of a typical waypoint
but only 6 within 300 m. Earth declutters by hiding whichever labels overlap, so at distance
150 labels fight for the same screen and the winners change every frame. That is the jumping.
It is not placement -- moving labels streetward would collapse them onto ONE line and make it
worse, and moving them down the facade reintroduces the depth conflict the anchor lift removed.

THE FIX: draw a label only once its building is big enough on screen. KML's <Region>/<Lod> does
exactly that -- minLodPixels is the projected size below which the feature is not drawn.

WHY THIS NEEDS A SPLIT: a Region governs its whole Placemark, and each of ours is a
MultiGeometry of Point + Polygon. Attaching a Region would hide the BUILDING at distance too,
which destroys the skyline -- the thing the flyover exists to show. So each placemark becomes
two:

  POLYGON placemark  keeps the name, the description and the extrusion, and takes a
                     '<style>_nolabel' variant whose LabelStyle scale is 0. No Region: the
                     building is always drawn. Keeping the name and description here is what
                     lets gen_corridor_tour.py and gen_building_loop.py go on reading the file
                     unchanged -- both match on <b>ADDRESS</b> plus <Polygon> in one placemark.

  LABEL placemark    carries the name, the lifted Point, and the Region. This is the only thing
                     that draws text, and only inside the Lod window.

The description is NOT duplicated. Thirty-nine description bodies had already drifted out of
step with their own labels once in this project; two copies of the same prose is how that
happens again.

Idempotent, and reversible with --unsplit.

  python scripts/split_label_lod.py --min-lod 128
  python scripts/split_label_lod.py --unsplit
"""
import argparse, math, re

GEOM = "kml/geometry/geometry.kml"
M = 111320.0


def split(g: str, min_lod: int, max_lod: int, fade: int, min_box_m: float):
    styles = re.findall(r'<Style id="([^"]+)">(.*?)</Style>', g, re.S)
    nolabel = []
    for sid, body in styles:
        if sid.endswith("_nolabel"):
            continue
        b = re.sub(r"<LabelStyle>.*?</LabelStyle>", "<LabelStyle><scale>0</scale></LabelStyle>",
                   body, flags=re.S)
        if "<LabelStyle>" not in b:
            b = "<LabelStyle><scale>0</scale></LabelStyle>" + b
        nolabel.append(f'\t<Style id="{sid}_nolabel">{b}</Style>\n')

    # STYLEMAPS NEED TWINS TOO. 83 of the 196 placemarks point at a <StyleMap>, not a <Style>.
    # The first cut only twinned <Style> elements, so 80 polygon placemarks ended up naming a
    # '#..._nolabel' that did not exist and Earth fell back to its DEFAULT white/grey fill --
    # every In Review project turned grey. A twin map repoints both its pairs at the twins.
    for sid, body in re.findall(r'<StyleMap id="([^"]+)">(.*?)</StyleMap>', g, re.S):
        if sid.endswith("_nolabel"):
            continue
        b2 = re.sub(r"<styleUrl>#([^<]+)</styleUrl>", r"<styleUrl>#\1_nolabel</styleUrl>", body)
        nolabel.append(f'\t<StyleMap id="{sid}_nolabel">{b2}</StyleMap>\n')

    n = 0
    synth = [0]

    def one(m):
        nonlocal n
        pm = m.group(0)
        pt = re.search(r"<Point>.*?</Point>", pm, re.S)
        po = re.search(r"<Polygon>.*?</Polygon>", pm, re.S)
        nm = re.search(r"<name>([^<]*)</name>", pm)
        su = re.search(r"<styleUrl>#([^<]+)</styleUrl>", pm)
        if not (po and nm and su):
            return pm
        n += 1
        cs = re.search(r"<coordinates>\s*(.*?)\s*</coordinates>", po.group(0), re.S).group(1)
        lons = [float(t.split(",")[0]) for t in cs.split()]
        lats = [float(t.split(",")[1]) for t in cs.split()]
        if pt is None:
            # 22 placemarks -- every BART building, Dharma University, both Innovation Zones,
            # 1717 San Pablo -- carry a Polygon and a name but NO Point, so Earth drew their
            # label at the polygon centroid: unregioned, and never lifted clear of the roof
            # either. Synthesise the anchor the others already have.
            roof = max(float(t.split(",")[2]) for t in cs.split())
            clon = sum(lons[:-1]) / (len(lons) - 1)
            clat = sum(lats[:-1]) / (len(lats) - 1)
            z = round(roof + max(3.0, roof * 0.05), 1)
            pt = re.match(r"(?s).*", f"<Point><coordinates>{clon!r},{clat!r},{z}</coordinates>"
                                     f"<altitudeMode>relativeToGround</altitudeMode></Point>")
            synth[0] += 1
        lat0 = sum(lats) / len(lats)
        k = math.cos(math.radians(lat0))
        # PAD THE BOX TO A FLOOR. minLodPixels is a projected SIZE, so without a floor a 10 m
        # ADU would need the camera almost on top of it before its label ever appeared.
        halfy = max((max(lats) - min(lats)) / 2, (min_box_m / 2) / M)
        halfx = max((max(lons) - min(lons)) / 2, (min_box_m / 2) / (M * k))
        cx, cy = (max(lons) + min(lons)) / 2, (max(lats) + min(lats)) / 2
        region = (f"<Region><LatLonAltBox>"
                  f"<north>{cy+halfy!r}</north><south>{cy-halfy!r}</south>"
                  f"<east>{cx+halfx!r}</east><west>{cx-halfx!r}</west></LatLonAltBox>"
                  f"<Lod><minLodPixels>{min_lod}</minLodPixels><maxLodPixels>{max_lod}</maxLodPixels>"
                  f"<minFadeExtent>{fade}</minFadeExtent></Lod></Region>")

        poly_pm = pm.replace(pt.group(0), "") if pt.group(0) in pm else pm
        poly_pm = poly_pm.replace(f"<styleUrl>#{su.group(1)}</styleUrl>",
                                  f"<styleUrl>#{su.group(1)}_nolabel</styleUrl>")
        poly_pm = re.sub(r"<MultiGeometry>\s*(<Polygon>.*?</Polygon>)\s*</MultiGeometry>",
                         r"\1", poly_pm, flags=re.S)
        label_pm = (f"\t\t<Placemark>\n\t\t\t<name>{nm.group(1)}</name>\n"
                    f"\t\t\t<styleUrl>#{su.group(1)}</styleUrl>\n\t\t\t{region}\n"
                    f"\t\t\t{pt.group(0)}\n\t\t</Placemark>")
        return poly_pm + "\n" + label_pm

    out = re.sub(r"\t*<Placemark>.*?</Placemark>", one, g, flags=re.S)
    last = out.rindex("</Style>") + len("</Style>\n")
    out = out[:last] + "".join(nolabel) + out[last:]

    # GATE: refuse to emit a file whose placemarks name styles that are not in it. A dangling
    # styleUrl does not error in Earth -- it silently renders the default, which is how the
    # In Review projects went grey without anything complaining.
    defined = set(re.findall(r'<Style id="([^"]+)"', out)) | set(re.findall(r'<StyleMap id="([^"]+)"', out))
    dangling = sorted({u for u in re.findall(r"<styleUrl>#([^<]+)</styleUrl>", out)
                       if u not in defined})
    if dangling:
        raise SystemExit(f"REFUSING TO WRITE: {len(dangling)} styleUrl(s) resolve to nothing, "
                         f"Earth would render them default grey: {dangling[:5]}")
    return out, n, synth[0]


def unsplit(g: str):
    """Fold every label placemark back into the polygon placemark it came from."""
    labels = {}
    def grab(m):
        pm = m.group(0)
        if "<Region>" not in pm or "<Point>" not in pm or "<Polygon>" in pm:
            return pm
        nm = re.search(r"<name>([^<]*)</name>", pm)
        pt = re.search(r"<Point>.*?</Point>", pm, re.S)
        labels[nm.group(1)] = pt.group(0)
        return ""
    g = re.sub(r"\t*<Placemark>.*?</Placemark>\n?", grab, g, flags=re.S)

    def restore(m):
        pm = m.group(0)
        nm = re.search(r"<name>([^<]*)</name>", pm)
        po = re.search(r"<Polygon>.*?</Polygon>", pm, re.S)
        if not (nm and po and nm.group(1) in labels):
            return pm
        pm = pm.replace(po.group(0), f"<MultiGeometry>{labels[nm.group(1)]}{po.group(0)}</MultiGeometry>")
        return re.sub(r"<styleUrl>#([^<]+)_nolabel</styleUrl>", r"<styleUrl>#\1</styleUrl>", pm)
    g = re.sub(r"\t*<Placemark>.*?</Placemark>", restore, g, flags=re.S)
    g = re.sub(r'\t*<Style id="[^"]+_nolabel">.*?</Style>\n?', "", g, flags=re.S)
    g = re.sub(r'\t*<StyleMap id="[^"]+_nolabel">.*?</StyleMap>\n?', "", g, flags=re.S)
    return g, len(labels)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-lod", type=int, default=128,
                    help="projected pixels below which a label is not drawn; higher = labels "
                         "appear later/closer")
    ap.add_argument("--max-lod", type=int, default=-1, help="-1 = no upper bound")
    ap.add_argument("--fade", type=int, default=64, help="fade-in extent in pixels; 0 = pop")
    ap.add_argument("--min-box", type=float, default=40.0, help="floor on the region box, metres")
    ap.add_argument("--unsplit", action="store_true")
    ap.add_argument("--file", default=GEOM)
    a = ap.parse_args()
    g = open(a.file, encoding="utf-8", errors="replace").read()
    already = "<Region>" in g
    if a.unsplit:
        if not already:
            raise SystemExit("not split — nothing to undo")
        out, n = unsplit(g)
        print(f"{a.file}: folded {n} label placemarks back in")
    else:
        if already:
            out, _ = unsplit(g)          # re-split cleanly so --min-lod can be re-tuned
            g = out
        out, n, sy = split(g, a.min_lod, a.max_lod, a.fade, a.min_box)
        print(f"{a.file}: split {n} placemarks into polygon + label; "
              f"labels draw above {a.min_lod} px (fade {a.fade}), box floor {a.min_box:.0f} m; "
              f"{sy} label anchors synthesised for placemarks that had no Point")
    open(a.file, "w", encoding="utf-8").write(out)
