#!/usr/bin/env python3
"""svg_label_tour.py — boxed image labels that ride the camera, for ANY existing tour.

The dorm prototype needed BUILDING-IN/BUILDING-OUT comments emitted by gen_dorm_tour.py. That
does not generalise: the corridor tours are built by a different generator and regenerating a
published tour just to add comments is a needless risk. This finds the orbits itself, from the
camera track -- a run of legs whose heading sweeps through more than 270 degrees -- so it works
on any tour already on disk, including ones recorded from.

WHAT IT DOES, and why each part is there (all of it learned by John watching it):

  * ONE LABEL AT A TIME. gx:AnimatedUpdate switches visibility, so a label appears when its
    orbit begins and goes when it ends. Thirty labels floating at once was the original problem.
  * THE LABEL RIDES THE NEAR SIDE. Earth depth-tests icons against buildings, so a fixed anchor
    is swallowed as the camera closes. On every leg it moves to the camera's bearing from the
    centroid, at the footprint's circumradius plus a margin -- outside any shape, always facing
    the camera.
  * ON EVERY LEG, WITH THE LEG'S DURATION. Moving every 4th leg snapped; every leg is ~7.5
    degrees and Earth interpolates over the duration.
  * THE IMAGE IS CROPPED TO THE BOX. IconStyle scales the whole PNG, and a padded one spends
    most of the scale on nothing.

  python scripts/svg_label_tour.py --tour shattuck-s2n-path --street shattuck
"""
import argparse, math, os, pathlib, re, shutil, subprocess, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_building_loop import buildings as site_buildings
from stamp_geometry import geometry_sha


def site_rings(geom_path):
    """{ADDRESS: [(lon, lat), ...]} — every footprint vertex of a site, for reach-by-bearing."""
    import collections
    out = collections.defaultdict(list)
    g = open(geom_path, errors="replace").read()
    for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S):
        ad = re.search(r"<b>([^<]*)</b><br/>", pm)
        po = re.search(r"<Polygon>.*?<coordinates>\s*(.*?)\s*</coordinates>", pm, re.S)
        if not (ad and po):
            continue
        for tok in po.group(1).split():
            c = tok.split(",")
            if len(c) >= 2:
                out[ad.group(1).upper().strip()].append((float(c[0]), float(c[1])))
    return out


# SOFTNESS of the support function, in metres. The support function of a polygon,
# h(u) = max_i (r_i . u), is a max of sinusoids: continuous, but with a CORNER wherever the
# winning vertex changes. Those corners are what makes a swept label jerk -- 2700 Shattuck's
# h swings 24.5 to 68.2 m over a revolution with 4 vertex switches, 1750 Sacramento 54.2 to
# 108.0 m with 9. Replacing the hard max with a log-sum-exp soft max,
#
#     h_a(u) = (1/a) log SUM exp(a * r_i . u)
#
# gives a C-infinity function that converges to h as a grows. SOFT_M is 1/a expressed in metres:
# small = faithful and cornered, large = smooth and slightly outside the true hull.
SOFT_M = 3.0

# THE OTHER HALF OF THE JERK IS THE ANGLE, NOT THE MAGNITUDE. Softening h(u) smooths how FAR the
# label sits; it does nothing about the DIRECTION. When the camera passes near a building's
# centroid the bearing to it is ill-conditioned -- a small camera movement swings it wildly -- and
# the label teleports to the far side. Measured on Shattuck: mean step 8 m, worst step 60 m, which
# is the label crossing the whole building in one leg. The label's angular position is therefore a
# RATE-LIMITED FOLLOWER of the camera bearing: it turns toward the camera at no more than
# MAX_TURN_DEG per leg, so a flip becomes a swing and the step is bounded by radius * the limit.
MAX_TURN_DEG = 12.0
MAX_RISE_M = 6.0        # metres a label may climb or fall per leg
# THE RADIAL PUMP. The support function of an elongated footprint is not a circle, and 2700
# Shattuck's swings from 36 m to 77 m -- half-width to half-diagonal. Riding it exactly, the
# label breathed in and out FOUR times per orbit, once per corner (John, 2026-09-04: "2700 does
# stutter"). SOFT_M cannot fix this: it rounds corners over a 3 m scale and the swing is 41 m --
# the oscillation is the shape itself, not a corner artifact.
#
# The constraint is one-sided. The label must stay OUTSIDE the footprint or Earth depth-tests it
# away behind the building, so reach may only be smoothed UPWARD. Riding the circumradius is the
# fully-smoothed end of that and puts the box 71-79 m off a short face, which John rejected on
# 2026-09-02. A FLOOR is the middle: never closer than this fraction of the site's own maximum
# reach, so a long building's swing collapses to the top quarter of its range while a compact one
# -- where max and min are nearly equal anyway -- is untouched.
REACH_FLOOR_FRAC = 0.75
MAX_REACH_M = 3.0       # metres the reach may change per leg, after the floor


def reach(ring, lon, lat, ux, uy, soft=SOFT_M):
    """How far the footprint extends along unit vector (ux, uy), smoothed at the corners.

    Returns the SOFT support function of the vertex set. With soft=0 this is the exact support
    function -- the max over vertices -- which is what a hard-edged offset needs. With soft > 0
    the corners are rounded, which is what a MOVING label needs, because the corner is the jerk.
    """
    k = math.cos(math.radians(lat))
    ds = [((x - lon) * k * 111320.0) * ux + ((y - lat) * 111320.0) * uy for x, y in ring]
    if not ds:
        return 0.0
    if soft <= 0:
        return max(max(ds), 0.0)
    m = max(ds)
    # subtract the max before exponentiating -- otherwise exp overflows on a large footprint
    return max(m + soft * math.log(sum(math.exp((d - m) / soft) for d in ds)), 0.0)
from gen_svg_labels import slug as slugify, normkey
from xml.dom import minidom

GEOM = pathlib.Path("kml/geometry/geometry.kml")
IMGS = pathlib.Path("scratch/2026-08-31/svg-labels")   # overridable with --imgs
# AT THE ROOFLINE. The history of this number is the whole problem in miniature: roof + 34 m
# floated free of the building and left frame during orbits; 0.80 of roof sank into the mass and
# could land on Earth's "Image Landsat / Copernicus" strip; 0.86 still centred the box on the
# facade, which on 2530 Bancroft put it 5.9 m below a 42 m roofline and reading as pinned to the
# wall (John, 2026-09-02: "bring it up so we can see it"). At 1.0 the box straddles the roof
# edge -- upper half against sky, lower half against the building -- which is where a label
# belongs and is legible from a camera looking slightly down. It stays outside the mass because
# it rides the circumradius, so raising it costs no occlusion.
# TWO HEIGHTS, because the two situations are opposites (John, 2026-09-02).
#
# ORBITED: the camera is close and tilted slightly down, so the box wants its TOP just under the
# roofline -- "so we see it for most of an orbit". Anchored ORBIT_DROP metres below the roof.
#
# PASSED BY: the building is distant and off to the side, and a label below the roofline is read
# against the skyline behind it. Lifting it PASS_RISE metres clear of the roof puts it against
# sky, which is what makes it catch the eye at range -- John's "how can we see it as we pass by".
#
# Neither can be exact: the box is drawn at a fixed SCREEN size, so its height in metres depends
# on camera distance. These are tuned for the orbit radius, and are single numbers to change.
# NEVER FAR ABOVE THE CAMERA. A label at the roofline of a 98 m tower sits 70 m above a cruise
# camera flying at 25 m, so you have to look up to find it -- "for tall buildings, it is too hard
# to see the labels" (John, 2026-09-02). The height is therefore capped near the CAMERA'S OWN
# altitude: a short building still gets its roofline, because the cap is above it and does
# nothing, while a tower's label drops to just above the flight line where the eye already is.
# During an orbit the camera is at roof + 10, so the cap is above the roof and the orbit height
# is untouched.
# AIM AT WHERE THE CAMERA IS LOOKING, NOT AT THE BUILDING. Every height rule before this one was
# relative to the ROOF -- roof - 5, roof + 14, capped at camera + 12 -- and all of them ignored
# that the camera is TILTED. At tilt 74 the view axis falls 16 degrees below horizontal, so 84 m
# out the centre of frame is at 21 m altitude while the camera itself is at 45 m. Labels placed
# near the roof therefore sat +27 m above the middle of the picture: 2700 Shattuck clipped the
# top edge and 2274 was lit for its whole span and never visible at all (John, 2026-09-02).
#
# The label now goes on the VIEW AXIS at its own distance, lifted FRAME_LIFT metres so it rides
# slightly high in frame rather than dead centre over the street, and clamped to the building it
# names: never above the roof, never below FLOOR_M.
FRAME_LIFT = 9.0
FLOOR_M = 8.0
ABOVE_FLIGHT = 12.0      # retained only as an upper guard
ORBIT_DROP = 5.0
# AT THE ROOFLINE, NOT ABOVE IT. This was 14 m, on my reasoning that a distant label reads better
# against sky than against the city behind it. On screen that just looked like the box floating
# free of its building (John, 2026-09-02: "they are now floating 10m above each structure"), which
# is the same complaint that killed the original roof + 34 m anchor. Bancroft, the take he kept,
# sits every label exactly at the roofline -- so that is where they go.
PASS_RISE = 0.0
LIFT_FRACTION = 1.00     # fallback for the static placemark; the animation overrides it
                         # "Image Landsat / Copernicus" strip at the bottom of frame
# HUG THE NEAR FACE, DO NOT ORBIT THE WHOLE SITE. The label used to sit at the footprint's
# CIRCUMRADIUS plus a margin -- a circle wide enough to clear the site in every direction. That
# is correct for occlusion and badly wrong for large or long sites: 2700 Shattuck's label stood
# 79 m from its centre, out over the street, which reads as floating in the sky rather than
# sitting on the building (John, 2026-09-02). The offset is now measured ALONG THE CAMERA'S
# BEARING -- how far the footprint actually extends that way -- plus a small margin. A compact
# site barely moves; a big one gains its label back.
MARGIN_M = 8.0
# John has Earth's own Icon/Label Size on "large" and still reads the box as small at 2.5, so
# 3.2. The image itself is 1080 px wide; scale multiplies its on-screen size and Earth's
# preference multiplies again on top.
ICON_SCALE = 3.2


def orbits(tour):
    """Index spans of legs whose heading sweeps past 270 degrees — i.e. an orbit."""
    hd = [float(h) for h in re.findall(r"<heading>([-\d.]+)</heading>", tour)]
    spans, cur, tot = [], [0], 0.0
    for i in range(1, len(hd)):
        d = (hd[i] - hd[i - 1] + 540) % 360 - 180
        if 0.5 < abs(d) < 25:
            cur.append(i); tot += d
        else:
            if abs(tot) > 270:
                spans.append((cur[0], cur[-1]))
            cur, tot = [i], 0.0
    if abs(tot) > 270:
        spans.append((cur[0], cur[-1]))
    return spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", required=True, help="tour stem in kml/tours/")
    ap.add_argument("--street", default=None, help="street-label set to fold in, e.g. shattuck")
    ap.add_argument("--out", default=None)
    ap.add_argument("--tag", default="",
                    help="suffix for the package filename AND the Movie Maker tour name. Two "
                         "builds of one route otherwise carry identical tour names and appear as "
                         "two indistinguishable rows in Movie Maker's list.")
    ap.add_argument("--imgs", default=None,
                    help="label PNG directory; use a separate one to compare renderers")
    ap.add_argument("--label-args", default="",
                    help="extra args passed straight to gen_svg_labels.py, e.g. "
                         "\'--raster cairosvg --panel-opacity 1.0\'")
    ap.add_argument("--all", action="store_true",
                    help="label EVERY building the flight passes, not only the orbit targets. A "
                         "label appears when the camera comes within --radius of its building and "
                         "goes when it leaves, so the screen still carries only what is at hand.")
    ap.add_argument("--radius", type=float, default=260.0,
                    help="metres: how close the camera must come before a label is lit")
    ap.add_argument("--max-labels", type=int, default=0,
                    help="cap how many labels may be lit at once; the NEAREST win. 0 = no cap. "
                         "Radius alone is not enough downtown, where 260 m can enclose fifteen "
                         "projects and the screen fills with boxes -- the very problem the "
                         "one-at-a-time rule was meant to solve.")
    ap.add_argument("--orbit-focus", type=int, default=1,
                    help="labels lit DURING an orbit. 1 = only the building being orbited. On a "
                         "dense corridor the nearest-five set stays saturated through an orbit, so "
                         "the subject is one box among five identical ones and does not read as "
                         "the subject at all (John on Bancroft, 2026-09-01).")
    ap.add_argument("--hysteresis", type=float, default=1.35,
                    help="a lit label stays lit until the camera is this multiple of --radius "
                         "away. Without it, a building sitting near the boundary switches on and "
                         "off leg after leg -- Bancroft toggled 0.40 times per leg against "
                         "University's 0.27, which is the flicker John saw as randomness.")
    ap.add_argument("--move-every", type=int, default=2,
                    help="reposition a visible label every Nth leg. 1 is smoothest; 2 halves the "
                         "file for no visible difference outside an orbit.")
    a = ap.parse_args()
    global IMGS
    if a.imgs:
        IMGS = pathlib.Path(a.imgs)

    tour_path = pathlib.Path(f"kml/tours/{a.tour}.kml")
    tour = re.search(r"<gx:Tour>.*?</gx:Tour>", tour_path.read_text(errors="replace"), re.S).group(0)
    g = GEOM.read_text(errors="replace")
    SITES = site_buildings()
    RINGS = site_rings(str(GEOM))

    legs = re.findall(r"<gx:FlyTo>.*?</gx:FlyTo>\n?", tour, re.S)
    headings = [float(re.search(r"<heading>([-\d.]+)</heading>", l).group(1))
                if re.search(r"<heading>([-\d.]+)</heading>", l) else 0.0 for l in legs]
    cams = [(float(m.group(1)), float(m.group(2))) for m in
            (re.search(r"<longitude>([-\d.]+)</longitude>\s*<latitude>([-\d.]+)</latitude>", l) for l in legs)]
    # PREFER EXPLICIT MARKERS. gen_dorm_tour.py brackets each building with BUILDING-IN/OUT
    # comments. Heading-sweep detection is a fallback for tours that have none -- and on the dorm
    # tour it fails outright, merging all four orbits into one because the turns BETWEEN
    # buildings are gentle enough to look like more of the same sweep.
    marks = re.findall(r"<!--BUILDING-(IN|OUT) ([a-z0-9-]+)-->", tour)
    if marks:
        legs_seen, spans, open_at = 0, [], {}
        for tok in re.split(r"(<gx:FlyTo>.*?</gx:FlyTo>|<!--BUILDING-(?:IN|OUT) [a-z0-9-]+-->)",
                            tour, flags=re.S):
            if tok.startswith("<!--BUILDING-IN"):
                open_at[re.search(r"IN ([a-z0-9-]+)", tok).group(1)] = legs_seen
            elif tok.startswith("<!--BUILDING-OUT"):
                nm = re.search(r"OUT ([a-z0-9-]+)", tok).group(1)
                if nm in open_at:
                    spans.append((open_at.pop(nm), max(legs_seen - 1, 0)))
            elif tok.startswith("<gx:FlyTo>"):
                legs_seen += 1
        print(f"  using {len(spans)} BUILDING marker span(s) from the tour")
        # THE MARKER NAMES THE BUILDING -- USE IT. Matching a span to the nearest site by camera
        # centroid is right for a FULL orbit, where the mean camera position is the building's
        # centre. gen_hop_tour flies a QUARTER turn, whose mean sits about a radius off to one
        # side and lands on a neighbour: the private-200 tour lit 2036 Bancroft, 2037 Durant and
        # 130 Berkeley Sq, none of which is among its fifteen subjects. The label then rode a
        # building the camera was not looking at, which is why John saw labels appear and vanish.
        span_slug = {}
        for (lo, hi), (_, nm) in zip(spans, [m for m in marks if m[0] == "IN"]):
            span_slug[(lo, hi)] = nm
    else:
        spans = orbits(tour)
        span_slug = {}
    orbit_of = {}
    print(f"  {len(legs)} legs, {len(spans)} orbit(s) detected")

    # which site is each orbit about?
    targets = []
    for lo, hi in spans:
        want = span_slug.get((lo, hi))
        if want:
            hit = [(k, v) for k, v in SITES.items() if slugify(k) == want]
            if hit:
                targets.append((lo, hi, hit[0][0], hit[0][1]))
                print(f"    legs {lo:>3}-{hi:<3} -> {hit[0][1][4].splitlines()[0][:46]}  (from marker)")
                continue
        seg = cams[lo:hi + 1]
        clon = sum(p[0] for p in seg) / len(seg); clat = sum(p[1] for p in seg) / len(seg)
        addr, v = min(SITES.items(), key=lambda kv: (kv[1][0] - clon) ** 2 + (kv[1][1] - clat) ** 2)
        targets.append((lo, hi, addr, v))
        print(f"    legs {lo:>3}-{hi:<3} -> {v[4].splitlines()[0][:46]}  (nearest)")

    # WHICH SPANS ARE A SUBJECT. This MUST be computed before the --all branch below, which
    # replaces targets with proximity entries carrying (None, None). It used to be computed
    # after, from the replaced list, so in --all mode orbit_of came out EMPTY: being_orbited was
    # false for every building including the one being orbited, so the subject moved on the
    # every-other-leg cadence meant for distant pass-bys and stuttered through its own orbit
    # (John, 2026-09-04: "2190 flutters"), and --orbit-focus never fired because here_orbit was
    # always None. The comment on the --all branch claimed the spans were "retained and used for
    # cadence below" -- they were retained in spans, but nothing read them.
    orbit_of = {addr: (lo, hi) for lo, hi, addr, _ in targets if lo is not None}

    # --- ALL MODE: every site the flight actually passes, lit by proximity ---
    if a.all:
        near = {}
        for addr, v in SITES.items():
            if not re.search(r"\d", v[4]):
                continue
            k = math.cos(math.radians(v[1]))
            dmin = min(math.hypot((c[0] - v[0]) * k * 111320, (c[1] - v[1]) * 111320) for c in cams)
            if dmin <= a.radius:
                near[addr] = v
        print(f"    {len(near)} building(s) come within {a.radius:.0f} m of this flight")
        # KEEP THE ORBIT SPANS. --all used to replace targets outright, which threw away which
        # legs are an orbit -- so the building being orbited moved on the same every-other-leg
        # cadence as everything else and visibly stuttered, while orbits-only stayed smooth.
        # John caught exactly that. The spans are retained and used for cadence below.
        targets = [(None, None, addr, v) for addr, v in near.items()]

    # WHICH SPANS ARE A SUBJECT — needed in EVERY mode, not just --all. This lived inside the
    # --all branch, so a tour built without it (private-200, whose fifteen subjects come from
    # BUILDING markers) had an empty orbit_of: being_orbited was always False, every subject got
    # the PASS-BY height of roof + 0, and the box centred on the roofline with half of it against
    # the sky. John: "the labels are floating above the building again, not on the face."
    # (built ABOVE, before --all replaces targets -- see there for why)

    # render just those labels
    IMGS.mkdir(parents=True, exist_ok=True)
    # ONE subprocess, not one per label. Each invocation pays Python startup and a full read of
    # v2 -- about 1.3 s -- so 58 labels cost 80 s of process churn and almost no rasterising.
    cmd = [sys.executable, "scripts/gen_svg_labels.py", "--outdir", str(IMGS)]
    cmd += a.label_args.split()
    for _, _, addr, _ in targets:
        cmd += ["--address", addr]
    subprocess.run(cmd, capture_output=True)

    # Index what was actually rendered, by normalised key, so a geometry name that differs
    # cosmetically from v2's address_display still finds its label instead of being skipped.
    by_norm = {}
    for f in IMGS.glob("*.png"):
        by_norm.setdefault(normkey(f.stem.replace("-", " ")), f)

    styles, pms, imgs = [], [], []
    for lo, hi, addr, v in targets:
        s = slugify(addr); png = IMGS / f"{s}.png"
        if not png.exists():
            alt = by_norm.get(normkey(addr))
            if alt is None:
                print(f"    no image for {s} — skipped"); continue
            print(f"    {s} -> {alt.stem} (matched on normalised address)")
            png = alt
        imgs.append(png)
        styles.append(f'<Style id="lbl_{s}"><IconStyle><scale>{ICON_SCALE}</scale>'
                      f'<Icon><href>{png.name}</href></Icon>'
                      f'<hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/></IconStyle>'
                      f'<LabelStyle><scale>0</scale></LabelStyle></Style>')
        pms.append(f'<Placemark id="pm_{s}"><name></name><visibility>0</visibility>'
                   f'<styleUrl>#lbl_{s}</styleUrl><Point>'
                   f'<coordinates>{v[0]!r},{v[1]!r},{v[2] * LIFT_FRACTION:.1f}</coordinates>'
                   f'<altitudeMode>relativeToGround</altitudeMode></Point></Placemark>')

    def vis(s, v, secs=0.0):
        return (f'\t\t\t<gx:AnimatedUpdate><gx:duration>{secs:.2f}</gx:duration><Update><targetHref/>'
                f'<Change><Placemark targetId="pm_{s}"><visibility>{v}</visibility></Placemark>'
                f'</Change></Update></gx:AnimatedUpdate>\n')

    def move(s, lon, lat, alt, secs):
        return (f'\t\t\t<gx:AnimatedUpdate><gx:duration>{secs:.2f}</gx:duration><Update><targetHref/>'
                f'<Change><Placemark targetId="pm_{s}"><Point>'
                f'<coordinates>{lon:.8f},{lat:.8f},{alt:.1f}</coordinates>'
                f'<altitudeMode>relativeToGround</altitudeMode></Point></Placemark>'
                f'</Change></Update></gx:AnimatedUpdate>\n')

    # A SHORT ARC DOES NOT NEED A MOVING LABEL. Sweeping the label round the building every leg
    # is right for a full orbit, where the camera sees every face. On gen_hop_tour's QUARTER turn
    # the camera only ever sees one side, so moving the label just drags it across sloping ground
    # -- and altitudes are relativeToGround, so the label bobs -- and can swing it out of frame
    # entirely (John, 2026-09-02: "2920 jumps up and down, 2700 is missing"). For any span
    # sweeping less than STILL_BELOW degrees the label is placed ONCE, on the bearing the camera
    # holds at the middle of the arc, and left there.
    STILL_BELOW = 150.0
    sweep = {}
    for lo, hi, addr, v in targets:
        if lo is None:            # --all mode: proximity targets carry no span
            continue
        hs = [h for h in headings[lo:hi + 1]]
        tot = 0.0
        for i in range(1, len(hs)):
            tot += abs((hs[i] - hs[i - 1] + 540) % 360 - 180)
        sweep[(lo, hi)] = tot
    still = {k for k, t in sweep.items() if t < STILL_BELOW}
    if still:
        print(f"    {len(still)} span(s) sweep < {STILL_BELOW:.0f} deg — label placed once, not swept")

    # THE LEG OF CLOSEST APPROACH, per building. A pass-by is not an orbit: the camera only ever
    # sees one side of it, so sweeping the label round the footprint every other leg just drags it
    # across the face and, on the way past, round toward the back -- John, 2026-09-04: "2947 moves
    # right, away from the flight path". Aim it once, from where the camera will be at its
    # nearest, and leave it. The still rule already existed for short spans but could never apply
    # here, because --all targets carry no span at all.
    # Each site's own maximum reach, sampled round the compass once, for the floor above.
    maxreach = {}
    for _, _, addr, v in targets:
        ring = RINGS.get(addr.upper().strip())
        if ring:
            maxreach[addr] = max(reach(ring, v[0], v[1], math.sin(math.radians(t)),
                                       math.cos(math.radians(t))) for t in range(0, 360, 5))
        else:
            maxreach[addr] = v[3]

    closest = {}
    for _, _, addr, v in targets:
        kk = math.cos(math.radians(v[1]))
        closest[addr] = min(range(len(cams)),
                            key=lambda i: ((cams[i][0] - v[0]) * kk) ** 2 + (cams[i][1] - v[1]) ** 2)

    # rebuild the playlist leg by leg
    lastalt = {}          # last altitude used per label, for the vertical rate limit
    lastreach = {}        # last reach used per label, for the radial rate limit
    just_lit = set()      # labels switched on THIS leg -- they must be placed on it
    live = set()          # which labels are currently lit (all-mode)
    bear = {}             # last bearing actually used per label, for rate limiting
    out, li, moves = [], 0, 0
    for tok in re.split(r"(<gx:FlyTo>.*?</gx:FlyTo>\n?)", tour, flags=re.S):
        if not tok.startswith("<gx:FlyTo>"):
            out.append(tok); continue
        if a.all:
            # PROXIMITY, NOT SPANS. Light a label when the camera comes inside --radius of its
            # building and drop it when it leaves, so a corridor shows what is beside it rather
            # than every project in the city at once.
            # inside an orbit, the subject owns the screen
            here_orbit = next((ad for ad, (lo2, hi2) in orbit_of.items() if lo2 <= li <= hi2), None)
            if a.orbit_focus and here_orbit:
                want = {here_orbit}
            else:
                cand = []
                for _, _, addr, v in targets:
                    k = math.cos(math.radians(v[1]))
                    dm = math.hypot((cams[li][0] - v[0]) * k * 111320,
                                    (cams[li][1] - v[1]) * 111320)
                    # HYSTERESIS: a label already lit holds until well past the radius, so a
                    # building hovering at the boundary cannot flicker on and off each leg.
                    limit = a.radius * (a.hysteresis if addr in live else 1.0)
                    if dm <= limit:
                        cand.append((dm, addr))
                cand.sort()
                if a.max_labels:
                    cand = cand[:a.max_labels]
                want = {addr for _, addr in cand}
            just_lit = want - live
            for addr in just_lit:
                out.append(vis(slugify(addr), 1))
            for addr in live - want:
                out.append(vis(slugify(addr), 0))
                bear.pop(addr, None)
                lastalt.pop(addr, None)
                lastreach.pop(addr, None)
            live = want
        for lo, hi, addr, v in targets:
            if lo is not None and li == lo:
                out.append(vis(slugify(addr), 1))
        # position the label on the camera's side for this leg
        for lo, hi, addr, v in targets:
            # A STILL LABEL IS PLACED AT THE START OF ITS SPAN, AIMED FROM THE MIDDLE. Writing
            # it at the middle leg left it at the placemark's initial position -- the building's
            # own CENTROID, i.e. inside the building -- for the whole first half of its span.
            # 2700 Shattuck lit at leg 15, was not placed until leg 22 and went dark at 30: it
            # spent half its life buried and then appeared briefly (John, 2026-09-02: "very late
            # to appear ... vanishes quickly").
            in_span = (lo is not None and lo <= li <= hi
                       and ((lo, hi) not in still or li == lo))
            # THE BUILDING BEING ORBITED MOVES EVERY LEG. It is the subject of the shot and the
            # camera sweeps fastest around it, so half-rate updates read as a stutter. Everything
            # else -- passed at a distance, drifting slowly across frame -- is fine at half rate,
            # which is what keeps the file small.
            olo, ohi = orbit_of.get(addr, (None, None))
            being_orbited = olo is not None and olo <= li <= ohi
            # A LABEL MUST BE PLACED ON THE LEG IT LIGHTS. The static placemark sits at the
            # centroid at LIFT_FRACTION x roof -- inside the building, at roof height -- and is
            # only ever meant as a fallback the animation overrides. But a label lit on an odd
            # leg was not moved until the next even one, so it showed at that fallback first.
            # 2420 Shattuck (roof 59.5 m) is lit for so few legs that the fallback was most of
            # what John saw: "2420 is too high to see".
            #
            # A PASS-BY IS PLACED ONCE. Only the orbit subject is swept; everything else is
            # aimed from closest approach and left, so it cannot crawl round the footprint.
            pass_by = a.all and addr in live and not being_orbited
            in_near = (a.all and addr in live
                       and (addr in just_lit
                            or (being_orbited and True)
                            or (not pass_by and li % max(a.move_every, 1) == 0)))
            if in_span or in_near:
                blon, blat, roof, rad = v[0], v[1], v[2], v[3]
                # for a still label, aim from the MIDDLE of the arc so one placement serves the
                # whole span; for a swept one, from this leg
                if pass_by:
                    aim = closest.get(addr, li)
                elif lo is not None and (lo, hi) in still:
                    aim = (lo + hi) // 2
                else:
                    aim = li
                clon, clat = cams[min(aim, len(cams) - 1)]
                k = math.cos(math.radians(blat))
                dx, dy = (clon - blon) * k, clat - blat
                d = math.hypot(dx, dy) or 1e-9
                # rate-limit the bearing, then measure the reach along the bearing we will use
                want = math.degrees(math.atan2(dx, dy)) % 360.0
                prev = bear.get(addr)
                if prev is None:
                    use = want
                else:
                    delta = (want - prev + 540.0) % 360.0 - 180.0
                    use = (prev + max(-MAX_TURN_DEG, min(MAX_TURN_DEG, delta))) % 360.0
                bear[addr] = use
                ux, uy = math.sin(math.radians(use)), math.cos(math.radians(use))
                ring = RINGS.get(addr.upper().strip())
                out_m = (reach(ring, blon, blat, ux, uy) if ring else rad) + MARGIN_M
                out_m = max(out_m, REACH_FLOOR_FRAC * maxreach.get(addr, rad))
                prev_r = lastreach.get(addr)
                if prev_r is not None:
                    out_m = max(prev_r - MAX_REACH_M, min(prev_r + MAX_REACH_M, out_m))
                lastreach[addr] = out_m
                r = out_m / 111320.0
                dx, dy, d = ux, uy, 1.0
                dur = re.search(r"<gx:duration>([0-9.]+)</gx:duration>", tok)
                ca = re.search(r"<altitude>([-\d.]+)</altitude>", tok)
                ct = re.search(r"<tilt>([-\d.]+)</tilt>", tok)
                alt = (roof - ORBIT_DROP) if being_orbited else (roof + PASS_RISE)
                if ca and ct:
                    cam_alt = float(ca.group(1)); tilt = float(ct.group(1))
                    # horizontal distance from the camera to where the label will stand
                    lx = blon + ux * r / k; ly = blat + uy * r
                    dcam = math.hypot((lx - cams[aim][0]) * k * 111320.0,
                                      (ly - cams[aim][1]) * 111320.0)
                    axis = cam_alt - dcam * math.tan(math.radians(max(0.0, 90.0 - tilt)))
                    alt = min(max(axis + FRAME_LIFT, FLOOR_M), roof, cam_alt + ABOVE_FLIGHT)
                # RATE-LIMIT THE CLIMB, exactly as the bearing is rate-limited. The view axis
                # moves fast when tilt and camera altitude change together, and the roof cap
                # binds and releases between legs, so the height could jump the tower's whole
                # facade in a single leg: 2190 Shattuck ranged 29.5 m to 110.0 m -- 110.0 being
                # its roof exactly -- which is the vertical half of "2190 flutters". A label may
                # climb or fall MAX_RISE_M per leg and no more; it still tracks the axis, just
                # not instantly.
                prev_alt = lastalt.get(addr)
                if prev_alt is not None:
                    alt = max(prev_alt - MAX_RISE_M, min(prev_alt + MAX_RISE_M, alt))
                lastalt[addr] = alt
                out.append(move(slugify(addr), blon + dx / d * r / k, blat + dy / d * r,
                                max(alt, 8.0), float(dur.group(1)) if dur else 0.0))
                moves += 1
        out.append(tok)
        for lo, hi, addr, v in targets:
            if lo is not None and li == hi:
                out.append(vis(slugify(addr), 0))
        li += 1
    tour = "".join(out)

    # geometry: polygons only, every floating text label dropped
    kept = [re.sub(r"<name>[^<]*</name>", "<name></name>", pm, count=1)
            for pm in re.findall(r"<Placemark>.*?</Placemark>", g, re.S) if "<Polygon>" in pm]
    geom_styles = "".join(re.findall(r"<Style id=\"[^\"]*\">.*?</Style>|<StyleMap id=\"[^\"]*\">.*?</StyleMap>", g, re.S))

    # fold in the amber street signs so it is one file to load
    street = ""
    if a.street:
        sp = pathlib.Path(f"kml/tours/labels/{a.street}-street-labels.kml")
        if sp.exists():
            st = sp.read_text(errors="replace")
            street = ("".join(re.findall(r"<Style id=\"[^\"]*\">.*?</Style>", st, re.S))
                      + "".join(re.findall(r"<Placemark>.*?</Placemark>", st, re.S)))
            imgs.append(pathlib.Path("kml/tours/labels/transparent-1x1.png"))
            print(f"    folded in {a.street} street signs")

    # NAME THE TOUR FOR MOVIE MAKER'S LIST, NOT FOR US. Movie Maker shows saved tours by their
    # <gx:Tour><name>, and the unlabelled package of the same route carries an IDENTICAL name --
    # two indistinguishable rows, no way to know which one has labels (John, 2026-09-04). Mark
    # the labelled build in the name itself, with the label count, which is the thing that
    # differs. Nothing here changes what Movie Maker can FIND: it lists what is loaded in Places
    # and has no notion of a directory. The package path is for the file picker and the catalog.
    tourname = re.search(r"(<gx:Tour>.{0,300}?<name>)([^<]*)(</name>)", tour, re.S)
    if tourname:
        stem = tourname.group(2).split(" · ")[0]
        mark = f"{stem} · LABELLED · {len(pms)} buildings" + (f" · {a.tag}" if a.tag else "")
        tour = tour[:tourname.start(2)] + mark + tour[tourname.end(2):]

    sha = geometry_sha()
    doc = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">\n'
           f'<Document>\n\t<name>{a.tour} · LABELLED · geom-{sha}</name>\n'
           + geom_styles + "".join(styles) + "\n" + tour + "\n"
           + "".join(kept) + "".join(pms) + street + "\n</Document>\n</kml>\n")
    minidom.parseString(doc)

    # WRITE THE PACKAGE DIRECTLY. This used to land in scratch/ plus a Desktop copy, and every
    # build then had to be hand-placed into kml/tours/packages/ under the __geom-<sha> convention
    # -- a manual step that is easy to skip and impossible to notice having skipped, which is the
    # same class of bug as the unpromoted explorer data. The sha comes from the SHARED
    # geometry_sha(), so a package built here is named exactly as build_tour_package.py names its
    # own and a stale one is visible by its name alone.
    out_path = pathlib.Path(
        a.out or f"kml/tours/packages/{a.tour}-labelled{'-' + a.tag if a.tag else ''}__geom-{sha}.kmz")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    EPOCH = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("doc.kml", EPOCH); zi.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(zi, doc)
        for p in dict.fromkeys(imgs):
            if p.exists():
                zi2 = zipfile.ZipInfo(p.name, EPOCH); zi2.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(zi2, p.read_bytes())
    print(f"  {len(kept)} polygons, {len(pms)} boxed labels, {moves} repositions")
    print(f"  {out_path} ({out_path.stat().st_size/1024:.0f} KB)")
    print(f'  tour name in Movie Maker: "{mark if tourname else "(unnamed)"}"')
    print(f"  LOAD IT to record -- Movie Maker lists what is in Places, not what is on disk:")
    print(f"    open {out_path}")


if __name__ == "__main__":
    main()
