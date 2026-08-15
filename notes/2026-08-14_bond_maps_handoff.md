# Hand-off — Municipal-bond incidence maps + the Berkeley structure maps (for the next CC)

**Written:** 2026-08-14. **For:** a Claude Code session picking up municipal-bond analysis and turning
these maps into websites. **Repo:** `~/berkeley-data` (git, branch `dev`; deploys to berkeleybuild.com).
**Read `CLAUDE.md` and `PROGRESS.md` first** — this doc assumes those rules (dev-only, snapshot-before-write,
CKAN is a verification target not a data source, John owns all pushes/deploys).

---

## 0. TL;DR — what exists, in one paragraph

There are **three interactive parcel maps**, each a MapLibre HTML that streams a sibling `*_data.json`,
with **clickable dots** (popup + a Google-Maps link). One is a **municipal-bond incidence map** (what a new
$300M bond costs each property owner, ad-valorem vs flat). The other two are a **construction time-lapse**
(every structure at its build year) and an **ownership / recorded-document-recency** map. All are generated
by re-runnable Python scripts from **open civic data** (Alameda assessor + parcel geometry). The target
architecture for the websites is documented in a **structure-history schema design doc** (§7 of it is the
whole taxation/bond model). The bond map's numbers are **directionally honest but calibration-limited** —
see §3 for exactly what's real vs placeholder.

---

## 1. The bond-incidence map (the main thing for a bond analyst)

- **Generator:** [scripts/gen_bond_incidence.py](scripts/gen_bond_incidence.py) — re-runnable machinery.
- **Output (served):** [docs/maps/bond_incidence.html](docs/maps/bond_incidence.html) + `docs/maps/bond_incidence_data.json` (4.7 MB, streamed).
- **Commit:** `45b521f` (graduated from a scratch prototype).
- **Run:** `python scripts/gen_bond_incidence.py` (from repo root; env in §8).

**What it shows** — 27,618 assessed parcels, three toggle modes + clickable popups:
1. **Annual cost (ad-valorem bond)** — each parcel's yearly cost under a hypothetical $300M GO bond.
2. **Flat-tax vs ad-valorem** — same $300M raised as a flat parcel tax; diverging color = who pays more/less.
3. **Last recorded document (refi/transfer)** — recording recency, a financial-activity signal (NOT tenure — see §4).

**The levy math (all DERIVED in the script, nothing hardcoded):**
```
tax base (total assessed value)   = SUM(TotalNetValue)          = $29.0 B  over 27,618 parcels
annual debt service ($300M/30yr/5%) = P·r/(1-(1+r)^-n)          = $19.5 M / yr   (level payments)
ad-valorem rate                    = annual ÷ total_AV          = $67 per $100,000 of assessed value
per-parcel cost (ad valorem)       = rate × parcel_AV           (median $448, p10 $84, p90 $1,220 → 15× spread)
flat parcel tax (same $)           = annual ÷ n_parcels         = $707 / parcel (uniform)
```
`PRINCIPAL`, `TERM_YEARS`, `INTEREST` are constants at the top of the script — change them and re-run.

**Honesty rails (baked into the script docstring — keep them):**
- Assessed value ≠ market value (Prop 13, acquisition-based). The AV distribution is the *point* of the
  incidence story but is NOT a wealth distribution.
- Exemptions (homeowner's $7k, nonprofit, veteran) are **not modeled** — the base is gross `TotalNetValue`.
- Uses **total citywide AV** as the district base — an approximation. The real per-district base needs the
  county **Tax Rate Area (TRA)** assignment (see §7 open items).
- **The actual tax bill is the oracle:** before publishing any projection, reproduce *current* bills from the
  model and reconcile. A rate you can't reproduce is one you don't understand. Never fabricate a levy rate
  (same discipline as CKAN).

**The core finding (survives all caveats):** an ad-valorem bond's cost is proportional to assessed value,
which — under Prop 13 — is wildly unequal for similar homes. A flat parcel tax redistributes that burden
(and lets high-value commercial off cheaply: a $162 M industrial parcel pays $109k/yr ad-valorem vs $707 flat).

**The full tax model design** (TRA, taxing entities, levy types, per-parcel bill reconstruction, scenario
layer) is **§7 of** [notes/2026-08-14_structure_history_open_data_design.md](notes/2026-08-14_structure_history_open_data_design.md). Read that before extending the bond work — it is the schema for doing this properly.

---

## 2. The other two maps (same architecture; for the "structures built" website)

**Construction time-lapse** — every structure at its build year, a play/slider animation.
- **Generator:** [scripts/gen_yearbuilt_timelapse.py](scripts/gen_yearbuilt_timelapse.py)
- **Output:** [docs/maps/berkeley_construction_timelapse.html](docs/maps/berkeley_construction_timelapse.html) + `berkeley_construction_data.json` (25,471 dated parcels)
- **Build date** = assessor `YearBuilt`, **overridden by City landmark true dates** where available
  ([data/reference/berkeley_landmark_build_dates.csv](data/reference/berkeley_landmark_build_dates.csv),
  from [scripts/gen_landmark_corrections.py](scripts/gen_landmark_corrections.py)). Assessor mis-dates ~70%
  of landmarks (median 8 yr off) — e.g. 2811 Benvenue is 1903, not the assessor's 1925.
- Play speed = the `setInterval(...,180)` in the JS (commit `0aa0173`, 3× slower than original).

**Ownership / recorded-document recency** — owner type + recording recency.
- **Generator:** [scripts/gen_ownership_map.py](scripts/gen_ownership_map.py)
- **Output:** [docs/maps/berkeley_ownership.html](docs/maps/berkeley_ownership.html) + `berkeley_ownership_data.json`
- **Owner-type classifier** (`owner_type()` in that script): individual / investor(LLC-Corp-LP) / trust / institutional. Result: individual 70%, trust 23%, investor 5.7%, institutional ~2%.
- ⚠ **This map was corrected 2026-08-14 (commit `586c3ae`)** — see §4; do not reintroduce "tenure/years held".

There's also an older ghost-unit map (`docs/maps/elmwood_hidden_units_map.html`) and detector
[scripts/ghost_units.py](scripts/ghost_units.py) — relevant to the structure-history site, not the bond work.

---

## 3. Clickable dots + the FOUR link targets John wants (read this carefully — most don't deep-link)

Every map's popup shows the parcel's facts + one working external link. John wants structure locations to
link to **(a) Google street view, (b) owner name, (c) county assessor record, (d) property tax record.**
Here is the verified reality of each (I tested them this session):

| Target | Status | Detail |
|---|---|---|
| **(a) Google Street View / Maps** | ✅ **Works, deep-links** | `https://www.google.com/maps/search/?api=1&query={ADDRESS}+Berkeley+CA`. Already in all three popups. |
| **(b) Owner name** | ✅ **We have it; no external record to link** | Owner names are in [data/reference/berkeley_parcel_owners_2026-08-13.csv](data/reference/berkeley_parcel_owners_2026-08-13.csv) (from the ArcGIS TaxParcel owner layer). The **county Assessor site deliberately HIDES owner names** (statutory privacy), and the Recorder deed index is a session-gated portal — so there is **no external owner-record to deep-link.** Best move: a **portfolio reveal on our own map** (1,654 owners hold ≥2 parcels; click owner → highlight all their parcels). |
| **(c) County assessor record** | ⚠ **Online but NOT deep-linkable** | `https://propinfo.acgov.org` returns a rich record — **35 years of assessed values, use code, parent/child parcel lineage** — but it's a POST/SPA: I tested `?PrintParcel=53-1695-26` and it **drops to a blank search form.** A per-dot link would land the user on an empty box. And it shows **no owner name.** |
| **(d) Property tax record** | ⚠ **Same page as (c)** | `propinfo.acgov.org` is the *joint* Assessor/Treasurer lookup — same URL, same no-deep-link limitation. |

**→ Design recommendation for the website (important):** since (c)/(d) can't be deep-linked and hide owners,
**do NOT link out — ingest the assessor/tax data into our own DB and show it inline in the popup.** We
already demonstrated pulling a full `propinfo.acgov.org` record per parcel (assessed-value history + use
code + parcel lineage), and we already hold owner names. So the popup can natively show *owner + assessed-
value history + tax estimate*, with **Google Street View as the only true external link.** The alternative
external option worth evaluating is **Regrid** (John has a free-access offer) — Regrid has per-parcel pages
and an API and may deep-link cleanly.

---

## 4. Load-bearing GOTCHA — `LatestDocumentDate` is NOT tenure (a validity bug we fixed)

Caught on a known-truth parcel: **2811 Benvenue (owned since 1988) displayed as "5 yr held."** Root cause:
`berkeley.db.LatestDocumentDate` is the **last recorded document of ANY kind** — a refinance, trust transfer,
or lien resets it. The **2020–2022 spike is the pandemic refinance boom** (2021 alone = ~9% of parcels,
impossible as sales). So "years owned" was systematically understated. **Both the ownership map and the bond
prototype were corrected** (commit `586c3ae`) to label it honestly as *"years since last recorded document"*
— a refi/financial-activity signal, never tenure. **True years-owned needs the County Recorder deed index
with document type** (grant deed = sale vs deed of trust = loan) — not in hand. Also note: the owners CSV's
own `LatestDocu` column is a **stale 2017-capped** extract — use `berkeley.db.LatestDocumentDate` (fresh to
2026) for the date, the CSV only for owner **names/types**.

---

## 5. Map architecture pattern (reuse this for every new map / the websites)

- **Stack:** MapLibre GL JS 4.7.1 + CARTO `light_all` raster basemap, both via CDN (unpkg + cartocdn). No build step.
- **Streaming:** the HTML is tiny (5–7 KB) and **fetches a sibling `*_data.json`** (4–5 MB, ~25–28k points) rather than inlining points. Keep this pattern; inlining 25k points bloats the HTML.
- **⚠ `file://` blocks the fetch (CORS) — you MUST serve it:** `cd docs/maps && python3 -m http.server 8777`, then open `http://localhost:8777/<map>.html`. On the deployed site (docs/ is web-served) it just works.
- **⚠ The CC in-app browser pane CANNOT render these large streamed maps** (memory) — it makes zero tile requests and `map.on('load')` never fires. **Verify via `javascript_tool`/data checks, not screenshots.** Real browsers (and the deployed site) render fine. Don't waste time trying to screenshot them in-pane.
- **Popup + link pattern** (in each generator's JS): `map.on('click','pts',...)` builds a `maplibregl.Popup` with the parcel facts + the Google-Maps `<a>`, plus `mouseenter/leave` cursor. Copy it for new maps.
- **APN joins:** always canonicalize via `housing_rules.to_canonical_apn(raw, "alameda")` (`sys.path.insert(0,"scripts"); from housing_rules import to_canonical_apn`). Never bare strip-non-digits. Lot **area** comes from parcel **geometry** (EPSG:2227, US ft), not the unreliable `LotSize` column.
- **Overlay:** Elmwood outline from `data/reference/berkeley_neighborhoods.geojson`.

---

## 6. Data inventory (every input, with schema)

| File | What | Key columns |
|---|---|---|
| [databases/berkeley.db](databases/berkeley.db) (50 MB) | **Alameda assessor parcels, 29,131** (refreshed 2026-06-16, Feb-2026 data) | `APN`, `TotalNetValue`/`Land`/`Imps` (assessed $), `Latitude`/`Longitude`, `LatestDocumentDate` (last recording — see §4), `SitusStree`/`SitusStr_1`/`SitusAddre`, `UseCode`, `LotSize` (⚠ mostly 0/unreliable) |
| [data/raw/berkeley_taxparcels_2026-08-12.geojson](data/raw/berkeley_taxparcels_2026-08-12.geojson) (13 MB) | parcel **polygons** (committed) | `APN`, `Units`, `UseCode`, `geometry` |
| [data/reference/berkeley_parcel_owners_2026-08-13.csv](data/reference/berkeley_parcel_owners_2026-08-13.csv) | **owner names** (ArcGIS TaxParcel owner layer) | `APN`, `OwnersName`, `LatestDocu` (⚠ stale 2017 — don't use for dates) |
| [data/reference/berkeley_neighborhoods.geojson](data/reference/berkeley_neighborhoods.geojson) | neighborhood polygons | `Name` (Elmwood, etc.), `geometry` |
| [data/reference/berkeley_landmark_build_dates.csv](data/reference/berkeley_landmark_build_dates.csv) | City-landmark true build dates (build-year override) | `apn`, `name_year` |
| [data/reference/berkeley_secondary_unit_addresses.geojson](data/reference/berkeley_secondary_unit_addresses.geojson) | RPP secondary-unit addresses (ghost units) | `FullAddres`, geometry |

**`UseCode` is a WEAK signal** (verified repeatedly): `1xxx`=SFR, `2xxx`=small residential, `73xx`=**condos**
(not commercial), `3x`≈commercial, `77xx`=apartments/mixed. Don't filter on raw codes — use a curated
two-level crosswalk (see the design doc §8, "building-type vocabulary").

---

## 7. The target architecture + open items for the bond analysis

**Read:** [notes/2026-08-14_structure_history_open_data_design.md](notes/2026-08-14_structure_history_open_data_design.md)
— the full schema for a structure-history database (identity spine, provenance/assertion stream, temporal
crosswalks, lineage). **§7 is the entire taxation/bond model** (TRA, `taxing_entity`, `levy` with base
mechanism, `measure`/bond, `tax_bill_line`, the scenario layer). **§8** is what we borrowed from UrbanSim
(Waddell), incl. the versioned `zoning` table.

**Open items to make the bond map publishable (in priority order):**
1. **Acquire the Tax Rate Area (TRA) data** — the parcel→TRA assignment + the annual **tax-rate book by TRA**
   (Alameda Auditor-Controller). This is what turns "total citywide AV" into a real per-district base and
   itemizes the actual levy stack (city/county/BUSD/Peralta/EBMUD/EBRPD/BART/AC Transit + parcel taxes).
2. **Reconstruct + reconcile current bills** against `propinfo.acgov.org` (the oracle) before any projection.
3. **Model exemptions** (homeowner's, nonprofit, veteran) — they shift the ad-valorem base.
4. **Ingest per-parcel assessor/tax records** (propinfo) into our DB → powers inline popups AND the bill
   reconciliation. Evaluate **Regrid** (free-access offer) for deed/transfer history + deep-linkable pages.
5. **The pro-forma feasibility angle** (does upzoning produce housing?) is a separate, taught module:
   [notebooks/v4/JN-Feasibility.ipynb](notebooks/v4/JN-Feasibility.ipynb) (generator
   [scripts/v4/build_jn_feasibility.py](scripts/v4/build_jn_feasibility.py), baseline
   `data/baselines/feasibility_baseline_2026-08-14.json`). Calibration ask drafted for Paul Waddell:
   [notes/2026-08-14_waddell_outreach.md](notes/2026-08-14_waddell_outreach.md).

---

## 8. Environment & discipline

- **Python:** `/opt/miniconda3/envs/jupyter_env/bin/python` (geopandas, pandas, plotly, nbformat, nbconvert).
- **Serve a map:** `cd docs/maps && python3 -m http.server 8777`.
- **Run a generator:** `python scripts/gen_<map>.py` **from repo root** (paths are repo-root-relative).
- **Notebooks execute from repo root** — `ExecutePreprocessor(...).preprocess(nb, {'metadata':{'path':'.'}})`, not `nbconvert --execute` (which uses the notebook's dir and breaks relative paths).
- **Discipline (from CLAUDE.md — non-negotiable):** dev branch only; **John owns all pushes/deploys** (never push without his say-so); **snapshot before any DB write** (`cp` + `PRAGMA integrity_check`, read-only preview → John's go-ahead → guarded write); **CKAN/HCD is a verification target, never a data source**; build only from CPRA + Alameda assessor. `scratch/` is gitignored + reboot-surviving for uncertain work.
- **Uncommitted prototype (gitignored, in `scratch/2026-08-14/`):** `gen_bond_incidence.py` (superseded by the scripts/ version), `elmwood_feasibility.py`, and the emitted Datasette CSVs. Ignore the scratch bond generator; `scripts/gen_bond_incidence.py` is canonical.

---

## 9. Session commit trail (all on `dev`, nothing pushed)
`8b7917f` clickable dots + Google-Maps link · `0aa0173` slower play speed · `586c3ae` ownership
tenure→recording-recency validity fix · `45b521f` bond map graduated to docs/maps + UrbanSim prior-art ·
`3a2ac07` teaching JN-Feasibility + Waddell draft. Design doc + Waddell draft + feasibility baseline are all
committed and unpushed.
