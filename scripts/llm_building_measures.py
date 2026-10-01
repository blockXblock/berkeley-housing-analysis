#!/usr/bin/env python3
r"""llm_building_measures.py -- read a project's building MEASURES from the City's own text: gross square feet, parking
spaces, storeys, height in feet.

Phase 6 (John, 2026-09-30): square footage and parking are KEPT (the earlier "drop" rested only on v2's empty column)
and heights are built from sources (D7). The measures are stated in prose -- "construct a 134,409 square-foot,
eight-story (89 feet-2 inches) mixed-use building", "NEW 36,554 SQFT MIXED USE BLDG", "63 ground-level parking spaces"
-- so a model reads them against the definition below. Each number is KEPT only if its quote appears VERBATIM in the
cited record AND contains the number (for storeys, a number word counts: "six-story" supports 6). Nothing inferred.

Read per PROJECT from its Planning descriptions and its master building-permit descriptions; keyed by the project's
stable key. Evidence: data/derived/building_measures_evidence_<date>.json. No database write.

  .venv/bin/python scripts/llm_building_measures.py --dry-run [--db BUILD]
  .venv/bin/python scripts/llm_building_measures.py --sonnet submit|status|collect [--db BUILD]
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
OUT = ROOT / "scratch/2026-09-30_measures"
MEASURES = ("gross_sqft", "parking_spaces", "stories", "height_feet")
WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                    "fifteen sixteen seventeen eighteen nineteen twenty".split())}

DEFINITION = """Report the NEW building's measures that the record's own text states, for this housing project:
- gross_sqft: the building's total floor area in square feet ("134,409 square-foot", "36,554 SQFT"). If the text gives
  only part (e.g. residential square feet, or commercial space), report null for gross_sqft. Not lot size.
- parking_spaces: the number of vehicle parking spaces the project provides ("63 ground-level parking spaces"). Bicycle
  parking does not count. "No parking" or "zero parking" is 0.
- stories: number of stories of the new building ("six-story", "8-story", "5 stories").
- height_feet: the building's height in feet ("70 feet", "89 feet- 2 inches" -> 89).
If several buildings are described, report the measures for the LARGEST new building and say so in the quote.
Report each measure only if stated; otherwise null. For each, copy the exact words that state it."""


def project_texts(dbp=V4):
    db = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
    planning = {k: json.loads(p) for k, p in db.execute(
        "SELECT source_record_key, raw_payload FROM events WHERE event_type_code='planning_filed'")}
    permit_desc = dict(db.execute("SELECT source_record_key, MAX(raw_description) FROM events "
                                  "WHERE event_type_code LIKE 'permit_%' GROUP BY 1"))
    masters = {sid: json.loads(n)["master_permits"] for sid, n in db.execute("SELECT structure_id, notes FROM structures")}
    out = {}
    for pid, notes in db.execute("SELECT project_id, notes FROM projects"):
        n = json.loads(notes)
        key = n.get("project_key")
        if not key or n.get("anchor_role") == "outside_city_permitting":
            continue
        sids = [s for (s,) in db.execute("SELECT structure_id FROM project_structures WHERE project_id=?", (pid,))]
        texts = []
        for rec in ([n["anchor"]] if n.get("anchor") else []) + [r for r in (n.get("records") or []) if r != n.get("anchor")][:3]:
            t = (planning.get(rec, {}).get("description") or "").strip()
            if t:
                texts.append((rec, t[:700]))
        for m in [m for s in sids for m in masters[s]][:3]:
            if permit_desc.get(m):
                texts.append((m, permit_desc[m][:500]))
        if texts:
            out[key] = texts
    return out


def _has_number(q: str, n: int) -> bool:
    q2 = q.replace(",", "").lower()
    if re.search(rf"(?<![\d.]){n}(?![\d])", q2):
        return True
    return any(WORDS.get(w) == n for w in re.findall(r"[a-z]+", q2))


def verify(ans, texts):
    norm = lambda x: re.sub(r"\s+", " ", x or "").strip().lower()
    src = {k: norm(t) for k, t in texts}
    kept = {}
    for m in MEASURES:
        it = ans.get(m) or {}
        v, q, s = it.get("value"), it.get("quote"), str(it.get("source") or "").strip().strip("[]").strip()
        try:
            v = int(float(v)) if v is not None else None
        except Exception:
            v = None
        if v is not None and q and s in src and norm(q) in src[s] and _has_number(q, v):
            kept[m] = {"value": v, "quote": q, "source": s}
    return kept


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sonnet", choices=["submit", "status", "collect"])
    ap.add_argument("--pack", type=int, default=6)
    ap.add_argument("--db", default=str(V4))
    a = ap.parse_args()
    state = OUT / "sonnet_batch_state.json"
    recs = project_texts(Path(a.db))
    keys = sorted(recs)
    groups = [keys[i:i + a.pack] for i in range(0, len(keys), a.pack)]
    print(f"{len(keys)} projects with text")

    def prompt(g):
        body = "\n\n".join(f"PROJECT {k}\n" + "\n".join(f"  [{s}] {t}" for s, t in recs[k]) for k in g)
        shape = ", ".join(f"\"{m}\": {{\"value\": <integer or null>, \"quote\": <exact words or null>, \"source\": "
                          f"<record key without brackets, or null>}}" for m in MEASURES)
        return (f"You are reading City of Berkeley records for {len(g)} housing projects. Judge each on its own text."
                f"\n\n{DEFINITION}\n\nAnswer with a JSON array only, one object per project, in order:\n"
                f"[{{\"project\": <PROJECT key>, {shape}}}]\n\n{body}")

    if a.dry_run:
        print(prompt(groups[0])[:2200])
        print(f"\n{len(groups)} requests, ~{sum(len(prompt(g)) for g in groups)/4/1e6:.2f}M input tokens. NOTHING ASKED.")
        return 0
    if a.sonnet == "submit":
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "groups.json").write_text(json.dumps(groups))
        mr.batch_submit([{"custom_id": f"g{i}", "params": {"model": mr.BATCH_MODEL, "max_tokens": 900 * len(g) + 800,
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
                kept = verify(got[k], recs[k])
                rejected += sum(1 for m in MEASURES if (got[k].get(m) or {}).get("value") is not None) - len(kept)
                rows.append({"project_key": k, **kept})
        print(f"answers {len(rows)}; " + "; ".join(f"{m} {sum(1 for r in rows if m in r)}" for m in MEASURES)
              + f"; values rejected (not verbatim / number not in quote) {rejected}; unanswered {len(unanswered)}")
        mr.write_evidence(rows, "building_measures", DEFINITION,
                          extra={"model": mr.BATCH_MODEL, "rule": "kept only if the quote is verbatim and contains the number",
                                 "unanswered": unanswered})
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
