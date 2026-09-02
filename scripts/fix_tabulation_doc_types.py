#!/usr/bin/env python3
"""fix_tabulation_doc_types.py — file tabulation forms as tabulation forms.

THE PROBLEM. `documents` carries two vocabulary ids for the same thing in practice: 25
(tabulation_form, "Zoning Tabulation Form") and 23 (other). Nine 1.E forms were filed under 23,
including 1974 Shattuck's — the 599-unit tower the homepage calls one of the two tallest in the
pipeline. Anyone measuring affordability coverage by `document_type_id=25` silently misses them,
which is exactly what happened today: a harvest target list built on type 25 counted three
projects as having no 1.E when the form was already in hand.

NOT A BLANKET UPDATE. type 23 is "other" — a catch-all, so it must be read row by row, not
swept. `documents` id 1412 is type 23 and is a Phase I Environmental Site Assessment appendix
(2190 Shattuck), NOT a tabulation form: no r2_url, no page count, uploaded by hand. It is
excluded by name, and the exclusion is asserted rather than assumed.

Each row promoted must independently satisfy ALL of:
  * document_type_id = 23
  * r2_url under affordability_forms/   (where the harvester puts these)
  * title matching tabulation / 1.E
  * exactly 1 page                      (a 1.E is a one-page form)

GATED. Preview by default; --write is transactional with per-row rowcount==1 and
verify-or-rollback. Snapshot before --write.
"""
import argparse, re, sqlite3, sys

DB = "databases/berkeley_housing_v2.db"
TABULATION, OTHER = 25, 23
EXCLUDE = {1412}          # Phase I ESA appendix — type 23, but not a tabulation form


def candidates(conn):
    rows = conn.execute(
        "SELECT id, project_id, title, page_count, COALESCE(r2_url,'') "
        "FROM documents WHERE document_type_id=? ORDER BY project_id", (OTHER,)).fetchall()
    ok, skip = [], []
    for r in rows:
        i, pid, title, pages, url = r
        why = []
        if i in EXCLUDE:                              why.append("explicitly excluded")
        if "affordability_forms/" not in url:         why.append("not under affordability_forms/")
        if not re.search(r"tabulation|1\.E\b", title, re.I): why.append("title is not a tabulation form")
        if pages != 1:                                why.append(f"page_count={pages}, expected 1")
        (skip if why else ok).append((r, why))
    return ok, skip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    conn = sqlite3.connect(a.db)
    before = conn.execute("SELECT COUNT(*) FROM documents WHERE document_type_id=?",
                          (TABULATION,)).fetchone()[0]
    ok, skip = candidates(conn)

    print(f"type-{TABULATION} (tabulation_form) rows before: {before}\n" + "=" * 78)
    print(f"PROMOTE {len(ok)}:")
    for (i, pid, title, pages, url), _ in ok:
        print(f"  id {i:<5} proj{pid:<5} {title[:62]}")
    print(f"\nLEAVE ALONE {len(skip)}:")
    for (i, pid, title, pages, url), why in skip:
        print(f"  id {i:<5} proj{pid:<5} {title[:52]}\n        reason: {'; '.join(why)}")
    print("=" * 78)
    print(f"after = {before} + {len(ok)} = {before + len(ok)}")

    if not a.write:
        print("\nPREVIEW ONLY — no write. Snapshot, then re-run with --write.")
        return 0
    try:
        conn.execute("BEGIN")
        n = 0
        for (i, *_), _ in ok:
            cur = conn.execute(
                "UPDATE documents SET document_type_id=?, updated_at=datetime('now'),"
                " notes=COALESCE(notes||' ','')||'Re-typed 23->25 on 2026-09-02: a 1.E tabulation"
                " form filed under other.' WHERE id=? AND document_type_id=?",
                (TABULATION, i, OTHER))
            assert cur.rowcount == 1, f"rowcount {cur.rowcount} for id {i}"
            n += 1
        after = conn.execute("SELECT COUNT(*) FROM documents WHERE document_type_id=?",
                             (TABULATION,)).fetchone()[0]
        assert after == before + n, f"count {after} != {before}+{n}"
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE id=1412 AND document_type_id=?",
                            (OTHER,)).fetchone()[0] == 1, "the ESA appendix must stay type 23"
        conn.commit()
        print(f"\nCOMMITTED {n} row(s). type-{TABULATION}: {before} -> {after}")
    except Exception as e:
        conn.rollback()
        print(f"\nROLLED BACK — {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
