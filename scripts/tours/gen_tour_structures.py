#!/usr/bin/env python3
"""gen_tour_structures.py — the canonical list of structures that appear in the flyover tours.

DERIVED, never hand-maintained: the tour geometry (kml/geometry/geometry.kml) is the hand-edited
canonical, so IT defines the set, not a list someone typed. Re-run whenever geometry.kml changes.

A structure is "in the tours" if its address appears as a <b>...</b> header inside a geometry.kml
placemark description AND resolves to ONE v4 project (re-pointed from v2 2026-10-02; the key column
is now v4's project_key). The remainder are UC sub-buildings (North/South towers of one project),
addresses v4 holds several projects at, and placemarks with no v4 project.

`has_tabulation` = an architect Tabulation Form (1.E) is FETCHED TO R2 for that project, i.e. we
hold a STATED building footprint. That is the only source that describes the building which WILL
exist -- taxable sqft, aerial/Overture footprints and existing-condition site plans all describe
the building being demolished (verified three-for-three, 2026-08-23).

Output: data/reference/tour_structures_171.csv (or --out)    READ-ONLY on all sources.
"""
import argparse, csv, re
from collections import Counter

from scripts.tours import v4_source as V

KML = "kml/geometry/geometry.kml"
OUT = "data/reference/tour_structures_171.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geom", default=KML)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    addrs = {m.group(1).upper().strip()
             for m in re.finditer(r"<b>([^<]*)</b><br/>", open(a.geom).read())}
    # v4 (2026-10-02): a geometry address resolves to ONE v4 project through v4_source (the address
    # canon + two declared tie-breaks); an ambiguous address is listed, never guessed.
    idx = V.by_address()
    hastab = V.tabulation_projects()
    hasplan = V.projects_with_document("plan_set")
    rows, seen, amb = [], set(), []
    for ad in sorted(addrs):
        r = V.lookup(ad, idx)
        if r is None:
            if V.akey(ad) in idx[1]:
                amb.append(ad)
            continue
        if r["project_key"] not in seen:
            seen.add(r["project_key"]); rows.append(r)
    count = lambda r: (r["beds"] if r["uc"] else r["units"]) or 0
    rows.sort(key=lambda r: -count(r))

    def priority(r):
        # UC projects self-permit: UC Regents approve and UC issues its own building permit, so
        # there is no Accela ZP record to harvest -- these must come from UC, not the City.
        # CLAUDE.md: filter on the CLASSIFICATION, never a hardcoded id.
        # The 0-2u tail is the ministerial ADU/infill cohort: no discretionary Planning
        # entitlement, so no Form 1.E was ever filed. Not worth harvesting.
        u = count(r)
        return ("done" if r["project_key"] in hastab else
                "uc-harvest-from-uc" if r["uc"] else
                "skip-ministerial-adu" if u <= 2 else
                "high" if u >= 45 else "medium")
    with open(a.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["project_key", "address", "units", "status", "height_stories",
                    "has_tabulation", "has_plan_set", "is_uc", "harvest_priority"])
        for r in rows:
            w.writerow([r["project_key"], r["address_display"], count(r), r["stage"], r["height_stories"],
                        int(r["project_key"] in hastab), int(r["project_key"] in hasplan),
                        int(r["uc"]), priority(r)])
    print(f"wrote {a.out}: {len(rows)} structures from {len(addrs)} geometry addresses"
          f" ({len(amb)} ambiguous in v4, skipped: {', '.join(amb)})")
    for k, v in Counter(priority(r) for r in rows).most_common():
        print(f"   {k:24} {v}")


if __name__ == "__main__":
    main()
