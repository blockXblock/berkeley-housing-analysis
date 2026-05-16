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

Design notes:
    - Patterns checked in priority order. completes_project patterns
      are restrictive enough that they only fire on real new construction
      descriptions, so subsidiary patterns can run AFTER without conflict.
    - This module deliberately does NOT modify v2.db. The classifier
      runs at export time. To iterate on patterns, edit this file and
      regenerate.
    - Coverage at time of writing: 55 of 70 CO events in v2 have
      permit_id populated and can be classified via permit description.
      The remaining 15 are migration stubs with no source data; they
      are filtered out by is_evidentiary_co_event() before classification.
"""

import re
from typing import Optional


# Patterns that indicate the permit represents the main new-construction
# scope of work. If a CO event is finaled on a permit matching one of
# these, the project really is built.
COMPLETES_PROJECT_PATTERNS = [
    # "Construction of new..." — strongest signal
    (r'\bconstruction\s+of\s+new\b', 'construction_of_new'),
    (r'\bconstruct(ion)?\s+(a\s+)?new\b', 'construct_new'),

    # "Building new..." — building used as verb
    (r'\bbuilding\s+(a\s+)?new\s+(single\s+family|multi[- ]family|residence|home|house|building|sfr|sfd|adu)\b',
     'building_new_residence'),
    (r'\bbuild\s+new\s+(single\s+family|multi[- ]family|residence|home|house|building|sfr|sfd|adu)\b',
     'build_new'),

    # "New N-story / N-unit" patterns — describes the building itself
    (r'\bnew\s+\d+[- ]?stor(y|ies|ey)\b', 'new_n_story'),
    (r'\b\d+[- ]?stor(y|ies|ey)\s+(new|mixed[- ]use|multi[- ]family|residential|building)\b',
     'n_story_building'),

    # Unit-count descriptions (strong signal for primary)
    (r'\b\d+\s+(residential\s+)?(dwelling\s+)?units?\b', 'unit_count'),
    (r'\b\d+[- ]?unit\s+(building|development|residential|multi[- ]family|mixed[- ]use)\b',
     'n_unit_building'),

    # Mixed-use / multifamily building
    (r'\bmixed[- ]use\s+building\b(?!.*\b(solar|photovoltaic|pv|electrical|plumbing|hvac)\s+(for|on|at)\b)',
     'mixed_use_building'),
    (r'\bmulti[- ]family\s+(building|development|residential)\b(?!.*\b(solar|photovoltaic|pv|electrical|plumbing|hvac)\s+(for|on|at)\b)',
     'multifamily_building'),

    # ADU primary scope
    (r'\b(new|build|construct|add|create)\s+adu\b', 'new_adu'),
    (r'\baccessory\s+dwelling\s+unit\b(?!.*\b(solar|photovoltaic|pv|electrical|plumbing|hvac)\s+(for|on|at)\b)',
     'adu_full'),
    (r'\bgarage\s+conversion\s+to\s+adu\b', 'garage_to_adu'),
    (r'\bconvert\s+(garage|basement)\s+to\s+(adu|dwelling)\b', 'convert_to_adu'),

    # Phased developments
    (r'\bphase\s+(i+|\d+)\b.*\b(\d+\s+(units?|stor)|multi[- ]family|residential\s+building)\b',
     'phased_development'),

    # Senior living / specialized residential
    (r'\b(senior\s+living|assisted\s+living|memory\s+care)\s+(facility|residence|building)\b',
     'senior_living'),
]


# Patterns that indicate the permit does NOT represent project completion.
# These are subsidiary trade work, work on pre-existing structures, or
# narrow-scope permits.
DOES_NOT_COMPLETE_PATTERNS = [
    # Solar / PV / battery
    (r'\b(solar|photovoltaic|pv\b|battery\s+storage|battery\s+backup)\b', 'solar_pv'),
    (r'\bphoto[- ]?voltaic\b', 'photovoltaic'),
    (r'\bsolar\s+(panel|collector|installation|electric|system)\b', 'solar_system'),
    (r'\bev\s+charger\b|\belectric\s+vehicle\s+charger\b', 'ev_charger'),

    # Electrical-only work
    (r'^\s*electrical\b', 'electrical_prefix'),
    (r'\belectrical\s+(panel|service|upgrade|outlet|circuit|sub[- ]?panel)\b', 'electrical_scope'),
    (r'\bservice\s+upgrade\b|\bpanel\s+upgrade\b|\bsub[- ]?panel\b', 'service_panel_upgrade'),
    (r'\bmeter\s+main\s+upgrade\b', 'meter_main'),
    (r'\btemp(orary)?\s+power\b', 'temp_power'),

    # HVAC / plumbing / mechanical trades
    (r'\bfurnace\s+(changeout|replace|install|upgrade)\b|\bfurnace\b', 'furnace'),
    (r'\bwater\s+heater\s+(changeout|replace|install|upgrade)\b|\bwater\s+heater\b', 'water_heater'),
    (r'\bheat\s+pump\b', 'heat_pump'),
    (r'\b(hvac|air\s+condition)\s+(install|replace|upgrade)\b', 'hvac_install'),
    (r'^\s*(mechanical|plumbing|hvac)\b', 'trade_prefix'),
    (r'\b(gas\s+line|sewer\s+lateral|water\s+line)\s+(replace|repair|install)\b', 'utility_line'),

    # Retrofit / seismic on existing
    (r'\bvoluntary\s+seismic\b', 'voluntary_seismic'),
    (r'\bseismic\s+retrofit\b', 'seismic_retrofit'),
    (r'\bretrofit\b(?!.*\bnew\s+construction\b)', 'retrofit'),

    # Existing structure work
    (r'\bexisting\s+(building|structure|hotel|residence)\b(?!.*\bdemolish\b)', 'existing_structure'),
    (r'\b(historic|landmark)\s+(restoration|preservation|renovation)\b', 'historic_work'),
    (r'\brenovation\s+of\s+existing\b', 'renovation_existing'),
    (r'\btenant\s+improvement\b|\bt\.?i\.?\s+(for|to|at)\b', 'tenant_improvement'),

    # Repairs / replacements / minor work
    (r'\brepair\s+(light|fan|heater|sink|outlet|window|roof|stair)\b', 'repair_fixture'),
    (r'\b(housing\s+case|housing\s+code|code\s+compliance|code\s+violation)\b', 'housing_code'),
    (r'^\s*repair\b(?!.*\bnew\s+construction\b)', 'repair_prefix'),
    (r'^\s*(re[- ]?roof|roof\s+replacement|roofing)\b', 'roofing'),
    (r'^\s*(siding|stucco\s+repair)\b', 'siding'),

    # Demolition only (no paired new construction in same description)
    (r'^\s*demolish\b(?!.*\bnew\s+construction\b)(?!.*\bbuild\s+new\b)', 'demolish_only'),
    (r'^\s*demolition\b(?!.*\bnew\s+construction\b)(?!.*\bbuild\s+new\b)', 'demolition_only'),

    # Sub-permits to other primary permits
    (r'\bdeferred\s+submittal\b', 'deferred_submittal'),
    (r'\brevision\s+(to|of|for)\b', 'revision'),
    (r'\b(rev|def)\d+\b', 'rev_def_suffix'),

    # Signage / fencing / minor site work
    (r'^\s*(sign|fence|retaining\s+wall|driveway|curb\s+cut)\b', 'site_minor'),

    # Fire / life safety standalone
    (r'^\s*fire\s+(sprinkler|alarm|suppression)\b', 'fire_system'),
]


def classify_permit_for_completion(description: Optional[str]) -> str:
    """
    Classify a permit description.

    Returns one of:
        "completes_project"          — permit represents new construction scope
        "does_not_complete_project"  — permit is subsidiary, existing-structure, or trade
        "ambiguous"                  — neither set of patterns matches

    Args:
        description: The permit description text. May be None or empty.

    Note: Classification is asymmetric and order-sensitive. A description
    like "Solar PV on new 5-story multifamily" must classify as
    does_not_complete_project (solar is what this permit DOES, even though
    the context mentions new construction). To achieve this, the completes
    patterns include negative lookahead to avoid matching when subsidiary
    terms appear with "for", "on", "at".
    """
    if not description:
        return 'ambiguous'

    desc_lower = description.lower()

    # Check completes_project patterns FIRST.
    # The patterns are restrictive (require "new construction", "building new
    # residence", "N-unit building", etc.) so they don't false-positive on
    # descriptions like "electrical for new construction of...".
    for pattern, _name in COMPLETES_PROJECT_PATTERNS:
        if re.search(pattern, desc_lower):
            # But verify it's not a "[trade] for [new construction]" pattern
            # which should be subsidiary, not primary.
            if _is_trade_for_pattern(desc_lower):
                continue
            return 'completes_project'

    # Then check does_not_complete patterns.
    for pattern, _name in DOES_NOT_COMPLETE_PATTERNS:
        if re.search(pattern, desc_lower):
            return 'does_not_complete_project'

    return 'ambiguous'


def _is_trade_for_pattern(desc_lower: str) -> bool:
    """
    Check whether description is a trade permit FOR a larger project,
    e.g., "Electrical for new construction of 5-story building".

    The trade prefix wins — this is subsidiary work, not primary completion.
    """
    trade_prefixes = [
        r'^\s*(solar|photovoltaic|pv|electrical|plumbing|mechanical|hvac|fire\s+sprinkler)',
    ]
    for pattern in trade_prefixes:
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
        db_connection: A sqlite3.Connection to v2.db.

    Returns:
        (has_evidence, classified_events)
          has_evidence: True if at least one evidentiary CO event
            classifies as completes_project.
          classified_events: List of dicts for each CO event, with keys:
            event_id, event_date, permit_id, permit_number, description,
            summary, is_evidentiary, classification, classification_source

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

        if is_evidentiary:
            if event_dict['permit_description']:
                classification = classify_permit_for_completion(
                    event_dict['permit_description']
                )
                classification_source = 'permit_description'
            elif event_dict['summary']:
                classification = classify_permit_for_completion(
                    event_dict['summary']
                )
                classification_source = 'event_summary'

        if is_evidentiary and classification == 'completes_project':
            has_evidence = True

        classified.append({
            **event_dict,
            'is_evidentiary': is_evidentiary,
            'classification': classification,
            'classification_source': classification_source,
        })

    return has_evidence, classified


# Self-test cases — run with `python3 permit_role_classifier.py` to verify.
TEST_CASES = [
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


def run_tests():
    """Run self-tests. Returns (passed, failed) counts."""
    passed = 0
    failed = 0
    for description, expected, label in TEST_CASES:
        actual = classify_permit_for_completion(description)
        if actual == expected:
            passed += 1
        else:
            failed += 1
            print(f"FAIL [{label}]: {description!r}")
            print(f"  expected: {expected}")
            print(f"  actual:   {actual}")
    return passed, failed


if __name__ == '__main__':
    passed, failed = run_tests()
    print(f"\nResults: {passed} passed, {failed} failed")
    if failed:
        exit(1)
