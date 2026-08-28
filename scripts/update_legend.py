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
import argparse, collections, re

GEOM = "kml/geometry/geometry.kml"
PAGE = "docs/index.html"
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


def census(path):
    g = open(path, encoding="utf-8", errors="replace").read()
    c = collections.Counter()
    for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S):
        if "<Polygon>" not in pm:
            continue
        su = re.search(r"<styleUrl>#style_status_([^<]+)</styleUrl>", pm)
        if su:
            c[su.group(1).replace("_nolabel", "").replace("_", " ")] += 1
    return c


def sentence(c):
    parts = []
    for status, hexc, word, phrase in GLOSS:
        if not c.get(status.replace("-", "-")) and not c.get(status):
            continue
        parts.append(f'<span style="color:{hexc}">{word}</span> {phrase}')
    agency = [p for p in parts if "UC Berkeley" in p or "BART" in p]
    stages = [p for p in parts if p not in agency]
    s = f" <b>Colour shows where each project stands:</b> {' &middot; '.join(stages)}"
    if agency:
        # an em-dash, not a full stop: the agency clause opens with a <span>, so a sentence
        # break would leave a lowercase colour word starting a sentence
        s += (f" &mdash; {' and '.join(agency)} are permitted by their own agency rather than the City")
    return s + ". Warm colours are paper stages, cool colours are physical ones."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geometry", default=GEOM)
    ap.add_argument("--page", default=PAGE)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    c = census(a.geometry)
    print("census on the map:")
    for status, *_ in GLOSS:
        print(f"  {status:<20} {c.get(status,0):>3}{'   (absent — omitted from the legend)' if not c.get(status) else ''}")
    new = sentence(c)
    print("\nlegend:\n ", re.sub(r"<[^>]+>", "", new).strip())
    if a.dry_run:
        return
    h = open(a.page, encoding="utf-8").read()
    n = 0
    def swap(m):
        nonlocal n
        body = m.group(2)
        if MARK not in body:
            return m.group(0)
        n += 1
        head = body[:body.index(" <b>Colour shows")] if " <b>Colour shows" in body else body.split(MARK)[0]
        return m.group(1) + head.rstrip() + new + m.group(3)
    h = re.sub(r"(<h3>.*?</h3>\s*<p>)(.*?)(</p>)", swap, h, flags=re.S)
    open(a.page, "w", encoding="utf-8").write(h)
    print(f"\nrewrote the legend in {n} video description(s)")


if __name__ == "__main__":
    main()
