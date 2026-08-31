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
import math, os, pathlib, re, shutil, subprocess, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_building_loop import buildings as site_buildings
from gen_svg_labels import slug as slugify

SITES = site_buildings()

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
LIFT_FRACTION = 0.80    # anchor at this fraction of roof height: level with the upper facade
ICON_SCALE = 3.5
MARGIN_M = 14.0         # how far OUTSIDE the footprint's bounding circle the label rides
STEP = 4                # move the label every Nth orbit camera

# THE LABEL RIDES THE NEAR SIDE. (John, 2026-08-31: "the labels ... sink inside building as the
# flight approaches ... since the geometry of each building, or set of buildings is complex --
# sometimes two large parallelepipeds at right angles to each other -- solving the label
# visibility problem is interesting. A good solution will have many applications.")
#
# Earth DEPTH-TESTS icons against 3D geometry -- they are not drawn over it, which is what I had
# assumed. So any anchor inside the building's mass is swallowed as the camera closes in, and a
# centroid anchor is inside the mass by definition. Raising it clear of the roof fixes occlusion
# but puts it back out of frame during the orbit, which is where this started.
#
# The general fix does not depend on the shape at all: keep the label BETWEEN the camera and the
# building. On every orbit step, move it to the camera's own bearing from the centroid, at the
# footprint's circumradius plus a margin -- outside the mass whatever that mass looks like,
# because the circumradius bounds any footprint, L-shaped or two blocks at right angles or a
# thirteen-building BART site. It stays at facade height, so it reads as belonging to the
# building rather than floating over it, and it is always on the side the camera can see.
#
# This is why it generalises: it needs a centroid and a bounding radius, and nothing else.


def main():
    geo = {}
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
        # centroid, roof and CIRCUMRADIUS from the shared site aggregation -- one entry per
        # SITE, so a two-wing project is one shape with one bounding circle, which is exactly
        # what a label needs to stay outside of.
        site = next((v for k, v in SITES.items() if slugify(k) == slug), None)
        if not site:
            print(f"  no site for {slug} — skipped"); continue
        lon, lat, roof, rad = site[0], site[1], site[2], site[3]
        geo[slug] = (lon, lat, roof, rad)
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

    # --- MOVE THE LABEL TO THE CAMERA'S SIDE, EVERY STEP CAMERAS ---
    def move(slug, lon, lat, alt):
        return (f'\t\t\t<gx:AnimatedUpdate><gx:duration>0</gx:duration><Update><targetHref/>'
                f'<Change><Placemark targetId="pm_{slug}"><Point>'
                f'<coordinates>{lon:.8f},{lat:.8f},{alt:.1f}</coordinates>'
                f'<altitudeMode>relativeToGround</altitudeMode></Point></Placemark>'
                f'</Change></Update></gx:AnimatedUpdate>\n')

    out, cur, n_moves = [], None, 0
    # walk the playlist: track which building we are in, and rewrite each FlyTo with a move
    for tok in re.split(r"(<gx:FlyTo>.*?</gx:FlyTo>\n|<gx:AnimatedUpdate>.*?</gx:AnimatedUpdate>\n)",
                        tour, flags=re.S):
        if tok.startswith("<gx:AnimatedUpdate>"):
            m = re.search(r'targetId="pm_([a-z0-9-]+)"><visibility>(\d)', tok)
            if m:
                cur = m.group(1) if m.group(2) == "1" else None
                idx = 0
            out.append(tok); continue
        if tok.startswith("<gx:FlyTo>") and cur and cur in geo:
            lon, lat, roof, rad = geo[cur]
            c = re.search(r"<longitude>([-\d.]+)</longitude>\s*<latitude>([-\d.]+)</latitude>", tok)
            if c and idx % STEP == 0:
                clon, clat = float(c.group(1)), float(c.group(2))
                k = math.cos(math.radians(lat))
                dx, dy = (clon - lon) * k, (clat - lat)
                d = math.hypot(dx, dy) or 1e-9
                r = (rad + MARGIN_M) / 111320.0          # ride just outside the bounding circle
                out.append(move(cur, lon + dx / d * r / k, lat + dy / d * r,
                                roof * LIFT_FRACTION))
                n_moves += 1
            idx += 1
        out.append(tok)
    tour = "".join(out)
    print(f"  {n_moves} label repositions — the box rides the camera's side of each building")

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
