#!/usr/bin/env python3
"""parse_zab_minutes.py -- the Zoning Adjustments Board's ACTIONS, read from its own Action Minutes.

John, 2026-10-07 (approved the deciding-body rule): the City's Planning workflow logs many Board decisions as a
"Staff Decision". The Board's minutes say what it decided, on which record, on which date. This reads every minutes
PDF listed in a ZAB harvest manifest (scripts/harvest_zab_documents.py), checks its SHA-256, and writes one row per
(meeting, item, record):

  data/derived/zab_actions_<manifest date>.jsonl
    {meeting_date, item, heading, record, record_cited, prefix_restored, action, action_text, vote, item_text,
     minutes_file, minutes_sha256, source}

Reading rules (never a guess):
  * an ITEM starts at a numbered heading ("6. 3030 Telegraph Ave – New Public Hearing") and runs to the next;
  * its RECORDS are the Planning record numbers in it. A number cited without its prefix after "Use Permit"
    ("Use Permit 2016-0101") gets the City's prefix for that year -- UP before 2015, ZP from 2015, when the City moved
    to Accela -- and is marked prefix_restored;
  * its ACTION is the first outcome word (approved, denied, continued, ...) after its "Vote:" line, or after "Action:"
    where there is no vote; an item whose action cannot be read keeps action = null;
  * the same meeting can come from both sources (berkeleyca.gov from 2021, the Clerk's Records Online from 2002), and
    a draft can sit beside the final: one row per (meeting, record, action) is kept, preferring a FINAL berkeleyca.gov
    file, then Records Online, then a draft.

  .venv/bin/python scripts/parse_zab_minutes.py [--manifest data/raw/zab/manifest_2026-10-06.csv]
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REC = re.compile(r"\b((?:ZP|UP|AUP|ZAB|DRSA|LMSAP|LMCA|PLN|ZC|MODUP|MOD|V)\d{4}-\d{4})\b")
BARE = re.compile(r"\bUse Permit\s*#?\s*(\d{4})-(\d{4})\b", re.I)
ITEM = re.compile(r"^\s{0,6}(\d{1,2})\.\s+(\S.{3,}?)\s*$", re.M)
OUTCOME = re.compile(r"\b(APPROVED|DENIED|CONTINUED|WITHDRAWN|UPHELD|DISMISSED|REMANDED|AFFIRMED|REVERSED|TABLED|"
                     r"NO ACTION|REFERRED)\b", re.I)
VOTE = re.compile(r"Vote:\s*([0-9]+(?:-[0-9]+){2,4})")


def items(text: str):
    heads = list(ITEM.finditer(text))
    for i, h in enumerate(heads):
        body = text[h.start(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        recs = {r: (r, False) for r in REC.findall(body)}
        for y, n in BARE.findall(body):
            k = ("ZP" if int(y) >= 2015 else "UP") + f"{y}-{n}"
            recs.setdefault(k, (f"{y}-{n}", True))
        if not recs:
            continue
        cut = body.find("Vote:") if "Vote:" in body else body.find("Action:")
        tail = body[cut:] if cut >= 0 else ""
        m = OUTCOME.search(tail)
        v = VOTE.search(body)
        yield {"item": h[1], "heading": re.sub(r"\s+", " ", h[2])[:120], "records": recs,
               "item_text": re.sub(r"\s+", " ", body)[:1800],      # what the Board heard: application, units, stories
               "action": m[1].upper() if m else None,
               "action_text": re.sub(r"\s+", " ", tail[m.start(): m.start() + 160]).strip() if m else None,
               "vote": v[1] if v else None}


def rank(row: dict) -> int:
    f = row["minutes_file"].lower()
    if row["source"] == "berkeleyca.gov" and "draft" not in f:
        return 0
    return 1 if row["source"] == "records_online" else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=sorted(glob.glob(str(ROOT / "data/raw/zab/manifest_*.csv")))[-1])
    a = ap.parse_args()
    man = Path(a.manifest)
    rows, bad = [], []
    for r in csv.DictReader(open(man)):
        if r["kind"] not in ("minutes", "minutes_records_online") or not r["meeting_date"]:
            continue
        f = ROOT / r["file"]
        b = f.read_bytes()
        if hashlib.sha256(b).hexdigest() != r["sha256"]:
            bad.append(r["file"])
            continue
        text = subprocess.run(["pdftotext", "-layout", str(f), "-"], capture_output=True, text=True).stdout
        src = "records_online" if r["kind"] == "minutes_records_online" else "berkeleyca.gov"
        for it in items(text):
            for rec, (cited, restored) in sorted(it["records"].items()):
                rows.append({"meeting_date": r["meeting_date"], "item": it["item"], "heading": it["heading"],
                             "record": rec, "record_cited": cited, "prefix_restored": restored,
                             "action": it["action"], "action_text": it["action_text"], "vote": it["vote"],
                             "item_text": it["item_text"],
                             "minutes_file": r["file"], "minutes_sha256": r["sha256"], "source": src})
    assert not bad, f"minutes changed since the manifest: {bad[:5]}"
    best = {}
    for row in rows:
        k = (row["meeting_date"], row["record"], row["action"])
        if k not in best or rank(row) < rank(best[k]):
            best[k] = row
    out = ROOT / "data/derived" / f"zab_actions_{man.stem.split('_', 1)[1]}.jsonl"
    with open(out, "w") as fh:
        for row in sorted(best.values(), key=lambda x: (x["meeting_date"], int(x["item"]), x["record"])):
            fh.write(json.dumps(row) + "\n")
    acts = {}
    for row in best.values():
        acts[row["action"]] = acts.get(row["action"], 0) + 1
    print(f"{len(rows)} item-records read, {len(best)} kept after de-duplication; actions {acts}; "
          f"{sum(r['prefix_restored'] for r in best.values())} with a restored prefix -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
