#!/usr/bin/env python3
r"""llm_commercial_area.py -- read each housing project's commercial (non-residential) floor area from the City's text.

John, 2026-10-08 (package the project pro-forma into JN-Feasibility): commercial rent is the input that moved the
validation most, and a pattern match found it for 87 projects. This replaces the pattern with a reading: a model reads
each 5+ unit project's own Planning descriptions and the Zoning Adjustments Board's items about it, and reports the
ground-floor commercial / retail / office floor area the project would build. Kept only if the quote is VERBATIM in the
cited text and states the number. Nothing is inferred; a project whose text states none reads as none.

READ ONCE, STORE, LOOK UP: data/derived/commercial_area_evidence_<date>.json keyed by v4 project_key.

  .venv/bin/python scripts/llm_commercial_area.py --dry-run
  .venv/bin/python scripts/llm_commercial_area.py --sonnet submit|status|collect
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import model_readers as mr  # noqa: E402
from llm_project_units import _has_number  # noqa: E402

V4 = ROOT / "databases/berkeley_housing_v4.db"
ITEMS = ROOT / "data/derived/zab_actions_2026-10-06.jsonl"
OUT = ROOT / "scratch/2026-10-08_commercial_area"

DEFINITION = """QUESTION. Each PROJECT below is one housing development in Berkeley; its texts are the City's own Planning
record descriptions and the Zoning Adjustments Board's agenda items about it. Report, from those texts only, the
NEW COMMERCIAL FLOOR AREA the project would build, in square feet: ground-floor retail, restaurant, office, or other
non-residential space in the new building. Not residential floor area, not the whole building, not parking, not the
lot, not existing commercial space that is demolished, not "live-work" units (those are dwellings). If several figures
are given (e.g. "1,550 square feet of commercial area" and an earlier version), report the one in the most recent text
and quote it. If the text states no commercial floor area, answer null.
Give the exact words the figure comes from (copied verbatim, containing the number) and the source in brackets."""


def project_texts(dbp=V4):
    db = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
    planning = {}
    for k, p in db.execute("SELECT source_record_key, raw_payload FROM events WHERE event_type_code='planning_filed'"):
        d = (json.loads(p).get("description") or "").strip()
        if d:
            planning[k] = d
    items = {}
    for line in open(ITEMS):
        r = json.loads(line)
        if r.get("item_text"):
            items.setdefault(r["record"], []).append((f"ZAB {r['meeting_date']} item {r['item']}", r["item_text"]))
    keep = {k for (k,) in db.execute("SELECT project_key FROM v_projects WHERE COALESCE(NULLIF(units_built_or_permitted,0), "
                                     "proposed_units) >= 5 AND COALESCE(rhna_excluded,0) = 0")}
    out = {}
    for (n,) in db.execute("SELECT notes FROM projects"):
        n = json.loads(n)
        key = n.get("project_key")
        if key not in keep:
            continue
        recs = list(dict.fromkeys([r for r in [n.get("anchor")] + list(n.get("records") or []) if r]))
        texts = [(r, planning[r][:900]) for r in recs if r in planning][:4]
        texts += [x for r in recs for x in items.get(r, [])][:3]
        if texts:
            out[key] = texts
    return out


def verify(ans, texts):
    v, q, s = ans.get("value"), ans.get("quote"), str(ans.get("source") or "").strip().strip("[]").strip()
    if v in (None, "", 0) or not q:
        return None
    try:
        n = int(float(str(v).replace(",", "")))
    except Exception:
        return None
    norm = lambda x: re.sub(r"\s+", " ", x or "").strip().lower()
    for k, t in texts:
        if k == s and norm(q) in norm(t) and _has_number(q, n):
            return {"commercial_sqft": n, "quote": q, "source": s}
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sonnet", choices=["submit", "status", "collect"])
    ap.add_argument("--pack", type=int, default=4)
    a = ap.parse_args()
    state = OUT / "sonnet_batch_state.json"
    recs = project_texts()
    keys = sorted(recs)
    groups = [keys[i:i + a.pack] for i in range(0, len(keys), a.pack)]
    print(f"{len(keys)} projects with text")

    def prompt(g):
        body = "\n\n".join(f"PROJECT {k}\n" + "\n".join(f"  [{s}] {t}" for s, t in recs[k]) for k in g)
        return (f"{DEFINITION}\n\nAnswer with a JSON array only, one object per project, in order:\n"
                f"[{{\"project\": <PROJECT key>, \"value\": <integer square feet or null>, \"quote\": <exact words or null>, "
                f"\"source\": <the bracketed source id without brackets, or null>}}]\n\n{body}")

    if a.dry_run:
        print(prompt(groups[0])[:2500])
        print(f"\n{len(groups)} requests, ~{sum(len(prompt(g)) for g in groups)/4/1e6:.2f}M input tokens. NOTHING ASKED.")
        return 0
    if a.sonnet == "submit":
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "groups.json").write_text(json.dumps(groups))
        mr.batch_submit([{"custom_id": f"g{i}", "params": {"model": mr.BATCH_MODEL, "max_tokens": 2500 * len(g) + 800,
                          "messages": [{"role": "user", "content": prompt(g)}]}} for i, g in enumerate(groups)], state)
        return 0
    if a.sonnet == "status":
        mr.batch_status(state)
        return 0
    if a.sonnet == "collect":
        groups = json.loads((OUT / "groups.json").read_text())
        rows, unanswered, rejected = [], [], 0
        for cid, parsed, raw, _ in mr.batch_results(state):
            got = {str(x.get("project")): x for x in (parsed or []) if isinstance(x, dict)}
            for k in groups[int(cid[1:])]:
                if k not in got:
                    unanswered.append(k)
                    continue
                v = verify(got[k], recs[k])
                rejected += bool(got[k].get("value") not in (None, "", 0) and not v)
                rows.append({"project_key": k, **(v or {"commercial_sqft": None})})
        print(f"answers {len(rows)}; with a verified area {sum(1 for r in rows if r['commercial_sqft'])}; "
              f"proposed but rejected {rejected}; unanswered {len(unanswered)}")
        mr.write_evidence(rows, "commercial_area", DEFINITION,
                          extra={"model": mr.BATCH_MODEL, "rule": "kept only if the quote is verbatim and states the number",
                                 "unanswered": unanswered})
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
