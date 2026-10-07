#!/usr/bin/env python3
r"""llm_zab_items.py -- read what the Zoning Adjustments Board heard: units, stories, height, State Density Bonus.

John, 2026-10-07 ("yes on the three calls"): v2 carried proposed units, heights and density-bonus tags for projects
v4 could not read them for; v2 is not a source, but the Board's own Action Minutes state them for every item it heard
("construct a five-story (63-foot) mixed-use building with ... 144 dwelling units ... utilizing a State Density
Bonus"). A model reads each project's items (data/derived/zab_actions_<date>.jsonl, item_text) against HCD's
definitions; an answer is kept only if its quote is VERBATIM in the cited item and states the value (the number, or
the words "density bonus") -- so nothing can be inferred or carried over.

READ ONCE, STORE, LOOK UP: data/derived/zab_items_evidence_<date>.json keyed by v4 project_key. build_projects uses a
value only where v4's own readings have none. Nothing here writes to a database.

  .venv/bin/python scripts/llm_zab_items.py --dry-run
  .venv/bin/python scripts/llm_zab_items.py --sonnet submit|status|collect
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
from llm_project_units import _has_number  # noqa: E402   (the same number test as the units and measures readings)
from housing_rules.reading_rules import DEFINITIONS as HCD_DEFINITIONS  # noqa: E402

V4 = ROOT / "databases/berkeley_housing_v4.db"
ITEMS = ROOT / "data/derived/zab_actions_2026-10-06.jsonl"
OUT = ROOT / "scratch/2026-10-07_zab_items"

DEFINITION = HCD_DEFINITIONS + """

QUESTION. Each PROJECT below is one housing development; its text is what the City's Zoning Adjustments Board heard
about it (agenda item: application, zoning, CEQA, recommendation, action). Report, from that text only:
  units         -- the number of NEW DWELLING UNITS the project would build (housing units under the definitions
                   above; not existing units demolished, not commercial space, not parking spaces);
  stories       -- the building's number of stories;
  height_feet   -- the building's height in feet;
  density_bonus -- true only if the text says the project uses a State Density Bonus.
For EACH value give the exact words it comes from (copied verbatim, containing the number, or the words "density
bonus") and the item they come from. A value the text does not state is null. If several buildings are described,
report the totals the text states, or null."""


def project_items(dbp=V4, items=ITEMS):
    """v4 project_key -> [(source id, item text)], the Board's items on any of the project's records."""
    by_rec = {}
    for line in open(items):
        r = json.loads(line)
        if r.get("item_text"):
            by_rec.setdefault(r["record"], []).append(r)
    db = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
    out = {}
    for notes, in db.execute("SELECT notes FROM projects"):
        n = json.loads(notes)
        key = n.get("project_key")
        recs = [r for r in [n.get("anchor")] + list(n.get("records") or []) if r]
        hits = [x for r in dict.fromkeys(recs) for x in by_rec.get(r, [])]
        if not key or not hits:
            continue
        hits.sort(key=lambda x: (x["action"] != "APPROVED", x["meeting_date"]), reverse=False)
        seen, texts = set(), []
        for x in hits:
            sid = f"ZAB {x['meeting_date']} item {x['item']}"
            if sid in seen:
                continue
            seen.add(sid)
            texts.append((sid, x["item_text"]))
            if len(texts) == 3:
                break
        out[key] = texts
    return out


def _norm(x):
    return re.sub(r"\s+", " ", x or "").strip().lower()


def verify(ans: dict, texts) -> dict:
    """keep each value only if its quote is verbatim in the cited item and states it."""
    kept = {}
    src = {k: t for k, t in texts}
    for field in ("units", "stories", "height_feet", "density_bonus"):
        a = ans.get(field)
        if not isinstance(a, dict):
            continue
        v, q, s = a.get("value"), a.get("quote"), str(a.get("source") or "").strip()
        if v in (None, False, "") or not q or s not in src or _norm(q) not in _norm(src[s]):
            continue
        if field == "density_bonus":
            if v is True and "density bonus" in _norm(q):
                kept[field] = {"value": True, "quote": q, "source": s}
            continue
        try:
            n = int(float(v))
        except Exception:
            continue
        if _has_number(q, n):
            kept[field] = {"value": n, "quote": q, "source": s}
    return kept


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sonnet", choices=["submit", "status", "collect"])
    ap.add_argument("--pack", type=int, default=6)
    ap.add_argument("--db", default=str(V4))
    ap.add_argument("--retry", help="an evidence file: re-ask only its UNANSWERED projects (a run that hit max_tokens); "
                                    "written as a second, suffixed evidence file -- the first is never overwritten")
    a = ap.parse_args()
    state = OUT / ("sonnet_batch_state.json" if not a.retry else "sonnet_batch_state_retry.json")
    recs = project_items(Path(a.db))
    keys = sorted(recs)
    if a.retry:
        keys = sorted(set(json.load(open(a.retry))["unanswered"]) & set(recs))
        a.pack = min(a.pack, 2)
    groups = [keys[i:i + a.pack] for i in range(0, len(keys), a.pack)]
    print(f"{len(keys)} v4 projects the Board heard ({sum(len(v) for v in recs.values())} items)")

    def prompt(g):
        body = "\n\n".join(f"PROJECT {k}\n" + "\n".join(f"  [{s}] {t}" for s, t in recs[k]) for k in g)
        return (f"You are reading the Action Minutes of Berkeley's Zoning Adjustments Board for {len(g)} housing "
                f"projects. Judge each on its own text only.\n\n{DEFINITION}\n\nAnswer with a JSON array only, one object "
                f"per project, in order:\n[{{\"project\": <PROJECT key>, "
                + ", ".join(f"\"{f}\": {{\"value\": <...or null>, \"quote\": <exact words or null>, \"source\": <the "
                            f"bracketed item id without brackets, or null>}}" for f in ("units", "stories", "height_feet",
                                                                                         "density_bonus"))
                + f"}}]\n\n{body}")

    if a.dry_run:
        print(prompt(groups[0])[:2500])
        print(f"\n{len(groups)} requests, ~{sum(len(prompt(g)) for g in groups)/4/1e6:.2f}M input tokens. NOTHING ASKED.")
        return 0
    if a.sonnet == "submit":
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / ("groups.json" if not a.retry else "groups_retry.json")).write_text(json.dumps(groups))
        mr.batch_submit([{"custom_id": f"g{i}", "params": {"model": mr.BATCH_MODEL,
                          "max_tokens": (700 if not a.retry else 4000) * len(g) + 600,
                          "messages": [{"role": "user", "content": prompt(g)}]}} for i, g in enumerate(groups)], state)
        return 0
    if a.sonnet == "status":
        mr.batch_status(state)
        return 0
    if a.sonnet == "collect":
        groups = json.loads((OUT / ("groups.json" if not a.retry else "groups_retry.json")).read_text())
        rows, unanswered = [], []
        for cid, parsed, raw, _ in mr.batch_results(state):
            got = {str(x.get("project")): x for x in (parsed or []) if isinstance(x, dict)}
            for k in groups[int(cid[1:])]:
                if k not in got:
                    unanswered.append(k)
                    continue
                rows.append({"project_key": k, **verify(got[k], recs[k])})
        kept = {f: sum(1 for r in rows if f in r) for f in ("units", "stories", "height_feet", "density_bonus")}
        print(f"answers {len(rows)}; kept {kept}; unanswered {len(unanswered)}")
        mr.write_evidence(rows, "zab_items", DEFINITION, date=(None if not a.retry else
                          Path(a.retry).stem.split("_evidence_")[1] + "b"),
                          extra={"model": mr.BATCH_MODEL, "items": str(ITEMS.relative_to(ROOT)),
                                 "rule": "kept only if the quote is verbatim in the cited item and states the value",
                                 "unanswered": unanswered})
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
