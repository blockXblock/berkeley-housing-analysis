#!/usr/bin/env python3
"""build_tour_package.py — recombine a camera-only tour KML with the CANONICAL geometry.

The tour library (kml/tours/*.kml) is camera-only (gx:FlyTo paths, no polygons); the buildings
in a recorded video come from whatever geometry file was loaded in Google Earth at record time.
Old videos therefore show old skylines. This script makes regeneration deterministic: it splices
a tour's <gx:Tour> element into the canonical geometry document and emits ONE self-contained
package KML — open it in Google Earth Pro, press play, re-record. Geometry provenance (source
file + sha + placemark count) is stamped into the package description so a video can always be
traced to the skyline it showed.

CANONICAL GEOMETRY: kml/geometry/geometry.kml (served copy republished to docs/geometry.kml) (the hand-edited footprints; verified 2026-07-03 identical
to kml_versions/Geometry/Geometry-2026-05-18-labeled.kml). Hand-edits continue to land there;
packages are DERIVED — never hand-edit a package.

Every rebuild changes the geometry sha, so every package FILENAME changes, which silently
orphans the served catalog docs/tours.json -- its entries keep pointing at the previous
generation. That is not hypothetical: on 2026-08-26 all 11 catalog entries pointed at
geom-5bb87b9b029c while the packages on disk were geom-eedc7a00b1fd, so every tour download
the site offered had been a 404 for some time. So --all now REPOINTS the catalog itself, and
refuses to write a catalog whose targets do not exist on disk.

Usage:
  python scripts/build_tour_package.py kml/tours/205sec.kml            # one tour
  python scripts/build_tour_package.py --all                            # every camera-only tour
Output: kml/tours/packages/<tour-stem>__<geometry-date>.kml
"""
import hashlib
import json
import pathlib
import re
import shutil
import sys
import zipfile
from xml.dom import minidom

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEOMETRY = ROOT / "kml" / "geometry" / "geometry.kml"
OUTDIR = ROOT / "kml" / "tours" / "packages"
GX_NS = 'xmlns:gx="http://www.google.com/kml/ext/2.2"'
ICON = ROOT / "kml" / "tours" / "labels" / "transparent-1x1.png"


def write_kmz(kml_path: pathlib.Path) -> pathlib.Path:
    """A .kmz twin of the package, with the label icon zipped inside.

    THE LABELS NEED AN IMAGE. geometry.kml's styles point at transparent-1x1.png -- without it
    Earth ignores the LabelStyle scale (measured 2026-08-26: a ladder of seven settings flown
    down Shattuck; scale only bites when the IconStyle has a real image). The href is RELATIVE,
    and Earth can fail to resolve a sibling file and fall back to a NETWORK fetch, which is what
    John hit. A KMZ resolves it internally, so the .kmz is the copy to open and to publish; the
    .kml stays for diffing and for anything that reads the package as text.
    """
    dest = kml_path.with_suffix(".kmz")
    # FIXED TIMESTAMPS. A zip records the current time per member, so an otherwise identical
    # rebuild produced 61 byte-different .kmz files and showed up as 61 modified files in git
    # every single time. The package's provenance is the geometry sha in its own filename, not
    # a mtime, so pinning the epoch makes the output reproducible and the diff honest.
    EPOCH = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("doc.kml", EPOCH)
        zi.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(zi, kml_path.read_text(encoding="utf-8"))
        if ICON.exists():
            zi = zipfile.ZipInfo(ICON.name, EPOCH)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, ICON.read_bytes())
    return dest


def extract_tour(tour_path: pathlib.Path) -> str:
    x = tour_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<gx:Tour\b.*?</gx:Tour>", x, re.S)
    if not m:
        raise SystemExit(f"{tour_path}: no <gx:Tour> element (not a camera tour)")
    return m.group(0)


def build(tour_path: pathlib.Path) -> pathlib.Path:
    geom = GEOMETRY.read_text(encoding="utf-8", errors="replace")
    tour = extract_tour(tour_path)
    # keep the geometry's own name honest before packaging it — a package that embeds a
    # mislabelled geometry propagates the lie to every tour.
    import subprocess as _sp
    _sp.run([sys.executable, 'scripts/stamp_geometry.py'], capture_output=True)
    sha = hashlib.sha256(GEOMETRY.read_bytes()).hexdigest()[:12]
    # GEOM_STAMP: a package must SAY which geometry it carries. Google Earth shows only
    # the <name>, and geometry.kml called itself "Geometry-2026-05-18-labeled-no-icon"
    # for months after its content had moved on -- so a stale layer and a current one
    # looked identical in My Places. 2026-08-24: names now carry date + sha.

    n_pm = len(re.findall(r"<Placemark", geom))

    out = geom
    # ensure the gx namespace exists on the root <kml> tag
    kml_tag = re.search(r"<kml\b[^>]*>", out).group(0)
    if "xmlns:gx" not in kml_tag:
        out = out.replace(kml_tag, kml_tag[:-1] + f" {GX_NS}>", 1)
    # provenance stamp + the tour, injected right after the <Document> opening tag
    doc_tag = re.search(r"<Document\b[^>]*>", out)
    if not doc_tag:
        raise SystemExit(f"{GEOMETRY}: no <Document> element")
    stamp = (f"\n<!-- TOUR PACKAGE (generated by scripts/build_tour_package.py — do not hand-edit)"
             f"\n     tour:     {tour_path.relative_to(ROOT)}"
             f"\n     geometry: {GEOMETRY.relative_to(ROOT)} sha256:{sha} placemarks:{n_pm} -->\n")
    out = out.replace(doc_tag.group(0), doc_tag.group(0) + stamp + tour, 1)

    minidom.parseString(out)  # well-formedness gate — refuse to emit broken XML
    OUTDIR.mkdir(parents=True, exist_ok=True)
    dest = OUTDIR / f"{tour_path.stem}__geom-{sha}.kml"
    dest.write_text(out, encoding="utf-8")
    # the .kml twin needs the icon as a sibling; the .kmz carries its own copy
    if ICON.exists() and not (OUTDIR / ICON.name).exists():
        shutil.copy(ICON, OUTDIR / ICON.name)
    write_kmz(dest)
    return dest


def camera_only_tours():
    for fp in sorted((ROOT / "kml" / "tours").rglob("*.kml")):
        if "packages" in fp.parts:
            continue
        x = fp.read_text(encoding="utf-8", errors="replace")
        if "<gx:Tour" in x and "<Polygon" not in x:
            yield fp


def repoint_catalog(sha: str) -> None:
    """Point docs/tours.json at the generation just built. Verify BEFORE writing."""
    cat = ROOT / "docs" / "tours.json"
    if not cat.exists():
        return
    raw = cat.read_text(encoding="utf-8")
    # SCOPED TO THE PACKAGE FIELDS. A blanket substitution over the whole file also rewrote
    # recorded_geometry_era -- the field whose entire job is to record which generation a video
    # was FLOWN AGAINST -- to the current sha on every rebuild. So every entry claimed it had
    # been recorded against whatever was newest, and the one piece of data that says "this video
    # is stale" was being erased by the build that made it stale.
    out = re.sub(r'("package"\s*:\s*"[^"]*?)geom-[0-9a-f]{12}', rf"\g<1>geom-{sha}", raw)
    # the sha ALSO lives in its own field, which the path substitution above never touched --
    # every entry claimed 5bb87b9b029c while its package path said something else. A catalog
    # that contradicts itself is how the 404 went unnoticed for so long.
    out = re.sub(r'("package_geometry_sha":\s*")[0-9a-f]{12}(")', rf"\g<1>{sha}\g<2>", out)
    entries = json.loads(out)
    entries = entries if isinstance(entries, list) else entries.get("tours", [])
    missing = [e["package"] for e in entries
               if e.get("package") and not (ROOT / e["package"]).exists()]
    if missing:
        print(f"  catalog NOT updated — {len(missing)} entry would 404:", file=sys.stderr)
        for m in missing:
            print(f"    {m}", file=sys.stderr)
        raise SystemExit(1)
    if out != raw:
        cat.write_text(out, encoding="utf-8")
        print(f"catalog: docs/tours.json repointed to geom-{sha} ({len(entries)} entries verified)")
    else:
        print(f"catalog: docs/tours.json already at geom-{sha}")


def prune(sha: str) -> None:
    """Delete packages from superseded generations. ONLY after the catalog is verified.

    THIS BELONGS HERE AND NOT IN A HUMAN'S HANDS. Pruning by hand went wrong twice, the same
    way both times -- picking the generation to KEEP by a heuristic instead of by the sha that
    was actually just built. Once by frequency, where 53 old against 53 new was a tie and the
    NEW set lost; once alphabetically, where geom-9c… sorted before geom-d8… and again the new
    set lost. Both left docs/tours.json pointing at files that no longer existed: the exact
    sitewide tour-download 404 the repoint guard exists to prevent.

    Ordering is the safety property. repoint_catalog() runs first and exits non-zero if any
    entry would 404, so by the time this runs the catalog is known good and `sha` is known to
    be the generation it names. Nothing is inferred.
    """
    gone = 0
    for f in sorted(OUTDIR.iterdir()):
        m = re.search(r"__geom-([0-9a-f]{12})\.km[lz]$", f.name)
        if m and m.group(1) != sha:
            f.unlink()
            gone += 1
    if gone:
        print(f"pruned {gone} file(s) from superseded generations; kept geom-{sha}")


if __name__ == "__main__":
    args = sys.argv[1:]
    targets = list(camera_only_tours()) if args == ["--all"] else [pathlib.Path(a) for a in args]
    if not targets:
        raise SystemExit("usage: build_tour_package.py <tour.kml> [...] | --all")
    built = []
    for t in targets:
        dest = build(t)
        built.append(dest)
        print(f"packaged: {dest.relative_to(ROOT)}")
    if args == ["--all"] and built:
        sha = re.search(r"__geom-([0-9a-f]{12})\.kml$", built[0].name).group(1)
        repoint_catalog(sha)
        prune(sha)
