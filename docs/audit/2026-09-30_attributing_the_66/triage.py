"""City-presence check for our ours-only buildings + the triage CSV. Run after match.py and classify.py."""
import json, sqlite3, re, sys, csv, collections
sys.path.insert(0, 'scripts')
from housing_rules.parcel_lineage import Resolver
from housing_rules.address import normalize_address
W = 'scratch/2026-09-30_attribute66/'
G = json.load(open(W + 'groups_classified.json'))
HCD = sqlite3.connect('file:databases/hcd_apr_mirror_2026-06-17_fresh.db?mode=ro', uri=True)
R = Resolver(sqlite3.connect('file:databases/berkeley_housing_v4.db?mode=ro', uri=True))
num = lambda v: int(float(v)) if str(v or '').strip() not in ('', 'None') else 0
def ak(a):
    try: n, s = normalize_address(a or '')
    except Exception: return None
    return f'{n}|{s}' if n and s and n != '0' else None
rows = []
for y, apn, addr, tid, bp in HCD.execute("select YEAR,APN,STREET_ADDRESS,JURS_TRACKING_ID,NO_BUILDING_PERMITS from table_a2 where upper(JURIS_NAME)='BERKELEY'"):
    pids, _ = R.resolve(apn, addr)
    rows.append(dict(tid=(tid or '').strip(), bp=num(bp), pids=set(pids), ak=ak(addr), raw=re.sub(r'[^0-9A-Z]', '', str(apn or '').upper())))
out = []
for g in G:
    if g['cat'] == 'agree' or g['cat'].startswith('finding'): continue
    o = [r for r in g['rows'] if r['side'] == 'ours']; c = [r for r in g['rows'] if r['side'] == 'city']
    sub = g['cat']
    if g['cat'] == 'ours only':
        if any(a.startswith('0 SAN PABLO') for a in g['addrs']): sub = "finding A03 (Poet's Place)"
        else:
            keys = {r['key'] for r in o}; pids = set().union(*[set(r['pids']) for r in o]); aks = {r['ak'] for r in o if r['ak']}
            raws = {re.sub(r'[^0-9A-Z]', '', str(r['apn'] or '').upper()) for r in o}
            hit = [x for x in rows if x['tid'] in keys or x['pids'] & pids or x['ak'] in aks or (x['raw'] in raws and len(x['raw']) >= 9)]
            same = [x for x in hit if x['tid'] in keys]
            sub = ('City reported the building permit, no completion' if same and any(x['bp'] > 0 for x in same) else
                   'City lists the permit number, no units' if same else
                   'City has other rows at the parcel, not this permit' if hit else 'City has no row at all')
    out.append(dict(category=g['cat'], subcategory=sub, diff=g['diff'], ours=g['ours'], city=g['city'], ours_years=' '.join(g['ours_years']),
                    city_years=' '.join(g['city_years']), address='; '.join(a for a in g['addrs'] if a)[:80],
                    our_permits=' '.join(r['key'] for r in o), city_rows=' '.join(r['key'] for r in c),
                    apns=' '.join(sorted({str(r['apn']) for r in g['rows']}))[:80], status='to verify'))
out.sort(key=lambda r: (r['category'], r['subcategory'], -abs(r['diff'])))
with open('docs/audit/2026-09-30_attributing_the_66_triage.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
t = collections.defaultdict(lambda: [0, 0])
for r in out: t[(r['category'], r['subcategory'])][0] += 1; t[(r['category'], r['subcategory'])][1] += r['diff']
for k, (n, u) in sorted(t.items()): print(f'{u:+5} {n:4}  {k[0]} / {k[1]}')
print('outside verified findings:', sum(r['diff'] for r in out) - 41)
