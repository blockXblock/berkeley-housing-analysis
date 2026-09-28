#!/usr/bin/env python3
# ============================ SEQUESTERED 2026-09-28 ============================
# DO NOT RUN. Original path: scripts/migration/preview_accela_planning_ingest.py
# WHY: Read-only preview for ingest_planning_scope_a, which has been applied. Carried its own copy of the broken HOUSING regex.
raise SystemExit("SEQUESTERED 2026-09-28 -- see header; original path scripts/migration/preview_accela_planning_ingest.py")
# ================================================================================
"""preview_accela_planning_ingest.py — READ-ONLY preview of the Accela Planning ingest.

WHY THIS IS THE BINDING CONSTRAINT. It has surfaced three separate times today:
  * of 43 completed multi-unit non-exempt projects, 30 lack an ENTITLEMENT event -- more than lack
    a building permit
  * 2336 Dwight (ZP2026-0091, +8 net units, filed 2026-09-15) and five other multi-unit proposals
    have no project in v2 at all
  * the seven-rung classifier cannot date rung 3 (application accepted) for more than ~69 projects

⚠ WHAT THE LIST VIEW DOES AND DOES NOT CARRY. Each Planning row has `Date` (filed), a CURRENT
`Status`, `Record Type`, `Description` and `capdetail_href`. It has NO transition dates. So this
ingest can establish WHERE a project stands and WHEN it was filed -- it cannot measure the
submitted -> accepted interval John wants for the ministerial-versus-discretionary comparison.
Those dates live on the CapDetail pages. We hold 14,936 Planning capIDs and have visited about 95,
by hand, in data/raw/accela_status/. That harvest is a separate and larger job.

Writes nothing. Reports what each scope option would do so the scope is John's call, not mine.

Usage:  python scripts/migration/preview_accela_planning_ingest.py
"""
import collections
import glob
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "databases/berkeley_housing_v2.db"

DEV_PREFIX = re.compile(r"^(ZP|PLN|DRS|DRC|LM|ZCBP)", re.I)
HOUSING = re.compile(
    r"(\b(dwelling|adu|jadu|duplex|triplex|fourplex|apartment|residence|residential|"
    r"middle housing|sb ?9|sb ?330|sb ?35|sb ?684|ab ?2011|town ?home|housing|single.family|"
    r"infill|live.?work)\b|\d+\s*[-\s]?\s*units?\b)", re.I)
NET_NEW = re.compile(
    r"\b(construct|build|new|demolish|convert|legaliz|add)\w*\b.{0,60}"
    r"\b(unit|dwelling|adu|jadu|duplex|triplex|fourplex|apartment|town ?home|residence|home)s?\b", re.I)
# current status -> the rung it evidences
ACCEPTED = re.compile(r"application complete|under review|in review|pending final action", re.I)
ENTITLED = re.compile(r"^approved", re.I)
CLOSED = re.compile(r"withdrawn|denied|closed|expired|void", re.I)


def iso(m):
    x = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", (m or "").strip())
    return f"{x.group(3)}-{int(x.group(1)):02d}-{int(x.group(2)):02d}" if x else ""


def key(a):
    a = re.sub(r",.*$", "", str(a or "").upper())
    p = re.sub(r"[^A-Z0-9 ]", " ", a).split()
    return (p[0], p[1]) if len(p) > 1 and p[0].isdigit() else None


def main() -> int:
    recs = {}
    for fn in glob.glob(str(ROOT / "data/raw/accela/date_range/Planning_*.jsonl")):
        for line in open(fn):
            try:
                d = json.loads(line)
            except Exception:
                continue
            n = str(d.get("Record Number") or "").strip()
            if n and n not in recs:
                recs[n] = d
    db = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)
    addr = collections.defaultdict(set)
    for p, a in db.execute("SELECT project_id,address_display FROM v_projects_flat WHERE address_display IS NOT NULL"):
        k = key(a)
        if k:
            addr[k].add(p)
    have_perm = {n for (n,) in db.execute("SELECT permit_number FROM permits WHERE permit_number IS NOT NULL")}

    dev = {n: d for n, d in recs.items() if DEV_PREFIX.match(n)}
    hous = {n: d for n, d in dev.items()
            if HOUSING.search(" ".join(str(d.get(f, "")) for f in ("Description", "Project Name", "Record Type")))}
    print(f"  Planning records (distinct)              {len(recs):,}")
    print(f"  ...development types (ZP/PLN/DR*/LM*/ZCBP) {len(dev):,}")
    print(f"  ...with housing language                 {len(hous):,}")
    print(f"  ...already in v2 as a permit row         {sum(1 for n in hous if n in have_perm):,}\n")

    matched, unmatched, netnew_unmatched = [], [], []
    for n, d in hous.items():
        k = key((d.get("_cells") or [""])[-1])
        pids = addr.get(k, set()) if k else set()
        (matched if pids else unmatched).append((n, d, pids))
        if not pids and NET_NEW.search(str(d.get("Description") or "")):
            netnew_unmatched.append((n, d))

    ev = collections.Counter()
    for n, d, pids in matched:
        s = str(d.get("Status") or "")
        if iso(d.get("Date", "")):
            ev["application_submitted"] += 1
        if ENTITLED.match(s):
            ev["entitlement_approved"] += 1
        elif ACCEPTED.search(s):
            ev["application_complete"] += 1
    print("SCOPE A — events onto projects v2 ALREADY HAS (no new projects)")
    print(f"  housing records matching an existing project   {len(matched):,}")
    for k2, v in ev.most_common():
        print(f"    {k2:<26} {v:>5} events")
    print(f"  projects touched                               {len({p for _,_,ps in matched for p in ps}):,}\n")

    print("SCOPE B — A, plus create projects for UNMATCHED records that propose NET NEW units")
    print(f"  unmatched housing records                      {len(unmatched):,}")
    print(f"  ...of those, proposing net new units           {len(netnew_unmatched):,}  <- would become projects")
    yr = collections.Counter(iso(d.get("Date", ""))[:4] for _, d in netnew_unmatched)
    print("  by filing year: " + " ".join(f"{k}:{v}" for k, v in sorted(yr.items()) if k))
    print()
    print("SCOPE C — A, plus a project for EVERY unmatched housing record")
    print(f"  would create                                   {len(unmatched):,} projects"
          f"  ({len(unmatched)/1099*100:.0f}% growth)\n")

    print("  largest unmatched net-new proposals:")
    def units(d):
        m = re.findall(r"(\d+)\s*[-\s]?\s*units?\b", str(d.get("Description") or ""), re.I)
        return max((int(x) for x in m), default=0)
    for n, d in sorted(netnew_unmatched, key=lambda x: -units(x[1]))[:10]:
        print(f"    {iso(d.get('Date','')):<11} {n:<16} [{str(d.get('Status'))[:13]:<13}] "
              f"{units(d):>4}u  {str(d.get('Description'))[:46]}")
    print("\n  Nothing written. Scope is John's call.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
