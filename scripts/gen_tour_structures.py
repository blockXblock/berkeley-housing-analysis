#!/usr/bin/env python3
"""gen_tour_structures.py — the canonical list of structures that appear in the flyover tours.

DERIVED, never hand-maintained: the tour geometry (kml/geometry/geometry.kml) is the hand-edited
canonical, so IT defines the set, not a list someone typed. Re-run whenever geometry.kml changes.

A structure is "in the tours" if its address appears as a <b>...</b> header inside a geometry.kml
placemark description AND resolves to a v2 project. 184 placemarks -> 171 projects; the remainder
are UC sub-buildings (North/South towers of one project) and un-merged duplicates.

`has_tabulation` = an architect Tabulation Form (1.E) is FETCHED TO R2 for that project, i.e. we
hold a STATED building footprint. That is the only source that describes the building which WILL
exist -- taxable sqft, aerial/Overture footprints and existing-condition site plans all describe
the building being demolished (verified three-for-three, 2026-08-23).

Output: data/reference/tour_structures_171.csv    READ-ONLY on all sources.
"""
import csv, re, sqlite3

KML = "kml/geometry/geometry.kml"
OUT = "data/reference/tour_structures_171.csv"
TAB = "(title like '%1.E%' or lower(title) like '%tabulation%')"


def main():
    addrs = {m.group(1).upper().strip()
             for m in re.finditer(r"<b>([^<]*)</b><br/>", open(KML).read())}
    c = sqlite3.connect("databases/berkeley_housing_v2.db"); c.row_factory = sqlite3.Row
    hastab = {r[0] for r in c.execute(
        f"select distinct project_id from documents where {TAB} and r2_url is not null")}
    hasplan = {r[0] for r in c.execute(
        "select distinct d.project_id from documents d "
        "left join vocabulary_document_types v on v.id=d.document_type_id "
        "where v.code='plan_set' and d.r2_url is not null")}
    rows = [dict(r) for r in c.execute(
        "select project_id,address_display,total_units,status_label,height_stories from v_projects_flat")
        if (r["address_display"] or "").upper().strip() in addrs]
    rows.sort(key=lambda r: -(r["total_units"] or 0))
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["project_id", "address", "units", "status", "height_stories",
                    "has_tabulation", "has_plan_set", "harvest_priority"])
        for r in rows:
            u = r["total_units"] or 0
            # the 0-2u tail is the ministerial ADU/infill cohort: post-2017 state ADU law means no
            # discretionary Planning entitlement, so no Form 1.E was ever filed. Not worth harvesting.
            pri = ("done" if r["project_id"] in hastab else
                   "skip-ministerial-adu" if u <= 2 else
                   "high" if u >= 45 else "medium")
            w.writerow([r["project_id"], r["address_display"], u, r["status_label"],
                        r["height_stories"], int(r["project_id"] in hastab),
                        int(r["project_id"] in hasplan), pri])
    print(f"wrote {OUT}: {len(rows)} structures")
    from collections import Counter
    for k, v in Counter(
        ("done" if r["project_id"] in hastab else
         "skip-ministerial-adu" if (r["total_units"] or 0) <= 2 else
         "high" if (r["total_units"] or 0) >= 45 else "medium") for r in rows).most_common():
        print(f"   {k:24} {v}")


if __name__ == "__main__":
    main()
