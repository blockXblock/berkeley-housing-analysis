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
    """Materialize event_classifications from the model-read evidence (housing_rules.permit_effect,
    HCD definitions): one label per event, DELETE + INSERT, stamped with evidence_hash(). THE single
    home of the JN-C recipe (the notebook calls this; never re-type the loop). The regex path it
    replaced is in scripts/superseded/v4__stage_methods_regex_layers.py. Returns dict(role -> count)."""
    import datetime as dt
    from scripts.housing_rules.permit_effect import permit_effect, evidence_hash
    clf_hash, now = evidence_hash(), dt.datetime.now(dt.timezone.utc).isoformat()
    labels, unread = [], 0
    for ev_id, permit in con.execute("SELECT event_id, source_record_key FROM events "
                                     "WHERE event_type_code NOT LIKE 'planning_%' "      # a Planning record is not a building permit
                                     "AND event_type_code NOT LIKE 'registry_%' "      # nor a Rent Board registration (2026-10-01)
                                     "AND event_type_code NOT IN ('accela_listed', 'business_license', 'ctcac_project', 'fees_recorded', 'attachment_listed', 'zab_action')"):  # nor a listing, licence, CTCAC row, fee total, Board action
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
    Only ever promotes an UNCOUNTED event; never overwrites an existing count.

    The one exception is convention `phase_carried` (John, 2026-09-29): a phase permit that the reading
    counted with the SAME units its completing phase carries (Logan Park South: Phase I and Phase II both
    69). The row names the carrier in `carried_by`, and the demotion runs only when the carrier is itself a
    ledger-grounded counted master with that same count AND the carrier's own permit text names the
    demoted permit. A zero never stands alone: it points at where the units are counted."""
    rows = pd.read_csv(csv_path)
    cks = _calibration('calibration_checksums.json')['grounded_counts']
    assert len(rows) == cks['rows'] and int(rows.grounded_count.sum()) == cks['units'], \
        f'grounded_counts calibration drift: {len(rows)}/{int(rows.grounded_count.sum())} vs pinned ' \
        f'{cks["rows"]}/{cks["units"]}'
    still_held = {h['permit'] for h in json.load(open(held_path))['held_147']}
    carried = rows[rows.convention == 'phase_carried']
    changed = 0
    try:
        for r in rows.drop(carried.index).itertuples():
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
        demoted = 0
        for r in carried.itertuples():   # after every promotion, so each carrier is already grounded
            p, carrier = r.source_record_key, str(r.carried_by)
            assert int(r.grounded_count) == 0, f'phase_carried {p}: grounded_count must be 0'
            crow = rows[(rows.source_record_key == carrier) & (rows.convention != 'phase_carried')]
            assert len(crow) == 1, f'phase_carried {p}: carrier {carrier} is not a ledger-grounded row'
            cn = int(crow.grounded_count.iloc[0])
            cstate = _finaled_state(con, carrier)
            assert len(cstate) == 1, f'phase_carried {p}: carrier {carrier} has {len(cstate)} finaled events'
            crole, cmaster, cnu, cnote = cstate[0]
            assert crole == 'new_unit' and cmaster == 1 and cnu == cn and 'grounded_counts' in (cnote or ''), \
                f'phase_carried {p}: carrier {carrier} is not a counted grounded master ({crole}/{cmaster}/{cnu})'
            cdesc = con.execute("SELECT raw_description FROM events WHERE source_record_key=? "
                                "AND event_type_code='permit_finaled'", (carrier,)).fetchone()[0] or ''
            assert p in cdesc, f'phase_carried {p}: carrier {carrier} permit text does not name {p}'
            state = _finaled_state(con, p)
            assert len(state) == 1, f'phase_carried {p}: {len(state)} finaled events (expect 1)'
            role, is_master, nu, note = state[0]
            if role == 'subsidiary' and nu == 0 and 'phase_carried' in (note or ''):
                continue  # idempotent re-run
            assert role == 'new_unit' and is_master == 1 and nu == cn, \
                f'phase_carried {p}: expected a counted master carrying {cn}, found {role}/{is_master}/{nu}'
            rc = con.execute(
                "UPDATE event_classifications SET housing_role='subsidiary', is_master=0, net_units=0, "
                "basis='evidentiary', basis_note=COALESCE(basis_note,'')||' | grounded_counts phase_carried "
                "(units carried by '||?||'; src '||?||')' "
                "WHERE event_id IN (SELECT event_id FROM events WHERE source_record_key=? AND event_type_code='permit_finaled')",
                (carrier, str(r.source_ref)[:120], p)).rowcount
            assert rc == 1, f'phase_carried {p}: rowcount={rc} (expect 1)'
            demoted += rc
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {'rows': len(rows), 'promoted': changed, 'demoted': demoted}


# ---------------------------------------------------------------- EVIDENCE: inspections and stored documents
# Loaded AFTER JN-B's dedup (so distinct inspections on one day are never collapsed) and BEFORE JN-C's
# classification. Each original file is a `sources` row with its SHA-256; every inspection record becomes one
# event or is rejected WITH a reason (ingestion conservation, as in JN-A). Added 2026-09-28.
INSPECTIONS_DIR = os.path.join(ROOT, 'data', 'raw', 'accela_inspections')
DOCUMENTS_MANIFEST = os.path.join(ROOT, 'data', 'derived', 'documents_r2_manifest_2026-09-28.csv')
# Every DECLARED document manifest, in load order. A new manifest is a new row here, never an edit of an old
# file. The 2026-09-29 file is the Accela attachments behind John's assisted-living rulings (Dwight, San Pablo,
# Step Up), harvested straight from Accela, not exported from v2.
DOCUMENT_MANIFESTS = (
    DOCUMENTS_MANIFEST,
    os.path.join(ROOT, 'data', 'derived', 'documents_r2_manifest_2026-09-29.csv'),
    os.path.join(ROOT, 'data', 'derived', 'documents_r2_manifest_2026-09-30.csv'),   # Poet's Place (DRCF2021-0008)
)
PLANNING_RECORDS = os.path.join(ROOT, 'data', 'raw', 'accela_capdetail', 'capdetail_2026-09-26.jsonl')
# Every DECLARED CapDetail harvest, in load order: (file, retrieved date, what it is). A new harvest is a new row
# here, never an edit of an old file. The 2026-09-29 file is the 44 records the planning-scope rulings INCLUDE
# (corrections/v4/planning_scope_rulings.csv, John 2026-09-29) that the old regex filter never fetched.
PLANNING_HARVESTS = (
    # the 2026-09-26 harvest RE-PARSED 2026-09-30 from its own saved pages with the parcel fix (ff94c85): identical to
    # capdetail_2026-09-26.jsonl except 13 multi-parcel records that regain their non-primary parcels. The original
    # file stays in the repo as history; the pages did not change, so nothing was re-fetched.
    (os.path.join(ROOT, 'data', 'raw', 'accela_capdetail', 'capdetail_2026-09-26_reparsed-2026-09-30.jsonl'), '2026-09-26',
     'CapDetail harvest of housing Planning records, re-parsed 2026-09-30 (parcel fix); raw pages pinned in '
     'data/raw/accela_capdetail/pages_manifest_2026-09-26.csv'),
    (os.path.join(ROOT, 'data', 'raw', 'accela_capdetail', 'capdetail_2026-09-29_adds.jsonl'), '2026-09-29',
     'CapDetail harvest of the 44 records planning_scope_rulings.csv includes (harvest_capdetail.py --records); '
     'raw pages pinned in data/raw/accela_capdetail/pages_manifest_2026-09-29_adds.csv'),
    # Tier 1 of the 2006-2014 backfill (John, 2026-09-30): pre-2015 primary applications (use permits, AUPs, their
    # modifications) the first reading called housing or could not decide. Projects rule P1b makes one a project only
    # if it reaches a building; the rest are evidence.
    (os.path.join(ROOT, 'data', 'raw', 'accela_capdetail', 'capdetail_2026-09-30_pre2015.jsonl'), '2026-09-30',
     'CapDetail harvest of 1,359 pre-2015 primary applications (Tier 1; harvest_capdetail.py --records); raw pages '
     'pinned in data/raw/accela_capdetail/pages_manifest_2026-09-30_pre2015.csv'),
    # Ashby BART's first Planning filing (John, 2026-09-30, phase 5): its text ("TOD development proposal", a request
    # for a roundtable meeting) carries no housing word, so no filter or scope reading admitted it. Fetched by name so
    # classification ruling R006 (counts toward RHNA) has a project to attach to.
    (os.path.join(ROOT, 'data', 'raw', 'accela_capdetail', 'capdetail_2026-09-30_ashby-bart.jsonl'), '2026-09-30',
     'CapDetail of PLN2026-0185, the Ashby BART TOD pre-application (harvest_capdetail.py --records); page pinned in '
     'data/raw/accela_capdetail/pages_manifest_2026-09-30_ashby-bart.csv'),
)


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
                              r['apn_hint'] or None, sid,
                              # a manifest harvested straight from Accela carries its own provenance; the
                              # 2026-09-28 manifest was exported from v2 and names the v2 row instead
                              r.get('provenance') or f"v2 document {r['v2_document_id']} ({r['v2_source_system']})")
                             for r in rows]).rowcount
        assert n == len(rows), f'documents: inserted {n} of {len(rows)}'
        con.commit()
    except Exception:
        con.rollback()
        raise
    return dict(rows=len(rows), inserted=n)


def load_all_documents(con):
    """Load every declared manifest in DOCUMENT_MANIFESTS; -> {file: load_documents totals}."""
    return {os.path.basename(m): load_documents(con, m) for m in DOCUMENT_MANIFESTS}


PLANNING_LOG = os.path.join(ROOT, 'data', 'raw', 'cpra-downloads', '2026 Master Permits Log.xlsx')


def load_planning_log(con, path=PLANNING_LOG):
    """CPRA 26-1972: the Planning department's own 2026 master log (2025-26 applications). Each row that names a record
    becomes one 'planning_log_entry' event (the whole row in raw_payload, its sheet named) and its APPLICANT an actor --
    the only public source of applicants. The row's density-bonus, streamlining and BMR statements stay in the payload
    for the projects and ledger stages. Rows with no record number (placeholders, section headings) are rejected with
    the reason, so the run conserves. Added 2026-09-30 (cutover phase 4)."""
    import datetime as dt, re as _re
    import pandas as _pd
    from scripts.housing_rules.owner_name import is_organisation
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    loc = os.path.relpath(path, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    con.execute("INSERT OR IGNORE INTO event_types VALUES ('planning_log_entry','ENTITLEMENT_APPLIED',0,"
                "'a row of the Planning department master log (CPRA 26-1972); the row in raw_payload')")
    out = dict(rows=0, entries=0, rejected=0, applicants=0, applicant_actions=0)
    rej = []
    try:
        sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                          "('cpra_planning_log',?,?,?,?)", (loc, '2026-09-21', _sha256(path),
                          'CPRA 26-1972: Berkeley Planning 2026 Master Permits Log (9 sheets)')).lastrowid
        rid = None
        known = dict(con.execute("SELECT display_name, actor_id FROM actors WHERE role_class='applicant'"))
        for sh in _pd.ExcelFile(path).sheet_names:
            d = _pd.read_excel(path, sheet_name=sh, dtype=str)
            d.columns = [_re.sub(r'\s+', ' ', str(c)).strip() for c in d.columns]
            for i, row in d.iterrows():
                out['rows'] += 1
                rec = str(row.iloc[0] or '').strip()
                if not _re.match(r'^[A-Z]+\d{4}-\d{4}$', rec):
                    rej.append(f'{sh}#{i}: no record number ({rec[:20]!r})'); continue
                rowd = {k: v for k, v in row.to_dict().items() if isinstance(v, str) and v.strip()}
                rowd['_sheet'] = sh
                date = None
                for c in ('Date Received', 'Date received'):
                    try:
                        date = _pd.to_datetime(row.get(c)).date().isoformat() if row.get(c) else None
                    except Exception:
                        date = None
                    if date: break
                if rid is None:
                    rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,"
                                      "rows_rejected,conserved) VALUES (?,?,0,0,0,1)", (sid, now)).lastrowid
                ev = con.execute("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                                 "source_id,ingestion_run_id,raw_payload,raw_address,raw_description,created_at) VALUES "
                                 "('planning_log_entry',?,?,?,?,?,?,?,?,?)",
                                 (date, 'day' if date else 'unknown', rec, sid, rid, json.dumps(rowd),
                                  rowd.get('Site Address'), (rowd.get('Description') or '')[:500], now)).lastrowid
                out['entries'] += 1
                who = (rowd.get('Applicant') or '').strip()
                if who:
                    if who not in known:
                        known[who] = con.execute("INSERT INTO actors (actor_kind,display_name,role_class) VALUES (?,?,'applicant')",
                                                 ('organization' if is_organisation(who) else 'person', who)).lastrowid
                        out['applicants'] += 1
                    con.execute("INSERT INTO actor_actions (actor_id,event_id,entity_type,entity_id,role,source_id,coverage_note) "
                                "VALUES (?,?,'permit_event',?,'applicant',?,'applicant as the 2026 Planning master log names it')",
                                (known[who], ev, ev, sid))
                    out['applicant_actions'] += 1
        out['rejected'] = len(rej)
        con.execute("UPDATE ingestion_runs SET rows_in_source=?, rows_ingested=?, rows_rejected=?, rejected_detail=?, "
                    "conserved=? WHERE run_id=?", (out['rows'], out['entries'], len(rej), '; '.join(rej)[:4000] or None,
                    int(out['rows'] == out['entries'] + len(rej)), rid))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return out


def load_all_planning(con):
    """Load every declared harvest in PLANNING_HARVESTS; -> {file: load_planning totals}."""
    return {os.path.basename(p): load_planning(con, p, retrieved, note) for p, retrieved, note in PLANNING_HARVESTS}


def load_planning(con, path=PLANNING_RECORDS, retrieved_at='2026-09-26', note=None):
    """Harvested Accela PLANNING records (CapDetail) -> events, as the city recorded them.
    Each record -> one 'planning_filed' event on its list date, carrying the whole parsed record (every task,
    pending ones included) as raw_payload. Each DATED processing-status task -> one 'planning_task' event
    (task, disposition, the due date the city set itself, and who marked it, in raw_payload). What a task
    MEANS for a project's stage (accepted, entitled) is read later by housing_rules.planning_record and the
    rung-3 selection, never here. Whoever marked a task becomes a city_staff actor exactly as written
    (initials are not resolved to names). Returns dict(records, filed, tasks, dated_tasks, staff, marks)."""
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    loc = os.path.relpath(path, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    con.executemany("INSERT OR IGNORE INTO event_types VALUES (?,?,0,?)", [
        ('planning_filed', 'ENTITLEMENT_APPLIED', 'Accela Planning record filed (list date); the parsed record in raw_payload'),
        ('planning_task', 'ENTITLEMENT_APPLIED', 'dated city review task on a Planning record (task, disposition, '
         'due date, marked by, in raw_payload); its stage meaning is read later, not at load')])
    recs = [json.loads(l) for l in open(path)]
    tot = dict(records=len(recs), filed=0, tasks=0, dated_tasks=0, staff=0, marks=0)
    try:
        sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                          "('accela_capdetail',?,?,?,?)", (loc, retrieved_at, _sha256(path),
                          note or PLANNING_HARVESTS[0][2])).lastrowid
        rejected = [r['record'] for r in recs if not r.get('list_date')]
        rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,"
                          "rows_rejected,rejected_detail,conserved) VALUES (?,?,?,?,?,?,1)",
                          (sid, now, len(recs), len(recs) - len(rejected), len(rejected),
                           ('no list date: ' + ' '.join(rejected)) if rejected else None)).lastrowid
        # staff already created by an earlier harvest are REUSED: one person, one actor, across files
        staff = dict(con.execute("SELECT display_name, actor_id FROM actors WHERE role_class='city_staff'"))
        from scripts.housing_rules.owner_name import is_organisation
        owners = dict(con.execute("SELECT display_name, actor_id FROM actors WHERE role_class='owner'"))   # one name, one actor
        n_staff_before, marks = len(staff), []
        for r in recs:
            tasks = r.get('processing_status') or []
            tot['tasks'] += len(tasks)
            if r['record'] in rejected:
                continue
            parcels = r.get('parcels_raw') or []
            apn = parcels[0] if parcels else None
            filed = dt.datetime.strptime(r['list_date'], '%m/%d/%Y').date().isoformat()
            fev = con.execute("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                        "source_id,ingestion_run_id,raw_payload,raw_address,raw_apn,raw_description,created_at) "
                        "VALUES ('planning_filed',?,'day',?,?,?,?,?,?,?,?)",
                        (filed, r['record'], sid, rid, json.dumps(r), r.get('work_location'), apn,
                         f"{r.get('record_type')} — {r.get('description') or ''}"[:500], now)).lastrowid
            tot['filed'] += 1
            # The OWNER the Accela record lists (2026-09-30, phase 4): the name before " * " in the record's owner
            # field (machine-formatted: NAME * mailing address). As the record shows it at retrieval -- not proven to be
            # the owner on the filing date, so the role says "record_owner", not "owner_at_filing".
            oname = (r.get('owner') or '').split(' * ')[0].strip()
            if oname:
                if oname not in owners:
                    owners[oname] = con.execute("INSERT INTO actors (actor_kind,display_name,role_class) VALUES (?,?,'owner')",
                                                ('organization' if is_organisation(oname) else 'person', oname)).lastrowid
                con.execute("INSERT INTO actor_actions (actor_id,event_id,entity_type,entity_id,role,source_id,coverage_note) "
                            "VALUES (?,?,'permit_event',?,'record_owner',?,'owner as the Accela Planning record lists it, at "
                            "retrieval')", (owners[oname], fev, fev, sid))
                tot['record_owners'] = tot.get('record_owners', 0) + 1
            for t in tasks:
                if not t.get('status_date'):
                    continue
                payload = dict(t, record=r['record'], record_type=r.get('record_type'))
                ev = con.execute("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                                 "source_id,ingestion_run_id,raw_payload,raw_address,raw_apn,raw_description,created_at) "
                                 "VALUES ('planning_task',?,'day',?,?,?,?,?,?,?,?)",
                                 (t['status_date'], r['record'], sid, rid, json.dumps(payload), r.get('work_location'),
                                  apn, f"{t.get('task')} — {t.get('status')}", now)).lastrowid
                tot['dated_tasks'] += 1
                who = (t.get('status_by') or '').strip()
                if who:
                    if who not in staff:
                        staff[who] = con.execute("INSERT INTO actors (actor_kind,display_name,role_class,notes) VALUES "
                                                 "('person',?,'city_staff',?)", (who, 'as written on Accela Planning '
                                                 'records; initials are not resolved to a name')).lastrowid
                    marks.append((staff[who], ev, 'permit_event', ev, 'marked_review_task', sid))
        con.executemany("INSERT INTO actor_actions (actor_id,event_id,entity_type,entity_id,role,source_id) "
                        "VALUES (?,?,?,?,?,?)", marks)
        tot['staff'], tot['marks'] = len(staff) - n_staff_before, len(marks)
        con.commit()
    except Exception:
        con.rollback()
        raise
    return tot


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
        # The County's SITUS address per parcel -> addresses + parcel_addresses (2026-09-30), read separately so the
        # source fingerprint above is unchanged. Through the address canon; a situs with no house number or a '0'
        # placeholder is not an address. Needed to place a building on the right child of a SPLIT parcel
        # (housing_rules.parcel_lineage). Corner lots carry ONE frontage here (CLAUDE.md rule 4), so a non-match is
        # not evidence against a parcel.
        from scripts.housing_rules.address import normalize_address
        addr_ids = {}
        out['situs_addresses'] = 0
        for apn, situs in src.execute("SELECT APN, SitusAddre FROM parcels"):
            if apn not in by_apn or not situs:
                continue
            try:
                num, street = normalize_address(situs)
            except Exception:
                continue
            if not num or not street or num == '0':
                continue
            key = f"{num}|{street}"
            if key not in addr_ids:
                addr_ids[key] = con.execute("INSERT INTO addresses (number, street, normalized) VALUES (?,?,?)",
                                            (num, street, key)).lastrowid
            con.execute("INSERT OR IGNORE INTO parcel_addresses VALUES (?,?)", (by_apn[apn][0], addr_ids[key]))
            out['situs_addresses'] += 1
        # Each parcel's OUTLINE (the County's WKT MULTIPOLYGON) -> geometries as a GeoJSON Feature, with the County's own
        # label point kept as a property (2026-09-30, cutover phase 4). Same declared source, read separately so the
        # fingerprint above is unchanged. A project's or building's location is reached through its parcels.
        from shapely import wkt as _wkt
        from shapely.geometry import mapping as _mapping
        out['geometries'] = out['geometry_rejected'] = 0
        for apn, geom, lat, lon in src.execute("SELECT APN, the_geom, Latitude, Longitude FROM parcels"):
            if apn not in by_apn or not geom:
                continue
            try:
                g = _mapping(_wkt.loads(geom))
            except Exception:
                out['geometry_rejected'] += 1
                continue
            feat = {"type": "Feature", "geometry": g,
                    "properties": {"label_point": [float(lon), float(lat)] if lat and lon else None}}
            con.execute("INSERT OR IGNORE INTO geometries (entity_type, entity_id, geojson, valid_from, source_id) "
                        "VALUES ('parcel', ?, ?, ?, ?)", (by_apn[apn][0], json.dumps(feat), PARCELS_ASOF, sid))
            out['geometries'] += 1
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


BUILDING_HARVESTS = (
    # Licensed Professionals of every master building permit (John, 2026-10-01: separate developer / owner /
    # architect / builder). Parsed from the saved CapDetail pages with parse_licensed_professionals (662f0d9).
    (os.path.join(ROOT, 'data', 'raw', 'accela_capdetail', 'building_capdetail_2026-10-01.jsonl'), '2026-10-01',
     'CapDetail harvest of the master building permits (Licensed Professionals); raw pages pinned in '
     'data/raw/accela_capdetail/pages_manifest_2026-10-01_building.csv'),
)


def load_building_professionals(con, harvests=BUILDING_HARVESTS):
    """The LICENSED PROFESSIONALS a building permit names (the contractor of record, sometimes more) -> actors with
    their own role, never inferred from another role. Identity = the licence the page states (State CSLB #, else the
    City business licence BL-...), so one contractor across many buildings is ONE actor; the company is the last name
    line, a contact person (if any) stays in notes as written. Role from the page's licence TYPE: 'Construction or
    Contractor' -> contractor_primary (the page's primary Licensed Professional -- NOT necessarily the general
    contractor: 1951 Shattuck's Phase 1 lists its electrician first and Webcor Builders as additional; which one is the
    builder is the licence CLASSIFICATION, CSLB's to state) / contractor_additional (the 'Additional Licensed
    Professionals'); any other type -> licensed_professional, its type in the coverage note (never guessed to be an
    architect). Anchored on the permit's issuance event, else its earliest event. A permit not in the events is
    rejected with its reason. The page's OWNER field (NAME * mailing address, as the planning loader reads it) becomes
    role permit_owner -- the owner the BUILDING permit lists at retrieval, a separate claim from the assessor's."""
    import datetime as dt
    from scripts.housing_rules.owner_name import is_organisation
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    anchor = {}
    for k, eid, t, d in con.execute("SELECT source_record_key, event_id, event_type_code, event_date FROM events "
                                    "WHERE event_type_code LIKE 'permit_%' ORDER BY source_record_key, "
                                    "event_type_code != 'permit_issued', event_date, event_id"):
        anchor.setdefault(k, eid)
    ident, owners = {}, {}
    out = {}
    for path, retrieved, note in harvests:
        loc = os.path.relpath(path, ROOT)
        assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
        recs = [json.loads(l) for l in open(path)]
        try:
            sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                              "('accela_capdetail_building',?,?,?,?)", (loc, retrieved, _sha256(path), note)).lastrowid
            rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,"
                              "rows_rejected,conserved) VALUES (?,?,?,0,0,1)", (sid, now, len(recs))).lastrowid
            ok, bad, acts = 0, [], 0
            for r in recs:
                eid = anchor.get(r['record'])
                if eid is None:
                    bad.append(f"{r['record']}: no permit event"); continue
                if 'licensed_professionals' not in r:
                    bad.append(f"{r['record']}: parsed without the licensed-professional parser"); continue
                ok += 1
                oname = (r.get('owner') or '').split(' * ')[0].strip()
                if oname:
                    if oname not in owners:
                        owners[oname] = con.execute("INSERT INTO actors (actor_kind,display_name,role_class) VALUES "
                                                    "(?,?,'owner')", ('organization' if is_organisation(oname) else 'person',
                                                                      oname)).lastrowid
                    con.execute("INSERT INTO actor_actions (actor_id,event_id,entity_type,entity_id,role,source_id,"
                                "coverage_note) VALUES (?,?,'permit_event',?,'permit_owner',?,'owner as the Accela building "
                                "permit lists it, at retrieval')", (owners[oname], eid, eid, sid))
                    acts += 1
                for i, p in enumerate(r['licensed_professionals']):
                    names = [n for n in p.get('names') or [] if '@' not in n]
                    company = names[-1] if names else (p.get('business_license') or '?')
                    key = (p.get('license_board'), p.get('license_number')) if p.get('license_number') \
                        else ('BL', p.get('business_license')) if p.get('business_license') else ('name', company)
                    ctype = p.get('license_type') or ''
                    if ctype.startswith('Construction'):
                        role, rc = ('contractor_primary' if i == 0 else 'contractor_additional'), 'contractor'
                    else:
                        role, rc = 'licensed_professional', 'licensed_professional'
                    if key not in ident:
                        ident[key] = con.execute(
                            "INSERT INTO actors (actor_kind,display_name,role_class,notes) VALUES (?,?,?,?)",
                            ('organization' if is_organisation(company) else 'person', company, rc,
                             json.dumps({"license_board": p.get('license_board'), "license_number": p.get('license_number'),
                                         "business_license": p.get('business_license'), "address": p.get('address'),
                                         "contact_names": names[:-1]}))).lastrowid
                    con.execute("INSERT INTO actor_actions (actor_id,event_id,entity_type,entity_id,role,source_id,"
                                "coverage_note) VALUES (?,?,'permit_event',?,?,?,?)",
                                (ident[key], eid, eid, role, sid, f"{r['record']} Licensed Professionals: {ctype or 'type not stated'}"))
                    acts += 1
            con.execute("UPDATE ingestion_runs SET rows_ingested=?, rows_rejected=?, rejected_detail=?, conserved=? "
                        "WHERE run_id=?", (ok, len(bad), '; '.join(bad)[:3000] or None, int(ok + len(bad) == len(recs)), rid))
            con.commit()
        except Exception:
            con.rollback()
            raise
        out[os.path.basename(path)] = dict(records=len(recs), loaded=ok, rejected=len(bad), actions=acts)
    out['_actors'] = len(ident)
    return out


ACCELA_LIST_MANIFEST = os.path.join(ROOT, 'data', 'manifests', 'accela_list_dump_2026-10-01.json')


def load_accela_list(con, manifest=ACCELA_LIST_MANIFEST):
    """EVERY record in the Accela public list dumps (Building + Planning date-range sweeps), John 2026-10-01: "load the
    commercial records for mixed-use projects". Which records are a project's (a retail tenant improvement, a business
    licence certificate, a sign, a short-term rental) is decided AFTER the build, by the project's building addresses
    (v_project_records_listed), so the load takes the whole declared dump rather than a scope it cannot know yet.
      accela_listed  one per distinct (module, record), dated at its list Date; the list row in raw_payload
                     (record type, description, status, address cell). Additive to the CPRA/CapDetail events of the
                     same record -- a listing, not a permit event: it never sets an issuance or a completion.
    The dump is DECLARED by a manifest pinning each file's SHA-256; a file that changed HALTS. Sweep windows overlap,
    so a record listed in several files lands once (the first file in path order) and the rest are rejected as
    'duplicate listing' -- conserved: rows = events + rejected.
    event_addresses (created here, additive): each listing's address through THE address canon
    (housing_rules.address.normalize_address) into the shared addresses table, with its suite ("1951 SHATTUCK Ave, C"
    -> unit 'C') -- so a view can join listings to a building's addresses (aliases included) without re-deriving."""
    from scripts.housing_rules.address import normalize_address
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    m = json.load(open(manifest))
    for f in m['files']:
        got = _sha256(os.path.join(ROOT, f['path']))
        assert got == f['sha256'], f"accela list dump changed since its manifest: {f['path']}"
    if not con.execute("SELECT 1 FROM lifecycle_phases WHERE phase_code='CITY_RECORD'").fetchone():
        con.execute("INSERT INTO lifecycle_phases VALUES ('CITY_RECORD', 90, 'existing', "
                    "'a City record whose stage meaning is read later (a listing, a business or use certificate)')")
    con.execute("INSERT OR IGNORE INTO event_types VALUES ('accela_listed','CITY_RECORD',0,"
                "'a record in the Accela public list (Building or Planning module), dated at its list Date; the row in raw_payload')")
    con.execute("CREATE TABLE IF NOT EXISTS event_addresses (event_id INTEGER NOT NULL REFERENCES events(event_id), "
                "address_id INTEGER NOT NULL REFERENCES addresses(address_id), unit TEXT, PRIMARY KEY (event_id, address_id))")
    addr_id = dict((n, a) for a, n in con.execute("SELECT address_id, normalized FROM addresses"))
    loc = os.path.relpath(manifest, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    rows_in = sum(f['rows'] for f in m['files'])
    n_addr = 0
    try:
        sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,source_asof,checksum,notes) VALUES "
                          "('accela_list_dump',?,?,?,?,?)", (loc, m['frozen'], m['frozen'], _sha256(manifest),
                          m['note'])).lastrowid
        rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                          "conserved) VALUES (?,?,?,0,0,1)", (sid, now, rows_in)).lastrowid
        seen, ok, dup, pager, bad = set(), 0, 0, 0, []
        for f in m['files']:
            module = os.path.basename(f['path']).split('_')[0]
            for i, line in enumerate(open(os.path.join(ROOT, f['path']))):
                d = json.loads(line)
                rec = str(d.get('Record Number') or d.get('Permit Number') or '').strip()
                if not rec:
                    cells = d.get('_cells') or []
                    if cells and '< Prev' in str(cells[0]):   # the result table's page-navigation row, not a record
                        pager += 1
                    else:
                        bad.append(f"{os.path.basename(f['path'])}:{i} no record number")
                    continue
                if (module, rec) in seen:
                    dup += 1; continue
                seen.add((module, rec))
                try:
                    when = dt.datetime.strptime(d.get('Date') or '', '%m/%d/%Y').date().isoformat()
                except ValueError:
                    when = None
                addr = next((c for c in (d.get('_cells') or []) if isinstance(c, str) and ', BERKELEY CA' in c.upper()), None)
                d['_module'] = module
                ev = con.execute("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                                 "source_id,ingestion_run_id,raw_payload,raw_address,raw_apn,raw_description,created_at) "
                                 "VALUES ('accela_listed',?,?,?,?,?,?,?,NULL,?,?)",
                                 (when, 'day' if when else 'unknown', rec, sid, rid, json.dumps(d), addr,
                                  (d.get('Description') or '')[:500], now)).lastrowid
                ok += 1
                if addr:
                    parts = [x.strip() for x in addr.split(',')]
                    unit = parts[1] if len(parts) > 2 and 'BERKELEY CA' not in parts[1].upper() else None
                    try:
                        num, street = normalize_address(parts[0])
                    except Exception:
                        num = street = None
                    if num and street and num != '0':
                        key = f"{num}|{street}"
                        if key not in addr_id:
                            addr_id[key] = con.execute("INSERT INTO addresses (number, street, normalized) VALUES (?,?,?)",
                                                       (num, street, key)).lastrowid
                        con.execute("INSERT OR IGNORE INTO event_addresses VALUES (?,?,?)", (ev, addr_id[key], unit))
                        n_addr += 1
        rejected = dup + pager + len(bad)
        assert ok + rejected == rows_in, (ok, rejected, rows_in)
        con.execute("UPDATE ingestion_runs SET rows_ingested=?, rows_rejected=?, rejected_detail=? WHERE run_id=?",
                    (ok, rejected, f"{dup} duplicate listings (overlapping sweep windows); {pager} page-navigation rows "
                     f"('< Prev 1 2 Next >', captured by the sweep as rows); " + '; '.join(bad)[:3000], rid))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return dict(files=len(m['files']), rows=rows_in, events=ok, duplicate_listings=dup, pager_rows=pager,
                rejected_other=len(bad),
                with_address=n_addr)


def load_building_fees(con, harvests=BUILDING_HARVESTS):
    """The FEES the City records on each harvested building permit (the CapDetail Fees tab; John 2026-10-01). One
    'fees_recorded' event per permit that has any, dated at RETRIEVAL (the totals are cumulative to that day), the tab's
    own figures in raw_payload as printed: total_paid, total_outstanding, the invoices on its first page. Not
    itemized by fee type (that needs each invoice's detail page). Re-derived from the source pages, never copied from
    v2's v1-era fee rows."""
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    if not con.execute("SELECT 1 FROM lifecycle_phases WHERE phase_code='CITY_RECORD'").fetchone():
        con.execute("INSERT INTO lifecycle_phases VALUES ('CITY_RECORD', 90, 'existing', "
                    "'a City record whose stage meaning is read later (a listing, a business or use certificate)')")
    # NOT 'permit_*': the build's permit filters are LIKE 'permit_%', and a fee total must never read as a permit event
    # NOT 'permit_*': the build filters permit events with LIKE 'permit_%' -- a fee total must never read as one
    con.execute("INSERT OR IGNORE INTO event_types VALUES ('fees_recorded','CITY_RECORD',0,"
                "'the fees a building permit page records (paid / outstanding totals), dated at retrieval')")
    out = {}
    for path, retrieved, note in harvests:
        loc = os.path.relpath(path, ROOT) + '#fees'
        assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
        recs = [json.loads(l) for l in open(path)]
        try:
            sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                              "('accela_capdetail_fees',?,?,?,?)", (loc, retrieved, _sha256(path),
                              'Fees tab of the harvested building-permit pages')).lastrowid
            rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                              "conserved) VALUES (?,?,?,0,0,1)", (sid, now, len(recs))).lastrowid
            ok, none, no_tab = 0, 0, []
            for r in recs:
                f = r.get('fees')
                if f is None:
                    no_tab.append(r['record']); continue
                if not f:
                    none += 1; continue
                when = (r.get('fetched_at') or retrieved)[:10]
                con.execute("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                            "source_id,ingestion_run_id,raw_payload,raw_description,created_at) "
                            "VALUES ('fees_recorded',?,'day',?,?,?,?,?,?)",
                            (when, r['record'], sid, rid, json.dumps(f),
                             f"paid {f.get('total_paid', '$0.00')}; outstanding {f.get('total_outstanding', '$0.00')}", now))
                ok += 1
            # conserved: every page is a fee event, an empty fee tab (no fees), or a page with no fee tab (named)
            con.execute("UPDATE ingestion_runs SET rows_ingested=?, rows_rejected=?, rejected_detail=?, conserved=? "
                        "WHERE run_id=?", (ok, none + len(no_tab), f"{none} pages with an empty fee tab (no fees); no fee "
                        f"tab: {', '.join(no_tab)}", int(ok + none + len(no_tab) == len(recs)), rid))
            con.commit()
        except Exception:
            con.rollback()
            raise
        out[os.path.basename(path)] = dict(pages=len(recs), with_fees=ok, no_fees=none, no_fee_tab=len(no_tab))
    return out


CAPTURES_MANIFEST = os.path.join(ROOT, 'data', 'manifests', 'accela_status_captures_2026-10-01.json')


def load_attachment_lists(con, manifest=CAPTURES_MANIFEST):
    """The ATTACHMENT LISTS in the Accela record captures (John 2026-10-01, the v2 -> v4 audit: v2 held ~1,236 of these
    as 'documents' with no file). Each listed file -> one 'attachment_listed' event on its record, dated at the City's
    upload date; raw_payload = the file name as listed (it often carries the document's own date and kind: '2022-03-01_
    LTR Incomplete_...'), its size, the upload date, and the capture file + line it came from. The files are NOT held.
    Read by the captures' own STRUCTURE: a record header ('PERMIT:', 'BUILDING PERMIT:', 'Permit Number:') and
    three-field lines (name | size | upload date, in either order). A listed file before any header is rejected and
    counted. Declared by a manifest pinning each capture by SHA-256."""
    import datetime as dt, re as _re
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    REC = _re.compile(r'^\s*(?:BUILDING PERMIT|PERMIT|Permit Number|Record(?: Number)?|RECORD)\s*:\s*'
                      r'([A-Z]{1,7}\d{4}-\d{3,5}(?:-[A-Z]+\d+)?)\b', _re.I)
    DATE = _re.compile(r'^\d\d/\d\d/\d{4}$')
    SIZE = _re.compile(r'^\d+(?:\.\d+)?\s*(?:bytes|KB|MB|GB)$', _re.I)
    m = json.load(open(manifest))
    for f in m['files']:
        assert _sha256(os.path.join(ROOT, f['path'])) == f['sha256'], f"capture changed since its manifest: {f['path']}"
    con.execute("INSERT OR IGNORE INTO event_types VALUES ('attachment_listed','CITY_RECORD',0,"
                "'a file listed in an Accela record''s Attachments, dated at its upload; the file is not held')")
    loc = os.path.relpath(manifest, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    try:
        sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                          "('accela_status_captures',?,?,?,?)", (loc, m['frozen'], _sha256(manifest), m['note'])).lastrowid
        rows, orphan = [], 0
        for f in m['files']:
            cur = None
            for i, line in enumerate(open(os.path.join(ROOT, f['path']), errors='replace')):
                h = REC.match(line)
                if h:
                    cur = h.group(1).upper(); continue
                parts = [p.strip() for p in line.rstrip('\n').split(' | ')]
                if len(parts) != 3:
                    continue
                d = [p for p in parts if DATE.match(p)]; z = [p for p in parts if SIZE.match(p)]
                n = [p for p in parts if not DATE.match(p) and not SIZE.match(p)]
                if len(d) == 1 and len(z) == 1 and len(n) == 1:
                    if cur is None:
                        orphan += 1; continue
                    rows.append((cur, n[0], d[0], z[0], os.path.basename(f['path']), i + 1))
        rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                          "rejected_detail,conserved) VALUES (?,?,?,?,?,?,1)",
                          (sid, now, len(rows) + orphan, len(rows), orphan,
                           f"{orphan} listed files before any record header" if orphan else None)).lastrowid
        for rec, name, up, size, cf, ln in rows:
            when = dt.datetime.strptime(up, '%m/%d/%Y').date().isoformat()
            con.execute("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                        "source_id,ingestion_run_id,raw_payload,raw_description,created_at) "
                        "VALUES ('attachment_listed',?,'day',?,?,?,?,?,?)",
                        (when, rec, sid, rid, json.dumps({"file": name, "size": size, "uploaded": up,
                                                          "capture": cf, "line": ln}), name[:300], now))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return dict(captures=len(m['files']), attachments=len(rows), records=len({r[0] for r in rows}), orphans=orphan)


DRAWN_GEOMETRY_KML = os.path.join(ROOT, 'kml', 'geometry', 'versions', 'Geometry-2026-05-18-labeled.kml')


def load_drawn_outlines(con, path=DRAWN_GEOMETRY_KML):
    """Hand-drawn building outlines with heights (John 2026-10-01, v2 -> v4 audit item 3): the placemarks of the
    2026-05-18 geometry KML (the file v2's kml_import read) whose OWN style marks them as drawn -- '_footprint' (a drawn
    building outline) or '_synthetic' (estimated massing) -- never the '_parcel' lot outlines, which v4 takes from the
    County. Each -> geometries row, entity_type 'drawn_outline', entity_id = the canonical address id of the address
    its name begins with ('2400 Bowditch St · North · 750 units ...'); the polygon, its height (the coordinates'
    altitude, metres), the style and the full name in the GeoJSON properties. Linked to projects in the views."""
    import re as _re
    from scripts.housing_rules.address import normalize_address
    t = open(path, errors='replace').read()
    loc = os.path.relpath(path, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    addr_id = dict((n, a) for a, n in con.execute("SELECT address_id, normalized FROM addresses"))
    sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                      "('drawn_geometry_kml',?,?,?,?)", (loc, '2026-05-18', _sha256(path),
                      'hand-drawn building footprints / synthetic massing with heights (Google Earth)')).lastrowid
    out, skipped = 0, []
    try:
        for pm in _re.findall(r'<Placemark>(.*?)</Placemark>', t, _re.S):
            st = _re.search(r'<styleUrl>#?([^<]*)</styleUrl>', pm)
            kind = _re.sub(r'\d+$', '', st.group(1)).rsplit('_', 1)[-1] if st else None
            if kind not in ('footprint', 'synthetic'):
                continue
            name = _re.search(r'<name>([^<]*)</name>', pm).group(1).strip()
            coords = _re.search(r'<coordinates>(.*?)</coordinates>', pm, _re.S).group(1).split()
            pts = [tuple(float(x) for x in c.split(',')) for c in coords]
            try:
                num, street = normalize_address(name.split('·')[0].strip())
            except Exception:
                num = street = None
            if not num or not street:
                skipped.append(name); continue
            key = f"{num}|{street}"
            if key not in addr_id:
                addr_id[key] = con.execute("INSERT INTO addresses (number, street, normalized) VALUES (?,?,?)",
                                           (num, street, key)).lastrowid
            gj = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[x, y] for x, y, *_ in pts]]},
                  "properties": {"name": name, "kind": kind, "style": st.group(1),
                                 "height_m": max((p[2] for p in pts if len(p) > 2), default=None)}}
            con.execute("INSERT OR REPLACE INTO geometries (entity_type, entity_id, geojson, valid_from, source_id) "
                        "VALUES ('drawn_outline', ?, ?, ?, ?)", (addr_id[key], json.dumps(gj), f'2026-05-18#{out}', sid))
            out += 1
        con.commit()
    except Exception:
        con.rollback()
        raise
    return dict(outlines=out, skipped=skipped)


ATTACHMENT_HARVESTS = (os.path.join(ROOT, 'data', 'raw', 'accela_attachments', 'attachments_2026-10-03.jsonl'),)


def load_attachment_harvests(con, paths=ATTACHMENT_HARVESTS):
    """The attachment lists HARVESTED from Accela (scripts/harvest_attachment_lists.py; John 2026-10-03), alongside the
    hand captures load_attachment_lists reads. One 'attachment_listed' event per listed file, dated at the City's upload
    date (the mm/dd/yyyy after the size in the grid row); raw_payload = file name, size, upload date and, for an approval
    letter that was downloaded, its local path + SHA-256 (the PDFs stay local, uncommitted). A record the hand captures
    already listed is skipped, so a file is never listed twice."""
    import datetime as dt, re as _re
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    have = {k for (k,) in con.execute("SELECT DISTINCT source_record_key FROM events WHERE event_type_code='attachment_listed'")}
    out = {}
    for path in paths:
        loc = os.path.relpath(path, ROOT)
        assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
        recs = [json.loads(l) for l in open(path)]
        try:
            sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                              "('accela_attachment_harvest',?,?,?,?)", (loc, recs[0]['fetched_at'][:10] if recs else None,
                              _sha256(path), "harvest_attachment_lists.py: each record's Accela attachment list")).lastrowid
            n_rows = sum(len(r['rows']) for r in recs)
            rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                              "conserved) VALUES (?,?,?,0,0,1)", (sid, now, n_rows)).lastrowid
            ok, skipped = 0, 0
            for r in recs:
                if r['record'] in have:
                    skipped += len(r['rows']); continue
                for x in r['rows']:
                    m = _re.search(r"(\d+(?:\.\d+)?\s*(?:bytes|KB|MB|GB))\s+(\d\d/\d\d/\d{4})", x.get('rowtext') or '')
                    up = dt.datetime.strptime(m.group(2), '%m/%d/%Y').date().isoformat() if m else None
                    pl = {"file": x.get('filename'), "size": m.group(1) if m else None, "uploaded": up,
                          "saved": x.get('saved'), "sha256": x.get('sha256'), "harvest": loc}
                    con.execute("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                                "source_id,ingestion_run_id,raw_payload,raw_description,created_at) "
                                "VALUES ('attachment_listed',?,?,?,?,?,?,?,?)",
                                (up, 'day' if up else 'unknown', r['record'], sid, rid, json.dumps(pl),
                                 (x.get('filename') or '')[:300], now))
                    ok += 1
            con.execute("UPDATE ingestion_runs SET rows_ingested=?, rows_rejected=?, rejected_detail=?, conserved=? WHERE run_id=?",
                        (ok, skipped, f"{skipped} files on records the hand captures already list", int(ok + skipped == n_rows), rid))
            con.commit()
        except Exception:
            con.rollback()
            raise
        out[os.path.basename(path)] = dict(records=len(recs), files=n_rows, loaded=ok, skipped=skipped)
    return out


ZAB_ACTIONS = os.path.join(ROOT, 'data', 'derived', 'zab_actions_2026-10-06.jsonl')


def load_zab_actions(con, path=ZAB_ACTIONS):
    """The Zoning Adjustments Board's actions, read from its own Action Minutes (scripts/parse_zab_minutes.py; John
    approved the deciding-body rule 2026-10-07). One 'zab_action' event per (meeting, item, record): dated at the meeting,
    keyed on the Planning record the minutes cite; raw_payload = the parsed row (action, its text, the vote, the
    heading, the minutes file + SHA-256). build_projects reads these to name the body that decided."""
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    loc = os.path.relpath(path, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    rows = [json.loads(l) for l in open(path)]
    con.execute("INSERT OR IGNORE INTO event_types VALUES ('zab_action','CITY_RECORD',0,"
                "'an action of the Zoning Adjustments Board on a Planning record, read from its Action Minutes')")
    try:
        sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                          "('zab_action_minutes',?,?,?,?)", (loc, '2026-10-06', _sha256(path),
                          'parse_zab_minutes.py over the ZAB minutes harvest (berkeleyca.gov + Records Online)')).lastrowid
        rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                          "conserved) VALUES (?,?,?,0,0,1)", (sid, now, len(rows))).lastrowid
        for r in rows:
            con.execute("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                        "source_id,ingestion_run_id,raw_payload,raw_description,created_at) "
                        "VALUES ('zab_action',?,'day',?,?,?,?,?,?)",
                        (r['meeting_date'], r['record'], sid, rid, json.dumps(r),
                         f"ZAB {r['action'] or 'action not read'} -- {r['heading']}"[:300], now))
        con.execute("UPDATE ingestion_runs SET rows_ingested=?, conserved=1 WHERE run_id=?", (len(rows), rid))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return dict(rows=len(rows), approved=sum(r['action'] == 'APPROVED' for r in rows))


PLANNING_FEES = os.path.join(ROOT, 'data', 'raw', 'accela_capdetail', 'planning_fees_2026-10-01.jsonl')


def load_planning_fees(con, path=PLANNING_FEES):
    """The FEES tab of every saved Planning page (scripts/extract_capdetail_fees.py; John 2026-10-01): application,
    use-permit and review fees, the tab's totals as printed. Same 'fees_recorded' event type as building permits,
    keyed by the Planning record and dated at its harvest (the manifest's date; totals are cumulative to then).
    Cross-checked: ZP2022-0019's page total ($55,760.00) equals the independent 2026 capture file's."""
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    con.execute("INSERT OR IGNORE INTO event_types VALUES ('fees_recorded','CITY_RECORD',0,"
                "'the fees a permit or Planning record page records (paid / outstanding totals), dated at retrieval')")
    loc = os.path.relpath(path, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    recs = [json.loads(l) for l in open(path)]
    try:
        sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                          "('accela_capdetail_fees',?,?,?,?)", (loc, '2026-10-01', _sha256(path),
                          'Fees tab of the saved Planning pages (pinned by their pages manifests)')).lastrowid
        rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                          "conserved) VALUES (?,?,?,0,0,1)", (sid, now, len(recs))).lastrowid
        ok, none = 0, 0
        for r in recs:
            f = r.get('fees')
            if not f:
                none += 1; continue
            when = r['manifest'][len('pages_manifest_'):len('pages_manifest_') + 10]
            con.execute("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                        "source_id,ingestion_run_id,raw_payload,raw_description,created_at) "
                        "VALUES ('fees_recorded',?,'day',?,?,?,?,?,?)",
                        (when, r['record'], sid, rid, json.dumps(f),
                         f"paid {f.get('total_paid', '$0.00')}; outstanding {f.get('total_outstanding', '$0.00')}", now))
            ok += 1
        con.execute("UPDATE ingestion_runs SET rows_ingested=?, rows_rejected=?, rejected_detail=?, conserved=? WHERE run_id=?",
                    (ok, none, f"{none} pages with no fee tab or an empty one", int(ok + none == len(recs)), rid))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return dict(pages=len(recs), with_fees=ok, without=none)


DOCUMENT_ROLES = os.path.join(ROOT, 'data', 'derived', 'document_roles_evidence_2026-10-01.json')


def load_document_roles(con, path=DOCUMENT_ROLES):
    """The parties the project DOCUMENTS name, by the role the document states (title blocks, cover sheets, application
    forms; llm_document_roles.py, each kept only with a verbatim quote containing the name). Role = 'plans_' + the
    document's own label (plans_owner, plans_developer, plans_architect, plans_landscape_architect, plans_civil_engineer,
    ..., plans_other with its label): a drawing's "OWNER: Grosvenor Americas" is the project's sponsor as the plans name
    it, a separate claim from the assessor's owner of record, and both stay visible. Anchored on the DOCUMENT
    (entity_type 'document', entity_id = documents.document_id); the quote travels in the note. Run after load_documents."""
    import datetime as dt
    from scripts.housing_rules.owner_name import is_organisation
    ev = json.load(open(path))
    loc = os.path.relpath(path, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    have = {d for (d,) in con.execute("SELECT document_id FROM documents")}
    sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                      "('document_roles_evidence',?,?,?,?)", (loc, ev.get('read_at', '')[:10], _sha256(path),
                      f"parties by stated role in project documents; model {ev.get('model')}; {ev.get('rule')}")).lastrowid
    actors, acts, missing = {}, 0, []
    try:
        for r in ev['readings']:
            if r['document_id'] not in have:
                missing.append(r['document_id']); continue
            for p in r['parties']:
                name = ' '.join(p['name'].split())
                role = 'plans_' + p['role']
                k = (name.upper(), p['role'])
                if k not in actors:
                    actors[k] = con.execute("INSERT INTO actors (actor_kind,display_name,role_class,notes) VALUES (?,?,?,?)",
                                            ('organization' if is_organisation(name) else 'person', name, p['role'],
                                             json.dumps({"license": p.get('license')}) if p.get('license') else None)).lastrowid
                con.execute("INSERT INTO actor_actions (actor_id,event_id,entity_type,entity_id,role,source_id,coverage_note) "
                            "VALUES (?,NULL,'document',?,?,?,?)",
                            (actors[k], r['document_id'], role, sid,
                             (f"[{p['label']}] " if p.get('label') else '') + f"quote: {p['quote']}"[:400]))
                acts += 1
        con.commit()
    except Exception:
        con.rollback()
        raise
    assert not missing, f"document_roles evidence names documents v4 does not hold: {missing[:5]}"
    return dict(documents=len(ev['readings']), actions=acts, actors=len(actors))


CTCAC_LIST = os.path.join(ROOT, 'data', 'raw', 'funding', 'ctcac_List_of_Projects_2026-06.xlsx')


def load_ctcac_projects(con, path=CTCAC_LIST, city='BERKELEY'):
    """CTCAC's statewide List of Projects (tax-credit projects through June 2026; the file the funding ledger cites),
    the rows in one CITY (John, 2026-10-01: trace who builds, owns, runs and pays for each project). Each application
    -> one 'ctcac_project' event (dated at its placed-in-service date, else undated), the whole row in raw_payload
    (units by AMI level and by bedroom count, award amounts, stage). Its parties become actors in their OWN roles, as
    CTCAC lists them: developer, tax_credit_owner (the owner partnership), general_partner (1..5), property_manager
    (the management company). The award amounts stay in the funding ledger; this load is the parties and the unit
    mix. APN through the canon (CTCAC's own, which can be stale -- rule 4: never re-pointed here); address -> event_addresses.
    CTCAC's APN is often RETIRED (a split or re-plat since the award), so the County lineage resolves it to CURRENT parcel
    ids at load (housing_rules.parcel_lineage.Resolver, the buildings' rule), kept as _current_parcel_ids with its
    basis -- the stated APN itself stays in raw_apn untouched. Run after load_county_lineage."""
    import datetime as dt
    import pandas as _pd
    from scripts.housing_rules.apn import to_canonical_apn
    from scripts.housing_rules.address import normalize_address
    from scripts.housing_rules.owner_name import is_organisation
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    if not con.execute("SELECT 1 FROM lifecycle_phases WHERE phase_code='CITY_RECORD'").fetchone():
        con.execute("INSERT INTO lifecycle_phases VALUES ('CITY_RECORD', 90, 'existing', "
                    "'a City record whose stage meaning is read later (a listing, a business or use certificate)')")
    con.execute("INSERT OR IGNORE INTO event_types VALUES ('ctcac_project','CITY_RECORD',0,"
                "'a CTCAC tax-credit application in the List of Projects, dated at placed-in-service; the row in raw_payload')")
    con.execute("CREATE TABLE IF NOT EXISTS event_addresses (event_id INTEGER NOT NULL REFERENCES events(event_id), "
                "address_id INTEGER NOT NULL REFERENCES addresses(address_id), unit TEXT, PRIMARY KEY (event_id, address_id))")
    addr_id = dict((n, a) for a, n in con.execute("SELECT address_id, normalized FROM addresses"))
    loc = os.path.relpath(path, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    raw = _pd.read_excel(path, sheet_name='Alameda', header=None, dtype=str)
    h = next(i for i in range(15) if raw.iloc[i].astype(str).str.contains('Project City', case=False).any())
    raw.columns = [str(c).strip() for c in raw.iloc[h]]
    d = raw.iloc[h + 1:]
    rows = d[d['Project City'].astype(str).str.upper().str.strip() == city]
    from housing_rules.parcel_lineage import Resolver
    resolver = Resolver(con)
    actors = {}

    def actor(name, rc):
        name = (name or '').strip()
        if not name or name.lower() == 'nan':
            return None
        if (name, rc) not in actors:
            got = con.execute("SELECT actor_id FROM actors WHERE display_name=? AND role_class=?", (name, rc)).fetchone()
            actors[(name, rc)] = got[0] if got else con.execute(
                "INSERT INTO actors (actor_kind,display_name,role_class) VALUES (?,?,?)",
                ('organization' if is_organisation(name) else 'person', name, rc)).lastrowid
        return actors[(name, rc)]

    try:
        sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,source_asof,checksum,notes) VALUES "
                          "('ctcac_list_of_projects',?,?,?,?,?)", (loc, '2026-09-30', '2026-06-30', _sha256(path),
                          f'CTCAC List of Projects, Alameda sheet, Project City = {city}')).lastrowid
        rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                          "conserved) VALUES (?,?,?,0,0,1)", (sid, now, len(rows))).lastrowid
        ok, acts = 0, 0
        for _, r in rows.iterrows():
            row = {k: v for k, v in r.to_dict().items() if isinstance(v, str) and v.strip() and v != 'nan'}
            try:
                apn = to_canonical_apn(row.get("Assessor's Parcel Number (APN)") or '', 'Alameda')
            except Exception:
                apn = None
            pis = (row.get('Placed in Service (PIS) Date') or '')[:10] or None
            addr = row.get('Project Address')
            pids, basis = resolver.resolve(row.get("Assessor's Parcel Number (APN)"), addr)
            row['_current_parcel_ids'], row['_parcel_basis'] = list(pids), basis
            ev = con.execute("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                             "source_id,ingestion_run_id,raw_payload,raw_address,raw_apn,raw_description,created_at) "
                             "VALUES ('ctcac_project',?,?,?,?,?,?,?,?,?,?)",
                             (pis, 'day' if pis else 'unknown', row['Application Number'], sid, rid, json.dumps(row), addr,
                              apn, f"{row.get('Project Name', '')} -- {row.get('Housing Type', '')}"[:300], now)).lastrowid
            ok += 1
            try:
                num, street = normalize_address(addr.split(',')[0]) if addr else (None, None)
            except Exception:
                num = street = None
            if num and street and num != '0':
                key = f"{num}|{street}"
                if key not in addr_id:
                    addr_id[key] = con.execute("INSERT INTO addresses (number, street, normalized) VALUES (?,?,?)",
                                               (num, street, key)).lastrowid
                con.execute("INSERT OR IGNORE INTO event_addresses VALUES (?,?,NULL)", (ev, addr_id[key]))
            parties = [(row.get('Developer'), 'developer', 'developer'),
                       (row.get('Owner or Applicant Name'), 'owner', 'tax_credit_owner'),
                       (row.get('Management Company'), 'manager', 'property_manager')] + \
                      [(row.get(f'General Partner ({i})'), 'owner', 'general_partner') for i in range(1, 6)]
            for name, rc, role in parties:
                a = actor(name, rc)
                if a:
                    con.execute("INSERT INTO actor_actions (actor_id,event_id,entity_type,entity_id,role,source_id,"
                                "coverage_note) VALUES (?,?,'permit_event',?,?,?,?)",
                                (a, ev, ev, role, sid, f"as CTCAC lists it for {row['Application Number']}"))
                    acts += 1
        con.execute("UPDATE ingestion_runs SET rows_ingested=?, conserved=? WHERE run_id=?", (ok, int(ok == len(rows)), rid))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return dict(rows=len(rows), events=ok, actor_actions=acts, actors=len(actors))


BUSINESS_LICENSES = os.path.join(ROOT, 'data', 'raw', 'business_licenses_20251115.json')
BUSINESS_LICENSES_ASOF = '2025-11-15'


def load_business_licenses(con, path=BUSINESS_LICENSES):
    """City of Berkeley business licences, export of 2025-11-15 (13,004; John 2026-10-01: load them -- which ground
    floors have a licensed business TODAY, and who the rental owners and contractors are). A snapshot with no licence
    dates, so every licence is dated at the snapshot:
      business_license  one per licence; the row in raw_payload (BL number, sub-type, NAICS, dba, business name,
                        location, employees, ownership type)
    source_record_key = the BL number -- the same number a building permit's Licensed Professionals name
    (BL-038324, Nibbi Bros), so a contractor's licence and its permits join on it. The licensee is an actor
    (role business_licensee), keyed by its BL number. raw_apn = the canonical APN (none for the 'ZZZ...' placeholder);
    the location (b1_full_address; '0 VARIOUS' for contractors working citywide) goes through THE address canon into
    event_addresses. b1_address1 is the licensee's MAILING address and is not used as a location."""
    import datetime as dt
    from scripts.housing_rules.apn import to_canonical_apn
    from scripts.housing_rules.address import normalize_address
    from scripts.housing_rules.owner_name import is_organisation
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    if not con.execute("SELECT 1 FROM lifecycle_phases WHERE phase_code='CITY_RECORD'").fetchone():
        con.execute("INSERT INTO lifecycle_phases VALUES ('CITY_RECORD', 90, 'existing', "
                    "'a City record whose stage meaning is read later (a listing, a business or use certificate)')")
    con.execute("INSERT OR IGNORE INTO event_types VALUES ('business_license','CITY_RECORD',0,"
                "'a City business licence in the 2025-11-15 export, dated at the snapshot; the row in raw_payload')")
    con.execute("CREATE TABLE IF NOT EXISTS event_addresses (event_id INTEGER NOT NULL REFERENCES events(event_id), "
                "address_id INTEGER NOT NULL REFERENCES addresses(address_id), unit TEXT, PRIMARY KEY (event_id, address_id))")
    addr_id = dict((n, a) for a, n in con.execute("SELECT address_id, normalized FROM addresses"))
    loc = os.path.relpath(path, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    rows = json.load(open(path))
    try:
        sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,source_asof,checksum,notes) VALUES "
                          "('city_business_licenses',?,?,?,?,?)", (loc, BUSINESS_LICENSES_ASOF, BUSINESS_LICENSES_ASOF,
                          _sha256(path), 'City of Berkeley business licence export (13,004 licences)')).lastrowid
        rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                          "conserved) VALUES (?,?,?,0,0,1)", (sid, now, len(rows))).lastrowid
        ok, bad, n_apn, n_addr, actors = 0, [], 0, 0, {}
        for i, r in enumerate(rows):
            bl = (r.get('recordid') or '').strip()
            if not bl:
                bad.append(f"row {i}: no BL number"); continue
            try:
                apn = to_canonical_apn(r.get('apn') or '', 'Alameda')
            except Exception:
                apn = None
            n_apn += bool(apn)
            where = (r.get('b1_full_address') or '').strip()
            ev = con.execute("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                             "source_id,ingestion_run_id,raw_payload,raw_address,raw_apn,raw_description,created_at) "
                             "VALUES ('business_license',?,'day',?,?,?,?,?,?,?,?)",
                             (BUSINESS_LICENSES_ASOF, bl, sid, rid, json.dumps(r), where or None, apn,
                              (r.get('busdesc') or '')[:300], now)).lastrowid
            ok += 1
            try:
                num, street = normalize_address(where) if where else (None, None)
            except Exception:
                num = street = None
            if num and street and num != '0':
                key = f"{num}|{street}"
                if key not in addr_id:
                    addr_id[key] = con.execute("INSERT INTO addresses (number, street, normalized) VALUES (?,?,?)",
                                               (num, street, key)).lastrowid
                con.execute("INSERT OR IGNORE INTO event_addresses VALUES (?,?,NULL)", (ev, addr_id[key]))
                n_addr += 1
            name = (r.get('b1_business_name') or r.get('dba') or '').strip()
            if name:
                if bl not in actors:
                    actors[bl] = con.execute("INSERT INTO actors (actor_kind,display_name,role_class) VALUES (?,?,?)",
                                             ('organization' if is_organisation(name) else 'person', name,
                                              'business')).lastrowid
                con.execute("INSERT INTO actor_actions (actor_id,event_id,entity_type,entity_id,role,source_id,"
                            "coverage_note) VALUES (?,?,'permit_event',?,'business_licensee',?,?)",
                            (actors[bl], ev, ev, sid, f'licence {bl}, as the City export lists it, 2025-11-15'))
        con.execute("UPDATE ingestion_runs SET rows_ingested=?, rows_rejected=?, rejected_detail=?, conserved=? WHERE run_id=?",
                    (ok, len(bad), '; '.join(bad)[:3000] or None, int(ok + len(bad) == len(rows)), rid))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return dict(rows=len(rows), events=ok, rejected=len(bad), with_apn=n_apn, with_address=n_addr, licensees=len(actors))


RENT_BOARD_UNITS = os.path.join(ROOT, 'data', 'raw', 'rent_board', '2026-07-13 Unit Full Details.xlsx')
RENT_BOARD_TENANCIES = os.path.join(ROOT, 'data', 'raw', 'rent_board', 'UnitHistory_2026 Database Export.xlsx')
RENT_BOARD_ASOF = '2026-07-13'


def load_rent_board(con, units_path=RENT_BOARD_UNITS, tenancies_path=RENT_BOARD_TENANCIES):
    """Berkeley Rent Stabilization Board unit registry, CPRA #26-2375 (granted 2026-08-17; tenant identifiers redacted
    by the Board). John, 2026-10-01: load ALL of it, tenancy start dates included -- the turnover of rental units and the
    real occupancy and rent of new units (an ADU rented, owner-occupied, rent-free...) replace ABAG's guess where it
    reaches. Two event types:
      registry_unit     one per registered unit, dated at the snapshot (2026-07-13); the whole row in raw_payload
                        (status, coverage, occupant type, bedrooms, tenancy start, rents, subsidy)
      registry_tenancy  one per tenancy in the history, dated at its start; the whole row in raw_payload
    source_record_key = 'RB:<canonical APN>:<unit designation or unit address>' so a unit's snapshot and its tenancies
    share a key. Owner, owner business and manager become actors with DISTINCT roles (registry_owner,
    registry_owner_business, registry_manager): an owner is not a manager. Every row lands or is rejected with its
    reason. Run after dedup and before classify (classify_all skips registry_*)."""
    import datetime as dt, re as _re
    import pandas as _pd
    from scripts.housing_rules.apn import to_canonical_apn
    from scripts.housing_rules.owner_name import is_organisation
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    # the schema's own TENURE phase ("Sale / lease / occupancy (usually unsourced)") -- now sourced
    con.executemany("INSERT OR IGNORE INTO event_types VALUES (?,'TENURE',0,?)", [
        ('registry_unit', 'a Rent Board registered unit at the registry snapshot; the row in raw_payload'),
        ('registry_tenancy', 'a tenancy in the Rent Board history, dated at its start; the row in raw_payload')])

    def canon(a):
        try:
            return to_canonical_apn(str(a).strip().zfill(12), 'Alameda')
        except Exception:
            return None

    def norm_unit(x):
        return _re.sub(r"\s+", " ", str(x or "").strip().upper())

    def date(x):
        try:
            return _pd.to_datetime(x).date().isoformat() if x not in (None, "") else None
        except Exception:
            return None

    actors = {}
    def actor(name, role_class):
        name = (name or "").strip()
        if not name:
            return None
        k = (name, role_class)
        if k not in actors:
            got = con.execute("SELECT actor_id FROM actors WHERE display_name=? AND role_class=?", k).fetchone()
            actors[k] = got[0] if got else con.execute(
                "INSERT INTO actors (actor_kind,display_name,role_class) VALUES (?,?,?)",
                ('organization' if is_organisation(name) else 'person', name, role_class)).lastrowid
        return actors[k]

    out = {}
    try:
        for kind, path, etype in (('units', units_path, 'registry_unit'), ('tenancies', tenancies_path, 'registry_tenancy')):
            loc = os.path.relpath(path, ROOT)
            assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
            sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,source_asof,checksum,notes) VALUES "
                              "('rent_board_registry',?,?,?,?,?)", (loc, '2026-09-21', RENT_BOARD_ASOF, _sha256(path),
                              'Berkeley Rent Stabilization Board, CPRA #26-2375 (tenant identifiers redacted by the Board)')).lastrowid
            d = _pd.read_excel(path, dtype=str)
            rid = con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                              "conserved) VALUES (?,?,?,0,0,1)", (sid, now, len(d))).lastrowid
            ok, rej, acts = 0, [], 0
            for i, r in d.iterrows():
                row = {k: v for k, v in r.to_dict().items() if isinstance(v, str) and v.strip()}
                apn = canon(row.get('APN') or row.get('APN Number'))
                if not apn:
                    rej.append(f"row {i}: no parseable APN ({row.get('APN') or row.get('APN Number')!r})"); continue
                unit = norm_unit(row.get('Unit Designation') or row.get('Unit Name') or row.get('Unit Address')
                                 or row.get('Address'))
                key = f"RB:{apn}:{unit}"
                when = RENT_BOARD_ASOF if etype == 'registry_unit' else date(row.get('Start Date Of Tenancy'))
                ev = con.execute("INSERT INTO events (event_type_code,event_date,event_date_precision,source_record_key,"
                                 "source_id,ingestion_run_id,raw_payload,raw_address,raw_apn,raw_description,created_at) "
                                 "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                 (etype, when, 'day' if when else 'unknown', key, sid, rid, json.dumps(row),
                                  row.get('Unit Address') or row.get('Address'), apn,
                                  (row.get('Unit Status Code') or row.get('Reason') or '')[:200], now)).lastrowid
                ok += 1
                if etype == 'registry_unit':
                    for name, rc, role in ((row.get('Owner Name'), 'owner', 'registry_owner'),
                                           (row.get('Primary Owner Business Name'), 'owner', 'registry_owner_business'),
                                           (row.get('Manager Name'), 'manager', 'registry_manager')):
                        a = actor(name, rc)
                        if a:
                            con.execute("INSERT INTO actor_actions (actor_id,event_id,entity_type,entity_id,role,source_id,"
                                        "coverage_note) VALUES (?,?,'permit_event',?,?,?,'as the Rent Board registry lists it, "
                                        "2026-07-13')", (a, ev, ev, role, sid))
                            acts += 1
            con.execute("UPDATE ingestion_runs SET rows_ingested=?, rows_rejected=?, rejected_detail=?, conserved=? WHERE run_id=?",
                        (ok, len(rej), '; '.join(rej)[:4000] or None, int(len(d) == ok + len(rej)), rid))
            out[kind] = dict(rows=len(d), events=ok, rejected=len(rej), actor_actions=acts)
        con.commit()
    except Exception:
        con.rollback()
        raise
    return out


TAXABLE_AREA_CSV = os.path.join(ROOT, 'data', 'raw', 'berkeley_taxable_sqft_2026-09-15.csv')


def load_taxable_area(con, path=TAXABLE_AREA_CSV):
    """The City's Taxable Square Footage (data.cityofberkeley.info 9a47-nj4i, City-updated 2026-08-14) -> parcel_area:
    taxable BUILDING square feet and lot square feet per CURRENT parcel. Phase 6 (John, 2026-09-30): an independent,
    parcel-level cross-check on the square footage the permits and Planning records state for a new building -- it
    covers everything taxable on the parcel, so it is labelled parcel-level, never a building's own area. Every row lands
    or is rejected with the reason. Requires load_parcels."""
    import csv, datetime as dt
    from scripts.housing_rules.apn import to_canonical_apn
    loc = os.path.relpath(path, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    con.execute("CREATE TABLE IF NOT EXISTS parcel_area (parcel_id INTEGER NOT NULL REFERENCES parcels(parcel_id), "
                "building_sqft_taxable REAL, lot_sqft REAL, as_of_date TEXT NOT NULL, source_id INTEGER REFERENCES "
                "sources(source_id), PRIMARY KEY (parcel_id, as_of_date))")
    cur = dict(con.execute("SELECT apn_normalized, parcel_id FROM parcel_identifiers WHERE is_current=1"))
    rows = list(csv.DictReader(open(path)))
    out = dict(rows=len(rows), loaded=0, rejected=0)
    rej = []
    try:
        sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,source_asof,checksum,notes) VALUES "
                          "('city_taxable_sqft',?,?,?,?,?)", (loc, '2026-09-15', '2026-08-14', _sha256(path),
                          'City of Berkeley Taxable Square Footage (data.cityofberkeley.info 9a47-nj4i)')).lastrowid
        for r in rows:
            try:
                pid = cur.get(to_canonical_apn(r['apn'], 'Alameda'))
            except Exception as e:
                pid = None
            if pid is None:
                rej.append(f"{r['apn']}: not a current parcel"); continue
            n = con.execute("INSERT OR IGNORE INTO parcel_area VALUES (?,?,?,?,?)",
                            (pid, float(r['bldsqfttaxable']) if r['bldsqfttaxable'] else None,
                             float(r['lotsqft']) if r['lotsqft'] else None, '2026-08-14', sid)).rowcount
            if n:
                out['loaded'] += 1
            else:
                rej.append(f"{r['apn']}: duplicate row for the parcel")
        out['rejected'] = len(rej)
        con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                    "rejected_detail,conserved) VALUES (?,?,?,?,?,?,?)",
                    (sid, dt.datetime.now(dt.timezone.utc).isoformat(), len(rows), out['loaded'], len(rej),
                     '; '.join(rej)[:4000] or None, int(len(rows) == out['loaded'] + len(rej))))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return out


COUNTY_LINEAGE_MANIFEST = os.path.join(ROOT, 'data', 'raw', 'county_parcel_lineage', 'manifest_2026-09-30.csv')
# The Alameda Assessor's own parent -> child APN lists (23 tables, 2005-2027; scripts/fetch_county_lineage.py). They
# REPLACE the 2026-09-28 bootstrap candidates (John, 2026-09-30): ADR-003 said lineage is not authoritative until
# confirmed against the County's record, and the County's record is what this is. One of the 30 candidates was wrong
# (2001 Ashby, 053-1591-018-03 -> 018-04, not 014-01). The candidate CSV stays in data/derived as history.
_L_PARENT = ('PARENT_APN', 'PARENT_PARCEL', 'PARENT_PARCEL_NUMBER')
_L_CHILD = ('CHILD_APN', 'CHILD_PARCEL_NUMBER')
_L_END = ('END_DT', 'END_DATE', 'INACTIVATION_DATE', 'PARENT_PARCEL_END_DATE')


def load_county_lineage(con, manifest=COUNTY_LINEAGE_MANIFEST):
    """County lineage -> former parcels + confirmed parcel_lineage edges. Requires load_parcels.
    Every retired APN in a Berkeley book becomes a FORMER parcel (its own identity, a non-current identifier with
    valid_to = the County's end date); each PARENT -> CHILD row becomes a 'confirmed' edge between parcels, typed
    split (parent has several children), merger (child has several parents) or renumber. Each table's SHA-256 is
    checked against the manifest before it is read. Returns counts."""
    import csv, datetime as dt, json as _json
    from scripts.housing_rules.apn import to_canonical_apn
    assert con.execute("SELECT 1 FROM parcels LIMIT 1").fetchone(), 'load_parcels first'
    loc = os.path.relpath(manifest, ROOT)
    assert not con.execute("SELECT 1 FROM sources WHERE locator=?", (loc,)).fetchone(), f'already loaded: {loc}'
    files = list(csv.DictReader(open(manifest)))
    base = os.path.dirname(manifest)

    def pick(row, names):
        up = {k.upper(): v for k, v in row.items()}
        return next((up[n] for n in names if up.get(n) not in (None, '')), None)

    def canon(a):
        try:
            return to_canonical_apn(str(a).strip(), 'Alameda') if a else None
        except Exception:
            return None

    def iso(ms):
        try:
            v = int(ms)
            return None if v < 0 else dt.datetime.fromtimestamp(v / 1000, dt.timezone.utc).date().isoformat()
        except Exception:
            return None

    cur = dict(con.execute("SELECT apn_normalized, parcel_id FROM parcel_identifiers WHERE is_current=1"))
    books = {a.split('-')[0] for a in cur}
    edges, end_of, layer_of = {}, {}, {}
    out = dict(tables=len(files), county_rows=0, unparsed=0, berkeley_edges=0, former_parcels=0,
               split=0, merger=0, renumber=0)
    for f in files:
        path = os.path.join(base, f['file'])
        assert _sha256(path) == f['sha256'], f"{f['file']}: sha256 differs from the manifest"
        for r in _json.load(open(path))['rows']:
            out['county_rows'] += 1
            p, c = canon(pick(r, _L_PARENT)), canon(pick(r, _L_CHILD))
            if not p or not c:
                out['unparsed'] += 1
                continue
            if p.split('-')[0] not in books and c.split('-')[0] not in books:
                continue
            edges.setdefault(p, set()).add(c)
            layer_of[(p, c)] = f['layer']
            e = iso(pick(r, _L_END))
            if e:
                end_of[p] = max(end_of.get(p, e), e)
    parents_of = {}
    for p, cs in edges.items():
        for c in cs:
            parents_of.setdefault(c, set()).add(p)
    try:
        sid = con.execute("INSERT INTO sources (source_kind,locator,retrieved_at,checksum,notes) VALUES "
                          "('county_parcel_lineage',?,?,?,?)", (loc, '2026-09-30', _sha256(manifest),
                          'Alameda County Assessor: Deleted Parcel Lists 2018-2026 + Parcels Inactivated in Roll '
                          'Year 2005-2027 (services5.arcgis.com/ROBnTHSNjoZ2Wm1P); every table sha-checked')).lastrowid
        pid_of = dict(cur)

        def parcel(apn):
            if apn in pid_of:
                return pid_of[apn]
            pid = con.execute("INSERT INTO parcels (city, notes) VALUES ('Berkeley', ?)",
                              ('former parcel, retired per the County assessor lineage',)).lastrowid
            con.execute("INSERT INTO parcel_identifiers (parcel_id,apn_raw,apn_normalized,valid_to,is_current,county,"
                        "source_id) VALUES (?,?,?,?,0,'Alameda',?)", (pid, apn, apn, end_of.get(apn), sid))
            pid_of[apn] = pid
            out['former_parcels'] += 1
            return pid
        for p, cs in sorted(edges.items()):
            for c in sorted(cs):
                kind = 'split' if len(cs) > 1 else 'merger' if len(parents_of.get(c, ())) > 1 else 'renumber'
                n = con.execute("INSERT OR IGNORE INTO parcel_lineage (parent_parcel_id,child_parcel_id,event_type,status,"
                                "recorded_map_ref,source_id) VALUES (?,?,?,'confirmed',?,?)",
                                (parcel(p), parcel(c), kind, layer_of[(p, c)], sid)).rowcount
                out['berkeley_edges'] += n
                out[kind] += n
        con.execute("INSERT INTO ingestion_runs (source_id,started_at,rows_in_source,rows_ingested,rows_rejected,"
                    "rejected_detail,conserved) VALUES (?,?,?,?,?,?,1)",
                    (sid, dt.datetime.now(dt.timezone.utc).isoformat(), out['county_rows'],
                     out['county_rows'] - out['unparsed'], out['unparsed'],
                     f"{out['unparsed']} County rows lack a parseable parent or child APN"))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return out
