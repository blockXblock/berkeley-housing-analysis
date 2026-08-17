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

    # ---- auto-fly gx:Tour: fly decade-by-decade while the globe clock advances (buildings pop in) ----
    m["decade"] = (m.name_year // 10 * 10).astype(int)
    clon0, clat0 = float(m.Longitude.mean()), float(m.Latitude.mean())
    ymax = int(m.name_year.max())

    def flyto(lon, lat, rng, tilt, heading, year, dur, mode="bounce"):
        return (f'      <gx:FlyTo><gx:duration>{dur}</gx:duration><gx:flyToMode>{mode}</gx:flyToMode>\n'
                f'        <LookAt><longitude>{lon:.6f}</longitude><latitude>{lat:.6f}</latitude><altitude>0</altitude>'
                f'<heading>{heading}</heading><tilt>{tilt}</tilt><range>{rng}</range>'
                '<altitudeMode>relativeToGround</altitudeMode>'
                f'<gx:TimeStamp><when>{year:04d}-07-01T00:00:00Z</when></gx:TimeStamp></LookAt>\n'
                '      </gx:FlyTo>')
    wait = lambda d: f'      <gx:Wait><gx:duration>{d}</gx:duration></gx:Wait>'

    fly = [flyto(clon0, clat0, 13000, 45, 0, 1850, 3), wait(1.5)]           # open: empty Berkeley, 1850
    for i, dec in enumerate(sorted(m.decade.unique())):                     # one stop per decade with landmarks
        g = m[m.decade == dec]
        fly += [flyto(float(g.Longitude.mean()), float(g.Latitude.mean()), 2800, 58,
                      (i * 25) % 360, int(min(dec + 9, ymax)), 4.5), wait(2.5)]
    fly += [flyto(clon0, clat0, 13000, 45, 0, ymax, 4.5), wait(3)]          # close: pull back, all shown
    tour = ('  <gx:Tour>\n    <name>▶ Berkeley landmarks build-out (auto-fly)</name>\n'
            '    <gx:Playlist>\n' + "\n".join(fly) + '\n    </gx:Playlist>\n  </gx:Tour>\n')

    kml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">\n<Document>\n'
        '  <name>Berkeley Built — Landmark Buildings by Year</name>\n'
        f'  <description><![CDATA[{len(m)} City-designated landmarks, each carrying a TimeSpan that begins at its '
        'true build year. Play the tour "▶ Berkeley landmarks build-out" (double-click it in the Places panel) for a '
        'hands-free decade-by-decade flight while the buildings appear, or drag the TIME SLIDER yourself; click any '
        'placemark for Street View / 3D / historical imagery.]]></description>\n'
        f'  <Style id="lm">\n'
        f'    <IconStyle><scale>0.9</scale><color>{GOLD}</color>'
        '<Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle>\n'
        '    <LabelStyle><scale>0.7</scale></LabelStyle>\n  </Style>\n'
        + tour
        + "\n".join(pms) +
        "\n</Document>\n</kml>\n")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(kml)
    print(f"wrote {OUT}  ({len(pms)} placemarks, {round(len(kml)/1024)} KB)")

if __name__ == "__main__":
    main()
