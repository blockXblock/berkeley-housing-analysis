#!/usr/bin/env python3
"""sync_status_from_v2.py — carry v2's status_label into geometry.kml's labels.

WHY IT MATTERS MORE THAN IT USED TO. Since the 2026-08-27 restyle, a building's COLOUR is
derived from the status written in its own label (restyle_by_status.py), and the homepage
carries a legend describing that mapping. So a stale label is now a visibly wrong map and a
false legend, not just a stale string. When berkeley-data-60 reconciles a status in v2, this is
the step that makes the skyline agree.

MATCHES ON THE ADDRESS IN THE DESCRIPTION, not on the label text -- the label is the thing being
corrected, so it cannot also be the key. Only addresses that resolve to EXACTLY ONE v2 project
are touched: 2400 Bowditch, 2200 Bancroft and 2556 Haste each appear twice (North/South wings
of one project) and the BART buildings have no v2 address at all.

UPDATES BOTH TWINS. split_label_lod.py gives every building a polygon placemark and a label
placemark, and the name appears in both; changing one would leave the map disagreeing with
itself.

  python scripts/sync_status_from_v2.py --dry-run
  python scripts/sync_status_from_v2.py
"""
import argparse, re, sqlite3, collections

GEOM = "kml/geometry/geometry.kml"
DB = "databases/berkeley_housing_v2.db"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=GEOM)
    ap.add_argument("--db", default=DB)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    g = open(a.file, encoding="utf-8", errors="replace").read()

    rows = collections.defaultdict(list)
    for addr, units, status in sqlite3.connect(a.db).execute(
            "select address_display, total_units, status_label from v_projects_flat "
            "where address_display is not null"):
        rows[addr.upper().strip()].append((units, status))
    v2 = {k: v[0] for k, v in rows.items() if len(v) == 1}

    # address -> what the label currently claims, taken from the POLYGON twin
    changes = {}
    for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S):
        if "<Polygon>" not in pm:
            continue
        ad = re.search(r"<b>([^<]*)</b><br/>", pm)
        nm = re.search(r"<name>([^<]*)</name>", pm)
        if not (ad and nm):
            continue
        key = ad.group(1).upper().strip()
        if key not in v2:
            continue
        units, status = v2[key]
        parts = [p.strip() for p in nm.group(1).split("·")]
        if len(parts) < 2 or parts[-1] == status:
            continue
        parts[-1] = status
        changes[nm.group(1)] = (" · ".join(parts), status, parts[-1])

    if not changes:
        print("no status labels are out of step with v2")
        return
    print(f"{len(changes)} label(s) differ from v2:\n")
    for old, (new, status, _) in changes.items():
        print(f"  {old}\n    -> {new}")
    if a.dry_run:
        return

    n = 0
    for old, (new, status, _) in changes.items():
        # BOTH twins carry the name
        n += g.count(f"<name>{old}</name>")
        g = g.replace(f"<name>{old}</name>", f"<name>{new}</name>")
        # and the description balloon states the status separately
        g = re.sub(r"(<b>Status:</b>\s*)([^<]*)(<br/>|\]\]>)",
                   lambda m, s=status, o=old: (m.group(1) + s + m.group(3))
                   if f"<name>{new}</name>" in g else m.group(0), g)
    # rewrite the Status line inside each changed building's own description, scoped per placemark
    def fix_desc(m):
        pm = m.group(0)
        nm = re.search(r"<name>([^<]*)</name>", pm)
        if not nm:
            return pm
        for _, (new, status, _) in changes.items():
            if nm.group(1) == new:
                return re.sub(r"(<b>Status:</b>\s*)[^<]*", r"\g<1>" + status, pm)
        return pm
    g = re.sub(r"<Placemark>.*?</Placemark>", fix_desc, g, flags=re.S)

    open(a.file, "w", encoding="utf-8").write(g)
    print(f"\nupdated {n} placemark name(s) across both twins, and their description Status lines")


if __name__ == "__main__":
    main()
