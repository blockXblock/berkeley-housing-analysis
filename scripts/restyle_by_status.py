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
import argparse, collections, re, sqlite3

GEOM = "kml/geometry/geometry.kml"
DB = "databases/berkeley_housing_v2.db"
ICON = ('<Icon><href>transparent-1x1.png</href></Icon>'
        '<hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>')

STATUS_BY_ADDR = {}

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


def agency_exempt(db=DB):
    """{ADDRESS: 'UC Project'|'BART Project'} from v2's OWN CLASSIFICATION FLAGS.

    NOT from the existing styleUrl. An earlier version read '#style_UC_Project' out of the
    placemark, which worked exactly once: after the first restyle those placemarks carry
    '#style_status_UC_Project', the check silently failed, and seven UC buildings fell through
    to whatever status their label happened to end with -- 2400 Bowditch to Pre-Application,
    2200 Bancroft and 2556 Haste to Under Construction, 1950 Oxford to Completed. Reading the
    flag is both correct (CLAUDE.md: filter on the flag, never a hardcoded id or a style name)
    and idempotent.
    """
    out = {}
    for addr, code in sqlite3.connect(db).execute(
            "select f.address_display, t.code from project_classifications pc "
            "join vocabulary_classification_types t on t.id=pc.classification_type_id "
            "join v_projects_flat f on f.project_id=pc.project_id "
            "where t.code in ('uc_project','bart_project')"):
        if addr:
            out[addr.upper().strip()] = "UC Project" if code == "uc_project" else "BART Project"
    return out


def classify(name, pm, exempt):
    """-> (status, agency or None). AGENCY IS AN OUTLINE, NOT A FILL (John, 2026-08-28).

    Colouring UC and BART buildings purple/magenta outright cost their status entirely: 27
    buildings, 2,928 units, including 2200 Bancroft with excavation and foundations underway
    and 2556 Haste at 556 units under construction -- all reading as "agency" and nothing else.
    Fill now carries the stage and the outline carries the agency, so both are legible at once.
    Their status is not in their label (a BART placemark is named "North Berkeley BART: Bridge 1
    (8 st)"), so it comes from v2 by address, same as everything else.
    """
    agency = None
    if "BART" in name:
        agency = "BART Project"
    # address from the description balloon, else from the head of the label. BOTH are needed:
    # 2400 Bowditch South and 2200 Bancroft South carry plain-text descriptions with no
    # <b>ADDRESS</b>, so a description-only lookup drops two UC wings onto their label's status.
    ad = re.search(r"<b>([^<]*)</b><br/>", pm)
    cands = ([ad.group(1)] if ad else []) + [name.split("·")[0]]
    if agency is None:
        for cand in cands:
            if cand.upper().strip() in exempt:
                agency = exempt[cand.upper().strip()]
                break
    # the stage itself
    parts = [p.strip() for p in name.split("·")]
    if len(parts) > 1 and parts[-1] in COLOUR:
        return parts[-1], agency
    for cand in cands:                      # agency buildings carry no stage in their label
        st = STATUS_BY_ADDR.get(cand.upper().strip())
        if st in COLOUR:
            return st, agency
    if name in EXPLICIT:
        e = EXPLICIT[name]
        return (e, agency) if e in COLOUR else (None, agency or e)
    return (None, agency)


def kml_colour(rgb, alpha):
    return f"{alpha:02x}{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}"     # aabbggrr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=GEOM)
    ap.add_argument("--db", default=DB)
    ap.add_argument("--label-scale", type=float, default=3.0)
    ap.add_argument("--fill-alpha", type=int, default=128)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    g = open(a.file, encoding="utf-8", errors="replace").read()

    # classify from the POLYGON twins, then apply to both twins by name
    exempt = agency_exempt(a.db)
    seen = collections.Counter()
    for addr, st in sqlite3.connect(a.db).execute(
            "select address_display, status_label from v_projects_flat where address_display is not null"):
        seen[addr.upper().strip()] += 1
        STATUS_BY_ADDR[addr.upper().strip()] = st
    for k, n in seen.items():
        if n > 1:
            STATUS_BY_ADDR.pop(k, None)     # ambiguous address, do not guess
    status_of, unknown = {}, []
    for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S):
        nm = re.search(r"<name>([^<]*)</name>", pm)
        if not nm or "<Polygon>" not in pm:
            continue
        st, agency = classify(nm.group(1), pm, exempt)
        if st is None and agency is None:
            unknown.append(nm.group(1))
        else:
            status_of.setdefault(nm.group(1), (st, agency))
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
    open(a.file, "w", encoding="utf-8").write(g)
    print(f"\nrestyled {n[0]} polygon and {n[1]} label placemarks")


if __name__ == "__main__":
    main()
