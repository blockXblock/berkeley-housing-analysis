#!/usr/bin/env python3
r"""extract_capdetail_fees.py -- the FEES tab of every saved Planning CapDetail page, as one pinned extract.

John, 2026-10-01 ("load and batch"): Planning fees (application, use-permit, environmental review...) are on the same
Fees tab as building permits, and the Planning pages harvested 2026-09-26..30 are already on disk. This reads each page
listed in a Planning pages manifest, verifies its SHA-256, parses the tab with parse_capdetail.parse_fees, and writes
one row per record. The parsed Planning harvests are NOT rewritten (they are declared inputs already loaded); the fees
travel in their own file, which stage_methods.load_planning_fees declares.

  .venv/bin/python scripts/extract_capdetail_fees.py   # -> data/raw/accela_capdetail/planning_fees_2026-10-01.jsonl
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from parse_capdetail import parse_fees  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

PAGES = {  # manifest -> the directory its pages were saved in
    "pages_manifest_2026-09-26.csv": "scratch/2026-09-26_capdetail/pages",
    "pages_manifest_2026-09-29_adds.csv": None,
    "pages_manifest_2026-09-30_pre2015.csv": None,
    "pages_manifest_2026-09-30_ashby-bart.csv": None,
}
OUT = ROOT / "data/raw/accela_capdetail/planning_fees_2026-10-01.jsonl"


def find(fn, hint):
    if hint and (ROOT / hint / fn).exists():
        return ROOT / hint / fn
    hits = sorted(ROOT.glob(f"scratch/*/pages/{fn}"))
    return hits[0] if hits else None


def main() -> int:
    rows, missing, bad = [], [], []
    for man, hint in PAGES.items():
        for r in csv.DictReader(open(ROOT / "data/raw/accela_capdetail" / man)):
            p = find(r["filename"], hint)
            if p is None:
                missing.append(r["record"]); continue
            b = p.read_bytes()
            if hashlib.sha256(b).hexdigest() != r["sha256"]:
                bad.append(r["record"]); continue
            f = parse_fees(BeautifulSoup(gzip.decompress(b).decode("utf-8", "replace"), "html.parser"))
            rows.append({"record": r["record"], "manifest": man, "page_sha256": r["sha256"], "fees": f})
    assert not bad, f"pages changed since their manifest: {bad[:5]}"
    with open(OUT, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    with_fees = sum(1 for r in rows if r["fees"])
    print(f"{len(rows)} pages read ({with_fees} with fees); missing from disk: {len(missing)} {missing[:5]}; -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
