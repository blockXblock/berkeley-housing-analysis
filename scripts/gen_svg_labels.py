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
import argparse, os, pathlib, re, shutil, sqlite3, subprocess, sys, tempfile

DB = "databases/berkeley_housing_v2.db"
# 20% LARGER (John, 2026-09-02). Everything scales together -- canvas, box and type -- so the
# proportions are unchanged and only the rendered pixel count grows. IconStyle scale stays put.
SCALE = 1.20
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
    if r["developer"]:
        l5.append(f"dev {str(r['developer'])[:30]}")
    if r["owner_current"] and str(r["owner_current"]).strip().upper() != str(r["developer"] or "").strip().upper():
        l5.append(f"owner {str(r['owner_current'])[:22]}")
    return l1, " · ".join(l2), " · ".join(l3), " · ".join(l4), " · ".join(l5)


def svg(r):
    l1, l2, l3, l4, l5 = lines_for(r)
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
    for text in (l3, l4, l5):
        if not text:
            continue
        y += int(52 * S); rows.append((y, int(38 * S), 400, "#c2ccd8", text))
    box_h = y + pad
    globals()["BOX_H"] = box_h
    top = (W - box_h) // 2
    body = [f'<rect x="0" y="{top}" width="{W}" height="{box_h}" rx="{int(26*SCALE)}" '
            f'fill="#0d1117" fill-opacity="0.86" stroke="#{accent}" stroke-opacity="0.95" '
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
        # 0.46 measured off a rendered label: "Trachtenberg Architects · filed 2023-12-20" is
        # 42 characters and occupies 837 px at 46 px type. The first guess of 0.52 ellipsised
        # lines with room to spare.
        fits = int((W - x0 * 2) / (size * 0.46))
        if len(text) > fits:
            text = text[:max(fits - 1, 4)].rstrip(" ·") + "\u2026"
        body += line(x0, top + ry, size, weight, fill, text)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}" '
            f'viewBox="0 0 {W} {W}">' + "".join(body) + "</svg>")


def slug(a):
    return re.sub(r"[^a-z0-9]+", "-", str(a).lower()).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uc", action="store_true", help="only uc_project buildings")
    ap.add_argument("--address", action="append", default=[], help="match by address fragment")
    ap.add_argument("--outdir", default="scratch/2026-08-31/svg-labels")
    ap.add_argument("--force", action="store_true", help="re-render even if the PNG exists")
    a = ap.parse_args()
    out = pathlib.Path(a.outdir); out.mkdir(parents=True, exist_ok=True)

    picks = rows(a.uc)
    if a.address:
        picks = [r for r in picks
                 if any(f.upper() in str(r["address_display"]).upper() for f in a.address)]
    if not picks:
        raise SystemExit("nothing matched")

    tmp = pathlib.Path(tempfile.mkdtemp())
    made = 0
    for r in picks:
        s = slug(r["address_display"])
        # CACHE. Rasterising 58 labels through qlmanage takes two minutes, and a rebuild that
        # only changes the tour re-renders every one of them. Skip a PNG that already exists;
        # delete the file (or the directory) to force a re-render after a data change.
        if (out / f"{s}.png").exists() and not a.force:
            made += 1
            continue
        (tmp / f"{s}.svg").write_text(svg(r), encoding="utf-8")
        # qlmanage renders the SVG; alpha survives, and a square canvas needs no crop
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
        made += 1
        print(f"  {out / (s + '.png')}   {' | '.join(x for x in lines_for(r) if x)[:88]}")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n  {made} label image(s) in {out}")


if __name__ == "__main__":
    main()
