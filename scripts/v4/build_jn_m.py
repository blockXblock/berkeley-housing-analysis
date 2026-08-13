#!/usr/bin/env python3
"""build_jn_m.py — generator for notebooks/v4/JN-M_corridor_density.ipynb.

The durable, re-runnable home of the 2026-08 corridor housing-density investigation. Markdown-in-
source (text cells ARE the deliverable). Derives every figure from data and asserts against the
timestamped baseline (data/baselines/corridor_density_baseline_2026-08-12.json) — never hardcodes.

Run:  python scripts/v4/build_jn_m.py    # (re)writes the .ipynb
"""
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

nb = new_notebook()
C = []
def md(s): C.append(new_markdown_cell(s.strip()))
def code(s): C.append(new_code_cell(s.strip()))

md(r"""
# JN-M — Berkeley Corridor Housing Density

**Question (John's thesis):** College Ave / Elmwood has far more multi-unit housing per block than the
zoning label suggests, and people are *"building in their back yards"* — adding ADUs on lots the map
calls single-family. Show it, and compare College to other corridors and to the rest of Berkeley.

**Headline finding.** College–Elmwood (Dwight→Alcatraz) runs **~15 du/acre — 2.2× the citywide median
(6.8)** — and *exceeds* the University Ave commercial corridor (6.0). The **East side of College**
(zoned low "for fire evacuation") carries **~4× the ADU-building rate of the West** — densification is
concentrated on exactly the side the map freezes.

**Method, in one line:** existing stock = Census 2020 PL (units/pop per block) on TIGER2020 geometry;
adds = our fixed-classifier ADU cohort; corridors cut at the city's own boundaries (College = Dwight→
Alcatraz, per the Corridors Zoning Update). Density = units per **land** acre.

> **Current regime = Middle Housing (Ord. 7,978-N.S., effective Nov 1 2025):** up to **8 units by-right on
> a 5,000 sf residential lot** (≈70 du/ac), everywhere residential except the high fire-hazard hills. This
> supersedes the old R-1…R-4 du/ac caps — so this notebook benchmarks existing density against the **Middle
> Housing allowance**, not the defunct districts.

> **Discipline:** every number below is DERIVED and gated against an external timestamped baseline
> (`data/baselines/corridor_density_baseline_2026-08-12.json`). A legitimate change = append a new
> baseline, never edit a magic number.
""")

md(r"""
## Data lineage

```mermaid
graph LR
  PL[Census 2020 PL 94-171<br/>pop P1 + housing H1] --> BLK[berkeley_blocks_2020.geojson<br/>1,522 blocks]
  TIG[TIGER2020 tabblock20<br/>geometry + ALAND] --> BLK
  ADU[ADU cohort<br/>fixed classifier, ~93% vs APR] --> IDX
  PAR[berkeley.db parcels<br/>situs -> corridor tag] --> IDX
  BLK --> IDX[block_density_index.py<br/>build + corridor_summary]
  CZU[CZU Existing Conditions<br/>Dwight->Alcatraz, zoned caps] -.corridor bounds + caps.-> IDX
  IDX --> FIG[figures -> baseline gate]
  IDX --> VIZ[choropleth / 3D KML / vs-zoned]
```

**Not a data source (firewall):** the HCD APR (validation oracle only) and the CZU's *derived* density
numbers (comparison target only). Per-parcel **zoning** is form-based and lives behind Accela ACA (to be
harvested there — Socrata WAF-blocks this environment); it is NOT ingested here.
""")

code(r"""
import os, sys, json
# resolve repo root (dir with CLAUDE.md) so relative data paths + the scripts import work from anywhere
_d = os.getcwd()
while _d != "/" and not os.path.exists(os.path.join(_d, "CLAUDE.md")): _d = os.path.dirname(_d)
os.chdir(_d); sys.path.insert(0, os.path.join(_d, "scripts"))
from block_density_index import build, corridor_summary, figures
import pandas as pd; pd.set_option("display.width", 170)
blk = build()
summary = corridor_summary(blk)
summary
""")

md(r"""
### Reading the table
`du_per_ac` = existing housing units per **land** acre (Census 2020). `adu_per_ac` = our ADU cohort
adds per acre — the *backyard-building rate*. `pct_of_cap` = existing density as a share of the
**indicative** zoned du/ac cap (only meaningful for the lot-area-per-unit zones — R-1/R-2/R-2A; the
`NaN` corridors are form-based, no du/ac cap). The two indented rows split College **East vs West** of
the avenue centerline.
""")

code(r"""
# --- VIZ 1: choropleth (where) — blocks colored by du/acre, corridors outlined ---
import matplotlib.pyplot as plt, numpy as np
from matplotlib.colors import ListedColormap; from matplotlib.patches import Patch
g = blk.to_crs(3857)
bins=[0,5,10,20,40,1e9]; cols=["#f7f7f7","#fdd49e","#fc8d59","#d7301f","#7f0000"]
g["cls"]=pd.cut(g.dua,bins=bins,labels=False,include_lowest=True)
fig,ax=plt.subplots(figsize=(9,11))
g.plot(ax=ax,color=[cols[int(c)] if pd.notna(c) else "#eee" for c in g.cls],edgecolor="#bbb",linewidth=.15)
CC={"College (Elmwood)":"#00a0dc","University":"#8a2be2","Adeline":"#00897b","Telegraph":"#e6007e","Solano":"#666"}
for n,c in CC.items():
    s=g[g.corridor==n]
    if len(s):
        s.dissolve().boundary.plot(ax=ax,edgecolor=c,linewidth=2.2)
        cx,cy=s.dissolve().geometry.centroid.iloc[0].coords[0]
        ax.annotate(f"{n}\n{s.housing_units.sum()/s.acres.sum():.0f} du/ac",(cx,cy),ha="center",
                    fontsize=8,fontweight="bold",color=c,bbox=dict(boxstyle="round,pad=.2",fc="white",ec=c,alpha=.9))
ax.legend(handles=[Patch(fc=cols[i],ec="#999",label=l) for i,l in enumerate(["<5 (SFR)","5-10","10-20","20-40","40+"])],
          loc="lower left",fontsize=8,title="units/acre")
ax.set_title("Berkeley block housing density (Census 2020) — units per land acre",fontweight="bold"); ax.set_axis_off()
plt.tight_layout(); plt.show()
""")

md(r"""
> **What this could mislead about:** hills read white (low) partly because blocks are large — always
> pair the map with the per-acre table. Corridor outlines are census blocks *near* the avenue, not
> parcel-exact frontage.
""")

code(r"""
# --- VIZ 2: existing density vs the CURRENT by-right allowance (Middle Housing, eff Nov 1 2025) ---
from block_density_index import MH_BYRIGHT_DU_AC, MH_RESIDENTIAL
s=corridor_summary(blk).set_index("cohort")
order=["College (Elmwood)","Telegraph","Adeline","University","Solano"]
dua=[float(s.loc[c,"du_per_ac"]) for c in order]; city=float(blk.housing_units.sum()/blk.acres.sum())
fig,ax=plt.subplots(figsize=(10,5)); y=np.arange(len(order))
ax.barh(y,dua,color=["#00a0dc","#e6007e","#00897b","#8a2be2","#666"])
ax.axvline(MH_BYRIGHT_DU_AC,color="#c00",lw=2)
ax.text(MH_BYRIGHT_DU_AC-1,len(order)-0.5,f"Middle Housing by-right ≈{MH_BYRIGHT_DU_AC:.0f} du/ac\n(8 units / 5,000 sf lot, residential)",
        ha="right",va="center",fontsize=8,color="#c00")
ax.axvline(city,ls="--",color="gray"); ax.text(city+.4,-.7,f"citywide {city:.1f}",fontsize=8,color="gray")
for i,c in enumerate(order):
    tag = f"{100*dua[i]/MH_BYRIGHT_DU_AC:.0f}% of MH allowance" if c in MH_RESIDENTIAL else "commercial corridor (MH n/a)"
    ax.text(dua[i]+.5,i,tag,va="center",fontsize=8,color="#555")
ax.set_yticks(y); ax.set_yticklabels(order); ax.invert_yaxis(); ax.set_xlabel("du / land acre")
ax.set_xlim(0, MH_BYRIGHT_DU_AC*1.08)
ax.set_title("Existing density vs the CURRENT by-right ceiling (Middle Housing, eff. Nov 1 2025)",fontweight="bold")
plt.tight_layout(); plt.show()
""")

md(r"""
## Reframe: the current regime is Middle Housing, not the old districts

The **Middle Housing Ordinance (7,978-N.S., effective Nov 1 2025)** allows **up to 8 units by-right on a
typical 5,000 sf residential lot** (3 stories / 35 ft; ≈52 ft with density bonus) across **all primarily-
residential Berkeley EXCEPT the high fire-hazard hills.** That **supersedes** the old R-1/R-2/R-2A/R-3/R-4
du/ac caps — so benchmarking existing density against those old caps is meaningless. The honest story:

- **The existing-density finding stands and is regime-independent** — College–Elmwood ~15 du/ac = 2.2×
  citywide is the *already-built* hidden multi-unit + backyard-ADU density, whatever the code says.
- **Against the current ~70 du/ac by-right ceiling, every corridor is far below** — College–Elmwood is
  only ~**22%** of what Middle Housing now permits. The story flips from "denser than allowed" to
  **"already dense, and now vastly more is legal by-right."**
- **The relevant map is now Middle-Housing-eligible vs fire-hazard-EXEMPT** (§2 below), not old districts.
  ADU-building is the one lever that still works in the exempt hill areas — worth testing whether the
  East-of-College ADU cluster sits inside the exemption.

**Per-parcel zoning / MH-eligibility** is **harvested via Accela ACA** (`aca-prod.accela.com/BERKELEY/`),
NOT Socrata (which WAF-blocks this environment). Queued.
""")

md(r"""
## §2 — Middle-Housing-eligible vs fire-hazard-EXEMPT

Middle Housing exempts the high fire-hazard hills. So the current-regime map is **eligible vs exempt**, not
old districts. Overlaying Berkeley's Hill/Fire Zones (city ArcGIS org, curl-accessible — *not* Socrata) on
the corridor blocks tests a tempting hypothesis: *is the ADU-heavy East side of College inside the fire
exemption (i.e., the one lever left where MH doesn't reach)?*
""")

code(r"""
# --- fire-hazard (MH-exempt) overlay: Hill Zone 2-3 ---
from block_density_index import fire_exempt_mask
b = blk.copy(); b["fire_exempt"] = fire_exempt_mask(b)
print(f"Berkeley blocks in high-fire-hazard (Hill Zone 2-3, MH-exempt): {int(b.fire_exempt.sum())} / {len(b)}")
ce = b[b.corridor == "College (Elmwood)"]
for side in ["West", "East"]:
    s = ce[ce.college_side == side]
    print(f"  College {side:5}: {len(s):2} blocks | in fire-exempt zone = {int(s.fire_exempt.sum())} | "
          f"ADUs = {int(s.adu_adds.sum())} | {s.housing_units.sum()/s.acres.sum():.1f} du/ac")
""")

md(r"""
**Result — hypothesis disproved.** College–Elmwood is **0 / 44 blocks** in the fire-hazard zone (it's
flatland) — **both sides are fully MH-eligible.** So the ~4× ADU concentration on the East side is **not** a
fire-exemption artifact; its cause is elsewhere (larger single-family lots / owner-builder incentive — to
test next). The density corridors all sit **outside** the ~24% of the city (the hills) that MH exempts —
i.e., Middle Housing's 8-units-by-right *does* reach exactly where the hidden density already is.
""")

code(r"""
# --- BASELINE GATE: derive vs the external timestamped baseline (never hardcode) ---
base=json.load(open("data/baselines/corridor_density_baseline_2026-08-12_mh.json"))
got=figures(blk); want=base["figures"]; bad={}
for k,v in want.items():
    if abs(float(got[k])-float(v))>0.05: bad[k]=(got[k],v)
if bad:
    raise AssertionError(f"figures drifted vs baseline {base['created']} @ {base['git_sha']}: {bad}\n"
                         "-> DIAGNOSE (computed vs baseline, likely cause) then APPEND a new timestamped baseline, do not edit magic numbers.")
print(f"baseline gate PASS — {len(want)} figures match {base['created']} @ {base['git_sha']}")
print(json.dumps(got,indent=2))
""")

md(r"""
## Next steps (queued)
1. **Accela ACA per-parcel zoning harvest** for the corridor parcels → parcel-exact "denser than
   zoned" (our HARVESTER; John logs in). Replaces the WAF-dead Socrata path.
2. **CPRA #26-1972-style request** already drafted (`notes/2026-08-12_cpra_corridors_parcel_gis.md`)
   for Raimi's parcel GIS (existing units + opportunity coding) as an independent cross-check.
3. **Building footprints / sqft** → realized FAR → the FAR-headroom version for form-based zones.
4. **deck.gl / 3D KML** density skyline for the web (the extruded-block KML is built).
""")

nb["cells"] = C
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
import os
os.makedirs("notebooks/v4", exist_ok=True)
nbf.write(nb, "notebooks/v4/JN-M_corridor_density.ipynb")
print("wrote notebooks/v4/JN-M_corridor_density.ipynb —", len(C), "cells")
