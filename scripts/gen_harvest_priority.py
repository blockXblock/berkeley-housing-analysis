#!/usr/bin/env python3
"""gen_harvest_priority.py — ranked list of BIG multi-parcel projects whose architect plan sets we do NOT
yet hold, WITH the city permit/case record IDs so a Chrome/harvester run can pull the plans.

Reads the footprint-vs-parcel audit (data/reference/footprint_vs_parcel_doc_audit.csv), keeps the multi-
parcel projects with no plan/tabulation doc and >=45 units, and attaches — for each — the Accela record
IDs to look up on Berkeley's permit portal: Building Permit numbers (Bxxxx-xxxxx) and Zoning/pre-app
numbers (ZPxxxx-xxxx) from the `permits` table (+ any embedded in document permit_number / titles), the
largest BP valuation (confirms the real construction record), how many documents we already hold, and a
harvest note. Output: data/reference/harvest_priority_plansets.csv.

The harvest keys live in `permits.permit_number`, NOT `documents` — that was the v1 bug. Read-only.
Run: python scripts/gen_harvest_priority.py
"""
import sqlite3, re
import pandas as pd

BP = re.compile(r"\bB\d{4}-\d{4,5}\b")            # building permit record (plans attached here)
ZP = re.compile(r"\b(?:ZP|UP|DRCP|ZC|LMSAP)\d{4}-\d{3,4}\b", re.I)  # zoning / pre-app / use-permit record

def main():
    aud = pd.read_csv("data/reference/footprint_vs_parcel_doc_audit.csv")
    aud["units"] = aud.name.str.extract(r"(\d+) units").astype(float)
    big = aud[(aud.nparc > 1) & (~aud.has_measure_doc) & (aud.units >= 45) & aud.project_id.notna()].copy()
    big["project_id"] = big.project_id.astype(int)

    v2 = sqlite3.connect("databases/berkeley_housing_v2.db")
    flat = pd.read_sql("SELECT project_id, address_display, total_units FROM v_projects_flat", v2)
    permits = pd.read_sql("SELECT project_id, permit_number, valuation, issued_date, description FROM permits", v2)
    docs = pd.read_sql("SELECT project_id, title, permit_number, r2_url FROM documents", v2)
    uc = set(pd.read_sql(
        "SELECT DISTINCT pc.project_id FROM project_classifications pc "
        "JOIN vocabulary_classification_types ct ON ct.id=pc.classification_type_id "
        "WHERE ct.code='uc_project'", v2).project_id)

    def harvest_ids(pid):
        """Return (bp_ids, zp_ids, max_bp_valuation, latest_bp_issued) for the project."""
        pp = permits[permits.project_id == pid]
        dd = docs[docs.project_id == pid]
        blob = " ".join([str(x) for x in
                         list(pp.permit_number.dropna()) + list(dd.permit_number.dropna()) + list(dd.title.dropna())])
        bps = sorted(set(BP.findall(blob)))
        zps = sorted({m.upper() for m in ZP.findall(blob)})
        # largest construction BP valuation (the real building record)
        val = pp.valuation.dropna()
        maxval = int(val.max()) if len(val) and val.max() > 0 else None
        # latest BP issued date among rows whose permit_number is a B-record
        bprows = pp[pp.permit_number.fillna("").str.match(r"B\d{4}-\d")]
        issued = bprows.issued_date.dropna()
        latest = max(issued) if len(issued) else None
        return " ".join(bps), " ".join(zps), maxval, latest

    recs = []
    for _, r in big.iterrows():
        pid = r.project_id
        row = flat[flat.project_id == pid]
        addr = row.address_display.iloc[0] if len(row) else r["name"].split(" · ")[0]
        bp, zp, val, issued = harvest_ids(pid)
        ndoc = int((docs.project_id == pid).sum())
        is_uc = pid in uc
        if is_uc:
            note = "UC PROJECT — no city permit (UC self-permits); harvest plans from UC, not the Accela portal"
        elif bp:
            note = "BP record on file — plans attach to this permit; harvest its plan set"
        elif zp:
            note = "only a zoning/pre-app record — pull schematic/site plan; BP may not be issued yet"
        else:
            note = "NO city record on file — find the Accela case number first (portal search by address)"
        recs.append({"units": int(r.units), "project_id": pid, "address": addr, "is_uc": is_uc,
                     "bp_records": bp, "zoning_records": zp, "max_bp_valuation": val,
                     "latest_bp_issued": issued, "parcels_spanned": int(r.nparc),
                     "fp_over_lots_ratio": r.ratio, "docs_held": ndoc, "harvest_note": note})
    out = pd.DataFrame(recs).sort_values("units", ascending=False).reset_index(drop=True)
    out.insert(0, "rank", out.index + 1)
    out.to_csv("data/reference/harvest_priority_plansets.csv", index=False)

    pd.set_option("display.max_colwidth", 40); pd.set_option("display.width", 240)
    print(f"ranked harvest list: {len(out)} big (>=45u) multi-parcel projects missing a harvested plan set "
          f"-> data/reference/harvest_priority_plansets.csv\n")
    show = out[["rank", "units", "address", "is_uc", "bp_records", "zoning_records", "docs_held"]]
    print(show.to_string(index=False))
    nonuc = out[~out.is_uc]
    has_bp = int((nonuc.bp_records != "").sum())
    has_zp = int(((nonuc.bp_records == "") & (nonuc.zoning_records != "")).sum())
    norec = int(((nonuc.bp_records == "") & (nonuc.zoning_records == "")).sum())
    print(f"\n  UC (harvest from UC, not the city): {int(out.is_uc.sum())}"
          f"   |  city-permittable — BUILDING-PERMIT record: {has_bp}"
          f"   |  only zoning/pre-app: {has_zp}"
          f"   |  no city record yet: {norec}")

if __name__ == "__main__":
    main()
