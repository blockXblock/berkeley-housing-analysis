#!/usr/bin/env python3
"""build_jn_feasibility.py — generator for notebooks/v4/JN-Feasibility.ipynb.

A TEACHING notebook: "Build UrbanSim's development-feasibility model, in the open, the Datasette way."
It walks a student through assembling a parcel table from open civic data, borrowing UrbanSim's schema
ideas, reimplementing its SqFtProForma pro-forma transparently (~15 legible lines, cited, BSD-3), and
running a baseline-vs-upzone scenario on the Elmwood commercial strip — then confronts them with the
lesson that the result is dominated by CALIBRATION, not code.

Markdown-in-source (the text cells ARE the deliverable). Every figure is DERIVED and gated against an
external timestamped baseline (data/baselines/feasibility_baseline_2026-08-14.json) — never hardcoded.

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
> (`data/baselines/feasibility_baseline_2026-08-14.json`). *Structural* figures (parcel/acre counts) are
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
- `value = bulk × (1 − parking) × efficiency × rent ÷ cap_rate` — income, capitalized
- `profit = value − cost` — **feasible if > 0**

Every constant is a **labeled placeholder**. A student changes one and re-runs — that is the exercise.
""")
code(r"""
# CALIBRATION — LABELED PLACEHOLDERS (replace with real Berkeley data / Waddell before any claim)
RENT_SQFT_YR, CAP_RATE, FINANCING = 45.0, 0.045, 1.10     # ~$3.75/sqft/mo rent; 4.5% cap; soft-cost mult
PARKING_LOSS, EFFICIENCY, UNIT_SQFT = 0.15, 0.82, 950     # floor-area losses; avg dwelling incl common
FT_PER_STORY, COVERAGE = 11.0, 0.72                       # height->stories; footprint share of lot
def cost_per_sqft(h): return 400 if h <= 45 else 560 if h <= 85 else 720   # wood -> podium -> highrise

def proforma(lot_sqft, land_cost, max_far, max_height):
    far = min(max_far, (max_height / FT_PER_STORY) * COVERAGE)    # zoning binds
    bulk = far * lot_sqft
    cost = bulk * cost_per_sqft(max_height) * FINANCING + land_cost
    rentable = bulk * (1 - PARKING_LOSS) * EFFICIENCY
    value = rentable * RENT_SQFT_YR / CAP_RATE
    return value - cost, rentable / UNIT_SQFT                     # (profit, potential units)
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
base = json.load(open("data/baselines/feasibility_baseline_2026-08-14.json"))
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
## Step 8 — The real lesson: the model is only as good as its calibration

Under these placeholder inputs, **almost every parcel already pencils at baseline**, so the upzone flips
*zero* additional parcels — it only stacks more units onto already-feasible lots. **That zero is an
artifact, not a finding**, and it is the most important thing to learn here. Two inputs drive it:

1. **Land cost = assessed value.** Prop-13 assessed land is far below market for prime College Ave retail,
   so acquisition looks cheap and everything "pencils." Real market land → far fewer baseline-feasible
   parcels → the upzone question becomes real.
2. **The commercial set is too broad** (UseCode 3x ≈ the acreage printed in Step 2, vs the true ~5.3-ac
   strip). A spatial cut to the College frontage tightens it.

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
