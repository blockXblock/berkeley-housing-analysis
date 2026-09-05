#!/usr/bin/env python3
"""reaim_tour_after_move.py — move a tour's camera when its buildings move.

THE FAILURE THIS FIXES. A tour's <gx:FlyTo> waypoints are absolute coordinates authored against
the geometry as it stood. Correct a footprint and the camera keeps flying to where the building
used to be: on 2026-09-05 Acton Courtyard moved 56 m and 14 of its waypoints stayed behind, so the
flight arrived at an empty patch of University Avenue with the label 56 m away. Step Up Housing had
meanwhile moved 166 m ONTO Acton's old ground, so the camera that used to frame Acton now framed a
different building entirely.

THE RULE: a waypoint belongs to whichever building it was NEAREST TO IN THE OLD GEOMETRY, and it
moves by exactly that building's delta. That preserves the choreography -- each waypoint keeps its
distance, bearing and altitude relative to its own subject -- rather than re-deriving a flight path,
which would discard whatever the tour author framed by hand.

  python3 scripts/reaim_tour_after_move.py --tour panoramic-kennedy-legacy-slow20 \
      --old-geom-rev 9b0df97^ --apply
"""
import argparse, math, re, subprocess, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_building_loop import placemark_name

GEOM = "kml/tours/panoramic-kennedy-legacy.kml"
CLAIM_RADIUS_M = 200.0     # beyond this a waypoint is a transit leg, owned by nobody


def centroids(text):
    out = {}
    for pm in re.findall(r"<Placemark>.*?</Placemark>", text, re.S):
        if "<Polygon>" not in pm:
            continue
        k = placemark_name(pm)
        pts = [q.split(",") for c in re.findall(
            r"<Polygon>.*?<coordinates>\s*(.*?)\s*</coordinates>", pm, re.S) for q in c.split()]
        pts = [(float(x[0]), float(x[1])) for x in pts if len(x) >= 2]
        if k and pts:
            out[k] = (sum(a for a, _ in pts) / len(pts), sum(b for _, b in pts) / len(pts))
    return out


# A CORRECTED BUILDING IS OFTEN RENAMED TOO, and then matching by address cannot see that the old
# and new placemark are the same thing. All three of the big 2026-09-05 moves were renamed as part
# of the correction -- the whole point was that the old address was wrong -- so the first version of
# this tool silently skipped exactly the buildings it was written for. An explicit map is the only
# honest way to say "these two names are one building".
RENAMED = {
    "1370UNIVERSITYAVE": "2002ACTONST",     # Acton Courtyard, onto its own street
    "2110HASTEST":       "2451SHATTUCKAVE", # Fine Arts, onto the old cinema site
    "2115HASTEST":       "2451SHATTUCKAVE",
    "1685SHATTUCKAVE":   "2109VIRGINIAST",  # Panoramic Legacy = proj15
}


def norm(s):
    k = re.sub(r"[^A-Z0-9]", "", s.upper()).replace("APPROXLOC", "")
    return RENAMED.get(k, k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", required=True)
    ap.add_argument("--old-geom-rev", required=True,
                    help="git rev holding the geometry BEFORE the footprints moved")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    old_txt = subprocess.run(["git", "show", f"{a.old_geom_rev}:{GEOM}"],
                             capture_output=True, text=True).stdout
    if not old_txt:
        raise SystemExit(f"could not read {GEOM} at {a.old_geom_rev}")
    old, new = centroids(old_txt), centroids(open(GEOM, errors="replace").read())
    on, nn = {norm(k): v for k, v in old.items()}, {norm(k): v for k, v in new.items()}

    delta = {}
    for k in set(on) & set(nn):
        d = (nn[k][0] - on[k][0], nn[k][1] - on[k][1])
        m = math.hypot(d[0] * math.cos(math.radians(on[k][1])) * 111320, d[1] * 111320)
        if m > 1.0:
            delta[k] = (d, m, on[k])
    print(f"  {len(delta)} building(s) moved since {a.old_geom_rev}")
    for k, (_, m, _) in sorted(delta.items(), key=lambda x: -x[1][1])[:6]:
        print(f"    {k[:30]:30} {m:6.1f} m")

    path = f"kml/tours/{a.tour}.kml"
    text = open(path, errors="replace").read()
    moved = 0
    claims = {}

    def fix(block):
        nonlocal moved
        lo = re.search(r"<longitude>([-\d.]+)</longitude>", block)
        la = re.search(r"<latitude>([-\d.]+)</latitude>", block)
        if not (lo and la):
            return block
        x, y = float(lo.group(1)), float(la.group(1))
        k = math.cos(math.radians(y))
        # whose was this waypoint, in the OLD geometry?
        best, bd = None, 1e9
        for key, (_, _, oldpos) in delta.items():
            d = math.hypot((oldpos[0] - x) * k * 111320, (oldpos[1] - y) * 111320)
            if d < bd:
                best, bd = key, d
        # a waypoint nearer some UNMOVED building than to any moved one is not ours to touch
        for key, pos in on.items():
            if key in delta:
                continue
            if math.hypot((pos[0] - x) * k * 111320, (pos[1] - y) * 111320) < bd:
                return block
        if best is None or bd > CLAIM_RADIUS_M:
            return block
        (dx, dy), _, _ = delta[best]
        claims[best] = claims.get(best, 0) + 1
        moved += 1
        block = block.replace(lo.group(0), f"<longitude>{x+dx:.8f}</longitude>")
        block = block.replace(la.group(0), f"<latitude>{y+dy:.8f}</latitude>")
        return block

    out = re.sub(r"<gx:FlyTo>.*?</gx:FlyTo>", lambda m: fix(m.group(0)), text, flags=re.S)
    total = len(re.findall(r"<gx:FlyTo>", text))
    print(f"\n  {moved} of {total} waypoints re-aimed:")
    for k, n in sorted(claims.items(), key=lambda x: -x[1]):
        print(f"    {n:3} waypoints followed {k[:34]}")
    if a.apply:
        open(path, "w").write(out)
        print(f"  written to {path}")
    else:
        print("  (dry run — pass --apply)")


if __name__ == "__main__":
    main()
