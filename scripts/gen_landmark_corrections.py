#!/usr/bin/env python3
"""gen_landmark_corrections.py — primary-source build-date correction layer from the City Landmarks list.

The assessor's `YearBuilt` is unreliable for the historic stock (validated: it mis-dates or lacks a date for
~70% of designated landmarks — the Westenberg House at 2811 Benvenue reads 1925, but the landmarked/documented
date is 1903). The City's "List of Designated Landmarks, Structures of Merit & Historic Districts" carries the
true **Date of Construction** for ~300 of Berkeley's oldest, best-documented buildings. This parses that PDF and
matches it to parcels, producing a correction layer to OVERRIDE `YearBuilt` where a landmark record exists.

Source PDF: data/raw/berkeley_landmarks_list.pdf (City of Berkeley; re-download from berkeleyca.gov to refresh).
Output: data/reference/berkeley_landmark_build_dates.csv (apn, address, name_year, assessor_year, designated,
lm_type, matched). Calibrated on 2811 Benvenue -> 1903.

Usage: python scripts/gen_landmark_corrections.py   (needs pdftotext on PATH)
"""
import re, csv, subprocess, sys, warnings, pathlib
import pandas as pd, sqlite3, geopandas as gpd
warnings.filterwarnings("ignore"); sys.path.insert(0, "scripts")
from housing_rules import to_canonical_apn

PDF = "data/raw/berkeley_landmarks_list.pdf"   # gitignored (*.pdf); auto-downloaded if absent
PDF_URL = "https://berkeleyca.gov/sites/default/files/documents/COB%20Landmarks%20Updated%20Jan%202023_0.pdf"
OUT = "data/reference/berkeley_landmark_build_dates.csv"

def _ensure_pdf():
    if not pathlib.Path(PDF).exists():
        import urllib.request
        pathlib.Path(PDF).parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(PDF_URL, PDF)
_ST = r"\b(AVE|AVENUE|ST|STREET|WAY|BLVD|RD|DR|PL|CT|LN|TER|CIR|PLACE|COURT|ROAD)\b.*$"

def _key(num, street):
    st = re.sub(r"[^A-Z0-9 ]", "", re.sub(_ST, "", str(street).upper()).strip()).split()
    return f"{num} {st[0]}" if st else None

def parse_landmarks():
    _ensure_pdf()
    txt = subprocess.run(["pdftotext", "-layout", PDF, "-"], capture_output=True, text=True).stdout
    rec = re.compile(r"^\s*(\d{2,5})\s"); date = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b")
    typ = re.compile(r"\b(LM|SM|SOM|HD)\b")
    rows, buf = [], []
    for ln in txt.splitlines():
        stcol = ln[10:24].strip()
        if rec.match(ln) and date.search(ln) and typ.search(ln):
            m = rec.match(ln); d = date.search(ln)
            # construction year = a 4-digit 1700-2026 AFTER the address number and BEFORE the designation date
            cands = [int(x.group()) for x in re.finditer(r"\b\d{4}\b", ln)
                     if x.start() >= m.end() and x.start() < d.start() and 1700 <= int(x.group()) <= 2026]
            rows.append(dict(number=m.group(1), street=" ".join([w for w in buf if w] + [stcol]).strip(),
                             year_built=(cands[0] if cands else None), designated=d.group(1), type=typ.search(ln).group(1)))
            buf = []
        else:
            if stcol and not any(k in stcol for k in ("Street", "Address", "Construction", "Page", "HIGHLIGHTED")):
                buf.append(stcol)
            if not ln.strip(): buf = []
    return pd.DataFrame(rows)

def main():
    lm = parse_landmarks()
    lm["key"] = lm.apply(lambda r: _key(r.number, r.street), axis=1)
    bd = sqlite3.connect("databases/berkeley.db")
    par = pd.read_sql("SELECT APN,SitusAddre FROM parcels WHERE SitusAddre IS NOT NULL", bd)
    def pkey(a):
        m = re.match(r"\s*(\d+)\s+(.*)", str(a).upper())
        if not m: return None
        st = re.sub(_ST, "", m.group(2)).strip().split()
        return f"{m.group(1)} {st[0]}" if st else None
    par["key"] = par.SitusAddre.map(pkey)
    par["capn"] = par.APN.apply(lambda a: to_canonical_apn(a, "alameda") if a else None)
    pmap = par.dropna(subset=["key"]).drop_duplicates("key").set_index("key")
    tp = gpd.read_file("data/raw/berkeley_taxparcels_2026-08-12.geojson")[["APN", "YearBuilt"]]
    tp["capn"] = tp.APN.apply(lambda a: to_canonical_apn(a, "alameda") if a else None)
    tp["YearBuilt"] = pd.to_numeric(tp.YearBuilt, errors="coerce")
    yb = tp.dropna(subset=["capn"]).drop_duplicates("capn").set_index("capn").YearBuilt
    out = []
    for _, r in lm.iterrows():
        capn = pmap.loc[r.key].capn if (r.key in pmap.index) else None
        a_yr = yb.get(capn) if capn else None
        out.append(dict(apn=capn, address=f"{r.number} {r.street}", name_year=r.year_built,
                        assessor_year=(int(a_yr) if pd.notna(a_yr) else None),
                        designated=r.designated, lm_type=r.type, matched=capn is not None))
    C = pd.DataFrame(out); C.to_csv(OUT, index=False)
    m = C[C.matched & C.name_year.notna() & C.assessor_year.notna()].copy(); m["diff"] = (m.name_year - m.assessor_year).abs()
    print(f"landmarks={len(C)} matched={int(C.matched.sum())} both-dates={len(m)} "
          f"assessor-misdated(>2y)={int((m['diff']>2).sum())} ({100*(m['diff']>2).mean():.0f}%) median_err={m['diff'].median():.0f}y")
    print("wrote", OUT)

if __name__ == "__main__":
    main()
