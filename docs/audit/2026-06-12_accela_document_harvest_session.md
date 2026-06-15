# Session resume — Accela plan-set harvest → R2 → v2 → Explorer (2026-06-12)

**For the next Claude.** This session built and proved an Accela document byte-fetch
engine, harvested 20 architect plan sets, uploaded them to R2 (John did the upload),
enriched v2.documents with the R2 links, and regenerated the Explorer data. Read this
before touching anything; verify specifics against the DB/files (this doc is a map).

Two-agent discipline still applies: **I (Claude) do filesystem + DB work; John owns all
pushes/deploys/uploads/Cloudflare purges; chat-Claude plans.** Snapshot → preview → STOP →
fingerprint on any canonical write. Never commit/push/upload without John's explicit word.
**Verify before characterizing** — this session caught 3 false-positive heuristics and 1
wrong-record bug by quoting artifacts instead of trusting summaries.

---

## CURRENT STATE (verified at session end)

- **Branch:** `dev`, **0 ahead of origin/dev** (in sync — last pushed commit was `1bcddba`
  "proj15 corrections + documents provenance", pushed earlier; `main` was merged + pushed
  to `d0672e6` earlier too).
- **Uncommitted tracked changes (NOT committed, John's call):** `docs/explorer_data.js`
  + `docs/explorer_data_v2_working.js` (the freshly regenerated Explorer data — STAGED FOR
  JOHN'S PUBLISH), `.gitignore`, plus pre-existing unrelated dirty files (D6/D7 notebooks,
  `data/apr/2024/*` csvs, a tour KML, deleted flyover backup). The unrelated ones are
  separate threads — do not sweep them into any commit.
- **Untracked (NOT committed):** `experiments/accela_scrape/{document_download_poc.py,
  generalize_test.py,harvest_plansets.py}` (the proven engine — preserve these), `.venv/`,
  `corrections/`, and assorted notes.
- **v2 canonical DB:** `databases/berkeley_housing_v2.db` — **1986 documents, 22 with
  r2_url** (integrity ok). 8 projects now have plan-set R2 links: 9/10/11/15/17/26/36/41.
- **Snapshots (rollback points):** `databases/keep_snapshot_2026-06-11_pre-v2-corrections.db`
  and `databases/keep_snapshot_2026-06-12_pre-r2-plansets.db`.

---

## WHAT WAS DONE THIS SESSION (the arc)

1. **proj15 (2109 Virginia) corrections** — earlier in session: verified 2 architect-plan
   PDFs (sha256), corrected v2 (`height_stories 2→8, height_feet 131→89.33, total_units
   131→110`), enriched documents 617/615 with R2 links, committed the provenance CSVs
   (`corrections/v2_corrections_seed.csv` + `proj15_documents_manifest.csv` → commit
   `1bcddba`), pushed dev, merged dev→main (`d0672e6`), pushed main.
   - **NOTE:** plan-set cover says **89'-4"** (not 88'-4" as the Accela prose did). The
     seed CSV flags proj11's height as VERIFY-before-write — still pending.
2. **Built the Accela document byte-fetch engine** (did not exist before — only an
   inspection-pagination POC did). Proved it single-record on proj15 with a **sha256
   ground-truth match**, then proved it generalizes 4/4 on varied records, then harvested.
3. **Harvested 20 plan sets** from 8 doc-linked projects → `/tmp/harvest_stage/` + manifest.
4. **John uploaded the 20 to R2**; I enriched v2 (13 enrich-in-place + 7 net-new insert,
   ids 2118–2124) in one guarded transaction. documents 1979→1986.
5. **Regenerated Explorer data** (`export_explorer_data_v2.py` → `explorer_data_v2_working.js`
   → copied to `explorer_data.js`). Staged for John's publish. NOT committed/deployed.

---

## THE PROVEN ACCELA ENGINE (don't re-derive — this was hard-won)

Reusable scripts in `experiments/accela_scrape/` (run with **`.venv/bin/python`** — the
project `.venv` has playwright 1.60 + chromium; do NOT use conda/jupyter_env):
- `document_download_poc.py` — single-record download + sha256.
- `generalize_test.py` — multi-record generalization harness.
- `harvest_plansets.py` — the full harvester (resumable via `/tmp/harvest_stage/state.json`).
- `url_discovery_scraper.py` (pre-existing) — `discover_url(permit, module_hint="Planning")`
  resolves a permit → capID triplet. **Use this; capIDs are NOT in the repo and must be
  discovered.** (A wrong capID from a loose grep cost time — always assert the permit label.)

**The recipe (works unchanged across all ZP Planning records tested):**
1. `discover_url(permit, module_hint="Planning")` → `master.capdetail_url` (capID1=`*PLN`).
2. `page.goto(url)` anonymously — **no login needed**. ASSERT `#ctl00_PlaceHolderMain_lblPermitNumber`
   == the permit (catches wrong-record).
3. **Activate the lazy attachment grid** (NOT a postback, NOT a collapsible section):
   `page.evaluate("handlePortletNavigation(document.querySelector('a[data-control=\"tab-attachments\"]'))")`.
   The page stashes the iframe's real src in JS var `attachmentUrl` on ready then blanks it;
   this nav restores it. The iframe is `ctl00_PlaceHolderMain_attachmentEdit_iframeAttachmentList`,
   0×0, and loads `../FileUpload/AttachmentsList.aspx?...&module=Planning&...` (capID comes
   from server session, so load CapDetail first — don't hit the iframe URL cold).
4. `page.wait_for_selector('#<iframe>', state="attached")` → `.content_frame()` (it's 0×0 so
   `state="visible"` never fires). Grid rows = `a[href*='lnkFileName']`, ~10/page.
5. **Paginate** inside the frame: find the `Next >` anchor's `__doPostBack` target, fire
   `frame.evaluate("__doPostBack('<target>','')")`, **poll for first-row change** (three-state:
   success / last_page=no-Next / failed=no-change). Cap ~12 pages.
6. **Download:** `with page.expect_download() as dl: frame.evaluate("__doPostBack('attachmentList$gdvAttachmentList$ctlNN$lnkFileName','')")`
   then `dl.value.save_as(...)`. Needs `accept_downloads=True` on the context.

**Gotchas (verified):** PROVEN RULE — `__doPostBack(target,'')` via `page.evaluate()` fires
the postback; `link.click()` does NOT. Login/block detection must use **visible text + URL
+ password-field**, never raw HTML (scripts contain `login.aspx`, `storage access denied`).
Grid "MB" is actually **MiB** (bytes/1048576 == displayed). Timing: ~25–35 s/record incl
discovery + a ~40 MB download.

---

## KEY ARTIFACTS / LOCATIONS

- `/tmp/harvest_stage/` — **EPHEMERAL** (could be wiped on reboot). Holds: 20 staged PDFs
  (`<proj>/<filename>`), `manifest.csv` (review surface), `r2_uploaded_urls.csv`
  (key→public_url), `state.json` (resume). The PDFs are already in R2 + v2, so these are
  now backups, but the two CSVs are the provenance join source if anything needs re-running.
- R2 public base: `https://pub-2cee87f70da64080ab70ee0a34b55099.r2.dev/`. Harvest keys:
  `architect_plans/proj<ID>_<slug>_<YYYY-MM-DD>.pdf`. (proj15's original 617/615 use the
  older `architect_plans:proj15_...` colon keys — both live in R2.)
- Explorer: `docs/explorer.html` loads `docs/explorer_data.js` (a `cp` of `_v2_working.js`)
  + `docs/explorer.js`. The Projects-tab expandable row **already renders a "Documents (N)"
  panel** with clickable `d.url` links — surfacing R2 links is pure data pipeline, no UI work.
  Export script: `scripts/export_explorer_data_v2.py` (doc url = COALESCE(drive,source,ia,r2)).

---

## PENDING / NEXT STEPS (nothing started; await John)

1. **John's publish** of the regenerated Explorer data (commit + push `docs/explorer_data.js`
   [+ `_working.js`] on dev, then Cloudflare purge). After that the 22 R2 links go live.
2. **Commit the engine?** `experiments/accela_scrape/*.py` are untracked/proven — John may
   want them committed (and `.venv` gitignored — `.gitignore` is already modified).
3. **Remaining WOULD-HARVEST work (NOT done):** the **17 uncataloged "None" addresses**
   (2700/2420/2920/2276 Shattuck, 2601 San Pablo, 2036 Bancroft, 2441 Le Conte, 1750
   Sacramento BART, 2145 Grant, etc.) — these have raw Accela captures but **no project_id
   linkage**, so they need a project created/linked first, then harvest. Also the **3
   drive-upload plan sets** (proj5 2425 Durant, docs 1407/1408/1409) are type=2 but lack
   sha256/r2 — separate enrichment. And the larger **509 capture-but-not-cataloged**
   attachment backlog if scope expands beyond plan sets.
4. **proj11/22/123 pending corrections** still in `corrections/v2_corrections_seed.csv`
   (proj22/123 height_stories, proj11 height_feet VERIFY-flagged) — never applied.

---

## DISCIPLINE REMINDERS
- Canonical writes: snapshot → read-only preview → STOP for John → transactional write
  with per-statement rowcount guards + verify-or-rollback → independent fingerprint.
- Be polite to Accela: jittered 5–15 s between records, 0.8–2.5 s between page turns,
  single record for tests, STOP on captcha/auth/redirect.
- `.db` files are NOT git-tracked; provenance lives in `corrections/*.csv` + `docs/audit/`.
- The `/tmp/harvest_stage` CSVs are the only on-disk record of the harvest join — if a
  re-run is ever needed and /tmp was wiped, re-harvest is cheap (engine is proven).
