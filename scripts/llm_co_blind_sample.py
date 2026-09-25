#!/usr/bin/env python3
"""llm_co_blind_sample.py — BLIND stratified test: can a model read Accela and say what is built?

The adversarial 8 (scripts/llm_co_classify_test.py) showed the method survives the cases that beat
our regexes -- 8/8. It could not show an error RATE, because the cases were chosen because we knew
they were hard. This draws a sample nobody has pre-labelled.

STRATIFIED, NOT PROPORTIONAL. 77% of v2's projects are single-unit, so a proportional draw of 75
would be ~58 ADUs and would tell us almost nothing about the buildings that carry the units. John:
"I worry that we will miss our big projects and be swamped by tiny ADU." Strata oversample large:

    50+ units   25 of 95     20-49 units 15 of 28     5-19 units 12 of 22
    2-4 units   11 of 112    1 unit      12 of 842

BLIND means: the sample is drawn by seeded RNG, the prompts contain no v2 field, and the truth
column is not read until after every answer is in.

A DISAGREEMENT IS NOT AUTOMATICALLY A MODEL ERROR. v2 was demonstrably wrong on several projects
today -- 1914 Fifth and 2420 Shattuck were staged as if their parking lot and pizza-restaurant
permits were housing completions, and 214 units were marked withdrawn while under construction. So
disagreements are reported for ADJUDICATION, not scored against the model on sight.

Ground truth for scoring: `v_projects_flat.co_issued_date IS NOT NULL` (ADR-001, verdict-driven).

Usage:  python scripts/llm_co_blind_sample.py --model claude-sonnet-5 [--n 75] [--seed 20260925]
"""
import argparse
import collections
import glob
import json
import random
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scratch/2026-09-25/llm_blind_sample"
ALREADY_TESTED = {4, 13, 150, 157, 143, 178, 152, 139}      # the adversarial 8, excluded

STRATA = [("50+", 50, 10**9, 25), ("20-49", 20, 49, 15), ("5-19", 5, 19, 12),
          ("2-4", 2, 4, 11), ("1", 1, 1, 12)]

PROMPT = """You are reading raw permit and planning records from the City of Berkeley's Accela system for ONE development site.

Decide whether the HOUSING DEVELOPMENT at this site has been BUILT AND COMPLETED.

Rules that matter here:
- A permit with status "Finaled" means THAT permit's work passed final inspection. It does NOT mean the housing development is complete. A demolition permit, a parking-lot permit, or a restaurant fit-out can all be "Finaled" on a site where no housing was ever built.
- Descriptions often begin with a dated log line (e.g. "2/15/19 - mechanical permit issued.") that is NOT the scope of work. Read past it.
- Descriptions may end with unrelated contractor notes (e.g. "added Temp power pole").
- A site accumulates its whole history. Old permits may belong to a building that no longer exists, or to a different project than the one currently proposed.
- "Phase 1", "Phase 2" etc. are parts of ONE building, not separate buildings.
- If the records are too thin to tell, say so with confidence "low" rather than guessing.

Answer in strict JSON, no other text:
{"built": true|false, "confidence": "high"|"medium"|"low", "what_was_actually_finaled": "<short>", "reason": "<one sentence>"}

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
    ap.add_argument("--seed", type=int, default=20260925)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{ROOT/'databases/berkeley_housing_v2.db'}?mode=ro", uri=True)
    rows = [(p, u or 0, a, co) for p, u, a, co in db.execute(
        "SELECT project_id, total_units, address_display, co_issued_date FROM v_projects_flat")
        if p not in ALREADY_TESTED and a]

    rng = random.Random(args.seed)
    sample = []
    for label, lo, hi, n in STRATA:
        pool = [r for r in rows if lo <= r[1] <= hi]
        rng.shuffle(pool)
        picked = pool[:n]
        sample += [(label,) + r for r in picked]
        print(f"  stratum {label:<6} pool {len(pool):>4}  drawn {len(picked):>3}")
    print(f"  TOTAL sample: {len(sample)}\n")

    # gather records per sampled project
    want = {}
    for s in sample:
        k = key(s[3])
        if k:
            want.setdefault(k, []).append(s[1])
    recs = collections.defaultdict(list)
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
                    recs[k].append({"module": mod, "record": num, "date": d.get("Date", ""),
                                    "status": (d.get("Status") or "").strip(),
                                    "address": (d.get("_cells") or [""])[-1].split(", BERKELEY")[0],
                                    "description": (d.get("Description") or "").strip()})
    if args.dry_run:
        n_rec = sum(len({r['record'] for r in recs[key(s[3])]}) if key(s[3]) else 0 for s in sample)
        print(f"  Accela records the sample would carry: {n_rec:,}")
        print(f"  estimated input tokens: ~{n_rec*55//1:,}")
        return 0

    results = []
    for i, (stratum, pid, units, addr, co) in enumerate(sample, 1):
        k = key(addr)
        rs = recs.get(k, [])
        seen, ded = set(), []
        for r in sorted(rs, key=lambda r: r["date"].split("/")[-1] + r["date"][:5]):
            if r["record"] in seen:
                continue
            seen.add(r["record"]); ded.append(r)
        lines = "\n".join(
            f"  [{r['module']}] {r['record']} | {r['date']} | status={r['status'] or '-'} | {r['address']}\n"
            f"      {r['description'][:300]}" for r in ded)
        prompt = PROMPT % (str(addr).split(",")[0], lines or "  (no records found)")
        try:
            out = subprocess.run(["llm", "-m", args.model, prompt],
                                 capture_output=True, text=True, timeout=180)
            raw = out.stdout.strip()
        except Exception as e:  # noqa: BLE001
            raw = f'{{"error": "{e}"}}'
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            got = json.loads(m.group(0)) if m else {}
        except Exception:
            got = {}
        truth = co is not None
        results.append({"project_id": pid, "stratum": stratum, "units": units,
                        "address": str(addr)[:44], "records": len(ded),
                        "v2_has_co": truth, "model_built": got.get("built"),
                        "agree": got.get("built") is truth, "confidence": got.get("confidence"),
                        "finaled": got.get("what_was_actually_finaled"), "reason": got.get("reason")})
        print(f"  [{i:>2}/{len(sample)}] {stratum:<6} proj{pid:<5} {units:>4}u  rec={len(ded):>3}  "
              f"v2={truth!s:<5} model={got.get('built')!s:<5} {'agree' if results[-1]['agree'] else 'DIFFER'}",
              flush=True)
    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    n = len(results); a = sum(1 for r in results if r["agree"])
    print(f"\n  agreement with v2: {a}/{n}  ({a/n*100:.0f}%)")
    print("  by stratum:")
    for label, *_ in STRATA:
        s = [r for r in results if r["stratum"] == label]
        if s:
            print(f"    {label:<6} {sum(1 for r in s if r['agree'])}/{len(s)}")
    print(f"\n  {n-a} disagreements -> adjudicate by hand; v2 is not automatically right")
    print(f"  -> {OUT}/results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
