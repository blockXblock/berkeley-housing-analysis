#!/usr/bin/env python3
"""
Generate KML file for 3D visualization of Berkeley housing pipeline.
Includes all projects with heights shown as extruded polygons.

Reads polygon geometries from project_geometries table when available,
falls back to synthetic squares for projects without stored geometry.
"""

import sqlite3
import json
import math
from datetime import datetime
from pathlib import Path

DB_PATH = Path('/Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db')
# Output paths: dated archive + stable URL (script writes both)
_GEOMETRY_DIR = Path('/Users/johngage/berkeley-data/docs/kml_versions/Geometry')
OUTPUT_PATH = _GEOMETRY_DIR / f"Geometry-{datetime.now().strftime('%Y-%m-%d')}.kml"
STABLE_OUTPUT_PATH = Path('/Users/johngage/berkeley-data/docs/geometry.kml')

# Street grid rotation - Berkeley streets run ~350° from true north (10° west of north)
GRID_ROTATION_DEG = 10  # clockwise rotation to align with street grid
GRID_ROTATION_RAD = math.radians(GRID_ROTATION_DEG)
LAT_CENTER = 37.87  # approximate center latitude for scaling
LON_SCALE = math.cos(math.radians(LAT_CENTER))  # ~0.789

def rotate_point(center_lon, center_lat, dx, dy):
    """
    Rotate a point around center by GRID_ROTATION_DEG degrees.
    dx, dy are offsets in degrees (dy for lat, dx for lon before scaling).
    Returns (new_lon, new_lat).
    """
    # Scale dx for longitude (degrees are narrower at this latitude)
    dx_scaled = dx / LON_SCALE

    # Rotate
    cos_a = math.cos(GRID_ROTATION_RAD)
    sin_a = math.sin(GRID_ROTATION_RAD)

    new_dx = dx_scaled * cos_a - dy * sin_a
    new_dy = dx_scaled * sin_a + dy * cos_a

    # Scale back and apply to center
    new_lon = center_lon + new_dx * LON_SCALE
    new_lat = center_lat + new_dy

    return new_lon, new_lat


def polygon_centroid(coords):
    """
    Compute simple arithmetic mean of polygon vertex coordinates.
    Args: coords is a list of [lon, lat] pairs.
    Returns: (centroid_lon, centroid_lat). Returns (None, None) if empty.
    """
    if not coords:
        return None, None
    n = len(coords)
    return (sum(c[0] for c in coords) / n, sum(c[1] for c in coords) / n)

def parse_geojson_coords(geojson_str):
    """
    Parse GeoJSON string and extract polygon coordinates.
    Handles both Polygon and MultiPolygon types.
    Returns list of [lon, lat] coordinate pairs for the exterior ring.
    """
    try:
        geom = json.loads(geojson_str)
        geom_type = geom.get('type', '')

        if geom_type == 'Polygon':
            # First ring is exterior
            return geom['coordinates'][0]
        elif geom_type == 'MultiPolygon':
            # Use first polygon's exterior ring
            return geom['coordinates'][0][0]
        else:
            return None
    except (json.JSONDecodeError, KeyError, IndexError):
        return None

# Pipeline stage to style mapping (KML uses AABBGGRR color format)
# Color values are base RGB in BBGGRR format (alpha added at style generation)
PIPELINE_STYLES = {
    'UC_Project': ('FF00AA', 'Purple'),              # Purple (#AA00FF)
    'Under Construction': ('FF6229', 'Blue'),        # Blue (#2962FF)
    'Completed': ('53C800', 'Green'),                # Green (#00C853)
    'Permits Active': ('FFFF00', 'Cyan'),            # Cyan
    'Entitled': ('0080FF', 'Orange'),                # Orange
    'In Review': ('00FFFF', 'Yellow'),               # Yellow
    'Decision Pending': ('00FFFF', 'Yellow'),        # Yellow
    'Application Submitted': ('00FFFF', 'Yellow'),   # Yellow
    'Pre-Application': ('C0C0C0', 'Light Gray'),     # Light Gray
    'Stalled': ('0000FF', 'Red'),                    # Red
    'Withdrawn': ('0000FF', 'Red'),                  # Red
    'Unknown': ('C0C0C0', 'Light Gray'),             # Light Gray
}

# Line width by geometry source category
GEOM_LINE_WEIGHTS = {
    'parcel': 1.5,      # apn_parcel, apn_parcel_merged, apn_parcel_subdivided, site_plan
    'footprint': 2.5,   # building_footprint, manual_polygon
    'synthetic': 1.0,   # synthetic_footprint, or no geometry
}

def get_geom_weight_category(geometry_type):
    """Map geometry type code to line weight category."""
    if geometry_type in ('apn_parcel', 'apn_parcel_merged', 'apn_parcel_subdivided', 'site_plan'):
        return 'parcel'
    elif geometry_type in ('building_footprint', 'manual_polygon'):
        return 'footprint'
    else:
        return 'synthetic'

# Building footprint size (in degrees, roughly 20m)
FOOTPRINT = 0.0002

def get_style_id(status):
    """Convert status to KML style ID"""
    if not status:
        return "style_Unknown"
    # Normalize status for style ID
    style_name = status.replace(' ', '_').replace('-', '_')
    return f"style_{style_name}"

def generate_kml():
    print("=" * 60)
    print("GENERATE KML - Berkeley Housing Pipeline 3D Skyline")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all projects with coordinates and heights, joined with geometry
    # Excludes projects with superseded geometry (duplicates)
    # UC projects first (render on top), then by units
    cursor.execute('''
        SELECT
            p.address_display, p.units, p.vli_units,
            p.height_stories, p.height_feet, p.status,
            p.latitude, p.longitude, p.pipeline_stage,
            p.construction_data_reliability, p.is_uc_project,
            pg.geojson, vgt.code as geometry_type
        FROM projects p
        LEFT JOIN project_geometries pg ON p.id = pg.project_id AND pg.is_current = 1
        LEFT JOIN vocabulary_geometry_types vgt ON pg.geometry_type_id = vgt.id
        WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL
          AND (
            pg.id IS NOT NULL  -- has current geometry
            OR NOT EXISTS (SELECT 1 FROM project_geometries pg2 WHERE pg2.project_id = p.id)  -- OR has no geometry rows at all
          )
        ORDER BY p.is_uc_project DESC, p.units DESC
    ''')
    projects = cursor.fetchall()
    print(f"Projects with coordinates: {len(projects)}")

    # Count projects with heights
    with_height = sum(1 for p in projects if p[3] or p[4])
    print(f"Projects with height data: {with_height}")

    # Build KML
    kml_parts = []

    # Header
    kml_parts.append('''<?xml version="1.0" ?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Berkeley Housing Pipeline - 3D Skyline</name>
    <description>''' + f"{len(projects)} housing projects. Heights shown as stories × 3.5m. Generated {datetime.now().strftime('%Y-%m-%d')}." + '''</description>''')

    # Add styles for each combination of pipeline stage + geometry weight category
    # Fill: 50% alpha (80), Line: 100% alpha (FF), same base color
    for stage, (base_color, desc) in PIPELINE_STYLES.items():
        for weight_cat, line_width in GEOM_LINE_WEIGHTS.items():
            style_id = f"{get_style_id(stage)}_{weight_cat}"
            fill_color = f"80{base_color}"   # 50% alpha for fill
            line_color = f"FF{base_color}"   # 100% alpha for line

            kml_parts.append(f'''
    <Style id="{style_id}">
      <PolyStyle>
        <color>{fill_color}</color>
        <fill>1</fill>
        <outline>1</outline>
      </PolyStyle>
      <LineStyle>
        <color>{line_color}</color>
        <width>{line_width}</width>
      </LineStyle>
    </Style>''')

    # Add label-only style: hides the default pushpin icon and renders
    # the Placemark's <name> as white text at the Point coordinates.
    kml_parts.append('''
    <Style id="LabelOnly">
      <IconStyle>
        <scale>0</scale>
        <Icon><href></href></Icon>
      </IconStyle>
      <LabelStyle>
        <color>ffffffff</color>
        <scale>0.9</scale>
      </LabelStyle>
    </Style>''')

    # Add folder for projects
    kml_parts.append('''
    <Folder>
      <name>Housing Projects</name>''')

    # Add each project as a placemark
    projects_added = 0
    uc_count = 0
    using_stored_geom = 0
    using_synthetic = 0

    for row in projects:
        address, units, vli_units, height_stories, height_feet, status, lat, lng, pipeline_stage, reliability, is_uc_project, geojson_str, geometry_type = row

        # Calculate height in meters
        if height_feet:
            height_m = height_feet * 0.3048
        elif height_stories:
            height_m = height_stories * 3.5  # 3.5m per story
        else:
            height_m = 10.5  # Default 3 stories

        # Round height
        height_m = round(height_m, 1)

        # Determine display status
        display_status = pipeline_stage or status or 'Unknown'

        # Get style - UC projects get special purple color
        if is_uc_project:
            style_key = 'UC_Project'
            uc_count += 1
        elif pipeline_stage in PIPELINE_STYLES:
            style_key = pipeline_stage
        else:
            style_key = 'Unknown'

        # Determine geometry weight category for line styling
        geom_weight_cat = get_geom_weight_category(geometry_type)
        style_url = f"{get_style_id(style_key)}_{geom_weight_cat}"

        # Build label text: "Address · units · stage"
        address_label = (address or 'unknown address').title()
        stage_label = (display_status or 'Unknown').replace('_', ' ').title()
        if units and units > 0:
            label_text = f"{address_label} · {units} units · {stage_label}"
        else:
            label_text = f"{address_label} · {stage_label}"

        # Create description
        desc_parts = [
            f"<b>{address}</b><br/>",
            f"<b>Units:</b> {units or 0}<br/>",
            f"<b>VLI Units:</b> {vli_units or 0}<br/>",
            f"<b>Stories:</b> {height_stories or 'est.'}<br/>",
            f"<b>Height:</b> {height_m}m<br/>",
            f"<b>Status:</b> {display_status}",
        ]
        if is_uc_project:
            desc_parts.append("<br/><b style='color:purple'>UC Berkeley Project</b>")
        if reliability == 'estimated_height':
            desc_parts.append("<br/><i>(height estimated from units)</i>")

        description = ''.join(desc_parts)

        # Create polygon coordinates
        # Priority: use stored geometry from project_geometries, fall back to synthetic
        if geojson_str:
            polygon_coords = parse_geojson_coords(geojson_str)
            if polygon_coords:
                # Build coordinate string from stored geometry
                coord_lines = []
                for coord in polygon_coords:
                    lon, lat_coord = coord[0], coord[1]
                    coord_lines.append(f"        {lon},{lat_coord},{height_m}")
                coords = '\n'.join(coord_lines)
                using_stored_geom += 1
            else:
                # Fallback: GeoJSON parsing failed
                polygon_coords = None

        if not geojson_str or not polygon_coords:
            # Synthetic square footprint with rotation
            dx = FOOTPRINT
            dy = FOOTPRINT
            center_lon, center_lat = lng, lat
            se_lon, se_lat = rotate_point(center_lon, center_lat, dx, -dy)
            ne_lon, ne_lat = rotate_point(center_lon, center_lat, dx, dy)
            nw_lon, nw_lat = rotate_point(center_lon, center_lat, -dx, dy)
            sw_lon, sw_lat = rotate_point(center_lon, center_lat, -dx, -dy)
            coords = f'''
        {se_lon},{se_lat},{height_m}
        {ne_lon},{ne_lat},{height_m}
        {nw_lon},{nw_lat},{height_m}
        {sw_lon},{sw_lat},{height_m}
        {se_lon},{se_lat},{height_m}
    '''
            using_synthetic += 1

        # Compute label anchor: polygon centroid at building roof altitude.
        # For synthetic squares, polygon_coords may be None, in which case
        # we use the project's lat/lng directly.
        if polygon_coords:
            label_lon, label_lat = polygon_centroid(polygon_coords)
        else:
            label_lon, label_lat = lng, lat

        kml_parts.append(f'''
      <Placemark>
        <name>{label_text}</name>
        <description><![CDATA[
{description}
]]></description>
        <styleUrl>#{style_url}</styleUrl>
        <MultiGeometry>
          <Point>
            <coordinates>{label_lon},{label_lat},{height_m}</coordinates>
            <altitudeMode>relativeToGround</altitudeMode>
          </Point>
          <Polygon>
            <extrude>1</extrude>
            <altitudeMode>relativeToGround</altitudeMode>
            <outerBoundaryIs>
              <LinearRing>
                <coordinates>{coords}</coordinates>
              </LinearRing>
            </outerBoundaryIs>
          </Polygon>
        </MultiGeometry>
      </Placemark>''')
        projects_added += 1

    # Close folder and document
    kml_parts.append('''
    </Folder>
  </Document>
</kml>''')

    # Write KML file (dated archive + stable URL copy)
    kml_content = ''.join(kml_parts)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        f.write(kml_content)
    STABLE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STABLE_OUTPUT_PATH, 'w') as f:
        f.write(kml_content)

    conn.close()

    print(f"\n✓ Generated KML with {projects_added} projects")
    print(f"  UC projects (purple): {uc_count}")
    print(f"  Using stored geometry: {using_stored_geom}")
    print(f"  Using synthetic squares: {using_synthetic}")
    print(f"  Dated archive: {OUTPUT_PATH}")
    print(f"  Stable URL:    {STABLE_OUTPUT_PATH}")
    print(f"  File size:     {OUTPUT_PATH.stat().st_size:,} bytes")

if __name__ == '__main__':
    generate_kml()
