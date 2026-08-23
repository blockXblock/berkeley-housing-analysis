#!/usr/bin/env python3
"""ingest_plansets_phase2.py — write the phase-2 harvested + R2-uploaded plan sets AND tabulation
forms into v2.documents.

Gated op (John approved go + full scope 2026-08-23). Reads the phase-2 manifest + r2_uploaded_urls,
inserts one documents row per uploaded file: plan sets → document_type_id=2 (plan_set); 1.E /
tabulation forms → a NEW document_type_id (tabulation_form, added here if absent). sha256-dedup
against existing documents (idempotent). Transactional: verify inserted count == expected, else
ROLLBACK. Snapshot taken first.

Run: .venv/bin/python scripts/ingest_plansets_phase2.py [--commit]   (default: preview + rollback)
"""
import sys, os, csv, re, argparse, datetime, sqlite3

DB = "databases/berkeley_housing_v2.db"
STAGE = "scratch/2026-08-23/harvest_stage_phase2"
MANIFEST = f"{STAGE}/manifest.csv"
URLMAP = f"{STAGE}/r2_uploaded_urls.csv"
DOCTYPE_PLAN_SET = 2
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def clean_title(fn):
    return re.sub(r"[_]+", " ", re.sub(r"\.pdf$", "", fn, flags=re.I)).strip()


def pub_date(fn):
    m = re.search(r"(\d{4})[-_.](\d{2})[-_.](\d{2})", fn)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def ensure_tabulation_type(con):
    row = con.execute("SELECT id FROM vocabulary_document_types WHERE code='tabulation_form'").fetchone()
    if row:
        return row[0]
    nid = con.execute("SELECT MAX(id)+1 FROM vocabulary_document_types").fetchone()[0]
    con.execute("INSERT INTO vocabulary_document_types (id, code, label) VALUES (?,?,?)",
                (nid, "tabulation_form", "Zoning Tabulation Form"))
    print(f"  + added vocabulary_document_types id={nid} code=tabulation_form")
    return nid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()

    staged = [r for r in csv.DictReader(open(MANIFEST)) if r["status"] == "STAGED-OK"]
    urlmap = {r["suggested_r2_key"]: r for r in csv.DictReader(open(URLMAP))}

    con = sqlite3.connect(DB)
    existing_sha = {r[0] for r in con.execute("SELECT sha256 FROM documents WHERE sha256 IS NOT NULL AND sha256<>''")}
    before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    try:
        con.execute("BEGIN")
        tab_type = ensure_tabulation_type(con)
        rows, skipped = [], []
        for r in staged:
            key = r["suggested_r2_key"].strip()
            um = urlmap.get(key)
            if not um or um["status"] not in ("uploaded-verified", "skipped-exists"):
                skipped.append((key, "not uploaded")); continue
            sha = r["sha256"].strip()
            if sha in existing_sha:
                skipped.append((key, "sha dup")); continue
            is_tab = "tabulation" in r.get("classifier_reason", "")
            size_bytes = os.path.getsize(r["local_path"]) if os.path.exists(r["local_path"]) else int(um["size_bytes"])
            pc = None if r["page_count"] in ("", "?", "n/a") else int(r["page_count"])
            rows.append((int(r["project_id"]), tab_type if is_tab else DOCTYPE_PLAN_SET,
                         clean_title(r["filename"]), pub_date(r["filename"]),
                         r["permit_number"].strip() or None, "accela_harvest_phase2_2026-08-23",
                         "active", um["public_url"], sha, size_bytes, pc, NOW,
                         f"filename: {r['filename']}", NOW, NOW))
        cols = ("project_id", "document_type_id", "title", "published_date", "permit_number",
                "source_system", "url_status", "r2_url", "sha256", "file_size_bytes", "page_count",
                "fetched_at", "notes", "created_at", "updated_at")
        n_tab = sum(1 for x in rows if x[1] == tab_type)
        print(f"staged: {len(staged)}  to insert: {len(rows)} ({n_tab} tabulation, {len(rows)-n_tab} plan_set)  skipped: {len(skipped)}")
        for k, why in skipped[:8]:
            print(f"  SKIP {k[:50]} ({why})")
        for r in rows:
            con.execute(f"INSERT INTO documents ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})", r)
        after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        assert after - before == len(rows), f"count delta {after-before} != {len(rows)}"
        if a.commit:
            con.commit(); print(f"\nCOMMITTED. documents {before} -> {after} (+{len(rows)}), tabulation_form type={tab_type}")
        else:
            con.rollback(); print(f"\nPREVIEW ok (rolled back). would be {before} -> {after}. Re-run with --commit.")
    except Exception as e:
        con.rollback(); print(f"\nROLLED BACK on error: {e}"); sys.exit(1)
    finally:
        con.close()


if __name__ == "__main__":
    main()
