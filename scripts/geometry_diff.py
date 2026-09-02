#!/usr/bin/env python3
"""geometry_diff.py — what VISIBLY changed between two geometry generations.

WHY. tour_staleness.py compares the sha a video was flown against with the current one and
calls any mismatch stale. A sha mismatch means the FILE differs, not that the PICTURE does.
On 2026-08-30 it flagged Bancroft, Shattuck and University for re-recording when the only
changes between those generations were two balloon addresses (invisible on screen) and one
label on Haste Street, which none of those three corridors passes. Re-recording a corridor is
an hour of John's time; "stale" has to mean something changed that a viewer could see.

So this compares what Earth actually renders: each placemark's NAME (the on-screen label) and
its polygon RING (position and height). Balloon text, document names and file stamps are
ignored because a viewer never sees them.

It also resolves BOTH sha conventions. Until 2026-08-30 the sha was a hash of the whole file,
which included the stamped date; after, it is the geometry's content hash. Catalog entries
written before the fix carry the old kind, so an era sha is looked up as either.

  python scripts/geometry_diff.py <sha-or-'current'> <sha-or-'current'>
"""
import hashlib, re, subprocess, sys

GEOM = "kml/geometry/geometry.kml"


def strip_name(t):
    return re.sub(r"(<Document>\s*<name>)([^<]*)(</name>)", r"\1\3", t, count=1)


def versions():
    """{sha: (commit, date, text)} for BOTH conventions, newest first."""
    out, log = {}, subprocess.run(
        ["git", "log", "--format=%H %ad", "--date=format:%m-%d %H:%M", "--", GEOM],
        capture_output=True, text=True).stdout.splitlines()
    for line in log:
        if not line.strip():
            continue
        h, d = line.split(" ", 1)
        t = subprocess.run(["git", "show", f"{h}:{GEOM}"], capture_output=True, text=True).stdout
        if not t:
            continue
        for sha in (hashlib.sha256(strip_name(t).encode()).hexdigest()[:12],   # content (new)
                    hashlib.sha256(t.encode()).hexdigest()[:12]):              # whole file (old)
            out.setdefault(sha, (h, d, t))
    return out


def rendered(t):
    """{name: ring} — exactly what a viewer sees: the label and the shape."""
    out = {}
    for pm in re.findall(r"<Placemark>.*?</Placemark>", t, re.S):
        n = re.search(r"<name>([^<]*)</name>", pm)
        if not n:
            continue
        po = re.search(r"<Polygon>.*?<coordinates>\s*(.*?)\s*</coordinates>", pm, re.S)
        ring = " ".join(po.group(1).split()) if po else None
        key = n.group(1).strip()
        # A BUILDING IS TWO PLACEMARKS. Since split_label_lod.py, every building is an extruded
        # Polygon plus a label Point that carries the SAME <name>. The label has no <Polygon>,
        # so a plain assignment let it overwrite the polygon's ring with None -- all 197 of
        # them. That silently disabled everything downstream: visible_change_for() skipped every
        # changed building ("none within 250 m of this flight" for every tour, always), and
        # `moved` compared None against None, so a building changing shape or HEIGHT was never
        # detected at all. Keep the ring; never let a label clobber it.
        if ring is not None or key not in out:
            out[key] = ring
    return out


def diff(a_text, b_text):
    A, B = rendered(a_text), rendered(b_text)
    added = [k for k in B if k not in A]
    removed = [k for k in A if k not in B]
    moved = [k for k in A if k in B and A[k] != B[k]]
    # a LABEL change shows as one name gone and a near-identical one arriving
    relabel = []
    for r in list(removed):
        stem = r.split("·")[0].strip()
        for x in list(added):
            if x.split("·")[0].strip() == stem and A[r] == B[x]:
                relabel.append((r, x)); removed.remove(r); added.remove(x); break
    return added, removed, moved, relabel


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    V = versions()
    cur = open(GEOM).read()
    def text(k):
        if k == "current":
            return cur
        k = k.replace("geom-", "")
        if k not in V:
            sys.exit(f"unknown geometry sha: {k}\n  known: {len(V)} generations in git history")
        return V[k][2]
    a, b = text(sys.argv[1]), text(sys.argv[2])
    added, removed, moved, relabel = diff(a, b)
    if not (added or removed or moved or relabel):
        print("  NO VISIBLE DIFFERENCE — labels and shapes identical.")
        print("  Anything that changed (balloon text, document name, stamp) is not rendered.")
        return
    for lbl, items in (("buildings added", added), ("buildings removed", removed),
                       ("shape or height changed", moved)):
        if items:
            print(f"  {lbl}: {len(items)}")
            for i in items[:12]:
                print(f"     {i[:70]}")
    if relabel:
        print(f"  labels changed: {len(relabel)}")
        for r, x in relabel[:12]:
            print(f"     {r[:60]}\n       -> {x[:60]}")


if __name__ == "__main__":
    main()
