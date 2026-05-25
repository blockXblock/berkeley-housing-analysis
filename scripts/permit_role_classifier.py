"""
Permit role classifier for the Berkeley Housing Pipeline v2 database.

Classifies permits to determine whether their certificate-of-occupancy (CO)
events should count as evidence that a project is "completed". The goal is
to fix a documented misclassification bug where 50% of projects shown as
"completed" on berkeleybuild.com were actually flagged by CO events on
subsidiary permits (solar, electrical, furnace, demolition, etc.), not the
project's primary new-construction permit.

Berkeley uses a combined BEMP (Building/Electrical/Mechanical/Plumbing)
permit structure — there are no separate E/PL/ME permits. A single
parcel may have multiple distinct BEMP permits for distinct scopes of
work (new construction, retrofit on existing structure, solar
installation, etc.). The classifier reads each permit's description to
determine whether finalizing that permit means the new development is
done.

Three return values:
    "completes_project"          — permit description matches new-
                                   construction signals
    "does_not_complete_project"  — permit description matches subsidiary,
                                   existing-structure, or trade signals
    "ambiguous"                  — neither set matches cleanly

Used by:
    scripts/export_explorer_data_v2.py to derive each project's stage
    correctly.

Design notes (v2 refactor 2026-05-16):
    - Leading-word precedence: the first significant word(s) of a
      description determine scope. "Shoring for new construction" is
      shoring (subsidiary), not new construction.
    - Patterns are tested against lowercased description. All matching
      is case-insensitive via normalization, not re.IGNORECASE.
    - LOGGED_CONFLICTS captures descriptions where body-scan found both
      completes and does-not-complete patterns (diagnostic only).
    - needs_manual_verification() flags completes_project descriptions
      that should be human-reviewed before trusting.
"""

import re
from typing import Optional


# Module-level log of body-scan conflicts (both pattern classes matched).
# Cleared each time the module is reloaded. Used for diagnostics.
LOGGED_CONFLICTS = []


# ===========================================================================
# LEADING-WORD PATTERNS
# ===========================================================================
# Tested with re.match against the lowercased, stripped description.
# Allow leading whitespace via \s* prefix.

SUBSIDIARY_LEAD_PATTERNS = [
    r'\s*shoring\b',
    r'\s*excavation\b',
    r'\s*grading\b',
    r'\s*temporary\s+foundation\b',
    r'\s*demolish\b',
    r'\s*demo\s+(single|apartment|building|residence)',
    # Solar/PV patterns — these are trade permits, not new construction
    r'\s*roof\s+mounted\s+(photovoltaic|pv|solar)\b',
    r'\s*pv\b',
    r'\s*photovoltaic\b',
    r'\s*solar\s+panel',
    # HVAC/mechanical patterns
    r'\s*furnace\b',
    # Electrical service patterns
    r'\s*meter\s+main\s+upgrade\b',
    # Seismic retrofit patterns
    r'\s*(voluntary\s+)?seismic\s+retrofit\b',
    # Repair patterns
    r'\s*repair\b',
    # Deferred submittal patterns — these are plan supplements, not scope permits
    r'\s*deferred\s+submittal\b',
    # NOTE: 'remove and replace' is intentionally broad. The audit corpus
    # shows this leading phrase only on component replacement permits
    # (foundation, siding, etc.), never on teardown-and-rebuild — those
    # are split in Berkeley's permit system into separate Demolish and
    # New Construction permits. If a future permit uses 'Remove and
    # replace existing structure with new N-unit building', this pattern
    # will misclassify it; revisit then.
    r'\s*remove\s+and\s+replace\b',
    r'\s*replace\s+\d+\s+square\s+feet',
    r'\s*remove\s*&\s*replace\b',
    r'\s*install\s+(exterior\s+)?sign',
    r'\s*install\s+digital\s+led',
    r'\s*install\s+\(\d+\)\s+non\s+illuminated',
    r'\s*installation\s+of\s+sign',
    r'\s*insulation,?\s+drywall',
    r'\s*interior\s+remodel',
    r'\s*residential\s+remodel\b',
    r'\s*kitchen\s+(&|and)\s+bath\s+remodel',
    r'\s*remodel\s+kitchen\b',
    r'\s*reconfigure\s+walls',
    r'\s*bolting\s+and\s+bracing',
    r'\s*100a?\s+temp\s+meter',
    r't/o\s+existing\s+roof',          # 'T/O' is a leading abbreviation;
                                       # no leading-whitespace prefix here
                                       # by design.
    r'\s*add\s+second\s+layer',
    r'\s*phase\s+1\b',
    r'\s*phase\s+i\b(?!i)',            # 'Phase I' but not 'Phase II'
    r'\s*unit\s*#[a-z]',
    r'\s*this\s+revision\s+application',
]

COMPLETES_LEAD_PATTERNS = [
    r'\s*new\s+construction\b',
    r'\s*construction\s+of\b',
    r'\s*adu\s+new\s+construction',
    r'\s*building\s+[a-z]:\s*(new\s+)?(construction\s+)?(single\s+family|residential)',
]


# ===========================================================================
# BODY-SCAN PATTERNS
# ===========================================================================
# Tested with re.search anywhere in the lowercased description.
# These run only when no leading-word pattern matches.

COMPLETES_BODY_PATTERNS = [
    r'\b\d+[- ]?units?\b',
    r'\(\s*\d+\s*\)\s*units?\b',
    r'\b\d+\s+new\s+detached\s+adus?\b',
    r'\b\d+[- ]?stor(y|ies|ey)\s+(new|mixed[- ]use|multi[- ]?family|residential|apartment|condominium|building)\b',
    r'\bmultifamily\s+residential\s+building\b',
    r'\bcongregate\s+residence\b',
    r'\bmixed[- ]?use\s+(apartment|building|condominium)\b',
    r'\bcondominium\s+project\b',
    r'\bnew\s+single\s+family\s+(home|residence|house)\b',
    r'\bsingle\s+family\s+home\b',
    r'\bnew\s+adus?\b',
    r'\bcomplete\s+interior\s+build[- ]?out\b',
]

DOES_NOT_COMPLETE_BODY_PATTERNS = [
    r'\bsiding\b',
    r'\bskylight\b',
    r'\bmural\b',
    r'\bled\s+screen\b',
    r'\btransfer\s+tax\s+rebate\b',
    r'\btar\s+(&|and)\s+paint\b',
    r'\bclass\s+a\s+modified\s+bitumen\b',
    r'\b(remove|replace)\b[^.]*\bwindow\b',
    r'\bwindow\b[^.]*\b(remove|replace)\b',
    r'\bpatch\s+and\s+repair\s+stucco\b',
    r'\binsulation\b[^.]*\bdrywall\b',
    r'\bdrywall\b[^.]*\binsulation\b',
]

NEEDS_MANUAL_VERIFICATION_PATTERNS = [
    r'\bcomplete\s+interior\s+build[- ]?out\b',
]


# ===========================================================================
# CLASSIFIER FUNCTIONS
# ===========================================================================

def classify_permit_for_completion(description: Optional[str]) -> str:
    """
    Classify a permit description using leading-word precedence.

    Returns one of:
        "completes_project"          — permit represents new construction scope
        "does_not_complete_project"  — permit is subsidiary, existing-structure, or trade
        "ambiguous"                  — neither set of patterns matches

    Args:
        description: The permit description text. May be None or empty.

    Control flow:
        A) Empty/None → 'ambiguous'
        B) Leading subsidiary pattern → 'does_not_complete_project'
        C) Leading completes pattern → 'completes_project'
        D) Body scan: if both classes match → 'ambiguous' (logged)
                      if only completes → 'completes_project'
                      if only does_not_complete → 'does_not_complete_project'
                      if neither → 'ambiguous'
    """
    # Step A: Empty check
    if not description:
        return 'ambiguous'

    desc_stripped = description.strip()
    if not desc_stripped:
        return 'ambiguous'

    desc_lower = desc_stripped.lower()

    # Step B: Check leading subsidiary patterns (re.match = anchored at start)
    for pattern in SUBSIDIARY_LEAD_PATTERNS:
        if re.match(pattern, desc_lower):
            return 'does_not_complete_project'

    # Step C: Check leading completes patterns
    for pattern in COMPLETES_LEAD_PATTERNS:
        if re.match(pattern, desc_lower):
            return 'completes_project'

    # Step D: Body scan
    completes_hits = []
    for pattern in COMPLETES_BODY_PATTERNS:
        if re.search(pattern, desc_lower):
            completes_hits.append(pattern)

    does_not_complete_hits = []
    for pattern in DOES_NOT_COMPLETE_BODY_PATTERNS:
        if re.search(pattern, desc_lower):
            does_not_complete_hits.append(pattern)

    if completes_hits and does_not_complete_hits:
        # Both matched — log conflict, return ambiguous
        LOGGED_CONFLICTS.append({
            'description': description,
            'completes_patterns': completes_hits,
            'does_not_complete_patterns': does_not_complete_hits,
        })
        return 'ambiguous'

    if completes_hits:
        return 'completes_project'

    if does_not_complete_hits:
        return 'does_not_complete_project'

    return 'ambiguous'


def needs_manual_verification(description: Optional[str]) -> bool:
    """
    Returns True if a completes_project classification of this description
    should be flagged for manual human review.

    Some descriptions match completes_project patterns but describe
    intermediate work (e.g., "complete interior build-out" may be a
    phase completion, not full project completion).

    Args:
        description: The permit description text.
    """
    if not description:
        return False

    desc_lower = description.lower()

    for pattern in NEEDS_MANUAL_VERIFICATION_PATTERNS:
        if re.search(pattern, desc_lower):
            return True

    return False


def is_evidentiary_co_event(event: dict) -> bool:
    """
    Return True if a CO event has enough information to be used as
    completion evidence.

    Requires either:
      - permit_id populated (links to a permit row whose description we
        can classify), OR
      - non-empty summary text (we can attempt to classify the summary
        directly as a fallback), OR
      - non-empty source_url (provides traceability even if other fields
        are empty)

    Stub events from the v1->v2 migration with NULL permit_id, empty
    summary, and empty source_url are NOT evidentiary. They should not
    drive stage decisions because we have no way to verify what they
    refer to.

    Args:
        event: Dict-like object with keys: permit_id, summary, source_url
    """
    permit_id = event.get('permit_id')
    summary = (event.get('summary') or '').strip()
    source_url = (event.get('source_url') or '').strip()

    return bool(permit_id) or bool(summary) or bool(source_url)


def project_has_completion_evidence(project_id: int, db_connection) -> tuple[bool, list[dict]]:
    """
    Determine whether a project has at least one evidentiary CO event
    that classifies as completes_project.

    Args:
        project_id: The project ID to check.
        db_connection: A sqlite3.Connection to databases/berkeley_housing_v2.db (the canonical v2 path; do NOT use the bare basename v2.db — that creates a fail-open stub at the working directory).

    Returns:
        (has_evidence, classified_events)
          has_evidence: True if at least one evidentiary CO event
            classifies as completes_project.
          classified_events: List of dicts for each CO event, with keys:
            event_id, event_date, permit_id, permit_number, description,
            summary, is_evidentiary, classification, classification_source,
            needs_manual_verification

    The caller can use classified_events for diagnostics and for showing
    the project's completion evidence (or lack thereof) on the Explorer.
    """
    cur = db_connection.cursor()
    rows = cur.execute("""
        SELECT
            pe.id as event_id,
            pe.event_date,
            pe.permit_id,
            pe.summary,
            pe.source_url,
            pm.permit_number,
            pm.description as permit_description
        FROM project_events pe
        JOIN vocabulary_event_types vet ON vet.id = pe.event_type_id
        LEFT JOIN permits pm ON pm.id = pe.permit_id
        WHERE pe.project_id = ?
          AND vet.code = 'co_issued'
        ORDER BY pe.event_date
    """, (project_id,)).fetchall()

    classified = []
    has_evidence = False

    for row in rows:
        event_dict = {
            'event_id': row[0],
            'event_date': row[1],
            'permit_id': row[2],
            'summary': row[3],
            'source_url': row[4],
            'permit_number': row[5],
            'permit_description': row[6],
        }

        is_evidentiary = is_evidentiary_co_event(event_dict)

        # Classify: prefer permit description, fall back to event summary
        classification = 'ambiguous'
        classification_source = 'no_source'
        manual_verification_needed = False

        if is_evidentiary:
            source_text = None
            if event_dict['permit_description']:
                source_text = event_dict['permit_description']
                classification_source = 'permit_description'
            elif event_dict['summary']:
                source_text = event_dict['summary']
                classification_source = 'event_summary'

            if source_text:
                classification = classify_permit_for_completion(source_text)
                if classification == 'completes_project':
                    manual_verification_needed = needs_manual_verification(source_text)

        if is_evidentiary and classification == 'completes_project':
            has_evidence = True

        classified.append({
            **event_dict,
            'is_evidentiary': is_evidentiary,
            'classification': classification,
            'classification_source': classification_source,
            'needs_manual_verification': manual_verification_needed,
        })

    return has_evidence, classified


# ===========================================================================
# SELF-TESTS
# ===========================================================================

# Original 17 test cases (from baseline commit) — must still pass.
ORIGINAL_TEST_CASES = [
    # Known real completions (from 2026-05-14 audit) — should classify as completes_project
    ("Construction of new 6 story senior living facility type I-A",
     'completes_project', 'project 173'),
    ("Construction of new, 8-story, mixed-use building w/ 28 residential units",
     'completes_project', 'project 134'),
    ("Phase II for 8-story multi-family building with 40 residential Units",
     'completes_project', 'project 176'),
    ("Building new Single Family Residence",
     'completes_project', 'project 83 main'),
    ("Construction of 5-story, mixed-use building with 144 units",
     'completes_project', 'project 150 main'),

    # Known misattributions (from 2026-05-14 audit) — should classify as does_not_complete_project
    ("Voluntary seismic retrofit that includes new plywood sheathing, new wood blocking and lateral bracing",
     'does_not_complete_project', 'project 34'),
    ("Furnace changeout in attic",
     'does_not_complete_project', 'project 70'),
    ("ROOF MOUNTED PHOTOVOLTAIC",
     'does_not_complete_project', 'project 79'),
    ("Meter main upgrade 100-200A",
     'does_not_complete_project', 'project 90'),
    ("PV solar panels",
     'does_not_complete_project', 'project 90'),
    ("photovoltaic electric power system",
     'does_not_complete_project', 'project 134 solar'),
    ("Demolish Single Family Residence",
     'does_not_complete_project', 'project 83 demo'),
    ("Demolish two-story Duplex",
     'does_not_complete_project', 'project 150 demo'),
    ("Repair light in shower, install bathroom fan and small heater",
     'does_not_complete_project', 'project 27'),
    ("Deferred Submittal for B2021-02404",
     'does_not_complete_project', 'project 173 sub'),
    ("PV ground mounted solar panels",
     'does_not_complete_project', 'project 83 solar'),

    # Empty/None — should be ambiguous
    ("", 'ambiguous', 'empty string'),
    (None, 'ambiguous', 'None'),
]

# New test cases from 2026-05-16 audit corpus.
NEW_COMPLETES_TEST_CASES = [
    ("Construction of a 9665-SF, four story 39-unit congregate residence.",
     'completes_project', 'audit: 39-unit congregate'),
    ("Construction of a 9,815 SF, four story 11-unit + attached ADU multifamily residential building.",
     'completes_project', 'audit: 11-unit multifamily'),
    ("New construction of 5-story residential apartment with no parking. Shoring under B2023-04569",
     'completes_project', 'audit: new construction leading'),
    ("72-unit, 7-story, mixed-use apartment building.",
     'completes_project', 'audit: 72-unit'),
    ("Privately funded, 4-story, mixed use, (36) unit condominium project with garage.",
     'completes_project', 'audit: (36) unit'),
    ("ADU new construction - 6 new detached ADUs",
     'completes_project', 'audit: ADU new construction'),
    ("Building A: New Single Family home in the rear.",
     'completes_project', 'audit: Building A leading'),
    ("Building B: Construction single family home on the front of lot",
     'completes_project', 'audit: Building B leading'),
    ("Phase 2 - Superstructure - Concrete Floor slabs up to 3rd Floor and all wood framing above, exterior facade and complete interior build-out",
     'completes_project', 'audit: Phase 2 superstructure'),
]

NEW_DOES_NOT_COMPLETE_TEST_CASES = [
    ("Shoring Design package for retaining wall associated with Building Permit Application #B2023-02354.",
     'does_not_complete_project', 'audit: shoring design'),
    ("Shoring for excavation for new structure. (Rebuild is under Permit #B2021-04232.)",
     'does_not_complete_project', 'audit: shoring for excavation'),
    ("Shoring Wall @ East",
     'does_not_complete_project', 'audit: shoring wall'),
    ("Shoring, excavation, and grading. The temporary shoring system is intended to be constructed to allow excavation and grading for the proposed building construction.",
     'does_not_complete_project', 'audit: shoring excavation grading'),
    ("Temporary Foundation for a 2950 sq. ft. single family Residence.  See permit number B2024-02570 regarding the new construction.",
     'does_not_complete_project', 'audit: temporary foundation'),
    ("Demolish Apartment Building. (Ref. #B2023-02332 New Construction)",
     'does_not_complete_project', 'audit: demolish apartment'),
    ("Demo single family 1-story house over crawl space. Cap sewer & gas as required.",
     'does_not_complete_project', 'audit: demo single family'),
    ("Replace 760 square feet of deteriorated siding on the south elevation of the existing two story main residence.",
     'does_not_complete_project', 'audit: replace siding'),
    ("Remove & replace one (1) kitchen window, same size & location. Fire Zone 2 Property.",
     'does_not_complete_project', 'audit: remove replace window'),
    ("Remove and replace 60 linear feet of decomposed foundation for transfer tax rebate.",
     'does_not_complete_project', 'audit: remove replace foundation'),
    ("Install exterior sign",
     'does_not_complete_project', 'audit: install exterior sign'),
    ("Install (1) non illuminated walls sign.",
     'does_not_complete_project', 'audit: install non illuminated sign'),
    ("Install digital LED screen on exterior south facing façade and mural on exterior east facing façade.",
     'does_not_complete_project', 'audit: digital LED screen'),
    ("Insulation, drywall, replace shower pan/walls. Reset toilet.",
     'does_not_complete_project', 'audit: insulation drywall'),
    ("Interior remodel of the kitchen & two (2) baths on the main floor & one (1) bath on the lower level. Electrical uprades throughout. Fire Zone 2 Property.",
     'does_not_complete_project', 'audit: interior remodel'),
    ("Residential Remodel",
     'does_not_complete_project', 'audit: residential remodel'),
    ("Kitchen & Bath Remodel, addition of 2 skylights, new exterior - rear stairs",
     'does_not_complete_project', 'audit: kitchen bath remodel'),
    ("Remodel Kitchen.  Replace cabinets, appliances, counter tops and flooring in same location.  No structural changes, no ceiling work, update GFCI outlets and switches. Fire zone 2",
     'does_not_complete_project', 'audit: remodel kitchen'),
    ("Unit #A, First Floor. Add bathroom & laundry closet. Unit #B, Second Floor. Kitchen remodel, infill & add an interior door to convert the family room into a fourth bedroom. Plan reviewer increased valuation from $1,200 to $43,000.",
     'does_not_complete_project', 'audit: unit #A leading'),
    ("Bolting and bracing of the lowest level. Qualifies for Transfer Tax Rebate",
     'does_not_complete_project', 'audit: bolting bracing'),
    ("100A Temp Meter Release",
     'does_not_complete_project', 'audit: 100A temp meter'),
    ("Phase I: Underground piping, concrete structure to Level 3, MEP rough-ins below grade through Level 3.",
     'does_not_complete_project', 'audit: phase I leading'),
    ("This revision application is for an updated job address for an already approved permit. The plans have been revised with corrected address.",
     'does_not_complete_project', 'audit: this revision application'),
    ("Add second layer of tar & paint",
     'does_not_complete_project', 'audit: add second layer'),
    ("T/O EXISTING ROOFING MATL. INSTALL CLASS A MODIFIED BITUMEN ROOF SYSTEM, HEAT WELDING SEAMS",
     'does_not_complete_project', 'audit: T/O existing roof'),
    ("Reconfigure walls to relocate kitchen and create 2 baths.",
     'does_not_complete_project', 'audit: reconfigure walls'),
    ("Replace windows and doors. Patch and repair stucco to prep for painting.  Fire zone 2",
     'does_not_complete_project', 'audit: patch repair stucco'),
]


def run_tests():
    """Run self-tests. Returns (passed, failed) counts."""
    passed = 0
    failed = 0

    all_cases = (
        ORIGINAL_TEST_CASES +
        NEW_COMPLETES_TEST_CASES +
        NEW_DOES_NOT_COMPLETE_TEST_CASES
    )

    for description, expected, label in all_cases:
        actual = classify_permit_for_completion(description)
        if actual == expected:
            passed += 1
        else:
            failed += 1
            print(f"FAIL [{label}]: {description!r}")
            print(f"  expected: {expected}")
            print(f"  actual:   {actual}")

    return passed, failed


def run_smoke_tests():
    """Run 3-case smoke test for refactor sanity. Returns pass count."""
    print("=== SMOKE TEST (refactor sanity) ===")
    smoke_cases = [
        # (description, expected_classification, label)
        ("Shoring Wall @ East", "does_not_complete_project", "leading subsidiary"),
        ("New construction of 5-story residential apartment with no parking.",
         "completes_project", "leading completes"),
        ("Construction of a 9665-SF, four story 39-unit congregate residence.",
         "completes_project", "body-pattern completes via unit-count"),
    ]
    passed = 0
    for desc, expected, label in smoke_cases:
        actual = classify_permit_for_completion(desc)
        status = "PASS" if actual == expected else "FAIL"
        print(f"  [{status}] {label}: got {actual!r}, expected {expected!r}")
        if actual == expected:
            passed += 1
        else:
            print(f"        description: {desc!r}")
    print()
    return passed


def run_manual_verification_tests():
    """Test needs_manual_verification function."""
    print("=== MANUAL VERIFICATION FLAG TEST ===")
    # Phase 2 case should flag for manual verification
    desc = "Phase 2 - Superstructure - Concrete Floor slabs up to 3rd Floor and all wood framing above, exterior facade and complete interior build-out"
    flag = needs_manual_verification(desc)
    status = "PASS" if flag else "FAIL"
    print(f"  [{status}] Phase 2 with 'complete interior build-out': needs_manual_verification={flag} (expected True)")
    print()
    return 1 if flag else 0


if __name__ == '__main__':
    smoke_passed = run_smoke_tests()

    print("=== FULL SELF-TEST ===")
    passed, failed = run_tests()

    manual_passed = run_manual_verification_tests()

    total_passed = smoke_passed + passed + manual_passed
    total_tests = 3 + len(ORIGINAL_TEST_CASES) + len(NEW_COMPLETES_TEST_CASES) + len(NEW_DOES_NOT_COMPLETE_TEST_CASES) + 1

    print(f"Results: {total_passed} passed, {total_tests - total_passed} failed")
    print(f"  Smoke tests: {smoke_passed}/3")
    print(f"  Original tests: {passed - len(NEW_COMPLETES_TEST_CASES) - len(NEW_DOES_NOT_COMPLETE_TEST_CASES)}/{len(ORIGINAL_TEST_CASES)}")
    print(f"  New completes tests: counted in full")
    print(f"  New does_not_complete tests: counted in full")
    print(f"  Manual verification test: {manual_passed}/1")

    if total_passed < total_tests:
        exit(1)
