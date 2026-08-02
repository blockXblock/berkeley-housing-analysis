#!/usr/bin/env python3
"""Regenerate building labels in docs/geometry.kml from the CANONICAL v2 database.

Supersedes the label half of add_labels_to_kml.py, which read the FROZEN v1
database (berkeley_housing_analysis.db) and therefore emitted stale unit counts
and stages.

Edits <name> IN PLACE so hand-edited footprints, corrected extrusion heights, and
no-icon (pushpin-suppressing) styles are preserved. Label format is unchanged:
    "ADDRESS [· SUBNAME] · N units · STAGE"
Usage:  python scripts/relabel_geometry_from_v2.py [--apply]   (default: preview)
"""
import re, sqlite3, sys, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
GEOM = ROOT / "kml/geometry/geometry.kml"   # canonical source (republish to docs/geometry.kml for the served download)
DB   = ROOT / "databases/berkeley_housing_v2.db"
norm = lambda s: re.sub(r"[^0-9a-z]", "", s.lower())

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
v2 = {}
for addr, units, stage in con.execute(
        "SELECT address_display,total_units,status_label FROM v_projects_flat "
        "WHERE address_display IS NOT NULL"):
    v2[norm(addr)] = (units, stage)

text = GEOM.read_text(encoding="utf-8", errors="ignore")
changes, unmatched = [], []

def relabel(m):
    label = m.group(1)
    if "·" not in label:
        return m.group(0)
    parts = [p.strip() for p in label.split("·")]
    addr = parts[0]
    sub = [p for p in parts[1:] if "unit" not in p.lower() and p != parts[-1]]
    key = norm(addr)
    if key not in v2:
        unmatched.append(addr); return m.group(0)
    units, stage = v2[key]
    if units is None or stage is None:
        return m.group(0)
    new = " · ".join([addr] + sub + [f"{units} units", str(stage)])
    if new != label:
        changes.append((label, new))
    return f"<name>{new}</name>"

out = re.sub(r"<name>([^<]*)</name>", relabel, text)
print(f"labels updated: {len(changes)}   unmatched: {len(set(unmatched))}")
for old, new in changes[:12]:
    print(f"  - {old}\n  + {new}")
if len(changes) > 12: print(f"  ... and {len(changes)-12} more")
if "--apply" in sys.argv:
    GEOM.write_text(out, encoding="utf-8")
    print(f"\nAPPLIED -> {GEOM}")
else:
    print("\n(preview only; re-run with --apply)")
