#!/usr/bin/env python3
r"""GATE: one implementation per canonical rule.

WHY. CLAUDE.md has said "never a new per-script copy" since June, in bold. Four copies of the address
normalizer were consolidated 2026-07-03. By 2026-09-26 there were two again, and the author (me) then
imported the WRONG one -- build_v2/s0_keys.normalize_address, the v3 pipeline's internal keying --
while believing it was obeying the rule. A canon nobody can name gets re-derived.

WHAT IT CHECKS. For each canonical concept, exactly one module may DEFINE it; everyone else must
import. A local `def normalize_address` outside the canon is a failure, not a style preference.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# concept -> (the ONE module allowed to define it, the def-name pattern, why it matters)
# concept -> (the ONE module allowed to define it, a DISTINCTIVE def pattern, why it matters)
# The pattern must be distinctive: `def classify` and `def extract` occur all over a Python tree and
# gave 10 and 24 false hits on the first run, including inside .venv. Match the signature, not the name.
CANON = {
    "address key": ("scripts/housing_rules/address.py",
                    r"def\s+normalize_address\s*\(",
                    "rule 4c; a street-only key matches every project on that street"),
    "APN canon": ("scripts/housing_rules/apn.py",
                  r"def\s+to_canonical_apn\s*\(",
                  "rule 4; strip-non-digits gave 890/892 false-dead"),
    "permit role": ("scripts/housing_rules/permit_effect.py",
                    r"def\s+permit_effect\s*\(",
                    "what a permit does (model-read evidence; the regex classify is superseded)"),
    "record role": ("scripts/housing_rules/planning_record.py",
                    r"RECORD_ROLES\s*=\s*\{",
                    "which Planning record is the application; LMSAP is not a primary application"),
    "housing filter": ("scripts/housing_rules/planning_filter.py",
                       r"HOUSING\s*=\s*re\.compile",
                       "a plural blindness here excluded a 166-dwelling project"),
    "building label": ("scripts/housing_rules/building_label.py",
                       r"_DESIG_LETTER\s*=\s*re\.compile",
                       "which building a permit belongs to; 'Building a new house' is not Building A"),
}
# Known copies OUTSIDE live machinery, each named with its reason (John, 2026-09-28). Named files, not
# skipped folders: a NEW copy anywhere, including these folders, still fails.
ALLOWED = {
    "address key": {
        "modules/address_normalizer.py": "the Feb-2026 teaching notebooks' package (01_collection-03_analysis)",
        "scripts/build_v2/s0_keys.py": "the v3 curriculum's internal keying; never imported by live code",
    },
}
# A sandbox (experiments/) and a throwaway (scratch/) may hold anything; a LIVE path may not.
SKIP = ("/.venv/", "/superseded/", "/scripts/gates/", "/test_", "/scratch/", "/experiments/",
        "/.ipynb_checkpoints/", "/node_modules/", "/site-packages/")

def _live_py():
    for p in ROOT.rglob("*.py"):
        rel = str(p.relative_to(ROOT))
        if any(s in "/" + rel for s in SKIP):
            continue
        yield rel, p


def run() -> tuple[bool, list[str]]:
    msgs, ok = [], True
    for concept, (owner, pat, why) in CANON.items():
        rx = re.compile(pat)
        definers = []
        for rel, p in _live_py():
            try:
                if rx.search(p.read_text(errors="replace")):
                    definers.append(rel)
            except Exception:
                continue
        allowed = ALLOWED.get(concept, {})
        extra = [d for d in definers if d != owner and d not in allowed]
        if owner not in definers:
            ok = False
            msgs.append(f"FAIL {concept}: the canon module {owner} does not define it")
        if extra:
            ok = False
            msgs.append(f"FAIL {concept}: defined in {len(extra)+1} places -- {owner} (canon) "
                        f"PLUS {extra}. {why}")
        if owner in definers and not extra:
            known = [d for d in definers if d in allowed]
            msgs.append(f"ok   {concept}: one definition ({owner})"
                        + (f" + {len(known)} named exception(s): {known}" if known else ""))
    return ok, msgs


if __name__ == "__main__":
    ok, msgs = run()
    print("\n".join(msgs))
    raise SystemExit(0 if ok else 1)
