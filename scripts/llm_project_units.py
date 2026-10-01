#!/usr/bin/env python3
r"""llm_project_units.py -- read how many dwelling units an APPLICATION-ONLY project proposes, from the City's own text.

Phase 6 decision D4 (John, 2026-09-30). A project with buildings takes its units from its building permits; a project
that is still only an application (entitled, in review, withdrawn) has no building yet, so its units can only come
from what its records STATE. The first scope reading gave buckets ("2_to_9"), not counts. A model reads each
application's text against the definition below; an answer is kept only if its quote appears VERBATIM in the cited
record AND contains the number it reports -- so a count cannot be invented or inferred.

READ ONCE, STORE, LOOK UP (scripts/model_readers.py): data/derived/project_units_evidence_<date>.json keyed by the
project's anchor record. Nothing here writes to a database.

  .venv/bin/python scripts/llm_project_units.py --dry-run [--db BUILD]
  .venv/bin/python scripts/llm_project_units.py --sonnet submit|status|collect [--db BUILD]
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

V4 = ROOT / "databases/berkeley_housing_v4.db"
OUT = ROOT / "scratch/2026-09-30_units"

DEFINITION = """Report the number of NEW DWELLING UNITS this housing application proposes, as its own text states it.
- Count dwelling units (apartments, condominiums, townhouses, houses, ADUs, JADUs, live-work units if the text calls them
  dwelling or residential units). Do NOT count beds, rooms, group-living rooms, hotel rooms or parking spaces.
- If the text states a total ("50 residential units, 6 ADUs" -> 56 only if it says so; otherwise report 50 and quote it),
  report the number the text states for the project's new dwellings; never add numbers the text does not add.
- If the text proposes a CHANGE to an earlier approval ("increase from 66 to 73 units"), report the NEW total it states (73).
- If units are being removed only, or no count is stated, answer null.
Copy the exact words that state the number."""


def project_texts(dbp=V4):
    db = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
    planning = {k: json.loads(p) for k, p in db.execute(
        "SELECT source_record_key, raw_payload FROM events WHERE event_type_code='planning_filed'")}
    out = {}
    for pid, notes in db.execute("SELECT project_id, notes FROM projects"):
        n = json.loads(notes)
        if not n.get("anchor") or n.get("units", 0) > 0:
            continue                                  # buildings carry their own units
        key = n["anchor"]
        texts = []
        for rec in [key] + [r for r in (n.get("records") or []) if r != key][:5]:
            t = (planning.get(rec, {}).get("description") or "").strip()
            if t:
                texts.append((rec, f"{planning[rec].get('record_type')}: {t}"[:700]))
        if texts:
            out[key] = texts
    return out


def verify(ans, texts):
    """keep the count only if the quote is verbatim in the cited text and contains the number."""
    n, q, s = ans.get("units"), ans.get("quote"), str(ans.get("source") or "").strip().strip("[]").strip()
    if n is None or not q:
        return None
    try:
        n = int(n)
    except Exception:
        return None
    norm = lambda x: re.sub(r"\s+", " ", x or "").strip().lower()
    for k, t in texts:
        if k == s and norm(q) in norm(t) and re.search(rf"(?<!\d){n}(?!\d)", q.replace(",", "")):
            return {"units": n, "quote": q, "source": s}
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sonnet", choices=["submit", "status", "collect"])
    ap.add_argument("--pack", type=int, default=8)
    ap.add_argument("--db", default=str(V4))
    a = ap.parse_args()
    state = OUT / "sonnet_batch_state.json"
    recs = project_texts(Path(a.db))
    keys = sorted(recs)
    groups = [keys[i:i + a.pack] for i in range(0, len(keys), a.pack)]
    print(f"{len(keys)} application-only projects with text")

    def prompt(g):
        body = "\n\n".join(f"PROJECT {k}\n" + "\n".join(f"  [{s}] {t}" for s, t in recs[k]) for k in g)
        return (f"You are reading City of Berkeley Planning records for {len(g)} housing applications. Judge each on its "
                f"own text only.\n\n{DEFINITION}\n\nAnswer with a JSON array only, one object per project, in order:\n"
                f"[{{\"project\": <PROJECT key>, \"units\": <integer or null>, \"quote\": <exact words, or null>, "
                f"\"source\": <the record key the quote is from, without brackets, or null>}}]\n\n{body}")

    if a.dry_run:
        print(prompt(groups[0])[:2000])
        print(f"\n{len(groups)} requests, ~{sum(len(prompt(g)) for g in groups)/4/1e6:.2f}M input tokens. NOTHING ASKED.")
        return 0
    if a.sonnet == "submit":
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "groups.json").write_text(json.dumps(groups))
        mr.batch_submit([{"custom_id": f"g{i}", "params": {"model": mr.BATCH_MODEL, "max_tokens": 600 * len(g) + 600,
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
                rejected += bool(got[k].get("units") is not None and not v)
                rows.append({"project_key": k, **(v or {"units": None})})
        print(f"answers {len(rows)}; with a verified count {sum(1 for r in rows if r['units'] is not None)}; "
              f"proposed but rejected {rejected}; unanswered {len(unanswered)}")
        mr.write_evidence(rows, "project_units", DEFINITION,
                          extra={"model": mr.BATCH_MODEL, "rule": "kept only if the quote is verbatim and contains the number",
                                 "unanswered": unanswered})
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
