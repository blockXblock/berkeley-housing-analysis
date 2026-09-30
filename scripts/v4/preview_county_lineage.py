"""READ-ONLY preview: the Alameda Assessor's own parcel lineage (data/raw/county_parcel_lineage/, 23 tables) against
v4's parcel identifiers, candidate lineage and building parcel links. Nothing is written to any DB.

Edges are PARENT -> CHILD as the County published them. A parent with ONE child is a renumber or merger (safe to follow);
a parent with SEVERAL children is a SPLIT, and which child a pre-split permit belongs to is not in the lineage (ADR-003:
lineage says what became what, not where a building sits) -- reported, never guessed."""
import collections, csv, glob, json, sqlite3, sys
sys.path.insert(0, 'scripts')
from housing_rules import to_canonical_apn

DB = sys.argv[1] if len(sys.argv) > 1 else 'databases/berkeley_housing_v4.db'
db = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
PARENT = ('PARENT_APN', 'PARENT_PARCEL', 'PARENT_PARCEL_NUMBER')
CHILD = ('CHILD_APN', 'CHILD_PARCEL_NUMBER')
END = ('END_DT', 'END_DATE', 'INACTIVATION_DATE', 'PARENT_PARCEL_END_DATE')


def pick(row, names):
    up = {k.upper(): v for k, v in row.items()}
    for n in names:
        if up.get(n) not in (None, ''):
            return up[n]
    return None


def canon(a):
    try:
        return to_canonical_apn(str(a).strip(), 'alameda') if a else None
    except Exception:
        return None


def iso(ms):
    import datetime as dt
    try:
        v = int(ms)
        return None if v < 0 else dt.datetime.fromtimestamp(v / 1000, dt.timezone.utc).date().isoformat()
    except Exception:
        return None


current = dict(db.execute("SELECT apn_normalized, parcel_id FROM parcel_identifiers WHERE is_current=1"))
books = {a.split('-')[0] for a in current}
edges, raw_rows, unparsed = collections.defaultdict(set), 0, 0
end_of = {}
for f in sorted(glob.glob('data/raw/county_parcel_lineage/*_20*_20*.json')) + \
        sorted(glob.glob('data/raw/county_parcel_lineage/Assessor_Office_Deleted_Parcel_List_*.json')):
    d = json.load(open(f))
    if not isinstance(d, dict):
        continue
    for r in d['rows']:
        raw_rows += 1
        p, c = canon(pick(r, PARENT)), canon(pick(r, CHILD))
        if not p or not c:
            unparsed += 1
            continue
        if p.split('-')[0] not in books and c.split('-')[0] not in books:
            continue
        edges[p].add(c)
        e = iso(pick(r, END))
        if e:
            end_of[p] = max(end_of.get(p, e), e)
print(f'County rows read {raw_rows:,} (unparsed parent/child {unparsed:,}); Berkeley-book parents {len(edges):,}')


def descendants(apn, seen=None):
    """current parcels this APN became (following non-current children)."""
    seen = seen or set()
    if apn in current:
        return {apn}
    if apn in seen or apn not in edges:
        return set()
    seen.add(apn)
    out = set()
    for c in edges[apn]:
        out |= descendants(c, seen)
    return out


def verdict(apn):
    if apn in current:
        return 'current', {apn}
    if apn not in edges:
        return 'not_in_county', set()
    ds = descendants(apn)
    return ('one_current' if len(ds) == 1 else 'split_several' if ds else 'no_current_descendant'), ds


# 1. v4's candidate former identifiers (the bootstrap, source kind parcel_lineage_candidates)
src = [s for (s,) in db.execute("SELECT source_id FROM sources WHERE source_kind='parcel_lineage_candidates'")]
pid_apn = collections.defaultdict(set)
for a, pid in current.items():
    pid_apn[pid].add(a)
rows = db.execute("SELECT apn_normalized, parcel_id FROM parcel_identifiers WHERE is_current=0 AND source_id IN (%s)"
                  % ",".join("?" * len(src)), src).fetchall()
out1 = collections.Counter()
detail1 = []
for apn, pid in rows:
    v, ds = verdict(apn)
    tgt = pid_apn[pid]
    cls = ('CONFIRMED' if v == 'one_current' and ds & tgt else
           'SPLIT_includes_target' if v == 'split_several' and ds & tgt else
           'CONTRADICTED' if ds and not ds & tgt else
           'target_is_current_apn' if v == 'current' else 'COUNTY_SILENT')
    out1[cls] += 1
    detail1.append((cls, apn, sorted(tgt), sorted(ds), end_of.get(apn)))
print('\n1. v4 candidate former-APNs vs the County:', dict(out1))
for d in sorted(detail1):
    if d[0] != 'CONFIRMED':
        print('   ', d)

# 2. permit APNs v4 cannot join to any parcel
ids = {a for (a,) in db.execute("SELECT apn_normalized FROM parcel_identifiers")}
perm = collections.defaultdict(set)
for key, apn in db.execute("SELECT DISTINCT source_record_key, raw_apn FROM events WHERE event_type_code LIKE 'permit_%' "
                           "AND raw_apn IS NOT NULL"):
    c = canon(apn)
    if c and c not in ids:
        perm[c].add(key)
child_of = collections.defaultdict(set)          # a NEW child APN -> its parent(s)
for p, cs in edges.items():
    for c in cs:
        child_of[c].add(p)
out2 = collections.Counter()
for apn, keys in perm.items():
    v, ds = verdict(apn)
    if v == 'one_current':
        out2['old APN -> one current parcel'] += len(keys)
    elif v == 'split_several':
        out2['old APN -> split (several current)'] += len(keys)
    elif child_of.get(apn):
        par = {q for p in child_of[apn] for q in ({p} if p in current else descendants(p))}
        out2['NEW child APN, parent lot is current' if par else 'new child APN, parent not current'] += len(keys)
    else:
        out2['County silent'] += len(keys)
print(f'\n2. permits on APNs v4 cannot join ({sum(len(k) for k in perm.values())} permits, {len(perm)} APNs):', dict(out2))

# 3. buildings: current link vs what the County says
links = db.execute("""SELECT s.structure_id, e.raw_apn, sp.parcel_id, u.unit_count FROM structures s
    JOIN events e ON e.event_id = s.master_event_id LEFT JOIN structure_parcels sp ON sp.structure_id = s.structure_id
    AND sp.is_primary = 1 LEFT JOIN units u ON u.structure_id = s.structure_id""").fetchall()
out3, big = collections.Counter(), []
for sid, apn, pid, units in links:
    c = canon(apn)
    if not c:
        out3['no permit APN'] += 1
        continue
    v, ds = verdict(c)
    now = pid_apn.get(pid, set()) if pid else set()
    if v == 'current':
        out3['on a current APN (unchanged)'] += 1
        continue
    cls = ('link CONFIRMED' if ds and now and now <= ds and v == 'one_current' else
           'link CONTRADICTED' if ds and now and not (now & ds) else
           'link is one of a split' if v == 'split_several' and now & ds else
           'unlinked -> County gives ONE parcel' if not now and v == 'one_current' else
           'unlinked -> County split' if not now and v == 'split_several' else
           'unlinked, new child APN' if not now and child_of.get(c) else
           'unlinked, County silent' if not now else 'other')
    out3[cls] += 1
    if cls not in ('on a current APN (unchanged)', 'link CONFIRMED') and (units or 0) >= 5:
        big.append((units, sid, c, cls, sorted(ds)[:3], sorted(child_of.get(c, []))[:2]))
print('\n3. buildings (by master permit APN):', dict(out3))
for b in sorted(big, reverse=True)[:25]:
    print('   ', b)
