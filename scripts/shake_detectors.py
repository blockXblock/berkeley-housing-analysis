#!/usr/bin/env python3
"""
shake_detectors.py — deterministic, READ-ONLY anomaly detector for the Berkeley
Housing Pipeline (v2). The all-years / all-blocks replacement for the expensive
agent "shake-the-DB" sweep, re-founded on the refreshed Feb-2026 assessor reference.

NEVER WRITES. Opens both DBs read-only (mode=ro). Emits a findings JSON.

Each check encodes its EXPECTED-vs-SIGNAL false-positive filters (the session's
hard-won lessons) so the output is signal, not noise:
  - UC projects legitimately skip city stages (stage_skip).
  - CO-only import cohort (id 185-279 + 280-899, no lifecycle events) inverts the
    funnel legitimately — segmented out, never funnel-flagged.
  - merged_into_id soft-retires are excluded from active analysis (dedup discipline).
  - corner-lot dual-address is a PERMANENT false positive (proj136: situs "2108
    Berkeley Way" != building "1951 Shattuck", same parcel) — flag-for-review only.
  - the ADU-pair rule: same APN+addr+units is a shadow ONLY IF NOT two distinct
    real permits w/ two distinct CO dates (protects 624/869, 645/880, 362/888).
  - late-2025/2026 County recording lag: vacant-but-recent is not an error.
  - APN crosswalk is the 3-LAYER deterministic match via BOOK/PAGE/PARCEL, never
    strip-non-digits alone.

Usage:
  python scripts/shake_detectors.py --scope calibration   # CY2024 + 2 blocks, asserts known truth
  python scripts/shake_detectors.py --scope full           # all 8 years + all blocks

Output: data/audit/shake_findings_<date>.json
"""
import sqlite3, json, argparse, sys, datetime, re
from pathlib import Path
from collections import defaultdict, Counter

BASE = Path(__file__).resolve().parent.parent
V2_PATH = BASE / 'databases' / 'berkeley_housing_v2.db'
BDB_PATH = BASE / 'databases' / 'berkeley.db'   # the REFRESHED assessor ref (NOT ./berkeley.db stub)

# ---- vocabulary ids (verified 2026-06-16) ----
EVT = {  # event_type code -> id
    'application_submitted': 2, 'application_complete': 3, 'entitlement_approved': 9,
    'demo_permit_issued': 13, 'building_permit_issued': 14, 'co_issued': 17,
    'permit_finaled': 25, 'permit_classified_primary': 26, 'permit_classified_subsidiary': 27,
    'first_inspection_observed': 28, 'final_inspection_passed': 29,
}
UC_CLASSIFICATION_ID = 6
STUB_CO_DATE = '2024-01-01'                       # v1->v2 migration stub, never a real CO
CO_ONLY_ID_RANGES = [(185, 279), (280, 899)]      # the CO-only import cohort id blocks
PRE_CO_LIFECYCLE = {2, 3, 9, 13, 14}              # any of these => NOT a CO-only-cohort project
COUNTY_LAG_DAYS = 270                             # recording lag window: vacant-but-recent != error
TODAY = datetime.date(2026, 6, 16)
LOW_IMPS_PER_UNIT = 20000                         # magnitude sanity: < $20k Imps/unit on a completion is suspicious

# Known calibration anchors (for scope=calibration filtering + assertion suite)
DEDUP_PAIRS = [(86, 109), (25, 115), (113, 118), (96, 138), (127, 162), (544, 852), (179, 887)]
DEDUP_ABSORBED = [a for _, a in DEDUP_PAIRS]
DEDUP_SURVIVORS = [s for s, _ in DEDUP_PAIRS]
ADU_PROTECTED_PAIRS = [(624, 869), (645, 880), (362, 888)]
UC_PROJECTS = [165, 170, 171, 177]
CORNER_LOT_ANCHOR = 136


# ============================ CROSSWALK (3-layer, deterministic) ============================
def canon_v2_apn(apn):
    """v2 stored APN -> 12-digit canonical (book3 page4 parcel3 sub2). None if not resolvable."""
    if not apn:
        return None
    d = ''.join(c for c in apn if c.isdigit())
    if len(d) == 12:
        return d
    return None  # 8/11/51-digit etc. -> bad format, surfaced by stale_apn/phantoms


def canon_bdb_components(book, page, parcel, sub):
    """assessor BOOK/PAGE/PARCEL/SUB_PARCEL -> 12-digit canonical (the deterministic anchor)."""
    try:
        return (book or '').strip().zfill(3) + (page or '').strip().zfill(4) \
            + (parcel or '').strip().zfill(3) + (sub or '').strip().zfill(2)
    except Exception:
        return None


def build_assessor_index(bdb):
    """canonical APN -> assessor row. NOTE: ~2,677 canonical keys collapse multiple assessor
    sub-parcels (condos sharing book/page/parcel, distinct sub). Index is last-write-wins, so a
    finding on a COLLIDED key may read a sibling sub-parcel's Imps -> we return the collided set so
    built_vs_vacant/scale findings on those keys are tagged 'verify - possible sibling-parcel Imps'."""
    idx = {}
    collided = set()
    collapsed = 0   # parcels overwritten by last-write-wins (lost to a shared canonical key)
    for apn, book, page, parcel, sub, imps, land, situs, use, lot, lat, lon in bdb.execute(
        "SELECT APN,BOOK,PAGE,PARCEL,SUB_PARCEL,Imps,Land,SitusAddre,UseCode,LotSize,Latitude,Longitude FROM parcels"):
        c = canon_bdb_components(book, page, parcel, sub)
        if not c:
            continue
        if c in idx:
            collided.add(c)
            collapsed += 1
        idx[c] = {'apn': apn, 'imps': imps or 0.0, 'land': land or 0.0, 'situs': situs or '',
                  'usecode': str(use or ''), 'lotsize': lot, 'lat': lat, 'lon': lon, 'book': book, 'page': page}
    return idx, collided, collapsed


def parse_lotsize(lot):
    if lot is None:
        return None
    try:
        return float(str(lot).replace(',', ''))
    except Exception:
        return None


# normalize a street address for comparison (number + street stem)
_ORD = {'first': '1st', 'second': '2nd', 'third': '3rd', 'fourth': '4th', 'fifth': '5th',
        'sixth': '6th', 'seventh': '7th', 'eighth': '8th', 'ninth': '9th', 'tenth': '10th'}
_SUF = re.compile(r'\b(ave|avenue|st|street|blvd|boulevard|way|dr|drive|rd|road|ln|lane|ct|court|pl|place|ter|terrace)\b')


def norm_addr(a):
    if not a:
        return ('', '')
    s = a.lower()
    # drop ONLY the trailing "<city> <zip>" tail (assessor situs has it) — must NOT eat a
    # street named "Berkeley Way" (the proj136 corner-lot case). Strip city+zip at end only.
    s = re.sub(r'\s+berkeley\s*,?\s*(ca\s*)?\d{5}(-\d+)?\s*$', '', s)
    s = re.sub(r'\s+berkeley\s*$', '', s)
    for w, n in _ORD.items():
        s = re.sub(r'\b' + w + r'\b', n, s)
    m = re.match(r'\s*(\d+)', s)
    num = m.group(1) if m else ''
    street = _SUF.sub('', s)
    street = re.sub(r'[^a-z0-9 ]', ' ', street)
    street = re.sub(r'^\s*\d+\s*', '', street).strip()
    street = re.sub(r'\s+', ' ', street)
    return (num, street)


# ============================ DB CONTEXT ============================
class Ctx:
    def __init__(self):
        self.v2 = sqlite3.connect(f'file:{V2_PATH}?mode=ro', uri=True)
        self.bdb = sqlite3.connect(f'file:{BDB_PATH}?mode=ro', uri=True)
        self.v2.row_factory = sqlite3.Row
        self.assessor, self.collided_keys, self.collapsed_parcels = build_assessor_index(self.bdb)
        self.assessor_dupes = len(self.collided_keys)
        # active projects (merged_into_id IS NULL)
        self.merged = {r['id']: r['merged_into_id'] for r in
                       self.v2.execute("SELECT id, merged_into_id FROM projects WHERE merged_into_id IS NOT NULL")}
        self.active_ids = {r[0] for r in self.v2.execute("SELECT id FROM projects WHERE merged_into_id IS NULL")}
        self.uc_ids = {r[0] for r in self.v2.execute(
            "SELECT project_id FROM project_classifications WHERE classification_type_id=?", (UC_CLASSIFICATION_ID,))}
        # event types present per project
        self.evt_types = defaultdict(set)
        for pid, et in self.v2.execute("SELECT project_id, event_type_id FROM project_events"):
            self.evt_types[pid].add(et)
        # CO-only cohort: id in ranges AND no pre-CO lifecycle event
        self.co_only = set()
        for pid in self.active_ids:
            in_range = any(lo <= pid <= hi for lo, hi in CO_ONLY_ID_RANGES)
            if in_range and not (self.evt_types[pid] & PRE_CO_LIFECYCLE):
                self.co_only.add(pid)
        # r2 doc coverage (resolvability)
        self.r2_projects = {r[0] for r in self.v2.execute(
            "SELECT DISTINCT project_id FROM documents WHERE r2_url IS NOT NULL AND r2_url!=''")}
        # primary parcel apn per project
        self.primary_apn = {}
        for pid, apn, addr in self.v2.execute("""
                SELECT pp.project_id, pk.apn, pk.address FROM project_parcels pp
                JOIN parcels pk ON pk.id=pp.parcel_id WHERE pp.is_primary=1"""):
            self.primary_apn[pid] = {'apn': apn, 'addr': addr, 'canon': canon_v2_apn(apn)}

    def resolvability(self, pid):
        return 'has_r2_doc' if pid in self.r2_projects else 'needs_harvest'


def finding(check, key, severity, signal, evidence, classification, expected_filter, resolvability=None):
    return {'check': check, 'key': key, 'severity': severity, 'signal': signal,
            'classification': classification, 'expected_filter': expected_filter,
            'resolvability': resolvability, 'evidence': evidence}


# ============================ LIFECYCLE ============================
def check_funnel_per_year(ctx):
    """projects+units per stage per CY — DESCRIPTIVE aux table only.
       (In-year co-vs-bp is NOT a funnel inversion: completions and permits in the same year are
       different project cohorts. Real project-level inversion is covered by stage_skip. No flags here.)"""
    stages = {'entitled': EVT['entitlement_approved'], 'bp': EVT['building_permit_issued'], 'co': EVT['co_issued']}
    table = defaultdict(lambda: defaultdict(set))
    table_nc = defaultdict(lambda: defaultdict(set))
    for pid, et, ed in ctx.v2.execute("SELECT project_id,event_type_id,event_date FROM project_events WHERE event_date>'2000'"):
        if pid not in ctx.active_ids:
            continue
        for name, eid in stages.items():
            if et == eid:
                table[ed[:4]][name].add(pid)
                if pid not in ctx.co_only:
                    table_nc[ed[:4]][name].add(pid)
    summary = {y: {**{s: len(table[y][s]) for s in stages},
                   **{f'{s}_non_cohort': len(table_nc[y][s]) for s in stages}} for y in sorted(table)}
    return [], {'funnel_by_year': summary, 'co_only_cohort_size': len(ctx.co_only)}


def check_stage_skip(ctx):
    """completed (co set) but NO building_permit_issued event. EXCLUDE UC; TAG CO-only cohort; flag the rest."""
    findings = []
    for r in ctx.v2.execute(f"""
            SELECT project_id,total_units,co_issued_date FROM v_projects_flat
            WHERE co_issued_date IS NOT NULL AND co_issued_date!='' AND co_issued_date<>'{STUB_CO_DATE}'"""):
        pid = r['project_id']
        has_bp = EVT['building_permit_issued'] in ctx.evt_types[pid]
        if has_bp:
            continue
        if pid in ctx.uc_ids:
            continue  # UC legitimately skips city permitting
        if pid in ctx.co_only:
            findings.append(finding('stage_skip', pid, 'info',
                f'proj{pid} completed without a BP event — CO-only import cohort (event-funnel meaningless)',
                {'co_date': r['co_issued_date'], 'units': r['total_units']},
                'expected_co_only_cohort', 'CO-only cohort (id block, no lifecycle events) — segmented out',
                ctx.resolvability(pid)))
        else:
            findings.append(finding('stage_skip', pid, 'medium',
                f'proj{pid} completed (CO {r["co_issued_date"]}) but has NO building_permit_issued event — genuine gap',
                {'co_date': r['co_issued_date'], 'units': r['total_units'],
                 'event_types_present': sorted(ctx.evt_types[pid])},
                'review', 'not UC, not CO-only cohort', ctx.resolvability(pid)))
    return findings, {}


def check_monotonicity(ctx):
    """stage dates should be non-decreasing: app_sub <= app_complete <= entitlement <= bp <= co.
       Year-precision stub events (2024-01-01/2025-01-01 class) flagged as date-stub, not ordering error."""
    findings = []
    order = ['application_submitted', 'application_complete', 'entitlement_approved',
             'building_permit_issued', 'co_issued']
    firsts = defaultdict(dict)   # pid -> code -> (date, precision)
    for pid, et, ed, prec in ctx.v2.execute(
            "SELECT project_id,event_type_id,event_date,event_date_precision FROM project_events WHERE event_date>'2000'"):
        if pid not in ctx.active_ids:
            continue
        for code in order:
            if et == EVT[code]:
                cur = firsts[pid].get(code)
                if cur is None or ed < cur[0]:
                    firsts[pid][code] = (ed, prec)
    for pid, d in firsts.items():
        seq = [(c, d[c][0], d[c][1]) for c in order if c in d]
        for i in range(1, len(seq)):
            (pc, pd, pp), (cc, cd, cpr) = seq[i - 1], seq[i]
            if cd < pd:
                is_stub = (cpr == 'year' or pp == 'year' or cd.endswith('-01-01') or pd.endswith('-01-01'))
                findings.append(finding('monotonicity', pid, 'low' if is_stub else 'medium',
                    f'proj{pid}: {cc} ({cd}) precedes {pc} ({pd}) — out of order',
                    {'earlier_stage': pc, 'earlier_date': pd, 'later_stage': cc, 'later_date': cd},
                    'date_stub' if is_stub else 'review',
                    'year-precision entitlement-stub class' if is_stub else 'real ordering violation',
                    ctx.resolvability(pid)))
    return findings, {}


def check_unit_drift(ctx):
    """unit count across project_versions revisions (NOT events; units_affected is 100% NULL).
       Latest approved revision is truth; flag projects whose versions disagree (informational)."""
    findings = []
    vers = defaultdict(list)
    for pid, tu, cur, eff in ctx.v2.execute(
            "SELECT project_id,total_units,is_current,effective_date FROM project_versions WHERE total_units IS NOT NULL"):
        if pid in ctx.active_ids:
            vers[pid].append((tu, cur, eff))
    for pid, vs in vers.items():
        units = [v[0] for v in vs]
        if len(set(units)) > 1:
            current = next((v[0] for v in vs if v[1]), units[-1])
            findings.append(finding('unit_drift', pid, 'low',
                f'proj{pid}: unit count varies across {len(vs)} versions {sorted(set(units))} — current(truth)={current}',
                {'versions': units, 'current_truth': current, 'spread': max(units) - min(units)},
                'review', 'latest approved revision is truth (info only)', ctx.resolvability(pid)))
    return findings, {}


# ============================ IDENTITY ============================
def _is_protected_adu(ctx, pids):
    """ADU-pair rule: >=2 projects with their own 'completes' permit AND >=2 distinct CO dates."""
    perms = {pid: _completing_permits(ctx, pid) for pid in pids}
    n_real = sum(1 for pid in pids if perms[pid])
    all_co = {d for pid in pids for _, d in perms[pid] if d}
    return (n_real >= 2 and len(all_co) >= 2), perms, sorted(all_co)


def check_apn_collisions(ctx):
    """one canonical APN -> multiple ACTIVE projects. Classify: phasing / protected-ADU-pair / duplicate."""
    findings = []
    by_apn = defaultdict(list)
    for pid, info in ctx.primary_apn.items():
        if pid in ctx.active_ids and info['canon']:
            by_apn[info['canon']].append(pid)
    for canon, pids in by_apn.items():
        if len(pids) < 2:
            continue
        names = {pid: ctx.primary_apn[pid]['addr'] for pid in pids}
        distinct_addr = len(set(a or '' for a in names.values()))
        is_adu, perms, co_dates = _is_protected_adu(ctx, pids)
        if distinct_addr > 1:
            cls, sev, exp = 'phasing_or_multibuilding', 'low', 'distinct addresses => legit phasing (Acheson-style)'
        elif is_adu:
            cls, sev, exp = 'protected_adu_pair', 'low', 'ADU-pair rule: 2 real permits + 2 distinct COs = 2 real buildings, never merge'
        else:
            cls, sev, exp = 'duplicate_candidate', 'medium', 'same address, no two-real-permit/two-CO evidence => possible duplicate'
        findings.append(finding('apn_collisions', canon, sev,
            f'APN {canon} shared by {len(pids)} active projects: {pids}',
            {'projects': pids, 'addresses': names, 'assessor': ctx.assessor.get(canon, {}).get('apn'),
             'distinct_co_dates': co_dates},
            cls, exp))
    return findings, {}


def check_address_apn_consistency(ctx):
    """our address vs County situs. Classify by (house-number match, street match):
       num+street match => consistent (skip); num match + street differ => street_name_variance
       (abbreviation noise, e.g. MLK=M L King); street match + num differ => house_number_discrepancy;
       both differ => corner-lot/wrong-parcel (proj136 dual-frontage — PERMANENT FP, flag-for-review)."""
    findings = []
    for pid, info in ctx.primary_apn.items():
        if pid not in ctx.active_ids or not info['canon']:
            continue
        a = ctx.assessor.get(info['canon'])
        if not a:
            continue  # handled by stale_apn
        our_num, our_st = norm_addr(info['addr'])
        cty_num, cty_st = norm_addr(a['situs'])
        if not our_st or not cty_st:
            continue
        num_match = (our_num == cty_num and our_num != '')
        st_match = (our_st == cty_st)
        if num_match and st_match:
            continue  # consistent
        if num_match and not st_match:
            cls, sev, exp = 'street_name_variance', 'low', \
                'same house number, street label/abbrev differs (e.g. MLK = M L King) — likely same address'
        elif st_match and not num_match:
            cls, sev, exp = 'house_number_discrepancy', 'medium', \
                'same street, different house number — review (possible wrong unit/parcel)'
        else:
            cls, sev, exp = 'expected_corner_lot', 'low', \
                'different street AND number = dual-frontage corner lot (PERMANENT FP) or wrong parcel — flag-for-review, never auto-fix'
        findings.append(finding('address_apn_consistency', pid, sev,
            f'proj{pid} addr "{info["addr"]}" vs County situs "{a["situs"]}" (APN {a["apn"]})',
            {'our_addr': info['addr'], 'county_situs': a['situs'], 'apn': a['apn'],
             'our': [our_num, our_st], 'county': [cty_num, cty_st]},
            cls, exp, ctx.resolvability(pid)))
    return findings, {}


def check_stale_apn(ctx):
    """v2 primary APN absent from CURRENT assessor => orphaned/re-platted (not staleness now)."""
    findings = []
    for pid, info in ctx.primary_apn.items():
        if pid not in ctx.active_ids:
            continue
        if info['canon'] is None:
            findings.append(finding('stale_apn', pid, 'medium',
                f'proj{pid} APN "{info["apn"]}" is not a resolvable 12-digit APN (bad format)',
                {'stored_apn': info['apn']}, 'bad_format', 'non-12-digit stored APN', ctx.resolvability(pid)))
            continue
        if info['canon'] in ctx.assessor:
            continue
        # absent from current assessor: classify re-plat vs too-new (recent County lag)
        co = ctx.v2.execute("SELECT co_issued_date,bp_issued_date FROM v_projects_flat WHERE project_id=?", (pid,)).fetchone()
        recent = False
        if co and (co[0] or co[1]):
            d = co[0] or co[1]
            try:
                recent = (TODAY - datetime.date.fromisoformat(d[:10])).days < COUNTY_LAG_DAYS
            except Exception:
                pass
        cls = 'too_new_county_lag' if recent else 'orphaned_or_replatted_crosswalk_queue'
        findings.append(finding('stale_apn', pid, 'low' if recent else 'medium',
            f'proj{pid} APN {info["canon"]} ("{info["apn"]}") absent from Feb-2026 assessor',
            {'canon': info['canon'], 'stored_apn': info['apn'], 'addr': info['addr'],
             'co_or_bp': (co[0] or co[1]) if co else None},
            cls, 'recent completion within County lag window' if recent else 'crosswalk queue (prior-APN/re-plat lineage)',
            ctx.resolvability(pid)))
    return findings, {}


def _completing_permits(ctx, pid):
    """permits on a project with a 'completes' verdict and a finaled/co date — for the ADU-pair rule."""
    rows = ctx.v2.execute("""
        SELECT permit_number, completion_verdict, finaled_date, issued_date FROM permits
        WHERE project_id=? AND completion_verdict='completes'""", (pid,)).fetchall()
    return [(r[0], r[2] or r[3]) for r in rows]


def check_shadows(ctx):
    """same canonical APN + same units across >=2 active projects: SHADOW unless two distinct real
       permits w/ two distinct CO dates (ADU-pair rule => PROTECT)."""
    findings = []
    by_key = defaultdict(list)
    for pid, info in ctx.primary_apn.items():
        if pid not in ctx.active_ids or not info['canon']:
            continue
        tu = ctx.v2.execute("SELECT total_units FROM v_projects_flat WHERE project_id=?", (pid,)).fetchone()
        units = tu[0] if tu else None
        by_key[(info['canon'], units)].append(pid)
    for (canon, units), pids in by_key.items():
        if len(pids) < 2:
            continue
        # gather completing permits + distinct co dates per project
        perms = {pid: _completing_permits(ctx, pid) for pid in pids}
        co_dates = {pid: {d for _, d in perms[pid] if d} for pid in pids}
        n_with_real = sum(1 for pid in pids if perms[pid])
        all_co = set()
        for pid in pids:
            all_co |= co_dates[pid]
        two_real_two_co = (n_with_real >= 2 and len(all_co) >= 2)
        cls = 'protected_adu_pair' if two_real_two_co else 'shadow_candidate'
        findings.append(finding('shadows', f'{canon}|{units}u', 'low' if two_real_two_co else 'high',
            f'APN {canon} + {units}u shared by {pids}: '
            + ('two real permits + distinct COs => REAL buildings (protect)' if two_real_two_co
               else 'shadow candidate (no two-real-permit/two-CO evidence)'),
            {'projects': pids, 'units': units, 'completing_permits': perms, 'distinct_co_dates': sorted(all_co)},
            cls, 'ADU-pair rule: 2 real permits + 2 distinct COs = 2 real buildings, never merge'))
    return findings, {}


def check_phantoms(ctx):
    """orphan completion events, permits w/o APN, projects w/ zero events, merged-away leaks."""
    findings = []
    # merged projects leaking into v_projects_flat (the view must filter them)
    leaked = ctx.v2.execute(f"""
        SELECT project_id FROM v_projects_flat WHERE project_id IN
        (SELECT id FROM projects WHERE merged_into_id IS NOT NULL)""").fetchall()
    for r in leaked:
        findings.append(finding('phantoms', r[0], 'high',
            f'MERGED project {r[0]} (merged_into_id set) is LEAKING into v_projects_flat',
            {'project_id': r[0], 'merged_into_id': ctx.merged.get(r[0])},
            'merged_leak', 'soft-retire view filter (merged_into_id IS NULL)'))
    # co_issued events whose project is missing/merged
    for pid, n in ctx.v2.execute(f"""
            SELECT project_id, COUNT(*) FROM project_events WHERE event_type_id={EVT['co_issued']}
            AND project_id NOT IN (SELECT id FROM projects WHERE merged_into_id IS NULL) GROUP BY project_id"""):
        findings.append(finding('phantoms', pid, 'medium',
            f'{n} co_issued event(s) on project {pid} which is not active (missing or merged)',
            {'project_id': pid, 'co_events': n, 'merged_into_id': ctx.merged.get(pid)},
            'merged_or_orphan_event', 'merged_into_id soft-retire'))
    # active projects with zero lifecycle events (UC = expected: off the city permitting grid)
    for pid in ctx.active_ids:
        if not ctx.evt_types[pid]:
            uc = pid in ctx.uc_ids
            findings.append(finding('phantoms', pid, 'info' if uc else 'low',
                f'active project {pid} has ZERO events' + (' (UC)' if uc else ''), {'project_id': pid, 'is_uc': uc},
                'uc_no_events' if uc else 'no_events',
                'UC project (UC issues its own permits) — expected' if uc else 'none (genuine gap)',
                ctx.resolvability(pid)))
    # active primary parcels with no/unresolvable APN (UC = expected: off the city APN grid)
    for pid in ctx.active_ids:
        if ctx.primary_apn.get(pid) is None:
            uc = pid in ctx.uc_ids
            findings.append(finding('phantoms', pid, 'info' if uc else 'medium',
                f'active project {pid} has NO primary parcel' + (' (UC)' if uc else ''), {'project_id': pid, 'is_uc': uc},
                'uc_no_parcel' if uc else 'no_parcel',
                'UC project (UC land / Regents, off city APN grid) — expected' if uc else 'none (genuine gap)',
                ctx.resolvability(pid)))
    return findings, {}


# ============================ ASSESSOR-ORACLE ============================
def check_built_vs_vacant(ctx):
    """completed projects -> parcel Imps>0? Imps=0 on a completion = wrong-APN or recent-lag.
       Magnitude: Imps should scale with units."""
    findings = []
    for r in ctx.v2.execute(f"""
            SELECT project_id,total_units,co_issued_date FROM v_projects_flat
            WHERE co_issued_date IS NOT NULL AND co_issued_date!='' AND co_issued_date<>'{STUB_CO_DATE}'"""):
        pid = r['project_id']
        if pid not in ctx.active_ids:
            continue
        info = ctx.primary_apn.get(pid)
        if not info or not info['canon']:
            continue  # stale_apn/phantoms territory
        a = ctx.assessor.get(info['canon'])
        if not a:
            continue  # stale_apn territory
        co = r['co_issued_date']
        try:
            recent = (TODAY - datetime.date.fromisoformat(co[:10])).days < COUNTY_LAG_DAYS
        except Exception:
            recent = False
        is_uc = pid in ctx.uc_ids
        imps = a['imps']
        units = r['total_units'] or 0
        sib = info['canon'] in ctx.collided_keys   # collided canonical key => Imps may be a sibling sub-parcel's
        sib_note = ' | VERIFY: collided canonical key — Imps may be from a sibling sub-parcel' if sib else ''
        if imps <= 0:
            cls = ('uc_offsite_parcel' if is_uc else ('too_new_county_lag' if recent else 'wrong_apn_or_unbuilt'))
            sev = 'low' if (recent or is_uc) else 'high'
            findings.append(finding('built_vs_vacant', pid, sev,
                f'proj{pid} completed (CO {co}, {units}u) but parcel {a["apn"]} reads Imps=$0 (vacant)',
                {'co_date': co, 'units': units, 'apn': a['apn'], 'imps': imps, 'usecode': a['usecode'],
                 'recent_within_lag': recent, 'is_uc': is_uc, 'sibling_parcel_risk': sib},
                cls,
                ('UC group quarters / off-site parcel' if is_uc else
                 ('recent completion within County lag' if recent else 'completion should be built')) + sib_note,
                ctx.resolvability(pid)))
        elif units >= 5 and imps / max(units, 1) < LOW_IMPS_PER_UNIT and not is_uc:
            findings.append(finding('built_vs_vacant', pid, 'medium',
                f'proj{pid} {units}u completed but Imps ${imps:,.0f} = ${imps/units:,.0f}/unit (suspiciously low)',
                {'co_date': co, 'units': units, 'apn': a['apn'], 'imps': imps, 'imps_per_unit': round(imps / units),
                 'sibling_parcel_risk': sib},
                'low_magnitude', f'Imps/unit < ${LOW_IMPS_PER_UNIT:,} (possible wrong-parcel/partial)' + sib_note,
                ctx.resolvability(pid)))
    return findings, {}


def check_usecode_sanity(ctx):
    """completed-housing on a clearly non-residential UseCode (commercial/industrial 3xxx-6xxx) => flag-for-review.
       (residential 1xxx-2xxx, institutional/UC 7xxx are expected; mixed-use towers may be coded commercial.)"""
    findings = []
    for r in ctx.v2.execute(f"""
            SELECT project_id,total_units,co_issued_date FROM v_projects_flat
            WHERE co_issued_date IS NOT NULL AND co_issued_date!='' AND co_issued_date<>'{STUB_CO_DATE}'"""):
        pid = r['project_id']
        if pid not in ctx.active_ids:
            continue
        info = ctx.primary_apn.get(pid)
        if not info or not info['canon']:
            continue
        a = ctx.assessor.get(info['canon'])
        if not a or not a['usecode']:
            continue
        uc = a['usecode']
        lead = uc[0] if uc else ''
        if lead in ('3', '4', '5', '6'):   # commercial / industrial / misc — not residential
            findings.append(finding('usecode_sanity', pid, 'low',
                f'proj{pid} completed housing ({r["total_units"]}u) on UseCode {uc} (non-residential code)',
                {'units': r['total_units'], 'apn': a['apn'], 'usecode': uc, 'co_date': r['co_issued_date']},
                'review', 'mixed-use towers may carry a commercial code — review, not error',
                ctx.resolvability(pid)))
    return findings, {}


def check_scale_sanity(ctx):
    """LotSize vs unit count: many units on a tiny lot w/ no vertical justification => wrong-parcel/units."""
    findings = []
    for r in ctx.v2.execute("""
            SELECT project_id,total_units,height_stories,co_issued_date FROM v_projects_flat
            WHERE total_units IS NOT NULL AND total_units>=20"""):
        pid = r['project_id']
        if pid not in ctx.active_ids:
            continue
        info = ctx.primary_apn.get(pid)
        if not info or not info['canon']:
            continue
        a = ctx.assessor.get(info['canon'])
        if not a:
            continue
        lot = parse_lotsize(a['lotsize'])
        if lot is None or lot <= 0:
            continue
        stories = r['height_stories'] or 0
        sib = info['canon'] in ctx.collided_keys
        sib_note = ' | VERIFY: collided canonical key — LotSize may be from a sibling sub-parcel' if sib else ''
        # implausible only if dense AND no vertical justification (low/unknown stories)
        if lot < 2500 and r['total_units'] >= 30 and stories < 4:
            findings.append(finding('scale_sanity', pid, 'medium',
                f'proj{pid}: {r["total_units"]}u on {lot:.0f} sqft lot, {stories or "unknown"} stories — implausibly dense',
                {'units': r['total_units'], 'lotsize': lot, 'stories': stories, 'apn': a['apn'],
                 'sibling_parcel_risk': sib},
                'review', 'high-rise (>=4 stories) excluded as legit density' + sib_note, ctx.resolvability(pid)))
    return findings, {}


# ============================ BLOCK COHORTS ============================
BLINDSPOT_RECENT_YEAR = '2023'        # LatestDocumentDate >= this = recent development (proxy)
BLINDSPOT_HIGH_IMPS = 2_000_000       # Imps suggesting multi-unit scale (RHNA-relevant)


def check_block_cohort(ctx, blocks):
    """census every assessor parcel on a block (BOOK-PAGE). Census counts ALL untracked-built-housing,
       but a BLIND-SPOT FINDING is emitted only for parcels showing RECENT development
       (LatestDocumentDate >= 2023) OR multi-unit-scale Imps — existing old single-family stock is
       expected-untracked, not signal (we model projects, not every house). LatestDocumentDate is a
       RECORDING date (may be a sale, not construction) -> finding says 'verify'."""
    findings = []
    census = {}
    tracked_canon = {info['canon'] for pid, info in ctx.primary_apn.items()
                     if pid in ctx.active_ids and info['canon']}
    for book, page in blocks:
        rows = ctx.bdb.execute(
            "SELECT APN,BOOK,PAGE,PARCEL,SUB_PARCEL,Imps,UseCode,SitusAddre,LatestDocumentDate FROM parcels WHERE BOOK=? AND PAGE=?",
            (book, page)).fetchall()
        b = {'block': f'{book}-{page}', 'parcels': len(rows), 'tracked': 0,
             'untracked_built_housing_total': 0, 'untracked_built_housing_flagged': 0}
        for apn, bk, pg, pa, sub, imps, use, situs, ldd in rows:
            c = canon_bdb_components(bk, pg, pa, sub)
            if c in tracked_canon:
                b['tracked'] += 1
                continue
            imps = imps or 0
            housing = str(use or '')[:1] in ('1', '2')
            if imps > 0 and housing:
                b['untracked_built_housing_total'] += 1
                recent = bool(ldd and ldd >= BLINDSPOT_RECENT_YEAR)
                big = imps >= BLINDSPOT_HIGH_IMPS
                if recent or big:
                    b['untracked_built_housing_flagged'] += 1
                    findings.append(finding('block_cohort', f'{book}-{page}:{apn}', 'medium',
                        f'BLIND SPOT: untracked built-housing parcel {apn} ("{situs}") on block {book}-{page}'
                        + (f' — recent record {ldd}' if recent else '') + (f' — Imps ${imps:,.0f} (multi-unit scale)' if big else ''),
                        {'apn': apn, 'situs': situs, 'imps': imps, 'usecode': use,
                         'latest_doc_date': ldd, 'recent': recent, 'high_imps': big},
                        'untracked_built_housing',
                        'qualified by recency/magnitude; LatestDocumentDate is a recording date (verify vs construction)'))
        census[f'{book}-{page}'] = b
    return findings, {'block_census': census}


# ============================ RUNNER ============================
CHECKS = [check_funnel_per_year, check_stage_skip, check_monotonicity, check_unit_drift,
          check_apn_collisions, check_address_apn_consistency, check_stale_apn, check_shadows,
          check_phantoms, check_built_vs_vacant, check_usecode_sanity, check_scale_sanity]


def calibration_blocks(ctx):
    """the 2 known calibrated blocks: proj136's block (corner-lot/Acheson) + first ADU pair's block."""
    blocks = []
    for pid in (CORNER_LOT_ANCHOR, ADU_PROTECTED_PAIRS[0][0]):
        info = ctx.primary_apn.get(pid)
        if info and info['canon']:
            a = ctx.assessor.get(info['canon'])
            # derive BOOK/PAGE from the canonical (book=first3, page=next4) -> assessor stores unpadded
            book = str(int(info['canon'][:3])); page = info['canon'][3:7]
            blocks.append((book, page))
    return list(dict.fromkeys(blocks))


def run(scope, out_path):
    ctx = Ctx()
    all_findings = []
    aux = {}
    blocks = calibration_blocks(ctx) if scope == 'calibration' else None
    for fn in CHECKS:
        f, a = fn(ctx)
        all_findings.extend(f)
        aux.update(a)
    bf, ba = check_block_cohort(ctx, blocks if blocks else all_blocks(ctx))
    all_findings.extend(bf)
    aux.update(ba)

    # scope filter for calibration: keep findings touching the calibration anchor set or the 2 blocks
    anchors = set([CORNER_LOT_ANCHOR] + DEDUP_SURVIVORS + DEDUP_ABSORBED + UC_PROJECTS
                  + [p for pair in ADU_PROTECTED_PAIRS for p in pair])
    if scope == 'calibration':
        def touches(f):
            k = f['key']
            if isinstance(k, int):
                return k in anchors
            return any(str(p) in str(k) for p in anchors) or f['check'] in ('block_cohort', 'funnel_per_year')
        emitted = [f for f in all_findings if touches(f)]
    else:
        emitted = all_findings

    # intersections: keys flagged by >1 check (high-confidence edge cases)
    by_proj = defaultdict(set)
    for f in emitted:
        if isinstance(f['key'], int):
            by_proj[f['key']].add(f['check'])
    intersections = {pid: sorted(chk) for pid, chk in by_proj.items() if len(chk) > 1}

    grouped = defaultdict(list)
    for f in emitted:
        grouped[f['check']].append(f)

    result = {
        'generated': TODAY.isoformat(),
        'scope': scope,
        'db': {'v2': str(V2_PATH), 'assessor': str(BDB_PATH),
               'assessor_parcels_indexed': len(ctx.assessor),
               'assessor_collided_keys': ctx.assessor_dupes, 'assessor_collapsed_parcels': ctx.collapsed_parcels},
        'cohorts': {'active_projects': len(ctx.active_ids), 'merged_soft_retired': len(ctx.merged),
                    'co_only_cohort': len(ctx.co_only), 'uc_projects': sorted(ctx.uc_ids)},
        'caveats': [
            {'caveat': 'assessor_canonical_key_collisions',
             'collided_keys': ctx.assessor_dupes, 'collapsed_parcels': ctx.collapsed_parcels,
             'note': f'{ctx.assessor_dupes} canonical APN keys (book3+page4+parcel3+sub2) collide, collapsing '
                     f'{ctx.collapsed_parcels} assessor sub-parcels (condos sharing book/page/parcel, distinct sub) '
                     'via last-write-wins. So Imps/LotSize on a collided key may be a SIBLING sub-parcel. '
                     'built_vs_vacant + scale_sanity findings on collided keys carry sibling_parcel_risk=true and '
                     'a VERIFY note. Not fixed — recorded so collided-key findings are not mistaken for clean.'},
            {'caveat': 'co_only_cohort_measured',
             'count': len(ctx.co_only),
             'note': 'CO-only import cohort (id blocks 185-279 + 280-899 with no pre-CO lifecycle event) = '
                     'the MEASURED count, not the stale ~597 estimate. Event-funnel/stage metrics are '
                     'meaningless for these — segmented out of funnel/stage_skip flagging (tagged info).'},
            {'caveat': 'latest_document_date_is_recording_date',
             'note': 'berkeley.db LatestDocumentDate is a County RECORDING date (may be a sale, not '
                     'construction). block_cohort blind-spots use it as a recency proxy and say VERIFY; '
                     'never treat it as a build date.'},
        ],
        'finding_counts': {chk: len(rows) for chk, rows in sorted(grouped.items())},
        'intersections_multi_check': intersections,
        'aux': aux,
        'findings_by_check': {chk: rows for chk, rows in sorted(grouped.items())},
    }
    if scope == 'calibration':
        result['calibration_assertions'] = run_calibration_assertions(ctx, all_findings)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as fh:
        json.dump(result, fh, indent=2, default=str)
    return result


def all_blocks(ctx):
    return [(str(b), p) for b, p in ctx.bdb.execute("SELECT DISTINCT BOOK,PAGE FROM parcels")]


def run_calibration_assertions(ctx, all_findings):
    """programmatic KNOWN-TRUTH checks: reproduce findings WITHOUT re-flagging resolved items."""
    A = []

    def rec(name, ok, detail):
        A.append({'assertion': name, 'PASS': bool(ok), 'detail': detail})

    # A1: no merged-absorbed project appears as an ACTIVE anomaly (only as expected merged_leak=0)
    active_merged = [f for f in all_findings if isinstance(f['key'], int) and f['key'] in DEDUP_ABSORBED
                     and f['classification'] not in ('merged_leak', 'merged_or_orphan_event')]
    rec('merged_absorbed_not_active_anomaly', len(active_merged) == 0,
        f'{len(active_merged)} active-anomaly findings on absorbed ids (expect 0): '
        + str([(f['key'], f['check']) for f in active_merged][:8]))

    # A1b: no merged leak into v_projects_flat
    leaks = [f for f in all_findings if f['check'] == 'phantoms' and f['classification'] == 'merged_leak']
    rec('no_merged_leak_into_view', len(leaks) == 0, f'{len(leaks)} merged projects leaking (expect 0)')

    # A2: proj136 in address_apn_consistency classified corner-lot EXPECTED
    p136_addr = [f for f in all_findings if f['check'] == 'address_apn_consistency' and f['key'] == CORNER_LOT_ANCHOR]
    rec('proj136_corner_lot_expected',
        len(p136_addr) == 1 and p136_addr[0]['classification'] == 'expected_corner_lot',
        str([(f['key'], f['classification']) for f in p136_addr]))

    # A3: proj136 NOT flagged by built_vs_vacant (Imps $70M)
    p136_bvv = [f for f in all_findings if f['check'] == 'built_vs_vacant' and f['key'] == CORNER_LOT_ANCHOR]
    rec('proj136_passes_built_vs_vacant', len(p136_bvv) == 0,
        f'expect 0 built_vs_vacant findings for proj136, got {len(p136_bvv)}')

    # A4: protected ADU pairs NOT shadow_candidate (either protected_adu_pair or absent)
    bad_adu = [f for f in all_findings if f['check'] == 'shadows' and f['classification'] == 'shadow_candidate'
               and any(str(p) in str(f['key']) or p in f['evidence'].get('projects', []) for pair in ADU_PROTECTED_PAIRS for p in pair)]
    rec('adu_pairs_not_shadows', len(bad_adu) == 0,
        f'{len(bad_adu)} ADU pairs wrongly flagged shadow_candidate (expect 0)')

    # A5: stale_apn surfaces the crosswalk queue (orphans present, classified crosswalk/queue)
    stale = [f for f in all_findings if f['check'] == 'stale_apn'
             and f['classification'] == 'orphaned_or_replatted_crosswalk_queue']
    rec('stale_apn_surfaces_crosswalk_queue', len(stale) > 0,
        f'{len(stale)} orphaned/re-plat crosswalk-queue items surfaced')

    return {'all_pass': all(a['PASS'] for a in A), 'assertions': A}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Deterministic read-only anomaly detector (NEVER writes the DBs).')
    ap.add_argument('--scope', choices=['calibration', 'full'], default='calibration')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    out = args.out or str(BASE / 'data' / 'audit' / f'shake_findings_{TODAY.isoformat()}_{args.scope}.json')
    res = run(args.scope, out)
    print(f"scope={args.scope}  active={res['cohorts']['active_projects']}  "
          f"co_only={res['cohorts']['co_only_cohort']}  assessor_idx={res['db']['assessor_parcels_indexed']}")
    print("finding counts:", json.dumps(res['finding_counts'], indent=2))
    if 'calibration_assertions' in res:
        ca = res['calibration_assertions']
        print(f"\nCALIBRATION ASSERTIONS — all_pass={ca['all_pass']}")
        for a in ca['assertions']:
            print(f"  [{'PASS' if a['PASS'] else 'FAIL'}] {a['assertion']}: {a['detail']}")
    print(f"\nwrote {out}")
