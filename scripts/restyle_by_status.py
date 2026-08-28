#!/usr/bin/env python3
"""restyle_by_status.py — make every building's colour actually mean its status.

THE BUG THIS FIXES (measured 2026-08-27). The skyline's colours had drifted until they encoded
almost nothing: 106 buildings shared one yellow that held In Review x75, Completed x18,
Entitled x8 and Permitted x5, while of the 39 Completed buildings only 16 were green -- the rest
wore yellow, blue or orange. The homepage legend on the "17 Largest" video was, in consequence,
false for roughly a third of the map. Colours had been assigned per-placemark by hand over
years, so nothing kept them in step as statuses changed.

THE PALETTE IS ORDINAL, NOT ARBITRARY. The pipeline is a sequence, so the colours read as one:
WARM = paper stages (in review, entitled), COOL = physical stages (permitted, under
construction), GREEN = done. Off-ramps go red; agency-exempt projects go violet, visually
outside the pipeline because that is what they are. A viewer watches a corridor shift
yellow -> orange -> cyan -> blue -> green without memorising ten colours.

Blue for Under Construction and green for Completed are DELIBERATELY UNCHANGED: they are the
site's already-published convention, stated in the "17 Largest" description, so anyone who has
watched the existing videos has learned them.

STATUS COMES FROM THE PLACEMARK'S OWN LABEL, which was verified against v2. Four buildings carry
no status in their label and are resolved explicitly below.

  python scripts/restyle_by_status.py
  python scripts/restyle_by_status.py --dry-run
"""
import argparse, re, collections

GEOM = "kml/geometry/geometry.kml"
ICON = ('<Icon><href>transparent-1x1.png</href></Icon>'
        '<hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>')

PALETTE = [                      # order is the pipeline order, and the legend's order
    ("Pre-Application",    "9e9e9e"),
    ("In Review",          "ffd400"),
    ("Entitled",           "ff8000"),
    ("Permitted",          "00e5ff"),
    ("Under Construction", "2962ff"),
    ("Completed",          "00c853"),
    ("Stalled",            "ff0000"),
    ("Withdrawn",          "b0003a"),
    ("UC Project",         "aa00ff"),
    ("BART Project",       "ff00ff"),
]
COLOUR = dict(PALETTE)

# the four with no status in their label
EXPLICIT = {
    "1717 SAN PABLO Ave": "Under Construction",       # its own description says so
    "Dharma University": "Permitted",                 # description: "permitted for 10 stories"
    "Innovation Zone - North - Bakar": "UC Project",  # Bakar BioEnginuity Hub, a UC facility
    "Innovation Zone - South": "UC Project",          # INFERRED from the name, not from a source
}


def slug(s):
    return "style_status_" + re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def classify(name, pm):
    if "BART" in name:
        return "BART Project"
    if re.search(r"<styleUrl>#style_UC_Project", pm):
        return "UC Project"
    if name in EXPLICIT:
        return EXPLICIT[name]
    parts = [p.strip() for p in name.split("·")]
    if len(parts) > 1 and parts[-1] in COLOUR:
        return parts[-1]
    return None


def kml_colour(rgb, alpha):
    return f"{alpha:02x}{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}"     # aabbggrr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=GEOM)
    ap.add_argument("--label-scale", type=float, default=3.0)
    ap.add_argument("--fill-alpha", type=int, default=128)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    g = open(a.file, encoding="utf-8", errors="replace").read()

    # classify from the POLYGON twins, then apply to both twins by name
    status_of, unknown = {}, []
    for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S):
        nm = re.search(r"<name>([^<]*)</name>", pm)
        if not nm or "<Polygon>" not in pm:
            continue
        s = classify(nm.group(1), pm)
        (status_of.setdefault(nm.group(1), s) if s else unknown.append(nm.group(1)))
    if unknown:
        raise SystemExit(f"REFUSING: {len(unknown)} building(s) have no resolvable status: {unknown[:5]}")

    counts = collections.Counter(status_of.values())
    print(f"{'status':<22} {'bldgs':>5}  colour")
    for s, rgb in PALETTE:
        print(f"  {s:<20} {counts.get(s,0):>5}  #{rgb}")
    if a.dry_run:
        return

    styles = []
    for s, rgb in PALETTE:
        common = (f"<LineStyle><color>{kml_colour(rgb,255)}</color><width>1.5</width></LineStyle>"
                  f"<PolyStyle><color>{kml_colour(rgb,a.fill_alpha)}</color></PolyStyle>"
                  f"<IconStyle><scale>0.4</scale>{ICON}</IconStyle>")
        styles.append(f'\t<Style id="{slug(s)}"><LabelStyle><scale>{a.label_scale}</scale></LabelStyle>{common}</Style>\n')
        styles.append(f'\t<Style id="{slug(s)}_nolabel"><LabelStyle><scale>0</scale></LabelStyle>{common}</Style>\n')
    g = re.sub(r'(<Style id="[^"]+_nolabel">.*?</Style>\n)(?!.*<Style id="[^"]+_nolabel">)',
               lambda m: m.group(1) + "".join(styles), g, count=1, flags=re.S)

    n = [0, 0]
    def point(m):
        pm = m.group(0)
        nm = re.search(r"<name>([^<]*)</name>", pm)
        if not nm or nm.group(1) not in status_of:
            return pm
        poly = "<Polygon>" in pm
        n[0 if poly else 1] += 1
        sid = slug(status_of[nm.group(1)]) + ("_nolabel" if poly else "")
        return re.sub(r"<styleUrl>#[^<]+</styleUrl>", f"<styleUrl>#{sid}</styleUrl>", pm)
    g = re.sub(r"<Placemark>.*?</Placemark>", point, g, flags=re.S)

    defined = set(re.findall(r'<Style id="([^"]+)"', g)) | set(re.findall(r'<StyleMap id="([^"]+)"', g))
    dangling = sorted({u for u in re.findall(r"<styleUrl>#([^<]+)</styleUrl>", g) if u not in defined})
    if dangling:
        raise SystemExit(f"REFUSING TO WRITE — dangling styleUrl(s): {dangling[:5]}")
    open(a.file, "w", encoding="utf-8").write(g)
    print(f"\nrestyled {n[0]} polygon and {n[1]} label placemarks")


if __name__ == "__main__":
    main()
