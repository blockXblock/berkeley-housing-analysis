#!/usr/bin/env python3
"""sync_status_from_v4.py — carry each building's Explorer stage and count into geometry.kml's labels.

(Renamed from sync_status_from_v2.py on 2026-10-02, when the tours were re-pointed at v4.)

WHY IT MATTERS. Since the 2026-08-27 restyle, a building's COLOR is derived from the status
written in its own label (restyle_by_status.py), and the homepage carries a legend describing
that mapping. So a stale label is a visibly wrong map and a false legend, not just a stale string.

THE STAGE IS THE EXPLORER'S. v4_source imports the Explorer exporter's own stage computation, so
the word on a building here is the word the Explorer shows for it ("Under Review", "Entitled but
Inactive", ...). restyle_by_status.py folds that word into the legend's colors.

MATCHES ON THE ADDRESS IN THE DESCRIPTION, not on the label text -- the label is the thing being
corrected, so it cannot also be the key. Only addresses that resolve to EXACTLY ONE v4 project
(after v4_source.by_address's two declared tie-breaks) are touched; every ambiguous address is
listed and left alone.

UPDATES BOTH TWINS. split_label_lod.py gives every building a polygon placemark and a label
placemark, and the name appears in both; changing one would leave the map disagreeing with
itself. The description's Status line is rewritten in the same placemarks.

  python scripts/tours/sync_status_from_v4.py --dry-run
  python scripts/tours/sync_status_from_v4.py --out scratch/.../geometry.kml   # leave the source alone
  python scripts/tours/sync_status_from_v4.py                                 # in place
"""
import argparse, re

# THE label format lives in label_format.py. Splitting on "·" here and rejoining with " · "
# would flatten the two-line fold every time this ran.
from scripts.tours.label_format import parts as label_parts, compose as label_compose
from scripts.tours import v4_source as V

GEOM = "kml/geometry/geometry.kml"

# Figures the MAP is ahead of the database on, from a primary source. Syncing one of these would
# REGRESS a verified correction, so it is held until the database catches up. EMPTY since
# 2026-08-28; the mechanism stays because a blind sync would quietly undo such a correction.
HOLD_UNITS = {}


def resolve(pm, name, index):
    """The one v4 project this placemark shows, or None."""
    ad = re.search(r"<b>([^<]*)</b><br/>", pm)
    # DO NOT REQUIRE THE DESCRIPTION ADDRESS. 2200 Bancroft South and 2400 Bowditch South carry
    # plain-text descriptions, so the label head is the fallback key.
    for cand in ([ad.group(1)] if ad else []) + [label_parts(name)[0] if label_parts(name) else ""]:
        r = V.lookup(cand, index)
        if r:
            return r
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=GEOM)
    ap.add_argument("--out", help="write here instead of over --file")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    g = open(a.file, encoding="utf-8", errors="replace").read()
    index = V.by_address()

    changes, unresolved = {}, set()
    for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S):
        if "<Polygon>" not in pm:
            continue
        nm = re.search(r"<name>([^<]*)</name>", pm)
        if not nm:
            continue
        r = resolve(pm, nm.group(1), index)
        if not r:
            unresolved.add(nm.group(1).replace("\n", " · "))
            continue
        parts = label_parts(nm.group(1))          # understands the two-line fold
        if len(parts) < 2:
            continue
        before = list(parts)
        parts[-1] = r["stage"]
        want = V.count_label(r)
        k = V.akey(r["address_display"])
        if k in HOLD_UNITS:
            want = HOLD_UNITS[k]
        for i, p in enumerate(parts):
            if re.match(r"^\d[\d,]*\s+(units|beds)$", p) and want:
                parts[i] = want
        if parts == before:
            continue
        changes[nm.group(1)] = (label_compose(parts), r["stage"], r["project_key"])

    print(f"{len(changes)} label(s) differ from v4; {len(unresolved)} polygon name(s) resolve to no "
          f"single v4 project (left as they are)\n")
    for old, (new, status, key) in changes.items():
        print(f"  [{key}] {old.replace(chr(10), ' · ')}\n      -> {new.replace(chr(10), ' · ')}")
    if unresolved:
        print("\n  unresolved:")
        for u in sorted(unresolved):
            print(f"    {u}")
    if a.dry_run or not changes:
        return

    n = [0]
    def fix(m):
        pm = m.group(0)
        nm = re.search(r"<name>([^<]*)</name>", pm)
        if not nm or nm.group(1) not in changes:
            return pm
        new, status, _ = changes[nm.group(1)]
        n[0] += 1
        pm = pm.replace(f"<name>{nm.group(1)}</name>", f"<name>{new}</name>", 1)
        return re.sub(r"(<b>Status:</b>\s*)[^<\]]*", lambda s: s.group(1) + status, pm)
    g = re.sub(r"<Placemark>.*?</Placemark>", fix, g, flags=re.S)
    out = a.out or a.file
    open(out, "w", encoding="utf-8").write(g)
    print(f"\nupdated {n[0]} placemark(s) across both twins (names + Status lines) -> {out}")


if __name__ == "__main__":
    main()
