#!/usr/bin/env python3
"""storeys_from_permits.py — storey counts from permit DESCRIPTIONS, for buildings with no 1.E.

The method comes from berkeley-data-07's resolution of 2150 Kittredge: a building permit
description states the construction type and floor count for free -- "(5) floors of Type III-A
over (2) floors + basement Type I" is a 5-over-2 podium, 7 storeys. That resolves buildings which
never had a Tabulation Form, which is most of the pre-Accela and ministerial stock.

THE TRAP, WHICH IS THE SAME TRAP AS EVER. A permit description usually describes the DEMOLITION
before the construction: "Demolish existing 1-story (4-car) garage and construct a new 3-story
duplex". A naive search returns 1 -- the building being torn down. Verified on proj66 2204 Dwight
and proj130 1048 Keith, both of which returned the demolished structure.

So a storey count is only accepted when it sits AFTER a construction verb and is not attached to
a demolition or existing-condition phrase. Where both appear the CONSTRUCTION one wins; where
only a demolition figure exists, nothing is returned.

Output: data/reference/storeys_from_permits.csv   READ-ONLY.
"""
import csv, re, sqlite3, sys

BUILD = r"(?:constructs?|construction|erect|build|new|propos\w*|add\w*)"
DEMO = r"(?:demo\w*|remov\w*|existing|replac\w*|tear|razing?)"
# "3-story", "3 story", "three-story", "(5) floors", "5-over-2"
NUM = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,
       "nine":9,"ten":10,"eleven":11,"twelve":12}
STOREY = re.compile(
    r"(?P<over>\(?(\d+)\)?\s*(?:floors?|stor\w+)\s+over\s+\(?(\d+)\)?\s*(?:floors?|stor\w+))"
    r"|(?P<n>\b(\d{1,2})\s*[-\s]?\s*stor\w+)"
    r"|(?P<w>\b(" + "|".join(NUM) + r")\s*[-\s]?\s*stor\w+)", re.I)


def candidates(text):
    """[(storeys, span_start, snippet)] — every storey figure in the text."""
    out = []
    for m in STOREY.finditer(text):
        if m.group("over"):
            v = int(m.group(2)) + int(m.group(3))          # 5-over-2 podium = 7
        elif m.group("n"):
            v = int(m.group(5))
        else:
            v = NUM[m.group(7).lower()]
        if 1 <= v <= 60:
            out.append((v, m.start(), text[max(0, m.start()-70):m.end()+20]))
    return out


def classify(snippet):
    """Is this figure about what is being BUILT, or what is being REMOVED?"""
    pre = snippet.lower()
    d = re.search(DEMO, pre); b = re.search(BUILD, pre)
    if d and b:
        return "build" if b.start() > d.start() else "demo"
    if d:
        return "demo"
    if b:
        return "build"
    return "unknown"


def main():
    c = sqlite3.connect("databases/berkeley_housing_v2.db"); c.row_factory = sqlite3.Row
    only = {int(x) for x in sys.argv[1:]} if sys.argv[1:] else None
    rows = []
    for p in c.execute("""select project_id,address_display,total_units,status_label
                          from v_projects_flat where address_display is not null"""):
        if only and p["project_id"] not in only:
            continue
        txt = " | ".join([r["description"] for r in c.execute(
            "select description from permits where project_id=? and description is not null",
            (p["project_id"],))] + [r["description"] for r in c.execute(
            "select description from project_versions where project_id=? and description is not null",
            (p["project_id"],))])
        if not txt.strip():
            continue
        cands = candidates(txt)
        if not cands:
            continue
        tagged = [(v, classify(s), s) for v, _i, s in cands]
        build = [t for t in tagged if t[1] == "build"]
        unk = [t for t in tagged if t[1] == "unknown"]
        pick, basis = None, ""
        if build:
            pick = max(t[0] for t in build)                 # the tallest thing being built
            basis = "construction phrase"
        elif unk and not [t for t in tagged if t[1] == "demo"]:
            pick = max(t[0] for t in unk); basis = "unqualified (no demolition nearby)"
        else:
            basis = "ONLY demolition figures — rejected"
        rows.append(dict(project_id=p["project_id"], address=p["address_display"],
                         units=p["total_units"], status=p["status_label"],
                         storeys=pick, basis=basis,
                         all_figures="; ".join(f"{v}({t})" for v, t, _ in tagged),
                         snippet=(build or unk or tagged)[0][2].replace("\n", " ")[:150]))
    with open("data/reference/storeys_from_permits.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["project_id","address","units","status","storeys",
                                           "basis","all_figures","snippet"])
        w.writeheader(); [w.writerow(r) for r in rows]
    got = [r for r in rows if r["storeys"]]
    print(f"scanned {len(rows)} projects with a storey figure · resolved {len(got)}")
    return rows


if __name__ == "__main__":
    main()
