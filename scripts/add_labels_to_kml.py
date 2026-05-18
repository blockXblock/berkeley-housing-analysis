#!/usr/bin/env python3
"""
Augment a Berkeley Housing Pipeline geometry KML with labels.

For each Placemark inside the Housing Projects folder:
- Look up the project in berkeley_housing_analysis.db by address
- Build label text: "Address · units · stage" (with sub-building suffix if present)
- Wrap the existing <Polygon> in <MultiGeometry> + <Point> at the polygon centroid + roof altitude
- Replace the Placemark's <name> with the label text

Also strips the embedded "Berkeley Housing Pipeline - Extended Dramatic Tour"
so the geometry file is clean.

Input: a Geometry-*.kml file (default: Geometry-2026-05-17.kml)
Output: two files
    - docs/kml_versions/Geometry/Geometry-YYYY-MM-DD-labeled.kml (dated archive)
    - docs/geometry.kml (stable URL for the public site)

Usage:
    python3 scripts/add_labels_to_kml.py
    python3 scripts/add_labels_to_kml.py --input path/to/different/geometry.kml
"""
import argparse
import re
import sqlite3
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path('/Users/johngage/berkeley-data')
DEFAULT_INPUT = REPO_ROOT / 'docs/kml_versions/Geometry/Geometry-2026-05-17.kml'
DB_PATH = REPO_ROOT / 'databases/berkeley_housing_analysis.db'
GEOMETRY_DIR = REPO_ROOT / 'docs/kml_versions/Geometry'
STABLE_OUTPUT_PATH = REPO_ROOT / 'docs/geometry.kml'


def load_projects():
    """Build a dict mapping normalized-address -> project info."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("""
        SELECT address_display, units, pipeline_stage, height_feet, height_stories
        FROM projects
        WHERE address_display IS NOT NULL
    """)
    projects = {}
    for row in cur:
        key = row['address_display'].strip().upper()
        projects[key] = dict(row)
    conn.close()
    return projects


def normalize_for_match(placemark_name):
    """
    Normalize a Placemark name for database matching.
    Strips suffixes like ' - North', '- South', or trailing ' 1', ' 2', ' 3'.
    Returns (base_address_upper, suffix or None).
    """
    name = placemark_name.strip()
    # Try dash-separated suffix: "X - South", "X- South", "X-South"
    # Whitespace before the dash is optional; whitespace after is also optional.
    dash_match = re.match(r'^(.*?)\s*-\s*(\w+)\s*$', name)
    if dash_match:
        return dash_match.group(1).strip().upper(), dash_match.group(2)
    # Try numeric building-number suffix: "Ashby BART 1", "Ashby Bart 2"
    num_match = re.match(r'^(.*?)\s+(\d+)\s*$', name)
    if num_match:
        suffix = f"Building {num_match.group(2)}"
        return num_match.group(1).strip().upper(), suffix
    return name.upper(), None


def polygon_centroid(coords_text):
    """
    Parse a KML <coordinates> text block and return (centroid_lon, centroid_lat).
    Coordinates are space- or newline-separated "lon,lat[,alt]" tuples.
    """
    points = []
    for token in coords_text.split():
        parts = token.split(',')
        if len(parts) >= 2:
            try:
                points.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    if not points:
        return None, None
    return sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)


def compute_height_m(row):
    """Return building height in meters, using same logic as generate_kml.py."""
    if row['height_feet']:
        return round(row['height_feet'] * 0.3048, 1)
    if row['height_stories']:
        return round(row['height_stories'] * 3.5, 1)
    return 10.5


def build_label(row, suffix):
    """Build label text from a project row and optional sub-building suffix."""
    address = (row['address_display'] or 'unknown address').title()
    stage = (row['pipeline_stage'] or 'Unknown').replace('_', ' ').title()
    units = row['units']
    parts = [address]
    if suffix:
        parts.append(suffix)
    if units and units > 0:
        parts.append(f"{units} units")
    parts.append(stage)
    return ' · '.join(parts)


# Regex to find one Placemark block at a time
PLACEMARK_RE = re.compile(r'(<Placemark>.*?</Placemark>)', re.DOTALL)
NAME_RE = re.compile(r'<name>([^<]+)</name>')
COORDS_RE = re.compile(r'<coordinates>([^<]+)</coordinates>')
POLYGON_RE = re.compile(r'(<Polygon>.*?</Polygon>)', re.DOTALL)


def augment_placemark(placemark_text, projects, stats):
    """
    Return a modified Placemark with label + MultiGeometry wrapping,
    or the original Placemark unchanged if no DB match was found.
    Updates the stats dict in place.
    """
    name_match = NAME_RE.search(placemark_text)
    if not name_match:
        stats['no_name'].append('(unknown)')
        return placemark_text
    name = name_match.group(1)
    base_upper, suffix = normalize_for_match(name)
    # Try direct match, then fallback with common street-type suffixes
    # for cases like "2400 BOWDITCH" -> "2400 BOWDITCH ST" in DB.
    lookup_keys = [base_upper] + [
        f"{base_upper} {suf}" for suf in ('ST', 'AVE', 'WAY', 'BLVD', 'PL', 'DR')
    ]
    matched_key = next((k for k in lookup_keys if k in projects), None)
    if matched_key is None:
        stats['unmatched'].append(name)
        return placemark_text
    row = projects[matched_key]
    label_text = build_label(row, suffix)
    height_m = compute_height_m(row)

    polygon_match = POLYGON_RE.search(placemark_text)
    if not polygon_match:
        stats['no_polygon'].append(name)
        return placemark_text
    polygon_xml = polygon_match.group(1)
    coords_match = COORDS_RE.search(polygon_xml)
    if not coords_match:
        stats['no_coords'].append(name)
        return placemark_text
    centroid_lon, centroid_lat = polygon_centroid(coords_match.group(1))
    if centroid_lon is None:
        stats['no_centroid'].append(name)
        return placemark_text

    new_name = f'<name>{label_text}</name>'
    multi_geom = (
        f'<MultiGeometry>'
        f'<Point>'
        f'<coordinates>{centroid_lon},{centroid_lat},{height_m}</coordinates>'
        f'<altitudeMode>relativeToGround</altitudeMode>'
        f'</Point>'
        f'{polygon_xml}'
        f'</MultiGeometry>'
    )
    out = NAME_RE.sub(new_name, placemark_text, count=1)
    out = POLYGON_RE.sub(multi_geom, out, count=1)
    stats['matched'] += 1
    return out


def strip_embedded_tour(kml_text):
    """Remove the embedded <gx:Tour>...</gx:Tour> block."""
    tour_re = re.compile(r'\s*<gx:Tour>.*?</gx:Tour>\s*', re.DOTALL)
    return tour_re.sub('\n\t', kml_text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT,
                        help=f'Input KML path (default: {DEFAULT_INPUT})')
    args = parser.parse_args()

    print(f"Reading {args.input}")
    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")
    kml_text = args.input.read_text(encoding='utf-8')

    print(f"Loading projects from {DB_PATH}")
    projects = load_projects()
    print(f"  {len(projects)} projects loaded")

    # Strip the embedded leftover tour
    kml_text = strip_embedded_tour(kml_text)

    # Augment each Placemark with labels
    stats = {
        'matched': 0,
        'unmatched': [],
        'no_name': [],
        'no_polygon': [],
        'no_coords': [],
        'no_centroid': [],
    }
    def replace_one(match):
        return augment_placemark(match.group(1), projects, stats)
    out_text = PLACEMARK_RE.sub(replace_one, kml_text)

    # Write output
    today = datetime.now().strftime('%Y-%m-%d')
    dated_output = GEOMETRY_DIR / f"Geometry-{today}-labeled.kml"
    GEOMETRY_DIR.mkdir(parents=True, exist_ok=True)
    STABLE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    dated_output.write_text(out_text, encoding='utf-8')
    STABLE_OUTPUT_PATH.write_text(out_text, encoding='utf-8')

    # Summary
    print()
    print(f"✓ Labels added to {stats['matched']} Placemarks")
    if stats['unmatched']:
        print(f"  Unmatched ({len(stats['unmatched'])}):")
        for n in stats['unmatched']:
            print(f"    - {n!r}")
    for k in ['no_name', 'no_polygon', 'no_coords', 'no_centroid']:
        if stats[k]:
            print(f"  {k} ({len(stats[k])}):")
            for n in stats[k]:
                print(f"    - {n!r}")
    print()
    print(f"  Dated archive: {dated_output}")
    print(f"  Stable URL:    {STABLE_OUTPUT_PATH}")
    print(f"  File size:     {dated_output.stat().st_size:,} bytes")


if __name__ == '__main__':
    main()
