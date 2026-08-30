#!/usr/bin/env python3
"""publish_video.py — put a recorded flyover on the site: catalog entry + homepage block.

WHY. Publishing a video is two hand-edits in two files with no way to check them, and it is
about to happen seven-plus times as John re-records the corridor set. Hand-editing is how the
catalog ended up listing 13 of 61 packages and how a legend went stale.

WHAT IT RECORDS THAT A HAND-EDIT FORGETS: the geometry generation the video was FLOWN AGAINST,
read from the package on disk rather than typed. That field is the only thing that makes
tour_staleness.py able to answer "does this video still show the current map", and it was
being erased by the build until 2026-08-28.

  python scripts/publish_video.py --tour durant-w2e --youtube ABC123 \\
      --title "Durant Avenue — Milvia to College" --position 1
"""
import argparse, datetime, hashlib, json, pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAT = ROOT / "docs" / "tours.json"
PAGE = ROOT / "docs" / "index.html"
GEOM = ROOT / "kml" / "geometry" / "geometry.kml"

BLOCK = '''    <div style="margin: 20px auto; max-width: 1000px; padding: 0 1.5rem;">
  <h3>{title}</h3>
  <p>{blurb}</p>
  <div style="border-radius: 8px; overflow: hidden; position: relative; padding-bottom: 56.25%; height: 0;">
    <iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
            src="https://www.youtube.com/embed/{vid}?autoplay=1&mute=1&loop=1&playlist={vid}&controls=1&modestbranding=1&rel=0"
            title="{plain}"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen></iframe>
    </div>
</div>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", required=True, help="tour stem, e.g. durant-w2e")
    ap.add_argument("--youtube", required=True, help="11-character id, or the full URL")
    ap.add_argument("--title", required=True)
    ap.add_argument("--blurb", default=None, help="paragraph text; the colour legend is appended by update_legend.py")
    ap.add_argument("--position", type=int, default=1, help="1 = first video on the page")
    ap.add_argument("--recorded", default=None, help="YYYY-MM-DD; defaults to today")
    ap.add_argument("--replaces", default=None,
                    help="id or URL of the video this one supersedes. The existing block is EDITED "
                         "IN PLACE -- same position, same paragraph, same legend -- and only the "
                         "video id and title change. Re-recording a corridor is the common case, "
                         "and rebuilding the block from scratch would silently drop the copy and "
                         "the colour legend that update_legend.py had put there.")
    a = ap.parse_args()
    vid = re.sub(r"^.*(?:youtu\.be/|v=|embed/)", "", a.youtube).split("&")[0].split("?")[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        raise SystemExit(f"that does not look like a YouTube id: {vid!r}")

    tour = ROOT / f"kml/tours/{a.tour}.kml"
    if not tour.exists():
        raise SystemExit(f"no such tour: {tour}")
    subprocess.run(["python3", str(ROOT / "scripts/stamp_geometry.py")], capture_output=True)
    sha = hashlib.sha256(GEOM.read_bytes()).hexdigest()[:12]
    pkg = ROOT / f"kml/tours/packages/{a.tour}__geom-{sha}.kml"
    if not pkg.exists():
        raise SystemExit(f"no package for the CURRENT geometry: {pkg.name}\n"
                         f"  run build_tour_package.py --all first — publishing against a stale\n"
                         f"  package would record a generation the video was not flown against")

    x = tour.read_text(errors="replace")
    dur = round(sum(float(v) for v in re.findall(r"<gx:duration>([\d.]+)", x)), 1)
    era = f"geom-{sha}"
    for feature, tag in (("<!--SWOOP-INTRO-->", "swoops"), ("<gx:Wait>", None)):
        if feature == "<!--SWOOP-INTRO-->" and feature in x:
            era += " · swoops"
    cat = json.loads(CAT.read_text())
    entry = {"id": a.tour, "title": a.title, "tour_kml": f"kml/tours/{a.tour}.kml",
             "source_kml_missing": False,
             "package": f"kml/tours/packages/{a.tour}__geom-{sha}.kml",
             "package_geometry_sha": sha, "flyto_legs": x.count("<gx:FlyTo>"),
             "duration_s": dur, "video": {"youtube": vid},
             "recorded": a.recorded or datetime.date.today().isoformat(),
             "recorded_geometry_era": era, "has_pushpins": False,
             "mapping_inferred": False, "needs_rerecord": False}
    # the catalog is DATA, the homepage is HTML. An entity like &mdash; renders on the page but
    # is literal text anywhere else that reads the catalog, so unescape it on the way in.
    entry["title"] = __import__("html").unescape(entry["title"])
    cat["tours"] = [t for t in cat["tours"] if t["id"] != a.tour]
    cat["tours"].insert(0, entry)
    CAT.write_text(json.dumps(cat, indent=1, ensure_ascii=False))

    h = PAGE.read_text()
    plain = re.sub(r"&[a-z]+;", "-", a.title)
    if a.replaces:
        old = re.sub(r"^.*(?:youtu\.be/|v=|embed/)", "", a.replaces).split("&")[0].split("?")[0]
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", old):
            raise SystemExit(f"--replaces does not look like a YouTube id: {old!r}")
        # SPLIT ON THE DELIMITER, never a regex spanning blocks. A regex written to match one
        # block once deleted FOUR (2026-08-28); splitting and asserting a single hit cannot.
        D = '<div style="margin: 20px auto; max-width: 1000px; padding: 0 1.5rem;">'
        parts = h.split(D)
        hit = [i for i, b in enumerate(parts) if f"embed/{old}" in b]
        if len(hit) != 1:
            raise SystemExit(f"expected exactly 1 block for {old}, found {len(hit)} — refusing to edit")
        i = hit[0]; blk = parts[i]
        blk = blk.replace(old, vid)                       # src, playlist= and the title attribute
        blk = re.sub(r"<h3>.*?</h3>", f"<h3>{a.title}</h3>", blk, count=1, flags=re.S)
        # the iframe's title attribute is the accessible name -- a screen reader announces it,
        # so leaving the superseded video's title there is a real defect, not cosmetic
        blk = re.sub(r'(<iframe[^>]*?\btitle=")[^"]*(")', lambda m: m.group(1) + plain + m.group(2),
                     blk, count=1, flags=re.S)
        if a.blurb:
            blk = re.sub(r"<p[^>]*>.*?</p>", f"<p>{a.blurb}</p>", blk, count=1, flags=re.S)
        if old in blk or f"embed/{vid}" not in blk:
            raise SystemExit("swap did not take — refusing to write")
        parts[i] = blk
        PAGE.write_text(D.join(parts))
        print(f"catalog : {a.tour} -> {vid}, {dur:.0f} s, era {era}")
        print(f"homepage: {old} -> {vid} in place (position unchanged, paragraph and legend kept)")
        return
    h = re.sub(r'    <div style="margin: 20px auto; max-width: 1000px; padding: 0 1.5rem;">\s*<h3>[^<]*</h3>.*?youtube\.com/embed/'
               + re.escape(vid) + r'.*?</div>\s*</div>\n', "", h, flags=re.S)   # replace, never duplicate
    blocks = list(re.finditer(r'    <div style="margin: 20px auto; max-width: 1000px; padding: 0 1.5rem;">\s*<h3>', h))
    if not blocks:
        raise SystemExit("could not find a video block to anchor against in docs/index.html")
    at = blocks[min(max(a.position, 1) - 1, len(blocks) - 1)].start()
    blurb = a.blurb or f"A flyover of the {a.title} corridor."
    h = h[:at] + BLOCK.format(title=a.title, blurb=blurb, vid=vid, plain=plain) + h[at:]
    PAGE.write_text(h)

    print(f"catalog : {a.tour} -> {vid}, {dur:.0f} s, era {era}")
    print(f"homepage: inserted at position {a.position} ({len(blocks)+1} videos now)")
    print(f"\nnext: python3 scripts/update_legend.py     # appends the current colour legend")


if __name__ == "__main__":
    main()
