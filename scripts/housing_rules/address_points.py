r"""address_points.py -- the CITY address-point layer, as a THIRD join lane.

WHY IT EXISTS. CLAUDE.md rule 4c gives two lanes for reaching a parcel: the canonical APN and the
normalized address. Both fail on the same class of record -- a project whose address is a
placeholder. "0 <street>" is how ONE city department records an unnumbered or vacant parcel, and the
SAME structure often carries a real street address from a DIFFERENT department (John, 2026-09-26).
This layer is that other department's answer, keyed by parcel:

    proj73  Planning: "0 LE ROY Ave"   assessor situs: BLANK   address points: 1463 Le Roy Ave

Three sources, three answers for one parcel. "Unnumbered" was never a fact about the parcel, only
about who was asked -- so an address-point lookup is a legitimate third lane, not a fallback hack.

SOURCE: data/reference/berkeley_addresses_with_fields.csv -- the City address-point layer
(~25.5k rows), keyed here by housing_rules.to_canonical_apn. PRIMARY city data, not CKAN (rule 1).

⚠ THE FILE CARRIES TWO COORDINATE SYSTEMS. `X_CORD`/`Y_CORD` are WEB MERCATOR (-13609197, 4563294);
the WGS84 pair is in the separate `longitude`/`latitude` columns. Reading the projected pair as
lat/long yields distances of ~1.5e12 m and silently rejects correct matches -- it cost a true
resolution (1298 Queens Rd) before being caught. Always use `latitude`/`longitude`.

USE IT TO VERIFY, NOT ONLY TO LOOK UP: `distance_m()` compares a candidate against coordinates you
already hold, which makes an address claim falsifiable on geometry instead of on a string.
"""

from __future__ import annotations

import csv
import math
import re
from functools import lru_cache
from pathlib import Path

from .apn import to_canonical_apn

CSV = Path(__file__).resolve().parent.parent.parent / "data/reference/berkeley_addresses_with_fields.csv"


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=1)
def by_apn() -> dict[str, tuple[str, float | None, float | None]]:
    """canonical APN -> (address, latitude, longitude). Loaded once per process."""
    out: dict[str, tuple[str, float | None, float | None]] = {}
    if not CSV.exists():
        return out
    with open(CSV, newline="") as f:
        for row in csv.DictReader(f):
            apn = (row.get("APN") or "").strip()
            addr = " ".join((row.get("ADDRESS") or "").split())
            if not apn or not addr:
                continue
            try:
                k = to_canonical_apn(apn, "alameda")
            except Exception:
                continue
            # WGS84 columns, never X_CORD/Y_CORD (see the module docstring)
            out.setdefault(k, (addr, _f(row.get("latitude")), _f(row.get("longitude"))))
    return out


def address_for(apn_canonical: str | None) -> str | None:
    """the City's street address for a parcel, or None."""
    row = by_apn().get(apn_canonical or "")
    return row[0] if row else None


def point_for(apn_canonical: str | None):
    row = by_apn().get(apn_canonical or "")
    return (row[1], row[2]) if row else (None, None)


def distance_m(lat1, lon1, lat2, lon2) -> float | None:
    """metres between two WGS84 points; None if any coordinate is missing/unparseable."""
    lat1, lon1, lat2, lon2 = _f(lat1), _f(lon1), _f(lat2), _f(lon2)
    if None in (lat1, lon1, lat2, lon2):
        return None
    dlat = (lat2 - lat1) * 111_320
    dlon = (lon2 - lon1) * 111_320 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dlat, dlon)


_PLACEHOLDER = re.compile(r"^\s*0\s+\S")


def is_placeholder_address(addr: str | None) -> bool:
    """True for a "0 <street>" placeholder -- a real convention, but many-to-one, so it cannot
    IDENTIFY a parcel on its own (several APNs share "0 Latham Ln")."""
    return bool(_PLACEHOLDER.match(str(addr or "")))


def is_unusable_address(addr: str | None) -> bool:
    r"""True when an address cannot IDENTIFY a parcel, for any of the reasons seen in v2:

      * a "0 <street>" placeholder      -- "0 LATHAM", many-to-one across several APNs
      * no house number at all          -- "SAN PABLO Ave", "VIRGINIA St", "Ashby BART"
      * no street after normalisation   -- "1353 Berkeley", where the canon strips a trailing
                                           "Berkeley" as a CITY name and leaves nothing

    Triggering lane 3 only on the "0 " form was too narrow: it fired on 1 record and rescued none of
    the 7 unreachable projects, because most of them fail one of the other two ways.
    """
    if not addr:
        return True
    if is_placeholder_address(addr):
        return True
    from .address import normalize_address
    num, street = normalize_address(addr)
    return not (num and street)


MAX_SUBSTITUTION_METRES = 150


def resolve(addr: str | None, apns, lat=None, lon=None,
            max_m: float = MAX_SUBSTITUTION_METRES) -> tuple[str | None, str | None]:
    r"""-> (best address, source). Keeps a usable address; otherwise substitutes the City address
    point for a supplied canonical APN -- but ONLY if geometry agrees.

    ⚠ THE SUBSTITUTION MUST BE VERIFIED, NOT TRUSTED. Given coordinates for the thing being resolved,
    a candidate further than `max_m` is REJECTED. This is not belt-and-braces: proj151 ("Ashby BART",
    618 units) has a stored APN whose address point is '2954 San Pablo Ave', **1,562 m** from the
    coordinates v2 holds for the project -- a different site entirely. Substituting it would have
    silently re-addressed the largest project in the set. The same check confirmed the two good ones
    at 1 m and 3 m ('1353 Berkeley' -> '1353 Berkeley Way'; '1828 Berkeley' -> '1830 Berkeley Way',
    where the County's number differs from v2's by two on the same parcel).

    Sources returned: 'as_given' · 'city_address_points' (verified, or no coordinates to check
    against) · 'rejected_too_far' · 'unresolved'. A caller that cannot supply coordinates gets
    'city_address_points_unverified' so the difference stays visible instead of being assumed away.
    """
    if not is_unusable_address(addr):
        return addr, "as_given"
    for a in (apns or ()):
        got = address_for(a)
        if not got:
            continue
        if lat is None or lon is None:
            return got, "city_address_points_unverified"
        plat, plon = point_for(a)
        d = distance_m(lat, lon, plat, plon)
        if d is None:
            return got, "city_address_points_unverified"
        if d <= max_m:
            return got, "city_address_points"
        return (addr or None), "rejected_too_far"
    return (addr or None), ("unresolved" if addr else None)
