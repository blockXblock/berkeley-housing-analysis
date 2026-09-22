#!/usr/bin/env python3
"""Every multi-unit housing project in Berkeley, current — derived from primary sources, read-only.

Built 2026-09-21 (notes/2026-09-21_multiunit_master_list_plan.md, Track C). Answers John's ask: a
recently-updated list of every multi-unit project, with planning + building status, that v2 can be
reconciled AGAINST. Nothing here writes to any DB; the outputs are derived CSVs for review, and the
`not_in_v2` rows are the ingestion worklist for a later gated write.

Sources (all primary; CKAN/HCD never read — CLAUDE.md rule 1):
  1. Accela date-range census  data/raw/accela/date_range/{Building,Planning}_*.jsonl
     - one row per record FILED in the window, with the record's status AS OF THE SCRAPE (file mtime).
       Built 2026-07-03/04 (2015 -> 2026-07-03) + swept 2026-09-21 (2026-07-04 -> 09-21).
     - Building rows carry Address; Planning rows carry only Project Name (address in ~54%).
  2. CPRA "BP Annual Permit Report" productions  data/raw/cpra-downloads/BP_Annual Permit Report-*.xlsx
     - Issued-only extract (expired/cancelled absent by construction); 23 columns; UnitsAdded is
       inflated on -DEF/-REV children (housing_rules.permit_role.classify undoes that).
     - Later productions win per permit (they are re-runs with refreshed finaled dates).
  3. v2  databases/berkeley_housing_v2.db  (v_projects_flat + permits + project_parcels/parcels)
     - the SERVING DB we are reconciling against, matched by permit number, canonical APN, and the
       3-layer address normalizer (housing_rules.address.normalize_address) — never bare strings.

Candidate = any record with a multi-unit signal:
  - CPRA primary permit (role not subsidiary/demolition/non_housing) with net_units >= --min-units
  - census Building record NOT in any CPRA production, in an active/pending status, with >= min units
    in its description (a SCREEN — `units_source=description`, review before trusting)
  - census Planning record of a housing type (Zoning Permit / Pre-Application / Use Permit / Design
    Review) with >= min units in Project Name or Description (same screen)
Records group into projects by canonical APN when known, else by (house number, street).

Outputs (data/derived/):
  multiunit_projects_<date>.csv  — one row per project: ids, address, apn, best units (+source),
                                   planning record(s)+status, building record(s)+status, CPRA dates,
                                   v2 project_id / match_basis, not_in_v2, needs_status_refresh
  multiunit_records_<date>.csv   — one row per contributing record (traceability)
  + a summary printed to stdout.

Usage: python scripts/multiunit_master_list.py [--min-units 2] [--date YYYY-MM-DD]
"""
import argparse, csv, datetime as dt, glob, json, os, re, sqlite3, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from housing_rules.address import normalize_address          # noqa: E402  (rule 4c — the ONE copy)
from housing_rules.apn import to_canonical_apn                # noqa: E402  (rule 4 — the ONE canon)
from housing_rules.permit_role import classify, net_units     # noqa: E402

CENSUS = ROOT / "data/raw/accela/date_range"
CPRA_DIR = ROOT / "data/raw/cpra-downloads"
V2 = ROOT / "databases/berkeley_housing_v2.db"
OUT = ROOT / "data/derived"

# CPRA productions, OLDEST -> NEWEST: a later production's row wins for a permit seen in both.
CPRA_FILES = [
    "BP_Annual Permit Report-2018-2022.xlsx",
    "BP_Annual Permit Report-2023-2025.xlsx",
    "BP_Annual Permit Report-2023-2025_rerun-2026-07-07.xlsx",
    "BP_Annual Permit Report-2025-2026-07-07.xlsx",
]
RECORD_RE = re.compile(r"^[A-Z]{1,5}\d{4}-\d{3,6}")           # drops the pagination junk rows
ACTIVE_BUILDING = {"Issued", "Under Review", "Corrections List Issued", "Approved w/Conditions",
                   "Ready To Issue", "Ready to Issue", "Pending Payment", "Received", "Approved"}
PLANNING_TYPES = ("Zoning Permit", "Pre-Application", "Use Permit", "Administrative Use Permit",
                  "Design Review")
# Unit-count screen on free text. Catches "124 Unit Mixed Use", "40-unit", "6 apartments";
# also catches "replace subpanel in all 6 apartments" — hence units_source=description is a flag.
UNIT_RE = re.compile(
    r"\b(\d{1,3})\s*[-–]?\s*(?:new\s+)?(?:dwelling\s+)?(?:residential\s+)?(?:rental\s+)?"
    r"(?:unit|units|dwelling units|apartments?|condos?|condominiums?|townhomes?|townhouses?|flats)\b", re.I)
ADDR_IN_TEXT = re.compile(r"\b(\d{1,5})\s+([A-Za-z][A-Za-z .'-]{2,40}?)(?:\s+(?:st|street|ave|avenue|way|blvd|"
                          r"boulevard|rd|road|dr|drive|ln|lane|ct|court|pl|place|ter|terrace)\b\.?)", re.I)


def units_in_text(text):
    m = [int(x) for x in UNIT_RE.findall(str(text or "")) if 0 < int(x) < 2000]
    return max(m) if m else 0


PREFIX_RE = re.compile(r"^\s*(?:[A-Z0-9 /&-]{2,14}:\s*)+")           # "SB330: ", "UP MOD: ", "ZCMH: "
BARE_ADDR = re.compile(r"^\s*(\d{1,5})\s+([A-Za-z][A-Za-z .'-]{2,40}?)\s*\.?\s*$")


def address_in_text(text):
    """Best-effort site address from free text: a bare 'NNNN Street' field, else 'NNNN Street <suffix>'."""
    t = PREFIX_RE.sub("", str(text or ""))
    m = BARE_ADDR.match(t)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    m = ADDR_IN_TEXT.search(t)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    m = re.search(r"\b(?:at|@|of|for)\s+(\d{3,5})\s+([A-Za-z][A-Za-z'-]{2,20}(?:\s+[A-Z][A-Za-z'-]{2,20})?)", t)
    if m and m.group(2).split()[0].lower() not in _NOT_STREET:
        return f"{m.group(1)} {m.group(2)}"
    return ""


_NOT_STREET = {"dwelling", "dwellings", "unit", "units", "square", "sq", "sf", "residential", "apartment",
               "apartments", "story", "stories", "foot", "feet", "ft", "bed", "beds", "bedroom", "parking",
               "spaces", "new", "existing", "the", "and", "with", "total", "affordable", "rental", "student"}


def desc_key(text):
    """Records of one project (ZP + PLN + DRCP) usually share a verbatim description — the only
    join available when Planning rows carry no address. First 120 chars, normalized."""
    t = re.sub(r"[^a-z0-9 ]", " ", str(text or "").lower())
    t = re.sub(r"\s+", " ", t).strip()
    return t[:120] if len(t) >= 25 else None


# Project Names / situs strings carry trailing junk the normalizer is not built for:
# "2138 KITTREDGE STREET - PDR", "1752 Shattuck Final Design Review", "2601 COLLEGE Ave, BERKELEY CA 94704, SHARE".
_JUNK = re.compile(r"\s*(?:,| - |–|\(|\bfinal\b|\bpreliminary\b|\bdesign review\b|\buse permit\b|\bmixed[- ]use\b|"
                   r"\*|\bview additional\b|\bpdr\b|\bpre[- ]?app\b|\bsb ?\d{2,4}\b|\bab ?\d{3,4}\b|\bunit\b|\bapt\b|#).*$", re.I)


def clean_address(raw):
    return _JUNK.sub("", str(raw or "")).strip()


def addr_key(raw):
    num, street = normalize_address(clean_address(raw))
    return (num, street) if num and street else None


# ----------------------------------------------------------------------------- loaders
def load_census(module, key):
    """Dedupe by record number; the LAST window file (sorted) wins. status_asof = that file's mtime."""
    recs = {}
    for f in sorted(glob.glob(str(CENSUS / f"{module}_*.jsonl"))):
        asof = dt.date.fromtimestamp(os.path.getmtime(f)).isoformat()
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                k = str(r.get(key) or "")
                if RECORD_RE.match(k):
                    r["_status_asof"] = asof
                    r["_window"] = Path(f).stem
                    recs[k] = r
    return recs


def load_cpra():
    import pandas as pd
    per = {}
    for name in CPRA_FILES:
        f = CPRA_DIR / name
        if not f.exists():
            print(f"  ! missing CPRA production {name} — skipped", file=sys.stderr)
            continue
        df = pd.read_excel(f, header=7)
        df = df[[c for c in df.columns if not str(c).startswith("Unnamed")]]
        for r in df.to_dict("records"):
            pn = str(r.get("PermitNumber") or "").strip()
            if not pn or pn == "nan":
                continue
            r = {k: (None if (v is None or str(v) == "nan" or str(v) == "NaT") else v) for k, v in r.items()}
            r["_production"] = name
            per[pn] = r                       # later production wins
    return per


RECORD_STATUS = ROOT / "data/raw/accela_record_status"


def load_record_status():
    """Per-record CapDetail snapshots (scripts/refresh_record_status.py, Track D): record -> {status, work_location, asof}.
    Newer than the census for the records it covers; the overlay below prefers it when its date is later."""
    out = {}
    for f in glob.glob(str(RECORD_STATUS / "*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if d.get("record_status") and d.get("scraped_at"):
            out[d["permit_number"]] = dict(status=d["record_status"], work_location=d.get("work_location") or "",
                                           asof=str(d["scraped_at"])[:10])
    return out


def overlay_record_status(records, rs):
    """Replace a record's census status/asof with the per-record snapshot when the snapshot is newer; fill a
    missing address from work_location. Marks the record so the CSV shows where the status came from."""
    n = 0
    for r in records:
        snap = rs.get(r["record"])
        if not snap or snap["asof"] < r["status_asof"]:
            continue
        if snap["status"] != r["status"]:
            r["census_status"] = r["status"]
        r["status"], r["status_asof"], r["status_source"] = snap["status"], snap["asof"], "capdetail"
        if not addr_key(r["address"]) and snap["work_location"]:
            r["address"] = snap["work_location"]; r["address_borrowed"] = 0; r["address_from"] = "capdetail"
        n += 1
    return n


def load_v2():
    con = sqlite3.connect(V2)
    con.row_factory = sqlite3.Row
    projects = {r["project_id"]: dict(r) for r in con.execute(
        "select project_id, address_display, address_normalized, total_units, status_label, filed_date, "
        "entitled_date, bp_issued_date, co_issued_date from v_projects_flat")}
    by_permit = {r[0]: r[1] for r in con.execute("select permit_number, project_id from permits where permit_number is not null")}
    by_apn = defaultdict(set)
    for apn, pid in con.execute("select p.apn_normalized, pp.project_id from project_parcels pp join parcels p on p.id=pp.parcel_id"):
        if apn:
            by_apn[apn].add(pid)
    by_addr = defaultdict(set)
    for pid, p in projects.items():
        k = addr_key(p["address_normalized"] or p["address_display"])
        if k:
            by_addr[k].add(pid)
    con.close()
    return projects, by_permit, by_apn, by_addr


# ----------------------------------------------------------------------------- candidates
def cpra_candidates(cpra, census_b, min_units):
    out = []
    for pn, r in cpra.items():
        role, is_master, note = classify(r.get("Work Type"), r.get("WorkDescription"), r.get("ADU"),
                                         r.get("OccType"), r.get("UnitsAdded"), r.get("UnitsRemoved"), pn)
        if role in ("subsidiary", "demolition", "non_housing"):
            continue
        u = net_units(r.get("UnitsAdded"), r.get("UnitsRemoved"), role, r.get("WorkDescription") or "")
        if (u or 0) < min_units:
            continue
        c = census_b.get(pn, {})
        addr = f"{str(r.get('StreetNumber') or '').split('.')[0]} {r.get('StreetName') or ''} {r.get('StreetType') or ''}".strip()
        out.append(dict(record=pn, module="Building", source="cpra", record_type=r.get("Work Type"),
                        role=role, units=int(u), units_source="cpra_UnitsAdded", status_source="census",
                        address=addr, apn=to_canonical_apn(r.get("Parcel Number")),
                        filed=str(r.get("Submittal Date") or "")[:10], issued=_mdy(r.get("Issuance Date")),
                        finaled=str(r.get("Finaled Date") or "")[:10],
                        status=c.get("Status") or ("Finaled" if r.get("Finaled Date") else "Issued (CPRA; not in census)"),
                        status_asof=c.get("_status_asof") or _prod_date(r["_production"]),
                        description=str(r.get("WorkDescription") or "")[:160], production=r["_production"]))
    return out


def census_building_candidates(census_b, cpra, min_units):
    out = []
    for pn, r in census_b.items():
        if pn in cpra or r.get("Status") not in ACTIVE_BUILDING:
            continue
        u = units_in_text(r.get("Description"))
        if u < min_units:
            continue
        out.append(dict(record=pn, module="Building", source="census", record_type=r.get("Project Name"),
                        role="screen", units=u, units_source="description", status_source="census",
                        address=str(r.get("Address") or ""), apn=None,
                        filed=_mdy(r.get("Date")), issued="", finaled="",
                        status=r.get("Status"), status_asof=r["_status_asof"],
                        description=str(r.get("Description") or "")[:160], production=r["_window"]))
    return out


def planning_candidates(census_p, min_units):
    out = []
    for rn, r in census_p.items():
        rtype = str(r.get("Record Type") or "")
        if not (rtype.startswith(PLANNING_TYPES) or rn.startswith("ZP")):
            continue
        text = f"{r.get('Project Name') or ''} | {r.get('Description') or ''}"
        u = units_in_text(text)
        if u < min_units:
            continue
        addr = address_in_text(r.get("Project Name")) or address_in_text(r.get("Description"))
        out.append(dict(record=rn, module="Planning", source="census", record_type=rtype, role="screen",
                        units=u, units_source="description", status_source="census", address=addr, apn=None,
                        filed=_mdy(r.get("Date")), issued="", finaled="",
                        status=r.get("Status"), status_asof=r["_status_asof"],
                        description=str(r.get("Description") or "")[:160], production=r["_window"]))
    return out


def _mdy(s):
    s = str(s or "")
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", s)
    return f"{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else s[:10]


def _prod_date(name):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else ""


# ----------------------------------------------------------------------------- grouping + v2 match
def group_projects(records):
    """APN first (when known), else address. Records without either stay singletons (flagged)."""
    by_addr_apn = {}                         # addr_key -> apn learned from a CPRA row at that address
    for r in records:
        k = addr_key(r["address"])
        if k and r["apn"]:
            by_addr_apn.setdefault(k, r["apn"])
    # Borrow an address across records that share a description (Planning rows without one).
    by_desc_addr = {}
    for r in records:
        d = desc_key(r["description"])
        if d and r["address"] and addr_key(r["address"]):
            by_desc_addr.setdefault(d, r["address"])
    for r in records:
        if not addr_key(r["address"]):
            d = desc_key(r["description"])
            if d and d in by_desc_addr:
                r["address"] = by_desc_addr[d]
                r["address_borrowed"] = 1
    groups = defaultdict(list)
    for r in records:
        k = addr_key(r["address"])
        apn = r["apn"] or (by_addr_apn.get(k) if k else None)
        d = desc_key(r["description"])
        gkey = ("apn", apn) if apn else (("addr",) + k if k else (("desc", d) if d else ("rec", r["record"])))
        r["_apn_eff"] = apn
        groups[gkey].append(r)
    return groups


def match_v2(recs, apn, akey, v2):
    projects, by_permit, by_apn, by_addr = v2
    hits, basis = set(), []
    for r in recs:
        if r["record"] in by_permit:
            hits.add(by_permit[r["record"]]); basis.append("permit")
    if apn and apn in by_apn:
        hits |= by_apn[apn]; basis.append("apn")
    if akey and akey in by_addr:
        hits |= by_addr[akey]; basis.append("address")
    if not hits and akey:                         # rule 4c house-number tolerance — a WEAKER basis, flagged
        num, street = akey
        for (n2, s2), pids in by_addr.items():
            if s2 == street and n2.isdigit() and num.isdigit() and abs(int(n2) - int(num)) <= 10:
                hits |= pids; basis.append("address~10")
    return sorted(hits), "+".join(sorted(set(basis)))


def build(min_units, today):
    print("loading census …", file=sys.stderr)
    census_b = load_census("Building", "Permit Number")
    census_p = load_census("Planning", "Record Number")
    print(f"  building {len(census_b):,} | planning {len(census_p):,}", file=sys.stderr)
    print("loading CPRA productions …", file=sys.stderr)
    cpra = load_cpra()
    print(f"  {len(cpra):,} permits (latest production wins)", file=sys.stderr)
    v2 = load_v2()

    records = (cpra_candidates(cpra, census_b, min_units)
               + census_building_candidates(census_b, cpra, min_units)
               + planning_candidates(census_p, min_units))
    rs = load_record_status()
    n_over = overlay_record_status(records, rs)
    print(f"  per-record status snapshots: {len(rs):,} loaded, {n_over} records overlaid", file=sys.stderr)
    groups = group_projects(records)

    rows = []
    for gkey, recs in groups.items():
        apn = recs[0]["_apn_eff"]
        akeys = [addr_key(r["address"]) for r in recs if addr_key(r["address"])]
        akey = akeys[0] if akeys else None
        addr = next((clean_address(r["address"]) for r in recs if addr_key(r["address"])), "")
        best = max(recs, key=lambda r: (r["units_source"] == "cpra_UnitsAdded", r["units"]))
        pl = [r for r in recs if r["module"] == "Planning"]
        bp = [r for r in recs if r["module"] == "Building"]
        latest_pl = max(pl, key=lambda r: r["filed"]) if pl else None
        latest_bp = max(bp, key=lambda r: r["filed"]) if bp else None
        v2_ids, basis = match_v2(recs, apn, akey, v2)
        v2p = v2[0].get(v2_ids[0]) if v2_ids else None
        active = any(r["status"] in ACTIVE_BUILDING or (r["module"] == "Planning" and r["status"] not in
                     ("Approved", "Closed", "Withdrawn", "Denied", "Void")) for r in recs)
        stale = any(r["status_asof"] < (dt.date.fromisoformat(today) - dt.timedelta(days=30)).isoformat()
                    for r in recs if r["status"] in ACTIVE_BUILDING or r["module"] == "Planning")
        rows.append(dict(
            project_key="|".join(str(x) for x in gkey), address=addr, apn=apn or "",
            units_best=best["units"], units_source=best["units_source"],
            planning_records=";".join(r["record"] for r in pl),
            planning_status=latest_pl["status"] if latest_pl else "",
            planning_filed=latest_pl["filed"] if latest_pl else "",
            building_records=";".join(r["record"] for r in bp),
            building_status=latest_bp["status"] if latest_bp else "",
            building_filed=latest_bp["filed"] if latest_bp else "",
            first_bp_issued=min((r["issued"] for r in bp if r["issued"]), default=""),
            last_finaled=max((r["finaled"] for r in bp if r["finaled"]), default=""),
            status_asof=min(r["status_asof"] for r in recs),
            v2_project_id=";".join(map(str, v2_ids)), v2_match_basis=basis,
            v2_units=v2p["total_units"] if v2p else "", v2_status=v2p["status_label"] if v2p else "",
            v2_bp_issued=v2p["bp_issued_date"] if v2p else "", v2_co=v2p["co_issued_date"] if v2p else "",
            not_in_v2=int(not v2_ids), needs_status_refresh=int(active and stale),
            units_disagree=int(bool(v2p) and v2p["total_units"] is not None and abs(int(v2p["total_units"]) - best["units"]) > 1),
            n_records=len(recs), address_missing=int(not addr),
            address_borrowed=int(any(r.get("address_borrowed") for r in recs)),
        ))
    rows.sort(key=lambda r: (-r["units_best"], r["address"]))
    return rows, records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-units", type=int, default=2)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()
    rows, records = build(a.min_units, a.date)
    OUT.mkdir(exist_ok=True)
    pf = OUT / f"multiunit_projects_{a.date}.csv"
    rf = OUT / f"multiunit_records_{a.date}.csv"
    with open(pf, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with open(rf, "w", newline="") as f:
        keys = [k for k in records[0].keys() if not k.startswith("_")]
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore"); w.writeheader(); w.writerows(records)

    n = len(rows)
    print(f"\n{pf.name}: {n} projects (>= {a.min_units} units) from {len(records)} records")
    for lo in (5, 10, 50):
        print(f"  >= {lo:>3} units: {sum(1 for r in rows if r['units_best'] >= lo):>4}")
    print(f"  in v2: {sum(1 for r in rows if not r['not_in_v2'])}   NOT in v2: {sum(1 for r in rows if r['not_in_v2'])}"
          f"   (not in v2 & >=5u: {sum(1 for r in rows if r['not_in_v2'] and r['units_best'] >= 5)})")
    print(f"  units_source=cpra: {sum(1 for r in rows if r['units_source']=='cpra_UnitsAdded')}   "
          f"description-screen only: {sum(1 for r in rows if r['units_source']=='description')}")
    print(f"  needs_status_refresh (active, status older than 30d): {sum(1 for r in rows if r['needs_status_refresh'])}")
    print(f"  units_disagree with v2 (>1): {sum(1 for r in rows if r['units_disagree'])}   address_missing: {sum(1 for r in rows if r['address_missing'])}")
    print(f"  planning-only (no building record): {sum(1 for r in rows if r['planning_records'] and not r['building_records'])}")
    print(f"\n{rf.name}: {len(records)} records")


if __name__ == "__main__":
    main()
