#!/usr/bin/env python3
"""batch_stage_classify.py — classify every project's pipeline rung via the Anthropic Batch API.

WHY BATCH. The serial approach failed on 2026-09-25 and the failure is instructive: 25 projects
took 49 minutes and returned nothing, because one `llm` subprocess per project, against a key that
throttles under sustained use, is the wrong shape. A trivial call took 2.0s early in that session
and had not returned after 300s by the end of it. The Batch API is not a workaround for rate
limits -- it is the queue those limits exist to protect. It is also 50% cheaper and removes
wall-clock from the problem entirely: submit, walk away, collect a file.

THE SEVEN RUNGS carry John's acceptance step -- the interval between "filed" and "accepted" is
staff discretion made visible, and it is what SB 9 / SB 35 / SB 330 / SB 684 / AB 2011 act on. Each
project therefore returns (rung, track) as a pair, plus the record numbers the judgment rests on,
so a wrong answer shows up as a wrong CITATION and can be gated like any other write.

THE TRAPS OF 2026-09-25 are encoded in rung 7: a finaled demolition, parking-lot, solar,
temporary-power or restaurant-fit-out permit is NOT a housing completion. Those are 1914 Fifth
(a parking lot with a beer garden), 2420 Shattuck (a pizza restaurant) and 2538 Durant, each of
which our own keyword classifier called a housing completion.

Commands:
  submit    build the requests, print the cost, and send the batch     [--dry-run to stop short]
  status    poll the batch
  collect   fetch results, parse, and write results.json               [read-only on the DB]

Nothing is written to any database. Ever. Collection produces a file for review.
"""
import argparse
import collections
import glob
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
# READING_RULES is imported but DEFAULTS OFF. Two controls on 2026-09-26 found the tips do not
# help and may hurt. At permit grain against 206 human rulings: rules-off 199/206 beat rules-on
# 196/206, and on the rows that GENERATED the rules, 8/8 beat 6/8. At project grain here the
# accuracy delta was noise (+1 of 168) but the DIRECTION matched: rules-on pushed rungs DOWN on 11
# of 17 disagreements, mean -0.24 -- the tips are suppressive, exactly as their failure analysis
# predicted (rule 4 zeroed completing phases, rule 5 rejected a mini-dorm John had ruled a dwelling).
# Tips about the data transmit our biases. DEFINITIONS of the question do not -- and the rung
# definitions in RUNGS below are precisely that, which is why they stay.
from housing_rules.reading_rules import READING_RULES   # available via --rules; see that module
OUT = ROOT / "scratch/2026-09-26/batch_stage"
STATE = OUT / "batch_state.json"
MODEL = "claude-sonnet-5"   # the same model the 8/8 adversarial and 75-project blind tests used

RUNGS = [
  "1 pre_application — informal enquiry, pre-application meeting, or zoning research letter only. No formal application filed.",
  "2 application_submitted — a planning application exists but the city has NOT yet accepted it: status Incomplete Pending Applicant, Corrections Pending Applicant, Pending, or a resubmittal still awaiting staff review.",
  "3 application_accepted — the city has DEEMED THE APPLICATION COMPLETE and consideration has begun: status Application Complete, or Under/In Review following acceptance, or a hearing scheduled. Not yet approved or denied.",
  "4 entitled — a planning approval has been granted (Approved or Approved w/Conditions on a zoning or use permit). No building permit for the housing issued.",
  "5 permitted — a building permit for the HOUSING ITSELF has been Issued, but no inspections and nothing finaled.",
  "6 under_construction — inspections are occurring on the housing building permit, or phase permits are issued and active, but the housing permit is not finaled.",
  "7 completed — the building permit FOR THE HOUSING ITSELF has been Finaled. Note carefully: a finaled demolition permit, parking-lot permit, solar permit, temporary-power permit or restaurant tenant-improvement is NOT a housing completion.",
]

PROMPT = """You are reading raw permit and planning records from the City of Berkeley's Accela system for ONE development site.

Judge the SPECIFIC PROPOSED HOUSING DEVELOPMENT, not the site. An existing building being altered does not make a proposal complete.

Assign the highest rung the proposal has genuinely reached:

{rungs}

Also decide the APPROVAL TRACK:
- "ministerial" if the records invoke SB 9, SB 35, SB 330, SB 684, AB 2011, by-right or streamlined review, or an ADU/JADU (ADUs are ministerial by state law)
- "discretionary" if it goes through a use permit, public hearing, design review, or a zoning permit requiring staff or commission judgment
- "unclear" if the records do not say

{reading_rules}
- A site accumulates its whole history; old permits may belong to a building that no longer exists.
- If the records are too thin to tell, use confidence "low" rather than guessing.

Reply with ONLY a JSON object, no prose:
{{"rung": 1-7, "rung_name": "<name>", "track": "ministerial"|"discretionary"|"unclear", "confidence": "high"|"medium"|"low", "evidence": ["<record numbers>"], "reason": "<one sentence>"}}

SITE: {site}

RECORDS:
{records}"""


def api_key():
    p = Path.home() / "Library/Application Support/io.datasette.llm/keys.json"
    k = json.load(open(p)).get("anthropic")
    if not k:
        sys.exit("no anthropic key in llm's keys.json")
    return k


def key(a):
    a = re.sub(r",.*$", "", str(a or "").upper())
    p = re.sub(r"[^A-Z0-9 ]", " ", a).split()
    return (p[0], p[1]) if len(p) > 1 and p[0].isdigit() else None


def build(limit=None, sample=None, seed=20260926, no_rules=False):
    db = sqlite3.connect(f"file:{ROOT/'databases/berkeley_housing_v2.db'}?mode=ro", uri=True)
    proj = [(p, u or 0, a, s) for p, u, a, s in db.execute(
        """SELECT project_id,total_units,address_display,status_code FROM v_projects_flat
           WHERE address_display IS NOT NULL ORDER BY total_units DESC""")]
    if limit:
        proj = proj[:limit]
    if sample:
        import random
        rng = random.Random(seed)
        strata = [(50, 10**9), (20, 49), (5, 19), (2, 4), (1, 1)]
        per = max(1, sample // len(strata))
        picked = []
        for lo, hi in strata:
            pool = [x for x in proj if lo <= x[1] <= hi]
            rng.shuffle(pool)
            picked += pool[:per]
        proj = picked
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
    rungs = "\n".join(RUNGS)
    reqs, meta = [], {}
    for p, u, a, s in proj:
        rs = sorted(recs.get(p, []), key=lambda r: r["d"].split("/")[-1] + r["d"][:5])
        lines = "\n".join(f"  [{r['m']}] {r['n']} | {r['d']} | status={r['s'] or '-'}\n      {r['w']}"
                          for r in rs) or "  (no records found)"
        reqs.append({
            "custom_id": f"proj{p}",
            # 400 truncated 89 of 1,099: extended thinking is ON by default and eats the budget
                       # before the JSON is emitted. The failures were valid JSON cut mid-string.
                       "params": {"model": MODEL, "max_tokens": 2000,
                       "messages": [{"role": "user", "content": PROMPT.format(
                           rungs=rungs, site=str(a).split(",")[0], records=lines,
                           reading_rules=("" if no_rules else READING_RULES))}]},
        })
        meta[f"proj{p}"] = {"project_id": p, "units": u, "address": str(a)[:44],
                            "v2_stage": s, "records": len(rs)}
    return reqs, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["submit", "status", "collect"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--rules", action="store_true",
                    help="INCLUDE READING_RULES. Off by default: the controls found the tips "
                         "neutral-to-harmful. Kept so the comparison stays reproducible.")
    ap.add_argument("--no-rules", action="store_true",
                    help="omit READING_RULES — the CONTROL arm. The delta against a rules-on run "
                         "on the same projects is the lift the rules provide; the rules-off score "
                         "is the model's cold ability. Without it we cannot tell reading from "
                         "reciting, which is the question the whole rearchitecture turns on.")
    ap.add_argument("--sample", type=int, default=None,
                    help="stratified sample by unit size (control runs do not need all 1,099)")
    ap.add_argument("--tag", default="", help="suffix for the output dir")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    global OUT, STATE
    if args.tag:
        OUT = OUT.parent / f"batch_stage_{args.tag}"
        STATE = OUT / "batch_state.json"
    OUT.mkdir(parents=True, exist_ok=True)
    import anthropic
    client = anthropic.Anthropic(api_key=api_key())

    if args.cmd == "submit":
        reqs, meta = build(args.limit, args.sample, no_rules=not args.rules)
        chars = sum(len(r["params"]["messages"][0]["content"]) for r in reqs)
        tin, tout = chars / 4, len(reqs) * 200
        print(f"  requests      {len(reqs):,}")
        print(f"  input tokens  ~{tin/1e6:.2f}M      output ~{tout/1e3:.0f}k")
        print(f"  standard      ${tin/1e6*3 + tout/1e6*15:.2f}")
        print(f"  BATCH (-50%)  ${(tin/1e6*3 + tout/1e6*15)/2:.2f}")
        print(f"  no records    {sum(1 for m in meta.values() if m['records']==0)} projects")
        (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
        if args.dry_run:
            print("\n  DRY RUN — not submitted.")
            return 0
        b = client.messages.batches.create(requests=reqs)
        STATE.write_text(json.dumps({"batch_id": b.id, "n": len(reqs),
                                     "created": str(b.created_at), "model": MODEL}, indent=2))
        print(f"\n  SUBMITTED  batch {b.id}   status={b.processing_status}")
        print(f"  -> {STATE}")
        print(f"  poll:    python3 scripts/batch_stage_classify.py status")
        return 0

    st = json.loads(STATE.read_text()) if STATE.exists() else None
    if not st:
        sys.exit("no batch_state.json — run submit first")
    b = client.messages.batches.retrieve(st["batch_id"])
    c = b.request_counts
    print(f"  batch {b.id}\n  status {b.processing_status}")
    print(f"  processing={c.processing} succeeded={c.succeeded} errored={c.errored} "
          f"canceled={c.canceled} expired={c.expired}")
    if args.cmd == "status":
        return 0

    if b.processing_status != "ended":
        sys.exit("  batch has not ended yet — nothing to collect")
    meta = json.loads((OUT / "meta.json").read_text())
    rows, bad = [], []
    for r in client.messages.batches.results(st["batch_id"]):
        m = dict(meta.get(r.custom_id, {}))
        if r.result.type != "succeeded":
            bad.append({"custom_id": r.custom_id, "type": r.result.type,
                        "detail": str(getattr(r.result, "error", ""))[:200]})
            continue
        # content[0] is a ThinkingBlock when extended thinking is on — take the TEXT block,
        # never a positional guess.
        txt = "".join(b.text for b in r.result.message.content if getattr(b, "type", "") == "text")
        mm = re.search(r"\{.*\}", txt, re.S)
        try:
            got = json.loads(mm.group(0)) if mm else {}
        except Exception:
            got = {}
        if not got:
            bad.append({"custom_id": r.custom_id, "type": "unparseable", "detail": txt[:200]})
            continue
        m.update({k2: got.get(k2) for k2 in
                  ("rung", "rung_name", "track", "confidence", "evidence", "reason")})
        rows.append(m)
    (OUT / "results.json").write_text(json.dumps(rows, indent=2))
    if bad:
        (OUT / "failures.json").write_text(json.dumps(bad, indent=2))
    print(f"\n  parsed {len(rows):,}   failed {len(bad)}")
    print("  rungs :", dict(sorted(collections.Counter(r["rung"] for r in rows).items())))
    print("  track :", dict(collections.Counter(r["track"] for r in rows).most_common()))
    agree = sum(1 for r in rows if r.get("rung") == 7 and r["v2_stage"] == "completed")
    print(f"  rung 7 and v2 'completed' agree on {agree}")
    print(f"  -> {OUT}/results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
