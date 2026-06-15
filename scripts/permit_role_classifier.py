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
    # "Install … PV/solar …" — a solar permit ON a (possibly new) building is
    # still a trade permit; reject it BEFORE the body scan can match the new
    # building it references (e.g. "Install PV on roof of new ADU"). (2026-06-14)
    r'\s*install\b[\w\s.,()/&\d\'"-]{0,40}?\b(?:photovoltaic|pv|solar)\b',
    # HVAC/mechanical patterns
    r'\s*furnace\b',
    # Electrical service patterns
    r'\s*meter\s+main\s+upgrade\b',
    # Electrical service / panel / meter permits (2026-06-14 CAT-2 fix). The permit's
    # PRIMARY scope is the electrical upgrade; a mentioned ADU is the unit being SERVED
    # (it has its own permit), not built here. Leading-anchored, so a genuine ADU build
    # that merely also mentions electrical ("New detached ADU including electrical") is
    # NOT caught — it leads with the ADU verb, not the electrical work.
    r'\s*electrical\s+service\s+upgrade\b',
    r'\s*service\s+upgrade\b',
    r'\s*(?:new\s+)?electrical\s+(?:meter|service|sub-?panel|panel)\b',
    r'\s*new\s+\d+\s*amp(?:ere)?s?\b',
    r'\s*(?:main\s+)?(?:electrical\s+)?panel\s+upgrade\b',
    r'\s*upgrade\s+(?:the\s+)?(?:existing\s+)?(?:electrical\s+)?(?:service|panel|meter)\b',
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
    # --- FIX A (2026-06-14): ADU completion under-match ---
    # Creation / conversion / legalization of an accessory dwelling unit is a
    # housing completion. A creation verb must sit near the ADU token, so a
    # trade permit that merely mentions an ADU ("re-roof the ADU") is NOT caught
    # here — and leading-word SUBSIDIARY patterns still reject trade leads first.
    r'\b(?:new|construct\w*|build\w*|erect\w*|creat\w+|legaliz\w+|propos\w+)\b[\w\s.,;:#&"\'()/\-]{0,70}?\b(?:adus?|accessory\s+dwelling\s+units?|j\.?a\.?d\.?u\.?s?|junior\s+accessory\s+dwelling\s+units?)\b',
    r'\b(?:convert|conversion)\w*\b[\w\s.,;:#&"\'()/\-]{0,55}?\b(?:in)?to\b[\w\s.,;:#&"\'()/\-]{0,35}?\b(?:adus?|accessory\s+dwelling\s+units?|j\.?a\.?d\.?u\.?s?)\b',
    r'\b(?:adus?|accessory\s+dwelling\s+units?)\b[\w\s.,;:#&"\'()/\-]{0,40}?\b(?:built|constructed|created|will\s+be\s+built|to\s+be\s+(?:built|constructed))\b',
    r'\b(?:detached|attached|new|proposed|junior)\s+(?:\w+\s+){0,5}?(?:adus?|accessory\s+dwelling\s+units?)\b',
    r'\b(?:adus?|accessory\s+dwelling\s+units?)\b[\w\s.,;:#&"\'()/\-]{0,30}?\b(?:in\s+place\s+of|in\s+the\s+(?:rear|backyard)|garage\s+conversion)\b',
    r'\baddition\s+of\b[\w\s.,;:#&"\'()/\-]{0,30}?\badus?\b',
    # --- FIX B (2026-06-14): proj219-class named-unit-count under-match ---
    # "N <type> units" where the TYPE word names housing (apartment/dwelling/
    # residential/rental/condominium/townhome). Gates on the unit-TYPE word, not
    # a bare integer — a trade permit's UnitsAdded=1 never reads "N apartment
    # units". Catches "(57) apartment units", "81 dwelling units", "163 rental
    # units", parenthetical or plain.
    r'\(\s*\d+\s*\)\s*(?:[a-z]+\s+){0,2}?(?:apartment|dwelling|residential|rental|condominium|townhome)\s+units?\b',
    r'\b\d+\s+(?:[a-z]+\s+){0,2}?(?:apartment|dwelling|residential|rental|condominium|townhome)\s+units?\b',
    # --- FIX C (2026-06-14): new single-family / residence completions ---
    # Creation verb + a DWELLING token (single-family / residence / house / dwelling /
    # SFR). Size/story descriptors may sit between, but partial-work phrasing is excluded
    # by requiring the dwelling token itself: "new second level", "new addition", "new
    # roof", and "... service to existing residence" carry no dwelling token in position
    # and stay ambiguous. These are BODY patterns, so the solar/demo/trade SUBSIDIARY
    # leads still fire first ("demolish single family residence" / "install PV on new
    # house" reject before reaching here).
    r'\b(?:new|construct\w*|build\w*|erect\w*)\b[\w\s.,;:#&"\'()/\-]{0,40}?\bsingle[- ]?family\s+(?:home|house|residence|dwelling)\b',
    r'\bnew\b[\w\s,.\'#()/\-]{0,12}?\b\d[\d,]*\s*(?:sq\.?\s*ft\.?|sf|sqft|square\s+feet)\b[\s,.\'#()/\-]{0,4}\b(?:residence|dwelling|house|sfr)\b',
    r'\bnew\b[\w\s,.\'#()/\-]{0,10}?\b(?:\d+|one|two|three|four)[- ]?stor(?:y|ies|ey)\b[\w\s,.\'#()/\-]{0,20}?\b(?:residence|dwelling|house|sfr|single[- ]family)\b',
    # --- FIX D (2026-06-14): manufactured / modular DWELLING completions ---
    # "manufactured/modular" is overloaded — "manufactured spa", "manufactured roof
    # truss", "air handling/condensing unit" are equipment/components, NOT dwellings,
    # and must stay rejected/ambiguous. Gate strictly on DWELLING context: the
    # manufactured/modular/factory-built token must sit near a dwelling token
    # (home/dwelling/residence/housing/ADU/accessory dwelling), OR carry the HUD/HCD-
    # approved + "manufactured unit" signature of a permitted manufactured home. A bare
    # "manufactured ... unit" with no dwelling/HUD-HCD signal does NOT match.
    r'\b(?:manufactured|modular|factory[- ]?(?:built|assembled))\b[\w\s.,;:#&"\'()/\-]{0,30}?\b(?:home|dwelling|residence|housing|adus?|accessory\s+dwelling)\b',
    r'\b(?:home|dwelling|residence|housing|adus?|accessory\s+dwelling)\b[\w\s.,;:#&"\'()/\-]{0,30}?\b(?:manufactured|modular|factory[- ]?(?:built|assembled))\b',
    r'\b(?:hud|hcd)\b[\w\s.,;:#&/\-]{0,20}?\bapproved\b[\w\s.,;:#&/\-]{0,25}?\bmanufactured\s+unit\b',
    # --- FIX E (2026-06-14): STEP-3 rescue blind spots (sixth pass) ---
    # The STEP-3 ambiguous-rescue eyeball exposed 5 families of real residential
    # completions this classifier was missing (verb/noun forms, abbreviations, typos).
    # These are BODY patterns, so the subsidiary LEADS still fire first (a trade permit
    # that merely contains a dwelling noun is rejected by its leading word). Precision
    # validated: 0 demotions across the 598 prior completes + 68 prior does_not.
    # E1 — creation verb (incl. conversion-of noun, add/adding, covert-typo) within a
    #      bounded window of a dwelling/unit noun (incl. condo, duplex, townhouse,
    #      in-law unit (space or hyphen), Nth/second/additional/junior unit, JADU dots).
    # NB: verb is 'builds?\b' (not 'build\w*') so the NOUN "building" ("the building will
    # remain a duplex", "existing building contains") does NOT read as a creation verb;
    # the gerund is covered by the separate 'building\s+a\s+new' alternative.
    r'\b(?:new|newly|construct\w*|building\s+a\s+new|builds?\b|erect\w*|creat\w+|add\b|adding\b|addition\s+of|convert\w*|conversion\w*|covert\w*|legaliz\w+|propos\w+|reclassif\w+|change\s+use)\b[\w\s,.\'"#:;&()/\-]{0,70}?\b(?:homes?|houses?|residences?|dwellings?|de?welling\s+units?|condo(?:minium)?s?|duplex|tri-?plex|four-?plex|town\s*houses?|town\s*homes?|adus?|j\.?a\.?d\.?u\.?s?|sadu|accessory\s+dwellings?(?:\s+units?)?|accessory\s+units?|in[\s-]?law\s+units?|(?:second|secondary|additional|junior|jr\.?)\s+(?:dwelling\s+)?units?|\d+(?:st|nd|rd|th)\s+unit|dwelling\s+units?|residential\s+units?|residential\s+building|multi[\s-]?unit\s+residential|apartment\s+units?|living\s+units?|granny\s+(?:units?|flats?)|cottages?)\b',
    # E2 — dwelling/unit noun FOLLOWED by a made/created/conversion verb (reverse order:
    #      "single-family dwelling ... constructed", "SECONDARY UNIT CONVERSION").
    r'\b(?:homes?|houses?|residences?|dwellings?|adus?|j\.?a\.?d\.?u\.?s?|accessory\s+dwellings?(?:\s+units?)?|(?:second|secondary|additional|junior)\s+(?:dwelling\s+)?units?|dwelling\s+units?)\b[\w\s,.\'"#:;&()/\-]{0,20}?\b(?:constructed|built|created|conversion)\b',
    # E3 — abbreviated single-family residence ("NEW 2889SQFT SINGLE FAMILY RES."),
    #      including "single family detached house/residence".
    r'\b(?:new|construct\w*|building\s+a\s+new)\b[\w\s,.\'"#:;&()/\-]{0,30}?\bsingle[\s-]*famil\w*\s+(?:detached\s+)?(?:res\.?\b|residence|home|house|dwelling)',
    # E4 — ADU with numeric-paren count "(2) ADU" or new/sqft/(N) context, or rear/backyard/
    #      addition location, or "New residential accessory structure".
    r'\(\s*\d+\s*\)[\w\s,.\'"#:;&()/\-]{0,12}?\badus?\b',
    r'(?:\(\s*n\s*\)|\bnew\b|\d[\d,]*\s*(?:sq\.?\s*ft\.?|sf|sqft|square\s+feet))[\w\s,.\'"#:;&()/\-]{0,40}?\b(?:adus?|accessory\s+dwelling|sadu|j\.?a\.?d\.?u\.?s?)\b',
    r'\badus?\b[\w\s,.\'"#:;&()/\-]{0,18}?\b(?:in\s+(?:back\s*yard|backyard|the\s+rear|rear)|addition)\b',
    r'\bnew\s+residential\s+accessory\s+structure\b',
    # E5 — explicit new-unit creation ("CREATION OF NEW UNIT", "create 2 new ... units",
    #      "second/additional dwelling unit") and conversion INTO residential / in-law unit.
    r'\bcreation\s+of\s+new\s+unit\b|\bcreate\b[\w\s,.\'"#:;&()/\-]{0,30}?\d+\s+new[\w\s,.\'"#:;&()/\-]{0,20}?\bunits?\b|\b(?:second|additional|new)\s+dwelling\s+unit\b',
    r'\b(?:in)?to\s+(?:a\s+)?residential\b|\b(?:in)?to\s+in[\s-]?law\s+unit\b',
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
    # --- INPUT-2 (2026-06-14, sixth pass): a single, SPECIFIC standalone-solar signal.
    # A whole-permit "photovoltaic electric power system" is a trade permit (bucket-4
    # B2023-03611). Broader electrical-service/panel BODY patterns were tried and REJECTED:
    # they over-rejected genuine completions that merely mention an electrical upgrade
    # (e.g. "New 749 SqFt detached ADU with a 200A service" → wrongly ambiguous) — the
    # CAT-2 negative-guard failure. Electrical-service rejection stays LEADING-only (above);
    # the residual minor permits are left 'ambiguous' (harvest queue), which moves no count
    # since does_not and ambiguous are both uncounted. ---
    r'\bphotovoltaic\s+electric\s+power\s+system\b',
    # electrical/service permit SERVING a separately-built unit: the ADU is the powered
    # object ("200 amps for ADU", "service to accommodate newly built ADU"), not the built
    # one. Ordered electrical→for/accommodate→ADU, so an ADU-build that merely mentions an
    # electrical upgrade ("New ADU ... Upgrade electrical panel" / "Upgrade panel. New
    # construction of two ADUs") is NOT caught — the ADU token precedes the electrical there.
    r'(?:\bamps?\b|\belectrical\s+(?:service|panel)\b|\bmeter\b)[\w\s,.\'"#&()/\-]{0,30}?\b(?:for|to\s+accommodate|serving|to\s+serve)\b[\w\s,.\'"#&()/\-]{0,20}?\b(?:adus?|accessory\s+dwelling(?:\s+units?)?)\b',
    r'\bnewly\s+built\s+adus?\b',
    # existing-building minor-work, relabel-only, multiplex remodel, seismic upgrade — specific.
    r'\bbuilding\s+contains\b',
    r'\bno\s+work\s+to\s+be\s+done\b',
    r'\b(?:duplex|tri-?plex|four-?plex|building)\s+remodel\b',
    r'\bremove[\w\s,.\'"#&()/\-]{0,25}?\bfrom\s+scope\b',
    r'\bseismic\s+upgrade\b',
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

    # Normalize unicode curly quotes/apostrophes to ASCII so they don't break the
    # bounded character classes in the patterns (e.g. "20’ tall, ADU"). (2026-06-14)
    desc_lower = (desc_stripped.lower()
                  .replace('’', "'").replace('‘', "'")
                  .replace('“', '"').replace('”', '"'))

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
    ("986 sq ft HUD/HDC approved manufactured unit to be installed on permanent foundation.",
     'completes_project', 'B2022-05902: manufactured dwelling (Fix D positive). Negatives that '
     'must stay non-completes: "manufactured roof truss" (B2024-02435), "manufactured spa" '
     '(B2022-05428) — asserted in CY2024 validation, classify ambiguous not does_not.'),
    ("Construction of new 390sf detached accessory dwelling unit. Upgrade existing electrical service.",
     'completes_project', 'B2021-05343 CAT-2 negative: ADU build that ALSO mentions an electrical '
     'upgrade — leads with the ADU verb, so the electrical lead must NOT over-reject it.'),
    # --- FIX E (2026-06-14) positives: one per STEP-3 rescue blind-spot family ---
    ("Conversion of 845 SF commercial space into residential.",
     'completes_project', 'E1 blind-spot 1: "Conversion of" NOUN + into residential (B2018-03653)'),
    ("(N) 699sqft ADU",
     'completes_project', 'E4 blind-spot 2: bare/(N) ADU, no creation verb (B2016-04204)'),
    ("505SF ADU in backyard",
     'completes_project', 'E4 blind-spot 2: ADU + location, no verb (B2019-03683)'),
    ('**NEW 2,889SQFT SINGLE FAMILY RES. 480SQFT BASEMENT GARAGE. FIRE ZONE 2 PROPERTY.',
     'completes_project', 'E3 blind-spot 3: abbreviation "SINGLE FAMILY RES." (B2015-03376)'),
    ('New Condo w/attached garage "C" 2172 sq ft. Added EV Charging Station.',
     'completes_project', 'E1 blind-spot 3: "condo" in residence vocabulary (B2019-05504)'),
    ("Remodel (E) workshop to in law unit by adding a new kitchen, new bathroom and, new laundry.",
     'completes_project', 'E1 blind-spot 4: "in law unit" (space, not hyphen) (B2018-00483)'),
    ("Covert existing 232SF garage/unpermitted studio into a ADU",
     'completes_project', 'E1 blind-spot 5: "Covert" typo + garage->ADU (B2021-03341)'),
    ("Convert garage to an Accessory Dewelling Unit.",
     'completes_project', 'E1 blind-spot 5: "Dewelling" typo (B2024-03769)'),
    ("RAISE EXISTING HOUSE THREE (3) FEET. CREATION OF NEW UNIT- 1260 S.F., ADDITION",
     'completes_project', 'E5: "CREATION OF NEW UNIT" (B2014-02947)'),
    ("Replace existing garage with one bedroom, one bath second dwelling unit with garage.",
     'completes_project', 'E5: "second dwelling unit" despite leading "Replace" (B2018-04404)'),
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
    ("Electrical service upgrade from 100A-200A service. Two 100A main panel will be installed (One for the main house and the second for the attached ADU - B2025-02754)",
     'does_not_complete_project', 'B2025-02754/proj64 CAT-2 fix: electrical-upgrade leading, ADU is a reference. Same bug class: B2024-00684, B2024-00915.'),
    ("New 400 Amp Service for 2 meters (ADU permit B2022-05577)",
     'does_not_complete_project', 'B2024-00684: electrical service permit referencing a separate ADU permit'),
    # --- INPUT-2 (2026-06-14) standalone-solar rejection ---
    ("This is a 18,900 STC WATT Photovoltaic Electric Power System W/ (35) Photovoltaic modules.",
     'does_not_complete_project', 'INPUT-2: standalone photovoltaic system (bucket-4 B2023-03611)'),
    # --- INPUT-2 FALSE-POSITIVE BLOCKS: these trade/relabel permits contain a dwelling token
    # (so a completes pattern also fires) AND a guard — the body scan's both-match rule yields
    # 'ambiguous', which correctly BLOCKS false-completion (the count-critical goal). They land
    # in the harvest queue, not does_not; that does_not-vs-ambiguous nicety is count-neutral and
    # deliberately not forced via fragile leading patterns (would risk the CAT-2 negatives). ---
    # (asserted in CY2024 validation as ambiguous, not via this completes/does_not suite)
    # --- CAT-2-class NEGATIVE GUARDS: genuine completions that mention a rejected keyword
    # but MUST stay completes. If a future INPUT-2 tightening trips these, narrow it. ---
    ("New 749 SqFt detached Accessory Dwelling Unit with a new water heater & A/C split mini system. Upgrade electrical panel to 200A.",
     'completes_project', 'NEG GUARD (B2022-00713): ADU build that mentions "Upgrade electrical panel" '
     '— ADU token leads, electrical is secondary, must NOT be rejected.'),
    ("7/27/21 - Upgrade electrical service panel to 200-Amps. New construction of two detached Accessory Dwelling Units (ADU).",
     'completes_project', 'NEG GUARD (B2020-01498): electrical-lead prefix then "New construction of two ADUs" '
     '— the build must win; "for ADU"-style serving language is absent.'),
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
