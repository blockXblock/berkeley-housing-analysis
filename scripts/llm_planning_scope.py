#!/usr/bin/env python3
r"""llm_planning_scope.py -- read every Berkeley PLANNING record and say whether it is a housing
development, against a written definition instead of a pattern.

WHY. The HOUSING regex kept failing by silent omission: `\bdwelling\b` cannot match "dwellings"
(ZP2022-0046, 166 of them), "townhouses" and spelled-out counts were absent, and PLN2026-0185 -- the
FIRST city filing for Berkeley's largest pipeline project, 618 units on the Ashby BART station block
-- said only "TOD development proposal", no housing word at all. English is not closable, so a pattern
over prose is a floor that looks like a census. John, 2026-09-28: use a model.

THE DEFINITION IS NOT IN THIS FILE. It is housing_rules.reading_rules.PLANNING_SCOPE (Gov. Code
65589.5(h)(2), verified current against leginfo 2026-09-28, plus John's units-stated-sufficiency
ruling) and it is stamped into the evidence file with its sha, so any later figure traces to the exact
wording that produced it. This script contributes only the QUESTION layer, the same division
llm_permit_effect.py uses.

WHAT IT DOES NOT DO. No database write. No re-run of the applied planning ingest -- a data error is a
new gated write, not a re-run (CLAUDE.md). It produces an evidence file and a disagreement report
against today's regex queue, for John to read before anything changes.

  --dry-run           show the payload and the projected cost, ask nothing
  --limit N           read N records (start here)
  --jev               Jev over every record (cheap, structured, a label + confidence)
  --report            compare a collected reading against the regex queue, both directions
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import model_readers as mr                                    # noqa: E402  THE model-call home
from housing_rules.planning_filter import DEV, HOUSING        # noqa: E402  DEV is form: still regex
from housing_rules.reading_rules import PLANNING_SCOPE        # noqa: E402  the written definition

OUT = ROOT / "scratch/2026-09-28_planning_scope"
CLASSES = {
    "housing_development":
        "This record is an application, or a step in one, for a project meeting the definition of a "
        "housing development project.",
    "housing_adjacent_not_development":
        "Housing is present but this record is not a development application: an inquiry about what "
        "is permitted, or a review of work on an existing building that creates no housing.",
    "not_housing":
        "Commercial, institutional, signage, telecommunications or public art. No housing.",
    "unknown":
        "The record's own text does not say enough to decide.",
}
UNITS = {
    "none_stated": "The record's text states no number of dwelling units.",
    "1": "The text states exactly one dwelling unit.",
    "2_to_9": "The text states between 2 and 9 dwelling units.",
    "10_to_49": "The text states between 10 and 49 dwelling units.",
    "50_or_more": "The text states 50 or more dwelling units.",
}
# What the city published on the record, and only that. Not another project at the same address, not
# CKAN -- reading either as evidence is the circularity bug CLAUDE.md names.
FIELDS = ("Record Number", "Record Type", "Project Name", "Description", "Status", "Date")


def records() -> dict[str, dict]:
    """every DEV Planning record from the list dumps, latest row per record number."""
    out: dict[str, dict] = {}
    for fn in glob.glob(str(ROOT / "data/raw/accela/date_range/Planning_*.jsonl")):
        for line in open(fn):
            try:
                d = json.loads(line)
            except Exception:
                continue
            n = str(d.get("Record Number") or "").strip()
            if n and DEV.match(n):
                out[n] = {k: d.get(k) for k in FIELDS}
    return out


def regex_queue(recs: dict[str, dict]) -> set[str]:
    """what the pattern currently believes, so the model's reading can be compared to it."""
    return {n for n, d in recs.items()
            if HOUSING.search(" ".join(str(d.get(f, "")) for f in
                                      ("Description", "Project Name", "Record Type")))}


def questions() -> dict:
    return {
        "scope": {"type": "choice",
                  "instructions": "Is this Berkeley Planning record an application for a housing "
                                  "development project?\n" + PLANNING_SCOPE,
                  "criteria": CLASSES},
        "units_stated": {"type": "choice",
                         "instructions": "How many dwelling units does THIS record's own text "
                                         "state? Report only what it states; never infer from an "
                                         "address or another project.\n" + PLANNING_SCOPE,
                         "criteria": UNITS},
    }


SONNET_Q = """You are reading {n} PLANNING records from the City of Berkeley. Judge each record on its
own; do not let one record inform another.

{rules}
Question, for EACH record: is that record an application, or a step in one, for a housing development
project as defined above?

Answer with a JSON array only, one object per record, in the same order:
[{{"record": <Record Number>,
   "scope": "housing_development" | "housing_adjacent_not_development" | "not_housing" | "unknown",
   "units_stated": <integer the record's own text states, or null if it states none>,
   "removes_units": <integer the text says are removed or eliminated, or 0>,
   "two_thirds_test": "met" | "not_met" | "not_evaluable",
   "reason": <one sentence that QUOTES the words you relied on>,
   "confidence": "high" | "medium" | "low"}}, ...]

Records:
{records}"""


def low_confidence(conf_floor: float) -> list[str]:
    """the records Jev was unsure about, from its own log -- read, never re-asked."""
    log = OUT / "jev_answers.jsonl"
    out = []
    for line in log.read_text().splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if "error" in r:
            continue
        try:
            c = float(r.get("scope_confidence"))
        except (TypeError, ValueError):
            c = 0.0
        if c < conf_floor:
            out.append(r["record"])
    return out


def sonnet(cmd: str, recs: dict, conf_floor: float, pack: int, dry: bool,
           tag: str = "", only: list | None = None) -> int:
    """`tag` keeps each batch's state in its own file, because one state file means one batch in
    flight: submitting a second pass while a retry was still running would have overwritten the batch
    id and lost 658 readings already paid for. `only` submits a named list of records instead of the
    low-confidence set -- the ADD rows deserve a second read whatever Jev's confidence was, since
    confidence cannot catch a confidently-wrong label (Jev called "BP15-0076. Residing." a housing
    development at 0.73, reading re-siding as residential)."""
    import hashlib
    import re as _re
    tag_suffix = f"_{tag}" if tag else ""
    state = OUT / f"sonnet_batch_state{tag_suffix}.json"
    ids_path = OUT / f"sonnet_ids{tag_suffix}.json"
    answers_path = OUT / "sonnet_answers.json"

    def already() -> set:
        """records ALREADY answered and stored -- never re-asked.

        Learned the expensive way: the first submission capped max_tokens at 400 per record, 64 of
        260 groups stopped at max_tokens (some returning NO text at all), and 658 of 2,594 records
        came back unparseable. Without a resume the retry would re-ask all 2,594 and pay for the
        1,936 that were already good. Same rule as the Jev runner: an errored row is not done, and a
        done row is never asked twice."""
        try:
            return {r["record"] for r in json.loads(answers_path.read_text()) if r.get("sonnet_scope")}
        except Exception:
            return set()

    if cmd == "submit":
        have = already()
        pool = only if only is not None else low_confidence(conf_floor)
        want = [n for n in pool if n in recs and n not in have]
        if have:
            print(f"{len(have)} already answered and stored; asking only the rest")
        groups = [want[i:i + pack] for i in range(0, len(want), pack)]
        prompt_hash = hashlib.sha256((SONNET_Q + PLANNING_SCOPE).encode()).hexdigest()[:12]
        reqs, ids = [], {}
        for i, g in enumerate(groups):
            body = "\n".join(json.dumps(recs[n], separators=(",", ":")) for n in g)
            text = SONNET_Q.format(n=len(g), rules=PLANNING_SCOPE, records=body)
            cid = f"g{i:05d}"
            reqs.append({"custom_id": cid,
                         # 400/record was NOT enough: a quoted reason plus five fields ran to ~330
                         # output tokens per record, and any group that thought before answering hit
                         # the cap and returned nothing at all. Measured 3,282 output tokens per
                         # 10-record group, so budget double that and let the cap be slack, not a
                         # ceiling the answer has to fit under.
                         "params": {"model": mr.BATCH_MODEL, "max_tokens": 800 * len(g) + 800,
                                    "messages": [{"role": "user", "content": text}]}})
            ids[cid] = g
        ids_path.write_text(json.dumps({"prompt_hash": prompt_hash, "ids": ids,
                                        "conf_floor": conf_floor}, indent=1))
        print(f"{len(want)} records {'named' if only is not None else f'below {conf_floor} confidence'}"
              f" -> {len(reqs)} requests "
              f"of {pack}; prompt {prompt_hash}")
        if dry:
            print(reqs[0]["params"]["messages"][0]["content"][:2000])
            return 0
        mr.batch_submit(reqs, state)
        return 0
    if cmd == "status":
        mr.batch_status(state)
        return 0
    # collect
    meta = json.loads(ids_path.read_text())
    rows, bad, tin, tout = [], [], 0, 0
    for cid, got, txt, usage in mr.batch_results(state):
        group = meta["ids"].get(cid, [])
        if usage:
            tin += usage.input_tokens
            tout += usage.output_tokens
        if got is None:
            bad += [{"record": n, "why": txt[:120]} for n in group]
            continue
        got = got if isinstance(got, list) else [got]
        by = {str(g.get("record")): g for g in got if isinstance(g, dict)}
        for n in group:
            g = by.get(n)
            if not g:
                bad.append({"record": n, "why": "absent from the answer array"})
                continue
            rows.append({"record": n, "sonnet_scope": g.get("scope"),
                         "sonnet_units_stated": g.get("units_stated"),
                         "sonnet_removes_units": g.get("removes_units"),
                         "two_thirds_test": g.get("two_thirds_test"),
                         "reason": g.get("reason"), "sonnet_confidence": g.get("confidence"),
                         "prompt_hash": meta["prompt_hash"], "model": mr.BATCH_MODEL})
    # MERGE, never overwrite: a retry batch covers only what failed, so overwriting would discard
    # every reading the previous batch got right.
    kept = {}
    try:
        for r in json.loads((OUT / "sonnet_answers.json").read_text()):
            if r.get("sonnet_scope"):
                kept[r["record"]] = r
    except Exception:
        pass
    before = len(kept)
    for r in rows:
        if r.get("sonnet_scope"):
            kept[r["record"]] = r
    (OUT / "sonnet_answers.json").write_text(json.dumps(list(kept.values()), indent=1))
    print(f"collected {len(rows)} readings ({len(bad)} unparsed/absent); "
          f"store {before} -> {len(kept)}; tokens in {tin:,} out {tout:,}")
    if bad:
        for b in bad[:10]:
            print("   MISSING", b)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--jev", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--write-evidence", action="store_true")
    ap.add_argument("--sonnet", choices=["submit", "status", "collect"], default=None,
                    help="second read of the records Jev was unsure about (< --conf), via the Batch "
                         "API. A single reader's label is not evidence: on permit_effect's hard "
                         "subset Jev and Sonnet disagreed 2,625 times out of 5,773.")
    ap.add_argument("--conf", type=float, default=0.70)
    ap.add_argument("--pack", type=int, default=10, help="records per request")
    ap.add_argument("--tag", default="", help="keeps this batch's state in its own file so two "
                                             "batches can be in flight at once")
    ap.add_argument("--only-file", default=None,
                    help="a file of record numbers, one per line, to read instead of the "
                         "low-confidence set")
    args = ap.parse_args()

    recs = records()
    rq = regex_queue(recs)
    order = sorted(recs)
    print(f"{len(recs):,} DEV Planning records · the regex queue holds {len(rq):,} of them "
          f"(a FLOOR, not a census)")
    todo = order[:args.limit] if args.limit else order

    if args.sonnet:
        only = ([l.strip() for l in open(args.only_file) if l.strip()]
                if args.only_file else None)
        return sonnet(args.sonnet, recs, args.conf, args.pack, args.dry_run, args.tag, only)

    if args.dry_run:
        n = order[0]
        print(f"\ndefinition: reading_rules.PLANNING_SCOPE, {len(PLANNING_SCOPE)} chars")
        print(f"one payload, {n}:")
        print(json.dumps({"state": recs[n], "questions": {k: {"type": v["type"],
              "instructions": v["instructions"][:70] + "...", "criteria": list(v["criteria"])}
              for k, v in questions().items()}}, indent=1)[:1200])
        per = len(PLANNING_SCOPE) * 2 / 4 + 120          # definitions dominate; ~4 chars per token
        print(f"\n~{per:.0f} input tokens per record x {len(recs):,} records "
              f"= ~{per * len(recs) / 1e6:.2f}M tokens. At Jev's $0.042/M that is "
              f"~${per * len(recs) / 1e6 * 0.042:.2f}.")
        print("NOTHING ASKED.")
        return 0

    if args.jev:
        q = questions()

        def ask(n):
            r = mr.jev_ask(recs[n], q)
            if "answers" not in r:
                return {"record": n, "error": r.get("error", "no answers")}
            a = r["answers"]
            return {"record": n, "model": r.get("model"),
                    "scope": a["scope"]["choice"], "scope_confidence": a["scope"].get("confidence"),
                    "units_stated": a["units_stated"]["choice"],
                    "units_confidence": a["units_stated"].get("confidence"),
                    "regex_said_housing": n in rq}

        rows = mr.run_resumable(todo, ask, OUT / "jev_answers.jsonl", id_field="record")
        if args.write_evidence:
            mr.write_evidence([r for r in rows if "error" not in r], "planning_scope",
                              PLANNING_SCOPE,
                              extra={"source": "data/raw/accela/date_range/Planning_*.jsonl",
                                     "dev_records": len(recs), "regex_queue": len(rq)})
        report(rows, recs, rq)
        return 0

    if args.report:
        log = OUT / "jev_answers.jsonl"
        rows = [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
        report(rows, recs, rq)
        return 0

    print(__doc__)
    return 2


def report(rows, recs, rq) -> None:
    """the two directions are NOT symmetric: the regex queue is a floor, so additions are candidate
    real misses and subtractions are candidate model errors. Both get counted; neither gets applied."""
    import collections
    ok = [r for r in rows if "error" not in r]
    if not ok:
        print("no answers yet")
        return
    by = collections.Counter(r["scope"] for r in ok)
    print(f"\nread {len(ok):,} records")
    for k, v in by.most_common():
        print(f"  {v:5}  {k}")
    model_housing = {r["record"] for r in ok if r["scope"] == "housing_development"}
    read = {r["record"] for r in ok}
    add = sorted(model_housing - rq)
    drop = sorted((rq & read) - model_housing)
    print(f"\nMODEL-ONLY (the regex missed these -- each is a candidate REAL MISS): {len(add)}")
    for n in add[:25]:
        print(f"   {n:16} {str(recs[n].get('Description'))[:96]}")
    print(f"\nREGEX-ONLY (the model says not a housing development -- candidate MODEL ERROR, the "
          f"direction that would SHRINK coverage): {len(drop)}")
    for n in drop[:25]:
        print(f"   {n:16} {str(recs[n].get('Description'))[:96]}")
    # Jev returns a NUMERIC confidence (0.51 .. 1.0), not "high"/"medium"/"low". My first version
    # string-matched the labels and reported 0 low-confidence records out of 25 whose confidences
    # ran from 0.51 to 1.0 -- a filter that cannot fire, which is the same defect shape as a wrong
    # grep key returning a confident zero.
    def conf(r):
        c = r.get("scope_confidence")
        try:
            return float(c)
        except (TypeError, ValueError):
            return {"high": 0.9, "medium": 0.6, "low": 0.3}.get(str(c).lower(), 0.0)
    low = sorted((conf(r), r["record"], r["scope"]) for r in ok if conf(r) < 0.7)
    print(f"\nconfidence below 0.70: {len(low)} of {len(ok)} -- the subset worth a second read by "
          f"Sonnet (Jev's confidence is numeric)")
    for c, n, sc in low[:15]:
        print(f"   {c:.2f}  {n:16} {sc}")
    # The category John needs to see: mixed-use with NO unit count. Units-stated sufficiency cannot
    # resolve these, so they land in unknown by the rule as written, and they are mid-size projects.
    mixed = [r["record"] for r in ok if r["scope"] == "unknown"
             and "mixed" in str(recs.get(r["record"], {}).get("Description", "")).lower()]
    print(f"\nunknown AND the text says mixed-use: {len(mixed)} -- a definition question for John, "
          f"not a model error (no units stated, so units-stated sufficiency cannot decide)")
    for n in mixed[:12]:
        print(f"   {n:16} {str(recs[n].get('Description'))[:88]}")
    print("\nNOTHING WRITTEN to any database. John reviews both directions.")


if __name__ == "__main__":
    raise SystemExit(main())
