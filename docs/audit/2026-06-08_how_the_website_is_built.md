# How berkeleybuild.com Is Built — Durable Summary — 2026-06-08

Written so we don't re-derive this every time. Reconciles the question "is the site hand-written or
generated?" — the answer is **both, in different layers**. Builds on `notes/2026-05-22_website_
fragility_diagnosis.md` and `notes/2026-05-22_script_lineage_inventory.md`.

## The short version
- **The HTML/JS pages were authored by Claude/CC directly** (Write/Edit, iteratively over many
  sessions — the "hours adding tabs, visualizations, videos, text"). **There is NO Python
  site-generator** that emits `index.html` or `explorer.html`. To change layout/text/videos/tabs,
  you **edit the HTML/JS directly** (Claude does it, or by hand).
- **One layer IS script-generated: the Explorer's DATA.** `scripts/export_explorer_data_v2.py` reads
  the database and writes the data blob the Explorer loads. The HTML *shell* and JS *logic* are
  stable Claude-authored files that consume that data.

So my earlier "hand-written, no generator" verdict was true *only of `index.html` specifically* — and
misleading about the site as a whole. The site is **Claude-generated (not script-generated) HTML +
one script-generated data file.**

## The pages (served from `docs/` → GitHub Pages → Cloudflare)
| File | What it is | How it changes |
|---|---|---|
| `docs/index.html` (824 ln) | Homepage: hero, stats, cards, **video embeds**, notebook tables. Button `href="explorer.html"` opens the Explorer. | **Edit directly.** git history = incremental content/style commits ("add YouTube embed", "increase button font sizes"). |
| `docs/explorer.html` (121 KB) | **The Explorer app shell** — tabs + visualizations (Tailwind, Chart.js, D3-Sankey, Leaflet, all via CDN). | **Edit directly.** Stable; the data script is written so this "doesn't need changes". |
| `docs/explorer.js` (184 KB) | The Explorer's **client-side logic** (tab rendering, charts, map). | **Edit directly** (Claude-authored JS). |
| `docs/explorer_data.js` (1.56 MB) | **GENERATED data blob** — `const DATA = {projects, events, fees, staff, players, timeline, documents}`. | **Re-run the exporter** (below). |
| also: `map.html`, `methodology.html`, `explorer_v2.html` (older) | secondary/legacy pages | edit directly |

Load chain: `explorer.html` → `<script src="explorer_data.js">` (generated) → `<script
src="explorer.js">` (authored).

## The one generator — and the fragility around it
`scripts/export_explorer_data_v2.py` — *"the ONLY script that should be used to generate
explorer_data.js."* Reads `databases/berkeley_housing_v2.db` (projects, permit_events, fees, staff
from `permit_events.marked_by`, developer/architect players) → writes a `const DATA={…}` JS file.

**⚠️ Known fragility (diagnosed 2026-05-22, the "data appears/disappears" bug):**
1. **Two competing exporters.** `export_explorer_data.py` (Gen-1, v1-era) reads the **frozen v1**
   `berkeley_housing_analysis.db` and writes `explorer_data.js` directly; `export_explorer_data_v2.py`
   (Gen-2) reads **v2** and writes `explorer_data_v2_working.js`. **Both** claim "single source of
   truth." For months the site served stale v1 data because the v1 script hadn't run since ~Apr 13 and
   the v2 script wrote to a *different filename*. **Use the v2 script only; never run the v1 one.**
2. **Filename gap.** v2 writes `docs/explorer_data_v2_working.js`; the site loads `docs/explorer_data.js`.
   The exporter's output must end up in `explorer_data.js` (copy/rename step). As of 2026-06-01 the two
   files are byte-identical (1,564,650 B) — i.e., the v2 output is now the live data; the gap was wired
   up during this session's explorer fix (v2 `v_projects_flat`-sourced + deploy).

## Other generated artifacts that feed the site (not the HTML itself)
- `scripts/generate_kml.py` → `docs/geometry.kml` + `docs/tours/*` (Google Earth tours, embedded/linked).
- `scripts/generate_apr_v2.py` → APR tables.
- Videos: hand-embedded YouTube IDs + `docs/videos/*.mp4` (no generator; live only in `index.html`).

## To refresh / change the site (the cheat sheet)
- **Change look/text/videos/tabs** → edit `docs/index.html` / `docs/explorer.html` / `docs/explorer.js`
  directly. No build step.
- **Refresh Explorer data after a DB change** → `python scripts/export_explorer_data_v2.py`, then
  ensure the output lands in `docs/explorer_data.js` (the file `explorer.html` loads). Do **not** run
  the v1 `export_explorer_data.py`.
- **Refresh map/tours** → `generate_kml.py`. **Deploy** → commit to `main` (GitHub Pages serves `docs/`).

## Bottom line
berkeleybuild.com = **Claude-authored HTML/JS pages** (edit directly; no site-generator) + **one
script-generated data file** (`export_explorer_data_v2.py` → `explorer_data.js`). The historical
fragility was *two* exporters and a filename mismatch, not a generator that rewrites the pages.
