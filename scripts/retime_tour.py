#!/usr/bin/env python3
"""retime_tour.py — scale every duration in a tour, so a flight can be slowed or quickened.

WHY A SCRIPT AND NOT A SED. A tour's timing lives in TWO element types, and they have to move
together or the flight desynchronises from itself: <gx:FlyTo> durations are camera moves, and
<gx:Wait> durations are the deliberate pauses between them. Scaling only the FlyTos leaves the
pauses at their old length, so a "20% slower" tour arrives at each building 20% slower and then
holds for exactly as long as before -- which reads as rushed at precisely the moments meant to
dwell. panoramic-kennedy-legacy has 165 FlyTo and 16 Wait durations.

Labels are unaffected: svg_label_tour reads each leg's duration out of the retimed tour and gives
its gx:AnimatedUpdate the same value, so label motion follows whatever pace is set here. Retime
FIRST, then label.

  python scripts/retime_tour.py --tour panoramic-kennedy-legacy --factor 1.2
"""
import argparse, pathlib, re, sys


def retime(text, factor):
    n = [0]

    def sub(m):
        n[0] += 1
        return f"<gx:duration>{float(m.group(1)) * factor:.3f}</gx:duration>"

    return re.sub(r"<gx:duration>([\d.]+)</gx:duration>", sub, text), n[0]


def total(text):
    return sum(float(x) for x in re.findall(r"<gx:duration>([\d.]+)</gx:duration>", text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", required=True, help="tour stem in kml/tours/")
    ap.add_argument("--factor", type=float, required=True,
                    help="multiply every duration by this. 1.2 = 20%% slower, 0.8 = 20%% quicker")
    ap.add_argument("--out", default=None, help="output stem; default <tour>-slow<pct>")
    a = ap.parse_args()

    src = pathlib.Path(f"kml/tours/{a.tour}.kml")
    if not src.exists():
        raise SystemExit(f"no such tour: {src}")
    text = src.read_text(errors="replace")
    before = total(text)
    out, n = retime(text, a.factor)

    # The tour NAME is what Movie Maker lists, and a retimed twin with the same name is
    # indistinguishable from its original in that list. Mark the pace in it.
    pct = round((a.factor - 1) * 100)
    tag = f"{abs(pct)}% {'slower' if pct > 0 else 'quicker'}"
    m = re.search(r"(<gx:Tour>.{0,300}?<name>)([^<]*)(</name>)", out, re.S)
    if m:
        out = out[:m.end(2)] + f" · {tag}" + out[m.end(2):]

    stem = a.out or f"{a.tour}-slow{abs(pct)}"
    dst = pathlib.Path(f"kml/tours/{stem}.kml")
    dst.write_text(out)
    print(f"  {n} durations scaled by {a.factor}")
    print(f"  {before:.1f}s ({before/60:.1f} min)  ->  {total(out):.1f}s ({total(out)/60:.1f} min)")
    print(f"  tour name: {re.search(r'<gx:Tour>.{0,300}?<name>([^<]*)', out, re.S).group(1)}")
    print(f"  wrote {dst}")


if __name__ == "__main__":
    main()
