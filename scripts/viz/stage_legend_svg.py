#!/usr/bin/env python3
"""stage_legend_svg.py — render the stage-colour legend as a self-contained animated SVG.

WHY THIS EXISTS. The legend was prose, repeated verbatim under all nine flyovers: a wall of
words asking the reader to hold seven colours in their head while a video plays. A picture is
the right shape for "these colours mean these stages, in this order". This draws it.

DERIVED, NEVER TYPED. Every colour, phrase, stage and count arrives from update_legend.census()
-- the same read of kml/geometry/geometry.kml that writes the prose. Nothing here knows a number.
A stage with no buildings on the map is omitted (the prose does this too); a stage that comes
back next week reappears on the next run without anyone editing an SVG by hand.

ONE THING IT SAYS THAT THE PROSE COULD NOT. The prose lists withdrawn alongside completed, as if
dark red were the seventh step of a six-step walk. It is not a stage, it is an exit. Here the
flow chips sit on the rail and the exits sit off it, past a gap, which is what the data means.

SELF-CONTAINED. No script, no external CSS, no webfont: it animates inside a plain <img> tag and
honours prefers-reduced-motion. Two layouts (wide rail, narrow stack) so the text stays legible
on a phone -- the page picks between them with <picture>.
"""
import re

M = 24                      # page margin inside the viewBox
FLOW = ["Pre-Application", "In Review", "Entitled",
        "Permitted", "Under Construction", "Completed"]
EXIT = ["Stalled", "Withdrawn"]
PAPER = {"Pre-Application", "In Review", "Entitled"}


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def wrap(text, width_px, px_per_char):
    """Greedy wrap on an estimated advance width. Good enough for short label phrases."""
    limit = max(1, int(width_px / px_per_char))
    lines, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if len(trial) > limit and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def gloss_phrase(name, phrase):
    """Drop a phrase's restatement of the chip's own name when a parenthetical follows it.

    The prose needs "entitled (approved, no building permit yet)" because it runs the colours
    together in one sentence with no headings. Here the chip is already labelled Entitled, so
    the first word is dead weight -- and it is the word that pushes that chip to four lines
    and makes the whole legend taller. Only fires on a parenthetical, so "completed and
    occupiable" keeps its "completed" and does not decay into "and occupiable".
    """
    low, nm = phrase.lower(), name.lower()
    if low.startswith(nm):
        rest = phrase[len(name):].strip()
        if rest.startswith("("):
            return rest.strip("()")
    return phrase


def _present(gloss, stage, agency):
    """(flow chips, exit chips, agency chips) -- each an ordered list of (name, hex, phrase, n)."""
    by = {g[0]: g for g in gloss}
    flow, exits, ag = [], [], []
    for name in FLOW:
        if stage.get(name):
            _, h, _w, phrase = by[name]
            flow.append((name, h, phrase, stage[name]))
    for name in EXIT:
        if stage.get(name):
            _, h, _w, phrase = by[name]
            exits.append((name, h, phrase, stage[name]))
    for name, h, _w, phrase in gloss:
        if name.endswith("Project") and agency.get(name):
            ag.append((name, h, phrase, agency[name]))
    return flow, exits, ag


CSS = """
    text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
    .ttl  {{ font-size: 13px; font-weight: 700; fill: #1a365d; letter-spacing: .06em; }}
    .meta {{ font-size: 11px; fill: #718096; }}
    .name {{ font-size: 12px; font-weight: 700; fill: #2d3748; }}
    .desc {{ font-size: 10.5px; fill: #5a6779; }}
    .cnt  {{ font-size: 17px; font-weight: 700; }}
    .band {{ font-size: 9px; font-weight: 700; fill: #a9b3c0; letter-spacing: .1em; }}
    .rail {{ stroke: #d6dde6; stroke-width: 2; fill: none; }}
    .dot  {{ animation: {travel} 9s ease-in-out infinite; }}
    @keyframes rideX {{ {kx} }}
    @keyframes rideY {{ {ky} }}
    @media (prefers-reduced-motion: reduce) {{ .dot {{ animation: none; }} }}
"""


def _keyframes(stops, axis):
    """Pause-at-each-stop keyframes: the marker dwells on a chip, then slides to the next."""
    if len(stops) < 2:
        return f"from {{ transform: translate{axis}({stops[0] if stops else 0}px); }}"
    out, n = [], len(stops)
    seg = 100.0 / (n - 1)
    for i, s in enumerate(stops):
        arrive = i * seg
        out.append(f"{arrive:.2f}% {{ transform: translate{axis}({s:.1f}px); }}")
        if i < n - 1:                      # hold, then move
            out.append(f"{arrive + seg * .55:.2f}% {{ transform: translate{axis}({s:.1f}px); }}")
    return " ".join(out)


def _swatch(x, y, hexcolor, ring=None):
    if ring:
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="{hexcolor}" '
                f'stroke="{ring}" stroke-width="4"/>')
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="{hexcolor}" '
            f'stroke="#ffffff" stroke-width="3"/>')


def wide(gloss, stage, agency, total_label):
    W = 960
    flow, exits, ag = _present(gloss, stage, agency)
    slots = len(flow) + (1.2 + len(exits) if exits else 0)
    col = (W - 2 * M) / slots
    xs = [M + col * (i + .5) for i in range(len(flow))]
    ex = [M + col * (len(flow) + 1.2 + i) for i in range(len(exits))]

    rail_y = 86
    y_cnt, y_name, y_desc = rail_y + 36, rail_y + 54, rail_y + 68

    body, maxline = [], 0
    for (name, hexc, phrase, n), x in zip(flow + exits, xs + ex):
        lines = wrap(gloss_phrase(name, phrase), col - 10, 5.4)
        maxline = max(maxline, len(lines))
        t = [f'<text class="cnt" x="{x:.1f}" y="{y_cnt}" text-anchor="middle" '
             f'fill="{hexc}">{n}</text>',
             f'<text class="name" x="{x:.1f}" y="{y_name}" text-anchor="middle">'
             f'{esc(name)}</text>']
        for j, ln in enumerate(lines):
            t.append(f'<text class="desc" x="{x:.1f}" y="{y_desc + j * 12}" '
                     f'text-anchor="middle">{esc(ln)}</text>')
        body.append(f'<g>{_swatch(x, rail_y, hexc)}{"".join(t)}</g>')

    H = y_desc + maxline * 12 + (50 if ag else 14)

    rail = (f'<path class="rail" d="M{xs[0]:.1f} {rail_y} H{xs[-1]:.1f}"/>' if len(xs) > 1 else "")

    div = ""
    cool = [i for i, (nm, *_r) in enumerate(flow) if nm not in PAPER]
    if cool and cool[0] > 0:
        bx = (xs[cool[0] - 1] + xs[cool[0]]) / 2
        div = (f'<path d="M{bx:.1f} {rail_y - 22} V{rail_y + 22}" stroke="#e2e8f0" '
               f'stroke-width="1" stroke-dasharray="3 3"/>'
               f'<text class="band" x="{bx - 10:.1f}" y="{rail_y - 28}" text-anchor="end">'
               f'ON PAPER</text>'
               f'<text class="band" x="{bx + 10:.1f}" y="{rail_y - 28}">PHYSICAL</text>')
    if exits:
        for x in ex:
            div += (f'<text class="band" x="{x:.1f}" y="{rail_y - 28}" text-anchor="middle">'
                    f'LEFT THE PIPELINE</text>')

    agrow = ""
    if ag:
        y = H - 18
        lead = "A thick outline marks a project permitted by its own agency, not by the City:"
        parts = [f'<text class="meta" x="{M}" y="{y + 4}">{esc(lead)}</text>']
        ax = M + len(lead) * 5.55 + 18          # measured off the lead, not a magic constant
        for name, hexc, phrase, n in ag:
            label = f"{phrase} ({n})"
            parts.append(f'<circle cx="{ax + 8}" cy="{y}" r="7" fill="#ffffff" stroke="{hexc}" '
                         f'stroke-width="4"/>')
            parts.append(f'<text class="meta" x="{ax + 21}" y="{y + 4}">{esc(label)}</text>')
            ax += 21 + len(label) * 5.55 + 22
        agrow = "".join(parts)

    css = CSS.format(travel="rideX", kx=_keyframes(xs, "X"), ky="from{}")
    dot = (f'<g class="dot"><circle cx="0" cy="{rail_y}" r="4.5" fill="#1a365d" '
           f'opacity=".85"/></g>' if len(xs) > 1 else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" '
            f'width="{W}" height="{H:.0f}" role="img" aria-labelledby="t d">'
            f'<title id="t">What the colours on the flyovers mean</title>'
            f'<desc id="d">{esc(total_label)}</desc>'
            f'<style>{css}</style>'
            f'<rect width="{W}" height="{H:.0f}" fill="#ffffff"/>'
            f'<text class="ttl" x="{M}" y="26">WHERE EACH PROJECT STANDS</text>'
            f'<text class="meta" x="{W - M}" y="26" text-anchor="end">{esc(total_label)}</text>'
            f'{rail}{div}{dot}{"".join(body)}{agrow}</svg>')


def narrow(gloss, stage, agency, total_label):
    W = 380
    flow, exits, ag = _present(gloss, stage, agency)
    x_rail, x_txt = M + 14, M + 40
    y0, rows, ys = 62, [], []
    y = y0
    for i, (name, hexc, phrase, n) in enumerate(flow + exits):
        lines = wrap(gloss_phrase(name, phrase), W - x_txt - M - 26, 5.0)
        ys.append(y if i < len(flow) else None)
        r = [f'<text class="name" x="{x_txt}" y="{y + 1}">{esc(name)}</text>',
             f'<text class="cnt" x="{W - M}" y="{y + 1}" text-anchor="end">{n}</text>']
        for j, ln in enumerate(lines):
            r.append(f'<text class="desc" x="{x_txt}" y="{y + 15 + j * 12}">{esc(ln)}</text>')
        rows.append(f'<g>{_swatch(x_rail, y - 4, hexc)}{"".join(r)}</g>')
        y += 20 + len(lines) * 12 + 14
        if i == len(flow) - 1 and exits:
            rows.append(f'<text class="band" x="{x_txt}" y="{y - 2}" fill="#b9c2cd">'
                        f'LEFT THE PIPELINE</text>')
            y += 20
    H = y + (40 if ag else 4)

    stops = [v - 4 for v in ys if v is not None]
    rail = (f'<path class="rail" d="M{x_rail} {stops[0]} V{stops[-1]}"/>' if len(stops) > 1 else "")
    dot = (f'<g class="dot"><circle cx="{x_rail}" cy="0" r="4.5" fill="#1a365d" opacity=".85"/></g>'
           if len(stops) > 1 else "")

    agrow = ""
    if ag:
        yy = H - 22
        parts = [f'<text class="meta" x="{M}" y="{yy}">Thick outline = permitted by its own '
                 f'agency:</text>']
        yy += 15
        ax = M
        for name, hexc, phrase, n in ag:
            parts.append(f'<circle cx="{ax + 7}" cy="{yy - 4}" r="6" fill="#ffffff" '
                         f'stroke="{hexc}" stroke-width="3.5"/>')
            parts.append(f'<text class="meta" x="{ax + 19}" y="{yy}">{esc(phrase)}</text>')
            ax += 30 + len(phrase) * 5.9
        agrow = "".join(parts)

    css = CSS.format(travel="rideY", kx="from{}", ky=_keyframes(stops, "Y"))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" '
            f'width="{W}" height="{H:.0f}" role="img" aria-labelledby="t d">'
            f'<title id="t">What the colours on the flyovers mean</title>'
            f'<desc id="d">{esc(total_label)}</desc>'
            f'<style>{css}</style>'
            f'<rect width="{W}" height="{H:.0f}" fill="#ffffff"/>'
            f'<text class="ttl" x="{M}" y="26">WHERE EACH PROJECT STANDS</text>'
            f'<text class="meta" x="{M}" y="43">{esc(total_label)}</text>'
            f'{rail}{dot}{"".join(rows)}{agrow}</svg>')
