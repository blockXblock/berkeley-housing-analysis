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
    ap.add_argument("--all", action="store_true",
                    help="label EVERY building the flight passes, not only the orbit targets. A "
                         "label appears when the camera comes within --radius of its building and "
                         "goes when it leaves, so the screen still carries only what is at hand.")
    ap.add_argument("--radius", type=float, default=260.0,
                    help="metres: how close the camera must come before a label is lit")
    ap.add_argument("--max-labels", type=int, default=0,
                    help="cap how many labels may be lit at once; the NEAREST win. 0 = no cap. "
                         "Radius alone is not enough downtown, where 260 m can enclose fifteen "
                         "projects and the screen fills with boxes -- the very problem the "
                         "one-at-a-time rule was meant to solve.")
    ap.add_argument("--move-every", type=int, default=2,
                    help="reposition a visible label every Nth leg. 1 is smoothest; 2 halves the "
                         "file for no visible difference outside an orbit.")
    a = ap.parse_args()

    tour_path = pathlib.Path(f"kml/tours/{a.tour}.kml")
    tour = re.search(r"<gx:Tour>.*?</gx:Tour>", tour_path.read_text(errors="replace"), re.S).group(0)
    g = GEOM.read_text(errors="replace")
    SITES = site_buildings()

    legs = re.findall(r"<gx:FlyTo>.*?</gx:FlyTo>\n?", tour, re.S)
    cams = [(float(m.group(1)), float(m.group(2))) for m in
            (re.search(r"<longitude>([-\d.]+)</longitude>\s*<latitude>([-\d.]+)</latitude>", l) for l in legs)]
    spans = orbits(tour)
    orbit_of = {}
    print(f"  {len(legs)} legs, {len(spans)} orbit(s) detected")

    # which site is each orbit about?
    targets = []
    for lo, hi in spans:
        seg = cams[lo:hi + 1]
        clon = sum(p[0] for p in seg) / len(seg); clat = sum(p[1] for p in seg) / len(seg)
        addr, v = min(SITES.items(), key=lambda kv: (kv[1][0] - clon) ** 2 + (kv[1][1] - clat) ** 2)
        targets.append((lo, hi, addr, v))
        print(f"    legs {lo:>3}-{hi:<3} -> {v[4].splitlines()[0][:46]}")

    # --- ALL MODE: every site the flight actually passes, lit by proximity ---
    if a.all:
        near = {}
        for addr, v in SITES.items():
            if not re.search(r"\d", v[4]):
                continue
            k = math.cos(math.radians(v[1]))
            dmin = min(math.hypot((c[0] - v[0]) * k * 111320, (c[1] - v[1]) * 111320) for c in cams)
            if dmin <= a.radius:
                near[addr] = v
        print(f"    {len(near)} building(s) come within {a.radius:.0f} m of this flight")
        # KEEP THE ORBIT SPANS. --all used to replace targets outright, which threw away which
        # legs are an orbit -- so the building being orbited moved on the same every-other-leg
        # cadence as everything else and visibly stuttered, while orbits-only stayed smooth.
        # John caught exactly that. The spans are retained and used for cadence below.
        orbit_of = {addr: (lo, hi) for lo, hi, addr, _ in targets}
        targets = [(None, None, addr, v) for addr, v in near.items()]

    # render just those labels
    IMGS.mkdir(parents=True, exist_ok=True)
    # ONE subprocess, not one per label. Each invocation pays Python startup and a full read of
    # v2 -- about 1.3 s -- so 58 labels cost 80 s of process churn and almost no rasterising.
    cmd = [sys.executable, "scripts/gen_svg_labels.py", "--outdir", str(IMGS)]
    for _, _, addr, _ in targets:
        cmd += ["--address", addr]
    subprocess.run(cmd, capture_output=True)

    styles, pms, imgs = [], [], []
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
    live = set()          # which labels are currently lit (all-mode)
    out, li, moves = [], 0, 0
    for tok in re.split(r"(<gx:FlyTo>.*?</gx:FlyTo>\n?)", tour, flags=re.S):
        if not tok.startswith("<gx:FlyTo>"):
            out.append(tok); continue
        if a.all:
            # PROXIMITY, NOT SPANS. Light a label when the camera comes inside --radius of its
            # building and drop it when it leaves, so a corridor shows what is beside it rather
            # than every project in the city at once.
            cand = []
            for _, _, addr, v in targets:
                k = math.cos(math.radians(v[1]))
                dm = math.hypot((cams[li][0] - v[0]) * k * 111320,
                                (cams[li][1] - v[1]) * 111320)
                if dm <= a.radius:
                    cand.append((dm, addr))
            cand.sort()
            if a.max_labels:
                cand = cand[:a.max_labels]
            want = {addr for _, addr in cand}
            for addr in want - live:
                out.append(vis(slugify(addr), 1))
            for addr in live - want:
                out.append(vis(slugify(addr), 0))
            live = want
        for lo, hi, addr, v in targets:
            if lo is not None and li == lo:
                out.append(vis(slugify(addr), 1))
        # position the label on the camera's side for this leg
        for lo, hi, addr, v in targets:
            in_span = (lo is not None and lo <= li <= hi)
            # THE BUILDING BEING ORBITED MOVES EVERY LEG. It is the subject of the shot and the
            # camera sweeps fastest around it, so half-rate updates read as a stutter. Everything
            # else -- passed at a distance, drifting slowly across frame -- is fine at half rate,
            # which is what keeps the file small.
            olo, ohi = orbit_of.get(addr, (None, None))
            being_orbited = olo is not None and olo <= li <= ohi
            in_near = (a.all and addr in live
                       and (being_orbited or li % max(a.move_every, 1) == 0))
            if in_span or in_near:
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
            if lo is not None and li == hi:
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
    dest = pathlib.Path.home() / "Desktop" / f"{out_path.stem}.kmz"
    shutil.copy(out_path, dest)
    print(f"  {len(kept)} polygons, {len(pms)} boxed labels, {moves} repositions")
    print(f"  {out_path} ({out_path.stat().st_size/1024:.0f} KB) -> {dest}")


if __name__ == "__main__":
    main()
