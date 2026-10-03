#!/usr/bin/env python3
"""tour_timeline.py — turn a tour KML into a timeline a web page can follow while the video plays.

WHY. A recorded tour is a video, and a video does not know where it is. The tour KML does: every
gx:FlyTo carries a duration and a camera, and every gx:Wait a hold. Movie Maker renders tour time
exactly (Allensworth, 2026-10-02: 126.06 s video = 126.0 s schedule; Telegraph: 215.68 s =
215.67 s), so the cumulative durations ARE the video's timecodes. This writes them out as
keyframes: at time t the camera has just arrived at (lat, lon, heading). A page interpolates
between keyframes to know where the video is at any moment.

THE GUARD. A timeline from a different version of the tour than the one recorded is silently
wrong by seconds that grow along the route. Pass --video (a local render) or --duration (the
published video's length, e.g. from YouTube) and the script refuses to write if the totals differ
by more than --tolerance seconds. The Telegraph KML was rebuilt 18 minutes after one render; this
is the check that tells you which render it matches.

  python scripts/tours/tour_timeline.py --tour telegraph-s2n --duration 216
  python scripts/tours/tour_timeline.py --tour telegraph-s2n --video /Volumes/T7-2025/Berkeley-Tours/New/1-Telegraph-S-N-swoop.m4v
  # a live screen recording (Shattuck N-S, June 2026): offset measured by matching motion, sync approximate
  python scripts/tours/tour_timeline.py --tour Shattuck-centerline-flight-with-2190-and-2276-orbits \
      --duration 445.8 --offset 3.5 --tolerance 2 --approximate

Writes docs/tours/streetview/<tour>.json (keyframes) and <tour>.vtt (the same as a WebVTT
metadata track, for a self-hosted <video>).
"""
import argparse, json, pathlib, re, subprocess, sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
NS = {"k": "http://www.opengis.net/kml/2.2", "gx": "http://www.google.com/kml/ext/2.2"}


def keyframes(kml_path):
    """[(t_arrive, lat, lon, heading, alt, tilt, kind)] — one per FlyTo arrival, plus hold ends."""
    tree = ET.parse(kml_path)
    playlist = tree.find(".//gx:Playlist", NS)
    if playlist is None:
        sys.exit(f"no gx:Playlist in {kml_path}")
    t, out, last = 0.0, [], None
    for el in playlist:
        tag = el.tag.split("}")[1]
        dur = float(el.findtext("gx:duration", "0", NS))
        if tag == "FlyTo":
            view = el.find("k:Camera", NS)
            if view is None:
                view = el.find("k:LookAt", NS)
            if view is None:
                t += dur
                continue
            g = lambda name, d="0": float(view.findtext(f"k:{name}", d, NS))
            t += dur
            last = (round(t, 3), g("latitude"), g("longitude"), g("heading"), g("altitude"), g("tilt"),
                    "camera" if view.tag.endswith("Camera") else "lookat")
            out.append(last)
        elif tag == "Wait":
            t += dur
            if last:                                  # the camera holds still: same view, later time
                last = (round(t, 3),) + last[1:]
                out.append(last)
        else:                                         # AnimatedUpdate, SoundCue: their duration counts too
            t += dur
    return out, round(t, 3)


def media_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def vtt_time(s):
    h, m = divmod(int(s), 3600)
    m, sec = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}.{int(round((s - int(s)) * 1000)):03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", required=True, help="tour id in docs/tours.json, e.g. telegraph-s2n")
    ap.add_argument("--video", help="local render to check the total against")
    ap.add_argument("--duration", type=float, help="published video length in seconds (if no local render)")
    ap.add_argument("--tolerance", type=float, default=1.0)
    ap.add_argument("--offset", type=float, default=0.0,
                    help="seconds of video before the tour starts (a screen recording, not a Movie Maker render)")
    ap.add_argument("--approximate", action="store_true",
                    help="mark the sync approximate: for live screen recordings, whose timing drifts")
    a = ap.parse_args()

    cat = json.load(open(ROOT / "docs/tours.json"))
    tours = cat if isinstance(cat, list) else cat.get("tours", [])
    entry = next((t for t in tours if t.get("id") == a.tour), None)
    if not entry:
        sys.exit(f"{a.tour} is not in docs/tours.json")
    kml = ROOT / entry["tour_kml"]
    frames, total = keyframes(kml)

    want = media_duration(a.video) if a.video else a.duration
    if want is None:
        sys.exit("pass --video or --duration: a timeline must be checked against the recording it will drive")
    if abs(want - (total + a.offset)) > a.tolerance:
        sys.exit(f"REFUSED: tour schedule {total:.2f} s + offset {a.offset:.2f} s vs recording {want:.2f} s — "
                 f"this KML is not the one that was recorded")

    out_dir = ROOT / "docs/tours/streetview"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "tour": a.tour,
        "title": entry.get("title"),
        "youtube": (entry.get("video") or {}).get("youtube"),
        "kml": entry["tour_kml"],
        "duration_s": total,
        "checked_against_s": round(want, 2),
        "offset_s": a.offset,
        "approximate": a.approximate,
        "fields": ["t", "lat", "lon", "heading", "alt", "tilt", "kind"],
        "keyframes": [[f[0], round(f[1], 7), round(f[2], 7), round(f[3], 2), round(f[4], 1), round(f[5], 1), f[6]]
                      for f in frames],
    }
    (out_dir / f"{a.tour}.json").write_text(json.dumps(data, separators=(",", ":")))
    cues = ["WEBVTT", ""]
    for (t0, *v0), (t1, *_) in zip(frames, frames[1:]):
        if t1 > t0:
            cues += [f"{vtt_time(t0)} --> {vtt_time(t1)}",
                     json.dumps({"lat": round(v0[0], 7), "lon": round(v0[1], 7), "heading": round(v0[2], 1)}), ""]
    (out_dir / f"{a.tour}.vtt").write_text("\n".join(cues))
    print(f"{a.tour}: {len(frames)} keyframes, {total:.2f} s (recording {want:.2f} s) -> {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
