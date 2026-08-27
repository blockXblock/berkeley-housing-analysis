#!/usr/bin/env python3
"""size_staff_reports.py — SIZING PASS: of the placeholder buildings with no resolved height, how many
have a text-readable DRC/staff-report-type Planning document we could read the storey count out of?

DRC staff reports are the cheap, explicit height source (2000 University: no 1.E, but its staff report
stated "84' tall 8 story" in clean text). They reach buildings the BP-description method can't (a project
that went through Design Review has a staff report even if its permit only says "construct ADU"). This
pass does NOT download the reports — it just discovers each project's Planning records and checks the
attachment grids for a staff-report-type filename, to size the reachable fraction before committing.

Two phases to avoid the session-contamination bug (interleaving searches + attachment loads corrupts
results): (1) address-search all projects, collect candidate records; (2) check attachment grids.
Read-only. Output: data/reference/staff_report_sizing.csv. Run in .venv (single browser).
"""
import sys, os, time, re, json, random
import pandas as pd

sys.path.insert(0, "experiments/accela_scrape")
import harvest_plansets as H
from harvest_address import search_by_address
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

OUT = "data/reference/staff_report_sizing.csv"
STATE = "scratch/2026-08-25/staff_sizing_state.json"
SUFFIXES = {"AVE", "ST", "WAY", "BLVD", "DR", "RD", "LN", "CT", "PL", "TER", "SQ", "CIR", "PATH", "WALK", "PKWY", "AVENUE", "STREET"}
# record types that carry a staff report, priority order (Design Review first, then Zoning/Use Permit)
SR_PREFIX_RANK = {"DRCP": 0, "DRCF": 0, "DRSA": 1, "ZP": 2, "UP": 3, "AUP": 3, "PLN": 4}
SR_RE = re.compile(r"staff report|DRC[_ ]?SR|\bSR[_ ]|staff.?rpt", re.I)
CAP = 3   # attachment grids to check per project (politeness)


def parse_addr(addr):
    toks = str(addr).upper().split()
    if not toks or not toks[0][0].isdigit():
        return None, str(addr)
    rest = toks[1:]
    if rest and rest[-1] in SUFFIXES:
        rest = rest[:-1]
    return re.sub(r"\D", "", toks[0]), " ".join(rest)


def prefix(p):
    m = re.match(r"([A-Z]+)", p or ""); return m.group(1) if m else ""


def check_attachments(ctx, url):
    """Return (has_staff_report, staff_report_filename, total_attachments)."""
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        if page.evaluate("""() => {const a=document.querySelector('a[data-control="tab-attachments"]');
            if(!a||typeof handlePortletNavigation!=='function')return 'no'; handlePortletNavigation(a);return 'ok';}""") != "ok":
            return (False, "", 0)
        time.sleep(2.5)
        fr = page.wait_for_selector(f"#{H.IFRAME_ID}", state="attached", timeout=25000).content_frame()
        try:
            fr.wait_for_load_state("networkidle", timeout=12000)
        except PWTimeout:
            pass
        time.sleep(1.5)
        rows = []
        for _ in range(12):
            rows = H.read_rows(fr)
            if rows:
                break
            time.sleep(1.0)
        sr = [r["filename"] for r in rows if SR_RE.search(r["filename"] or "")]
        return (bool(sr), sr[0][:60] if sr else "", len(rows))
    except Exception:
        return (False, "ERR", -1)
    finally:
        page.close()


def main():
    corr = pd.read_csv("data/reference/placeholder_corrections.csv")
    import sqlite3
    v2 = sqlite3.connect("databases/berkeley_housing_v2.db")
    # the 65: no resolved height
    targets = corr[corr.stories.isna()][["project_id", "address", "units"]].copy()
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"done": {}}
    results = state.get("rows", [])

    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    try:
        for _, pr in targets.iterrows():
            pid = int(pr.project_id)
            if str(pid) in state["done"]:
                continue
            no, name = parse_addr(pr.address)
            # PHASE 1: search (fresh context, no attachment loads -> no contamination)
            sctx = browser.new_context()
            spage = sctx.new_page()
            try:
                recs = search_by_address(spage, name, no, module="Planning", errors=[]).get("records", [])
            except Exception:
                recs = []
            finally:
                sctx.close()
            cands = [r for r in recs if prefix(r.get("permit_number_displayed", "")) in SR_PREFIX_RANK]
            cands.sort(key=lambda r: SR_PREFIX_RANK[prefix(r["permit_number_displayed"])])
            # PHASE 2: check attachment grids (separate context)
            actx = browser.new_context(viewport={"width": 1400, "height": 900},
                                       user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            found = None
            for r in cands[:CAP]:
                url = r.get("href") or ""
                if url and not url.startswith("http"):
                    url = "https://aca-prod.accela.com" + url
                if not url:
                    continue
                has_sr, fn, ntot = check_attachments(actx, url)
                if has_sr:
                    found = (r["permit_number_displayed"], fn)
                    break
                time.sleep(random.uniform(1.0, 2.5))
            actx.close()
            row = {"project_id": pid, "address": pr.address, "units": pr.units,
                   "n_records": len(recs), "n_sr_candidates": len(cands),
                   "has_staff_report": bool(found), "sr_record": found[0] if found else "",
                   "sr_filename": found[1] if found else ""}
            results.append(row)
            state["done"][str(pid)] = True
            state["rows"] = results
            json.dump(state, open(STATE, "w"))
            pd.DataFrame(results).to_csv(OUT, index=False)
            print(f"proj{pid} {pr.address}: {len(recs)} recs, staff report={'YES '+found[0] if found else 'no'}")
            time.sleep(random.uniform(2, 5))
    finally:
        browser.close(); p.stop()

    df = pd.DataFrame(results)
    df.to_csv(OUT, index=False)
    n = len(df); hit = int(df.has_staff_report.sum())
    print(f"\n{'#'*60}\nSIZING: {hit}/{n} of the no-height placeholders have a readable DRC staff report ({100*hit//max(1,n)}%)")


if __name__ == "__main__":
    main()
