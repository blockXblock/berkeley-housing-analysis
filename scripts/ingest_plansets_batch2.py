#!/usr/bin/env python3
"""ingest_plansets_batch2.py — write the 12 harvested + R2-uploaded plan sets into v2.documents.

ONE-TIME gated op (John approved 2026-08-23). Reads the harvest manifest + the r2_uploaded_urls
map, inserts one `plan_set` (document_type_id=2) documents row per uploaded file, linked to its
project, pointing at the R2 public URL. sha256-dedup against existing documents (idempotent — a
re-run inserts nothing). Transactional: verify inserted count == expected, else ROLLBACK.

Snapshot taken first: databases/keep_snapshot_2026-08-23_pre-planset-ingest.db
Run: .venv/bin/python scripts/ingest_plansets_batch2.py [--commit]   (default: preview only)
"""
import sys, os, csv, re, argparse, datetime, sqlite3

DB = "databases/berkeley_housing_v2.db"
STAGE = "scratch/2026-08-23/harvest_stage_batch2"
MANIFEST = f"{STAGE}/manifest.csv"
URLMAP = f"{STAGE}/r2_uploaded_urls.csv"
DOCTYPE_PLAN_SET = 2
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def clean_title(filename):
    base = re.sub(r"\.pdf$", "", filename, flags=re.I)
    return re.sub(r"[_]+", " ", base).strip()


def pub_date(filename):
    m = re.search(r"(\d{4})[-_.](\d{2})[-_.](\d{2})", filename)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="actually write (default: preview + rollback)")
    a = ap.parse_args()

    staged = [r for r in csv.DictReader(open(MANIFEST)) if r["status"] == "STAGED-OK"]
    urlmap = {r["suggested_r2_key"]: r for r in csv.DictReader(open(URLMAP))}

    con = sqlite3.connect(DB)
    existing_sha = {r[0] for r in con.execute("SELECT sha256 FROM documents WHERE sha256 IS NOT NULL AND sha256<>''")}

    rows, skipped = [], []
    for r in staged:
        key = r["suggested_r2_key"].strip()
        um = urlmap.get(key)
        if not um or um["status"] not in ("uploaded-verified", "skipped-exists"):
            skipped.append((key, "not uploaded-verified")); continue
        sha = r["sha256"].strip()
        if sha in existing_sha:
            skipped.append((key, "sha already in documents")); continue
        size_bytes = os.path.getsize(r["local_path"]) if os.path.exists(r["local_path"]) else int(um["size_bytes"])
        pc = None if r["page_count"] in ("", "?", "n/a") else int(r["page_count"])
        rows.append(dict(
            project_id=int(r["project_id"]), document_type_id=DOCTYPE_PLAN_SET,
            title=clean_title(r["filename"]), published_date=pub_date(r["filename"]),
            permit_number=r["permit_number"].strip() or None,
            source_system="accela_harvest_batch2_2026-08-23", url_status="active",
            r2_url=um["public_url"], sha256=sha, file_size_bytes=size_bytes, page_count=pc,
            fetched_at=NOW, notes=f"filename: {r['filename']}", created_at=NOW, updated_at=NOW))

    print(f"staged uploaded: {len(staged)}  |  to insert: {len(rows)}  |  skipped: {len(skipped)}")
    for k, why in skipped:
        print(f"  SKIP {k}  ({why})")
    for r in rows:
        print(f"  INSERT proj{r['project_id']} [{r['permit_number']}] {r['page_count']}pp  {r['title'][:52]}")

    before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    cols = ("project_id", "document_type_id", "title", "published_date", "permit_number",
            "source_system", "url_status", "r2_url", "sha256", "file_size_bytes", "page_count",
            "fetched_at", "notes", "created_at", "updated_at")
    try:
        con.execute("BEGIN")
        for r in rows:
            cur = con.execute(f"INSERT INTO documents ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
                              tuple(r[c] for c in cols))
            assert cur.rowcount == 1
        after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        assert after - before == len(rows), f"count delta {after-before} != {len(rows)}"
        if a.commit:
            con.commit(); print(f"\nCOMMITTED. documents {before} -> {after} (+{len(rows)})")
        else:
            con.rollback(); print(f"\nPREVIEW ok (rolled back). would be {before} -> {after}. Re-run with --commit.")
    except Exception as e:
        con.rollback(); print(f"\nROLLED BACK on error: {e}"); sys.exit(1)
    finally:
        con.close()


if __name__ == "__main__":
    main()
