#!/usr/bin/env python3
"""middle_housing_tracker.py — the Middle Housing Ordinance pipeline, application to occupancy.

Berkeley's Middle Housing Ordinance took effect **1 November 2025**, allowing up to 8 units on
almost any residential parcel. This tracks every record filed under it and how far each has moved:

    application -> approval -> building permit -> inspections -> building final (occupiable)

SOURCES (all independent primary; CKAN/HCD is the verification target and is never read here):
  * data/raw/accela/date_range/Planning_*.jsonl  — HARVESTER sweep, the application cohort
  * data/raw/accela/date_range/Building_*.jsonl  — HARVESTER sweep, permits at those addresses
  * data/raw/accela_inspections/<permit>.json    — per-permit inspection history

TWO METHOD WEAKNESSES, both load-bearing — read before quoting any number:

  1. **The Planning->Building join is by NORMALISED ADDRESS**, because the two Accela modules share
     no key in the list view. A match is evidence of a permit AT THAT ADDRESS, not proof it belongs
     to the middle-housing project. Mitigated by classifying each permit CONSTRUCTION vs INCIDENTAL
     (a re-roof, a panel upgrade, a temporary power pole and an address assignment are not middle
     housing) and by printing every description for eye-checking. Counts are reported as "addresses
     with a construction permit", never as "middle-housing units permitted". Confirming a link
     properly needs the per-record capID detail page; that is the queued upgrade.

  2. **Inspection coverage is partial.** data/raw/accela_inspections/ holds what the harvester has
     fetched, not every permit. A permit with no inspection file is reported `no inspection data`,
     which is NOT the same as `no inspections`. Absence of a file is absence of evidence only.

Completion signal = an APPROVED `Building 1200 Building Final` inspection. Per CLAUDE.md the
canonical completion is v2's co_issued_date, but this cohort is far too new to be in v2 at all.

Read-only. Writes a CSV; touches no database.

Usage:  python scripts/middle_housing_tracker.py [--since 2025-11-01] [--csv PATH] [--detail]
"""
import argparse
import csv
import glob
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCELA = ROOT / "data" / "raw" / "accela" / "date_range"
INSPECT = ROOT / "data" / "raw" / "accela_inspections"
DEFAULT_CSV = ROOT / "data" / "reference" / "middle_housing_tracker.csv"
REVIEWED = ROOT / "data" / "reference" / "middle_housing_units_reviewed.csv"

ORDINANCE_START = "2025-11-01"
MH_MARK = "MIDDLE HOUSING"
FINAL_INSPECTION = "BUILDING 1200 BUILDING FINAL"

_STREET_TYPES = {
    "ST", "STREET", "AVE", "AVENUE", "WAY", "DR", "DRIVE", "BLVD", "BOULEVARD",
    "RD", "ROAD", "CT", "COURT", "PL", "PLACE", "LN", "LANE", "TER", "TERRACE",
    "CIR", "CIRCLE", "PATH", "WALK", "PKWY", "PARKWAY",
}
# work that is plainly not the middle-housing project itself
_INCIDENTAL = re.compile(
    r"\b(re-?roof|tear off|roofing|shingle|panel upgrade|upgrade main electrical|"
    r"electrical panel|temporary power|temp power|power pole|water heater|furnace|"
    r"sewer lateral|address assignment|solar|photovoltaic|pv system|ev charger|"
    r"seismic retrofit|window replacement|fence|dry ?rot)\b", re.I)
# permit numbers that are not permits
_NON_PERMIT = re.compile(r"^(PREAPP|ESR-|\d{2}TMP)", re.I)


def iso(mdy: str) -> str:
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", (mdy or "").strip())
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def norm_addr(raw: str):
    """'2780 MABEL St, BERKELEY CA 94702' -> ('2780', 'MABEL')."""
    s = (raw or "").upper()
    s = re.sub(r",\s*BERKELEY.*$", "", s)
    s = re.sub(r"\b(REAR|UNIT|APT|STE|SUITE)\b.*$", "", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    parts = s.split()
    if not parts or not parts[0].isdigit():
        return None, None
    num, rest = parts[0], [p for p in parts[1:] if p not in _STREET_TYPES]
    return (num, " ".join(rest)) if rest else (num, None)


def load(module: str):
    for fn in sorted(glob.glob(str(ACCELA / f"{module}_*.jsonl"))):
        with open(fn) as fh:
            for line in fh:
                try:
                    yield json.loads(line)
                except Exception:
                    continue


def address_of(d: dict) -> str:
    cells = d.get("_cells") or []
    return d.get("Address") or (cells[-1] if cells else "") or d.get("Project Name", "")


def load_reviewed():
    """Eye-checked unit counts, keyed by record number. A record missing from the file is
    reported UNREVIEWED rather than guessed at — new applications must get a human read."""
    out = {}
    if not REVIEWED.exists():
        return out
    lines = [ln for ln in open(REVIEWED) if not ln.lstrip().startswith("#")]
    for r in csv.DictReader(lines):
        out[r["record"]] = r
    return out


def as_int(s):
    s = (s or "").strip()
    try:
        return int(s)
    except ValueError:
        return None


def inspections_for(permit: str):
    """-> (count, latest_date, passed_building_final) or None when we hold no file."""
    f = INSPECT / f"{permit}.json"
    if not f.exists():
        return None
    try:
        rows = json.load(open(f)).get("inspections") or []
    except Exception:
        return None
    passed = any(r.get("type_code", "").upper().startswith(FINAL_INSPECTION)
                 and r.get("result", "").lower() == "approved" for r in rows)
    dates = sorted(filter(None, (iso(r.get("date", "")) for r in rows)))
    return len(rows), (dates[-1] if dates else ""), passed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=ORDINANCE_START)
    ap.add_argument("--csv", default=str(DEFAULT_CSV))
    ap.add_argument("--detail", action="store_true", help="print every record and permit")
    args = ap.parse_args()

    cohort, newest_sweep = {}, ""
    for d in load("Planning"):
        when = iso(d.get("Date", ""))
        newest_sweep = max(newest_sweep, when)
        blob = " ".join(str(d.get(k, "")) for k in ("Record Type", "Description", "Project Name")).upper()
        if MH_MARK not in blob or when < args.since:
            continue
        rn = d.get("Record Number", "")
        if rn and rn not in cohort:
            cohort[rn] = {
                "record": rn, "filed": when, "record_type": d.get("Record Type", ""),
                "planning_status": d.get("Status", ""), "address": address_of(d),
                "_key": norm_addr(address_of(d)),
                "description": (d.get("Description", "") or "").strip(),
            }

    want = {c["_key"] for c in cohort.values() if c["_key"][0]}
    permits = {}
    for d in load("Building"):
        when = iso(d.get("Date", ""))
        if when < args.since:
            continue
        key = norm_addr(address_of(d))
        if key[0] and key in want:
            num = (d.get("Permit Number", "") or "").strip()
            desc = (d.get("Description", "") or "").strip()
            if _NON_PERMIT.match(num):
                kind = "not-a-permit"
            elif _INCIDENTAL.search(desc) or not desc:
                kind = "incidental"
            else:
                kind = "construction"
            permits.setdefault(key, []).append({
                "permit": num, "date": when, "status": (d.get("Status", "") or "").strip(),
                "desc": desc, "kind": kind,
            })

    reviewed = load_reviewed()
    rows = []
    for c in sorted(cohort.values(), key=lambda r: r["filed"]):
        ps = sorted(permits.get(c["_key"], []), key=lambda b: b["date"])
        con = [b for b in ps if b["kind"] == "construction"]
        issued = [b for b in con if b["status"].lower().startswith(("issued", "finaled"))]
        insp_n, insp_last, finaled = 0, "", False
        covered = False
        for b in con:
            got = inspections_for(b["permit"])
            if got:
                covered = True
                insp_n += got[0]
                insp_last = max(insp_last, got[1])
                finaled = finaled or got[2]
        rows.append({
            "record": c["record"], "filed": c["filed"], "record_type": c["record_type"],
            "planning_status": c["planning_status"], "address": c["address"].split(", BERKELEY")[0],
            "gross_units_proposed": (reviewed.get(c["record"], {}).get("gross_units_proposed", "")),
            "net_units": (reviewed.get(c["record"], {}).get("net_units", "")
                          if c["record"] in reviewed else "UNREVIEWED"),
            "construction_permits": len(con),
            "construction_permits_issued": len(issued),
            "inspections_held": insp_n if covered else "",
            "latest_inspection": insp_last,
            "building_final_passed": "yes" if finaled else ("no" if covered else ""),
            "permit_detail": " | ".join(f"{b['permit']}[{b['status'] or '-'}]({b['kind']}) {b['desc'][:90]}" for b in ps),
            "description": c["description"][:300],
        })

    out = Path(args.csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("Berkeley Middle Housing Ordinance — effective 2025-11-01")
    print(f"Accela sweep runs through {newest_sweep} · generated {date.today().isoformat()}\n")
    print(f"  applications filed                    {len(rows)}")
    for k, v in Counter(r["record_type"] for r in rows).most_common():
        print(f"      {v:>3}  {k}")
    nets = [as_int(r["net_units"]) for r in rows]
    unreviewed = [r["record"] for r in rows if r["net_units"] == "UNREVIEWED"]
    known = [n for n in nets if n is not None]
    gross = [as_int(r["gross_units_proposed"]) for r in rows]
    gross = [g for g in gross if g is not None]
    print("\n  what they propose (eye-checked, data/reference/middle_housing_units_reviewed.csv)")
    print(f"      {sum(1 for n in known if n > 0):>3}  add dwellings")
    print(f"      {sum(1 for n in known if n == 0):>3}  no change in dwellings (addition / remodel)")
    print(f"      {sum(1 for n in known if n < 0):>3}  REMOVE a dwelling")
    print(f"      net change across the cohort: {sum(known):+d} dwellings")
    print(f"      largest single project: {max(gross) if gross else 0} dwellings "
          f"(the ordinance allows up to 8)")
    if unreviewed:
        print(f"      !! {len(unreviewed)} UNREVIEWED - add to the reviewed file: {', '.join(unreviewed)}")
    print("\n  planning status")
    for k, v in Counter(r["planning_status"] for r in rows).most_common():
        print(f"      {v:>3}  {k or '(blank)'}")
    print(f"\n  addresses with a CONSTRUCTION permit  {sum(1 for r in rows if r['construction_permits'])}")
    print(f"  ...with one ISSUED                    {sum(1 for r in rows if r['construction_permits_issued'])}")
    print(f"  ...with inspection data held          {sum(1 for r in rows if r['inspections_held'] != '')}")
    print(f"  ...that passed a BUILDING FINAL       {sum(1 for r in rows if r['building_final_passed'] == 'yes')}")

    # actionable: issued construction permits we hold no inspection file for
    queue = []
    for r in rows:
        for b in (r["permit_detail"].split(" | ") if r["permit_detail"] else []):
            if "(construction)" in b and ("[Issued]" in b or "[Finaled]" in b):
                num = b.split("[")[0]
                if not (INSPECT / f"{num}.json").exists():
                    queue.append(num)
    if queue:
        print(f"\n  HARVESTER QUEUE - issued construction permits with no inspection file ({len(queue)}):")
        print("      " + " ".join(sorted(set(queue))))

    if args.detail:
        print("\n" + "=" * 78)
        for r in rows:
            print(f"\n{r['filed']}  {r['record']}  [{r['planning_status']}]  {r['address']}  net {r["net_units"]}")
            print("    " + r["description"][:150])
            for b in (r["permit_detail"].split(" | ") if r["permit_detail"] else []):
                print(f"      {b[:130]}")
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
