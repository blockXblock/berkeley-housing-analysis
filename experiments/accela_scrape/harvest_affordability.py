"""
harvest_affordability.py — the AFFORDABILITY-FORM counterpart to harvest_plansets.py.

Harvests the DEDICATED affordability forms (DBE 5.C / Tabulation 1.E / AHCP 5.A / AHR /
Housing Affordability Statement) from an Accela ACA attachments grid, extracts the
base/VLI/LI/MOD/bonus% with a verbatim source quote per value, runs the mandatory RECENCY
check (form date vs v2 effective_date), reconciles against v2's current tiers, and stages a
review manifest. NOTHING irreversible: local staging + CSV only. NO R2, NO v2 write, no commit.

REUSE: imports harvest_plansets as H and drives H.harvest_record, so it inherits the engine's
PROVEN + HARDENED components VERBATIM:
  * discover_url(permit) -> CapDetail -> assert ZP permit label -> handlePortletNavigation
    (tab-attachments) -> content_frame  [permit->capID discovery]
  * WAIT-FOR-ROWS grid poll (H.harvest_record ~L220: poll read_rows up to 15x) — the fix for
    the transient false-0-forms timing bug (proj27: 0-in-batch vs 3-on-rerun).
  * WITHIN-BATCH sha256 dedup (_BATCH_SHA in H.download_one) + CROSS-KEY sha8 collision guard
    (H.write_manifest) — a form is never silently stranded by a key clash, and the same bytes
    re-attached under two names are caught.
  * three-state "Next >" pagination; %PDF magic + size validation; resumable state.json;
    polite 5-15s jitter between records; STOP-on-captcha/auth (visible-text markers).

OVERRIDES ONLY (affordability vs plan-set):
  * CLASSIFIER -> aff_classify: TIGHTENED word-boundary form tokens (1.E / 5.C / 5.A via
    lookbehind/lookahead, so "5a" inside a date/word never matches) + form keywords, size
    < 2 MB to exclude plan sets. Bare "ami" intentionally DROPPED (too noisy).
  * STAGE dir, no lower size bound, cap 12, and suggested_r2_key prefix -> affordability_forms/.

PERMIT DISCOVERY NOTE: a project may have NO permit row in v2 (e.g. proj4). Permits here are
supplied per-record (from the harvest sweep) and resolved permit->capID by discover_url; the
scraper has no address->capID search, so the swept ZP permit(s) are the discovery input. If
all supplied permits yield no form, the record is reported NO-FORM (address search would be
the next step, not implemented here).

Usage:  cd ~/berkeley-data && .venv/bin/python experiments/accela_scrape/harvest_affordability.py
        (edit RECORDS for a different project set; resumable via state.json)
"""
import sys, os, re, csv, json, time, random, subprocess, sqlite3
sys.path.insert(0, "experiments/accela_scrape")
import harvest_plansets as H

# ---- redirect engine outputs to the affordability stage ----
H.STAGE = "/tmp/affordability_proj4_35_6"
H.STATE = f"{H.STAGE}/state.json"
H.MANIFEST = f"{H.STAGE}/_engine_manifest.csv"   # engine raw manifest; we also write reconcile_manifest.csv
DB = "databases/berkeley_housing_v2.db"
MIB = H.MIB

# ---- TIGHTENED inverse affordability classifier (replaces H.classify) ----
AFF_KW = ("density bonus eligibility", "eligibility statement", "tabulation",
          "affordability statement", "affordable housing compliance", "housing compliance plan",
          "affordable housing requirements", "affordable housing form", "ahcp", "ahr")
# word-boundary form tokens; NO bare "ami"
AFF_FORM_RE = re.compile(r"(?<![A-Za-z0-9])(1\.?e|5\.?c|5\.?a)(?![A-Za-z0-9])", re.I)
AFF_SIZE_MAX = 2 * MIB

def aff_classify(fn, size_bytes):
    fl = (fn or "").lower()
    kw = next((k for k in AFF_KW if k in fl), None)
    ftok = AFF_FORM_RE.search(fl)
    if not (kw or ftok):
        return (False, None, "no aff keyword/form-number")
    tag = kw or ftok.group(0)
    if size_bytes is not None and size_bytes > AFF_SIZE_MAX:
        return (False, tag, f"aff '{tag}' but {size_bytes/MIB:.1f}MiB>2 (plan set?)")
    return (True, tag, f"aff '{tag}'" + (f" +{size_bytes/MIB:.1f}MiB" if size_bytes else " +size?"))

H.classify = aff_classify
H.PLAN_KW = AFF_KW
H.CLEAN_KW = AFF_KW
H.SIZE_MIN = 0          # affordability forms are small; no lower bound
H.CAP_PLANSETS = 12     # several forms per project possible

# permits supplied from the harvest sweep (proj4 has no v2 permit row); known-good first
RECORDS = [
    dict(proj=4,  permits=["ZP2020-0104", "ZP2022-0058"], addr="1914 Fifth"),
    dict(proj=35, permits=["ZP2025-0101"],                addr="2190 Shattuck"),
    dict(proj=6,  permits=["ZP2024-0181", "ZP2024-0182"], addr="2029 University"),
]

# ---- form-type + r2 key derivation ----
def form_type(fn):
    fl = (fn or "").lower()
    if "tabulation" in fl or re.search(r"(?<![a-z0-9])1\.?e(?![a-z0-9])", fl):
        return "tabulation"
    if "eligibility statement" in fl or "density bonus eligibility" in fl or re.search(r"(?<![a-z0-9])5\.?c(?![a-z0-9])", fl):
        return "dbe"
    if "compliance" in fl or "ahcp" in fl or re.search(r"(?<![a-z0-9])5\.?a(?![a-z0-9])", fl):
        return "ahcp"
    if "affordability statement" in fl or "affordable housing requirements" in fl or "affordable housing form" in fl or "ahr" in fl:
        return "ahr"
    return "affform"

# ---- extractor (text-layer + OCR fallback when text < 50 chars) ----
def get_text(path):
    txt = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True).stdout.decode("utf-8", "replace")
    if len(txt.strip()) >= 50:
        return txt, "text-layer"
    try:
        base = path + ".ocr"
        subprocess.run(["pdftoppm", "-r", "400", "-png", path, base], capture_output=True, timeout=300)
        chunks, d = [], os.path.dirname(path)
        for png in sorted(p for p in os.listdir(d) if os.path.basename(base) in p and p.endswith(".png")):
            pp = os.path.join(d, png)
            out = subprocess.run(["tesseract", pp, "-", "--psm", "6"], capture_output=True, timeout=300).stdout
            chunks.append(out.decode("utf-8", "replace"))
            os.remove(pp)
        return "\n".join(chunks), "ocr"
    except Exception as e:
        return "", f"ocr-failed:{str(e)[:40]}"

def norm_inc(s):
    s = s.lower().replace("-", " ").strip()
    if "very low" in s:
        return "VLI"
    if "moderate" in s:
        return "MOD"
    if "low" in s:
        return "LI"
    return s.upper()

def extract(path):
    txt, mode = get_text(path)
    flat = re.sub(r"[ \t]+", " ", txt)
    res = {"mode": mode, "base": None, "tiers": {}, "bonus_pct": None, "quotes": {}, "raw_chars": len(txt.strip())}
    m = re.search(r'base project[^\n]*?:?\s*(\d{1,4})\s*units?', flat, re.I) or \
        re.search(r'(\d{1,4})\s*base\s*(?:project\s*)?units?', flat, re.I)
    if m:
        res["base"] = int(m.group(1)); res["quotes"]["base"] = m.group(0).strip()[:160]
    # count-first: "14-Units (15%) affordable to Very Low"
    for mm in re.finditer(r'(\d{1,4})\s*-?\s*units?\s*\((\d{1,3})%\)\s*affordable to\s*([A-Za-z\- ]+?)(?:income|household|\.|,|\n)', flat, re.I):
        inc = norm_inc(mm.group(3))
        res["tiers"][inc] = {"count": int(mm.group(1)), "pct": int(mm.group(2))}
        res["quotes"][inc] = mm.group(0).strip()[:180]
    # percent-first narrative: "15% (18 UNITS) ... affordable to Very-Low-Income"
    for mm in re.finditer(r'(\d{1,3})%\s*\((\d{1,4})\s*units?\)[^\n]*?affordable to\s*([A-Za-z\- ]+?)(?:income|household|\.|,|\n)', flat, re.I):
        inc = norm_inc(mm.group(3))
        if inc not in res["tiers"]:
            res["tiers"][inc] = {"count": int(mm.group(2)), "pct": int(mm.group(1))}
            res["quotes"][inc] = mm.group(0).strip()[:180]
    m = re.search(r'density bonus[^\n]*?(\d{1,3})%', flat, re.I) or re.search(r'(\d{1,3})%\s*density bonus', flat, re.I)
    if m:
        res["bonus_pct"] = int(m.group(1)); res["quotes"]["bonus"] = m.group(0).strip()[:160]

    # ---- AHCP "Total BMR Units Proposed by Income" parser (line-anchored, block-scoped) ----
    # The committed split lives in the "D Total BMR Units Proposed by Income" block as
    # "<band>% AMI (<label>) <count>" rows; a blank count means 0 (label line has no number).
    # We SCOPE to that block and require the count on the SAME physical line — otherwise a blank
    # label steals a digit from an unrelated section (observed: ELI/LI mis-grabbed). The
    # unit-type "TOTAL ... 452" row is used as an independent cross-check. 30->ELI 50->VLI
    # 80->LI 120->MOD.
    BAND = {"30": "ELI", "50": "VLI", "80": "LI", "120": "MOD"}
    if not any(c in res["tiers"] for c in ("VLI", "LI", "MOD", "ELI")):
        bm = re.search(r'Total BMR Units Proposed by Income(.*?)(?:TOTAL BMR Units|PROJECT UNIT TYPES|3\.\s)', txt, re.I | re.S)
        block = bm.group(1) if bm else ""
        ahcp_tiers = {}
        for line in block.splitlines():
            lm = re.match(r'\s*(\d{2,3})\s*%\s*AMI\s*\([^)]*\)\s+(\d{1,4})\s*$', line)
            if lm:
                inc = BAND.get(lm.group(1))
                if inc:
                    ahcp_tiers[inc] = int(lm.group(2))
                    res["quotes"][inc] = line.strip()[:120]
        if ahcp_tiers:
            # cross-check: BMR total in-block + market TOTAL row should reconcile to Total Units
            tb = re.search(r'TOTAL BMR Units\s+(\d{1,4})', txt, re.I)
            res["ahcp_bmr_total"] = int(tb.group(1)) if tb else None
            res["ahcp_crosscheck"] = (res["ahcp_bmr_total"] == sum(ahcp_tiers.values())) if tb else None
            for inc, cnt in ahcp_tiers.items():
                res["tiers"][inc] = {"count": cnt, "pct": None}
        mb = re.search(r'Base Units?:\s*([\d,]{1,7})', flat, re.I)
        if mb and res["base"] is None:
            res["base"] = int(mb.group(1).replace(",", "")); res["quotes"].setdefault("base", mb.group(0).strip())
        mt = re.search(r'Total Units?:\s*([\d,]{1,7})', flat, re.I)
        if mt:
            res["total"] = int(mt.group(1).replace(",", "")); res["quotes"]["total"] = mt.group(0).strip()
    return res

# ---- v2 reconcile context ----
def v2_ctx(pid):
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    eff = con.execute("SELECT effective_date FROM project_versions WHERE project_id=? AND is_current=1", (pid,)).fetchone()
    tot = con.execute("SELECT total_units FROM project_versions WHERE project_id=? AND is_current=1", (pid,)).fetchone()
    tiers = {}
    for code, n in con.execute("""SELECT vic.code, upa.unit_count FROM unit_program_affordability upa
            JOIN unit_program up ON up.id=upa.unit_program_id
            JOIN project_versions pv ON pv.id=up.project_version_id
            JOIN vocabulary_income_categories vic ON vic.id=upa.income_category_id
            WHERE pv.project_id=? AND pv.is_current=1""", (pid,)):
        tiers[code] = n
    con.close()
    return (eff[0] if eff else None), (tot[0] if tot else None), tiers

def recency(form_date, eff_date):
    if not eff_date:
        return "CLEARS (no effective_date)"
    if form_date == "nodate":
        return "UNKNOWN (form undated)"
    return "CLEARS (form newer)" if form_date >= eff_date else f"RECENCY-HOLD (form {form_date} < v2 {eff_date})"

REPORT_COLS = ["action", "project_id", "form_type", "form_date", "v2_effective_date", "recency",
               "extracted_tiers", "v2_current", "count_delta", "extract_mode", "source_quote",
               "confidence", "suggested_r2_key", "sha256", "filename", "local_path"]

def main():
    os.makedirs(H.STAGE, exist_ok=True)
    sha_set, stubs = H.load_v2()
    st = H.load_state()
    done = set(st["completed"])

    # REEXTRACT_ONLY: re-run the extract+reconcile pass over already-staged files (no Accela
    # hit, no re-download) — used after improving the parser. Skips the harvest loop entirely.
    reextract_only = bool(os.environ.get("REEXTRACT_ONLY"))

    for i, rec in enumerate([] if reextract_only else RECORDS):
        key = str(rec["proj"])
        if key in done:
            print(f"\n=== proj{rec['proj']} resume-skip ===")
            continue
        print(f"\n{'='*72}\nproj{rec['proj']} {rec['addr']} permits={rec['permits']}\n{'='*72}")
        rows, used = [], None
        for permit in rec["permits"]:
            single = dict(proj=rec["proj"], permit=permit, addr=rec["addr"])
            try:
                rr = H.harvest_record(single, sha_set, stubs)
            except Exception as e:
                rr = [dict(status="FAILED-exception", project_id=rec["proj"], permit_number=permit,
                           filename="", file_size_mib="", page_count="", classifier_reason=str(e)[:90],
                           grid_displayed_size="", sha256="", suggested_r2_key="",
                           existing_stub_doc_id="", local_path="")]
            used, rows = permit, rr
            got = any(r["status"] in ("STAGED-OK", "SKIPPED-DEDUP", "SKIPPED-DEDUP-BATCH") for r in rr)
            if got or len(rec["permits"]) == 1:
                break
            print(f"  permit {permit}: no affordability forms; trying next permit...")
            time.sleep(random.uniform(5, 15))
        for r in rows:
            r.setdefault("permit_number", used)
            if r["status"] == "STAGED-OK":
                ftype = form_type(r["filename"])
                fdate = H.extract_date(r["filename"])
                r["form_type"] = ftype
                r["form_date"] = fdate
                r["suggested_r2_key"] = f"affordability_forms/proj{rec['proj']}_{ftype}_{fdate}.pdf"
        print(f"  -> resolved permit: {used}")
        st["rows"].extend(rows)
        st["completed"].append(key)
        H.save_state(st)
        if i < len(RECORDS) - 1:
            dly = random.uniform(6, 14)
            print(f"  ...polite delay {dly:.1f}s")
            time.sleep(dly)

    # apply the CROSS-KEY sha8 collision guard (mutates rows in place) + write engine manifest
    H.write_manifest(st["rows"])

    # ---- extract + reconcile per staged form ----
    report = []
    by_proj = {}
    for r in st["rows"]:
        by_proj.setdefault(r["project_id"], []).append(r)

    for pid, rrows in sorted(by_proj.items(), key=lambda x: str(x[0])):
        eff, tot, v2tiers = v2_ctx(pid)
        staged = [r for r in rrows if r["status"] == "STAGED-OK"]
        stops = [r for r in rrows if r["status"].startswith("STOP")]
        if stops:
            report.append(dict(action="STOP", project_id=pid, v2_effective_date=eff or "NONE",
                               v2_current=json.dumps(v2tiers), source_quote=stops[0].get("classifier_reason", ""),
                               recency="", form_type="", form_date="", extracted_tiers="", count_delta="",
                               extract_mode="", confidence="", suggested_r2_key="", sha256="", filename="", local_path=""))
            continue
        if not staged:
            report.append(dict(action="NO-FORM", project_id=pid, v2_effective_date=eff or "NONE",
                               recency=recency("nodate", eff), v2_current=json.dumps(v2tiers),
                               source_quote="no affordability form in grid", form_type="", form_date="",
                               extracted_tiers="", count_delta="", extract_mode="", confidence="",
                               suggested_r2_key="", sha256="", filename="", local_path=""))
            continue
        for r in staged:
            ex = extract(r["local_path"]) if r.get("local_path") and os.path.exists(r["local_path"]) \
                 else {"mode": "no-file", "tiers": {}, "base": None, "bonus_pct": None, "quotes": {}, "raw_chars": 0}
            fdate = r.get("form_date") or H.extract_date(r["filename"])
            rec_state = recency(fdate, eff)
            extr = {k: v["count"] for k, v in ex.get("tiers", {}).items()}
            if ex.get("base") is not None:
                extr["_base"] = ex["base"]
            if ex.get("bonus_pct") is not None:
                extr["_bonus%"] = ex["bonus_pct"]
            delta = {}
            for code in ("VLI", "LI", "MOD"):
                if code in extr:
                    delta[code] = extr[code] - v2tiers.get(code, 0)
            has_aff = any(c in extr for c in ("VLI", "LI", "MOD"))
            if "RECENCY-HOLD" in rec_state:
                action = "RECENCY-HOLD"
            elif not has_aff:
                action = "REVIEW (no tier parsed)"
            elif set(v2tiers) <= {"ABOVE_MOD"}:
                action = "CORRECT (v2 all-market; form has tiers)"
            elif all(delta.get(c, 0) == 0 for c in delta):
                action = "CONFIRM"
            else:
                action = "CORRECT (count-delta -> OCR-verify)"
            conf = "high (text-layer parsed)" if ex.get("mode") == "text-layer" and has_aff \
                   else ("ocr" if ex.get("mode") == "ocr" else "low")
            report.append(dict(
                action=action, project_id=pid, form_type=r.get("form_type", form_type(r["filename"])),
                form_date=fdate, v2_effective_date=eff or "NONE", recency=rec_state,
                extracted_tiers=json.dumps(extr), v2_current=json.dumps(v2tiers),
                count_delta=json.dumps(delta), extract_mode=ex.get("mode", ""),
                source_quote=" || ".join(f"{k}:{v}" for k, v in ex.get("quotes", {}).items())[:500],
                confidence=conf, suggested_r2_key=r.get("suggested_r2_key", ""),
                sha256=r.get("sha256", ""), filename=r["filename"], local_path=r.get("local_path", "")))

    out = f"{H.STAGE}/reconcile_manifest.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REPORT_COLS)
        w.writeheader()
        for r in report:
            w.writerow({k: r.get(k, "") for k in REPORT_COLS})

    print(f"\n{'#'*72}\nAFFORDABILITY HARVEST SUMMARY\n{'#'*72}")
    staged_all = [r for r in st["rows"] if r["status"] == "STAGED-OK"]
    print(f"  staged forms: {len(staged_all)}   reconcile rows: {len(report)}")
    print(f"  reconcile manifest: {out}")
    for r in report:
        print(f"  [proj{r['project_id']}] {r['action']:<38} {r['form_type']:<11} {r['form_date']} "
              f"| recency: {r['recency']}")
        if r.get("extracted_tiers") and r["extracted_tiers"] not in ("", "{}"):
            print(f"        extracted={r['extracted_tiers']}  v2={r['v2_current']}  delta={r['count_delta']}  ({r['extract_mode']})")
        if r.get("source_quote"):
            print(f"        quote: {r['source_quote'][:170]}")

if __name__ == "__main__":
    main()
