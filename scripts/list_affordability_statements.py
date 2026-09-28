#!/usr/bin/env python3
r"""list_affordability_statements.py -- WHICH affordability statements exist, before anything is
downloaded. Read-only: lists attachment filenames, downloads NOTHING.

WHY. Berkeley's 1.E tabulation form never states affordability; income tiers live only in a Density
Bonus Eligibility Statement or an Affordable Housing Compliance Plan. We hold those for 9 projects,
which is why only 255 of ~1,200 affordable units in v2 are sourced. 33 projects with affordable units
have no sourced ruling -- 947 units. This pass answers which of them have a statement on file.

TWO THINGS LEARNED THE HARD WAY AND REUSED RATHER THAN REBUILT:
 1. The CapDetail harvest does NOT capture attachments. Measured over 300 saved pages: the attachment
    tab is present in all 300 and ZERO contain a filename. The grid lives in an IFRAME
    (ctl00_PlaceHolderMain_attachmentEdit_iframeAttachmentList) that only populates after the
    attachments TAB IS CLICKED -- waiting does not do it. An anonymous page shows only the upload
    widget ("maximum file size allowed is 200 MB"), which looks like "no attachments" and is not.
 2. experiments/accela_scrape/harvest_plansets.py already solved this in June. Its read_rows /
    find_next / grid_size_bytes and its IFRAME_ID are IMPORTED here, not re-typed. Its `classify` is
    NOT reused: that one is tuned for plan sets (>=5 MiB, plan keywords) and would reject a 0.08 MB
    statement outright.

  .venv/bin/python scripts/list_affordability_statements.py            # list, no downloads
  .venv/bin/python scripts/list_affordability_statements.py --limit 5  # smoke test
"""
from __future__ import annotations

import argparse
import csv
import glob
import importlib.util
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "experiments/accela_scrape"))

_spec = importlib.util.spec_from_file_location(
    "hp", ROOT / "experiments/accela_scrape/harvest_plansets.py")
hp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hp)                      # read_rows, find_next, grid_size_bytes, IFRAME_ID

from capdetail_select import addr_key             # noqa: E402  the rule-4c canon, via the selector

V2 = ROOT / "databases/berkeley_housing_v2.db"
OUT = ROOT / "scratch/2026-09-28_statements"
BASE = "https://aca-prod.accela.com"

# THIS SCRIPT NO LONGER DECIDES WHAT A STATEMENT IS CALLED.
#
# The first version matched /density bonus|eligibil|affordab|compliance plan/ on the filename and
# reported ZERO statements for proj153 -- 1701 San Pablo, an SB 35 project whose 110 units are ALL
# affordable. Its actual filenames are date-prefixed and abbreviated:
#     2023-02-27_RESUB_2023-02-22_Applic Response to DB Comments_1701 San Pablo.pdf
#     2023-02-27_RESUB_2._Revised Applicant Statement_San Pablo Ave.pdf
#     2022-11-04_SB35 Preliminary Application Ltr_1701 San Pablo.pdf
# "DB" is density bonus; "Revised Applicant Statement" is very likely the eligibility statement.
# Writing a pattern from what a document is CALLED rather than from what the city TYPES is the same
# error as matching `dwelling` and missing "166 dwellings".
#
# So: list EVERY filename (cheap, no downloads) and mark a broad CANDIDATE set for a model to judge.
# A candidate is a hint for the next step, never a verdict. NOT_A_SOURCE stays narrow and is only
# applied to things Berkeley's own practice proves cannot carry tiers -- the 1.E tabulation form.
CANDIDATE = re.compile(r"(density\s*bonus|\bdb\b|eligibil|affordab|compliance|inclusionary|\bbmr\b|"
                       r"below\s*market|\bsb\s*35\b|\bsb\s*330\b|\bab\s*2011\b|applicant\s*"
                       r"statement|unit\s*mix|income|covenant|regulatory\s*agreement)", re.I)
NOT_A_SOURCE = re.compile(r"(tabulation|\b1\.?e\b)", re.I)
ASSET = re.compile(r"\.(png|jpe?g|gif|svg|ico|css|woff2?|ttf|eot|mp4)(\?|$)", re.I)


def targets(db):
    """the 33 projects with affordable units and no APPROVED sourced ruling -> their planning records"""
    approved = set()
    p = ROOT / "corrections/v4/affordability_rulings.csv"
    if p.exists():
        for r in csv.DictReader(open(p)):
            if (r.get("status") or "").strip() == "approved":
                approved.add(r["subject"].strip().upper())
    need = {}
    for pid, addr, tot, eli, vli, li, mod in db.execute(
            """SELECT project_id,address_display,total_units,COALESCE(eli_units,0),
               COALESCE(vli_units,0),COALESCE(li_units,0),COALESCE(mod_units,0)
               FROM v_projects_flat WHERE address_display IS NOT NULL"""):
        aff = eli + vli + li + mod
        if aff > 0 and (addr or "").strip().upper() not in approved:
            need[pid] = {"address": addr, "units": tot, "affordable": aff}
    # planning records reaching those projects, from the completed CapDetail harvest
    by_addr = {}
    for pid, a in db.execute("SELECT project_id,address_display FROM v_projects_flat "
                             "WHERE address_display IS NOT NULL"):
        k = addr_key(a)
        if k:
            by_addr.setdefault(k, set()).add(pid)
    by_apn = {}
    for pid, apn in db.execute("SELECT pp.project_id,p.apn_normalized FROM project_parcels pp "
                               "JOIN parcels p ON p.id=pp.parcel_id "
                               "WHERE p.apn_normalized IS NOT NULL"):
        by_apn.setdefault(apn, set()).add(pid)
    src = sorted(glob.glob(str(ROOT / "scratch/2026-09-26_capdetail/capdetail_reparsed_*.jsonl")))
    recs = {}
    for line in open(src[-1]):
        try:
            r = json.loads(line)
        except Exception:
            continue
        pids = set(by_addr.get(addr_key(r.get("work_location")), set()))
        for c in (r.get("parcels_canonical") or []):
            if c:
                pids |= by_apn.get(c, set())
        for pid in pids & set(need):
            recs.setdefault(pid, []).append({"record": r["record"], "href": r.get("href"),
                                             "type": r.get("record_type")})
    return need, recs


def read_attachments(pg, href) -> list[dict]:
    r"""click the attachments tab, then read every grid page. Returns rows; downloads nothing.

    This follows harvest_plansets.py's PROVEN sequence exactly, because four of my own deviations
    each produced a silent zero:
      * the tab must be activated with handlePortletNavigation(a) -- a plain a.click() does nothing;
      * the grid frame comes from wait_for_selector('#'+IFRAME_ID).content_frame(), then networkidle;
      * read_rows returns DICTS {target, filename, rowtext}, not strings;
      * and above all: POLL until rows appear. That file's own comment records why -- "reading rows
        once after a fixed sleep yielded false 0-form results (proj27: 0 in batch, 3 on isolated
        re-run)". A single read is how you get a zero that means "not looking".
    """
    pg.goto(BASE + href, wait_until="domcontentloaded")
    pg.wait_for_timeout(1200)
    ok = pg.evaluate("""() => {const a=document.querySelector('a[data-control="tab-attachments"]');
                        if(!a||typeof handlePortletNavigation!=='function')return 'no';
                        handlePortletNavigation(a);return 'ok';}""")
    if ok != "ok":
        raise RuntimeError("attachment grid activation failed")
    pg.wait_for_timeout(2500)
    el = pg.wait_for_selector(f"#{hp.IFRAME_ID}", state="attached", timeout=30000)
    frame = el.content_frame()
    try:
        frame.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    # HOW MANY PAGES THE GRID ITSELF SAYS IT HAS. The pager renders numbered links (2,3,4...)
    # alongside "Next >", so the highest number is the page count -- an INDEPENDENT statement of
    # size to check our reading against, instead of trusting the loop to have finished.
    declared = frame.evaluate("""() => {
        let mx = 1;
        for (const a of document.querySelectorAll("a[href*='__doPostBack']")) {
            const t = (a.innerText || '').trim();
            if (/^[0-9]{1,3}$/.test(t)) mx = Math.max(mx, parseInt(t, 10));
        }
        return mx;
    }""")

    rows, pages, seen = [], 0, set()
    while pages < 40:
        page_rows = hp.read_rows(frame)
        fresh = 0
        for r in page_rows:
            fn = (r.get("filename") or "").strip()
            txt = (r.get("rowtext") or "").strip()
            if not fn or fn in seen:
                continue
            seen.add(fn)
            fresh += 1
            rows.append({"filename": fn, "row": txt[:220],
                         "bytes": hp.grid_size_bytes(txt) or 0})
        pages += 1
        nxt = hp.find_next(frame)
        if not nxt:
            break
        # FIRE THE PAGER. The first version of this loop TESTED find_next and never clicked it, so
        # the grid stayed on page 1, the content-compare guard correctly saw an unchanged page, and
        # every record with more than 10 attachments was reported as exactly 10 -- 33 of 105 records
        # (measured 2026-09-28 by hand: ZP2022-0021 has 46, ZP2023-0057 51, ZP2024-0029 21, each
        # listed as 10). The guard against the earlier 8x inflation was kept while the advance it
        # was guarding was dropped. Both halves are needed: fire __doPostBack, THEN require the
        # grid's first row to actually change before reading it as a new page.
        sig = (page_rows[0]["target"], page_rows[0]["filename"]) if page_rows else None
        frame.evaluate(f"__doPostBack('{nxt['target']}','')")
        changed = False
        for _ in range(16):
            pg.wait_for_timeout(500)
            try:
                after = hp.read_rows(frame)
            except Exception:
                after = []
            if after and (after[0]["target"], after[0]["filename"]) != sig:
                changed = True
                break
        if not changed:
            break                            # the pager did not advance: last page, or stalled
    # A truncated read must be VISIBLE, not silent. Raising means the caller records an ERROR row
    # for the record rather than a plausible-looking short list, which is what hid the bug.
    if pages < declared:
        raise RuntimeError(f"truncated: read {pages} of {declared} pages "
                           f"({len(rows)} filenames)")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default=None,
                    help="comma-separated record numbers to (re-)list; their rows REPLACE the "
                         "existing ones in statement_listing.csv and everything else is kept")
    ap.add_argument("--delay", type=float, default=2.0)
    args = ap.parse_args()
    db = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)
    need, recs = targets(db)
    work = [(pid, r) for pid in sorted(recs, key=lambda p: -need[p]["affordable"])
            for r in recs[pid]]
    only = {x.strip() for x in args.only.split(",")} if args.only else None
    if only:
        work = [(pid, r) for pid, r in work if r["record"] in only]
        missing = only - {r["record"] for _, r in work}
        if missing:
            print(f"NOT in the queue, skipped: {sorted(missing)}")
    if args.limit:
        work = work[:args.limit]
    print(f"projects needing a source: {len(need)} ({sum(v['affordable'] for v in need.values())} "
          f"affordable units)")
    print(f"of those, reachable planning records: {len(recs)} projects / {len(work)} records")
    print(f"projects with NO reachable planning record: "
          f"{sorted(set(need) - set(recs))[:12]} ...\n")

    OUT.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright
    found, empty, failed = 0, 0, 0
    rows_out = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        for i, (pid, r) in enumerate(work, 1):
            pg = b.new_page()
            pg.set_default_timeout(40000)
            pg.route(ASSET, lambda q: q.abort())
            try:
                atts = read_attachments(pg, r["href"])
            except Exception as e:
                atts, failed = [], failed + 1
                rows_out.append({"project_id": pid, "record": r["record"], "kind": "ERROR",
                                 "filename": f"{type(e).__name__}", "bytes": 0})
            pg.close()
            hits = [a for a in atts if CANDIDATE.search(a["filename"])
                    and not NOT_A_SOURCE.search(a["filename"])]
            if atts:
                found += 1
            else:
                empty += 1
            for a in atts:
                kind = ("CANDIDATE" if a in hits else
                        ("not-a-source" if NOT_A_SOURCE.search(a["filename"]) else "other"))
                rows_out.append({"project_id": pid, "record": r["record"], "kind": kind,
                                 "filename": a["filename"], "bytes": a["bytes"]})
            mark = f"  *** {len(hits)} candidate(s)" if hits else ""
            print(f"  [{i}/{len(work)}] proj{pid:<5} {r['record']:16} "
                  f"{len(atts):3} attachments{mark}", flush=True)
            time.sleep(args.delay)
        b.close()
    out = OUT / "statement_listing.csv"
    if only and out.exists():
        kept = [{**r, "project_id": int(r["project_id"]), "bytes": int(r["bytes"] or 0)}
                for r in csv.DictReader(open(out)) if r["record"] not in only]
        print(f"kept {len(kept)} rows for records outside --only")
        rows_out = kept + rows_out
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["project_id", "record", "kind", "filename", "bytes"])
        w.writeheader()
        w.writerows(rows_out)
    st = [r for r in rows_out if r["kind"] == "CANDIDATE"]
    projs = sorted({r["project_id"] for r in st})
    print(f"\nTHIS RUN: records with any attachment listed: {found}   with none: {empty}   "
          f"errors: {failed}")
    print(f"the totals below cover the whole merged listing, not just this run")
    print(f"CANDIDATE documents: {len(st)} across {len(projs)} projects  (a model judges which are real sources -- this script does not)")
    print(f"  affordable units those projects cover: "
          f"{sum(need[p]['affordable'] for p in projs if p in need)}")
    tot = sum(r['bytes'] for r in st)
    print(f"  total bytes to download if approved: {tot/1e6:.1f} MB")
    print(f"\nlisting -> {out}   NOTHING DOWNLOADED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
