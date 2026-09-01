#!/usr/bin/env python3
"""prewarm_tour.py — fly a tour's route silently until Earth has actually streamed it.

WHY. Google Earth Pro's disk cache is pinned at its 2048 MB maximum and is already full, so
loading a second corridor evicts the first. Record before the tiles arrive and you get the flat
grey terrain and missing 3D that John saw on Durant and Bancroft. Waiting "long enough" is
guesswork -- what is on screen does not tell you what is still queued.

Earth Pro exposes no Movie Maker automation (its whole AppleScript dictionary is GetViewInfo,
SetViewInfo, MoveCamera, SaveScreenShot, GetPointOnTerrain, GetStreamingProgress,
GetCurrentVersion), so recording stays manual. But GetStreamingProgress answers the question
that actually matters, and SetViewInfo can walk the route. So: jump to each waypoint along the
flight, wait until streaming reaches the threshold, move on. When it finishes, the corridor is
in cache and the take will not be starved.

RECORD ONE CORRIDOR AT A TIME. Warming a second corridor evicts this one -- that is the 2 GB
ceiling, not something this script can fix.

  python scripts/prewarm_tour.py --tour durant-w2e
  python scripts/prewarm_tour.py --tour shattuck-s2n-path --samples 30
"""
import argparse, math, re, subprocess, sys, time, pathlib


def osa(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"Google Earth did not respond: {r.stderr.strip() or 'is it running?'}")
    return r.stdout.strip()


def progress():
    try:
        return int(osa('tell application "Google Earth Pro" to GetStreamingProgress'))
    except ValueError:
        return -1


def goto(lat, lon, dist, tilt, az):
    osa(f'tell application "Google Earth Pro" to SetViewInfo '
        f'{{latitude:{lat:.8f}, longitude:{lon:.8f}, distance:{dist:.1f}, '
        f'tilt:{tilt:.1f}, azimuth:{az:.1f}}} speed 6')


def cameras(path):
    t = path.read_text(errors="replace")
    out = []
    for m in re.finditer(r"<Camera>(.*?)</Camera>", t, re.S):
        c = m.group(1)
        g = lambda k: float(re.search(rf"<{k}>([-\d.]+)</{k}>", c).group(1))
        try:
            out.append((g("longitude"), g("latitude"), g("altitude"), g("heading"), g("tilt")))
        except AttributeError:
            continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", required=True, help="tour stem in kml/tours/")
    ap.add_argument("--samples", type=int, default=24,
                    help="waypoints along the route. More is thorough and slower; the tiles "
                         "between waypoints come in anyway because Earth loads a whole view.")
    # WAIT FOR THE NUMBER TO STOP RISING, NOT FOR A MAGIC VALUE. GetStreamingProgress plateaus
    # at 98 on this machine and never reports 100 -- it read 98 before the first waypoint was
    # even sent. A fixed target of 100 made every waypoint "stall", which is a check that fails
    # on correct data: worse than no check, because it teaches you to ignore it. Done means the
    # figure has held steady for a few polls at a plausible level.
    ap.add_argument("--stable-polls", type=int, default=4,
                    help="consecutive unchanged readings that count as finished")
    ap.add_argument("--min", type=int, default=90, help="reading below this is genuinely unloaded")
    ap.add_argument("--dwell", type=float, default=3.0,
                    help="MINIMUM seconds to sit at each waypoint. This is the part that actually "
                         "warms the cache: GetStreamingProgress sat at 98 on this machine no "
                         "matter what was still arriving, so the percentage is a weak completion "
                         "signal and dwell time is the honest lever.")
    ap.add_argument("--timeout", type=float, default=25.0, help="seconds to wait per waypoint")
    a = ap.parse_args()

    path = pathlib.Path(f"kml/tours/{a.tour}.kml")
    if not path.exists():
        raise SystemExit(f"no such tour: {path}")
    cams = cameras(path)
    if not cams:
        raise SystemExit(f"{path}: no <Camera> elements")

    step = max(len(cams) // a.samples, 1)
    picks = cams[::step]
    print(f"  {path.name}: {len(cams)} cameras, warming {len(picks)} waypoints")
    print(f"  Earth version {osa('tell application \"Google Earth Pro\" to GetCurrentVersion')}")

    t0, slow = time.time(), []
    for i, (lon, lat, alt, hdg, tilt) in enumerate(picks, 1):
        goto(lat, lon, max(alt, 60.0), tilt, hdg)
        start, held, p = time.time(), 0, progress()
        while time.time() - start < a.timeout:
            if time.time() - start < a.dwell:
                time.sleep(0.3); p = progress(); continue
            time.sleep(0.6)
            q = progress()
            held = held + 1 if q == p else 0
            p = q
            if held >= a.stable_polls and p >= a.min:
                break
        took = time.time() - start
        settled = held >= a.stable_polls and p >= a.min
        flag = "" if settled else f"  <-- still climbing ({p}%)"
        if not settled:
            slow.append((i, p))
        print(f"    {i:>3}/{len(picks)}  {lat:.5f},{lon:.5f}  {p:>3}%  {took:5.1f}s{flag}")

    mins = (time.time() - t0) / 60
    print(f"\n  warmed in {mins:.1f} min; final streaming {progress()}%")
    if slow:
        print(f"  {len(slow)} waypoint(s) had not settled within {a.timeout:.0f}s "
              f"— those views may still record thin:")
        for i, p in slow[:6]:
            print(f"    waypoint {i}: {p}%")
        print("  Re-run to give them another go; the cache keeps what it already fetched.")
    else:
        print("  every waypoint settled. NOTE: Earth reports 98% here even when idle, so this")
        print("  confirms the route was walked and given dwell time, not that every tile landed.")
        print("  Record this corridor NOW — warming another evicts it (2 GB cache ceiling).")


if __name__ == "__main__":
    main()
