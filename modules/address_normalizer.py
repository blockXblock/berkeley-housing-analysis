"""
Address Normalizer Module

Functions for standardizing Berkeley addresses, handling street name
variations (FIFTH <-> 5TH), and street type variations (Ave <-> AV).
"""

import re
from typing import Dict, List, Tuple, Optional


# Street number word-to-numeral conversions
NUMBERED_STREETS = {
    '1ST': 'FIRST', 'FIRST': '1ST',
    '2ND': 'SECOND', 'SECOND': '2ND',
    '3RD': 'THIRD', 'THIRD': '3RD',
    '4TH': 'FOURTH', 'FOURTH': '4TH',
    '5TH': 'FIFTH', 'FIFTH': '5TH',
    '6TH': 'SIXTH', 'SIXTH': '6TH',
    '7TH': 'SEVENTH', 'SEVENTH': '7TH',
    '8TH': 'EIGHTH', 'EIGHTH': '8TH',
    '9TH': 'NINTH', 'NINTH': '9TH',
    '10TH': 'TENTH', 'TENTH': '10TH',
    '11TH': 'ELEVENTH', 'ELEVENTH': '11TH',
    '12TH': 'TWELFTH', 'TWELFTH': '12TH',
}

# Street type canonical forms and variations
STREET_TYPES = {
    'ST': ['ST', 'STREET', 'STR'],
    'AV': ['AV', 'AVE', 'AVENUE'],
    'WY': ['WY', 'WAY'],
    'BL': ['BL', 'BLVD', 'BOULEVARD'],
    'RD': ['RD', 'ROAD'],
    'DR': ['DR', 'DRIVE'],
    'LN': ['LN', 'LANE'],
    'PL': ['PL', 'PLACE'],
    'CT': ['CT', 'COURT', 'CRT'],
    'CR': ['CR', 'CIR', 'CIRCLE'],
    'TER': ['TER', 'TERR', 'TERRACE'],
    'PK': ['PK', 'PARK', 'PKWY', 'PARKWAY'],
    'SQ': ['SQ', 'SQUARE'],
    'HWY': ['HWY', 'HIGHWAY'],
}

# Reverse lookup: variation -> canonical
TYPE_TO_CANONICAL = {}
for canonical, variations in STREET_TYPES.items():
    for var in variations:
        TYPE_TO_CANONICAL[var] = canonical


def parse_address(address: str) -> Dict[str, str]:
    """
    Parse address into components.

    Parameters
    ----------
    address : str
        Full address string (e.g., "1234 SHATTUCK Ave")

    Returns
    -------
    dict with keys: street_number, street_name, street_type, unit

    Example
    -------
    >>> parse_address("2700 SHATTUCK Ave #101")
    {'street_number': '2700', 'street_name': 'SHATTUCK',
     'street_type': 'Ave', 'unit': '101'}
    """
    result = {
        'street_number': '',
        'street_name': '',
        'street_type': '',
        'unit': '',
        'original': address
    }

    if not address:
        return result

    # Clean address
    addr = str(address).strip()

    # Extract unit number (requires explicit # or APT or UNIT marker)
    unit_match = re.search(r'(#|APT\.?|UNIT|STE\.?|SUITE)\s*([A-Z0-9-]+)\s*$', addr, re.IGNORECASE)
    if unit_match:
        result['unit'] = unit_match.group(2)
        addr = addr[:unit_match.start()].strip()

    # Split into parts
    parts = addr.split()

    if not parts:
        return result

    # First part should be street number
    if parts[0].isdigit() or re.match(r'^\d+[A-Z]?$', parts[0], re.IGNORECASE):
        result['street_number'] = parts[0]
        parts = parts[1:]

    if not parts:
        return result

    # Last part is usually street type
    last = parts[-1].upper()
    if last in TYPE_TO_CANONICAL:
        result['street_type'] = parts[-1]
        parts = parts[:-1]

    # Remaining is street name
    result['street_name'] = ' '.join(parts)

    return result


def standardize_address(address: str, uppercase: bool = True) -> str:
    """
    Standardize address to canonical form.

    - Converts to uppercase
    - Normalizes street types (Ave -> AV)
    - Removes extra whitespace
    - Strips unit numbers

    Parameters
    ----------
    address : str
        Raw address
    uppercase : bool
        Convert to uppercase (default True)

    Returns
    -------
    str : Standardized address

    Example
    -------
    >>> standardize_address("2700 Shattuck Avenue #101")
    "2700 SHATTUCK AV"
    """
    parsed = parse_address(address)

    street_num = parsed['street_number']
    street_name = parsed['street_name']
    street_type = parsed['street_type']

    # Normalize street type to canonical
    type_upper = street_type.upper()
    canonical_type = TYPE_TO_CANONICAL.get(type_upper, type_upper)

    # Build standardized address
    parts = []
    if street_num:
        parts.append(street_num)
    if street_name:
        parts.append(street_name.upper() if uppercase else street_name)
    if canonical_type:
        parts.append(canonical_type if uppercase else street_type)

    return ' '.join(parts)


def get_street_name_variations(street_name: str) -> List[str]:
    """
    Get all variations of a street name.

    Handles numbered streets (FIFTH <-> 5TH) and case variations.

    Parameters
    ----------
    street_name : str
        Street name (e.g., "FIFTH" or "5TH")

    Returns
    -------
    list : All name variations

    Example
    -------
    >>> get_street_name_variations("FIFTH")
    ['FIFTH', 'Fifth', 'fifth', '5TH', '5th', '5Th']
    """
    variations = set()
    name_upper = street_name.upper()

    # Add case variations
    variations.add(name_upper)
    variations.add(street_name.lower())
    variations.add(street_name.title())

    # Check for numbered street conversion
    if name_upper in NUMBERED_STREETS:
        alternate = NUMBERED_STREETS[name_upper]
        variations.add(alternate)
        variations.add(alternate.lower())
        variations.add(alternate.title())

    return list(variations)


def get_street_type_variations(street_type: str) -> List[str]:
    """
    Get all variations of a street type.

    Parameters
    ----------
    street_type : str
        Street type (e.g., "Ave", "AV", "Avenue")

    Returns
    -------
    list : All type variations with case variations

    Example
    -------
    >>> get_street_type_variations("Ave")
    ['AV', 'Av', 'av', 'AVE', 'Ave', 'ave', 'AVENUE', 'Avenue', 'avenue']
    """
    variations = set()
    type_upper = street_type.upper()

    # Get canonical form
    canonical = TYPE_TO_CANONICAL.get(type_upper, type_upper)

    # Get all variations for this type
    if canonical in STREET_TYPES:
        for var in STREET_TYPES[canonical]:
            variations.add(var)
            variations.add(var.lower())
            variations.add(var.title())
    else:
        # Unknown type - just add case variations
        variations.add(type_upper)
        variations.add(street_type.lower())
        variations.add(street_type.title())

    return list(variations)


def normalize_address(address: str) -> str:
    """
    Normalize address for lookup matching.

    This is the primary function for preparing addresses for geocoding lookup.

    Parameters
    ----------
    address : str
        Raw address string

    Returns
    -------
    str : Normalized address for matching
    """
    if not address:
        return ''

    # Parse and standardize
    parsed = parse_address(address)

    street_num = parsed['street_number']
    street_name = parsed['street_name'].upper()
    street_type = parsed['street_type'].upper()

    # Normalize street type
    canonical_type = TYPE_TO_CANONICAL.get(street_type, street_type)

    # Build normalized form
    return f"{street_num} {street_name} {canonical_type}".strip()


def generate_address_variations(
    street_number: str,
    street_name: str,
    street_type: str
) -> List[str]:
    """
    Generate all possible address variations for lookup.

    Parameters
    ----------
    street_number : str
    street_name : str
    street_type : str

    Returns
    -------
    list : All address variations

    Example
    -------
    >>> variations = generate_address_variations("1914", "FIFTH", "ST")
    >>> "1914 5TH St" in variations
    True
    """
    name_variations = get_street_name_variations(street_name)
    type_variations = get_street_type_variations(street_type)

    all_variations = []
    for name in name_variations:
        for stype in type_variations:
            all_variations.append(f"{street_number} {name} {stype}")

    return list(set(all_variations))


def addresses_match(addr1: str, addr2: str) -> bool:
    """
    Check if two addresses match after normalization.

    Parameters
    ----------
    addr1, addr2 : str
        Addresses to compare

    Returns
    -------
    bool : True if addresses match
    """
    return normalize_address(addr1) == normalize_address(addr2)
