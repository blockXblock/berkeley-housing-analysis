---
title: Website inventory + domain/identity strategy
date: 2026-08-25
type: diagnostic
status: open
area: notes
---

# Website inventory + domain/identity strategy

**Date:** 2026-08-25
**Status:** working note (`notes/` = in-flight; graduates to `docs/audit/` when decisions settle)
**Verified by:** `gh api` sweep of all 6 orgs + personal account, `curl` of every live Pages
URL, `dig`/response-header check of berkeleybuild.com, `git log` authorship audit.
Nothing here is from memory — re-verify before relying on it.

---

## 1. Live and current (the sites that matter)

| Site | Owner | Source | Host | Last touched |
|---|---|---|---|---|
| **berkeleybuild.com** | `blockXblock` | `berkeley-housing-analysis` `main:/docs` | GitHub Pages, Cloudflare DNS proxy in front | 2026-08-23 |
| berkeley-housing-map | `blockXblock` | `main:/` | GH Pages | 2025-12-20 |
| berkeley-housing-research | `blockXblock` | `gh-pages:/` | GH Pages | 2026-02-22 |
| berkeley-datasette | `blockXblock` | — | **Vercel** (not Pages) | 2025-12-17 |
| Berkeley2050/guide | `Berkeley2050` | `main:/` | GH Pages | 2026-03-18 |
| tan-derivative-visualizer | `johngage` | `master:/` | GH Pages | 2026-06-23 |

**Not deployed anywhere:** `johngage/feller-campaign` — PRIVATE, personal account, no Pages
config, no homepage URL. It is not live. If published as-is the visible owner is `johngage`.
Move it to an org *before* it goes public.

**No Pages configured:** `berkeley-shops-audience`, `BerkeleyShops/berkeley-shops-website`,
`BerkeleyShops/mailchimp-audience-datasette`, `blockXblock/house-X-house`,
`WaterForAll/CubicMeterCost`, plus 4 CourseChat repos.

---

## 2. Dormant sites — all 21 are LIVE and publicly visible

Every one returns HTTP 200. They are indexable and linkable today. 20 of the 21 sit at
`johngage.github.io/*` — the URL itself carries the name.

### Tier A — plain HTML, trivial to update (edit the file, push)

| Repo | Title served | Bytes |
|---|---|---|
| `johngage` | John Gage's Personal Website | 1,481 |
| `three-sisters-stories` | Three Sisters Stories | 2,175 |
| `WaterPowerData` | Home \| waterpower | 14,952 |
| `waterdatascience` | (pre-built static, `.nojekyll`) | — |

### Tier B — Jekyll "textbook" template, updatable with Ruby/bundler

All seven share the same scaffold (`Gemfile`, `Guardfile`, `Makefile`, `_config.yml`,
`_bibliography`, `_build`, `_includes`, `_layouts`). The landing page is a meta-refresh
redirect into the book's first chapter — **these work correctly**, they are not broken links.

| Repo | Redirects to | Target loads |
|---|---|---|
| `dailycal` | `/dailycal/intro` | 200 |
| `berkeley2050` | `/berkeley2050/intro` | 200 |
| `voteA` | `/voteA/shortguide/journalismnbc` | 200 |
| `h1` | `/h1/intro` | 200 |
| `JB1` | `/JB1/01_overviewJG` | 200 |
| `oct1` | `/oct1/page1` | 200 |
| `KiberaProjects` | `/KiberaProjects/jquery` | 200 |

Cost to revive: a working Ruby + bundler toolchain. The Gemfile.lock files are 2022-era and
will likely need `bundle update` against current Ruby. Non-trivial but bounded.

### Tier C — other generators

| Repo | Generator | Note |
|---|---|---|
| `tlpf` | **Hugo** (Wowchemy, `go.mod`, `netlify.toml`) | Wowchemy is deprecated upstream; a Hugo version bump may break it |
| `TILBlog` | Python (`app.py`, GitHub Actions) | Simon Willison TIL clone; has CI |
| `water` | Jupyter Book (`Makefile`, `content`, `_nb_header.html`) | |
| `KiberaTownCentre` | Jekyll | serves 2,048 bytes |
| `DataScienceInstitute` | static | PRIVATE repo, PUBLIC site |
| `XIO-OperationalDataKTC` | static | Pages status `errored` |
| `johngage.github.io_old` | rendered Hugo dump | titled "TLPF import" |
| `class_one` | Jekyll | |

### Broken

- **`Berkeley2050Tech`** — serves 146 bytes of unrendered Jekyll front matter (`---`).
  No `_config.yml` at root, so Jekyll never processes `index.html`. Publicly broken.

### Also live under orgs

`CourseChat`: CivEng112, openprojects, BerkeleyELP2024, InfrastructureChat, WaterNet.

### Taking one down

Archiving a repo does **not** remove its Pages site. Pages must be disabled explicitly
(`gh api -X DELETE repos/OWNER/REPO/pages`) *before* archiving — an archived repo is
read-only and the Pages setting can no longer be changed.

---

## 3. Hosting reality — three corrections

1. **berkeleybuild.com is GitHub Pages, not Cloudflare hosting.** Response headers carry
   `x-github-request-id`, `x-github-edge-region`, and Fastly's `x-served-by` / `via: 1.1 varnish`.
   Cloudflare is DNS proxy + CDN in front (`server: cloudflare`, and CF injects its
   `challenge-platform` script — that is the only diff between the served page and
   `docs/index.html`). Two stacked caches is why purges feel laggy.
   → Supersedes the framing in the `deploy-mechanics-no-purge` memory.

2. **`gh api .../pages` reports `status: errored`.** Stale legacy-build state from
   2026-07-02, before the repo switched to `build_type: workflow`. Actual deploys via
   [.github/workflows/pages.yml](.github/workflows/pages.yml) succeed — last success
   2026-08-23. Cosmetic, but it will mislead a future check.

3. **`dev` is 26 commits ahead of `main`**, unpushed. `main` is 0 ahead.

**Cloudflare CLI auth is expired** (`~/.wrangler` token expiry 2026-08-12). Zones and any
Pages projects can't be enumerated until `npx wrangler login`.

---

## 4. Name-independence audit

### Already clean

- `blockXblock`, `Berkeley2050`, `BerkeleyShops`, `WaterForAll`: **zero public members**,
  no org name / email / blog set. The public sees an org, not a person.
- `docs/index.html` and `docs/explorer.html`: **zero** occurrences of "John Gage".
- Repo-local git identity is already the GitHub noreply address, not gmail.

### Leaks

1. **`CourseChat` publishes `john.gage@gmail.com`** as org email, org name
   "Infrastructure Curriculum". Directly attributable. Fix immediately.
2. **Commit authorship.** 923 commits in the PUBLIC `berkeley-housing-analysis` authored
   `johngage <4306060+johngage@users.noreply.github.com>`. The noreply address encodes both
   the account ID and the login. Anyone who clicks "commits" has the answer.
3. **Global git config is `john.gage@gmail.com`** — any freshly cloned repo leaks the real
   address unless `user.email` is set per-repo.
4. **20 dormant sites live at `johngage.github.io/*`** — the hostname is the name.
5. `docs/berkeley2050/index.html` and `correspondence.html` name John Gage (3×). This is
   deliberate and historical (Sun Microsystems co-founder, task-force founding) — flagged
   for awareness, not as a defect.

### The honest ceiling

Org naming defeats casual attribution. It does **not** survive anyone who reads `git log`.
"Not immediately my name" is nearly achieved. "Not attributable" is a different and much
harder project — it would require rewriting 923 commits' authorship, and even then the
GitHub account that owns the org is visible to anyone the org ever interacts with publicly.

---

## 5. Recommended architecture for the new sites

**Domains via Cloudflare Registrar** — at-cost pricing, WHOIS privacy included and on by
default. That is the control that actually keeps the name off a public record. Do not
register anywhere that exposes WHOIS.

**Two new orgs, membership private, org profile left blank** — replicate the `blockXblock`
pattern, which is already verified working:

- `BerkeleyOpenData` — neutral data: explorer, Datasette, methodology, KML/geometry
  downloads. No advocacy prose anywhere in the repo.
- `BerkeleyFuture` *or* `BerkeleyInfrastructure` — political analysis: Measure U
  evaluations, ballot work, the `docs/berkeley2050/` content.

**Separate repos per site — not one repo with two subdirectories.** Cloudflare Pages *can*
serve two projects from different directories of one repo, but a neutral-data site whose
public repo visibly contains the advocacy content is not neutral. Keep
`berkeley-housing-analysis` as the pipeline; publish generated artifacts into each site repo
via an Action with a deploy key. Site repos then hold data + presentation only.

**Cloudflare Pages for the new sites** (not GH Pages): per-project custom domains, branch
preview deploys, and it collapses the double-cache problem. Leave berkeleybuild.com on GH
Pages until the new sites are proven.

**Per-repo git identity** set at clone time for every new site repo, so authorship is
consistent from commit #1 rather than retrofitted.

---

## 6. Open decisions (John)

1. **Which domains are already owned?** Only `berkeleybuild.com` is externally visible.
2. **`BerkeleyFuture` vs `BerkeleyInfrastructure`** for the political brand.
   "Infrastructure" reads more neutral and inherits the 2017 task-force lineage in
   `docs/berkeley2050/founding/` — an asset. "Future" reads as advocacy, which may be the
   intent for ballot work.
3. **Dormant sites: revive, freeze, or take down?** Tier A is cheap to update; Tier B needs
   a Ruby toolchain; `Berkeley2050Tech` is publicly broken and should be fixed or removed.
4. **Commit-authorship posture** — leave history as-is (recommended: it is honest and the
   rewrite cost is high), or rewrite. John's call.
5. **`feller-campaign` ownership** before it is ever published.

---

## 7. Content triage — what's actually worth keeping

Added 2026-08-25 after reading the content of all 21 dormant sites (rendered pages +
source markdown via `gh api`).

### 7.1 LIVE DEPENDENCY — do not take down

**`johngage/berkeley2050`** is linked from the *current* production site.
`docs/berkeley2050/index.html` contains, under "Online editions still live":

> "The Vision 2050 report as a Jupyter Book (source) — the task-force materials,
> chapter by chapter, still serving"

pointing at `https://johngage.github.io/berkeley2050/`. Disabling that Pages site breaks
berkeleybuild.com. It also means `johngage.github.io` currently sits in the outbound link
path of the production site.

All other outbound links on that page were checked and are healthy (the 403 from Ballotpedia
and 429s from dailycal.org are bot-blocks, not dead links).

### 7.2 High value — migrate to the new orgs

| Repo | What it is | Goes to |
|---|---|---|
| **`berkeley2050`** | Full annotated edition of the Vision 2050 report: cover, forward, acknowledgements, task-force members, exec summary, Sections 1–7 each in **"Original \| Enhanced"** pairs, Appendices A & B, "Five Big Ideas", Adeline Plan TOC | `BerkeleyFuture` / `BerkeleyInfrastructure` |
| **`berkeley2050` → `10bigideas/bigfive.md`** | **Adeline Corridor Plan** affordable-housing targets — 1,450 projected units, 725 (50%) affordable target over 20 years | Relevant to **housing** work, not just infrastructure |
| **`dailycal`** | Data-journalism proposal for the Daily Cal: "Berkeley is the center of data science innovation", BART data sources, BART customer-satisfaction survey notebook, desk/beat organization by institution | `BerkeleyOpenData` (methodology/teaching) |
| **`voteA`** | Electoral-journalism guide: Media, Stories, Reporters, Resources, Interview templates | `BerkeleyFuture` — directly reusable for ballot-measure work |
| **`KiberaProjects`** | Kibera Town Centre: physical site, Nairobi county, KTC facilities, plus `HNP_Kenya_Board_Report_Nov2019_FINAL.md` | Kibera/water org |
| **`h1`** | Distributed wastewater treatment survey: manufacturers & patents, RedHorse Wetlands-in-a-Box, testing, nutrient-mass measurement, design + data science for WW engineering | Water org |
| **`TILBlog`** | Active TIL notebook with topical dirs: `Build_Berkeley`, `block-by-block`, `AI-Engineering`, `California-Africa`, `Schools`, `economy`, `science-technology`. Has CI. | Split: `Build_Berkeley` + `block-by-block` → Berkeley orgs |

Sample of the real content quality (`content/sec1/sec1plus.md`):

> "Vision 2050 is a citizen-led planning effort, convened by Mayor Jesse Arreguin, to develop
> a Berkeley vision to guide physical infrastructure planning for energy, water, housing,
> food, transportation, communications…"

### 7.3 Historical — preserve, don't develop

`water` (Water, Power, Network — Jupyter Book), `WaterPowerData` (Pelican site, KTC water
flow analysis, "ten numbers that matter" dashboard doc), `XIO-OperationalDataKTC` (real-time
KTC pump/treatment telemetry, 2016–2018), `KiberaTownCentre`, `DataScienceInstitute`
(Fernando Pérez on geophysics as Jupyter's predecessor — PRIVATE repo, PUBLIC site),
`tlpf` (Tegla Loroupe Peace Foundation, full Hugo site).

### 7.4 Retire

- `JB1`, `oct1`, `class_one`, `johngage.github.io_old` — Jupyter-Book/Jekyll template
  scaffolding and imports. `JB1` and `oct1` are literally template demos ("Page 2", "Test").
- `johngage` — 5-file personal page, blue background, gold nav buttons.
- `waterdatascience` — superseded by `water` / `WaterPowerData`.
- `CourseChat/WaterNet` — serves an **empty page**.
- **`Berkeley2050Tech` — publicly BROKEN** (146 bytes of raw `---` front matter) *and*
  linked from the production berkeley2050 page. Fix or delink; do not leave as-is.

### 7.5 Two flags

1. **Stale figures contradicting production.** `blockxblock.github.io/berkeley-housing-map`
   publicly serves *"84 Projects · 5,283 Housing Units · 2020-2025"*. This is a superseded
   count sitting under the **same org** as berkeleybuild.com. Two org-branded sites
   publishing different housing numbers is a credibility problem — the neutral-data brand
   depends on not doing this. Refresh from v2/v4 or take it down.

2. **Privacy, not anonymity.** `three-sisters-stories` publishes three children's first
   names and ages on a public, name-linked URL. Independent of the branding question —
   worth a decision on its own.

### 7.6 CourseChat (org-owned, still live)

`CivEng112` (Dave Rauchwerk's LLL classes — schedule, labs, readings, notebooks),
`InfrastructureChat` (Summer 2023, "Five Test Projects", video sessions),
`openprojects` (Quartz site: Agroforestry, AI & National Security, Block-By-Block
Infrastructure Modeling, Digital Twin Earth, Distributed Fiber Optic Sensing),
`BerkeleyELP2024` (Beahrs Environmental Leaders Program, water-properties notebooks).

`openprojects` contains the **Block-By-Block Infrastructure Modeling** thread — the
conceptual ancestor of `blockXblock`. Worth linking from the new sites as lineage.

**Reminder:** this org leaks `john.gage@gmail.com` as its public email (§4).
