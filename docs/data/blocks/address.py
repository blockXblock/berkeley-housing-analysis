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
- The City address-point layer's two-letter type codes (AV, BL, TE, CI, WK, HW, CM, PA) are folded to
  the full word FIRST, on the final token only (2026-10-13: 19,169 'AV' points keyed as 'benvenue av'
  and matched nothing). Folding, not stripping: Walk/Path/Cir/Hwy/Common stay IN the key because
  Berkeley has Rose Walk beside Rose St and Indian Rock Path beside Indian Rock Ave -- stripping them
  would merge distinct streets (measured: 15 false collisions in v4's event addresses).
- 2026-10-13 (John approved; measured in scratch/2026-10-13_address_canon/measure.py): the key is the part
  before the first comma; trailing city / state / zip / country go in any order ('BERKELEY CA 94705 United
  States') but never California St; the key is CUT after the last street-type token, so units and notes go
  ('TELEGRAPH AVE  101', 'HASKELL St, Rear'), and with no type token trailing unit words go; ordinals above
  tenth fold (SIXTY-SIXTH -> 66th); MLK shorthand folds to 'martin luther king jr'; half-addresses keep the
  half ('2765.5 Wallace', assessor 'HENRY ST  1/2' -> house '1231.5'); a type word that IS the name stays
  (Terrace Walk, Court St). Effect: v4 event addresses found in the City address list 56,118 -> 69,667 of
  71,891, none lost; no new two-street key collisions. The cases live in test_address.py.
- Returns (house_number, street) as a TUPLE so callers can apply house-number tolerance (rule 4c)
  instead of exact-string matching.
"""
import re

_ORD = {'first': '1st', 'second': '2nd', 'third': '3rd', 'fourth': '4th', 'fifth': '5th', 'sixth': '6th',
        'seventh': '7th', 'eighth': '8th', 'ninth': '9th', 'tenth': '10th', 'eleventh': '11th', 'twelfth': '12th',
        'thirteenth': '13th', 'fourteenth': '14th', 'fifteenth': '15th', 'sixteenth': '16th', 'seventeenth': '17th',
        'eighteenth': '18th', 'nineteenth': '19th', 'twentieth': '20th', 'thirtieth': '30th', 'fortieth': '40th',
        'fiftieth': '50th', 'sixtieth': '60th'}
_TENS = {'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70}
_ABBR = {'av': 'ave', 'bl': 'blvd', 'te': 'ter', 'ci': 'cir', 'wk': 'walk', 'hw': 'hwy', 'cm': 'common', 'pa': 'path'}
_DROP = r'(ave|avenue|st|street|blvd|boulevard|way|wy|dr|drive|rd|road|ln|lane|ct|court|pl|place|ter|terrace)'
_KEEP = r'(walk|path|cir|circle|hwy|highway|common|sq|square|pkwy|parkway|aly|alley|row|plz|plaza|loop|gdns|gardens)'
_TYPE = re.compile(rf'^({_DROP[1:-1]}|{_KEEP[1:-1]}|av|bl|te|ci|wk|hw|cm|pa)$')
_SUF = re.compile(rf'\b{_DROP}\b')
_UNIT = re.compile(r'\s+(apt|apartment|unit|ste|suite|#|bldg|building|rear|front|upper|lower|basement|lot|vacant lot|'
                   r'space|spc|room|rm|fl|floor)\b.*$')
_TAIL = re.compile(r'(\s+(berkeley|ca|united states|usa|us|\d{5}(-\d{4})?))+\s*$')
_STATE = re.compile(r'\s+california(?=\s+\d{5})|(?<=berkeley)\s+california\s*$')   # the state, never California St


def normalize_address(raw):
    if not raw:
        return ('', '')
    s = str(raw).lower().strip()
    s = s.split(',')[0]                                            # 1. the address is before the first comma
    s = re.sub(r'(?<=[a-z])\.', ' ', s)                            # M.L.K. -> m l k ; keeps 2765.5
    s = _STATE.sub('', s)                                          # 2. city / state / zip / country; '1353 Berkeley'
    s = _TAIL.sub('', s)                                           #    has no street left -> unusable (address_points)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\b(' + '|'.join(_TENS) + r')[\s-]+(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth)\b',
               lambda m: f"{_TENS[m.group(1)] + int(_ORD[m.group(2)][:-2])}{_ORD[m.group(2)][-2:]}", s)   # 4.
    for w, n in _ORD.items():
        s = re.sub(r'\b' + w + r'\b', n, s)
    s = re.sub(r'\b(m l k|mlk|m l king|ml king|martin luther king|martin l king|m luther king)( jr)?\b',
               'martin luther king jr', s)                                                             # 5.
    if re.search(r'\s1/2\s*$', s) and re.match(r'^\s*\d+\s+\D', s):   # assessor 'HENRY ST  1/2' -> house 1231.5
        s = re.sub(r'^\s*(\d+)', r'\1.5', re.sub(r'\s1/2\s*$', '', s))
    w = s.split()
    types = [i for i, t in enumerate(w) if i >= 2 and _TYPE.match(t)]
    if types:                                                      # 3. cut after the last street-type token
        w = w[:types[-1] + 1]
        w[-1] = _ABBR.get(w[-1], w[-1])
        s = ' '.join(w)
    else:
        s = _UNIT.sub('', s)
    half = re.match(r'^\s*(\d+)(\.5|\s+1/2)\s+(.*)$', s)                                                # 6.
    if half:
        num, s = half.group(1) + '.5', half.group(3)
    else:
        m = re.match(r'^\s*(\d+)(?!\d|st\b|nd\b|rd\b|th\b)', s)
        num = m.group(1) if m else ''
    street = re.sub(r'[^a-z0-9 ]', ' ', s)
    if num and not half:
        street = re.sub(r'^\s*\d+\s*', '', street)
    sw = street.split()                                            # a type word that IS the name stays:
    street = ' '.join(sw[:1] + [t for t in sw[1:] if not _SUF.fullmatch(t)])   # Terrace Walk, St Charles
    return (num, street)
