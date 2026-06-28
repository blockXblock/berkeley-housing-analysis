"""Permanent regression gate for s0_keys — FAILS if the clean-key behavior drifts.

Pure key-logic assertions (no DB dependency) so it pins the contract regardless of data state.
Run: python -m scripts.build_v2.test_s0_gate   (or: python scripts/build_v2/test_s0_gate.py)

This is the anti-drift guard: every later stage imports s0_keys; this test is what catches a
silent change to normalize_address / AddressKey.matches / disambiguate_distinct.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from s0_keys import normalize_address as N, disambiguate_distinct as D, canonicalize_apn

FAILS = []
def check(cond, msg):
    if not cond: FAILS.append(msg)

# ---- normalize_address: literal input -> (number, street, stype) ----
CASES = [
    ("2099 M L KING JR Way",            ("2099", "MLK", "WAY")),   # MLK variant + JR dropped
    ("2099 MLK Jr Way",                 ("2099", "MLK", "WAY")),   # the other MLK variant -> same
    ("2210 M L KING JR Way (basement ADU)", ("2210", "MLK", "WAY")), # parenthetical stripped
    ("2820 SAN PABLO Ave",              ("2820", "SAN PABLO", "AVE")),
    ("2820 San Pablo",                  ("2820", "SAN PABLO", None)),  # absent type
    ("1157 FRANCISCO",                  ("1157", "FRANCISCO", None)),
    ("2138 KITTREDGE St (id:118)",      ("2138", "KITTREDGE", "ST")),  # (id:N) stripped
    ("1222 SIXTY-SIXTH St",             ("1222", "66TH", "ST")),       # compound ordinal
    ("2411 Sixth St",                   ("2411", "6TH", "ST")),        # simple ordinal
    ("1444-1446 Fifth St",              ("1444", "5TH", "ST")),        # range -> first number
    ("2455 TELEGRAPH Ave",              ("2455", "TELEGRAPH", "AVE")),
]
for raw, exp in CASES:
    k = N(raw)
    got = (k.number, k.street, k.stype)
    check(got == exp, f"normalize_address({raw!r}) = {got}, expected {exp}")

# idempotency: normalizing twice (via reconstructed canonical) is stable
for raw, _ in CASES:
    k1 = N(raw)
    recon = f"{k1.number} {k1.street}" + (f" {k1.stype}" if k1.stype else "")
    k2 = N(recon)
    check((k1.number, k1.street, k1.stype) == (k2.number, k2.street, k2.stype),
          f"NOT idempotent: {raw!r} -> {recon!r} drifts")

# ---- match relation: type-wildcard (absent ~ any one present), different-present != ----
def m(a, b): return N(a).matches(N(b))
check(m("2820 San Pablo Ave", "2820 San Pablo"),      "wildcard: absent type must match present (2820 San Pablo)")
check(m("1157 FRANCISCO ST", "1157 FRANCISCO"),       "wildcard: 1157 Francisco absent~present")
check(m("2099 MLK Way", "2099 M L King Jr Way"),      "MLK variants must match")
check(not m("2200 Shattuck Ave", "2200 Shattuck Way"),"different PRESENT types must NOT merge (Ave vs Way)")
check(not m("2205 Blake St", "2201 Blake St"),        "different house numbers must NOT match")
check(not m("2816 Prince Ave", "2816 Prince St"),     "different present types (Prince Ave vs St) must NOT merge")

# ---- disambiguator: distinct iff distinct permit-family AND distinct CO ----
check(D({'families': {'B1'}, 'co': '2020-01-01'}, {'families': {'B2'}, 'co': '2022-02-02'}) is True,
      "distinct families + distinct CO -> DISTINCT")
check(D({'families': {'B1'}, 'co': '2020-01-01'}, {'families': {'B1'}, 'co': '2022-02-02'}) is False,
      "shared family -> NOT distinct (candidate dup)")
check(D({'families': {'B1'}, 'co': None},          {'families': {'B2'}, 'co': '2022-02-02'}) is False,
      "missing CO -> conservatively NOT distinct (flag, never auto-merge)")

# ---- APN canon: ONE function, Option-B DASHED format (pins the format the matcher relies on) ----
check(canonicalize_apn('057 201602101') == '057-2016-021-01', "canonicalize_apn must emit Option-B dashed")
check(canonicalize_apn('057201602101') == '057-2016-021-01', "canonicalize_apn must be raw-input tolerant, dashed out")
check(canonicalize_apn('057-2016-021-01') == '057-2016-021-01', "canonicalize_apn idempotent on dashed input")

if __name__ == "__main__":
    if FAILS:
        print(f"S0 GATE: FAIL ({len(FAILS)})")
        for f in FAILS: print("  XXX", f)
        sys.exit(1)
    print(f"S0 GATE: PASS ({len(CASES)} normalize + idempotency + 6 match + 3 disambig assertions)")
