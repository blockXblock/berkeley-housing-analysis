---
title: kiberawater.com — Wix → Cloudflare Pages migration plan
date: 2026-09-11
type: report
status: open
area: notes
---

# kiberawater.com — Wix → Cloudflare Pages migration plan

*Drafted 2026-09-11. Facts in §0 were checked live (dig / whois / site fetch) on the draft date.*

**STATUS 2026-09-11 (evening): Phase A CAPTURE = DONE.** Both Wix sites captured byte-complete to
`scratch/2026-09-11/kiberawater_wix_capture/` (+ `kiberatowncentre_wix_capture/`), mirrored to
`/Volumes/T7-2025/Berkeley-Research/kiberawater_wix_capture_2026-09-11/`. Read
`kiberawater_wix_capture/README_CAPTURE.md` for the inventory + verification. Nothing at Wix was changed.
**Scope addition (John, 2026-09-11):** the rebuild adds NEW material using **XIO real-time data** (KTC
telemetry) — the Datasette-Lite data pages in Phase B step 5 are the home for it. Next = Phase B.

**STATUS 2026-09-11 (late evening): Phase B BUILT LOCALLY.** New repo `~/kiberawater-site` (Quartz **v5.0.0**,
not v4 — YAML config, `npx quartz plugin install`; branch `v5`), commits `beddb44`→`4f292a7`, **NOT pushed, no GitHub
repo/org created** (governance = John's call; `upstream` remote = jackyzha0/quartz). `content/` = the Obsidian
vault; every Wix page recreated verbatim + `_redirects` + photo gallery (79 + 32 library, web-sized, MANIFEST.csv
back to Wix ids) + a NEW `data/` section (ten-numbers framing, Datasette-Lite slot awaiting a real WEDC/XIO
pull). Builds clean (`npx quartz build --serve` → localhost:8080), rendered and checked. `MIGRATION.md` in the
repo has the page-by-page mapping + the to-do. **2026-09-14: org = WaterForAll. Pushed to https://github.com/WaterForAll/kiberawater (PRIVATE, branch `v5`, HEAD `0f7112b`).** John added an Obsidian Bases **`Migration tracker.base`** (repo root = vault root; per-page `verified`/`wix_deleted` frontmatter) — the verification checklist for Phase C. `DEPLOY.md` in the repo = the exact Pages settings. **2026-09-14 evening: DEPLOYED.** Cloudflare **Workers (static assets, Git-connected)** — NOT legacy Pages; `wrangler.jsonc` in repo; build `npx quartz plugin install && npx quartz build`, deploy `npx wrangler deploy`; auto-rebuilds on push to `v5`. Live preview: **https://kiberawater.roam-graph.workers.dev** — every page 200, all old Wix URLs redirect, PDFs fixed (`ae40c87`, byte-exact). Zone `kiberawater.com` exists (Pending; Google MX to be deleted by John; TXT kept). **Next = Phase C** (John's Obsidian tracker → `verified: true` per page) → add custom domains on the Worker (Settings → Domains & Routes) → **Phase E** nameservers at Wix. (Superseded:) **Next = John in the Cloudflare dashboard:** (1) add zone `kiberawater.com`, (2) Workers & Pages → Create → Pages → Connect to Git → WaterForAll/kiberawater (DEPLOY.md settings) → `kiberawater.pages.dev`. Then C on the preview, then E cutover. wrangler login still expired (CLI only).

**Dashboard facts (logged in 2026-09-11) that refine §0:**
- Plan = Premium **Core**, yearly, last paid 2026-08-18, next **2027-08-17** (not ~2027-07).
- Domain **confirmed Wix-registered**; 3-year cycle, **renews 2027-09-05**; the transfer-lock/auth-code
  live in Wix → Domains (as assumed). Second site in the account: `johngage2.wixsite.com/kiberatowncentre`
  (free, 2 pages, one unique 2016 ICT4D-visit text block — captured).
- Contacts = 5 (1 real: Juliet Mmbone 2015; 1 spam; John ×3). Inbox = 4 threads (captured). Blog = 4
  posts, 0 drafts. Media Manager = 117 files / 264 MB — 34 never used on the site (IMG_95xx series,
  "Drone Flight Plan", a 5th PDF `Debates_withappendix_16Feb2016.pdf`); all captured.
- The drone video is a third-party YouTube embed (`Lr249hiO2gM`) — not Wix Video; re-embed by ID.
- The Timeline page is a **Lumifish Timeline** app (iframe) — 7 dated entries 2010-02-03 → 2015-06-01,
  text captured in `rendered/timeline.txt`; must be rebuilt as a plain Markdown timeline.

## 0. What exists today (verified)

| Thing | State | Implication |
|---|---|---|
| Site host | Wix (`185.230.63.x`, `x-wix-*` headers) | No export tool exists — content is re-created, not exported |
| Site size | ~10 pages: Home, News, About Us (3 sub-pages), Our Vision, Timeline, Coalition, Sign Up, Blog; **4 blog posts, all Sept 2015**; one embedded drone video; photo carousel; partner-link list; several contact addresses | Small. A hand migration is a day, not a project |
| Blog URLs | Wix pattern `/single-post/2015/09/07/<slug>` | Need `_redirects` if inbound links matter |
| Domain registrar | WHOIS: **Network Solutions**, created 2015-09-06, **expires 2027-09-06**, `clientTransferProhibited`. BUT Wix sends the annual ICANN "Review Your Domain's Contact Information" notices (Dec 2024, Dec 2025) — that is a registrar-of-record duty, so the domain is almost certainly **registered THROUGH Wix**, with NetSol as Wix's backend registrar | Verify in Wix dashboard → Domains. If Wix-held: the domain is a separate Wix product from the Premium plan (cancelling the plan does not drop it), but it keeps billing via Wix until transferred out. Transfer to Cloudflare Registrar = unlock + auth code from the Wix dashboard (Wix requires the domain be >60 days old and not recently transferred — fine) |
| Nameservers | `ns6/ns7.wixdns.net`; `www` → `cdn3.wixdns.net` | The cutover IS the nameserver change at NetSol |
| **Email** | MX → Google Workspace (`aspmx.l.google.com` …) — **but the Workspace is DEAD.** Gmail history: G Suite Basic for kiberawater.com (org "Human Needs Project") was reseller-provided via Wix; Google asked for direct billing 2021-10-03, suspended it 2021-10-05, cancelled 2021-12-05, and **deleted the account 2022-03-22**. Zero threads to/from any `@kiberawater.com` address exist in john.gage@gmail.com | **No email to protect.** Mail to `info@kiberawater.com` (still printed on the site) has bounced since 2022. The MX records are orphans — do NOT re-create them at cutover; either drop them or point the domain at Cloudflare Email Routing (free) to forward `info@` to a real mailbox. Remove/replace the dead addresses on the site |
| Sign-up form | Wix form → Wix Contacts | Export contacts BEFORE cancelling; replace with a static-compatible form |
| Related repos (johngage) | `KiberaProjects`, `kibera-water-standards`, `kibera-town-centre`, `KiberaTownCentre`, `water`, `WaterPowerData`, `XIO-OperationalDataKTC`, `waterdatascience`, `TILBlog`; org `CourseChat/openprojects` is a **Quartz** site already | Prior art for both the Obsidian/Quartz route and the Willison/TIL route exists in John's own repos |
| Cloudflare CLI | wrangler token expired 2026-08-12 (per inventory note) | Re-auth before any Pages work |

## 1. Decision: which model?

Two candidate models, and they are not the same thing:

- **Simon Willison's sites.** simonwillison.net is a *Django + Postgres* app (dynamic, hosted on a server) — not a fit for "static on Cloudflare". What IS portable from Simon's practice: everything in a git repo; dated permalinks; a TIL stream built by GitHub Actions (John already cloned this: `TILBlog`); **Datasette** for structured data. Datasette itself can't run on Cloudflare Pages, but **Datasette-Lite** (Datasette in the browser via Pyodide) is a static page and CAN — a natural home for the KTC water-flow telemetry (`XIO-OperationalDataKTC`, `WaterPowerData`).
- **Obsidian-friendly publishing.** Write in an Obsidian vault; publish the vault (or a `publish/` subset). Options: **Quartz v4** (open source, static, Obsidian-native wikilinks/backlinks/graph, builds on Cloudflare Pages from GitHub — John already runs one), **Obsidian Publish** ($8/mo, Obsidian-hosted, custom domain OK — but it is NOT Cloudflare and swaps one subscription for another), or a generic SSG (Eleventy/Hugo/Astro) with an Obsidian-export plugin (more plumbing, more control).

**Recommendation: Quartz v4 on Cloudflare Pages, with Datasette-Lite pages for data.** It satisfies "Obsidian-friendly" directly, costs $0/mo beyond the domain, reuses a pattern John has already run, and the Willison-style pieces (TILs, dated posts, data pages) layer on top as ordinary notes + one static Datasette-Lite page. Simon's *blog engine* is not worth reproducing for a ~10-page site.

## 2. Workflow

### Phase A — Capture (before touching anything)
1. `wget --mirror --page-requisites --convert-links https://kiberawater.com` into `scratch/` → a byte-level archive of the Wix site as it stands (Wix renders via JS; also save each page as PDF from the browser for a visual reference).
2. Pull original-resolution images: Wix serves `static.wixstatic.com/media/<id>` with transform suffixes; strip the suffix to get the original. Save with provenance (page, caption).
3. Download the drone video source (if it is Wix Video, it must be pulled from the Wix dashboard; if it is YouTube, note the ID). Video does not live in the repo — it goes on a YouTube channel (project media rule), embedded by ID.
4. Export **Wix Contacts** (Sign Up submissions) to CSV. Export the Wix Blog posts (Wix dashboard → Blog → export, or copy by hand — 4 posts).
5. Record the Wix billing state: Premium plan renewal date (a "will renew soon" notice arrived 2026-07-18, as it did 2025-07-23 — so the plan renews ~late July/August annually; the next charge is ~2027-07), and the domain's own renewal line.
6. In the Wix dashboard → Domains: confirm the domain is Wix-registered, note where the transfer-lock toggle and auth-code request live. Do NOT unlock yet.

### Phase B — Build the vault + site (in parallel with Wix still live)
1. New repo (org per inventory note §5 — a Kibera/water org, private membership; per-repo git identity). Structure: `content/` = the Obsidian vault (open it directly in Obsidian), `quartz/` = Quartz v4.
2. Recreate pages as Markdown notes with frontmatter (`title`, `date`, `tags`, `permalink`). Blog posts keep their 2015 dates. Use wikilinks freely; Quartz resolves them.
3. Add a `_redirects` file (Cloudflare Pages honors it): `/single-post/2015/09/07/<slug>` → `/posts/<slug>` etc., and `/blog` → `/posts`.
4. Replace the form: Cloudflare Pages Function + Turnstile writing to a KV/D1 store or emailing via MailChannels — or, cheaper in effort, a Google Form embedded/linked. Decide by how much the sign-up list actually matters (it has been quiet since 2015).
5. Data pages: one Datasette-Lite page loading a `.db`/`.csv` from the repo (KTC telemetry). This is the Willison piece.
6. Deploy to Cloudflare Pages from GitHub; the preview URL is `<project>.pages.dev`. Iterate here until it matches or beats the Wix site.

### Phase C — Editorial pass (the real opportunity)
The site's prose is 2015-present-tense ("we are forming the coalition…"). Migration is the moment to decide: archive as a dated record (add an "as of 2015" banner + a "what happened since" page), or rewrite. Link the lineage: `water` (Jupyter Book), `WaterPowerData` ("ten numbers that matter"), `XIO` telemetry, `KiberaTownCentre`, `h1` wastewater survey. Fix the placeholder social icons (Google+ is dead).

### Phase D — DNS prep (zero-downtime)
1. Add `kiberawater.com` as a zone in Cloudflare (free plan). Cloudflare will scan and import records; keep the `google-site-verification` TXT (Search Console), DELETE the 5 orphaned Google MX records (dead Workspace — see §0), and optionally enable Cloudflare Email Routing for `info@` → a real inbox.
2. Add the custom domain to the Pages project (Cloudflare creates the CNAME/apex records).
3. Lower nothing yet — Cloudflare's zone sits inactive until the nameservers change.

### Phase E — Cutover
1. Change nameservers (in the **Wix** dashboard → Domains, since Wix is registrar-of-record) to the two Cloudflare assigned 2026-09-14: **`karina.ns.cloudflare.com`** and **`alan.ns.cloudflare.com`**. Zone created 2026-09-14, status Pending until then. Propagation: minutes to ~24h. The site flips to Pages; email keeps working because MX was pre-staged.
2. Verify: `dig NS`, `dig MX`, send a test mail to an `@kiberawater.com` address, hit each old Wix URL and confirm the redirect, check Google Search Console (the TXT verification carries over).
3. Leave Wix running (already paid) for 2–4 weeks as a fallback, then **cancel the Wix Premium plan** — but keep the Wix ACCOUNT open until the domain transfer (step 4) completes.
4. Transfer the domain to Cloudflare Registrar: unlock + auth code from the **Wix** dashboard (Domains), not NetSol (Wix is the reseller of record). 5-day EPP transfer, adds a year at cost. Do it BEFORE cancelling the Wix account entirely — once the Wix account is closed, retrieving the auth code means Wix support. Expiry is 2027-09, so there is time, but the sequence matters.

## 3. Special challenges (ranked by bite)

1. ~~Email is the thing that breaks~~ — **RESOLVED 2026-09-11: there is no live email.** The Workspace died in 2022; the MX is an orphan. The residual task is the opposite: stop advertising dead addresses, and decide whether `info@` should exist at all (Cloudflare Email Routing → a real inbox is free and takes 5 minutes).
2. **No Wix export.** Everything is re-typed or scraped. At ~10 pages this is fine; the images and the video are the fiddly part (original files live in the Wix Media Manager — download from the dashboard, not the public site).
3. **Obsidian → public leakage.** A vault mixes private and public notes. Quartz publishes everything in `content/` by default — either keep a dedicated public vault (recommended for a small site) or use `draft: true` / an explicit `publish:` filter and TEST that a private note does not appear on the preview URL before cutover.
4. **Wikilinks vs. portability.** Obsidian's `[[Note]]` links work in Quartz but not in a generic SSG; if the site ever moves again, use Obsidian's "Use Markdown links" setting from day one for anything meant to be durable.
5. **Forms/interactivity.** Static hosting has no server; every "dynamic" Wix feature (form, member area, comments) needs an explicit replacement or a decision to drop it.
6. **Old inbound links.** The 2015 posts may be linked from partner sites (Carolina for Kibera, Human Needs Project). The `_redirects` file covers it; harvest the old URLs from the wget mirror so none are missed.
7. **Cloudflare auth is expired locally** (wrangler). Dashboard work needs none; CLI work needs a re-login first.
8. **Governance.** Which GitHub org owns it, who else can publish, and the org-email leak noted in the inventory (§4) — settle before the first commit, not after.

## 4. Cost after migration
Domain (~$10/yr at Cloudflare Registrar vs. Wix's domain renewal), Cloudflare Pages free, email $0 (Email Routing) or none. Wix Premium → $0.
