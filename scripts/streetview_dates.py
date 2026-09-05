#!/usr/bin/env python3
"""streetview_dates.py — when was there last a camera on this street, and how far back does it go?

THE POINT IS THE DATE, NOT THE PICTURE. Our structure inventory has no time dimension: the assessor
records ONE YearBuilt per parcel (the main structure), and Overture records shapes with no year at
all. 2811 Benvenue has three structures built in 1903, 1903 and the 1990s and every source we hold
collapses that to a single 1903 dot.

Street-level imagery is the one widely-available record that is BOTH independent of any permit or
assessment AND repeated over time. If a structure is absent in a 2013 pass and present in a 2016
pass, its construction is bracketed to those three years -- by a camera that drove past, with no
stake in the question. That covers the post-2007 ADU and infill cohort, which is precisely the
cohort a single per-parcel YearBuilt cannot see.

WE EXTRACT DATES, NOT IMAGERY, AND THAT DISTINCTION IS DELIBERATE. Google's Street View imagery is
licensed for viewing, not redistribution, so it cannot appear in a published flyby. A capture DATE
is a fact about the world, not a copyrightable image. Mapillary is CC-BY-SA and can supply both, so
it is the default here; Google is available for corroboration where a key exists.

  export MAPILLARY_TOKEN=...      # free, mapillary.com/dashboard/developers
  python3 scripts/streetview_dates.py --geom kml/tours/panoramic-kennedy-legacy.kml
  python3 scripts/streetview_dates.py --geom ... --provider google   # needs GOOGLE_MAPS_API_KEY
"""
import argparse, json, math, os, sys, urllib.parse, urllib.request, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_building_loop import buildings

RADIUS_M = 45.0


def bbox(lon, lat, m):
    dlat = m / 111320.0
    dlon = m / (111320.0 * math.cos(math.radians(lat)))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def mapillary(lon, lat, token):
    """Every Mapillary image near a point, with its capture date. This is the time series."""
    x0, y0, x1, y1 = bbox(lon, lat, RADIUS_M)
    url = ("https://graph.mapillary.com/images?" + urllib.parse.urlencode({
        "access_token": token, "fields": "id,captured_at,compass_angle,geometry",
        "bbox": f"{x0},{y0},{x1},{y1}", "limit": 200}))
    with urllib.request.urlopen(url, timeout=25) as r:
        data = json.load(r)
    out = []
    for im in data.get("data", []):
        ms = im.get("captured_at")
        if not ms:
            continue
        import datetime
        out.append(datetime.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m"))
    return out


def google(lon, lat, key):
    """Google returns ONE date -- the CURRENT default panorama. Not a history.

    The time slider that motivates this whole tool is only reachable through the Maps JavaScript
    StreetViewService, not through this endpoint. So Google here is a recency check, not a dating
    tool, and the docstring says so rather than letting the output imply otherwise.
    """
    url = ("https://maps.googleapis.com/maps/api/streetview/metadata?" + urllib.parse.urlencode({
        "location": f"{lat},{lon}", "key": key, "radius": int(RADIUS_M)}))
    with urllib.request.urlopen(url, timeout=20) as r:
        d = json.load(r)
    return [d["date"]] if d.get("status") == "OK" and d.get("date") else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geom", required=True)
    ap.add_argument("--provider", choices=("mapillary", "google"), default="mapillary")
    ap.add_argument("--only", default=None, help="substring filter on building name")
    a = ap.parse_args()

    token = os.environ.get("MAPILLARY_TOKEN") if a.provider == "mapillary" else os.environ.get("GOOGLE_MAPS_API_KEY")
    if not token:
        var = "MAPILLARY_TOKEN" if a.provider == "mapillary" else "GOOGLE_MAPS_API_KEY"
        print(f"  {var} is not set — nothing to query.\n")
        if a.provider == "mapillary":
            print("  A Mapillary token is free: mapillary.com → Dashboard → Developers → register an\n"
                  "  application. Its imagery is CC-BY-SA, so unlike Street View it can also be\n"
                  "  republished with attribution if you later want pictures as well as dates.")
        else:
            print("  A Google Maps Platform key is needed. Note it answers with ONE date (the current\n"
                  "  panorama), not the capture history — Google is a recency check here, not a dater.")
        sys.exit(2)

    sites = buildings(a.geom)
    if a.only:
        sites = {k: v for k, v in sites.items() if a.only.upper() in k.upper()}
    print(f"  {len(sites)} building(s) · {a.provider} · {RADIUS_M:.0f} m radius\n")
    print(f"  {'building':26} {'passes':>6}  capture dates")
    print(f"  {'-'*26} {'-'*6}  {'-'*46}")
    span = collections.Counter()
    for k in sorted(sites):
        lon, lat = sites[k][0], sites[k][1]
        try:
            dates = mapillary(lon, lat, token) if a.provider == "mapillary" else google(lon, lat, token)
        except Exception as e:
            print(f"  {k[:26]:26} {'ERR':>6}  {e}")
            continue
        yrs = sorted({d[:4] for d in dates})
        for y in yrs:
            span[y] += 1
        print(f"  {k[:26]:26} {len(dates):6}  {', '.join(yrs) if yrs else 'no coverage'}")
    if span:
        print(f"\n  years with any coverage across these buildings:")
        for y in sorted(span):
            print(f"    {y}  {'#' * span[y]} ({span[y]})")
        print("\n  A building absent in one year and present in the next is dated to that gap.")


if __name__ == "__main__":
    main()
