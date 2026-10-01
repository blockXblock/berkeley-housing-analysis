"""6th-cycle building-permit credit: ours (v4 buildings, first permit) vs the City's APR BP rows, matched by building. Read-only."""
import sys, json, sqlite3, collections, re
sys.path.insert(0, '.'); sys.path.insert(0, 'scripts')
from scripts.v4 import stage_methods as SM
from housing_rules.parcel_lineage import Resolver
from housing_rules.address import normalize_address
START, END = '2022-06-30', '2025-12-31'
V4 = SM.ro(SM.LIVE); R = Resolver(V4)
HCD = sqlite3.connect('file:databases/hcd_apr_mirror_2026-06-17_fresh.db?mode=ro', uri=True)
def akey(a):
    try: n, s = normalize_address(a or '')
    except Exception: return None
    return f'{n}|{s}' if n and s and n != '0' else None
rawk = lambda a: re.sub(r'[^0-9A-Z]', '', str(a or '').upper())
ours = []
for sid, n, first, keys, pl, addr in V4.execute("""
  WITH u AS (SELECT structure_id, SUM(unit_count) n FROM units GROUP BY structure_id),
  ev AS (SELECT se.structure_id, e.event_date d, e.source_record_key k, e.raw_payload p, e.raw_address a, se.role_in_structure r
         FROM structure_events se JOIN events e ON e.event_id = se.event_id WHERE e.event_type_code = 'permit_issued')
  SELECT u.structure_id, u.n, MIN(ev.d), group_concat(DISTINCT CASE WHEN ev.r='master' THEN ev.k END),
         MAX(CASE WHEN ev.r='master' THEN ev.p END), MAX(CASE WHEN ev.r='master' THEN ev.a END)
  FROM u LEFT JOIN ev USING(structure_id) GROUP BY u.structure_id"""):
    apn = json.loads(pl).get('Parcel Number') if pl else None
    pids, basis = R.resolve(apn, addr)
    ours.append(dict(side='ours', key=f'S{sid}', permits=keys or '', date=first or '', units=n, apn=apn, addr=addr,
                     pids=set(pids), ak=akey(addr), raw=rawk(apn)))
bp = [c for (c,) in HCD.execute("SELECT name FROM pragma_table_info('table_a2') WHERE name LIKE 'BP\\_%' ESCAPE '\\' AND name<>'BP_ISSUE_DT1'")]
city = []
for i, (y, apn, addr, tid, d, u) in enumerate(HCD.execute(f"""SELECT YEAR, APN, STREET_ADDRESS, JURS_TRACKING_ID, BP_ISSUE_DT1,
       {'+'.join(f'COALESCE({c},0)' for c in bp)} FROM table_a2 WHERE upper(JURIS_NAME)='BERKELEY'""")):
    if not u: continue
    pids, basis = R.resolve(apn, addr)
    city.append(dict(side='city', key=f'row{i}', permits=(tid or '').strip(), date=(d or f'{y}-??'), units=int(u), apn=apn, addr=addr,
                     pids=set(pids), ak=akey(addr), raw=rawk(apn)))
allr = ours + city
parent = list(range(len(allr)))
def find(i):
    while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
    return i
idx = collections.defaultdict(list)
for i, r in enumerate(allr):
    for p in r['pids']: idx[('p', p)].append(i)
    if r['ak']: idx[('a', r['ak'])].append(i)
    if len(r['raw']) >= 9: idx[('r', r['raw'])].append(i)
    for k in r['permits'].split(','):
        if k.strip().startswith('B'): idx[('k', k.strip())].append(i)
for v in idx.values():
    for j in v[1:]: parent[find(j)] = find(v[0])
G = collections.defaultdict(list)
for i, r in enumerate(allr): G[find(i)].append(r)
inc = lambda r: START <= r['date'][:10] <= END
out = []
for g in G.values():
    o6 = sum(r['units'] for r in g if r['side'] == 'ours' and inc(r)); c6 = sum(r['units'] for r in g if r['side'] == 'city' and inc(r))
    if o6 == 0 and c6 == 0: continue
    oa = sum(r['units'] for r in g if r['side'] == 'ours'); ca = sum(r['units'] for r in g if r['side'] == 'city')
    if ca == 0: cat = 'ours only (no City permit row)'
    elif oa == 0: cat = 'City only (no v4 building)'
    elif (o6 > 0) != (c6 > 0): cat = 'cycle boundary (dated in different cycles)'
    elif o6 != c6: cat = 'both in cycle, different units'
    else: cat = 'agree'
    out.append(dict(cat=cat, diff=o6 - c6, ours6=o6, city6=c6, ours_all=oa, city_all=ca,
                    addr='; '.join(sorted({str(r['addr'] or '').strip() for r in g if r['addr']}))[:70],
                    ours_dates=' '.join(sorted({r['date'][:10] for r in g if r['side']=='ours'})),
                    city_dates=' '.join(sorted({r['date'][:10] for r in g if r['side']=='city'})),
                    ours_permits=' '.join(r['permits'] for r in g if r['side']=='ours')[:80], city_ids=' '.join(r['permits'] for r in g if r['side']=='city')[:60]))
json.dump(out, open('scratch/2026-10-01_rhna/groups.json', 'w'), indent=1)
print('ours 6th cycle', sum(r['units'] for r in ours if inc(r)), '| City 6th cycle', sum(r['units'] for r in city if inc(r)), '| net', sum(x['diff'] for x in out))
t = collections.defaultdict(lambda: [0, 0])
for x in out: t[x['cat']][0] += 1; t[x['cat']][1] += x['diff']
for k, (n, d) in sorted(t.items(), key=lambda kv: kv[1][1]): print(f'{d:+6} {n:5}  {k}')
