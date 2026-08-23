#!/usr/bin/env python3
"""harvest_by_record.py — fetch plan sets + tabulation forms for an EXPLICIT record queue.

Phase-2 harvester. Reads a queue CSV (project_id, permit, address, module) and, for each record,
discovers its CapDetail in the right module, enumerates the attachment grid, and downloads the
plan/tabulation PDFs. Uses harvest_plansets.py's proven engine via the href path uniformly (works
for ZP / UP / DRCP / DRCF AND Building permits — the ZP-only gate is bypassed, the permit-label
assert still guards).

Two things this adds over harvest_plansets_batch2.py, WITHOUT editing the shared engine file:
  1. Own STAGE dir (scratch/2026-08-23/harvest_stage_phase2) so it can run alongside the geometry
     session's concurrent batch2 run without colliding on state/manifest.
  2. A TABULATION branch (default ON): the stock classifier needs a plan keyword AND >5MiB, so it
     skips a standalone "1.E" Tabulation Form (~176KB). We monkeypatch classify IN THIS PROCESS ONLY
     to also accept title/filename matching the tabulation pattern (1.E / tabulation) with no size
     floor. Does not touch the file, does not affect any other run.

NOTHING irreversible: downloads + hashes + local staging + a manifest. No R2, no v2 write (separate
gated step). Resumable, polite (5-15s between records). Run in .venv:
  .venv/bin/python scripts/harvest_by_record.py --csv scratch/2026-08-23/phase2_batchA_queue.csv
"""
import sys, os, time, random, argparse, re
import pandas as pd

sys.path.insert(0, "experiments/accela_scrape")
import harvest_plansets as H
from url_discovery_scraper import discover_url

STAGE = "scratch/2026-08-23/harvest_stage_phase2"
H.STAGE = STAGE
H.STATE = f"{STAGE}/state.json"
H.MANIFEST = f"{STAGE}/manifest.csv"

TAB_RE = re.compile(r"1\.E|tabulation", re.I)


def enable_tabulation_branch():
    """Monkeypatch H.classify (this process only) to also stage 1.E / tabulation forms, no size floor."""
    _orig = H.classify
    def classify(fn, size_bytes):
        ok, kw, reason = _orig(fn, size_bytes)
        if ok:
            return ok, kw, reason
        if TAB_RE.search(fn or ""):
            mib = f" +{size_bytes/H.MIB:.2f}MiB" if size_bytes else ""
            return (True, "tabulation", f"tabulation form{mib}")
        return ok, kw, reason
    H.classify = classify


def resolve_href(permit, module):
    d = discover_url(permit, module_hint=module, headless=True, max_runtime_seconds=120)
    if not d.get("found") or not d.get("master"):
        return None
    return d["master"]["capdetail_url"].replace("https://aca-prod.accela.com", "", 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="queue CSV: project_id,permit,address,module")
    ap.add_argument("--only", default="", help="comma-separated project ids (default: all)")
    ap.add_argument("--no-tabulation", action="store_true", help="disable the 1.E/tabulation branch")
    a = ap.parse_args()
    only = {int(x) for x in a.only.split(",") if x.strip()} if a.only else None
    if not a.no_tabulation:
        enable_tabulation_branch()

    q = pd.read_csv(a.csv)
    if only is not None:
        q = q[q.project_id.isin(only)]

    os.makedirs(STAGE, exist_ok=True)
    sha_set, stubs = H.load_v2()
    st = H.load_state()
    done = set(st["completed"])

    print(f"harvesting {len(q)} record(s); stage={STAGE}; tabulation={'off' if a.no_tabulation else 'ON'}")
    recs = list(q.itertuples(index=False))
    for i, row in enumerate(recs):
        permit = str(row.permit).strip()
        module = str(getattr(row, "module", "") or ("Building" if permit[:1] == "B" else "Planning")).strip()
        rec = dict(proj=int(row.project_id), permit=permit, addr=str(row.address))
        if permit in done:
            print(f"\n=== proj{rec['proj']} {permit} — done, skip ==="); continue
        print(f"\n{'='*70}\nproj{rec['proj']} {permit} ({rec['addr']}) [{module}]\n{'='*70}")
        href = resolve_href(permit, module)
        if href is None:
            print("  discovery failed; single retry..."); time.sleep(random.uniform(5, 10))
            href = resolve_href(permit, module)
        if href is None:
            rr = [dict(status="DISCOVERY-FAILED", project_id=rec["proj"], permit_number=permit,
                       filename="", file_size_mib="", page_count="", classifier_reason="0 capID after retry",
                       grid_displayed_size="", sha256="", suggested_r2_key="", existing_stub_doc_id="", local_path="")]
        else:
            rec["href"] = href
            try:
                rr = H.harvest_record(rec, sha_set, stubs)
            except Exception as e:
                rr = [dict(status="FAILED-exception", project_id=rec["proj"], permit_number=permit,
                           filename="", file_size_mib="", page_count="", classifier_reason=str(e)[:80],
                           grid_displayed_size="", sha256="", suggested_r2_key="", existing_stub_doc_id="", local_path="")]
        st["rows"].extend(rr)
        st["completed"].append(permit)
        H.save_state(st)
        H.write_manifest(st["rows"])
        if i < len(recs) - 1:
            dly = random.uniform(5, 15)
            print(f"  ...polite delay {dly:.1f}s"); time.sleep(dly)

    H.write_manifest(st["rows"])
    staged = [r for r in st["rows"] if r["status"] == "STAGED-OK"]
    tabs = [r for r in staged if "tabulation" in r.get("classifier_reason", "")]
    failed = [r for r in st["rows"] if r["status"].startswith("FAILED") or r["status"] == "DISCOVERY-FAILED"]
    noplan = [r for r in st["rows"] if r["status"] == "NO-PLANSETS"]
    total_gb = sum(r["file_size_mib"] for r in staged if r["file_size_mib"]) * H.MIB / 1e9
    print(f"\n{'#'*70}\nHARVEST SUMMARY (phase2 by-record)\n{'#'*70}")
    print(f"  staged: {len(staged)} (of which tabulation forms: {len(tabs)})  failed/no-capid: {len(failed)}  "
          f"no-plansets: {len(noplan)}  total: {total_gb:.2f} GB\n  manifest: {H.MANIFEST}")
    for r in staged:
        tag = "TAB" if "tabulation" in r.get("classifier_reason", "") else "PLN"
        print(f"    {tag} proj{r['project_id']} {r['permit_number']} {r['file_size_mib']}MiB p{r['page_count']}  {r['filename'][:40]}")
    for r in failed + noplan:
        print(f"    {r['status']} proj{r['project_id']} {r['permit_number']}")


if __name__ == "__main__":
    main()
