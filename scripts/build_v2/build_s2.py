"""S2 — materialize dated milestone EVENTS onto the s1_projects spine (the v2-from-sources rebuild).

================================ WHAT S2 TEACHES (read this first) ================================
A milestone is a DATED EVENT WITH A SOURCE AND AN HONEST INFERENCE FLAG — not a status string copied
forward. The old migration's error was exactly that: it set a project's "stage" from a v1 status
string and stamped everything is_inferred=0 / confidence=high whether or not any evidence backed it.

S2 inverts that. For every event we record FOUR things:
  (event_type, date, SOURCE, is_inferred)
and we obey one rule that makes the whole rebuild trustworthy:

  *** is_inferred = 0 is a PROMISE that a real STRUCTURED COLUMN backs this value. ***
  If a date comes straight from a structured CPRA column (Issuance Date / Finaled Date) -> is_inferred=0.
  If we had to GUESS or DERIVE it with no column behind it -> is_inferred=1 (or we don't assert it at all).

Where a source is silent (entitlement approval DATES are not a clean field in the planning scrapes),
we FLAG the gap as needs_acquisition rather than invent a plausible date. Honest absence beats
fabricated precision — fabricated precision is what made the old DB untrustworthy.
==================================================================================================

Imports the key canon from s0_keys (never reimplemented). --preview is READ-ONLY (no DB write).
"""
import sqlite3, sys, os, re, glob, argparse
from collections import defaultdict, Counter
import pandas as pd
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
from s0_keys import normalize_address                 # THE address-key canon (one definition, imported)
from housing_predicates import is_housing, net_units   # THE shared housing predicates (same as S1, no drift)
from gating import snapshot_v3                          # the SHARED snapshot helper (refuses to clobber)
from cpra_dedup import extract_master_permit           # collapses -REV/-DEF suffixes to the master permit

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
V3 = os.path.join(ROOT, 'databases', 'berkeley_housing_v3.db')
V2 = os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')
CPRA = [os.path.join(ROOT, 'data/raw/cpra-downloads', f) for f in
        ('BP_Annual Permit Report-2018-2022.xlsx', 'BP_Annual Permit Report-2023-2025.xlsx')]
TXT = os.path.join(ROOT, 'data/raw/accela_status')

# The lesson, also surfaced in the preview output and the lessons log.
LESSON = ("S2: milestones are dated events with sources and honest inference flags — "
          "not a status string copied forward (the migration's error).")


def parse_date(x):
    """STEP-helper. CPRA stores two date shapes: ISO 'YYYY-MM-DD 00:00:00' (Finaled Date) and
    US 'MM/DD/YYYY' (Issuance Date). Normalize both to 'YYYY-MM-DD'; anything else -> None.
    We never fabricate a date; an unparseable cell becomes None (absence), not a guess."""
    if x is None or str(x).strip().lower() == 'nan':
        return None
    s = str(x).strip()
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return m.group(0)
    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None


def load_cpra():
    """Load both CPRA feeds; rename the space-containing columns up front so row iteration can use
    clean attribute access (itertuples renames 'Finaled Date' to a positional name otherwise)."""
    def load(f):
        d = pd.read_excel(f, dtype=str, header=7)
        d.columns = [str(x).strip() for x in d.columns]
        return d
    df = pd.concat([load(f) for f in CPRA], ignore_index=True)
    df = df[df['PermitNumber'].notna()].copy()
    return df.rename(columns={'Issuance Date': 'IssuanceDate', 'Finaled Date': 'FinaledDate',
                              'Parcel Number': 'ParcelNumber', 'Work Type': 'WorkType'})


def load_spine():
    """The events attach to the S1 spine. Build a lookup: building key (number, street, type) ->
    s1_projects.building_id. Using the SAME key shape S1 wrote means events land on the right
    building and there can be no orphans."""
    c = sqlite3.connect(f'file:{V3}?mode=ro', uri=True); c.row_factory = sqlite3.Row
    smap = {(r['number'], r['street'], r['stype']): r['building_id']
            for r in c.execute("SELECT building_id,number,street,stype FROM s1_projects")}
    c.close()
    return smap


def build_events():
    """STEP 1-3 of S2. Returns a list of events, each a tuple:
        (building_id, building_key, event_type, date, is_inferred, source, source_permit, note)
    """
    smap = load_spine()
    df = load_cpra()

    # STEP 1 — keep only HOUSING rows (the predicate S1 already validated: residential occupancy OR
    # units>0 OR ADU-flag). Reusing it guarantees S2 sees exactly the rows S1 turned into the spine.
    df = df[[is_housing(o, u, n, a) for o, u, n, a in
             zip(df['OccType'], df['UnitsAdded'], df['NumberUnits'], df['ADU'])]]

    # STEP 2 — group each permit row under its BUILDING (same address key as S1), collecting the
    # dates we will turn into events. TWO filters on which dates count, and WHY:
    #   (a) MASTER permits only: a '-REV'/'-DEF' sub-permit is a revision of an existing permit, NOT a
    #       new issuance/finaling — counting it double-counts the milestone (the REV-trap S4 guards too).
    #   (b) the HOUSING-CREATING permit only: a building's "permitted"/"completed" milestone is when the
    #       permit that MADE THE HOUSING was issued/finaled — New construction OR a unit-adding addition
    #       (an ADU) — NOT when some later ANCILLARY permit (a sign, a tenant improvement, an MEP) at the
    #       same address happened to final years afterward. Skipping (b) is a real trap: 1950 Addison's
    #       New permit finaled 2022-08-09 (the true completion), but a later 0-unit permit there finaled
    #       2024-01-29 — MAX over ALL permits would mis-date the completion by 1.5 years. "Housing-
    #       creating" = Work Type 'New' OR UnitsAdded>0 OR the ADU flag (same idea as S1's is_housing,
    #       but applied per-PERMIT to pick the milestone-bearing permit, not the ancillary ones).
    def _ua(x):
        try: return float(str(x).replace(',', ''))
        except Exception: return 0.0
    bld = defaultdict(lambda: {'issue': [], 'final': [], 'permits': set()})
    for r in df.itertuples(index=False):
        st = r.StreetType
        st = '' if (st is None or str(st).strip().lower() == 'nan') else str(st)
        k = normalize_address(f"{r.StreetNumber} {r.StreetName} {st}".strip())
        key = (k.number, k.street, k.stype)
        if key not in smap:                            # not a spine building -> not our concern
            continue
        pn = str(r.PermitNumber)
        is_master = (extract_master_permit(pn) == pn)
        # a permit DATES a milestone iff it CREATES housing (Q3 net_units>0) — same shared rule as
        # S1 spine membership, so an ADU's BP/CO is dated by the ADU permit, not an ancillary sign/EV.
        creates_housing = net_units(str(r.WorkType).strip() == 'New', r.UnitsAdded, r.NumberUnits, r.ADU) > 0
        if is_master and creates_housing:
            iss = parse_date(r.IssuanceDate)
            fin = parse_date(r.FinaledDate)
            if iss: bld[key]['issue'].append((iss, pn))
            if fin: bld[key]['final'].append((fin, pn))
        bld[key]['permits'].add(pn)

    # STEP 3 — emit one dated event per (building, milestone). Each is backed by a STRUCTURED column,
    # so is_inferred=0 is honest here.
    events = []
    for key, b in bld.items():
        bid = smap[key]
        if b['issue']:
            # building_permit_issued = the FIRST BP issuance (MIN over masters). Why MIN: the 6th-cycle
            # RHNA credit is earned at the FIRST permit issuance; a later revision must not reset it.
            d, pn = min(b['issue'])
            events.append((bid, key, 'building_permit_issued', d, 0, 'CPRA:Issuance Date', pn,
                           'first BP issuance (master permits, MIN)'))
        if b['final']:
            # co_issued = the permit Finaled Date. Why: CPRA has NO separate Certificate-of-Occupancy
            # column; a finaled building permit is the structured signal the building is occupiable.
            # The DATE is structurally backed (is_inferred=0); we record the finaled->CO derivation in
            # the note so a reader knows it is a permit-final date, not a literal CO record. MAX over
            # masters = the building is fully complete when its last permit finals.
            d, pn = max(b['final'])
            events.append((bid, key, 'co_issued', d, 0, 'CPRA:Finaled Date', pn,
                           'CO = permit Finaled Date (CPRA has no separate CO column); MAX over masters'))
    return events, smap, bld


def corroborate():
    """STEP 4 (trust check). The Phase-3 reconciliation found CPRA dates and v2's permits-table dates
    are byte-identical where both exist (0 disagreements). Re-run that check live: for every permit in
    BOTH sources, do issued/finaled dates match? A disagreement would be a real finding, not noise."""
    df = load_cpra()
    cp = {}
    for pn, iss, fin in zip(df['PermitNumber'].astype(str), df['IssuanceDate'], df['FinaledDate']):
        e = cp.setdefault(pn, {'iss': None, 'fin': None})
        e['iss'] = e['iss'] or parse_date(iss)
        e['fin'] = e['fin'] or parse_date(fin)
    c = sqlite3.connect(f'file:{V2}?mode=ro', uri=True)
    iss_a = fin_a = 0
    findings = []   # (permit, field, cpra_date, v2_date) — CPRA(structured) disagrees with v2(cross-check)
    for pn, idate, fdate in c.execute("SELECT permit_number,issued_date,finaled_date FROM permits WHERE permit_number IS NOT NULL"):
        e = cp.get(pn)
        if not e:
            continue
        if idate and e['iss']:
            if str(idate)[:10] == e['iss']: iss_a += 1
            else: findings.append((pn, 'issued', e['iss'], str(idate)[:10]))
        if fdate and e['fin']:
            if str(fdate)[:10] == e['fin']: fin_a += 1
            else: findings.append((pn, 'finaled', e['fin'], str(fdate)[:10]))
    c.close()
    # A disagreement is NOT an S2 failure. S2's event uses the STRUCTURED CPRA date (the primary source);
    # a v2 mismatch is a finding ABOUT v2 (the thing we're rebuilding away from) for S8 to reconcile.
    # We assert the sourced fact and record the discrepancy — we never let v2 veto the structured source.
    return iss_a, fin_a, findings


def entitlement_coverage(smap):
    """STEP 5. Entitlement is the one milestone whose SOURCE is weak. The planning scrapes
    (accela_status/*.txt) carry a 'Record Status: Approved' signal and an address, but NOT a clean
    approval-DATE field (it lives, if anywhere, in an unstructured status-history block). So we MATCH
    buildings to an Approved record (we know they were entitled) but we DO NOT invent the date — each
    becomes entitlement_approved with date=NULL, is_inferred=1, source='needs_acquisition'. That is
    the honest move: assert the fact we can source (it was approved), flag the field we cannot (when)."""
    bybucket = defaultdict(list)
    for (num, st, ty), bid in smap.items():
        bybucket[(num, st)].append(bid)
    matched = set()
    for f in glob.glob(os.path.join(TXT, '*.txt')):
        txt = open(f, encoding='utf-8', errors='ignore').read()
        am = re.search(r'\*\*Address:\*\*\s*(.+)', txt)
        sm = re.search(r'\*\*Record Status:\*\*\s*(.+)', txt)
        if not am:
            continue
        # the .txt address line bleeds trailing markdown/city ("2820 San Pablo Ave, Berkeley | **Status:**
        # Approved") — take the street part before any ',' or '|' so normalize_address gets a clean address.
        addr_raw = re.split(r'[|,]', am.group(1).strip())[0].strip()
        k = normalize_address(addr_raw)
        status = sm.group(1).strip().lower() if sm else ''
        if 'approv' in status:
            for bid in bybucket.get((k.number, k.street), []):
                matched.add(bid)
    return matched


AS_OF = '2026-06-17'

def assemble():
    """Build the full S2 event set once (so preview and write can't drift). Returns
    (events, entitlement_building_ids, date_findings, spine_map). BP/CO are structured (is_inferred=0);
    entitlement is parsed-text (is_inferred=1, date=NULL); date_findings are the CPRA-vs-v2 S8 queue."""
    events, smap, bld = build_events()                 # BP + CO (structured, is_inferred=0)
    ent = entitlement_coverage(smap)
    for bid in sorted(ent):
        events.append((bid, None, 'entitlement_approved', None, 1,
                       'accela_status .txt: Record Status=Approved (date needs_acquisition)', None, 'parsed-text'))
    iss_a, fin_a, findings = corroborate()
    return events, ent, findings, iss_a, fin_a, smap


def write_s2(events, findings):
    """Persist s2_events + s2_date_reconcile into v3 (s0_*/s1_* untouched). Idempotent: DROP+rebuild."""
    con = sqlite3.connect(V3)
    con.executescript("""
      DROP TABLE IF EXISTS s2_events;
      DROP TABLE IF EXISTS s2_date_reconcile;
      DROP TABLE IF EXISTS s2_meta;
      CREATE TABLE s2_events(event_id INTEGER PRIMARY KEY, building_id INT, event_type TEXT, event_date TEXT,
        is_inferred INT, source TEXT, source_permit TEXT, note TEXT);
      CREATE INDEX ix_s2_bid ON s2_events(building_id);
      CREATE INDEX ix_s2_type ON s2_events(event_type);
      CREATE TABLE s2_date_reconcile(permit TEXT, field TEXT, cpra_date TEXT, v2_date TEXT);
      CREATE TABLE s2_meta(key TEXT, value TEXT);
    """)
    con.executemany("INSERT INTO s2_events(building_id,event_type,event_date,is_inferred,source,source_permit,note) "
                    "VALUES(?,?,?,?,?,?,?)", [(e[0], e[2], e[3], e[4], e[5], e[6], e[7]) for e in events])
    con.executemany("INSERT INTO s2_date_reconcile VALUES(?,?,?,?)", findings)
    from collections import Counter as _C
    bt = _C(e[2] for e in events)
    meta = [('stage', 'S2'), ('as_of', AS_OF), ('events', str(len(events))),
            ('building_permit_issued', str(bt['building_permit_issued'])), ('co_issued', str(bt['co_issued'])),
            ('entitlement_approved', str(bt['entitlement_approved'])), ('date_findings', str(len(findings))),
            ('key_module', 's0_keys.py + housing_predicates.py')]
    con.executemany("INSERT INTO s2_meta VALUES(?,?)", meta)
    con.commit(); con.close()
    return len(events), len(findings)

def fingerprint_s2():
    con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    ok = con.execute("PRAGMA integrity_check").fetchone()[0]
    n = con.execute("SELECT COUNT(*) FROM s2_events").fetchone()[0]
    bytype = dict(con.execute("SELECT event_type,COUNT(*) FROM s2_events GROUP BY event_type").fetchall())
    inf = dict(con.execute("SELECT event_type,is_inferred,COUNT(*) FROM s2_events GROUP BY event_type,is_inferred").fetchall()) if False else \
          {(r[0], r[1]): r[2] for r in con.execute("SELECT event_type,is_inferred,COUNT(*) FROM s2_events GROUP BY event_type,is_inferred")}
    orph = con.execute("SELECT COUNT(*) FROM s2_events e WHERE e.building_id NOT IN (SELECT building_id FROM s1_projects)").fetchone()[0]
    none_asserted = con.execute("SELECT COUNT(*) FROM s2_events WHERE event_type='entitlement_approved' AND event_date IS NOT NULL").fetchone()[0]
    nrec = con.execute("SELECT COUNT(*) FROM s2_date_reconcile").fetchone()[0]
    con.close()
    print("=== S2 FINGERPRINT (fresh connection) ===")
    print(f"  integrity: {ok}  | s2_events: {n}  by type: {bytype}")
    print(f"  is_inferred: BP={inf.get(('building_permit_issued',0),0)}/0  CO={inf.get(('co_issued',0),0)}/0  "
          f"entitlement={inf.get(('entitlement_approved',1),0)}/1  (BP/CO structured, entitlement parsed)")
    print(f"  entitlement events with an asserted date (must be 0): {none_asserted}")
    print(f"  s2_date_reconcile (S8 findings): {nrec}  | orphan events: {orph}")
    return ok, n, orph

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true'); ap.add_argument('--write', action='store_true'); ap.add_argument('--no-snapshot', action='store_true')
    args = ap.parse_args()

    events, ent, findings, iss_a, fin_a, smap = assemble()   # one assembly, shared by preview + write
    FAIL = []
    by_type = Counter(e[2] for e in events)
    by_inf = Counter((e[2], e[4]) for e in events)

    print("=== S2 PREVIEW — dated events onto the s1_projects spine (read-only; no write) ===")
    print(f"  lesson: {LESSON}")
    print(f"  spine buildings: {len(smap)}   events generated: {len(events)}")

    print(f"\n  [1] events by type + HONEST is_inferred (provenance per source, NOT blanket is_inferred=0):")
    for t, src in (('building_permit_issued', 'structured CPRA Issuance Date'),
                   ('co_issued', 'structured CPRA Finaled Date'),
                   ('entitlement_approved', 'PARSED .txt status — date NOT asserted')):
        print(f"      {t:24} {by_type[t]:>4}   is_inferred=0:{by_inf.get((t,0),0):>4}  is_inferred=1:{by_inf.get((t,1),0):>4}   ({src})")
    print(f"      -> BP/CO are structured-column-backed (is_inferred=0); entitlement is parsed-text with no")
    print(f"         date (is_inferred=1, needs_acquisition) — provenance marked honestly, not uniformly.")

    print(f"\n  [2] corroboration vs v2.permits — disagreements are S8 FINDINGS (persisted), not failures:")
    print(f"      BP issued: {iss_a} agree   |   finaled: {fin_a} agree   |   DISAGREEMENTS: {len(findings)} -> s2_date_reconcile (S8 queue)")
    for pn, field, cpra, v2d in findings:
        print(f"        {pn} {field}: CPRA(structured)={cpra}  vs  v2={v2d}  -> S2 uses CPRA; S8 reconciles")

    print(f"\n  [3] 568u Tier-1 completions get a co_issued event w/ the structured Finaled Date:")
    co_by_bid = {e[0]: e[3] for e in events if e[2] == 'co_issued'}
    TIER1 = ["2001 Fourth St", "1950 Addison St", "1900 Walnut St", "2503 Haste St", "1808 University Ave",
             "2747 San Pablo Ave", "0 San Pablo Ave", "2740 San Pablo Ave", "2556 Telegraph Ave", "2013 Second St"]
    okc = 0
    for addr in TIER1:
        k = normalize_address(addr); bid = smap.get((k.number, k.street, k.stype))
        co = co_by_bid.get(bid)
        if co: okc += 1
        else: FAIL.append(f"Tier-1 {addr}: no co_issued event")
    print(f"      {okc}/10 Tier-1 completions have a structured co_issued date")

    print(f"\n  [4] entitlement coverage (accela_status/*.txt — the weak-source milestone):")
    print(f"      spine buildings matched to an 'Approved' planning record: {len(ent)} -> entitlement_approved")
    print(f"      date NOT asserted (is_inferred=1, needs_acquisition); the FACT-of-approval is sourced.")
    print(f"      GAP (no .txt record): {len(smap)-len(ent)} of {len(smap)} buildings have NO entitlement event")
    print(f"      -> flagged as the entitlement-DATE acquisition queue (~33 discretionary proj/~2,253u, audit);")
    print(f"         S2 invents nothing to fill it.")

    spine_ids = set(smap.values())
    orphans = [e for e in events if e[0] not in spine_ids]
    print(f"\n  [5] s1_* tables untouched (preview is read-only).")
    print(f"  [6] orphan events (building_id not on the spine): {len(orphans)}")
    if orphans:
        FAIL.append(f"{len(orphans)} orphan events")

    print(f"\n  === S2 ACCEPTANCE GATE: {'PASS' if not FAIL else 'FAIL'} ===")
    for f in FAIL:
        print("    XXX", f)
    if args.write:
        if FAIL:
            print("\n  WRITE ABORTED — acceptance gate failed."); sys.exit(1)
        import hashlib
        v2b = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        if args.no_snapshot:
            print("\n  (--no-snapshot: idempotency re-run, NOT snapshotting — must not clobber the rollback point)")
        else:
            snap, created = snapshot_v3('s2')
            print(f"\n  snapshot: {os.path.basename(snap)} ({'created' if created else 'preserved existing — NOT clobbered'})")
        ne, nf = write_s2(events, findings)
        print(f"  S2 WRITE -> {os.path.basename(V3)}: {ne} s2_events, {nf} s2_date_reconcile")
        fingerprint_s2()
        v2a = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        print(f"  live v2 untouched: sha256 {'UNCHANGED' if v2b == v2a else 'CHANGED ✗✗'} ({v2b[:16]})")
