#!/usr/bin/env python
"""build_jn_measure_u.py — generator for notebooks/v4/JN-MeasureU.ipynb

Investigation JN (sandwich mode): reconcile the City's OFFICIAL Measure U Tax Rate
Statement figures with the parcel-level incidence model (docs/maps/bond_incidence.html,
scripts/gen_bond_incidence.py), derive the tax-base-growth assumptions hidden inside
the City's advertised rates, and map the parcel-by-parcel load.

Convention (CLAUDE.md): markdown (assumption+plan+why) -> code (operation) ->
markdown (found+verify). DERIVE + compare-to-baseline, never hardcode: the gate cell
asserts derived figures against data/baselines/measure_u_reconciliation_baseline_<date>.json
(bootstrap-created on first verified run; legitimate changes APPEND a new baseline).
Official TRS figures are SOURCE DATA (published constants w/ provenance), not derived
results — they live in one OFFICIAL dict and are mirrored into the baseline to guard edits.

Run:  /opt/miniconda3/envs/jupyter_env/bin/python scripts/v4/build_jn_measure_u.py
(from repo root; executes the notebook via ExecutePreprocessor with path='.')
"""
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

md, code = new_markdown_cell, new_code_cell
cells = []

# ----------------------------------------------------------------------------- S0 header
cells.append(md(r"""# JN-MeasureU — Reconciling the City's Tax Rate Statement with parcel-level incidence

**Question.** The City's official Tax Rate Statement (TRS) for Measure U (the $300M GO bond,
Nov 2026) advertises **$22.14 per $100,000** of assessed value (average over 40 years) with a
peak of **$35 per $100,000** from FY 2040-41. Our parcel-level incidence model
(`scripts/gen_bond_incidence.py` → `docs/maps/bond_incidence.html`) computes **~$67 per
$100,000** for the same debt serviced on *today's* assessed-value base. **Are these the same
levy?** Yes — and proving it exposes the TRS's hidden assumption: a tax base that roughly
doubles, with growth that Prop 13 arithmetic forces to come mostly from **reassessment at sale
and new construction**. This notebook derives that reconciliation from primary figures,
charts the assumptions, and maps the parcel-by-parcel load.

**Sources (all primary, read-only).**
- `databases/berkeley.db` — Alameda assessor parcels (Feb-2026 refresh; gross `TotalNetValue`).
- City of Berkeley Resolution 72,338-N.S. (June 16, 2026), Exhibit B **Tax Rate Statement**
  (Elections Code §9400-9404) + the 75-word ballot label + City Attorney impartial analysis.
- `databases/berkeley_housing_v2.db` — completed-project evidence for the new-construction wedge.

**Discipline.** Every result figure is **derived** in-cell and asserted against the external
timestamped baseline `data/baselines/measure_u_reconciliation_baseline_2026-08-15.json` at the
gate (§8). A mismatch DIAGNOSES and HALTS. CKAN/HCD plays no role here. Nothing in any chart
is hardcoded — charts read the derived variables.

**How to run.** From repo root, `jupyter_env` python. The optional agent-verification cell (§7)
is inert unless `JN_RUN_AGENT=1`."""))

cells.append(md(r"""## Data flow (lineage)

```mermaid
flowchart LR
  A[(berkeley.db\nAlameda assessor\nFeb-2026, 27.6k parcels)] --> C[S1 base + per-parcel AV]
  B[TRS Exhibit B\nRes. 72,338-N.S.\nofficial figures] --> D[S2 OFFICIAL dict]
  V[(berkeley_housing_v2.db\ncompletions >=2018)] --> W[S4 new-construction wedge evidence]
  C --> E[S3 reconciliation identities]
  D --> E
  E --> F[S4 base-growth model + charts]
  W --> F
  C --> G[S5 incidence distribution + Lorenz]
  C --> H[S6 parcel maps]
  E --> I{{S8 GATE vs baseline JSON}}
  F --> I
  G --> I
  I --> J[notes/2026-08-15 op-ed analysis\n+ docs/maps bond_incidence]
```
"""))

# ----------------------------------------------------------------------------- S1 base
cells.append(md(r"""## S1 — Load the assessed-value base

**Assumption.** The ad-valorem base is the sum of gross `TotalNetValue` over parcels with
positive assessed value (~27.6k parcels, ~$29B — the gate pins the exact figures).
**Base is bill-consistent NET assessed value (verified 2026-08-15 against a real bill):**
`TotalNetValue` nets out exemptions — on the oracle parcel 53-1695-26 (2811 Benvenue) it
equals Land + Imps − the $7,000 homeowner's exemption and matches the county tax bill's net
AV **to the dollar**. The v1 "gross base" honesty rail is retired; the code cell asserts the
identity so a future snapshot that breaks it halts here.
**Plan.** Read the assessor snapshot, filter `TotalNetValue > 0`, report n and the total,
and assert the oracle-parcel identity."""))

cells.append(code(r"""import sqlite3, json, os, sys, warnings
import pandas as pd, numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, "scripts")

DB = "databases/berkeley.db"
con = sqlite3.connect(DB)
p = pd.read_sql("SELECT APN,TotalNetValue,Land,Imps,UseCode,Latitude,Longitude,"
                "SitusStree,SitusStr_1 FROM parcels", con)
for c in ["TotalNetValue","Land","Imps","Latitude","Longitude"]:
    p[c] = pd.to_numeric(p[c], errors="coerce")
p = p[p.TotalNetValue > 0].copy()
p["addr"] = (p.SitusStree.fillna("").astype(str).str.strip()+" "
             +p.SitusStr_1.fillna("").astype(str).str.strip()).str.strip()
N_PARCELS = len(p)
TOTAL_AV  = float(p.TotalNetValue.sum())
DERIVED = {}          # accumulates every gated figure
DERIVED["n_parcels"] = N_PARCELS
DERIVED["total_av_b"] = TOTAL_AV/1e9
print(f"parcels with AV>0: {N_PARCELS:,}")
print(f"total assessed value (bill-consistent net): ${TOTAL_AV/1e9:.3f} B")
# oracle check (2026-08-15): the FY26 county bill for 53-1695-26 (2811 Benvenue) shows
# net AV $728,900 = Land 220,700 + Imps 515,200 - $7,000 homeowner's exemption.
o = p[p.APN == "53-1695-26"].iloc[0]
assert abs((o.Land + o.Imps - 7000) - o.TotalNetValue) < 1, \
    "TotalNetValue no longer bill-consistent net AV on the oracle parcel — investigate snapshot"
print(f"oracle 53-1695-26: Land+Imps-$7k = ${o.Land+o.Imps-7000:,.0f} == TotalNetValue "
      f"${o.TotalNetValue:,.0f}  (matches the actual FY26 bill's net AV)")"""))

cells.append(md(r"""**Found / verify.** The printed n and total must match the baseline (gate, §8) —
the same snapshot that feeds `docs/maps/bond_incidence.html`, so the JN and the public map
argue from one base. If the assessor snapshot is refreshed, the gate will fail loudly; the
correct response is a **new appended baseline**, never an edit."""))

# ----------------------------------------------------------------------------- S2 official
cells.append(md(r"""## S2 — The City's official figures (source data, with provenance)

**Assumption.** These are *published facts*, not derived results — the JN's inputs, quoted
from the official record. Each carries its provenance. The gate mirrors this block into the
baseline so silent edits are caught.

| figure | value | source |
|---|---|---|
| Principal | $300,000,000 | Measure text §4 |
| Average annual rate | $22.14 / $100k AV | 75-word label; TRS Exhibit B ("2.2 cents per $100") |
| Highest rate | $35 / $100k AV, first applies FY 2040-41 | TRS Exhibit B; impartial analysis |
| Total debt service | $610,000,000 | TRS Exhibit B |
| Average annual revenue | ~$15,200,000/yr | 75-word label |
| Issuance plan | $100M every 5 years from 2027 | TRS Exhibit B |
| Final collection | FY 2066/67 | TRS Exhibit B |

All from Resolution 72,338-N.S. (June 16, 2026) and the City Attorney's impartial analysis
(berkeleyca.gov, Nov 2026 measures)."""))

cells.append(code(r"""OFFICIAL = {
    "principal":        300_000_000,   # Measure text sec.4
    "avg_rate_100k":    22.14,         # TRS Exhibit B / ballot label
    "peak_rate_100k":   35.0,          # TRS Exhibit B / impartial analysis
    "peak_first_fy":    2040,          # "first year in which the highest tax rate will apply is 2040/41"
    "total_debt_service": 610_000_000, # TRS Exhibit B
    "avg_annual_revenue": 15_200_000,  # ballot label "approximately $15,200,000/year"
    "combined_avg_rate_100k": 44.13,   # June 2026 staff report: avg rate combined w/ existing GO authorizations
    "tranche":          100_000_000,   # "$100 million every five years commencing in 2027"
    "tranche_years":    [2027, 2032, 2037],
    "final_fy":         2066,          # final collection FY 2066/67
    "base_year":        2026,
}
print("OFFICIAL inputs loaded:", ", ".join(f"{k}={v}" for k,v in OFFICIAL.items()))"""))

# ----------------------------------------------------------------------------- S3 reconciliation
cells.append(md(r"""## S3 — Reconciliation: three identities

**Plan.** Derive, from the OFFICIAL figures plus the base from S1, with **no other inputs**:

1. **Implied borrowing rate** — the level-payment interest rate `r` that makes three $100M
   30-year tranches cost exactly the TRS's $610M in total debt service.
2. **The identity behind the map's $67** — peak-period debt service (all tranches
   outstanding) divided by *today's* base. Same numerator as the City's $35 peak; only the
   denominator (the base) differs.
3. **The implied base trajectory** — the base the City must be assuming in FY 2040-41 for the
   peak rate to be $35 (and its growth rate from today), and the *average* base implied by
   $22.14 — plus, solved properly against the actual phased debt-service schedule, the
   constant growth rate `g_avg` that reproduces the $22.14 average.

**Why it matters.** If the same debt service yields $67 on today's base and $35 on the City's
assumed 2040 base, then the *entire* difference is assumed base growth — which Prop 13 then
lets us decompose (S4)."""))

cells.append(code(r"""def level_payment(P, r, n=30):
    return P*r/(1-(1+r)**-n)

def bisect(f, lo, hi, tol=1e-12, it=200):
    flo = f(lo)
    for _ in range(it):
        mid = (lo+hi)/2; fm = f(mid)
        if flo*fm <= 0: hi = mid
        else: lo, flo = mid, fm
        if hi-lo < tol: break
    return (lo+hi)/2

# (1) implied borrowing rate from $610M total service on 3 x $100M x 30yr
n_pay, n_tr = 30, len(OFFICIAL["tranche_years"])
r_impl = bisect(lambda r: n_tr*n_pay*level_payment(OFFICIAL["tranche"], r) - OFFICIAL["total_debt_service"],
                1e-4, 0.15)
ann_tranche = level_payment(OFFICIAL["tranche"], r_impl)
ds_peak = n_tr*ann_tranche                     # all tranches outstanding
total_interest = OFFICIAL["total_debt_service"] - OFFICIAL["principal"]

# (2) the map's benchmark: peak DS on TODAY's base
rate_today_100k = ds_peak/TOTAL_AV*1e5

# (3) implied bases and growth
base_peak_impl = ds_peak/(OFFICIAL["peak_rate_100k"]/1e5)
yrs_to_peak = OFFICIAL["peak_first_fy"] - OFFICIAL["base_year"]
g_peak = (base_peak_impl/TOTAL_AV)**(1/yrs_to_peak) - 1
base_avg_impl = OFFICIAL["avg_annual_revenue"]/(OFFICIAL["avg_rate_100k"]/1e5)

# debt-service schedule (payment years t+1 .. t+30 per tranche)
years = list(range(OFFICIAL["base_year"], OFFICIAL["final_fy"]+2))
ds = {y: 0.0 for y in years}
for t in OFFICIAL["tranche_years"]:
    for y in range(t+1, t+1+n_pay):
        if y in ds: ds[y] += ann_tranche
pay_years = [y for y in years if ds[y] > 0]

def avg_rate_for_growth(g):
    return np.mean([ds[y]/(TOTAL_AV*(1+g)**(y-OFFICIAL["base_year"]))*1e5 for y in pay_years])
g_avg = bisect(lambda g: avg_rate_for_growth(g) - OFFICIAL["avg_rate_100k"], 0.0, 0.12)

first_full, last_pay = pay_years[0], pay_years[-1]
DERIVED.update(dict(
    implied_borrow_rate_pct = r_impl*100,
    ds_peak_m               = ds_peak/1e6,
    total_interest_m        = total_interest/1e6,
    rate_today_100k         = rate_today_100k,
    base_peak_impl_b        = base_peak_impl/1e9,
    g_peak_pct              = g_peak*100,
    base_avg_impl_b         = base_avg_impl/1e9,
    base_avg_multiple       = base_avg_impl/TOTAL_AV,
    g_avg_pct               = g_avg*100,
))
print(f"(1) implied borrowing rate: {r_impl*100:.2f}%  (interest ${total_interest/1e6:,.0f}M > principal? {total_interest>OFFICIAL['principal']})")
print(f"    annual DS per $100M tranche ${ann_tranche/1e6:.2f}M; peak DS (3 tranches) ${ds_peak/1e6:.1f}M/yr")
print(f"    schedule check: first payment {first_full}, last payment {last_pay} (TRS final FY {OFFICIAL['final_fy']}/67)")
print(f"(2) peak DS on TODAY's ${TOTAL_AV/1e9:.2f}B base = ${rate_today_100k:.1f} per $100k  <- the incidence map's benchmark")
print(f"(3) $35 peak in FY{OFFICIAL['peak_first_fy']} implies base ${base_peak_impl/1e9:.1f}B -> {g_peak*100:.2f}%/yr growth over {yrs_to_peak} yrs")
print(f"    $22.14 avg implies average base ${base_avg_impl/1e9:.1f}B = {base_avg_impl/TOTAL_AV:.2f}x today's")
print(f"    solved vs the actual phased DS schedule: g_avg = {g_avg*100:.2f}%/yr reproduces the $22.14 average")"""))

cells.append(md(r"""**Found / verify.** The reconciliation in one sentence: **the City's $35 peak and the
map's ~$67 are the *same annual debt service*; the City's number divides it by a future base
grown ~4–5%/yr, the map by today's base.** The implied borrowing rate (~5%) independently
lands on the incidence map's assumed coupon — two documents, one debt model. Interest
exceeds principal. The schedule's last payment year reproduces the TRS's FY 2066/67, which is
a genuine cross-check that the phased-issuance reading ($100M × 3, 30-yr tranches) is the
TRS's own model.

**What this could mislead about:** the City's figures are *not wrong* — they are nominal
projections on a growing base. The map's $67 is not a forecast of anyone's 2040 bill; it is
the today's-dollars, today's-assessments benchmark. Publish the two together or the campaign
will (correctly) say the map triples the official rate."""))

# ----------------------------------------------------------------------------- S4 growth decomposition
cells.append(md(r"""## S4 — The hidden assumption: who grows the base

**Assumption.** Under Prop 13, a parcel that does not change hands grows at most **2%/yr**
(the inflation cap). Citywide base growth beyond 2% must therefore come from
**reassessment at sale** (acquisition-value reset), **new construction** (including
improvement-triggered reassessment), and — cyclically — **Prop-8 decline-in-value
restorations**, which can exceed 2%/yr *without a sale* until a previously-reduced parcel
regains its factored base value (observed on the oracle parcel 2811 Benvenue: +10.4% in one
year, no sale). Restorations are bounded by the factored base, so the *structural* wedge is
turnover + construction; the arithmetic necessity is only that none of the excess growth can
come from sitting owners at the cap.
**Plan.** (a) Decompose the implied growth `g_avg`/`g_peak` into the 2%-cap component vs the
newcomer wedge. (b) Ground the new-construction share with in-hand evidence: v2-pipeline
projects (5+ units, CO ≥ 2018) joined to the assessor via the canonical APN crosswalk
(stale-APN guard applies: unmatched = re-plat/too-new, flagged, never re-pointed).
(c) Chart the trajectories and the counterfactual: what the *average advertised rate* would
be if the base grew only at the 2% cap — i.e., if there were no newcomers to bill."""))

cells.append(code(r"""# (a) decomposition of implied growth
wedge_avg  = 1 - 0.02/g_avg
wedge_peak = 1 - 0.02/g_peak
# counterfactual: base frozen at the 2% cap (no sales, no construction)
avg_rate_frozen = avg_rate_for_growth(0.02)

# (b) new-construction evidence: v2 completions joined to assessor AV
from housing_rules import to_canonical_apn
v2 = sqlite3.connect("databases/berkeley_housing_v2.db")
proj = pd.read_sql(
    "SELECT f.project_id, f.total_units, f.co_issued_date, pa.apn, pa.apn_raw, pa.apn_normalized "
    "FROM v_projects_flat f "
    "JOIN project_parcels pp ON pp.project_id=f.project_id "
    "JOIN parcels pa ON pa.id=pp.parcel_id "
    "WHERE f.co_issued_date >= '2018-01-01' AND f.total_units >= 5", v2)
def canon(x):
    if x is None or str(x).strip()=="" : return None
    try: return to_canonical_apn(str(x), "alameda")
    except Exception: return None
ap = p[["APN","TotalNetValue"]].copy()
ap["canon"] = ap.APN.map(canon)
ap = ap.dropna(subset=["canon"]).groupby("canon", as_index=False).TotalNetValue.sum()
proj["canon"] = proj.apn_normalized.where(proj.apn_normalized.notna(),
                                          proj.apn_raw.fillna(proj.apn)).map(canon)
m = proj.merge(ap, on="canon", how="left")
gg = m.groupby("project_id", dropna=False).agg(av=("TotalNetValue","sum"),
                                               units=("total_units","first"))
matched   = gg[gg.av > 0]
unmatched = gg[~(gg.av > 0)]
newcon_av = float(matched.av.sum())
DERIVED.update(dict(
    wedge_share_avg_pct  = wedge_avg*100,
    wedge_share_peak_pct = wedge_peak*100,
    avg_rate_frozen_100k = avg_rate_frozen,
    newcon_projects_matched = int(len(matched)),
    newcon_units_matched    = int(matched.units.sum()),
    newcon_av_b             = newcon_av/1e9,
    newcon_share_of_base_pct= newcon_av/TOTAL_AV*100,
))
print(f"(a) implied growth {g_avg*100:.2f}%/yr (avg-rate identity) .. {g_peak*100:.2f}%/yr (peak identity)")
print(f"    Prop-13 cap contributes 2.00%/yr -> newcomer wedge = {wedge_avg*100:.0f}%..{wedge_peak*100:.0f}% of all base growth")
print(f"    counterfactual: base growing at the 2% cap only -> average rate ${avg_rate_frozen:.2f} per $100k "
      f"(vs advertised ${OFFICIAL['avg_rate_100k']}) = {avg_rate_frozen/OFFICIAL['avg_rate_100k']:.2f}x")
print(f"(b) completed 5+ unit projects (CO>=2018) matched to assessor: {len(matched)} projects, "
      f"{int(matched.units.sum()):,} units, AV ${newcon_av/1e9:.2f}B = {newcon_av/TOTAL_AV*100:.1f}% of today's base")
print(f"    UNDERCOUNT: {len(unmatched)} projects ({int(unmatched.units.sum()):,} units) unmatched "
      f"(re-platted/too-new APNs — flagged, not re-pointed; e.g. 2352 Shattuck, 237u, AV $117.9M in assessor)")"""))

cells.append(code(r"""import plotly.graph_objects as go
from plotly.subplots import make_subplots
BLUE, ORANGE, GRAY, INK = "#3b6fb6", "#e07b39", "#8a8f98", "#30343b"
yrsX = list(range(OFFICIAL["base_year"], OFFICIAL["final_fy"]+2))
base_city   = [TOTAL_AV*(1+g_avg)**(y-OFFICIAL["base_year"])/1e9 for y in yrsX]
base_frozen = [TOTAL_AV*(1.02)**(y-OFFICIAL["base_year"])/1e9   for y in yrsX]

fig = go.Figure()
fig.add_trace(go.Scatter(x=yrsX, y=base_frozen, name="Prop-13 cap only (2%/yr, no sales, no construction)",
    line=dict(color=GRAY, width=2), stackgroup="b", fillcolor="rgba(138,143,152,.25)"))
fig.add_trace(go.Scatter(x=yrsX, y=[c-f for c,f in zip(base_city, base_frozen)],
    name="Newcomer wedge: reassessment at sale + new construction",
    line=dict(color=ORANGE, width=2), stackgroup="b", fillcolor="rgba(224,123,57,.30)"))
fig.add_trace(go.Scatter(x=yrsX, y=base_city, name=f"Base implied by the TRS ($22.14 avg -> {g_avg*100:.1f}%/yr)",
    line=dict(color=BLUE, width=2.5), hovertemplate="%{x}: $%{y:.1f}B"))
fig.add_hline(y=base_avg_impl/1e9, line_dash="dot", line_color=BLUE,
    annotation_text=f"TRS implied AVERAGE base ${base_avg_impl/1e9:.0f}B "
                    f"({base_avg_impl/TOTAL_AV:.1f}x today)", annotation_font_color=INK)
fig.update_layout(title="The tax base the Tax Rate Statement is assuming — and who supplies it",
    yaxis_title="assessed-value base ($B, nominal)", xaxis_title=None,
    template="plotly_white", legend=dict(orientation="h", y=-0.18), height=460, font=dict(color=INK))
fig.show()"""))

cells.append(md(r"""**What this chart shows / could mislead about.** The orange wedge is an **arithmetic
residual** (implied growth minus the statutory 2% cap), not an observed count of sales — the
honest claim is "must come from turnover + construction (+ cyclical Prop-8 restorations,
bounded — see the S4 assumption)," not "we watched it happen."
Dollars are nominal; the base *level* is not a wealth measure. The wedge share printed above
(~half to two-thirds of all growth, depending on which official figure you solve against) is
the load-bearing number: **the advertised $22.14 average is financed by the future buyers and
future buildings inside the wedge.**"""))

cells.append(code(r"""rate_city   = [ds[y]/(TOTAL_AV*(1+g_avg)**(y-OFFICIAL["base_year"]))*1e5 if ds[y]>0 else None for y in yrsX]
rate_frozen = [ds[y]/(TOTAL_AV*(1.02)**(y-OFFICIAL["base_year"]))*1e5   if ds[y]>0 else None for y in yrsX]
fig = go.Figure()
fig.add_trace(go.Scatter(x=yrsX, y=rate_frozen, name="if base grew at 2% cap only",
    line=dict(color=GRAY, width=2, dash="dash")))
fig.add_trace(go.Scatter(x=yrsX, y=rate_city, name="on the TRS-implied growing base",
    line=dict(color=BLUE, width=2.5)))
fig.add_hline(y=OFFICIAL["avg_rate_100k"], line_dash="dot", line_color=BLUE,
    annotation_text=f"advertised average ${OFFICIAL['avg_rate_100k']}/100k")
fig.add_hline(y=OFFICIAL["peak_rate_100k"], line_dash="dot", line_color=INK,
    annotation_text=f"disclosed peak ${OFFICIAL['peak_rate_100k']:.0f}/100k (FY{OFFICIAL['peak_first_fy']}-41)")
fig.add_hline(y=rate_today_100k, line_dash="dot", line_color=ORANGE,
    annotation_text=f"same peak debt service on TODAY's base ${rate_today_100k:.0f}/100k (the map)")
fig.update_layout(title="One debt service, three rates — the difference is only the base it is divided by",
    yaxis_title="$ per $100,000 assessed value", xaxis_title=None,
    template="plotly_white", legend=dict(orientation="h", y=-0.18), height=460, font=dict(color=INK))
fig.show()"""))

cells.append(md(r"""**Found / verify.** The gray dashed line is the counterfactual the campaign never
states: with no newcomers to refill the base, the *same* bond averages **~1.6x** the
advertised rate (exact figure printed in S4a and gated). The blue line's average reproduces
$22.14 by construction (that is how `g_avg` was solved) — the chart is a visualization of the
identity, not extra evidence. The orange benchmark is where the incidence map lives."""))

# ----------------------------------------------------------------------------- S5 distribution
cells.append(md(r"""## S5 — Who pays: the cross-sectional distribution

**Assumption.** The *distribution* of the burden across parcels is rate-invariant: every
parcel's bill is `rate x AV`, so shares, ratios and rankings hold whether you price at the
City's $22.14 average, its $35 peak, or the $67 today's-base benchmark (used below; scale by
0.52 for the peak rate).
**Plan.** Concentration (top 1/5/10/25/50% of parcels by AV), decile table, the
single-family p90/p10 spread, and a Lorenz-style cumulative-share curve."""))

cells.append(code(r"""rate_today = ds_peak/TOTAL_AV
p["cost"] = p.TotalNetValue*rate_today
s = p.sort_values("TotalNetValue", ascending=False).reset_index(drop=True)
cum = s.TotalNetValue.cumsum()/TOTAL_AV
conc = {f"top{int(q*100)}_share_pct": float(cum.iloc[int(N_PARCELS*q)-1]*100)
        for q in (0.01, 0.05, 0.10, 0.25, 0.50)}
sf = p[p.UseCode.astype(str).str.match(r"^1\d{3}$")]
q_sf = sf.cost.quantile([.10,.50,.90])
DERIVED.update(conc)
DERIVED.update(dict(
    median_cost_all = float(p.cost.median()),
    sfr_n           = int(len(sf)),
    sfr_median_cost = float(q_sf[.50]),
    sfr_p90_p10     = float(q_sf[.90]/q_sf[.10]),
))
# figures surfaced for the maps session + the site (session-coordination contract,
# notes/2026-08-15_session_coordination.md — the baseline is the single source of truth):
p["dec"] = pd.qcut(p.TotalNetValue, 10, labels=False)+1
gdec = p.groupby("dec")
apt = p[p.UseCode.astype(str).str.match(r"^7\d{3}$")]
DERIVED.update(dict(
    decile_share_pct   = [float(v) for v in (gdec.TotalNetValue.sum()/TOTAL_AV*100)],
    decile_median_cost = [float(v) for v in gdec.cost.median()],
    apt_share_pct      = float(apt.TotalNetValue.sum()/TOTAL_AV*100),
    flat_parcel_cost   = float(ds_peak/N_PARCELS),
    med_sfr_av         = float(sf.TotalNetValue.median()),
))
print(f"apartments (7xxx): {DERIVED['apt_share_pct']:.1f}% of the base | flat-tax equivalent "
      f"${DERIVED['flat_parcel_cost']:,.0f}/parcel | median SFR AV ${DERIVED['med_sfr_av']:,.0f}")
# WHO the top tiers are — composition by use bucket (derived for the site/map)
u = p.UseCode.astype(str)
p["bucket"] = np.select(
    [u.str.startswith("73"), u.str.startswith("7"), u.str.startswith("1"), u.str.startswith("2"),
     u.str.startswith("3") | u.str.startswith("4"), u.str.startswith("9")],
    ["condos", "apartments_mixed", "single_family", "small_residential",
     "commercial_industrial", "institutional"], default="other")
sq = p.sort_values("TotalNetValue", ascending=False).reset_index(drop=True)
tier_av, tier_ct, tier_entry = {}, {}, {}
for qq in (1, 5, 10, 25):
    k = int(N_PARCELS*qq/100); tp = sq.iloc[:k]
    shares = (tp.groupby("bucket").TotalNetValue.sum()/tp.TotalNetValue.sum()*100).round(1)
    tier_av[str(qq)] = {b: float(v) for b, v in shares.items()}
    tier_ct[str(qq)] = {b: int(v) for b, v in tp.bucket.value_counts().items()}
    tier_entry[str(qq)] = float(sq.TotalNetValue.iloc[k-1])
DERIVED.update(dict(tier_composition_av_pct=tier_av, tier_composition_count=tier_ct,
                    tier_entry_av=tier_entry))
# OWNER-OCCUPIED share (definition per maps session, scripts/build_parcel_facts.py, adopted
# 2026-08-15): owner_occupied = the $7,000 HOMEOWNER'S EXEMPTION flag — the assessor grants
# it only to owner-occupied homes: round((Land+Imps) - TotalNetValue) == 7000. Same identity
# as the S1 Benvenue oracle. CAVEAT (carry everywhere): a FLOOR on owner-occupancy — eligible
# owners who never file are missed — so the rental+commercial share is a CEILING.
oo = ((p.Land.fillna(0) + p.Imps.fillna(0) - p.TotalNetValue).round(0) == 7000)
DERIVED.update(dict(
    owner_occupied_parcels   = int(oo.sum()),
    owner_occupied_share_pct = float(p.loc[oo, "TotalNetValue"].sum()/TOTAL_AV*100),
))
print(f"owner-occupied (homeowner's-exemption flag): {int(oo.sum()):,} parcels carry "
      f"{DERIVED['owner_occupied_share_pct']:.1f}% of the ad-valorem bond (a FLOOR; "
      f"rental+commercial <= {100-DERIVED['owner_occupied_share_pct']:.1f}%)")
t1 = tier_av["1"]
print(f"top 1% composition (share of tier AV): apartments {t1.get('apartments_mixed',0):.0f}% | "
      f"commercial/industrial {t1.get('commercial_industrial',0):.0f}% | institutional "
      f"{t1.get('institutional',0):.0f}% | single-family {t1.get('single_family',0):.1f}% "
      f"({tier_ct['1'].get('single_family',0)} homes of {int(N_PARCELS*0.01)} parcels)")
print("share of the bond paid by the top X% of parcels (by AV):")
for q in (0.01,0.05,0.10,0.25,0.50):
    print(f"   top {q:>4.0%} ({int(N_PARCELS*q):>6,}) -> {cum.iloc[int(N_PARCELS*q)-1]*100:5.1f}%")
print(f"   bottom 50% -> {100-conc['top50_share_pct']:.1f}%")
print(f"all parcels: median ${p.cost.median():,.0f}/yr at the today's-base benchmark")
print(f"single-family (n={len(sf):,}): p10 ${q_sf[.10]:,.0f}, median ${q_sf[.50]:,.0f}, "
      f"p90 ${q_sf[.90]:,.0f}  -> p90/p10 = {q_sf[.90]/q_sf[.10]:.1f}x for the identical bond")"""))

cells.append(code(r"""x_lorenz = np.arange(1, N_PARCELS+1)/N_PARCELS*100
y_lorenz = cum.values*100
fig = make_subplots(rows=1, cols=2, column_widths=[0.55,0.45],
    subplot_titles=("Cumulative share of the bond, parcels ranked by AV",
                    "Median annual cost by AV decile (today's-base benchmark)"))
fig.add_trace(go.Scatter(x=x_lorenz, y=y_lorenz, name="share of bond",
    line=dict(color=BLUE, width=2.5), hovertemplate="top %{x:.0f}% of parcels pay %{y:.1f}%"), 1, 1)
fig.add_trace(go.Scatter(x=[0,100], y=[0,100], name="equal-per-parcel line",
    line=dict(color=GRAY, width=1.5, dash="dash")), 1, 1)
for q,lab in ((1,"top 1%"),(10,"top 10%")):
    yv = float(cum.iloc[int(N_PARCELS*q/100)-1]*100)
    fig.add_annotation(x=q, y=yv, text=f"{lab}: {yv:.0f}%", showarrow=True, arrowhead=2,
                       ax=40, ay=-25, font=dict(color=INK), row=1, col=1)
p["dec"] = pd.qcut(p.TotalNetValue, 10, labels=False)+1
dmed = p.groupby("dec").cost.median()
fig.add_trace(go.Bar(x=[f"D{i}" for i in dmed.index], y=dmed.values, marker_color=BLUE,
    text=[f"${v:,.0f}" for v in dmed.values], textposition="outside",
    name="median $/yr", showlegend=False), 1, 2)
fig.update_layout(template="plotly_white", height=440, font=dict(color=INK),
    title="Concentration of the ad-valorem burden", legend=dict(orientation="h", y=-0.18))
fig.update_yaxes(title_text="% of bond", row=1, col=1)
fig.update_yaxes(title_text="$/yr", row=1, col=2)
fig.show()"""))

cells.append(md(r"""**What this could mislead about.** AV is acquisition-based (Prop 13): the x-ranking is
**not a wealth ranking** — a long-held low-AV parcel may hold far more equity than a recently
bought high-AV one; that inversion is the *point* of the incidence story, not a flaw in it.
The base is bill-consistent net AV (S1). The decile bars use the today's-base benchmark; at
the City's disclosed peak rate every bar scales by ~0.52 and every *share* is unchanged.
**Whole-bill context (from the reconciled FY26 bill, 53-1695-26, total $21,064):** ad-valorem
lines are only ~43% of a Berkeley tax bill; the majority is **flat / square-footage parcel
charges** (BSEP, library, parks, fire) whose regressivity runs the **opposite** direction — a
long-tenured owner of a large low-AV house pays nearly the same flat stack as a recent buyer
of the identical one. This JN characterizes the ad-valorem channel **Measure U adds to**, not
the whole bill; publishing the ad-valorem finding without this context invites that rebuttal."""))

# ----------------------------------------------------------------------------- S6 maps
cells.append(md(r"""## S6 — The parcel-by-parcel load, mapped

**Plan.** Two in-notebook maps (same data as the public interactive
`docs/maps/bond_incidence.html`, which adds popups and the flat-tax toggle):
1. every parcel colored by its annual cost band (today's-base benchmark; the *spatial
pattern* is rate-invariant);
2. the top-1% parcels — the 276 properties that carry ~a fifth of the bond — against
everything else.
**Why in-JN:** the notebook is the durable, re-runnable home; the docs/ map is the public
artifact. Both must derive from the same base (the gate pins it)."""))

cells.append(code(r"""import plotly.express as px
pm = p.dropna(subset=["Latitude","Longitude"])
pm = pm[pm.Latitude.between(37.8,37.95) & pm.Longitude.between(-122.35,-122.2)].copy()
BINS  = [0,200,500,1000,2500,np.inf]
LABS  = ["< $200","$200–500","$500–1,000","$1,000–2,500","$2,500+"]
SEQ   = {"< $200":"#f5c9a2","$200–500":"#e79b60","$500–1,000":"#cf6a2e",
         "$1,000–2,500":"#a4430f","$2,500+":"#6e2607"}
pm["band"] = pd.cut(pm.cost, BINS, labels=LABS)
fig = px.scatter_mapbox(pm, lat="Latitude", lon="Longitude", color="band",
    category_orders={"band": LABS}, color_discrete_map=SEQ,
    hover_data={"addr":True,"cost":":$,.0f","TotalNetValue":":$,.0f","Latitude":False,"Longitude":False,"band":False},
    zoom=12.1, height=620, title="Annual ad-valorem cost per parcel (today's-base benchmark; pattern is rate-invariant)")
fig.update_traces(marker=dict(size=4, opacity=0.75))
fig.update_layout(mapbox_style="carto-positron", template="plotly_white",
    legend=dict(title="annual cost", orientation="h", y=-0.02), font=dict(color=INK),
    margin=dict(l=0,r=0,t=40,b=0))
fig.show()"""))

cells.append(code(r"""cut1 = s.TotalNetValue.iloc[int(N_PARCELS*0.01)-1]
pm["top1"] = np.where(pm.TotalNetValue >= cut1, "top 1% of parcels", "all other parcels")
top1_share = DERIVED["top1_share_pct"]
fig = px.scatter_mapbox(pm.sort_values("top1", ascending=False), lat="Latitude", lon="Longitude",
    color="top1", color_discrete_map={"all other parcels":"#c9ccd1", "top 1% of parcels":"#b3261e"},
    hover_data={"addr":True,"cost":":$,.0f","Latitude":False,"Longitude":False,"top1":False},
    zoom=12.1, height=620,
    title=f"The 276 parcels (top 1% by AV) that pay {top1_share:.0f}% of the bond")
fig.update_traces(marker=dict(size=4, opacity=0.8),
    selector=dict(name="all other parcels"))
fig.update_traces(marker=dict(size=7, opacity=0.95),
    selector=dict(name="top 1% of parcels"))
fig.update_layout(mapbox_style="carto-positron", template="plotly_white",
    legend=dict(title=None, orientation="h", y=-0.02), font=dict(color=INK),
    margin=dict(l=0,r=0,t=40,b=0))
fig.show()"""))

cells.append(md(r"""**What these maps could mislead about.** Dots, not parcel polygons — visual density
partly tracks lot size. The red cluster downtown/Southside is largely the **new large
apartment buildings** — the same buildings in S4's new-construction wedge: the map of who
pays most *is* a map of what was recently built or recently sold, which is the reconciliation
made spatial. Basemap tiles load from the network at view time."""))

# ----------------------------------------------------------------------------- S7 agent
cells.append(md(r"""## S7 — Optional: agent verification of the official inputs

**Pattern.** A pure-data JN cannot verify *published facts* (the TRS figures could be
mistyped in S2). This cell — **inert by default** — deploys a headless Claude Code agent
(`claude -p`, WebFetch-only) to re-fetch the City's posted documents and confirm the four
load-bearing OFFICIAL figures. Enable with `JN_RUN_AGENT=1` (requires the `claude` CLI +
network). The JN's reproducibility never depends on it; the gate uses the baseline either way."""))

cells.append(code(r"""import subprocess, shutil
if os.environ.get("JN_RUN_AGENT") == "1" and shutil.which("claude"):
    prompt = (
      "Fetch https://berkeleyca.gov/sites/default/files/Nov%202026%20Impartial%20Analyses.pdf "
      "and if needed the Measure U council item PDF. Confirm these four figures for Berkeley's "
      "$300M GO bond (Measure U, Nov 2026): average rate $22.14 per $100k AV; highest rate $35 "
      "per $100k first applying FY 2040-41; total debt service $610,000,000; issuance $100M every "
      "5 years from 2027. Reply with ONLY a JSON object: "
      '{"avg_rate": <number>, "peak_rate": <number>, "total_ds": <number>, "confirmed": <bool>, "notes": "<str>"}')
    try:
        r = subprocess.run(["claude","-p",prompt,"--allowedTools","WebFetch","--output-format","json"],
                           capture_output=True, text=True, timeout=420)
        out = json.loads(r.stdout); txt = out.get("result", r.stdout)
        j = json.loads(txt[txt.find("{"): txt.rfind("}")+1])
        ok = (abs(j["avg_rate"]-OFFICIAL["avg_rate_100k"])<0.01 and
              abs(j["peak_rate"]-OFFICIAL["peak_rate_100k"])<0.01 and
              abs(j["total_ds"]-OFFICIAL["total_debt_service"])<1)
        print(("AGENT CONFIRMS" if ok and j.get("confirmed") else "AGENT DISAGREES — investigate"),
              "-", j.get("notes",""))
    except Exception as e:
        print(f"agent verification errored (non-fatal): {e}")
else:
    print("SKIPPED (set JN_RUN_AGENT=1 with the claude CLI installed to verify OFFICIAL "
          "figures against the live posted documents)")"""))

# ----------------------------------------------------------------------------- S8 gate
cells.append(md(r"""## S8 — Gate: derived figures vs the external baseline

**Discipline.** Every result above was derived; here they are asserted against
`data/baselines/measure_u_reconciliation_baseline_2026-08-15.json` (which also mirrors the
OFFICIAL block, so an accidental edit of a published constant is caught too). On first run
the baseline is **bootstrap-created** from this verified run and announced loudly. On any
later mismatch the cell **diagnoses (figure, baseline, computed, likely cause) and HALTS** —
the legitimate response to a real change (new assessor snapshot, corrected TRS) is a **new
appended timestamped baseline**, never an edit of the old one."""))

cells.append(code(r"""BASELINE = "data/baselines/measure_u_reconciliation_baseline_2026-08-15.json"
TOL = {  # relative tolerances; official mirror must match exactly
    "n_parcels": 0, "total_av_b": .005, "implied_borrow_rate_pct": .01, "ds_peak_m": .01,
    "total_interest_m": .001, "rate_today_100k": .01, "base_peak_impl_b": .01,
    "g_peak_pct": .02, "base_avg_impl_b": .01, "base_avg_multiple": .01, "g_avg_pct": .02,
    "wedge_share_avg_pct": .02, "wedge_share_peak_pct": .02, "avg_rate_frozen_100k": .02,
    "newcon_projects_matched": 0, "newcon_units_matched": 0, "newcon_av_b": .02,
    "newcon_share_of_base_pct": .02, "top1_share_pct": .01, "top5_share_pct": .01,
    "top10_share_pct": .01, "top25_share_pct": .01, "top50_share_pct": .01,
    "median_cost_all": .01, "sfr_n": 0, "sfr_median_cost": .01, "sfr_p90_p10": .02,
    "decile_share_pct": .01, "decile_median_cost": .01, "apt_share_pct": .01,
    "flat_parcel_cost": .01, "med_sfr_av": .01,
    "tier_composition_av_pct": .05, "tier_composition_count": 0, "tier_entry_av": .01,
    "owner_occupied_parcels": 0, "owner_occupied_share_pct": .01,
}
if not os.path.exists(BASELINE):
    payload = {"created": "2026-08-15", "provenance": {
                   "assessor": "databases/berkeley.db (Alameda, Feb-2026 refresh)",
                   "official": "Resolution 72,338-N.S. Exhibit B (TRS) + impartial analysis, berkeleyca.gov",
                   "v2": "databases/berkeley_housing_v2.db v_projects_flat completions >=2018, 5+ units",
                   "generator": "scripts/v4/build_jn_measure_u.py"},
               "official": OFFICIAL, "derived": DERIVED}
    os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
    json.dump(payload, open(BASELINE, "w"), indent=2, default=str)
    print(f"*** BASELINE CREATED (bootstrap) -> {BASELINE}")
    print("    Review the figures above; future runs assert against this file. Legitimate")
    print("    changes APPEND a new dated baseline — never edit this one.")
else:
    b = json.load(open(BASELINE))
    fails, new_derived = [], []
    for k, v in b["official"].items():
        if str(OFFICIAL.get(k)) != str(v):
            fails.append(("OFFICIAL:"+k, v, OFFICIAL.get(k), "official constant edited — restore or append new baseline w/ provenance"))
    new_official = [k for k in OFFICIAL if k not in b["official"]]
    def _close(cv, bv, tol):
        if isinstance(bv, list):
            return isinstance(cv, list) and len(cv) == len(bv) and all(_close(x, y, tol) for x, y in zip(cv, bv))
        if isinstance(bv, dict):
            return isinstance(cv, dict) and set(cv) == set(bv) and all(_close(cv[k2], bv[k2], tol) for k2 in bv)
        if bv == 0: return cv == 0
        return abs(cv-bv)/abs(bv) <= max(tol, 1e-12)
    for k, tol in TOL.items():
        cv = DERIVED.get(k)
        if cv is None:
            fails.append((k, b["derived"].get(k), None, "generator no longer derives a gated figure")); continue
        if k not in b["derived"]:
            new_derived.append(k); continue          # additive key — appended below, loudly
        if not _close(cv, b["derived"][k], tol):
            cause = ("assessor snapshot changed" if k in ("n_parcels","total_av_b","median_cost_all",
                     "sfr_n","sfr_median_cost","sfr_p90_p10","newcon_av_b","newcon_projects_matched",
                     "newcon_units_matched","newcon_share_of_base_pct","apt_share_pct","med_sfr_av",
                     "flat_parcel_cost") or k.startswith(("top","decile"))
                     else "official-figure or model change")
            fails.append((k, b["derived"][k], cv, cause))
    if fails:
        print("GATE FAIL — diagnosis (figure | baseline | computed | likely cause):")
        for f in fails: print("  ", " | ".join(str(x) for x in f))
        raise AssertionError(f"{len(fails)} figure(s) diverge from {BASELINE} — investigate; "
                            "if the change is legitimate, APPEND a new dated baseline.")
    # ADDITIVE APPEND (evidence-append-only): brand-new keys may be added with a recorded
    # amendment; mutating an existing value still hard-fails above.
    if new_derived or new_official:
        for k in new_derived:  b["derived"][k]  = DERIVED[k]
        for k in new_official: b["official"][k] = OFFICIAL[k]
        b.setdefault("amendments", []).append({
            "date": "2026-08-15",
            "added_derived": new_derived, "added_official": new_official,
            "reason": "additive append: incidence figures surfaced for gen_bond_incidence.py and the "
                      "measure-u site (session-coordination contract); existing values untouched"})
        json.dump(b, open(BASELINE, "w"), indent=2, default=str)
        print(f"*** BASELINE AMENDED (additive): +{len(new_derived)} derived {new_derived} "
              f"+{len(new_official)} official {new_official} — existing values verified unchanged first")
    print(f"GATE PASS — {len(TOL)} derived figures + {len(b['official'])} official constants "
          f"match {BASELINE} within tolerance.")"""))

cells.append(md(r"""## Conclusions

1. **One levy, reconciled.** The TRS's $35 peak, its $22.14 forty-year average, and the
   incidence map's ~$67 today's-base figure are the *same* ~$20M/yr debt service divided by
   three different bases. The implied borrowing rate (~5%) and the FY 2066/67 final payment
   both fall out of the TRS's own numbers, confirming the phased three-tranche reading.
2. **The advertised rate is financed by newcomers.** Reproducing $22.14 requires the base to
   grow ~4–5%/yr; Prop 13 caps sitting owners at 2%; the remainder — roughly half to
   two-thirds of all assumed growth — must come from reassessment at sale and new
   construction. Were the base to grow at the cap alone, the same bond would average ~1.6x
   the advertised rate. The completed 5+ unit projects since 2018 already visible in the
   assessor (~$1B, ~3.5% of the base, an undercount) are that wedge, arriving.
3. **The burden is concentrated on the same newcomers.** Top 1% of parcels ≈ a fifth of the
   bond; single-family p90/p10 ≈ 15×; the map of heaviest payers is a map of recent sales and
   recent construction.
4. **Scale check on one real parcel** (53-1695-26, net AV $728,900, FY26 bill $21,064):
   Measure U adds **$161/yr** at the advertised average, **$255** at the disclosed peak,
   **~$511** at the today's-base benchmark — 0.8–2.4% of the bill, of which ~57% is flat /
   square-footage charges outside the ad-valorem channel entirely. Including this keeps the
   incidence argument honest about magnitude.
5. **Open to make this certifiable:** TRA per-district base; full line-item bill
   reconstruction (one bill now partially reconciled: the net-AV identity is verified, and
   the existing city GO rate was observed *declining* $60.90 → $49.00 per $100k FY25→FY26 —
   consistent with, not contradicting, the City's $44.13 combined-average claim); modeling
   of the remaining exemption classes (nonprofit, veteran, welfare).

*Provenance: assessor Feb-2026 snapshot; Resolution 72,338-N.S. Exhibit B; gate baseline
`data/baselines/measure_u_reconciliation_baseline_2026-08-15.json`; generator
`scripts/v4/build_jn_measure_u.py`; companion public map `docs/maps/bond_incidence.html`;
narrative `notes/2026-08-15_bond_measure_u_city_claims_incidence_v2050.md`.*"""))

# ----------------------------------------------------------------------------- build + execute
nb = new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"}})

OUT = "notebooks/v4/JN-MeasureU.ipynb"
if __name__ == "__main__":
    import os
    from nbconvert.preprocessors import ExecutePreprocessor
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    ep = ExecutePreprocessor(timeout=900, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": "."}})   # repo root, per convention
    nbf.write(nb, OUT)
    n_md = sum(1 for c in nb.cells if c.cell_type == "markdown")
    n_code = sum(1 for c in nb.cells if c.cell_type == "code")
    print(f"wrote {OUT}: {n_md} markdown + {n_code} code cells, "
          f"{os.path.getsize(OUT)/1e6:.1f} MB")
