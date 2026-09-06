#!/usr/bin/env python3
"""gen_svg_labels.py — render building labels as boxed images, because KML cannot fold text.

WHY. Google Earth ignores a newline inside <name>: a label is always ONE line, however long.
That caps how much a label can say -- "2200 Bancroft Way · 1625 beds · Under Construction" is
already 54 characters and there is no room for height, architect or floor area without it
becoming a banner across the sky. John, 2026-08-31: "their boxed appearance is tidy, and the
content could add more details about a structure that otherwise makes kml labels too long,
since they do not implement folded lines."

So the label becomes a PICTURE of text: an SVG we generate, rasterised to PNG and used as the
placemark's icon with LabelStyle scale 0 so Earth draws no text of its own. Four lines fit
comfortably where one line used to run off the screen.

NO IMAGE LIBRARY IS REQUIRED. SVG is XML we write directly, and macOS rasterises it with
qlmanage, which preserves alpha. Nothing is installed. The canvas is SQUARE because qlmanage
emits a square thumbnail -- authoring square means no cropping step and no white edges.

DATES ARE PRINTED TO THEIR RECORDED PRECISION. v2 marks 55% of filed_dates
event_date_precision='year' and renders them 1 January; a label saying "filed 1 Jan 2024" would
be inventing a day the city never recorded, so a year-precision date prints as the year alone.

  python scripts/gen_svg_labels.py --uc --outdir scratch/2026-08-31/svg-labels
"""
import argparse, hashlib, os, pathlib, re, shutil, sqlite3, subprocess, sys, tempfile

DB = "databases/berkeley_housing_v2.db"
# LARGER AGAIN (John, 2026-09-04: "the labels are still hard to read"). Everything scales
# together -- canvas, box and type -- so the proportions are unchanged and only the rendered
# pixel count grows. IconStyle scale stays put, and Earth draws the icon from its native pixel
# size, so a bigger render is both SHARPER (no upscaling blur) and physically larger on screen.
# 1.20 -> 1.60 is a third again on both counts.
SCALE = 1.60
# OPAQUE, AND RENDERED FAITHFULLY. Tested against real frames from the Shattuck recording
# (2026-09-04): at 0.86 the panel picks up whatever is behind it -- over a sunlit building you can
# read the street labels and rooflines THROUGH the text, which is the same illegibility the glyph
# outlines were added to fight, arriving from the other side. Over sky it was fine; over buildings
# it was not, so 1.0 it is.
#
# The renderer had to change with it. qlmanage is macOS Quick Look and FLATTENS alpha against a
# light background: it rendered the old 0.86 panel as a washed (47,51,56) grey rather than
# #0d1117. Every label in every video shipped before today is that grey. cairosvg at 1.0 gives
# the true (13,17,23) -- same opacity John approved, materially more contrast under white text,
# and faster (0.31 s/label against 0.53 s).
PANEL_OPACITY = 1.0
W = int(900 * SCALE)        # square canvas; the box is centred in it
BOX_H = int(300 * SCALE)
STATUS_RGB = {"Pre-Application": "9e9e9e", "In Review": "ffd400", "Entitled": "ff8000",
              "Permitted": "00e5ff", "Under Construction": "2962ff", "Completed": "00c853",
              "Stalled": "ff0000", "Withdrawn": "b0003a"}


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def rows(uc_only):
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    q = """SELECT f.*, (SELECT 1 FROM project_classifications pc
             JOIN vocabulary_classification_types v ON v.id=pc.classification_type_id
             WHERE pc.project_id=f.project_id AND v.code='uc_project') uc
           FROM v_projects_flat f JOIN projects p ON p.id=f.project_id
           WHERE p.merged_into_id IS NULL"""
    out = [r for r in c.execute(q)]
    return [r for r in out if r["uc"]] if uc_only else out


def lines_for(r):
    """Address, then up to three lines of detail. Order is what a reader wants first."""
    noun = "beds" if r["uc"] else "units"
    l1 = re.sub(r"\s+(St|Ave|Way|Dr|Blvd)$", lambda m: " " + m.group(1), str(r["address_display"]).title())
    l2 = []
    if r["total_units"]:
        l2.append(f"{r['total_units']:,} {noun}")
    l2.append(str(r["status_label"]))
    l3 = []
    if r["height_stories"]:
        l3.append(f"{int(r['height_stories'])} storeys")
    if r["height_feet"]:
        l3.append(f"{int(r['height_feet'])} ft")
    if r["building_sqft"]:
        l3.append(f"{int(r['building_sqft']):,} sq ft")
    # WHO BUILT IT (John, 2026-09-02: "add the architect name or developer or owner or all
    # three, if it fits"). Coverage is partial -- architect 11/21, developer 11/21, owner 8/21
    # on the over-200-unit set -- so each line carries whichever of them exist, labelled, and a
    # project with none simply has fewer lines. Owner strings are raw assessor names and can be
    # long, so they are trimmed rather than allowed to run off the box.
    l4, l5 = [], []
    if r["architect"]:
        l4.append(str(r["architect"])[:38])
    for col, word in (("co_issued_date", "completed"), ("bp_issued_date", "permitted"),
                      ("filed_date", "filed")):
        d = r[col]
        if d:
            # a year-precision date is printed as a YEAR -- see the module docstring
            l4.append(f"{word} {d[:4]}" if d.endswith("-01-01") else f"{word} {d}")
            break
    # A LINE EACH. Sharing one line, "dev NX Ventures · owner 1974 SHATTUCK AVENUE LLC" ran to
    # the ellipsis and the owner -- the part only we have -- was the half that got cut. The box
    # grows by one line instead, which costs nothing since it is sized to its content.
    l6 = []
    if r["developer"]:
        l5.append(f"dev {str(r['developer'])[:34]}")
    if r["owner_current"] and str(r["owner_current"]).strip().upper() != str(r["developer"] or "").strip().upper():
        l6.append(f"owner {str(r['owner_current'])[:40]}")
    return l1, " · ".join(l2), " · ".join(l3), " · ".join(l4), " · ".join(l5), " · ".join(l6)


def svg(r):
    l1, l2, l3, l4, l5, l6 = lines_for(r)
    accent = STATUS_RGB.get(str(r["status_label"]), "ffffff")
    # SIZE THE BOX TO ITS CONTENT. A fixed height either clips a project with a full team or
    # leaves a slab of empty panel under one with none.
    # MEASURE, THEN SIZE. A formula guessing the height left 8 px under the last baseline and
    # clipped the descenders of the team line. Lay the lines out first, then make the box fit
    # what is actually there.
    S = SCALE
    pad, x0 = int(34 * S), int(44 * S)
    rows, y = [], pad + int(52 * S)
    rows.append((y, int(62 * S), 700, "#ffffff", l1))
    y += int(60 * S); rows.append((y, int(46 * S), 600, f"#{accent}", l2))
    for text in (l3, l4, l5, l6):
        if not text:
            continue
        y += int(52 * S); rows.append((y, int(38 * S), 400, "#c2ccd8", text))
    box_h = y + pad
    globals()["BOX_H"] = box_h
    top = (W - box_h) // 2
    body = [f'<rect x="0" y="{top}" width="{W}" height="{box_h}" rx="{int(26*SCALE)}" '
            f'fill="#0d1117" fill-opacity="{PANEL_OPACITY}" stroke="#{accent}" stroke-opacity="0.95" '
            f'stroke-width="{int(6*SCALE)}"/>',
            f'<rect x="0" y="{top}" width="{int(14*SCALE)}" height="{box_h}" '
            f'rx="{int(7*SCALE)}" fill="#{accent}"/>']
    def line(x, y, size, weight, fill, text, outline=True):
        """Text with a thin dark stroke UNDER the fill.

        John, 2026-09-02: "try making the font sharper, more legible, perhaps by adding a thin
        outline to each character". Painting a stroked copy first and the solid fill over it
        keeps the letterforms their true weight -- stroking the visible glyph instead would fatten
        it and blur small type. The stroke gives every character its own edge, so the address
        stays readable where the box crosses a bright roof or pale sky rather than the dark
        panel it was designed against.
        """
        f = (f'font-family="Helvetica,Arial,sans-serif" font-size="{size}" '
             f'font-weight="{weight}"')
        out = []
        if outline:
            out.append(f'<text x="{x}" y="{y}" {f} fill="none" stroke="#05080d" '
                       f'stroke-width="{max(size*0.09,2.5):.1f}" stroke-opacity="0.85" '
                       f'stroke-linejoin="round">{esc(text)}</text>')
        out.append(f'<text x="{x}" y="{y}" {f} fill="{fill}">{esc(text)}</text>')
        return out

    for ry, size, weight, fill, text in rows:
        # Helvetica averages a bit over half its point size per character; trim to what the box
        # can actually hold so a long owner string cannot run off the right edge.
        # WIDTH PER CHARACTER, NOT PER STRING. A flat 0.46 em is right for mixed-case text and
        # badly wrong for the assessor's owner names, which are ALL CAPITALS and about a third
        # wider -- "owner 1974 SHATTUCK AVENUE LLC" measured under the limit and still ran off
        # the box. Capitals and digits are counted at 0.60 em, lowercase at 0.46, spaces and
        # punctuation at 0.30.
        def width(t):
            return sum(0.60 if c.isupper() or c.isdigit() else
                       0.30 if c in " ·.,-" else 0.46 for c in t) * size
        avail = W - x0 * 2
        if width(text) > avail:
            while len(text) > 4 and width(text + "\u2026") > avail:
                text = text[:-1]
            text = text.rstrip(" ·") + "\u2026"
        body += line(x0, top + ry, size, weight, fill, text)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}" '
            f'viewBox="0 0 {W} {W}">' + "".join(body) + "</svg>")


def normkey(a):
    """A slug-insensitive address key, for matching GEOMETRY names to v2 addresses.

    Lives here, not in svg_label_tour, because BOTH need it and a second copy is how the two
    drift apart. The tour matches rendered PNGs by this key; this module matches --address
    requests by it. Without the second half, a target named from the geometry never renders at
    all: "2099 MLK Jr Way" is not a substring of v2's "2099 M L KING JR Way", so the label was
    simply never made and the building went through the flight unlabelled.

    Normalises three ways the SAME address is written differently between the geometry file and
    v2, each of which silently dropped a real building until it was found the hard way:
      - MLK, spelled four ways (found via 2099 MLK on Shattuck).
      - a STREET-TYPE SUFFIX present on one side and not the other: the geometry says
        "2820 SAN PABLO AVE" and v2 "2820 San Pablo", so a 110-unit and a 1-unit building on
        San Pablo shipped as broken icons (2026-09-06). Strip a trailing Ave/St/Way/Blvd/etc.
      - a HOUSE-NUMBER RANGE: the geometry says "1701- 1717 San Pablo", v2 "1701 San Pablo Ave".
        Collapse "1701-1717" to its first number.
    """
    k = str(a).upper()
    k = re.sub(r"\b(\d+)\s*-\s*\d+\b", r"\1", k)          # 1701-1717 -> 1701 (house-number range)
    k = re.sub(r"[^A-Z0-9]", "", k)
    for alias in ("MARTINLUTHERKING", "MLKING"):
        k = k.replace(alias, "MLK")
    k = re.sub(r"(AVENUE|AVE|STREET|ST|BOULEVARD|BLVD|WAY|DRIVE|DR|PLACE|PL|COURT|CT|ROAD|RD|LANE|LN|TERRACE|TER|CIRCLE|CIR)$", "", k)
    return k


def slug(a):
    return re.sub(r"[^a-z0-9]+", "-", str(a).lower()).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uc", action="store_true", help="only uc_project buildings")
    ap.add_argument("--address", action="append", default=[], help="match by address fragment")
    ap.add_argument("--outdir", default="scratch/2026-08-31/svg-labels")
    ap.add_argument("--force", action="store_true", help="re-render even if the PNG exists")
    ap.add_argument("--raster", choices=("qlmanage", "cairosvg", "auto"), default="auto",
                    help="auto prefers cairosvg (faithful) and falls back to qlmanage (flattens "
                         "alpha) when it is not installed, so a machine without the venv still "
                         "builds -- with a warning, because the output differs.")
    ap.add_argument("--venv", default="scratch/2026-09-04/svgvenv/bin/python",
                    help="python that has cairosvg (PEP 668 blocks a system install)")
    ap.add_argument("--panel-opacity", type=float, default=None,
                    help="override the panel fill-opacity, e.g. 1.0 for a fully opaque box")
    a = ap.parse_args()
    if a.panel_opacity is not None:
        globals()["PANEL_OPACITY"] = a.panel_opacity
    raster, venv = a.raster, a.venv
    if raster in ("auto", "cairosvg"):
        ok = subprocess.run([venv, "-c", "import cairosvg"], capture_output=True).returncode == 0
        if ok:
            raster = "cairosvg"
        elif raster == "cairosvg":
            raise SystemExit(f"cairosvg not importable from {venv}")
        else:
            raster = "qlmanage"
            print("  WARNING: cairosvg not found; falling back to qlmanage, which FLATTENS "
                  "alpha and renders the panel a lighter grey than designed.")
    print(f"  rasteriser: {raster}   panel opacity: {PANEL_OPACITY}")
    out = pathlib.Path(a.outdir); out.mkdir(parents=True, exist_ok=True)

    picks = rows(a.uc)
    if a.address:
        want_norm = {normkey(f) for f in a.address}
        picks = [r for r in picks
                 if any(f.upper() in str(r["address_display"]).upper() for f in a.address)
                 or normkey(r["address_display"]) in want_norm]
    if not picks:
        raise SystemExit("nothing matched")

    tmp = pathlib.Path(tempfile.mkdtemp())
    made = 0
    for r in picks:
        s = slug(r["address_display"])
        # CACHE, KEYED ON CONTENT (not on the filename). Rasterising 58 labels through qlmanage
        # takes two minutes, so a rebuild that only changes the tour must not re-render them all.
        # But the original test was "does <slug>.png exist" -- a filename the DATA never touches,
        # so a corrected unit count or storey height left the old PNG in place forever and the
        # tour silently kept showing the superseded figure. 2128 Oxford went to press at 485
        # units / 26 storeys, rendered at 11:19, an hour and a half before the write that made it
        # 456 / 27. Hashing the SVG makes the cache self-invalidating: the label re-renders when
        # and only when something it DISPLAYS has changed.
        body = svg(r)
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
        stamp = out / f"{s}.sha"
        if ((out / f"{s}.png").exists() and stamp.exists()
                and stamp.read_text().strip() == digest and not a.force):
            made += 1
            continue
        (tmp / f"{s}.svg").write_text(body, encoding="utf-8")
        # qlmanage renders the SVG; alpha survives, and a square canvas needs no crop
        if raster == "cairosvg":
            png = tmp / f"{s}.svg.png"
            subprocess.run([venv, "-c",
                            "import sys,cairosvg;cairosvg.svg2png(url=sys.argv[1],"
                            "write_to=sys.argv[2],output_width=int(sys.argv[3]))",
                            str(tmp / f"{s}.svg"), str(png), str(W)], capture_output=True)
        else:
            subprocess.run(["qlmanage", "-t", "-s", str(W), "-o", str(tmp), str(tmp / f"{s}.svg")],
                           capture_output=True)
        png = tmp / f"{s}.svg.png"
        if not png.exists():
            print(f"  FAILED to rasterise {s}")
            continue
        # CROP THE PADDING. qlmanage emits a square, so a 300 px box inside a 900 px canvas is
        # two-thirds transparent -- and IconStyle scale sizes the whole image, so two-thirds of
        # the scale was being spent on nothing. That is why the label read as too small at a
        # size that had looked too large before. The box is centred by construction, so a
        # centred crop to the box height lands exactly on it.
        shutil.copy(png, out / f"{s}.png")
        subprocess.run(["sips", "-c", str(BOX_H), str(W), str(out / f"{s}.png")],
                       capture_output=True)
        # Stamp LAST, so an interrupted or failed render leaves no stamp and re-renders next run.
        stamp.write_text(digest)
        made += 1
        print(f"  {out / (s + '.png')}   {' | '.join(x for x in lines_for(r) if x)[:88]}")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n  {made} label image(s) in {out}")


if __name__ == "__main__":
    main()
