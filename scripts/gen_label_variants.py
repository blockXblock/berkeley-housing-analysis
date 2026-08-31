#!/usr/bin/env python3
"""gen_label_variants.py — three ways to label a skyline, as loadable experiments.

WHY. John asked to fold labels onto two lines. Google Earth does NOT honour a newline inside
<name> -- it renders one long line regardless -- so the fold shipped on 2026-08-30 does nothing
on screen. He then asked whether we can box them, and to see the options as experiments.

KML HAS NO LABEL BOX. LabelStyle carries a scale and a colour and nothing else; the only way to
draw a real box behind text is to rasterise the text into a PNG and use it as the icon, which
needs an image library this machine does not have. But a box is a weak answer to the actual
complaint -- "hard to see which label is for which building" -- because a box groups the TEXT.
What ties text to a building is a leader line, and KML gives that away free: a Point with
<extrude>1</extrude> draws a line from the label down to the ground.

  A  compact     one line, status dropped -- the FILL already encodes status, so the word is
                 redundant ink. Shortest possible label.
  B  stacked     two placemarks per building: address above, detail below, smaller and dimmer.
                 A real two-line label, since KML will not give us one.
  C  tethered    B plus the extruded leader line, so every label is visibly tied to its roof.

Each variant is a complete geometry document -- load one at a time and look at downtown.

  python scripts/gen_label_variants.py
"""
import os, re, shutil, sys, zipfile, pathlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from label_format import parts

GEOM = pathlib.Path("kml/geometry/geometry.kml")
OUT = pathlib.Path("scratch/2026-08-30/label-variants")
ICON = pathlib.Path("kml/tours/labels/transparent-1x1.png")
DETAIL_STYLE = (
    '<Style id="label_detail"><IconStyle><scale>0.4</scale>'
    '<Icon><href>transparent-1x1.png</href></Icon>'
    '<hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/></IconStyle>'
    '<LabelStyle><scale>1.3</scale><color>ccd8d8d8</color></LabelStyle>'
    '<LineStyle><color>66ffffff</color><width>1.4</width></LineStyle></Style>\n'
)
TETHER_STYLE = (
    '<Style id="label_tether"><IconStyle><scale>0.4</scale>'
    '<Icon><href>transparent-1x1.png</href></Icon>'
    '<hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/></IconStyle>'
    '<LabelStyle><scale>2.0</scale></LabelStyle>'
    '<LineStyle><color>88ffffff</color><width>1.6</width></LineStyle></Style>\n'
)
DETAIL_DROP_M = 16.0          # how far below the address line the detail sits


def label_points(g):
    """Every label twin: the Point placemarks that carry a visible name."""
    for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S):
        if "<Point>" not in pm or "<Polygon>" in pm:
            continue
        nm = re.search(r"<name>([^<]*)</name>", pm, re.S)
        co = re.search(r"<coordinates>([^<]*)</coordinates>", pm)
        if nm and co and len(parts(nm.group(1))) >= 2:
            yield pm, nm.group(1), co.group(1)


def write(name, doc):
    OUT.mkdir(parents=True, exist_ok=True)
    kml = OUT / f"{name}.kml"
    kml.write_text(doc, encoding="utf-8")
    kmz = OUT / f"{name}.kmz"
    EPOCH = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(kmz, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("doc.kml", EPOCH); zi.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(zi, doc)
        if ICON.exists():
            zi2 = zipfile.ZipInfo(ICON.name, EPOCH); zi2.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi2, ICON.read_bytes())
    return kmz


def main():
    g = GEOM.read_text(errors="replace")
    made = []

    # ---- A: compact one-liner, status dropped (the fill already says it) ----
    a = g
    n = 0
    for pm, name, _ in label_points(g):
        bits = parts(name)
        short = " · ".join(bits[:-1]) if len(bits) > 2 else bits[0]
        if short != name:
            a = a.replace(f"<name>{name}</name>", f"<name>{short}</name>")
            n += 1
    a = a.replace("Berkeley Housing Geometry", "LABELS A · compact · Berkeley Housing Geometry", 1)
    made.append(("A-compact", write("A-compact", a), f"{n} labels shortened, status word dropped"))

    # ---- B: stacked pair, and C: stacked pair with a leader line ----
    for tag, tether in (("B-stacked", False), ("C-tethered", True)):
        doc = g
        style = DETAIL_STYLE + (TETHER_STYLE if tether else "")
        # INSERT before the LAST </Document>; do not strip it. Stripping every occurrence and
        # re-appending left </kml> stranded and neither variant parsed.
        doc = re.sub(r"(<Document>\s*<name>[^<]*</name>)", r"\1\n" + style, doc, count=1)
        extra, n = [], 0
        for pm, name, coords in label_points(g):
            bits = parts(name)
            lon, lat, alt = (float(x) for x in coords.split(",")[:3])
            addr, detail = bits[0], " · ".join(bits[1:])
            # the twin keeps the ADDRESS only; a second placemark carries the detail below it
            new_pm = pm.replace(f"<name>{name}</name>", f"<name>{addr}</name>")
            if tether:
                new_pm = re.sub(r"<Point>", "<Point><extrude>1</extrude>", new_pm, count=1)
                new_pm = re.sub(r"<styleUrl>#[^<]*</styleUrl>", "<styleUrl>#label_tether</styleUrl>", new_pm, count=1)
            doc = doc.replace(pm, new_pm)
            extra.append(
                f'<Placemark><name>{detail}</name><styleUrl>#label_detail</styleUrl>'
                f'<Point>{"<extrude>1</extrude>" if tether else ""}'
                f'<coordinates>{lon!r},{lat!r},{max(alt - DETAIL_DROP_M, 2.0)}</coordinates>'
                f'<altitudeMode>relativeToGround</altitudeMode></Point></Placemark>\n')
            n += 1
        # the hidden polygon twins still carry the folded name; flatten those too so no
        # stray newline survives anywhere in the document
        for name2 in set(re.findall(r"<name>([^<]*)</name>", doc, re.S)):
            if "\n" in name2:
                doc = doc.replace(f"<name>{name2}</name>", f"<name>{' · '.join(parts(name2))}</name>")
        cut = doc.rindex("</Document>")
        doc = doc[:cut] + "".join(extra) + doc[cut:]
        doc = doc.replace("Berkeley Housing Geometry",
                          f"LABELS {tag[0]} · {'tethered' if tether else 'stacked'} · Berkeley Housing Geometry", 1)
        made.append((tag, write(tag, doc),
                     f"{n} buildings given a second label {DETAIL_DROP_M:.0f} m below"
                     + (", each tied to the ground by a leader line" if tether else "")))

    desk = pathlib.Path.home() / "Desktop"
    for tag, path, note in made:
        shutil.copy(path, desk / f"LABELS {tag}.kmz")
        print(f"  {tag:<12} {path.stat().st_size/1024:5.0f} KB  {note}")
    print(f"\n  copied to {desk} as 'LABELS A-compact.kmz' etc — load ONE at a time")


if __name__ == "__main__":
    main()
