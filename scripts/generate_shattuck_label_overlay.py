from pathlib import Path
import html
import math
import re
import sqlite3
import xml.etree.ElementTree as ET


# Run from the berkeley-data repository. This script is intended to live in
# scripts/, so parents[1] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "databases/berkeley_housing_v2.db"
GEOM_PATH = REPO_ROOT / "kml/geometry/versions/Geometry-2026-05-18-labeled.kml"
CONTROL_PATH = REPO_ROOT / "kml/geometry/versions/Control-Points__Shattuck Control Points.kml"
OUT_PATH = REPO_ROOT / "kml/geometry/versions/Shattuck-building-label-overlay-v5.kml"
SIDE_LABEL_ALT_M = 15.0


def local_xy(lon, lat, lon0, lat0):
    return ((lon - lon0) * 111320 * math.cos(math.radians(lat0)), (lat - lat0) * 110540)


def inv_local_xy(x, y, lon0, lat0):
    return (lon0 + x / (111320 * math.cos(math.radians(lat0))), lat0 + y / 110540)


def parse_controls():
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    root = ET.parse(CONTROL_PATH).getroot()
    pts = []
    for pm in root.findall(".//k:Placemark", ns):
        name = pm.findtext("k:name", namespaces=ns)
        coord_el = pm.find(".//k:Point/k:coordinates", ns)
        if name and coord_el is not None and coord_el.text:
            lon, lat, *_ = coord_el.text.strip().split(",")
            pts.append((name.strip(), float(lon), float(lat)))
    return pts


def closest_point_on_route(lon, lat, route):
    bx, by = local_xy(lon, lat, lon, lat)
    best = None
    for i in range(len(route) - 1):
        _, lon1, lat1 = route[i]
        _, lon2, lat2 = route[i + 1]
        x1, y1 = local_xy(lon1, lat1, lon, lat)
        x2, y2 = local_xy(lon2, lat2, lon, lat)
        vx, vy = x2 - x1, y2 - y1
        seg2 = vx * vx + vy * vy
        if seg2 == 0:
            continue
        t = max(0, min(1, ((bx - x1) * vx + (by - y1) * vy) / seg2))
        px, py = x1 + t * vx, y1 + t * vy
        d = math.hypot(bx - px, by - py)
        if best is None or d < best[0]:
            best = (d, px, py)
    if best is None:
        return lon, lat, 0
    d, px, py = best
    plon, plat = inv_local_xy(px, py, lon, lat)
    return plon, plat, d


def parse_geometry_heights():
    text = GEOM_PATH.read_text(errors="ignore")
    result = {}
    for block in re.findall(r"<Placemark>.*?</Placemark>", text, re.S):
        nm = re.search(r"<name>(.*?)</name>", block, re.S)
        if not nm:
            continue
        name = re.sub(r"<.*?>", "", nm.group(1)).strip()
        upper_name = name.upper()
        if "SHATTUCK" not in upper_name and "VIRGINIA" not in upper_name:
            continue
        nums = re.findall(r"\d+", name)
        if not nums:
            continue
        street_no = nums[0]
        street = "VIRGINIA" if "VIRGINIA" in upper_name else "SHATTUCK"
        pts = []
        for ctext in re.findall(r"<coordinates>(.*?)</coordinates>", block, re.S):
            for token in ctext.replace("\n", " ").replace("\t", " ").split():
                parts = token.split(",")
                if len(parts) >= 2:
                    try:
                        pts.append(
                            (
                                float(parts[0]),
                                float(parts[1]),
                                float(parts[2]) if len(parts) > 2 and parts[2] else 0.0,
                            )
                        )
                    except ValueError:
                        pass
        if pts:
            result[(street_no, street)] = {
                "geometry_name": name,
                "center_lon": sum(p[0] for p in pts) / len(pts),
                "center_lat": sum(p[1] for p in pts) / len(pts),
                "roof_m": max(p[2] for p in pts),
            }
    return result


def project_rows():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        select project_id, address_display, total_units, height_stories, height_feet,
               owner_current, developer, architect, latitude, longitude,
               co_issued_date, assessed_value, assessed_net_taxable, est_annual_tax,
               exists(select 1 from project_classifications pc
                      where pc.project_id = v_projects_flat.project_id
                        and pc.classification_type_id = 6) as is_uc
        from v_projects_flat
        where (
              lower(address_display) like '%shattuck%'
           or lower(address_display) like '%2109%virginia%'
        )
          and total_units is not null
          and total_units > 0
          and latitude is not null
          and longitude is not null
        order by total_units desc, address_display
        """
    ).fetchall()
    con.close()
    return rows


def clean(value, fallback="n/a"):
    if value is None:
        return fallback
    s = str(value).strip()
    return s if s else fallback


def clean_number(value, fallback="n/a"):
    if value is None:
        return fallback
    try:
        f = float(value)
        if f.is_integer():
            return str(int(f))
        return f"{f:g}"
    except (TypeError, ValueError):
        return clean(value, fallback)


def assessed_line(row):
    """Per-project assessed-value/tax line, branching on completion + value state.
    completed+value -> "$X assessed · ~$Y/yr (est. ad-valorem)"; completed+exempt (net=0) ->
    "$X assessed · tax-exempt"; completed+no-value-yet -> "assessed value pending"; pipeline
    or UC -> None (omit — pipeline has no assessed value; UC is Regents tax-exempt off-grid).
    "tax-exempt" is shown ONLY when net-taxable == 0; tax is the ad-valorem approx (excludes
    flat parcel levies)."""
    # access fields defensively (sqlite3.Row supports keys())
    keys = row.keys()
    is_uc = "is_uc" in keys and row["is_uc"]
    co = row["co_issued_date"] if "co_issued_date" in keys else None
    assessed = row["assessed_value"] if "assessed_value" in keys else None
    if is_uc:
        return None
    if assessed is not None:
        net = row["assessed_net_taxable"]
        if net == 0:
            return f"${assessed:,.0f} assessed · tax-exempt"
        tax = row["est_annual_tax"]
        tax_str = f" · ~${tax:,.0f}/yr (est. ad-valorem)" if tax else ""
        return f"${assessed:,.0f} assessed{tax_str}"
    if co:  # completed but no usable value (crosswalk/lag pending)
        return "assessed value pending"
    return None  # pipeline -> omit


def label_text(row):
    owner = clean(row["owner_current"])
    architect = clean(row["architect"])
    if owner == "n/a" and clean(row["developer"]) != "n/a":
        owner = f"Dev: {clean(row['developer'])}"
    lines = [
        clean(row["address_display"]),
        f"{clean_number(row['total_units'])} units · {clean_number(row['height_stories'])} stories",
        f"Owner: {owner}",
        f"Architect: {architect}",
    ]
    av = assessed_line(row)
    if av:
        lines.append(av)
    return "\n".join(lines)


def visible_label_name(row):
    architect = clean(row["architect"])
    owner = clean(row["owner_current"])
    developer = clean(row["developer"])
    credits = []
    if owner != "n/a":
        credits.append(f"Owner: {owner}")
    if developer != "n/a":
        credits.append(f"Dev: {developer}")
    if architect != "n/a":
        credits.append(f"Arch: {architect}")
    if not credits:
        credits.append("Owner/Dev/Arch: n/a")
    return "\n".join(
        [
            clean(row["address_display"]) + " ",
            f"{clean_number(row['total_units'])} units · {clean_number(row['height_stories'])} stories",
            *credits,
        ]
    )


def placemark(name, description, lon, lat, alt, style_url):
    return f"""
    <Placemark>
      <name>{html.escape(name)}</name>
      <description><![CDATA[{html.escape(description).replace(chr(10), '<br/>')}]]></description>
      <styleUrl>{style_url}</styleUrl>
      <Point>
        <altitudeMode>relativeToGround</altitudeMode>
        <coordinates>{lon:.10f},{lat:.10f},{alt:.1f}</coordinates>
      </Point>
    </Placemark>
"""


def generate():
    route = parse_controls()
    geom = parse_geometry_heights()
    rows = project_rows()

    roof_marks = []
    side_marks = []
    for row in rows:
        address_upper = (row["address_display"] or "").upper()
        nums = re.findall(r"\d+", row["address_display"] or "")
        street_no = nums[0] if nums else None
        street = "VIRGINIA" if "VIRGINIA" in address_upper else "SHATTUCK"
        g = geom.get((street_no, street))
        center_lon = g["center_lon"] if g else row["longitude"]
        center_lat = g["center_lat"] if g else row["latitude"]
        roof_m = g["roof_m"] if g else ((row["height_feet"] or 90) * 0.3048)
        text = label_text(row)
        short_name = f"{clean(row['address_display'])} · {clean(row['total_units'])}u"
        visible_name = visible_label_name(row)

        roof_alt = max(roof_m + 8, 25)
        roof_marks.append(placemark(short_name, text, center_lon, center_lat, roof_alt, "#roof_label"))

        street_lon, street_lat, dist = closest_point_on_route(center_lon, center_lat, route)
        # Put side/floating label 70% of the way from building center toward the street centerline.
        side_lon = center_lon + 0.70 * (street_lon - center_lon)
        side_lat = center_lat + 0.70 * (street_lat - center_lat)
        side_marks.append(placemark(visible_name, text, side_lon, side_lat, SIDE_LABEL_ALT_M, "#side_label"))

    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>Shattuck building label overlay - roof and side-offset v5</name>
  <Style id="roof_label">
    <IconStyle><scale>0</scale></IconStyle>
    <LabelStyle><color>ffffffff</color><scale>0.85</scale></LabelStyle>
  </Style>
  <Style id="side_label">
    <IconStyle><scale>0</scale></IconStyle>
    <LabelStyle><color>ff00ffff</color><scale>1.05</scale></LabelStyle>
  </Style>
  <Folder>
    <name>Roof center labels - white</name>
    <visibility>0</visibility>
{''.join(roof_marks)}
  </Folder>
  <Folder>
    <name>Street-side floating labels - yellow - 15m AGL</name>
    <visibility>1</visibility>
{''.join(side_marks)}
  </Folder>
</Document>
</kml>
'''
    OUT_PATH.write_text(kml, encoding="utf-8")
    print(f"Wrote: {OUT_PATH}")
    print(f"Projects labeled: {len(rows)}")
    print("First labels:")
    for row in rows[:8]:
        print(f"  - {row['address_display']}: {row['total_units']} units, {row['height_stories']} stories")


if __name__ == "__main__":
    generate()
