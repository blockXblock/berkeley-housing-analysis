#!/usr/bin/env python3
"""merge_duplicate_organizations.py — collapse duplicate `organizations` rows (2026-09-07).

WHY: two normalization conventions collided in `organizations.normalized_name` — 52 rows
snake_lower (the curated set) and 837 UPPER-WITH-SPACES (the tabulation-form / business-
licence import). They never deduped against each other, so `Trachtenberg Architects`
existed TWICE, and the firm behind most of Berkeley's large housing was split six ways.
Until this ran, the players network showed 13 architects where there are far fewer.

THE FIRM SUCCESSION (primary source: the firm's own site, sdtarch.com/profile/people/,
checked 2026-09-07): established 1991 by David Trachtenberg as Trachtenberg Architects;
now Stackhouse De la Peña Trachtenberg Architects (SDT) — Isaiah Stackhouse (Principal,
Design Director), Mauricio De la Peña (Principal, Managing Director, joined 2013),
David Trachtenberg (Founder). The site's own logo alt-text still reads "Trachtenberg
Architects". Same firm, renamed; SDT survives as the CURRENT name and the former name is
recorded in notes so historical attribution stays honest.

METHOD (mirrors the projects merge discipline in CLAUDE.md):
  - soft-retire via a new `organizations.merged_into_id`, so every absorbed row survives
    and the merge is reversible;
  - re-point `project_participants.organization_id` (and `people.organization_id`) to the
    survivor BEFORE retiring;
  - a person's name carried into an org name becomes a `people` row attached to the firm
    and the participant row gains `person_id` — the person is not erased, it is filed;
  - verified inside the transaction, rolled back on any failure.

David Trachtenberg IS the architect and the firm's founder — confirmed by the firm's own
People page and by John, who corrected an earlier account. The brother is ROBERT
Trachtenberg, a landscape designer trading as Garden Architecture (931 Pardee St; both
he and the firm hold Berkeley business licences, and he did the landscape on Backroads
and Comal where this firm was architect). Robert has no role in v2 and is NOT added here
— he belongs to the landscape trade, not to this firm.

NOT merged, deliberately: BILL SCHRADER (2 applicant links), MGH Management, Laconia Dev
LLC. Personal or holding names on professional roles with no evidenced firm behind them;
listed for a human, never guessed.

Usage: python3 scripts/migration/merge_duplicate_organizations.py [--commit]
Default is a read-only preview.
"""
import sqlite3, shutil, sys, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DB = BASE / 'databases' / 'berkeley_housing_v2.db'
COMMIT = '--commit' in sys.argv

SDT_NAME = 'Stackhouse De la Peña Trachtenberg Architects'
SDT_NOTE = ('Founded 1991 as Trachtenberg Architects by David Trachtenberg; renamed '
            'Stackhouse De la Peña Trachtenberg Architects (SDT). Principals: Isaiah '
            'Stackhouse (design), Mauricio De la Peña (managing, joined 2013), David '
            'Trachtenberg (founder). Source: sdtarch.com/profile/people/, read 2026-09-07. '
            'Projects designed before the rename were filed as "Trachtenberg Architects".')

# survivor_id -> (absorbed ids, [(absorbed_id, person full_name) ...])
MERGES = {
    24: ([23, 892, 891, 871, 876, 886],
         [(871, 'Isaiah Stackhouse'), (876, 'Isaiah Stackhouse'), (886, 'David Trachtenberg')]),
    22: ([874, 873, 875, 877, 879, 881, 883],
         [(873, 'Erik Waterman'), (875, 'Brian Carter'), (877, 'Jason Andre'),
          (879, 'Hannah Micallef'), (881, 'Jason Andre'), (883, 'Till Houtermans')]),
    14: ([884], []),
    20: ([888], []),
    33: ([870], []),
    53: ([882], []),
}
RENAME = {24: (SDT_NAME, SDT_NOTE)}


def main():
    con = sqlite3.connect(DB)
    con.execute('PRAGMA foreign_keys = ON')
    before = {}
    for keep, (absorbed, _) in MERGES.items():
        ids = [keep] + absorbed
        q = ','.join('?' * len(ids))
        before[keep] = con.execute(
            f'SELECT COUNT(*) FROM project_participants WHERE organization_id IN ({q})', ids).fetchone()[0]
        name = con.execute('SELECT name FROM organizations WHERE id=?', (keep,)).fetchone()[0]
        print(f'  keep id{keep:<4} {name[:42]:44s} absorbs {len(absorbed):2d} row(s), '
              f'{before[keep]:2d} link(s) after merge')

    if not COMMIT:
        print('\nPREVIEW ONLY — re-run with --commit to apply.')
        con.close()
        return

    stamp = datetime.date.today().isoformat()
    snap = DB.parent / f'keep_snapshot_{stamp}_pre-org-merge.db'
    shutil.copy2(DB, snap)
    assert snap.stat().st_size == DB.stat().st_size, 'snapshot size mismatch'
    chk = sqlite3.connect(f'file:{snap}?mode=ro', uri=True).execute('PRAGMA integrity_check').fetchone()[0]
    assert chk == 'ok', f'snapshot integrity_check: {chk}'
    print(f'\nsnapshot {snap.name}  {snap.stat().st_size:,} bytes  integrity_check={chk}')

    try:
        con.execute('BEGIN')
        cols = [r[1] for r in con.execute('PRAGMA table_info(organizations)')]
        if 'merged_into_id' not in cols:
            con.execute('ALTER TABLE organizations ADD COLUMN merged_into_id INTEGER '
                        'REFERENCES organizations(id)')
            print('added organizations.merged_into_id')

        moved = people_made = 0
        for keep, (absorbed, persons) in MERGES.items():
            for oid, full in persons:
                row = con.execute('SELECT id FROM people WHERE organization_id=? AND full_name=?',
                                  (keep, full)).fetchone()
                if row:
                    pid = row[0]
                else:
                    cur = con.execute(
                        'INSERT INTO people (organization_id, full_name, notes) VALUES (?,?,?)',
                        (keep, full, f'name was carried inside organizations.name (was org id {oid}); '
                                     f'filed as a person of the firm 2026-09-07'))
                    pid, people_made = cur.lastrowid, people_made + 1
                con.execute('UPDATE project_participants SET person_id=? '
                            'WHERE organization_id=? AND person_id IS NULL', (pid, oid))
            for oid in absorbed:
                cur = con.execute('UPDATE project_participants SET organization_id=? '
                                  'WHERE organization_id=?', (keep, oid))
                moved += cur.rowcount
                con.execute('UPDATE people SET organization_id=? WHERE organization_id=?', (keep, oid))
                con.execute('UPDATE organizations SET merged_into_id=? WHERE id=?', (keep, oid))
        for keep, (name, note) in RENAME.items():
            assert con.execute('UPDATE organizations SET name=?, notes=? WHERE id=?',
                               (name, note, keep)).rowcount == 1

        # ---- verify inside the transaction ----
        for keep, (absorbed, _) in MERGES.items():
            got = con.execute('SELECT COUNT(*) FROM project_participants WHERE organization_id=?',
                              (keep,)).fetchone()[0]
            assert got == before[keep], f'id{keep}: {got} links, expected {before[keep]}'
        orphan = con.execute('''SELECT COUNT(*) FROM project_participants pp
            JOIN organizations o ON o.id = pp.organization_id
            WHERE o.merged_into_id IS NOT NULL''').fetchone()[0]
        assert orphan == 0, f'{orphan} participant row(s) still point at a retired organization'
        dupes = con.execute('''SELECT COUNT(*) FROM (SELECT project_id, role_type_id, organization_id
            FROM project_participants GROUP BY 1,2,3 HAVING COUNT(*) > 1)''').fetchone()[0]
        assert dupes == 0, f'{dupes} duplicate (project, role, org) row(s) created'
        total = con.execute('SELECT COUNT(*) FROM project_participants').fetchone()[0]
        assert total == 992, f'participant rows changed: {total} (expected 992 — links move, never vanish)'
        con.commit()
        print(f'COMMITTED — {moved} participant link(s) re-pointed, {people_made} person row(s) created')
    except Exception as e:
        con.rollback()
        print(f'ROLLED BACK — {e}')
        raise
    finally:
        con.close()

    fresh = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    print('\nfingerprint (fresh connection):')
    print('  integrity_check:', fresh.execute('PRAGMA integrity_check').fetchone()[0])
    print('  organizations:', fresh.execute('SELECT COUNT(*) FROM organizations').fetchone()[0],
          '| retired:', fresh.execute('SELECT COUNT(*) FROM organizations WHERE merged_into_id IS NOT NULL').fetchone()[0])
    print('  participants:', fresh.execute('SELECT COUNT(*) FROM project_participants').fetchone()[0])
    for name, n in fresh.execute('''SELECT o.name, COUNT(*) FROM project_participants pp
        JOIN organizations o ON o.id = pp.organization_id
        JOIN vocabulary_role_types rt ON rt.id = pp.role_type_id
        WHERE rt.code LIKE 'architect%' OR rt.code = 'applicant'
        GROUP BY 1 ORDER BY 2 DESC LIMIT 6'''):
        print(f'    {name[:50]:52s} {n}')


if __name__ == '__main__':
    main()
