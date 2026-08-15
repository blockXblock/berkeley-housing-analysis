#!/usr/bin/env python3
"""gen_ownership_map.py — Berkeley parcel ownership map: tenure (years held) + owner type.

The SF Chronicle's California map shows the CURRENT owner (Regrid snapshot). This adds the two things we
already hold to make it Berkeley-specific and time-aware:
  - TENURE: 2026 - LatestDocu (year of the last recorded document ≈ when the current owner acquired it).
  - OWNER TYPE: classified from OwnersName — individual / investor(LLC-Corp-LP) / trust / institutional.
Two toggle modes over the same points; Elmwood outlined. Streams a separate data.json (small HTML).

HONESTY RAILS: (1) LatestDocu is the last *document* year (usually the last sale, but can be a refi/other
recording) — a proxy for acquisition, not a certified sale date. (2) "trust" is separated from "investor"
because most trusts are family estate-planning, NOT corporate. (3) This is the LATEST transfer only, not the
full ownership history (that needs the County Recorder deed index).

Inputs: data/reference/berkeley_parcel_owners_2026-08-13.csv (APN,OwnersName,LatestDocu) + committed taxparcels geometry.
Output: docs/maps/berkeley_ownership.html + docs/maps/berkeley_ownership_data.json.
Usage: python scripts/gen_ownership_map.py
"""
import geopandas as gpd, pandas as pd, json, os, re, sys, warnings
warnings.filterwarnings("ignore"); sys.path.insert(0, "scripts")
from housing_rules import to_canonical_apn
OUT = "docs/maps/berkeley_ownership.html"
DATA = "docs/maps/berkeley_ownership_data.json"

INVESTOR = re.compile(r"\b(LLC|L\.L\.C|INC|CORP|COMPANY|LTD|LP|L\.P|LLP|PARTNERS|PARTNERSHIP|PROPERTIES|"
                      r"HOLDINGS|VENTURES|CAPITAL|REALTY|MANAGEMENT|INVESTMENTS?|ENTERPRISES|GROUP|ASSOCIATES|& CO)\b")
# trust — incl. assessor abbreviations TRS/TTEE, and 'X TR' only in trust context (NOT bare 'TR' = tract)
TRUST = re.compile(r"\b(TRUST|TRUSTEE|TTEE|TRS|REVOCABLE|(?:FAMILY|LIVING|REV|FAM|LV|JOINT|SURVIVORS?)\s+TR)\b")
INSTIT = re.compile(r"\b(UNIVERSITY|REGENTS|CITY OF|COUNTY|STATE OF|CHURCH|SCHOOL|DISTRICT|CALIFORNIA|"
                    r"HOUSING AUTH|FOUNDATION|ASSOCIATION|ASSN|CONGREGATION|TEMPLE|SOCIETY|INSTITUTE|"
                    r"COOPERATIVE|CO-OP|MINISTRIES|DIOCESE|PARISH|NONPROFIT|COMMONS)\b")

def owner_type(name):
    n = str(name).upper()
    if INSTIT.search(n): return 3
    if TRUST.search(n): return 2
    if INVESTOR.search(n): return 1
    return 0            # individual

def main():
    tp = gpd.read_file("data/raw/berkeley_taxparcels_2026-08-12.geojson")[["APN", "geometry"]]
    tp["capn"] = tp.APN.apply(lambda a: to_canonical_apn(a, "alameda") if a else None)
    ow = pd.read_csv("data/reference/berkeley_parcel_owners_2026-08-13.csv")
    ow["capn"] = ow.APN.apply(lambda a: to_canonical_apn(a, "alameda") if pd.notna(a) else None)
    ow["otype"] = ow.OwnersName.map(owner_type)
    ow["yr"] = pd.to_numeric(ow.LatestDocu, errors="coerce")
    ow["tenure"] = (2026 - ow.yr).where(ow.yr.between(1900, 2026))
    # address per parcel for click popups (situs address from berkeley.db)
    import sqlite3
    _adf = pd.read_sql("SELECT APN, SitusStree, SitusStr_1 FROM parcels", sqlite3.connect("databases/berkeley.db"))
    _adf["capn"] = _adf.APN.apply(lambda a: to_canonical_apn(a, "alameda") if pd.notna(a) else None)
    _adf["addr"] = (_adf.SitusStree.fillna("").astype(str).str.strip() + " " + _adf.SitusStr_1.fillna("").astype(str).str.strip()).str.strip()
    ow = ow.merge(_adf.dropna(subset=["capn"]).drop_duplicates("capn")[["capn", "addr"]], on="capn", how="left")
    g = tp.merge(ow[["capn", "otype", "tenure", "OwnersName", "addr"]].dropna(subset=["capn"]).drop_duplicates("capn"), on="capn", how="inner")
    g = g[g.tenure.notna()].to_crs(4326)
    c = g.geometry.centroid
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(x, 5), round(y, 5)]},
              "properties": {"t": int(min(t, 99)), "o": int(o),
                             "a": str(ad) if pd.notna(ad) else "", "n": str(nm) if pd.notna(nm) else ""}}
             for x, y, t, o, ad, nm in zip(c.x, c.y, g.tenure, g.otype, g.addr, g.OwnersName)]
    counts = pd.Series([f["properties"]["o"] for f in feats]).value_counts().to_dict()
    lab = {0: "individual", 1: "investor (LLC/Corp/LP)", 2: "trust", 3: "institutional"}
    print(f"parcels mapped: {len(feats)} | owner types: " + ", ".join(f"{lab[k]}={counts.get(k,0)}" for k in range(4)))
    print(f"  median tenure: {pd.Series([f['properties']['t'] for f in feats]).median():.0f} yr")
    el = gpd.read_file("data/reference/berkeley_neighborhoods.geojson").to_crs(4326)
    elb = json.loads(el[el.Name.astype(str).str.contains("lmwood", case=False)][["geometry"]].to_json())

    html = """<!doctype html><html><head><meta charset="utf-8"><title>Who owns Berkeley</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<style>body,html,#map{margin:0;height:100%;font-family:system-ui}
.panel{position:absolute;top:12px;left:12px;background:rgba(255,255,255,.94);padding:10px 14px;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.3);font-size:13px}
.panel button{font-size:13px;padding:4px 12px;margin-right:6px;cursor:pointer;border:1px solid #999;background:#fff;border-radius:5px}
.panel button.on{background:#0074D9;color:#fff;border-color:#0074D9}
#legend{margin-top:8px} .sw{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:5px;vertical-align:middle}
.cap{color:#555;font-size:11px;margin-top:6px;max-width:320px}</style></head>
<body><div id="map"></div>
<div class="panel"><b>Who owns Berkeley</b><br>
<div style="margin:6px 0"><button id="bT" class="on" onclick="mode('t')">Tenure (years held)</button><button id="bO" onclick="mode('o')">Owner type</button></div>
<div id="legend"></div>
<div class="cap" id="cap">Color = how long the current owner has held each parcel (last recorded document year). Elmwood outlined.</div></div>
<script>
let FEATS={features:[]};
const TEN=['step',['get','t'],'#d7301f',5,'#fd8d3c',15,'#fee391',30,'#74add1',60,'#4575b4'];
const OWN=['match',['get','o'],1,'#d7301f',2,'#984ea3',3,'#377eb8','#bdbdbd'];
const LT='<div><span class="sw" style="background:#d7301f"></span>&lt;5 yr</div><div><span class="sw" style="background:#fd8d3c"></span>5-15</div><div><span class="sw" style="background:#fee391"></span>15-30</div><div><span class="sw" style="background:#74add1"></span>30-60</div><div><span class="sw" style="background:#4575b4"></span>60+ (long-held)</div>';
const LO='<div><span class="sw" style="background:#bdbdbd"></span>individual</div><div><span class="sw" style="background:#d7301f"></span>investor (LLC/Corp/LP)</div><div><span class="sw" style="background:#984ea3"></span>trust</div><div><span class="sw" style="background:#377eb8"></span>institutional</div>';
const map=new maplibregl.Map({container:'map',center:[-122.273,37.871],zoom:12.4,
 style:{version:8,sources:{c:{type:'raster',tiles:['https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OSM © CARTO'}},layers:[{id:'bg',type:'raster',source:'c'}]}});
function mode(m){
  document.getElementById('bT').className=m=='t'?'on':''; document.getElementById('bO').className=m=='o'?'on':'';
  map.setPaintProperty('pts','circle-color', m=='t'?TEN:OWN);
  document.getElementById('legend').innerHTML = m=='t'?LT:LO;
  document.getElementById('cap').textContent = m=='t'? 'Color = how long the current owner has held each parcel (last recorded document year). Elmwood outlined.' : 'Color = owner type, classified from the owner name. Trust is separated from investor (most trusts are family estate-planning). Elmwood outlined.';
}
map.on('load',()=>{
 map.addSource('el',{type:'geojson',data:__ELB__});
 map.addLayer({id:'elw',type:'line',source:'el',paint:{'line-color':'#0074D9','line-width':2}});
 map.addSource('p',{type:'geojson',data:'berkeley_ownership_data.json'});
 map.addLayer({id:'pts',type:'circle',source:'p',paint:{'circle-radius':['interpolate',['linear'],['zoom'],11,1.6,15,4],'circle-color':TEN,'circle-opacity':0.82}});
 fetch('berkeley_ownership_data.json').then(r=>r.json()).then(d=>{FEATS=d;}); mode('t');
 map.on('click','pts',e=>{ const p=e.features[0].properties, a=p.a||'(address unavailable)';
   const q=encodeURIComponent(a+' Berkeley CA'), TY=['individual','investor (LLC/Corp/LP)','trust','institutional'];
   new maplibregl.Popup().setLngLat(e.lngLat).setHTML(
     '<b>'+a+'</b>'+(p.n?'<br>'+p.n:'')+'<br>'+TY[p.o]+' · held '+p.t+' yr'
     +'<br><a href="https://www.google.com/maps/search/?api=1&query='+q+'" target="_blank" rel="noopener">Open in Google Maps ↗</a>').addTo(map); });
 map.on('mouseenter','pts',()=>map.getCanvas().style.cursor='pointer');
 map.on('mouseleave','pts',()=>map.getCanvas().style.cursor='');
});
</script></body></html>""".replace("__ELB__", json.dumps(elb))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"type": "FeatureCollection", "features": feats}, open(DATA, "w"))
    open(OUT, "w").write(html)
    print(f"wrote {OUT} ({round(len(html)/1024)} KB) + {DATA} ({round(os.path.getsize(DATA)/1e6,1)} MB)")

if __name__ == "__main__":
    main()
