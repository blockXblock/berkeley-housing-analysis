#!/usr/bin/env python3
"""harvest_capdetail.py -- HARVESTER stage: fetch CapDetail for the housing Planning records and
keep the PROCESSING STATUS block the inspection harvester discards.

WHY. v2 can say when an application was FILED and when it was ENTITLED, but the step between --
the city ACCEPTING the application as complete, after each department's review -- has only ever
been inferred. It is not an inference: the city publishes it, per record, with the due date it set
itself, the disposition, and the staff member who signed it. 14,936 Planning capIDs are held and
~95 had been visited, all by hand (data/raw/accela_status/*.txt). This fetches the housing subset.

SCOPE. The record set is the SAME filter the Planning ingest already uses -- DEV (record-number
prefix) + HOUSING (language) from housing_rules.planning_filter, IMPORTED, not
re-typed. 1,786 records (1,746 before the plural fix), all with a capdetail_href.

READ-ONLY. Fetches a public portal and writes gzipped HTML + one JSONL row per record under
scratch/. No DB is opened. Any v2/v4 write is a separate gated step.

DISCIPLINE.
  * Resumable: a record whose .html.gz already exists is skipped, so the run can be stopped and
    restarted; --force refetches.
  * "A 0-result is NOT evidence of absence until retried" (CLAUDE.md): a page yielding no workflow
    rows is retried once, and the outcome is recorded as retried_empty so a real absence is
    distinguishable from portal flakiness.
  * Polite: a configurable delay between records, one browser reused, no parallelism.
  * APNs are canonicalised ONLY by housing_rules.to_canonical_apn; apn_raw is kept unmutated.

RUN
  .venv/bin/python scripts/harvest_capdetail.py --limit 12          # smoke test first
  .venv/bin/python scripts/harvest_capdetail.py                     # full 1,746
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from housing_rules import to_canonical_apn          # noqa: E402  THE canon (never a local copy)
from housing_rules.planning_record import role      # noqa: E402  the canon record-role rule
from parse_capdetail import parse_capdetail         # noqa: E402

BASE = "https://aca-prod.accela.com"
OUTDIR = ROOT / "scratch/2026-09-26_capdetail"


def _filters():
    """DEV + HOUSING from the CANON, housing_rules.planning_filter.

    These used to be read out of scripts/migration/ingest_planning_scope_a.py (now
    scripts/superseded/migration__ingest_planning_scope_a.py) by importing that
    applied one-time write for its module-level regexes. That was better than copying them, and it
    was still wrong: the pattern had a FALSE NEGATIVE (`\bdwelling\b` cannot match the plural
    "dwellings") which excluded ZP2022-0046 -- 3000 Shattuck, 10 storeys, 166 dwellings -- from this
    very queue. A rule with no canonical home cannot be tested; the corrected pair now lives in
    housing_rules with the failing case pinned as a test.
    """
    from housing_rules.planning_filter import DEV, HOUSING
    return DEV, HOUSING


def queue(named: set[str] | None = None) -> list[dict]:
    """The housing records by the canon filter, or, with `named`, exactly those record numbers.

    `named` exists because the filter is no longer the scope authority: corrections/v4/
    planning_scope_rulings.csv (John, 2026-09-29) includes 44 records the regex never admitted, so
    they were never fetched. A named record is taken from the same list dumps, filter bypassed; one
    that is absent or has no capdetail_href is reported by the caller, never silently skipped."""
    DEV, HOUSING = _filters()
    recs: dict[str, dict] = {}
    for fn in glob.glob(str(ROOT / "data/raw/accela/date_range/Planning_*.jsonl")):
        for line in open(fn):
            try:
                d = json.loads(line)
            except Exception:
                continue
            n = str(d.get("Record Number") or "").strip()
            if n and n not in recs:
                recs[n] = d
    out = []
    for n, d in sorted(recs.items()):
        if named is not None:
            if n in named and d.get("capdetail_href"):
                out.append({"record": n, "href": d["capdetail_href"],
                            "record_type": d.get("Record Type"), "list_status": d.get("Status"),
                            "list_date": d.get("Date")})
            continue
        if not DEV.match(n):
            continue
        blob = " ".join(str(d.get(f, "")) for f in ("Description", "Project Name", "Record Type"))
        if not HOUSING.search(blob):
            continue
        if d.get("capdetail_href"):
            out.append({"record": n, "href": d["capdetail_href"],
                        "record_type": d.get("Record Type"), "list_status": d.get("Status"),
                        "list_date": d.get("Date")})
    return out


def fetch(page, href: str, settle_ms: int) -> str:
    """CapDetail HTML with the AJAX-filled workflow block actually PRESENT.

    Processing Status sits in a HIDDEN tab, so page.inner_text() cannot see it; the HTML is what
    carries it, and ExpandWorkflowSection() fills it after domcontentloaded without any click.

    Waiting on `#divProcessingTable tr` is NOT enough and was measured costing 40% of records a
    needless retry (2026-09-26): that selector matches the PLACEHOLDER row that exists before the
    AJAX returns, so the page was captured empty, parsed as empty, and only the retry -- a second
    full fetch -- got the data. Waiting for the workflow TEXT instead makes a populated record
    fast, and leaves the timeout to be paid only by records that genuinely have no workflow.
    """
    page.goto(BASE + href, wait_until="domcontentloaded")
    try:
        page.wait_for_function(
            """() => {
                 const d = document.getElementById('divProcessingTable');
                 return !!d && /Due on|Marked as/.test(d.textContent);
               }""",
            timeout=settle_ms)
    except Exception:
        pass          # genuinely-empty records land here; the caller's retry still applies
    return page.content()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="stop after N records (smoke test)")
    ap.add_argument("--delay", type=float, default=2.5, help="seconds between records")
    ap.add_argument("--settle", type=int, default=15000, help="ms to wait for the workflow block")
    ap.add_argument("--force", action="store_true", help="refetch records already on disk")
    ap.add_argument("--out", default=None)
    ap.add_argument("--records", default=None,
                    help="file of record numbers (one per line) to fetch instead of the filter's queue")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    named = None
    if args.records:
        named = {l.strip() for l in open(args.records) if l.strip()}
    q = queue(named)
    if named is not None:
        missing = sorted(named - {r["record"] for r in q})
        if missing:
            print(f"NOT IN THE LIST DUMPS (or no capdetail_href), not fetched: {missing}", flush=True)
    outdir = pathlib.Path(args.out) if args.out else OUTDIR
    (outdir / "pages").mkdir(parents=True, exist_ok=True)
    jsonl = outdir / "capdetail_parsed.jsonl"
    # An append-only ledger of VERIFIED absences. Absence is not data, so it is not inferred from a
    # blank page -- it is recorded only after a strong look (long wait, fresh session) found the
    # workflow table RENDERED and EMPTY, with the evidence kept. Without this, the resume rule
    # "an empty page never counts as done" would re-attempt every genuinely-empty record on every
    # run, and Pre-Applications alone would cost hours of pure timeout each time.
    ledger_path = outdir / "verified_empty.json"
    try:
        ledger = json.loads(ledger_path.read_text())
    except Exception:
        ledger = {}

    def already_have(rec: str) -> bool:
        """A saved page counts as DONE only if it actually contains a workflow.

        The harvester writes the page whether or not the parse found anything, and resume skips
        records whose page exists -- so an empty capture would become PERMANENT, immune to the
        retry rule, and indistinguishable from a record that truly has no workflow. That happened:
        DRCP2015-0002 was cached with zero tasks on 2026-09-26 and a refetch on a fresh session
        returned 5 ("2597 Telegraph DR for 10 units bldg.", Withdrawn). A genuinely-empty record is
        re-attempted on each run, which costs a timeout and is the right price for not fossilising
        a false absence (CLAUDE.md: a 0-result is not evidence of absence until retried).
        """
        f = outdir / "pages" / f"{rec}.html.gz"
        if not f.exists():
            return False
        if rec in ledger:
            return True            # a RECORDED absence, with evidence -- not an assumed one
        try:
            return "Marked as" in gzip.decompress(f.read_bytes()).decode("utf-8", "replace")
        except Exception:
            return False

    todo = [r for r in q if args.force or not already_have(r["record"])]
    if args.limit:
        todo = todo[:args.limit]
    print(f"queue {len(q)} housing Planning records · {len(todo)} to fetch "
          f"· out {outdir}", flush=True)

    ok = empty = retried_ok = failed = 0
    t0 = time.time()
    with sync_playwright() as p, open(jsonl, "a") as sink:
        b = p.chromium.launch(headless=True)
        def new_page():
            """A fresh page, with asset blocking that does NOT route every request through Python.

            Measured 2026-09-26: `route("**/*", ...)` sped a 12-record run up but DEGRADED a long
            one badly -- by ~100 navigations on one page, 73% of records were failing the first
            attempt and passing on a retry, pushing 4.2s/rec to 18.9s/rec and the ETA past 8 hours.
            The same records loaded first-try in under 4s in a fresh browser, so the cause was the
            harvester, not the portal or the record type: every HTML and XHR request was making a
            round-trip into a Python callback. Blocking by URL PATTERN keeps the AJAX that fills the
            workflow block out of Python entirely, and the page is recycled periodically so nothing
            accumulates across a 1,700-record run.
            """
            pg = b.new_page()
            pg.set_default_timeout(45000)
            pg.route(re.compile(r"\.(png|jpe?g|gif|svg|ico|css|woff2?|ttf|eot|mp4)(\?|$)", re.I),
                     lambda r: r.abort())
            return pg

        for i, r in enumerate(todo, 1):
            pg = new_page()          # per record: the session degrades at ~4 views, see new_page()
            rec, note = r["record"], ""
            try:
                # Pre-Applications publish NO workflow dispositions -- verified 2026-09-26 on
                # PLN2018-0048 / PLN2020-0001 / PLN2016-0037, fresh session and a 30s wait each:
                # divProcessingTable renders and is empty. They still get a real look, just not
                # the full patience owed to a record type that does publish one.
                settle = 6000 if role(r.get("record_type")) == "pre_application" else args.settle
                h = fetch(pg, r["href"], settle)
                parsed = parse_capdetail(h)
                if not parsed["processing_status"]:
                    # The retry must be STRONGER than the first attempt, not a repeat of it. A
                    # measured false absence (DRCF2018-0007, 2026-09-26: 4 tasks reported as 0)
                    # came from a short settle, and a retry at the same settle reproduced the
                    # error instead of correcting it. Double the patience on the second look.
                    time.sleep(args.delay)
                    try:
                        pg.close()
                    except Exception:
                        pass
                    pg = new_page()          # a retry on the SAME session is not a retry
                    h = fetch(pg, r["href"], settle * 2)
                    parsed = parse_capdetail(h)
                    note = "retried_empty" if not parsed["processing_status"] else "retried_ok"
                    if note == "retried_ok":
                        retried_ok += 1
                    else:
                        empty += 1
                        ledger[rec] = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                       "settle_ms": settle * 2,
                                       "table_rendered": "divProcessingTable" in h,
                                       "record_type": r.get("record_type")}
                        ledger_path.write_text(json.dumps(ledger, indent=1, sort_keys=True))
                (outdir / "pages" / f"{rec}.html.gz").write_bytes(
                    gzip.compress(h.encode("utf-8", "replace")))
                canon = []
                for a in parsed["parcels_raw"]:
                    try:
                        canon.append(to_canonical_apn(a, "alameda"))
                    except Exception:
                        canon.append(None)
                row = {**r, **parsed, "parcels_canonical": canon, "note": note,
                       "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
                sink.write(json.dumps(row) + "\n")
                sink.flush()
                ok += 1
            except Exception as e:
                failed += 1
                sink.write(json.dumps({**r, "error": f"{type(e).__name__}: {e}"[:300],
                                       "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
                sink.flush()
            try:
                pg.close()
            except Exception:
                pass
            if i % 10 == 0 or i == len(todo):
                el = time.time() - t0
                print(f"  [{i}/{len(todo)}] ok={ok} empty={empty} retried_ok={retried_ok} "
                      f"failed={failed} {el/i:.1f}s/rec eta={(len(todo)-i)*el/i/60:.0f}m",
                      flush=True)
            time.sleep(args.delay)
        b.close()
    print(f"done ok={ok} empty_after_retry={empty} retried_ok={retried_ok} failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
