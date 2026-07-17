"""
Harvest flagged plan sets from the doc-linked WOULD-HARVEST set -> local staging + review
manifest. NOTHING irreversible: downloads, hashes, local staging, a CSV. No R2, no v2 write.

Engine reused VERBATIM from generalize_test.py / document_download_poc.py (proven 5/5):
  discover_url -> goto CapDetail -> assert ZP -> handlePortletNavigation(tab-attachments)
  -> read gdvAttachmentList rows -> three-state paginate -> classify -> expect_download.

Resumable: /tmp/harvest_stage/state.json records completed permits + manifest rows.
Polite: random 5-15s between records, 0.8-2.5s between page turns. STOP a record on
captcha/auth/redirect (visible text). Per-record plan-set cap 8.
"""
import sys, os, time, re, json, hashlib, random, subprocess, sqlite3
sys.path.insert(0, "experiments/accela_scrape")
from url_discovery_scraper import discover_url
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

DB = "databases/berkeley_housing_v2.db"
STAGE = "/tmp/harvest_stage"
STATE = f"{STAGE}/state.json"
MANIFEST = f"{STAGE}/manifest.csv"
IFRAME_ID = "ctl00_PlaceHolderMain_attachmentEdit_iframeAttachmentList"
BLOCK_MARKERS = ("captcha", "are you a human", "checking your browser",
                 "verify you are human", "request blocked")
PLAN_KW = ("plan", "drawing", "resubmittal", "resubmission", "architectural")
CLEAN_KW = ("plan", "drawing", "resubmittal")     # a "clean" plan-set match
MIB = 1024 * 1024
SIZE_MIN = 5 * MIB
CAP_PLANSETS = 8
CAP_PAGES = 12
_BATCH_SHA = set()   # within-batch sha256 dedup (catches same file re-attached under 2 names)
_STAGED_PATHS = set()  # dest paths already STAGED-OK this run — a dedup delete must never
                       # remove one (same filename on a sibling record overwrites dest via
                       # save_as, then the remove would nuke the staged file: 2449 Dwight
                       # DRCF/DRCP Item-6b pair, 2026-07-16)

RECORDS = [
    dict(proj=9,  permit="ZP2024-0075", addr="1899 Oxford"),
    dict(proj=10, permit="ZP2022-0046", addr="3000 Shattuck"),
    dict(proj=11, permit="ZP2024-0074", addr="1581 University"),
    dict(proj=15, permit="ZP2024-0066", addr="2109 Virginia"),
    dict(proj=17, permit="ZP2023-0099", addr="2109 Milvia"),
    dict(proj=26, permit="ZP2024-0126", addr="2298 Durant"),
    dict(proj=36, permit="ZP2023-0090", addr="2733 San Pablo"),
    dict(proj=41, permit="ZP2024-0096", addr="2147 San Pablo"),
]

COLS = ["status", "project_id", "permit_number", "filename", "file_size_mib",
        "page_count", "classifier_reason", "grid_displayed_size", "sha256",
        "suggested_r2_key", "existing_stub_doc_id", "local_path"]


# ---------- v2 read-only context (dedup + stub matching) ----------
def load_v2():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    sha = {r[0] for r in con.execute(
        "SELECT sha256 FROM documents WHERE sha256 IS NOT NULL AND sha256<>''")}
    stubs = {}   # project_id -> list[(doc_id, notes_filename_casefold)]
    for did, pid, notes in con.execute(
            "SELECT id, project_id, notes FROM documents WHERE source_system LIKE '%.txt'"):
        m = re.match(r"\s*filename:\s*(.+)", notes or "")
        if not m:
            continue
        fn = re.split(r"\n|\s\|\s", m.group(1))[0].strip()
        if fn:
            stubs.setdefault(pid, []).append((did, fn.casefold()))
    con.close()
    return sha, stubs


def match_stub(stubs, pid, filename):
    fl = (filename or "").casefold()
    best = None
    for did, cfn in stubs.get(pid, []):
        if fl == cfn or fl.startswith(cfn) or cfn.startswith(fl):
            if best is None or len(cfn) > best[1]:
                best = (did, len(cfn))
    return best[0] if best else None


# ---------- engine helpers (verbatim from proven scripts) ----------
def read_rows(frame):
    return frame.evaluate(r"""() => {
        const out=[];
        document.querySelectorAll("a[href*='lnkFileName']").forEach(a => {
            const m=(a.getAttribute('href')||'').match(/__doPostBack\('([^']+)'/);
            const tr=a.closest('tr');
            out.push({target:m?m[1]:null, filename:(a.textContent||'').trim(),
                      rowtext:(tr?tr.innerText:'').replace(/\s+/g,' ').trim()});
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


def grid_size_str(rowtext):
    m = re.search(r"[\d.]+\s*(?:GB|MB|KB)", rowtext or "", re.I)
    return m.group(0) if m else ""


def grid_size_bytes(rowtext):
    # Accela displays "MB" but the value is actually MiB (proven: bytes/1048576 == shown).
    m = re.search(r"([\d.]+)\s*(GB|MB|KB)", rowtext or "", re.I)
    if not m:
        return None
    n = float(m.group(1)); u = m.group(2).upper()
    return int(n * {"GB": 1024 * MIB, "MB": MIB, "KB": 1024}[u])


def classify(fn, size_bytes):
    fl = (fn or "").lower()
    hit = next((k for k in PLAN_KW if k in fl), None)
    if not hit:
        return (False, None, "no plan keyword")
    if size_bytes is not None and size_bytes <= SIZE_MIN:
        return (False, hit, f"kw '{hit}' but {size_bytes/MIB:.1f}MiB<=5")
    return (True, hit, f"kw '{hit}'" + (f" +{size_bytes/MIB:.0f}MiB" if size_bytes else " +size?"))


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def page_count(path):
    try:
        out = subprocess.run(["pdfinfo", path], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r"^Pages:\s*(\d+)", out, re.M)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def extract_date(fn):
    m = re.search(r"(\d{4})[-_.](\d{2})[-_.](\d{2})", fn or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{2})[-_.](\d{2})[-_.](\d{4})", fn or "")  # MM-DD-YYYY
    if m:
        return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
    return "nodate"


def slugify(addr):
    return re.sub(r"[^a-z0-9]+", "-", addr.lower()).strip("-")


# ---------- per-record harvest ----------
def harvest_record(rec, sha_set, stubs):
    rows_out = []
    slug = slugify(rec["addr"])
    proj_dir = f"{STAGE}/{rec['proj']}"
    os.makedirs(proj_dir, exist_ok=True)

    # 2026-07-15 fix (the queued harvester items): a record may carry its own detail href
    # (from the date_range harvest, which enumerates EVERY record incl. -REV/-DEF sub-records
    # and Building-module permits). With an href we skip discovery AND the ZP-only gate —
    # the permit-label assert below still guards against wrong-page loads.
    if rec.get("href"):
        url = "https://aca-prod.accela.com" + rec["href"]
        print(f"  [{rec['permit']}] direct href")
    else:
        d = discover_url(rec["permit"], module_hint="Planning", headless=True, max_runtime_seconds=120)
        if not d.get("found"):
            return [dict(status="DISCOVERY-FAILED", project_id=rec["proj"], permit_number=rec["permit"],
                         filename="", file_size_mib="", page_count="", classifier_reason="",
                         grid_displayed_size="", sha256="", suggested_r2_key="",
                         existing_stub_doc_id="", local_path="")]
        m = d["master"]
        if not (m["permit_number_displayed"].startswith("ZP") and m["capid1"].endswith("PLN")):
            return [dict(status="SKIP-NOT-ZP-PLANNING", project_id=rec["proj"], permit_number=rec["permit"],
                         filename=m["permit_number_displayed"], file_size_mib="", page_count="",
                         classifier_reason=f"capid1={m['capid1']}", grid_displayed_size="", sha256="",
                         suggested_r2_key="", existing_stub_doc_id="", local_path="")]
        url = m["capdetail_url"]
        print(f"  [{rec['permit']}] capID {m['capid_triplet']}")

    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 1400, "height": 900},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        accept_downloads=True)
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        vis = (page.inner_text("body") or "").lower()
        if "login.aspx" in page.url.lower() or "signin" in page.url.lower() or any(b in vis for b in BLOCK_MARKERS):
            return [dict(status="STOP-block/auth", project_id=rec["proj"], permit_number=rec["permit"],
                         filename="", file_size_mib="", page_count="",
                         classifier_reason="captcha/auth/redirect (visible text)", grid_displayed_size="",
                         sha256="", suggested_r2_key="", existing_stub_doc_id="", local_path="")]
        el = page.query_selector("#ctl00_PlaceHolderMain_lblPermitNumber")
        if not el or el.inner_text().strip() != rec["permit"]:
            return [dict(status="FAILED-assert", project_id=rec["proj"], permit_number=rec["permit"],
                         filename=el.inner_text().strip() if el else "(none)", file_size_mib="",
                         page_count="", classifier_reason="permit label mismatch", grid_displayed_size="",
                         sha256="", suggested_r2_key="", existing_stub_doc_id="", local_path="")]
        if page.evaluate("""() => {const a=document.querySelector('a[data-control="tab-attachments"]');
                            if(!a||typeof handlePortletNavigation!=='function')return 'no';
                            handlePortletNavigation(a);return 'ok';}""") != "ok":
            return [dict(status="FAILED-activate", project_id=rec["proj"], permit_number=rec["permit"],
                         filename="", file_size_mib="", page_count="", classifier_reason="grid activation failed",
                         grid_displayed_size="", sha256="", suggested_r2_key="", existing_stub_doc_id="",
                         local_path="")]
        time.sleep(3)
        frame = page.wait_for_selector(f"#{IFRAME_ID}", state="attached", timeout=30000).content_frame()
        try:
            frame.wait_for_load_state("networkidle", timeout=25000)
        except PlaywrightTimeout:
            pass
        time.sleep(2)
        # Robust grid wait: the iframe's AttachmentsList.aspx can populate slowly under
        # back-to-back batch pressure — reading rows once after a fixed sleep yielded false
        # 0-form results (proj27: 0 in batch, 3 on isolated re-run). Poll until rows appear.
        for _ in range(15):
            if read_rows(frame):
                break
            time.sleep(1.0)

        seen_files = set()
        staged = 0
        page_no = 0
        while page_no < CAP_PAGES:
            page_no += 1
            rows = read_rows(frame)
            for r in rows:
                if r["filename"] in seen_files:
                    continue
                seen_files.add(r["filename"])
                size_b = grid_size_bytes(r["rowtext"])
                ok, kw, reason = classify(r["filename"], size_b)
                if not ok:
                    continue
                if staged >= CAP_PLANSETS:
                    print(f"    cap {CAP_PLANSETS} reached, skipping further flagged rows")
                    continue
                # must be on the page that holds this row to fire its ctl##
                live = [x for x in rows if x["filename"] == r["filename"] and x["target"]]
                if not live:
                    continue
                target = live[0]["target"]
                staged += 1
                rows_out.append(download_one(page, frame, target, r, rec, slug, kw, reason,
                                             size_b, sha_set, stubs, proj_dir))
            nxt = find_next(frame)
            if not nxt:
                break
            first_sig = (rows[0]["target"], rows[0]["filename"]) if rows else None
            frame.evaluate(f"__doPostBack('{nxt['target']}','')")
            changed = False
            for _ in range(16):
                time.sleep(0.5)
                try:
                    rows = read_rows(frame)
                except Exception:
                    rows = []
                if rows and (rows[0]["target"], rows[0]["filename"]) != first_sig:
                    changed = True
                    break
            if not changed:
                print(f"    pagination stalled at page {page_no}; stopping enumeration")
                break
            time.sleep(random.uniform(0.8, 2.5))
        if not rows_out:
            rows_out.append(dict(status="NO-PLANSETS", project_id=rec["proj"], permit_number=rec["permit"],
                                 filename="", file_size_mib="", page_count="", classifier_reason="",
                                 grid_displayed_size="", sha256="", suggested_r2_key="",
                                 existing_stub_doc_id="", local_path=""))
    finally:
        ctx.close(); browser.close(); p.stop()
    return rows_out


def download_one(page, frame, target, r, rec, slug, kw, reason, size_b, sha_set, stubs, proj_dir):
    fn_safe = r["filename"].replace("/", "_")
    dest = f"{proj_dir}/{fn_safe}"
    grid_str = grid_size_str(r["rowtext"])
    base = dict(status="", project_id=rec["proj"], permit_number=rec["permit"], filename=r["filename"],
                file_size_mib="", page_count="", classifier_reason=f"{reason} [{kw}]",
                grid_displayed_size=grid_str, sha256="", suggested_r2_key="",
                existing_stub_doc_id=match_stub(stubs, rec["proj"], r["filename"]) or "", local_path="")
    try:
        with page.expect_download(timeout=180000) as dl:
            frame.evaluate(f"__doPostBack('{target}','')")
        download = dl.value
        download.save_as(dest)
    except PlaywrightTimeout:
        base["status"] = "FAILED-no-download"
        return base
    size = os.path.getsize(dest)
    magic = open(dest, "rb").read(5)
    sha = sha256_of(dest)
    base["file_size_mib"] = round(size / MIB, 1)
    base["sha256"] = sha
    # dedup against v2
    if sha in sha_set:
        if dest not in _STAGED_PATHS:
            os.remove(dest)
        base["status"] = "SKIPPED-DEDUP"
        base["local_path"] = ""
        print(f"    DEDUP  {r['filename'][:50]}  (sha already in v2)")
        return base
    # within-batch dedup — same bytes re-attached under a different filename/date
    if sha in _BATCH_SHA:
        if dest not in _STAGED_PATHS:
            os.remove(dest)
        base["status"] = "SKIPPED-DEDUP-BATCH"
        base["local_path"] = ""
        print(f"    DEDUP-BATCH  {r['filename'][:46]}  (same sha already staged this run)")
        return base
    _BATCH_SHA.add(sha)
    # validate
    if magic != b"%PDF-" or size < 1024:
        base["status"] = "FAILED-corrupt"
        base["page_count"] = "n/a"
        os.remove(dest)
        print(f"    FAILED corrupt/short  {r['filename'][:50]}")
        return base
    pc = page_count(dest)
    base["page_count"] = pc if pc is not None else "?"
    base["local_path"] = dest
    date = extract_date(r["filename"])
    base["suggested_r2_key"] = f"architect_plans/proj{rec['proj']}_{slug}_{date}.pdf"
    base["status"] = "STAGED-OK"
    _STAGED_PATHS.add(dest)
    print(f"    STAGED {base['file_size_mib']}MiB p{base['page_count']}  {r['filename'][:48]}")
    return base


# ---------- state / manifest ----------
def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {"completed": [], "rows": []}


def save_state(st):
    json.dump(st, open(STATE, "w"), indent=2)


def write_manifest(rows):
    def grid_num(s):
        m = re.search(r"[\d.]+", s or "")
        return float(m.group(0)) if m else None

    def deviates(row):
        if row["status"] != "STAGED-OK":
            return False
        gd = grid_num(row["grid_displayed_size"])
        if gd is None or not row["file_size_mib"]:
            return False
        return abs(row["file_size_mib"] - gd) / gd > 0.10

    def rank(row):
        s = row["status"]
        if s.startswith("FAILED") or s.startswith("STOP") or s in ("DISCOVERY-FAILED", "SKIP-NOT-ZP-PLANNING"):
            return 0
        if s == "STAGED-OK" and deviates(row):
            return 1
        if s == "STAGED-OK":
            return 2
        if s == "SKIPPED-DEDUP":
            return 4
        return 3  # NO-PLANSETS etc
    ordered = sorted(rows, key=lambda r: (rank(r), str(r["project_id"])))
    # GUARD: suggested_r2_key must be unique across STAGED rows. On collision (e.g. two
    # same-date drawing sets), auto-append _<sha8> so a file is never silently stranded by
    # a key clash at upload time. Mutates the row in place so the fix persists to state.json.
    _seen = set()
    for r in ordered:
        if r.get("status") != "STAGED-OK":
            continue
        k = r.get("suggested_r2_key", "")
        if k and k in _seen:
            sha8 = (r.get("sha256") or "")[:8]
            newk = re.sub(r"\.pdf$", f"_{sha8}.pdf", k)
            print(f"  KEY-COLLISION guard: {k} -> {newk} (auto sha8)")
            r["suggested_r2_key"] = newk
            k = newk
        if k:
            _seen.add(k)
    import csv
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in ordered:
            w.writerow({k: r.get(k, "") for k in COLS})
    return ordered, deviates


def main():
    os.makedirs(STAGE, exist_ok=True)
    sha_set, stubs = load_v2()
    st = load_state()
    done = set(st["completed"])
    for i, rec in enumerate(RECORDS):
        if rec["permit"] in done:
            print(f"\n=== proj{rec['proj']} {rec['permit']} — already done, resume-skip ===")
            continue
        print(f"\n{'='*70}\nproj{rec['proj']} {rec['permit']} ({rec['addr']})\n{'='*70}")
        try:
            rr = harvest_record(rec, sha_set, stubs)
        except Exception as e:
            rr = [dict(status="FAILED-exception", project_id=rec["proj"], permit_number=rec["permit"],
                       filename="", file_size_mib="", page_count="", classifier_reason=str(e)[:80],
                       grid_displayed_size="", sha256="", suggested_r2_key="", existing_stub_doc_id="",
                       local_path="")]
        st["rows"].extend(rr)
        st["completed"].append(rec["permit"])
        save_state(st)
        write_manifest(st["rows"])
        if i < len(RECORDS) - 1 and rec["permit"] not in done:
            dly = random.uniform(5, 15)
            print(f"  ...polite delay {dly:.1f}s")
            time.sleep(dly)

    ordered, deviates = write_manifest(st["rows"])
    staged = [r for r in st["rows"] if r["status"] == "STAGED-OK"]
    failed = [r for r in st["rows"] if r["status"].startswith("FAILED")]
    dedup = [r for r in st["rows"] if r["status"] == "SKIPPED-DEDUP"]
    stops = [r for r in st["rows"] if r["status"].startswith("STOP")]
    total_gb = sum(r["file_size_mib"] for r in staged if r["file_size_mib"]) * MIB / 1e9
    look = ([("FAILED", r) for r in failed] + [("STOP", r) for r in stops]
            + [("SIZE-DEV", r) for r in staged if deviates(r)]
            + [("ODD-KW", r) for r in staged
               if not any(k in r["classifier_reason"] for k in CLEAN_KW)])
    print(f"\n{'#'*70}\nHARVEST SUMMARY\n{'#'*70}")
    print(f"  staged-ok : {len(staged)}   failed: {len(failed)}   deduped: {len(dedup)}   STOPs: {len(stops)}")
    print(f"  total staged size: {total_gb:.2f} GB")
    print(f"  manifest: {MANIFEST}")
    print(f"  LOOK TWICE ({len(look)}):")
    for tag, r in look:
        print(f"    [{tag}] proj{r['project_id']} {r['filename'][:46]} "
              f"({r['file_size_mib']}MiB vs {r['grid_displayed_size']}) {r['classifier_reason']}")
    if not look:
        print("    (none — every staged file is a clean plan/drawings/resubmittal match within 10% of grid size)")


if __name__ == "__main__":
    main()
