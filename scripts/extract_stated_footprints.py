#!/usr/bin/env python3
"""extract_stated_footprints.py — architect-STATED building footprints for the tour geometry.

Reads plan sets already held on R2 (documents.r2_url, type plan_set), locates the zoning-data
sheet, and pulls the "CITY OF BERKELEY ZONING TABULATIONS" table.

WHY THIS SOURCE AND NO OTHER: only the architect's tabulation describes the building that WILL
EXIST. City taxable sqft (9a47-nj4i), Overture/aerial footprints, and existing-condition site
plans all return the building being DEMOLISHED for a pipeline project -- verified three-for-three
on 2026-08-23, each failing plausibly rather than obviously.

EXTRACTION: text-first (milliseconds), OCR only as fallback (1-2 min/project). "Plan-set tables
are raster" is architect-specific -- 2036 Bancroft's sheet returned 1,116 words from get_text();
2920 Shattuck's has 47,650 vector paths and zero matching strings.

COLUMN ORDER IS THE HAZARD: the table runs EXISTING | ALLOWED | PROPOSED (sometimes 4 columns).
Taking the wrong column returns the demolished building -- plausible, and wrong. Three separate
mechanisms produced exactly that error in one session. Hence three independent validators:
   parcel   : implied lot (footprint/coverage) vs the county parcel polygon
   coverage : derived footprint/lot vs the sheet's own stated coverage %
   storeys  : gross floor area / footprint ~= stated storeys
A reading that fails them is reported SUSPECT, never silently used.

VERSION DRIFT: a project has several plan-set vintages. We take the LATEST by title date; a
figure from an older set can legitimately disagree.

READ-ONLY. Writes only data/reference/stated_footprints.csv. No DB, KML or R2 writes.
Usage: python scripts/extract_stated_footprints.py [--only 1,133] [--limit N]
"""
import argparse, csv, importlib.util, json, math, os, re, sqlite3, subprocess, sys, collections

H = importlib.util.spec_from_file_location("h", "scripts/harvest_planset_tabulations.py")
h = importlib.util.module_from_spec(H); H.loader.exec_module(h)
import fitz

CACHE = "scratch/2026-08-23/extract25"; os.makedirs(CACHE, exist_ok=True)
h.SCRATCH = CACHE
OUT = "data/reference/stated_footprints.csv"
PARCELS = "data/raw/berkeley_taxparcels_2026-08-12.geojson"
CELL = 0.002
# regional/city planning PDFs get mis-typed as plan_set because their titles contain "Plan"
JUNK = re.compile(r"rhna|hazard mitigation|groundwater|wsmp|sustainability plan|allocation plan", re.I)
DATE = re.compile(r"(20\d{2})[-_.]?(\d{2})?[-_.]?(\d{2})?")


def parcel_index():
    gj = json.load(open(PARCELS)); idx = collections.defaultdict(list)
    for f in gj["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else (
                 g["coordinates"] if g["type"] == "MultiPolygon" else [])
        for poly in polys:
            r = poly[0]; xs = [q[0] for q in r]; ys = [q[1] for q in r]
            for cx in range(int(min(xs)/CELL), int(max(xs)/CELL)+1):
                for cy in range(int(min(ys)/CELL), int(max(ys)/CELL)+1):
                    idx[(cx, cy)].append((f, r))
    return idx


def ring_area_sf(r):
    lat0 = sum(q[1] for q in r)/len(r); R = 6371000.0
    p = [(math.radians(q[0])*R*math.cos(math.radians(lat0)), math.radians(q[1])*R) for q in r]
    return abs(sum(p[i][0]*p[(i+1) % len(p)][1] - p[(i+1) % len(p)][0]*p[i][1]
                   for i in range(len(p))))/2*10.7639


def point_in(pt, r):
    x, y = pt; c = False; j = len(r)-1
    for i in range(len(r)):
        xi, yi = r[i][:2]; xj, yj = r[j][:2]
        if ((yi > y) != (yj > y)) and (x < (xj-xi)*(y-yi)/((yj-yi) or 1e-12)+xi):
            c = not c
        j = i
    return c


def parcel_for(idx, lon, lat):
    if lon is None or lat is None:
        return None, None
    for f, r in idx.get((int(lon/CELL), int(lat/CELL)), []):
        if point_in((lon, lat), r):
            return f["properties"].get("APN"), ring_area_sf(r)
    return None, None


def newest_plan_set(c, pid):
    rows = [dict(r) for r in c.execute(
        "select d.id,d.title,d.r2_url,d.file_size_bytes from documents d "
        "left join vocabulary_document_types v on v.id=d.document_type_id "
        "where d.project_id=? and v.code='plan_set' and d.r2_url is not null", (pid,))]
    rows = [r for r in rows if not JUNK.search(r["title"] or "")]
    if not rows:
        return None
    def key(r):
        m = DATE.search(r["title"] or "")
        return (m.group(0) if m else "0000", r["file_size_bytes"] or 0)
    return sorted(rows, key=key)[-1]          # LATEST vintage


def find_sheet(pdf, scan=20):
    """Best zoning-data page: most tabulation labels in the text layer; if the sheet is raster,
    fall back to the page whose OCR shows the markers."""
    doc = fitz.open(pdf); best = None
    try:
        for i in range(min(len(doc), scan)):
            t = doc[i].get_text()
            n = len(h.LABEL_RX.findall(t))
            w = len(doc[i].get_text("words"))
            if n >= 3 and (best is None or (n, w) > (best[1], best[2])):
                best = (i, n, w)
    finally:
        doc.close()
    if best:
        return best[0], "text"
    for i in range(min(6, len(fitz.open(pdf)))):     # raster sheets: OCR-scan the front pages
        png = f"{CACHE}/_scan.png"
        d = fitz.open(pdf); d[i].get_pixmap(dpi=150).save(png); d.close()
        if h.MARKERS.search(h.ocr(png)):
            return i, "ocr"
    return None, None


def propose(vals_lists):
    """PROPOSED = the LAST column. Values arrive as ordered per-row lists (one list per APN row)."""
    return [row[-1] for row in vals_lists if row]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=""); ap.add_argument("--limit", type=int)
    a = ap.parse_args()

    idx = parcel_index()
    c = sqlite3.connect("databases/berkeley_housing_v2.db"); c.row_factory = sqlite3.Row
    targets = [int(r["project_id"]) for r in csv.DictReader(open("data/reference/tour_structures_171.csv"))
               if r["harvest_priority"] == "high" and r["has_plan_set"] == "1"]
    if a.only:
        keep = {int(x) for x in a.only.split(",") if x.strip()}
        targets = [t for t in targets if t in keep]
    if a.limit:
        targets = targets[:a.limit]

    out = []
    for pid in targets:
        p = c.execute("select project_id,address_display,total_units,status_label,height_stories,"
                      "latitude,longitude from v_projects_flat where project_id=?", (pid,)).fetchone()
        rec = dict(project_id=pid, address=p["address_display"], units=p["total_units"],
                   status=p["status_label"], db_stories=p["height_stories"])
        doc = newest_plan_set(c, pid)
        if not doc:
            rec["note"] = "no usable plan set"; out.append(rec)
            print(f"proj{pid:<5} no usable plan set", flush=True); continue
        rec["doc_title"] = doc["title"]
        pdf = f"{CACHE}/proj{pid}.pdf"
        if not (os.path.exists(pdf) and os.path.getsize(pdf) > 1e6):
            subprocess.run(["curl", "-sS", "--max-time", "900", "-o", pdf, doc["r2_url"]])
        if not (os.path.exists(pdf) and os.path.getsize(pdf) > 1e6):
            rec["note"] = "download failed"; out.append(rec)
            print(f"proj{pid:<5} download failed", flush=True); continue

        page, how = find_sheet(pdf)
        if page is None:
            rec["note"] = "no zoning sheet located"; out.append(rec)
            print(f"proj{pid:<5} {str(p['address_display'])[:24]:26} no zoning sheet", flush=True); continue
        rec["sheet_page"] = page + 1; rec["method"] = how

        fps = lots = covs = gfas = sts = []
        if how == "text":
            g = h.extract_text_first(pdf, page)
            fps, lots = propose(g.get("footprint_sf", [])), propose(g.get("lot_area_sf", []))
            covs, gfas = propose(g.get("lot_coverage_pct", [])), propose(g.get("gross_floor_sf", []))
            sts = propose(g.get("stories", []))
        if not fps:                                   # text gave nothing usable -> OCR
            vals, ev, low = h.extract(h.read_sheet(pdf, page))
            rec["method"] = "ocr"; rec["low_confidence"] = ",".join(low)
            fps = [vals["footprint_sf"]] if vals.get("footprint_sf") else []
            lots = [vals["lot_area_sf"]] if vals.get("lot_area_sf") else []
            covs = [vals["lot_coverage_pct"]] if vals.get("lot_coverage_pct") else []
            gfas = [vals["gross_floor_sf"]] if vals.get("gross_floor_sf") else []
            sts = [vals["stories"]] if vals.get("stories") else []

        # MULTI-APN PROJECTS MUST NOT BE SUMMED. 2036 Bancroft states a footprint per APN, and
        # APN -017-04 reads "NO CHANGE" -- an EXISTING 4-storey building being RETAINED, not new
        # construction. Summing gave 36,145 sf for what is really an 11,610 sf new tower plus a
        # retained building. Which row is new and which is retained needs a human eye on the
        # sheet, so report the parts and refuse to total them.
        if len(fps) > 1:
            rec["footprint_sf"] = None
            rec["footprint_parts"] = " | ".join(f"{x:,.0f}" for x in fps)
            rec["note"] = (f"MULTI-APN: {len(fps)} footprint rows, NOT summed. One may be an "
                           f"existing building RETAINED ('NO CHANGE'). Needs manual split.")
        else:
            rec["footprint_sf"] = round(fps[0]) if fps else None
            rec["footprint_parts"] = ""
        rec["lot_area_sf"] = round(sum(lots)) if lots else None
        rec["coverage_pct"] = covs[0] if covs else None
        rec["gross_floor_sf"] = round(sum(gfas)) if gfas else None
        rec["stories"] = sts[-1] if sts else None

        apn, par = parcel_for(idx, p["longitude"], p["latitude"])
        rec["apn"], rec["parcel_sf"] = apn, (round(par) if par else None)
        checks, ok = [], []
        if rec["footprint_sf"] and rec["coverage_pct"] and par:
            implied = rec["footprint_sf"]/rec["coverage_pct"]*100
            r = implied/par; checks.append(f"implied_lot/parcel={r:.2f}"); ok.append(0.85 <= r <= 1.18)
        if rec["footprint_sf"] and rec["lot_area_sf"] and rec["coverage_pct"]:
            der = rec["footprint_sf"]/rec["lot_area_sf"]*100
            checks.append(f"derived_cov={der:.0f}%vs{rec['coverage_pct']:.0f}%")
            ok.append(abs(der-rec["coverage_pct"]) <= 10)
        if rec["gross_floor_sf"] and rec["footprint_sf"]:
            imp = rec["gross_floor_sf"]/rec["footprint_sf"]
            checks.append(f"gfa/fp={imp:.1f}storeys")
            if rec["stories"]:
                ok.append(abs(imp-rec["stories"]) <= 1.5)
        if rec["footprint_sf"] and par and rec["footprint_sf"] > par*1.15:
            checks.append("footprint EXCEEDS parcel"); ok.append(False)
        rec["checks"] = "; ".join(checks)
        # A PASS ON ONE CHECK IS NOT A PASS. 2530 Bancroft scored PASS on implied_lot/parcel
        # =0.98 alone -- but that check is DEGENERATE when footprint == lot area (100% coverage):
        # it is satisfied by construction, not by evidence. The reading was in fact incoherent
        # (100% coverage, 65 ft, "BUILDING STORIES 1" for a 110-unit building). Require TWO
        # independent checks to agree before calling anything verified.
        degenerate = (rec["footprint_sf"] and rec["lot_area_sf"]
                      and abs(rec["footprint_sf"] - rec["lot_area_sf"]) < 0.02 * rec["lot_area_sf"])
        n_ok = len(ok)
        if len(fps) > 1:
            rec["verdict"] = "NEEDS-MANUAL-SPLIT"
        elif n_ok == 0:
            rec["verdict"] = "UNVERIFIED"
        elif not all(ok):
            rec["verdict"] = "SUSPECT"
        elif n_ok < 2 or degenerate:
            rec["verdict"] = "WEAK"          # passed, but on too little independent evidence
            rec["checks"] += ("; only %d check(s)" % n_ok) + ("; footprint==lot (degenerate)" if degenerate else "")
        else:
            rec["verdict"] = "PASS"
        out.append(rec)
        print(f"proj{pid:<5} {str(p['address_display'])[:24]:26} p{rec['sheet_page']:<3} {rec['method']:5} "
              f"fp={rec['footprint_sf']} cov={rec['coverage_pct']} st={rec['stories']} "
              f"[{rec['verdict']}] {rec['checks'][:56]}", flush=True)

    cols = ["project_id", "address", "units", "status", "db_stories", "footprint_sf", "footprint_parts",
            "lot_area_sf", "coverage_pct", "gross_floor_sf", "stories", "apn", "parcel_sf",
            "verdict", "checks", "method", "sheet_page", "low_confidence", "doc_title", "note"]
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); [w.writerow(r) for r in out]
    print(f"\nwrote {OUT} ({len(out)} projects)")
    print("  " + str(dict(collections.Counter(r.get("verdict", "no-reading") for r in out))))


if __name__ == "__main__":
    main()
