import json, collections
G = json.load(open('scratch/2026-09-30_attribute66/groups.json'))
FOUND = {'1812 UNIVERSITY': 'A01', '2510 CHANNING': 'A02', '2435 SAN PABLO': 'A03', '1367 UNIVERSITY': 'A04', '2100 SAN PABLO': 'A05', '2000 DWIGHT': 'A06'}
def finding(g):
    for a in g['addrs']:
        for k, v in FOUND.items():
            if a.upper().startswith(k): return v
cat = collections.defaultdict(list)
for g in G:
    f = finding(g)
    if f: g['cat'] = 'finding ' + f
    elif g['diff'] == 0: g['cat'] = 'timing only' if g['ours_years'] != g['city_years'] else 'agree'
    elif g['city'] == 0: g['cat'] = 'ours only'
    elif g['ours'] == 0: g['cat'] = 'city only'
    else: g['cat'] = 'count differs'
    cat[g['cat']].append(g)
print(f"{'category':<16}{'buildings':>10}{'units':>8}")
for k in sorted(cat, key=lambda k: -abs(sum(g['diff'] for g in cat[k]))):
    print(f"{k:<16}{len(cat[k]):>10}{sum(g['diff'] for g in cat[k]):>+8}")
rest = [g for g in G if not g['cat'].startswith('finding') and g['cat'] != 'agree']
print('outside findings, net:', sum(g['diff'] for g in rest))
json.dump(G, open('scratch/2026-09-30_attribute66/groups_classified.json', 'w'), indent=1)
for k in ('ours only', 'city only', 'count differs'):
    print(f'\n== {k}: size distribution', collections.Counter(min(abs(g["diff"]), 5) for g in cat[k]))
