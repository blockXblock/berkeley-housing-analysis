"""Canonical APN normalization — the SINGLE source of truth for APN form.

GENERALITY GUARD (the whole point of the statewide design): an APN's canonical form is
its ASSESSING COUNTY's REGISTERED format, NOT a universal assumption. Two levels of the
trap to avoid:
  * length/structure: CA has 58 independent county formats (SF uses Block-Lot, not
    book-page-parcel). A county's canonical LENGTH comes from ITS registered format.
  * CHARACTER CLASS: APNs are alphanumeric in the general case (BOE: "numeric OR
    alphanumeric"); letter suffixes appear on subdivided/condo/amended parcels. Even
    ALAMEDA carries 25 alphanumeric APNs (book 48A/48H). So `apn_normalized` is TEXT and
    the canonical form is NOT "digits-only" — it is whatever the county's registered
    char-class allows.

`to_canonical_apn(raw, county)` parses the APN STRING (never the assessor's component
columns, frequently NULL even when the string has the full number), upper-cases, folds
every variant to the county's canonical key, and validates against the county's
REGISTERED pattern. Returns None for empty / multi-APN / unparseable / out-of-pattern.
Authority-scoped: the key is (county, canonical), never the canonical alone.

Every consumer imports THIS (materialize_assessed_value, export_explorer_data_v2,
build_parcel_crosswalk, shake_detectors) — no per-script canon copies.
"""
import re

# --- per-county APN format registry (the generality layer) -----------------
# Mirrors the TARGET schema's jurisdictions.apn_format. Each county registers its OWN
# measured scheme — structure, per-segment widths, CHARACTER CLASS, separators, the
# canonical length, and a validation PATTERN. The DB enforcement reads the pattern FROM
# here; county #2's alphanumeric / Block-Lot format is a registry row, not a code change.
APN_FORMATS = {
    'Alameda': {
        'structure': 'book-page-parcel-sub',
        'segment_widths': [3, 4, 3, 2],          # book, page, parcel, sub
        'char_class': 'alphanumeric',            # book may carry a letter (48A/48H); rest numeric
        'input_separators': ['-', ' '],          # accepted on the way in (raw is chaotic)
        'canonical_separator': '-',              # the ONE separator the canonical form uses (Option B)
        'total_length': 12,                      # digit count (canonical adds 3 separators -> 15 chars)
        # registered validation pattern (Option B — STRUCTURE-PRESERVING): one canonical hyphen,
        # segment widths kept, uppercase alphanumeric, variable parcel/sub for deeper splits.
        'pattern': r'^[0-9A-Z]{3}-[0-9A-Z]{4}-[0-9A-Z]{3,}-[0-9A-Z]{2,}$',
        'note': 'MEASURED from 30,007 real Alameda APNs: 29,982 all-numeric + 25 with a book LETTER '
                '(48A/48H). Canonical = book3-page4-parcel3-sub2 joined by "-" (structure-preserving, '
                'Option B). NOT digits-only, NOT a fixed-width concat, NOT universal.',
    },
    # county #2 (e.g. 'San Francisco': Block-Lot) registers its OWN separator/widths/pattern here.
}


def county_format(county):
    fmt = APN_FORMATS.get(county)
    if fmt is None and county is not None:
        # county names are proper nouns; the registry key is title-case. A lowercase key used to
        # raise, and callers that swallowed the raise silently degraded to no-APN matching
        # (the 2026-07-03 residual-chase lesson) — resolve case-insensitively instead.
        fmt = APN_FORMATS.get(str(county).strip().title())
    if fmt is None:
        raise ValueError(f"no registered APN format for assessing county {county!r}")
    return fmt


def canonical_length(county):
    """The registered canonical length for a county (drives the DB trigger bound)."""
    return county_format(county)['total_length']


def registered_pattern(county):
    """The county's registered validation regex (the trigger enforces this, attributed)."""
    return county_format(county)['pattern']


def to_canonical_apn(apn, county='Alameda'):
    """Any APN form -> the county's canonical key (Option B: structure-preserving), or None.

    Folds the chaotic raw forms (hyphen/space/none, mixed widths, case) to ONE canonical
    form: per-segment zero-padded to the registered widths, joined by the county's canonical
    separator, upper-cased. For Alameda: book3-page4-parcel3-sub2 with "-".
      55-1895-41 -> 055-1895-041-00 ; 057 204600100 -> 057-2046-001-00 ;
      57-2046-1 -> 057-2046-001-00 ; 48A-7075-15 -> 48A-7075-015-00.
    Returns None for empty / multi-APN / out-of-registered-pattern.
    """
    fmt = county_format(county)
    if apn is None:
        return None
    s = str(apn).strip().upper()                 # case-fold (48a -> 48A)
    if not s or ',' in s:                         # empty or multi-APN cell
        return None
    w = fmt['segment_widths']
    total = fmt['total_length']
    sep = fmt['canonical_separator']
    parts = re.split(r'[\s\-]+', s)
    if len(parts) >= 3:
        sub = parts[3] if len(parts) >= 4 else ''
        segs = [parts[0].zfill(w[0]), parts[1].zfill(w[1]), parts[2].zfill(w[2]), sub.zfill(w[3])]
    elif len(parts) == 2:                         # book + concatenated rest ("057 204600100")
        rest = parts[1].zfill(total - w[0])       # split the rest by the registered widths
        segs = [parts[0].zfill(w[0]), rest[:w[1]], rest[w[1]:w[1] + w[2]], rest[w[1] + w[2]:]]
    elif re.fullmatch(r'\d+[A-Z]\d{9}', s):       # single-token ALPHANUMERIC book-letter concat ("048H769000300")
        # mirrors the numeric concat above but the book carries a letter (48A/48H class).
        # bn drops its padding zero so book is the 3-char registered form (048->48, +H -> "48H").
        m = re.fullmatch(r'(\d+)([A-Z])(\d{9})', s)
        bn, letter, rest = m.groups()
        book = bn.lstrip('0') + letter
        segs = [book, rest[:w[1]], rest[w[1]:w[1] + w[2]], rest[w[1] + w[2]:]]
    else:                                         # single token (only meaningful for all-numeric APNs)
        d = ''.join(ch for ch in s if ch.isdigit())
        if not s.isdigit() or not d:
            return None
        if len(d) == total - 1:                   # legacy: missing the sub leading zero
            d = d[:total - w[3]] + d[total - w[3]:].zfill(w[3])
        elif len(d) == total - 4:                 # legacy: book2 page4 parcel2 (no sub)
            d = d[:2].zfill(w[0]) + d[2:2 + w[1]] + d[2 + w[1]:].zfill(w[2]) + '0' * w[3]
        if len(d) != total:
            return None
        segs = [d[:w[0]], d[w[0]:w[0] + w[1]], d[w[0] + w[1]:w[0] + w[1] + w[2]], d[w[0] + w[1] + w[2]:]]
    c = sep.join(segs)
    return c if re.fullmatch(fmt['pattern'], c) else None


def canon_with_reason(apn, county='Alameda'):
    """Like to_canonical_apn but returns (canonical_or_None, reason).

    reason is None on success, else a short string explaining the refusal — so callers can
    LOG every rejected APN (raw value + reason) instead of dropping it silently. Reuses
    to_canonical_apn as the single source of folding truth; only classifies the None cases.
    """
    c = to_canonical_apn(apn, county)
    if c is not None:
        return c, None
    if apn is None or not str(apn).strip():
        return None, 'empty'
    s = str(apn).strip()
    if ',' in s:
        return None, 'multi-APN cell (comma)'
    digits = ''.join(ch for ch in s if ch.isdigit())
    total = canonical_length(county)
    if len(digits) != total:
        return None, f'wrong digit length ({len(digits)}; need {total})'
    return None, 'out-of-registered-pattern'


def is_canonical_apn(apn, county='Alameda'):
    """True iff apn already matches the county's registered canonical pattern."""
    if apn is None:
        return False
    return re.fullmatch(county_format(county)['pattern'], str(apn)) is not None
