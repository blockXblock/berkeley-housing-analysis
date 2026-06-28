"""S0 — clean address / APN / permit-family key build for the v2-from-sources rebuild.

PERMANENT, IDEMPOTENT key logic. The same raw address always yields the same AddressKey;
the match relation is the single source of truth for "are these the same building?".

Design (from the S0 acceptance gate, 2026-06-17):
- Strip ALL parentheticals ((id:N), (basement ADU), ...) before keying.
- Canonical MLK: every Martin-Luther-King variant -> 'MLK', trailing 'JR' dropped.
- Ordinal fold: ordinal words -> numeric (First->1ST, Sixty-Sixth->66TH).
- Street type NORMALIZED (Avenue->AVE), never dropped from the key.
- MATCH RELATION, not string equality: an ABSENT type is a wildcard that matches any one
  present type at the same number+street ("2820 San Pablo" ~ "2820 San Pablo Ave"), but two
  DIFFERENT present types do NOT match ("2200 Shattuck Ave" != "2200 Shattuck Way").
- Protected/distinct buildings on a shared key are separated by the DISAMBIGUATOR
  (distinct permit-family AND distinct CO date), generalized to ANY >1-hit, not a whitelist.
"""
import re, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))   # scripts/ for housing_rules


def canonicalize_apn(raw, county='Alameda'):
    """THE single APN canon for the v2-rebuild — the one entry point S0-write, S1-match, and both
    gate tests import. Delegates to the project's canonical housing_rules.to_canonical_apn (NEVER a
    fork / never strip-non-digits); returns Option-B dashed (e.g. '057-2016-021-01') or None."""
    from housing_rules import to_canonical_apn
    try:
        return to_canonical_apn(raw, county)
    except Exception:
        return None


def is_adu(value):
    """THE single reader of the CPRA ADU flag — imported everywhere the flag is checked (is_housing,
    net_units, S2), so a type mismatch can't silently dead-branch in one place while working in another.
    Normalizes every shape the column arrives as: Python bool, numpy.bool_, or the raw string
    'Yes'/'No data available'. (Bug it prevents: `str(numpy.True_).lower()` is 'true', not 'yes', so a
    bare `== 'yes'` check returned False on a true ADU and silently dropped 265 ADU dwellings.)"""
    return str(value).strip().lower() in ('yes', 'true', '1')


# ---- street-type normalization (full / variant -> canonical abbrev) ----
STREET_TYPES = {
    'avenue': 'AVE', 'ave': 'AVE', 'av': 'AVE',
    'street': 'ST', 'st': 'ST', 'str': 'ST',
    'boulevard': 'BLVD', 'blvd': 'BLVD', 'blv': 'BLVD',
    'drive': 'DR', 'dr': 'DR',
    'road': 'RD', 'rd': 'RD',
    'lane': 'LN', 'ln': 'LN',
    'court': 'CT', 'ct': 'CT',
    'place': 'PL', 'pl': 'PL',
    'terrace': 'TER', 'ter': 'TER', 'terr': 'TER',
    'way': 'WAY',
    'circle': 'CIR', 'cir': 'CIR',
    'parkway': 'PKWY', 'pkwy': 'PKWY',
    'path': 'PATH', 'plaza': 'PLZ', 'plz': 'PLZ',
    'square': 'SQ', 'sq': 'SQ', 'walk': 'WALK',
    'alley': 'ALY', 'aly': 'ALY', 'crescent': 'CRES',
}
_CANON_TYPES = set(STREET_TYPES.values())

_SIMPLE_ORD = {
    'first': '1ST', 'second': '2ND', 'third': '3RD', 'fourth': '4TH', 'fifth': '5TH',
    'sixth': '6TH', 'seventh': '7TH', 'eighth': '8TH', 'ninth': '9TH', 'tenth': '10TH',
    'eleventh': '11TH', 'twelfth': '12TH', 'thirteenth': '13TH',
}
_TENS = {'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
         'eighty': 80, 'ninety': 90}
_ONES_ORD = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5, 'sixth': 6,
             'seventh': 7, 'eighth': 8, 'ninth': 9}
_SUFFIX = {1: 'ST', 2: 'ND', 3: 'RD'}


def _ord_suffix(n):
    if 10 <= n % 100 <= 20:
        return 'TH'
    return _SUFFIX.get(n % 10, 'TH')


def _fold_ordinals(s):
    # compound: "SIXTY-SIXTH" / "SIXTY SIXTH" -> 66TH
    def comp(m):
        n = _TENS[m.group(1).lower()] + _ONES_ORD[m.group(2).lower()]
        return f"{n}{_ord_suffix(n)}"
    s = re.sub(r'\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[\s-]'
              r'(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth)\b',
              comp, s, flags=re.I)
    # plain tens ordinal: "SIXTIETH" -> 60TH (rare; handle the -tieth form)
    s = re.sub(r'\b(twen|thir|for|fif|six|seven|eigh|nine)tieth\b',
               lambda m: {'twen': '20TH', 'thir': '30TH', 'for': '40TH', 'fif': '50TH',
                          'six': '60TH', 'seven': '70TH', 'eigh': '80TH', 'nine': '90TH'}[m.group(1).lower()],
               s, flags=re.I)
    for w, n in _SIMPLE_ORD.items():
        s = re.sub(r'\b' + w + r'\b', n, s, flags=re.I)
    return s


def _canon_mlk(s):
    # all Martin Luther King variants -> MLK, drop trailing JR
    s = re.sub(r'\bMARTIN\s+LUTHER\s+KING(\s+JR)?\b', 'MLK', s, flags=re.I)
    s = re.sub(r'\bM\.?\s*L\.?\s*KING(\s+JR)?\b', 'MLK', s, flags=re.I)
    s = re.sub(r'\bMLK\s+JR\b', 'MLK', s, flags=re.I)
    return s


class AddressKey:
    __slots__ = ('number', 'street', 'stype', 'raw')

    def __init__(self, number, street, stype, raw):
        self.number = number    # str digits, '' if none
        self.street = street    # normalized street core (no type), uppercase
        self.stype = stype      # canonical type or None (absent)
        self.raw = raw

    @property
    def bucket(self):
        """Index bucket — number + street core, type-agnostic (the wildcard lives in matches())."""
        return (self.number, self.street)

    def matches(self, other):
        """The match relation. Same number+street, and type-compatible:
        equal types, or either type absent (wildcard). Different present types -> NO match."""
        if not self.number or self.number != other.number or self.street != other.street:
            return False
        if self.stype is None or other.stype is None:
            return True
        return self.stype == other.stype

    def __repr__(self):
        t = f" {self.stype}" if self.stype else ""
        return f"<{self.number} {self.street}{t}>"


def normalize_address(raw):
    """raw address string -> AddressKey (idempotent)."""
    if not raw:
        return AddressKey('', '', None, raw)
    s = str(raw)
    s = re.sub(r'\([^)]*\)', ' ', s)                 # strip ALL parentheticals
    s = re.sub(r'#\s*\S+', ' ', s)                   # strip unit "#4"
    s = re.sub(r'\bUNIT\s+\S+', ' ', s, flags=re.I)
    s = s.upper().strip()
    s = re.sub(r'\s+', ' ', s)
    s = _canon_mlk(s)
    s = _fold_ordinals(s)
    s = re.sub(r'[.,]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    # leading house number (take first of a range "1444-1446" / "1444 1446")
    m = re.match(r'^(\d+)(?:\s*[-/]\s*\d+)?\s+(.*)$', s)
    if not m:
        return AddressKey('', s, None, raw)
    number, rest = m.group(1), m.group(2).strip()
    toks = rest.split()
    stype = None
    if toks and toks[-1] in _CANON_TYPES:            # already-canonical trailing type
        stype = toks[-1]; toks = toks[:-1]
    elif toks and toks[-1].lower() in STREET_TYPES:  # variant trailing type
        stype = STREET_TYPES[toks[-1].lower()]; toks = toks[:-1]
    # drop a trailing standalone JR/SR left after MLK etc.
    while toks and toks[-1] in ('JR', 'SR'):
        toks = toks[:-1]
    street = ' '.join(toks)
    return AddressKey(number, street, stype, raw)


def disambiguate_distinct(rec_a, rec_b):
    """The generalized protected-pair / shadow rule: two records that share a matching address
    key are DISTINCT buildings iff they have distinct permit-families AND distinct CO dates.
    rec = {'families': set(), 'co': 'YYYY-MM-DD' or None}. Returns True if DISTINCT (keep both).
    Conservative: if either lacks a CO date, treat as NOT-distinct (candidate dup) -> flag, never auto-merge."""
    fa, fb = rec_a.get('families') or set(), rec_b.get('families') or set()
    ca, cb = rec_a.get('co'), rec_b.get('co')
    distinct_family = bool(fa) and bool(fb) and not (fa & fb)
    distinct_co = bool(ca) and bool(cb) and ca != cb
    return distinct_family and distinct_co
