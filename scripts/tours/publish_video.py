#!/usr/bin/env python3
"""publish_video.py — put a recorded flyover on the site: catalog entry + homepage block.

WHY. Publishing a video is two hand-edits in two files with no way to check them, and it is
about to happen seven-plus times as John re-records the corridor set. Hand-editing is how the
catalog ended up listing 13 of 61 packages and how a legend went stale.

WHAT IT RECORDS THAT A HAND-EDIT FORGETS: the geometry generation the video was FLOWN AGAINST,
read from the package on disk rather than typed. That field is the only thing that makes
tour_staleness.py able to answer "does this video still show the current map", and it was
being erased by the build until 2026-08-28.

WHY --video. A YouTube embed opens on Auto, often 240p, and a page can no longer ask for HD
(vq= and setPlaybackQuality are ignored). So the site plays its own copy from R2: give the
master render with --video and the script makes a 1080p and a 720p web copy beside it (in
web/, on the T7), uploads them to R2 videos/<tour>-{1080,720}.mp4, checks the public URL
serves the same bytes, and only then writes data-mp4 into the homepage block. Without
--video the video is published YouTube-only and the script says so.

  python scripts/tours/publish_video.py --tour durant-w2e --youtube ABC123 \\
      --title "Durant Avenue — Milvia to College" --position 1 \\
      --video /Volumes/T7-2025/Berkeley-Tours/New/durant-w2e.m4v
"""
import argparse, datetime, hashlib, json, os, pathlib, re, subprocess, urllib.error, urllib.request
import sys as _sys, os as _os
from scripts.tours.stamp_geometry import geometry_sha as _geometry_sha

ROOT = pathlib.Path(__file__).resolve().parents[2]
CAT = ROOT / "docs" / "tours.json"
PAGE = ROOT / "docs" / "index.html"
GEOM = ROOT / "kml" / "geometry" / "geometry.kml"
# the bucket's custom domain; r2.dev is rate-limited. The same base as streetview.html and the play-all page.
R2_VIDEOS = "https://docs.berkeleybuild.com/videos"
# The encodes the 11 live flyovers use. 1080: re-encoded only when the master is above ~8 Mb/s (a Google Earth
# render is ~11), otherwise remuxed. 720: what phones get.
ENC_1080 = ["-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p"]
ENC_720 = ["-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "slow", "-crf", "24", "-maxrate", "1800k",
           "-bufsize", "3600k", "-pix_fmt", "yuv420p", "-an"]

BLOCK = '''    <div style="margin: 20px auto; max-width: 1000px; padding: 0 1.5rem;">
  <h3>{title}</h3>
  <p>{blurb}</p>
  <div class="vfacade" data-yt="{vid}"{mp4attr}>
    <button type="button" class="vfacade-btn" aria-label="Play video: {plain}">
      <img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" alt=""
           loading="lazy" decoding="async" width="1280" height="720">
      <span class="vfacade-play" aria-hidden="true"></span>
    </button>
    <noscript><iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
            src="https://www.youtube.com/embed/{vid}?rel=0&modestbranding=1"
            title="{plain}"
            frameborder="0"
            allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen></iframe></noscript>
  </div>
  <p style="margin:.4rem 0 0;font-size:.9rem"><a href="https://www.youtube.com/watch?v={vid}">Watch on YouTube</a></p>
</div>
'''


def _probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=height,bit_rate:format=duration,bit_rate", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out); s = d["streams"][0]
    return int(s["height"]), int(s.get("bit_rate") or d["format"]["bit_rate"]), float(d["format"]["duration"])


def make_web_copies(master, tour):
    """master render -> <its folder>/web/<tour>-1080.mp4 and -720.mp4, +faststart. Reuses a copy already made."""
    master = pathlib.Path(master)
    if not master.exists():
        raise SystemExit(f"no such video: {master}  (is the T7 mounted?)")
    h, rate, dur = _probe(master)
    if h < 1080:
        raise SystemExit(f"{master.name} is {h}p; the site's HD copy needs a 1080p master")
    web = master.parent / "web"; web.mkdir(exist_ok=True)
    out = {}
    for res in ("1080", "720"):
        f = web / f"{tour}-{res}.mp4"
        if not f.exists():
            enc = (ENC_1080 if h > 1080 or rate > 8_000_000 else ["-c:v", "copy"]) if res == "1080" else ENC_720
            if res == "1080" and h > 1080:
                enc = ["-vf", "scale=-2:1080"] + enc
            audio = ["-c:a", "copy"] if res == "1080" else []          # ENC_720 drops audio (-an)
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(master), *enc, *audio,
                            "-movflags", "+faststart", str(f)], check=True)
        fh, _, fdur = _probe(f)
        if fh != int(res) or abs(fdur - dur) > 0.5:
            raise SystemExit(f"{f.name}: {fh}p, {fdur:.1f} s -- expected {res}p, {dur:.1f} s; delete it and rerun")
        out[res] = f
    return out, dur


def upload_web_copies(copies, tour, overwrite=False):
    """Both copies -> R2 videos/<tour>-<res>.mp4, then confirm the PUBLIC url serves that many bytes.

    A key that already holds the same bytes (sha256 metadata, or size where an older upload has none) is skipped.
    DIFFERENT bytes under the key are refused without --overwrite: the same tour id re-recorded is the one case
    that should replace it, and then the custom domain may serve the old copy for up to a day (max-age 86400)."""
    import boto3
    from botocore.config import Config
    from boto3.s3.transfer import TransferConfig
    from scripts.upload_pdfs_to_r2 import load_env, need, sha256_file
    load_env(str(ROOT / ".env.r2"))
    s3 = boto3.client("s3", endpoint_url=f"https://{need('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
                      aws_access_key_id=need("R2_ACCESS_KEY_ID"), aws_secret_access_key=need("R2_SECRET_ACCESS_KEY"),
                      region_name="auto", config=Config(retries={"max_attempts": 10, "mode": "adaptive"}))
    bucket = need("R2_BUCKET")
    # parallel parts dropped the connection on this link (2026-10-24): one 8 MB part at a time
    xfer = TransferConfig(max_concurrency=1, multipart_chunksize=8 * 1024 * 1024)
    for res, f in copies.items():
        key, size, sha = f"videos/{tour}-{res}.mp4", f.stat().st_size, sha256_file(f)
        try:
            head = s3.head_object(Bucket=bucket, Key=key)
        except s3.exceptions.ClientError:
            head = None
        if head:
            theirs = head.get("Metadata", {}).get("sha256")
            same = theirs == sha if theirs else head["ContentLength"] == size
            if same:
                print(f"r2      : {key} already holds this copy, not re-uploaded")
            elif not overwrite:
                raise SystemExit(f"{key} holds a DIFFERENT video; pass --overwrite to replace it")
        if not head or (not same and overwrite):
            print(f"r2      : uploading {key} ({size / 1e6:.0f} MB)...", flush=True)
            s3.upload_file(str(f), bucket, key, Config=xfer, ExtraArgs={
                "ContentType": "video/mp4", "CacheControl": "public, max-age=86400",
                "Metadata": {"sha256": sha, "source": f.name}})
            if s3.head_object(Bucket=bucket, Key=key)["ContentLength"] != size:
                raise SystemExit(f"{key}: uploaded size does not match {f}")
        url = f"{R2_VIDEOS}/{tour}-{res}.mp4"
        # Cloudflare answers Python's default User-Agent with 403 (curl gets 200), so name ourselves
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "berkeleybuild-publish_video/1"})
        try:
            r = urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            raise SystemExit(f"{url} answered {e.code}; the upload is in the bucket but the public url does not serve it")
        if r.status != 200 or int(r.headers["Content-Length"]) != size:
            raise SystemExit(f"{url} serves {r.status}, {r.headers.get('Content-Length')} bytes; expected {size}"
                             + (" (the domain may still be caching the replaced copy)" if head else ""))
        print(f"r2      : {url}  {size / 1e6:.0f} MB, public, verified")
    return f"{R2_VIDEOS}/{tour}"


def set_mp4(blk, mp4):
    """Set (or, with mp4=None, remove) the facade's data-mp4 attribute."""
    attr = f' data-mp4="{mp4}"' if mp4 else ""
    new, n = re.subn(r'(<div class="vfacade" data-yt="[^"]*")(?: data-mp4="[^"]*")?', lambda m: m.group(1) + attr,
                     blk, count=1)
    if n != 1:
        raise SystemExit("could not find the vfacade div in the block — refusing to edit")
    return new

# A published flyover is a POSTER, not a running player. Nine autoplaying loops cost the
# homepage 7.3 s of load and ran video far below the fold for readers who never scrolled to
# them. The canonical embed URL stays in the markup (inside <noscript>) because this script
# and update_legend.py both identify a video block by that literal string -- and because a
# reader without JS should still get the video, not an inert picture.


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
    ap.add_argument("--video", default=None,
                    help="the 1080p master render (on the T7). Makes the web copies, uploads them to R2 and "
                         "has the homepage play them in HD. Without it the video is YouTube-only (Auto, often 240p).")
    ap.add_argument("--overwrite", action="store_true",
                    help="replace an R2 copy that holds a different video (the same tour re-recorded)")
    a = ap.parse_args()
    vid = re.sub(r"^.*(?:youtu\.be/|v=|embed/)", "", a.youtube).split("&")[0].split("?")[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        raise SystemExit(f"that does not look like a YouTube id: {vid!r}")

    tour = ROOT / f"kml/tours/{a.tour}.kml"
    if not tour.exists():
        raise SystemExit(f"no such tour: {tour}")
    subprocess.run(["python3", str(ROOT / "scripts/tours/stamp_geometry.py")], capture_output=True)
    sha = _geometry_sha(str(GEOM))
    pkg = ROOT / f"kml/tours/packages/{a.tour}__geom-{sha}.kml"
    if not pkg.exists():
        raise SystemExit(f"no package for the CURRENT geometry: {pkg.name}\n"
                         f"  run build_tour_package.py --all first — publishing against a stale\n"
                         f"  package would record a generation the video was not flown against")
    # upload BEFORE touching the catalog or the page: a failed upload leaves both as they were
    mp4 = None
    if a.video:
        copies, vdur = make_web_copies(a.video, a.tour)
        mp4 = upload_web_copies(copies, a.tour, a.overwrite)

    x = tour.read_text(errors="replace")
    dur = round(sum(float(v) for v in re.findall(r"<gx:duration>([\d.]+)", x)), 1)
    if a.video and abs(vdur - dur) > 2:
        print(f"WARNING : {pathlib.Path(a.video).name} runs {vdur:.1f} s but the tour KML {dur:.1f} s -- "
              f"is this the right render? (Street View timelines follow the KML)")
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
        # an R2 copy left on the block would play the SUPERSEDED recording, so without --video it comes off
        if not mp4 and "data-mp4=" in blk:
            print("WARNING : the block's R2 copy is the old recording; removed. Rerun with --video for HD.")
        blk = set_mp4(blk, mp4)
        if (old != vid and old in blk) or f"embed/{vid}" not in blk:     # old == vid: adding HD to a published video
            raise SystemExit("swap did not take — refusing to write")
        thumb = re.search(r'src="(img/thumbs/[^"]+)"', blk)
        if thumb and not (ROOT / "docs" / thumb.group(1)).exists():
            print(f"WARNING : poster docs/{thumb.group(1)} does not exist yet -- save the new thumbnail there")
        parts[i] = blk
        PAGE.write_text(D.join(parts))
        print(f"catalog : {a.tour} -> {vid}, {dur:.0f} s, era {era}")
        print(f"homepage: {old} -> {vid} in place (position unchanged, paragraph and legend kept)"
              + (", HD from R2" if mp4 else ""))
        print(f"\nnext: python3 scripts/tours/build_tour_map_gallery.py   # the play-all page lists the R2 copies")
        return
    # never duplicate. This used to delete the existing block with a regex ending ".*?</div>\s*</div>", which a
    # block carrying the "Watch on YouTube" line after its facade no longer matches -- it would run on into the
    # next block. Refuse instead; --replaces is the edit-in-place path.
    if f"embed/{vid}" in h:
        raise SystemExit(f"{vid} is already on the homepage; use --replaces {vid} to update its block in place")
    blocks = list(re.finditer(r'    <div style="margin: 20px auto; max-width: 1000px; padding: 0 1.5rem;">\s*<h3>', h))
    if not blocks:
        raise SystemExit("could not find a video block to anchor against in docs/index.html")
    at = blocks[min(max(a.position, 1) - 1, len(blocks) - 1)].start()
    blurb = a.blurb or f"A flyover of the {a.title} corridor."
    mp4attr = f' data-mp4="{mp4}"' if mp4 else ""
    h = h[:at] + BLOCK.format(title=a.title, blurb=blurb, vid=vid, plain=plain, mp4attr=mp4attr) + h[at:]
    PAGE.write_text(h)

    print(f"catalog : {a.tour} -> {vid}, {dur:.0f} s, era {era}")
    print(f"homepage: inserted at position {a.position} ({len(blocks)+1} videos now)"
          + ("" if mp4 else "  -- YouTube-only (Auto, often 240p): rerun with --replaces and --video for HD"))
    print(f"\nnext: python3 scripts/tours/update_legend.py     # appends the current colour legend")
    print(f"      python3 scripts/tours/build_tour_map_gallery.py   # the play-all page lists the R2 copies")


if __name__ == "__main__":
    main()
