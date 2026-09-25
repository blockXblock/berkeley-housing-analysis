#!/usr/bin/env python3
"""Build the 1911-vs-1950 Elmwood comparison figure from the fetched Sanborn sheets.

Crops the SAME geography — College Ave between Russell and Ashby, Sanborn block 5359 —
out of sheet 180 in both editions and sets them side by side. The crop windows are
expressed as fractions of the sheet so they survive a different `pct:` download size.

Run `scripts/fetch_sanborn_elmwood.py` first.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "sanborn"
OUT = ROOT / "docs" / "images" / "elmwood_sanborn_1911_1950.jpg"

# fractional crop of sheet 180: College Ave frontage, Russell (top) -> Ashby (bottom)
PANELS = [
    ("1911", "College Ave, Russell to Ashby — 1911", (0.067, 0.429, 0.354, 0.843)),
    ("1950", "The same block (5359) — 1950",          (0.066, 0.450, 0.326, 0.900)),
]
PANEL_H = 2100


def font(size: int):
    for p in ("/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main() -> int:
    panels = []
    for year, _cap, (l, t, r, b) in PANELS:
        src = RAW / f"sanborn_berkeley_v2_{year}_0180.jpg"
        if not src.exists():
            raise SystemExit(f"missing {src} - run scripts/fetch_sanborn_elmwood.py")
        im = Image.open(src)
        W, H = im.size
        c = im.crop((int(l * W), int(t * H), int(r * W), int(b * H)))
        panels.append(c.resize((int(c.width * PANEL_H / c.height), PANEL_H), Image.LANCZOS))

    pad, top = 30, 96
    W = sum(p.width for p in panels) + pad * (len(panels) + 1)
    out = Image.new("RGB", (W, PANEL_H + top + 24), "white")
    d = ImageDraw.Draw(out)
    f = font(46)
    x = pad
    for p, (_y, cap, _box) in zip(panels, PANELS):
        out.paste(p, (x, top))
        d.text((x, 30), cap, fill="black", font=f)
        x += p.width + pad

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT, quality=88, optimize=True)
    print(f"{OUT}  {out.size}  {OUT.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
