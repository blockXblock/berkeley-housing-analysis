#!/usr/bin/env python3
"""harvest_plansets_batch2.py — plan-set harvest for the BIG multi-parcel projects from the
2026-08-23 harvest-priority list (data/reference/harvest_priority_plansets.csv).

Reuses experiments/accela_scrape/harvest_plansets.py's PROVEN engine VERBATIM (import, don't
fork): discover -> CapDetail -> attachments grid -> paginate -> classify -> expect_download.

TARGET = the PLANNING (ZP) entitlement record, NOT the Building permit. Verified 2026-08-23:
the architect "Project Plans" set (incl. the zoning-tabulation / footprint page) is attached to
the ZP record; the construction Building permit's attachments grid is EMPTY in the public ACA
portal (checked 1951 Shattuck B2021-04893 -> 0 rows). So we harvest the ZP records for which we
already hold a ZP number in v2. Records are DERIVED from the CSV (zoning_records column), not
hardcoded. harvest_record discovers each ZP in the Planning module and its own ZP-gate guards it.

The 12 projects whose plan sets sit on a Building permit / whose ZP number we do NOT yet hold
need the ZP discovered first (Planning address search is currently broken; phase 2).

NOTHING irreversible: downloads + hashes + local staging + a manifest CSV. No R2, no v2 write.
The R2 upload + v2 ingest is a SEPARATE gated step after John reviews the manifest.

Resumable (state.json records completed permits). Polite (5-15s between records). Run:
  .venv/bin/python scripts/harvest_plansets_batch2.py                 # all ZP-known projects
  .venv/bin/python scripts/harvest_plansets_batch2.py --only 27,12    # subset by project id
"""
import sys, os, time, random, argparse, re
import pandas as pd

sys.path.insert(0, "experiments/accela_scrape")
import harvest_plansets as H   # the proven engine

# stage under scratch/ (reboot-surviving) — override the engine's /tmp constants
STAGE = "scratch/2026-08-23/harvest_stage_batch2"
H.STAGE = STAGE
H.STATE = f"{STAGE}/state.json"
H.MANIFEST = f"{STAGE}/manifest.csv"

CSV = "data/reference/harvest_priority_plansets.csv"
ZP = re.compile(r"\b(?:ZP|UP|DRCP|DRCF|LMSAP)\d{4}-\d{3,4}\b", re.I)


def build_records():
    """Derive the harvest record list from the CSV: every non-UC project that carries a ZP
    (Planning) record number. First ZP per project. NOT hardcoded — reflects the CSV."""
    df = pd.read_csv(CSV)
    recs = []
    for _, r in df.iterrows():
        if r.get("is_uc"):
            continue
        z = str(r.get("zoning_records") or "")
        m = ZP.findall(z)
        if not m:
            continue
        recs.append(dict(proj=int(r.project_id), permit=m[0].upper(),
                         addr=str(r.address).title(), units=int(r.units)))
    # de-dup by project (a project appears once per footprint row in the CSV)
    seen, out = set(), []
    for rec in sorted(recs, key=lambda x: -x["units"]):
        if rec["proj"] in seen:
            continue
        seen.add(rec["proj"]); out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated project ids (default: all)")
    a = ap.parse_args()
    only = {int(x) for x in a.only.split(",") if x.strip()} if a.only else None

    os.makedirs(STAGE, exist_ok=True)
    sha_set, stubs = H.load_v2()
    st = H.load_state()
    done = set(st["completed"])

    recs = [r for r in build_records() if (only is None or r["proj"] in only)]
    print(f"harvesting {len(recs)} ZP(Planning) record(s); stage={STAGE}")
    for i, rec in enumerate(recs):
        if rec["permit"] in done:
            print(f"\n=== proj{rec['proj']} {rec['permit']} — already done, resume-skip ===")
            continue
        print(f"\n{'='*70}\nproj{rec['proj']} {rec['permit']} ({rec['addr']}, {rec['units']}u)\n{'='*70}")
        try:
            rr = H.harvest_record(rec, sha_set, stubs)   # native Planning discovery + ZP gate
        except Exception as e:
            rr = [dict(status="FAILED-exception", project_id=rec["proj"], permit_number=rec["permit"],
                       filename="", file_size_mib="", page_count="", classifier_reason=str(e)[:80],
                       grid_displayed_size="", sha256="", suggested_r2_key="", existing_stub_doc_id="", local_path="")]
        st["rows"].extend(rr)
        st["completed"].append(rec["permit"])
        H.save_state(st)
        H.write_manifest(st["rows"])
        if i < len(recs) - 1:
            dly = random.uniform(5, 15)
            print(f"  ...polite delay {dly:.1f}s")
            time.sleep(dly)

    ordered, deviates = H.write_manifest(st["rows"])
    staged = [r for r in st["rows"] if r["status"] == "STAGED-OK"]
    failed = [r for r in st["rows"] if r["status"].startswith("FAILED") or r["status"] == "DISCOVERY-FAILED"]
    noplan = [r for r in st["rows"] if r["status"] == "NO-PLANSETS"]
    skipnzp = [r for r in st["rows"] if r["status"] == "SKIP-NOT-ZP-PLANNING"]
    total_gb = sum(r["file_size_mib"] for r in staged if r["file_size_mib"]) * H.MIB / 1e9
    print(f"\n{'#'*70}\nHARVEST SUMMARY (batch2 / Planning)\n{'#'*70}")
    print(f"  staged-ok: {len(staged)}  failed/no-capid: {len(failed)}  no-plansets: {len(noplan)}  "
          f"not-zp: {len(skipnzp)}  total: {total_gb:.2f} GB\n  manifest: {H.MANIFEST}")
    for r in staged:
        print(f"    STAGED proj{r['project_id']} {r['file_size_mib']}MiB p{r['page_count']}  {r['filename'][:46]}")
    for r in failed + noplan + skipnzp:
        print(f"    {r['status']} proj{r['project_id']} {r['permit_number']}")


if __name__ == "__main__":
    main()
