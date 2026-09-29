#!/usr/bin/env python3
r"""planning_scope_decision_set.py -- turn two model readings into the rows John actually has to rule
on, with both readers' verdicts and the quoted reason beside each one.

Read-only. Writes one CSV to scratch/. No database write; the applied planning ingest is not re-run.

WHAT IT DECIDES, AND WHAT IT REFUSES TO DECIDE.
  * The second reader WINS where it exists. It read the same stamped definition and had to quote the
    words it relied on, and it differs from the cheap label on 58% of the records it re-read -- so
    preferring it is not deference, it is preferring the reading that shows its work.
  * UNKNOWN IS NOT A DROP. My first version counted every non-housing_development verdict as a DROP
    and so folded "the model determined this is not a development" together with "the model could not
    tell". The second is not a reason to remove a record from the queue; it is a record that STAYS,
    unresolved. HOLD_UNKNOWN is its own effect.
  * A row whose readers merely DISAGREE, with no effect on the queue, is still listed
    (effect blank): disagreement is where the definition is still ambiguous, which is worth John's
    eye even when nothing moves.

WHAT THE `final_reader` COLUMN IS FOR. Sonnet only re-read what Jev was unsure about, so a row marked
`jev` rests on a single label. Filter on it before trusting a queue change: confidence-based triage
cannot catch a confidently-wrong label, and this column is how that limit stays visible.

  .venv/bin/python scripts/planning_scope_decision_set.py
"""
from __future__ import annotations

import collections
import csv
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from housing_rules.planning_filter import DEV, HOUSING       # noqa: E402
from housing_rules.planning_record import role               # noqa: E402

SCRATCH = ROOT / "scratch/2026-09-28_planning_scope"
NOT_DEV = ("housing_adjacent_not_development", "not_housing")
CONF_FLOOR = 0.70


def records() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for fn in glob.glob(str(ROOT / "data/raw/accela/date_range/Planning_*.jsonl")):
        for line in open(fn):
            try:
                d = json.loads(line)
            except Exception:
                continue
            n = str(d.get("Record Number") or "").strip()
            if n and DEV.match(n):
                out[n] = d
    return out


def conf(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    recs = records()
    rq = {n for n, d in recs.items()
          if HOUSING.search(" ".join(str(d.get(f, "")) for f in
                                    ("Description", "Project Name", "Record Type")))}
    jev = {r["record"]: r for r in
           (json.loads(l) for l in open(SCRATCH / "jev_answers.jsonl")) if "error" not in r}
    try:
        son = {r["record"]: r for r in json.loads((SCRATCH / "sonnet_answers.json").read_text())}
    except Exception:
        son = {}

    rows = []
    for n, d in sorted(recs.items()):
        j, s = jev.get(n), son.get(n)
        if not j:
            continue
        regex = n in rq
        verdict = (s or {}).get("sonnet_scope") or j["scope"]
        if verdict == "housing_development":
            effect = "" if regex else "ADD"
        elif verdict in NOT_DEV:
            effect = "DROP" if regex else ""
        else:
            effect = "HOLD_UNKNOWN" if regex else ""
        contested = bool(s and s["sonnet_scope"] != j["scope"])
        if not effect and not contested:
            continue
        rows.append({
            "record": n, "record_role": role(d.get("Record Type")), "status": d.get("Status"),
            "regex_said_housing": regex,
            "jev": j["scope"], "jev_confidence": j.get("scope_confidence"),
            "sonnet": (s or {}).get("sonnet_scope", ""),
            "final_reader": "sonnet" if s else "jev", "final": verdict, "effect": effect,
            # a Jev-only row below the floor is still IN FLIGHT in a pending second read, which is a
            # different thing from a row nobody will ever look at again
            "second_read": ("done" if s else
                            ("pending" if conf(j.get("scope_confidence")) < CONF_FLOOR
                             else "not_queued")),
            "units_stated": (s or {}).get("sonnet_units_stated", j.get("units_stated")),
            "removes_units": (s or {}).get("sonnet_removes_units", ""),
            "two_thirds_test": (s or {}).get("two_thirds_test", ""),
            "reason": (s or {}).get("reason", ""),
            "description": str(d.get("Description") or "")[:300],
        })

    out = SCRATCH / "decision_set.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(recs):,} DEV records · regex queue {len(rq):,} · jev {len(jev):,} · "
          f"sonnet {len(son):,}")
    print(f"decision set: {len(rows):,} rows -> {out.relative_to(ROOT)}\n")
    for k, v in collections.Counter(r["effect"] or "contested_only" for r in rows).most_common():
        print(f"  {v:5}  {k}")
    print("\nhow firm each effect is:")
    for eff in ("ADD", "DROP", "HOLD_UNKNOWN"):
        sel = [r for r in rows if r["effect"] == eff]
        by = collections.Counter(r["second_read"] for r in sel)
        print(f"  {eff:13} {len(sel):5}   " + "  ".join(f"{k}={v}" for k, v in by.most_common()))
    print("\nby record role:")
    for eff in ("ADD", "DROP", "HOLD_UNKNOWN"):
        sel = [r for r in rows if r["effect"] == eff]
        print(f"  {eff:13} " + ", ".join(f"{k} {v}" for k, v in
                                         collections.Counter(r["record_role"] for r in sel)
                                         .most_common()))
    rm = [r for r in rows if str(r["removes_units"] or "0").isdigit() and int(r["removes_units"] or 0) > 0]
    live = [r for r in rm if str(r["status"]) not in ("Withdrawn", "Void", "Expired", "Cancelled")]
    print(f"\nunit REMOVALS stated: {len(rm)} records; on records the city did not withdraw or void: "
          f"{len(live)} records, {sum(int(r['removes_units']) for r in live)} units "
          f"(the largest single claim, 75 units, sits on a WITHDRAWN application -- status before count)")
    print("\nNOTHING WRITTEN to any database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
