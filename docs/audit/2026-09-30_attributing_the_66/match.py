"""Building-level match of our 2018-25 completions (live v4) to the City's APR CO rows. Read-only."""
import sys, json, sqlite3, collections, re
sys.path.insert(0, '.'); sys.path.insert(0, 'scripts')
from scripts.v4 import stage_methods as SM
from housing_rules.parcel_lineage import Resolver
from housing_rules.address import normalize_address

LIN = sqlite3.connect('file:databases/berkeley_housing_v4.db?mode=ro', uri=True)
R = Resolver(LIN)
HCD = sqlite3.connect('file:databases/hcd_apr_mirror_2026-06-17_fresh.db?mode=ro', uri=True)
V4 = SM.ro(SM.LIVE)

def akey(a):
    try: n, s = normalize_address(a or '')
    except Exception: return None
    return f'{n}|{s}' if n and s and n != '0' else None

# ours: counted finaled masters 2018-25, one row per event (JN-E grain)
ours = []
for k, d, u, pl, addr in V4.execute("""SELECT e.source_record_key, e.event_date, c.net_units, e.raw_payload, e.raw_address
      FROM events e JOIN event_classifications c USING(event_id)
      WHERE e.event_type_code='permit_finaled' AND c.housing_role='new_unit' AND c.is_master=1 AND COALESCE(c.net_units,0)>0
        AND strftime('%Y',e.event_date) BETWEEN '2018' AND '2025'"""):
    apn = json.loads(pl).get('Parcel Number')
    pids, basis = R.resolve(apn, addr)
    ours.append(dict(side='ours', key=k, year=d[:4], units=u, apn=apn, addr=addr, pids=set(pids), basis=basis, ak=akey(addr)))
co = [c for (c,) in HCD.execute("SELECT name FROM pragma_table_info('table_a2') WHERE name LIKE 'CO\\_%' ESCAPE '\\' AND name<>'CO_ISSUE_DT1'")]
city = []
for i, (y, apn, addr, tid, u) in enumerate(HCD.execute(f"""SELECT YEAR, APN, STREET_ADDRESS, JURS_TRACKING_ID, {'+'.join(f'COALESCE({c},0)' for c in co)} u
      FROM table_a2 WHERE upper(JURIS_NAME)='BERKELEY'""")):
    if not u: continue
    pids, basis = R.resolve(apn, addr)
    city.append(dict(side='city', key=f'row{i}:{tid or ""}', year=str(y), units=int(u), apn=apn, addr=addr, pids=set(pids), basis=basis, ak=akey(addr)))
print('ours rows', len(ours), sum(r['units'] for r in ours), '| city rows', len(city), sum(r['units'] for r in city))

# union-find over shared parcel id or shared address key
allr = ours + city
parent = list(range(len(allr)))
def find(i):
    while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
    return i
def union(a, b): parent[find(a)] = find(b)
by = collections.defaultdict(list)
for i, r in enumerate(allr):
    for p in r['pids']: by[('p', p)].append(i)
    if r['ak']: by[('a', r['ak'])].append(i)
    raw = re.sub(r'[^0-9A-Z]', '', str(r['apn'] or '').upper())
    if len(raw) >= 9: by[('raw', raw)].append(i)          # same source APN, even when the Resolver cannot pick a child
for idx in by.values():
    for j in idx[1:]: union(idx[0], j)
groups = collections.defaultdict(list)
for i, r in enumerate(allr): groups[find(i)].append(r)
out = []
for g in groups.values():
    o = sum(r['units'] for r in g if r['side'] == 'ours'); c = sum(r['units'] for r in g if r['side'] == 'city')
    oy = sorted({r['year'] for r in g if r['side'] == 'ours'}); cy = sorted({r['year'] for r in g if r['side'] == 'city'})
    out.append(dict(ours=o, city=c, diff=o - c, ours_years=oy, city_years=cy,
                    addrs=sorted({(r['addr'] or '').strip() for r in g})[:3], rows=[{k: (sorted(v) if isinstance(v, set) else v) for k, v in r.items()} for r in g]))
json.dump(out, open('scratch/2026-09-30_attribute66/groups.json', 'w'), indent=1, default=str)
print('groups', len(out), 'net diff', sum(x['diff'] for x in out))
print('unresolved parcels: ours', collections.Counter(r['basis'] for r in ours).most_common(6))
print('                    city', collections.Counter(r['basis'] for r in city).most_common(6))
