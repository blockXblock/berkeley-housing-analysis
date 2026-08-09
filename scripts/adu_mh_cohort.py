#!/usr/bin/env python3
"""adu_mh_cohort.py — derive the ADU + Middle-Housing cohort (geocoded) -> data/processed/adu_mh_cohort.csv.

Two independently-defined groups, the durable home for the 2026-08 investigation:
  ADU  — v4 events that ADD a dwelling AND are ADU-designated (city ADU flag OR description),
         INCLUDING conversion-ADUs via the fixed classifier (housing_rules.permit_role RULE 5.5).
         Validated vs the HCD APR oracle: ~93% recall (857 vs the APR's 842). Geocoded by the
         canonical-APN crosswalk to berkeley.db parcel centroids.
  MH   — Middle Housing = PLN Planning records whose Project Name is 'ZCMH: <address>' (the new
         ordinance, Nov-2025+). 27 distinct records; address from Project Name, geocoded by address.

NOT the block-level truth — geocoding is parcel-centroid precision (the APR's own points are better,
but the APR is the oracle, never a data source). Output feeds gen_adu_middle_housing.py.
"""
import sqlite3, sys, json, glob, re, csv
sys.path.insert(0, "scripts")
from housing_rules import to_canonical_apn
from housing_rules.permit_role import _adu_creation

def canon(a):
    try: return to_canonical_apn(a, "alameda")
    except Exception: return None

def berkeley_apn_latlon():
    bd = sqlite3.connect("databases/berkeley.db"); m = {}
    for a, lat, lon in bd.execute("SELECT APN,Latitude,Longitude FROM parcels WHERE Latitude IS NOT NULL"):
        c = canon(a)
        if c: m[c] = (float(lat), float(lon))
    return m

def adu_cohort(bmap):
    v4 = sqlite3.connect("databases/berkeley_housing_v4.db")
    apns = set()
    for apn, role, desc, payload in v4.execute(
        "SELECT e.raw_apn,c.housing_role,e.raw_description,e.raw_payload "
        "FROM events e JOIN event_classifications c USING(event_id) WHERE e.raw_apn!=''"):
        try: p = json.loads(payload) if payload else {}
        except Exception: p = {}
        flag = str(p.get("ADU", "")).strip().lower() in ("yes", "y", "true", "1")
        d = (desc or "").upper()
        adu_desc = ("ADU" in d or "ACCESSORY DWELLING" in d or "JADU" in d)
        keep = (role == "new_unit" and (flag or adu_desc)) or \
               (role in ("alteration", "ambiguous") and _adu_creation((desc or "").lower()))
        if keep:
            c = canon(apn)
            if c: apns.add(c)
    out = []
    for c in apns:
        if c in bmap: out.append(dict(key=c, lat=bmap[c][0], lon=bmap[c][1], type="ADU", units=1, source="v4"))
    return out

def _mh_units(desc):
    d = (desc or "").lower()
    if "four" in d or "4 " in d or "fourplex" in d or "four dwelling" in d: return 4, "fourplex"
    if "three" in d or "triplex" in d or "3 " in d: return 3, "triplex"
    return 2, "duplex"  # default duplex (2-4 ordinance; conservative)

# ordinal street words -> the assessor's numbered form (Berkeley: "8TH ST", not "EIGHTH STREET")
ORDINALS = {"FIRST":"1ST","SECOND":"2ND","THIRD":"3RD","FOURTH":"4TH","FIFTH":"5TH","SIXTH":"6TH",
            "SEVENTH":"7TH","EIGHTH":"8TH","NINTH":"9TH","TENTH":"10TH","ELEVENTH":"11TH","TWELFTH":"12TH"}
_ST_TYPES = "STREET|ST|AVENUE|AVE|WAY|DRIVE|DR|BOULEVARD|BLVD|ROAD|RD|COURT|CT|PLACE|PL|LANE|LN|TERRACE|CIRCLE|CIR"

_MH_STOP = {"MIDDLE","HOUSING","PREAPP","ZCMH","APPLICATION","PROJECT","MAJOR","RESIDENTIAL","NEW","FOR","THE","AND"}

def _geocode_mh(proj, bd):
    """Find a house number + street ANYWHERE in the project-name text (handles 'ZCMH:'/'PREAPP -'
    prefixes, ranges like 1312-1314 by trying both endpoints, ordinal streets, and addresses with no
    street-type word), then match berkeley.db situs."""
    text = proj.upper()
    m = re.search(rf"(\d{{2,5}})(?:-(\d+))?\s+([A-Z0-9][A-Z0-9 .]*?)\s*(?:{_ST_TYPES})\b", text)
    if not m:  # fallback: number + a plain word, no street-type present
        m = re.search(r"(\d{2,5})(?:-(\d+))?\s+([A-Z][A-Za-z]{2,})", text)
        if not m or m.group(3) in _MH_STOP: return None, None
    n1, n2, name = m.group(1), m.group(2), m.group(3).strip()
    nums = [n1] + ([n2] if n2 else [])
    first = ORDINALS.get(name.split()[0], name.split()[0]) if name else ""
    for n in nums:
        row = bd.execute("SELECT Latitude,Longitude FROM parcels WHERE SitusAddre LIKE ? AND SitusAddre LIKE ? "
                         "AND Latitude IS NOT NULL LIMIT 1", (f"{n} %", f"%{first}%")).fetchone()
        if row: return (float(row[0]), float(row[1])), f"{n} {name}".title()
    return None, f"{n1} {name}".title()

def mh_cohort(bmap):
    seen = {}
    for f in glob.glob("data/raw/accela/date_range*/Planning_*.jsonl"):
        for line in open(f):
            try: d = json.loads(line)
            except Exception: continue
            if "MIDDLE HOUSING" not in str(d.get("Description", "")).upper(): continue
            rn = d.get("Record Number", "")
            if rn and rn not in seen: seen[rn] = d
    bd = sqlite3.connect("databases/berkeley.db")
    out, missed = [], []
    for rn, d in seen.items():
        proj = str(d.get("Project Name", ""))
        latlon, addr = _geocode_mh(proj, bd)
        units, typ = _mh_units(d.get("Description"))
        if latlon:
            out.append(dict(key=rn, lat=latlon[0], lon=latlon[1], type=typ, units=units,
                            source="MH", addr=addr or proj, status=d.get("Status", "")))
        else:
            missed.append(proj)
    if missed:
        print(f"  MH ungeocoded ({len(missed)}): " + "; ".join(missed[:6]))
    return out

def main():
    bmap = berkeley_apn_latlon()
    adu = adu_cohort(bmap); mh = mh_cohort(bmap)
    rows = adu + mh
    with open("data/processed/adu_mh_cohort.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["key","lat","lon","type","units","source","addr","status"])
        w.writeheader()
        for r in rows: w.writerow(r)
    print(f"ADU: {len(adu)} geocoded | Middle Housing: {len(mh)} geocoded  -> data/processed/adu_mh_cohort.csv")

if __name__ == "__main__":
    main()
