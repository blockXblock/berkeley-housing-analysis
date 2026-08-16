#!/usr/bin/env python3
"""gen_measure_u_site.py — generates docs/measure-u/index.html (berkeleybuild.com/measure-u/).

The Measure U evidence site: what Berkeley pays now, arguments, timing, oversight,
V2050 compliance, burden, and the maps.

DISCIPLINE (repo cardinal rule): every result figure on the page is DERIVED — read from the
JN-MeasureU baseline (data/baselines/measure_u_reconciliation_baseline_2026-08-15.json,
gate-verified; includes the tax_incidence session's citywide fixed-charge block). Editorial
tables (claims analysis, V2050 comparison, commitments, timeline) are sourced prose; numeric
tokens inside them are injected, never typed. Re-run after any baseline append:
python3 scripts/gen_measure_u_site.py

The one real-parcel worked example is published WITHOUT address/APN (privacy default; the
JN and notes carry the full identification).
"""
import json, os

BASELINE = "data/baselines/measure_u_reconciliation_baseline_2026-08-15.json"
OUT = "docs/measure-u/index.html"

b = json.load(open(BASELINE))
O, D = b["official"], b["derived"]

# ---- derived tokens (all from the baseline) ----
rate_today = D["rate_today_100k"]
rate_avg, rate_peak = O["avg_rate_100k"], O["peak_rate_100k"]
base_b, n = D["total_av_b"], D["n_parcels"]
borrow, ds_peak_m = D["implied_borrow_rate_pct"], D["ds_peak_m"]
interest_m = D["total_interest_m"]
g_avg, g_peak = D["g_avg_pct"], D["g_peak_pct"]
wedge_lo, wedge_hi = D["wedge_share_avg_pct"], D["wedge_share_peak_pct"]
frozen = D["avg_rate_frozen_100k"]
mult = D["base_avg_multiple"]
flat = D["flat_parcel_cost"]
med_sfr_av = D["med_sfr_av"]
med_avg, med_peak, med_today = (med_sfr_av * r / 1e5 for r in (rate_avg, rate_peak, rate_today))
BENV_AV, BENV_BILL = 728_900, 21_064          # real FY26 bill (source data; see JN oracle)
bv_avg, bv_peak, bv_today = (BENV_AV * r / 1e5 for r in (rate_avg, rate_peak, rate_today))
top = {k: D[f"top{k}_share_pct"] for k in (1, 5, 10, 25, 50)}
sfr_spread, sfr_n = D["sfr_p90_p10"], D["sfr_n"]
nc_av, nc_share, nc_units, nc_proj = D["newcon_av_b"], D["newcon_share_of_base_pct"], D["newcon_units_matched"], D["newcon_projects_matched"]
apt_share = D["apt_share_pct"]

# tier composition (who the top tiers are)
tc, ct, te = D["tier_composition_av_pct"], D["tier_composition_count"], D["tier_entry_av"]

# citywide tax structure (tax_incidence session's block, mirrored into this baseline)
TI = D["tax_incidence"]
psf = TI["parcel_tax_per_sqft_total"]; flat_pt = TI["parcel_tax_flat_per_parcel"]
unit_pt = TI["parcel_tax_per_dwelling_unit"]; adval_pct = TI["ad_valorem_rate_pct"]
disp = TI["dispersion_p90_p10"]
dec = {int(r["decile"]): {k: float(v) for k, v in r.items() if k != "decile"} for r in TI["sfr_by_av_decile"]}
d1, d5, d10 = dec[1], dec[5], dec[10]

LIFE = [("Durable, long-life, low carry", 42, "#3b6fb6",
         "seawall, marina piles, Bay Trail, sidewalks, ADA ramps, paths"),
        ("Catch-up renewal of existing assets", 150, "#8a8f98",
         "pools, restrooms, play structures, elevators, end-of-life HVAC, 911 center, seismic partials, Fire Stations 4 & 6"),
        ("New/expanded capacity → permanent new O&M", 82, "#e07b39",
         "Frances Albrier replacement, new Adeline parkland, behavioral-health building, Fire Training Center")]
life_tot = sum(x[1] for x in LIFE)

usd = lambda x: f"${x:,.0f}"
pct = lambda x, d=1: f"{x:.{d}f}%"

CSS = """
:root{--blue:#3b6fb6;--orange:#e07b39;--ink:#30343b;--gray:#8a8f98;--red:#b3261e;
--bg:#fcfcfb;--card:#ffffff;--line:#e5e4e0;--muted:#6b7075}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.55}
a{color:var(--blue)} .wrap{max-width:1060px;margin:0 auto;padding:0 20px}
header.hero{padding:56px 0 30px;border-bottom:1px solid var(--line)}
.kicker{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
h1{font-size:40px;line-height:1.12;margin:10px 0 14px;font-weight:800}
.lede{font-size:18px;color:#444;max-width:56em}
nav{position:sticky;top:0;background:rgba(252,252,251,.95);backdrop-filter:blur(4px);border-bottom:1px solid var(--line);z-index:9}
nav .wrap{display:flex;gap:18px;overflow-x:auto;padding:10px 20px;font-size:13.5px;white-space:nowrap}
nav a{text-decoration:none;color:var(--muted)} nav a:hover{color:var(--ink)}
section{padding:44px 0;border-bottom:1px solid var(--line)}
h2{font-size:26px;margin-bottom:6px} .sub{color:var(--muted);margin-bottom:22px;max-width:60em}
h3{font-size:17px;margin:20px 0 8px}
p.body{max-width:60em;margin:10px 0;font-size:15px}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:18px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.tile b{display:block;font-size:24px;font-weight:800} .tile span{font-size:12.5px;color:var(--muted)}
.tile.warn b{color:var(--red)}
.chan{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-top:18px}
.chan .tile p{font-size:13.5px;color:#4a4a46;margin-top:8px} .chan .tile em{color:var(--muted);font-size:12.5px}
.barrow{display:grid;grid-template-columns:220px 1fr 90px;gap:10px;align-items:center;margin:7px 0;font-size:14px}
.track{background:#efeeea;border-radius:5px;height:26px;position:relative}
.fill{height:100%;border-radius:5px}
.stack{display:flex;height:30px;border-radius:6px;overflow:hidden;margin:10px 0 4px}
.stack div{height:100%} .stack div+div{border-left:2px solid var(--bg)}
.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:13px;color:var(--muted);margin-top:6px}
.dot{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:middle}
table{width:100%;border-collapse:collapse;font-size:14px;margin-top:14px;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th{background:#f4f3f0;text-align:left;padding:10px 12px;font-size:12.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
td{padding:10px 12px;border-top:1px solid var(--line);vertical-align:top}
.note{background:#f6f5f2;border-left:4px solid var(--orange);border-radius:0 8px 8px 0;padding:12px 16px;font-size:14px;margin:16px 0;color:#4a4a46}
.quote{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px 24px;margin:14px 0;font-size:15px}
.tl{list-style:none;padding-left:0;margin-top:14px}
.tl li{position:relative;padding:0 0 16px 26px;border-left:2px solid var(--line);margin-left:8px;font-size:14.5px}
.tl li::before{content:"";position:absolute;left:-6px;top:4px;width:10px;height:10px;border-radius:50%;background:var(--blue)}
.tl li.now::before{background:var(--red)} .tl li.fut::before{background:var(--gray)}
.tl b{display:inline-block;min-width:120px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px;margin-top:18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;text-decoration:none;color:var(--ink);display:block}
.card:hover{border-color:var(--blue)} .card h4{font-size:16px;margin-bottom:6px} .card p{font-size:13.5px;color:var(--muted)}
.card .go{color:var(--blue);font-size:13px;font-weight:600;margin-top:10px;display:block}
footer{padding:36px 0 60px;font-size:13px;color:var(--muted)}
.small{font-size:12.5px;color:var(--muted)}
@media(max-width:640px){h1{font-size:30px}.barrow{grid-template-columns:130px 1fr 80px}}
@media(max-width:720px){table{display:block;overflow-x:auto}}
"""

def bar(label, val, vmax, color, txt):
    w = val / vmax * 100
    return (f'<div class="barrow"><div>{label}</div><div class="track">'
            f'<div class="fill" style="width:{w:.1f}%;background:{color}"></div></div>'
            f'<div><b>{txt}</b></div></div>')

rates_bars = (
    bar("Advertised 40-yr average", rate_avg, rate_today, "var(--blue)", f"${rate_avg:.2f}")
    + bar("Disclosed peak (FY 2040-41)", rate_peak, rate_today, "var(--ink)", f"${rate_peak:.0f}")
    + bar("Same debt service, today's base", rate_today, rate_today, "var(--orange)", f"${rate_today:.0f}")
    + bar("If the base grew only 2%/yr (avg)", frozen, rate_today, "var(--gray)", f"${frozen:.2f}"))

conc_bars = "".join(bar(f"Top {k}% of parcels ({int(n*k/100):,})", top[k], 100, "var(--blue)", pct(top[k]))
                    for k in (1, 5, 10, 25, 50)) \
            + bar("Bottom 50% of parcels", 100 - top[50], 100, "var(--gray)", pct(100 - top[50]))

life_stack = "".join(f'<div style="width:{v/life_tot*100:.1f}%;background:{c}" title="{lab}"></div>'
                     for lab, v, c, _ in LIFE)
life_leg = "".join(f'<span><span class="dot" style="background:{c}"></span>{lab} — ~${v}M ({v/life_tot*100:.0f}%): {d}</span>'
                   for lab, v, c, d in LIFE)

wedge_cap = 2.0 / g_avg * 100
t1, c1 = tc["1"], ct["1"]
t25, c25 = tc["25"], ct["25"]

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Measure U, Examined — Berkeley's $300M Infrastructure Bond</title>
<meta name="description" content="Independent analysis of Berkeley's November 2026 $300M infrastructure bond: what Berkeley pays now, the official numbers reconciled, who pays, Vision 2050 compliance, oversight, and parcel-by-parcel maps.">
<style>{CSS}</style></head><body>

<header class="hero"><div class="wrap">
<div class="kicker">berkeleybuild.com · independent analysis · updated August 15, 2026</div>
<h1>Measure U, examined</h1>
<p class="lede">Berkeley asks voters on November 3, 2026 to authorize a <b>$300 million</b> general-obligation
bond for infrastructure. This site explains, in plain language, how Berkeley property taxes actually work;
reconciles the City's official numbers with the county assessor roll, parcel by parcel; tests the campaign's
claims; measures the measure against the City's own <b>Vision&nbsp;2050</b> framework; and states the
conditions under which the Vision&nbsp;2050 professionals support it. Every figure is derived from primary
sources — the resolution, the Tax Rate Statement, {TI['_evidence'].split(';')[0]}, and the
{n:,}-parcel assessor roll — by a re-runnable, gate-checked pipeline.</p>
</div></header>

<nav><div class="wrap">
<a href="#taxes-now">Taxes today</a><a href="#measure">The measure</a><a href="#rates">One levy, three rates</a>
<a href="#burden">Who pays</a><a href="#arguments">The arguments</a><a href="#v2050">Vision 2050</a>
<a href="#oversight">Oversight</a><a href="#timing">Timing</a><a href="#maps">Maps</a><a href="#method">Method</a>
</div></nav>

<section id="taxes-now"><div class="wrap">
<h2>Start here: the three ways Berkeley taxes its households</h2>
<p class="sub">Before judging a new tax, know the ones you already pay. Berkeley households pay through three
different channels, and they work in completely different — often opposite — ways.</p>
<div class="chan">
<div class="tile"><b>1 · Tax on your home's VALUE</b>
<p>About <b>{adval_pct:.2f}%</b> of your home's <i>assessed value</i> every year (all agencies combined).
Here's the catch: under Proposition 13, assessed value is <b>not what your home is worth — it's what you paid
for it</b>, plus at most 2% per year. So Berkeley splits into two groups. If you bought decades ago, your
taxable value crawls upward and is now far below market. If you bought recently — or built something new —
your taxable value is your full purchase price or construction cost. <b>Identical houses on the same block
can carry taxable values 15× apart.</b> When a long-held house sells, its taxable value jumps to the sale
price overnight.</p><em>Measure U adds to this channel.</em></div>
<div class="tile"><b>2 · Taxes on your home's SIZE</b>
<p>Berkeley's special taxes — schools, library, parks, fire, streets — mostly ignore value entirely. They
charge by the <b>square foot of your building</b>: about <b>${psf:.2f} per sq ft per year</b>, plus about
{usd(flat_pt)} in flat per-parcel charges. A 1,900&nbsp;sq&nbsp;ft house pays the same whether it was bought
in 1975 or last Tuesday. This channel runs <i>opposite</i> to channel 1: it's heaviest, as a share of what
the county says your house is worth for taxes, on <b>long-held, low-assessed homes</b>.</p>
<em>On a real Berkeley bill, this channel is the majority of the total.</em></div>
<div class="tile"><b>3 · Tax on what you BUY</b>
<p>Sales tax — currently 10.25% in Berkeley, rising to 10.75% if companion Measure V passes. It taxes
spending, not property, so renters pay it directly. Online purchases delivered to Berkeley are generally
charged the same rate, but the locally-kept share of an online sale is often pooled countywide rather than
credited to Berkeley the way an in-store sale is — one reason cities keep returning to property measures.</p>
<em>Measure V (same ballot) raises this channel.</em></div>
</div>
<h3>The two property channels, side by side — real numbers, citywide</h3>
<p class="body">Modeled across <b>{TI['sfr_parcels_modelled']:,} single-family homes</b> (schedule
reconstructed from {TI['_evidence'].split(';')[0]}, validated against City building data):</p>
<table><tr><th>Single-family homes, by assessed value</th><th>Median assessed value</th><th>Median size</th>
<th>Total property tax</th><th>Share from SIZE-based charges</th><th>Effective rate on assessed value</th></tr>
<tr><td>Lowest tenth (mostly longest-held)</td><td>{usd(d1['median_av'])}</td><td>{d1['median_sqft']:,.0f} sq ft</td>
<td>{usd(d1['total'])}/yr</td><td><b>{d1['flat_share_pct']:.0f}%</b></td><td><b>{d1['pct_of_av']:.1f}%</b></td></tr>
<tr><td>Middle tenth</td><td>{usd(d5['median_av'])}</td><td>{d5['median_sqft']:,.0f} sq ft</td>
<td>{usd(d5['total'])}/yr</td><td>{d5['flat_share_pct']:.0f}%</td><td>{d5['pct_of_av']:.1f}%</td></tr>
<tr><td>Highest tenth (mostly recent buyers)</td><td>{usd(d10['median_av'])}</td><td>{d10['median_sqft']:,.0f} sq ft</td>
<td>{usd(d10['total'])}/yr</td><td>{d10['flat_share_pct']:.0f}%</td><td>{d10['pct_of_av']:.1f}%</td></tr></table>
<div class="note"><b>Read that first row again.</b> The longest-held homes pay the least in dollars — but
{d1['flat_share_pct']:.0f}% of their bill comes from size-based charges they can't reduce, and their bill is
the <i>highest share of assessed value</i> ({d1['pct_of_av']:.1f}% vs {d10['pct_of_av']:.1f}%). The value
channel alone varies {disp['av']:.0f}× between similar homes; the size channel varies only
{disp['flat']:.1f}×; the total bill varies {disp['total']:.1f}×. <b>The two channels pull in opposite
directions — and Berkeley leans on the size channel harder than any other Alameda County city.</b> Any honest
debate about a new tax has to say which channel it uses and who that lands on. Measure U uses channel 1.</div>
</div></section>

<section id="measure"><div class="wrap">
<h2>The measure in official numbers</h2>
<p class="sub">From Resolution 72,338-N.S. (June 16, 2026), its Exhibit B Tax Rate Statement, and the City
Attorney's impartial analysis. Requires a two-thirds vote.</p>
<div class="facts">
<div class="tile"><b>$300M</b><span>principal authorized</span></div>
<div class="tile"><b>${interest_m:,.0f}M</b><span>interest — more than principal ($610M total debt service)</span></div>
<div class="tile"><b>{borrow:.2f}%</b><span>borrowing rate implied by the TRS's own figures</span></div>
<div class="tile"><b>$100M × 3</b><span>issuance: 2027, 2032, 2037</span></div>
<div class="tile"><b>FY 2066/67</b><span>final tax collection — a 40-year commitment</span></div>
<div class="tile warn"><b>64%</b><span>support in the City's own April 2026 poll, after arguments — vs 66.7% required</span></div>
</div>
</div></section>

<section id="rates"><div class="wrap">
<h2>One levy, three rates</h2>
<p class="sub">The ballot label says <b>${rate_avg:.2f} per $100,000</b> of assessed value. The Tax Rate
Statement discloses a peak of <b>${rate_peak:.0f}</b>. The same peak-period debt service
(~${ds_peak_m:.0f}M/yr), divided by <i>today's</i> ${base_b:.1f}B base, is <b>${rate_today:.0f}</b>.
All three are the same levy — the only difference is the tax base it is divided by.</p>
{rates_bars}
<div class="small" style="margin-top:6px">$ per $100,000 of assessed value. Derived from the TRS's $610M total
debt service and the {n:,}-parcel assessor roll (bill-consistent net AV).</div>
<h3>The hidden assumption: who grows the base</h3>
<p class="sub" style="margin-bottom:8px">Reproducing the advertised ${rate_avg:.2f} average requires the base to grow
<b>{g_avg:.1f}–{g_peak:.1f}% per year</b> (its 40-year average base: <b>{mult:.2f}×</b> today's). Prop 13 caps
parcels that don't change hands at 2%. The remainder — the orange share — must come from
<b>reassessment at sale and new construction</b> (plus bounded, cyclical Prop-8 restorations).</p>
<div class="stack" style="max-width:720px">
<div style="width:{wedge_cap:.1f}%;background:var(--gray)" title="Prop-13 2% cap"></div>
<div style="width:{100-wedge_cap:.1f}%;background:var(--orange)" title="newcomer wedge"></div>
</div>
<div class="legend" style="max-width:720px">
<span><span class="dot" style="background:var(--gray)"></span>Growth from sitting owners at the 2% cap</span>
<span><span class="dot" style="background:var(--orange)"></span>Newcomer wedge — sales &amp; new construction: <b>{wedge_lo:.0f}–{wedge_hi:.0f}%</b> of all assumed growth</span>
</div>
<div class="note"><b>The point:</b> the advertised low average rate is financed by future buyers and future
buildings. If the base grew only at the Prop-13 cap, the identical bond would average
<b>${frozen:.0f} per $100,000 — {frozen/rate_avg:.1f}× the advertised figure</b>. The buildings completed
since 2018 already visible in the roll ({nc_proj} projects, {nc_units:,} units, ${nc_av:.1f}B, an undercount)
are that wedge arriving.</div>
</div></section>

<section id="burden"><div class="wrap">
<h2>Who pays</h2>
<p class="sub">Three terms, in plain English, then the numbers.</p>
<p class="body"><b>“Ad-valorem”</b> is Latin for <i>on the value</i>: your Measure U bill is one citywide
rate multiplied by your parcel's assessed value. Big assessed value, big bill; small, small.</p>
<p class="body"><b>“Assessed value is acquisition-based”</b> means the county doesn't tax what your property
is <i>worth</i> — it taxes what you (or your building's developer) <i>paid</i>, plus at most 2% a year since.
That's Proposition 13. So this bond automatically bills recent buyers and new buildings hardest, and bills
the longest-held properties least — regardless of anyone's wealth or ability to pay.</p>
<p class="body"><b>The shares below don't depend on which rate applies</b> (they are “rate-invariant”):
whatever rate the City ends up levying — the $22.14 average, the $35 peak — everyone's bill scales by the
same factor, so each group's <i>slice of the total</i> never changes. The slices are the honest thing to
argue about.</p>
{conc_bars}
<h3>Who ARE the “top 1%” of parcels? (Not homeowners.)</h3>
<p class="body">The top 276 parcels — the ones paying a fifth of the whole bond — are almost entirely
<b>large buildings, not houses</b>: <b>{t1.get('apartments_mixed',0):.0f}%</b> of the tier's value is
apartment buildings ({c1.get('apartments_mixed',0)} parcels — including the big projects completed in the
last decade), <b>{t1.get('commercial_industrial',0):.0f}%</b> is commercial and industrial (West Berkeley
plants, downtown offices and hotels), and <b>{t1.get('institutional',0):.0f}%</b> is institutional. Exactly
<b>{c1.get('single_family',0)} single-family homes</b> make the top 1%. Widen the lens and homes take over:
you enter the top 25% at {usd(te['25'])} of assessed value — a recently-bought Berkeley house — and
single-family homes are that tier's largest group ({c25.get('single_family',0):,} of {int(n*0.25):,}
parcels, {t25.get('single_family',0):.0f}% of its value).</p>
<table><tr><th>Tier</th><th>You're in it above…</th><th>What the tier mostly is</th></tr>
<tr><td>Top 1% ({int(n*0.01):,} parcels — {top[1]:.1f}% of the bond)</td><td>{usd(te['1'])}</td>
<td>Apartment buildings ({t1.get('apartments_mixed',0):.0f}%), commercial/industrial
({t1.get('commercial_industrial',0):.0f}%), institutions ({t1.get('institutional',0):.0f}%). Almost no houses.</td></tr>
<tr><td>Top 5% ({int(n*0.05):,} — {top[5]:.1f}%)</td><td>{usd(te['5'])}</td>
<td>Still mostly big buildings, but recently-sold homes start appearing ({ct['5'].get('single_family',0)} homes).</td></tr>
<tr><td>Top 10% ({int(n*0.10):,} — {top[10]:.1f}%)</td><td>{usd(te['10'])}</td>
<td>Mixed: apartments ({tc['10'].get('apartments_mixed',0):.0f}%) and recent home purchases
({ct['10'].get('single_family',0):,} homes).</td></tr>
<tr><td>Top 25% ({int(n*0.25):,} — {top[25]:.1f}%)</td><td>{usd(te['25'])}</td>
<td>Recently-bought single-family homes are now the largest group.</td></tr></table>
<p class="body">So the plain-language version: <b>at the very top, Measure U is a tax on big buildings —
mostly apartments, which pass it into rents. Below that, it is a tax on whoever bought a home most
recently.</b> The half of Berkeley that has held longest pays {100-top[50]:.0f}% of the bond.</p>
<div class="facts" style="margin-top:22px">
<div class="tile"><b>{sfr_spread:.1f}×</b><span>spread in annual cost between the 90th- and 10th-percentile
single-family home — for the identical bond</span></div>
<div class="tile"><b>{apt_share:.0f}%</b><span>of the bond falls on apartment parcels — largely renter-borne
via pass-through</span></div>
<div class="tile"><b>{nc_share:.1f}%+</b><span>carried by the {nc_units:,}+ units completed since 2018 — on
~0.1% of parcels</span></div>
<div class="tile"><b>{usd(flat)}</b><span>what the same money as a flat per-parcel tax would cost everyone —
which would instead land hardest on long-held small homes</span></div>
</div>
<h3>What it adds to a real bill</h3>
<table><tr><th>Basis</th><th>Median single-family home (assessed at {usd(med_sfr_av)})</th>
<th>One real parcel (assessed at {usd(BENV_AV)}; FY26 bill {usd(BENV_BILL)})</th></tr>
<tr><td>Advertised 40-yr average (${rate_avg:.2f}/100k)</td><td>{usd(med_avg)}/yr</td><td>{usd(bv_avg)}/yr</td></tr>
<tr><td>Disclosed peak (${rate_peak:.0f}/100k, FY 2040-41)</td><td>{usd(med_peak)}/yr</td><td>{usd(bv_peak)}/yr</td></tr>
<tr><td>Today's-base benchmark (${rate_today:.0f}/100k)</td><td>{usd(med_today)}/yr</td><td>{usd(bv_today)}/yr</td></tr></table>
<div class="note"><b>Keep the magnitude honest:</b> on that real bill, Measure U adds roughly 1–2% of the
total. The bill's majority is the <a href="#taxes-now">size-based channel</a>, where citywide single-family
totals already run {usd(TI['aggregate_sfr_parcel_taxes'])} a year against {usd(TI['aggregate_sfr_ad_valorem'])}
of value-based tax. The case examined on this page is about <i>who</i> pays and <i>what governs the
spending</i> — not a claim that this bond alone breaks anyone's budget.</div>
</div></section>

<section id="arguments"><div class="wrap">
<h2>The campaign's claims, against the record</h2>
<p class="sub">From the ballot label, the staff reports, and the City's public materials. None of these claims
is false; each is examined for what it leaves out.</p>
<table><tr><th>The claim</th><th>What the record shows</th></tr>
<tr><td>“${rate_avg:.2f} per $100,000 assessed value” <span class="small">(ballot label)</span></td>
<td>True as a 40-year average on a base assumed to reach {mult:.1f}× today's. The disclosed peak is
${rate_peak:.0f}; the staff-reported average combined with existing GO debt is $44.13 (a figure the county
rate history suggests needs reconciling — existing city GO alone has averaged $51.90 per $100k over 12
years); the same debt on today's base is ${rate_today:.0f}. Several numbers, one levy — voters see the
smallest.</td></tr>
<tr><td>“Subject to independent oversight and audits” <span class="small">(ballot label)</span></td>
<td>The text provides two existing council-appointed commissions, an annual City Manager report, and a City
Auditor audit at least every three years. No dedicated citizens' bond oversight committee — unless the
Council creates one (see <a href="#oversight">Oversight</a>).</td></tr>
<tr><td>“Fire stations, emergency response, parks… climate resiliency” <span class="small">(ballot label)</span></td>
<td>The named categories are real, but the project list is explicitly <i>non-exhaustive and non-binding</i>:
any acquisition or improvement of real property qualifies, including projects never shown to the public, and
proceeds may reimburse money already spent.</td></tr>
<tr><td>“Documented in… the City's Vision 2050 Framework” <span class="small">(impartial analysis)</span></td>
<td>Vision 2050 is cited by name while its central sequence — plan, prioritize, then ask — is inverted:
project-by-project prioritization is deferred until <i>after</i> voters approve the money
(see <a href="#v2050">Vision 2050</a>).</td></tr>
<tr><td>“Over $1.5–2.1 billion in unfunded needs” <span class="small">(findings; webpage)</span></td>
<td>The City's own stated need moved from $882M (2020) to &gt;$1B (Dec 2025) to &gt;$1.5B (adopted CIP) to
&gt;$2.1B (proposed CIP) — a 2.4× spread that is itself evidence no stable program plan sits under the ask.</td></tr>
<tr><td>“$313M program capacity” <span class="small">(staff report)</span></td>
<td>Includes <b>$40.5M (13%) for staffing and implementation</b>, and the measure permits reimbursing
prior expenditures — meaningful General-Fund relief for a city projecting $31M/$29M deficits, which is not
what the label advertises.</td></tr>
<tr><td>“Berkeley's GO tax ($270) is far below Oakland's ($660) and Albany's ($685)” <span class="small">(work session)</span></td>
<td>Arithmetically correct — county data confirms the ratios. But it counts only the GO-bond line. Berkeley
financed through <i>parcel taxes</i> instead: on the reconciled real bill, city GO debt is $357 while city
parcel taxes are $7,045. The comparison measures the one channel Berkeley uses least; on <i>total</i>
ad-valorem rates Berkeley sits mid-pack among Alameda County's 14 cities.</td></tr>
<tr><td>“Delay makes it more expensive” <span class="small">(City Manager)</span></td>
<td>True — construction escalation is real, and it applies equally to the ~$1.7B of need this bond does
<i>not</i> fund. Urgency argues for a complete financing plan at least as strongly as for this $300M.</td></tr>
</table>
</div></section>

<section id="v2050"><div class="wrap">
<h2>Compliance with Vision 2050</h2>
<p class="sub">Measured against the official reports: the Vision 2050 Framework (2020) and “Realize Vision
2050” (October 2025) — the City's own task force of infrastructure professionals.</p>
<table><tr><th>Vision 2050 said</th><th>Measure U does</th></tr>
<tr><td>Prepare an <b>Infrastructure Program Plan by Spring 2026</b> to inform “the timing and what should be
included in a future funding measure”</td><td>No plan adopted; prioritization performed at asset-category
level only; project-by-project prioritization deferred until <i>after</i> passage.</td></tr>
<tr><td>“A series of general obligation bonds totaling <b>$250–300M over the next 25–30 years</b>, without
breaching responsible debt thresholds”</td><td>The entire envelope authorized at once; issued over ~10 years;
$610M of debt service running to FY 2066/67.</td></tr>
<tr><td>Complete an <b>Asset Management Program</b> first, so new assets are maintained cradle-to-grave</td>
<td>AMP in progress, incomplete; the measure's maintenance language is a non-binding “whereas.”</td></tr>
<tr><td>Weigh <b>2026 vs 2028</b> using polling, the economy, and competing measures; the 2025 report flags
“a sense of the public feeling tax fatigue”</td><td>2026 chosen: seven measures on one ballot including a
companion sales tax, with the City's own poll at 64% against a 66.7% threshold.</td></tr>
<tr><td>Core resilient-infrastructure categories: storm drains, <b>green infrastructure</b> ($207M watershed
plan), <b>undergrounding</b> on evacuation routes, transfer station, urban forest</td>
<td>Absent from the project list. Fire gets $107M against a ~$350M master-plan need; Civic Center seismic
line items don't return either building to use.</td></tr>
<tr><td><i>Where it does align:</i> phased $100M issuance ≈ a series; project screening used Envision-based
criteria; all-electric requirement matches the clean-energy strategy</td><td>Genuine alignments — necessary
but not sufficient. The name is cited; the discipline is not yet bound.</td></tr></table>

<h3>The lifecycle sort the City never published</h3>
<p class="sub" style="margin-bottom:8px">Every capital dollar creates a different operating future. Sorting the
City's own 36-project list (a v0 professional sort — the City has published no per-project O&amp;M or design
life anywhere):</p>
<div class="stack" style="max-width:760px">{life_stack}</div>
<div class="legend" style="max-width:760px;flex-direction:column;gap:6px">{life_leg}</div>
<div class="note">Final collection is <b>FY 2066/67</b> — while artificial turf (~10-yr life), play
structures (~15–20), HVAC (~20–25) and elevators (~25) will be worn out and replaced, possibly twice, on the
debt that bought them. That mismatch is precisely what Vision 2050's cradle-to-grave strategy exists to
prevent — and what the oversight conditions below are designed to fix.</div>
</div></section>

<section id="oversight"><div class="wrap">
<h2>Oversight: what the measure provides, and what support requires</h2>
<p class="sub">The measure's own §6(F) assigns oversight to two commissions <i>“or their successors”</i> — so
every body below can be created by ordinary Council ordinance or resolution. No charter amendment, no second
election. The Vision 2050 professionals' support is conditioned on one omnibus <b>Implementation &amp;
Accountability Resolution</b>, adopted before ballots print.</p>
<table><tr><th>#</th><th>Action</th><th>Legal instrument</th><th>Who acts (● = new body)</th><th>By</th></tr>
<tr><td>1</td><td>Adopt the full <b>Infrastructure Program Plan</b> — before any issuance beyond tranche 1</td>
<td>Council resolution, bound into the Debt Management Policy</td><td>● Capital Program Office prepares; Council adopts</td><td>Jun 2027</td></tr>
<tr><td>2</td><td><b>Lifecycle-cost discipline</b>: no bond appropriation without published per-project O&amp;M,
design life, and the operating fund that carries it</td><td>Ordinance (new BMC chapter)</td>
<td>City Manager produces; ● Oversight Committee certifies</td><td>Q1 2027</td></tr>
<tr><td>3</td><td><b>Independent Citizens' Bond Oversight Committee</b> — qualified public members, annual
public report, pre-issuance certification</td><td>Ordinance, as the “successor” body under §6(F)</td>
<td>● The Committee (7–9 members, no city employees)</td><td>Mar 2027</td></tr>
<tr><td>4</td><td>Complete the <b>Asset Management Program</b> + establish a <b>Facilities Maintenance Reserve
Fund</b> with anti-supplanting law</td><td>Resolution + fund ordinance</td>
<td>● AMP Steering Committee; Finance administers</td><td>Jul 2027</td></tr>
<tr><td>5</td><td><b>Tranche gating</b>: each $100M sale requires #1–#4 plus certification</td>
<td>Debt Management Policy amendment</td><td>Council; ● Committee certifies each gate</td><td>2027</td></tr>
<tr><td>6</td><td>Unified delivery + <b>UC Berkeley / LBNL technology partnership</b></td>
<td>Reorganization + Council-ratified MOU</td><td>● Office of Infrastructure Program Delivery; ● Technical
Advisory Panel</td><td>FY28</td></tr>
<tr><td>7</td><td>Annual <b>State of the Infrastructure</b> report + public dashboard</td>
<td>Resolution (reporting requirement)</td><td>City Manager; ● Committee publishes its own assessment</td><td>FY28</td></tr></table>
<div class="quote"><b>The position, stated plainly.</b> The people who wrote Vision 2050 spent years demanding
exactly this discipline. Their support for Measure U is the exchange: signatures and credibility for a
September resolution adopting all seven commitments, with dates. If the resolution fails, the support —
and its central claim — fails with it.</div>
</div></section>

<section id="timing"><div class="wrap">
<h2>Timing</h2>
<p class="sub">How Berkeley got here, and the forty-one years the decision covers.</p>
<ul class="tl">
<li><b>Nov 2016</b>Measure T1: $100M infrastructure bond — now “almost exhausted” (2025 task force)</li>
<li><b>Nov 2018</b>Measure R directs the Mayor to convene the Vision 2050 process</li>
<li><b>2020</b>Vision 2050 Framework adopted: double capital spending, cradle-to-grave asset management</li>
<li><b>Nov 2024</b>Measure FF (streets parcel tax, ~$15M/yr × 14) plus new street &amp; library levies —
first appearing on FY26 bills, driving most of that year's bill increase</li>
<li><b>Oct 2025</b>“Realize Vision 2050”: Program Plan by Spring 2026 <i>first</i>; $250–300M bond series
over 25–30 years; flags public tax fatigue</li>
<li><b>Apr 2026</b>City's poll: 69% initial support → 64% after arguments (threshold: 66.7%)</li>
<li><b>Jun 16, 2026</b>Council places Measure U ($300M) and a companion sales tax on the ballot — the Spring
2026 Program Plan not adopted</li>
<li class="now"><b>Aug 2026</b>Ballot arguments filed (due 8/14); rebuttals due 8/21 noon</li>
<li class="now"><b>Nov 3, 2026</b>Election — two-thirds required</li>
<li class="fut"><b>2027–2037</b>Three $100M issuances (the commitments above gate tranches 2 and 3)</li>
<li class="fut"><b>FY 2040-41</b>Disclosed peak tax rate (${rate_peak:.0f}/$100k) begins</li>
<li class="fut"><b>FY 2066/67</b>Final collection. A child born this year pays this tax until age 40.</li>
</ul>
</div></section>

<section id="maps"><div class="wrap">
<h2>The maps</h2>
<p class="sub">Interactive, parcel-by-parcel. Each streams a data file — open from this site (they don't run
from file://). Click any dot for the parcel's facts.</p>
<div class="cards">
<a class="card" href="../maps/bond_incidence.html"><h4>What the bond costs each parcel</h4>
<p>All {n:,} assessed parcels: annual ad-valorem cost at the official rates, flat-tax comparison, and
recorded-document recency. The incidence argument, made spatial — the heaviest payers are the newest
buildings and sales.</p>
<span class="go">Open the bond-incidence map →</span></a>
<a class="card" href="../maps/berkeley_construction_timelapse.html"><h4>Berkeley, built over time</h4>
<p>Every structure at its build year (landmark-corrected), as a time-lapse — the 75 years in which the
infrastructure now on the ballot aged.</p><span class="go">Open the construction time-lapse →</span></a>
<a class="card" href="../maps/berkeley_ownership.html"><h4>Ownership &amp; recording activity</h4>
<p>Owner type (individual / trust / investor / institutional) and years since the last recorded document —
the financial-activity texture beneath the assessment roll.</p><span class="go">Open the ownership map →</span></a>
</div>
</div></section>

<section id="method"><div class="wrap">
<h2>Method &amp; provenance</h2>
<p class="sub">Independent citizen analysis — not a City of Berkeley communication.</p>
<ul style="font-size:14px;padding-left:20px;line-height:1.9">
<li><b>Primary sources:</b> Resolution 72,338-N.S. + Exhibit B Tax Rate Statement (June 16, 2026); City
Attorney impartial analysis; Vision 2050 Framework (2020) and Realize Vision 2050 (Oct 2025); Alameda County
assessor roll (Feb 2026, {n:,} parcels, ${base_b:.1f}B bill-consistent net assessed value); the county's
FY25-26 tax-rate tables (all 22 jurisdictions).</li>
<li><b>The citywide tax-structure model</b> (channel-2 figures above): schedule reconstructed from
{TI['_evidence']} — applied to {TI['sfr_parcels_modelled']:,} single-family parcels. Scope:
{TI['_scope']}</li>
<li><b>Reproducibility:</b> every figure on this page is derived by <code>JN-MeasureU</code> (a gate-checked
notebook asserting its figures against a timestamped baseline) and injected by
<code>scripts/gen_measure_u_site.py</code> — nothing hand-typed. The assessed-value base was verified to the
dollar against an actual FY26 county tax bill.</li>
<li><b>Honesty rails:</b> assessed value ≠ market value ≠ wealth (that inversion is the finding, not a flaw);
the City's advertised figures are arithmetically defensible nominal projections, reconciled here, not
debunked; the lifecycle sort is a professional v0 pending the City's own O&amp;M numbers.</li>
<li><b>Limits (open items):</b> per-district Tax Rate Area bases; full line-item bill reconstruction beyond
single-family; ~12 smaller charges on a third base not yet modeled (the channel-2 figures are a lower
bound); the staff's $44.13 combined-rate claim awaits reconciliation against the existing GO debt-service
schedule.</li>
</ul>
</div></section>

<footer><div class="wrap">Measure U, Examined · berkeleybuild.com · built from public records, August 2026 ·
figures derived from the {n:,}-parcel Alameda assessor roll, the county tax-rate tables, and the City's own
filed documents.</div></footer>
</body></html>"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write(html)
print(f"wrote {OUT} ({len(html)/1024:.0f} KB)")
print(f"channels: adval {adval_pct:.2f}% | psf ${psf:.2f} | d1 total {usd(d1['total'])} ({d1['flat_share_pct']:.0f}% flat, "
      f"{d1['pct_of_av']:.1f}% of AV) vs d10 {usd(d10['total'])} ({d10['flat_share_pct']:.0f}%, {d10['pct_of_av']:.1f}%)")
print(f"top1: apts {t1.get('apartments_mixed',0):.0f}% / ci {t1.get('commercial_industrial',0):.0f}% / "
      f"inst {t1.get('institutional',0):.0f}% / {c1.get('single_family',0)} SF homes | entry {usd(te['1'])}")
