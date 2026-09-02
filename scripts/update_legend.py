#!/usr/bin/env python3
"""update_legend.py — regenerate the homepage colour legend FROM the geometry census.

WHY IT IS GENERATED AND NOT WRITTEN. The legend this replaces was hand-written, drifted, and
ended up false for about a third of the map -- it called yellow "building permit issued" when
yellow was overwhelmingly In Review. The restyle fixed the colours; this stops the TEXT drifting
away from them again. Same discipline as everywhere else today: derive, never hardcode.

IT LISTS ONLY WHAT IS ON THE MAP. Statuses move. Pre-Application emptied when 2344 Fulton went
to In Review, and Stalled emptied when 2317 Channing was entitled -- so grey and red now describe
nothing, and naming them would send a viewer hunting for a colour that is not there. Equally,
if a project goes Stalled next week the colour returns to the legend on the next run without
anyone remembering to add it.

  python scripts/update_legend.py --dry-run
  python scripts/update_legend.py
"""
import argparse, collections, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "viz"))
import stage_legend_svg

GEOM = "kml/geometry/geometry.kml"
PAGE = "docs/index.html"
SVG_DIR = "docs/svg"
MARK = "Colour shows where each project stands"


# display colour (readable on white) and the phrase, in pipeline order
GLOSS = [
    ("Pre-Application",    "#7a7a7a", "yellow" and "grey",  "at pre-application"),
    ("In Review",          "#b8860b", "yellow",             "under review"),
    ("Entitled",           "#ff8000", "orange",             "entitled (approved, no building permit yet)"),
    ("Permitted",          "#00b8cc", "cyan",               "permitted, not yet started"),
    ("Under Construction", "#2962ff", "blue",               "under construction"),
    ("Completed",          "#00a844", "green",              "completed and occupiable"),
    ("Stalled",            "#ff0000", "red",                "stalled"),
    ("Withdrawn",          "#b0003a", "dark red",           "withdrawn"),
    ("UC Project",         "#aa00ff", "purple",             "UC Berkeley"),
    ("BART Project",       "#ff00ff", "magenta",            "BART joint development"),
]


UNSLUG = {}


def census(path):
    """(stage counts from the FILL, agency counts from the OUTLINE).

    Since 2026-08-28 a style id is style_status_<Stage>[__<Agency>], because fill carries the
    stage and outline carries the agency. Counting the whole id as one bucket would put every UC
    and BART building back into an agency-only category the map no longer has.
    """
    g = open(path, encoding="utf-8", errors="replace").read()
    stage, agency = collections.Counter(), collections.Counter()
    for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S):
        if "<Polygon>" not in pm:
            continue
        su = re.search(r"<styleUrl>#style_status_([^<]+)</styleUrl>", pm)
        if not su:
            continue
        head, _, tail = su.group(1).replace("_nolabel", "").partition("__")
        # slug back to the GLOSS spelling: the id turns "Pre-Application" into
        # "Pre_Application", so a plain underscore->space swap yields "Pre Application" and
        # silently drops grey from the legend while seven buildings are wearing it.
        stage[UNSLUG.get(head, head.replace("_", " "))] += 1
        if tail:
            agency[UNSLUG.get(tail, tail.replace("_", " "))] += 1
    return stage, agency



def sentence(stage, agency):
    """Stage clause from the fills; a second clause for the outlines, only if any exist."""
    stages = [f'<span style="color:{h}">{w}</span> {p}'
              for st, h, w, p in GLOSS if not st.endswith("Project") and stage.get(st)]
    s = (f" <b>Colour shows where each project stands:</b> {' &middot; '.join(stages)}."
         " Warm colours are paper stages, cool colours are physical ones.")
    ag = [f'<span style="color:{h}">{w}</span> for {p}'
          for st, h, w, p in GLOSS if st.endswith("Project") and agency.get(st)]
    if ag:
        s += (" A thick outline marks a project permitted by its own agency rather than by the"
              f" City &mdash; {' and '.join(ag)}; the fill still shows the stage.")
    return s


def _build_unslug():
    for st, *_ in GLOSS:
        UNSLUG[re.sub(r"[^A-Za-z0-9]+", "_", st).strip("_")] = st


def main():
    _build_unslug()
    ap = argparse.ArgumentParser()
    ap.add_argument("--geometry", default=GEOM)
    ap.add_argument("--page", default=PAGE)
    ap.add_argument("--tail", default=None,
                    help="closing sentence appended AFTER the legend on every video. Defaults to "
                         "the site pointer; pass '' to omit.")
    ap.add_argument("--svg-dir", default=SVG_DIR,
                    help="where the two legend SVGs are written; pass '' to skip them.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    stage, agency = census(a.geometry)
    print("stage (fill):")
    for st, *_ in GLOSS:
        if not st.endswith("Project"):
            print(f"  {st:<20} {stage.get(st,0):>3}{'   (absent — omitted)' if not stage.get(st) else ''}")
    print("agency (outline):")
    for st, *_ in GLOSS:
        if st.endswith("Project"):
            print(f"  {st:<20} {agency.get(st,0):>3}{'   (absent — omitted)' if not agency.get(st) else ''}")
    TAIL = (" Elsewhere on BerkeleyBuild.com: the architects\u2019 own plan sets and the "
            "affordability tabulations filed with them, and for every project in the pipeline the "
            "full permit timeline \u2014 when it was filed, when it was approved, when the building "
            "permit issued, and when it was finished.")
    new = sentence(stage, agency) + (TAIL if a.tail is None else a.tail)
    print("\nlegend:\n ", re.sub(r"<[^>]+>", "", new).strip())
    if a.dry_run:
        return
    if a.svg_dir:
        # Count ONLY what the picture explains. Two Bakar Innovation Zone polygons carry an
        # AGENCY fill with no stage (a leftover of the pre-2026-08-28 styling, when the fill
        # carried the agency), so the map holds more polygons than the legend has meanings.
        # Folding them into the headline would make the number quietly disagree with the chips.
        shown = {g[0] for g in GLOSS if not g[0].endswith("Project")}
        total = sum(v for k, v in stage.items() if k in shown)
        skipped = sum(v for k, v in stage.items() if k not in shown)
        if skipped:
            print(f"  note: {skipped} polygon(s) carry an agency fill with no stage — "
                  f"excluded from the legend total")
        label = f"{total} buildings on the flyovers"
        os.makedirs(a.svg_dir, exist_ok=True)
        for fname, fn in (("stage_legend.svg", stage_legend_svg.wide),
                          ("stage_legend_narrow.svg", stage_legend_svg.narrow)):
            out = os.path.join(a.svg_dir, fname)
            open(out, "w", encoding="utf-8").write(fn(GLOSS, stage, agency, label))
            print(f"wrote {out}  ({os.path.getsize(out):,} bytes)")

    h = open(a.page, encoding="utf-8").read()
    n = 0
    def swap(m):
        """Rewrite the legend on any block that is a VIDEO block, whether or not it has one.

        This used to bail out when the marker was absent, so it could only ever UPDATE an
        existing legend -- a newly published video got none at all, and the Bancroft flyover
        went live without one. The guard is now "is this a video block", tested by looking for
        a YouTube embed just after it, rather than "does it already say what I am about to say".
        """
        nonlocal n
        body = m.group(2)
        tail_of_page = h[m.end():m.end() + 900]
        if "youtube.com/embed" not in tail_of_page:
            return m.group(0)
        n += 1
        head = body[:body.index(" <b>Colour shows")] if " <b>Colour shows" in body else body
        return m.group(1) + head.rstrip() + new + m.group(3)
    h = re.sub(r"(<h3>.*?</h3>\s*<p>)(.*?)(</p>)", swap, h, flags=re.S)
    open(a.page, "w", encoding="utf-8").write(h)
    print(f"\nrewrote the legend in {n} video description(s)")


if __name__ == "__main__":
    main()
