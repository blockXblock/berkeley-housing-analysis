# Berkeley Housing Website — Operations & Architecture Guide

**Purpose:** the durable guide for future-you to update/edit berkeleybuild.com, and the design
reference for building more robust, extendable sites (e.g. replicating the model for other cities).
**Location note:** this lives in `website/` (repo root), **outside `docs/`**, on purpose — GitHub
Pages serves `docs/`, so anything there can become public (a handoff doc was inadvertently live on
berkeleybuild.com for ~4.5 hours on 2026-05-16). Keep internal ops docs out of `docs/`.

Companion: `docs/audit/2026-06-08_how_the_website_is_built.md` (the short reconciliation);
`notes/2026-05-22_website_fragility_diagnosis.md` + `notes/2026-05-22_script_lineage_inventory.md`.

---

## PART 1 — Current architecture (what we have)

berkeleybuild.com is **two layers**:

1. **Claude/CC-authored HTML/JS pages** (edited directly — there is **no site-generator** that emits
   them). Hours of iterative Write/Edit built these.
2. **One script-generated data file** — the Explorer's data, produced from the database.

### Pages (served from `docs/` → GitHub Pages → Cloudflare → berkeleybuild.com)
| File | Role | Changed by |
|---|---|---|
| `docs/index.html` | Homepage: hero, stats, cards, **video embeds**, notebook tables. Button → `explorer.html`. | edit directly |
| `docs/explorer.html` | Explorer **app shell**: tabs + viz (Tailwind / Chart.js / D3-Sankey / Leaflet via CDN). | edit directly |
| `docs/explorer.js` | Explorer **client logic** (~184 KB). | edit directly |
| `docs/explorer_data.js` | **GENERATED** `const DATA = {projects, events, fees, staff, players, timeline, documents}` (~1.5 MB). | re-run exporter |
| `docs/map.html`, `docs/methodology.html`, `docs/explorer_v2.html` | secondary / legacy pages | edit directly |
| `docs/geometry.kml`, `docs/tours/*` | Google Earth geometry + tours | `generate_kml.py` |
| `docs/videos/*.mp4` | local flyover videos | hand-added |

Load chain: `explorer.html` → `explorer_data.js` (generated) → `explorer.js` (authored).

### The one generator
`scripts/export_explorer_data_v2.py` — reads `databases/berkeley_housing_v2.db`
(projects, permit_events, fees, staff from `permit_events.marked_by`, developer/architect players),
writes `docs/explorer_data_v2_working.js`, which must end up as `docs/explorer_data.js` (the file the
page loads). **This is the only thing on the site that's script-generated.**

### Branch / deploy model
- **`dev`** = all analysis/audit/DB work; currently push-**HELD** (~15 commits ahead of origin).
- **`main`** = the **deploy branch** GitHub Pages serves from (`main` + `/docs`). In sync with origin.
- `origin` = `github.com/blockXblock/berkeley-housing-analysis`. Cloudflare sits in front of Pages.
- **Rule:** site deploys go to **`main` only** and must **not** drag the held `dev` commits to origin.
  (Databases are gitignored, so they never deploy regardless.)

---

## PART 2 — Operational playbooks

### A. Add or replace a YouTube video
1. *(You)* publish the video on YouTube (public or unlisted), copy the **video ID** (after `watch?v=`).
2. *(Me/edit)* insert an `<iframe>` in `docs/index.html` at the chosen spot, matching the pattern:
   ```html
   <iframe src="https://www.youtube.com/embed/VIDEO_ID?autoplay=1&mute=1&loop=1&playlist=VIDEO_ID&controls=1&modestbranding=1&rel=0"
           title="TITLE" frameborder="0"
           allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
           allowfullscreen></iframe>
   ```
   (Drop the `?autoplay…` query for a plain click-to-play embed.)
3. Deploy (Playbook E). Decide placement: first/hero video vs a later card.
4. *(You)* if it doesn't appear, **purge Cloudflare cache** (dashboard) or wait for TTL.

### B. Edit text / layout / tabs
Edit the relevant `.html`/`.js` directly. Homepage = `index.html`; Explorer UI = `explorer.html`
(structure) + `explorer.js` (behavior). No build step; preview locally by opening the file.

### C. Refresh Explorer data after a DB change
```
python scripts/export_explorer_data_v2.py      # writes docs/explorer_data_v2_working.js
cp docs/explorer_data_v2_working.js docs/explorer_data.js   # the file the page actually loads
```
**Never run the v1 `scripts/export_explorer_data.py`** (reads the frozen v1 DB; it's the source of the
historical "data appeared/disappeared" bug). Verify the diff looks sane, then deploy (E).

### D. Add / update a KML tour or geometry
`python scripts/generate_kml.py` → regenerates `docs/geometry.kml` / `docs/tours/*`. Tour-authoring
conventions: `docs/methodology/kml_tour_authoring_prompt.md`. Deploy (E).

### E. Deploy (the isolation procedure)
The site change must reach `main` without carrying held `dev` work:
```
# from a clean state, with your change committed on dev (or staged):
git checkout main
git checkout dev -- docs/index.html          # bring ONLY the changed file(s) over
git commit -m "site: <what changed>"
git push origin main                          # publishes via GitHub Pages
git checkout dev                              # back to work branch
```
Then keep `dev` and `main` in sync for those files so they don't diverge. **Always show the diff and
get a human go-ahead before `git push` — pushing is publishing.** After push: GitHub Pages rebuilds
(~1 min); Cloudflare may serve stale HTML until cache purge/TTL.

### F. Rollback
`git revert <commit>` on `main` + push, or `git checkout main~1 -- docs/<file>` then commit. The
previous `explorer_data*.js` snapshots (e.g. `explorer_data_pre_v2_rewrite_*.js`) are kept for data
rollbacks.

---

## PART 3 — Known fragility & standing rules (don't repeat these)
1. **Two competing data exporters** (`export_explorer_data.py` v1 vs `export_explorer_data_v2.py` v2),
   both claiming "single source of truth," writing **different filenames**. The site once served
   months-stale v1 data. → **Keep only the v2 path; delete or quarantine the v1 exporter; make its
   output filename = the loaded filename.**
2. **Internal docs in `docs/` can go public.** Keep ops/notes **out of `docs/`** (this file's location).
3. **Branch discipline:** `dev` = work (push-held); `main` = deploy. Never merge `dev`→`main`
   wholesale; cherry-pick the site files.
4. **Cloudflare caches** the page — a deploy isn't visible until cache clears.
5. **Hand-duplicated embeds:** video iframes are copy-pasted across the page; there's no single list,
   so they drift. (See Part 4.)

---

## PART 4 — Architecture for robust, extendable sites (incl. multi-city)

The current site works but is **fragile by construction**: presentation and data are entangled,
content is hand-duplicated, the build is manual, and there's no CI. For the project's stated goal —
*"any high school in California should be able to clone the model for their local city"* — the
architecture has to become **data-driven, componentized, and reproducibly built.** Target principles:

1. **Separate data from presentation (one source of truth).** All dynamic content — projects, videos,
   tours, stats, nav — comes from **structured data** (the DB + small JSON/YAML manifests), never
   hand-typed into HTML. A `videos.json` (`{id, title, description, section, autoplay}`) rendered into
   embeds kills the copy-paste drift in Part 3 #5.

2. **One canonical export, output where it's loaded.** Collapse the two exporters into one
   (`export_site_data.py`) that writes directly to the file the page loads (no rename step, no v1/v2
   ambiguity). Validate row counts / completion fingerprint on export (we already do this for the DB).

3. **Componentize / template.** Use a lightweight static-site generator (**Eleventy, Astro, or Hugo**)
   so headers, nav, video cards, project cards are **components**, authored once and reused across
   pages and across cities. This is the single biggest robustness win and the prerequisite for
   multi-site reuse.

4. **Reproducible build + CI.** A documented build step (`npm run build` / SSG build) run by **GitHub
   Actions** on merge to `main` → no manual file copies, no "did I run the exporter?" The deploy
   becomes: merge content → CI builds → Pages publishes → (optional) Cloudflare cache purge via API.

5. **Config-driven multi-city.** One codebase, **per-city config + data**: `cities/berkeley/config.yml`
   + that city's DB export. A new city = new config + data dir + its own open-data feed, same templates
   and notebooks. This *is* the "clone for your city" framework. The DB schema and the export contract
   become the portable interface.

6. **Deploy hygiene.** Keep the **content/site repo separate from the analysis branch** (or use a
   protected `main` + PR previews). Cache-bust generated assets (hash in filename, e.g.
   `explorer_data.<hash>.js`) so Cloudflare/browsers never serve stale data.

7. **Verification.** Build-time link checks, schema-valid manifests, and a smoke test that the Explorer
   loads the expected project count — the same verify-before-ship discipline used on the database.

**Recommended target stack (concrete):** Astro or Eleventy (components + Markdown content) →
data from a single documented DB export + JSON manifests → GitHub Actions build/deploy → Cloudflare
with cache-purge-on-deploy → per-city config dirs for replication. Migrate incrementally: first move
the video list to a manifest (#1), then unify the exporter (#2), then templatize the shared chrome
(#3), then add CI (#4) — each step independently shippable.

---

## Quick reference
- **New video:** edit `docs/index.html`, deploy to `main` (Playbook A+E).
- **Data refresh:** `export_explorer_data_v2.py` → copy to `explorer_data.js` → deploy (C+E).
- **Deploy = `main` only, push is publishing, get go-ahead, then Cloudflare purge.**
- **Never** run the v1 exporter; **never** put internal docs in `docs/`; **never** merge `dev`→`main`.
