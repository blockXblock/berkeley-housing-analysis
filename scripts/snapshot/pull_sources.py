#!/usr/bin/env python3
"""pull_sources.py — fetch the public sources behind the Berkeley Snapshot report.

Every file lands in data/raw/snapshot/<date>/ and is recorded in manifest.json (url, fetched_at, bytes, sha256).
Large federal files (LODES, TIGER) are fetched once and kept out of git (*.gz/*.zip); the manifest pins them.
Read-only with respect to every database. Re-run with --date to refresh into a new dated folder.

Run: .venv/bin/python scripts/snapshot/pull_sources.py [--date 2026-10-01]
"""
import argparse, datetime, hashlib, json, os, subprocess, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CR = 'https://api.censusreporter.org/1.0/data/show/latest?table_ids={t}&geo_ids={g}'
PLACE = '16000US0606000'                      # Berkeley city, CA
# ACS tables: people, tenure, income, age, cars, housing stock, rents, commute mode
ACS_GROUPS = [
    'B01003,B01001,B25003,B25008,B26001',
    'B19001,B19013,B19301,B17021',
    'B25044,B08301,B08303',
    'B25001,B25004,B25024,B25034,B25041',
    'B25064,B25077,B25070,B25091',
    'B03002,B11001,B15003',
]
LODES = 'https://lehd.ces.census.gov/data/lodes/LODES8/ca/'
SOURCES = {
    # Census LEHD LODES 2023: origin-destination, workplace and residence area characteristics (block level)
    'lodes/ca_xwalk.csv.gz': LODES + 'ca_xwalk.csv.gz',
    'lodes/ca_od_main_JT00_2023.csv.gz': LODES + 'od/ca_od_main_JT00_2023.csv.gz',
    'lodes/ca_od_aux_JT00_2023.csv.gz': LODES + 'od/ca_od_aux_JT00_2023.csv.gz',
    'lodes/ca_wac_S000_JT00_2023.csv.gz': LODES + 'wac/ca_wac_S000_JT00_2023.csv.gz',
    'lodes/ca_rac_S000_JT00_2023.csv.gz': LODES + 'rac/ca_rac_S000_JT00_2023.csv.gz',
    # California DMV vehicle registrations by ZIP and fuel type, as of 2026-01-01
    'dmv/vehicle-fuel-type-counts-2025.csv': None,   # resolved from the data.ca.gov package below
    # California Department of Finance E-5: population and housing estimates, January 1, 2026
    'dof/E-5_2026_InternetVersion.xlsx': 'https://dof.ca.gov/media/docs/forecasting/Demographics/estimates/e-5-population-and-housing-estimates-for-cities-counties-and-the-state-2020-2026/E-5_2026_InternetVersion.xlsx',
    # EBMUD 2025 Urban Water Management Plan (district demand by sector; storage)
    'ebmud/UWMP_2025.pdf': 'https://www.ebmud.com/download_file/force/58536/735?UWMP_STANDALONE-2025-FINAL.pdf',
    # Census TIGER 2024 boundaries (statewide; filtered to Berkeley by the builder)
    'tiger/tl_2024_06_bg.zip': 'https://www2.census.gov/geo/tiger/TIGER2024/BG/tl_2024_06_bg.zip',
    'tiger/tl_2024_06_tract.zip': 'https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_06_tract.zip',
}


def fetch(url, path, manifest, rel):
    if os.path.exists(path) and rel in manifest:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # curl, not urllib: data.ca.gov's download redirect refuses Python's client (HTTP 403) but serves curl.
    code = subprocess.run(['curl', '-sL', '-m', '900', '-A', 'Mozilla/5.0 (BerkeleyBuild research)', '-o', path,
                           '-w', '%{http_code}', url], capture_output=True, text=True).stdout.strip()
    if code != '200':
        os.path.exists(path) and os.remove(path)
        raise urllib.error.HTTPError(url, int(code or 0), 'download failed', None, None)
    h = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    manifest[rel] = dict(url=url, fetched_at=datetime.datetime.now().isoformat(timespec='seconds'),
                         bytes=os.path.getsize(path), sha256=h)
    print(f'  {rel}  {os.path.getsize(path):,} bytes')


def dmv_url():
    api = 'https://data.ca.gov/api/3/action/package_show?id=vehicle-fuel-type-count-by-zip-code'
    res = json.load(urllib.request.urlopen(api, timeout=60))['result']['resources']
    r = next(r for r in res if r['name'].startswith('1/1/2026'))
    return r['url']


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--date', default=datetime.date.today().isoformat())
    out = os.path.join(ROOT, 'data', 'raw', 'snapshot', ap.parse_args().date)
    mpath = os.path.join(out, 'manifest.json')
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    try:
        for geo, label in ((PLACE, 'city'), ('140|' + PLACE, 'tract'), ('150|' + PLACE, 'blockgroup')):
            # block groups: one table per request (some tables are not published at that grain; the API then
            # refuses the whole request). A refused table is recorded as unavailable, not silently skipped.
            groups = ACS_GROUPS if label != 'blockgroup' else [t for g in ACS_GROUPS for t in g.split(',')]
            for i, t in enumerate(groups):
                rel = f'acs/{label}_{i}.json' if label != 'blockgroup' else f'acs/{label}_{t}.json'
                try:
                    fetch(CR.format(t=t, g=geo), os.path.join(out, rel), manifest, rel)
                except urllib.error.HTTPError as e:
                    manifest['unavailable:' + rel] = dict(url=CR.format(t=t, g=geo), error=f'HTTP {e.code}')
                    print(f'  {rel}  unavailable (HTTP {e.code})')
        for rel, url in SOURCES.items():
            fetch(url or dmv_url(), os.path.join(out, rel), manifest, rel)
    finally:
        json.dump(manifest, open(mpath, 'w'), indent=1)
    print(f'{len(manifest)} files pinned in {mpath}')


if __name__ == '__main__':
    main()
