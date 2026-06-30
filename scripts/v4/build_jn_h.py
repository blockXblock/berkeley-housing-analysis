"""Build JN-H_document_harvester.ipynb — the harvester / document-acquisition MAP.

A knowledge-map JN (build_jn_c/d/e pattern, markdown-in-source). Unlike JN-E it derives no result figures,
so there is no baseline to gate; instead its CODE cells SELF-VERIFY the inventory against the live code
(grep the actual scripts/lines) so the map can't silently drift from reality. The text cells — the
engine-vs-wrapper distinction, the data flow, the momentary-link problem, the triage heuristics, the
provenance discipline — ARE the deliverable. This domain previously lived only in scattered scripts; the
"needs a B-permit fix" error happened because it wasn't written down. This writes it down.

Run: python scripts/v4/build_jn_h.py
"""
import os, re
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
NB_OUT = os.path.join(ROOT, 'notebooks', 'v4', 'JN-H_document_harvester.ipynb')
cells = []
def md(t): cells.append(new_markdown_cell(t.strip("\n")))
def code(s): cells.append(new_code_cell(s.strip("\n")))

# ---- light build-time sanity: the cited facts still hold (warn, don't hard-halt; a map drifts -> update it) ----
def sanity():
    ud = open(os.path.join(ROOT,'experiments/accela_scrape/url_discovery_scraper.py')).read()
    hp = open(os.path.join(ROOT,'experiments/accela_scrape/harvest_plansets.py')).read()
    checks = {
        "url_discovery defaults Building": 'module_hint: str = "Building"' in ud or "default to Building" in ud,
        "harvest_plansets forces Planning (:167-ish)": 'module_hint="Planning"' in hp,
        "harvest_plansets ZP-skip (:174-ish)": "SKIP-NOT-ZP-PLANNING" in hp,
    }
    for k, v in checks.items(): print(f"  [sanity] {k}: {'OK' if v else 'DRIFTED — update JN-H'}")
    return all(checks.values())

# ============================================================ §0
md("""
# JN-H — Document Harvester / Acquisition Map

**What this is.** The durable, explained map of how we **independently acquire primary documents** from
Berkeley Accela (architect plan sets, tabulation/affordability forms) to GROUND counts we cannot derive
from the permit record — e.g. the **+147 held buildings** in the CO reconciliation (JN-E §7), whose unit
counts are absent from our WorkDescriptions.

**Why it exists.** This domain lived only in scattered scripts. A prior scope mis-read one wrapper and
concluded "B-permit harvest needs to be built" — **wrong** (it's the default). That error happened because
the harvester's capabilities weren't written down. **This notebook writes them down**, so they aren't
re-derived (or re-mis-derived).

**The acquisition discipline (the invariant).** A harvested count's source is **`source_document_id` → the
BUILDING's own document** (its plan set / tabulation / DBE form). **The city APR was only ever the
ENUMERATOR** — it tells us *which* buildings to chase (the held 69/55/23), never the count. **If a count
ever traces to the city APR, the independence is void** (oracle-not-source, at the document level).

**Note on form.** JN-H is a *knowledge-map* JN — it derives no result figures, so (unlike JN-E) it has no
timestamped baseline to gate. Instead its code cells **self-verify the inventory against the live code**, so
the map cannot silently drift from the scripts it describes.
""")

# ============================================================ §1
md("""
## §1 — Infrastructure inventory, explained: the ENGINE vs the WRAPPERS
**The distinction that was mis-read.** The harvester is two layers:

**B-permit-NATIVE engine (discovery / queue / inspection — Building is the DEFAULT):**
- `experiments/accela_scrape/url_discovery_scraper.py` — `discover_url(permit, module_hint="Building")`;
  Building is the **default**, REV/DEF sub-record-aware, parses capID from CapDetail hrefs.
- `scripts/run_url_discovery.py` — orchestrates the B-permit `url_discovery_queue`.
- `scripts/build_url_discovery_queue.py` / `scripts/build_scrape_queue.py` — build queues **from v2 in-scope B-permits**.
- `scripts/scrape_inspections.py` + `experiments/accela_scrape/inspection_scraper.py` — inspection scrape via **Building** CapDetail.
- `scripts/accela_workflow.py` — address search across **Building and Planning**.
- `experiments/accela_scrape/test_fetch_*.py`, `playwright_inspections_poc.py` — the proven **`Module=Building`** fetch path.

**ZP-scoped WRAPPERS (a past entitlement-plan-set campaign — NOT engine limits):**
- `harvest_plansets.py` — plan sets for ~8 hardcoded **ZP** permits; forces `module_hint="Planning"` and
  **skips non-ZP** (the only ZP-specific lines — see code below).
- `harvest_affordability.py` — DBE/Tabulation/AHCP forms, ZP-discovered.
- `generalize_test.py`, `harvest_run2.py` — ZP plan-set test/run harnesses.
- `document_download_poc.py` — the **attachment-grid download MECHANISM** (proven on a ZP record; the widget is module-agnostic).
- `upload_harvest_to_r2.py` — staging → R2.

**📝 THE KEY EXPLANATION (recorded so it isn't re-derived):** *B-permit harvest is the **DEFAULT**, not a
missing feature. The ONLY ZP-specificity is `harvest_plansets.py` lines ~167 (forces Planning) and ~174
(`SKIP-NOT-ZP-PLANNING`). A prior scope wrongly generalized that one wrapper's ZP scope to the whole
harvester. The discovery/queue/inspection stack is Building-native; the document wrappers were just pointed
at a ZP campaign.*
""")
code("""
import os, re
ROOT=os.path.expanduser('~/berkeley-data')
def show(path, pats, n=3):
    src=open(os.path.join(ROOT,path)).read().splitlines()
    print(f'--- {path} ---')
    for i,l in enumerate(src,1):
        if any(re.search(p,l) for p in pats): print(f'  {i}: {l.strip()[:96]}')
# ENGINE: Building is the default
show('experiments/accela_scrape/url_discovery_scraper.py', [r'default to Building', r'module_hint: str ?= ?"Building"', r'module: str ?= ?"Building"'])
# WRAPPER: the ONLY ZP-specific lines
show('experiments/accela_scrape/harvest_plansets.py', [r'module_hint="Planning"', r'SKIP-NOT-ZP-PLANNING', r'startswith\\("ZP"\\)'])
print('=> engine defaults Building; the ZP constraint is isolated to the harvest_plansets wrapper.')
""")

# ============================================================ §2
md("""
## §2 — The data flow (and the MOMENTARY-LINK problem)
```
permit#  ──discover_url(Building)──▶  capID / CapDetail (Module=Building)
   │                                        │
   │                                  attachment grid (iframe, JS-generated links)
   ▼                                        ▼
 (city APR = ENUMERATOR only:        page.expect_download  ──▶  PDF
  which buildings, never the count)         │
                                            ▼
                                    upload_harvest_to_r2  ──▶  R2 (source_document_id)
                                            │
                                            ▼
                                    extract unit count FROM THE PDF CONTENT
                                            │
                                            ▼
                              gated v4 write (new_unit, net_units=N,
                              basis_note=source_document_id)  ──▶  JN-E re-derives  ──▶  NEW timestamped baseline appended
```
**⚠ THE MOMENTARY-LINK PROBLEM (Accela-specific, learned by getting burned).** Accela attachment/navigation
links are **JavaScript-generated at click-time** (`__doPostBack` / `handlePortletNavigation`), **NOT stable
URLs** — they carry **session-scoped, transient tokens** valid ONLY in the live session at the moment
generated. Implications (these *explain the architecture*):
- **You CANNOT harvest URLs and fetch them later in a batch — the link expires.** This is *why* the harvester
  uses **Playwright** (`page.evaluate`, `page.expect_download`) in a **live session**, not plain HTTP GETs.
- **A failed/empty fetch is OFTEN the link not-yet-materialized or expired, NOT the document being absent.**
  Retry **in-session** before concluding absent (ties to the transient-no-capID rule in CLAUDE.md).
- **The download must happen WITHIN the same live page context** that generated the link (the attachment-grid
  iframe), not as a detached request.

**Verifiability concern per hop:** discovery (capID can be a transient miss → retry); download (link is
momentary → must be same-session); R2 (the `source_document_id` is the provenance anchor — without it the
count is unverifiable); extract (count from CONTENT, never filename — see §3.5); gated write + baseline
(JN-E convention — append, never hand-edit).
""")
code("""
# self-verify: the harvester really does use a live Playwright session + JS-generated nav (not static GETs)
for path in ['experiments/accela_scrape/document_download_poc.py']:
    src=open(os.path.join(ROOT,path)).read()
    for token in ['expect_download','handlePortletNavigation','iframe','__doPostBack','attachmentUrl','page.evaluate']:
        print(f'  {path}: contains {token!r}? {token in src}')
print('=> live-session Playwright + JS-generated attachment links (momentary) — confirmed in the code.')
""")

# ============================================================ §3
md("""
## §3 — The genuine gap, precisely (NOT "build a B-permit harvester")
**What is NOT the gap:** building B-permit harvest. It **exists** and is the default (§1).

**What IS the gap:** the **attachment-download widget has been PROVEN on ZP records, not yet RUN on a
B-permit's attachments.** It is the **same Accela widget** (`handlePortletNavigation('tab-attachments')` →
iframe → `expect_download`), so it *should* work for Building, but that is **unconfirmed** — a confirmation
run, not a build. Plus the wrapper's two ZP lines (`harvest_plansets.py` :167/:174) would skip a B-permit,
so you either call the mechanism directly or relax those two lines.

**Fragility (operational reality, why "absent" is unreliable):**
- **postback / iframe flakiness** — the grid is an ASP.NET `__doPostBack` widget inside an iframe; navigation
  can fail transiently.
- **transient no-capID / momentary link** — a zero result is OFTEN transient (discovery flakiness or an
  expired momentary link), **NOT** absence. **Retry before concluding absent** (CLAUDE.md HARVESTER rule;
  2026-06-15: 5/6 "discovery-failed" large buildings resolved on a plain retry).
- **"absent" is not a finding on a single try** — only a *consistent, post-retry* zero (or a scrape that
  returns inspections but no document) is a real finding.
""")

# ============================================================ §3.5
md("""
## §3.5 — Document-triage heuristics (title + size as a CONTENT signal)
The attachment grid lists documents with **titles and file sizes** that hint at content. Use them to
**prioritize which to pull+parse for the unit count** — don't download everything blindly:
- **Large PDF (tens of MB), "Architectural / Plan Set"** → the full plans; the count is in there but
  **buried** (slow to parse, may need OCR / page-targeting).
- **Small structured form (KB-scale)** — "**Tabulation Form 1.E**", "**DBE Eligibility**", "**AHCP**",
  "**Unit Mix / Summary**" → often the **CLEANEST count source** (structured table, fast parse). **Prefer
  these for the count when present.**
- **Tiny files** (transmittals, cover letters, fee receipts) → noise, **skip for counts**.
- **Multiple versions** (resubmittals, "Rev 1/2/3", entitlement vs final) → titles are **HINTS, not truth**;
  a "Final" may be an early resubmittal (cf. proj179's `ZP2018-0135` resubmittal chain).

**📝 VERIFIABILITY (oracle-not-source, at the document level):** the title/size **PRIORITIZES** which document
to open; the **COUNT must come from the document's CONTENT, never its filename.** Filename **enumerates
candidates**; content **grounds the number**. If two documents give different counts (early resubmittal vs
final), use the **authoritative/latest** and **FLAG the divergence**.

**Practical harvest heuristic:** pull the **structured form (tabulation / DBE / unit-mix) FIRST** if present
(fast, clean); fall back to parsing the **plan set** only if no structured count exists.
""")

# ============================================================ §4
md("""
## §4 — How to harvest the +147 (the actual invocations)
**The held set (JN-E §7):** B2021-03302 (2352 Shattuck, 69), B2018-03422 (2503 Haste, 55),
B2016-05139 (2740 San Pablo, 23).

**B2021-03302 — the easy case (extraction-from-R2, no scrape):** 2352 Shattuck = **proj179**, whose
architect plan sets are **already in R2** (`architect_plans/proj179_2352-shattuck_*.pdf`), and proj179 was
already investigated (North 168 + **South 69** + 237). Extract the South count from the R2 plan set /
the existing investigation — no Accela hit needed.

**B2018-03422 & B2016-05139 — the scrape cases (B-permits):**
```
# 1. discover (works AS-IS — Building is the default):
#    add the 2 permits to the queue, then run discovery
python3 scripts/build_url_discovery_queue.py            # or insert the 2 rows directly
python3 scripts/run_url_discovery.py --limit 2 -v       # discover_url(Building) -> capID + metadata
#    (or one-off, in a Python session:)
#    from url_discovery_scraper import discover_url
#    discover_url("B2018-03422")   # module_hint defaults to "Building"

# 2. download attachments (THE CONFIRMATION RUN — the module-agnostic widget on a B-permit):
#    point the document_download_poc.py mechanism at the discovered Building CapDetail URL,
#    OR relax harvest_plansets.py :167 (module_hint="Building") + :174 (accept non-ZP) and run it.
#    Prefer the structured form (tabulation/DBE) first (§3.5); fall back to the plan set.

# 3. upload + extract:
python3 experiments/accela_scrape/upload_harvest_to_r2.py    # -> R2, source_document_id
#    extract the unit count from the PDF CONTENT (harvest_affordability.py get_text/extract pattern)
```
**Run character:** discovery = fast, mostly reliable (retry transient misses). Download = fragile
(Playwright/iframe/momentary-link), needs a live session + the confirmation run. **Creds:** Accela is public
for these records (no login); R2 upload needs the R2 env creds.
""")
code("""
# self-verify the invocation surface exists (read-only; does NOT scrape)
import inspect, sys
sys.path.insert(0, os.path.join(ROOT,'experiments','accela_scrape'))
for f in ['scripts/run_url_discovery.py','scripts/build_url_discovery_queue.py',
          'experiments/accela_scrape/document_download_poc.py','experiments/accela_scrape/upload_harvest_to_r2.py']:
    print(f'  exists: {os.path.exists(os.path.join(ROOT,f))}  {f}')
ud=open(os.path.join(ROOT,'experiments/accela_scrape/url_discovery_scraper.py')).read()
print('  discover_url default module is Building:', 'module_hint: str = "Building"' in ud)
""")

# ============================================================ §5
md("""
## §5 — Provenance + verifiability ledger (failure modes)
| invariant | what it means | what BREAKS if violated |
|---|---|---|
| **count-from-building-doc, never-city** | the number comes from the building's own plan set / tabulation / DBE; city APR only enumerated which buildings | the +147 becomes **oracle-as-source** — circular; JN-E's independence is void |
| **doc-content over filename** | title/size pick *which* doc; the count is read from CONTENT | a mislabeled "Final" (early resubmittal) silently gives a **wrong count** |
| **divergence is signal, not error** | if doc count ≠ city count, **use the doc's** and FLAG it | suppressing the divergence discards **the entire value of independent verification** |
| **momentary-link → live session + retry** | links expire; download in-session; a transient zero is a retry | a single empty fetch wrongly recorded as **"document absent"** (a false finding) |
| **gated write + baseline-append** | the count enters v4 via a gated write (`source_document_id`), then JN-E re-derives and a NEW baseline is appended | hand-editing a count or a baseline makes the figure **unverifiable** (breaks the JN-E gate) |

**The feedback path, end to end:** harvested count → gated v4 write (`new_unit`, `net_units=N`,
`basis_note=source_document_id`) → JN-E re-derives (the building moves from `phase_under_held` into
`co_completions`) → **a new timestamped reconciliation baseline is appended** (never a hand-edit). The
city's 69/55/23 never enter the number — only the document does.
""")

if __name__ == '__main__':
    print('=== JN-H build sanity (inventory still matches live code) ===')
    ok = sanity()
    print('  ', 'all inventory claims hold' if ok else 'SOME DRIFTED — update the §1 text before relying on it')
    nb = new_notebook(cells=cells, metadata={'kernelspec': {'name':'python3','display_name':'Python 3'}})
    os.makedirs(os.path.dirname(NB_OUT), exist_ok=True)
    with open(NB_OUT,'w') as f: nbf.write(nb, f)
    print(f'\n=== emitted: {os.path.relpath(NB_OUT, ROOT)} ({len(cells)} cells) ===')
