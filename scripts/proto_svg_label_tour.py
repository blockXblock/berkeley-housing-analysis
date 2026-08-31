#!/usr/bin/env python3
"""proto_svg_label_tour.py — one rich boxed label at a time, appearing as the camera arrives.

THE PROBLEM (John, across 2026-08-30/31): "lots of unconnected text floating above the image."
Every building in view is labelled all the time, so a downtown frame carries thirty labels and
none of them owns a tower. Restyling does not fix that -- a tidier label is still one of thirty.

TWO CHANGES, TOGETHER:

  1. THE LABEL IS AN IMAGE. Earth ignores newlines in <name>, so a text label is one line
     however long. As a rendered PNG it carries four: address, beds and status in the status
     colour, height and floor area, architect and date. See gen_svg_labels.py.

  2. ONLY THE CURRENT BUILDING IS LABELLED. gx:AnimatedUpdate switches a placemark's visibility
     DURING the tour, so each label appears as its orbit begins and goes as the camera climbs
     away. One label on screen, unmistakably the one being flown.

The floating text twins are dropped entirely from this document -- the polygons stay, so the
skyline is unchanged, but nothing is labelled except the building in shot.

  python scripts/proto_svg_label_tour.py
"""
import os, pathlib, re, shutil, subprocess, sys, zipfile

ROOT = pathlib.Path(".")
GEOM = ROOT / "kml/geometry/geometry.kml"
TOUR = ROOT / "kml/tours/uc-dormitories.kml"
IMGS = ROOT / "scratch/2026-08-31/svg-labels"
OUT = ROOT / "scratch/2026-08-31/UC-dorm-svg-labels.kmz"
# ANCHOR AND SIZE, both learned from watching it (John, 2026-08-31): "the labels are far above
# the structure. they are not visible at all during the spiral. during the flight between
# buildings, they are visible as large rectangles far away."
#
# The orbit camera sits at roof + 10 to roof + 30 m and tilts 66-76 degrees -- close to level,
# looking at the building. A label at roof + 34 is ABOVE that view axis, so it leaves the top of
# frame exactly when the building is being examined. Dropping the anchor onto the building's own
# upper facade puts it in the middle of the shot AND makes it look attached rather than moored
# above. Earth draws icons as billboards over the scene, so it is not occluded by the wall.
#
# Icon scale is SCREEN size, near enough independent of distance -- which is why 7.0 read as a
# large rectangle from far away. Halved.
LIFT_FRACTION = 0.80    # anchor at this fraction of roof height: on the upper facade
ICON_SCALE = 3.5


def main():
    g = GEOM.read_text(errors="replace")
    tour_src = TOUR.read_text(errors="replace")
    tour = re.search(r"<gx:Tour>.*?</gx:Tour>", tour_src, re.S).group(0)

    # --- keep the polygons and their styles; DROP every label twin ---
    kept, dropped = [], 0
    for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S):
        if "<Polygon>" in pm:
            kept.append(re.sub(r"<name>[^<]*</name>", "<name></name>", pm, count=1))
        else:
            dropped += 1
    styles = "".join(re.findall(r"<Style id=\"[^\"]*\">.*?</Style>|<StyleMap id=\"[^\"]*\">.*?</StyleMap>", g, re.S))

    # --- one icon placemark per rendered label, hidden until its moment ---
    order = [s for s in re.findall(r"<!--BUILDING-IN ([a-z0-9-]+)-->", tour)]
    label_pms, icon_styles, imgs = [], [], []
    for slug in order:
        png = IMGS / f"{slug}.png"
        if not png.exists():
            print(f"  no image for {slug} — skipped"); continue
        imgs.append(png)
        # anchor: the site centroid at roof height, taken from the polygon we kept
        pm = next((p for p in kept if slug.split("-")[0] in p and slug.split("-")[1] in p.lower()), None)
        cs = re.search(r"<coordinates>\s*(.*?)\s*</coordinates>", pm, re.S).group(1) if pm else None
        pts = [tuple(map(float, t.split(",")[:3])) for t in cs.split() if "," in t] if cs else []
        if not pts:
            print(f"  no anchor for {slug} — skipped"); continue
        lon = sum(p[0] for p in pts) / len(pts); lat = sum(p[1] for p in pts) / len(pts)
        roof = max(p[2] for p in pts if len(p) > 2)
        icon_styles.append(
            f'<Style id="lbl_{slug}"><IconStyle><scale>{ICON_SCALE}</scale>'
            f'<Icon><href>{png.name}</href></Icon>'
            f'<hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/></IconStyle>'
            f'<LabelStyle><scale>0</scale></LabelStyle></Style>')
        label_pms.append(
            f'<Placemark id="pm_{slug}"><name></name><visibility>0</visibility>'
            f'<styleUrl>#lbl_{slug}</styleUrl>'
            f'<Point><coordinates>{lon!r},{lat!r},{roof * LIFT_FRACTION:.1f}</coordinates>'
            f'<altitudeMode>relativeToGround</altitudeMode></Point></Placemark>')

    # --- switch each label on at BUILDING-IN and off at BUILDING-OUT ---
    def upd(slug, vis):
        return (f'\t\t\t<gx:AnimatedUpdate><gx:duration>0</gx:duration><Update><targetHref/>'
                f'<Change><Placemark targetId="pm_{slug}"><visibility>{vis}</visibility>'
                f'</Placemark></Change></Update></gx:AnimatedUpdate>\n')
    # ON AT THE ORBIT, NOT THE APPROACH. The marker sits before the run-in, so switching there
    # put the label on screen for the whole crossing -- a billboard hanging over open sky, which
    # is what John saw as "large rectangles far away". Skip past the approach FlyTo so the label
    # arrives with the building.
    def on_after_approach(m):
        return ""
    tour = re.sub(r"(\t*<!--BUILDING-IN ([a-z0-9-]+)-->\n)(\s*<gx:FlyTo>.*?</gx:FlyTo>\n)",
                  lambda m: m.group(3) + upd(m.group(2), 1), tour, flags=re.S)
    tour = re.sub(r"\t*<!--BUILDING-OUT ([a-z0-9-]+)-->\n", lambda m: upd(m.group(1), 0), tour)

    doc = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">\n'
           '<Document>\n\t<name>UC dormitories · SVG labels · one at a time</name>\n'
           + styles + "".join(icon_styles) + "\n" + tour + "\n"
           + "".join(kept) + "".join(label_pms) + "\n</Document>\n</kml>\n")

    from xml.dom import minidom
    minidom.parseString(doc)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    EPOCH = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("doc.kml", EPOCH); zi.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(zi, doc)
        for p in imgs:
            zi2 = zipfile.ZipInfo(p.name, EPOCH); zi2.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi2, p.read_bytes())
    shutil.copy(OUT, pathlib.Path.home() / "Desktop" / "UC dorm SVG labels.kmz")
    print(f"  {len(kept)} polygons kept, {dropped} floating text labels dropped")
    print(f"  {len(label_pms)} image labels, shown one at a time: {', '.join(order)}")
    print(f"  {OUT}  ({OUT.stat().st_size/1024:.0f} KB)  -> ~/Desktop/UC dorm SVG labels.kmz")


if __name__ == "__main__":
    main()
