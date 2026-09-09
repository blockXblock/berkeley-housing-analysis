#!/usr/bin/env python3
"""build_jn_feasibility.py — generator for notebooks/v4/JN-Feasibility.ipynb.

A TEACHING notebook: "Build UrbanSim's development-feasibility model, in the open, the Datasette way."
It walks a student through assembling a parcel table from open civic data, borrowing UrbanSim's schema
ideas, reimplementing its SqFtProForma pro-forma transparently (~15 legible lines, cited, BSD-3), and
running a baseline-vs-upzone scenario on the Elmwood commercial strip — then confronts them with the
lesson that the result is dominated by CALIBRATION, not code.

Markdown-in-source (the text cells ARE the deliverable). Every figure is DERIVED and gated against an
external timestamped baseline (data/baselines/feasibility_baseline_2026-09-08.json) — never hardcoded.

Run:  python scripts/v4/build_jn_feasibility.py     # (re)writes the .ipynb  (run from repo root)
"""
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

nb = new_notebook()
C = []
def md(s): C.append(new_markdown_cell(s.strip()))
def code(s): C.append(new_code_cell(s.strip()))

md(r"""
# JN-Feasibility — Build UrbanSim's pro-forma, in the open

**What this teaches.** How to build the core of an UrbanSim-style land-use model — *"if we change the
zoning here, does development actually happen?"* — but **openly and legibly**: open civic data → a few
SQLite tables → a 15-line pro-forma you can read → an explorable Datasette dataset. No gated regional
data, no 1,268-line engine, no black box.

**The worked question (John's Elmwood thesis):** if Berkeley raises the height/FAR limit on the ~5-acre
Elmwood *commercial* strip, does housing actually pencil out there — and how much? We answer it with the
same method UrbanSim uses, reimplemented so every assumption is visible.

> ⚠️ **This is a METHOD DEMO, not a citable number.** Every calibration input (rents, construction cost,
> cap rate, and the baseline/upzone zoning envelopes) is a **labeled placeholder**. Land cost uses the
> *assessed* value — a Prop-13 proxy that understates market land, so this **overstates** feasibility.
> Read the result as "does the machinery work + roughly which parcels flip," never as a unit count.

> **Prior art:** UrbanSim (Paul Waddell, UC Berkeley CED / UDST), `SqFtProForma`
> ([BSD-3 source](https://github.com/UDST/developer/blob/master/developer/sqftproforma.py)). We reuse the
> **method**, not the code — a transparent reimplementation legible enough to teach.

> **Discipline:** every figure is DERIVED from the data and gated against an external timestamped baseline
> (`data/baselines/feasibility_baseline_2026-09-08.json`). *Structural* figures (parcel/acre counts) are
> stable; *calibration* figures move with the assumptions. A legitimate change = **append a new baseline**,
> never edit a magic number.
""")

md(r"""
## Data lineage — sources → tables → result

```mermaid
graph LR
  ASR[Alameda assessor<br/>berkeley.db: Land $, UseCode] --> P[parcel table<br/>lot area from GEOMETRY]
  TP[taxparcels geojson<br/>polygons + Units] --> P
  NBH[neighborhood polygons] --> P
  P --> X[building-type crosswalk<br/>UrbanSim borrowing #1]
  X --> COM[commercial strip parcels]
  Z[zoning table: baseline + upzone<br/>UrbanSim borrowing #2] --> PF
  CAL[calibration: rent / cost / cap-rate<br/>PLACEHOLDER] --> PF
  COM --> PF[pro-forma<br/>SqFtProForma method]
  PF --> FIG[feasibility figures<br/>baseline vs upzone]
  FIG --> GATE[baseline gate]
  FIG --> DS[(Datasette:<br/>parcels · zoning · results)]
```

The whole model is four small tables and one function. That is the point: a student can hold the entire
thing in their head, and every arrow is an open, inspectable step.
""")

md(r"""
## Step 1 — Assemble the open parcel table

**Plan:** join what open civic data gives us into one parcel table: geometry (parcel polygons), current
units, land value, and use code. **Teaching point:** compute **lot area from the geometry**, not from the
assessor's `LotSize` column — we already found `LotSize` is mostly 0/unreliable. The geometry never lies
about area.
""")
code(r"""
import sqlite3, json, sys, warnings
import pandas as pd, geopandas as gpd
warnings.filterwarnings("ignore"); sys.path.insert(0, "scripts")

tp = gpd.read_file("data/raw/berkeley_taxparcels_2026-08-12.geojson")[["APN", "Units", "UseCode", "geometry"]]
tp["lot_sqft"] = tp.to_crs(2227).geometry.area          # EPSG:2227 = CA zone III, US survey feet
tp["Units"] = pd.to_numeric(tp.Units, errors="coerce").fillna(0)

db = sqlite3.connect("databases/berkeley.db")
land = pd.read_sql("SELECT APN, Land, SitusStree, SitusStr_1 FROM parcels", db)
land["Land"] = pd.to_numeric(land.Land, errors="coerce")
tp = tp.merge(land, on="APN", how="left")

nbh = gpd.read_file("data/reference/berkeley_neighborhoods.geojson").to_crs(tp.crs)
elpoly = nbh[nbh.Name.astype(str).str.contains("lmwood", case=False)].dissolve().geometry.iloc[0]
elm = tp[tp.geometry.centroid.within(elpoly)].copy()
print(f"Elmwood parcels assembled: {len(elm)}  (lot area from geometry, land $ from assessor)")
""")

md(r"""
## Step 2 — The building-type problem, and UrbanSim borrowing #1

**Problem:** the raw assessor `UseCode` is a *weak* signal — e.g. `73xx` in Elmwood is **condominiums**,
not commercial. Filtering on raw codes gets you the wrong parcels.

**UrbanSim's fix (borrowing #1):** a **two-level crosswalk** — map many detailed codes into a few analytic
buckets, as a *maintained lookup*, not a one-off filter. Here we bucket by the leading digit and pull the
**commercial** parcels (the strip John's argument is about).

**Honest caveat we surface, not hide:** "UseCode 3x = commercial" is approximate — it captures more than
the true ~5-acre College retail core (a spatial cut would refine it). We report the acreage so the reader
sees the over-capture.
""")
code(r"""
def general_bucket(uc):
    p = (str(uc).lstrip("0")[:1] or "0")
    return {"1": "residential_sf", "2": "residential_small", "3": "commercial", "4": "industrial",
            "6": "institutional", "7": "residential_multi_or_condo", "9": "misc"}.get(p, "other")
elm["bucket"] = elm.UseCode.map(general_bucket)

comm = elm[elm.bucket == "commercial"].copy()
comm = comm[(comm.lot_sqft > 200) & comm.Land.notna()]
comm["addr"] = (comm.SitusStree.fillna("").astype(str).str.strip() + " "
                + comm.SitusStr_1.fillna("").astype(str).str.strip()).str.strip()
print(f"commercial parcels: {len(comm)}  ({comm.lot_sqft.sum()/43560:.1f} acres)")
print("NOTE: 3x is approximate — broader than the 5.3-ac College retail core; a spatial cut refines it.")
comm[["addr", "UseCode", "lot_sqft", "Land", "Units"]].head()
""")

md(r"""
## Step 3 — Zoning as a table, and UrbanSim borrowing #2

**UrbanSim's fix (borrowing #2):** store the zoning *envelope* as its own table with a `scenario` column —
never as a column welded onto the parcel. Then **an upzoning is a new row, not an edit**, and baseline-vs-
proposal is a table swap. (This mirrors UrbanSim's `conditional_upzone`, which overrides the baseline via
a `max()`.)

Both envelopes below are **PLACEHOLDERS** — the real Elmwood C-E limits and the actual proposal must be
substituted before any claim.
""")
code(r"""
zoning = pd.DataFrame([
    {"scenario": "baseline",       "max_far": 2.0, "max_height_ft": 30.0},   # PLACEHOLDER: ~2-3 stories, today
    {"scenario": "elmwood_upzone", "max_far": 3.5, "max_height_ft": 55.0},   # PLACEHOLDER: ~5 stories, proposal
])
zoning
""")

md(r"""
## Step 4 — The pro-forma (the whole model is one function)

This is a transparent reimplementation of UrbanSim's `SqFtProForma`. The math, straight from the
[source](https://github.com/UDST/developer/blob/master/developer/sqftproforma.py):

- `FAR = min(max_far, (max_height / ft_per_story) × coverage)` — **zoning binds** the buildable ratio
- `bulk = FAR × lot_sqft` — gross buildable floor area
- `cost = bulk × cost_per_sqft(height-tier) × financing + land_cost`
- `noi = bulk × (1 − parking) × efficiency × rent × (1 − opex)` — **net** operating income
- `value = noi ÷ cap_rate` — income, capitalized
- `profit = value − cost` — **feasible if > 0**

**The opex line is load-bearing and was missing until 2026-09-08.** A cap rate is applied to NET
operating income, not to gross rent. Capitalising gross rent overstated value by `1/(1−opex)` — about
**1.5×** at a normal 35% apartment opex ratio — which made *every* parcel pencil regardless of land and
hid what the model was actually sensitive to. See the sensitivity note after Step 5.

Every constant is a **labeled placeholder**. A student changes one and re-runs — that is the exercise.
""")
code(r"""
# CALIBRATION — LABELED PLACEHOLDERS (replace with real Berkeley data / Waddell before any claim)
RENT_SQFT_YR, CAP_RATE, FINANCING = 45.0, 0.045, 1.10     # ~$3.75/sqft/mo GROSS rent; 4.5% cap; soft-cost mult
OPEX_RATIO = 0.35                                         # operating expenses as a share of gross rent
PARKING_LOSS, EFFICIENCY, UNIT_SQFT = 0.15, 0.82, 950     # floor-area losses; avg dwelling incl common
FT_PER_STORY, COVERAGE = 11.0, 0.72                       # height->stories; footprint share of lot
def cost_per_sqft(h): return 400 if h <= 45 else 560 if h <= 85 else 720   # wood -> podium -> highrise

def proforma(lot_sqft, land_cost, max_far, max_height):
    far = min(max_far, (max_height / FT_PER_STORY) * COVERAGE)    # zoning binds
    bulk = far * lot_sqft
    cost = bulk * cost_per_sqft(max_height) * FINANCING + land_cost
    rentable = bulk * (1 - PARKING_LOSS) * EFFICIENCY
    noi = rentable * RENT_SQFT_YR * (1 - OPEX_RATIO)              # cap rates apply to NOI, not gross rent
    value = noi / CAP_RATE
    return value - cost, rentable / UNIT_SQFT                     # (profit, potential units)
""")

md(r"""
## Step 4a — Why the opex line changes the answer (and what a cap rate actually means)

The single line `noi = rentable * RENT_SQFT_YR * (1 - OPEX_RATIO)` moved this model from
"everything pencils" to "half of it pencils, and the upzone makes it worse." It is worth understanding
exactly why, because the mistake it corrects is the most common error in amateur pro-formas.

**An income property's arithmetic runs down a ladder, and every rung loses money:**

| rung | what it is | why it shrinks |
|---|---|---|
| Gross Potential Rent | every unit, full year, asking rent | the number in a listing |
| − vacancy & collection loss | 5%ish | turnover gaps, non-payment |
| = Effective Gross Income | what actually arrives | |
| − **operating expenses** | **30–40%** | see below |
| = **Net Operating Income (NOI)** | what the building earns | **this is what gets valued** |

**A cap rate is defined on NOI.** "4.5% cap" means an investor pays $100 for $4.50 of *NOI* — not
$4.50 of rent. Capitalising gross rent is the same category error as valuing a restaurant at an
earnings multiple applied to its food sales.

**Where the 30–40% goes**, and why California is at the high end:
- **Property tax** — Proposition 13 assesses *new construction at market*, so a new building pays
  roughly 1.25% of full value every year, forever. This is the largest single line, and it is the one
  most often forgotten by people who think Prop 13 makes California cheap. It does — for the *old*
  building being replaced, not the new one.
- **Insurance** — rising steeply across California; no longer a rounding error.
- **Management** — 4–5% of EGI for a professional operator.
- **Maintenance, turnover, utilities, reserves** — the rest.
- Berkeley adds its own: rent-board registration fees, seismic obligations, and a local regulatory
  overhead that is small per unit but real.

**The arithmetic of the fix.** At `OPEX_RATIO = 0.35`, capitalised value falls from `$45/0.045 =
$1,000` per rentable sqft to `$29.25/0.045 = $650`. That is a **35% haircut on the asset**, and the
developer's entire margin lives inside a band far narrower than 35%. Which is why removing the error
does not shave the result — it inverts it.

**The lesson generalises past this notebook:** when a model says *everything* is feasible, the fault is
almost never in the world. It is in the revenue line.
""")

md(r"""
## Step 4b — How a developer actually decides (the model's `profit > 0` is not how)

This notebook asks `profit > 0`. **No developer asks that.** A deal that clears zero by a dollar is a
deal nobody funds. Understanding the real test explains why "feasible" parcels sit undeveloped for
decades, which is the thing a zoning debate most needs to explain.

**1. Yield on cost, compared to the exit cap rate.** The developer computes

> `yield on cost = stabilised NOI ÷ total development cost`

and compares it to the cap rate the finished building would sell at. The difference is **the spread**,
quoted in basis points. Build at a 6.0% yield on cost and sell at a 4.5% cap and you have a **150 bps
spread** — that gap *is* the profit, because it is what turns cost into value.

**The rule of thumb: you need 100–150 bps.** Below that, nobody takes construction risk — the same
money can buy an existing, leased, de-risked building at the cap rate and skip three years of
uncertainty. **A project can be wildly "profitable" by `profit > 0` and still be uninvestable**, and
most marginal projects are exactly there.

**2. Residual land value — developers solve the equation backwards.** They do not ask "can I afford
this land?" They fix the required yield and solve for what the land *can* be worth:

> `residual land value = (stabilised NOI ÷ required yield on cost) − construction − soft costs − fees − profit`

If the residual comes in under what the owner will accept, **there is no deal at any zoning**. This is
the mechanism behind the result in Step 8: Elmwood's binding constraint was never the land price the
model charged, it was that the revenue could not support the building in the first place.

**3. The capital stack imposes its own tests, and each is a veto.**
- **Construction lender:** 60–65% loan-to-cost, and a **debt service coverage ratio** of 1.20–1.25 at
  stabilisation. Fail the DSCR and the loan shrinks regardless of profit.
- **Equity:** 15–20% IRR and a 1.6–2.0× multiple over roughly five years. Equity is the expensive
  money and it sets the hurdle.
- **Both must clear simultaneously.** A deal can pass the lender and fail equity, and it is dead.

**4. Risk is priced, not assumed away.** Entitlement risk (will it be approved, and after how many
hearings), construction risk (fixed-price contract or not), lease-up risk (how fast to stabilisation),
and interest-rate risk on the exit cap. Each widens the spread a developer demands.

**So read this notebook's `feasible` column as a *ceiling*, not a forecast.** It marks parcels that
are not obviously impossible. The set that actually gets built is a strict — and much smaller — subset.
""")

md(r"""
## Step 5 — Run baseline vs. upzone, derive the figures
""")
code(r"""
for _, z in zoning.iterrows():
    r = comm.apply(lambda p: proforma(p.lot_sqft, p.Land, z.max_far, z.max_height_ft),
                   axis=1, result_type="expand")
    comm[z.scenario + "_profit"], comm[z.scenario + "_units"] = r[0], r[1]

comm["base_feas"] = comm.baseline_profit > 0
comm["up_feas"]   = comm.elmwood_upzone_profit > 0
comm["flip"]      = comm.up_feas & ~comm.base_feas               # feasible ONLY under the upzone
net = lambda col, mask: int(((comm[col] - comm.Units).clip(lower=0) * mask).sum())

fig = {
    "elmwood_parcels":    int(len(elm)),
    "commercial_parcels": int(len(comm)),
    "commercial_acres":   round(comm.lot_sqft.sum() / 43560, 1),
    "baseline_feasible":  int(comm.base_feas.sum()),
    "baseline_net_units": net("baseline_units", comm.base_feas),
    "upzone_feasible":    int(comm.up_feas.sum()),
    "upzone_net_units":   net("elmwood_upzone_units", comm.up_feas),
    "upzone_flips":       int(comm.flip.sum()),
    "upzone_flip_units":  net("elmwood_upzone_units", comm.flip),
}
fig
""")

md(r"""
## Step 6 — Gate: derive, then assert against a timestamped baseline

We never hardcode the answer in the logic. We compute it, then compare to an external baseline file. We
split **structural** figures (parcel/acre counts — stable given the same parcel snapshot, hard-asserted)
from **calibration** figures (feasibility counts — they *move* when the assumptions change). If a
calibration figure drifts, that is not a bug: **append a new baseline**, don't edit the number.
""")
code(r"""
base = json.load(open("data/baselines/feasibility_baseline_2026-09-08.json"))
STRUCTURAL = {"elmwood_parcels", "commercial_parcels", "commercial_acres"}
bad = []
for k, v in fig.items():
    want = base["figures"][k]
    tol = 0 if k in STRUCTURAL else 1e-6
    if abs(v - want) > tol:
        bad.append((k, v, want))
if bad:
    print("GATE MISMATCH — diagnose (computed vs baseline):")
    for k, v, w in bad:
        print(f"  {k}: computed {v} vs baseline {w}")
    print("If calibration legitimately changed, APPEND a new timestamped baseline — never edit the number.")
else:
    print(f"GATE PASS — all {len(fig)} figures match baseline (sha {base['git_sha']}).")
    print("Structural figures are stable; calibration figures move with the assumptions in Step 4.")
""")

md(r"""
## Step 7 — Visualize: does housing pencil, baseline vs upzone?

📝 *Before:* the bars show, for each scenario, how many commercial parcels "pencil" (profit > 0) and the
potential net-new units. Watch whether the upzone **adds feasible parcels** or merely **piles more units
onto parcels that already penciled**.
""")
code(r"""
try:
    import plotly.graph_objects as go
    S = ["baseline", "elmwood_upzone"]
    feas  = [fig["baseline_feasible"], fig["upzone_feasible"]]
    units = [fig["baseline_net_units"], fig["upzone_net_units"]]
    f = go.Figure()
    f.add_bar(name="parcels that pencil", x=S, y=feas, marker_color="#7fcdbb")
    f.add_bar(name="net new units (potential)", x=S, y=units, marker_color="#e31a1c", yaxis="y2")
    f.update_layout(
        title="Elmwood commercial strip — does housing pencil? (PLACEHOLDER calibration)",
        yaxis=dict(title="parcels feasible"),
        yaxis2=dict(title="net new units", overlaying="y", side="right"),
        barmode="group", template="plotly_white", height=430,
        legend=dict(orientation="h", y=1.12))
    f.show()
except Exception as e:
    print("plotly unavailable — figures:", {k: fig[k] for k in
          ["baseline_feasible","baseline_net_units","upzone_feasible","upzone_net_units","upzone_flips"]})
""")
md(r"""
📝 *After — what this chart could MISLEAD about:* (1) the y-axes are **truncated/dual** — do not read the
red and green bars against each other. (2) These units are a **potential ceiling**, not a forecast — they
assume every feasible parcel redevelops fully to housing. (3) The parcels are **occupied retail** —
"feasible" means *a developer could profit by demolishing the shops*, which is a policy choice, not a free
lunch. (4) Above all: the result is **calibration-dominated** — see Step 8.
""")

md(r"""
## Step 7a — The missing variable: time, and the cost of assembling money

Every number so far is **static**. The model builds the building instantly. Real projects spend years
between "the parcel pencils" and "someone pours concrete," and **that interval has a price the
pro-forma above charges nobody for.**

**Why the delay is structural, not incompetence.** A market-rate deal in Berkeley needs entitlement
(commonly 1–3 years through Zoning Adjustments Board, design review, and any appeal), then building
permit, then 18–30 months of construction. But a project with any affordability — which in Berkeley is
most of them, via inclusionary requirements or density-bonus concessions — must **stack subsidy from
several agencies at once**:

| layer | typical sources | rhythm |
|---|---|---|
| Federal | **LIHTC 9%** (competitive; roughly one in three or four applications wins) or **4% credits + tax-exempt bonds** via CDLAC, now itself oversubscribed | annual or a few rounds a year |
| State | AHSC, IIG, MHP, HHAP, No Place Like Home | own rounds, own scoring |
| County | Alameda County A1 bond funds | periodic NOFAs |
| City | Berkeley Housing Trust Fund (Measure U1 revenue), Measure O | periodic NOFAs |

**Four features of that table generate years, and they compound:**

1. **Rounds are discrete.** Miss a filing window and the *minimum* cost is twelve months. Not a delay
   in the deal — a delay in being allowed to ask.
2. **Sources must close together.** Each wants the others committed first; a single late award holds
   the whole stack.
3. **Each has its own readiness bar** — site control, entitlement, a certain design maturity — so the
   applicant spends real money *before* learning whether the ask succeeds.
4. **Losing a competitive round is normal, not exceptional.** A 9% LIHTC application that scores just
   below the line re-applies next year, with a full year of escalation in the meantime.

**Assembling four to eight sources routinely takes two to five years** — on top of entitlement.

**What that costs, in three ways at once:**
- **Carrying cost.** Land and predevelopment equity are committed and earning nothing. That capital's
  opportunity cost is 8–12% a year.
- **Escalation.** Construction costs rise 4–6% a year. The building you priced is not the building you
  will buy.
- **Expiry risk.** Entitlements and awards lapse; some must be re-won on new rules.

These are multiplicative, not additive: **three years at a 10% cost of capital is a 1.33× multiplier on
everything committed at the start** — and it is applied to a margin that Step 4b said lives inside a
100–150 bps band.

**This is the honest answer to "why doesn't it get built if it pencils?"** Often the static pro-forma is
right and the *dynamic* one is not. The cell below charges the model for time and shows how few years it
takes to erase the Elmwood result entirely.
""")
code(r"""
# TIME COST — derived from the same constants as Step 4, nothing hardcoded.
# A delay of N years: construction costs escalate, and committed capital earns nothing.
ESCALATION, CARRY = 0.05, 0.10          # cost inflation/yr; opportunity cost of committed capital/yr

def proforma_delayed(lot_sqft, land_cost, max_far, max_height, years):
    far  = min(max_far, (max_height / FT_PER_STORY) * COVERAGE)
    bulk = far * lot_sqft
    build = bulk * cost_per_sqft(max_height) * FINANCING * (1 + ESCALATION) ** years
    carried_land = land_cost * (1 + CARRY) ** years          # land tied up, earning nothing
    rentable = bulk * (1 - PARKING_LOSS) * EFFICIENCY
    value = rentable * RENT_SQFT_YR * (1 - OPEX_RATIO) / CAP_RATE
    return value - (build + carried_land)

rows = []
for yrs in [0, 1, 2, 3, 4, 5]:
    prof = comm.apply(lambda p: proforma_delayed(p.lot_sqft, p.Land, 2.0, 30.0, yrs), axis=1)
    psf  = prof / comm.lot_sqft                      # profit per sqft of LOT — the margin, not a count
    rows.append({"years_of_delay": yrs,
                 "baseline_feasible": int((prof > 0).sum()),
                 "share_of_109": round(100 * (prof > 0).mean(), 1),
                 "median_margin_$_per_lot_sqft": round(psf.median(), 2)})
delay = pd.DataFrame(rows)
print(delay.to_string(index=False))
print(f"\nEscalation {ESCALATION:.0%}/yr on construction, {CARRY:.0%}/yr carry on land.")
print("The COUNT falls off a cliff; the MARGIN column shows why — it was never far from zero.")
print("Read this against Step 7: the upzone was already infeasible at year 0.")
""")
md(r"""
📝 **What the delay table shows, and what it must not be read as saying.**

The feasible count does not decay gently — it **falls off a cliff between year 0 and year 1**, and the
margin column explains why. At year 0 the median parcel clears by only a few dollars per square foot of
lot; one year of escalation on ~$864/sqft of construction costs more than that entire margin. **The
cliff is the finding.** A result that survives on a margin this thin was never robust, and reporting
only the binary count would have hidden that.

It falls because **cost escalates while revenue in this model does not**. That asymmetry is the point but also the caveat: rents rise too, and a fair dynamic
model would trend both. Treat the table as *the shape of the risk*, not a forecast — a project whose
margin sits in a 100–150 bps band cannot absorb several years of one-sided escalation, and the years
are not optional when the money must come from six agencies with their own calendars.

**The policy reading.** Two levers change this picture, and only one of them is zoning:
- **Zoning** decides whether a building is *legal*. Step 8 shows the Elmwood upzone does not make it
  *financeable* — at these construction costs it makes it worse.
- **Process time** decides whether a financeable building survives long enough to exist. Aligning
  application windows, granting by-right approval where a project already conforms, and shortening the
  gap between award rounds all attack the multiplier directly.

For the marginal project, **the calendar is a bigger lever than the height limit** — and unlike the
height limit, it costs nothing to grant.
""")

md(r"""
## Step 8 — The real lesson: the model is only as good as its calibration

**The upzone flips zero parcels. That zero is robust — but not for the reason first supposed, and the
story of how it was tested is the lesson.**

An earlier version of this notebook predicted: *"Land cost = assessed value; Prop-13 assessed land is far
below market, so acquisition looks cheap and everything pencils. Real market land → far fewer
baseline-feasible parcels."* **That prediction was tested on 2026-09-08 and is false.**

A land-value surface was built from the **4,187 Berkeley parcels transferred since 2024** — Prop-13 resets
assessment to market on sale, so recent sales are a market observation. Elmwood came out at **$63.98/sqft
market against $25.63 assessed, 2.5×**. Substituting it changed the answer by **one parcel**.

Solving `profit = 0` for land shows why: break-even land is **$505/sqft** under baseline zoning. Assessed
and market land are both **1–2% of it**. Land was never binding.

**What was binding was an error in the math, not the calibration:** `value = rentable × rent ÷ cap_rate`
capitalised **gross** rent. Cap rates apply to **NOI**. At 4.5% that implied $1,000 per rentable sqft against
$440 all-in construction — a 2.3× ratio under which everything pencils no matter what land costs. The
`OPEX_RATIO` line in Step 4 is the fix.

With opex deducted the strip becomes knife-edge at baseline (break-even land ≈ $26/sqft against a $25.63
assessed basis) and the upzone break-even goes **negative**: 55ft forces podium construction at $560/sqft,
and the extra FAR does not cover the cost step. **So the zero survives the fix, with its meaning inverted** —
before, nothing flipped because everything already pencilled; after, nothing flips because upzoning to 55ft
is counterproductive at these construction costs.

Two caveats still standing:
1. **The commercial set is too broad** (UseCode 3x ≈ the acreage printed in Step 2, vs the true ~5.3-ac
   strip). A spatial cut to the College frontage tightens it.
2. **`OPEX_RATIO = 0.35` is itself a placeholder.** The result is knife-edge around it — 30% pencils, 35%
   does not — so this input now deserves the scrutiny land wrongly received.

**This is the transferable lesson of every land-use model, UrbanSim included:** the code is small and
cheap; the *calibration* — real construction costs, rents by use, cap rate, and land acquisition — is the
whole ballgame. A student who internalizes that has learned the most important thing about these models.
""")

md(r"""
## Step 9 — The Datasette way: make it an explorable dataset, not a black box

The entire model is four tables and one function — so publish the tables and let anyone *query* the model
in a browser, no Python required:

- `parcels` (APN, lot_sqft, Land, Units, bucket, addr)
- `zoning` (scenario, max_far, max_height_ft)
- `feasibility_results` (APN, scenario, profit, units, feasible)

Then a student explores by SQL — e.g.:

```sql
-- which parcels flip to feasible only under the upzone?
SELECT p.addr, p.lot_sqft, r.units
FROM feasibility_results r
JOIN parcels p USING (APN)
WHERE r.scenario = 'elmwood_upzone' AND r.feasible
  AND p.APN NOT IN (SELECT APN FROM feasibility_results
                    WHERE scenario = 'baseline' AND feasible)
ORDER BY r.units DESC;
```

Change one calibration constant, re-run this notebook, re-publish — and the *same query* now tells a
different story. The model becomes a thing you **interrogate**, not a thing you **trust**. That is the
open/Datasette contrast with UrbanSim's gated data + heavyweight engine.
""")
code(r"""
# emit the Datasette-ready tables (this is what a student would publish + query)
import os
os.makedirs("scratch/2026-08-14", exist_ok=True)
res = []
for scen in ["baseline", "elmwood_upzone"]:
    for _, p in comm.iterrows():
        res.append({"APN": p.APN, "scenario": scen,
                    "profit": round(p[scen + "_profit"]), "units": round(p[scen + "_units"], 1),
                    "feasible": int(p[scen + "_profit"] > 0)})
import pandas as pd
pd.DataFrame(res).to_csv("scratch/2026-08-14/feasibility_results.csv", index=False)
comm[["APN", "addr", "lot_sqft", "Land", "Units", "bucket"]].to_csv("scratch/2026-08-14/feasibility_parcels.csv", index=False)
zoning.to_csv("scratch/2026-08-14/feasibility_zoning.csv", index=False)
print("wrote 3 Datasette-ready tables to scratch/2026-08-14/ (parcels, zoning, results)")
""")

md(r"""
## Step 10 — Calibration checklist (placeholder → real) & next steps

To turn this method demo into a defensible Elmwood analysis, replace each placeholder with a real source:

| Input | Placeholder here | Real source needed |
|---|---|---|
| Baseline & upzone zoning | FAR 2→3.5, 30→55 ft | **Berkeley C-E district limits + the actual proposal** |
| Land / acquisition cost | assessed `Land` (Prop-13) | recent commercial **sale comps** on the strip |
| Residential rent | $45/sqft/yr flat | Berkeley **market rents by unit type** |
| Construction cost | 3-tier $/sqft | Berkeley **cost data by structure type** |
| Cap rate | 4.5% | market cap rate for Berkeley multifamily |
| Commercial parcel set | UseCode 3x (~broad) | **spatial cut** to the College retail frontage |

**The single highest-value acquisition is Paul Waddell's Bay Area calibration** (costs, rents, cap rate) —
his UrbanSim is already calibrated for exactly this. That is the ask in the outreach draft
(`notes/2026-08-14_waddell_outreach.md`).

**As a curriculum piece, this notebook is complete as-is:** it teaches the full arc — assemble open data →
borrow UrbanSim's schema ideas → a transparent pro-forma → scenario-as-table-swap → the calibration lesson
→ publish to Datasette. The Elmwood *answer* waits on calibration; the *method* is fully taught.
""")

nb["cells"] = C
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
import os
os.makedirs("notebooks/v4", exist_ok=True)
nbf.write(nb, "notebooks/v4/JN-Feasibility.ipynb")
print("wrote notebooks/v4/JN-Feasibility.ipynb —", len(C), "cells")
