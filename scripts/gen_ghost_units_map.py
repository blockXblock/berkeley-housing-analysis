#!/usr/bin/env python3
"""gen_ghost_units_map.py — self-contained MapLibre map of the Elmwood's hidden ("ghost") dwelling units.

Renders the RPP secondary-unit addresses (data/reference/berkeley_secondary_unit_addresses.geojson) — the
city-assigned addresses (½ / A-D / rear / cottage) for units the zoning map calls single-family — over the
official Elmwood neighborhood boundary + the 5.3-acre commercial BID (the "wrong lever" contrast). Points are
colored by address TYPE; click for the address. Output is one HTML file that loads MapLibre GL + a CARTO
basemap from CDN (open it in a browser; needs internet). v1 quick map — the sharper assessor-undercount CLASS
coloring is the JN-M reveal-map refinement.

Usage: python scripts/gen_ghost_units_map.py   # -> docs/maps/elmwood_hidden_units_map.html
"""
import geopandas as gpd, json, re, os, warnings
warnings.filterwarnings("ignore")
OUT = "docs/maps/elmwood_hidden_units_map.html"

def kind(a):
    a = str(a).upper()
    if "1/2" in a: return "half"
    if "REAR" in a: return "rear"
    if "COTTAGE" in a: return "cottage"
    if re.search(r" [A-D]$", a): return "letter"
    return "other"

def main():
    sec = gpd.read_file("data/reference/berkeley_secondary_unit_addresses.geojson").drop_duplicates("FullAddres")
    sec["kind"] = sec.FullAddres.map(kind)
    nbh = gpd.read_file("data/reference/berkeley_neighborhoods.geojson").to_crs(4326)
    elpoly = nbh[nbh.Name.astype(str).str.contains("lmwood", case=False)].dissolve()
    el = sec[sec.within(elpoly.geometry.iloc[0])].copy()
    bid = gpd.read_file("data/reference/berkeley_bid_elmwood.geojson").to_crs(4326)
    pts = json.loads(el[["FullAddres", "kind", "geometry"]].to_json())
    elb = json.loads(elpoly[["geometry"]].to_json())
    bidb = json.loads(bid[["geometry"]].to_json())
    cx, cy = elpoly.geometry.iloc[0].centroid.coords[0]

    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Elmwood hidden units</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<style>body,html,#map{{margin:0;height:100%;font-family:system-ui}}
.legend{{position:absolute;bottom:18px;left:12px;background:#fff;padding:10px 12px;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.3);font-size:13px}}
.legend b{{display:block;margin-bottom:4px}} .sw{{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px;vertical-align:middle}}
.cap{{position:absolute;top:12px;left:12px;background:#fff;padding:8px 12px;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.3);font-size:13px;max-width:320px}}</style></head>
<body><div id="map"></div>
<div class="cap"><b>Elmwood: {len(el)} secondary-unit addresses</b><br>City-assigned addresses (&frac12; / A-B / rear) for units the zoning map calls single-family. The Elmwood commercial strip (red) is 5.3 acres vs the 376-acre neighborhood.</div>
<div class="legend"><b>Hidden unit type</b>
<div><span class="sw" style="background:#e6194b"></span>fractional (&frac12;)</div>
<div><span class="sw" style="background:#f58231"></span>letter unit (A&ndash;D)</div>
<div><span class="sw" style="background:#911eb4"></span>rear / cottage</div></div>
<script>
const map=new maplibregl.Map({{container:'map',center:[{cx:.4f},{cy:.4f}],zoom:14.2,
 style:{{version:8,sources:{{carto:{{type:'raster',tiles:['https://basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png'],tileSize:256,attribution:'© OSM © CARTO'}}}},layers:[{{id:'bg',type:'raster',source:'carto'}}]}}}});
map.on('load',()=>{{
 map.addSource('el',{{type:'geojson',data:{json.dumps(elb)}}});
 map.addLayer({{id:'el-line',type:'line',source:'el',paint:{{'line-color':'#00a0dc','line-width':2.5}}}});
 map.addSource('bid',{{type:'geojson',data:{json.dumps(bidb)}}});
 map.addLayer({{id:'bid-fill',type:'fill',source:'bid',paint:{{'fill-color':'#e6194b','fill-opacity':0.35}}}});
 map.addSource('pts',{{type:'geojson',data:{json.dumps(pts)}}});
 map.addLayer({{id:'pts',type:'circle',source:'pts',paint:{{
   'circle-radius':5,'circle-stroke-width':1,'circle-stroke-color':'#fff',
   'circle-color':['match',['get','kind'],'half','#e6194b','letter','#f58231','rear','#911eb4','cottage','#911eb4','#888']}}}});
 map.on('click','pts',e=>new maplibregl.Popup().setLngLat(e.lngLat).setHTML('<b>'+e.features[0].properties.FullAddres+'</b><br>'+e.features[0].properties.kind).addTo(map));
 map.on('mouseenter','pts',()=>map.getCanvas().style.cursor='pointer');
 map.on('mouseleave','pts',()=>map.getCanvas().style.cursor='');
}});
</script></body></html>"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(html)
    print(f"wrote {OUT} — {len(el)} Elmwood hidden-unit points")

if __name__ == "__main__":
    main()
