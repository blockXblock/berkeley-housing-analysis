"""permit_role — the v4 housing-role classifier, lifted to an importable home.

WHY THIS FILE EXISTS (the "drift pattern" fix, June-18 audit): the `classify` rule-engine + its
vocabulary + its 16 tests were trapped as CELL-STRING source inside `scripts/v4/build_jn_c.py`
(a notebook *generator* that can't even be imported — it builds-on-load and crashed on a hardcoded
output path). Every consumer had to exec-extract `classify` from the executed notebook — exactly the
duplicate-and-drift hazard the June-18 audit named (Q29: "machinery whose docstring claims active use
but nothing imports it") and the **June-7 housing_rules architecture decision** says to prevent:
define a rule ONCE, in scripts/housing_rules/, with citations, where consumers import it.

This module is that single home. The logic below is BEHAVIOR-IDENTICAL to the build_jn_c cell-string
`classify`/`net_units` — proven old-vs-new over the full v4 corpus before adoption (every
(role, is_master, note) identical). It is a deliberate verbatim LIFT: no logic changed, no cleanup,
priority-order preserved exactly. Any future improvement is a separate gated decision.

Consumers: scripts/v4/build_jn_c.py (imports + renders), scripts/v4/build_jn_d.py,
scripts/v4/harden_relabel.py, the relabel pass + curriculum NB (coming). Tests:
scripts/housing_rules/test_permit_role.py (16 anchored vocab cases + 9 deflation cases).

    classify(work_type, description, adu_flag, occtype, units_added, units_removed, permit_number)
        -> (role, is_master, note)
        role ∈ {new_unit, alteration, demolition, subsidiary, non_housing, ambiguous}
    net_units(units_added, units_removed, role, description="") -> int | None

Role from description+work-type (prose, first-match-wins priority rules with disqualifiers);
net_units from the structured unit fields only (prose-blind). ADU=Yes requires description
corroboration to be confident (the dirty-flag case -> ambiguous, not auto new_unit).
"""
import json

# ---- VOCABULARY (the domain knowledge; lifted verbatim from build_jn_c CELL 1) ----
HOUSING_TERMS = [
    "single family","single-family","new sfr","single-family dwelling"," sfr",
    "residential building","residential development","residential apartment",
    "housing development","student housing","group living","live/work","live-work",
    "duplex","triplex","fourplex","townhouse","townhome","row house",
    "dwelling unit","dwellings","accessory dwelling","apartment","multifamily","multi-family",
    "condominium"," condo",
]
CONVERSION_TERMS = [
    "convert to dwelling","convert to residential","add dwelling unit","convert garage",
    "convert detached","garage conversion","conversion of upper floor","convert basement",
    "convert attic","convert existing",
]
LEGALIZATION_TERMS = [
    "legalize","legalization","unpermitted","bring into compliance","ab 2533","legalize existing",
]
ADU_TERMS = ["adu","jadu","accessory dwelling unit","junior accessory"]
# ADU-creation signals (2026-08-02 fix, validated vs HCD APR oracle): an ADU that is CREATED —
# new detached OR conversion of an existing structure (garage/basement/attic) — ADDS a dwelling,
# even when Work Type reads alteration/addition and the ADU flag is unset/dirty. The old rules
# routed these to alteration/ambiguous with net 0 (the block-level undercount vs the APR).
ADU_CREATE_SIGNAL = ["convert","conversion","into a","into an","into adu","to adu","to an adu",
                     "new adu","construct","establish","build","garage into","basement into","attic into"]
ADU_NOT_CREATE = ["demolish","remove","existing adu","repair","remodel of existing"]
# movable-home permanence markers: ONLY these make a movable/park-model count as a dwelling
PERMANENCE_TERMS = ["permanent foundation","wheels removed","on foundation","affixed to foundation",
                    "tongue removed","placed on a foundation"]
MOVABLE_TERMS = ["tiny home","tiny house","park model","movable","trailer","manufactured home","rv "]
# multifamily markers: a confident new_unit whose count is BLANK and which looks multifamily must NOT
# default to 1 (that would under-count a real apartment) - it stays flagged as a count-gap to harvest.
MULTIFAM_TERMS = ["apartment","multifamily","multi-family","residential building","residential development",
                  "residential apartment","housing development","story residential","-story residential",
                  "units","condominium","mixed use","mixed-use","story building"]
NONHOUSING_TERMS = [
    "re-roof","reroof","siding","hvac","water heater","furnace","temp power","temporary power",
    "tower crane","shoring","abatement","electrical service","solar","photovoltaic"," pv ",
    "re-pipe","repipe","window replacement","kitchen remodel","bathroom remodel","deck","fence",
    "retaining wall",
]


# ---- payload field access + helpers (lifted verbatim from build_jn_c CELL 2) ----
def _norm(s): return " ".join(str(s).split()).strip().lower() if s is not None else ""
def _has(t, terms): return any(x in t for x in terms)
def _adu_creation(desc):
    # ADU named + a creation/conversion signal + not a removal/remodel-of-existing.
    return _has(desc, ADU_TERMS) and _has(desc, ADU_CREATE_SIGNAL) and not _has(desc, ADU_NOT_CREATE)
def _to_int(v):
    try:
        if v is None or str(v).strip().lower() in ("","nan","none"): return None
        return int(float(str(v).strip()))
    except Exception: return None

def payload_get(payload, key):
    try: return json.loads(payload).get(key)
    except Exception: return None

def classify(work_type, description, adu_flag, occtype, units_added, units_removed, permit_number):
    wt=_norm(work_type); desc=_norm(description); pn=_norm(permit_number)
    adu_yes = _norm(adu_flag) in ("yes","y","true","1")
    occ = _norm(occtype)
    is_new = wt.startswith("new")
    alt = any(k in wt for k in ("alteration","addition"))
    has_adu_lang = _has(desc, ADU_TERMS) or _has(desc, CONVERSION_TERMS) or _has(desc, LEGALIZATION_TERMS)

    # RULE 1 - child sub-permit
    if "-rev" in pn or "-def" in pn:
        return "subsidiary",0,"REV/DEF child - counted via master only"
    # RULE 2 - demolition
    if "demolition" in wt or "demolish" in wt:
        return "demolition",0,"Work Type demolition"
    # RULE 3 - sign
    if wt=="sign":
        return "non_housing",0,"Work Type sign"
    # RULE 4 - movable home: dwelling ONLY with permanence markers, else inconclusive
    if _has(desc, MOVABLE_TERMS):
        if _has(desc, PERMANENCE_TERMS):
            return "new_unit",1,"Movable/park-model with permanence markers - counts as dwelling"
        return "ambiguous",0,"Movable/tiny/trailer without permanence markers - inspect (may be non-counting RV)"
    # RULE 5 - ADU=Yes requires description corroboration to be confident
    if adu_yes:
        if has_adu_lang:
            return "new_unit",1,"ADU=Yes corroborated by ADU/conversion/legalization language"
        # ADU flag but no corroborating language -> inconclusive (the dirty-flag case)
        return "ambiguous",0,"ADU=Yes but no corroborating description language - inspect"
    # RULE 5.5 - ADU CREATED by description (2026-08-02 fix): a permit whose description names an ADU
    # being created (new detached, or conversion of garage/basement/attic) adds a dwelling even when
    # the ADU flag is unset/dirty and Work Type reads alteration/addition. Placed before the work-type
    # rules so a conversion-ADU isn't misrouted to alteration/ambiguous (net 0). Validated vs HCD APR.
    if _adu_creation(desc):
        return "new_unit",1,"ADU created (new or conversion) - adds a dwelling (2026-08-02 fix)"
    # RULE 6 - New + housing language => confident
    if is_new and _has(desc, HOUSING_TERMS):
        return "new_unit",1,"New + housing indicator"
    # RULE 7 - New + units>0 + no disqualifier => confident
    ua=_to_int(units_added)
    if is_new and ua and ua>0 and not _has(desc, NONHOUSING_TERMS):
        return "new_unit",1,f"New + units={ua}, no disqualifier"
    # RULE 8 - New but unconfirmed => inconclusive
    if is_new:
        return "ambiguous",0,"New but no housing indicator/units - inspect"
    # RULE 9 - alteration/addition WITH conversion or legalization language => inconclusive
    if alt and (_has(desc, CONVERSION_TERMS) or _has(desc, LEGALIZATION_TERMS)):
        return "ambiguous",0,"Alteration with conversion/legalization language - may add a dwelling, inspect"
    # RULE 10 - plain alteration/addition => non-housing (units floored 0)
    if alt:
        return "alteration",0,"Alteration/addition, no dwelling language (units floored 0)"
    # RULE 11 - blank/unmatched => inconclusive (generous)
    if wt in ("","nan","none"):
        return "ambiguous",0,"No Work Type - inspect"
    return "ambiguous",0,"Unmatched by vocabulary - inspect"

def net_units(units_added, units_removed, role, description=""):
    # Non-creating roles contribute 0.
    if role in ("alteration","demolition","non_housing","subsidiary"): return 0
    ua=_to_int(units_added)
    if ua is not None:
        return ua  # real structured count present - use it (prose-blind, as before)
    # DEFLATION FIX: a confident new_unit with a BLANK/null UnitsAdded. An SFR or ADU is 1 dwelling by
    # definition, so a blank count should be 1, not 0 (the 640-projects->405-units undercount). BUT a
    # MULTIFAMILY permit with a blank count is a real data gap - defaulting it to 1 would under-count a
    # whole apartment building - so it stays null-and-flagged (a harvest gap), not guessed as 1.
    desc=_norm(description)
    if role=="new_unit":
        if _has(desc, MULTIFAM_TERMS):
            return None   # multifamily with missing count -> flagged gap, do NOT guess 1
        return 1          # single dwelling (SFR/ADU/small) with blank count -> 1 by definition
    return ua             # any other creating role with blank count -> leave as-is


def classifier_hash():
    """THE classifier identity hash — the single source of the recipe (lifted 2026-07-02 from the
    duplicated copies in build_jn_c cell-4 and stage_methods.classify_all; ADR-002's staleness
    query `classifier_hash != current` only works if every writer stamps the SAME hash).
    Hashes the vocabulary the ORIGINAL recipe hashed (4 lists + 'rules-v1') — do NOT add lists
    here without bumping the version suffix, or identical logic re-stamps as 'stale'."""
    import hashlib
    return hashlib.sha256((json.dumps(
        [HOUSING_TERMS, CONVERSION_TERMS, LEGALIZATION_TERMS, NONHOUSING_TERMS,
         ADU_CREATE_SIGNAL, ADU_NOT_CREATE]) + "rules-v2"   # v2 = 2026-08-02 ADU-conversion fix
    ).encode()).hexdigest()[:16]
