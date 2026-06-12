"""Pure classifier functions over housing_rules.lookups.

No notebook state. No database access. No I/O. Every function is callable from
D5, D6, ad-hoc scripts, or (in the SQL rebuild) a CASE expression.

Behavioral conventions:
    None input  -> None / False output (missing data is a valid case)
    Out-of-range non-None input -> raise ValueError (fail loudly per discipline)

The "later cycle owns shared boundary" rule for cycle_for_date is implemented
here by iterating cycles in descending start_date order. The lookup data stores
boundaries verbatim from cited sources.
"""
from datetime import date
from typing import Optional, List

from .lookups import (
    RHNA_CYCLES,
    PROJECTION_PERIODS,
    INCOME_TIERS,
    STREAMLINING_PROVISIONS,
)


def cycle_for_date(d: Optional[date]) -> Optional[str]:
    """Return the RHNA cycle name ("5th", "6th") containing date `d`.

    Args:
        d: A datetime.date, or None for missing data.

    Returns:
        "5th" or "6th" for valid in-range dates.
        None when `d` is None.

    Raises:
        ValueError: when `d` is a real date but falls outside all defined cycles
                    (pre-5th or post-6th). Future cycles need to be added to
                    lookups.RHNA_CYCLES before classification will succeed.

    Boundary convention:
        When two cycles share a boundary date (e.g., 5th ends 2023-01-31 and
        6th starts 2023-01-31), the LATER cycle owns the date. Implemented by
        iterating cycles in descending start_date order and returning the first
        match.

    SQL equivalent (after lookups become tables):
        SELECT name FROM rhna_cycles
        WHERE :d BETWEEN start_date AND end_date
        ORDER BY start_date DESC LIMIT 1;
        -- raises in application code if no row returned
    """
    if d is None:
        return None
    for cycle in sorted(RHNA_CYCLES, key=lambda c: c["start"], reverse=True):
        if cycle["start"] <= d <= cycle["end"]:
            return cycle["name"]
    raise ValueError(
        f"date {d.isoformat()} is outside all defined RHNA cycles "
        f"(earliest: {min(c['start'] for c in RHNA_CYCLES).isoformat()}, "
        f"latest: {max(c['end'] for c in RHNA_CYCLES).isoformat()}). "
        f"Add a new cycle to lookups.RHNA_CYCLES if this is intentional."
    )


def is_projection_period(d: Optional[date], cycle: str = "6th") -> bool:
    """True if `d` falls within the projection period for the named cycle.

    Args:
        d: A datetime.date, or None.
        cycle: Name of the cycle whose projection period to check (default "6th").

    Returns:
        True if start <= d <= end (inclusive) for the named cycle's projection period.
        False otherwise, including when `d` is None or when the date is
        outside the projection-period window.

    Note: this function does NOT raise for out-of-window dates. The semantics
    are a boolean predicate ("is this date in the projection period?") for
    which "no" is always a valid answer. Compare to cycle_for_date, which is
    a lookup that must produce a name and fails loudly when it cannot.

    SQL equivalent:
        SELECT EXISTS(
            SELECT 1 FROM projection_periods
            WHERE cycle = :cycle AND :d BETWEEN start_date AND end_date
        );
    """
    if d is None:
        return False
    for pp in PROJECTION_PERIODS:
        if pp["cycle"] == cycle and pp["start"] <= d <= pp["end"]:
            return True
    return False


def valid_income_tiers_for_year(year: int) -> List[str]:
    """Return the list of income tier names reportable in APR year `year`.

    Args:
        year: An APR reporting calendar year (e.g., 2024).

    Returns:
        List of tier names (e.g., ["EXTREMELY_LOW", "VLOW", "LOW", "MOD",
        "ABOVE_MOD"]). Order matches insertion order in lookups.INCOME_TIERS.

    Raises:
        ValueError: if `year` is outside the union of all tier valid ranges
                    (i.e., no tier is applicable). This signals that
                    INCOME_TIERS needs an entry for the new year, not that
                    the question has a valid empty answer.

    SQL equivalent:
        SELECT name FROM income_tiers
        WHERE :year BETWEEN valid_from AND valid_to;
    """
    tiers = [t["name"] for t in INCOME_TIERS if t["valid_from"] <= year <= t["valid_to"]]
    if not tiers:
        all_from = min(t["valid_from"] for t in INCOME_TIERS)
        all_to   = max(t["valid_to"]   for t in INCOME_TIERS)
        raise ValueError(
            f"year {year} is outside all income tier valid ranges "
            f"({all_from}-{all_to}). Add tier entries to lookups.INCOME_TIERS "
            f"if APR coverage should extend here."
        )
    return tiers


def valid_streamlining_provisions_for_year(year: int) -> List[str]:
    """Return the list of streamlining provision names applicable in APR year `year`.

    Args:
        year: An APR reporting calendar year (e.g., 2024).

    Returns:
        List of provision names (e.g., ["SB35", "SB9", "AB2011", "SB6", "SB423"]
        for 2024). Order matches insertion order in
        lookups.STREAMLINING_PROVISIONS.

    Raises:
        ValueError: if `year` is outside the union of all provision valid
                    ranges. Same rationale as valid_income_tiers_for_year.

    SQL equivalent:
        SELECT name FROM streamlining_provisions
        WHERE :year BETWEEN valid_from AND valid_to;
    """
    provs = [p["name"] for p in STREAMLINING_PROVISIONS if p["valid_from"] <= year <= p["valid_to"]]
    if not provs:
        all_from = min(p["valid_from"] for p in STREAMLINING_PROVISIONS)
        all_to   = max(p["valid_to"]   for p in STREAMLINING_PROVISIONS)
        raise ValueError(
            f"year {year} is outside all streamlining provision valid ranges "
            f"({all_from}-{all_to}). Add provision entries to "
            f"lookups.STREAMLINING_PROVISIONS if APR coverage should extend here."
        )
    return provs
