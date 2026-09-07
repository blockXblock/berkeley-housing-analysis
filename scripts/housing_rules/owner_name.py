"""THE owner-name classifier — is a name on the record an individual, an investor entity,
a family trust, or an institution?

Lifted 2026-09-07 from scripts/gen_ownership_map.py:owner_type(), which had been the only
home for it. Same discipline as to_canonical_apn and normalize_address: IMPORT it, never
re-type it. A second, ad-hoc copy written the same day for the players page got two things
wrong that this one already had right, which is the whole argument for one home:

  - bare 'TR' is a TRACT abbreviation, not a trust — only 'FAMILY/LIVING/REV/JOINT TR' is;
  - a name is not an entity because it is long. "EDINOFF SUSAN & WORTH DONA" is two natural
    persons co-owning, and that is the single most common owner shape on the roll.

TRUST is deliberately separated from INVESTOR: most trusts on Berkeley's roll are family
estate planning, i.e. a wrapper around natural persons — so anything that filters for
"organisations, not individuals" must exclude trusts as well as individuals. That is what
is_organisation() encodes; do not re-derive it from the integer codes at each call site.
"""
import re

INVESTOR = re.compile(r"\b(LLC|L\.L\.C|INC|CORP|COMPANY|LTD|LP|L\.P|LLP|PARTNERS|PARTNERSHIP|PROPERTIES|"
                      r"HOLDINGS|VENTURES|CAPITAL|REALTY|MANAGEMENT|INVESTMENTS?|ENTERPRISES|GROUP|ASSOCIATES|& CO)\b")
# trust — incl. assessor abbreviations TRS/TTEE, and 'X TR' only in trust context (NOT bare 'TR' = tract)
TRUST = re.compile(r"\b(TRUST|TRUSTEE|TTEE|TRS|REVOCABLE|(?:FAMILY|LIVING|REV|FAM|LV|JOINT|SURVIVORS?)\s+TR)\b")
# SCH and MINISTRY added 2026-09-07: "STARR KING SCH MINISTRY" (Starr King School for the
# Ministry) classified as an individual under SCHOOL/MINISTRIES alone. This widens the
# institutional class slightly, which also affects the published ownership map's colouring.
INSTIT = re.compile(r"\b(UNIVERSITY|REGENTS|CITY OF|COUNTY|STATE OF|CHURCH|SCHOOL|SCH|MINISTRY|DISTRICT|CALIFORNIA|"
                    r"HOUSING AUTH|FOUNDATION|ASSOCIATION|ASSN|CONGREGATION|TEMPLE|SOCIETY|INSTITUTE|"
                    r"COOPERATIVE|CO-OP|MINISTRIES|DIOCESE|PARISH|NONPROFIT|COMMONS)\b")

INDIVIDUAL, INVESTOR_T, TRUST_T, INSTITUTIONAL = 0, 1, 2, 3
LABELS = {INDIVIDUAL: "individual", INVESTOR_T: "investor (LLC/Corp/LP)",
          TRUST_T: "trust", INSTITUTIONAL: "institutional"}


def owner_type(name):
    """0 individual · 1 investor · 2 trust · 3 institutional. Order matters: an
    institutional name may also contain an investor word."""
    n = str(name).upper()
    if INSTIT.search(n):
        return INSTITUTIONAL
    if TRUST.search(n):
        return TRUST_T
    if INVESTOR.search(n):
        return INVESTOR_T
    return INDIVIDUAL


def is_organisation(name):
    """True only for names that are a COMPANY or an INSTITUTION — the test to use before
    putting an owner name on a public page as a network node. Individuals and family
    trusts are natural persons and return False."""
    return owner_type(name) in (INVESTOR_T, INSTITUTIONAL)
