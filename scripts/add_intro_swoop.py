#!/usr/bin/env python3
"""add_intro_swoop.py — open AND close a corridor tour from a raised vantage.

JOHN'S SPEC (2026-08-28): "move 50 m directly west from the starting point, and go up 50 m.
When the tour starts, hold for 5 s from this vantage point, so the viewer can see where we are
going, then descend to the starting point and continue following the path."

WHY IT HELPS: a corridor tour currently begins already moving, at 25 m, mid-street. The viewer
gets no establishing beat — no sense of which way the flight runs or what is ahead. Five seconds
held above and behind the start reads as an opening shot instead of a jump cut.

BACKWARDS ALONG THE PATH, NOT DUE WEST. The spec says west because Durant runs west-to-east;
generalised, the vantage sits BEHIND the start along the initial heading, so the same tool opens
a north-to-south corridor correctly rather than shoving the camera sideways into a block.

THE HOLD IS A <gx:Wait>, not a zero-length FlyTo. Wait is the element that means "hold the
camera"; faking it with a duplicate FlyTo works but leaves the tour claiming a move that is not
one, and Earth is free to interpolate through it.

TILT IS AIMED DOWN THE STREET, NOT AT THE START POINT. From 50 m up and 50 m back, aiming at the
start would be a 45-degree look at the pavement, which shows the viewer nothing about where the
flight goes. The default aims at a point --look-ahead metres along the route.

THE OUTRO IS THE MIRROR (John, 2026-08-28): "turn and go up to look back where we came from."
Same distance and rise, but BEYOND the end rather than behind the start, and facing the reciprocal
heading, so the closing shot frames the ground just flown. Opening and closing are then the same
move read forwards and backwards.

  python scripts/add_intro_swoop.py kml/tours/durant-w2e.kml --out kml/tours/durant-w2e-swoop.kml \
      --hold 8 --rise 75 --look-ahead 150
"""
import argparse, math, os, re

M = 111320.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tour")
    ap.add_argument("--out", required=True)
    ap.add_argument("--back", type=float, default=50.0, help="metres behind the start, along the initial heading")
    ap.add_argument("--rise", type=float, default=50.0, help="metres above the first waypoint's altitude")
    ap.add_argument("--hold", type=float, default=5.0, help="seconds held at the vantage")
    ap.add_argument("--descend", type=float, default=4.0, help="seconds to fly down onto the start point")
    ap.add_argument("--look-ahead", type=float, default=300.0,
                    help="aim the vantage at a point this far along the route; 0 aims at the start point")
    ap.add_argument("--outro-hold", type=float, default=None,
                    help="seconds held at the closing vantage; defaults to --hold, mirroring the open")
    ap.add_argument("--ascend", type=float, default=None,
                    help="seconds to climb and turn onto the closing vantage; defaults to --descend")
    ap.add_argument("--no-outro", action="store_true", help="open only, no closing shot")
    a = ap.parse_args()

    x = open(a.tour, encoding="utf-8", errors="replace").read()
    first = re.search(r"<gx:FlyTo>.*?</gx:FlyTo>", x, re.S)
    if not first:
        raise SystemExit(f"{a.tour}: no <gx:FlyTo>")
    cam = first.group(0)
    get = lambda tag: float(re.search(rf"<{tag}>([-\d.]+)</{tag}>", cam).group(1))
    lon, lat, alt, hdg = get("longitude"), get("latitude"), get("altitude"), get("heading")
    k = math.cos(math.radians(lat))

    # behind the start: reverse of the heading the flight sets off on
    back_brg = (hdg + 180.0) % 360.0
    vlon = lon + (a.back * math.sin(math.radians(back_brg)) / M) / k
    vlat = lat + (a.back * math.cos(math.radians(back_brg)) / M)
    valt = alt + a.rise

    # aim down the corridor rather than at the pavement
    horiz = a.back + a.look_ahead
    tilt = 90.0 - math.degrees(math.atan2(a.rise, horiz)) if horiz > 0 else 45.0
    tilt = max(0.0, min(89.0, tilt))

    def flyto(dur, mode, lo, la, al, hd, ti):
        return (f"\t\t\t<gx:FlyTo>\n\t\t\t\t<gx:duration>{dur:.2f}</gx:duration>\n"
                f"\t\t\t\t<gx:flyToMode>{mode}</gx:flyToMode>\n\t\t\t\t<Camera>\n"
                f"\t\t\t\t\t<longitude>{lo:.10f}</longitude>\n\t\t\t\t\t<latitude>{la:.10f}</latitude>\n"
                f"\t\t\t\t\t<altitude>{al:.1f}</altitude>\n\t\t\t\t\t<heading>{hd:.2f}</heading>\n"
                f"\t\t\t\t\t<tilt>{ti:.1f}</tilt>\n\t\t\t\t\t<roll>0</roll>\n"
                f"\t\t\t\t\t<altitudeMode>relativeToGround</altitudeMode>\n"
                f"\t\t\t\t</Camera>\n\t\t\t</gx:FlyTo>\n")

    intro = (flyto(0.10, "bounce", vlon, vlat, valt, hdg, tilt)
             + f"\t\t\t<gx:Wait><gx:duration>{a.hold:.2f}</gx:duration></gx:Wait>\n"
             + flyto(a.descend, "smooth", lon, lat, alt, hdg, float(re.search(r"<tilt>([-\d.]+)</tilt>", cam).group(1))))

    out = x.replace("<gx:Playlist>", "<gx:Playlist>\n" + intro.rstrip("\n"), 1)

    if not a.no_outro:
        # THE MIRROR: beyond the END, facing back the way we came.
        last = list(re.finditer(r"<gx:FlyTo>.*?</gx:FlyTo>", x, re.S))[-1].group(0)
        lg = lambda tag: float(re.search(rf"<{tag}>([-\d.]+)</{tag}>", last).group(1))
        elon, elat, ealt, ehdg = lg("longitude"), lg("latitude"), lg("altitude"), lg("heading")
        ek = math.cos(math.radians(elat))
        olon = elon + (a.back * math.sin(math.radians(ehdg)) / M) / ek
        olat = elat + (a.back * math.cos(math.radians(ehdg)) / M)
        back_hdg = (ehdg + 180.0) % 360.0
        outro = (flyto(a.ascend if a.ascend is not None else a.descend, "smooth",
                       olon, olat, ealt + a.rise, back_hdg, tilt)
                 + f"\t\t\t<gx:Wait><gx:duration>"
                   f"{(a.outro_hold if a.outro_hold is not None else a.hold):.2f}</gx:duration></gx:Wait>\n")
        out = out.replace("</gx:Playlist>", outro + "\t\t</gx:Playlist>", 1)
    out = re.sub(r"(<name>)([^<]*?)( · \d\d-\d\d \d\d:\d\d · cp-[0-9a-f]{6})(</name>)",
                 r"\1\2 · swoop\3\4", out)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(out)
    print(f"wrote {a.out}")
    print(f"  vantage  {vlat:.6f}, {vlon:.6f} at {valt:.0f} m — {a.back:.0f} m behind the start "
          f"(bearing {back_brg:.0f}deg), {a.rise:.0f} m above it")
    print(f"  tilt     {tilt:.1f}deg, aimed {a.look_ahead:.0f} m down the route")
    print(f"  timing   {a.hold:.0f} s hold, then {a.descend:.0f} s descent onto the start point")
    if not a.no_outro:
        print(f"  outro    {a.ascend if a.ascend is not None else a.descend:.0f} s climb beyond the end, "
              f"turned {180}deg to face back, then "
              f"{(a.outro_hold if a.outro_hold is not None else a.hold):.0f} s hold")
    print(f"  total    {sum(float(v) for v in re.findall(r'<gx:duration>([\d.]+)', out)):.0f} s "
          f"(was {sum(float(v) for v in re.findall(r'<gx:duration>([\d.]+)', x)):.0f} s)")


if __name__ == "__main__":
    main()
