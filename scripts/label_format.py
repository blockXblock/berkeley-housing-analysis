#!/usr/bin/env python3
"""label_format.py — THE one definition of how a building label reads on screen.

John, 2026-08-30: "can we change the labels in our tours to be more compact -- fold to two
lines, smaller font size ... their appearance is confusing, sometimes hard to see which label
is for which building."

A one-line label of 39 characters average (74 at worst) is a wide banner floating over a
skyline. Several of them overlap and you cannot tell which belongs to which tower. Folding the
address onto its own line roughly halves the width, which is what actually separates them.

    2200 Bancroft Way
    1,625 beds · Under Construction

THIS LIVES IN ONE PLACE ON PURPOSE. sync_status_from_v2.py rewrites these labels from the
database and would flatten the fold back to one line if it did its own splitting and joining;
gen_building_loop groups sites by the address at the head of the name. Both now parse and
compose through here, so the format cannot drift the way buildings() and the geometry sha did.
"""
import re

FOLD = "\n"


def parts(name):
    """Split a label into its components, whether it is folded or not.

    Accepts both the historical one-line 'A · B · C' and the folded 'A\\nB · C'.
    """
    return [p.strip() for p in re.split(r"\n|·", name) if p.strip()]


def compose(bits):
    """Address on line one, everything else on line two — the on-screen form.

    A single-component label (a street sign, a site with no figures) stays on one line: there
    is nothing to fold and an orphan line break would just push it off its building.
    """
    bits = [str(b).strip() for b in bits if str(b).strip()]
    if len(bits) < 2:
        return bits[0] if bits else ""
    return bits[0] + FOLD + " · ".join(bits[1:])


def is_folded(name):
    return FOLD in name


def flat(name):
    """The one-line canonical form — for matching, diffing and logging."""
    return " · ".join(parts(name))
