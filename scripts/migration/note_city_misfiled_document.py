#!/usr/bin/env python3
"""note_city_misfiled_document.py — record a CITY filing error without contradicting it (2026-09-07).

THE FINDING: `2022_01_13_RESUB_Use Permit Resubmission Full Arch Set_2065 Kittredge.pdf` is
2065 Kittredge's architecture set, and the City published it on the Accela record for
2018 BLAKE ST. Verified in the primary source, not inferred:

    data/raw/accela_status/2018_BLAKE_St.txt line 169
    2022_01_13_RESUB_Use Permit Resubmission Full Arch Set_2065 Kittredge.pdf | 19.16 MB | 01/24/2022

sitting between 2018 Blake's own 2022-01-15 Plan Check 2 Drawing Set and its 2022-02-22
Incomplete letter. Our ingest recorded it faithfully; the harvester then named the R2 object
proj148_2018-blake-st_2022-01-13.pdf after the record it was found on.

WHY project_id IS NOT CHANGED. Re-pointing it to proj180 would make our database assert
something the primary source does not say, and would erase a citable fact about the City's
own records — the thing CLAUDE.md rule 1 and the append-only evidence layer exist to prevent.
Instead the discrepancy is RECORDED, following the ADR-003 pattern: keep the source-faithful
value, add the derived one beside it, never mutate the faithful one.

WHAT IS OURS TO FIX: the same City file is in `documents` TWICE, typed inconsistently by two
ingests — id 126 as `application` from the status scrape, id 2298 as `plan_set` from the
August harvest. Same filename, same date, and the scrape's "19.16 MB" matches 2298's
file_size_bytes of 20,091,416 exactly. That duplicate is our error, so 126 is soft-retired
into 2298 via a new documents.merged_into_id — retired, never deleted, because documents are
EVIDENCE and evidence is append-only.

Usage: .venv/bin/python scripts/migration/note_city_misfiled_document.py [--commit]
"""
import sqlite3, shutil, sys, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DB = BASE / 'databases' / 'berkeley_housing_v2.db'
COMMIT = '--commit' in sys.argv

KEEP, RETIRE = 2298, 126
SCRAPE = 'data/raw/accela_status/2018_BLAKE_St.txt line 169'

NOTE_KEEP = (
    "filename: 2022_01_13_RESUB_Use Permit Resubmission Full Arch Set_2065 Kittredge.pdf\n"
    "CITY FILING ERROR, recorded 2026-09-07, NOT corrected here. This document's CONTENT is "
    "the architecture set for 2065 KITTREDGE ST (project 180). The City of Berkeley published "
    "it on the Accela record for 2018 Blake St (project 148), between that project's own "
    f"2022-01-15 Plan Check 2 Drawing Set and its 2022-02-22 Incomplete letter — see {SCRAPE}. "
    "project_id therefore stays 148, which is where the primary source puts it; changing it "
    "would make this database assert something the City's record does not say. The R2 object "
    "key (proj148_2018-blake-st_2022-01-13.pdf) reflects the same provenance. Anyone studying "
    "2065 Kittredge should read this document; anyone auditing the City's records should note "
    "that it was filed on the wrong project."
)
NOTE_RETIRE = (
    "filename: 2022_01_13_RESUB_Use Permit Resubmission Full Arch Set_2065 Kittredge.pdf\n"
    "Size: 19.16 MB\n"
    f"DUPLICATE of document {KEEP}, retired 2026-09-07. Same City file reached us twice: this "
    "row from the Accela status scrape (typed 'application'), and 2298 from the August 2026 "
    "harvest (typed 'plan_set'). Identity confirmed by filename, date, and size — the scrape's "
    "19.16 MB equals 2298's file_size_bytes of 20,091,416. 2298 survives because it carries the "
    "R2 URL, sha256, page count and published_date that this row lacks. Retired, not deleted: "
    "documents are evidence and the evidence layer is append-only."
)


def main():
    con = sqlite3.connect(DB)
    con.execute('PRAGMA foreign_keys = ON')
    for did in (KEEP, RETIRE):
        r = con.execute('SELECT id, project_id, title, file_size_bytes FROM documents WHERE id=?',
                        (did,)).fetchone()
        print(f'  doc{r[0]:<5} project={r[1]}  size={r[3]}  {r[2][:56]}')
    print(f'\n  -> doc{RETIRE} retired into doc{KEEP}; both keep project_id=148 (the City\'s filing)')
    print(f'  -> both gain a note recording the City error and the duplication')

    if not COMMIT:
        print('\nPREVIEW ONLY — re-run with --commit to apply.')
        con.close(); return

    stamp = datetime.date.today().isoformat()
    snap = DB.parent / f'keep_snapshot_{stamp}_pre-doc-misfile-note.db'
    shutil.copy2(DB, snap)
    assert snap.stat().st_size == DB.stat().st_size, 'snapshot size mismatch'
    chk = sqlite3.connect(f'file:{snap}?mode=ro', uri=True).execute('PRAGMA integrity_check').fetchone()[0]
    assert chk == 'ok', f'snapshot integrity_check: {chk}'
    print(f'\nsnapshot {snap.name}  {snap.stat().st_size:,} bytes  integrity_check={chk}')

    before = con.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
    try:
        con.execute('BEGIN')
        if 'merged_into_id' not in [r[1] for r in con.execute('PRAGMA table_info(documents)')]:
            con.execute('ALTER TABLE documents ADD COLUMN merged_into_id INTEGER '
                        'REFERENCES documents(id)')
            print('added documents.merged_into_id')
        assert con.execute('UPDATE documents SET notes=? WHERE id=?', (NOTE_KEEP, KEEP)).rowcount == 1
        assert con.execute('UPDATE documents SET notes=?, merged_into_id=? WHERE id=?',
                           (NOTE_RETIRE, KEEP, RETIRE)).rowcount == 1

        # verify inside the transaction
        after = con.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
        assert after == before == 2255, f'document count moved: {before} -> {after}'
        pid = con.execute('SELECT project_id FROM documents WHERE id IN (?,?)', (KEEP, RETIRE)).fetchall()
        assert all(p[0] == 148 for p in pid), f'project_id changed: {pid} — it must not'
        retired = con.execute('SELECT COUNT(*) FROM documents WHERE merged_into_id IS NOT NULL').fetchone()[0]
        assert retired == 1, f'{retired} retired rows, expected 1'
        assert con.execute('SELECT merged_into_id FROM documents WHERE id=?', (KEEP,)).fetchone()[0] is None
        con.commit()
        print('COMMITTED — 1 document retired, 2 notes written, 0 project_id changes')
    except Exception as e:
        con.rollback(); print(f'ROLLED BACK — {e}'); raise
    finally:
        con.close()

    fresh = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    print('\nfingerprint (fresh connection):')
    print('  integrity_check:', fresh.execute('PRAGMA integrity_check').fetchone()[0])
    print('  documents:', fresh.execute('SELECT COUNT(*) FROM documents').fetchone()[0],
          '| retired:', fresh.execute('SELECT COUNT(*) FROM documents WHERE merged_into_id IS NOT NULL').fetchone()[0])
    for r in fresh.execute('SELECT id, project_id, merged_into_id FROM documents WHERE id IN (?,?)', (KEEP, RETIRE)):
        print('   doc', r)


if __name__ == '__main__':
    main()
