#!/usr/bin/env python3
"""stamp_geometry.py — keep geometry.kml's document name honest about its own contents.

Google Earth's My Places shows only the <name>. geometry.kml called itself
"Geometry-2026-05-18-labeled-no-icon" for three months after its content had moved on, so a stale
May layer and the current file were indistinguishable on screen -- and recording against the wrong
one captures the wrong buildings with nothing to say so.

I stamped it by hand on 2026-08-24 and it went stale again within two days, because a hand stamp
is not a mechanism. Run this after ANY edit to geometry.kml; build_tour_package.py calls it too,
so a package can never carry a mislabelled geometry.

Also republishes docs/geometry.kml, which must always match.
"""
import hashlib, datetime, re, shutil, sys, xml.etree.ElementTree as ET

SRC = "kml/geometry/geometry.kml"
PUB = "docs/geometry.kml"


def geometry_sha(path=SRC):
    """The sha of the GEOMETRY, with the document name stripped out.

    THE ONE DEFINITION. Everything that names a package, repoints the catalog or reports
    staleness must call this rather than hashing the file's bytes. The stamped name carries
    TODAY'S DATE, so a whole-file hash changes at midnight even though no building moved --
    on 2026-08-30 that silently invalidated all 133 packages, refused a publish, and would
    have renamed and redeployed 43 MB of identical files every single day. A fingerprint that
    changes when nothing changed is worse than none: it trains you to ignore it.
    """
    t = open(path).read()
    body = re.sub(r"(<Document>\s*<name>)([^<]*)(</name>)", r"\1\3", t, count=1)
    return hashlib.sha256(body.encode()).hexdigest()[:12]


def main():
    t = open(SRC).read()
    n = t.count("<Placemark")
    sha = geometry_sha()
    name = f"Berkeley Housing Geometry · {datetime.date.today().isoformat()} · {n} buildings · geom-{sha}"
    m = re.search(r"(<Document>\s*<name>)([^<]*)(</name>)", t)
    if not m:
        sys.exit("no <Document><name> found")
    if m.group(2) == name:
        print(f"already current: {name}")
        return
    out = t[:m.start(2)] + name + t[m.end(2):]
    open(SRC, "w").write(out)
    ET.parse(SRC)
    shutil.copy(SRC, PUB)
    print(f"stamped: {name}\n  was:   {m.group(2)}")


if __name__ == "__main__":
    main()
