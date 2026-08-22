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
import argparse, csv, os, re, sqlite3, subprocess, sys

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
TAIL = re.compile(r"COMPLIES|WAIVER|CONCESSION|SEE\s*TABLE|N\s*/?\s*A", re.I)
CODEREF = re.compile(r"BMC\s*[\d.]+[A-Z.\d]*", re.I)


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
    "lot_coverage_pct":  (1, 100),
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", help="comma-separated project_ids (default: all with a plan set)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--scan-pages", type=int, default=10)
    a = ap.parse_args()

    os.makedirs(SCRATCH, exist_ok=True)
    v2 = sqlite3.connect("databases/berkeley_housing_v2.db"); v2.row_factory = sqlite3.Row
    q = """select d.project_id, d.title, d.page_count, d.file_size_bytes, d.r2_url,
                  v.address_display, v.status_label, v.total_units, v.height_stories
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
        vals, ev, low = extract(read_sheet(pdf, pg))
        ev_txt = " || ".join(f"{k}: {v}" for k, v in sorted(ev.items()))
        rec = dict(project_id=pid, address=r["address_display"], status=r["status_label"],
                   units=r["total_units"], db_stories=r["height_stories"], sheet_page=pg + 1,
                   note="", low_confidence=",".join(low), doc_title=r["title"], evidence=ev_txt, **{f: vals.get(f) for f, _ in FIELDS})
        # internal consistency: footprint ≈ lot_area × coverage
        if rec.get("lot_area_sf") and rec.get("lot_coverage_pct") and rec.get("footprint_sf"):
            implied = rec["lot_area_sf"] * rec["lot_coverage_pct"] / 100.0
            rec["coverage_check"] = round(rec["footprint_sf"] / implied, 3) if implied else None
        results.append(rec)
        print(f"proj{pid:<5} p{pg+1:<3} {str(r['address_display'])[:26]:28} "
              f"fp={rec.get('footprint_sf')} cov={rec.get('lot_coverage_pct')} "
              f"lot={rec.get('lot_area_sf')} ht={rec.get('height_ft')} st={rec.get('stories')}"
              + (f"  LOW:{','.join(low)}" if low else ""), flush=True)

    cols = ["project_id", "address", "status", "units", "db_stories", "sheet_page"] + \
           [f for f, _ in FIELDS] + ["coverage_check", "low_confidence", "note", "doc_title", "evidence"]
    os.makedirs("data/reference", exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for rec in results:
            w.writerow(rec)
    print(f"\nwrote {OUT}  ({len(results)} projects)")


if __name__ == "__main__":
    main()
