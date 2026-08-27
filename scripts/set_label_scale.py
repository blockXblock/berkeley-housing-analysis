#!/usr/bin/env python3
"""set_label_scale.py — set the font size of the building labels in geometry.kml.

WHY THIS EXISTS (John, 2026-08-26): geometry.kml's 180 styles each carry an IconStyle at
scale 0 -- which is what suppresses the pushpins -- but NONE carries a LabelStyle, so every
building name renders at Earth's default size and the file offers no way to change it. This
adds (or updates) a LabelStyle on every style, so label size is a property of the geometry and
therefore travels into every tour package and every recording.

THE ICON IS NOT OPTIONAL (measured 2026-08-26). With <IconStyle><scale>0</scale> and no href,
Earth largely IGNORES the LabelStyle scale -- adding one at 1.8 made the labels look SMALLER
than the no-LabelStyle default. A ladder of seven settings flown down Shattuck settled it: the
label only grows with scale when the IconStyle points at a real (transparent) image. So every
style gets a 1x1 transparent PNG at icon scale 0.4, exactly as the street signs do.

THE PNG MUST TRAVEL WITH THE KML -- the href is relative. Earth may fail to resolve a sibling
file and fall back to a NETWORK fetch (it did, for John, from a plain directory), so the
reliable distribution is a KMZ with the image zipped inside. This script drops the PNG beside
the file it edits; build_tour_package.py emits a .kmz per package for the same reason.

IT IS NOT THE ONLY MULTIPLIER. Earth's own Tools > Options > 3D View > "Icon/Label Size"
multiplies this. scale 2.0 against a Small global setting still reads small; set that to Large
before recording.

Idempotent: re-run with a different --scale to re-tune. --scale 1.0 restores Earth's default.

  python scripts/set_label_scale.py --scale 1.8
  python scripts/set_label_scale.py --scale 1.8 --colour ffffffff
"""
import argparse, os, re, sys

GEOM = "kml/geometry/geometry.kml"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, required=True, help="LabelStyle scale; 1.0 = Earth default")
    ap.add_argument("--colour", default=None, help="KML aabbggrr; omit to leave colour alone")
    ap.add_argument("--file", default=GEOM)
    ap.add_argument("--icon-scale", type=float, default=0.4,
                    help="IconStyle scale for the transparent marker; 0 disables the icon and, "
                         "as measured, breaks the label scaling")
    a = ap.parse_args()
    g = open(a.file, encoding="utf-8", errors="replace").read()

    col = f"<color>{a.colour}</color>" if a.colour else ""
    added = updated = iconed = 0
    ICON = ('<Icon><href>transparent-1x1.png</href></Icon>'
            '<hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>')

    def fix(m):
        nonlocal added, updated, iconed
        sid, body = m.group(1), m.group(2)
        if "<LabelStyle>" in body:
            updated += 1
            body = re.sub(r"<LabelStyle>.*?</LabelStyle>",
                          f"<LabelStyle><scale>{a.scale}</scale>{col}</LabelStyle>", body, flags=re.S)
        elif "<IconStyle>" in body:
            # only the placemark styles -- an IconStyle is what marks one
            added += 1
            body = body.replace("<IconStyle>",
                                f"<LabelStyle><scale>{a.scale}</scale>{col}</LabelStyle>\n\t\t<IconStyle>", 1)
        if "<IconStyle>" in body:
            # THE ICON IS WHAT MAKES scale WORK -- see the module docstring.
            iconed += 1
            body = re.sub(r"<IconStyle>.*?</IconStyle>",
                          f"<IconStyle><scale>{a.icon_scale}</scale>{ICON}</IconStyle>", body, flags=re.S)
        return f'<Style id="{sid}">{body}</Style>'

    out = re.sub(r'<Style id="([^"]+)">(.*?)</Style>', fix, g, flags=re.S)
    if out == g:
        print("no change")
        return
    open(a.file, "w", encoding="utf-8").write(out)
    print(f"{a.file}: LabelStyle scale {a.scale} on {added + updated} styles "
          f"({added} added, {updated} updated); transparent icon at {a.icon_scale} on {iconed}")
    import shutil
    src = "kml/tours/labels/transparent-1x1.png"
    dst = os.path.join(os.path.dirname(a.file) or ".", "transparent-1x1.png")
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy(src, dst)
        print(f"  copied the icon dependency to {dst}")
    print("  remember Earth's own Tools > Options > 3D View > Icon/Label Size multiplies this")


if __name__ == "__main__":
    main()
