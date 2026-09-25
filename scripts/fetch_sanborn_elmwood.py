#!/usr/bin/env python3
"""Fetch Library of Congress Sanborn fire-insurance sheets covering the Elmwood.

WHY: the Sanborn sheets are the only primary source that records, block by block and
building by building, how many STOREYS each structure had — the numeral is drawn inside
each footprint. That is the one input our modern parcel/assessor data cannot supply for
pre-war Berkeley, and it is what makes a historical floor-area (FAR) series possible.

WHAT IS ACTUALLY DIGITISED AT LoC (verified 2026-09-24):
    Berkeley vol. 2 — 1911  -> g00419191102   sheets present
    Berkeley vol. 2 — 1950  -> g00419195002   sheets present
    1917 / 1929 editions    -> catalogued, `resources: 0`, NO images exposed.
Those two dates are therefore the comparison available for free. The 1929 edition, and
the 1950 *updates*, are behind ProQuest Digital Sanborn Maps (UC Berkeley subscribes —
John's faculty credentials reach it). See notes/2026-09-24_sanborn_elmwood_1911_1950.md.

SHEET NUMBERS ARE STABLE BETWEEN 1911 AND 1950 for this area (read off each edition's own
street index, not assumed):
    sheet 179 = College Ave EVEN side, 2800-2958  (Hillegass / Benvenue / College)
    sheet 180 = College Ave ODD  side, 2801-2939  (College / Piedmont / Kelsey)
Both run Stuart -> Russell -> Ashby, i.e. the whole Elmwood commercial core.

Public domain (US federal). Re-run is idempotent; existing files are skipped.
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "sanborn"

# edition key -> (LoC volume id, sheet-name prefix)
EDITIONS = {
    "1911": ("g00419191102", "00419_02_1911"),
    "1950": ("g00419195002", "00419_02_1950"),
}
SHEETS = ["ind1", "ind2", "ind3", "0179", "0180"]
PCT = 50  # 50% of full res ~= 3300x3900, enough to read storey numerals

TMPL = (
    "https://tile.loc.gov/image-services/iiif/"
    "service:gmd:gmd436m:g4364m:g4364bm:g4364bm_{vol}:{pfx}-{sheet}"
    "/full/pct:{pct}/0/default.jpg"
)


def fetch(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    req = urllib.request.Request(url, headers={"User-Agent": "berkeley-data/1.0 (civic research)"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            if r.status != 200:
                return False
            dest.write_bytes(r.read())
        return dest.stat().st_size > 0
    except Exception as exc:  # noqa: BLE001 - report and continue
        print(f"    !! {exc}", file=sys.stderr)
        return False


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest, missing = [], []
    for year, (vol, pfx) in EDITIONS.items():
        print(f"{year} (vol 2, {vol})")
        for sheet in SHEETS:
            dest = OUT / f"sanborn_berkeley_v2_{year}_{sheet}.jpg"
            url = TMPL.format(vol=vol, pfx=pfx, sheet=sheet, pct=PCT)
            if fetch(url, dest):
                digest = hashlib.sha256(dest.read_bytes()).hexdigest()
                manifest.append(f"{digest}  {dest.name}  {dest.stat().st_size}  {url}")
                print(f"  {sheet}  {dest.stat().st_size:>9,} bytes")
            else:
                missing.append(f"{year}/{sheet}")
                print(f"  {sheet}  MISSING")

    (OUT / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n")
    print(f"\n{len(manifest)} sheets in {OUT}")
    if missing:
        print(f"missing: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
