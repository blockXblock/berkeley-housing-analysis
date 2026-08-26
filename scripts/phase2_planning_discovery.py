#!/usr/bin/env python3
"""phase2_planning_discovery.py — READ-ONLY discovery map: for each phase-2 project (big multi-parcel,
not yet harvested), address-search the Planning module and, for each plan-bearing candidate record,
count the architect-plan attachments — so we know WHICH Planning record to harvest per project.

NOTHING downloaded, no R2, no DB write. Just: address -> candidate Planning records -> per-record
attachment summary (how many plan-keyword files >=5MiB, the largest). Output a ranked map to
data/reference/phase2_planning_discovery.csv.

Uses the 2026-08-23 Planning address-search fix (harvest_address.py) + harvest_plansets.py's attachment
engine. Resumable (per-project). Polite (delays between record loads + projects). Run in the .venv:
  .venv/bin/python scripts/phase2_planning_discovery.py
"""
import sys, os, time, re, json, random
import pandas as pd

sys.path.insert(0, "experiments/accela_scrape")
import harvest_plansets as H
from harvest_address import search_by_address   # takes a page — no nested sync_playwright
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

CSV_IN = "data/reference/harvest_priority_plansets.csv"
OUT = "data/reference/phase2_planning_discovery.csv"
STATE = "scratch/2026-08-23/phase2_discovery_state.json"
HARVESTED = {20, 22, 27, 114}   # already have plan sets

# street suffixes to strip so the search gets just the street NAME (the fixed search wants no suffix)
SUFFIXES = {"AVE", "ST", "WAY", "SQ", "BLVD", "DR", "RD", "LN", "CT", "PL", "TER", "CIR",
            "PATH", "WALK", "PKWY", "PLZ", "ROW", "AVENUE", "STREET"}
# record-type prefixes that carry architect plan sets, in harvest-priority order
PLAN_PREFIX_RANK = {"ZP": 0, "UP": 1, "AUP": 1, "DRCP": 2, "DRCF": 2, "LMSAP": 3, "DRSA": 4, "PLN": 5}
CAP_CANDIDATES = 5          # max attachment-grid loads per project (politeness)


def parse_addr(addr):
    toks = str(addr).upper().split()
    if not toks or not toks[0][0].isdigit():
        return None, str(addr)
    no = re.sub(r"\D", "", toks[0])
    rest = toks[1:]
    if rest and rest[-1] in SUFFIXES:
        rest = rest[:-1]
    return no, " ".join(rest)


def prefix(permit):
    m = re.match(r"([A-Z]+)", permit or "")
    return m.group(1) if m else ""


def year(permit):
    m = re.search(r"(\d{4})", permit or "")
    return int(m.group(1)) if m else 0


def attach_summary(ctx, url):
    """Load a CapDetail attachments grid; return (n_plan_files, largest_plan_mib, n_total, sample)."""
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        if page.evaluate("""() => {const a=document.querySelector('a[data-control="tab-attachments"]');
            if(!a||typeof handlePortletNavigation!=='function')return 'no'; handlePortletNavigation(a);return 'ok';}""") != "ok":
            return (0, 0.0, 0, "")
        time.sleep(2.5)
        fr = page.wait_for_selector(f"#{H.IFRAME_ID}", state="attached", timeout=25000).content_frame()
        try:
            fr.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeout:
            pass
        time.sleep(1.5)
        rows = []
        for _ in range(12):
            rows = H.read_rows(fr)
            if rows:
                break
            time.sleep(1.0)
        n_plan, largest, sample = 0, 0.0, ""
        for r in rows:
            sb = H.grid_size_bytes(r["rowtext"])
            ok, kw, _ = H.classify(r["filename"], sb)
            if ok:
                n_plan += 1
                mib = (sb or 0) / H.MIB
                if mib > largest:
                    largest, sample = mib, r["filename"]
        return (n_plan, round(largest, 1), len(rows), sample[:54])
    except Exception as e:
        return (-1, 0.0, 0, f"ERR {str(e)[:40]}")
    finally:
        page.close()


def main():
    df = pd.read_csv(CSV_IN)
    projs = (df[(~df.is_uc) & (~df.project_id.isin(HARVESTED))]
             .drop_duplicates("project_id").sort_values("units", ascending=False))

    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"done": {}}
    results = state.get("rows", [])

    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(accept_downloads=False, viewport={"width": 1400, "height": 900},
                              user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    try:
        for _, pr in projs.iterrows():
            pid = int(pr.project_id)
            if str(pid) in state["done"]:
                print(f"proj{pid} — done, skip"); continue
            no, name = parse_addr(pr.address)
            print(f"\n{'='*66}\nproj{pid} {pr.address} ({int(pr.units)}u) -> search Planning '{no} {name}'")
            spage = ctx.new_page()
            try:
                res = search_by_address(spage, name, no, module="Planning", errors=[])
                recs = res.get("records", [])
            except Exception as e:
                recs = []; print(f"  search error: {str(e)[:60]}")
            finally:
                spage.close()
            # rank plan-bearing candidates: by type priority then newest
            cands = [r for r in recs if prefix(r.get("permit_number_displayed", "")) in PLAN_PREFIX_RANK]
            cands.sort(key=lambda r: (PLAN_PREFIX_RANK[prefix(r["permit_number_displayed"])],
                                      -year(r["permit_number_displayed"])))
            print(f"  {len(recs)} records, {len(cands)} plan-bearing; checking up to {CAP_CANDIDATES}")
            proj_rows = []
            for r in cands[:CAP_CANDIDATES]:
                permit = r["permit_number_displayed"]
                url = r.get("href") or ""
                if url and not url.startswith("http"):
                    url = "https://aca-prod.accela.com" + url
                npl, largest, ntot, sample = attach_summary(ctx, url) if url else (0, 0, 0, "no-href")
                print(f"    {permit:<14} plan_files={npl} largest={largest}MiB total={ntot}  {sample}")
                proj_rows.append(dict(project_id=pid, address=pr.address, units=int(pr.units),
                                      candidate=permit, plan_files=npl, largest_plan_mib=largest,
                                      total_attach=ntot, sample=sample))
                time.sleep(random.uniform(1.5, 3.5))
            if not proj_rows:
                proj_rows.append(dict(project_id=pid, address=pr.address, units=int(pr.units),
                                      candidate="", plan_files=0, largest_plan_mib=0,
                                      total_attach=0, sample=f"{len(recs)} records, 0 plan-bearing"))
            results.extend(proj_rows)
            state["done"][str(pid)] = True
            state["rows"] = results
            json.dump(state, open(STATE, "w"), indent=2)
            pd.DataFrame(results).to_csv(OUT, index=False)
            time.sleep(random.uniform(3, 7))
    finally:
        ctx.close(); browser.close(); p.stop()

    # summary: best candidate per project (most plan files, then largest)
    out = pd.DataFrame(results)
    out.to_csv(OUT, index=False)
    print(f"\n{'#'*66}\nDISCOVERY MAP -> {OUT}")
    best = (out[out.plan_files > 0].sort_values(["project_id", "plan_files", "largest_plan_mib"],
                                                ascending=[True, False, False])
            .drop_duplicates("project_id"))
    print(f"projects with a harvestable plan-set record: {best.project_id.nunique()} / {out.project_id.nunique()}")
    for _, r in best.sort_values("units", ascending=False).iterrows():
        print(f"  proj{int(r.project_id):<4} {r.address:<20} -> {r.candidate:<14} "
              f"{int(r.plan_files)} plan file(s), largest {r.largest_plan_mib}MiB")
    nohit = sorted(set(out.project_id) - set(best.project_id))
    print(f"  no plan-set record found: {len(nohit)} -> {nohit}")


if __name__ == "__main__":
    main()
