"""Housing-policy business rules: HCD/ABAG cycle, projection, tier, and streamlining lookups + classifiers.

Single source of truth for date-based and year-based classification of permits,
applications, and housing units against state housing-element / RHNA rules.

Designed to migrate cleanly to SQL: each list-of-dicts lookup maps to a table,
each classifier function maps to a CASE expression or a small SQL function.

Public surface (re-exported from submodules):
    Data:
        RHNA_CYCLES, PROJECTION_PERIODS, INCOME_TIERS, STREAMLINING_PROVISIONS
    Functions:
        cycle_for_date, is_projection_period, rhna_credit_cycle,
        valid_income_tiers_for_year, valid_streamlining_provisions_for_year
        classify, net_units  (v4 permit housing-role classifier; see permit_role.py)
"""
from .lookups import (
    RHNA_CYCLES,
    PROJECTION_PERIODS,
    INCOME_TIERS,
    STREAMLINING_PROVISIONS,
)
from .classifiers import (
    cycle_for_date,
    is_projection_period,
    rhna_credit_cycle,
    valid_income_tiers_for_year,
    valid_streamlining_provisions_for_year,
)

from .permit_role import classify, net_units  # v4 permit housing-role classifier (lifted from build_jn_c)

__all__ = [
    "RHNA_CYCLES",
    "PROJECTION_PERIODS",
    "INCOME_TIERS",
    "STREAMLINING_PROVISIONS",
    "cycle_for_date",
    "is_projection_period",
    "rhna_credit_cycle",
    "valid_income_tiers_for_year",
    "valid_streamlining_provisions_for_year",
    "classify",
    "net_units",
]

from .apn import to_canonical_apn, is_canonical_apn  # canonical APN form
