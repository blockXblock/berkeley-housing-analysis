"""
Generalization test — does the proj15 byte-fetch recipe hold across record variety?

Reuses the PROVEN mechanism from document_download_poc.py verbatim:
  discover capID -> goto CapDetail -> assert permit -> handlePortletNavigation(tab-attachments)
  -> read gdvAttachmentList rows in the iframe -> paginate via frame __doPostBack (three-state)
  -> lnkFileName postback + page.expect_download.

4 records of different shapes. Per record: enumerate ALL pages, classify plan sets, download
ONE flagged plan set. Report deviations. Polite: jittered 5-15s between records, ~1-2s between
page turns. STOP a record on captcha/auth/redirect (visible text). /tmp only; no R2/v2/commit.
"""
import sys, time, re, hashlib, random
sys.path.insert(0, "experiments/accela_scrape")
from url_discovery_scraper import discover_url
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

IFRAME_ID = "ctl00_PlaceHolderMain_attachmentEdit_iframeAttachmentList"
BLOCK_MARKERS = ("captcha", "are you a human", "checking your browser",
                 "verify you are human", "request blocked")
PLAN_KW = ("plan", "drawing", "resubmittal", "resubmission", "architectural")
CAP_PAGES = 12

RECORDS = [
    dict(proj=9,  permit="ZP2024-0075", addr="1899 Oxford",     expect_plansets=4),
    dict(proj=11, permit="ZP2024-0074", addr="1581 University", expect_plansets=1),
    dict(proj=26, permit="ZP2024-0126", addr="2298 Durant",     expect_plansets=4),
    dict(proj=41, permit="ZP2024-0096", addr="2147 San Pablo",  expect_plansets=2),
]


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def parse_size(rowtext):
    m = re.search(r"([\d.]+)\s*(GB|MB|KB)", rowtext or "", re.I)
    if not m:
        return None
    n = float(m.group(1)); u = m.group(2).upper()
    return int(n * {"GB": 1e9, "MB": 1e6, "KB": 1e3}[u])


def is_planset(fn, size):
    fl = (fn or "").lower()
    if not any(k in fl for k in PLAN_KW):
        return (False, "no-keyword")
    if size is not None and size <= 5_000_000:
        return (False, f"kw but {size/1e6:.1f}MB<=5")
    return (True, "kw" + (f"+{size/1e6:.0f}MB" if size else "+size?"))


def read_rows(frame):
    return frame.evaluate(r"""() => {
        const out = [];
        document.querySelectorAll("a[href*='lnkFileName']").forEach(a => {
            const m = (a.getAttribute('href')||'').match(/__doPostBack\('([^']+)'/);
            const tr = a.closest('tr');
            out.push({ target: m?m[1]:null,
                       filename: (a.textContent||'').trim(),
                       rowtext: (tr?tr.innerText:'').replace(/\s+/g,' ').trim() });
        });
        return out;
    }""")


def find_next(frame):
    return frame.evaluate(r"""() => {
        for (const a of document.querySelectorAll('a')) {
            const t=(a.innerText||a.textContent||'').trim();
            const h=a.getAttribute('href')||'';
            if (h.includes('__doPostBack') && (/next/i.test(t)||t==='>'||t==='&gt;')) {
                const m=h.match(/__doPostBack\('([^']+)'/);
                if (m) return {target:m[1], text:t};
            }
        }
        return null;
    }""")


def run_record(rec):
    out = dict(rec, recipe="UNCHANGED", deviations=[], capid=None, rec_type=None,
               total_attachments=0, total_pages=0, flagged=[], download=None, error=None)
    # ---- 1. URL discovery ----
    d = discover_url(rec["permit"], module_hint="Planning", headless=True, max_runtime_seconds=120)
    if not d.get("found"):
        out["error"] = f"URL discovery failed: {d.get('errors')}"
        out["recipe"] = "FAILED"
        return out
    m = d["master"]
    out["capid"] = m["capid_triplet"]
    out["rec_type"] = m["permit_number_displayed"]
    url = m["capdetail_url"]

    # discover_url ran+closed its own Playwright above; now start ours (sequential, not nested)
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 1400, "height": 900},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        accept_downloads=True,
    )
    page = ctx.new_page()
    try:
        cyc = time.time()
        # ---- 2. load + assert + activate ----
        page.goto(url, wait_until="networkidle", timeout=60000)
        vis = (page.inner_text("body") or "").lower()
        if "login.aspx" in page.url.lower() or "signin" in page.url.lower():
            out["error"] = "redirected to login"; out["recipe"] = "STOP-auth"; return out
        if any(b in vis for b in BLOCK_MARKERS):
            out["error"] = "captcha/block (visible text)"; out["recipe"] = "STOP-block"; return out
        el = page.query_selector("#ctl00_PlaceHolderMain_lblPermitNumber") \
            or page.query_selector("span[id*='lblPermitNumber']")
        permit_shown = (el.inner_text().strip() if el else "")
        if permit_shown != rec["permit"]:
            out["error"] = f"permit mismatch: page shows {permit_shown!r}"
            out["recipe"] = "FAILED"; return out
        fired = page.evaluate("""() => {
            const a=document.querySelector('a[data-control="tab-attachments"]');
            if(!a) return 'NO_NAV'; if(typeof handlePortletNavigation!=='function') return 'NO_FN';
            handlePortletNavigation(a); return 'ok';
        }""")
        if fired != "ok":
            out["error"] = f"activation failed: {fired}"; out["recipe"] = "FAILED"; return out
        if fired != "ok":
            out["deviations"].append(f"activation:{fired}")
        time.sleep(3)
        iframe_el = page.wait_for_selector(f"#{IFRAME_ID}", state="attached", timeout=30000)
        frame = iframe_el.content_frame()
        try:
            frame.wait_for_load_state("networkidle", timeout=25000)
        except PlaywrightTimeout:
            pass
        time.sleep(2)
        # ---- 3. enumerate ALL pages + classify; ---- 4. download first flagged plan set ----
        seen = set(); page_no = 0
        while page_no < CAP_PAGES:
            page_no += 1
            rows = read_rows(frame)
            for r in rows:
                key = r["filename"]
                if key in seen:
                    continue
                seen.add(key)
                out["total_attachments"] += 1
                size = parse_size(r["rowtext"])
                ok, why = is_planset(r["filename"], size)
                if ok:
                    out["flagged"].append(dict(file=r["filename"], size=size, page=page_no, why=why))
            # download one flagged plan set the moment we're on its page
            if out["download"] is None:
                here = [r for r in rows if is_planset(r["filename"], parse_size(r["rowtext"]))[0] and r["target"]]
                if here:
                    pick = here[0]
                    safe = re.sub(r"[^A-Za-z0-9]+", "_", rec["addr"]).strip("_")
                    dest = f"/tmp/gen_{rec['proj']}_{safe}.pdf"
                    try:
                        with page.expect_download(timeout=120000) as dl:
                            frame.evaluate(f"__doPostBack('{pick['target']}','')")
                        download = dl.value
                        download.save_as(dest)
                        magic = open(dest, "rb").read(5)
                        out["download"] = dict(
                            file=pick["filename"], suggested=download.suggested_filename,
                            path=dest, size=__import__("os").path.getsize(dest),
                            is_pdf=(magic == b"%PDF-"), sha256=sha256_of(dest),
                            page=page_no)
                    except PlaywrightTimeout:
                        out["deviations"].append("download: expect_download timed out")
            # paginate
            first_sig = (rows[0]["target"], rows[0]["filename"]) if rows else None
            nxt = find_next(frame)
            if not nxt:
                break  # last_page
            frame.evaluate(f"__doPostBack('{nxt['target']}','')")
            changed = False
            for _ in range(16):
                time.sleep(0.5)
                try:
                    rows2 = read_rows(frame)
                except Exception:
                    rows2 = []
                if rows2 and (rows2[0]["target"], rows2[0]["filename"]) != first_sig:
                    changed = True; break
            if not changed:
                out["deviations"].append(f"pagination stalled at page {page_no}")
                break
            time.sleep(random.uniform(1.0, 2.0))  # polite between page turns
        out["total_pages"] = page_no
        out["cycle_seconds"] = round(time.time() - cyc, 1)
        if out["download"] is None and out["flagged"]:
            out["deviations"].append("had flagged plan set(s) but no download captured")
        if out["deviations"]:
            out["recipe"] = "BENT: " + "; ".join(out["deviations"])
    finally:
        ctx.close(); browser.close(); p.stop()
    return out


def main():
    results = []
    for i, rec in enumerate(RECORDS):
        print(f"\n{'='*72}\nRECORD {rec['proj']} {rec['permit']} ({rec['addr']})\n{'='*72}")
        r = run_record(rec)
        results.append(r)
        print(f"  capID: {r['capid']}  type: {r['rec_type']}")
        print(f"  attachments: {r['total_attachments']} across {r['total_pages']} pages"
              f"  (cycle {r.get('cycle_seconds','?')}s)")
        print(f"  plan-set flagged ({len(r['flagged'])}, expected ~{rec['expect_plansets']}):")
        for f in r["flagged"]:
            sz = f"{f['size']/1e6:.1f}MB" if f["size"] else "?MB"
            print(f"      p{f['page']} [{sz}] {f['file'][:62]}")
        dl = r["download"]
        if dl:
            print(f"  DOWNLOADED: {dl['file'][:55]}")
            print(f"      -> {dl['path']}  {dl['size']:,}B  pdf={dl['is_pdf']}  sha256={dl['sha256'][:24]}…")
            print(f"      suggested_filename matches row: {dl['suggested']==dl['file']}")
        else:
            print(f"  DOWNLOADED: none ({r.get('error') or 'no flagged target'})")
        print(f"  RECIPE: {r['recipe']}")
        if i < len(RECORDS) - 1:
            d = random.uniform(5, 15)
            print(f"  ...polite delay {d:.1f}s before next record")
            time.sleep(d)

    print(f"\n{'#'*72}\nGENERALIZATION VERDICT\n{'#'*72}")
    unchanged = sum(1 for r in results if r["recipe"] == "UNCHANGED")
    for r in results:
        print(f"  proj{r['proj']:>3} {r['permit']}: {r['recipe'][:80]}")
    print(f"\n  {unchanged}/{len(results)} records ran the proj15 recipe UNCHANGED.")
    alldev = [d for r in results for d in r["deviations"]]
    print(f"  deviations: {alldev if alldev else 'NONE — recipe generalizes'}")


if __name__ == "__main__":
    main()
