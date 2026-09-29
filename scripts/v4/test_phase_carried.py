"""Proves apply_grounded_counts' phase_carried demotion BOTH ways, on an in-memory DB.

Run: python -m scripts.v4.test_phase_carried   (from the repo root)

A phase permit may be demoted to 0 only when the carrier permit is a ledger-grounded counted master with
the same count AND the carrier's own permit text names the demoted permit. Anything less must HALT and
leave the DB unchanged (count-once, never a free-standing zero).
"""
import json, os, sqlite3, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.v4 import stage_methods as M

HEADER = 'source_record_key,grounded_count,convention,source_document,source_ref,corroboration,adjudicated,note,carried_by\n'
CARRIER = 'C-2'
PHASE1 = 'P-1'


def build(carrier_desc, carrier_role='new_unit', carrier_note='model | grounded_counts (plan set)'):
    con = sqlite3.connect(':memory:')
    con.executescript("""
      CREATE TABLE events (event_id INTEGER PRIMARY KEY, source_record_key TEXT, event_type_code TEXT,
                           raw_description TEXT, raw_payload TEXT);
      CREATE TABLE event_classifications (event_id INTEGER PRIMARY KEY, housing_role TEXT, is_master INT,
                           net_units INT, basis TEXT, basis_note TEXT);""")
    con.execute("INSERT INTO events VALUES (1,?,'permit_finaled',?, '{}')", (CARRIER, carrier_desc))
    con.execute("INSERT INTO events VALUES (2,?,'permit_finaled','Phase I - South Building', '{}')", (PHASE1,))
    con.execute("INSERT INTO event_classifications VALUES (1,?,1,10,'evidentiary',?)", (carrier_role, carrier_note))
    con.execute("INSERT INTO event_classifications VALUES (2,'new_unit',1,10,'model','model reading')")
    con.commit()
    return con


def ledger(tmp):
    path = os.path.join(tmp, 'grounded_counts.csv')
    with open(path, 'w') as f:
        f.write(HEADER)
        f.write(f'{CARRIER},10,dwelling,plan set,ref,corr,2026-09-29,note,\n')
        f.write(f'{PHASE1},0,phase_carried,doc,ref,corr,2026-09-29,note,{CARRIER}\n')
    held = os.path.join(tmp, 'held.json')
    json.dump({'held_147': []}, open(held, 'w'))
    return path, held


def state(con, p):
    return con.execute("SELECT housing_role, is_master, net_units FROM events e JOIN event_classifications c "
                       "USING(event_id) WHERE source_record_key=?", (p,)).fetchone()


def halts(con, csv_path, held, why):
    before = state(con, PHASE1)
    try:
        M.apply_grounded_counts(con, csv_path, held)
    except AssertionError as e:
        assert why in str(e), f'halted for the wrong reason: {e}'
        assert state(con, PHASE1) == before, 'a halted run changed the DB'
        return
    raise AssertionError(f'expected a HALT ({why}) but the demotion ran')


def main():
    M._calibration = lambda name: {'grounded_counts': {'rows': 2, 'units': 10}}
    with tempfile.TemporaryDirectory() as tmp:
        csv_path, held = ledger(tmp)

        # 1. Carrier grounded, counted, and names the phase permit -> demoted; a re-run is a no-op.
        con = build(f'Phase II of South Building. Phase I under Permit number {PHASE1}')
        out = M.apply_grounded_counts(con, csv_path, held)
        assert out['demoted'] == 1 and state(con, PHASE1) == ('subsidiary', 0, 0), out
        assert state(con, CARRIER) == ('new_unit', 1, 10)
        assert M.apply_grounded_counts(con, csv_path, held)['demoted'] == 0

        # 2. Carrier text does not name the phase permit -> HALT, nothing changes.
        halts(build('Phase II of South Building'), csv_path, held, 'does not name')

        # 3. Carrier not in the ledger -> HALT, nothing changes.
        lone = os.path.join(tmp, 'lone.csv')
        with open(lone, 'w') as f:
            f.write(HEADER + f'{PHASE1},0,phase_carried,doc,ref,corr,2026-09-29,note,{CARRIER}\n')
        M._calibration = lambda name: {'grounded_counts': {'rows': 1, 'units': 0}}
        halts(build(f'Phase I under {PHASE1}'), lone, held, 'not a ledger-grounded row')
        M._calibration = lambda name: {'grounded_counts': {'rows': 2, 'units': 10}}

        # 4. Phase permit's count differs from the carrier's -> not the same units: HALT, nothing changes.
        con = build(f'Phase I under {PHASE1}')
        con.execute("UPDATE event_classifications SET net_units=12 WHERE event_id=2"); con.commit()
        halts(con, csv_path, held, 'expected a counted master carrying')
    print('test_phase_carried: PASS (demotes with a grounded carrier; halts without one, DB unchanged)')


if __name__ == '__main__':
    main()
