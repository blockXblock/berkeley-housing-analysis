#!/usr/bin/env python3
"""build_tour_map_gallery.py — the /tours/ page: every flyover on one map, each opening beside a
live map and Street View (docs/tours/streetview.html).

Reads the timelines that tour_timeline.py wrote (docs/tours/streetview/*.json), so a tour appears
here only once its sync has been checked against its recording. Writes docs/tours/index.html and
stamps the display titles into each timeline so the tour page shows the same name.

Also writes docs/tours/play-all.html: every flyover in this order, back to back, full screen, for a
presentation (John, 2026-10-24). It plays self-hosted copies on R2 (R2_VIDEOS/<tour id>-1080.mp4 and
-720.mp4), NOT YouTube: an embed starts each video on Auto quality (often 240p) and a page cannot force
HD. A tour with no R2 copy is left out of play-all, with a warning, until one is uploaded.

  python scripts/tours/build_tour_map_gallery.py
"""
import html, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
TL = ROOT / "docs/tours/streetview"
OUT = ROOT / "docs/tours/index.html"
PLAY_ALL = ROOT / "docs/tours/play-all.html"
R2_VIDEOS = "https://docs.berkeleybuild.com/videos"
# tours with both encodes uploaded to R2 videos/ (keys <id>-1080.mp4, <id>-720.mp4). Read from the home page's
# data-mp4 attributes, which publish_video.py writes only after it has uploaded and checked both files. A hand-kept
# set here went stale the first time a video was published without editing it. Not the catalog: a
# build_tours_manifest.py regeneration re-seeds the older videos' "video" field and would drop an r2 key.
ON_R2 = set(re.findall(r'data-mp4="' + re.escape(R2_VIDEOS) + r'/([^"]+)"', (ROOT / "docs/index.html").read_text()))

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
    ("panoramic-kennedy-legacy-slow20", "Patrick Kennedy & Panoramic Interests, 35 years",
     "Every Berkeley building by Panoramic Interests, 1990-2028: 23 buildings, 699 homes."),
    # John, 2026-10-24: title as he gave it, and kept: "Seven Base Stories" refers to a City Council idea to zone
    # all commercial at 7 stories, not to the PC's 5-story base. Do not "correct" it. HYPOTHETICAL buildings, not projects: the 7-story 5-over-2 scenario
    # folder of kml/geometry/college-opportunity-sites.kml, flown by kml/tours/elmwood-orbit.kml.
    ("elmwood-orbit", "Elmwood Future At Seven Base Stories",
     "Hypothetical: eight College Avenue sites drawn at 7 stories, a density-bonus scenario. Not proposals."),
]
COLORS = ["#c0392b", "#8e44ad", "#1f5fbf", "#16a085", "#d35400", "#2c3e50", "#b7950b", "#27ae60", "#7f8c8d", "#6d4c41", "#c2185b"]


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
        aerial = len(route) < 2                               # flown entirely from the air: draw the flight path
        if aerial:
            route = [[k[1], k[2]] for k in d["keyframes"]]
        route = route[::max(1, len(route) // 120)]           # enough points to draw, small enough to embed
        items.append({"id": tid, "title": title, "blurb": blurb, "yt": d["youtube"], "colour": colour,
                      "minutes": round(d["duration_s"] / 60, 1), "approx": d.get("approximate", False), "aerial": aerial,
                      "route": [[round(a, 5), round(b, 5)] for a, b in route]})

    cards = []
    for i, it in enumerate(items):
        badge = '<span class="badge">sync approximate</span>' if it["approx"] else ""
        cards.append(f'''
    <a class="card" href="streetview.html?tour={html.escape(it["id"])}" data-i="{i}" style="--c:{it["colour"]}">
      <div class="thumb"><img src="../img/tourposters/{html.escape(it["id"])}.jpg" alt="" loading="lazy"><span class="len">{it["minutes"]} min</span></div>
      <div class="body"><h2>{html.escape(it["title"])}</h2><p>{html.escape(it["blurb"])}</p>
        <span class="cta">Fly it with the map and Street View &rarr;</span>{badge}</div>
    </a>''')

    play = [it for it in items if it["id"] in ON_R2]
    for it in items:
        if it["id"] not in ON_R2:
            print(f"play-all: {it['id']} has no R2 copy, left out")
    PLAY_ALL.write_text(play_all_page(play))
    print(f"wrote {PLAY_ALL.relative_to(ROOT)}: {len(play)} flyovers")

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
  .hero {{ position:relative; min-height:clamp(260px, 42vh, 420px); display:flex; align-items:flex-end; overflow:hidden; background:#000; }}
  .hero video, .hero img.still {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
  .hero::after {{ content:""; position:absolute; inset:0; background:linear-gradient(to top, rgba(0,0,0,.78), rgba(0,0,0,.1) 60%); }}
  .hero .in {{ position:relative; z-index:1; max-width:1200px; width:100%; margin:0 auto; padding:24px 16px; color:#fff; }}
  .hero a.home {{ position:absolute; top:14px; left:16px; z-index:2; color:#fff; background:rgba(0,0,0,.55); padding:3px 9px; border-radius:4px; text-decoration:none; }}
  .hero .lede {{ color:#f1ece0; }}
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
  .playall {{ max-width:1200px; margin:0 auto 26px; padding:0 16px; font-size:1.15rem; }}
  .playall a {{ color:var(--ink); font-weight:bold; }}
  footer {{ max-width:1200px; margin:0 auto 30px; padding:0 16px; color:var(--muted); font-size:.85rem; }}
</style>
</head>
<body>
<section class="hero">
  <video id="loop" muted loop playsinline preload="metadata" poster="../videos/hero-shattuck-loop.jpg">
    <source src="../videos/hero-shattuck-loop.mp4" type="video/mp4"></video>
  <a class="home" href="../">&larr; berkeleybuild.com</a>
  <div class="in">
    <h1>Fly Berkeley&rsquo;s future, street by street</h1>
    <p class="lede">Each flyover plays beside a live map and Google Street View: watch the buildings planned for a street
      while you see the street as it stands today. Pick a route on the map or below.</p>
  </div>
</section>
<div id="map"></div>
<div class="grid">{"".join(cards)}
</div>
<p class="playall"><a href="play-all.html">&#9654; Play all the flyovers, one after another, full screen</a></p>
<footer>Flyovers are recorded in Google Earth from the project's 3D model of planned buildings. Map © OpenStreetMap contributors.</footer>
<script>
const T = {json.dumps(items, separators=(",", ":"))};
const map = L.map("map", {{ scrollWheelZoom: false }});
L.tileLayer("https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{ maxZoom: 19, attribution: "© OpenStreetMap contributors" }}).addTo(map);
const lines = [], cards = document.querySelectorAll(".card");
map.fitBounds(L.latLngBounds(T.flatMap(t => t.route)).pad(0.05));   // a view first: layers project against it
function light(i, on) {{
  const a = T[i].aerial;
  lines[i].setStyle({{ weight: on ? (a ? 5 : 9) : (a ? 3 : 5), opacity: on ? 1 : (a ? 0.5 : 0.8) }}); if (on) lines[i].bringToFront();
  cards[i].classList.toggle("on", on);
}}
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const loop = document.getElementById("loop");
if (!still) loop.play().catch(() => {{}});
T.forEach((t, i) => {{
  const l = L.polyline(still ? t.route : t.route.slice(0, 2), {{ color: t.colour, weight: t.aerial ? 3 : 5, opacity: t.aerial ? 0.5 : 0.8, dashArray: t.aerial ? "2 8" : null }}).addTo(map)
    .bindTooltip(t.title, {{ sticky: true }});
  l.on("mouseover", () => light(i, true)); l.on("mouseout", () => light(i, false));
  l.on("click", () => location.href = "streetview.html?tour=" + encodeURIComponent(t.id));
  L.circleMarker(t.route[0], {{ radius: 5, color: t.colour, fillColor: "#fff", fillOpacity: 1, weight: 3 }}).addTo(map);
  lines.push(l);
  cards[i].addEventListener("mouseenter", () => light(i, true));
  cards[i].addEventListener("mouseleave", () => light(i, false));
}});
// draw each route along its street, one after another, the first time the map comes into view
function drawRoutes() {{
  const DUR = 1400, GAP = 350;
  T.forEach((t, i) => setTimeout(() => {{
    const t0 = performance.now();
    (function step(now) {{
      const f = Math.min(1, (now - t0) / DUR), n = Math.max(2, Math.round(f * t.route.length));
      lines[i].setLatLngs(t.route.slice(0, n));
      if (f < 1) requestAnimationFrame(step);
    }})(t0);
  }}, i * GAP));
}}
let drawn = false;
const whole = () => {{ drawn = true; T.forEach((t, i) => lines[i].setLatLngs(t.route)); }};
if (!still) new IntersectionObserver((es, o) => {{ if (es[0].isIntersecting && !drawn) {{ drawn = true; drawRoutes(); o.disconnect();
  setTimeout(whole, T.length * 350 + 2500); }} }},   // safety net if animation frames stall
  {{ threshold: 0.25 }}).observe(document.getElementById("map"));
setTimeout(() => {{ if (!drawn) whole(); }}, 6000);   // never leave the map empty, whatever the browser does
</script>
</body>
</html>
'''
    OUT.write_text(page)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(items)} tours")


def play_all_page(items):
    """One full-screen player that runs the list back to back. The CONTAINER goes full screen, not the
    <video>, so swapping the source between flyovers never drops out of full screen."""
    vids = [{"id": it["id"], "title": it["title"], "min": it["minutes"]} for it in items]
    rows = "".join(f'<li><button data-i="{i}">{html.escape(v["title"])} <span>{v["min"]} min</span></button></li>'
                   for i, v in enumerate(vids))
    total = round(sum(v["min"] for v in vids))
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Play all flyovers · BerkeleyBuild</title>
<meta name="description" content="Every BerkeleyBuild flyover, back to back, full screen, in HD.">
<style>
  * {{ box-sizing:border-box; }}
  html, body {{ margin:0; height:100%; background:#000; color:#f1ece0; font-family:Georgia,"Times New Roman",serif; }}
  #stage {{ position:fixed; inset:0; background:#000; }}
  #stage video {{ width:100%; height:100%; object-fit:contain; background:#000; display:block; }}
  #stage.idle, #stage.idle * {{ cursor:none; }}
  #title {{ position:absolute; left:4vw; bottom:9vh; font-size:clamp(1.3rem, 3.2vw, 2.6rem); font-weight:bold; color:#fff;
           text-shadow:0 2px 12px rgba(0,0,0,.9); opacity:0; transition:opacity .8s; pointer-events:none; max-width:80vw; }}
  #title.on {{ opacity:1; }}
  #title small {{ display:block; font-size:.5em; font-weight:normal; opacity:.85; margin-top:.3em; }}
  #bar {{ position:absolute; left:0; right:0; top:0; display:flex; gap:10px; align-items:center; padding:10px 14px;
         background:linear-gradient(rgba(0,0,0,.75), rgba(0,0,0,0)); transition:opacity .4s; }}
  #stage.idle #bar {{ opacity:0; }}
  #bar a, #bar button {{ color:#fff; background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.3); border-radius:5px;
                        padding:5px 11px; font:inherit; font-size:.95rem; text-decoration:none; cursor:pointer; }}
  #bar .n {{ margin-left:auto; font-size:.95rem; opacity:.85; }}
  #start {{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center;
           gap:18px; padding:20px; background:radial-gradient(#1d1a16, #000); text-align:center; overflow:auto; }}
  #start[hidden] {{ display:none; }}   /* display:flex above would otherwise beat the hidden attribute */
  #start h1 {{ margin:0; font-size:clamp(1.6rem, 4vw, 2.8rem); }}
  #start p {{ margin:0; color:#b5a88f; max-width:40rem; }}
  #go {{ font:inherit; font-size:1.3rem; font-weight:bold; padding:14px 30px; border-radius:8px; border:0; background:#ffd166;
        color:#1d1a16; cursor:pointer; }}
  #start ol {{ list-style:none; padding:0; margin:0; columns:2 18rem; column-gap:24px; text-align:left; }}
  #start li button {{ background:none; border:0; color:#efe8d8; font:inherit; padding:3px 0; cursor:pointer; text-align:left; }}
  #start li button:hover {{ color:#ffd166; }}
  #start li span {{ color:#b5a88f; font-size:.85em; }}
  #start .keys {{ font-size:.85rem; }}
</style>
</head>
<body>
<div id="stage">
  <video id="v" playsinline muted preload="auto"></video>
  <div id="title"></div>
  <div id="bar"><a href="./">&larr; Tours</a><button id="prev" aria-label="Previous flyover">&#9664;&#9664;</button>
    <button id="pp" aria-label="Pause">&#10074;&#10074;</button><button id="next" aria-label="Next flyover">&#9654;&#9654;</button>
    <button id="fs">Full screen</button><span class="n" id="n"></span></div>
  <div id="start">
    <h1>All {len(vids)} flyovers, back to back</h1>
    <p>About {total} minutes in HD, one after another, full screen. Or start from any flyover in the list.</p>
    <button id="go">&#9654; Play all</button>
    <ol>{rows}</ol>
    <p class="keys">Keys: &rarr; next &middot; &larr; previous &middot; space pause &middot; F full screen &middot; Esc leave full screen</p>
  </div>
</div>
<script>
const V = {json.dumps(vids, separators=(",", ":"))};
const BASE = {json.dumps(R2_VIDEOS)};
// phones (short side under 600 CSS px) get 720p; tablets and computers 1080p, as on the home page
const RES = Math.min(screen.width, screen.height) >= 600 ? "-1080.mp4" : "-720.mp4";
const stage = document.getElementById("stage"), v = document.getElementById("v"), title = document.getElementById("title");
let i = 0, hideTitle, idle;
function load(k, play) {{
  i = (k + V.length) % V.length;
  v.src = BASE + "/" + V[i].id + RES;
  document.getElementById("n").textContent = (i + 1) + " / " + V.length;
  title.innerHTML = V[i].title.replace(/&/g, "&amp;").replace(/</g, "&lt;") + "<small>" + (i + 1) + " of " + V.length + "</small>";
  title.classList.add("on"); clearTimeout(hideTitle); hideTitle = setTimeout(() => title.classList.remove("on"), 5000);
  if (play) v.play().catch(() => {{}});
  // warm the next file so the cut is quick
  const nx = V[(i + 1) % V.length]; fetch(BASE + "/" + nx.id + RES, {{ headers: {{ Range: "bytes=0-2000000" }} }}).catch(() => {{}});
}}
function full() {{ if (!document.fullscreenElement && stage.requestFullscreen) stage.requestFullscreen().catch(() => {{}}); }}
function begin(k) {{ document.getElementById("start").hidden = true; full(); load(k, true); wake(); }}
document.getElementById("go").onclick = () => begin(0);
document.querySelectorAll("#start li button").forEach(b => b.onclick = () => begin(+b.dataset.i));
v.addEventListener("ended", () => {{ if (i < V.length - 1) load(i + 1, true); else {{ document.exitFullscreen?.().catch(() => {{}}); document.getElementById("start").hidden = false; }} }});
const pp = document.getElementById("pp");
const toggle = () => v.paused ? v.play() : v.pause();
v.addEventListener("play", () => {{ pp.innerHTML = "&#10074;&#10074;"; pp.setAttribute("aria-label", "Pause"); }});
v.addEventListener("pause", () => {{ pp.innerHTML = "&#9654;"; pp.setAttribute("aria-label", "Play"); }});
pp.onclick = toggle;
document.getElementById("prev").onclick = () => load(i - 1, true);
document.getElementById("next").onclick = () => load(i + 1, true);
document.getElementById("fs").onclick = () => document.fullscreenElement ? document.exitFullscreen() : full();
document.addEventListener("keydown", e => {{
  if (!document.getElementById("start").hidden) return;
  if (e.key === "ArrowRight") load(i + 1, true);
  else if (e.key === "ArrowLeft") load(i - 1, true);
  else if (e.key === " ") {{ e.preventDefault(); toggle(); }}
  else if (e.key === "f" || e.key === "F") full();
  else return;
  wake();
}});
// hide the bar and the cursor after 3 seconds without the mouse
function wake() {{ stage.classList.remove("idle"); clearTimeout(idle); idle = setTimeout(() => stage.classList.add("idle"), 3000); }}
stage.addEventListener("mousemove", wake); stage.addEventListener("touchstart", wake);
</script>
</body>
</html>
'''


if __name__ == "__main__":
    main()
