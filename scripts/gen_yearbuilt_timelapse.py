#!/usr/bin/env python3
"""gen_yearbuilt_timelapse.py — animated build-out map of Berkeley by year built (landmark-corrected).

Every parcel appears at its **YearBuilt**, colored by dwelling units, as a year slider/play advances — so you
watch Berkeley get built (the Elmwood fills ~1900-1925 then freezes; the corridors light up recently).

HONESTY RAILS (baked into the caption): (1) YearBuilt is the MAIN STRUCTURE's year — this shows *construction*,
NOT units added later; ADUs/conversions are invisible here (see JN-M §3 for those). (2) `YearBuilt` is approximate
(off ~8yr median on landmarks); we OVERRIDE it with the City landmark true dates where available
(data/reference/berkeley_landmark_build_dates.csv — e.g. 2811 Benvenue -> 1903 not 1925). (3) parcels with no
build date are excluded and counted.

Source: data/raw/berkeley_taxparcels_2026-08-12.geojson + the landmark correction layer.
Output: docs/maps/berkeley_construction_timelapse.html (self-contained; MapLibre + CARTO via CDN).
Usage: python scripts/gen_yearbuilt_timelapse.py
"""
import geopandas as gpd, pandas as pd, json, os, sys, warnings
warnings.filterwarnings("ignore"); sys.path.insert(0, "scripts")
from housing_rules import to_canonical_apn
OUT = "docs/maps/berkeley_construction_timelapse.html"
DATA = "docs/maps/berkeley_construction_data.json"   # streamed, not inlined (25k points)

def main():
    tp = gpd.read_file("data/raw/berkeley_taxparcels_2026-08-12.geojson")[["APN", "YearBuilt", "Units", "geometry"]]
    tp["YearBuilt"] = pd.to_numeric(tp.YearBuilt, errors="coerce")
    tp["Units"] = pd.to_numeric(tp.Units, errors="coerce").fillna(1).clip(lower=1)
    tp["capn"] = tp.APN.apply(lambda a: to_canonical_apn(a, "alameda") if a else None)
    # landmark override
    lm = pd.read_csv("data/reference/berkeley_landmark_build_dates.csv")
    lmmap = lm[lm.apn.notna() & lm.name_year.notna()].drop_duplicates("apn").set_index("apn").name_year
    tp["year"] = tp.apply(lambda r: int(lmmap[r.capn]) if (r.capn in lmmap.index) else r.YearBuilt, axis=1)
    tp["corrected"] = tp.capn.isin(lmmap.index)
    # address per parcel (for click popups) — join situs address from berkeley.db by canonical APN
    import sqlite3
    _adf = pd.read_sql("SELECT APN, SitusStree, SitusStr_1 FROM parcels", sqlite3.connect("databases/berkeley.db"))
    _adf["capn"] = _adf.APN.apply(lambda a: to_canonical_apn(a, "alameda") if pd.notna(a) else None)
    _adf["addr"] = (_adf.SitusStree.fillna("").astype(str).str.strip() + " " + _adf.SitusStr_1.fillna("").astype(str).str.strip()).str.strip()
    AMAP = dict(_adf.dropna(subset=["capn"]).drop_duplicates("capn")[["capn", "addr"]].values)
    # inline parcel card (owner/type/use/assessed) from parcel_facts.db — consistent across all 3 maps
    _pf = pd.read_sql("SELECT capn, owner_name, owner_type, use_bucket, assessed_total FROM parcel_facts",
                      sqlite3.connect("databases/parcel_facts.db"))
    PF = {r.capn: (r.owner_name, r.owner_type, r.use_bucket, r.assessed_total) for r in _pf.itertuples()}
    def _card(cp):
        t = PF.get(cp)
        if not t: return {"own": "", "ot": "", "ub": "", "av": 0}
        o, ot, ub, av = t
        return {"own": "" if pd.isna(o) else str(o), "ot": "" if pd.isna(ot) else str(ot),
                "ub": "" if pd.isna(ub) else str(ub), "av": int(av / 1000) if pd.notna(av) else 0}
    n_total = len(tp); n_nodate = int((~tp.year.between(1850, 2026)).sum())
    g = tp[tp.year.between(1850, 2026)].to_crs(4326)
    c = g.geometry.centroid
    feats = [{"type": "Feature",
              "geometry": {"type": "Point", "coordinates": [round(x, 5), round(y, 5)]},
              "properties": {"y": int(yr), "u": int(min(u, 9)), "c": int(cr), "a": AMAP.get(cp, ""), **_card(cp)}}
             for x, y, yr, u, cr, cp in zip(c.x, c.y, g.year, g.Units, g.corrected, g.capn)]
    cx, cy = g.to_crs(4326).unary_union.centroid.coords[0] if False else (-122.273, 37.871)
    n_shown = len(feats)
    print(f"parcels: {n_total} | shown (dated 1850-2026): {n_shown} | no build date (excluded): {n_nodate} | landmark-corrected: {int(tp.corrected.sum())}")

    el = gpd.read_file("data/reference/berkeley_neighborhoods.geojson").to_crs(4326)
    elb = json.loads(el[el.Name.astype(str).str.contains("lmwood", case=False)][["geometry"]].to_json())

    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Berkeley built, year by year</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<style>body,html,#map{{margin:0;height:100%;font-family:system-ui}}
.panel{{position:absolute;top:12px;left:12px;right:12px;background:rgba(255,255,255,.94);padding:10px 14px;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.3);font-size:13px}}
.yr{{font-size:26px;font-weight:700}} #play{{font-size:15px;padding:3px 12px;margin-right:10px;cursor:pointer}}
#slider{{width:60%;vertical-align:middle}} .cap{{color:#555;font-size:11px}}
.legend{{position:absolute;bottom:16px;left:12px;background:#fff;padding:8px 10px;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.3);font-size:12px}}
.sw{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}}</style></head>
<body><div id="map"></div>
<div class="panel"><span class="yr" id="ylab">1850</span> &nbsp; <button id="play">▶ play</button>
<input type="range" id="slider" min="1850" max="2026" value="1850" step="1">
<span id="count"></span>
<div class="cap">Each dot = a parcel's <b>main structure</b> at its YearBuilt (landmark-corrected). Shows construction, NOT ADUs/units added later. {n_nodate:,} parcels have no build date (excluded). Elmwood outlined.</div></div>
<div class="legend"><b>Units in structure</b>
<div><span class="sw" style="background:#9ecae1"></span>1 (single-family)</div>
<div><span class="sw" style="background:#fd8d3c"></span>2</div>
<div><span class="sw" style="background:#d7301f"></span>3+</div></div>
<script>
let FEATS={{features:[]}};   // filled by fetch (streamed from the data file, not inlined)
const map=new maplibregl.Map({{container:'map',center:[{cx},{cy}],zoom:12.4,
 style:{{version:8,sources:{{c:{{type:'raster',tiles:['https://basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png'],tileSize:256,attribution:'© OSM © CARTO'}}}},layers:[{{id:'bg',type:'raster',source:'c'}}]}}}});
let year=1850, playing=false, timer=null;
function setYear(y){{ year=y; document.getElementById('ylab').textContent=y; document.getElementById('slider').value=y;
  map.setFilter('pts',['<=',['get','y'],y]);
  const n=FEATS.features.filter(f=>f.properties.y<=y).length;
  document.getElementById('count').textContent=n.toLocaleString()+' structures built'; }}
map.on('load',()=>{{
 map.addSource('el',{{type:'geojson',data:{json.dumps(elb)}}});
 map.addLayer({{id:'elw',type:'line',source:'el',paint:{{'line-color':'#0074D9','line-width':2}}}});
 map.addSource('p',{{type:'geojson',data:'berkeley_construction_data.json'}});
 map.addLayer({{id:'pts',type:'circle',source:'p',paint:{{
   'circle-radius':['interpolate',['linear'],['zoom'],11,1.6,15,4],
   'circle-color':['step',['get','u'],'#9ecae1',2,'#fd8d3c',3,'#d7301f'],
   'circle-opacity':0.8}}}});
 fetch('berkeley_construction_data.json').then(r=>r.json()).then(d=>{{ FEATS=d; setYear(1850); }});
 map.on('click','pts',e=>{{ const p=e.features[0].properties, a=p.a||'(address unavailable)';
   const q=encodeURIComponent(a+' Berkeley CA');
   new maplibregl.Popup().setLngLat(e.lngLat).setHTML(
     '<b>'+a+'</b>'
     +(p.own?'<br>owner: '+p.own+(p.ot?' <span style="color:#777">('+p.ot+')</span>':''):'')
     +'<br>Built '+p.y+(p.c=='1'||p.c===1?' <span style="color:#0074D9">(landmark-corrected)</span>':'')+(p.ub?' &middot; '+p.ub.replace(/_/g,' '):'')
     +'<br>'+p.u+' unit'+(p.u==1?'':'s')+' in structure'
     +(p.av?'<br>assessed value: $'+(p.av*1000).toLocaleString():'')
     +'<br><a href="https://www.google.com/maps/search/?api=1&query='+q+'" target="_blank" rel="noopener">Street view ↗</a>').addTo(map); }});
 map.on('mouseenter','pts',()=>map.getCanvas().style.cursor='pointer');
 map.on('mouseleave','pts',()=>map.getCanvas().style.cursor='');
}});
document.getElementById('slider').oninput=e=>{{ setYear(+e.target.value); }};
document.getElementById('play').onclick=()=>{{
  playing=!playing; document.getElementById('play').textContent=playing?'❚❚ pause':'▶ play';
  if(playing){{ if(year>=2026) setYear(1850);
    timer=setInterval(()=>{{ if(year>=2026){{clearInterval(timer);playing=false;document.getElementById('play').textContent='▶ play';return;}} setYear(year+1); }}, 180); }}
  else clearInterval(timer);
}};
</script></body></html>"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"type": "FeatureCollection", "features": feats}, open(DATA, "w"))
    open(OUT, "w").write(html)
    print(f"wrote {OUT} ({round(len(html)/1024)} KB) + {DATA} ({round(os.path.getsize(DATA)/1e6,1)} MB), {n_shown} dated parcels")

if __name__ == "__main__":
    main()
