"""approval_letter -- recognize a MINISTERIAL APPROVAL LETTER from the City's own attachment file name.

John, 2026-10-03 ("fold in, then harvest"): SB 35 and AB 2011 approvals are filed in Accela as pre-application-type
records with no decision workflow; the approval is a signed Letter of Compliance ATTACHED to the record. The City names
these files by a fixed convention, "<YYYY-MM-DD>_<kind>_<address>.pdf", where the leading date is the letter's own date:
    2023-01-20_SB35_Compliance_1708 Harmon REDUCED.pdf
    2026-06-02_SB35_Compliance Ltr_2330 Durant.pdf
    2019-12-20_Approval Packet_2001 Ashby.pdf
This reads that convention. It is a reading of the City's file-naming scheme, not an inference about content: a name
that does not follow it returns None, and so do the letters that are NOT an approval of the project:
    2025-11-26_SB 35 Non-Compliant Letter_2330 Durant.pdf       (a refusal)
    2026-02-02_SB35 Labor Compliance Acknowledgement_...        (labor standards, not the approval)
    2025-10-17_AB2011_Modification Compliance Ltr_...           (approves a MODIFICATION -> kind 'modification')
    2025-08-20_AB2011 App_Complete Ltr_...                      (completeness, not approval)
Verified against the eight SB 35 letters read in full (scratch/2026-10-03_ministerial): each gives the date the letter
itself states. Tests: housing_rules/test_smoke.py.
"""
from __future__ import annotations

import re

_LEAD = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})[_ ]+(.*)$")
# not \b: the City's names join words with "_", which \b counts as a word character ("_SB35_" would never match)
_LAW = re.compile(r"(?<![A-Za-z0-9])(SB\s?35|AB\s?2011|SB\s?423)(?![0-9])", re.I)
_NOT = re.compile(r"non[- ]?complian|labor|acknowledg|incomplete|complete ltr|application|comment|response|invoice|"
                  r"table|obj(ective)? std|(?<![A-Za-z])app(?![A-Za-z])|eligibility criteria", re.I)
# "SB35 Obj Std Compliance Table" is the checklist and "APP_1C_SB35 Eligibility Criteria Compliance" a section of the
# APPLICATION form -- the developer's submittal, not the City's letter


def approval_from_filename(name: str):
    """-> (date, law, kind) for an approval letter, else None. kind = 'approval' | 'modification'. law = 'SB 35' |
    'AB 2011' | 'SB 423' | None (an 'Approval Packet' that names no law)."""
    m = _LEAD.match(name or "")
    if not m:
        return None
    date, rest = m.group(1), m.group(2)
    if _NOT.search(rest):
        return None
    law = _LAW.search(rest)
    lawname = re.sub(r"\s", "", law.group(1)).upper().replace("SB", "SB ").replace("AB", "AB ") if law else None
    if law and re.search(r"complian", rest, re.I):
        return (date, lawname, "modification" if re.search(r"modif", rest, re.I) else "approval")
    if re.match(r"approval packet", rest, re.I):
        return (date, lawname, "approval")
    return None
