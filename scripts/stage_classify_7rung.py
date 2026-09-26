#!/usr/bin/env python3
"""stage_classify_7rung.py — assign every project a pipeline rung, and flag the approval track.

THE SEVENTH RUNG, and why John wanted it. Between "application submitted" and "entitled" sits a
distinct step the city controls: the application is not ACCEPTED for a while, and only when it is
deemed complete does consideration of the permit begin. That interval is staff discretion made
visible.

It matters now because California is removing that discretion. SB 9, SB 35, SB 330, SB 684 and
AB 2011 push projects onto MINISTERIAL or by-right tracks where acceptance is automatic if
objective standards are met. So every project also gets an approval-track flag, and the pair
(rung, track) is what lets us measure how city performance changes against our own historical
record -- the submitted->accepted and accepted->entitled intervals, discretionary versus ministerial,
over time.

Markers present in the Planning corpus today: SB330 120, SB35 19, SB684 15, SB9 12, by-right 7,
ministerial 4, AB2011 4.

EVIDENCE, NOT A BARE LABEL. Each answer must cite the record numbers it rests on, so a wrong rung
shows as a wrong citation and can be gated like any other write. That is what would have caught the
one genuine model error in the 75-project blind test, where a verdict contradicted its own reason.

The traps of 2026-09-25 are encoded in rung 7: a finaled demolition, parking-lot, solar or
restaurant-fit-out permit is NOT a housing completion.

Usage:
  python scripts/stage_classify_7rung.py --limit 25        # smoke test
  python scripts/stage_classify_7rung.py                   # all 1,099  (~$5.70 on Sonnet)
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
OUT = ROOT / "scratch/2026-09-25/stage7"

RUNGS = [
  "1 pre_application — informal enquiry, pre-application meeting, or zoning research letter only. No formal application filed.",
  "2 application_submitted — a planning application exists but the city has NOT yet accepted it: status Incomplete Pending Applicant, Corrections Pending Applicant, Pending, or a resubmittal still awaiting staff review.",
  "3 application_accepted — the city has DEEMED THE APPLICATION COMPLETE and consideration has begun: status Application Complete, Under Review or In Review after an acceptance, or a hearing scheduled. Not yet approved or denied.",
  "4 entitled — a planning approval has been granted (Approved or Approved w/Conditions on a zoning or use permit). No building permit for the housing has been issued.",
  "5 permitted — a building permit for the HOUSING ITSELF has been Issued, but no inspections and nothing finaled.",
  "6 under_construction — inspections are occurring on the housing building permit, or phase permits are issued and active, but the housing permit is not finaled.",
  "7 completed — the building permit FOR THE HOUSING ITSELF has been Finaled. Note carefully: a finaled demolition permit, parking-lot permit, solar permit, temporary-power permit or restaurant tenant-improvement is NOT a housing completion.",
]

PROMPT = """You are reading raw permit and planning records from the City of Berkeley's Accela system for ONE development site.

Judge the SPECIFIC PROPOSED HOUSING DEVELOPMENT, not the site. An existing building being altered does not make a proposal complete.

Assign the highest rung the proposal has genuinely reached:

%s

Also decide the APPROVAL TRACK:
- "ministerial" if the records invoke SB 9, SB 35, SB 330, SB 684, AB 2011, by-right or streamlined review, or an ADU/JADU (ADUs are ministerial by state law)
- "discretionary" if it goes through a use permit, public hearing, design review or zoning permit requiring staff or commission judgment
- "unclear" if the records do not say

Notes on reading these records:
- Descriptions often BEGIN with a dated log line ("2/15/19 - mechanical permit issued.") that is not the scope. Read past it.
- Descriptions may END with unrelated contractor notes ("added Temp power pole").
- A site accumulates its whole history; old permits may belong to a building that no longer exists.
- "Phase 1", "Phase 2" are parts of ONE building.
- If the records are too thin to tell, use confidence "low" rather than guessing.

Answer in strict JSON, no other text:
{"rung": 1-7, "rung_name": "<name>", "track": "ministerial"|"discretionary"|"unclear", "confidence": "high"|"medium"|"low", "evidence": ["<record numbers this rests on>"], "reason": "<one sentence>"}

SITE: %s

RECORDS:
%s
"""


def key(a):
    a = re.sub(r",.*$", "", str(a or "").upper())
    p = re.sub(r"[^A-Z0-9 ]", " ", a).split()
    return (p[0], p[1]) if len(p) > 1 and p[0].isdigit() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{ROOT/'databases/berkeley_housing_v2.db'}?mode=ro", uri=True)
    proj = [(p, u or 0, a, s) for p, u, a, s in db.execute(
        """SELECT project_id,total_units,address_display,status_code FROM v_projects_flat
           WHERE address_display IS NOT NULL ORDER BY total_units DESC""")]
    if args.limit:
        proj = proj[:args.limit]
    want = {}
    for p, u, a, s in proj:
        k = key(a)
        if k:
            want.setdefault(k, []).append(p)
    recs, seen = collections.defaultdict(list), collections.defaultdict(set)
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
                        recs[p].append({"m": mod, "n": num, "d": d.get("Date", ""),
                                        "s": (d.get("Status") or "").strip(),
                                        "w": (d.get("Description") or "").strip()[:280]})
    rung_txt = "\n".join(RUNGS)
    results = []
    for i, (p, u, a, s) in enumerate(proj, 1):
        rs = sorted(recs.get(p, []), key=lambda r: r["d"].split("/")[-1] + r["d"][:5])
        lines = "\n".join(f"  [{r['m']}] {r['n']} | {r['d']} | status={r['s'] or '-'}\n      {r['w']}"
                          for r in rs) or "  (no records found)"
        try:
            out = subprocess.run(["llm", "-m", args.model,
                                  PROMPT % (rung_txt, str(a).split(",")[0], lines)],
                                 capture_output=True, text=True, timeout=180).stdout.strip()
        except Exception as e:  # noqa: BLE001
            out = f'{{"error":"{e}"}}'
        m = re.search(r"\{.*\}", out, re.S)
        try:
            got = json.loads(m.group(0)) if m else {}
        except Exception:
            got = {}
        results.append({"project_id": p, "units": u, "address": str(a)[:40], "v2_stage": s,
                        "records": len(rs), "rung": got.get("rung"), "rung_name": got.get("rung_name"),
                        "track": got.get("track"), "confidence": got.get("confidence"),
                        "evidence": got.get("evidence"), "reason": got.get("reason")})
        if i % 25 == 0 or i <= 5:
            print(f"  [{i}/{len(proj)}] proj{p:<5} {u:>5}u  v2={str(s)[:18]:<18} "
                  f"rung={got.get('rung')} {str(got.get('rung_name'))[:18]:<18} track={got.get('track')}", flush=True)
    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    ok = [r for r in results if r["rung"]]
    print(f"\n  classified {len(ok)}/{len(results)}")
    print("  rung distribution:", dict(sorted(collections.Counter(r["rung"] for r in ok).items())))
    print("  track distribution:", dict(collections.Counter(r["track"] for r in ok).most_common()))
    print(f"  -> {OUT}/results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
