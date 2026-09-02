#!/usr/bin/env python3
"""insert_r2_plan_set_docs.py — register the 5 uploaded plan sets in `documents`.

WHY. These five PDFs were harvested on 2026-08-23 but never ingested and never mirrored: no
`documents` row, no r2_url, one local copy. They are now in R2 (verified public 200 + size).
This records them, so the site's promise that the documents are freely available is backed by
a row someone can query rather than a file on one laptop.

GATED. --write is transactional: BEGIN, insert, verify the expected count, COMMIT or ROLLBACK.
Run without --write for the read-only preview. Snapshot the DB before --write.

CONVENTIONS COPIED FROM THE 274 ROWS ALREADY THERE, not invented:
  document_type_id 2  = plan set   (25 = tabulation form, which is why the 2023-01-27 key
                                    collided -- a DIFFERENT document already owned it)
  source_system       = accela_harvest_{batch2,phase2}_2026-08-23, matching the harvest dir
  title               = the source filename with separators as spaces, as the harvest rows do
"""
import argparse, os, re, sqlite3, sys, datetime

ROWS_TSV = "scratch/r2_upload_rows.tsv"
DB = "databases/berkeley_housing_v2.db"
PLAN_SET = 2


def title_of(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"\s+", " ", stem.replace("_", " ")).strip()


def source_system_of(path):
    m = re.search(r"harvest_stage_(batch2|phase2)", path)
    return f"accela_harvest_{m.group(1)}_2026-08-23" if m else "accela_harvest_2026-08-23"


def load():
    out = []
    with open(ROWS_TSV, encoding="utf-8") as f:
        next(f)
        for line in f:
            pid, addr, fpath, size, sha, url = line.rstrip("\n").split("\t")
            m = re.match(r"(\d{4}-\d{2}-\d{2})", os.path.basename(fpath))
            out.append(dict(project_id=int(pid), address=addr, local=fpath,
                            size=int(size), sha=sha, url=url,
                            title=title_of(fpath), published=m.group(1) if m else None,
                            source_system=source_system_of(fpath)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    rows = load()
    conn = sqlite3.connect(a.db)
    before = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    print(f"documents before: {before}\n" + "=" * 78)
    dupes = 0
    for r in rows:
        clash = conn.execute("SELECT id FROM documents WHERE sha256=? OR r2_url=?",
                             (r["sha"], r["url"])).fetchone()
        flag = f"  ALREADY PRESENT as id {clash[0]} — will skip" if clash else ""
        dupes += 1 if clash else 0
        print(f"proj{r['project_id']:<4} {r['address']}")
        print(f"  title        {r['title']}")
        print(f"  type         {PLAN_SET} (plan set)")
        print(f"  published    {r['published']}")
        print(f"  source       {r['source_system']}")
        print(f"  size/sha     {r['size']:,} B / {r['sha'][:16]}…")
        print(f"  r2_url       {r['url']}{flag}\n")
    new = len(rows) - dupes
    print("=" * 78)
    print(f"would insert {new} row(s); {dupes} already present. after = {before + new}")

    if not a.write:
        print("\nPREVIEW ONLY — no write. Re-run with --write after snapshotting.")
        return 0

    now = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        conn.execute("BEGIN")
        n = 0
        for r in rows:
            if conn.execute("SELECT 1 FROM documents WHERE sha256=? OR r2_url=?",
                            (r["sha"], r["url"])).fetchone():
                continue
            cur = conn.execute(
                "INSERT INTO documents (project_id, document_type_id, title, published_date,"
                " source_system, r2_url, sha256, file_size_bytes, fetched_at, notes,"
                " created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (r["project_id"], PLAN_SET, r["title"], r["published"], r["source_system"],
                 r["url"], r["sha"], r["size"], now,
                 "Harvested 2026-08-23; uploaded to R2 2026-09-02 (was unmirrored and unrecorded).",
                 now, now))
            assert cur.rowcount == 1, f"rowcount {cur.rowcount} for {r['url']}"
            n += 1
        after = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        assert after == before + n, f"count {after} != {before}+{n}"
        conn.commit()
        print(f"\nCOMMITTED {n} row(s). documents: {before} -> {after}")
    except Exception as e:
        conn.rollback()
        print(f"\nROLLED BACK — {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
