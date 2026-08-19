#!/usr/bin/env python3
"""prototype_geometry_style.py — restyle skyline geometry with clean height-tiered polygons + LOD labels.

Demonstrates the "readable labels + clean base polygons" upgrade for the tour geometry:
  - polygons kept verbatim (footprint + extrude) but given a translucent, HEIGHT-TIERED fill + crisp
    outline, so the drumbeat (low ADU/middle-housing) reads as one colour and the towers pop in warm reds.
  - a separate LABEL placemark per building: a Point at the building TOP with a <LabelStyle> and a
    <Region>/<Lod> so the name only fades in when the camera is close — killing overview clutter.
  - long names shortened to one essential ("2400 Bowditch St · 750u"); full detail stays in the balloon.

Usage:
  python scripts/prototype_geometry_style.py OUT.kml IN1.kml [IN2.kml ...] [--limit N] [--label-lod PX]
    --limit N     : keep only the N TALLEST buildings (for a small prototype)
    --label-lod PX: minLodPixels before a label appears (higher = only when zoomed in; default 450)
"""
import re, sys

TIERS = [(8, "#2fa37d", "7a", "ADU / small"), (25, "#e6a23c", "9a", "mid-rise"),
         (10_000, "#d0342c", "b0", "tower")]     # (max height m, fill rgb, alpha, label)

def kcolor(rgb, alpha):                            # '#RRGGBB' + alpha -> KML aabbggrr
    return alpha + rgb[5:7] + rgb[3:5] + rgb[1:3]

def tier_idx(h):
    for i, (mx, *_ ) in enumerate(TIERS):
        if h <= mx: return i
    return len(TIERS) - 1

def short_label(name):
    parts = [p.strip() for p in name.split("·")]
    m = re.search(r"(\d+)\s*units?", name, re.I)
    if m: return f"{parts[0]} · {m.group(1)}u"
    typ = next((p for p in parts[1:] if p and not p.replace("-", "").isdigit()), "")
    return typ or parts[0]

def parse(kml):
    for pm in re.findall(r"<Placemark>.*?</Placemark>", kml, re.S):
        name = re.search(r"<name>(.*?)</name>", pm, re.S)
        poly = re.search(r"<Polygon>.*?</Polygon>", pm, re.S)
        desc = re.search(r"<description>.*?</description>", pm, re.S)
        if not poly: continue
        coords = re.search(r"<coordinates>(.*?)</coordinates>", poly.group(0), re.S).group(1).split()
        pts = [tuple(map(float, c.split(","))) for c in coords if c.strip()]
        lons = [p[0] for p in pts]; lats = [p[1] for p in pts]; hs = [p[2] for p in pts if len(p) > 2]
        h = max(hs) if hs else 0
        yield {"name": name.group(1).strip() if name else "", "poly": poly.group(0),
               "desc": desc.group(0) if desc else "",
               "clon": sum(lons)/len(lons), "clat": sum(lats)/len(lats), "h": h,
               "bbox": (min(lons), max(lons), min(lats), max(lats))}

def main():
    a = sys.argv[1:]
    limit = int(a[a.index("--limit")+1]) if "--limit" in a else None
    lod = int(a[a.index("--label-lod")+1]) if "--label-lod" in a else 450
    files = [x for x in a if x.endswith(".kml")]
    out, ins = files[0], files[1:]

    blds = [b for f in ins for b in parse(open(f).read())]
    blds.sort(key=lambda b: -b["h"])
    if limit: blds = blds[:limit]
    tiers_used = sorted({tier_idx(b["h"]) for b in blds})

    styles = ""
    for i in tiers_used:
        mx, rgb, al, lab = TIERS[i]
        styles += (f'  <Style id="poly{i}"><PolyStyle><color>{kcolor(rgb, al)}</color><outline>1</outline></PolyStyle>'
                   f'<LineStyle><color>e6ffffff</color><width>1.1</width></LineStyle>'
                   f'<IconStyle><scale>0</scale></IconStyle></Style>\n'
                   f'  <Style id="lab{i}"><IconStyle><scale>0</scale></IconStyle>'
                   f'<LabelStyle><scale>0.9</scale><color>ff{kcolor(rgb, "ff")[2:]}</color></LabelStyle></Style>\n')

    body = []
    for b in blds:
        i = tier_idx(b["h"]); w, e, s, n = b["bbox"]
        body.append(f'  <Placemark><styleUrl>#poly{i}</styleUrl>{b["desc"]}{b["poly"]}</Placemark>')
        # label placemark: Point at building top, only visible when zoomed in (Region/Lod)
        body.append(
            f'  <Placemark><name>{short_label(b["name"])}</name><styleUrl>#lab{i}</styleUrl>'
            f'<Region><LatLonAltBox><west>{w:.6f}</west><east>{e:.6f}</east><south>{s:.6f}</south>'
            f'<north>{n:.6f}</north></LatLonAltBox><Lod><minLodPixels>{lod}</minLodPixels>'
            f'<maxLodPixels>-1</maxLodPixels></Lod></Region>'
            f'<Point><altitudeMode>relativeToGround</altitudeMode>'
            f'<coordinates>{b["clon"]:.6f},{b["clat"]:.6f},{b["h"]}</coordinates></Point></Placemark>')

    kml = ('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n'
           f'  <name>{out.split("/")[-1].replace(".kml","")}</name>\n' + styles + "\n".join(body) +
           "\n</Document>\n</kml>\n")
    import os; os.makedirs(os.path.dirname(out), exist_ok=True); open(out, "w").write(kml)
    from collections import Counter
    c = Counter(tier_idx(b["h"]) for b in blds)
    print(f"wrote {out}  ({len(blds)} buildings, {round(len(kml)/1024)} KB, label-LOD {lod}px)")
    print("  by tier:", {TIERS[k][3]: v for k, v in sorted(c.items())})

if __name__ == "__main__":
    main()
