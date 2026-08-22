#!/usr/bin/env python3
"""gen_elmwood_pinmap.py — participatory 'Reimagine Elmwood' map (Artifact live-doc prototype).

Renders the Elmwood commercial district as a self-contained inline SVG (no CDN, no tiles — Artifact CSP
safe): faint neighbourhood context dots + the commercial parcels as polygons (underused ones, Imps<Land,
flagged gold). The shell is an Artifact LIVE DOC: an editor double-clicks a spot, writes an idea, and the
pin is appended to the shared document — every editor sees every pin. Per-viewer draft UI lives in
<artifact-local>. Publish with capabilities:{artifact:{}}.

Output: scratch/2026-08-16/elmwood_pinmap.html
"""
import geopandas as gpd, pandas as pd, sqlite3, math, warnings, os
warnings.filterwarnings("ignore")

def main():
    tp = gpd.read_file("data/raw/berkeley_taxparcels_2026-08-12.geojson")[["APN", "UseCode", "geometry"]]
    nbh = gpd.read_file("data/reference/berkeley_neighborhoods.geojson").to_crs(tp.crs)
    el = nbh[nbh.Name.astype(str).str.contains("lmwood", case=False)].dissolve().geometry.iloc[0]
    elm = tp[tp.geometry.centroid.within(el)].copy().to_crs(4326)
    elm["uc1"] = elm.UseCode.astype(str).str.lstrip("0").str[:1]
    db = sqlite3.connect("databases/berkeley.db")
    info = pd.read_sql("SELECT APN,Land,Imps,SitusStree,SitusStr_1 FROM parcels", db)
    for c in ["Land", "Imps"]:
        info[c] = pd.to_numeric(info[c], errors="coerce")
    elm = elm.merge(info, on="APN", how="left")
    elm["addr"] = (elm.SitusStree.fillna("").astype(str).str.strip() + " "
                   + elm.SitusStr_1.fillna("").astype(str).str.strip()).str.strip()
    comm = elm[elm.uc1 == "3"].copy()

    # projection: lon/lat -> SVG viewBox 0..W x 0..H, mercator-ish, 4% pad
    b = elm.total_bounds
    W = 1000.0; cosL = math.cos(math.radians((b[1] + b[3]) / 2))
    H = round(W * (b[3] - b[1]) / ((b[2] - b[0]) * cosL), 1)
    pad = 0.04 * W
    def X(lon): return round(pad + (lon - b[0]) / (b[2] - b[0]) * (W - 2 * pad), 1)
    def Y(lat): return round(pad + (b[3] - lat) / (b[3] - b[1]) * (H - 2 * pad), 1)

    # faint context dots: every Elmwood parcel centroid
    ctx = "".join(f'<circle cx="{X(c.x)}" cy="{Y(c.y)}" r="1.4"/>'
                  for c in elm.geometry.centroid)
    # commercial parcels as polygons; gold if underused (Imps<Land or Imps==0)
    polys = []
    for _, r in comm.iterrows():
        g = r.geometry if r.geometry.geom_type == "Polygon" else list(r.geometry.geoms)[0]
        pts = " ".join(f"{X(x)},{Y(y)}" for x, y in g.exterior.coords)
        under = (pd.notna(r.Imps) and pd.notna(r.Land) and r.Imps < r.Land) or (r.Imps == 0)
        polys.append(f'<polygon points="{pts}" class="{"under" if under else "comm"}"><title>'
                     f'{r.addr}{" · underused (land &gt; building)" if under else ""}</title></polygon>')
    parcels = "".join(polys)
    # street labels at median parcel position per street (top corridors)
    comm["street"] = comm.SitusStr_1.fillna("").astype(str).str.strip()
    labels = ""
    for st, grp in comm.groupby("street"):
        if len(grp) < 4 or not st: continue
        cx = grp.geometry.centroid.x.median(); cy = grp.geometry.centroid.y.median()
        labels += f'<text x="{X(cx)}" y="{Y(cy)}" class="street">{st.title()}</text>'

    n_comm = len(comm); n_under = int(((comm.Imps < comm.Land) | (comm.Imps == 0)).sum())

    html = TEMPLATE.replace("__W__", str(int(W))).replace("__H__", str(int(H))) \
        .replace("__CTX__", ctx).replace("__PARCELS__", parcels).replace("__LABELS__", labels) \
        .replace("__NCOMM__", str(n_comm)).replace("__NUNDER__", str(n_under))
    os.makedirs("scratch/2026-08-16", exist_ok=True)
    open("scratch/2026-08-16/elmwood_pinmap.html", "w").write(html)
    print(f"wrote scratch/2026-08-16/elmwood_pinmap.html ({round(len(html)/1024)} KB) — "
          f"{n_comm} commercial parcels ({n_under} underused), {len(elm)} context dots")


TEMPLATE = r"""<!doctype html>
<title>Reimagine Elmwood</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,500;0,600;1,500&family=Public+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --ground:#eef1ec; --panel:#f8faf6; --ink:#1b2420; --muted:#5c675e; --line:#d5dcd3;
  --green:#1f6f4a; --gold:#bd8a2c; --blue:#2b62a6; --blue-soft:#3f78bd;
  --shadow:0 1px 3px rgba(20,40,30,.12),0 6px 20px rgba(20,40,30,.10);
}
:root:not([data-theme="light"]){ @media (prefers-color-scheme:dark){
  :root{ --ground:#121613; --panel:#1a201c; --ink:#e7ece7; --muted:#93a096; --line:#2b332d;
    --green:#4bb583; --gold:#d7a750; --blue:#6ea3e0; --blue-soft:#5b92d6;
    --shadow:0 1px 3px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);} } }
:root[data-theme="dark"]{ --ground:#121613; --panel:#1a201c; --ink:#e7ece7; --muted:#93a096; --line:#2b332d;
  --green:#4bb583; --gold:#d7a750; --blue:#6ea3e0; --blue-soft:#5b92d6;
  --shadow:0 1px 3px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{background:var(--ground);color:var(--ink);font-family:"Public Sans",system-ui,sans-serif;
  display:flex;flex-direction:column;overscroll-behavior:none}
header{padding:16px 20px 12px;border-bottom:1px solid var(--line);background:var(--panel)}
h1{font-family:"Spectral",Georgia,serif;font-weight:600;font-size:26px;margin:0;letter-spacing:-.01em;color:var(--green);text-wrap:balance}
.sub{margin:4px 0 0;color:var(--muted);font-size:13.5px;max-width:62ch;line-height:1.45}
.meta{display:flex;gap:18px;align-items:baseline;margin-top:10px;flex-wrap:wrap;font-size:12.5px;color:var(--muted)}
.count{font-family:"Spectral",serif;font-size:20px;font-weight:600;color:var(--ink)}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;color:var(--muted);margin-left:auto}
.legend .sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
main{flex:1;position:relative;overflow:hidden}
.mapwrap{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:14px;touch-action:none}
.mapinner{position:relative;width:100%;max-width:min(1100px,calc(__H__ / __W__ * 92vh * (__W__/__H__)));aspect-ratio:__W__/__H__}
svg{width:100%;height:100%;display:block;cursor:crosshair;border-radius:10px;background:var(--panel);box-shadow:var(--shadow)}
svg circle{fill:var(--line)}
svg .comm{fill:color-mix(in srgb,var(--green) 22%,transparent);stroke:var(--green);stroke-width:.8}
svg .under{fill:color-mix(in srgb,var(--gold) 42%,transparent);stroke:var(--gold);stroke-width:1.1}
svg .street{fill:var(--muted);font:600 11px "Public Sans",sans-serif;letter-spacing:.04em;text-anchor:middle;text-transform:uppercase;paint-order:stroke;stroke:var(--panel);stroke-width:3px}
#pins{position:absolute;inset:0;pointer-events:none}
.pin{position:absolute;transform:translate(-50%,-100%);pointer-events:auto;border:0;background:none;cursor:pointer;
  width:22px;height:22px;padding:0;filter:drop-shadow(0 1px 2px rgba(0,0,0,.35))}
.pin::before{content:"";position:absolute;left:50%;top:0;transform:translateX(-50%);width:15px;height:15px;
  border-radius:50% 50% 50% 0;transform:translateX(-50%) rotate(-45deg);background:var(--blue);border:2px solid #fff}
.pin[data-cat="housing"]::before{background:var(--blue)} .pin[data-cat="shops"]::before{background:var(--green)}
.pin[data-cat="open"]::before{background:var(--gold)} .pin[data-cat="transit"]::before{background:#7a52c9}
.pin[data-cat="other"]::before{background:#6b7a70}
.pin .idea{position:absolute;display:none}
.pin:focus-visible{outline:2px solid var(--blue);outline-offset:2px;border-radius:4px}
/* per-viewer overlay UI */
.pop{position:absolute;z-index:20;width:280px;background:var(--panel);border:1px solid var(--line);
  border-radius:12px;box-shadow:var(--shadow);padding:13px;transform:translate(-50%,12px);display:none}
.pop.on{display:block}
.pop label{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:600}
.pop input[type=text]{width:100%;margin-top:6px;padding:9px 10px;border:1px solid var(--line);border-radius:8px;
  background:var(--ground);color:var(--ink);font:inherit;font-size:14px}
.pop input:focus{outline:2px solid var(--green);outline-offset:1px;border-color:var(--green)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.chip{font-size:12px;padding:5px 10px;border-radius:999px;border:1px solid var(--line);background:var(--ground);
  color:var(--ink);cursor:pointer;font-family:inherit}
.chip[aria-pressed=true]{background:var(--green);color:#fff;border-color:var(--green)}
.row{display:flex;gap:8px;justify-content:flex-end;margin-top:4px}
.btn{font:600 13px "Public Sans",sans-serif;padding:8px 14px;border-radius:8px;border:1px solid var(--line);
  background:var(--ground);color:var(--ink);cursor:pointer}
.btn.pri{background:var(--green);color:#fff;border-color:var(--green)}
.read{position:absolute;left:50%;bottom:16px;transform:translateX(-50%);background:var(--ink);color:var(--ground);
  font-size:12.5px;padding:8px 14px;border-radius:999px;box-shadow:var(--shadow);display:none;z-index:30}
.hint{position:absolute;left:50%;top:14px;transform:translateX(-50%);z-index:10;background:var(--panel);
  border:1px solid var(--line);border-radius:999px;padding:6px 14px;font-size:12.5px;color:var(--muted);box-shadow:var(--shadow)}
.tip{position:absolute;z-index:25;max-width:240px;background:var(--ink);color:var(--ground);font-size:13px;line-height:1.4;
  padding:9px 12px;border-radius:10px;box-shadow:var(--shadow);transform:translate(-50%,-100%) translateY(-14px);display:none}
.tip .cat{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;opacity:.7;display:block;margin-bottom:3px}
</style>

<header>
  <h1>Reimagine Elmwood</h1>
  <p class="sub">Berkeley's Elmwood commercial district &mdash; College &amp; Telegraph. Double-click any spot and share what could happen there. Gold parcels are underused today (the land is worth more than the building).</p>
  <div class="meta">
    <artifact-local><span><span class="count" id="cnt">0</span> <span id="unit">ideas</span> so far</span></artifact-local>
    <span>__NCOMM__ commercial parcels &middot; __NUNDER__ underused</span>
    <span class="legend">
      <span><span class="sw" style="background:var(--green)"></span>Shops &amp; food</span>
      <span><span class="sw" style="background:var(--blue)"></span>Housing</span>
      <span><span class="sw" style="background:var(--gold)"></span>Open space</span>
      <span><span class="sw" style="background:#7a52c9"></span>Transit &amp; bike</span>
    </span>
  </div>
</header>

<main>
  <div class="mapwrap" id="wrap">
    <div class="mapinner" id="inner">
      <svg viewBox="0 0 __W__ __H__" id="map" aria-label="Elmwood commercial district map">
        <g opacity="0.5">__CTX__</g>
        __PARCELS__
        __LABELS__
      </svg>
      <div id="pins"></div>
    </div>
  </div>
  <div class="hint">Double-click the map to add an idea</div>
  <div class="read" id="read">You're viewing this map read-only &mdash; ask John for edit access to add ideas.</div>

  <artifact-local>
    <div class="pop" id="pop">
      <label>What could happen here?</label>
      <input type="text" id="idea" maxlength="140" placeholder="e.g. a childcare co-op in the vacant storefront" autocomplete="off">
      <div class="chips" id="chips">
        <button class="chip" data-cat="housing" aria-pressed="false">Housing</button>
        <button class="chip" data-cat="shops" aria-pressed="true">Shops &amp; food</button>
        <button class="chip" data-cat="open" aria-pressed="false">Open space</button>
        <button class="chip" data-cat="transit" aria-pressed="false">Transit &amp; bike</button>
        <button class="chip" data-cat="other" aria-pressed="false">Other</button>
      </div>
      <div class="row"><button class="btn" id="cancel">Cancel</button><button class="btn pri" id="add">Add idea</button></div>
    </div>
    <div class="tip" id="tip"></div>
  </artifact-local>
</main>

<script>
(async function(){
  const artifact = await (window.claude?.use?.("artifact") ?? Promise.resolve(null));
  const inner=document.getElementById('inner'), pins=document.getElementById('pins'),
        pop=document.getElementById('pop'), idea=document.getElementById('idea'),
        chips=document.getElementById('chips'), cnt=document.getElementById('cnt'),
        tip=document.getElementById('tip'), readBanner=document.getElementById('read');
  let px=0, py=0, cat="shops", readonly=false;

  function relPct(e){ const r=inner.getBoundingClientRect();
    return [ (e.clientX-r.left)/r.width*100, (e.clientY-r.top)/r.height*100 ]; }
  function recount(){ const n=pins.querySelectorAll('.pin').length; cnt.textContent=n;
    const u=document.getElementById('unit'); if(u) u.textContent = n===1?'idea':'ideas'; }

  // open the idea popover at a double-clicked spot
  inner.addEventListener('dblclick', e=>{
    if(readonly) return;
    if(e.target.closest('.pin')) return;
    [px,py]=relPct(e);
    pop.style.left=Math.min(88,Math.max(12,px))+'%'; pop.style.top=py+'%';
    pop.classList.add('on'); idea.value=''; idea.focus();
  });
  chips.addEventListener('click', e=>{ const b=e.target.closest('.chip'); if(!b) return;
    [...chips.children].forEach(c=>c.setAttribute('aria-pressed', c===b)); cat=b.dataset.cat; });
  document.getElementById('cancel').onclick=()=>pop.classList.remove('on');

  // ADD IDEA — a gesture that appends a pin to the shared document (syncs to every editor)
  document.getElementById('add').onclick=()=>{
    const text=idea.value.trim(); if(!text) { idea.focus(); return; }
    const pin=document.createElement('button');
    pin.className='pin'; pin.setAttribute('data-cat',cat);
    pin.setAttribute('data-x',px.toFixed(2)); pin.setAttribute('data-y',py.toFixed(2));
    pin.style.left=px.toFixed(2)+'%'; pin.style.top=py.toFixed(2)+'%';
    pin.setAttribute('aria-label','idea: '+text.slice(0,60));
    const s=document.createElement('span'); s.className='idea'; s.textContent=text; pin.appendChild(s);
    pins.appendChild(pin);              // <- the gesture the runtime saves + syncs
    pop.classList.remove('on'); recount();
  };

  // show an idea when a pin is clicked/focused
  function showTip(pin){ const t=pin.querySelector('.idea'); if(!t) return;
    const catName={housing:'Housing',shops:'Shops & food',open:'Open space',transit:'Transit & bike',other:'Other'}[pin.dataset.cat]||'Idea';
    tip.innerHTML='<span class="cat"></span>'; tip.firstChild.textContent=catName;
    tip.appendChild(document.createTextNode(t.textContent));
    tip.style.left=pin.style.left; tip.style.top=pin.style.top; tip.style.display='block'; }
  pins.addEventListener('click', e=>{ const p=e.target.closest('.pin'); if(p) showTip(p); });
  document.addEventListener('click', e=>{ if(!e.target.closest('.pin')&&!e.target.closest('#tip')) tip.style.display='none'; });

  // other editors' pins arrive as document edits -> keep the count honest
  document.addEventListener('claude:edit', recount);
  document.addEventListener('claude:sync-off', ()=>{ readonly=true; readBanner.style.display='block'; });
  if(!artifact){ /* not in a granting view: still usable as a local sketch, just not shared */ }
  recount();
})();
</script>
"""

if __name__ == "__main__":
    main()
