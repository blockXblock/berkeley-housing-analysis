"""Housing predicates — the SINGLE definition of "what is housing", imported by S1 (row grouping +
spine membership) and S2 (milestone-bearing permits) and every later stage. Defined ONCE here so the
concept can't be re-derived inline and drift — the "New only / UnitsAdded only" over-tighten recurred
THREE times (S1 spine, S2 events, S1 unit signal) precisely because it was duplicated.

TWO distinct predicates — keep them distinct, it matters (see build_v2_lessons.md, the interlude):

  is_housing(...)  — RECOGNITION (broad): is this CPRA row part of the housing universe? Residential
                     occupancy OR any units OR the ADU flag. Used to GROUP rows into buildings; includes
                     R-occupancy alterations and an ADU project's ancillary permits (they still BELONG
                     to a housing building).

  net_units(...)   — CREATION + COUNT (narrow): did this permit CREATE dwellings, and how many?
                     UnitsAdded; else NumberUnits if New; else min(NumberUnits,2) if ADU; else 0.
                     Used for S1 spine membership (a building enters iff any permit has net_units>0) AND
                     S2 milestone events (only creating permits date BP/CO). Same column read PER CONTEXT:
                     NumberUnits is new-units on a New permit, the (capped) ADU count on an ADU permit,
                     but EXISTING stock on a plain alteration -> 0 (else a 4,239-unit over-count).
"""
import re
from s0_keys import is_adu                              # the ONE ADU-flag reader (bool/np.bool/'Yes')


def _f(x):
    try:
        return float(str(x).replace(',', '') or 0)
    except Exception:
        return 0.0


def is_housing(occtype, units_added, number_units, adu_flag):
    """RECOGNITION (broad). True iff a residential occupancy class (R-1/2/3, incl R-2.1/R-3.1) OR any
    dwelling units OR the explicit ADU flag. Recovers mixed-use towers (A/B ground-floor OccType, e.g.
    3000 San Pablo 78u coded A-2) and U-coded ADUs; excludes 0-unit garages/restaurants."""
    if re.search(r'\bR-?[123]', str(occtype).upper()):
        return True
    if _f(units_added) > 0 or _f(number_units) > 0:
        return True
    return is_adu(adu_flag)


def net_units(is_new, units_added, number_units, adu_flag):
    """CREATION + COUNT (narrow). Net-new dwelling units this permit creates (MAX across a building's
    permits = REV/phase guard):
      - UnitsAdded if present (explicit net add);
      - else NumberUnits if Work Type=New (a new building: all its units are new);
      - else min(NumberUnits, 2) if ADU=Yes (the ADU/JADU — capped, since a permit on an 82-unit
        building flagged ADU reports NumberUnits=82, the EXISTING stock, not 82 new ADUs);
      - else 0 (a plain alteration's NumberUnits is the EXISTING unit count, NOT new housing).
    is_new is a boolean (py/np); adu_flag is read through the shared is_adu (bool/'Yes' tolerant)."""
    ua = _f(units_added); nu = _f(number_units)
    if ua > 0:
        return ua
    if bool(is_new):
        return nu
    if is_adu(adu_flag) and nu > 0:
        return min(nu, 2)
    return 0
