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
        'separators': ['-', ' '],
        'total_length': 12,
        # registered validation pattern: uppercase alphanumeric, canonical 12 + up to 2 future-sub.
        'pattern': r'^[0-9A-Z]{12,14}$',
        # GLOB form of the "any out-of-class character" reject, for the SQLite trigger:
        'reject_glob': '*[^0-9A-Z]*',
        'note': 'MEASURED from 30,007 real Alameda APNs: 29,982 all-numeric 12-digit + 25 with a '
                'book LETTER suffix (48A/48H). Alphanumeric, 12 chars — NOT digits-only, NOT universal.',
    },
    # county #2 (e.g. 'San Francisco': Block-Lot, possibly alphanumeric) registers its scheme here.
}


def county_format(county):
    fmt = APN_FORMATS.get(county)
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
    """Any APN form -> the county's canonical key (alphanumeric, upper-cased), or None.

    For Alameda (book3 page4 parcel3 sub2 = 12 chars, book alphanumeric): handles
    hyphenated (55-1895-41, 48A-7075-15, 057-2046-008-05, 57-2046-1), 12-char
    (057204600100), book+spaced-rest (057 204600100), and digit-only legacies. Returns
    None for empty / multi-APN / out-of-registered-pattern.
    """
    fmt = county_format(county)
    if apn is None:
        return None
    s = str(apn).strip().upper()                 # case-fold (48a -> 48A)
    if not s or ',' in s:                         # empty or multi-APN cell
        return None
    w = fmt['segment_widths']
    total = fmt['total_length']
    parts = re.split(r'[\s\-]+', s)
    if len(parts) >= 3:
        sub = parts[3] if len(parts) >= 4 else ''
        c = parts[0].zfill(w[0]) + parts[1].zfill(w[1]) + parts[2].zfill(w[2]) + sub.zfill(w[3])
    elif len(parts) == 2:                         # book + concatenated rest ("057 204600100")
        c = parts[0].zfill(w[0]) + parts[1].zfill(total - w[0])
    else:                                         # single token (only meaningful for all-numeric APNs)
        d = ''.join(ch for ch in s if ch.isdigit())
        if not s.isdigit() or not d:
            return None
        if len(d) == total:
            c = d
        elif len(d) == total - 1:                 # legacy: missing the sub leading zero
            c = d[:total - w[3]] + d[total - w[3]:].zfill(w[3])
        elif len(d) == total - 4:                 # legacy: book2 page4 parcel2 (no sub)
            c = d[:2].zfill(w[0]) + d[2:2 + w[1]] + d[2 + w[1]:].zfill(w[2]) + '0' * w[3]
        else:
            return None
    return c if re.fullmatch(fmt['pattern'], c) else None


def is_canonical_apn(apn, county='Alameda'):
    """True iff apn already matches the county's registered canonical pattern."""
    if apn is None:
        return False
    return re.fullmatch(county_format(county)['pattern'], str(apn)) is not None
