"""v4 pipeline stage METHODS — universal, parameterized; each reads its Berkeley CALIBRATION
from corrections/v4/. THE importable home (the aa6ded0 lift discipline): JN-B / JN-C / JN-F
notebooks and the rebuild drivers IMPORT these — never re-define them as cell-strings.

Validated from-raw 2026-07-02 (scratch/2026-07-02/ drivers): GATE PASS — CO 3,676 / BP 3,945 /
events == live / counted-completion set == live with 0 differences. Hardened same day after the
8-angle review: verify-or-halt on rc==0 (a missing calibration target halts; only a verified
already-applied state passes), calibration checksums re-pinned (calibration_checksums.json),
held-items externalized (held_items.json), keeper-survival + CO-neutrality dedup guards,
NULL-payload differ detection, rollback-on-failure in every write method.

Faithful re-expressions of the gated one-shot writes (scratch/2026-06-2{8,9}/*_write.py, audits
docs/audit/2026-06-2{8,9}_*), re-shaped from "mutate the live DB once" to "apply to a REBUILD db
as a pipeline stage". Snapshots/restore are deliberately absent — the target is a throwaway
rebuild (caller guards the live DB); every method is idempotent-via-verify and rolls back its
transaction on any failed guard.
"""
import json
import os
import re
import sqlite3

import pandas as pd

ROOT = os.path.expanduser('~/berkeley-data')
CORR = os.path.join(ROOT, 'corrections', 'v4')
LIVE = os.path.realpath(os.path.join(ROOT, 'databases', 'berkeley_housing_v4.db'))


def _calibration(name):
    return json.load(open(os.path.join(CORR, name)))


def connect_guarded(db_path, allow_live=False):
    """Open a rebuild target read-write; REFUSE the live corrected DB unless explicitly forced."""
    if os.path.realpath(db_path) == LIVE and not allow_live:
        raise SystemExit(f'REFUSED: {db_path} is the LIVE corrected DB. Stage methods mutate their '
                         f'target; point at a rebuild copy (or pass allow_live=True, which you '
                         f'almost never want).')
    return sqlite3.connect(db_path)


def ro(db_path):
    return sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)


# ---------------------------------------------------------------- metrics (shared derivations)
def co_total(con, y0='2018', y1='2025'):
    return con.execute(
        "SELECT COALESCE(SUM(c.net_units),0) FROM events e "
        "JOIN event_classifications c ON c.event_id=e.event_id "
        "WHERE e.event_type_code='permit_finaled' AND c.housing_role='new_unit' AND c.is_master=1 "
        "AND strftime('%Y',e.event_date) BETWEEN ? AND ?", (y0, y1)).fetchone()[0]


def co_all_positive(con):
    """JN-E's headline grain: all counted completions, net_units>0, no year filter."""
    return con.execute(
        "SELECT COALESCE(SUM(c.net_units),0) FROM events e "
        "JOIN event_classifications c ON c.event_id=e.event_id "
        "WHERE e.event_type_code='permit_finaled' AND c.housing_role='new_unit' AND c.is_master=1 "
        "AND COALESCE(c.net_units,0)>0").fetchone()[0]


def bp_permit_level(con):
    return con.execute(
        "WITH one AS (SELECT e.source_record_key sk, c.net_units nu, "
        "  ROW_NUMBER() OVER (PARTITION BY e.source_record_key ORDER BY e.event_id) rn "
        "  FROM events e JOIN event_classifications c ON c.event_id=e.event_id "
        "  WHERE e.event_type_code='permit_issued' AND c.housing_role='new_unit' AND c.is_master=1) "
        "SELECT COALESCE(SUM(nu),0) FROM one WHERE rn=1").fetchone()[0]


def event_count(con):
    return con.execute('SELECT COUNT(*) FROM events').fetchone()[0]


def _finaled_state(con, permit):
    """All finaled classification rows for a permit: [(housing_role, is_master, net_units, basis_note)]."""
    return con.execute(
        "SELECT c.housing_role, c.is_master, c.net_units, c.basis_note FROM events e "
        "JOIN event_classifications c ON c.event_id=e.event_id "
        "WHERE e.source_record_key=? AND e.event_type_code='permit_finaled'", (permit,)).fetchall()


# ---------------------------------------------------------------- JN-B: event dedup (universal)
def dedup_events(con, holds_path=os.path.join(CORR, 'event_dedup_holds.json')):
    """Collapse same-(permit, milestone, date) duplicate events to one (keep MIN event_id).

    Universal METHOD; the CALIBRATION is the hold-list. Holds (never collapsed):
    (a) auto — any group whose substantive payload fields disagree between the copies
        (NULL-vs-value counts as a disagreement: a NULL-payload copy must never absorb the
        payload-bearing copy), or — when classifications exist — whose classifications disagree;
    (b) calibration — every group in the hold-list. A calibration hold that matches NO duplicate
        group RAISES before any mutation (hold-list drift must halt, not silently collapse).
    Deletes the duplicate event + its 1:1 classification row if any. Guards after the delete:
    exact rowcounts, zero orphaned classifications, EVERY group's keeper survives, and — when
    classifications existed — the counted-CO total is UNCHANGED (dedup is CO-neutral by contract).
    Returns dict(removed, removed_classifications, held_auto, held_calib, groups).
    """
    holds = json.load(open(holds_path))['tier2_holds']
    calib_holds = {f"{h['source_record_key']}|{h['event_type_code']}|{h['event_date_prefix']}"
                   for h in holds}
    con.execute('DROP TABLE IF EXISTS dupgrp')
    con.execute('DROP VIEW IF EXISTS dupgrp')
    # TEMP TABLE (not VIEW): computed ONCE — the later keeper-survival guard must see the
    # PRE-delete group set, and the triple json_extract pass over raw_payload is paid once.
    # COALESCE(..., CHAR(1)): COUNT(DISTINCT) ignores NULLs, so without the sentinel a
    # {NULL, 'real text'} pair reads as agreeing and keep-MIN could delete the only
    # payload-bearing copy.
    con.execute("""CREATE TEMP TABLE dupgrp AS
      SELECT source_record_key k, event_type_code et, event_date d,
        source_record_key||'|'||event_type_code||'|'||substr(event_date,1,10) gkey,
        COUNT(*) c, MIN(event_id) keep_id,
        COUNT(DISTINCT COALESCE(json_extract(raw_payload,'$.WorkDescription'), CHAR(1))) nd_wd,
        COUNT(DISTINCT COALESCE(json_extract(raw_payload,'$.UnitsAdded'), CHAR(1))) nd_ua,
        COUNT(DISTINCT COALESCE(json_extract(raw_payload,'$.NumberUnits'), CHAR(1))) nd_nu
      FROM events GROUP BY 1,2,3 HAVING c>1""")
    groups = con.execute('SELECT COUNT(*) FROM dupgrp').fetchone()[0]

    unmatched = calib_holds - {r[0] for r in con.execute('SELECT gkey FROM dupgrp')}
    if unmatched:
        con.execute('DROP TABLE dupgrp')
        raise AssertionError(
            f'event_dedup_holds calibration drift: hold group(s) {sorted(unmatched)} match NO '
            f'duplicate group in this stream — halting BEFORE any collapse (a silently-unmatched '
            f'hold is how a held pair gets wrongly collapsed).')

    have_class = con.execute('SELECT COUNT(*) FROM event_classifications').fetchone()[0] > 0
    class_holds = set()
    co_before = None
    if have_class:
        co_before = co_total(con)
        class_holds = {r[0] for r in con.execute("""
          SELECT g.gkey FROM dupgrp g JOIN events e
            ON e.source_record_key=g.k AND e.event_type_code=g.et AND e.event_date=g.d
          JOIN event_classifications c ON c.event_id=e.event_id
          GROUP BY g.gkey
          HAVING COUNT(DISTINCT c.housing_role||'/'||c.is_master||'/'||COALESCE(c.net_units,-1))>1
        """)}

    rows = con.execute("""SELECT e.event_id, g.gkey, (g.nd_wd>1 OR g.nd_ua>1 OR g.nd_nu>1)
                          FROM events e JOIN dupgrp g
                            ON g.k=e.source_record_key AND g.et=e.event_type_code AND g.d=e.event_date
                          WHERE e.event_id<>g.keep_id""").fetchall()
    to_remove, held_auto, held_calib = [], set(), set()
    for event_id, gkey, substantive_differ in rows:
        if gkey in calib_holds:
            held_calib.add(gkey)
        elif substantive_differ or gkey in class_holds:
            held_auto.add(gkey)
        else:
            to_remove.append(event_id)

    try:
        rc_c = rc_e = 0
        if to_remove:
            qs = ','.join('?' * len(to_remove))
            rc_c = con.execute(f'DELETE FROM event_classifications WHERE event_id IN ({qs})', to_remove).rowcount
            rc_e = con.execute(f'DELETE FROM events WHERE event_id IN ({qs})', to_remove).rowcount
        orphan = con.execute('SELECT COUNT(*) FROM event_classifications c LEFT JOIN events e '
                             'ON e.event_id=c.event_id WHERE e.event_id IS NULL').fetchone()[0]
        # keeper-survival: dupgrp is a pre-delete SNAPSHOT, so this genuinely verifies every
        # group's chosen keeper still exists (a recomputed view could never fail this check).
        lost = con.execute('SELECT COUNT(*) FROM dupgrp g WHERE NOT EXISTS '
                           '(SELECT 1 FROM events e WHERE e.event_id=g.keep_id)').fetchone()[0]
        assert rc_e == len(to_remove) and orphan == 0 and lost == 0, \
            f'dedup guard: rc_e={rc_e}/{len(to_remove)} orphan={orphan} keeper_lost={lost}'
        if have_class:
            co_after = co_total(con)
            assert co_after == co_before, \
                f'dedup CO-NEUTRALITY violated: {co_before} -> {co_after} (a counted classification ' \
                f'was deleted — the collapsed copy carried the count; ROLLED BACK)'
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.execute('DROP TABLE IF EXISTS dupgrp')
    return {'removed': rc_e, 'removed_classifications': rc_c,
            'held_auto': sorted(held_auto), 'held_calib': sorted(held_calib), 'groups': groups}


# ---------------------------------------------------------------- JN-C: classify all (THE recipe)
def classify_all(con):
    """Materialize event_classifications with the COMMITTED classifier — THE single home of the
    JN-C cell-4 recipe (the notebook calls this; never re-type the loop). DELETE + INSERT, one
    label per event, prose-blind net_units, hash from housing_rules.permit_role.classifier_hash().
    Returns dict(role -> count)."""
    import sys
    import datetime as dt
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    from housing_rules.permit_role import classify, net_units, payload_get, classifier_hash
    clf_hash = classifier_hash()
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    labels = []
    for ev_id, payload, desc, raw_units, permit in con.execute(
            'SELECT event_id, raw_payload, raw_description, raw_units, source_record_key FROM events'):
        wt = payload_get(payload, 'Work Type')
        d = desc if desc is not None else payload_get(payload, 'WorkDescription')
        role, is_master, note = classify(wt, d, payload_get(payload, 'ADU'),
                                         payload_get(payload, 'OccType'),
                                         payload_get(payload, 'UnitsAdded'),
                                         payload_get(payload, 'UnitsRemoved'), permit)
        nu = net_units(payload_get(payload, 'UnitsAdded'), payload_get(payload, 'UnitsRemoved'), role, d)
        labels.append((ev_id, role, is_master, nu, clf_hash, now, 'description', note))
    try:
        con.execute('DELETE FROM event_classifications')
        con.executemany('INSERT INTO event_classifications '
                        '(event_id,housing_role,is_master,net_units,classifier_hash,classified_at,basis,basis_note) '
                        'VALUES (?,?,?,?,?,?,?,?)', labels)
        con.commit()
    except Exception:
        con.rollback()
        raise
    return dict(con.execute('SELECT housing_role, COUNT(*) FROM event_classifications GROUP BY 1'))


# ---------------------------------------------------------------- JN-F: the correction methods
# Write discipline shared by every apply_*: UPDATE with a state-narrowing WHERE; rc==1 = applied
# now; rc==0 is ONLY acceptable if the target verifiably already carries the corrected state
# (idempotent re-run) — anything else (typo'd permit, missing row, drifted upstream state) RAISES.
# The one-shots enforced this as rc==1-or-rollback; verify-or-halt restores that protection while
# keeping re-runs legal. Every method rolls back its transaction on any failure.

def _demote_dup_finaled_masters(con, permit):
    """Demote every non-MIN finaled new_unit master of `permit` to subsidiary/0. Returns rowcount."""
    return con.execute("""
      UPDATE event_classifications SET housing_role='subsidiary', net_units=0,
        basis_note=COALESCE(basis_note,'')||' | dedup47: duplicate file-row finaled event collapsed to single count'
      WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key=? AND event_type_code='permit_finaled')
        AND housing_role='new_unit' AND is_master=1
        AND event_id > (SELECT MIN(e2.event_id) FROM events e2
                        JOIN event_classifications c2 ON c2.event_id=e2.event_id
                        WHERE e2.source_record_key=? AND e2.event_type_code='permit_finaled'
                          AND c2.housing_role='new_unit' AND c2.is_master=1)""",
                       (permit, permit)).rowcount


def apply_dedup47(con, csv_path=os.path.join(CORR, 'dedup47_permits.csv')):
    """Collapse duplicate finaled-master counting: each calibration permit must count ONCE.
    Premise: exactly 2 counted finaled-masters (the JN-B hold-list + different-date structure
    guarantee this in a faithful rebuild) -> demote the non-MIN. n==1 is accepted ONLY as an
    idempotent re-run signature (a prior demotion visible in a basis_note); a bare n==1 — the
    signature of JN-B having wrongly collapsed the held pair — HALTS."""
    permits = pd.read_csv(csv_path)['permit'].tolist()
    cks = _calibration('calibration_checksums.json')['dedup47']
    assert len(permits) == cks['permits'], \
        f'dedup47 calibration drift: {len(permits)} permits vs pinned {cks["permits"]}'
    demoted = 0
    try:
        for p in permits:
            state = _finaled_state(con, p)
            counted = [s for s in state if s[0] == 'new_unit' and s[1] == 1]
            if len(counted) == 2:
                rc = _demote_dup_finaled_masters(con, p)
                assert rc == 1, f'dedup47 {p}: expected 1 demotion, got {rc}'
                demoted += rc
            elif len(counted) == 1:
                already = any(s[0] == 'subsidiary' and 'dedup47' in (s[3] or '') for s in state)
                assert already, (
                    f'dedup47 premise fail {p}: 1 counted finaled-master but NO demoted twin with a '
                    f'dedup47 basis_note — the duplicate was likely COLLAPSED upstream (JN-B hold '
                    f'drift?) instead of demoted; the rebuild is structurally short one event.')
            else:
                raise AssertionError(f'dedup47 premise fail {p}: {len(counted)} counted finaled-masters '
                                     f'(expect 2 fresh, or 1 + demoted twin on re-run)')
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {'permits': len(permits), 'demoted': demoted}


def _c2_frames(csv_path, held_path=os.path.join(CORR, 'held_items.json')):
    rec = pd.read_csv(csv_path)
    cks = _calibration('calibration_checksums.json')['c2_count_recovery']
    excluded = {h['permit'] for h in json.load(open(held_path))['c2_excluded']}
    counted = rec[rec.recovered_count.notna()]
    conv = counted['count_convention'].astype(str)
    unknown = set(conv.unique()) - set(cks['known_conventions'])
    if unknown:
        raise AssertionError(
            f'C2 calibration drift: unrecognized count_convention value(s) {sorted(unknown)} — add '
            f'them to calibration_checksums.json known_conventions (deciding their tranche) before '
            f'applying; an unrecognized convention must never silently land in T1.')
    is_t2 = conv.str.contains('live_work') | conv.str.contains('sleeping')
    t1 = counted[~is_t2 & ~counted.source_record_key.isin(excluded)]
    t2 = counted[is_t2 & ~counted.source_record_key.isin(excluded)]
    # the originals' pre-write checksums (c2_tranche{1,2}_write.py HALT guards), re-pinned:
    assert len(t1) == cks['t1_permits'] and int(t1.recovered_count.sum()) == cks['t1_units'], \
        f'C2-T1 checksum fail: {len(t1)}/{int(t1.recovered_count.sum())} vs pinned ' \
        f'{cks["t1_permits"]}/{cks["t1_units"]} — calibration edited without updating checksums'
    assert len(t2) == cks['t2_permits'] and int(t2.recovered_count.sum()) == cks['t2_units'], \
        f'C2-T2 checksum fail: {len(t2)}/{int(t2.recovered_count.sum())} vs pinned ' \
        f'{cks["t2_permits"]}/{cks["t2_units"]}'
    got_t2 = {r.source_record_key: int(r.recovered_count) for r in t2.itertuples()}
    assert got_t2 == cks['t2_values'], f'C2-T2 exact-value fail: {got_t2} vs pinned {cks["t2_values"]}'
    return t1, t2


def _verify_c2_applied(con, permit, n, want_flag):
    """rc==0 acceptance test: the permit already carries the corrected state — its finaled master
    is new_unit with net_units==n (T2: + the convention flag), OR it was legitimately superseded
    by the downstream C-multifamily demotion (the one order coupling, visible in the basis_note)."""
    for role, is_master, nu, note in _finaled_state(con, permit):
        if not is_master:
            continue
        if role == 'new_unit' and nu == n and (not want_flag or 'convention_dependent=true' in (note or '')):
            return True
        if role == 'subsidiary' and nu == 0 and 'C-multifamily' in (note or ''):
            return True
    return False


def apply_c2(con, csv_path=os.path.join(CORR, 'c2_count_recovery.csv')):
    """C2 count-gap recovery, both tranches, from the calibration CSV (checksummed against
    calibration_checksums.json BEFORE any write). T1: plain dwelling counts -> set net_units.
    T2: convention-dependent counts -> net_units + the convention_dependent flag. Exclusions
    (B2020-03895) come from held_items.json, not code."""
    t1, t2 = _c2_frames(csv_path)
    UPD1 = ("UPDATE event_classifications SET net_units=? "
            "WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key=? AND event_type_code='permit_finaled') "
            "AND housing_role='new_unit' AND is_master=1 AND (net_units IS NULL OR net_units!=?)")
    UPD2 = ("UPDATE event_classifications "
            "SET net_units=?, basis_note=COALESCE(basis_note,'')||' | C2-T2 convention_dependent=true ('||?||'; src c2_count_recovery.csv)' "
            "WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key=? AND event_type_code='permit_finaled') "
            "AND housing_role='new_unit' AND is_master=1 AND (net_units IS NULL OR net_units!=?)")
    n1 = n2 = 0
    try:
        for r in t1.itertuples():
            n = int(r.recovered_count)
            rc = con.execute(UPD1, (n, r.source_record_key, n)).rowcount
            assert rc == 1 or _verify_c2_applied(con, r.source_record_key, n, want_flag=False), \
                f'C2-T1 {r.source_record_key}: rc={rc} and target is NOT in the corrected state ' \
                f'(missing/mis-typed permit, or upstream stage drift) — HALT'
            n1 += rc
        for r in t2.itertuples():
            n = int(r.recovered_count)
            rc = con.execute(UPD2, (n, str(r.count_convention), r.source_record_key, n)).rowcount
            assert rc == 1 or _verify_c2_applied(con, r.source_record_key, n, want_flag=True), \
                f'C2-T2 {r.source_record_key}: rc={rc} and target is NOT in the corrected state — HALT'
            n2 += rc
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {'t1_permits': len(t1), 't1_units': int(t1.recovered_count.sum()), 't1_changed': n1,
            't2_permits': len(t2), 't2_units': int(t2.recovered_count.sum()), 't2_changed': n2}


def _demote_to_subsidiary(con, permit, note):
    return con.execute(
        "UPDATE event_classifications SET housing_role='subsidiary', net_units=0, "
        "basis_note=COALESCE(basis_note,'')||' | '||? "
        "WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key=? AND event_type_code='permit_finaled') "
        "AND housing_role='new_unit' AND is_master=1", (note, permit)).rowcount


def _is_demoted(con, permit):
    return any(role == 'subsidiary' and nu == 0
               for role, is_master, nu, note in _finaled_state(con, permit) if is_master)


def _keep_is_counted(con, permit):
    return any(role == 'new_unit' and (nu or 0) >= 1
               for role, is_master, nu, note in _finaled_state(con, permit) if is_master)


def apply_c3_shattuck(con, csv_path=os.path.join(CORR, 'c3_shattuck_collapse.csv')):
    """Phantom-master collapse: demote each calibration row's Phase-2 permit -> subsidiary/0,
    verifying the keep-side master is (still) the counted one — a swapped keep/demote column
    would otherwise demote the real building and pass."""
    rows = pd.read_csv(csv_path)
    cks = _calibration('calibration_checksums.json')['c3_shattuck']
    assert len(rows) == cks['rows'], f'c3_shattuck calibration drift: {len(rows)} rows vs pinned {cks["rows"]}'
    changed = 0
    try:
        for r in rows.itertuples():
            rc = _demote_to_subsidiary(con, r.demote_permit,
                                       f'C3 phantom-master: phase of one building, subsidiary to {r.keep_permit}')
            assert rc == 1 or _is_demoted(con, r.demote_permit), \
                f'C3-shattuck {r.demote_permit}: rc={rc} and not already demoted — HALT'
            assert _keep_is_counted(con, r.keep_permit), \
                f'C3-shattuck KEEP-side fail: {r.keep_permit} is not a counted new_unit master — ' \
                f'swapped keep/demote columns would look exactly like this; ROLLED BACK'
            changed += rc
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {'rows': len(rows), 'changed': changed}


def apply_c3_tail(con, json_path=os.path.join(CORR, 'c3_tail_demote_list.json')):
    """ADU-tail ancillary demotion: solar/meter/panel/service permits mis-counted new_unit=1 ->
    subsidiary/0, PROTECTING the paired real ADU. The keep-side is verified BEFORE the demote
    (a protect failure must abort with zero pending writes, not after the damage)."""
    targets = json.load(open(json_path))
    cks = _calibration('calibration_checksums.json')['c3_tail']
    assert len(targets) == cks['targets'] and sum(t['net'] for t in targets) == cks['net_total'], \
        f'c3_tail calibration drift: {len(targets)}/{sum(t["net"] for t in targets)} vs pinned ' \
        f'{cks["targets"]}/{cks["net_total"]}'
    changed = 0
    try:
        for t in targets:
            assert t['keep'], f'C3-tail {t["demote"]}: calibration row has NO keep-ADU — refusing to ' \
                              f'demote without a verified protected pair'
            keep = t['keep'][0]
            # PROTECT-first: verify the real ADU is counted BEFORE touching the ancillary.
            assert _keep_is_counted(con, keep), \
                f'C3-tail PROTECT fail (pre-write): paired ADU {keep} is not a counted new_unit ' \
                f'master — demoting {t["demote"]} could erase the pair; NO WRITE'
            rc = _demote_to_subsidiary(con, t['demote'], f'C3-tail: ancillary subsidiary to ADU {keep}')
            assert rc == 1 or _is_demoted(con, t['demote']), \
                f'C3-tail {t["demote"]}: rc={rc} and not already demoted — HALT'
            changed += rc
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {'targets': len(targets), 'changed': changed}


SITEWORK = re.compile(r'foundation|podium|grading|shoring|excavation', re.I)


def apply_c_multifamily(con, csv_path=os.path.join(CORR, 'c_multifamily_collapse.csv')):
    """Phased-multifamily collapse: demote foundation/podium phase, keep completion; apply the
    calibration's completion-net bump (the 40->41 manager-unit re-home). ORDER: after C2 — and
    the coupling is now ENFORCED: a bump that matches nothing and is not already applied HALTS
    (running before C2 leaves the completion at its pre-C2 value, which this catches).
    Protection guard: every demote target's WorkDescription must read as sitework."""
    rows = pd.read_csv(csv_path)
    cks = _calibration('calibration_checksums.json')['c_multifamily']
    bump_rows = rows[rows.bump_completion_net_to.notna()]
    assert len(rows) == cks['rows'] and len(bump_rows) == cks['bump_rows'], \
        f'c_multifamily calibration drift: {len(rows)}/{len(bump_rows)} vs pinned ' \
        f'{cks["rows"]}/{cks["bump_rows"]}'
    changed = bumped = 0
    try:
        for r in rows.itertuples():
            wd = con.execute("SELECT DISTINCT json_extract(raw_payload,'$.WorkDescription') FROM events "
                             "WHERE source_record_key=?", (r.demote_foundation,)).fetchone()
            wd = wd[0] if wd else ''
            assert SITEWORK.search(str(wd) or ''), \
                f'C-multifamily PROTECT: {r.demote_foundation} not clearly sitework: {str(wd)[:80]}'
            rc = _demote_to_subsidiary(con, r.demote_foundation,
                                       f'C-multifamily: foundation/podium phase, subsidiary to completion {r.keep_completion}')
            assert rc == 1 or _is_demoted(con, r.demote_foundation), \
                f'C-multifamily {r.demote_foundation}: rc={rc} and not already demoted — HALT'
            changed += rc
            if pd.notna(r.bump_completion_net_to):
                target = int(r.bump_completion_net_to)
                rc = con.execute(
                    "UPDATE event_classifications SET net_units=?, "
                    "basis_note=COALESCE(basis_note,'')||' | C-multifamily completion bump (re-homed convention flag)' "
                    "WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key=? AND event_type_code='permit_finaled') "
                    "AND housing_role='new_unit' AND is_master=1 AND net_units=?",
                    (target, r.keep_completion, target - 1)).rowcount
                already = any(role == 'new_unit' and nu == target
                              for role, m, nu, _ in _finaled_state(con, r.keep_completion) if m)
                assert rc == 1 or already, \
                    f'C-multifamily bump {r.keep_completion}: rc={rc} and net_units is neither ' \
                    f'{target-1} nor {target} — the AFTER-C2 order coupling was likely violated ' \
                    f'(the completion is not at its C2 value); HALT'
                bumped += rc
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {'rows': len(rows), 'changed': changed, 'bumped': bumped}


# ---------------------------------------------------------------- HELD items (hold-not-apply)
def assert_held(con, held_path=os.path.join(CORR, 'held_items.json')):
    """The held under-count stays HELD: no held permit may carry a counted finaled new_unit
    master (counting one requires independent grounding — the city's number is never adopted).
    The list is CALIBRATION (held_items.json): the Accela harvest resolves a permit by moving it
    out of that file with provenance, never by editing code."""
    held = json.load(open(held_path))
    for h in held['held_147']:
        p = h['permit']
        n = con.execute("""SELECT COUNT(*) FROM events e JOIN event_classifications c ON c.event_id=e.event_id
            WHERE e.source_record_key=? AND e.event_type_code='permit_finaled'
              AND c.housing_role='new_unit' AND c.is_master=1 AND COALESCE(c.net_units,0)>0""",
                        (p,)).fetchone()[0]
        assert n == 0, (f'HELD VIOLATION: {p} carries a counted completion. If it was legitimately '
                        f'grounded (e.g. the Accela harvest), move it OUT of held_items.json with '
                        f'provenance — do not bypass this assert.')
    return {'held_147': [h['permit'] for h in held['held_147']],
            'c1_phantom': held['c1_phantom']}


# ---------------------------------------------------------------- grounded counts (harvest results)
def apply_grounded_counts(con, csv_path=os.path.join(CORR, 'grounded_counts.csv'),
                          held_path=os.path.join(CORR, 'held_items.json')):
    """Promote document-grounded completions: each ledger row carries a count read from the
    BUILDING'S OWN document (plan set / tabulation — never the city APR) with full provenance.
    This is the resolution path for held items: the permit must have been moved OUT of
    held_items.json (with a resolution note) BEFORE it can appear here — enforced below.
    Promotes the FINALED event only (count-once at completion; the BP side is left untouched).
    Only ever promotes an UNCOUNTED event; never overwrites an existing count."""
    rows = pd.read_csv(csv_path)
    cks = _calibration('calibration_checksums.json')['grounded_counts']
    assert len(rows) == cks['rows'] and int(rows.grounded_count.sum()) == cks['units'], \
        f'grounded_counts calibration drift: {len(rows)}/{int(rows.grounded_count.sum())} vs pinned ' \
        f'{cks["rows"]}/{cks["units"]}'
    still_held = {h['permit'] for h in json.load(open(held_path))['held_147']}
    changed = 0
    try:
        for r in rows.itertuples():
            p, n = r.source_record_key, int(r.grounded_count)
            assert p not in still_held, \
                f'grounded_counts {p}: still listed in held_items.held_147 — resolve the hold ' \
                f'(move to resolved with provenance) before grounding'
            state = _finaled_state(con, p)
            assert len(state) == 1, f'grounded_counts {p}: {len(state)} finaled events (expect 1)'
            role, is_master, nu, note = state[0]
            if role == 'new_unit' and is_master == 1 and nu == n and 'grounded_counts' in (note or ''):
                continue  # idempotent re-run
            assert (nu or 0) == 0, \
                f'grounded_counts {p}: finaled event already carries net_units={nu} — refusing to overwrite'
            rc = con.execute(
                "UPDATE event_classifications SET housing_role='new_unit', is_master=1, net_units=?, "
                "basis=?, basis_note=COALESCE(basis_note,'')||' | grounded_counts ('||?||'; src '||?||')' "
                "WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key=? AND event_type_code='permit_finaled')",
                (n, 'evidentiary', str(r.source_document)[:180], str(r.source_ref)[:120], p)).rowcount
            assert rc == 1, f'grounded_counts {p}: rowcount={rc} (expect 1)'
            changed += rc
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {'rows': len(rows), 'promoted': changed}
