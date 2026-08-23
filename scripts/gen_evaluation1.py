#!/usr/bin/env python3
"""gen_evaluation1.py — Evaluation No. 1 of the Vision 2050 working group:
answers to the four questions the op-ed poses about Measure U.

DERIVE, don't hand-type: every figure comes from data/reference/measure_u_project_list.json
(city costs + working-group classifications, provenance inside) and the gate-verified
JN-MeasureU baseline. Output: docs/berkeley2050/evaluation-1-measure-u.html — carries a
DRAFT banner until the group signs off; goes public only when John pushes AND the group
approves removing the banner.
"""
import json, os

PL = json.load(open("data/reference/measure_u_project_list.json"))
B = json.load(open("data/baselines/measure_u_reconciliation_baseline_2026-08-21.json"))
D, O = B["derived"], B["official"]
projects = PL["projects"]
usd = lambda x: f"${x:,.0f}"
M = lambda x: f"${x/1e6:.1f}M"

tot = sum(p["cost"] for p in projects)
cats = {c: sum(p["cost"] for p in projects if p["cat"] == c) for c in "ABC"}
recurs = [p for p in projects if p["recurs"]]
recurs_sum = sum(p["cost"] for p in recurs)
short = [p for p in projects if p["life"] == "short"]
short_sum = sum(p["cost"] for p in short)
partial = [p for p in projects if "partial" in p["notes"].lower() or "% funded" in p["name"].lower() or "funded)" in p["name"]]
# NRC benchmark on new/expanded capacity (category C)
nrc_lo, nrc_hi = cats["C"] * 0.02, cats["C"] * 0.04

CAT_LABEL = {"A": "A — durable, long-life, low carry", "B": "B — catch-up renewal of existing assets",
             "C": "C — new/expanded capacity (permanent new O&M)"}
CAT_COLOR = {"A": "#3b6fb6", "B": "#8a8f98", "C": "#e07b39"}
LIFE_LABEL = {"short": "&lt;25 yr", "medium": "25–40 yr", "long": "&gt;40 yr"}

rows = "\n".join(
    f'<tr><td>{p["name"]}</td><td>{p["dept"]}</td><td style="text-align:right">{M(p["cost"])}</td>'
    f'<td><span class="dot" style="background:{CAT_COLOR[p["cat"]]}"></span>{p["cat"]}</td>'
    f'<td>{LIFE_LABEL[p["life"]]}</td><td>{"⟳ yes" if p["recurs"] else "no"}</td>'
    f'<td class="small">{p["notes"]}</td></tr>'
    for p in sorted(projects, key=lambda x: -x["cost"]))

stack = "".join(f'<div style="width:{cats[c]/tot*100:.1f}%;background:{CAT_COLOR[c]}" title="{CAT_LABEL[c]}"></div>'
                for c in "ABC")
legend = " ".join(f'<span><span class="dot" style="background:{CAT_COLOR[c]}"></span>{CAT_LABEL[c]} — '
                  f'{M(cats[c])} ({cats[c]/tot*100:.0f}%)</span>' for c in "ABC")

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evaluation No. 1 — Measure U</title>
<meta name="description" content="The Vision 2050 working group's independent evaluation of Measure U: answers to the four questions on lifecycle, operating costs, sustainability, and oversight.">
<style>
:root{{--blue:#3b6fb6;--orange:#e07b39;--ink:#30343b;--gray:#8a8f98;--red:#b3261e;--bg:#fcfcfb;--card:#fff;--line:#e5e4e0;--muted:#6b7075}}
*{{box-sizing:border-box;margin:0}}
body{{background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.55}}
a{{color:var(--blue)}} .wrap{{max-width:1000px;margin:0 auto;padding:0 20px}}
.draft{{background:#b3261e;color:#fff;text-align:center;padding:8px;font-weight:700;letter-spacing:.06em}}
header.hero{{padding:44px 0 26px;border-bottom:1px solid var(--line)}}
.kicker{{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}}
.kicker a{{color:var(--muted);text-decoration:none}}
h1{{font-size:34px;line-height:1.14;margin:10px 0 12px;font-weight:800}}
.lede{{font-size:17px;color:#444;max-width:56em}}
section{{padding:38px 0;border-bottom:1px solid var(--line)}}
h2{{font-size:24px;margin-bottom:4px}} .q{{color:var(--muted);font-style:italic;margin-bottom:18px;max-width:56em}}
h3{{font-size:16.5px;margin:18px 0 8px}}
p.body{{max-width:58em;margin:10px 0;font-size:15px}}
.answer{{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--blue);border-radius:0 10px 10px 0;padding:16px 20px;margin:14px 0;font-size:15.5px;max-width:58em}}
.answer b:first-child{{color:var(--blue)}}
.stack{{display:flex;height:30px;border-radius:6px;overflow:hidden;margin:12px 0 6px;max-width:760px}}
.stack div{{height:100%}} .stack div+div{{border-left:2px solid var(--bg)}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;color:var(--muted);margin:6px 0 4px}}
.dot{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:middle}}
table{{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:14px;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}}
th{{background:#f4f3f0;text-align:left;padding:9px 10px;font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}}
td{{padding:8px 10px;border-top:1px solid var(--line);vertical-align:top}}
.small{{font-size:12.5px;color:var(--muted)}}
.note{{background:#f6f5f2;border-left:4px solid var(--orange);border-radius:0 8px 8px 0;padding:12px 16px;font-size:14px;margin:14px 0;color:#4a4a46;max-width:58em}}
footer{{padding:32px 0 56px;font-size:13px;color:var(--muted)}}
@media(max-width:760px){{table{{display:block;overflow-x:auto}}}}
</style></head><body>
<div class="draft">DRAFT — for review by the working group; not yet published</div>

<header class="hero"><div class="wrap">
<div class="kicker"><a href="index.html">← Berkeley 2050</a> · independent evaluation no. 1 · {PL["as_of"]}</div>
<h1>Four questions about Measure U — our first answers</h1>
<p class="lede">In our public statement we posed four questions about Measure U, Berkeley's $300 million
infrastructure bond, and promised to publish what we find. These are the working group's first answers,
built from the City's own project list, the official Tax Rate Statement, and standard asset-management
practice. Where the City publishes better figures, we will gladly replace ours — that was always the
point.</p>
</div></header>

<section><div class="wrap">
<h2>Question 1 — Long-life assets, or maintenance that comes due again?</h2>
<p class="q">How much of the bond funds long-life assets, and how much catches up on maintenance that
comes due again before the bonds are repaid in 2067?</p>
<div class="answer"><b>Answer:</b> Of the {M(tot)} project list, about <b>{cats['A']/tot*100:.0f}%
({M(cats['A'])}) is durable, long-life, low-carry investment</b> — sidewalks, the seawall, marine
piles, trails, accessibility. About <b>{cats['B']/tot*100:.0f}% ({M(cats['B'])}) is catch-up renewal
of existing assets</b>, and <b>{cats['C']/tot*100:.0f}% ({M(cats['C'])}) builds new or expanded
facilities</b>. Within the list, <b>{M(short_sum)} sits in assets or systems with design lives under
25 years</b> — artificial turf (~8–10 yr), play structures, elevators, building HVAC, and 911
electronics — which will be worn out and replaced, some of them twice, while the debt that bought them
is still being repaid.</div>
<div class="stack">{stack}</div>
<div class="legend">{legend}</div>
<p class="body">The classification is the working group's professional judgment, project by project
(full table below); the City has published no per-project design lives, so it can — and should —
improve on this table. A further caution: several waterfront items are only 20–60% funded here, so
their completion depends on grants not yet secured.</p>
</div></section>

<section><div class="wrap">
<h2>Question 2 — What new operating obligations, paid from what?</h2>
<p class="q">What annual operating and maintenance obligations do the funded projects create, and from
what revenue source will those be paid?</p>
<div class="answer"><b>Answer:</b> <b>No official figure exists.</b> Neither the measure, the staff
reports, nor the project list states a single project's estimated operating cost or names an operating
revenue source. Applying the standard planning benchmark — annual maintenance of 2–4% of replacement
value (National Research Council, <i>Committing to the Cost of Ownership</i>) — to the {M(cats['C'])}
of new and expanded facilities alone implies roughly <b>{M(nrc_lo)}–{M(nrc_hi)} per year of new,
permanent operating obligation</b>, before counting the larger footprints of the replacement fire
stations. The only identified destination for those costs is the General Fund — which the measure's
own findings describe as facing $31 million and $29 million deficits in the next two fiscal years.</div>
<p class="body">This is the answer the City can improve fastest, and the one that matters most: a
one-page table — each project's expected annual O&amp;M and the fund that carries it — would convert
our benchmark estimate into fact. Until it exists, every new facility is a promise the operating budget
has not yet agreed to keep.</p>
</div></section>

<section><div class="wrap">
<h2>Question 3 — Sustainability and resilience, project by project</h2>
<p class="q">How does each major project perform on sustainability, including lifetime energy and water
use and resilience to flood, fire, extreme heat, and earthquake risk?</p>
<div class="answer"><b>Answer: partially designed-in, nowhere measured.</b> The measure's one binding
sustainability element is strong: <b>all-electric construction</b> and replacement of natural-gas
systems, city-wide, with Council-only exceptions. Real resilience investments are present — the South
Cove seawall and Marina Boulevard work address sea-level rise directly; all three fire facilities
include photovoltaic and battery systems for outage resilience; the seismic items harden two civic
buildings (partially). But <b>no project carries a published Envision score</b>, although the City
screened project <i>categories</i> with Envision-based criteria — and the categories Vision 2050
ranked highest for climate resilience (storm drains and green infrastructure, undergrounding on
evacuation routes, the urban forest) are <b>absent from the list entirely</b>. One item runs the wrong
direction: artificial turf carries heat-island, lifecycle, and disposal costs the list does not
discuss.</div>
<p class="body">Our recommendation is procedural, not adversarial: score each funded project on
Envision — the framework the City already uses — and publish the scores before the first bond sale.
Sustainability claimed in categories and delivered in projects are two different things, and only the
second can be audited.</p>
</div></section>

<section><div class="wrap">
<h2>Question 4 — Who oversees, audits, and reports?</h2>
<p class="q">Who oversees, audits, and reports publicly on project progress — and on what schedule?</p>
<div class="answer"><b>Answer, from the measure's own text:</b> the Parks, Recreation &amp; Waterfront
Commission and the Transportation &amp; Infrastructure Commission (or successors) report annually;
the City Manager reports annually within the budget process; and the City Auditor audits expenditures
<b>at least once every three years</b>. That is the entire structure: <b>no dedicated bond oversight
committee, no pre-issuance certification, no published reporting calendar.</b> By comparison, school
bonds under Proposition 39 require an independent citizens' oversight committee as a matter of law,
and Berkeley's own Measure T1 experience showed how quickly project lists drift without one.</div>
<p class="body">The measure's §6(F) assigns oversight to the two commissions <i>"or their successors"</i>
— which means the Council can create a qualified, independent citizens' oversight committee by ordinary
ordinance, without amending the measure. We recommend exactly that, with one addition that costs
nothing and guarantees everything else: <b>certification before each bond sale</b> that the sale
conforms to an adopted Program Plan. Oversight that begins after the money is spent is bookkeeping;
oversight that gates the next tranche is governance.</p>
</div></section>

<section><div class="wrap">
<h2>The project list, classified</h2>
<p class="q">The City's {len(projects)} funded line items ({M(tot)}), sorted by cost — with the working
group's category, design-life class, and recurs-before-2067 flag. ⟳ marks assets expected to need
replacement again before the final debt payment in FY 2066/67.</p>
<table>
<tr><th>Project</th><th>Dept</th><th>Cost</th><th>Cat</th><th>Design life</th><th>Recurs?</th><th>Notes</th></tr>
{rows}
</table>
<p class="small" style="margin-top:8px">Costs and descriptions: City of Berkeley project list.
Classifications: working group v0 judgment — corrections welcome, especially the City's own.</p>
</div></section>

<section><div class="wrap">
<h2>Method &amp; sources</h2>
<p class="body">City project list (council packet, 36 items, {M(tot)}); Resolution 72,338-N.S. and its
Tax Rate Statement (final collection FY 2066/67; $610M total debt service); the {D['n_parcels']:,}-parcel
county assessment roll (2026-27, ${D['total_av_b']:.1f}B); NRC maintenance benchmark (2–4% of
replacement value annually); Proposition 39 (Ed. Code §15278) for the school-bond oversight comparison.
Everything derived and re-runnable; dataset published at
<a href="../../data/reference/measure_u_project_list.json">measure_u_project_list.json</a> in our
repository. We are volunteer, independent advisors to the City, unaffiliated with any campaign.</p>
</div></section>

<footer><div class="wrap">Vision 2050 working group · independent evaluation no. 1 ·
berkeleybuild.com/berkeley2050 · corrections welcome, the City's most of all.</div></footer>
</body></html>"""

OUT = "docs/berkeley2050/evaluation-1-measure-u.html"
open(OUT, "w").write(html)
print(f"wrote {OUT} ({len(html)/1024:.0f} KB)")
print(f"totals: {M(tot)} | A {M(cats['A'])} ({cats['A']/tot*100:.0f}%) B {M(cats['B'])} "
      f"({cats['B']/tot*100:.0f}%) C {M(cats['C'])} ({cats['C']/tot*100:.0f}%)")
print(f"short-life (<25yr) {M(short_sum)} across {len(short)} items | recurs-flagged {M(recurs_sum)} across {len(recurs)}")
print(f"NRC O&M on C: {M(nrc_lo)}-{M(nrc_hi)}/yr")
