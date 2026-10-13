#!/usr/bin/env python3
r"""llm_address_resolve.py -- resolve the v4 event addresses the canon cannot find in the City's address list.

John, 2026-10-13 ("have a model read the unmatched addresses"). After the canon fix (housing_rules.address,
2026-10-13), 69,667 of v4's 71,891 distinct event addresses key onto an address in the City's address-point layer;
2,224 do not. More regex would repeat the mistake that polluted v2, so each one is READ instead, as a CHOICE FROM
THE CITY'S OWN LIST: the model sees the raw address, where it came from, and the candidates the City lists (the
nearest house numbers on the same street, close street names, the City's address for the event's parcel), and
either picks one candidate or answers none with a reason. A pick is kept only if it is one of the offered
candidates; nothing is invented, and the canon never learns from a reading.

READ ONCE, STORE, LOOK UP: data/derived/address_resolution_evidence_<date>.json, keyed by the raw address string.

  .venv/bin/python scripts/llm_address_resolve.py --dry-run
  .venv/bin/python scripts/llm_address_resolve.py --sonnet submit|status|collect
"""
from __future__ import annotations

import argparse
import collections
import csv
import difflib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import model_readers as mr  # noqa: E402
from housing_rules import to_canonical_apn  # noqa: E402
from housing_rules.address import normalize_address  # noqa: E402

V4 = ROOT / "databases/berkeley_housing_v4.db"
POINTS = ROOT / "data/reference/berkeley_addresses_with_fields.csv"
OUT = ROOT / "scratch/2026-10-13_address_resolve"
REASONS = ("same_address_different_form", "spelling_or_typo", "unit_or_half_of_a_listed_address",
           "renumbered_or_replatted", "not_in_city_list", "not_an_address")

DEFINITION = f"""QUESTION. Each ITEM is an address string from a City of Berkeley record (a permit, a Planning record, the
Rent Board registry, a business license) that does not match any address in the City's own address list. Below it
are CANDIDATES from that list: addresses on the same street with nearby house numbers, streets with similar names,
and the City's address for the record's parcel when the record names one.
Decide whether the item refers to one of the candidates. If none fits but the record's own text (the "e.g." quote)
names a full street address, give it as "stated" (copied exactly from that text); it is kept only if it is in the
City's list. Pick a candidate ONLY if the item plainly means that
address: the same address written differently ('VINCENTE' for 'VICENTE'), or a unit / half / rear of that address
('1707 1/4 Oxford' -> 1707 Oxford), or the City's address for the same parcel. Do NOT pick the nearest number just
because it is near: a house number that is simply absent from the list is "not_in_city_list". If the text is not
an address at all, answer "not_an_address".
reason must be one of: {", ".join(REASONS)}."""


def _num(s):
    s = str(s or "")
    return s[:-2] if s.endswith(".0") else s


def city_list():
    """(house, street) -> [(City address, APN)] and street -> sorted [(house float, City address, APN)]."""
    by_key, by_street = collections.defaultdict(list), collections.defaultdict(list)
    for r in csv.DictReader(open(POINTS)):
        addr = r["ADDRESS"].split(" Apt ")[0].split(" Unit ")[0].split(" Ste ")[0]
        k = normalize_address(f"{_num(r['ST_NUM'])} {r['FEANME']} {r['FEATYP']}")
        if not k[0]:
            continue
        if (addr, r["APN"]) not in by_key[k]:
            by_key[k].append((addr, r["APN"]))
        try:
            by_street[k[1]].append((float(k[0]), addr, r["APN"]))
        except ValueError:
            pass
    for s in by_street:
        by_street[s] = sorted(set(by_street[s]))
    return by_key, by_street


def unmatched(dbp=V4):
    by_key, by_street = city_list()
    db = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
    rows = collections.defaultdict(lambda: {"events": 0, "sources": set(), "apns": set(), "sample": None})
    for a, src, apn, desc in db.execute("""SELECT e.raw_address, s.source_kind, e.raw_apn, substr(e.raw_description, 1, 160)
                                           FROM events e JOIN sources s USING(source_id) WHERE e.raw_address <> ''"""):
        if normalize_address(a) in by_key:
            continue
        r = rows[a]
        r["events"] += 1
        r["sources"].add(src)
        if apn:
            try:
                r["apns"].add(to_canonical_apn(apn, "alameda"))
            except Exception:
                pass
        r["sample"] = r["sample"] or desc
    from housing_rules.address_points import address_for
    streets = sorted(by_street)
    items = {}
    for a, r in rows.items():
        num, st = normalize_address(a)
        cands = []
        if st in by_street and num and num != "0":          # a '0 <street>' placeholder has no nearby number
            try:
                n = float(num)
                near = sorted(by_street[st], key=lambda x: abs(x[0] - n))[:6]
                cands += [(c[1], c[2], "same street, nearby number") for c in near]
            except ValueError:
                pass
        for s2 in difflib.get_close_matches(st, streets, n=3, cutoff=0.8):
            if s2 == st:
                continue
            pool = by_street[s2]
            try:
                n = float(num)
                pool = sorted(pool, key=lambda x: abs(x[0] - n))
            except ValueError:
                pass
            cands += [(c[1], c[2], f"similar street name '{s2}'") for c in pool[:3]]
        for apn in sorted(x for x in r["apns"] if x):
            ca = address_for(apn)
            if ca:
                cands.append((ca, apn, "the City's address for the record's parcel"))
        seen, cl = set(), []
        for c in cands:
            if c[0] not in seen:
                seen.add(c[0])
                cl.append(c)
        items[a] = {"events": r["events"], "sources": sorted(r["sources"]), "sample": r["sample"],
                    "candidates": [{"id": f"C{i + 1}", "address": c[0], "apn": c[1], "why": c[2]}
                                   for i, c in enumerate(cl[:12])]}
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sonnet", choices=["submit", "status", "collect"])
    ap.add_argument("--pack", type=int, default=15)
    a = ap.parse_args()
    state = OUT / "sonnet_batch_state.json"
    items = unmatched()
    keys = sorted(items)
    ids = {k: f"A{i}" for i, k in enumerate(keys)}
    groups = [keys[i:i + a.pack] for i in range(0, len(keys), a.pack)]
    print(f"{len(keys)} unmatched addresses ({sum(v['events'] for v in items.values()):,} events); "
          f"{sum(1 for v in items.values() if not v['candidates'])} with no candidate at all")

    def prompt(g):
        body = []
        for k in g:
            it = items[k]
            body.append(f"ITEM {ids[k]}: {json.dumps(k)}  (from {', '.join(it['sources'])}; {it['events']} records; "
                        f"e.g. {json.dumps(it['sample'] or '')})\n" +
                        ("\n".join(f"  {c['id']}: {c['address']}  [APN {c['apn']}; {c['why']}]" for c in it["candidates"])
                         or "  (no candidates)"))
        return (f"{DEFINITION}\n\nAnswer with a JSON array only, one object per ITEM, in order:\n"
                f"[{{\"item\": <ITEM id>, \"choice\": <candidate id or null>, \"stated\": <an address copied from the "
                f"record text, or null>, \"reason\": <one of the reasons>, \"note\": <a few words>}}]\n\n" + "\n\n".join(body))

    if a.dry_run:
        print(prompt(groups[0])[:4000])
        print(f"\n{len(groups)} requests, ~{sum(len(prompt(g)) for g in groups) / 4 / 1e6:.2f}M input tokens. NOTHING ASKED.")
        return 0
    if a.sonnet == "submit":
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "groups.json").write_text(json.dumps({"groups": groups, "ids": ids}))
        mr.batch_submit([{"custom_id": f"g{i}", "params": {"model": mr.BATCH_MODEL, "max_tokens": 120 * len(g) + 600,
                          "messages": [{"role": "user", "content": prompt(g)}]}} for i, g in enumerate(groups)], state)
        return 0
    if a.sonnet == "status":
        mr.batch_status(state)
        return 0
    if a.sonnet == "collect":
        by_key, _ = city_list()
        saved = json.loads((OUT / "groups.json").read_text())
        groups, ids = saved["groups"], saved["ids"]
        rows, unanswered, rejected = [], [], 0
        for cid, parsed, raw, _ in mr.batch_results(state):
            got = {str(x.get("item")): x for x in (parsed or []) if isinstance(x, dict)}
            for k in groups[int(cid[1:])]:
                ans = got.get(ids[k])
                if not ans or ans.get("reason") not in REASONS:
                    unanswered.append(k)
                    continue
                cand = {c["id"]: c for c in items.get(k, {}).get("candidates", [])}
                ch = ans.get("choice")
                if ch and ch not in cand:          # a pick must be one of the offered candidates
                    rejected += 1
                    ch = None
                c = cand.get(ch) if ch else None
                stated = (ans.get("stated") or "").strip()
                if not c and stated:               # a stated address: verbatim in the record text AND in the City list
                    hit = by_key.get(normalize_address(stated))
                    if stated.lower() in (items[k]["sample"] or "").lower() and hit:
                        c = {"address": hit[0][0], "apn": hit[0][1], "why": f"stated in the record text: {stated!r}"}
                    else:
                        rejected += 1
                rows.append({"raw_address": k, "events": items[k]["events"], "sources": items[k]["sources"],
                             "city_address": c["address"] if c else None, "city_apn": c["apn"] if c else None,
                             "candidate_basis": c["why"] if c else None, "reason": ans["reason"],
                             "note": ans.get("note")})
        print(f"answers {len(rows)}; resolved to a City address {sum(1 for r in rows if r['city_address'])}; "
              f"picks outside the candidates / unverifiable stated addresses rejected {rejected}; unanswered {len(unanswered)}")
        print(json.dumps(collections.Counter(r["reason"] for r in rows), indent=1))
        mr.write_evidence(rows, "address_resolution", DEFINITION,
                          extra={"model": mr.BATCH_MODEL, "canon": "housing_rules.address 2026-10-13",
                                 "rule": "a pick is kept only if it is one of the City-list candidates offered",
                                 "unanswered": unanswered})
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
