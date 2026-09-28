# ============================ SEQUESTERED 2026-09-26 ============================
# DO NOT RUN. Original home: scripts/v4/stage_methods.py (JN-F sections 3-5).
# WHY: the four regex-era correction layers (C2 count recovery, C3 Shattuck phantom master, C3 ADU-tail,
# C-multifamily phase collapse) patched specific errors of the regex classifier. JN-C now classifies from
# model-read evidence (housing_rules.permit_effect, HCD definitions), which achieves 38 of their 43 targets
# directly; the rest are John's ledger rulings or the buildings stage. John approved 2026-09-26.
# Calibration files: corrections/v4/superseded/.
raise SystemExit("SEQUESTERED 2026-09-26 -- regex-era correction layers; see header")
# ================================================================================

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




# ---------------------------------------------------------------- classify_all's regex path (retired 2026-09-28)
# Removed from stage_methods.classify_all(source='regex'); nothing called it after JN-C switched to evidence.
def classify_all_regex(con):
    import datetime as dt
    from scripts.housing_rules.permit_role import classify, net_units, payload_get, classifier_hash
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
