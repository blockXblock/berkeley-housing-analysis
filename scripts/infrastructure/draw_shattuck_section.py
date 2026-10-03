"""Cross-section of Shattuck Avenue between Center Street and Allston Way, mid-block, looking north.

Horizontal positions: measured from data/raw/infrastructure/*.geojson (EBMUD water mains, City of
Berkeley sanitary and storm sewers, pulled 2026-08-30), as offsets from the middle of the right of
way. Right-of-way edges: Alameda County assessor parcel lines (databases/berkeley.db).
Depths: from the City's recorded invert and rim elevations where they exist; otherwise assumed and
drawn dashed. The BART station is schematic (not in any of these datasets).
Context: CE 112 lab, 21 Oct 2022 (Carlton Chan, EBMUD) asked students to design a new water main
along this block; slide 5 of that lab is the model for this drawing.
"""
import pathlib
from xml.sax.saxutils import escape as esc

OUT = pathlib.Path(__file__).resolve().parents[2] / "docs/maps/shattuck-cross-section.svg"
W, H = 2200, 1520
PX = 6.8                      # px per foot, both axes: true scale
ROW = 102.5                   # half-width of the right of way, ft (62.5 m between parcel lines)
XL = 330                      # x of the west parcel line
X0 = XL + ROW * PX            # x of the right-of-way centre
Y0 = 380                      # y of the street surface
DEEP = 62                     # depth drawn, ft

def x(ft): return X0 + ft * PX
def y(ft): return Y0 + ft * PX

INK, PAPER, SOIL = "#2b2620", "#f6f0e1", "#dccdae"
WATER, SEWER, GAS = "#1f5fbf", "#2e7d32", "#b88a00"

# key: (offset ft east of centre, depth to centre ft, diameter in, colour, solid?, title, note)
P = {
    "w1": (-59, 3.5, 6, WATER, False, "Water main, 6 in., 1967", "EBMUD · depth assumed"),
    "s1": (-43, 11.0, 8, SEWER, True, "Sewer, 8 in. plastic, 2015", "invert ≈ 11 ft (City record)"),
    "w2": (18, 3.5, 12, WATER, False, "Water main, 12 in., 1966", "EBMUD, upper zone · depth assumed"),
    "st": (56, 9.0, 24, SEWER, True, "Storm drain, 24 in. concrete", "invert ≈ 10 ft (City record)"),
    "s2": (61, 6.5, 36, SEWER, False, "Sewer trunk, 36 in. concrete, c. 1950", "records disagree · depth estimated"),
    "w3": (64, 3.5, 12, WATER, False, "Water main, 12 in., 2019", "EBMUD, lower zone · depth assumed"),
    "w4": (75, 3.5, 12, WATER, False, "Water main, 12 in., 1966", "EBMUD, lower zone · depth assumed"),
    "s3": (82, 10.3, 8, SEWER, True, "Sewer, 8 in. plastic, 2015", "invert ≈ 10.7 ft (City record)"),
}

o = []
a = o.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
  f'font-family="Georgia, \'Times New Roman\', serif" fill="{INK}">')
a('<defs>'
  f'<pattern id="soil" width="24" height="20" patternUnits="userSpaceOnUse"><rect width="24" height="20" fill="{SOIL}"/>'
  '<path d="M2 5 l6 -2 M13 12 l7 -2 M4 17 l5 -1 M17 4 l4 -1" stroke="#9a8664" stroke-width="1" fill="none"/>'
  '<circle cx="10" cy="7" r="0.9" fill="#9a8664"/><circle cx="21" cy="15" r="0.7" fill="#9a8664"/></pattern>'
  '<pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
  '<line x1="0" y1="0" x2="0" y2="7" stroke="#6b5d4a" stroke-width="0.8"/></pattern>'
  '<pattern id="concrete" width="11" height="11" patternUnits="userSpaceOnUse"><rect width="11" height="11" fill="#e9e5db"/>'
  '<circle cx="3" cy="4" r="0.8" fill="#9a958b"/><circle cx="8" cy="9" r="0.6" fill="#9a958b"/></pattern>'
  '</defs>')
a(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')

# ---------- title ----------
a('<text x="60" y="62" font-size="36" font-weight="bold">What lies beneath Shattuck Avenue</text>')
a('<text x="60" y="98" font-size="19" font-style="italic">Between Center Street and Allston Way, mid-block, looking north. '
  'Drawn to true scale: no vertical exaggeration.</text>')

# ---------- right-of-way dimension ----------
dy = 150
a(f'<line x1="{x(-ROW)}" y1="{dy}" x2="{x(ROW)}" y2="{dy}" stroke="{INK}" stroke-width="1.2"/>'
  f'<path d="M{x(-ROW)} {dy} l12 -5 l0 10 z M{x(ROW)} {dy} l-12 -5 l0 10 z" fill="{INK}"/>'
  f'<rect x="{X0-230}" y="{dy-15}" width="460" height="28" fill="{PAPER}"/>'
  f'<text x="{X0}" y="{dy+6}" font-size="17" text-anchor="middle">205 ft from parcel line to parcel line (county assessor)</text>')

# ---------- buildings, set back behind the parcel lines ----------
for side, label in ((-1, "2140 Shattuck"), (1, "2171 Shattuck")):
    edge = x(side * ROW)
    left = edge - 200 if side < 0 else edge
    a(f'<rect x="{left}" y="{Y0-180}" width="200" height="180" fill="#efe6d2" stroke="{INK}" stroke-width="2"/>')
    for r in range(3):
        for c in range(3):
            a(f'<rect x="{left+22+c*60}" y="{Y0-162+r*52}" width="36" height="34" fill="url(#hatch)" stroke="{INK}" stroke-width="1.2"/>')
    a(f'<text x="{left+100}" y="{Y0-190}" font-size="15" text-anchor="middle" font-style="italic">{label}</text>')

# ---------- ground ----------
a(f'<rect x="{x(-ROW)-40}" y="{Y0}" width="{2*ROW*PX+80}" height="{DEEP*PX}" fill="url(#soil)" stroke="{INK}" stroke-width="1"/>')
a(f'<line x1="{x(-ROW)-40}" y1="{Y0}" x2="{x(ROW)+40}" y2="{Y0}" stroke="{INK}" stroke-width="3"/>')
for side in (-1, 1):
    a(f'<line x1="{x(side*ROW)}" y1="{Y0}" x2="{x(side*ROW)}" y2="{Y0+26}" stroke="{INK}" stroke-width="1.2" stroke-dasharray="4 4"/>')
    curb = x(side * (ROW - 15))
    a(f'<rect x="{curb - 3}" y="{Y0-5}" width="6" height="5" fill="{INK}"/>')
a(f'<text x="{x(-ROW+7.5)}" y="{Y0-10}" font-size="14" text-anchor="middle">sidewalk</text>'
  f'<text x="{x(ROW-7.5)}" y="{Y0-10}" font-size="14" text-anchor="middle">sidewalk</text>'
  f'<text x="{X0+60}" y="{Y0-130}" font-size="16" text-anchor="middle" letter-spacing="2">SHATTUCK AVENUE: lanes, BART plaza, bus stops (layout simplified)</text>')

# ---------- depth scale ----------
sx = XL - 110
a(f'<line x1="{sx}" y1="{Y0}" x2="{sx}" y2="{y(60)}" stroke="{INK}" stroke-width="1.5"/>')
for d in range(0, 61, 10):
    a(f'<line x1="{sx-8}" y1="{y(d)}" x2="{sx}" y2="{y(d)}" stroke="{INK}" stroke-width="1.5"/>'
      f'<text x="{sx-14}" y="{y(d)+6}" font-size="16" text-anchor="end">{d} ft</text>')
a(f'<text x="{sx-78}" y="{y(30)}" font-size="16" transform="rotate(-90 {sx-78} {y(30)})" text-anchor="middle">depth below the street</text>')

# ---------- BART station (schematic) ----------
b0, b1, top, mez, rail, bot = -34, 34, 15, 31, 50, 58
a(f'<rect x="{x(b0)}" y="{y(top)}" width="{(b1-b0)*PX}" height="{(bot-top)*PX}" fill="url(#concrete)" '
  f'stroke="{INK}" stroke-width="2" stroke-dasharray="10 6"/>')
a(f'<line x1="{x(b0)}" y1="{y(mez)}" x2="{x(b1)}" y2="{y(mez)}" stroke="{INK}" stroke-width="1.5" stroke-dasharray="10 6"/>')
a(f'<text x="{X0}" y="{y(top)+30}" font-size="19" text-anchor="middle" font-weight="bold">Downtown Berkeley BART station</text>'
  f'<text x="{X0}" y="{y(top)+54}" font-size="16" text-anchor="middle" font-style="italic">mezzanine and fare gates · opened 1973</text>'
  f'<text x="{X0}" y="{y(top)+78}" font-size="15" text-anchor="middle" font-style="italic">outline and depth schematic: not in these records</text>')
# island platform with a train on each side
a(f'<rect x="{x(-9)}" y="{y(rail-4)}" width="{18*PX}" height="{4*PX}" fill="#d8d2c4" stroke="{INK}" stroke-width="1.5"/>')
a(f'<text x="{X0}" y="{y(rail-4)-12}" font-size="15" text-anchor="middle" font-style="italic">island platform</text>')
for tx in (-23, 11):
    a(f'<rect x="{x(tx)}" y="{y(rail-11.5)}" width="{12*PX}" height="{11*PX}" rx="12" fill="#fbfaf5" stroke="{INK}" stroke-width="1.6"/>'
      f'<rect x="{x(tx)+12}" y="{y(rail-9.5)}" width="{12*PX-24}" height="{3*PX}" fill="none" stroke="{INK}" stroke-width="1.1"/>'
      f'<line x1="{x(tx)-6}" y1="{y(rail)+2}" x2="{x(tx)+12*PX+6}" y2="{y(rail)+2}" stroke="{INK}" stroke-width="2.5"/>')

# BART communications fiber in the trainway (per John Gage); no public record of a drop here
a(f'<line x1="{x(b0)+6}" y1="{y(rail-13)}" x2="{x(b1)-6}" y2="{y(rail-13)}" stroke="#e67e22" stroke-width="3"/>'
  f'<text x="{X0}" y="{y(rail-13)-8}" font-size="14" text-anchor="middle" fill="#b85c00" font-style="italic">'
  f'BART fiber, in the trainway: no public record of a drop here</text>')

# station stair at the street (one of the Shattuck entrances)
a(f'<path d="M{x(-8)} {Y0} l0 -26 l40 0 l0 26" fill="#efe6d2" stroke="{INK}" stroke-width="1.5"/>'
  f'<path d="M{x(-8)-4} {Y0-26} l24 -14 l24 14" fill="none" stroke="{INK}" stroke-width="1.5"/>')

# ---------- streetlights at A-A, with conduit drawn where it usually runs ----------
LIGHT = "#c0392b"
for lo in (-43, -23, 82):
    lx = x(lo)
    a(f'<line x1="{lx}" y1="{Y0}" x2="{lx}" y2="{Y0-95}" stroke="{INK}" stroke-width="3"/>'
      f'<path d="M{lx} {Y0-95} q14 -10 26 -4" fill="none" stroke="{INK}" stroke-width="2.5"/>'
      f'<rect x="{lx+18}" y="{Y0-99}" width="16" height="8" rx="3" fill="#fff4c9" stroke="{INK}" stroke-width="1.2"/>'
      f'<line x1="{lx}" y1="{Y0}" x2="{lx}" y2="{y(2)}" stroke="{LIGHT}" stroke-width="1.5" stroke-dasharray="3 3"/>'
      f'<circle cx="{lx}" cy="{y(2)}" r="3" fill="{LIGHT}"/>')
a(f'<line x1="{x(-48)}" y1="{y(2)}" x2="{x(-18)}" y2="{y(2)}" stroke="{LIGHT}" stroke-width="1.5" stroke-dasharray="3 3"/>')
a(f'<text x="{x(-99)}" y="{Y0-142}" font-size="14" fill="{LIGHT}" font-style="italic">streetlights (City, LS-2): poles mapped;</text>'
  f'<text x="{x(-99)}" y="{Y0-124}" font-size="14" fill="{LIGHT}" font-style="italic">conduit dashed at a typical 2 ft, not surveyed</text>')

# ---------- pipes ----------
def pipe(cx, cy, dia, col, solid, scale=PX, minr=3.0, sw=2.5):
    r = max(dia / 24 * scale, minr)
    dash = "" if solid else ' stroke-dasharray="5 3"'
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fbfaf5" stroke="{col}" stroke-width="{sw}"{dash}/>'
            f'<circle cx="{cx}" cy="{cy}" r="{max(r-sw-1, 1)}" fill="{col}" opacity="0.22"/>'), r

for k, (off, dep, dia, col, solid, t, n) in P.items():
    s, _ = pipe(x(off), y(dep), dia, col, solid)
    a(s)

def label(tx, ty, k, anchor="start"):
    off, dep, dia, col, solid, t, n = P[k]
    return (f'<text x="{tx}" y="{ty}" font-size="16" fill="{col}" font-weight="bold" text-anchor="{anchor}">{t}</text>'
            f'<text x="{tx}" y="{ty+19}" font-size="14" font-style="italic" text-anchor="{anchor}">{n}</text>')

# west pipes: labels below, clear of the station
# s1: label below, ending just west of the station; w1: label to its left, above s1's
a(f'<path d="M{x(-43)} {y(11)+6} L{x(-43)} {y(19)-5}" stroke="{INK}" stroke-width="0.9" fill="none"/>')
a(label(x(-36), y(19), "s1", "end"))
a(f'<path d="M{x(-59)} {y(3.5)+6} L{x(-59)} {y(9)-5}" stroke="{INK}" stroke-width="0.9" fill="none"/>')
a(label(x(-61), y(9), "w1", "end"))
# w2 over the station roof
a(f'<path d="M{x(18)} {y(3.5)+6} L{x(18)} {y(8)} L{x(14)} {y(8)}" stroke="{INK}" stroke-width="0.9" fill="none"/>')
a(label(x(13), y(8)+5, "w2", "end"))

# east corridor: boxed in the section, drawn 3x in the detail below
cx0, cx1, cd1 = 48, 90, 14
a(f'<rect x="{x(cx0)}" y="{Y0+2}" width="{(cx1-cx0)*PX}" height="{cd1*PX}" fill="none" stroke="{INK}" stroke-width="1.5" stroke-dasharray="3 3"/>')
a(f'<text x="{x((cx0+cx1)/2)}" y="{y(cd1)+22}" font-size="16" text-anchor="middle" font-weight="bold">A · see detail below</text>')

# ---------- detail A, 3x ----------
S = PX * 3
DX, DY = 1170, y(DEEP) + 175          # top-left of the detail frame
def dxp(ft): return DX + (ft - cx0) * S
def dyp(ft): return DY + ft * S
a(f'<text x="{DX}" y="{DY-134}" font-size="20" font-weight="bold">Detail A · the east side, three times larger</text>')
a(f'<text x="{DX}" y="{DY-110}" font-size="15" font-style="italic">48 to 90 ft east of the center line, top 14 ft. Six pipes share a strip 26 ft wide.</text>')
a(f'<rect x="{DX}" y="{DY}" width="{(cx1-cx0)*S}" height="{cd1*S}" fill="url(#soil)" stroke="{INK}" stroke-width="1.5"/>')
a(f'<line x1="{DX}" y1="{DY}" x2="{dxp(cx1)}" y2="{DY}" stroke="{INK}" stroke-width="3"/>')
a(f'<rect x="{dxp(ROW-15)-4}" y="{DY-6}" width="8" height="6" fill="{INK}"/>')
a(f'<text x="{dxp(ROW-15)}" y="{DY-12}" font-size="13" text-anchor="middle">curb</text>')
# 3 ft cover line from the lab's rule
a(f'<line x1="{DX}" y1="{dyp(3)}" x2="{dxp(cx1)}" y2="{dyp(3)}" stroke="{WATER}" stroke-width="1" stroke-dasharray="2 4"/>'
  f'<text x="{DX+8}" y="{dyp(3)-6}" font-size="13" fill="{WATER}" font-style="italic">3 ft minimum cover</text>')
for k in ("st", "s2", "w3", "w4", "s3"):
    off, dep, dia, col, solid, t, n = P[k]
    s, r = pipe(dxp(off), dyp(dep), dia, col, solid, scale=S, minr=5, sw=3)
    a(s)
# labels: water above the frame; storm and sewers below, placed so no leader crosses a label
for k, anchor, dx in (("w3", "end", -8), ("w4", "start", 8)):
    off, dep = P[k][0], P[k][1]
    a(f'<path d="M{dxp(off)} {dyp(dep)-12} L{dxp(off)} {DY-70}" stroke="{INK}" stroke-width="0.9" fill="none"/>')
    a(label(dxp(off) + dx, DY - 64, k, anchor))
for k, row, anchor, dx in (("s2", 0, "start", 6), ("st", 1, "end", -6), ("s3", 1, "end", -6)):
    off, dep, dia = P[k][0], P[k][1], P[k][2]
    ly = dyp(cd1) + 36 + row * 50
    a(f'<path d="M{dxp(off)} {dyp(dep)+max(dia/24*S, 5)+3} L{dxp(off)} {ly+4}" stroke="{INK}" stroke-width="0.9" fill="none"/>')
    a(label(dxp(off) + dx, ly, k, anchor))

# ---------- notes, bottom left ----------
NX, NY = 60, y(DEEP) + 70
notes = [
    [f'<tspan font-weight="bold" fill="{GAS}">Gas.</tspan> PG&amp;E\'s 10–12 in. distribution main (198 psi; laid 1966 and 1983)',
     'crosses Shattuck about 12 m north of Allston, not at this section: see the plan.'],
    ['<tspan font-weight="bold">Electric, phone, cable:</tspan> underground here (Underground Utility',
     'District), routes not public; nor are low-pressure gas or private fiber.'],
    ['<tspan font-weight="bold">Solid</tspan> = position and depth from City or EBMUD records.',
     '<tspan font-weight="bold">Dashed</tspan> = position from records, depth assumed or schematic.'],
    ['<tspan font-weight="bold">Will it back up?</tspan> City branch drains are sized for a 10-year storm (2.03 in.',
     'in 6 hours); bigger storms are expected to pond and run down the street [1]. The',
     'City has not yet published a capacity model for downtown (Strawberry watershed):',
     'its 2011 plan modeled 2 of 10 watersheds, and the citywide model was still being',
     'calibrated in Aug 2025 [1, 2]. On 22 Dec 2025, 5 of the City\'s 36 storm-drain',
     'service requests came from this block\'s corners [3].'],
    ['<tspan font-weight="bold">The 36 in. sewer</tspan> is sized for rain that leaks into old sewers, not for sewage:',
     'a 2014 federal consent decree requires Berkeley, EBMUD and neighbors to cut those',
     'wet-weather flows by 2036 [4]. Its recorded inverts sit too close to the rims, so',
     'its depth here is an estimate.'],
]
yy = NY
for lines in notes:
    for i, line in enumerate(lines):
        a(f'<text x="{NX}" y="{yy}" font-size="16">{line}</text>'); yy += 22
    yy += 16
srcs = ['Data: EBMUD water mains; City of Berkeley sewers, storm drains and manholes (pulled 30 Aug 2026); Alameda County assessor parcels (Feb 2026).',
        '[1] City of Berkeley, Watershed Management Plan (Oct 2011, adopted 2012), ch. 6. [2] City of Berkeley, Stormwater Master Plan community meeting, 28 Aug 2025.',
        '[3] City of Berkeley open data, 311 Cases (p88g-6gs2), "Storm Drain Problem/Maintenance". [4] Berkeleyside, "Winter storms test East Bay\'s progress...", 3 May 2023.',
        'After CE 112, UC Berkeley, lab of 21 Oct 2022 (Carlton Chan, EBMUD): "design a new water distribution pipeline along Shattuck Ave from Center St to Allston St."']
for i, s_ in enumerate(srcs):
    a(f'<text x="{NX}" y="{H-104+i*21}" font-size="13" font-style="italic">{esc(s_)}</text>')
a('</svg>')
OUT.write_text("\n".join(o))
print("wrote", OUT)
