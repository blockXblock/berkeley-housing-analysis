#!/usr/bin/env python3
"""svg_label_tour.py — boxed image labels that ride the camera, for ANY existing tour.

The dorm prototype needed BUILDING-IN/BUILDING-OUT comments emitted by gen_dorm_tour.py. That
does not generalise: the corridor tours are built by a different generator and regenerating a
published tour just to add comments is a needless risk. This finds the orbits itself, from the
camera track -- a run of legs whose heading sweeps through more than 270 degrees -- so it works
on any tour already on disk, including ones recorded from.

WHAT IT DOES, and why each part is there (all of it learned by John watching it):

  * ONE LABEL AT A TIME. gx:AnimatedUpdate switches visibility, so a label appears when its
    orbit begins and goes when it ends. Thirty labels floating at once was the original problem.
  * THE LABEL RIDES THE NEAR SIDE. Earth depth-tests icons against buildings, so a fixed anchor
    is swallowed as the camera closes. On every leg it moves to the camera's bearing from the
    centroid, at the footprint's circumradius plus a margin -- outside any shape, always facing
    the camera.
  * ON EVERY LEG, WITH THE LEG'S DURATION. Moving every 4th leg snapped; every leg is ~7.5
    degrees and Earth interpolates over the duration.
  * THE IMAGE IS CROPPED TO THE BOX. IconStyle scales the whole PNG, and a padded one spends
    most of the scale on nothing.

  python scripts/svg_label_tour.py --tour shattuck-s2n-path --street shattuck
"""
import argparse, math, os, pathlib, re, shutil, subprocess, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_building_loop import buildings as site_buildings
from gen_svg_labels import slug as slugify
from xml.dom import minidom

GEOM = pathlib.Path("kml/geometry/geometry.kml")
IMGS = pathlib.Path("scratch/2026-08-31/svg-labels")
LIFT_FRACTION = 0.86     # nudged up from 0.80: at 0.80 the box could land on Earth's own
                         # "Image Landsat / Copernicus" strip at the bottom of frame
MARGIN_M = 14.0
ICON_SCALE = 2.5


def orbits(tour):
    """Index spans of legs whose heading sweeps past 270 degrees — i.e. an orbit."""
    hd = [float(h) for h in re.findall(r"<heading>([-\d.]+)</heading>", tour)]
    spans, cur, tot = [], [0], 0.0
    for i in range(1, len(hd)):
        d = (hd[i] - hd[i - 1] + 540) % 360 - 180
        if 0.5 < abs(d) < 25:
            cur.append(i); tot += d
        else:
            if abs(tot) > 270:
                spans.append((cur[0], cur[-1]))
            cur, tot = [i], 0.0
    if abs(tot) > 270:
        spans.append((cur[0], cur[-1]))
    return spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", required=True, help="tour stem in kml/tours/")
    ap.add_argument("--street", default=None, help="street-label set to fold in, e.g. shattuck")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    tour_path = pathlib.Path(f"kml/tours/{a.tour}.kml")
    tour = re.search(r"<gx:Tour>.*?</gx:Tour>", tour_path.read_text(errors="replace"), re.S).group(0)
    g = GEOM.read_text(errors="replace")
    SITES = site_buildings()

    legs = re.findall(r"<gx:FlyTo>.*?</gx:FlyTo>\n?", tour, re.S)
    cams = [(float(m.group(1)), float(m.group(2))) for m in
            (re.search(r"<longitude>([-\d.]+)</longitude>\s*<latitude>([-\d.]+)</latitude>", l) for l in legs)]
    spans = orbits(tour)
    print(f"  {len(legs)} legs, {len(spans)} orbit(s) detected")

    # which site is each orbit about?
    targets = []
    for lo, hi in spans:
        seg = cams[lo:hi + 1]
        clon = sum(p[0] for p in seg) / len(seg); clat = sum(p[1] for p in seg) / len(seg)
        addr, v = min(SITES.items(), key=lambda kv: (kv[1][0] - clon) ** 2 + (kv[1][1] - clat) ** 2)
        targets.append((lo, hi, addr, v))
        print(f"    legs {lo:>3}-{hi:<3} -> {v[4].splitlines()[0][:46]}")

    # render just those labels
    IMGS.mkdir(parents=True, exist_ok=True)
    for _, _, addr, _ in targets:
        subprocess.run([sys.executable, "scripts/gen_svg_labels.py", "--address", addr,
                        "--outdir", str(IMGS)], capture_output=True)

    styles, pms, imgs, updates = [], [], [], {}
    for lo, hi, addr, v in targets:
        s = slugify(addr); png = IMGS / f"{s}.png"
        if not png.exists():
            print(f"    no image for {s} — skipped"); continue
        imgs.append(png)
        styles.append(f'<Style id="lbl_{s}"><IconStyle><scale>{ICON_SCALE}</scale>'
                      f'<Icon><href>{png.name}</href></Icon>'
                      f'<hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/></IconStyle>'
                      f'<LabelStyle><scale>0</scale></LabelStyle></Style>')
        pms.append(f'<Placemark id="pm_{s}"><name></name><visibility>0</visibility>'
                   f'<styleUrl>#lbl_{s}</styleUrl><Point>'
                   f'<coordinates>{v[0]!r},{v[1]!r},{v[2] * LIFT_FRACTION:.1f}</coordinates>'
                   f'<altitudeMode>relativeToGround</altitudeMode></Point></Placemark>')
        updates[lo] = ("on", s)
        updates[hi] = ("off", s)
        for i in range(lo, hi + 1):
            updates.setdefault(i, ("move", s, addr))

    def vis(s, v, secs=0.0):
        return (f'\t\t\t<gx:AnimatedUpdate><gx:duration>{secs:.2f}</gx:duration><Update><targetHref/>'
                f'<Change><Placemark targetId="pm_{s}"><visibility>{v}</visibility></Placemark>'
                f'</Change></Update></gx:AnimatedUpdate>\n')

    def move(s, lon, lat, alt, secs):
        return (f'\t\t\t<gx:AnimatedUpdate><gx:duration>{secs:.2f}</gx:duration><Update><targetHref/>'
                f'<Change><Placemark targetId="pm_{s}"><Point>'
                f'<coordinates>{lon:.8f},{lat:.8f},{alt:.1f}</coordinates>'
                f'<altitudeMode>relativeToGround</altitudeMode></Point></Placemark>'
                f'</Change></Update></gx:AnimatedUpdate>\n')

    # rebuild the playlist leg by leg
    out, li, moves = [], 0, 0
    for tok in re.split(r"(<gx:FlyTo>.*?</gx:FlyTo>\n?)", tour, flags=re.S):
        if not tok.startswith("<gx:FlyTo>"):
            out.append(tok); continue
        for lo, hi, addr, v in targets:
            if li == lo:
                out.append(vis(slugify(addr), 1))
        # position the label on the camera's side for this leg
        for lo, hi, addr, v in targets:
            if lo <= li <= hi:
                blon, blat, roof, rad = v[0], v[1], v[2], v[3]
                clon, clat = cams[li]
                k = math.cos(math.radians(blat))
                dx, dy = (clon - blon) * k, clat - blat
                d = math.hypot(dx, dy) or 1e-9
                r = (rad + MARGIN_M) / 111320.0
                dur = re.search(r"<gx:duration>([0-9.]+)</gx:duration>", tok)
                out.append(move(slugify(addr), blon + dx / d * r / k, blat + dy / d * r,
                                roof * LIFT_FRACTION, float(dur.group(1)) if dur else 0.0))
                moves += 1
        out.append(tok)
        for lo, hi, addr, v in targets:
            if li == hi:
                out.append(vis(slugify(addr), 0))
        li += 1
    tour = "".join(out)

    # geometry: polygons only, every floating text label dropped
    kept = [re.sub(r"<name>[^<]*</name>", "<name></name>", pm, count=1)
            for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S) if "<Polygon>" in pm]
    geom_styles = "".join(re.findall(r"<Style id=\"[^\"]*\">.*?</Style>|<StyleMap id=\"[^\"]*\">.*?</StyleMap>", g, re.S))

    # fold in the amber street signs so it is one file to load
    street = ""
    if a.street:
        sp = pathlib.Path(f"kml/tours/labels/{a.street}-street-labels.kml")
        if sp.exists():
            st = sp.read_text(errors="replace")
            street = ("".join(re.findall(r"<Style id=\"[^\"]*\">.*?</Style>", st, re.S))
                      + "".join(re.findall(r"<Placemark>.*?</Placemark>", st, re.S)))
            imgs.append(pathlib.Path("kml/tours/labels/transparent-1x1.png"))
            print(f"    folded in {a.street} street signs")

    doc = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">\n'
           f'<Document>\n\t<name>{a.tour} · SVG labels · one at a time</name>\n'
           + geom_styles + "".join(styles) + "\n" + tour + "\n"
           + "".join(kept) + "".join(pms) + street + "\n</Document>\n</kml>\n")
    minidom.parseString(doc)

    out_path = pathlib.Path(a.out or f"scratch/2026-08-31/{a.tour}-svg-labels.kmz")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    EPOCH = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("doc.kml", EPOCH); zi.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(zi, doc)
        for p in dict.fromkeys(imgs):
            if p.exists():
                zi2 = zipfile.ZipInfo(p.name, EPOCH); zi2.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(zi2, p.read_bytes())
    dest = pathlib.Path.home() / "Desktop" / f"{a.tour} SVG labels.kmz"
    shutil.copy(out_path, dest)
    print(f"  {len(kept)} polygons, {len(pms)} boxed labels, {moves} repositions")
    print(f"  {out_path} ({out_path.stat().st_size/1024:.0f} KB) -> {dest}")


if __name__ == "__main__":
    main()
