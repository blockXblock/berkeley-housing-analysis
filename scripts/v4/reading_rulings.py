"""reading_rulings.py — John's rulings that OVERRULE a model reading of a permit (approved 2026-09-30).

The housing role of every permit comes from stored model readings (housing_rules.permit_effect). A reading can be
wrong in a way that grounded_counts cannot fix: grounded_counts only RAISES a count (or carries a phase's units to
its completing permit). This ledger lowers one, with evidence: e.g. B2024-05916, "Renew old permit B2017-02937",
which Accela lists as an Electrical Permit, but which the model read as 5 new units from the permit's unit field.

Each row of corrections/v4/reading_rulings.csv names the reading it overrules (expected_role / expected_units) and
the ruling (ruled_role / ruled_units). The ruling applies to EVERY classified event of the permit (submitted, issued,
finaled, and inspections too, which inherit the permit's label), so building-permit and completion counts move
together and no event keeps a master flag the structures fold would still count.

Guards (a wrong ruling must halt, never write):
  * the permit's current reading must equal expected_*, or already carry this ruling (an idempotent re-run);
  * a ruled permit must not also appear in grounded_counts.csv (two ledgers must never fight over one permit);
  * rows and permits are pinned in calibration_checksums.json["reading_rulings"].
Runs in the chain right after stage_methods.apply_grounded_counts (JN-F). Refuses nothing about the target DB
itself; callers open it through stage_methods.connect_guarded.
"""
import os

import pandas as pd

try:
    from scripts.v4 import stage_methods as SM      # repo root on sys.path (tests, scripts)
except ImportError:
    import stage_methods as SM                     # scripts/v4 on sys.path (the JN notebooks)

RULINGS = os.path.join(SM.CORR, 'reading_rulings.csv')
TAG = 'reading_ruling'


def _events(con, permit):
    return con.execute(
        "SELECT e.event_id, e.event_type_code, c.housing_role, c.is_master, c.net_units, c.basis_note "
        "FROM events e JOIN event_classifications c ON c.event_id = e.event_id WHERE e.source_record_key = ?",
        (permit,)).fetchall()


def apply_reading_rulings(con, csv_path=RULINGS, grounded_path=os.path.join(SM.CORR, 'grounded_counts.csv')):
    rows = pd.read_csv(csv_path, dtype=str).fillna('')
    cks = SM._calibration('calibration_checksums.json')['reading_rulings']
    assert len(rows) == cks['rows'] and rows.source_record_key.nunique() == cks['permits'], \
        f'reading_rulings calibration drift: {len(rows)}/{rows.source_record_key.nunique()} vs pinned {cks["rows"]}/{cks["permits"]}'
    grounded = set(pd.read_csv(grounded_path, dtype=str).source_record_key)
    changed = 0
    try:
        for r in rows.itertuples():
            p = r.source_record_key
            assert p not in grounded, f'reading_ruling {p}: also in grounded_counts.csv; one permit, one ledger'
            ev = _events(con, p)
            assert ev, f'reading_ruling {p}: no classified events'
            exp_units, ruled_units = int(r.expected_units or 0), int(r.ruled_units or 0)
            for eid, etype, role, master, nu, note in ev:
                if TAG in (note or ''):
                    assert (role, int(nu or 0)) == (r.ruled_role, ruled_units), \
                        f'reading_ruling {p} {etype}: carries the ruling note but reads {role}/{nu}'
                    continue                                          # idempotent re-run
                if etype not in ('permit_issued', 'permit_finaled', 'permit_submitted'):
                    # inspections and other events inherit the permit's label; they must not keep a master flag the
                    # structures fold would still see (the 2026-09-30 ADU lesson). No expected-reading check here.
                    if (role, int(master or 0), int(nu or 0)) == (r.ruled_role, 0, ruled_units):
                        continue
                    rc = con.execute(
                        "UPDATE event_classifications SET housing_role=?, is_master=0, net_units=?, basis='evidentiary', "
                        "basis_note=COALESCE(basis_note,'')||' | " + TAG + " ('||?||'; src '||?||')' WHERE event_id=?",
                        (r.ruled_role, ruled_units, str(r.adjudicated), str(r.source_ref)[:120], eid)).rowcount
                    assert rc == 1, f'reading_ruling {p} {etype}: rowcount={rc}'
                    changed += rc
                    continue
                assert (role, int(nu or 0)) == (r.expected_role, exp_units), (
                    f'reading_ruling {p} {etype}: expected the reading {r.expected_role}/{exp_units} to overrule, '
                    f'found {role}/{nu}; the evidence has changed, re-adjudicate')
                rc = con.execute(
                    "UPDATE event_classifications SET housing_role=?, is_master=0, net_units=?, basis='evidentiary', "
                    "basis_note=COALESCE(basis_note,'')||' | " + TAG + " ('||?||'; src '||?||')' WHERE event_id=?",
                    (r.ruled_role, ruled_units, str(r.adjudicated), str(r.source_ref)[:120], eid)).rowcount
                assert rc == 1, f'reading_ruling {p} {etype}: rowcount={rc}'
                changed += rc
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {'rows': len(rows), 'events_changed': changed}
