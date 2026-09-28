"""test_chain_resolution.py -- the chain-vs-conflated rule, tested on REAL record descriptions
taken from the Planning store 2026-09-26. Run: python -m scripts.housing_rules.test_chain_resolution

Why these cases: 19% of v2 projects sit at an address with more than one Zoning Permit. Getting the
CHAIN case wrong writes a modification's completeness review as the project's acceptance date;
getting the CONFLATED case wrong silently merges two different buildings into one timeline.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from capdetail_select import cited_records, is_modification, resolve_chain


def rec(n, desc):
    return {"record": n, "description": desc, "record_type": "Zoning Permit"}


# proj35, 2190 SHATTUCK Ave (452u): an original plus two modifications of it -> ONE project
CHAIN = [
    rec("ZP2016-0117", "Demolition of an existing two story commercial building"),
    rec("ZP2022-0026", "Use Permit modification of ZP2016-0117 to revise the approved project"),
    rec("ZP2025-0101", "Use Permit Modification (SB330 PLN2025-0) of ZP2016-0117"),
]
# proj10, 3000 SHATTUCK Ave: two UNRELATED applications, no citation between them
CONFLATED = [
    rec("ZP2015-0229", "Demo existing commercial use, build 5 story mixed use building"),
    rec("ZP2022-0046", "Demolish the existing gas station, and construct a 9-story mixed use"),
]
# proj91, 2009 ADDISON St (45u): a two-step chain, the child citing the middle record
NESTED = [
    rec("ZP2017-0004", "Demolish a non-residential building over 4,000 square feet"),
    rec("ZP2018-0235", "Use Permit Modification for ZP2017-0004"),
    rec("ZP2024-0111", "Modify use permits ZP2018-0235 and ZP2017-0004"),
]


def main() -> int:
    fails = []

    def check(label, got, want):
        if got != want:
            fails.append(f"{label}: got {got!r}, want {want!r}")

    check("single", resolve_chain([CHAIN[0]])[1], "single")

    root, kind = resolve_chain(CHAIN)
    check("chain kind", kind, "chain")
    check("chain root", root and root["record"], "ZP2016-0117")

    root, kind = resolve_chain(CONFLATED)
    check("conflated kind", kind, "conflated")
    check("conflated root", root, None)

    root, kind = resolve_chain(NESTED)
    check("nested kind", kind, "chain")
    check("nested root", root and root["record"], "ZP2017-0004")

    check("citation extracted", "ZP2016-0117" in cited_records(CHAIN[1]), True)
    check("self not cited", cited_records(CHAIN[0]), set())
    check("modification detected", is_modification(CHAIN[1]), True)
    check("original is not a modification", is_modification(CHAIN[0]), False)
    # a citation WITHOUT a modification word is not a parent link (e.g. "SB330 PLN2025-0069 filed")
    check("cite without modword", is_modification(
        rec("ZP2023-0001", "SB330 Application, see PLN2022-0011 for the preliminary filing")), False)

    for f in fails:
        print("  FAIL", f)
    print(f"chain_resolution: {11-len(fails)}/11 checks pass")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
