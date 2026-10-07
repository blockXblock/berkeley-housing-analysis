#!/usr/bin/env python3
"""harvest_zab_documents.py -- the Zoning Adjustments Board's agendas and minutes, as the City publishes them (read-only).

John, 2026-10-06 ("harvest the ZAB agendas"): the City's Planning workflow records many large approvals as a
"Staff Decision", yet 78% of those on 5+ unit projects are dated on a Thursday, the ZAB's meeting day, and the records
name no hearing. The Board's own agendas and minutes say which projects it heard and what it decided, so the deciding
body can be read from the Board's record instead of inferred from a weekday.

Source: the ZAB page on berkeleyca.gov and its paged meeting list (?page=0..N), which links each meeting's agenda and
minutes PDF. Every linked agenda/minutes PDF is downloaded once, with its SHA-256, into
    data/raw/zab/<kind>/<file name>
and listed in data/raw/zab/manifest_<date>.csv (url, kind, meeting_date, file, bytes, sha256). Resumable: a file already
on disk is not fetched again. A page that fails is retried once and logged, never treated as absent.

SECOND SOURCE, the City Clerk's Records Online (OnBase Public Access): ZAB minutes 2002 to the present, the Board's
Action Minutes, which name each item's Planning record ("Use Permit #ZP2016-0117"), its address, the motion, the vote
and the ACTION. berkeleyca.gov lists only 2021 on; the archive fills the earlier years (it holds 1 set each for 2019 and
2020 -- a gap in the archive, recorded, not filled). Saved to data/raw/zab/minutes_records_online/<yyyy-mm-dd>.pdf.

  .venv/bin/python scripts/harvest_zab_documents.py [--pages 0-6] [--records-online]
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://berkeleyca.gov"
BOARD = BASE + "/your-government/boards-commissions/zoning-adjustments-board"
UA = {"User-Agent": "curl/8.7.1"}   # the City's server refuses the Python default agent
KINDS = {"legislative-body-meeting-agendas": "agenda", "legislative-body-meeting-minutes": "minutes"}
LINK = re.compile(r'href="(/sites/default/files/(legislative-body-meeting-(?:agendas|minutes))/[^"]+\.pdf)"', re.I)
DATE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")


def get(url: str) -> bytes:
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except Exception as e:  # retried once; the caller logs a second failure
            err = e
            time.sleep(3)
    raise err


RO_API = "https://records.cityofberkeley.info/PublicAccess/api"
RO_MINUTES_QUERY, RO_DOC_SOURCE = 131, "123"     # "Public - Minutes Query (Keywords)"; its "Doc Source" keyword


def records_online(out: Path, failed: list) -> list[dict]:
    """Every ZAB minutes document in Records Online, one PDF per meeting date."""
    import json
    body = {"QueryID": RO_MINUTES_QUERY, "FromDate": "01/01/2002", "ToDate": dt.date.today().strftime("%m/%d/%Y"),
            "Keywords": [{"ID": RO_DOC_SOURCE, "Value": "Zoning Adjustments Board", "KeywordOperator": "="}],
            "QueryLimit": 0}
    req = urllib.request.Request(RO_API + "/CustomQuery/KeywordSearch", data=json.dumps(body).encode(),
                                 headers={**UA, "Content-Type": "application/json"})
    docs = json.loads(urllib.request.urlopen(req, timeout=180).read())["Data"]
    print(f"Records Online: {len(docs)} ZAB minutes documents", flush=True)
    rows, seen = [], collections.Counter()
    for d in docs:
        m_, d_, y_ = d["Name"].split(";")[0].strip().split("/")
        day = dt.date(int(y_), int(m_), int(d_)).isoformat()
        seen[day] += 1
        name = day + (f"_{seen[day]}" if seen[day] > 1 else "") + ".pdf"
        f = out / "minutes_records_online" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        url = RO_API + "/Document/" + urllib.parse.quote(d["ID"], safe="") + "/"
        if not f.exists():
            try:
                f.write_bytes(get(url))
                time.sleep(1)
            except Exception as e:
                failed.append(f"records online {day}: {e}")
                continue
        b = f.read_bytes()
        rows.append({"url": "records.cityofberkeley.info Records Online, CLK - Minutes, " + d["Name"].strip(),
                     "kind": "minutes_records_online", "meeting_date": day, "file": str(f.relative_to(ROOT)),
                     "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="0-6", help="listing pages, e.g. 0-6")
    ap.add_argument("--records-online", action="store_true", help="also the Clerk's archive of ZAB minutes, 2002-")
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.pages.split("-"))
    out = ROOT / "data/raw/zab"
    links, failed = {}, []
    for n in range(lo, hi + 1):
        try:
            page = get(f"{BOARD}?page={n}").decode("utf-8", "replace")
        except Exception as e:
            failed.append(f"page {n}: {e}")
            continue
        for path, folder in LINK.findall(page):
            links[BASE + path] = KINDS[folder.lower()]
    print(f"{len(links)} agenda/minutes links on pages {lo}-{hi}", flush=True)
    rows = []
    for url, kind in sorted(links.items()):
        name = urllib.parse.unquote(url.rsplit("/", 1)[1])
        f = out / kind / name
        f.parent.mkdir(parents=True, exist_ok=True)
        if not f.exists():
            try:
                f.write_bytes(get(url))
                time.sleep(1)               # polite: one file a second
            except Exception as e:
                failed.append(f"{url}: {e}")
                continue
        b = f.read_bytes()
        m = DATE.search(name)
        rows.append({"url": url, "kind": kind,
                     "meeting_date": dt.date(int(m[1]), int(m[2]), int(m[3])).isoformat() if m else "",
                     "file": str(f.relative_to(ROOT)), "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    if a.records_online:
        rows += records_online(out, failed)
    man = out / f"manifest_{dt.date.today().isoformat()}.csv"
    with open(man, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["url"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["meeting_date"], r["kind"])))
    kinds = collections.Counter(r["kind"] for r in rows)
    print(f"saved {len(rows)} ({kinds}); failed {len(failed)} {failed[:5]} -> {man.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
