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
def classify_all(con, source='evidence'):
    """Materialize event_classifications. DEFAULT (since 2026-09-26): the model-read evidence
    (housing_rules.permit_effect, HCD definitions); source='regex' keeps the old rules path callable.
    Regex path: the COMMITTED classifier — THE single home of the
    JN-C cell-4 recipe (the notebook calls this; never re-type the loop). DELETE + INSERT, one
    label per event, prose-blind net_units, hash from housing_rules.permit_role.classifier_hash().
    Returns dict(role -> count)."""
    import sys
    import datetime as dt
    from scripts.housing_rules.permit_role import classify, net_units, payload_get, classifier_hash
    if source == 'evidence':   # model-read labels (housing_rules.permit_effect), same vocabulary
        from scripts.housing_rules.permit_effect import permit_effect, evidence_hash
        clf_hash, now = evidence_hash(), dt.datetime.now(dt.timezone.utc).isoformat()
        labels, unread = [], 0
        for ev_id, permit in con.execute('SELECT event_id, source_record_key FROM events'):
            got = permit_effect(permit)
            if got is None:
                unread += 1
                got = ('ambiguous', 0, None, 'not in the evidence file')
            role, is_master, nu, note = got
            labels.append((ev_id, role, is_master, nu, clf_hash, now, 'model', note))
        con.execute('DELETE FROM event_classifications')
        con.executemany('INSERT INTO event_classifications '
                        '(event_id,housing_role,is_master,net_units,classifier_hash,classified_at,basis,basis_note) '
                        'VALUES (?,?,?,?,?,?,?,?)', labels)
        con.commit()
        out = dict(con.execute('SELECT housing_role, COUNT(*) FROM event_classifications GROUP BY 1'))
        out['_unread_events'] = unread
        return out
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


# The four regex-era correction layers (apply_c2, apply_c3_shattuck, apply_c3_tail, apply_c_multifamily
# and their helpers) were retired 2026-09-26: scripts/superseded/v4__stage_methods_regex_layers.py.


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
            # never OVERWRITE a different count; but a role PROMOTION over an equal stored count is
            # legitimate (the 2026-07-03 ADU-recall class: RULE-9 ambiguous rows whose UnitsAdded was
            # already right — promoting ambiguous->new_unit at the same value changes no number)
            if role == 'new_unit' and is_master == 1 and 0 < (nu or 0) < n:
                # UPGRADE path (the 1173-Hearst amendment, John-approved 2026-07-03): the stored count
                # came from the derive rule's blank-count floor (1) while the permit's OWN structured
                # NumberUnits states n. Never a downgrade; only when the raw field corroborates exactly.
                raw_nu = con.execute(
                    "SELECT CAST(json_extract(raw_payload,'$.NumberUnits') AS INT) FROM events "
                    "WHERE source_record_key=? AND event_type_code='permit_finaled'", (p,)).fetchone()[0]
                # A dated ruling on a NAMED convention (anything but plain 'dwelling', e.g. dwelling+live_work)
                # is itself the authority for the higher count: the structured field cannot express it.
                convention_ruling = str(getattr(r, 'convention', 'dwelling')) != 'dwelling' and \
                    str(getattr(r, 'adjudicated', '') or '') not in ('', 'nan')
                assert raw_nu == n or convention_ruling, \
                    f'grounded_counts {p}: upgrade {nu}->{n} REFUSED — raw NumberUnits={raw_nu} does not corroborate'
            else:
                assert (nu or 0) in (0, n), \
                    f'grounded_counts {p}: finaled event carries net_units={nu} != ledger {n} — refusing to overwrite'
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


# ---------------------------------------------------------------- EVIDENCE: inspections and stored documents
# Loaded AFTER JN-B's dedup (so distinct inspections on one day are never collapsed) and BEFORE JN-C's
# classification. Each original file is a `sources` row with its SHA-256; every inspection record becomes one
# event or is rejected WITH a reason (ingestion conservation, as in JN-A). Added 2026-09-28.
INSPECTIONS_DIR = os.path.join(ROOT, 'data', 'raw', 'accela_inspections')
DOCUMENTS_MANIFEST = os.path.join(ROOT, 'data', 'derived', 'documents_r2_manifest_2026-09-28.csv')


def _sha256(path):
    import hashlib
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def load_inspections(con, directory=INSPECTIONS_DIR):
    """Harvested Accela inspection histories -> 'inspection' events (phase CONSTRUCTION), one per record.
    Refuses to load a file twice. Returns dict(files, records, events, rejected)."""
    import glob, datetime as dt
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    con.execute("INSERT OR IGNORE INTO event_types VALUES ('inspection','CONSTRUCTION',0,"
                "'Accela inspection record (type, result, inspector in raw_payload)')")
    files = sorted(glob.glob(os.path.join(directory, '*.json')))
    assert files, f'no inspection files in {directory}'
    tot = dict(files=0, records=0, events=0, rejected=0)
    try:
        for f in files:
            loc = os.path.relpath(f, ROOT)
            assert not con.execute("SELECT 1 FROM sources WHERE source_kind='accela_inspection' AND locator=?",
                                   (loc,)).fetchone(), f'already loaded: {loc}'
            d = json.load(open(f))
            permit, recs = d.get('permit_number'), d.get('inspections') or []
            sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                              "('accela_inspection',?,?,?,?)", (loc, d.get('extraction_timestamp'), _sha256(f),
                              f"{d.get('extraction_method') or ''} {d.get('url') or ''}"[:300])).lastrowid
            ok, rejected = [], []
            for r in recs:
                try:
                    day = dt.datetime.strptime(r['date'], '%m/%d/%Y').date().isoformat()
                except Exception:
                    rejected.append(f"{r.get('inspection_id')}: unparseable date {r.get('date')!r}"); continue
                ok.append((day, r))
            rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,"
                              "rows_rejected,rejected_detail,conserved) VALUES (?,?,?,?,?,?,?)",
                              (sid, now, len(recs), len(ok), len(rejected), '; '.join(rejected)[:2000] or None,
                               int(len(recs) == len(ok) + len(rejected)))).lastrowid
            con.executemany("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                            "source_id,ingestion_run_id,raw_payload,raw_description,created_at) VALUES "
                            "('inspection',?,'day',?,?,?,?,?,?)",
                            [(day, permit, sid, rid, json.dumps(r), f"{r.get('type_code')} — {r.get('result')}", now)
                             for day, r in ok])
            tot['files'] += 1; tot['records'] += len(recs); tot['events'] += len(ok); tot['rejected'] += len(rejected)
        con.commit()
    except Exception:
        con.rollback()
        raise
    return tot


def load_documents(con, manifest=DOCUMENTS_MANIFEST):
    """Stored-document manifest -> documents table (one sources row for the manifest, with its SHA-256)."""
    import csv, datetime as dt
    ddl = open(os.path.join(ROOT, 'schema', 'v4', 'schema_v4.sql')).read()
    con.executescript(ddl.split('-- BEGIN documents')[1].split('-- END documents')[0])   # idempotent DDL
    loc = os.path.relpath(manifest, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    rows = list(csv.DictReader(open(manifest)))
    try:
        sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                          "('document_manifest',?,?,?,?)", (loc, dt.datetime.now(dt.timezone.utc).isoformat(),
                          _sha256(manifest), 'files held in R2; exported from v2 documents with provenance')).lastrowid
        n = con.executemany("INSERT INTO documents (record_key,record_key_source,title,doc_date,doc_type,store_url,"
                            "sha256,file_size_bytes,page_count,address_hint,apn_hint,source_id,provenance) VALUES "
                            "(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            [(r['record_key'] or None, r['record_key_source'], r['title'], r['doc_date'] or None,
                              r['doc_type'], r['store_url'], r['sha256'] or None,
                              int(r['file_size_bytes']) if r['file_size_bytes'] else None,
                              int(r['page_count']) if r['page_count'] else None, r['address_hint'] or None,
                              r['apn_hint'] or None, sid, f"v2 document {r['v2_document_id']} ({r['v2_source_system']})")
                             for r in rows]).rowcount
        assert n == len(rows), f'documents: inserted {n} of {len(rows)}'
        con.commit()
    except Exception:
        con.rollback()
        raise
    return dict(rows=len(rows), inserted=n)


# ---------------------------------------------------------------- REFERENCE: parcels, assessed values, owners
# The county's parcels become v4 parcels with a stable internal id; APNs are time-labeled IDENTIFIERS on them
# (parcel_identifiers), never the key (ADR-003). Assessed values and owners of record attach to the parcel with
# their source. Owners are actors with an 'owner_of_record' action on the parcel. Added 2026-09-28.
PARCELS_DB = os.path.join(ROOT, 'databases', 'berkeley.db')          # ArcGIS Parcels feed, refreshed 2026-06-16
PARCELS_ASOF = '2026-02-01'                                            # the feed's own currency (Feb 2026)
OWNERS_CSV = os.path.join(ROOT, 'data', 'reference', 'berkeley_parcel_owners_2026-08-13.csv')


def load_parcels(con, parcels_db=PARCELS_DB, owners_csv=OWNERS_CSV):
    """Assessor parcels -> parcels + parcel_identifiers + assessed_values; owner file -> actors + actor_actions.
    Every source row lands or is rejected with a reason. Refuses to run twice. Returns counts."""
    import csv, hashlib, datetime as dt
    from scripts.housing_rules.apn import to_canonical_apn
    from scripts.housing_rules.owner_name import is_organisation
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    assert not con.execute("SELECT 1 FROM parcels LIMIT 1").fetchone(), 'parcels already loaded'
    src = sqlite3.connect(f'file:{parcels_db}?mode=ro', uri=True)
    rows = src.execute("SELECT APN, Land, Imps, TotalNetValue FROM parcels ORDER BY APN").fetchall()
    fp = hashlib.sha256('\n'.join('|'.join(map(str, r)) for r in rows).encode()).hexdigest()
    out = dict(source_rows=len(rows), parcels=0, duplicate_rows=0, rejected=0, owners_rows=0,
               owners_linked=0, owners_unmatched=0, actors=0)
    try:
        sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,source_asof,checksum,notes) VALUES "
                          "('assessor','databases/berkeley.db:parcels',?,?,?,?)", (now, PARCELS_ASOF, fp,
                          'Alameda County Parcels FeatureServer (data.acgov.org), refreshed 2026-06-16; checksum = '
                          'SHA-256 of the sorted APN|Land|Imps|TotalNetValue rows')).lastrowid
        by_apn, rejected = {}, []
        for apn, land, imps, total in rows:
            if apn in by_apn:
                out['duplicate_rows'] += 1; continue            # exact duplicate rows in the feed (12 APNs)
            try:
                canon = to_canonical_apn(apn, 'Alameda')
            except Exception as e:
                rejected.append(f'{apn}: {e}'); continue
            pid = con.execute("INSERT INTO parcels (city, notes) VALUES ('Berkeley', NULL)").lastrowid
            con.execute("INSERT INTO parcel_identifiers (parcel_id,apn_raw,apn_normalized,is_current,county,source_id) "
                        "VALUES (?,?,?,1,'Alameda',?)", (pid, apn, canon, sid))
            con.execute("INSERT INTO assessed_values (parcel_id,land,improvements,total_net_value,as_of_date,source_id) "
                        "VALUES (?,?,?,?,?,?)", (pid, land, imps, total, PARCELS_ASOF, sid))
            by_apn[apn] = (pid, canon)
        out['parcels'], out['rejected'] = len(by_apn), len(rejected)
        con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                    "rejected_detail,conserved) VALUES (?,?,?,?,?,?,?)",
                    (sid, now, len(rows), len(by_apn) + out['duplicate_rows'], len(rejected),
                     '; '.join(rejected)[:2000] or None,
                     int(len(rows) == len(by_apn) + out['duplicate_rows'] + len(rejected))))
        by_canon = {c: p for p, c in by_apn.values()}
        orows = list(csv.DictReader(open(owners_csv)))
        osid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,source_asof,checksum,notes) VALUES "
                           "('assessor_owner',?,?,?,?,?)", (os.path.relpath(owners_csv, ROOT), now, '2026-08-13',
                           _sha256(owners_csv), 'City of Berkeley tax parcels, OwnersName (the v2 owner join of '
                           '2026-09-02). Owner of record as of the file; APNs are not stable identifiers.')).lastrowid
        actor_ids, links, unmatched = {}, [], []
        for r in orows:
            name = (r.get('OwnersName') or '').strip()
            if not name:
                unmatched.append(f"{r.get('APN')}: no owner name"); continue
            try:
                pid = by_canon.get(to_canonical_apn(r['APN'], 'Alameda'))
            except Exception as e:
                pid = None
            if pid is None:
                unmatched.append(f"{r.get('APN')}: not a current parcel"); continue
            if name not in actor_ids:
                actor_ids[name] = con.execute("INSERT INTO actors (actor_kind,display_name,role_class) VALUES (?,?,'owner')",
                                              ('organization' if is_organisation(name) else 'person', name)).lastrowid
            links.append((actor_ids[name], pid, osid))
        con.executemany("INSERT INTO actor_actions (actor_id,entity_type,entity_id,role,source_id,coverage_note) VALUES "
                        "(?,'parcel',?,'owner_of_record',?,'owner of record per the 2026-08-13 city tax-parcel file')",
                        links)
        con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                    "rejected_detail,conserved) VALUES (?,?,?,?,?,?,?)",
                    (osid, now, len(orows), len(links), len(unmatched), '; '.join(unmatched)[:2000] or None,
                     int(len(orows) == len(links) + len(unmatched))))
        out.update(owners_rows=len(orows), owners_linked=len(links), owners_unmatched=len(unmatched), actors=len(actor_ids))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return out
