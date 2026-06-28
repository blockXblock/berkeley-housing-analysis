"""S1.5 — building-identity split (ADDITIVE, option b): split genuine multi-building developments
out of the address-keyed S1 spine, and MATERIALIZE the routing so S2 CONSUMES it (never re-derives).

Stage 1 (this file, PREVIEW-ONLY for now): read the live s1_projects spine, enable
split_multibuilding (with the one-line _RB_INCL widening: +duplex/townhouse/SFD/cottage/ADU), and
preview s1_5_projects (1385 -> 1386) PLUS the building_id -> {permits, canon_apns} routing map.

NOT WIRED, NO WRITE yet — John owns the gated write. Imports build_s1 (split rule + spine builder),
s0_keys, housing_predicates, cpra_dedup; observes parcel_lineage (v2) as CANDIDATE, not fact.
--preview is READ-ONLY.
"""
import sqlite3, sys, os, argparse, re
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import build_s1
from s0_keys import normalize_address
from cpra_dedup import extract_master_permit
from housing_rules.apn import to_canonical_apn

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
V3 = os.path.join(ROOT, 'databases', 'berkeley_housing_v3.db')
V2 = os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')
# the one-line _RB_INCL widening (genuine new-housing nouns missing from the split-rule include set)
_WIDEN = r'|\b(duplex|triplex|fourplex|town ?house|town ?home|cottage|sfd|single ?family|accessory dwelling)\b'


def _lineage_apns():
    c = sqlite3.connect(f'file:{V2}?mode=ro', uri=True)
    apns = set()
    for pr, ch in c.execute("SELECT parent_apn_raw,child_apn_raw FROM parcel_lineage "
                            "WHERE parent_apn_raw IS NOT NULL AND child_apn_raw IS NOT NULL"):
        for blob in (pr, ch):
            for x in str(blob).split(','):
                ca = to_canonical_apn(x.strip())
                if ca: apns.add(ca)
    c.close(); return apns


def gather():
    # widen the split-rule include set at runtime (no file edit) for this stage
    orig_incl = build_s1._RB_INCL
    build_s1._RB_INCL = re.compile(orig_incl.pattern + _WIDEN, re.I)
    try:
        spine, _, _, _ = build_s1.build_spine()          # 1385 buildings, addr-keyed
        split = build_s1.split_multibuilding(spine)       # apply the rule
    finally:
        build_s1._RB_INCL = orig_incl

    # map live s1_projects building_id by bucket (the additive anchor)
    v3 = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    bid_by_bucket = {b: bid for bid, b in v3.execute("SELECT building_id,bucket FROM s1_projects")}
    maxbid = v3.execute("SELECT MAX(building_id) FROM s1_projects").fetchone()[0]
    v3.close()
    bucketstr = lambda gk: f"{gk[0]} {gk[1]}".strip()
    lin = _lineage_apns()

    routing = []   # (building_id, bucket, addr, units, co_years, n_permits, canon_apns, via, split_origin)
    held = []      # eligible-but-blocked (lineage/held queue)
    nextid = (maxbid or 0) + 1
    # detect split-eligible-but-blocked (>=2 realbuild APNs but rule left collapsed)
    def realbuild_apns(b):
        au = defaultdict(float); ay = defaultdict(set)
        for (pn, ca, nu, isnew, fd, desc) in b['rows']:
            bsrc = build_s1
            if ca and bool(isnew) and nu >= 2 and not bsrc._RB_EXCL.search(desc or '') and bool(
                    re.compile(orig_incl.pattern + _WIDEN, re.I).search(desc or '')):
                au[ca] = max(au[ca], nu)
                if fd: ay[ca].add(fd[:4])
        return {a: u for a, u in au.items() if u >= 2}, ay

    for k, b in split.items():
        origin_bucket = bucketstr(k[:3]) if len(k) == 4 else bucketstr(k)
        addr = f"{(k[:3] if len(k)==4 else k)[0]} {(k[:3] if len(k)==4 else k)[1]} {(k[:3] if len(k)==4 else k)[2] or ''}".strip()
        permits = sorted(b['permits']); apns = sorted(a for a in b['apns'] if a)
        coys = sorted({d[:4] for d in b['finaled']})
        if len(k) == 4:                                   # a split sub-building
            # the largest sub keeps the parent building_id; others get fresh ids (deterministic by APN order)
            via = 'split'; bid = None                      # resolved below after we know the group
        else:
            bid = bid_by_bucket.get(origin_bucket); via = 'inherited'
        routing.append({'key': k, 'bucket': origin_bucket, 'addr': addr, 'units': b['units'],
                        'co_years': coys, 'permits': permits, 'apns': apns, 'via': via, 'bid': bid})

    # assign building_ids to split subs: parent bucket's existing id -> largest sub; rest -> new ids
    bysplit = defaultdict(list)
    for r in routing:
        if r['via'] == 'split': bysplit[r['bucket']].append(r)
    for bucket, subs in bysplit.items():
        subs.sort(key=lambda r: -r['units'])              # largest first
        subs[0]['bid'] = bid_by_bucket.get(bucket)        # largest keeps parent id
        for r in subs[1:]:
            r['bid'] = nextid; nextid += 1

    # held queue: buildings split-ELIGIBLE (>=2 realbuild APNs) but rule left collapsed (single output row)
    split_origin_buckets = set(bysplit)
    for k, b in spine.items():
        rb, ay = realbuild_apns(b)
        if len(rb) >= 2 and bucketstr(k) not in split_origin_buckets:
            du = len(set(rb.values())) > 1
            dy = len({min(ay[a]) for a in rb if ay[a]}) > 1
            held.append({'bucket': bucketstr(k), 'realbuild_apns': dict(rb),
                         'distinct_units': du, 'distinct_years': dy,
                         'lineage': bool({a for a in rb} & lin)})

    lineage_involved = sum(1 for r in routing if {a for a in r['apns']} & lin)
    return {'routing': routing, 'held': held, 'n_in': len(spine), 'n_out': len(split),
            'n_split': len(bysplit), 'lineage_involved': lineage_involved}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument('--preview', action='store_true')
    args = ap.parse_args()
    g = gather(); FAIL = []
    print("=== S1.5 STAGE 1 PREVIEW — building-identity split (read-only; NO write) ===")
    print(f"\n  spine: {g['n_in']} -> s1_5_projects: {g['n_out']}  (delta +{g['n_out']-g['n_in']})")
    print(f"  buildings split: {g['n_split']}")
    print(f"\n  [splits + routing] (building_id <- the map S2 will CONSUME):")
    for r in sorted(g['routing'], key=lambda r: (r['bucket'], -r['units'])):
        if r['via'] == 'split':
            print(f"     bid={r['bid']} [{r['via']}] {r['addr']}  units={r['units']:.0f} CO={r['co_years']} "
                  f"APNs={r['apns']} permits={len(r['permits'])}")
    print(f"\n  [held queue] eligible-but-blocked (>=2 realbuild APNs, rule left collapsed): {len(g['held'])}")
    for h in g['held']:
        print(f"     {h['bucket']}: realbuild={h['realbuild_apns']} distinct_units={h['distinct_units']} "
              f"distinct_years={h['distinct_years']} lineage={h['lineage']}")
    print(f"\n  [s1_5_meta gauge] lineage_involved_buildings = {g['lineage_involved']}")

    # ---- ACCEPTANCE assertions (preview) ----
    splits = {r['bucket'] for r in g['routing'] if r['via'] == 'split'}
    if g['n_out'] - g['n_in'] != 1: FAIL.append(f"delta {g['n_out']-g['n_in']} != +1")
    if g['n_split'] != 1: FAIL.append(f"splits {g['n_split']} != 1")
    if splits != {'2352 SHATTUCK'}: FAIL.append(f"split bucket {splits} != {{'2352 SHATTUCK'}}")
    # 2352 -> North 135 + South 69
    su = sorted(r['units'] for r in g['routing'] if r['bucket'] == '2352 SHATTUCK' and r['via'] == 'split')
    if su != [69.0, 135.0]: FAIL.append(f"2352 split units {su} != [69,135]")
    # 1173 stays HELD (eligible after widening, blocked by distinct tests)
    h1173 = [h for h in g['held'] if h['bucket'] == '1173 HEARST']
    if not h1173: FAIL.append("1173 HEARST not in held queue (expected eligible-but-blocked)")
    elif h1173[0]['distinct_units'] or h1173[0]['distinct_years']:
        FAIL.append(f"1173 HEARST not blocked by BOTH distinct tests: {h1173[0]}")
    print(f"\n  === S1.5 STAGE-1 ACCEPTANCE: {'PASS' if not FAIL else 'FAIL'} ===")
    for f in FAIL: print("    XXX", f)
    print(f"\n  STOP — preview only, NO write. parcel_lineage observed as candidate. John owns the gated write.")
