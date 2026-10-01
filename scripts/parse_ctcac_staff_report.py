#!/usr/bin/env python3
r"""parse_ctcac_staff_report.py -- the FINANCING of a tax-credit project, read from its CTCAC staff report's structure.

John, 2026-10-01: trace the source of the money for each project -- lenders and investors, not only public funders.
A CTCAC Project Staff Report states (1) a Construction Financing and a Permanent Financing table (Source | Amount, the
two tables side by side), and (2) labelled fields ("Investor/Consultant:", "Private Placement Purchaser:",
"CDLAC Applicant/Bond Issuer:", "Bond Counsel:", "Management Agent:"). Both are read from the PAGE LAYOUT: a table row
is the words that share a line (PyMuPDF word coordinates); a source and its amount pair because they sit on the same
row in the same column -- never by guessing. Nothing is classified here: a source is kept verbatim ("Tax Exempt Bond-
Chase Bank"), and which party is a lender, investor or public funder is read later from those words.

  .venv/bin/python scripts/parse_ctcac_staff_report.py      # -> data/derived/ctcac_financing_<date>.json

Inputs: data/raw/ctcac/staff_reports/*.pdf, pinned in manifest_2026-10-01.csv (application, url, sha256, bytes).
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data/raw/ctcac/staff_reports"
MANIFEST = DIR / "manifest_2026-10-01.csv"
LABELS = ("Investor/Consultant", "Private Placement Purchaser", "CDLAC Applicant/Bond Issuer", "Bond Counsel",
          "Management Agent", "Developer", "General Partner", "Bond Issuer", "Lender", "Syndicator")
AMOUNT = re.compile(r"^\$[\d,]+(\.\d+)?$")


def rows(page):
    """the page's lines: words grouped by their vertical centre, each word with its x position."""
    g = collections.defaultdict(list)
    for x0, y0, x1, y1, w, *_ in page.get_text("words"):
        g[round((y0 + y1) / 6)].append((x0, w))
    return [sorted(v) for _, v in sorted(g.items())]


def _unused_segments(row):
    """split a row into (source words, amount) pairs: each amount closes the source written before it."""
    out, cur = [], []
    for x, w in row:
        if AMOUNT.match(w):
            out.append((" ".join(t for _, t in cur).strip(), w, cur[0][0] if cur else x))
            cur = []
        else:
            cur.append((x, w))
    return out


def parse(path):
    doc = pymupdf.open(path)
    fin = {"construction": [], "permanent": []}
    labels = {}
    table_done = False
    for page in doc:
        rs = rows(page)
        for i, r in enumerate(rs):
            words = " ".join(w for _, w in r)
            for lab in LABELS:
                if words.startswith(lab + ":") or words.startswith(lab + "(s):"):
                    val = words.split(":", 1)[1].strip()
                    if val:
                        labels.setdefault(lab, val)
            if not table_done and words.startswith("Construction Financing") and "Permanent Financing" in words:
                cons_x = next(x for x, w in r if w == "Construction")
                perm_x = next(x for x, w in r if w == "Permanent")
                # the column boundary is where the table's SECOND "Source" heading starts (the permanent column's
                # left edge); amounts are right-aligned, so a midpoint would push a short amount ($100) across
                hdr = next((r2 for r2 in rs[i + 1:i + 4] if sum(w == "Source" for _, w in r2) == 2), None)
                split = ([x for x, w in hdr if w == "Source"][1] - 5) if hdr else (cons_x + perm_x) / 2
                # read EACH COLUMN top to bottom: a source's words are carried until its amount appears (a name and
                # its amount can sit on adjacent lines); the table ends at TOTAL or at "Determination of Credit".
                pending = {"construction": [], "permanent": []}
                for r2 in rs[i + 1:]:
                    w2 = " ".join(w for _, w in r2)
                    if w2.startswith(("Determination", "*Less")):
                        break
                    if w2.startswith("Source"):
                        continue
                    for x, w in r2:
                        col = "permanent" if x >= split else "construction"
                        if AMOUNT.match(w):
                            src = " ".join(pending[col]).strip()
                            fin[col].append({"source": src or "?", "amount": w})
                            pending[col] = []
                        else:
                            pending[col].append(w)
                table_done = True                             # one table per report; keep scanning for labels
    return fin, labels


def main() -> int:
    out, problems = [], []
    for m in csv.reader(open(MANIFEST)):
        app, url, sha, size = m
        p = DIR / f"{app}.pdf"
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != sha:
            sys.exit(f"{p.name} changed since the manifest")
        fin, labels = parse(p)
        if not fin["construction"] and not fin["permanent"]:
            problems.append(app)
        # GATE: the permanent sources must add up to the report's own TOTAL (the construction column need not: some
        # sources arrive only at conversion). A mismatch means a row was misread -- stop, never store it.
        n = lambda a: int(a.replace("$", "").replace(",", "").split(".")[0])
        tot = [n(x["amount"]) for x in fin["permanent"] if x["source"] == "TOTAL"]
        perm = sum(n(x["amount"]) for x in fin["permanent"] if x["source"] != "TOTAL")
        if tot and perm != tot[0]:
            sys.exit(f"{app}: permanent sources sum to {perm:,} but the report's TOTAL is {tot[0]:,} -- misread")
        out.append({"application": app, "url": url, "sha256": sha, "financing": fin, "labelled": labels})
        print(f"{app}: construction {len(fin['construction'])} · permanent {len(fin['permanent'])} · labels {sorted(labels)}")
    path = ROOT / "data/derived" / f"ctcac_financing_{time.strftime('%Y-%m-%d')}.json"
    json.dump({"read_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "method": "page layout: table rows by word coordinates; "
               "labelled fields by their own labels; nothing classified", "reports": out,
               "no_table_found": problems}, open(path, "w"), indent=1)
    print(f"wrote {path.relative_to(ROOT)}; no table found: {problems}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
