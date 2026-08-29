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
import argparse, collections, re, sqlite3

GEOM = "kml/geometry/geometry.kml"
DB = "databases/berkeley_housing_v2.db"

# Figures the MAP is ahead of v2 on, from a primary source. Syncing one of these would REGRESS a
# verified correction, so it is held until v2 catches up -- the data lane's write, not mine.
#
# EMPTY as of 2026-08-28. 2036 Bancroft was held at 87 against v2's 85, which turned out to be a
# migration placeholder (unit_program read "Bedroom distribution unknown; placed as 1BR for schema
# compliance"). The data lane has since committed 87 with the real bedroom mix, so the hold is
# released and a sync is a no-op there. The mechanism stays: the map can be ahead of v2 whenever a
# primary source is read before v2 is updated, and a blind sync would quietly undo it.
HOLD_UNITS = {}


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
    uc = set()
    for addr, in sqlite3.connect(a.db).execute(
            "select f.address_display from project_classifications pc "
            "join vocabulary_classification_types t on t.id=pc.classification_type_id "
            "join v_projects_flat f on f.project_id=pc.project_id where t.code='uc_project'"):
        if addr:
            uc.add(addr.upper().strip())

    # address -> what the label currently claims, taken from the POLYGON twin
    changes = {}
    for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S):
        if "<Polygon>" not in pm:
            continue
        ad = re.search(r"<b>([^<]*)</b><br/>", pm)
        nm = re.search(r"<name>([^<]*)</name>", pm)
        # DO NOT REQUIRE THE DESCRIPTION ADDRESS. 2200 Bancroft South and 2400 Bowditch South
        # carry plain-text descriptions with no <b>ADDRESS</b>, so requiring one skipped them
        # and left one wing reading "550 units" while its twin read "1625 beds" -- the same
        # project disagreeing with itself across two placemarks.
        if not nm:
            continue
        key = (ad.group(1) if ad else nm.group(1).split("·")[0]).upper().strip()
        if key not in v2:
            key = nm.group(1).split("·")[0].upper().strip()
        if key not in v2:
            continue
        units, status = v2[key]
        parts = [p.strip() for p in nm.group(1).split("·")]
        if len(parts) < 2:
            continue
        before = list(parts)
        if parts[-1] != status:
            parts[-1] = status
        # UC IS COUNTED IN BEDS, NOT UNITS, AND CARRIES NO RATIO (CLAUDE.md). A private student
        # project is not uc_project and stays in units -- The Valiant is the case in point.
        noun = "beds" if key in uc else "units"
        for i, p in enumerate(parts):
            m = re.match(r"^(\d+)\s+(units|beds)$", p)
            if not m:
                continue
            want = units
            if key in HOLD_UNITS and HOLD_UNITS[key][0] != units:
                want = HOLD_UNITS[key][0]        # map is ahead of v2, from a primary source
            if want is not None and (int(m.group(1)) != want or m.group(2) != noun):
                parts[i] = f"{want} {noun}"
        if parts == before:
            continue
        changes[nm.group(1)] = (" · ".join(parts), status, None)

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
