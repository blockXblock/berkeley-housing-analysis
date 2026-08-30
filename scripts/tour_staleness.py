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
import argparse, datetime, hashlib, json, os, pathlib, re, subprocess, sys
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
        # tour_kml is NULL for a video with no flight behind it (Patrick Kennedy is a
        # documentary). Those entries exist precisely so the deploy gate can see them; the
        # report must survive them rather than crash on the first one.
        tk = t.get("tour_kml")
        tour = (ROOT / tk) if tk else None
        reasons = []
        if flown is None:
            reasons.append("no geometry sha recorded — era is prose, provenance unknown")
        elif flown != cur:
            reasons.append(f"flown against geom-{flown}, map is now geom-{cur}")
        if tour is None:
            reasons.append("no tour KML — cannot be re-recorded, only replaced")
        elif tour.exists():
            x = tour.read_text(errors="replace")
            if "<!--SWOOP-INTRO-->" in x and "swoop" not in era.lower():
                reasons.append("tour has gained the opening/closing swoop since")
        if t.get("needs_rerecord"):
            reasons.append("flagged needs_rerecord")
        # A SHA MISMATCH IS NOT A REASON TO RE-RECORD. It says the file differs, not that the
        # picture does -- and even a real label change matters only if it is somewhere this
        # particular flight can see. Re-recording costs John an hour; make "stale" mean
        # something a viewer of THIS corridor could actually notice.
        if flown and flown != cur and tour is not None and tour.exists():
            verdict = visible_change_for(flown, tour)
            if verdict is not None:
                reasons = [r for r in reasons
                           if not r.startswith("flown against")] + [verdict]
        # "stale" now means A VIEWER WOULD SEE SOMETHING WRONG, not that a hash moved. A
        # verdict ending "no need to re-record" is a clearance, so it must not also raise the
        # flag -- a report that says both at once is one nobody reads twice.
        clear = [r for r in reasons if r.endswith("no need to re-record")]
        stale = bool(reasons) and not (clear and len(clear) == len(reasons))
        out.append({"id": t["id"], "video": vid, "recorded": t.get("recorded", "?"),
                    "flown": flown, "current": cur, "stale": stale,
                    "clear": bool(clear), "reasons": reasons})
    return cur, out



def visible_change_for(flown_sha, tour_path, radius_m=250.0):
    """What a viewer of THIS corridor would see differently, or None if unknowable.

    Returns a sentence for the report: either that nothing rendered changed, or that changes
    exist but none within radius_m of this flight, or which buildings near it changed.
    """
    import math
    # NO SILENT except HERE. The first version of this swallowed a NameError and returned
    # None, so the report printed the old sha-mismatch line and looked like it was working.
    # A checker that fails quietly is worse than no checker.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from geometry_diff import versions, diff, rendered
    except ImportError as e:
        print(f"  (cannot judge visible change: {e})", file=sys.stderr)
        return None
    V = versions()
    key = flown_sha.replace("geom-", "")
    if key not in V:
        return f"flown against geom-{flown_sha} — that generation is not in git history"
    cur_text = open(GEOM).read()
    added, removed, moved, relabel = diff(V[key][2], cur_text)
    changed = added + removed + moved + [x for _, x in relabel]
    if not changed:
        return "map file differs but NOTHING RENDERED CHANGED — no need to re-record"
    # where is this flight, and what changed near it?
    R = rendered(cur_text)
    cams = [(float(a_), float(b_)) for a_, b_ in re.findall(
        r"<longitude>([-\d.]+)</longitude>\s*<latitude>([-\d.]+)</latitude>",
        tour_path.read_text(errors="replace"))]
    if not cams:
        return None
    near = []
    for name in changed:
        ring = R.get(name)
        if not ring:
            continue
        pts = [tuple(map(float, tok.split(",")[:2])) for tok in ring.split() if "," in tok]
        if not pts:
            continue
        lon = sum(p[0] for p in pts) / len(pts); lat = sum(p[1] for p in pts) / len(pts)
        k = math.cos(math.radians(lat))
        d = min(math.hypot((c[0] - lon) * k * 111320, (c[1] - lat) * 111320) for c in cams)
        if d <= radius_m:
            near.append((name, d))
    if not near:
        return (f"{len(changed)} building(s) changed since, but none within "
                f"{radius_m:.0f} m of this flight — no need to re-record")
    near.sort(key=lambda x: x[1])
    head = "; ".join(f"{n[:44]} ({d:.0f} m)" for n, d in near[:3])
    return f"RE-RECORD: {len(near)} changed building(s) in view — {head}"


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
    clear = [r for r in rows if r.get("clear") and not r["stale"]]
    print(f"published videos: {len(rows)}   need re-recording: {len(stale)}"
          f"   map moved but nothing visible: {len(clear)}\n")
    for r in rows:
        mark = "RE-REC" if r["stale"] else ("cleared" if r.get("clear") else "current")
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
