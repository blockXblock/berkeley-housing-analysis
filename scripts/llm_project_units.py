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
OUT = ROOT / "scratch/2026-10-03_units"

from housing_rules.reading_rules import DEFINITIONS as HCD_DEFINITIONS  # noqa: E402

# 2026-10-03 (John approved): the question now uses HCD's own definitions (housing_rules.reading_rules), the same text
# every permit reading uses. The 2026-10-01 definition had its own blanket exclusion of "hotel rooms, group-living
# rooms", stricter than HCD, which counts SRO rooms that are separate living quarters (2427 San Pablo: "70
# single-occupancy rooms ... for a total of 78 units" read as 8).
DEFINITION = HCD_DEFINITIONS + """

QUESTION. Report the number of NEW DWELLING UNITS (housing units under the definitions above) this housing
application proposes, as its own text states it.
- If the text states a total ("50 residential units, 6 ADUs" -> 56 only if it says so; otherwise report 50 and quote it),
  report the number the text states for the project's new dwellings; never add numbers the text does not add. Where the
  text itself totals rooms and apartments as units ("... for a total of 78 units"), report that total.
- If the text proposes a CHANGE to an earlier approval ("increase from 66 to 73 units"), report the NEW total it states (73).
- Group quarters (student dormitories, beds) are not dwelling units: answer null for them.
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


WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                    "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}


def _has_number(q: str, n: int) -> bool:
    """the quote states n, in digits or as a number word ("three dwelling units") -- the same test the measures use."""
    q2 = q.replace(",", "").lower()
    return bool(re.search(rf"(?<![\d.]){n}(?!\d)", q2)) or any(WORDS.get(w) == n for w in re.findall(r"[a-z]+", q2))


# BY DEFINITION (John, 2026-10-01): a count the words fix without a numeral. A quote naming ONE dwelling (an ADU, JADU,
# dwelling unit, single-family dwelling, residence, cottage) and stating no other number is 1; duplex / triplex /
# fourplex are 2 / 3 / 4. Tagged read_as=by_definition so it can always be told apart from a count the City wrote out.
_PLEX = {"duplex": 2, "triplex": 3, "tri-plex": 3, "fourplex": 4, "four-plex": 4, "quadplex": 4}
_ONE = re.compile(r"\b(adu|jadu|sfd|accessory dwelling unit|dwelling unit|single[- ]family (?:home|residence|dwelling|house)|"
                  r"residence|cottage|residential unit|live[- ]work unit|unit|house|home)\b")


def _by_definition(q: str):
    ql = q.lower()
    # a number word that sizes the BUILDING, not the dwellings ("two-story", "three-bedroom") is not a second count
    ql = re.sub(r"\b[a-z]+-(?:story|stories|storey|bed|bedroom|bath|car)\b", " ", ql)
    if re.search(r"\d", ql.replace("sq", "")) and re.search(r"\b\d+\s*(units?|dwellings?|adus?)\b", ql):
        return None                                   # a count is written -- "stated" decides, not this rule
    if any(WORDS.get(w, 0) > 1 for w in re.findall(r"[a-z]+", ql)) or re.search(r"\b(units|dwellings|adus|homes|houses)\b", ql):
        return None                                   # another number or a plural: not one dwelling
    plex = [v for w, v in _PLEX.items() if re.search(rf"\b{w}\b", ql)]
    if len(plex) == 1:
        return plex[0]
    return 1 if _ONE.search(ql) else None


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
        if k == s and norm(q) in norm(t) and _has_number(q, n):
            return {"units": n, "quote": q, "source": s, "read_as": "stated"}
        if k == s and norm(q) in norm(t) and _by_definition(q) == n:
            return {"units": n, "quote": q, "source": s, "read_as": "by_definition"}
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
