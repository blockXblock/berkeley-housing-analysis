#!/usr/bin/env python3
"""
Generate KML file for 3D visualization of Berkeley housing pipeline.
Includes all projects with heights shown as extruded polygons.
"""

import sqlite3
import math
from datetime import datetime
from pathlib import Path

DB_PATH = Path('/Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db')
OUTPUT_PATH = Path('/Users/johngage/berkeley-data/docs/berkeley_skyline.kml')

# Street grid rotation - Berkeley streets run ~350° from true north (10° west of north)
GRID_ROTATION_DEG = -10  # counterclockwise rotation to align with street grid
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

# Pipeline stage to style mapping (KML uses AABBGGRR color format)
# UC Projects get special gold color and render first
PIPELINE_STYLES = {
    'UC_Project': ('FF00D7FF', 'Gold'),              # Gold - UC projects
    'Under Construction': ('FF00FF00', 'Green'),     # Green
    'Completed': ('FFFF0000', 'Blue'),               # Blue
    'Permits Active': ('FFFFFF00', 'Cyan'),          # Cyan
    'Entitled': ('FF0080FF', 'Orange'),              # Orange
    'In Review': ('FF00FFFF', 'Yellow'),             # Yellow
    'Decision Pending': ('FF00FFFF', 'Yellow'),      # Yellow
    'Application Submitted': ('FF00FFFF', 'Yellow'), # Yellow
    'Pre-Application': ('FFC0C0C0', 'Light Gray'),   # Light Gray
    'Stalled': ('FF0000FF', 'Red'),                  # Red
    'Withdrawn': ('FF0000FF', 'Red'),                # Red
    'Unknown': ('FFC0C0C0', 'Light Gray'),           # Light Gray
}

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

    # Get all projects with coordinates and heights
    # UC projects first (render on top), then by units
    cursor.execute('''
        SELECT
            address_display, units, vli_units,
            height_stories, height_feet, status,
            latitude, longitude, pipeline_stage,
            construction_data_reliability, is_uc_project
        FROM projects
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY is_uc_project DESC, units DESC
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

    # Add styles for each pipeline stage
    for stage, (color, desc) in PIPELINE_STYLES.items():
        style_id = get_style_id(stage)
        kml_parts.append(f'''
    <Style id="{style_id}">
      <PolyStyle>
        <color>{color}</color>
        <fill>1</fill>
        <outline>1</outline>
      </PolyStyle>
      <LineStyle>
        <color>ff000000</color>
        <width>1</width>
      </LineStyle>
    </Style>''')

    # Add folder for projects
    kml_parts.append('''
    <Folder>
      <name>Housing Projects</name>''')

    # Add each project as a placemark
    projects_added = 0
    uc_count = 0
    for row in projects:
        address, units, vli_units, height_stories, height_feet, status, lat, lng, pipeline_stage, reliability, is_uc_project = row

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

        # Get style - UC projects get special gold color
        if is_uc_project:
            style_key = 'UC_Project'
            uc_count += 1
        elif pipeline_stage in PIPELINE_STYLES:
            style_key = pipeline_stage
        else:
            style_key = 'Unknown'
        style_url = get_style_id(style_key)

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
            desc_parts.append("<br/><b style='color:gold'>UC Berkeley Project</b>")
        if reliability == 'estimated_height':
            desc_parts.append("<br/><i>(height estimated from units)</i>")

        description = ''.join(desc_parts)

        # Create polygon coordinates with rotation to align with Berkeley street grid
        # Special case: 2400 BOWDITCH St uses half-block polygon
        if '2400 BOWDITCH' in address.upper():
            # Half-block dimensions: ~55m N-S, ~55m E-W
            dx = 0.00035  # ~55m in longitude at this latitude
            dy = 0.00025  # ~55m in latitude
            center_lon, center_lat = -122.2570, 37.8670
        else:
            # Standard square footprint
            dx = FOOTPRINT
            dy = FOOTPRINT
            center_lon, center_lat = lng, lat

        # Calculate rotated corners (SE, NE, NW, SW, back to SE)
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

        kml_parts.append(f'''
      <Placemark>
        <name>{address}</name>
        <description><![CDATA[
{description}
]]></description>
        <styleUrl>#{style_url}</styleUrl>
        <Polygon>
          <extrude>1</extrude>
          <altitudeMode>relativeToGround</altitudeMode>
          <outerBoundaryIs>
            <LinearRing>
              <coordinates>{coords}</coordinates>
            </LinearRing>
          </outerBoundaryIs>
        </Polygon>
      </Placemark>''')
        projects_added += 1

    # Close folder and document
    kml_parts.append('''
    </Folder>
  </Document>
</kml>''')

    # Write KML file
    kml_content = ''.join(kml_parts)
    with open(OUTPUT_PATH, 'w') as f:
        f.write(kml_content)

    conn.close()

    print(f"\n✓ Generated KML with {projects_added} projects")
    print(f"  UC projects (gold): {uc_count}")
    print(f"  Output: {OUTPUT_PATH}")
    print(f"  File size: {OUTPUT_PATH.stat().st_size:,} bytes")

if __name__ == '__main__':
    generate_kml()
