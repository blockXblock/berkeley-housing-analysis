#!/usr/bin/env python3
"""
Measure U in one picture: three tranches -> a fixed debt-service plateau -> two ways
to divide it by the tax base -> two very different "rates per $100k".

Three panels on ONE shared time axis (FY of first tranche .. final FY), so the chain
reads top to bottom:
  A  Debt service each year, stacked by tranche; hatched = the interest share
     (the time value of money: early payments on each tranche are mostly interest).
  B  The assessed-value base the rate is divided by: held at today's (grey) vs the
     growth the City's advertised rates imply (violet). The shaded wedge is the
     part of the base that does not exist yet -- future sales reassessed to market
     + new construction -- i.e. who the City's rate assumes will pay.
  C  Rate per $100k = A / B, year by year, on each base.

EVERY number is derived from data/baselines/measure_u_reconciliation_baseline_*.json
(official: principal, tranches, total debt service, final FY, advertised rates;
derived: today's base, implied borrowing rate, implied base growth). Nothing is typed
into the drawing. Change the baseline, rerun, the picture changes.

Usage:  python -m scripts.viz.bond_tranches_svg [--out PATH]
"""

import argparse
import glob
import json

BASELINE_GLOB = "data/baselines/measure_u_reconciliation_baseline_*.json"
OUT_DEFAULT = "docs/maps/bond_tranches.svg"

# palette: the validated reference instance (dataviz skill). Tranches = categorical slots
# 1-3 (validated adjacent, light + dark); base/rate lines = one hue + grey (emphasis form).
C = dict(t1="#2a78d6", t2="#eb6834", t3="#1baf7a", steady="#52514e", proj="#4a3aa7",
         ink="#0b0b0b", ink2="#52514e", muted="#8a8985", grid="#e6e5e1", surface="#fcfcfb")
C_DARK = dict(t1="#3987e5", t2="#d95926", t3="#199e70", steady="#c3c2b7", proj="#9085e9",
              ink="#ffffff", ink2="#c3c2b7", muted="#8a8985", grid="#33332f", surface="#1a1a19")


def load_baseline():
    path = sorted(glob.glob(BASELINE_GLOB))[-1]
    b = json.load(open(path))
    return path, b["official"], b["derived"]


def amortize(principal, r, n):
    """Level-payment schedule: list of (payment, interest, principal_part) for n years."""
    pay = principal * r / (1 - (1 + r) ** -n)
    bal, out = principal, []
    for _ in range(n):
        i = bal * r
        out.append((pay, i, pay - i))
        bal -= pay - i
    return out


def model(off, der):
    r = der["implied_borrow_rate_pct"] / 100
    tranche = off["tranche"]
    issues = off["tranche_years"]
    n = off["final_fy"] - issues[-1] + 1          # payments per tranche (30 for a 30-yr tranche)
    years = list(range(issues[0], off["final_fy"] + 1))
    ds = {y: [] for y in years}                    # per year: list of (tranche_idx, pay, interest)
    for k, y0 in enumerate(issues):
        for j, (pay, i, _) in enumerate(amortize(tranche, r, n)):
            ds[y0 + j].append((k, pay, i))
    total_ds = sum(p for y in years for _, p, _ in ds[y])
    base0 = der["total_av_b"] * 1e9
    g = der["g_avg_pct"] / 100                     # growth the City's AVERAGE rate implies
    base = {y: base0 * (1 + g) ** (y - off["base_year"]) for y in years}
    rate_steady = {y: sum(p for _, p, _ in ds[y]) / base0 * 1e5 for y in years}
    rate_proj = {y: sum(p for _, p, _ in ds[y]) / base[y] * 1e5 for y in years}
    avg_ds = total_ds / len(years)
    peak_ds = max(sum(p for _, p, _ in ds[y]) for y in years)
    plateau = [y for y in years if abs(sum(p for _, p, _ in ds[y]) - peak_ds) < 1]
    return dict(r=r, n=n, years=years, issues=issues, ds=ds, total_ds=total_ds, avg_ds=avg_ds,
                peak_ds=peak_ds, plateau=(plateau[0], plateau[-1]), base0=base0, g=g, base=base,
                rate_steady=rate_steady, rate_proj=rate_proj,
                avg_rate_steady=sum(rate_steady.values()) / len(years),
                avg_rate_proj=sum(rate_proj.values()) / len(years),
                interest_total=sum(i for y in years for _, _, i in ds[y]),
                wedge_share=1 - sum(sum(p for _, p, _ in ds[y]) * base0 / base[y] for y in years) / total_ds)


def checks(m, off, der):
    """The picture must reproduce the official figures it claims to explain. HALT if not."""
    problems = []
    if abs(m["total_ds"] - off["total_debt_service"]) / off["total_debt_service"] > 0.01:
        problems.append(f"total debt service {m['total_ds']/1e6:.0f}M vs official {off['total_debt_service']/1e6:.0f}M")
    if abs(m["avg_rate_proj"] - off["avg_rate_100k"]) > 1.0:
        problems.append(f"avg projected-base rate {m['avg_rate_proj']:.2f} vs advertised {off['avg_rate_100k']}")
    if abs(m["peak_ds"] / m["base0"] * 1e5 - der["rate_today_100k"]) > 0.5:
        problems.append(f"peak today's-base rate {m['peak_ds']/m['base0']*1e5:.1f} vs baseline {der['rate_today_100k']:.1f}")
    if problems:
        raise SystemExit("baseline mismatch -- diagnose before drawing:\n  " + "\n  ".join(problems))


def fmt_m(x):
    return f"${x/1e6:.1f}M"


def wrap(text, width):
    """Greedy word wrap for SVG text (no auto-wrap in SVG 1.1)."""
    lines, cur = [], ""
    for w in text.split():
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + [cur]


def text_block(x, y, lines, cls="s", lh=15, extra=""):
    return "".join(f'<text x="{x}" y="{y + i*lh}" class="{cls}" {extra}>{l}</text>' for i, l in enumerate(lines))


def svg(m, off, der, src):
    W, H = 960, 990
    L, R = 92, 36
    years = m["years"]
    y0, y1 = years[0], years[-1]
    x = lambda y: L + (y - y0) / (y1 - y0) * (W - L - R)
    bw = (W - L - R) / (y1 - y0) * 0.78
    panels = [("A", 96, 305), ("B", 395, 605), ("C", 655, 850)]  # (id, top, bottom)

    def yscale(top, bot, vmax):
        return lambda v: bot - v / vmax * (bot - top)

    out = []
    o = out.append
    o(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
      f'font-family="system-ui,-apple-system,Segoe UI,Helvetica,Arial,sans-serif" font-size="12">')
    # theme tokens: light on :root, dark under prefers-color-scheme + data-theme
    o("<style>")
    o(":root{" + ";".join(f"--{k}:{v}" for k, v in C.items()) + "}")
    o("@media (prefers-color-scheme:dark){:root:not([data-theme=light]){" + ";".join(f"--{k}:{v}" for k, v in C_DARK.items()) + "}}")
    o(":root[data-theme=dark]{" + ";".join(f"--{k}:{v}" for k, v in C_DARK.items()) + "}")
    o(".ink{fill:var(--ink)}.ink2{fill:var(--ink2)}.muted{fill:var(--muted)}.grid{stroke:var(--grid)}"
      ".t1{fill:var(--t1)}.t2{fill:var(--t2)}.t3{fill:var(--t3)}"
      ".steady{stroke:var(--steady)}.proj{stroke:var(--proj)}.projfill{fill:var(--proj)}"
      "text{fill:var(--ink)} .h{font-weight:700;font-size:15px}.s{font-size:11px;fill:var(--ink2)}"
      ".n{font-variant-numeric:tabular-nums}</style>")
    o('<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
      '<line x1="0" y1="0" x2="0" y2="6" stroke="var(--surface)" stroke-width="2.2"/></pattern></defs>')
    o(f'<rect width="{W}" height="{H}" fill="var(--surface)"/>')

    # ---- title ----
    o(f'<text x="{L}" y="30" class="h" style="font-size:19px">Measure U: the same ${off["principal"]/1e6:.0f}M bond, two rates per $100k</text>')
    o(text_block(L, 52, wrap(f'Three ${off["tranche"]/1e6:.0f}M tranches ({", ".join(map(str, m["issues"]))}), each repaid over {m["n"]} years at the {m["r"]*100:.1f}% the City\'s ${off["total_debt_service"]/1e6:.0f}M total debt service implies. '
      f'Same dollars in every panel; only the base they are divided by changes.', 150)))

    # ---- panel A: debt service stacked by tranche, hatched interest ----
    top, bot = panels[0][1], panels[0][2]
    vmax = m["peak_ds"] * 1.18
    ya = yscale(top, bot, vmax)
    o(f'<text x="{L}" y="{top-8}" class="h">A · What is owed each year — debt service, $M</text>')
    for v in (5e6, 10e6, 15e6, 20e6):
        if v < vmax:
            o(f'<line x1="{L}" x2="{W-R}" y1="{ya(v):.1f}" y2="{ya(v):.1f}" class="grid"/>')
            o(f'<text x="{L-8}" y="{ya(v)+4:.1f}" text-anchor="end" class="s n">{v/1e6:.0f}</text>')
    cls = ["t1", "t2", "t3"]
    for y in years:
        base_y = bot
        for k, pay, i in m["ds"][y]:
            h = (pay / vmax) * (bot - top)
            yt = base_y - h
            xx = x(y) - bw / 2
            o(f'<g><title>FY{y} · tranche {k+1} ({m["issues"][k]}): {fmt_m(pay)} of which interest {fmt_m(i)}</title>')
            o(f'<rect x="{xx:.1f}" y="{yt:.1f}" width="{bw:.1f}" height="{max(h-1.5,0):.1f}" class="{cls[k]}" rx="1"/>')
            hi = (i / vmax) * (bot - top)                      # interest share, hatched, drawn at the top of the segment
            o(f'<rect x="{xx:.1f}" y="{yt:.1f}" width="{bw:.1f}" height="{max(min(hi,h-1.5),0):.1f}" fill="url(#hatch)" rx="1"/>')
            o('</g>')
            base_y = yt
    # average line + plateau brace
    o(f'<line x1="{L}" x2="{W-R}" y1="{ya(m["avg_ds"]):.1f}" y2="{ya(m["avg_ds"]):.1f}" stroke="var(--ink)" stroke-dasharray="4 3" stroke-width="1.2"/>')
    o(f'<text x="{W-R}" y="{ya(m["avg_ds"])-19:.1f}" text-anchor="end" class="s n" style="fill:var(--ink);font-weight:600">{len(years)}-year average {fmt_m(m["avg_ds"])}/yr</text>'
      f'<text x="{W-R}" y="{ya(m["avg_ds"])-6:.1f}" text-anchor="end" class="s n" style="fill:var(--ink);font-weight:600">— the City\'s figure</text>')
    p0, p1 = m["plateau"]
    o(f'<line x1="{x(p0)-bw/2:.1f}" x2="{x(p1)+bw/2:.1f}" y1="{ya(m["peak_ds"])-10:.1f}" y2="{ya(m["peak_ds"])-10:.1f}" stroke="var(--ink)" stroke-width="1.2"/>')
    o(f'<text x="{(x(p0)+x(p1))/2:.1f}" y="{ya(m["peak_ds"])-16:.1f}" text-anchor="middle" class="s n" style="fill:var(--ink);font-weight:600">all three tranches, {p1-p0+1} years: {fmt_m(m["peak_ds"])}/yr</text>')
    # legend A
    lx = L
    for k, lab in enumerate(m["issues"]):
        o(f'<rect x="{lx}" y="{bot+14}" width="11" height="11" class="{cls[k]}" rx="2"/><text x="{lx+16}" y="{bot+24}" class="s">tranche {k+1} · issued {lab}</text>')
        lx += 150
    o(f'<rect x="{lx}" y="{bot+14}" width="11" height="11" class="t1" rx="2"/><rect x="{lx}" y="{bot+14}" width="11" height="11" fill="url(#hatch)" rx="2"/>'
      f'<text x="{lx+16}" y="{bot+24}" class="s">hatched = interest</text>')
    o(text_block(L, bot + 42, wrap(f'Interest is ${m["interest_total"]/1e6:.0f}M of the ${m["total_ds"]/1e6:.0f}M total. Each tranche is a level-payment loan: the payment is the same every year, but in its early years it is mostly interest and only later mostly principal — that is the time value of money in the picture.', 150)))

    # ---- panel B: the base ----
    top, bot = panels[1][1], panels[1][2]
    bmax = max(m["base"].values()) * 1.08
    yb = yscale(top, bot, bmax)
    o(f'<text x="{L}" y="{top-8}" class="h">B · What it is divided by — assessed-value base, $B</text>')
    for v in range(0, int(bmax / 1e9) + 1, 25):
        if v > 0:
            o(f'<line x1="{L}" x2="{W-R}" y1="{yb(v*1e9):.1f}" y2="{yb(v*1e9):.1f}" class="grid"/>')
            o(f'<text x="{L-8}" y="{yb(v*1e9)+4:.1f}" text-anchor="end" class="s n">{v}</text>')
    pts_proj = " ".join(f"{x(y):.1f},{yb(m['base'][y]):.1f}" for y in years)
    pts_steady_rev = " ".join(f"{x(y):.1f},{yb(m['base0']):.1f}" for y in reversed(years))
    o(f'<polygon points="{pts_proj} {pts_steady_rev}" class="projfill" opacity="0.14"/>')
    o(f'<line x1="{x(y0):.1f}" x2="{x(y1):.1f}" y1="{yb(m["base0"]):.1f}" y2="{yb(m["base0"]):.1f}" class="steady" stroke-width="2.5"/>')
    o(f'<polyline points="{pts_proj}" fill="none" class="proj" stroke-width="2.5"/>')
    o(f'<text x="{x(y0)+6:.1f}" y="{yb(m["base0"])+16:.1f}" class="s n" style="fill:var(--steady);font-weight:600">held at today\'s base: ${m["base0"]/1e9:.1f}B, every year</text>')
    ylab = years[len(years) // 2]
    o(f'<text x="{x(ylab):.1f}" y="{yb(m["base"][ylab])-14:.1f}" text-anchor="end" class="s n" style="fill:var(--proj);font-weight:600">base the City\'s rates imply: +{m["g"]*100:.1f}%/yr → ${m["base"][y1]/1e9:.0f}B by {y1}</text>')
    wy = years[len(years) * 3 // 4]
    wtop = yb(m["base0"]) - 62
    o(text_block(x(wy), wtop, wrap(f'the wedge: base that does not exist yet — future sales reassessed to market, plus new construction. It carries {m["wedge_share"]*100:.0f}% of the debt service.', 46), extra='text-anchor="middle" style="fill:var(--proj)"'))

    # ---- panel C: rate per $100k ----
    top, bot = panels[2][1], panels[2][2]
    rmax = max(m["rate_steady"].values()) * 1.15
    yc = yscale(top, bot, rmax)
    o(f'<text x="{L}" y="{top-8}" class="h">C · The result — rate per $100k of assessed value (= A ÷ B)</text>')
    for v in (20, 40, 60):
        if v < rmax:
            o(f'<line x1="{L}" x2="{W-R}" y1="{yc(v):.1f}" y2="{yc(v):.1f}" class="grid"/>')
            o(f'<text x="{L-8}" y="{yc(v)+4:.1f}" text-anchor="end" class="s n">${v}</text>')
    # step lines (rate is constant within a year)
    def steps(series):
        pts = []
        for y in years:
            pts.append(f"{x(y)-bw/2:.1f},{yc(series[y]):.1f}")
            pts.append(f"{x(y)+bw/2:.1f},{yc(series[y]):.1f}")
        return " ".join(pts)
    o(f'<polyline points="{steps(m["rate_steady"])}" fill="none" class="steady" stroke-width="2.5"/>')
    o(f'<polyline points="{steps(m["rate_proj"])}" fill="none" class="proj" stroke-width="2.5"/>')
    pk = m["peak_ds"] / m["base0"] * 1e5
    o(f'<text x="{(x(p0)+x(p1))/2:.1f}" y="{yc(pk)-8:.1f}" text-anchor="middle" class="s n" style="fill:var(--steady);font-weight:600">on today\'s base: ${pk:.0f} for {p1-p0+1} years · ${m["avg_rate_steady"]:.0f} average</text>')
    pky = max(years, key=lambda y: m["rate_proj"][y])
    yl = years[len(years) // 3]
    o(text_block(x(yl), yc(rmax * 0.72), wrap(f'on the growing base: ${m["avg_rate_proj"]:.0f} average ≈ the City\'s ${off["avg_rate_100k"]}. (Steady {m["g"]*100:.1f}%/yr growth peaks at ${m["rate_proj"][pky]:.0f} in {pky}; the City\'s own schedule, growing faster early, says ${off["peak_rate_100k"]:.0f} in {off["peak_first_fy"]}-{str(off["peak_first_fy"]+1)[2:]}.)', 60), extra='text-anchor="start" style="fill:var(--proj);font-weight:600"'))
    # shared x axis
    for y in years:
        if (y - y0) % 5 == 0 or y == y1:
            o(f'<text x="{x(y):.1f}" y="{bot+18}" text-anchor="middle" class="s n">{y}</text>')
            o(f'<line x1="{x(y):.1f}" x2="{x(y):.1f}" y1="{bot}" y2="{bot+4}" stroke="var(--ink2)"/>')
    for k, yy in enumerate(m["issues"]):
        o(f'<line x1="{x(yy)-bw/2:.1f}" x2="{x(yy)-bw/2:.1f}" y1="{panels[0][1]}" y2="{bot}" stroke="var(--{cls[k]})" stroke-dasharray="2 4" opacity="0.7"/>')
    foot = wrap(f'Reading down: the dollars owed (A) are fixed by the bond. The City\'s advertised ${off["avg_rate_100k"]} comes from dividing them by a base (B) that its own rate schedule assumes will grow about {m["g"]*100:.1f}% a year — '
      f'that is, from future buyers reassessed at their purchase price and from new buildings. Held on today\'s base, the same obligation is ${m["avg_rate_steady"]:.0f} on average and ${pk:.0f} for the {p1-p0+1} plateau years. Both are the same ${off["total_debt_service"]/1e6:.0f}M; they differ in who pays it.', 150)
    o(text_block(L, bot + 42, foot))
    o(text_block(L, bot + 42 + 15 * len(foot) + 4, wrap(f'Source: {src}; official figures from Resolution 72,338-N.S. Exhibit B + impartial analysis; base = Alameda County assessor, Berkeley parcels. Generated by scripts/viz/bond_tranches_svg.py — every number is derived, none typed in.', 160), extra='style="fill:var(--muted)"'))
    o("</svg>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DEFAULT)
    a = ap.parse_args()
    src, off, der = load_baseline()
    m = model(off, der)
    checks(m, off, der)
    print(f"baseline {src}")
    print(f"tranches {m['issues']} x ${off['tranche']/1e6:.0f}M, {m['n']} yrs each at {m['r']*100:.2f}% -> payment {fmt_m(m['ds'][m['issues'][0]][0][1])}/yr per tranche")
    print(f"total DS {fmt_m(m['total_ds'])} (interest {fmt_m(m['interest_total'])}); avg {fmt_m(m['avg_ds'])}/yr; plateau {fmt_m(m['peak_ds'])}/yr {m['plateau'][0]}-{m['plateau'][1]}")
    print(f"today's base ${m['base0']/1e9:.1f}B -> rate avg ${m['avg_rate_steady']:.1f}, plateau ${m['peak_ds']/m['base0']*1e5:.1f}")
    print(f"projected base +{m['g']*100:.2f}%/yr -> rate avg ${m['avg_rate_proj']:.2f} (advertised {off['avg_rate_100k']}), peak ${max(m['rate_proj'].values()):.1f} (city {off['peak_rate_100k']})")
    print(f"wedge (share of DS carried by base growth): {m['wedge_share']*100:.1f}%")
    open(a.out, "w").write(svg(m, off, der, src))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
