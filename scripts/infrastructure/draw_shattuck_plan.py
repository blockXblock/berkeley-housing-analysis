"""Plan view of Shattuck Avenue, Center Street to Allston Way, with every public utility layer.

Reads the raw pulls in data/raw/infrastructure/ (2026-08-30) and parcel outlines from
databases/berkeley.db. Coordinates are projected to a local frame: 'along' = metres south from
Center Street along Shattuck, 'off' = metres east of the right-of-way centre. North is up
(the street runs about 3 degrees off true north).
"""
import json, math, pathlib, re, sqlite3
from xml.sax.saxutils import escape as esc

REPO = pathlib.Path.home() / "berkeley-data"
RAW = REPO / "data/raw/infrastructure"
OUT = pathlib.Path(__file__).resolve().parents[2] / "docs/maps/shattuck-plan.svg"

# local frame (same as the section): A = centreline near Center St, B = near Allston Way
A = (37.87018, -122.26804); B = (37.86912, -122.26813)
K = 111320; KX = K * math.cos(math.radians(37.87))
ax, ay, bx, by = A[1] * KX, A[0] * K, B[1] * KX, B[0] * K
L = math.hypot(bx - ax, by - ay); UX, UY = (bx - ax) / L, (by - ay) / L
def frame(lon, lat):
    dx, dy = lon * KX - ax, lat * K - ay
    return dx * UX + dy * UY, -(dx * UY - dy * UX)        # along (m, south +), off (m, east +)

ALO, AHI, OLO, OHI = -40, 140, -48, 48                    # drawn window, metres
S = 7.2                                                   # px per metre
PX0, PY0 = 120, 150                                       # top-left of the map window
W, H = 1620, PY0 + (AHI - ALO) * S + 150
def px(off): return PX0 + (off - OLO) * S
def py(al): return PY0 + (al - ALO) * S

INK, PAPER = "#2b2620", "#f6f0e1"
C = {"water": "#1f5fbf", "sewer": "#2e7d32", "storm": "#5b8c2a", "gas": "#d4a400", "light": "#c0392b",
     "bart": "#555", "uud": "#cbb98f"}

def coords(g):
    t, c = g["type"], g["coordinates"]
    return {"Point": [[c]], "LineString": [c], "MultiLineString": c,
            "Polygon": [c[0]], "MultiPolygon": [p[0] for p in c]}.get(t, [])

def path(lines):
    out = []
    for line in lines:
        pts = [frame(lon, lat) for lon, lat in line]
        if not any(ALO - 30 < a < AHI + 30 and OLO - 30 < o < OHI + 30 for a, o in pts):
            continue
        out.append("M" + " L".join(f"{px(o):.1f} {py(a):.1f}" for a, o in pts))
    return " ".join(out)

o = []; add = o.append
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" width="{W}" height="{H:.0f}" '
    f'font-family="Georgia, \'Times New Roman\', serif" fill="{INK}">')
add('<defs><clipPath id="win"><rect x="{}" y="{}" width="{}" height="{}"/></clipPath>'.format(
    px(OLO), py(ALO), (OHI - OLO) * S, (AHI - ALO) * S) +
    '<pattern id="uud" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    f'<rect width="8" height="8" fill="#efe6d2"/><line x1="0" y1="0" x2="0" y2="8" stroke="{C["uud"]}" stroke-width="2"/></pattern></defs>')
add(f'<rect width="{W}" height="{H:.0f}" fill="{PAPER}"/>')
add('<text x="60" y="60" font-size="34" font-weight="bold">Under Shattuck Avenue, in plan</text>')
add('<text x="60" y="94" font-size="18" font-style="italic">Center Street to Allston Way · every utility line the public records show · north is up</text>')
add(f'<rect x="{px(OLO)}" y="{py(ALO)}" width="{(OHI-OLO)*S}" height="{(AHI-ALO)*S}" fill="#f1ead8" stroke="{INK}" stroke-width="1.5"/>')
add('<g clip-path="url(#win)">')

# parcels; parcels inside an Underground Utility District get a hatch
def inside(pt, ring):
    x, y = pt; c = False
    for i in range(len(ring)):
        x1, y1 = ring[i]; x2, y2 = ring[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c
uud = [p for f in json.load(open(RAW / "berkeley_underground_utility_districts_2026-08-30.geojson"))["features"]
       if f["geometry"] for p in coords(f["geometry"])]
db = sqlite3.connect(f"file:{REPO/'databases/berkeley.db'}?mode=ro", uri=True)
for wkt, lat, lon in db.execute("select the_geom, Latitude, Longitude from parcels where cast(Latitude as real) "
                                "between 37.8682 and 37.8712 and cast(Longitude as real) between -122.2695 and -122.2667"):
    for ring in re.findall(r"\(\(([^()]+)\)\)", wkt or ""):
        pts = [tuple(map(float, p.split())) for p in ring.split(",")]
        centre = (float(lon), float(lat))
        in_uud = any(inside(centre, r) for r in uud)
        d = "M" + " L".join(f"{px(frame(x, y)[1]):.1f} {py(frame(x, y)[0]):.1f}" for x, y in pts) + " Z"
        add(f'<path d="{d}" fill="{"url(#uud)" if in_uud else "#e6dcc4"}" stroke="#8a7a5c" stroke-width="0.8"/>')

# BART station footprint: schematic
add(f'<rect x="{px(-10)}" y="{py(ALO-5)}" width="{20*S}" height="{(98-(ALO-5))*S}" fill="none" stroke="{C["bart"]}" '
    f'stroke-width="2" stroke-dasharray="12 6"/>')

def layer(fname, colour, width, dash="", pred=lambda p: True):
    for f in json.load(open(RAW / fname))["features"]:
        if f["geometry"] and pred(f["properties"]):
            d = path(coords(f["geometry"]))
            if d:
                add(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}" stroke-linecap="round"{dash}/>')

layer("berkeley_storm_sewer_mains_2026-08-30.geojson", C["storm"], 3, ' stroke-dasharray="10 4 2 4"')
layer("berkeley_sanitary_sewer_mains_2026-08-30.geojson", C["sewer"], 3.2)
layer("berkeley_ebmud_water_mains_2026-08-30.geojson", C["water"], 2.6)
layer("berkeley_pge_gas_pipelines_2026-08-30.geojson", C["gas"], 6)

# streetlights, and the inferred circuits joining each row
lights = []
for f in json.load(open(RAW / "berkeley_streetlights_2026-08-30.geojson"))["features"]:
    p = f["properties"]
    a, of = frame(p["LONGITUDE"], p["LATITUDE"])
    if ALO < a < AHI and OLO < of < OHI:
        lights.append((a, of))
for lo, hi in ((-20, -10), (-10, -3), (22, 34)):
    row = sorted((a, of) for a, of in lights if lo <= of < hi and -5 < a < 98)
    if len(row) > 1:
        add(f'<path d="M' + " L".join(f"{px(of):.1f} {py(a):.1f}" for a, of in row) +
            f'" fill="none" stroke="{C["light"]}" stroke-width="1.3" stroke-dasharray="3 4"/>')
for a, of in lights:
    add(f'<circle cx="{px(of):.1f}" cy="{py(a):.1f}" r="4.5" fill="#fff8e6" stroke="{C["light"]}" stroke-width="2"/>')

# section line A-A at mid-block
SA = 46
add(f'<line x1="{px(OLO)}" y1="{py(SA)}" x2="{px(OHI)}" y2="{py(SA)}" stroke="{INK}" stroke-width="1.6" stroke-dasharray="18 5 3 5"/>')
add('</g>')
add(f'<text x="{px(OLO)-12}" y="{py(SA)+6}" font-size="20" font-weight="bold" text-anchor="end">A</text>'
    f'<text x="{px(OHI)+12}" y="{py(SA)+6}" font-size="20" font-weight="bold">A</text>')

# street names
add(f'<text x="{px(0)}" y="{py(-6)+6}" font-size="16" text-anchor="middle" letter-spacing="2">CENTER ST</text>')
add(f'<text x="{px(0)}" y="{py(104)+6}" font-size="16" text-anchor="middle" letter-spacing="2">ALLSTON WAY</text>')
add(f'<text x="{px(36)}" y="{py(130)}" font-size="16" letter-spacing="2" transform="rotate(-90 {px(36)} {py(130)})">SHATTUCK AVE</text>')

# north arrow and scale bar
nx, ny = px(OHI) - 40, py(ALO) + 50
add(f'<path d="M{nx} {ny-30} l10 26 l-10 -6 l-10 6 z" fill="{INK}"/><text x="{nx}" y="{ny+16}" font-size="16" text-anchor="middle">N</text>')
sb = py(AHI) + 40
add(f'<line x1="{px(OLO)}" y1="{sb}" x2="{px(OLO)+20*S}" y2="{sb}" stroke="{INK}" stroke-width="3"/>'
    f'<text x="{px(OLO)+20*S+10}" y="{sb+5}" font-size="15">20 m (66 ft)</text>')

# legend and notes, right column
LX, LY = px(OHI) + 70, py(ALO) + 10
def key(y, draw, title, note):
    add(draw(y))
    add(f'<text x="{LX+70}" y="{y+5}" font-size="17" font-weight="bold">{esc(title)}</text>')
    for i, line in enumerate(note):
        add(f'<text x="{LX+70}" y="{y+27+i*21}" font-size="15" font-style="italic">{esc(line)}</text>')
seg = lambda col, w, dash="": (lambda y: f'<line x1="{LX}" y1="{y}" x2="{LX+52}" y2="{y}" stroke="{col}" stroke-width="{w}"{dash}/>')
rows = [
    (seg(C["gas"], 6), "PG&E gas main, 10–12 in.", ["198 psi; laid 1966 and 1983. Crosses Shattuck on a diagonal",
                                                    "about 12 m north of the Allston center line. PG&E's public map is",
                                                    "approximate: true position needs a pothole."]),
    (seg(C["water"], 2.6), "EBMUD water mains", ["4 to 12 in.; 1925 to 2019; two pressure zones."]),
    (seg(C["sewer"], 3.2), "Sanitary sewers (City)", ["8 in. plastic (2015) to a 36 in. concrete trunk (c. 1950):",
                                                         "one link in a 27–36 in. chain through downtown."]),
    (seg(C["storm"], 3, ' stroke-dasharray="10 4 2 4"'), "Storm drains (City)", ["24 in. along the east side, 12 in. laterals; 2 of 7 segments on the",
                                                                                  "block have no size recorded. Feeds 54×36 and 63×42 in. arch",
                                                                                  "drains about 165 m north."]),
    (lambda y: f'<circle cx="{LX+26}" cy="{y}" r="5" fill="#fff8e6" stroke="{C["light"]}" stroke-width="2"/>'
               f'<line x1="{LX}" y1="{y}" x2="{LX+18}" y2="{y}" stroke="{C["light"]}" stroke-width="1.3" stroke-dasharray="3 4"/>',
     "Streetlights and their circuits", ["City-owned, metal poles, on PG&E's LS-2 rate under one",
                                          "service account. Lights are mapped; the conduit is not:",
                                          "dashed red lines are inferred, not surveyed."]),
    (lambda y: f'<rect x="{LX}" y="{y-12}" width="52" height="24" fill="url(#uud)" stroke="#8a7a5c"/>',
     "Underground Utility District", ["Both sides of the block are in one. PG&E electric,",
                                      "phone and cable run underground here, but their",
                                      "routes and vaults are not public. Not drawn."]),
    (seg(C["bart"], 2, ' stroke-dasharray="12 6"'), "BART station, Addison to Allston", ["Footprint schematic. BART's communications fiber runs",
                                                                                  "in the trainway; no public record shows it dropping",
                                                                                  "or terminating along Shattuck."]),
    (lambda y: f'<line x1="{LX}" y1="{y}" x2="{LX+52}" y2="{y}" stroke="{INK}" stroke-width="1.6" stroke-dasharray="18 5 3 5"/>',
     "A–A: the cross-section", ["Drawn separately at true scale."]),
]
y = LY
for draw, title, note in rows:
    key(y, draw, title, note); y += 54 + 21 * len(note)
add(f'<text x="{LX}" y="{y+20}" font-size="15"><tspan font-weight="bold">Fiber.</tspan> No public layer shows commercial or City fiber</text>'
    f'<text x="{LX}" y="{y+42}" font-size="15">on this block. 811 locators mark it on request before digging.</text>')
backup = ["Will the drains back up? City branch drains are sized for a 10-year",
          "storm (2.03 in. in 6 hours); bigger storms are expected to pond [1].",
          "No capacity model of downtown (Strawberry watershed) has been",
          "published: the 2011 plan modeled 2 of 10 watersheds, and the",
          "citywide model was being calibrated in Aug 2025 [1, 2]. On 22 Dec",
          "2025, 5 of the City's 36 storm-drain requests came from this",
          "block's corners [3]. The 36 in. sewer is sized for rain leaking into",
          "old sewers, which a 2014 consent decree must cut by 2036 [4]."]
for i, line in enumerate(backup):
    add(f'<text x="{LX}" y="{y+90+i*21}" font-size="15"{" font-weight=\"bold\"" if i == 0 and False else ""}>{esc(line)}</text>')
srcs = ["Data: EBMUD water mains; City of Berkeley sewers, storm drains, streetlights and Underground Utility Districts; PG&E gas pipeline map (60 psi and above only); all pulled 30 Aug 2026. Parcels: Alameda County assessor, Feb 2026.",
        "[1] City of Berkeley, Watershed Management Plan (Oct 2011), ch. 6. [2] Stormwater Master Plan community meeting, 28 Aug 2025. [3] Berkeley open data, 311 Cases (p88g-6gs2).",
        "[4] Berkeleyside, 'Winter storms test East Bay's progress in stopping sewage from entering the bay', 3 May 2023."]
for i, s_ in enumerate(srcs):
    add(f'<text x="60" y="{H-78+i*20:.0f}" font-size="12.5" font-style="italic">{esc(s_)}</text>')
add('</svg>')
OUT.write_text("\n".join(o)); print("wrote", OUT, f"{len(lights)} lights")
