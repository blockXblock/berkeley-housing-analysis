#!/usr/bin/env python3
"""build_tour_map_gallery.py — the /tours/ page: every flyover on one map, each opening beside a
live map and Street View (docs/tours/streetview.html).

Reads the timelines that tour_timeline.py wrote (docs/tours/streetview/*.json), so a tour appears
here only once its sync has been checked against its recording. Writes docs/tours/index.html and
stamps the display titles into each timeline so the tour page shows the same name.

  python scripts/tours/build_tour_map_gallery.py
"""
import html, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
TL = ROOT / "docs/tours/streetview"
OUT = ROOT / "docs/tours/index.html"

# Display order and words. Titles match the home page's video titles.
TOURS = [
    ("shattuck-s2n-path", "Shattuck Avenue, south to north", "Woolsey Street through downtown to Rose, past the towers."),
    ("Shattuck-centerline-flight-with-2190-and-2276-orbits", "Shattuck Avenue, north to south (June 2026)",
     "Every project entitled or in review in June 2026, Rose Street to the Oakland line."),
    ("telegraph-s2n", "Telegraph Avenue, Woolsey to UC Berkeley", "From the Oakland line up past Ashby and Dwight to the campus."),
    ("university-880-uc", "University Avenue, the Harbor to UC Berkeley", "The full length, from the Berkeley Harbor to Oxford Street."),
    ("san-pablo-n2s", "San Pablo Avenue, north to south", "2.3 miles of west Berkeley, Albany line to Oakland border."),
    ("bancroft-e2w", "Bancroft Way, Piedmont to Aquatic Park", "From the campus edge through downtown to the bay."),
    ("durant-w2e", "Durant Avenue, Milvia to Piedmont", "One block south of campus, west to east."),
    ("uc-dormitories", "UC Berkeley student housing", "5,010 beds in four projects."),
    ("tour-private-pipeline-over-200-units-2026-05-16", "Berkeley's 17 largest private projects", "Every private project planned with more than 200 homes."),
]
COLORS = ["#c0392b", "#8e44ad", "#1f5fbf", "#16a085", "#d35400", "#2c3e50", "#b7950b", "#27ae60", "#7f8c8d"]


def main():
    items = []
    for (tid, title, blurb), colour in zip(TOURS, COLORS):
        f = TL / f"{tid}.json"
        if not f.exists():
            print(f"skip {tid}: no checked timeline")
            continue
        d = json.loads(f.read_text())
        d["title"] = title
        f.write_text(json.dumps(d, separators=(",", ":")))
        route = [[k[1], k[2]] for k in d["keyframes"] if k[4] <= 60]
        route = route[::max(1, len(route) // 120)]           # enough points to draw, small enough to embed
        items.append({"id": tid, "title": title, "blurb": blurb, "yt": d["youtube"], "colour": colour,
                      "minutes": round(d["duration_s"] / 60, 1), "approx": d.get("approximate", False),
                      "route": [[round(a, 5), round(b, 5)] for a, b in route]})

    cards = []
    for i, it in enumerate(items):
        badge = '<span class="badge">sync approximate</span>' if it["approx"] else ""
        cards.append(f'''
    <a class="card" href="streetview.html?tour={html.escape(it["id"])}" data-i="{i}" style="--c:{it["colour"]}">
      <div class="thumb"><img src="../img/thumbs/{it["yt"]}.jpg" alt="" loading="lazy"><span class="len">{it["minutes"]} min</span></div>
      <div class="body"><h2>{html.escape(it["title"])}</h2><p>{html.escape(it["blurb"])}</p>
        <span class="cta">Fly it with the map and Street View &rarr;</span>{badge}</div>
    </a>''')

    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Berkeley Flyovers</title>
<meta name="description" content="Fly Berkeley's housing future street by street, with a live map and Street View beside every flyover.">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  :root {{ --ink:#2b2620; --paper:#f6f0e1; --muted:#6b5d4a; --card:#fffaf0; --line:#ddd2b8; }}
  @media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --ink:#efe8d8; --paper:#1d1a16; --muted:#b5a88f; --card:#28241e; --line:#3a342b; }} }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink); font-family:Georgia,"Times New Roman",serif; }}
  header {{ max-width:1200px; margin:0 auto; padding:28px 16px 12px; }}
  header a.home {{ color:var(--muted); font-size:.95rem; text-decoration:none; }}
  h1 {{ font-size:clamp(1.8rem, 4vw, 2.8rem); margin:.3rem 0 .4rem; line-height:1.1; }}
  .lede {{ font-size:clamp(1rem, 2vw, 1.2rem); color:var(--muted); max-width:46rem; margin:0; }}
  #map {{ height:min(62vh, 560px); max-width:1200px; margin:16px auto; border:1px solid var(--line); }}
  .grid {{ max-width:1200px; margin:0 auto 40px; padding:0 16px; display:grid; gap:18px;
           grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); }}
  .card {{ display:flex; flex-direction:column; background:var(--card); border:1px solid var(--line);
           border-top:6px solid var(--c); color:inherit; text-decoration:none; border-radius:6px; overflow:hidden;
           transition:transform .15s, box-shadow .15s; }}
  .card:hover, .card:focus, .card.on {{ transform:translateY(-3px); box-shadow:0 8px 22px rgba(0,0,0,.15); }}
  .thumb {{ position:relative; aspect-ratio:16/9; background:#000; }}
  .thumb img {{ width:100%; height:100%; object-fit:cover; display:block; }}
  .len {{ position:absolute; right:8px; bottom:8px; background:rgba(0,0,0,.75); color:#fff; font-size:.85rem; padding:2px 7px; border-radius:3px; }}
  .body {{ padding:12px 14px 14px; display:flex; flex-direction:column; gap:6px; flex:1; }}
  .body h2 {{ font-size:1.15rem; margin:0; }}
  .body p {{ margin:0; color:var(--muted); font-size:.95rem; flex:1; }}
  .cta {{ color:var(--c); font-weight:bold; }}
  .badge {{ align-self:flex-start; font-size:.75rem; border:1px solid var(--muted); color:var(--muted); padding:1px 6px; border-radius:10px; }}
  footer {{ max-width:1200px; margin:0 auto 30px; padding:0 16px; color:var(--muted); font-size:.85rem; }}
</style>
</head>
<body>
<header>
  <a class="home" href="../">&larr; berkeleybuild.com</a>
  <h1>Fly Berkeley&rsquo;s future, street by street</h1>
  <p class="lede">Each flyover plays beside a live map and Google Street View: watch the buildings planned for a street
    while you see the street as it stands today. Pick a route on the map or below.</p>
</header>
<div id="map"></div>
<div class="grid">{"".join(cards)}
</div>
<footer>Flyovers are recorded in Google Earth from the project's 3D model of planned buildings. Map © OpenStreetMap contributors.</footer>
<script>
const T = {json.dumps(items, separators=(",", ":"))};
const map = L.map("map", {{ scrollWheelZoom: false }});
L.tileLayer("https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{ maxZoom: 19, attribution: "© OpenStreetMap contributors" }}).addTo(map);
const lines = [], cards = document.querySelectorAll(".card");
function light(i, on) {{
  lines[i].setStyle({{ weight: on ? 9 : 5, opacity: on ? 1 : 0.8 }}); if (on) lines[i].bringToFront();
  cards[i].classList.toggle("on", on);
}}
T.forEach((t, i) => {{
  const l = L.polyline(t.route, {{ color: t.colour, weight: 5, opacity: 0.8 }}).addTo(map)
    .bindTooltip(t.title, {{ sticky: true }});
  l.on("mouseover", () => light(i, true)); l.on("mouseout", () => light(i, false));
  l.on("click", () => location.href = "streetview.html?tour=" + encodeURIComponent(t.id));
  L.circleMarker(t.route[0], {{ radius: 5, color: t.colour, fillColor: "#fff", fillOpacity: 1, weight: 3 }}).addTo(map);
  lines.push(l);
  cards[i].addEventListener("mouseenter", () => light(i, true));
  cards[i].addEventListener("mouseleave", () => light(i, false));
}});
map.fitBounds(L.featureGroup(lines).getBounds().pad(0.05));
</script>
</body>
</html>
'''
    OUT.write_text(page)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(items)} tours")


if __name__ == "__main__":
    main()
