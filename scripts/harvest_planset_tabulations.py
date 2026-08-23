#!/usr/bin/env python3
"""harvest_planset_tabulations.py — footprint + HEIGHT from architect plan-set zoning sheets, via OCR.

WHY OCR AND NOT pdftotext
-------------------------
The City of Berkeley "Zoning Tabulations" table on an architect's zoning-data sheet (typically A0.1 /
"ZONING CODE DATA") is drawn as VECTOR PATHS or pasted as a RASTER IMAGE, not as a text layer. Verified on
2920 Shattuck (proj8, page 2): 47,650 vector drawings, 7 images, and the strings "ZONING TABULATIONS",
"BUILDING FOOTPRINT", "LOT COVERAGE" and every value in the table are ABSENT from `page.get_text()`.
Both `pdftotext -layout` and PyMuPDF word extraction therefore return nothing for it. See
`docs/audit/2026-08-22_building_footprint_vs_parcel_findings.md`.

This matters because the sibling harvester (`harvest_tabulation_footprints.py`) only finds the 9 documents
whose TITLE matches '%Tabulation%'. The same numbers sit inside 121 plan sets covering 33 projects.

WHAT IT RECOVERS (both defects in one pass)
-------------------------------------------
  BUILDING FOOTPRINT + LOT AREA + LOT COVERAGE  -> the base polygon should be the BUILDING, not the lot
  BUILDING HEIGHT + BUILDING STORIES            -> replaces the `height_stories=3.0` migration placeholder

The table's columns are [existing/base, allowable-w/-UPs, PROPOSED]. We take the PROPOSED value — the
building that will exist — which is precisely what City taxable sqft could not give us (it describes the
building being demolished).

READ-ONLY. Writes only data/reference/planset_tabulations.csv. No DB or KML writes.
Usage:  python scripts/harvest_planset_tabulations.py [--projects 8,9,10] [--limit N] [--scan-pages N]
"""
import argparse, csv, math, os, re, sqlite3, subprocess, sys

PARCELS = "data/raw/berkeley_taxparcels_2026-08-12.geojson"
CELL = 0.002

SCRATCH = "scratch/2026-08-22/plansets"
OUT     = "data/reference/planset_tabulations.csv"
# markers that identify the zoning-data sheet
MARKERS = re.compile(r"ZONING TABULATION|BUILDING FOOTPRINT|LOT COVERAGE|ZONING CODE DATA", re.I)

# label -> canonical field.  Order matters: longer/more specific first.
FIELDS = [
    ("footprint_sf",   r"BUILDING\s*FOOTPRINT"),
    ("lot_area_sf",    r"LOT\s*AREA(?!\s*\(ACRES)"),
    ("lot_coverage_pct", r"LOT\s*COVERAGE"),
    ("height_ft",      r"BUILDING\s*HEIGHT"),
    ("stories",        r"BUILDING\s*STORIES"),
    ("gross_floor_sf", r"GROSS\s*FLOOR\s*AREA"),
    ("dwelling_units", r"NUMBER\s*OF\s*DWELLING\s*UNITS"),
]
# a value token: 12,345 | 45% | 125'-2" | 11
NUM = re.compile(r"(\d{1,3}(?:,\d{3})+|\d{1,3}\s*%|\d+\s*'\s*-?\s*\d*\s*\"?|\d{1,6}(?:\.\d+)?)")
# text that terminates the data columns (compliance column)
# NOTE: "N/A" is a legitimate CELL VALUE (an allowed-column entry), NOT a row terminator.
# Treating it as one truncated 3030 Telegraph's 4-column row at the N/A and returned the
# EXISTING footprint (27,024 sf) instead of the PROPOSED (19,811 sf) -- the same
# demolished-building error, arriving from a new direction. Only compliance-column text
# terminates a row.
TAIL = re.compile(r"COMPLIES|WAIVER|CONCESSION|SEE\s*TABLE", re.I)
# Code/table citations carry digits that leak into the value tokens. Matching only
# "BMC 23.204..." missed "TABLE 23.204-8", which is how 3030 Telegraph's storey row
# ("3  4*  TABLE 23.204-8  4  9") yielded 9 storeys for a building the same sheet
# describes four times as 5-STORY (and GFA/footprint = 94,664/19,811 = 4.8 confirms 5).
CODEREF = re.compile(r"(?:BMC|TABLE|SECTION|SEC\.|CHAPTER|PER)\s*[\d]+[\d.\-A-Z]*", re.I)


def ocr(png, psm=6):
    r = subprocess.run(["tesseract", png, "-", "--psm", str(psm)],
                       capture_output=True, text=True)
    return r.stdout


def to_number(tok):
    """'10,232'->10232 ; '52%'->52 ; "125'-2\"" -> 125.17 ; '11'->11"""
    t = tok.strip()
    if "%" in t:
        return float(re.sub(r"[^\d.]", "", t))
    m = re.match(r"(\d+)\s*'\s*-?\s*(\d+)?", t)
    if m and "'" in t:
        return round(int(m.group(1)) + (int(m.group(2) or 0) / 12.0), 2)
    t = t.replace(",", "").strip()
    try:
        return float(t)
    except ValueError:
        return None


def parse_row(line):
    """Return the PROPOSED value: the last value token before the compliance tail,
    ignoring BMC code references (which contain digits)."""
    body = TAIL.split(line)[0]
    body = CODEREF.sub(" ", body)
    toks = [t for t in NUM.findall(body)]
    if not toks:
        return None, None
    # strip a leading label-embedded number (rare) by preferring the LAST token
    val = to_number(toks[-1])
    return val, toks[-1]



# ---------------------------------------------------------------------------
# TEXT-FIRST EXTRACTION  (added 2026-08-23)
#
# "The zoning table is vector/raster, so OCR is required" is TRACHTENBERG-SPECIFIC,
# not universal. 2920 Shattuck p2 genuinely has 0 matching strings among 47,650 vector
# paths -- but 2036 Bancroft's sheet returned 1,116 words from get_text(), including
# every label, with NO OCR at all. Only the label->value join needed spatial work,
# because labels and values sit in separate text blocks on the same visual row.
#
# So: try text, fall back to OCR. OCR is ~1-2 min/project; this is milliseconds.
# ---------------------------------------------------------------------------
LABEL_RX = re.compile(
    r"LOT\s*AREA|LOT\s*COVERAGE|BUILDING\s*FOOTPRINT|MAX\s*BLDG\.?\s*HEIGHT|"
    r"BUILDING\s*HEIGHT|#\s*STORIES|BUILDING\s*STORIES|GROSS\s*FLOOR\s*AREA", re.I)



def _field_of(label):
    k = label.upper()
    return ("footprint_sf" if "FOOTPRINT" in k else
            "lot_coverage_pct" if "COVERAGE" in k else
            "lot_area_sf" if ("LOT" in k and "AREA" in k) else
            "gross_floor_sf" if "GROSS" in k else
            "stories" if "STORIES" in k else "height_ft")


def text_rows(pdf, page):
    """Rebuild visual rows from the text layer: [(text, x0, y0, x1, y1)]."""
    import fitz
    doc = fitz.open(pdf)
    try:
        pg = doc[page]
        buckets = {}
        for x0, y0, x1, y1, word, b, l, n in pg.get_text("words"):
            buckets.setdefault((b, l), []).append((x0, y0, x1, y1, word))
    finally:
        doc.close()
    out = []
    for v in buckets.values():
        v.sort(key=lambda t: t[0])
        out.append((" ".join(t[4] for t in v), min(t[0] for t in v), min(t[1] for t in v),
                    max(t[2] for t in v), max(t[3] for t in v)))
    return out


def extract_text_first(pdf, page):
    """Label->value by SPATIAL ROW MATCH. Returns {field: [values left-to-right]}.

    Values are kept as an ORDERED LIST because the columns are
    EXISTING | ALLOWED | PROPOSED -- the caller must pick PROPOSED (the last), never
    the first. Taking the first returns the building being DEMOLISHED.
    """
    rows = text_rows(pdf, page)
    if not rows:
        return {}
    found = {}
    for txt, x0, y0, x1, y1 in rows:
        m = LABEL_RX.search(txt)
        if not m:
            continue
        cy = (y0 + y1) / 2
        vals = []
        for t2, a0, b0, a1, b1 in rows:
            if a0 <= x1 - 2:                       # must be to the RIGHT of the label
                continue
            if abs((b0 + b1) / 2 - cy) > 6:        # same visual row
                continue
            if LABEL_RX.search(t2):
                continue
            for tok in NUM.findall(t2):
                v = to_number(tok)
                if v is None:
                    continue
                # reject out-of-range tokens: BMC code refs (23.204), dimension strings and
                # stray drawing numerals otherwise pollute the height/storey rows.
                lo, hi = BOUNDS.get(_field_of(m.group(0)), (None, None))
                if lo is not None and not (lo <= v <= hi):
                    continue
                vals.append((a0, v))
        if not vals:
            continue
        vals.sort()
        field = _field_of(m.group(0))
        found.setdefault(field, []).append([v for _, v in vals])
    return found



def storeys_from_gfa(gross_floor_sf, footprint_sf):
    """GROSS FLOOR AREA / FOOTPRINT ~= STOREYS.

    A free third validator: no external data, no parcel join, no tabulation cross-check.
    It independently caught BOTH of the errors John found on 2026-08-23:
      3030 Telegraph  94,664 / 19,811 = 4.8  -> 5 storeys (parser had said 9)
      2036 Bancroft   80,343 / 11,610 = 6.9  -> ~8 storeys, the NEW tower on APN -16
                      98,865 / 24,535 = 4.0  -> exactly the RETAINED building's stated 4
    Use it to sanity-check any storey reading, and to catch the case where a multi-parcel
    project has one NEW building and one RETAINED ("NO CHANGE") building whose footprints
    must NOT be summed.
    """
    if not gross_floor_sf or not footprint_sf:
        return None
    return gross_floor_sf / footprint_sf


def storeys_agree(stated, gross_floor_sf, footprint_sf, tol=1.5):
    """True/False/None — does a stated storey count survive the GFA/footprint check?"""
    implied = storeys_from_gfa(gross_floor_sf, footprint_sf)
    if implied is None or not stated:
        return None
    return abs(stated - implied) <= tol

def conservation_ok(existing, proposed, tol=0.005):
    """A LOT LINE ADJUSTMENT moves lot area between parcels -- it cannot create it.
    Sum(existing lots) == Sum(proposed lots) therefore PROVES the column order, for free,
    on any multi-parcel project. Verified on 2036 Bancroft: 6,595+37,696 == 14,582+29,709
    == 44,291 sf. Where it does not apply, fall back to: derived footprint/lot must
    reproduce the sheet's own stated coverage %."""
    if not existing or not proposed:
        return None
    a, b = sum(existing), sum(proposed)
    return abs(a - b) <= tol * max(a, b)


def find_sheet(pdf, scan_pages, dpi_scan=150):
    """Page index (0-based) of the zoning-data sheet, or None."""
    import fitz
    doc = fitz.open(pdf)
    try:
        for i in range(min(len(doc), scan_pages)):
            png = f"{SCRATCH}/_scan.png"
            doc[i].get_pixmap(dpi=dpi_scan).save(png)
            if MARKERS.search(ocr(png)):
                return i
    finally:
        doc.close()
    return None


def read_sheet_cached(pdf, page, pid, dpi=400):
    """OCR is the expensive step and its output never changes for a fixed (pdf, page).
    Cache it so validation logic can be re-run in seconds instead of an hour."""
    cache = f"{SCRATCH}/ocr_proj{pid}_p{page}.txt"
    if os.path.exists(cache) and os.path.getsize(cache) > 200:
        return open(cache, errors="ignore").read()
    txt = read_sheet(pdf, page, dpi)
    with open(cache, "w") as fh:
        fh.write(txt)
    return txt


def read_sheet(pdf, page, dpi=400):
    """OCR the sheet in vertical strips (a full E-size sheet at 400dpi is too wide for one pass)."""
    import fitz
    doc = fitz.open(pdf)
    pg = doc[page]; r = pg.rect
    text = []
    # generous, heavily-overlapping strips: a Berkeley zoning table spans ~0.33 of sheet width,
    # so every strip here is wide enough to contain one whole, and the overlap guarantees
    # at least one strip does not cut through it.
    for lo, hi in [(0.00, 0.45), (0.25, 0.70), (0.45, 0.92), (0.55, 1.00), (0.30, 0.95)]:
        clip = fitz.Rect(r.x0 + r.width * lo, r.y0, r.x0 + r.width * hi, r.y1)
        png = f"{SCRATCH}/_strip.png"
        pg.get_pixmap(dpi=dpi, clip=clip).save(png)
        text.append(ocr(png))
    doc.close()
    return "\n".join(text)


# plausibility bounds — a value outside these is an OCR artifact, not a reading
BOUNDS = {
    "footprint_sf":      (200, 400_000),
    "lot_area_sf":       (500, 900_000),
    "lot_coverage_pct":  (15, 100),   # <15% on an urban infill site is noise, not a reading
    "height_ft":         (8, 900),
    "stories":           (1, 60),
    "gross_floor_sf":    (500, 3_000_000),
    "dwelling_units":    (1, 2000),
}


def score_line(line):
    """How COMPLETE is this OCR'd row?

    Strips overlap, so the same row is read several times — and a strip whose right edge
    cuts through the table yields the label plus the EXISTING column only, with the
    PROPOSED column truncated away. Taking the first match would silently return the
    existing building (this is exactly how 2920 Shattuck first returned 13,648/45%/36'/3
    instead of 10,232/52%/125'-2"/11). Prefer the most complete reading of the row:
      + the compliance tail proves the row was captured to its right edge
      + more value tokens means more columns survived
    """
    s = 0
    if TAIL.search(line):
        s += 100                       # row reached the compliance column -> not truncated
    body = CODEREF.sub(" ", TAIL.split(line)[0])
    s += 10 * len(NUM.findall(body))   # more columns captured
    return s


def extract(text):
    """Collect EVERY reading of each field across all strips, then keep the most complete."""
    cands = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        for field, pat in FIELDS:
            if re.search(pat, line, re.I):
                val, raw = parse_row(line)
                if val is None:
                    continue
                lo, hi = BOUNDS.get(field, (None, None))
                if lo is not None and not (lo <= val <= hi):
                    continue           # out-of-range -> OCR artifact
                cands.setdefault(field, []).append((score_line(line), val, line.strip()[:110]))
    out, evidence, low = {}, {}, []
    for field, lst in cands.items():
        lst.sort(key=lambda t: -t[0])
        score, val, line = lst[0]
        out[field] = val
        evidence[field] = line
        vals = {round(v, 2) for _, v, _ in lst}
        if len(vals) > 1:
            evidence[field] += f"   [{len(vals)} readings: {sorted(vals)}]"
        # score >= 100 means the row reached its compliance column, so the PROPOSED
        # column was captured. Below that we only ever saw a truncated row -> the value
        # is probably the EXISTING building. Flag it; never present it as a clean reading.
        if score < 100:
            low.append(field)
            evidence[field] += "   [LOW-CONFIDENCE: truncated row, may be the EXISTING column]"
    return out, evidence, sorted(low)


def parcel_index():
    """Berkeley county tax parcels, bucketed for point-in-polygon lookup."""
    import collections, json
    gj = json.load(open(PARCELS))
    idx = collections.defaultdict(list)
    for f in gj["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else (
                 g["coordinates"] if g["type"] == "MultiPolygon" else [])
        for poly in polys:
            r = poly[0]
            xs = [q[0] for q in r]; ys = [q[1] for q in r]
            for cx in range(int(min(xs)/CELL), int(max(xs)/CELL)+1):
                for cy in range(int(min(ys)/CELL), int(max(ys)/CELL)+1):
                    idx[(cx, cy)].append((f, r))
    return idx


def ring_area_sf(r):
    lat0 = sum(q[1] for q in r)/len(r); R = 6371000.0
    pts = [(math.radians(q[0])*R*math.cos(math.radians(lat0)), math.radians(q[1])*R) for q in r]
    a = sum(pts[i][0]*pts[(i+1) % len(pts)][1] - pts[(i+1) % len(pts)][0]*pts[i][1]
            for i in range(len(pts)))
    return abs(a)/2*10.7639


def point_in(pt, r):
    x, y = pt; c = False; j = len(r)-1
    for i in range(len(r)):
        xi, yi = r[i][:2]; xj, yj = r[j][:2]
        if ((yi > y) != (yj > y)) and (x < (xj-xi)*(y-yi)/((yj-yi) or 1e-12)+xi):
            c = not c
        j = i
    return c


def parcel_for(idx, lon, lat):
    """(APN, parcel_area_sf) for the parcel containing the project's coordinate."""
    if lon is None or lat is None:
        return None, None
    for f, r in idx.get((int(lon/CELL), int(lat/CELL)), []):
        if point_in((lon, lat), r):
            return f["properties"].get("APN"), ring_area_sf(r)
    return None, None


def verdict(rec):
    """TWO INDEPENDENT checks. The LOW-CONFIDENCE flag only proves a row was captured
    completely -- it says nothing about whether the VALUES are right. 2680 Bancroft
    came back unflagged with a lot area 39% off the county parcel, and 2274 Shattuck
    unflagged with a physically impossible 1.1% lot coverage. So:
      (a) EXTERNAL -- OCR'd lot area vs the county parcel polygon (independent source)
      (b) INTERNAL -- derived footprint/lot vs the separately-OCR'd lot coverage
    """
    fp, lot, cov, par = (rec.get("footprint_sf"), rec.get("lot_area_sf"),
                         rec.get("lot_coverage_pct"), rec.get("parcel_sf"))
    checks, notes = [], []
    if lot and par:
        ratio = lot/par
        rec["lot_vs_parcel"] = round(ratio, 3)
        ok = 0.90 <= ratio <= 1.10
        checks.append(ok)
        notes.append(f"lot/parcel={ratio:.2f}{'' if ok else ' MISMATCH'}")
    if fp and lot:
        der = fp/lot*100
        rec["derived_coverage_pct"] = round(der, 1)
        if cov:
            ok = abs(der-cov) <= 10
            checks.append(ok)
            notes.append(f"derived_cov={der:.0f}% vs stated {cov:.0f}%{'' if ok else ' MISMATCH'}")
    # a footprint bigger than its own lot is impossible
    if fp and par and fp > par*1.10:
        checks.append(False); notes.append("footprint EXCEEDS parcel")
    if not checks:
        rec["verdict"] = "UNVERIFIED"
    elif all(checks):
        rec["verdict"] = "PASS" if not rec.get("low_confidence") else "PASS(flagged fields)"
    else:
        rec["verdict"] = "SUSPECT"
    rec["checks"] = "; ".join(notes)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", help="comma-separated project_ids (default: all with a plan set)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--scan-pages", type=int, default=10)
    a = ap.parse_args()

    os.makedirs(SCRATCH, exist_ok=True)
    pidx = parcel_index()
    v2 = sqlite3.connect("databases/berkeley_housing_v2.db"); v2.row_factory = sqlite3.Row
    q = """select d.project_id, d.title, d.page_count, d.file_size_bytes, d.r2_url,
                  v.address_display, v.status_label, v.total_units, v.height_stories,
                  v.latitude, v.longitude
           from documents d
           left join vocabulary_document_types vdt on vdt.id = d.document_type_id
           left join v_projects_flat v on v.project_id = d.project_id
           where d.r2_url is not null and vdt.code = 'plan_set'"""
    rows = [dict(r) for r in v2.execute(q)]
    # one plan set per project: the SMALLEST (fastest, and usually the focused zoning set)
    best = {}
    for r in rows:
        k = r["project_id"]
        if k not in best or (r["file_size_bytes"] or 9e18) < (best[k]["file_size_bytes"] or 9e18):
            best[k] = r
    todo = sorted(best.values(), key=lambda r: r["project_id"])
    if a.projects:
        keep = {int(x) for x in a.projects.split(",")}
        todo = [r for r in todo if r["project_id"] in keep]
    if a.limit:
        todo = todo[:a.limit]

    results = []
    for r in todo:
        pid = r["project_id"]
        pdf = f"{SCRATCH}/proj{pid}.pdf"
        if not (os.path.exists(pdf) and os.path.getsize(pdf) > 1e6):
            print(f"proj{pid}: fetching {(r['file_size_bytes'] or 0)/1e6:.0f}MB", flush=True)
            subprocess.run(["curl", "-sS", "--max-time", "900", "-o", pdf, r["r2_url"]])
        if not os.path.exists(pdf):
            print(f"proj{pid}: DOWNLOAD FAILED", flush=True); continue
        pg = find_sheet(pdf, a.scan_pages)
        if pg is None:
            print(f"proj{pid}: no zoning sheet found in first {a.scan_pages} pages", flush=True)
            results.append(dict(project_id=pid, address=r["address_display"], status=r["status_label"],
                                units=r["total_units"], sheet_page=None, note="zoning sheet not located"))
            continue
        vals, ev, low = extract(read_sheet_cached(pdf, pg, pid))
        ev_txt = " || ".join(f"{k}: {v}" for k, v in sorted(ev.items()))
        rec = dict(project_id=pid, address=r["address_display"], status=r["status_label"],
                   units=r["total_units"], db_stories=r["height_stories"], sheet_page=pg + 1,
                   note="", low_confidence=",".join(low), doc_title=r["title"], evidence=ev_txt, **{f: vals.get(f) for f, _ in FIELDS})
        apn, par = parcel_for(pidx, r["longitude"], r["latitude"])
        rec["apn"], rec["parcel_sf"] = apn, (round(par) if par else None)
        verdict(rec)
        results.append(rec)
        print(f"proj{pid:<5} p{pg+1:<3} {str(r['address_display'])[:26]:28} "
              f"fp={rec.get('footprint_sf')} cov={rec.get('lot_coverage_pct')} "
              f"lot={rec.get('lot_area_sf')} ht={rec.get('height_ft')} st={rec.get('stories')}"
              + f"  [{rec.get('verdict')}]"
              + (f" {rec.get('checks')}" if rec.get("checks") else "")
              + (f"  LOW:{','.join(low)}" if low else ""), flush=True)

    cols = ["project_id", "address", "status", "units", "db_stories", "sheet_page"] + \
           [f for f, _ in FIELDS] + ["apn", "parcel_sf", "lot_vs_parcel", "derived_coverage_pct",
            "verdict", "checks", "low_confidence", "note", "doc_title", "evidence"]
    os.makedirs("data/reference", exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for rec in results:
            w.writerow(rec)
    print(f"\nwrote {OUT}  ({len(results)} projects)")


if __name__ == "__main__":
    main()
