#!/usr/bin/env python3
"""gen_kennedy_labels.py — SVG labels for the 23 buildings in the Panoramic/Kennedy tour.

WHY A SEPARATE GENERATOR. gen_svg_labels renders from v_projects_flat, and v2 holds only 8 of
these 23. The rest completed 1990-2018, before the CPRA permit feed v2 is built from begins, so
their figures come from the developer's own published pages -- a SECONDARY source that rule 1 does
not admit into v2. They live in data/reference/kennedy_panoramic_buildings_*.csv instead, with a
source and confidence per row, and this script reads that file rather than hardcoding anything.

THE LABELS ARE NOT INTERCHANGEABLE, AND THEY SAY SO. A building v2 knows gets the standard label,
unmarked, because every figure on it came through a gated write from a primary document. A building
from the CSV gets a final line naming where its numbers came from -- "units per developer", "units
per tour caption". Unmarked, "19 below market" on a 2001 building would claim the same standing as
a unit count taken from a ZAB packet. It does not have it.

  python scripts/gen_kennedy_labels.py            # render all 23
  python scripts/gen_kennedy_labels.py --list     # show what each would say, render nothing
"""
import argparse, csv, glob, os, pathlib, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_svg_labels as G
from gen_building_loop import buildings

TOUR = "kml/tours/panoramic-kennedy-legacy.kml"
CSV_GLOB = "data/reference/kennedy_panoramic_buildings_*.csv"
OUTDIR = pathlib.Path("scratch/2026-09-04/kennedy-labels")
VENV = "scratch/2026-09-04/svgvenv/bin/python"
SRC_LABEL = {"developer_site": "per developer", "tour_caption": "per tour caption",
             "assessor": "per assessor"}


def csv_rows():
    path = sorted(glob.glob(CSV_GLOB))[-1]
    with open(path) as f:
        out = {}
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            # keyed on BOTH: the tour joins on its own string, which is the developer's address
            # for the four the assessor does not hold.
            out[G.normkey(r["address"])] = r
            if r.get("tour_address"):
                out[G.normkey(r["tour_address"])] = r
        return path, out


def blank():
    return {k: None for k in (
        "address_display", "total_units", "status_label", "height_stories", "height_feet",
        "building_sqft", "filed_date", "architect", "developer", "owner_current", "eli_units",
        "vli_units", "li_units", "mod_units", "assessed_value", "est_annual_tax", "uc",
        "project_id")}


def csv_lines(rec):
    """Six lines from a CSV row. The last one is always the provenance."""
    title = f"{rec['tour_name']} ({rec['year']})"
    if rec["use"] != "housing":
        # UC Storage is 800 STORAGE units; 2130 Center is commercial. A unit count here would be
        # a lie of format -- the label's second line means homes everywhere else in the tour.
        what = rec["note"].split("—")[-1].strip() if "—" in rec["note"] else rec["use"]
        body = [what, "not housing", "dev Panoramic Interests"]
    elif rec["units"]:
        body = [f"{int(rec['units']):,} units · Completed",
                f"{int(rec['affordable'])} below market" if rec["affordable"] else "",
                "dev Panoramic Interests"]
    else:
        body = ["units not published", "Proposed", "dev Panoramic Interests"]
    prov = f"units {SRC_LABEL.get(rec['source'], rec['source'])}"
    if rec["use"] != "housing" or not rec["units"]:
        prov = SRC_LABEL.get(rec["source"], rec["source"])
    return ([title] + body + [prov] + [""] * 6)[:6]


def render(lines, slug, outdir):
    d = blank(); d["address_display"] = lines[0]; d["status_label"] = "Completed"; d["uc"] = 0
    orig = G.lines_for
    G.lines_for = lambda _r, _L=lines: _L
    svg, box = G.svg(d), None
    box = G.BOX_H
    G.lines_for = orig
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "a.svg").write_text(svg)
    png = outdir / f"{slug}.png"
    subprocess.run([VENV, "-c", "import sys,cairosvg;cairosvg.svg2png(url=sys.argv[1],"
                    "write_to=sys.argv[2],output_width=int(sys.argv[3]))",
                    str(tmp / "a.svg"), str(png), str(G.W)], capture_output=True)
    subprocess.run(["sips", "-c", str(box), str(G.W), str(png)], capture_output=True)
    return png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print what each label says, render nothing")
    ap.add_argument("--outdir", default=str(OUTDIR))
    a = ap.parse_args()
    out = pathlib.Path(a.outdir); out.mkdir(parents=True, exist_ok=True)

    path, recs = csv_rows()
    v2 = {G.normkey(r["address_display"]): r for r in G.rows(False)}
    sites = buildings(TOUR)
    print(f"  {len(sites)} sites in {TOUR}")
    print(f"  {len(recs)} rows in {os.path.basename(path)}\n")

    n_v2 = n_csv = n_miss = 0
    for key in sorted(sites):
        k = G.normkey(key)
        slug = G.slug(key)
        if k in v2:
            r = v2[k]
            lines = [x for x in G.lines_for(r) if x]
            tag = f"v2 proj{r['project_id']}"
            n_v2 += 1
            if not a.list:
                render(([*lines] + [""] * 6)[:6], slug, out)
        elif k in recs:
            lines = [x for x in csv_lines(recs[k]) if x]
            tag = f"csv {recs[k]['source']}"
            n_csv += 1
            if not a.list:
                render(([*lines] + [""] * 6)[:6], slug, out)
        else:
            tag = "NO SOURCE"; lines = []
            n_miss += 1
        print(f"  {key[:30]:30} {tag:20} {' | '.join(lines)[:78]}")
    print(f"\n  {n_v2} from v2 (unmarked) · {n_csv} from the CSV (marked) · {n_miss} unsourced")
    if not a.list:
        print(f"  labels in {out}")


if __name__ == "__main__":
    main()
