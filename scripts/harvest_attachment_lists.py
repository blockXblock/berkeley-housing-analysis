#!/usr/bin/env python3
"""harvest_attachment_lists.py -- the ATTACHMENT LIST of each named Accela Planning record (HARVESTER; read-only).

John, 2026-10-03: "fold in, then harvest". Ministerial approvals (SB 35, AB 2011) are filed as pre-application-type
records with no decision workflow; the approval is a signed Letter of Compliance ATTACHED to the record
("2023-01-20_SB35_Compliance_1708 Harmon REDUCED.pdf"). v4 held attachment lists for only 85 records (hand captures),
so it could not see them. This lists every attachment of each record named (file name, upload date, size) and
downloads only small approval-type letters, so the build can read approval dates from the City's own letters.

  .venv/bin/python scripts/harvest_attachment_lists.py --records FILE   # lines: RECORD=capdetail_href
Output (append, resumable -- a record already in the output is skipped):
  data/raw/accela_attachments/attachments_<date>.jsonl   one line per record: {record, href, fetched_at, rows:[...]}
  data/raw/accela_attachments/letters_<date>/<record>/<file>   approval-type letters under 8 MB, with SHA-256 in the jsonl
Grid paging and downloads are scripts/accela_grid.py (the tested pager). A record whose grid fails twice is logged and
retried on the next run (CLAUDE.md: a 0-result is not evidence of absence until retried).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import accela_grid as ag  # noqa: E402

LETTER = re.compile(r"complian|approv|letter of|ltr|decision|notice of|NOD\b|zoning cert|determin|eligib", re.I)
SKIP = re.compile(r"PRE-APP|planning submittals|ZR_|plan set|plans\b", re.I)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    outdir = ROOT / "data/raw/accela_attachments"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"attachments_{a.date}.jsonl"
    letters = outdir / f"letters_{a.date}"
    done = {json.loads(l)["record"] for l in open(out)} if out.exists() else set()
    todo = [l.strip().split("=", 1) for l in open(a.records) if "=" in l]
    todo = [(r, h) for r, h in todo if r not in done][: a.limit or None]
    print(f"{len(done)} done, {len(todo)} to fetch -> {out.relative_to(ROOT)}", flush=True)
    from playwright.sync_api import sync_playwright
    t0, ok, failed = time.time(), 0, []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        for i, (rec, href) in enumerate(todo, 1):
            got = None
            for attempt in (1, 2):
                pg = b.new_page()
                pg.set_default_timeout(60000)
                try:
                    pg.goto(ag.BASE + href, wait_until="domcontentloaded")
                    pg.wait_for_timeout(2500)
                    frame = ag.open_grid(pg, href)
                    rows = []
                    for page_rows in ag.walk(pg, frame):
                        for r in page_rows:
                            row = {k: r.get(k) for k in r if k != "target"}
                            fn = (r.get("filename") or "").strip()
                            size = ag.grid_size_bytes(r.get("rowtext")) or 0
                            if r.get("target") and LETTER.search(fn) and not SKIP.search(fn) and size < 8 * 1048576:
                                d = letters / rec
                                d.mkdir(parents=True, exist_ok=True)
                                f = d / fn.replace("/", "_")
                                if not f.exists():
                                    try:
                                        with pg.expect_download(timeout=180000) as dl:
                                            frame.evaluate(f"__doPostBack('{r['target']}','')")
                                        dl.value.save_as(str(f))
                                    except Exception as e:  # a failed download keeps the listing
                                        row["download_error"] = str(e)[:120]
                                if f.exists():
                                    row["saved"] = str(f.relative_to(ROOT))
                                    row["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
                            rows.append(row)
                    got = rows
                    break
                except Exception as e:
                    err = str(e)[:160]
                finally:
                    pg.close()
            if got is None:
                failed.append(rec)
                print(f"  FAILED {rec}: {err}", flush=True)
                continue
            with open(out, "a") as f:
                f.write(json.dumps({"record": rec, "href": href, "fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
                                    "rows": got}) + "\n")
            ok += 1
            if i % 10 == 0:
                rate = (time.time() - t0) / i
                print(f"  [{i}/{len(todo)}] ok={ok} failed={len(failed)} {rate:.1f}s/rec eta={rate*(len(todo)-i)/60:.0f}m", flush=True)
        b.close()
    print(f"done ok={ok} failed={len(failed)} {failed[:20]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
