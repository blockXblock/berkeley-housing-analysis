#!/usr/bin/env python3
# ============================ SEQUESTERED 2026-09-26 ============================
# DO NOT RUN. Original path: scripts/jev_stage_classify.py
# WHY: Model inference of a project's pipeline stage. Superseded for rungs 1-4 of the ~1,746 housing Planning records by the city's own CapDetail workflow facts (harvest by berkeley-data-32, NOT yet ingested as of 2026-09-26). NOT superseded for construction/inspection/CO rungs, pre-applications (they publish no workflow), or the ADU/infill tail: stage is NOT solved.
raise SystemExit("SEQUESTERED 2026-09-26 -- see header; original path scripts/jev_stage_classify.py")
# ================================================================================
"""jev_stage_classify.py — assign each project a pipeline stage using TypeSafe's `jev` classifier.

WHY JEV RATHER THAN A GENERAL MODEL. `llm-typesafe` (Simon Willison, 0.1a0) exposes a model built
for classification and scoring, with three answer types: `noul` (probability of yes), `choice` (one
category) and `score` ("a degree on ordered levels"). John's pipeline is a LADDER, not a set of
unrelated labels -- pre-application < in review < entitled < permitted < under construction <
completed -- so `score` fits it better than `choice`, which would throw the ordering away.

Two further reasons it suits this problem specifically:
  * `input_format=json` lets us hand it STRUCTURED permit fields rather than prose. Every regex
    defect on 2026-09-25 came from reading an Accela description -- narrative appended over time,
    dated log lines, trailing contractor notes -- as though it were a field.
  * `criteria` makes the rung definitions explicit and versionable, instead of buried in a prompt.

EVIDENCE, NOT JUST A LABEL. The stage is derived from cited permit numbers wherever possible, so a
wrong answer shows up as a wrong CITATION rather than an unfalsifiable label. That is what makes the
output gateable on the same terms as any other write, and it is what would have caught the one
genuine model error in the 75-project blind test, where a verdict contradicted its own reason.

STATUS: needs a TypeSafe API key (`llm keys set typesafe`). Without one this runs --dry-run and
prints exactly what it would send.

Usage:
  python scripts/jev_stage_classify.py --dry-run          # show the payload for a few projects
  python scripts/jev_stage_classify.py --limit 75         # run once a key exists
"""
import argparse
import collections
import glob
import json
import re
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scratch/2026-09-25/jev_stage"

# Ordered rungs. `score` returns a degree along these, so ORDER IS LOAD-BEARING.
LEVELS = [
    "Pre-application only: informal enquiry, pre-application meeting or zoning research letter. No formal application has been filed.",
    "Application filed and under review: a planning application (ZP/PLN/UP) exists and is in review, incomplete, or awaiting documents. No approval yet.",
    "Entitled: a planning approval has been granted (status Approved or Approved w/Conditions on a zoning permit or use permit). No building permit issued.",
    "Permitted: a building permit for the housing itself has been ISSUED, but no construction has been observed and nothing has been finaled.",
    "Under construction: inspections are occurring on the housing building permit, or phase permits are issued and active, but the housing permit is not finaled.",
    "Completed: the building permit FOR THE HOUSING ITSELF has been Finaled. Note carefully: a finaled demolition permit, parking-lot permit, solar permit or restaurant tenant-improvement is NOT a housing completion.",
]

SYSTEM = ("How far along the housing-development pipeline is the specific proposed project at this "
          "site? Judge the PROPOSED DEVELOPMENT, not the site: an existing building being altered "
          "does not make the proposal complete.")


def key(a):
    a = re.sub(r",.*$", "", str(a or "").upper())
    p = re.sub(r"[^A-Z0-9 ]", " ", a).split()
    return (p[0], p[1]) if len(p) > 1 and p[0].isdigit() else None


def gather(limit=None):
    db = sqlite3.connect(f"file:{ROOT/'databases/berkeley_housing_v2.db'}?mode=ro", uri=True)
    proj = [(p, u or 0, a, s) for p, u, a, s in db.execute(
        """SELECT project_id, total_units, address_display, status_code FROM v_projects_flat
           WHERE address_display IS NOT NULL ORDER BY total_units DESC""")]
    if limit:
        proj = proj[:limit]
    want = {}
    for p, u, a, s in proj:
        k = key(a)
        if k:
            want.setdefault(k, []).append(p)
    recs = collections.defaultdict(list)
    seen = collections.defaultdict(set)
    for mod in ("Building", "Planning"):
        for fn in glob.glob(str(ROOT / f"data/raw/accela/date_range/{mod}_*.jsonl")):
            for line in open(fn):
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                num = (d.get("Permit Number") or d.get("Record Number") or "").strip()
                if not num or re.match(r"^\d{2}TMP", num):
                    continue
                k = key((d.get("_cells") or [""])[-1])
                if k in want:
                    for p in want[k]:
                        if num in seen[p]:
                            continue
                        seen[p].add(num)
                        recs[p].append({
                            "record": num, "module": mod, "date": d.get("Date", ""),
                            "status": (d.get("Status") or "").strip(),
                            "work": (d.get("Description") or "").strip()[:280],
                        })
    return proj, recs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", type=int, default=2)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    proj, recs = gather(args.limit)
    print(f"  projects: {len(proj):,}   records gathered: {sum(len(v) for v in recs.values()):,}")

    if args.dry_run:
        crit = json.dumps(LEVELS)
        print(f"\n  answer_type : score   ({len(LEVELS)} ordered levels)")
        print(f"  system      : {SYSTEM[:96]}…")
        print(f"  criteria    : {len(crit):,} chars of ordered level definitions")
        print(f"\n  the CLI call, per project:\n")
        print("    llm -m jev -o answer_type score -o input_format json \\")
        print("        -o criteria '<LEVELS json>' \\")
        print(f"        -s '{SYSTEM[:58]}…' < project.json")
        for p, u, a, s in proj[:args.show]:
            payload = {"site": str(a).split(",")[0], "records": sorted(
                recs.get(p, []), key=lambda r: r["date"].split("/")[-1] + r["date"][:5])}
            f = OUT / f"payload_{p}.json"
            f.write_text(json.dumps(payload, indent=2))
            print(f"\n  proj{p} ({u}u, v2 says '{s}') -> {f.name}, {len(payload['records'])} records")
            for r in payload["records"][:4]:
                print(f"      {r['date']} {r['record']:<16} status={r['status'] or '-':<22} {r['work'][:46]}")
        print("\n  DRY RUN — nothing sent. Needs: llm keys set typesafe")
        return 0

    results = []
    for p, u, a, s in proj:
        payload = json.dumps({"site": str(a).split(",")[0], "records": sorted(
            recs.get(p, []), key=lambda r: r["date"].split("/")[-1] + r["date"][:5])})
        cmd = ["llm", "-m", "jev", "-o", "answer_type", "score",
               "-o", "input_format", "json", "-o", "criteria", json.dumps(LEVELS),
               "-s", SYSTEM, payload]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout.strip()
        except Exception as e:  # noqa: BLE001
            out = f'{{"error":"{e}"}}'
        results.append({"project_id": p, "units": u, "address": str(a)[:40],
                        "v2_stage": s, "records": len(recs.get(p, [])), "jev": out[:400]})
        print(f"  proj{p:<5} {u:>5}u  v2={s:<20} jev={out[:70]}", flush=True)
    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    print(f"\n  -> {OUT}/results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
