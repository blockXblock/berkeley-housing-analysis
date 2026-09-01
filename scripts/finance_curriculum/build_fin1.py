#!/usr/bin/env python3
"""Generate FIN1 — Where Berkeley's Money Comes From and Where It Goes.

First module of the city-finance curriculum (notebooks/finance_curriculum/).
Same discipline as the v4 investigation JNs: every figure in the notebook is
DERIVED at run time from the external-facts file — nothing is typed into a
chart call. Run:  .venv/bin/python scripts/finance_curriculum/build_fin1.py
"""
import nbformat as nbf
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "notebooks" / "finance_curriculum" / "FIN1_where_the_money_goes.ipynb"

cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s))
code = lambda s: cells.append(nbf.v4.new_code_cell(s))

md("""# FIN1 — Where Berkeley's Money Comes From and Where It Goes

**Berkeley City Finance Curriculum · Module 1**

This notebook teaches you to read a city's money the way an auditor would:
from the city's own filed documents, deriving every number yourself.

**The one rule of this curriculum:** no number in any chart is typed in by
hand. Every figure is computed, at run time, from a *facts file* that records
where each number came from (document, page, URL). If you don't believe a
number, the provenance is right there — go check it.

**What you'll be able to answer after this module:**
1. How much money does Berkeley take in, and from whom?
2. How much does it spend, and on what?
3. Why are those two numbers different — and why is that not a scandal?
4. What are pensions, and why does every budget conversation end up there?
""")

md("""## 1. The facts file

Cities publish their finances in two very different documents:

- The **ACFR** (Annual Comprehensive Financial Report) — *what actually
  happened* last fiscal year, audited.
- The **Adopted Budget** — *what the Council plans* to spend next year.

We extracted the key figures from Berkeley's FY2025 ACFR and the adopted
FY2027 budget into one JSON file, with a `sources` block naming every
document. ▶ Load it and look at the provenance first — always.""")

code("""import json, pandas as pd
from pathlib import Path

REPO = Path.cwd()
while not (REPO / "data" / "reference").exists():   # find repo root from notebook cwd
    REPO = REPO.parent

FACTS = json.load(open(REPO / "data" / "reference" / "berkeley_budget_external_facts_2026-08-15.json"))
print("facts as of:", FACTS["as_of"])
for k, v in FACTS["sources"].items():
    print(f"  {k}: {v[:95]}")""")

md("""## 2. Where the money comes from (FY2025, actual, audited)

📝 **What to read from this:** the *shape*. A city is not funded by one tax —
it is a bundle of revenue streams with different rules. Watch for three
groups: taxes on property **value**, taxes on building **size** (parcel
taxes), and taxes on what you **buy**. That VALUE / SIZE / BUY split is the
framework for Module 2.""")

code("""rev = {k: v for k, v in FACTS["revenues_fy2025_actual"].items() if not k.startswith("_") and k != "total"}
rev_total = FACTS["revenues_fy2025_actual"]["total"]

df = (pd.Series(rev, name="fy2025_actual_$").sort_values(ascending=False).to_frame())
df["share_%"] = (df["fy2025_actual_$"] / rev_total * 100).round(1)
residual = rev_total - df["fy2025_actual_$"].sum()
print(f"Citywide (all-funds) revenue, FY2025 actual: ${rev_total:,.0f}")
print(f"extraction residual (ACFR total minus the itemized lines): ${residual:,.0f} "
      f"({residual/rev_total*100:.2f}%) — small lines not itemized in the facts file; we carry it explicitly")
df.style.format({"fy2025_actual_$": "${:,.0f}"})""")

code("""# Group the streams for the flow diagram — the grouping is OURS (a lens),
# the dollars are the ACFR's.
GROUPS = {
    "Property tax (VALUE)": ["property_tax_general", "property_tax_debt_service"],
    "Parcel taxes (SIZE)": ["parcel_tax_library", "parcel_tax_parks", "parcel_tax_fire", "parcel_tax_paramedic"],
    "Sales & use taxes (BUY)": ["sales_tax"],
    "Other taxes": ["utility_users_tax", "business_license_tax", "transient_occupancy_tax", "other_taxes"],
    "Charges for services": ["charges_for_services"],
    "Grants & subventions": ["grants_operating", "grants_capital", "state_subventions"],
    "Investment & misc": ["investment_earnings", "miscellaneous"],
}
grouped = {g: sum(rev[k] for k in keys) for g, keys in GROUPS.items()}
grouped["Unattributed (extraction residual)"] = residual
assert abs(sum(grouped.values()) - rev_total) < 1, "grouping + residual must conserve the total"
for g, v in sorted(grouped.items(), key=lambda x: -x[1]):
    print(f"  {g:28s} ${v/1e6:7.1f}M  ({v/rev_total*100:4.1f}%)")""")

md("""### ▶ The revenue flow

📝 *Before you look:* a Sankey diagram makes flows proportional — a ribbon
twice as wide is twice as much money. Find the widest ribbon. It is **not**
property tax.""")

code("""import plotly.graph_objects as go

labels = list(grouped.keys()) + [f"All city revenues FY2025 (${rev_total/1e6:,.0f}M)"]
target = len(grouped)
fig = go.Figure(go.Sankey(
    node=dict(label=labels, pad=18, thickness=16),
    link=dict(
        source=list(range(len(grouped))),
        target=[target] * len(grouped),
        value=[grouped[g] for g in grouped],
    ),
))
fig.update_layout(title="Berkeley citywide revenues, FY2025 actual (ACFR) — derived, not typed",
                  height=430, margin=dict(l=10, r=10, t=40, b=10))
fig.show()""")

md("""📝 **What this could mislead you about:**
- *Charges for services* is the biggest single stream — but much of it is
  enterprise activity (refuse, marina, permits) where the charge funds the
  service that collects it. It is not free money the Council can move around.
- The diagram shows one year. Grants and investment earnings swing hard
  year to year; parcel taxes are stable by design.
- This is **citywide, all funds** — not the General Fund. The General Fund
  (the money the Council actually steers) is a subset.""")

md("""## 3. Where the money goes (FY2027, adopted plan)

📝 The spending side comes from a different document (the adopted budget)
for a different year (FY2027) — so the totals will NOT match the revenue
chart, and *that mismatch is the first exercise in honest reading*
(section 4).""")

code("""spend = FACTS["spend_fy2027_adopted"]
spend_total = spend["total"]
dept = pd.Series(spend["by_department"]).sort_values(ascending=False)
assert abs(dept.sum() - spend_total) <= 2, "departments must sum to the adopted total (±$2 rounding)"

TOP_N = 8
top = dept.head(TOP_N)
other = dept.iloc[TOP_N:].sum()
flows = list(top.items()) + [(f"All other ({len(dept)-TOP_N} depts)", other)]

labels = [f"FY2027 adopted budget (${spend_total/1e6:,.0f}M)"] + [n for n, _ in flows]
fig = go.Figure(go.Sankey(
    node=dict(label=labels, pad=18, thickness=16),
    link=dict(source=[0]*len(flows), target=list(range(1, len(flows)+1)),
              value=[v for _, v in flows]),
))
fig.update_layout(title="Berkeley adopted spending by department, FY2027 — derived, not typed",
                  height=460, margin=dict(l=10, r=10, t=40, b=10))
fig.show()""")

md("""📝 **What to notice:** Public Works and Health, Housing & Community
Services outrank Police — most people guess wrong. And the **category** view
below tells you *why* budgets are hard to cut: salaries and benefits are the
dominant category, and they are contractual.""")

code("""cat = pd.Series(spend["by_category"]).sort_values(ascending=False)
assert abs(cat.sum() - spend_total) <= 2
for k, v in cat.items():
    print(f"  {k:28s} ${v/1e6:7.1f}M  ({v/spend_total*100:4.1f}%)")""")

md("""## 4. Why revenues ≠ spending (and why that's not a scandal)

The revenue chart says one number; the spending chart says a much bigger
one. ▶ Compute the gap, then read the four honest reasons.""")

code("""gap = spend_total - rev_total
print(f"FY2027 adopted spend  ${spend_total/1e6:,.1f}M")
print(f"FY2025 actual revenue ${rev_total/1e6:,.1f}M")
print(f"difference            ${gap/1e6:,.1f}M")""")

md("""Four reasons, all structural:
1. **Different years** — FY2025 actuals vs FY2027 plan (two years of growth).
2. **Internal services double-count** — departments "buy" IT, fleet, and
   building services from each other; the adopted all-funds total counts the
   dollar on both sides.
3. **Capital spending** draws on fund balances and bond proceeds — money
   raised in *earlier* years.
4. **Adopted ≠ actual** — budgets authorize; actuals under-run.

**The skill:** when someone quotes "Berkeley's billion-dollar budget" or
"Berkeley only takes in $620M," they are both quoting real documents — for
different questions. Always ask: *which document, which year, which funds?*""")

md("""## 5. The pension undertow

Every California city-budget conversation arrives here. ▶ Derive Berkeley's
employer pension contributions and rates from the ACFR figures.""")

code("""p = FACTS["pensions"]
c = p["calpers_fy2025_actual"]
rates = p["employer_rates_pct_of_payroll"]
sal = FACTS["spend_fy2027_adopted"]["by_category"]["salaries_benefits"]
print(f"CalPERS employer contributions, FY2025 actual: ${c['total']/1e6:.1f}M")
for k in ("miscellaneous", "fire", "police"):
    print(f"  {k:14s} ${c[k]/1e6:5.1f}M   employer rate {rates[k]:.2f}% of payroll")
print(f"Net pension liability (6/30/2025): ${p['net_pension_liability_2025_06_30']/1e6:,.0f}M")
print(f"\\nFor scale: total FY2027 salaries+benefits budget = ${sal/1e6:,.0f}M")
print(f"CalPERS contribution ≈ {c['total']/sal*100:.0f}% of that category")""")

md("""📝 **Read the rates, not just the totals.** For every $100 of police
payroll, the city sends CalPERS ~$87 *on top*. That ratio — not any single
year's deficit — is why "just hire more" is never a free choice, and it is
the deep background to the sales-tax measure on the 2026 ballot.""")

md("""## 6. Integrity checks

The curriculum's discipline in miniature: the notebook re-verifies that its
own derivations conserve the source totals. If the facts file changes, these
cells — not a human's memory — catch it.""")

code("""checks = {
    "itemized revenues + residual = ACFR total": abs(sum(rev.values()) + residual - rev_total) < 1,
    "revenue residual is small (<0.5%)": abs(residual) / rev_total < 0.005,
    "revenue groups conserve the total": abs(sum(grouped.values()) - rev_total) < 1,
    "departments sum to adopted total (±$2)": abs(dept.sum() - spend_total) <= 2,
    "categories sum to adopted total (±$2)": abs(cat.sum() - spend_total) <= 2,
    "CalPERS components sum to its total": abs(sum(c[k] for k in ('miscellaneous','fire','police')) - c['total']) < 1,
}
for name, ok in checks.items():
    print(("✅" if ok else "❌"), name)
assert all(checks.values()), "integrity check failed — inspect the facts file"
print("\\nALL CHECKS PASS")""")

md("""## Exercises

1. Which revenue stream would fall fastest in a recession? Which would barely
   move? (Hint: VALUE vs SIZE vs BUY — Prop 13 makes one of them very slow.)
2. The four parcel taxes together raise more than the sales tax. Compute the
   ratio from `grouped`. What does that tell you about where Berkeley's
   voters have historically said yes?
3. `Non-Departmental` is a top-five "department." It has no employees. Look
   at the adopted budget (source `ADOPT` in the facts file) and find out what
   lives there.
4. Recompute the spending Sankey with `TOP_N = 12`. Which departments appear
   that you had never heard of?
5. **Harder:** the FY2027 General Fund pension budget is in the facts file
   (`gf_pension_budget_fy2027`). Compare it to the FY2025 actual citywide
   contribution. What are the two reasons the numbers differ?

## Where this goes next

- **FIN2 — The three ways a city taxes you** (VALUE / SIZE / BUY, and who
  actually pays, parcel by parcel)
- **FIN3 — How to read a bond** (Measure U's Tax Rate Statement, taken apart)
- **FIN4 — How a project list becomes a ballot measure** (the King Pool
  paper trail: commission → survey → silent re-scope)
- **FIN5 — The structural deficit** (why costs grow faster than revenues)
- **FIN6 — Ballot measures and the General Fund** (what each 2026 measure
  does to the money you just mapped)

*Sources: see the `sources` block printed in section 1 — every figure above
traces to a page of the ACFR FY2025 or the adopted FY2027–28 budget.*""")

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
})
OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUT)
print(f"wrote {OUT} ({len(cells)} cells)")
