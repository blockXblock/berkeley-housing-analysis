"""planning_record.py -- what ROLE a Berkeley Accela Planning record plays in the pipeline.

Lives here, not in a caller, because more than one consumer needs it (the CapDetail harvest's
rung-3 selection, and any later entitlement-event ingest) and CLAUDE.md's standing rule is one
canonical implementation, never a per-script copy.

WHY A ROLE AND NOT A DATE RULE. A project has many Planning records and EACH has its own
Completeness Review, so "when was this project's application accepted" cannot be answered by
reducing over all of them -- an extremum promotes one record's action to speak for the project
(MAX picks the latest companion review, MIN picks whatever came first at the address, possibly a
prior project's). The date must be SELECTED from the record that actually is the project's
application, which requires knowing which record that is. See
docs/methodology/identity_is_the_product.md.

ROLES
  primary_application  the discretionary land-use application whose approval IS the entitlement.
  ministerial_clearance a by-right zoning sign-off attached to a building permit, not a discretionary
                       approval -- a different rung, and the one the by-right reforms are moving work
                       INTO (docs/methodology/seven_rungs_and_the_ministerial_shift.md).
  pre_application      SB330-style preliminary filing; precedes the application, does not replace it.
  companion_review     design review, landmarks, appeal -- real city actions on the same project,
                       each with its own completeness review, none of which is the application.
  not_an_application   a zoning research letter is an INQUIRY. 65 of them pass an address+housing-
                       language filter while representing no application at all; counting one as a
                       filing would invent a project.
  unknown              an unrecognised type. Returned rather than guessed, so a new city record type
                       surfaces as a gap instead of being silently bucketed.
"""

RECORD_ROLES = {
    "Zoning Permit": "primary_application",
    # "Structural Alteration Permit" is a COMPANION approval, not an entitlement, despite a name
    # that reads like a permit in its own right: every one of the 18 in the 2026-09-26 harvest
    # carries the LMSAP prefix -- Landmarks Structural Alteration Permit, a Landmarks Preservation
    # Commission approval for work on a designated landmark. Mapping it to primary_application
    # selected LMSAP2024-0003 as proj129's application and would have written the Landmarks
    # completeness review as the project's acceptance date.
    "Structural Alteration Permit": "companion_review",
    "Zoning Certificate Building Permit": "ministerial_clearance",
    "Zoning Certificate Accessory Dwelling Units": "ministerial_clearance",
    "Pre-Application": "pre_application",
    "Design Review Committee Preliminary": "companion_review",
    "Design Review Committee Final": "companion_review",
    "MOD Design Review committee Preliminary": "companion_review",
    "Design Review Staff Level": "companion_review",
    "Design Review Signs and Awnings": "companion_review",
    "Landmarks Initiation": "companion_review",
    "Landmarks Signs and Awnings": "companion_review",
    "Landmarks Mills Act Contracts": "companion_review",
    "Appeal": "companion_review",
    "Condo Conversion Parcel Map": "companion_review",
    "Condo Conversion Tract Map": "companion_review",
    "Condo Conversion Local Law Compliance": "companion_review",
    "Zoning Research Letter": "not_an_application",
    "Development-Related Fee Calculations": "not_an_application",
}


def role(record_type: str | None) -> str:
    """The record's pipeline role. Unrecognised types return 'unknown', never a guess."""
    return RECORD_ROLES.get((record_type or "").strip(), "unknown")


def is_primary(record_type: str | None) -> bool:
    return role(record_type) == "primary_application"
