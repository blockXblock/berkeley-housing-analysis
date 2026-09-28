#!/usr/bin/env python3
"""reparse_capdetail.py -- rebuild the parsed JSONL from the saved CapDetail HTML.

The harvest saves every page as pages/<record>.html.gz, so the PAGE is the durable artifact and
the parsed JSONL is DERIVED. That separation is what let two parser corrections (the ESR record-
number shape, and excluding a record's own number from its Related Records) apply retroactively to
records already fetched, without asking the city's portal for anything a second time.

Writes a NEW dated file rather than overwriting, so a reparse is append-only evidence and the
previous parse stays comparable. Read-only w.r.t. the pages and the DBs.

  .venv/bin/python scripts/reparse_capdetail.py
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from housing_rules import to_canonical_apn          # noqa: E402  THE canon
from parse_capdetail import parse_capdetail         # noqa: E402

DIR = ROOT / "scratch/2026-09-26_capdetail"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(DIR))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    d = pathlib.Path(args.dir)

    # the queue rows carry list_date / record_type, which the page itself does not
    meta = {}
    src = d / "capdetail_parsed.jsonl"
    if src.exists():
        for line in open(src):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("record"):
                meta[r["record"]] = {k: r.get(k) for k in
                                     ("href", "record_type", "list_status", "list_date")}

    out = pathlib.Path(args.out) if args.out else d / f"capdetail_reparsed_{time.strftime('%Y-%m-%d')}.jsonl"
    pages = sorted(glob.glob(str(d / "pages/*.html.gz")))
    n = 0
    with open(out, "w") as sink:
        for fn in pages:
            rec = pathlib.Path(fn).name[:-len(".html.gz")]
            h = gzip.decompress(open(fn, "rb").read()).decode("utf-8", "replace")
            p = parse_capdetail(h)
            canon = []
            for a in p["parcels_raw"]:
                try:
                    canon.append(to_canonical_apn(a, "alameda"))
                except Exception:
                    canon.append(None)
            sink.write(json.dumps({"record": rec, **meta.get(rec, {}), **p,
                                   "parcels_canonical": canon,
                                   "reparsed_at": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
            n += 1
            if n % 200 == 0:
                print(f"  {n}/{len(pages)}", flush=True)
    print(f"reparsed {n} pages -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
