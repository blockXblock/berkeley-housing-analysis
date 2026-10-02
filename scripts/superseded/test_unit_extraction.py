#!/usr/bin/env python3
"""test_unit_extraction.py -- pin the unit-count extractor's behaviour.
Run: .venv/bin/python scripts/test_unit_extraction.py

WHY THIS FILE EXISTS. This extractor was written wrong three times in one session (2026-09-26):

  1. `(?:dwelling|...)?\\s*units?` could not match "166 dwellings" -- the optional noun consumed
     "dwelling" and then `units?` demanded "unit". A 10-storey, 166-dwelling project was silently
     classified "no unit phrase". Caught by session 3c, not by me.
  2. The fix made both nouns first-class but judged SUBSET-ness from a 40-character proximity
     window, so the "Very Low" in "...166 dwellings, including 17 Very Low-Income units" attached
     to the 166 and the extractor returned 17 as the total. It also regressed a case that had
     previously worked.
  3. This version reads subset-ness from the qualifier captured INSIDE each phrase.

Each round looked careful and would have passed an eyeball. That is the point: prose extraction by
pattern is the fragile layer, and a model reading the sentence (3c's Q2) is the better instrument.
These assertions exist so round four cannot silently undo round three.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("u", ROOT / "scripts/preview_capdetail_units.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

CASES = [
    # (description, expected units, note)
    ("with 166 dwellings, including 17 Very Low-Income units, and 1,043 square-feet of commercial "
     "space", 166, "ZP2022-0046 verbatim -- the regression that returned 17"),
    ("126 dwelling units (of which 3 are live/work) and 10 are provided as low income units",
     126, "ZP2021-0046 verbatim -- sub-counts must not win"),
    ("166 dwellings", 166, "the plural, alone"),
    ("48 units", 48, "the plain form"),
    ("a 55 unit building", 55, "singular noun, plural meaning"),
    ("3 dwellings", 3, "small plural"),
    ("Second story addition to existing front SFR on lot with 3 dwellings", 3,
     "ZP2019-0159 -- the other record the plural bug hid"),
    ("2 units and 14 parking spaces", 2, "non-dwelling nouns must not be counted"),
    ("construct 8 dwellings plus 2 ADU", 8, "ADU is a sub-count of the total here"),
    ("no housing here at all", None, "no phrase -> no number, never a guess"),
    ("", None, "empty"),
]


def main() -> int:
    fails = []
    for desc, want, note in CASES:
        got, conf, found = u.extract(desc)
        if got != want:
            fails.append((desc[:46], want, got, conf, note))
    for d, want, got, conf, note in fails:
        print(f"  FAIL {d!r}: want {want}, got {got} (conf={conf})  [{note}]")
    print(f"unit_extraction: {len(CASES)-len(fails)}/{len(CASES)} cases pass")
    # the subset machinery must not be bypassed by a future edit
    assert u.extract("17 Very Low-Income units")[0] is None, \
        "a lone subset count must not be reported as a total"
    print("  + a lone subset count is not reported as a total")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
