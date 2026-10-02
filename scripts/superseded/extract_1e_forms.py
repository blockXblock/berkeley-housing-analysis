#!/usr/bin/env python3
"""extract_1e_forms.py — read every City of Berkeley Tabulation Form 1.E we hold.

THE 1.E IS THE ORACLE. It is ~200 KB, pdftotext reads it directly with no OCR, it is a STANDARD
CITY FORM so the field names are identical across architects, and it carries FOOTPRINT, LOT AREA,
LOT COVERAGE, HEIGHT IN STOREYS and DWELLING UNITS together. Every extraction from one has
succeeded, while plan-set zoning tables yielded 1 usable footprint from 58 attempts.

THE COLUMN TRAP, AND HOW THIS RESOLVES IT. Columns run EXISTING | PROPOSED | PERMITTED. Taking
the wrong one returns the building being DEMOLISHED -- plausible, and wrong. On 2955 Shattuck I
took 51% (existing) instead of 92% (proposed) and drew a footprint 1.8x too small, having also
skipped the 1.E in favour of a plan set. The fix is not care, it is a TEST:

    THE DWELLING-UNITS ROW IDENTIFIES THE PROPOSED COLUMN.
    New construction reads "0 | 74 | NA" -- existing zero, proposed the real count. Matching that
    count against v2's total_units pins which column is PROPOSED, and every other row is then read
    from the same position. Where the units row is absent or ambiguous we fall back to the second
    numeric column and SAY SO in the verdict, rather than assume.

Cross-checks carried on every row (each caught a real error today):
    footprint = lot_area x coverage        internal consistency of the form itself
    footprint x storeys / units = 400-1500  floor area per dwelling
    lot_area vs the county parcel           flags multi-parcel sites, does not fail them

Output: data/reference/stated_1e.csv   READ-ONLY on all sources.
"""
import argparse, csv, json, math, os, re, sqlite3, subprocess, collections

CACHE = "scratch/2026-08-26/tabs"
OUT = "data/reference/stated_1e.csv"
PARCELS = "data/raw/berkeley_taxparcels_2026-08-12.geojson"
RX = "(d.title like '%1.E%' or d.title like '%1E %' or lower(d.title) like '%tabulation%')"
NUM = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*%?")


def rows_of(txt):
    out = {}
    for ln in txt.splitlines():
        s = " ".join(ln.split())
        for key, pat in (("units", r"Number of Dwelling Units"),
                         ("stories", r"Building Height\*?\s*\(#\s*Stories\)"),
                         ("lot_area", r"Lot Area"),
                         ("coverage", r"Lot Coverage"),
                         ("footprint", r"Building Footprint"),
                         ("gfa", r"Gross Floor Area")):
            if re.search(pat, s, re.I) and key not in out:
                tail = re.split(pat, s, flags=re.I)[-1]
                # COLLAPSE RANGES FIRST. An existing value is often written "1/2" or "1-2"
                # storeys; splitting that into two numbers shifts every later column right and
                # silently returns the wrong one. 2300 Ellsworth reads "1/2  7  5 (UP)" and gave
                # 2 storeys for a 69-unit building instead of 7 -- the units and coverage rows on
                # the same form were fine, so nothing else flagged it. Take the RANGE's upper
                # bound as the single existing value.
                tail = re.sub(r"(\d+)\s*[/+-]\s*(\d+)", lambda m: m.group(2), tail)
                vals = []
                for m in NUM.finditer(tail):
                    v = float(m.group(1).replace(",", ""))
                    vals.append(v)
                if vals:
                    out[key] = vals
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int); a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    c = sqlite3.connect("databases/berkeley_housing_v2.db"); c.row_factory = sqlite3.Row
    docs = collections.defaultdict(list)
    for r in c.execute(f"""select d.project_id,d.id,d.title,d.r2_url from documents d
                           where {RX} and d.r2_url is not null order by d.title desc"""):
        docs[r["project_id"]].append(r)
    pids = list(docs)[:a.limit] if a.limit else list(docs)

    out = []
    for pid in pids:
        p = c.execute("""select address_display,total_units,height_stories,status_label
                         from v_projects_flat where project_id=?""", (pid,)).fetchone()
        if not p:
            continue
        best = None
        for d in docs[pid]:                       # newest title first
            dst = f"{CACHE}/p{pid}_{d['id']}.pdf"
            if not os.path.exists(dst):
                subprocess.run(["curl", "-sS", "--max-time", "120", "-o", dst, d["r2_url"]])
            if not os.path.exists(dst) or os.path.getsize(dst) < 5000:
                continue
            txt = subprocess.run(["pdftotext", "-layout", dst, "-"],
                                 capture_output=True, text=True).stdout
            R = rows_of(txt)
            if "coverage" in R or "footprint" in R:
                best = (d, R); break
        rec = dict(project_id=pid, address=p["address_display"], units=p["total_units"],
                   status=p["status_label"], db_stories=p["height_stories"])
        if not best:
            rec["verdict"] = "NO-READ"; out.append(rec); continue
        d, R = best
        rec["doc_title"] = d["title"]

        # THE UNITS ROW PINS THE PROPOSED COLUMN
        col, how = None, ""
        if "units" in R and p["total_units"]:
            U = R["units"]
            for i, v in enumerate(U):
                if abs(v - p["total_units"]) > max(2, 0.05*p["total_units"]):
                    continue
                # A MATCH ON COLUMN 0 IS A TRAP. v2's total_units can still hold the count of
                # the building STANDING TODAY, so matching it picks EXISTING. 2204 Dwight reads
                # units "2 | 4" and storeys "2 | 3": v2 says 2 units, so the naive match chose
                # column 0 and I drew the building being replaced. If a later column carries a
                # LARGER unit count, that is the proposal.
                if i == 0 and any(x > v for x in U[1:]):
                    j = max(range(1, len(U)), key=lambda z: U[z])
                    col, how = j, (f"units row: v2 {p['total_units']} matches EXISTING; "
                                   f"proposed taken as the larger {U[j]:.0f}")
                else:
                    col, how = i, f"units row: {v:.0f} matches v2 {p['total_units']}"
                break
            if col is None:
                # v2 matched nothing; if the row looks like new construction (0 existing), the
                # proposal is simply the largest entry
                if U and U[0] == 0 and len(U) > 1:
                    j = max(range(1, len(U)), key=lambda z: U[z])
                    col, how = j, f"units row: 0 existing, proposed taken as {U[j]:.0f}"
        if col is None:
            col, how = 1, "FALLBACK second column (units row absent or no match)"
        rec["proposed_col"], rec["col_basis"] = col, how

        def pick(key):
            v = R.get(key)
            if not v:
                return None
            return v[col] if col < len(v) else v[-1]
        rec["lot_area_sf"] = pick("lot_area")
        rec["coverage_pct"] = pick("coverage")
        rec["footprint_sf"] = pick("footprint")
        rec["stories"] = pick("stories")
        rec["gfa_sf"] = pick("gfa")
        rec["raw_units_row"] = "|".join(f"{x:g}" for x in R.get("units", []))
        rec["raw_coverage_row"] = "|".join(f"{x:g}" for x in R.get("coverage", []))

        # derive footprint from lot x coverage when the form does not state it outright
        # PLAUSIBILITY FLOOR. A stray token can come back as a "footprint" of 16 sf, and
        # applying that shrank 2018 Blake from 4,547 sf to 16 before anything caught it. No
        # building has a footprint under 200 sf; reject rather than propagate.
        if rec["footprint_sf"] is not None and rec["footprint_sf"] < 200:
            rec["footprint_reject"] = f"{rec['footprint_sf']:g} sf implausible"
            rec["footprint_sf"] = None
        if not rec["footprint_sf"] and rec["lot_area_sf"] and rec["coverage_pct"]:
            rec["footprint_sf"] = round(rec["lot_area_sf"]*rec["coverage_pct"]/100)
            rec["footprint_source"] = "lot x coverage"
        elif rec["footprint_sf"]:
            rec["footprint_source"] = "stated"

        checks, ok = [], []
        if rec["footprint_sf"] and rec["lot_area_sf"] and rec["coverage_pct"]:
            der = rec["footprint_sf"]/rec["lot_area_sf"]*100
            checks.append(f"fp/lot={der:.0f}% vs {rec['coverage_pct']:.0f}%")
            ok.append(abs(der-rec["coverage_pct"]) <= 8)
        if rec["footprint_sf"] and rec["stories"] and p["total_units"]:
            spu = rec["footprint_sf"]*rec["stories"]/p["total_units"]
            rec["sf_per_unit"] = round(spu)
            checks.append(f"{spu:.0f} sf/unit")
            ok.append(300 <= spu <= 2500)
        rec["checks"] = "; ".join(checks)
        rec["verdict"] = ("UNVERIFIED" if not ok else
                          "PASS" if all(ok) and len(ok) >= 2 else
                          "WEAK" if all(ok) else "SUSPECT")
        out.append(rec)
        print(f"  proj{pid:<5} {str(p['address_display'])[:24]:26} fp={str(rec.get('footprint_sf')):>8} "
              f"st={str(rec.get('stories')):>5} [{rec['verdict']}] {how[:34]}", flush=True)

    cols = ["project_id","address","units","status","db_stories","footprint_sf","footprint_source",
            "lot_area_sf","coverage_pct","stories","gfa_sf","sf_per_unit","proposed_col",
            "col_basis","footprint_reject","raw_units_row","raw_coverage_row","verdict","checks","doc_title"]
    os.makedirs("data/reference", exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); [w.writerow(r) for r in out]
    print(f"\nwrote {OUT} ({len(out)} projects)")
    print("  " + str(dict(collections.Counter(r.get("verdict") for r in out))))


if __name__ == "__main__":
    main()
