#!/usr/bin/env python3
"""Reconcile every v2 project's status against the independent record. READ-ONLY; proposes, never writes.

Provoked 2026-09-23 by proj4, 1914 Fifth St: v2 carries 257 units at "In Review", the site was cleared
in 2015, two development attempts were withdrawn, and John confirmed from the street that it is a
parking lot. The status was defensible; the 257 units in the pipeline total were not informative. This
script asks the same questions of all 909 projects.

EVIDENCE, per project, gathered by ADDRESS rather than by v2's permit attachments (trusting the
attachment is what produced the 1914 Fifth false positive):
  - every census building permit at the address, with its current status and description
  - whether any of them is a NEW-CONSTRUCTION permit (housing_rules role 'new_unit')
  - whether any new_unit permit has an APPROVED 'Building 1200 Building Final' (the CO event)
  - the entitlement trail at the address: planning records and their statuses
  - the assessor built-signal (Imps) on the project's parcel

PROPOSED STATUS is advisory and always carries its reason. Six rules, conservative by design:
  completed_evidence     not Completed, but a new_unit permit has an approved Building Final
  built_no_final         not Completed, no final, but assessor Imps is large (reassessment lag case)
  dead_entitlement       In Review/Entitled/Pre-App, NO new-construction BP at the address, and every
                         entitlement record is Withdrawn/Closed/Void/Denied  -> the 1914 Fifth class
  stalled_no_bp          In Review/Entitled for >=3 years with no new-construction BP, entitlement live
  completed_unverified   Completed but no approved final anywhere and Imps = 0
  ok                     nothing to say

Nothing here changes a status. Output is a review sheet; the v2 write is a separate gated step, and
`status_label` also feeds the flyover colours, so a wrong flip is publicly visible.

Usage: python scripts/reconcile_project_status.py [--date YYYY-MM-DD]
"""
import argparse, csv, datetime as dt, json, re, sqlite3, sys, warnings
from collections import defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from multiunit_master_list import load_census, addr_key, load_address_apn   # noqa: E402
from housing_rules.permit_role import classify                              # noqa: E402

V2 = ROOT / "databases/berkeley_housing_v2.db"
ASSESSOR = ROOT / "databases/berkeley.db"
OUT = ROOT / "data/derived"
TERMINAL_PLANNING = {"Withdrawn", "Closed", "Void", "Denied", "Expired"}
BUILDING_FINAL = "Building 1200 Building Final"


# A census permit carries no Work Type and no UnitsAdded, and classify() needs both to reach
# 'new_unit' — measured 2026-09-23, even "New Construction of a 6-story multifamily with 60
# residential units" comes back 'ambiguous'. So new-construction detection is done in two tiers:
# the CPRA feed (authoritative: real Work Type + UnitsAdded, routed through classify) and, for
# permits outside the feed, this text test. Getting this wrong in the permissive direction is the
# safer error: a missed new-construction permit would wrongly call a live project dead.
_NEWCON = re.compile(
    r"\bnew construction\b|\bconstruct(?:ion of)?\s+(?:a\s+)?new\b|\bnew\s+\d+[- ]stor(?:y|ey)\b"
    r"|\bphase\s+[iv1-9]+\b.*\b(?:unit|multifamily|multi[- ]family|apartment|residential)\b"
    r"|\b\d{1,3}[- ]unit\b.*\b(?:building|bldg|multifamily|multi[- ]family|apartment)\b"
    r"|\b(?:multifamily|multi[- ]family)\s+building\b|\bnew\s+(?:sfd|single[- ]family|duplex|adu)\b", re.I)
_DEMO = re.compile(r"\bdemo(?:lish|lition)?\b", re.I)


def is_new_construction(desc, cpra_row=None, permit_number=""):
    """True when this permit could create a dwelling. CPRA row first (authoritative), text second."""
    if cpra_row is not None:
        role = classify(cpra_row.get("Work Type"), cpra_row.get("WorkDescription"), cpra_row.get("ADU"),
                        cpra_row.get("OccType"), cpra_row.get("UnitsAdded"), cpra_row.get("UnitsRemoved"),
                        permit_number)[0]
        if role == "new_unit":
            return True
        if str(cpra_row.get("Work Type") or "").strip().lower().startswith("new"):
            return True
    d = str(desc or "")
    if _DEMO.search(d[:80]) and not _NEWCON.search(d):
        return False
    return bool(_NEWCON.search(d))


def infer_work_type(desc):
    d = str(desc or "").lower()
    if re.search(r"\bdemo(lish|lition)?\b", d[:80]):
        return "Demolition"
    if re.search(r"\bnew construction\b|\bconstruct a new\b|\bnew \d+[- ]story\b", d):
        return "New"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()

    con = sqlite3.connect(V2); con.row_factory = sqlite3.Row
    projects = [dict(r) for r in con.execute(
        "select project_id, address_display, address_normalized, total_units, status_label, "
        "co_issued_date, bp_issued_date, filed_date, entitled_date from v_projects_flat")]
    # approved building finals now live in v2 (Layer A)
    finals = defaultdict(list)
    for pn, d in con.execute(
            "select permit_number, inspection_date from inspections "
            "where type_code=? and result='Approved' and inspection_date is not null", (BUILDING_FINAL,)):
        finals[pn].append(d)
    parcel_apn = {r[0]: r[1] for r in con.execute(
        "select pp.project_id, p.apn_normalized from project_parcels pp join parcels p on p.id=pp.parcel_id "
        "where p.apn_normalized is not null")}
    con.close()

    import pandas as pd, glob
    cpra = pd.concat([pd.read_excel(f, header=7) for f in
                      glob.glob(str(ROOT / "data/raw/cpra-downloads/BP_Annual*.xlsx"))]
                     ).drop_duplicates("PermitNumber", keep="last").set_index("PermitNumber")
    B, P = load_census("Building", "Permit Number"), load_census("Planning", "Record Number")
    a2a = load_address_apn()
    bld, pln = defaultdict(list), defaultdict(list)
    for pn, r in B.items():
        k = addr_key(r.get("Address"))
        if k: bld[k].append((pn, r))
    for rn, r in P.items():
        k = addr_key(r.get("Project Name")) or addr_key(r.get("Description"))
        if k: pln[k].append((rn, r))

    imps = {}
    if ASSESSOR.exists():
        ac = sqlite3.connect(ASSESSOR)
        from housing_rules.apn import to_canonical_apn
        for apn, im in ac.execute("select APN, Imps from parcels where APN is not null"):
            c = to_canonical_apn(apn)
            if c: imps[c] = im or 0
        ac.close()

    rows = []
    for p in projects:
        k = addr_key(p["address_normalized"] or p["address_display"])
        bs = bld.get(k, []) if k else []
        ps = pln.get(k, []) if k else []
        newcon = []
        for pn, r in bs:
            cr = None
            if pn in cpra.index:
                cr = cpra.loc[pn]
                if getattr(cr, "ndim", 1) > 1:
                    cr = cr.iloc[0]
            if is_new_construction(r.get("Description"), cr, pn):
                newcon.append(pn)
        co_dates = sorted(d for pn in newcon for d in finals.get(pn, []))
        apn = parcel_apn.get(p["project_id"]) or (a2a.get(k) if k else None)
        im = imps.get(apn)
        ent_live = [rn for rn, r in ps if r.get("Status") not in TERMINAL_PLANNING]
        ent_dead = [rn for rn, r in ps if r.get("Status") in TERMINAL_PLANNING]
        st = p["status_label"]
        age = None
        if p["filed_date"]:
            try: age = (dt.date.fromisoformat(a.date) - dt.date.fromisoformat(p["filed_date"][:10])).days // 365
            except ValueError: pass

        flag, reason = "ok", ""
        if st != "Completed" and co_dates:
            flag = "completed_evidence"
            reason = f"approved Building Final {co_dates[-1]} on new-construction permit(s) {','.join(newcon[:3])}"
        elif st in ("Under Construction", "Permitted") and newcon and im and im > 2_000_000 and not co_dates:
            # NOT a general 'Imps>0 means built' test: on a redevelopment site Imps is the EXISTING
            # building's value (2700 Shattuck $11.9M, Ashby BART $5.5M are pre-project structures).
            # Only meaningful once a new-construction permit exists AND the project is past entitlement.
            flag = "built_no_final"
            reason = (f"permitted/under construction with new-construction BP {newcon[0]} and assessor "
                      f"Imps ${im:,.0f}, but no approved Building Final — check for an unrecorded final")
        elif st in ("In Review", "Entitled", "Pre-Application") and not newcon and ps and not ent_live:
            flag = "dead_entitlement"
            reason = (f"no new-construction BP at the address; all {len(ent_dead)} planning records "
                      f"terminal ({','.join(sorted({r.get('Status') for _, r in ps}))})")
        elif st in ("In Review", "Entitled") and not newcon and age and age >= 3:
            flag = "stalled_no_bp"
            reason = f"{age}y since filing, no new-construction BP at the address; {len(ent_live)} live planning record(s)"
        elif st == "Completed" and not co_dates and (im is not None and im == 0):
            flag = "completed_unverified"
            reason = "no approved Building Final and assessor Imps = $0"

        rows.append(dict(
            project_id=p["project_id"], address=p["address_display"], units=p["total_units"],
            v2_status=st, flag=flag, reason=reason,
            co_evidence_date=co_dates[-1] if co_dates else "",
            n_census_building_permits=len(bs), new_construction_permits=";".join(newcon[:4]),
            latest_building_status=max((str(r.get("Status") or "") for _, r in bs), default=""),
            planning_records=";".join(rn for rn, _ in ps[:6]),
            planning_statuses=";".join(sorted({str(r.get("Status")) for _, r in ps})),
            live_planning=len(ent_live), assessor_imps=im if im is not None else "",
            apn=apn or "", years_since_filing=age if age is not None else "",
            address_matched_census=int(bool(bs)),
        ))

    order = {"completed_evidence": 0, "dead_entitlement": 1, "built_no_final": 2, "stalled_no_bp": 3,
             "completed_unverified": 4, "ok": 5}
    rows.sort(key=lambda r: (order[r["flag"]], -(r["units"] or 0)))
    OUT.mkdir(exist_ok=True)
    f = OUT / f"project_status_reconcile_{a.date}.csv"
    with open(f, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    agg = defaultdict(lambda: [0, 0])
    for r in rows:
        agg[r["flag"]][0] += 1; agg[r["flag"]][1] += r["units"] or 0
    print(f"{f.name}: {len(rows)} projects")
    for k in order:
        n, u = agg[k]
        if n: print(f"  {k:22} {n:>4} projects  {u:>6} units")
    print(f"\n  address matched the census: {sum(r['address_matched_census'] for r in rows)} of {len(rows)}")


if __name__ == "__main__":
    main()
