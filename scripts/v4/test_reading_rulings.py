"""Proves apply_reading_rulings BOTH ways, on an in-memory DB.

Run: python -m scripts.v4.test_reading_rulings   (from the repo root)

A ruling overrules a model reading on every classified event of a permit, but only when the current reading is
the one the ruling names; otherwise, or when the permit is also in grounded_counts, or when the ledger drifts from
its pinned size, it must HALT with the DB unchanged.
"""
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.v4 import reading_rulings as RR  # noqa: E402
from scripts.v4 import stage_methods as SM  # noqa: E402

P = 'B-TEST-1'
HEADER = 'source_record_key,expected_role,expected_units,ruled_role,ruled_units,evidence,source_ref,adjudicated,note\n'


def build(role='new_unit', units=5):
    con = sqlite3.connect(':memory:')
    con.executescript("""
      CREATE TABLE events (event_id INTEGER PRIMARY KEY, source_record_key TEXT, event_type_code TEXT);
      CREATE TABLE event_classifications (event_id INTEGER PRIMARY KEY, housing_role TEXT, is_master INT,
                           net_units INT, basis TEXT, basis_note TEXT);""")
    for eid, et in ((1, 'permit_issued'), (2, 'permit_finaled'), (3, 'inspection')):
        con.execute('INSERT INTO events VALUES (?,?,?)', (eid, P, et))
    con.execute("INSERT INTO event_classifications VALUES (1,?,1,?,'model','model reading')", (role, units))
    con.execute("INSERT INTO event_classifications VALUES (2,?,1,?,'model','model reading')", (role, units))
    con.execute("INSERT INTO event_classifications VALUES (3,?,1,?,'model','inherited by the inspection')", (role, units))
    con.commit()
    return con


def state(con):
    return con.execute('SELECT event_id, housing_role, is_master, net_units FROM event_classifications ORDER BY 1').fetchall()


def files(tmp, grounded_has_permit=False, expected='new_unit,5'):
    rul = os.path.join(tmp, 'rulings.csv')
    open(rul, 'w').write(HEADER + f'{P},{expected},alteration,0,evidence,ref,2026-09-30,note\n')
    gc = os.path.join(tmp, 'grounded.csv')
    open(gc, 'w').write('source_record_key,grounded_count\n' + (f'{P},5\n' if grounded_has_permit else 'OTHER,1\n'))
    return rul, gc


def halts(con, rul, gc, why):
    before = state(con)
    try:
        RR.apply_reading_rulings(con, rul, gc)
    except AssertionError as e:
        assert why in str(e), f'halted for the wrong reason: {e}'
        assert state(con) == before, 'a halted run changed the DB'
        return
    raise AssertionError(f'expected a HALT ({why}) but the ruling ran')


def main():
    SM._calibration = lambda name: {'reading_rulings': {'rows': 1, 'permits': 1}}
    with tempfile.TemporaryDirectory() as tmp:
        # 1. The reading matches: issued, finaled AND the inspection (which inherits the label and a master flag)
        #    all become alteration/0 with no master; a re-run is a no-op.
        con = build(); rul, gc = files(tmp)
        out = RR.apply_reading_rulings(con, rul, gc)
        assert out['events_changed'] == 3, out
        assert state(con) == [(1, 'alteration', 0, 0), (2, 'alteration', 0, 0), (3, 'alteration', 0, 0)], state(con)
        assert all('reading_ruling' in n for (n,) in con.execute('SELECT basis_note FROM event_classifications')), 'a changed row lacks its note'
        assert RR.apply_reading_rulings(con, rul, gc)['events_changed'] == 0

        # 2. The current reading is not the one the ruling names -> HALT, unchanged.
        halts(build(units=4), rul, gc, 'expected the reading')

        # 3. The permit is also in grounded_counts -> HALT, unchanged.
        rul2, gc2 = files(tmp, grounded_has_permit=True)
        halts(build(), rul2, gc2, 'one permit, one ledger')

        # 4. The ledger drifts from its pinned size -> HALT, unchanged.
        SM._calibration = lambda name: {'reading_rulings': {'rows': 2, 'permits': 2}}
        halts(build(), rul, gc, 'calibration drift')
    print('test_reading_rulings: PASS (overrules on every event when the reading matches; halts otherwise, DB unchanged)')


if __name__ == '__main__':
    main()
