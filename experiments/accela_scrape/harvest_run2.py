"""
Harvest run 2 — the 12 harvest-ready non-UC >200-unit projects.

Reuses harvest_plansets.py's engine VERBATIM (import + call harvest_record per record).
This driver only adds: the new 12-record list, the /tmp/harvest_stage_2 dir, and
multi-permit retry (proj 4 & 6: try permit 1, fall back to permit 2 if it yields no
plan-set grid). proj2 uses ONLY the clean permit ZP2024-0067 (v2 also has a corrupt
ZP2023-00401974 — NOT written/fixed here; reported for John).

Discipline (inherited from harvest_plansets): jitter 5-15s between records, 0.8-2.5s
between page turns, STOP on captcha/auth/redirect, per-record cap 8, resumable state.json,
sha256 dedup vs v2.documents. /tmp only; no R2/v2/commit.
"""
import sys, os, time, random
sys.path.insert(0, "experiments/accela_scrape")
import harvest_plansets as H

# redirect all outputs to run-2 dir (engine reads these module globals)
H.STAGE = "/tmp/harvest_stage_2"
H.STATE = f"{H.STAGE}/state.json"
H.MANIFEST = f"{H.STAGE}/manifest.csv"

RECORDS = [
    dict(proj=35,  permits=["ZP2025-0101"],               addr="2190 Shattuck"),
    dict(proj=152, permits=["ZP2022-0011"],               addr="1598 University"),
    dict(proj=119, permits=["ZP2023-0040"],               addr="1974 Shattuck"),
    dict(proj=3,   permits=["ZP2024-0058"],               addr="2700 Shattuck"),
    dict(proj=2,   permits=["ZP2024-0067"],               addr="2276 Shattuck"),   # clean only
    dict(proj=120, permits=["ZP2023-0079"],               addr="2274 Shattuck"),
    dict(proj=4,   permits=["ZP2020-0104", "ZP2022-0058"], addr="1914 Fifth"),
    dict(proj=6,   permits=["ZP2024-0181", "ZP2024-0182"], addr="2029 University"),
    dict(proj=179, permits=["ZP2018-0135"],               addr="2352 Shattuck"),
    dict(proj=7,   permits=["ZP2022-0171"],               addr="2601 San Pablo"),
    dict(proj=8,   permits=["ZP2022-0116"],               addr="2920 Shattuck"),
    dict(proj=121, permits=["ZP2023-0163"],               addr="2100 Milvia"),
]


def staged_or_dedup(rows):
    return any(r["status"] in ("STAGED-OK", "SKIPPED-DEDUP") for r in rows)


def main():
    os.makedirs(H.STAGE, exist_ok=True)
    sha_set, stubs = H.load_v2()
    st = H.load_state()
    done = set(st["completed"])
    for i, rec in enumerate(RECORDS):
        key = str(rec["proj"])
        if key in done:
            print(f"\n=== proj{rec['proj']} — resume-skip ===")
            continue
        print(f"\n{'='*70}\nproj{rec['proj']} {rec['addr']} (permits {rec['permits']})\n{'='*70}")
        rows = None
        used = None
        for permit in rec["permits"]:
            single = dict(proj=rec["proj"], permit=permit, addr=rec["addr"])
            try:
                rr = H.harvest_record(single, sha_set, stubs)
            except Exception as e:
                rr = [dict(status="FAILED-exception", project_id=rec["proj"], permit_number=permit,
                           filename="", file_size_mib="", page_count="", classifier_reason=str(e)[:80],
                           grid_displayed_size="", sha256="", suggested_r2_key="",
                           existing_stub_doc_id="", local_path="")]
            used = permit
            rows = rr
            if staged_or_dedup(rr) or len(rec["permits"]) == 1:
                break
            print(f"  permit {permit} yielded no plan-set grid; trying next permit...")
            time.sleep(random.uniform(5, 15))
        # tag which permit resolved
        for r in rows:
            r.setdefault("permit_number", used)
        print(f"  -> resolved permit: {used}")
        st["rows"].extend(rows)
        st["completed"].append(key)
        H.save_state(st)
        H.write_manifest(st["rows"])
        if i < len(RECORDS) - 1:
            dly = random.uniform(5, 15)
            print(f"  ...polite delay {dly:.1f}s")
            time.sleep(dly)

    ordered, deviates = H.write_manifest(st["rows"])
    staged = [r for r in st["rows"] if r["status"] == "STAGED-OK"]
    failed = [r for r in st["rows"] if r["status"].startswith("FAILED")]
    dedup = [r for r in st["rows"] if r["status"] == "SKIPPED-DEDUP"]
    stops = [r for r in st["rows"] if r["status"].startswith("STOP")]
    noplan = [r for r in st["rows"] if r["status"] == "NO-PLANSETS"]
    total_gb = sum(r["file_size_mib"] for r in staged if r["file_size_mib"]) * H.MIB / 1e9
    look = ([("FAILED", r) for r in failed] + [("STOP", r) for r in stops]
            + [("SIZE-DEV", r) for r in staged if deviates(r)]
            + [("ODD-KW", r) for r in staged
               if not any(k in r["classifier_reason"] for k in H.CLEAN_KW)])
    print(f"\n{'#'*70}\nHARVEST RUN 2 SUMMARY\n{'#'*70}")
    print(f"  staged-ok: {len(staged)}  failed: {len(failed)}  deduped: {len(dedup)}  "
          f"STOPs: {len(stops)}  no-plansets: {len(noplan)}")
    print(f"  total staged size: {total_gb:.2f} GB")
    print(f"  manifest: {H.MANIFEST}")
    by_proj = {}
    for r in staged:
        by_proj.setdefault(r["project_id"], 0)
        by_proj[r["project_id"]] += 1
    print(f"  staged per project: {dict(sorted(by_proj.items(), key=lambda x: str(x[0])))}")
    if noplan:
        print(f"  NO-PLANSETS projects: {sorted({r['project_id'] for r in noplan}, key=str)}")
    print(f"  LOOK TWICE ({len(look)}):")
    for tag, r in look:
        print(f"    [{tag}] proj{r['project_id']} {r['filename'][:44]} "
              f"({r['file_size_mib']}MiB vs {r['grid_displayed_size']}) {r['classifier_reason']}")
    if not look:
        print("    (none)")


if __name__ == "__main__":
    main()
