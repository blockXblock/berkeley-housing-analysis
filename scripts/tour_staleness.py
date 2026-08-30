#!/usr/bin/env python3
"""tour_staleness.py — which published videos no longer show the current map, and why.

WHY THIS EXISTS. "Which videos are out of date" lived in prose and in whoever's head was in the
session. That is how a homepage legend stayed FALSE for a third of the map for months, and how
a video with a 180-degree wrong turn in it stayed at the top of the page. A video's staleness is
a fact about two shas and a date; it should be a command.

READS recorded_geometry_era, WHICH WAS BEING ERASED. build_tour_package.py used to substitute
every "geom-XXXX" in the catalog on each rebuild, including this field -- so every entry claimed
it had been flown against whatever was newest. The substitution is now scoped to the package
path. Anything reading this field before 2026-08-28 was reading a lie.

  python scripts/tour_staleness.py
  python scripts/tour_staleness.py --json
"""
import argparse, datetime, hashlib, json, os, pathlib, re, subprocess
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stamp_geometry import geometry_sha as _geometry_sha

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAT = ROOT / "docs" / "tours.json"
GEOM = ROOT / "kml" / "geometry" / "geometry.kml"


def current_sha():
    subprocess.run(["python3", str(ROOT / "scripts" / "stamp_geometry.py")], capture_output=True)
    return _geometry_sha(str(GEOM))


def audit():
    cat = json.loads(CAT.read_text())
    cur = current_sha()
    out = []
    for t in cat["tours"]:
        vid = (t.get("video") or {}).get("youtube")
        if not vid:
            continue
        era = t.get("recorded_geometry_era", "") or ""
        m = re.search(r"geom-([0-9a-f]{12})", era)
        flown = m.group(1) if m else None
        tour = ROOT / t.get("tour_kml", "")
        reasons = []
        if flown is None:
            reasons.append("no geometry sha recorded — era is prose, provenance unknown")
        elif flown != cur:
            reasons.append(f"flown against geom-{flown}, map is now geom-{cur}")
        if tour.exists():
            x = tour.read_text(errors="replace")
            if "<!--SWOOP-INTRO-->" in x and "swoop" not in era.lower():
                reasons.append("tour has gained the opening/closing swoop since")
        if t.get("needs_rerecord"):
            reasons.append("flagged needs_rerecord")
        out.append({"id": t["id"], "video": vid, "recorded": t.get("recorded", "?"),
                    "flown": flown, "current": cur, "stale": bool(reasons), "reasons": reasons})
    return cur, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    cur, rows = audit()
    if a.json:
        print(json.dumps({"current_geometry": cur, "videos": rows}, indent=1))
        return
    stale = [r for r in rows if r["stale"]]
    print(f"current geometry: geom-{cur}")
    print(f"published videos: {len(rows)}   stale: {len(stale)}\n")
    for r in rows:
        mark = "STALE " if r["stale"] else "current"
        print(f"  [{mark}] {r['video']}  {r['id'][:38]:40} recorded {r['recorded']}")
        for why in r["reasons"]:
            print(f"            - {why}")
    unlisted = [p.name.split("__")[0] for p in sorted((ROOT / "kml/tours/packages").glob("*.kmz"))]
    listed = {t["id"] for t in json.loads(CAT.read_text())["tours"]}
    missing = sorted(set(unlisted) - listed)
    if missing:
        print(f"\n  {len(missing)} package(s) not in the catalog at all, so not tracked:")
        for m in missing[:12]:
            print(f"            {m}")
        if len(missing) > 12:
            print(f"            ... and {len(missing)-12} more")


if __name__ == "__main__":
    main()
