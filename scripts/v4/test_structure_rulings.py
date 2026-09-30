"""Proves build_structures' building-merge rulings BOTH ways, with no database.

Run: python -m scripts.v4.test_structure_rulings   (from the repo root)

An approved merge_masters row joins masters the text never joins; a row naming a permit that is not a master HALTS
(a ruling never goes stale quietly); an unapproved row changes nothing.
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
import build_structures as bs
from housing_rules.building_label import extract


def permits():
    def p(desc, master, units):
        return dict(events=[], description=desc, apn=None, address=None, units=None, is_master=master,
                    net_units=units, cls_source='test', label=extract(desc), site=('block', '056-1945'))
    return {'B2019-02213': p('Main Level - remodel entry, living room', 1, 1),
            'B2025-03015': p('To final B2019-02213. Remodel home and add ADU.', 1, 1),
            'B2020-00001': p('New detached ADU', 1, 1)}


def run(rows):
    bs.load_structure_rulings = lambda: [r for r in rows if r['status'] == 'approved']
    return bs.fold(permits())


def main():
    row = dict(ruling_id='S1', action='merge_masters', master_permits='B2019-02213;B2025-03015', status='approved')
    groups, _, merges, _, _ = run([row])
    assert len(groups) == 2 and sorted(groups[bs._root_of(groups, 'B2019-02213')]) == ['B2019-02213', 'B2025-03015']
    assert any(m[0] == ('ruling', 'S1') for m in merges)

    groups, _, _, _, _ = run([dict(row, status='proposed')])
    assert len(groups) == 3, 'an unapproved ruling must change nothing'

    try:
        run([dict(row, master_permits='B2019-02213;B9999-00000')])
        raise SystemExit('expected a HALT on a ruling naming a non-master')
    except AssertionError as e:
        assert 'not master permits now' in str(e), e
    print('test_structure_rulings: PASS (approved rows merge; unapproved do nothing; a stale ruling halts)')


if __name__ == '__main__':
    main()
