"""Smoke test for scripts.housing_rules. Run as:

    python -m scripts.housing_rules.test_smoke

Mandatory: this file must pass before any notebook integration. If a test
fails, fix the underlying classifier or lookup, re-run, repeat until clean.

Tests cover the spec from the Phase B handoff plus additional fail-loud cases
for the year-based functions (valid_income_tiers_for_year,
valid_streamlining_provisions_for_year) where the same out-of-range / None-input
discipline applies.
"""
from datetime import date

from scripts.housing_rules.classifiers import (
    cycle_for_date,
    is_projection_period,
    valid_income_tiers_for_year,
    valid_streamlining_provisions_for_year,
)


def _expect_raises(callable_, exc_type, label):
    try:
        result = callable_()
    except exc_type as e:
        return  # expected
    raise AssertionError(f"{label}: expected {exc_type.__name__}, got result {result!r}")


def main() -> int:
    # --- cycle boundary tests (from Phase B handoff, verbatim) ---
    assert cycle_for_date(date(2022, 12, 31)) == "5th", "deep 5th cycle"
    assert cycle_for_date(date(2023, 1, 30))  == "5th", "5th cycle's last day before shared boundary"
    assert cycle_for_date(date(2023, 1, 31))  == "6th", "boundary owned by later cycle (6th)"
    assert cycle_for_date(date(2023, 2, 1))   == "6th", "day after shared boundary"
    assert cycle_for_date(date(2031, 1, 31))  == "6th", "6th cycle's last documented day"

    # --- 5th cycle start boundary (added: same convention applies) ---
    assert cycle_for_date(date(2015, 1, 31))  == "5th", "5th cycle's first day"

    # --- missing data ---
    assert cycle_for_date(None) is None, "None input -> None output"

    # --- out of range: fail loudly ---
    _expect_raises(lambda: cycle_for_date(date(2031, 2, 1)),  ValueError, "post-6th raises")
    _expect_raises(lambda: cycle_for_date(date(2014, 12, 31)), ValueError, "pre-5th raises")

    # --- projection period (verbatim from spec) ---
    assert is_projection_period(date(2022, 6, 30)) is True,  "projection start boundary"
    assert is_projection_period(date(2022, 7, 1))  is True,  "deep projection period"
    assert is_projection_period(date(2023, 1, 30)) is True,  "projection end boundary"
    assert is_projection_period(date(2023, 1, 31)) is False, "day 1 of 6th cycle proper, NOT projection"
    assert is_projection_period(date(2022, 6, 29)) is False, "day before projection start"
    assert is_projection_period(None)              is False, "None -> False (predicate semantics)"

    # --- projection period: bounds beyond window stay False (predicate, doesn't raise) ---
    assert is_projection_period(date(1999, 1, 1))  is False, "far-past date is False, no raise"
    assert is_projection_period(date(2099, 1, 1))  is False, "far-future date is False, no raise"

    # --- projection period: non-existent cycle returns False ---
    assert is_projection_period(date(2022, 7, 1), cycle="7th") is False, \
        "unknown cycle name returns False, not raise"

    # --- income tiers (verbatim from spec) ---
    tiers_2024 = valid_income_tiers_for_year(2024)
    assert "ACUTELY_LOW" not in tiers_2024, "ACUTELY_LOW not yet reportable in 2024"
    assert "EXTREMELY_LOW" in tiers_2024,  "EXTREMELY_LOW reportable in 2024"

    tiers_2025 = valid_income_tiers_for_year(2025)
    assert "ACUTELY_LOW" in tiers_2025,    "ACUTELY_LOW first reportable in 2025"
    assert "EXTREMELY_LOW" in tiers_2025,  "EXTREMELY_LOW still reportable in 2025"

    # --- income tiers: stable across the cycle window ---
    tiers_2018 = valid_income_tiers_for_year(2018)
    assert set(tiers_2018) == {"EXTREMELY_LOW", "VLOW", "LOW", "MOD", "ABOVE_MOD"}, \
        "pre-ACUTELY_LOW tier set in 2018"

    # --- income tiers: out of range raises ---
    _expect_raises(lambda: valid_income_tiers_for_year(2017), ValueError, "pre-2018 tier lookup raises")
    _expect_raises(lambda: valid_income_tiers_for_year(2032), ValueError, "post-2031 tier lookup raises")

    # --- streamlining provisions: progressive accumulation by year ---
    provs_2018 = valid_streamlining_provisions_for_year(2018)
    assert provs_2018 == ["SB35"], f"only SB35 in 2018, got {provs_2018}"

    provs_2022 = valid_streamlining_provisions_for_year(2022)
    assert set(provs_2022) == {"SB35", "SB9"}, f"SB35+SB9 in 2022, got {provs_2022}"

    provs_2023 = valid_streamlining_provisions_for_year(2023)
    assert set(provs_2023) == {"SB35", "SB9", "AB2011", "SB6"}, \
        f"SB35+SB9+AB2011+SB6 in 2023, got {provs_2023}"

    provs_2024 = valid_streamlining_provisions_for_year(2024)
    assert set(provs_2024) == {"SB35", "SB9", "AB2011", "SB6", "SB423"}, \
        f"all five in 2024, got {provs_2024}"

    # --- streamlining: out of range raises ---
    _expect_raises(lambda: valid_streamlining_provisions_for_year(2017), ValueError,
                   "pre-SB35 provisions lookup raises")
    _expect_raises(lambda: valid_streamlining_provisions_for_year(2050), ValueError,
                   "post-all-sunsets provisions lookup raises")

    _check_to_canonical_apn()
    _check_sb9_units()

    print("All smoke tests passed.")
    return 0


def _check_to_canonical_apn():
    from scripts.housing_rules.apn import (to_canonical_apn, is_canonical_apn,
                                           canonical_length, registered_pattern)
    cases = {  # the bitten variants + an ALPHANUMERIC Alameda APN (book 48A) -> canonical
        "55-1895-41": "055189504100", "057204600100": "057204600100",
        "055-1895-018-05": "055189501805", "057 204600100": "057204600100",
        "57-2046-1": "057204600100", "05518220133": "055182201303",
        "57203217": "057203201700", "052 143301000": "052143301000",
        "48A-7075-15": "48A707501500", "48h-7680-1-2": "48H768000102",  # alphanumeric + case-fold
    }
    for inp, exp in cases.items():
        got = to_canonical_apn(inp, "Alameda")
        assert got == exp, f"{inp} -> {got} != {exp}"
        assert len(got) == 12, f"Alameda canonical must be 12, got {len(got)} for {inp}"
    assert canonical_length("Alameda") == 12                       # Alameda's REGISTERED length
    assert registered_pattern("Alameda") == r'^[0-9A-Z]{12,14}$'   # alphanumeric, NOT digits-only
    assert to_canonical_apn("057-2046-008-03, 057-2046-008-02", "Alameda") is None  # multi-APN
    assert to_canonical_apn(None, "Alameda") is None and to_canonical_apn("", "Alameda") is None
    assert is_canonical_apn("057204600100", "Alameda") and is_canonical_apn("48A707501500", "Alameda")
    assert not is_canonical_apn("57-2046-1", "Alameda")            # hyphenated raw -> not canonical
    # generality guard: an unregistered county raises (NOT a silent default-to-12)
    try:
        to_canonical_apn("57-2046-1", "Imaginary")
        raise AssertionError("unregistered county must raise")
    except ValueError:
        pass
    print("to_canonical_apn: 10 variants (incl. 48A alphanumeric) + pattern + multi/null + "
          "unregistered-raises — PASS")


def _check_sb9_units():
    from scripts.housing_rules.classifiers import sb9_countable_units, is_lot_split_only
    assert is_lot_split_only("SB 9 lot split — two-lot subdivision")
    assert is_lot_split_only("Tentative Parcel Map for urban lot split")
    assert not is_lot_split_only("Construction of a 12-unit apartment building")
    # lot-split-only permit -> 0 units even if a number is declared
    assert sb9_countable_units("SB9 lot split", declared_units=2, has_building_or_unit_event=False) == 0
    # lot split WITH an accompanying building/unit event -> count the units
    assert sb9_countable_units("SB9 lot split + new duplex", declared_units=2, has_building_or_unit_event=True) == 2
    # a normal building permit -> count as-is
    assert sb9_countable_units("New 4-unit building", declared_units=4, has_building_or_unit_event=False) == 4
    print("sb9_countable_units: lot-split=0 / split+building=units / normal=units — PASS")


if __name__ == "__main__":
    raise SystemExit(main())
