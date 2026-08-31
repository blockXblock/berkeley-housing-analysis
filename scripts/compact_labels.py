#!/usr/bin/env python3
"""compact_labels.py — fold building labels onto two lines and shrink the type.

Run after any change to geometry.kml's names. Idempotent: a label already folded is left alone,
so this can be run repeatedly and after sync_status_from_v2.py.

  python scripts/compact_labels.py --dry-run
  python scripts/compact_labels.py --scale 2.0
"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from label_format import parts, compose, is_folded

GEOM = "kml/geometry/geometry.kml"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geometry", default=GEOM)
    ap.add_argument("--scale", type=float, default=2.0,
                    help="LabelStyle scale for building labels. Was 3.0, which at two lines is "
                         "twice the ink on screen; 2.0 keeps them readable while letting the "
                         "buildings show through.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    g = open(a.geometry, errors="replace").read()

    changes = {}
    for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S):
        nm = re.search(r"<name>([^<]*)</name>", pm)
        if not nm:
            continue
        name = nm.group(1)
        # the document's own <name> is not a label
        if "Berkeley Housing Geometry" in name or is_folded(name):
            continue
        bits = parts(name)
        if len(bits) < 2:
            continue
        folded = compose(bits)
        if folded != name:
            changes[name] = folded

    print(f"  {len(changes)} label(s) to fold")
    for old, new in list(changes.items())[:4]:
        print(f"    {old}\n      -> {new!r}")
    scale_now = set(re.findall(r"<LabelStyle><scale>([\d.]+)</scale></LabelStyle>", g))
    print(f"  LabelStyle scales present: {sorted(scale_now)} -> {a.scale} (0 stays 0)")
    if a.dry_run:
        return

    for old, new in changes.items():
        g = g.replace(f"<name>{old}</name>", f"<name>{new}</name>")
    # shrink only the VISIBLE label style; scale 0 is the deliberately-hidden twin
    g = re.sub(r"<LabelStyle><scale>(?!0<)[\d.]+</scale></LabelStyle>",
               f"<LabelStyle><scale>{a.scale}</scale></LabelStyle>", g)
    open(a.geometry, "w").write(g)
    print(f"  wrote {a.geometry}")


if __name__ == "__main__":
    main()
