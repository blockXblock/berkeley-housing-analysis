#!/usr/bin/env python3
# ============================ SEQUESTERED 2026-09-29 ============================
# DO NOT RUN. Original path: scripts/llm_co_classify_test.py
# WHY: 2026-09-25 model experiment; replaced by model_readers.py / llm_permit_effect.py.
raise SystemExit('SEQUESTERED 2026-09-29 -- see header; original path scripts/llm_co_classify_test.py')
# ================================================================================
"""llm_co_classify_test.py — can a model read raw Accela records and say whether a project is built?

THE TEST John asked for. Every classification error found on 2026-09-25 was a LANGUAGE failure that
a regex could not survive:
  * a caption grep missed Acheson Bldg C because the city wrote '"ACHESON COMMONS" - BUILDING "C"'
  * '2/15/19 - mechanical permit issued.' read as a mechanical permit -- it is a 107-unit building
    behind a dated log prefix
  * a non-dwelling veto dropped a 56-UNIT BUILDING because a contractor's note at the end of the
    description said "temp power pole"
  * 1914 Fifth's Building Finals are a DEMO and a PARKING LOT WITH A BEER GARDEN; the site is still
    a parking lot and the 257-unit tower is unbuilt
  * 2420 Shattuck's Building Final is a pizza restaurant fit-out; the 132-unit tower is unbuilt

So the test set is deliberately adversarial: it is the cases that beat us, not a random sample.
A model that gets these right is worth rebuilding the linker around. One that does not, is not.

GROUND TRUTH is v2's verdict-driven `co_issued_date` (ADR-001/002) CORRECTED by John's direct
knowledge of the sites, which outranks the database where they disagree -- for 1914 Fifth and 2420
Shattuck the database's own stage field says in_review and John confirms both are unbuilt.

The model sees ONLY raw Accela rows: record number, date, status, description, address. It is told
nothing about units, nothing from v2, and nothing about which cases are hard.

Read-only. Writes prompt bundles and results to scratch/.
"""
import argparse
import json
import glob
import re
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scratch/2026-09-25/llm_co_test"

# project_id -> (label, ground truth built?, why the case is here)
CASES = {
    4:   ("1914 Fifth St (257u)",      False, "finals are a DEMO and a PARKING LOT + beer garden; still a parking lot"),
    13:  ("2420 Shattuck Ave (132u)",  False, "final is a pizza restaurant fit-out; tower unbuilt"),
    150: ("3030 Telegraph Ave (144u)", True,  "genuinely completed 2026"),
    157: ("2587 Telegraph Ave (52u)",  False, "under construction; leasing office + blade sign, no BP finaled"),
    143: ("2902 Adeline St (54u)",     False, "under construction; inspected 2026-09-22"),
    178: ("2131 University (Acheson)", True,  "4 buildings, all four permits finaled"),
    152: ("1598 University (207u)",    False, "678 inspections to 2026-05, no CO"),
    139: ("2538 Durant Ave (83u)",     False, "443 inspections to 2026-05, no CO"),
}


def key(a):
    a = re.sub(r",.*$", "", str(a or "").upper())
    p = re.sub(r"[^A-Z0-9 ]", " ", a).split()
    return (p[0], p[1]) if len(p) > 1 and p[0].isdigit() else None


def gather():
    db = sqlite3.connect(f"file:{ROOT/'databases/berkeley_housing_v2.db'}?mode=ro", uri=True)
    addr = {p: a for p, a in db.execute("SELECT project_id, address_display FROM v_projects_flat")}
    want = {key(addr[p]): p for p in CASES if addr.get(p)}
    recs = {p: [] for p in CASES}
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
                    recs[want[k]].append({
                        "module": mod, "record": num, "date": d.get("Date", ""),
                        "status": (d.get("Status") or "").strip(),
                        "address": (d.get("_cells") or [""])[-1].split(", BERKELEY")[0],
                        "description": (d.get("Description") or "").strip(),
                    })
    for p in recs:
        seen, ded = set(), []
        for r in recs[p]:
            if r["record"] in seen:
                continue
            seen.add(r["record"]); ded.append(r)
        recs[p] = sorted(ded, key=lambda r: r["date"].split("/")[-1] + r["date"][:5])
    return addr, recs


PROMPT = """You are reading raw permit and planning records from the City of Berkeley's Accela system for ONE development site.

Decide whether the HOUSING DEVELOPMENT at this site has been BUILT AND COMPLETED.

Rules that matter here:
- A permit with status "Finaled" means THAT permit's work passed final inspection. It does NOT mean the housing development is complete. A demolition permit, a parking-lot permit, or a restaurant fit-out can all be "Finaled" on a site where no housing was ever built.
- Descriptions often begin with a dated log line (e.g. "2/15/19 - mechanical permit issued.") that is NOT the scope of work. Read past it.
- Descriptions may end with unrelated contractor notes (e.g. "added Temp power pole").
- A site accumulates its whole history. Old permits may belong to a building that no longer exists, or to a different project than the one currently proposed.
- "Phase 1", "Phase 2" etc. are parts of ONE building, not separate buildings.

Answer in strict JSON, no other text:
{"built": true|false, "confidence": "high"|"medium"|"low", "what_was_actually_finaled": "<short>", "reason": "<one sentence>"}

SITE: %s

RECORDS:
%s
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-4o")
    ap.add_argument("--only", type=int, default=None)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    addr, recs = gather()
    results = []
    for pid, (label, truth, why) in CASES.items():
        if args.only and pid != args.only:
            continue
        rs = recs.get(pid, [])
        lines = "\n".join(
            f"  [{r['module']}] {r['record']} | {r['date']} | status={r['status'] or '-'} | {r['address']}\n"
            f"      {r['description'][:300]}" for r in rs)
        prompt = PROMPT % (label.split(" (")[0], lines or "  (no records found)")
        (OUT / f"prompt_{pid}.txt").write_text(prompt)
        try:
            out = subprocess.run(["llm", "-m", args.model, prompt],
                                 capture_output=True, text=True, timeout=180)
            raw = out.stdout.strip()
        except Exception as e:  # noqa: BLE001
            raw = f'{{"error": "{e}"}}'
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            got = json.loads(m.group(0)) if m else {"built": None, "reason": raw[:120]}
        except Exception:
            got = {"built": None, "reason": raw[:120]}
        ok = got.get("built") is truth
        results.append({"project_id": pid, "label": label, "records": len(rs),
                        "truth_built": truth, "model_built": got.get("built"),
                        "correct": ok, "confidence": got.get("confidence"),
                        "finaled": got.get("what_was_actually_finaled"),
                        "reason": got.get("reason"), "why_hard": why})
        mark = "OK  " if ok else "MISS"
        print(f"  [{mark}] {label:<30} records={len(rs):>3}  truth={truth!s:<5} model={got.get('built')!s:<5} "
              f"({got.get('confidence')})")
        if got.get("what_was_actually_finaled"):
            print(f"         finaled: {str(got['what_was_actually_finaled'])[:88]}")
        if not ok:
            print(f"         reason : {str(got.get('reason'))[:88]}")
    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    n = len(results); c = sum(1 for r in results if r["correct"])
    print(f"\n  {c}/{n} correct on the adversarial set  ({c/n*100:.0f}%)")
    print(f"  -> {OUT}/results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
