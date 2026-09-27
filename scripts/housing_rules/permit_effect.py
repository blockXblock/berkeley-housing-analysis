"""permit_effect.py — what each permit does to housing, READ BY A MODEL, as a lookup.

Replaces the regex classifier (permit_role.classify / net_units) as the source of a permit's housing
role. The answers were produced once and stored as evidence (data/derived/permit_effect_evidence_*.json):
Jev (TypeSafe) read every permit; Claude Sonnet 5 read the 4,747 that needed reasoning (Jev said
creates / demolishes / subpermit, any units, or confidence < 0.8). Numbered -REV/-DEF children take
their parent from the permit number. Nothing here calls a model; re-reading is a deliberate, versioned
re-run (scripts/llm_permit_effect.py), never a side effect of a build.

Role vocabulary is v4's (event_classifications.housing_role) so the build can switch sources without
touching anything downstream.
"""
import functools
import hashlib
import json
import re
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parents[2] / "data/derived/permit_effect_evidence_2026-09-26.json"
ROLE = {"creates": "new_unit", "alters": "alteration", "demolishes": "demolition",
        "subpermit": "subsidiary", "not_housing": "non_housing", "unclear": "ambiguous"}
_CHILD = re.compile(r"-(REV|DEF)\d+$")


@functools.lru_cache(maxsize=1)
def _load(path=EVIDENCE):
    rows = json.loads(Path(path).read_text())
    return {r["permit"]: r for r in rows}


def evidence_hash(path=EVIDENCE):
    """The classifier identity stamped on every label (ADR-002 staleness): the evidence file's content."""
    return "permit_effect@" + hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def permit_effect(permit):
    """-> (role, is_master, net_units, note) for one permit, or None if the permit was never read.

    Sonnet's answer wins where it exists (it counts and cites); otherwise Jev's category, with units
    only when Jev's range is exact (0/1/2). A 'creates' answer with no usable count is 'ambiguous',
    never a guessed number."""
    r = _load().get(permit)
    if r is None:
        return None
    child = bool(_CHILD.search(permit))
    if r.get("sonnet_effect"):
        role = ROLE.get(r["sonnet_effect"], "ambiguous")
        nu = int(r.get("dwellings_created") or 0)   # GROSS, per HCD: removals are reported separately
        removed = int(r.get("dwellings_removed") or 0)
        note = (f"sonnet: {r.get('reason') or ''}"[:280] + (f" | removed {removed}" if removed else ""))
    else:
        role = ROLE.get(r["jev_effect"], "ambiguous")
        nu = {"0": 0, "1": 1, "2": 2}.get(r.get("jev_units_bucket"))
        note = f"jev {r['jev_effect']} conf={r.get('jev_confidence')}"
    if role == "new_unit" and not nu:
        role, nu = "ambiguous", None
    if role != "new_unit":
        nu = 0 if role in ("alteration", "demolition", "non_housing", "subsidiary") else nu
    is_master = int(role == "new_unit" and not child)
    return role, is_master, nu, note
