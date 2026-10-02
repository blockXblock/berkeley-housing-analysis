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

STATUS COMES FROM THE PLACEMARK'S OWN LABEL, which sync_status_from_v4.py keeps equal to the
Explorer's stage for the building (v4, 2026-10-02). The Explorer has eleven stages and the legend
ten colors, so v4_source.KML_BUCKET folds each stage into its legend color; a label still carrying
a legacy v2 word ("In Review", "Permitted") maps to its own color. Four buildings carry no status
in their label and are resolved explicitly below; a building v4 cannot resolve to one project and
whose label carries no stage KEEPS the stage its current style records (reported, never guessed).

  python scripts/tours/restyle_by_status.py
  python scripts/tours/restyle_by_status.py --dry-run
"""
import argparse, collections, re

from scripts.tours import v4_source as V
from scripts.tours.label_format import parts as label_parts

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


def slug(s, agency=None):
    out = "style_status_" + re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return out + ("__" + re.sub(r"[^A-Za-z0-9]+", "_", agency).strip("_") if agency else "")


def agency_exempt(index):
    """{akey: 'UC Project'|'BART Project'} from v4's OWN CLASSIFICATION RULINGS
    (uc_student_housing / bart_joint_development), via v4_source.

    NOT from the existing styleUrl. An earlier version read '#style_UC_Project' out of the
    placemark, which worked exactly once: after the first restyle those placemarks carry
    '#style_status_UC_Project', the check silently failed, and seven UC buildings fell through
    to whatever status their label happened to end with -- 2400 Bowditch to Pre-Application,
    2200 Bancroft and 2556 Haste to Under Construction, 1950 Oxford to Completed. Reading the
    flag is both correct (CLAUDE.md: filter on the flag, never a hardcoded id or a style name)
    and idempotent.
    """
    return {k: r["agency"] for k, r in index[0].items() if r["agency"]}


def style_stage(pm):
    """The stage the placemark's CURRENT style records (style_status_<Stage>[__<Agency>]), or None."""
    m = re.search(r"<styleUrl>#style_status_([^<]+?)(?:__[^<]+?)?(?:_nolabel)?</styleUrl>", pm)
    if not m:
        return None
    return {slug(s)[len("style_status_"):]: s for s in COLOUR}.get(m.group(1))


def classify(name, pm, exempt, index, kept):
    """-> (status, agency or None). AGENCY IS AN OUTLINE, NOT A FILL (John, 2026-08-28).

    Colouring UC and BART buildings purple/magenta outright cost their status entirely: 27
    buildings, 2,928 units, including 2200 Bancroft with excavation and foundations underway
    and 2556 Haste at 556 units under construction -- all reading as "agency" and nothing else.
    Fill now carries the stage and the outline carries the agency, so both are legible at once.
    Their status is not in their label (a BART placemark is named "North Berkeley BART: Bridge 1
    (8 st)"), so it comes from v4 by address, same as everything else.
    """
    agency = None
    if "BART" in name:
        agency = "BART Project"
    # address from the description balloon, else from the head of the label. BOTH are needed:
    # 2400 Bowditch South and 2200 Bancroft South carry plain-text descriptions with no
    # <b>ADDRESS</b>, so a description-only lookup drops two UC wings onto their label's status.
    ad = re.search(r"<b>([^<]*)</b><br/>", pm)
    cands = ([ad.group(1)] if ad else []) + [label_parts(name)[0] if label_parts(name) else ""]
    if agency is None:
        for cand in cands:
            if V.akey(cand) in exempt:
                agency = exempt[V.akey(cand)]
                break
    # the stage itself, from the label, folded to its legend color
    parts = label_parts(name)
    if len(parts) > 1 and V.bucket(parts[-1]) in COLOUR:
        return V.bucket(parts[-1]), agency
    for cand in cands:                      # agency buildings carry no stage in their label
        r = V.lookup(cand, index)
        if r and r["kml_status"] in COLOUR:
            return r["kml_status"], agency
    if name in EXPLICIT:
        e = EXPLICIT[name]
        return (e, agency) if e in COLOUR else (None, agency or e)
    st = style_stage(pm)                    # v4 cannot resolve it: keep what the map says, and say so
    if st and not st.endswith("Project"):
        kept.append(name)
        return st, agency
    return (None, agency)


def kml_colour(rgb, alpha):
    return f"{alpha:02x}{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}"     # aabbggrr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=GEOM)
    ap.add_argument("--out", help="write here instead of over --file")
    ap.add_argument("--label-scale", type=float, default=3.0)
    ap.add_argument("--fill-alpha", type=int, default=128)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    g = open(a.file, encoding="utf-8", errors="replace").read()

    # classify from the POLYGON twins, then apply to both twins by name
    index = V.by_address()
    exempt = agency_exempt(index)
    status_of, unknown, kept = {}, [], []
    for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S):
        nm = re.search(r"<name>([^<]*)</name>", pm)
        if not nm or "<Polygon>" not in pm:
            continue
        st, agency = classify(nm.group(1), pm, exempt, index, kept)
        if st is None and agency is None:
            unknown.append(nm.group(1))
        else:
            status_of.setdefault(nm.group(1), (st, agency))
    if kept:
        print(f"  {len(kept)} building(s) v4 cannot resolve kept the stage their current style records: "
              + "; ".join(k.replace(chr(10), ' · ') for k in kept))
    if unknown:
        raise SystemExit(f"REFUSING: {len(unknown)} building(s) have no resolvable status: {unknown[:5]}")

    counts = collections.Counter(st for st, _ in status_of.values())
    ag = collections.Counter(a for _, a in status_of.values() if a)
    print(f"{'status (fill)':<22} {'bldgs':>5}  colour")
    for s, rgb in PALETTE:
        if s.endswith("Project"):
            continue
        print(f"  {s:<20} {counts.get(s,0):>5}  #{rgb}")
    print(f"{'agency (outline)':<22} {'bldgs':>5}")
    for k, v in ag.most_common():
        print(f"  {k:<20} {v:>5}  #{COLOUR[k]}")
    nofill = sum(1 for st, _ in status_of.values() if st is None)
    if nofill:
        print(f"  ({nofill} agency building(s) with no resolvable stage keep an agency fill)")
    if a.dry_run:
        return

    # one style per (fill, outline) pair actually used -- FILL is the stage, OUTLINE the agency
    styles = []
    for st, agency in sorted({v for v in status_of.values()}, key=lambda t: (t[0] or "", t[1] or "")):
        fill_rgb = COLOUR[st] if st else COLOUR[agency]
        line_rgb = COLOUR[agency] if agency else fill_rgb
        sid = slug(st or agency, agency if st else None)
        common = (f"<LineStyle><color>{kml_colour(line_rgb,255)}</color>"
                  f"<width>{3.0 if agency else 1.5}</width></LineStyle>"
                  f"<PolyStyle><color>{kml_colour(fill_rgb,a.fill_alpha)}</color></PolyStyle>"
                  f"<IconStyle><scale>0.4</scale>{ICON}</IconStyle>")
        styles.append(f'\t<Style id="{sid}"><LabelStyle><scale>{a.label_scale}</scale></LabelStyle>{common}</Style>\n')
        styles.append(f'\t<Style id="{sid}_nolabel"><LabelStyle><scale>0</scale></LabelStyle>{common}</Style>\n')
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
        st, agency = status_of[nm.group(1)]
        sid = slug(st or agency, agency if st else None) + ("_nolabel" if poly else "")
        return re.sub(r"<styleUrl>#[^<]+</styleUrl>", f"<styleUrl>#{sid}</styleUrl>", pm)
    g = re.sub(r"<Placemark>.*?</Placemark>", point, g, flags=re.S)

    defined = set(re.findall(r'<Style id="([^"]+)"', g)) | set(re.findall(r'<StyleMap id="([^"]+)"', g))
    dangling = sorted({u for u in re.findall(r"<styleUrl>#([^<]+)</styleUrl>", g) if u not in defined})
    if dangling:
        raise SystemExit(f"REFUSING TO WRITE — dangling styleUrl(s): {dangling[:5]}")
    open(a.out or a.file, "w", encoding="utf-8").write(g)
    print(f"\n-> {a.out or a.file}")
    print(f"restyled {n[0]} polygon and {n[1]} label placemarks")


if __name__ == "__main__":
    main()
