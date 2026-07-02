"""THE address normalizer — the single importable home for CLAUDE.md rule 4c's address-matching
layer (lifted 2026-07-03 from scripts/shake_detectors.py:104, the most evolved of what had become
FOUR per-script copies: build_parcel_crosswalk.py, shake_detectors.py, and two scratch matchers).
Same discipline as to_canonical_apn: IMPORT it, never re-type it — per-script copies drift, and the
2026-07-03 residual chase re-learned why (a fourth copy plus a swallowed county-key error silently
degraded a reconciliation join to address-only matching).

Semantics (each choice is load-bearing):
- Strips ONLY the trailing "<city> <zip>" tail (assessor situs carries it) — must NOT eat a street
  NAMED "Berkeley Way" (the proj136 corner-lot case, 2026-06-16).
- Ordinal words -> numerals (SIXTH == 6TH — rule 4c).
- Street-type suffixes dropped (ST/AVE/WAY/... — permit and assessor records disagree on them).
- Returns (house_number, street) as a TUPLE so callers can apply house-number tolerance (rule 4c)
  instead of exact-string matching.
"""
import re

_ORD = {'first': '1st', 'second': '2nd', 'third': '3rd', 'fourth': '4th', 'fifth': '5th',
        'sixth': '6th', 'seventh': '7th', 'eighth': '8th', 'ninth': '9th', 'tenth': '10th'}
_SUF = re.compile(r'\b(ave|avenue|st|street|blvd|boulevard|way|wy|dr|drive|rd|road|ln|lane|ct|court|pl|place|ter|terrace)\b')


def normalize_address(raw):
    """Normalize a Berkeley address for cross-source matching. Returns (house_number, street),
    both lowercase strings ('' when absent). See module docstring for the semantics."""
    if not raw:
        return ('', '')
    s = str(raw).lower()
    s = re.sub(r'\s+berkeley\s*,?\s*(ca\s*)?\d{5}(-\d+)?\s*$', '', s)
    s = re.sub(r'\s+berkeley\s*$', '', s)
    for w, n in _ORD.items():
        s = re.sub(r'\b' + w + r'\b', n, s)
    m = re.match(r'\s*(\d+)', s)
    num = m.group(1) if m else ''
    street = _SUF.sub('', s)
    street = re.sub(r'[^a-z0-9 ]', ' ', street)
    street = re.sub(r'^\s*\d+\s*', '', street).strip()
    street = re.sub(r'\s+', ' ', street)
    return (num, street)
