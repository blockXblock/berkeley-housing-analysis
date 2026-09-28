"""test_address_points.py -- python -m scripts.housing_rules.test_address_points"""
from scripts.housing_rules.address_points import (address_for, by_apn, distance_m,
                                                  is_placeholder_address, point_for, resolve)


def main() -> int:
    fails = []
    m = by_apn()
    if len(m) < 20000:
        fails.append(f"only {len(m)} APNs loaded -- expected ~25k")

    # the case that started this: Planning says "0 LE ROY Ave", the City layer says 1463
    if address_for("058-2244-025-01") != "1463 Le Roy Ave":
        fails.append(f"058-2244-025-01 -> {address_for('058-2244-025-01')!r}, wanted '1463 Le Roy Ave'")
    if address_for("060-2482-010-00") != "1298 Queens Rd":
        fails.append(f"060-2482-010-00 -> {address_for('060-2482-010-00')!r}, wanted '1298 Queens Rd'")

    # coordinates must be WGS84, not Web Mercator -- Berkeley is ~37.8N, -122.3E
    lat, lon = point_for("058-2244-025-01")
    if not (37 < (lat or 0) < 38 and -123 < (lon or 0) < -122):
        fails.append(f"coords {lat},{lon} are not WGS84 -- the X_CORD/Y_CORD trap")

    # distance sanity: the point should be within a lot's width of what v2 stores for proj73
    d = distance_m(37.882472, -122.260187, lat, lon)
    if d is None or d > 120:
        fails.append(f"distance to proj73's stored point is {d} -- expected under 120 m")

    for a, want in (("0 LATHAM", True), ("0 Grizzly Peak Blvd", True),
                    ("1463 Le Roy Ave", False), ("2136 SAN PABLO Ave", False),
                    ("", False), (None, False), ("0", False)):
        if is_placeholder_address(a) != want:
            fails.append(f"is_placeholder_address({a!r}) != {want}")

    # no coordinates supplied -> the answer is right but must be flagged UNVERIFIED
    if resolve("0 LE ROY Ave", ["058-2244-025-01"]) != ("1463 Le Roy Ave",
                                                       "city_address_points_unverified"):
        fails.append(f"resolve placeholder -> {resolve('0 LE ROY Ave', ['058-2244-025-01'])}")
    # with coordinates it is verified (proj73's stored point is 22 m from 1463 Le Roy)
    if resolve("0 LE ROY Ave", ["058-2244-025-01"], 37.882472, -122.260187) != (
            "1463 Le Roy Ave", "city_address_points"):
        fails.append("verified placeholder resolution failed")
    if resolve("2136 SAN PABLO Ave", []) != ("2136 SAN PABLO Ave", "as_given"):
        fails.append("resolve should leave a real address alone")
    # geometry must REJECT a far candidate: proj151 "Ashby BART" vs 2954 San Pablo, 1,562 m
    got = resolve("Ashby BART", ["053-1652-001-05"], 37.8531, -122.2704)
    if got != ("Ashby BART", "rejected_too_far"):
        fails.append(f"far candidate not rejected: {got}")
    # ... and ACCEPT a near one: 1353 Berkeley -> 1353 Berkeley Way at 1 m
    got = resolve("1353 Berkeley", ["057-2074-012-00"], 37.87091703, -122.28578696)
    if got != ("1353 Berkeley Way", "city_address_points"):
        fails.append(f"near candidate not accepted: {got}")
    # with no coordinates the caller must be told it is UNVERIFIED, never silently trusted
    if resolve("Ashby BART", ["053-1652-001-05"])[1] != "city_address_points_unverified":
        fails.append("a coordinate-less resolution must be marked unverified")
    if resolve("0 PARKER St", ["055-1829-011-00"])[1] != "unresolved":
        fails.append("an unresolvable placeholder must say so")
    from scripts.housing_rules.address_points import is_unusable_address
    for a, want in (("0 LATHAM", True), ("SAN PABLO Ave", True), ("VIRGINIA St", True),
                    ("Ashby BART", True), ("1353 Berkeley", True), (None, True), ("", True),
                    ("1463 Le Roy Ave", False), ("2136 SAN PABLO Ave", False)):
        if is_unusable_address(a) != want:
            fails.append(f"is_unusable_address({a!r}) != {want}")

    for f in fails:
        print("  FAIL", f)
    print(f"address_points: {len(m)} APNs loaded; "
          f"{'all checks pass' if not fails else f'{len(fails)} FAILURES'}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
