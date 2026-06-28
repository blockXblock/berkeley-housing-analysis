"""
Document-download byte-fetch POC — single record, ground-truth sha256 check.

Isolates the ONE unproven capability for the 50-PDF harvest:
  anonymous Playwright reach to a Planning ATTACHMENTS grid
  + lnkFileName __doPostBack
  + Playwright download interception (page.expect_download)

Reuses the validated anonymous-Playwright setup from playwright_inspections_poc.py
(browser launch, anonymous context, __doPostBack via page.evaluate()). The NEW part is
the attachment iframe + download handler.

Proven rule (carried over): __doPostBack(target,'') via evaluate() fires the ASP.NET
postback; link.click() does NOT.

Single record. No looping. Polite delay. /tmp only. Nothing uploaded or written to v2/R2.
"""
import hashlib
import re
import sys
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

RECORD = "ZP2024-0066 (2109 Virginia)"
EXPECT_PERMIT = "ZP2024-0066"          # asserted against the page's permit-number label
# capID resolved via url_discovery_scraper.discover_url("ZP2024-0066", module_hint="Planning"):
#   24PLN/00000/00479 (permit_number_displayed == ZP2024-0066). Step 1 asserts it.
RECORD_URL = ("https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx"
              "?Module=Planning&TabName=Planning"
              "&capID1=24PLN&capID2=00000&capID3=00479&agencyCode=BERKELEY")
IFRAME_ID = "ctl00_PlaceHolderMain_attachmentEdit_iframeAttachmentList"
TARGET_SHA256 = "eac26eb618fcde2e2d5e5e50d790baf15e72e90df7bb4da422e9cd37671165e2"
TARGET_MATCH = "2025-07-09"          # plan-set row selector (filename substring)
OUT_PATH = "/tmp/poc_2109_planset.pdf"

LOGIN_MARKERS = ("login.aspx", "sign in", "please login", "signin")
BLOCK_MARKERS = ("captcha", "are you a human", "checking your browser",
                 "access denied", "request blocked")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stop(step, why, extra=""):
    print(f"\n*** STOP at {step}: {why}")
    if extra:
        print(extra)
    print("\nNo workaround attempted (per stop rules). Single-record POC ends here.")
    sys.exit(2)


def run(headless=True):
    print("=" * 68)
    print("DOCUMENT-DOWNLOAD BYTE-FETCH POC")
    print(f"Record : {RECORD}")
    print(f"Target : {TARGET_MATCH} plan set  (expect sha256 {TARGET_SHA256[:16]}...)")
    print("=" * 68)
    report = dict(anon_record=False, anon_grid=False, postback_fired=False,
                  download_caught=False, sha256_match=None, seconds=None)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            accept_downloads=True,          # REQUIRED for download interception
        )
        page = context.new_page()

        # ---- Step 1: anonymous navigation to record detail ----
        cycle_t0 = time.time()   # full record->download cycle clock
        print("\n[1] Navigating anonymously to record detail...")
        try:
            page.goto(RECORD_URL, wait_until="networkidle", timeout=60000)
        except PlaywrightTimeout:
            stop("step 1", "timeout loading record detail page")
        title = page.title()
        url_now = page.url.lower()
        raw_l = page.content().lower()
        vis_l = (page.inner_text("body") or "").lower()   # VISIBLE text only
        print(f"    page title : {title!r}")
        print(f"    final url  : {page.url[:90]}")
        # Login/block detection must use URL, form fields, or VISIBLE text — never raw HTML:
        # anonymous Accela pages carry a "Sign In" nav link and scripts that log strings like
        # "storage access denied", both of which false-positive on raw-HTML substring matches.
        if any(m in url_now for m in ("login.aspx", "signin")):
            stop("step 1", "URL redirected to a login page — anonymous access refused",
                 f"url={page.url}")
        if "type=\"password\"" in raw_l or "type='password'" in raw_l:
            stop("step 1", "page presents a password form — auth wall", "")
        if title.lower() in ("just a moment...", "attention required! | cloudflare") \
                or any(m in vis_l for m in BLOCK_MARKERS):
            stop("step 1", "captcha / anti-bot challenge detected (visible text)",
                 f"title={title!r}")
        # Verify we are on the RIGHT record by reading the permit-number label.
        permit = ""
        el = page.query_selector("#ctl00_PlaceHolderMain_lblPermitNumber") \
            or page.query_selector("span[id*='lblPermitNumber']")
        if el:
            permit = (el.inner_text() or "").strip()
        print(f"    permit no. : {permit!r}  (expect {EXPECT_PERMIT})")
        if permit != EXPECT_PERMIT:
            stop("step 1", f"WRONG RECORD: page shows {permit!r}, expected {EXPECT_PERMIT!r}",
                 "Fix RECORD_URL's capID (discover via Accela search) before re-running.")
        report["anon_record"] = True
        print("    -> correct record loaded WITHOUT login. [OK]")
        time.sleep(3)  # polite + let JS/iframes settle

        # ---- Step 1b: activate the attachment grid ----
        # MECHANISM (reverse-engineered 2026-06-12): the grid is NOT a postback and NOT a
        # collapsible section. On document.ready the page stashes the iframe's server-rendered
        # src into a JS var `attachmentUrl`, then BLANKS the iframe to defer the load. Navigating
        # the "Attachments" portlet (<a data-control="tab-attachments">) runs handlePortletNavigation(),
        # which restores iframe.src = attachmentUrl -> the iframe loads
        #   ../FileUpload/AttachmentsList.aspx?iframeid=...&module=Planning&...&agencyCode=BERKELEY
        # That iframe is its OWN asp.net page; the gdvAttachmentList grid + lnkFileName postbacks
        # live INSIDE it. So fire the JS nav (not a click), then read rows from the frame.
        print("\n[1b] Activating attachments grid (JS portlet nav -> iframe src)...")
        fired = page.evaluate("""() => {
            const a = document.querySelector('a[data-control="tab-attachments"]');
            if (!a) return 'NO_NAV_LINK';
            if (typeof handlePortletNavigation !== 'function') return 'NO_HANDLER';
            handlePortletNavigation(a);
            return 'ok';
        }""")
        if fired != "ok":
            stop("step 1b", f"could not fire attachments portlet nav: {fired}")
        print("    fired handlePortletNavigation(tab-attachments) [OK]")
        time.sleep(3)  # let iframe load AttachmentsList.aspx

        # ---- Step 2: reach the ATTACHMENTS iframe + read the grid ----
        print("\n[2] Reaching attachments grid (iframe)...")
        try:
            # iframe is 0x0 (width=0 height=0) -> never "visible"; wait for DOM-attached only.
            iframe_el = page.wait_for_selector(f"#{IFRAME_ID}", state="attached", timeout=30000)
        except PlaywrightTimeout:
            # is there ANY attachment-ish element? report DOM to characterize the gap
            cand = page.evaluate("""() => Array.from(document.querySelectorAll('iframe'))
                                     .map(f => f.id || f.name || f.src).slice(0,15)""")
            stop("step 2", f"attachment iframe #{IFRAME_ID} not found",
                 f"iframes present on page: {cand}")
        frame = iframe_el.content_frame()
        if frame is None:
            stop("step 2", "iframe element found but content_frame() is None (cross-origin?)")
        try:
            frame.wait_for_load_state("networkidle", timeout=30000)
        except PlaywrightTimeout:
            pass
        time.sleep(2)
        # block/login check on the GRID FRAME — visible text + password field (not raw HTML)
        frame_vis = (frame.inner_text("body") or "").lower()
        if "type=\"password\"" in (frame.content() or "").lower():
            stop("step 2", "attachment grid iframe shows a PASSWORD form — grid is NOT anonymous")
        if any(m in frame_vis for m in BLOCK_MARKERS):
            stop("step 2", "attachment grid iframe shows a captcha/block (visible text)")

        def read_rows():
            return frame.evaluate(r"""() => {
                const out = [];
                document.querySelectorAll("a[href*='lnkFileName']").forEach(a => {
                    const href = a.getAttribute('href') || '';
                    const m = href.match(/__doPostBack\('([^']+)'/);
                    out.push({ target: m ? m[1] : null, text: (a.textContent || '').trim() });
                });
                return out;
            }""")

        def find_next():
            # frame's pager "Next" link with a __doPostBack target (proven pattern)
            return frame.evaluate(r"""() => {
                for (const a of document.querySelectorAll('a')) {
                    const txt=(a.innerText||a.textContent||'').trim();
                    const href=a.getAttribute('href')||'';
                    if (href.includes('__doPostBack') &&
                        (/next/i.test(txt) || txt==='>' || txt==='&gt;' || /next\s*&gt;/i.test(txt))) {
                        const m=href.match(/__doPostBack\('([^']+)'/);
                        if (m) return {target:m[1], text:txt};
                    }
                }
                return null;
            }""")

        def is_target(t):
            t=(t or "").lower()
            return "2025-07-09" in t and ("plan" in t)

        rows = read_rows()
        if not rows:
            stop("step 2", "no lnkFileName rows in the grid under anonymous access",
                 f"grid visible-text length={len(frame_vis)} (empty/auth-gated?)")
        report["anon_grid"] = True

        # ---- Step 2b: paginate the iframe grid to the target (three-state, cap 6) ----
        print("\n[2b] Paginating iframe grid to the 2025-07-09 plan set (cap 6 pages)...")
        MAX_PAGES = 6
        target = None
        for pageno in range(1, MAX_PAGES + 1):
            report["pages_walked"] = pageno
            print(f"    --- grid page {pageno}: {len(rows)} rows ---")
            for r in rows:
                ctl = re.search(r'\$(ctl\d+)\$', r["target"] or "")
                flag = "   <== TARGET" if is_target(r["text"]) else ""
                print(f"      [{ctl.group(1) if ctl else '??'}] {r['text'][:60]}{flag}")
            hits = [r for r in rows if is_target(r["text"]) and r["target"]]
            if len(hits) > 1:
                stop("step 2b", f"{len(hits)} rows match the target on page {pageno} — ambiguous",
                     "; ".join(h["text"] for h in hits))
            if len(hits) == 1:
                target = hits[0]["target"]
                print(f"    -> TARGET resolved on page {pageno}: {hits[0]['text']}")
                break
            first_sig = (rows[0]["target"], rows[0]["text"]) if rows else None
            nxt = find_next()
            if not nxt:                                   # state: last_page
                stop("step 2b", f"no Next link after page {pageno} (last_page) — target absent",
                     "2025-07-09 plan set not found in this record's attachment grid")
            print(f"    next -> {nxt['text']!r}  target=...{nxt['target'][-32:]}")
            frame.evaluate(f"__doPostBack('{nxt['target']}','')")   # proven: evaluate, not click
            changed = False                               # poll for first-row change
            for _ in range(16):
                time.sleep(0.5)
                try:
                    rows = read_rows()
                except Exception:
                    rows = []
                if rows and (rows[0]["target"], rows[0]["text"]) != first_sig:
                    changed = True
                    break
            if not changed:                               # state: failed
                stop("step 2b", f"pagination postback fired but grid did not change on page {pageno}")
            time.sleep(1.0)                               # polite between pages
        if not target:
            stop("step 2b", f"target not found within page cap ({MAX_PAGES})")

        # ---- Step 3: download the resolved target + intercept ----
        print(f"\n[3] Downloading target via lnkFileName postback...")
        print(f"    postback id : {target}")
        dl_t0 = time.time()
        try:
            with page.expect_download(timeout=120000) as dl:
                frame.evaluate(f"__doPostBack('{target}','')")
                report["postback_fired"] = True
            download = dl.value
            report["download_caught"] = True
        except PlaywrightTimeout:
            report["postback_fired"] = True
            stop("step 3", "postback fired but NO download event within 120s",
                 "expect_download() never caught a stream (inline response / anon not streamed?).")
        download.save_as(OUT_PATH)
        report["seconds"] = round(time.time() - dl_t0, 1)
        report["total_seconds"] = round(time.time() - cycle_t0, 1)
        print(f"    -> download caught: {download.suggested_filename!r}  ({report['seconds']}s)")
        print(f"    -> saved to {OUT_PATH}")

        browser.close()

    # ---- Step 4: DECISIVE sha256 ground-truth ----
    print("\n[4] sha256 ground-truth check...")
    import os
    size = os.path.getsize(OUT_PATH)
    head = open(OUT_PATH, "rb").read(5)
    got = sha256_of(OUT_PATH)
    report["sha256_match"] = (got == TARGET_SHA256)
    print(f"    file size : {size:,} bytes")
    print(f"    PDF magic : {head!r}  ({'looks like PDF' if head == b'%PDF-' else 'NOT a PDF'})")
    print(f"    expected  : {TARGET_SHA256}")
    print(f"    got       : {got}")
    print(f"    MATCH     : {report['sha256_match']}")

    # ---- Step 5: verdict ----
    print("\n" + "=" * 68)
    print("VERDICT")
    print("=" * 68)
    for k, v in report.items():
        print(f"  {k:18}: {v}")
    if report["sha256_match"]:
        print("\n  RESULT: byte-fetch engine WORKS — pulled the real, intact file.")
    else:
        print("\n  RESULT: got a file but sha256 != target — see size/magic above to judge"
              " whether it's the wrong attachment vs a corrupted/HTML response.")
    return report


if __name__ == "__main__":
    run(headless="--headed" not in sys.argv)
