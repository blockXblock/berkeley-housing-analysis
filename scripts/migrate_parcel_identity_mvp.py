#!/usr/bin/env python3
"""
migrate_parcel_identity_mvp.py — gated MVP migration for ADR-003 (parcel-identity model).

Applies schema/parcel_apn_lineage_schema_MVP.sql to v2 + backfills apn_raw/apn_normalized
(via the SINGLE housing_rules.to_canonical_apn, authority-parameterized + ALPHANUMERIC-aware)
+ bootstraps parcel_lineage candidates. NEVER mutates apn_raw (source-faithful preserved).

Enforcement is the assessing county's REGISTERED pattern (Alameda = ^[0-9A-Z]{12,14}$,
UPPERCASE ALPHANUMERIC — 25 real Alameda APNs carry a book letter 48A/48H; digits-only
would wrongly reject them). apn_normalized is TEXT (alphanumeric-safe).

  --preview   apply to a THROWAWAY COPY of the live DB, verify, discard. Live DB untouched.
  --write     apply to the live DB (the gated write; snapshot first).

Trigger tests always run in a SAVEPOINT that rolls back (test rows never persist).
"""
import sqlite3, argparse, shutil, sys, json, os
from pathlib import Path
sys.path.insert(0, 'scripts')
from housing_rules import to_canonical_apn  # the ONE canon function (alphanumeric, per-county)

LIVE = 'databases/berkeley_housing_v2.db'
SCHEMA = 'schema/parcel_apn_lineage_schema_MVP.sql'
COUNTY = 'Alameda'


def apply_schema(con):
    existing = [c[1] for c in con.execute("PRAGMA table_info(parcels)")]
    sql = open(SCHEMA).read()
    if 'apn_raw' in existing:                                  # re-run guard: skip the ALTERs
        sql = '\n'.join(l for l in sql.splitlines()
                        if not l.strip().upper().startswith('ALTER TABLE PARCELS ADD COLUMN'))
    con.executescript(sql)


def backfill(con):
    cur = con.cursor()
    n = none = 0
    for pid, apn in cur.execute("SELECT id, apn FROM parcels").fetchall():
        norm = to_canonical_apn(apn, COUNTY)                  # apn_raw preserved EXACTLY; normalized derived
        cur.execute("UPDATE parcels SET apn_raw=?, apn_normalized=?, assessing_county=? WHERE id=?",
                    (apn, norm, COUNTY, pid))
        n += 1
        none += (norm is None and apn is not None)
    return n, none


def _ins_lineage(cur, **k):
    cols = ('assessing_county', 'parent_parcel_id', 'child_parcel_id', 'parent_apn_raw',
            'child_apn_raw', 'parent_apn_normalized', 'child_apn_normalized', 'event_type',
            'status', 'confidence', 'evidence', 'source_name', 'notes')
    cur.execute(f"INSERT INTO parcel_lineage({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                tuple(k.get(c) for c in cols))


def bootstrap_lineage(con):
    cur = con.cursor()
    added = 0
    # (a) 25 Phase-2 re-points -> candidate apn_renumber (identity continuous; new external APN)
    for pid, prior, cur_apn, ev, parcel_id in cur.execute("""
            SELECT pc.project_id, pc.prior_apn, pc.current_apn, pc.evidence, pk.id
            FROM parcel_crosswalk pc
            JOIN project_parcels pp ON pp.project_id=pc.project_id AND pp.is_primary=1
            JOIN parcels pk ON pk.id=pp.parcel_id WHERE pc.confidence='HIGH'""").fetchall():
        _ins_lineage(cur, assessing_county=COUNTY, parent_parcel_id=None, child_parcel_id=parcel_id,
                     parent_apn_raw=prior, child_apn_raw=cur_apn,
                     parent_apn_normalized=to_canonical_apn(prior, COUNTY),
                     child_apn_normalized=to_canonical_apn(cur_apn, COUNTY),
                     event_type='apn_renumber', status='candidate', confidence='inferred',
                     evidence=json.dumps({'phase2_4source': ev, 'note': 'renumber = same identity, new external APN'}),
                     source_name='parcel_crosswalk Phase 2', notes='bootstrap candidate — confirm vs recorded map')
        added += 1
    # (b) proj179 Logan Park N/S split -> 2 candidate condo_map children
    p179 = cur.execute("""SELECT pk.id, pk.apn FROM project_parcels pp JOIN parcels pk ON pk.id=pp.parcel_id
                          WHERE pp.project_id=179 AND pp.is_primary=1""").fetchone()
    if p179:
        for child_apn, bldg in [('55-1895-41', 'North Building (B2019-05574, finaled 2022-01-14)'),
                                ('55-1895-42', 'South Building (B2019-05575 / merged proj887, 69u)')]:
            _ins_lineage(cur, assessing_county=COUNTY, parent_parcel_id=p179[0], child_parcel_id=None,
                         parent_apn_raw=p179[1], child_apn_raw=child_apn,
                         parent_apn_normalized=to_canonical_apn(p179[1], COUNTY),
                         child_apn_normalized=to_canonical_apn(child_apn, COUNTY),
                         event_type='condo_map', status='candidate', confidence='inferred',
                         evidence=json.dumps({'entitlement': 'ZP2018-0135 237u Phase I South + Phase II North',
                                              'building': bldg}),
                         source_name='Logan Park permits',
                         notes='one 237u project across two parcels — confirm vs recorded condo map')
            added += 1
    # (c) Acheson umbrella proj178 -> candidate subdivision_map marker (needs recorded map)
    p178 = cur.execute("""SELECT pk.id, pk.apn FROM project_parcels pp JOIN parcels pk ON pk.id=pp.parcel_id
                          WHERE pp.project_id=178 AND pp.is_primary=1""").fetchone()
    if p178:
        _ins_lineage(cur, assessing_county=COUNTY, parent_parcel_id=p178[0], child_parcel_id=None,
                     parent_apn_raw=p178[1], child_apn_raw=None,
                     parent_apn_normalized=None, child_apn_normalized=None,
                     event_type='subdivision_map', status='candidate', confidence='manual_review',
                     evidence=json.dumps({'note': 'Acheson umbrella, 4 pre-split APNs in one cell; '
                                                  'children = 57-2046-8-x current parcels'}),
                     source_name='Acheson Commons',
                     notes='multi-parcel umbrella split — needs the recorded map + per-building mapping')
        added += 1
    return added


def trigger_tests(con):
    """Insert tests in a SAVEPOINT that always rolls back. Confirms the teeth bite (Alameda pattern)."""
    cur = con.cursor()
    city = cur.execute("SELECT id FROM cities LIMIT 1").fetchone()[0]
    cur.execute("SAVEPOINT t")
    seq = [0]

    def ins(apn_norm, county='Alameda'):
        seq[0] += 1                                            # unique legacy apn so tests hit the
        legacy = f'__test_{seq[0]}__'                          # NEW trigger/index, not legacy UNIQUE(city_id,apn)
        try:
            cur.execute("INSERT INTO parcels(city_id, apn, apn_raw, apn_normalized, assessing_county) "
                        "VALUES(?,?,?,?,?)", (city, legacy, 'test', apn_norm, county))
            return 'ACCEPTED'
        except sqlite3.IntegrityError as e:
            return f'REJECTED ({str(e)[:55]})'

    r = {  # Option-B forms: structure-preserving hyphenated canonical
        'alphanumeric_48A_accepted': ins('48A-7075-015-00'),  # real Alameda letter-APN (B) -> ACCEPT
        'subparcel_accepted': ins('057-2046-008-04'),         # 4-segment sub (B) -> ACCEPT
        'A_form_concat_rejected': ins('057204600100'),        # Option-A concat (no hyphens) -> REJECT
        'raw_hyphenated_rejected': ins('57-2046-1'),          # raw (wrong book/page widths) -> REJECT
        'lowercase_rejected': ins('48a-7075-015-00'),         # lowercase -> REJECT (out of char-class)
        'short_rejected': ins('059-2325-038'),                # missing sub segment / too short -> REJECT
    }
    # authority-scoped uniqueness: same normalized + same county -> 2nd rejected
    ins('088-8888-888-00', 'Alameda')
    r['dup_same_county_rejected'] = ins('088-8888-888-00', 'Alameda')
    cur.execute("ROLLBACK TO t"); cur.execute("RELEASE t")
    return r


def run(mode):
    target = LIVE
    if mode == 'preview':
        target = '/tmp/parcel_identity_preview.db'
        shutil.copy(LIVE, target)
    con = sqlite3.connect(target)
    con.execute("PRAGMA foreign_keys=ON")
    q = lambda s: con.execute(s).fetchone()[0]
    pre = {'703': q("SELECT COUNT(*) FROM v_projects_flat WHERE co_issued_date>'' AND co_issued_date<>'2024-01-01'"),
           'view': q("SELECT COUNT(*) FROM v_projects_flat"), 'parcels': q("SELECT COUNT(*) FROM parcels")}
    apply_schema(con)
    n, none = backfill(con)
    added = bootstrap_lineage(con)
    trg = trigger_tests(con)
    post = {'703': q("SELECT COUNT(*) FROM v_projects_flat WHERE co_issued_date>'' AND co_issued_date<>'2024-01-01'"),
            'view': q("SELECT COUNT(*) FROM v_projects_flat"), 'parcels': q("SELECT COUNT(*) FROM parcels")}
    out = {
        'mode': mode,
        'backfill': {'rows': n,
                     'apn_raw_preserved_eq_apn': q("SELECT COUNT(*) FROM parcels WHERE apn_raw IS apn"),
                     'apn_normalized_matches_B_pattern': q(
                         "SELECT COUNT(*) FROM parcels WHERE "
                         "apn_normalized GLOB '[0-9A-Z][0-9A-Z][0-9A-Z]-[0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z]-*-*' "
                         "AND apn_normalized NOT GLOB '*[^0-9A-Z-]*' AND length(apn_normalized) BETWEEN 15 AND 17"),
                     'apn_normalized_null': q("SELECT COUNT(*) FROM parcels WHERE apn_normalized IS NULL"),
                     'sample_normalized': [r[0] for r in con.execute("SELECT apn_normalized FROM parcels WHERE apn_normalized IS NOT NULL ORDER BY id LIMIT 3")]},
        'lineage_bootstrapped': q("SELECT COUNT(*) FROM parcel_lineage"),
        'lineage_by_type_status': dict(con.execute("SELECT event_type||'/'||status, COUNT(*) FROM parcel_lineage GROUP BY 1").fetchall()),
        'trigger_tests': trg,
        'counts_unchanged': {'completions': [pre['703'], post['703']], 'view': [pre['view'], post['view']],
                             'parcels': [pre['parcels'], post['parcels']]},
    }
    if mode == 'write':
        con.commit(); out['committed'] = True; con.close()
    else:
        con.rollback(); con.close(); os.remove(target); out['committed'] = False
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    print(json.dumps(run('write' if a.write else 'preview'), indent=2, default=str))
