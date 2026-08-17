#!/usr/bin/env python3
"""build_landmark_kml.py — time-animated KML of Berkeley's landmark buildings by year built.

Each City-designated landmark becomes a placemark carrying a TimeSpan that BEGINS at its true build year
(name_year, the landmark-list date that corrects the assessor) with no end — so in Google Earth the TIME
SLIDER animates the landmarks appearing chronologically and STAYING (a cumulative build-out, exactly like
the year-by-year web map), in 3D, with Street View / historical aerial imagery available at each building.
No API key, no cost.

Source: data/reference/berkeley_landmark_build_dates.csv (build year + designation) + databases/berkeley.db
(lat/lon by canonical APN).  Output: kml/timeline/berkeley_landmarks_buildout.kml (tracked KML source).
Open it in Google Earth (Pro: File > Open; Earth web: New project > Import KML), then drag the time slider.
"""
import sqlite3, sys, os, html
import pandas as pd
sys.path.insert(0, "scripts")
from housing_rules import to_canonical_apn

OUT = "kml/timeline/berkeley_landmarks_buildout.kml"
GOLD = "ff4fc4fe"   # KML aabbggrr for #fec44f (matches the web map's gold)

def canon(a):
    try: return to_canonical_apn(a, "alameda") if pd.notna(a) else None
    except Exception: return None

def main():
    lm = pd.read_csv("data/reference/berkeley_landmark_build_dates.csv")
    lm = lm[lm.apn.notna() & lm.name_year.notna()].copy()
    lm["capn"] = lm.apn.map(canon)

    db = sqlite3.connect("databases/berkeley.db")
    p = pd.read_sql("SELECT APN, Latitude, Longitude FROM parcels", db)
    p["capn"] = p.APN.map(canon)
    for c in ["Latitude", "Longitude"]:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    p = p.dropna(subset=["capn"]).drop_duplicates("capn")

    m = (lm.merge(p[["capn", "Latitude", "Longitude"]], on="capn", how="inner")
           .dropna(subset=["Latitude", "Longitude"]).sort_values("name_year"))
    print(f"landmarks with year + coords: {len(m)}  (years {int(m.name_year.min())}–{int(m.name_year.max())})")

    pms = []
    for _, r in m.iterrows():
        yr = int(r.name_year)
        addr = html.escape(str(r.address))
        desig = html.escape(str(r.designated)) if pd.notna(r.designated) else "—"
        typ = html.escape(str(r.lm_type)) if pd.notna(r.lm_type) else ""
        # description is CDATA (raw HTML ok); name/others are XML-escaped
        desc = (f"<b>{addr}</b><br>Built <b>{yr}</b> (City landmark date)"
                f"<br>Designated {desig} &middot; {typ}")
        pms.append(
            "  <Placemark>\n"
            f"    <name>{addr} ({yr})</name>\n"
            f"    <description><![CDATA[{desc}]]></description>\n"
            f"    <TimeSpan><begin>{yr:04d}-01-01T00:00:00Z</begin></TimeSpan>\n"
            "    <styleUrl>#lm</styleUrl>\n"
            f"    <Point><coordinates>{r.Longitude:.6f},{r.Latitude:.6f},0</coordinates></Point>\n"
            "  </Placemark>")

    kml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n'
        '  <name>Berkeley Built — Landmark Buildings by Year</name>\n'
        f'  <description><![CDATA[{len(m)} City-designated landmarks, each carrying a TimeSpan that begins at '
        'its true build year. Drag the Google Earth TIME SLIDER (top toolbar) to watch the landmarks appear '
        'chronologically and accumulate; click any placemark, then use Street View / 3D / historical imagery.]]></description>\n'
        f'  <Style id="lm">\n'
        f'    <IconStyle><scale>0.9</scale><color>{GOLD}</color>'
        '<Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle>\n'
        '    <LabelStyle><scale>0.7</scale></LabelStyle>\n  </Style>\n'
        + "\n".join(pms) +
        "\n</Document>\n</kml>\n")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(kml)
    print(f"wrote {OUT}  ({len(pms)} placemarks, {round(len(kml)/1024)} KB)")

if __name__ == "__main__":
    main()
