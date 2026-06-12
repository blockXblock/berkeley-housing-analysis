"""Housing-policy lookup tables: cycle dates, projection periods, income tiers, streamlining provisions.

CITATIONS
---------
Every date and year boundary in this file traces to a named source. When a
boundary derives from a convention (e.g., "later cycle owns shared boundary
date"), the convention is implemented in classifiers.py and the data here
stores values verbatim as they appear in the cited source.

[1] Berkeley CY 2024 Housing Element APR submission PDF
    Source path: data/raw/cpra-downloads/  (CPRA fulfillment)
    Attachment 1 (APR form), page 7, "Housing Element Planning Period":
        "6th Cycle | 01/31/2023 - 01/31/2031"
    Used for: RHNA_CYCLES["6th"].start, .end

[2] Berkeley City Manager's Memo to Council, dated March 28, 2025
    Source path: data/raw/cpra-downloads/  (same PDF as [1], earlier pages)
    Page 4, footnote 3 / Table 4 header, "Projection Period":
        "Projection Period (June 30-2022-1/30/23)"
    Used for: PROJECTION_PERIODS["6th"].start, .end

[3] HCD/ABAG 5th cycle reference: 5th cycle is 8 years long and predates the
    6th. End date derives from [1] (the 6th cycle's start). Start date
    (Jan 31, 2015) is 8 years earlier; this is the standard ABAG 5th-cycle
    framework. Not directly quoted from a Berkeley-internal source, so flagged
    here for downstream verification if 5th-cycle precision becomes critical.

[4] HCD CY 2025 APR FAQ: ACUTELY_LOW_INCOME added as a reportable income
    tier for the CY 2025 reporting period (first year it appears in HCD APR
    form schema). Schema confirmation: table_a2 in databases/hcd_apr_mirror.db
    has columns ACUTELY_LOW_INCOME_DR and ACUTELY_LOW_INCOME_NDR, populated
    in CY 2025 Berkeley submissions but blank in prior years.
    Used for: INCOME_TIERS[ACUTELY_LOW].valid_from = 2025

[5] California SB 35 (Wiener, 2017): chaptered Sep 29, 2017; operative
    Jan 1, 2018. Original streamlining provision. Extended to Jan 1, 2036
    by SB 423 (Wiener, 2023).
    Used for: STREAMLINING_PROVISIONS[SB35].effective_date, .valid_from
    Source: California Legislative Information (leginfo.legislature.ca.gov),
            SB 35 bill text, 2017-2018 Regular Session

[6] California SB 9 (Atkins, 2021): effective Jan 1, 2022. Single-family
    duplex/lot-split ministerial approval.
    Used for: STREAMLINING_PROVISIONS[SB9].effective_date, .valid_from
    Source: widely cited; California Legislative Information, SB 9, 2021-2022

[7] California AB 2011 (Wicks, 2022): signed September 2022, operative
    July 1, 2023. Sunsets Jan 1, 2033. Affordable Housing & High Road Jobs Act.
    Used for: STREAMLINING_PROVISIONS[AB2011].effective_date, .valid_from, .valid_to
    Source: California Legislative Information; ABAG "Understanding AB 2011 & SB 6"
            (2023-07 brief); multiple legal-alert sources cross-referenced

[8] California SB 6 (Caballero, 2022): operative July 1, 2023. Sunsets
    Jan 1, 2033. Middle Class Housing Act.
    Used for: STREAMLINING_PROVISIONS[SB6].effective_date, .valid_from, .valid_to
    Source: California Legislative Information; same ABAG brief as [7]

[9] California SB 423 (Wiener, 2023): signed October 11, 2023; effective
    January 1, 2024. Extends/expands SB 35. Sunsets Jan 1, 2036.
    Used for: STREAMLINING_PROVISIONS[SB423].effective_date, .valid_from
    Source: California Legislative Information; Holland & Knight "California's
            2024 Housing Laws" briefing (2023-10)

CONVENTIONS
-----------
- RHNA_CYCLES.{start, end} are stored verbatim from the cited source. When the
  6th cycle's start (01/31/2023) equals the 5th cycle's stated end (01/31/2023),
  the "later cycle owns the boundary" convention is applied at classification
  time in classifiers.cycle_for_date — NOT by adjusting the data.
- PROJECTION_PERIODS.{start, end} are inclusive bounds; classifiers.is_projection_period
  uses start <= d <= end.
- INCOME_TIERS.{valid_from, valid_to} are inclusive year bounds; tier names match
  HCD APR table_a2 column prefixes (e.g., "EXTREMELY_LOW" → EXTREMELY_LOW_INCOME_DR,
  EXTREMELY_LOW_INCOME_NDR).
- STREAMLINING_PROVISIONS.{valid_from, valid_to} are inclusive year bounds for
  APR-year applicability; .effective_date is the precise legal effective date
  for sub-year audits.
"""
from datetime import date

# ---------------------------------------------------------------------------
# RHNA cycles — date-bounded periods of housing-element compliance
# ---------------------------------------------------------------------------
# SQL migration target:
#   CREATE TABLE rhna_cycles (
#       name TEXT PRIMARY KEY,
#       start_date DATE NOT NULL,
#       end_date DATE NOT NULL,
#       duration_years INTEGER NOT NULL,
#       region TEXT NOT NULL,
#       source_citation TEXT
#   );
RHNA_CYCLES = [
    {
        "name": "5th",
        "start": date(2015, 1, 31),
        "end":   date(2023, 1, 31),
        "duration_years": 8,
        "region": "ABAG/Bay Area",
        "source_citation": "[3] 5th cycle derived from [1]'s 6th-cycle start; 8-year duration standard",
    },
    {
        "name": "6th",
        "start": date(2023, 1, 31),
        "end":   date(2031, 1, 31),
        "duration_years": 8,
        "region": "ABAG/Bay Area",
        "source_citation": "[1] Berkeley CY 2024 APR submission, Attachment 1 p.7",
    },
]

# ---------------------------------------------------------------------------
# Projection periods — gap between ABAG baseline and 6th-cycle clock start
# ---------------------------------------------------------------------------
# Units permitted in the projection period count toward the cited cycle's
# RHNA progress even though they predate the cycle's nominal start.
#
# SQL migration target:
#   CREATE TABLE projection_periods (
#       cycle TEXT NOT NULL REFERENCES rhna_cycles(name),
#       start_date DATE NOT NULL,
#       end_date DATE NOT NULL,
#       source_citation TEXT,
#       PRIMARY KEY (cycle)
#   );
PROJECTION_PERIODS = [
    {
        "cycle": "6th",
        "start": date(2022, 6, 30),
        "end":   date(2023, 1, 30),
        "source_citation": "[2] Berkeley CM memo (Mar 28, 2025), p.4 footnote 3 / Table 4 header",
    },
]

# ---------------------------------------------------------------------------
# Income tiers — HCD APR reportable categories by year of applicability
# ---------------------------------------------------------------------------
# valid_from / valid_to are inclusive APR report-year bounds. A tier valid in
# year Y means HCD's APR form for CY Y has that tier as a reportable column.
#
# Names match HCD table_a2 column prefixes (e.g., "EXTREMELY_LOW" → the
# EXTREMELY_LOW_INCOME_DR and EXTREMELY_LOW_INCOME_NDR columns in HCD's CSV).
#
# SQL migration target:
#   CREATE TABLE income_tiers (
#       name TEXT NOT NULL,
#       valid_from INTEGER NOT NULL,
#       valid_to INTEGER NOT NULL,
#       hcd_column_prefix TEXT,
#       source_citation TEXT,
#       PRIMARY KEY (name, valid_from)
#   );
INCOME_TIERS = [
    {"name": "EXTREMELY_LOW", "valid_from": 2018, "valid_to": 2031,
     "hcd_column_prefix": "EXTREMELY_LOW_INCOME",
     "source_citation": "HCD APR table_a2 schema, present in all observed years"},
    {"name": "VLOW",          "valid_from": 2018, "valid_to": 2031,
     "hcd_column_prefix": "VLOW_INCOME",
     "source_citation": "HCD APR table_a2 schema, present in all observed years"},
    {"name": "LOW",           "valid_from": 2018, "valid_to": 2031,
     "hcd_column_prefix": "LOW_INCOME",
     "source_citation": "HCD APR table_a2 schema, present in all observed years"},
    {"name": "MOD",           "valid_from": 2018, "valid_to": 2031,
     "hcd_column_prefix": "MOD_INCOME",
     "source_citation": "HCD APR table_a2 schema, present in all observed years"},
    {"name": "ABOVE_MOD",     "valid_from": 2018, "valid_to": 2031,
     "hcd_column_prefix": "ABOVE_MOD_INCOME",
     "source_citation": "HCD APR table_a2 schema, present in all observed years"},
    {"name": "ACUTELY_LOW",   "valid_from": 2025, "valid_to": 2031,
     "hcd_column_prefix": "ACUTELY_LOW_INCOME",
     "source_citation": "[4] HCD CY 2025 APR FAQ; table_a2 columns ACUTELY_LOW_INCOME_DR/NDR populated only in CY 2025+"},
]

# ---------------------------------------------------------------------------
# Streamlining provisions — California ministerial-approval laws by year
# ---------------------------------------------------------------------------
# A provision is "valid for year Y" if Y >= valid_from AND Y <= valid_to.
# valid_from is the first APR reporting year in which the law was operative
# for at least part of the year. effective_date is the precise legal date.
#
# SQL migration target:
#   CREATE TABLE streamlining_provisions (
#       name TEXT PRIMARY KEY,
#       valid_from INTEGER NOT NULL,
#       valid_to INTEGER NOT NULL,
#       effective_date DATE NOT NULL,
#       sunset_date DATE,
#       hcd_column TEXT,
#       source_citation TEXT
#   );
STREAMLINING_PROVISIONS = [
    {
        "name": "SB35",
        "valid_from": 2018,  "valid_to": 2035,
        "effective_date": date(2018, 1, 1),
        "sunset_date":    date(2036, 1, 1),  # extended by SB 423; was 2026-01-01
        "hcd_column": "APPROVE_SB35",
        "source_citation": "[5] California SB 35 (Wiener, 2017); operative 2018-01-01; sunset extended to 2036-01-01 by SB 423",
    },
    {
        "name": "SB9",
        "valid_from": 2022, "valid_to": 2031,
        "effective_date": date(2022, 1, 1),
        "sunset_date":    None,  # no known sunset
        "hcd_column": None,      # no dedicated APR column in observed schema
        "source_citation": "[6] California SB 9 (Atkins, 2021); effective 2022-01-01; widely cited",
    },
    {
        "name": "AB2011",
        "valid_from": 2023, "valid_to": 2032,
        "effective_date": date(2023, 7, 1),
        "sunset_date":    date(2033, 1, 1),
        "hcd_column": None,
        "source_citation": "[7] California AB 2011 (Wicks, 2022); operative 2023-07-01; sunset 2033-01-01",
    },
    {
        "name": "SB6",
        "valid_from": 2023, "valid_to": 2032,
        "effective_date": date(2023, 7, 1),
        "sunset_date":    date(2033, 1, 1),
        "hcd_column": None,
        "source_citation": "[8] California SB 6 (Caballero, 2022); operative 2023-07-01; sunset 2033-01-01",
    },
    {
        "name": "SB423",
        "valid_from": 2024, "valid_to": 2035,
        "effective_date": date(2024, 1, 1),
        "sunset_date":    date(2036, 1, 1),
        "hcd_column": None,  # extends/replaces SB 35 reporting in some contexts
        "source_citation": "[9] California SB 423 (Wiener, 2023); effective 2024-01-01; sunset 2036-01-01",
    },
]
