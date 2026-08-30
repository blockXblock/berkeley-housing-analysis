#!/usr/bin/env python3
"""Generate docs/tours.json — the tour catalog powering the site's tour chooser.

Scans tour KMLs, their built packages, and known published videos; records the
GEOMETRY SHA each video was recorded against so staleness is a query, not archaeology.

Usage: python scripts/build_tours_manifest.py [--write]
"""
import json, re, hashlib, sys, subprocess
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
GEOM = ROOT / "kml/geometry/geometry.kml"
TOURS = ROOT / "kml/tours"
PKGS = TOURS / "packages"
OUT = ROOT / "docs/tours.json"

CURRENT_SHA = hashlib.sha256(GEOM.read_bytes()).hexdigest()[:12]

# Published videos. geometry_sha_at_record: the canonical sha when it was recorded;
# null = predates sha stamping (inferred from commit date). Mappings marked inferred
# were derived from names/dates and should be confirmed by John.
#
# THE THREE MAY IDS WERE CYCLICALLY SHIFTED (fixed 2026-08-29). They had been matched by
# DATE, which put each video on its neighbour's tour: Adeline&Shattuck held the private-
# pipeline video, the private pipeline held the UC dormitory video, and the UC dormitory
# held the Adeline&Shattuck one. They are now matched against the <h3> John wrote above
# each embed on the homepage -- his own description of what the video shows. Still marked
# inferred: a title match is strong evidence, not the same as watching the recording.
PUBLISHED = {
 "Shattuck-centerline-flight-with-2190-and-2276-orbits": dict(
    title="June 2026 Shattuck Avenue Building Pipeline", youtube="X0IMsbbhjGk",
    recorded="2026-06-09", geometry_era="2026-06-09 no-icons era", pushpins=False, inferred=True),
 "tour-adeline+shattuck-s2n": dict(
    title="Adeline & Shattuck Corridor", youtube="LAW1WIUF_ks",
    recorded="2026-05-18", geometry_era="2026-05-18", pushpins=True, inferred=True),
 "tour-private-pipeline-over-200-units-2026-05-16": dict(
    title="Berkeley's 17 Largest Private Housing Projects", youtube="3OQjzk9dIOw",
    recorded="2026-05-16", geometry_era="2026-05-17-ish", pushpins=True, inferred=True),
 "uc_dormitory_tour_2026-05-14 (4)": dict(
    title="UC Berkeley New Student Housing", youtube="5VLjGlMuHLU",
    recorded="2026-05-14", geometry_era="pre-2026-05-17", pushpins=True, inferred=True),
 "tour-elmwood+college+bancroft+shattuck-s2n": dict(
    title="Elmwood / College / Bancroft / Shattuck", youtube=None,
    mp4="videos/tour-elmwood+college+bancroft+shattuck-s2n.mp4",
    recorded="2026-05-06", geometry_era="pre-2026-05-14", pushpins=True, inferred=False),
 "campanile-adeline-shattuck": dict(
    title="Campanile / Adeline / Shattuck", youtube=None,
    mp4="videos/campanile-adeline-shattuck.mp4",
    recorded="2026-05-05", geometry_era="pre-2026-05-14", pushpins=True, inferred=False),
}

def is_tour(p):
    t = p.read_text(encoding="utf-8", errors="ignore")
    return "<gx:Tour>" in t or "<gx:FlyTo>" in t

def meta(p):
    t = p.read_text(encoding="utf-8", errors="ignore")
    return dict(flyto_legs=len(re.findall(r"<gx:FlyTo>", t)),
                duration_s=round(sum(float(d) for d in re.findall(r"<gx:duration>([\d.]+)</gx:duration>", t)), 1))

tours, misfiled = [], []
tour_files = {}
for p_ in sorted(TOURS.glob("*.kml")):
    if is_tour(p_):
        tour_files[p_.stem] = p_
    else:
        misfiled.append(dict(file=str(p_.relative_to(ROOT)),
                             note="contains no gx:Tour — geometry file misfiled in tours/",
                             polygons=len(re.findall(r"<Polygon>", p_.read_text(errors='ignore')))))

pkg_by_stem = {}
for q in PKGS.glob("*.kml"):
    pkg_by_stem[re.sub(r"__geom-[0-9a-f]+$", "", q.stem)] = q

for stem in sorted(set(tour_files) | set(pkg_by_stem)):
    src = tour_files.get(stem)
    pkg = pkg_by_stem.get(stem)
    pub = PUBLISHED.get(stem)
    entry = dict(id=stem, title=(pub or {}).get("title", stem.replace("-", " ")),
                 tour_kml=str(src.relative_to(ROOT)) if src else None,
                 source_kml_missing=src is None,
                 package=str(pkg.relative_to(ROOT)) if pkg else None,
                 package_geometry_sha=(re.search(r"__geom-([0-9a-f]+)", pkg.name).group(1) if pkg else None))
    if src: entry.update(meta(src))
    if pub:
        entry["video"] = {k: v for k, v in pub.items() if k in ("youtube", "mp4")}
        entry["recorded"] = pub["recorded"]
        entry["recorded_geometry_era"] = pub["geometry_era"]
        entry["has_pushpins"] = pub["pushpins"]
        entry["mapping_inferred"] = pub.get("inferred", False)
        entry["needs_rerecord"] = True
    else:
        entry["video"] = None
        entry["needs_rerecord"] = None
    tours.append(entry)

# packages whose tour source is absent from docs/tours/
pkg_stems = {re.sub(r"__geom-[0-9a-f]+$", "", q.stem) for q in PKGS.glob("*.kml")}
orphans = sorted(s for s in pkg_stems if s not in tour_files)

# MERGE, DO NOT OVERWRITE. PUBLISHED is a seed for the legacy May/June videos; every video
# published since is recorded by publish_video.py straight into the catalog. A regeneration
# that trusted PUBLISHED alone silently dropped four live mappings (Bancroft, the new
# Shattuck, University, and the UC dormitory tour whose key was missing its " (4)") -- the
# same class of bug as repoint_catalog erasing recorded_geometry_era. So an existing entry's
# publication facts always win over a regenerated blank.
CARRY = ("video", "recorded", "recorded_geometry_era", "has_pushpins",
         "mapping_inferred", "needs_rerecord")
if OUT.exists():
    try:
        prev = {t.get("id"): t for t in json.loads(OUT.read_text()).get("tours", [])}
    except Exception as e:
        raise SystemExit(f"refusing to regenerate: cannot read existing {OUT} ({e})")
    rescued = []
    for t in tours:
        old_t = prev.get(t.get("id"))
        if not old_t:
            continue
        if not t.get("video") and old_t.get("video"):
            for k in CARRY:
                if old_t.get(k) is not None:
                    t[k] = old_t[k]
            rescued.append((old_t["video"].get("youtube") or old_t["video"].get("mp4"), t["id"]))
    for vid, tid in rescued:
        print(f"carried forward mapping {vid} -> {tid}")

# A video can be on the page with no tour KML behind it -- Patrick Kennedy is a documentary,
# not a flight. Those entries are hand-written, live under an "unsourced-" id, and would be
# destroyed by a regeneration that only walks kml/tours/. Carry them through.
if OUT.exists():
    try:
        kept = [t for t in json.loads(OUT.read_text()).get("tours", [])
                if str(t.get("id", "")).startswith("unsourced-")]
        if kept:
            tours = tours + kept
            print(f"carried forward {len(kept)} unsourced entr(y/ies): "
                  + ", ".join(t["id"] for t in kept))
    except Exception as e:
        raise SystemExit(f"refusing to regenerate: cannot read existing {OUT} ({e})")

manifest = dict(
    generated=str(date.today()),
    canonical_geometry=dict(file="kml/geometry/geometry.kml", sha=CURRENT_SHA,
                            buildings=len(re.findall(r"<Polygon>", GEOM.read_text(errors="ignore"))),
                            pushpins_suppressed=True, labels_source="berkeley_housing_v2.db / v_projects_flat"),
    tours=tours,
    orphan_packages=orphans,
    misfiled_in_tours_dir=misfiled,
)
print(json.dumps(dict(tours=len(tours), orphan_packages=len(orphans),
                      misfiled=len(misfiled),
                      needs_rerecord=sum(1 for t in tours if t.get("needs_rerecord")),
                      published=sum(1 for t in tours if t["video"])), indent=1))
if "--write" in sys.argv:
    OUT.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
