"""Canonical APN normalization — the SINGLE source of truth for Alameda APN form.

CANONICAL STORED FORM: 12 digits, no punctuation, zero-padded — book(3) page(4)
parcel(3) sub(2). Example: `057204600100`. EVERY APN column in the DB stores ONLY
this form (enforced by DB triggers/CHECK constraints, 2026-06-16).

`to_canonical_apn(any)` parses the APN STRING (never the assessor's BOOK/PAGE/PARCEL/
SUB_PARCEL columns — those are frequently NULL even when the string carries the full
number, e.g. "59-2325-38", which collapsed distinct parcels to ...000). It accepts
every variant that has bitten this project and returns the one canonical form, or
None for an unparseable / multi-APN cell (the caller decides what to do with None).

Every consumer imports THIS (build_parcel_crosswalk, materialize_assessed_value,
shake_detectors, export_explorer_data_v2) — no per-script canon copies.
"""
import re

CANONICAL_RE = re.compile(r'^\d{12}$')


def to_canonical_apn(apn):
    """Any APN form -> 12-digit canonical (book3 page4 parcel3 sub2), or None.

    Handles: hyphenated (55-1895-41, 057-2046-008-05, 57-2046-1), 12-digit
    (057204600100), book+spaced-9 (057 204600100), and digit-only legacies
    (11-digit missing a sub pad, 8-digit book2-page4-parcel2). Returns None for
    empty, multi-APN comma/concat cells, or anything not resolvable to 12 digits.
    """
    if apn is None:
        return None
    s = str(apn).strip()
    if not s or ',' in s:
        return None  # empty or multi-APN cell — not a single APN
    parts = re.split(r'[\s\-]+', s)
    if len(parts) >= 3:
        sub = parts[3] if len(parts) >= 4 else ''
        c = parts[0].zfill(3) + parts[1].zfill(4) + parts[2].zfill(3) + sub.zfill(2)
    elif len(parts) == 2:                       # book + 9-digit rest ("057 204600100")
        c = parts[0].zfill(3) + parts[1].zfill(9)
    else:                                       # single token, digits only
        d = ''.join(ch for ch in s if ch.isdigit())
        if len(d) == 12:
            c = d
        elif len(d) == 11:                      # missing the sub leading zero
            c = d[:10] + d[10:].zfill(2)
        elif len(d) == 8:                       # legacy book2 page4 parcel2 (no sub)
            c = d[:2].zfill(3) + d[2:6] + d[6:8].zfill(3) + '00'
        else:
            return None
    return c if CANONICAL_RE.fullmatch(c) else None


def is_canonical_apn(apn):
    """True iff apn is already in the 12-digit canonical stored form."""
    return apn is not None and CANONICAL_RE.fullmatch(str(apn)) is not None
