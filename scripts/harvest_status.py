#!/usr/bin/env python3
"""harvest_status.py — Accela STATUS harvest for the status_label reconciliation (2026-08-27).

For each target project: address-search the Building AND Planning modules, load every record's CapDetail,
and extract Record Status / Record Type / Description / key dates. Read-only on Accela; writes only a
structured CSV that we then adjudicate against v2 status_label (the v2 write is a separate gated step).

Reuses the proven harvester machinery: harvest_address.search_by_address (postback + pagination, the
2026-08-23 Planning date-skip fix) + url_discovery_scraper._extract_field_from_capdetail.

Resumable (per-project state), polite (randomised delays). Run in the project .venv:
  .venv/bin/python scripts/harvest_status.py --ids 146,139,160,94
  .venv/bin/python scripts/harvest_status.py --ids-file scratch/2026-08-27/nonterminal_ids.txt
"""
import sys, os, re, json, time, random, argparse, sqlite3
import pandas as pd

sys.path.insert(0, "experiments/accela_scrape")
from harvest_address import search_by_address
from url_discovery_scraper import _extract_field_from_capdetail
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

DB = "databases/berkeley_housing_v2.db"
OUT = "data/reference/status_harvest_2026-08-27.csv"
STATE = "scratch/2026-08-27/status_harvest_state.json"
SUFFIXES = {"AVE", "ST", "WAY", "BLVD", "DR", "RD", "LN", "CT", "PL", "TER", "SQ", "CIR", "PATH",
            "WALK", "PKWY", "AVENUE", "STREET", "PLZ", "ROW"}
CAP_RECORDS = 8          # max CapDetail loads per project (politeness)
DATE_LABELS = {"applied": ["Applied Date", "Application Date", "File Date", "Opened Date"],
               "issued": ["Issued Date", "Issue Date"],
               "finaled": ["Finaled Date", "Completed Date", "Final Date", "Closed Date"]}


def parse_addr(addr):
    toks = str(addr).upper().split()
    if not toks or not toks[0][0].isdigit():
        return None, str(addr)
    rest = toks[1:]
    if rest and rest[-1] in SUFFIXES:
        rest = rest[:-1]
    return re.sub(r"\D", "", toks[0]), " ".join(rest)


def capdetail_status(ctx, url):
    """Load a record's CapDetail; parse Record Status / Type / description / dates from the page text.
    Accela renders 'Record Status:\\xa0<value>' on one line (nbsp after the colon); the record type is
    the line immediately above it (verified 2026-08-27 on DRCF2026-0003)."""
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        time.sleep(1.2)
        txt = page.inner_text("body").replace("\xa0", " ")

        def grab(*pats):
            for p in pats:
                m = re.search(p, txt, re.I)
                if m and m.group(1).strip():
                    return m.group(1).strip()
            return None

        lines = [l.strip() for l in txt.splitlines() if l.strip()]
        rtype = None
        for i, l in enumerate(lines):
            if l.lower().startswith("record status:"):
                rtype = lines[i - 1] if i > 0 else None
                break
        return {
            "record_status": grab(r"Record Status:\s*([^\n]+)"),
            "record_type": rtype,
            "description": (grab(r"Project Description:\s*([^\n]+)", r"Description:\s*([^\n]+)") or "")[:180],
            "applied": grab(r"Applied Date:\s*([^\n]+)", r"File Date:\s*([^\n]+)", r"Opened Date:\s*([^\n]+)"),
            "issued": grab(r"Issued Date:\s*([^\n]+)", r"Issue Date:\s*([^\n]+)"),
            "finaled": grab(r"Finaled Date:\s*([^\n]+)", r"Completed Date:\s*([^\n]+)", r"Closed Date:\s*([^\n]+)"),
        }
    except Exception as e:
        return {"record_status": f"ERR {str(e)[:40]}", "record_type": None, "description": "",
                "applied": None, "issued": None, "finaled": None}
    finally:
        page.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="comma-separated project_ids")
    ap.add_argument("--ids-file", help="file with one project_id per line")
    a = ap.parse_args()
    ids = []
    if a.ids:
        ids += [int(x) for x in a.ids.split(",") if x.strip()]
    if a.ids_file and os.path.exists(a.ids_file):
        ids += [int(l) for l in open(a.ids_file) if l.strip().isdigit()]
    if not ids:
        raise SystemExit("give --ids or --ids-file")

    v = sqlite3.connect(DB)
    q = f"SELECT project_id, address_display, total_units, status_label FROM v_projects_flat WHERE project_id IN ({','.join(map(str,ids))})"
    targets = pd.read_sql(q, v)
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"done": {}, "rows": []}
    rows = state["rows"]

    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    try:
        for _, pr in targets.iterrows():
            pid = int(pr.project_id)
            if str(pid) in state["done"]:
                print(f"proj{pid} done, skip"); continue
            no, name = parse_addr(pr.address_display)
            print(f"\n{'='*66}\nproj{pid} {pr.address_display} ({pr.total_units}u) v2='{pr.status_label}' -> search '{no} {name}'")
            recs = []
            for module in ("Building", "Planning"):
                sctx = browser.new_context(viewport={"width": 1400, "height": 900},
                                           user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
                sp = sctx.new_page()
                try:
                    r = search_by_address(sp, name, no, module=module, errors=[]).get("records", [])
                    for x in r:
                        x["module"] = module
                    recs += r
                except Exception as e:
                    print(f"  {module} search error: {str(e)[:50]}")
                finally:
                    sctx.close()
                time.sleep(random.uniform(1.0, 2.0))
            print(f"  {len(recs)} records across Building+Planning; loading up to {CAP_RECORDS} CapDetails")
            actx = browser.new_context(viewport={"width": 1400, "height": 900},
                                       user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            for r in recs[:CAP_RECORDS]:
                url = r.get("href") or ""
                if url and not url.startswith("http"):
                    url = "https://aca-prod.accela.com" + url
                if not url:
                    continue
                d = capdetail_status(actx, url)
                row = {"project_id": pid, "address": pr.address_display, "units": pr.total_units,
                       "v2_status": pr.status_label, "module": r.get("module"),
                       "permit": r.get("permit_number_displayed"), **d}
                rows.append(row)
                print(f"    {r.get('permit_number_displayed',''):<16} [{r.get('module')}] status={d['record_status']}  {d['description'][:44]}")
                time.sleep(random.uniform(1.2, 2.8))
            actx.close()
            state["done"][str(pid)] = True
            state["rows"] = rows
            json.dump(state, open(STATE, "w"), indent=1)
            pd.DataFrame(rows).to_csv(OUT, index=False)
            time.sleep(random.uniform(2, 4))
    finally:
        browser.close(); p.stop()

    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"\n{'#'*66}\nSTATUS HARVEST -> {OUT}  ({len(df)} records, {df.project_id.nunique()} projects)")


if __name__ == "__main__":
    main()
