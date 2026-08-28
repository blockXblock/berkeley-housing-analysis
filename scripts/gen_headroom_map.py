#!/usr/bin/env python3
"""gen_headroom_map.py — block-level housing-HEADROOM choropleth (docs/maps/headroom.html + _data.json).

Renders the max ADDABLE units per census block (scripts/block_headroom.py output) on a MapLibre map,
matching the house map stack (MapLibre GL + CARTO light basemap + GeoJSON), like gen_bond_incidence.py.
Four selectable metrics (MH by-right / MH+bonus / corridor-est / total), block popups, district
boundaries + a ranked-district panel, and an AFFORDABILITY panel (by-right middle housing is market-rate
on-site; affordability is monetized into the Housing Trust Fund, realized elsewhere — sourced note).

Inputs:  data/reference/block_headroom.csv  (per-block headroom, from block_headroom.py)
         data/processed/berkeley_blocks_2020.geojson  (block polygons)
         data/reference/berkeley_neighborhoods.geojson  (district polygons + Name)
Outputs: docs/maps/headroom_data.json (blocks w/ headroom props + district), docs/maps/headroom.html
Run: /opt/miniconda3/envs/jupyter_env/bin/python scripts/gen_headroom_map.py
"""
import json
import pandas as pd, geopandas as gpd

HR = "data/reference/block_headroom.csv"
BLOCKS = "data/processed/berkeley_blocks_2020.geojson"
NEIGH = "data/reference/berkeley_neighborhoods.geojson"
OUT_JSON = "docs/maps/headroom_data.json"
OUT_HTML = "docs/maps/headroom.html"


def build_data():
    hr = pd.read_csv(HR, dtype={"GEOID20": str})
    bsrc = gpd.read_file(BLOCKS).to_crs(4326)
    bsrc["GEOID20"] = bsrc.GEOID20.astype(str)
    adu_col = "adu_adds" if "adu_adds" in bsrc.columns else None
    blk = bsrc[["GEOID20", "geometry"] + ([adu_col] if adu_col else [])].copy()
    blk = blk.merge(hr, on="GEOID20", how="inner")
    if adu_col:
        blk["adu_adds"] = blk["adu_adds"].fillna(0).astype(int)
    else:
        blk["adu_adds"] = 0
    # district tag (block centroid within neighborhood) — project for a valid centroid
    n = gpd.read_file(NEIGH).to_crs(4326)[["Name", "geometry"]]
    cen = blk.copy(); cen["geometry"] = blk.to_crs(26910).geometry.centroid.to_crs(4326)
    tag = gpd.sjoin(cen[["GEOID20", "geometry"]], n, predicate="within", how="left")[["GEOID20", "Name"]]
    tag = tag.drop_duplicates("GEOID20")
    blk = blk.merge(tag, on="GEOID20", how="left")
    blk["district"] = blk.Name.fillna("—")
    keep = ["GEOID20", "district", "units_per_block", "headroom_mh_byright", "headroom_mh_bonus",
            "headroom_corridor_est", "headroom_total", "adu_adds", "parcels"]
    blk = blk[keep + ["geometry"]]
    blk.to_file(OUT_JSON, driver="GeoJSON")
    # district ranking (for the side panel)
    d = (blk.groupby("district").agg(
            blocks=("GEOID20", "nunique"),
            existing=("units_per_block", "sum"),
            mh_byright=("headroom_mh_byright", "sum"),
            mh_bonus=("headroom_mh_bonus", "sum"),
            corridor=("headroom_corridor_est", "sum"),
        ).reset_index())
    d = d[(d.district != "—") & (d.mh_byright > 0)].sort_values("mh_byright", ascending=False)
    d["growth_x"] = ((d.existing + d.mh_byright) / d.existing.replace(0, 1)).round(1)
    return d, int(blk.headroom_mh_byright.sum()), int(blk.units_per_block.sum())


def district_boundaries():
    n = gpd.read_file(NEIGH).to_crs(4326)[["Name", "geometry"]]
    return json.loads(n.to_json())


HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Berkeley Housing Headroom by Block</title>
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<style>
 :root{--ink:#1a1a1a;--panel:rgba(255,255,255,.95);--line:#e0ddd6}
 *{box-sizing:border-box}
 html,body{margin:0;height:100%;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--ink)}
 #map{position:absolute;inset:0}
 .panel{position:absolute;background:var(--panel);border:1px solid var(--line);border-radius:10px;
   box-shadow:0 2px 14px rgba(0,0,0,.12);backdrop-filter:blur(4px)}
 #head{top:12px;left:12px;max-width:340px;padding:14px 16px}
 #head h1{margin:0 0 4px;font-size:17px;letter-spacing:-.2px}
 #head p{margin:6px 0;color:#444;font-size:12.5px}
 .metricbtns{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 4px}
 .metricbtns button{font:600 11.5px/1 inherit;padding:7px 9px;border:1px solid #cfc9bd;background:#fff;
   border-radius:7px;cursor:pointer;color:#333}
 .metricbtns button.on{background:#b5371f;border-color:#b5371f;color:#fff}
 #legend{margin-top:8px;font-size:11.5px}
 #legend .row{display:flex;align-items:center;gap:7px;margin:3px 0}
 #legend .sw{width:16px;height:12px;border-radius:2px;border:1px solid rgba(0,0,0,.15)}
 #rank{top:12px;right:12px;width:270px;max-height:calc(100vh-24px);overflow:auto;padding:12px 14px}
 #rank h2{margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.5px;color:#666}
 table{border-collapse:collapse;width:100%;font-size:12px;font-variant-numeric:tabular-nums}
 th,td{text-align:right;padding:3px 4px;border-bottom:1px solid #efece5}
 th:first-child,td:first-child{text-align:left}
 th{color:#888;font-weight:600}
 tr.hi td{background:#fdf0ec}
 #aff{bottom:12px;left:12px;max-width:360px;padding:12px 15px;font-size:12.5px}
 #aff h2{margin:0 0 6px;font-size:13px;color:#b5371f;text-transform:uppercase;letter-spacing:.4px}
 #aff p{margin:5px 0;color:#333}
 .maplibregl-popup-content{font:13px/1.4 inherit;padding:11px 13px;border-radius:9px}
 .pop b{font-size:13.5px}.pop .g{color:#666}.pop table{margin-top:5px}
 .pop td{border:0;padding:1px 0}.pop td:last-child{padding-left:12px;font-weight:600}
 a{color:#b5371f}
 @media(max-width:760px){#rank{display:none}#head,#aff{max-width:calc(100vw-24px)}}
</style></head><body>
<div id="map"></div>
<div id="head" class="panel">
 <h1>Housing headroom, block by block</h1>
 <p>Maximum units that could be <b>added</b> to each block under current zoning — the ceiling zoning
    allows, not a forecast of what gets built.</p>
 <div class="metricbtns" id="mbtns"></div>
 <div id="legend"></div>
 <p style="font-size:11px;color:#777;margin-top:9px">__TOTAL__ addable units by-right citywide vs
    __EXISTING__ existing (2020). Middle Housing = up to 8 units/lot by-right, flatland residential.</p>
</div>
<div id="rank" class="panel">
 <h2>Districts by headroom</h2>
 <table id="rt"><thead><tr><th>District</th><th>Now</th><th>+By-right</th><th>×</th></tr></thead>
 <tbody></tbody></table>
</div>
<div id="aff" class="panel">
 <h2>Headroom ≠ affordability</h2>
 <p>By-right middle housing in high-demand districts (Elmwood, North Berkeley, Claremont) will be built
    <b>at market rate</b>. Projects pay an <b>in-lieu fee</b> into the Housing Trust Fund rather than
    including below-market units on site — on-site affordable units via the density bonus are
    "not financially feasible" for mid-size projects (Council FAQ).</p>
 <p style="color:#666">So the affordability these units generate is <b>realized elsewhere</b>, not in the
    desirable, high-headroom neighborhoods themselves.</p>
</div>
<script>
const DIST=__DIST__, RANK=__RANK__;
const METRICS={
 mh_byright:{label:"MH by-right",prop:"headroom_mh_byright",unit:"addable units / block",
   stops:[0,1,50,150,300,500],colors:["#eee9e0","#fde0c8","#fbb27a","#f07b3e","#d94b23","#a6270c"]},
 mh_bonus:{label:"+ density bonus",prop:"headroom_mh_bonus",unit:"addable units / block",
   stops:[0,1,80,220,450,750],colors:["#eee9e0","#fde0c8","#fbb27a","#f07b3e","#d94b23","#a6270c"]},
 corridor:{label:"Corridor (soft)",prop:"headroom_corridor_est",unit:"addable units / block",
   stops:[0,1,50,150,400,800],colors:["#eef0ea","#d9e6cf","#a9cf9a","#6fae66","#3f8f4e","#1f6b39"]},
 total:{label:"Total",prop:"headroom_total",unit:"addable units / block",
   stops:[0,1,120,320,650,1100],colors:["#ece9f0","#d8cfe6","#b49acf","#8f6fae","#6b3f9f","#4a1f8f"]},
 adu:{label:"ADU uptake",prop:"adu_adds",unit:"ADUs built 2018+ / block",
   stops:[0,1,2,3,5,7],colors:["#e9edf1","#cfe0ec","#9ec6e0","#5fa2cf","#2e73b0","#12466e"]},
};
let cur="mh_byright";
const map=new maplibregl.Map({container:'map',center:[-122.273,37.874],zoom:12.2,minzoom:10,maxzoom:17,
 style:{version:8,sources:{c:{type:'raster',tiles:['https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'],
 tileSize:256,attribution:'© OpenStreetMap © CARTO'}},layers:[{id:'bg',type:'raster',source:'c'}]}});

function fillExpr(m){const e=["step",["coalesce",["get",m.prop],0],m.colors[0]];
 for(let i=1;i<m.stops.length;i++){e.push(m.stops[i],m.colors[i]);}return e;}

function legend(m){const L=document.getElementById('legend');let h='';
 for(let i=m.colors.length-1;i>=0;i--){const lo=m.stops[i],hi=m.stops[i+1];
  const lab=i===0?'0':(hi?`${lo}–${hi}`:`${lo}+`);
  h+=`<div class="row"><span class="sw" style="background:${m.colors[i]}"></span>${lab}</div>`;}
 L.innerHTML=`<div style="font-weight:600;margin-bottom:4px">${m.unit}</div>`+h;}

function setMetric(k){cur=k;const m=METRICS[k];
 if(map.getLayer&&map.getLayer('blk'))map.setPaintProperty('blk','fill-color',fillExpr(m));
 [...document.querySelectorAll('#mbtns button')].forEach(b=>b.classList.toggle('on',b.dataset.k===k));
 legend(m);}

// UI paint (metric buttons, legend, district table) — NO map dependency, runs immediately so the
// control panel is usable even before the basemap tiles arrive.
function paintUI(){ if(paintUI.d)return; paintUI.d=1;
 const bb=document.getElementById('mbtns');
 Object.entries(METRICS).forEach(([k,m])=>{const b=document.createElement('button');
   b.textContent=m.label;b.dataset.k=k;b.className=k===cur?'on':'';b.onclick=()=>setMetric(k);bb.appendChild(b);});
 legend(METRICS[cur]);
 const tb=document.querySelector('#rt tbody');
 RANK.forEach(r=>{const tr=document.createElement('tr');
   if(/Elmwood/.test(r.district))tr.className='hi';
   tr.innerHTML=`<td>${r.district}</td><td>${r.existing.toLocaleString()}</td>
     <td>+${r.mh_byright.toLocaleString()}</td><td>${r.growth_x}×</td>`;tb.appendChild(tr);});
}
// map data (block choropleth + district outlines + popup) — needs the style loaded.
function addData(){ if(addData.d)return; addData.d=1;
 map.addSource('hr',{type:'geojson',data:'headroom_data.json'});
 map.addLayer({id:'blk',type:'fill',source:'hr',
   paint:{'fill-color':fillExpr(METRICS[cur]),'fill-opacity':0.72,'fill-outline-color':'rgba(120,110,95,.25)'}});
 map.addSource('dist',{type:'geojson',data:DIST});
 map.addLayer({id:'distln',type:'line',source:'dist',
   paint:{'line-color':'#5a5346','line-width':1.4,'line-dasharray':[2,1.5],'line-opacity':.55}});
 const pop=new maplibregl.Popup({closeButton:false,maxWidth:'260px'});
 map.on('mousemove','blk',e=>{const p=e.features[0].properties;map.getCanvas().style.cursor='pointer';
   pop.setLngLat(e.lngLat).setHTML(
   `<div class="pop"><b>${p.district}</b> <span class="g">block …${(''+p.GEOID20).slice(-4)}</span>
    <table>
    <tr><td class="g">Existing units</td><td>${p.units_per_block}</td></tr>
    <tr><td class="g">MH by-right</td><td>+${p.headroom_mh_byright}</td></tr>
    <tr><td class="g">+ density bonus</td><td>+${p.headroom_mh_bonus}</td></tr>
    <tr><td class="g">Corridor (soft)</td><td>+${p.headroom_corridor_est}</td></tr>
    <tr><td class="g">ADUs built (2018+)</td><td>${p.adu_adds}</td></tr>
    <tr><td class="g">Parcels</td><td>${p.parcels}</td></tr></table></div>`).addTo(map);});
 map.on('mouseleave','blk',()=>{map.getCanvas().style.cursor='';pop.remove();});
}
paintUI();                                   // control panel: immediate, map-independent
map.on('style.load',addData); map.on('load',addData);   // choropleth: when the style is ready
</script></body></html>"""


def main():
    d, tot, existing = build_data()
    rank = [dict(district=r.district, existing=int(r.existing), mh_byright=int(r.mh_byright),
                 mh_bonus=int(r.mh_bonus), corridor=int(r.corridor), growth_x=float(r.growth_x))
            for r in d.itertuples()]
    html = (HTML.replace("__DIST__", json.dumps(district_boundaries()))
                .replace("__RANK__", json.dumps(rank))
                .replace("__TOTAL__", f"{tot:,}")
                .replace("__EXISTING__", f"{existing:,}"))
    open(OUT_HTML, "w").write(html)
    print(f"wrote {OUT_HTML} + {OUT_JSON}")
    print(f"districts ranked: {len(rank)} | citywide MH by-right {tot:,} vs existing {existing:,}")


if __name__ == "__main__":
    main()
