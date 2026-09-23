#!/usr/bin/env python3
"""Derive a dated CO from the Accela inspection trail, and reconcile it against v2. Read-only.

THE RULE. Berkeley issues no traditional certificate of occupancy — the City FINALS permits, and the
moment a building becomes occupiable is an inspection: **`Building 1200 Building Final`, result
`Approved`**, carrying a date. That is the CO-equivalent and the only first-class completion evidence
available, which matters because the APR reports completions BY CALENDAR YEAR.

Two traps this encodes:
  - **Result matters.** A `Building 1200 Building Final` row can be `Site Cancellation`, `Cancelled`,
    `Disapproved` or `Partially Approved`. Only `Approved` is a completion (the 2026-05-19 recon note
    caught a Site-Cancellation final that reads like one but is workflow cleanup).
  - **Discipline matters** (CLAUDE.md): inspections present but NO building-final is a real finding —
    either not complete, or the final is not recorded. It is reported here, never guessed at.

Why the CPRA feed cannot do this job: `Finaled Status='Finaled'` appears on 2,060 primary permits with
NO date (it grew 706 -> 985 in the 2023-25 window between two productions of the same report), 402 of
915 units-adding permits have no `Finaled Date`, and `Completed`/`Completed Date` ship empty. The feed
is the bulk backbone; the inspection is the event.

Output: data/derived/co_from_inspections_<date>.csv, one row per project, classified —
  fills_gap        v2 has no co_issued_date; the inspection supplies one (the APR prize)
  agrees           within --tolerance days of v2 (default 7: inspection date vs recorded final date)
  disagrees_small  8..60 days apart
  disagrees_large  >60 days — nearly always a MULTI-BUILDING project forced into one date field
                   (proj179 Acheson North 2022-01-14 vs South 2023-08-08 is the type case)
  no_building_final  inspections harvested, no Building Final of any result
Nothing is written to any database. The CSV is the review sheet for a later gated write.

Usage: python scripts/derive_co_from_inspections.py [--tolerance 7] [--date YYYY-MM-DD]
"""
import argparse, csv, datetime as dt, glob, json, sqlite3, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSPECTIONS = ROOT / "data/raw/accela_inspections"
V2 = ROOT / "databases/berkeley_housing_v2.db"
OUT = ROOT / "data/derived"

BUILDING_FINAL = "Building 1200 Building Final"
PASSING = "Approved"                      # NOT 'Partially Approved', NOT 'Site Cancellation'
# ROLE GATE (added 2026-09-23 after John questioned proj4, 1914 Fifth St). An approved Building Final
# is only a COMPLETION if the permit could create a dwelling. proj4's three "finals" are a warehouse
# DEMOLITION, a site-work demo and a parking-lot grading permit — all finaled in 2017, none of them a
# 257-unit building becoming occupiable. Measured across the harvest: 19 of 834 permits producing an
# approved Building Final are demolition/non-housing, 93 are alterations, 58 ambiguous.
# Only housing_rules.permit_role.classify == 'new_unit' sets a date; the rest are reported, not used.
CO_ROLES = {"new_unit"}


def _iso(s):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(str(s), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def permit_roles():
    """permit -> role, from the CPRA feed where the permit is in it, else the census description."""
    import pandas as pd, warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(ROOT / "scripts"))
    from housing_rules.permit_role import classify
    from multiunit_master_list import load_census
    cp = pd.concat([pd.read_excel(f, header=7) for f in
                    glob.glob(str(ROOT / "data/raw/cpra-downloads/BP_Annual*.xlsx"))]
                   ).drop_duplicates("PermitNumber", keep="last").set_index("PermitNumber")
    census = load_census("Building", "Permit Number")
    roles = {}
    for pn in set(cp.index) | set(census):
        if pn in cp.index:
            r = cp.loc[pn]
            if getattr(r, "ndim", 1) > 1:
                r = r.iloc[0]
            roles[pn] = classify(r.get("Work Type"), r.get("WorkDescription"), r.get("ADU"),
                                 r.get("OccType"), r.get("UnitsAdded"), r.get("UnitsRemoved"), pn)[0]
        else:
            roles[pn] = classify(None, (census.get(pn) or {}).get("Description"),
                                 None, None, None, None, pn)[0]
    return roles


def read_inspections(roles=None):
    """permit -> {co, role, n_inspections, n_final_rows, final_results}. co = LAST approved building
    final, and ONLY when the permit's role can create a dwelling (see CO_ROLES)."""
    roles = roles or {}
    out = {}
    for f in sorted(INSPECTIONS.glob("*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        pn = d.get("permit_number")
        if not pn:
            continue
        ins = d.get("inspections") or []
        finals = [i for i in ins if str(i.get("type_code", "")).strip() == BUILDING_FINAL]
        dates = sorted(x for x in (_iso(i.get("date")) for i in finals
                                   if i.get("result") == PASSING) if x)
        role = roles.get(pn, "unknown")
        if role not in CO_ROLES:
            dates = []                     # finaled, but not a dwelling-creating permit
        out[pn] = dict(co=dates[-1] if dates else None, role=role, n_inspections=len(ins),
                       n_final_rows=len(finals),
                       final_results=";".join(sorted({str(i.get("result")) for i in finals})),
                       scraped=str(d.get("extraction_timestamp") or "")[:10])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tolerance", type=int, default=7)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()

    roles = permit_roles()
    insp = read_inspections(roles)
    con = sqlite3.connect(V2)
    con.row_factory = sqlite3.Row
    permit_to_project = {}
    for r in con.execute("select pm.permit_number, pm.project_id from permits pm where pm.permit_number is not null"):
        permit_to_project[r["permit_number"]] = r["project_id"]
    projects = {r["project_id"]: dict(r) for r in con.execute(
        "select project_id, address_display, total_units, status_label, co_issued_date from v_projects_flat")}
    con.close()

    by_project = defaultdict(dict)
    untracked = []
    for pn, v in insp.items():
        pid = permit_to_project.get(pn)
        (by_project[pid] if pid else untracked).__setitem__(pn, v) if pid else untracked.append((pn, v))

    rows = []
    for pid, permits in by_project.items():
        p = projects.get(pid)
        if not p:
            continue
        cos = {pn: v["co"] for pn, v in permits.items() if v["co"]}
        latest = max(cos.values()) if cos else None
        v2co = (p["co_issued_date"] or "")[:10] or None
        if not cos:
            cls = ("final_but_not_housing" if any(v["n_final_rows"] and v.get("role") not in CO_ROLES
                                                  for v in permits.values()) else "no_building_final")
            delta = ""
        elif not v2co:
            cls, delta = "fills_gap", ""
        else:
            delta = (dt.date.fromisoformat(latest) - dt.date.fromisoformat(v2co)).days
            cls = ("agrees" if abs(delta) <= a.tolerance
                   else "disagrees_small" if abs(delta) <= 60 else "disagrees_large")
        rows.append(dict(
            project_id=pid, address=p["address_display"], units=p["total_units"],
            v2_status=p["status_label"], v2_co_date=v2co or "",
            inspection_co_date=latest or "", classification=cls, delta_days=delta,
            n_permits_with_inspections=len(permits),
            n_permits_with_approved_final=len(cos),
            multi_permit=int(len(cos) > 1),
            per_permit=";".join(f"{k}={v}" for k, v in sorted(cos.items())),
            final_results_seen=";".join(sorted({v["final_results"] for v in permits.values() if v["final_results"]})),
            roles_seen=";".join(sorted({v.get("role","?") for v in permits.values()})),
            excluded_by_role=int(bool(permits) and not cos and any(
                v["n_final_rows"] and v.get("role") not in CO_ROLES for v in permits.values())),
        ))
    rows.sort(key=lambda r: (r["classification"], -(r["units"] or 0)))

    OUT.mkdir(exist_ok=True)
    f = OUT / f"co_from_inspections_{a.date}.csv"
    with open(f, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    counts = defaultdict(lambda: [0, 0])
    for r in rows:
        counts[r["classification"]][0] += 1
        counts[r["classification"]][1] += r["units"] or 0
    print(f"{f.name}: {len(rows)} projects from {len(insp)} harvested permits "
          f"({len(untracked)} permits not tracked by v2)")
    for k in ("fills_gap", "agrees", "disagrees_small", "disagrees_large", "no_building_final",
              "final_but_not_housing"):
        n, u = counts[k]
        print(f"  {k:18} {n:>4} projects  {u:>6} units")
    con = sqlite3.connect(V2)
    gap = con.execute("select count(*), sum(total_units) from v_projects_flat "
                      "where status_label='Completed' and co_issued_date is null").fetchone()
    con.close()
    print(f"\n  for scale: v2 has {gap[0]} projects marked Completed with NO co_issued_date ({gap[1]} units)")


if __name__ == "__main__":
    main()
