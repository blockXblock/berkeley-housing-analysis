#!/usr/bin/env python3
"""gen_ownership_map.py — Berkeley parcel map: last-recorded-document recency + owner type.

Two toggle modes over the same points; Elmwood outlined. Streams a separate data.json (small HTML).
  - LAST RECORDED DOCUMENT: 2026 - year(berkeley.db.LatestDocumentDate) = years since ANY document
    (sale, refinance, or transfer) was last recorded on the parcel. Read as recent FINANCIAL/OWNERSHIP
    ACTIVITY, useful as a strain/refi signal — NOT "years owned."
  - OWNER TYPE: classified from OwnersName — individual / investor(LLC-Corp-LP) / trust / institutional.

⚠ CORRECTION 2026-08-14 (calibrated on a KNOWN-TRUTH parcel): this map ORIGINALLY labeled the date as
"tenure / years held." That was WRONG on two counts, caught when 2811 Benvenue (owned since 1988) showed
as "5 yr": (1) the old source (owners CSV 'LatestDocu') is a STALE 2017-capped extract; (2) more
fundamentally, LatestDocumentDate is the last recorded document of ANY kind — the 2020-22 values are
the pandemic REFINANCE boom (2021 alone = ~9% of parcels, impossible as sales), NOT acquisitions.
A refi/trust transfer resets the date without changing ownership, so "years owned" is systematically
understated. TRUE years-owned needs the County Recorder deed index WITH document type (grant deed = sale
vs deed of trust = loan) — the Phase-2 deed-history acquisition. Here we now use the FRESH berkeley.db
date and label it honestly as recording recency.

OWNER-NAME/TYPE still come from the owners CSV (the county Assessor site hides owner names; the CSV is
the ArcGIS TaxParcel owner layer). Its NAMES are usable; its DATE column is not (superseded above).

Inputs: data/reference/berkeley_parcel_owners_2026-08-13.csv (APN,OwnersName) + committed taxparcels
geometry + databases/berkeley.db (LatestDocumentDate, situs address).
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
    # address + FRESH recorded-document date per parcel from berkeley.db (the CSV date is stale+invalid — see docstring)
    import sqlite3
    _adf = pd.read_sql("SELECT APN, SitusStree, SitusStr_1, LatestDocumentDate FROM parcels", sqlite3.connect("databases/berkeley.db"))
    _adf["capn"] = _adf.APN.apply(lambda a: to_canonical_apn(a, "alameda") if pd.notna(a) else None)
    _adf["addr"] = (_adf.SitusStree.fillna("").astype(str).str.strip() + " " + _adf.SitusStr_1.fillna("").astype(str).str.strip()).str.strip()
    _dy = pd.to_datetime(_adf.LatestDocumentDate, errors="coerce").dt.year         # 1900-01-01 = NULL placeholder
    _adf["recency"] = (2026 - _dy).where(_dy.between(1901, 2026))                   # YEARS SINCE LAST RECORDED DOCUMENT (not tenure)
    ow = ow.merge(_adf.dropna(subset=["capn"]).drop_duplicates("capn")[["capn", "addr", "recency"]], on="capn", how="left")
    g = tp.merge(ow[["capn", "otype", "recency", "OwnersName", "addr"]].dropna(subset=["capn"]).drop_duplicates("capn"), on="capn", how="inner")
    g = g[g.recency.notna()].to_crs(4326)
    c = g.geometry.centroid
    # inline parcel card (built/use/assessed) from parcel_facts.db — consistent across all 3 maps
    _pf = pd.read_sql("SELECT capn, use_bucket, build_year, assessed_total FROM parcel_facts",
                      sqlite3.connect("databases/parcel_facts.db"))
    PF = {r.capn: (r.use_bucket, r.build_year, r.assessed_total) for r in _pf.itertuples()}
    def _card(cp):
        t = PF.get(cp)
        if not t: return {"ub": "", "yb": 0, "av": 0}
        ub, yb, av = t
        return {"ub": "" if pd.isna(ub) else str(ub), "yb": int(yb) if pd.notna(yb) else 0,
                "av": int(av / 1000) if pd.notna(av) else 0}
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(x, 5), round(y, 5)]},
              "properties": {"t": int(min(t, 99)), "o": int(o),
                             "a": str(ad) if pd.notna(ad) else "", "n": str(nm) if pd.notna(nm) else "",
                             **_card(cp)}}
             for x, y, t, o, ad, nm, cp in zip(c.x, c.y, g.recency, g.otype, g.addr, g.OwnersName, g.capn)]
    counts = pd.Series([f["properties"]["o"] for f in feats]).value_counts().to_dict()
    lab = {0: "individual", 1: "investor (LLC/Corp/LP)", 2: "trust", 3: "institutional"}
    print(f"parcels mapped: {len(feats)} | owner types: " + ", ".join(f"{lab[k]}={counts.get(k,0)}" for k in range(4)))
    print(f"  median years-since-last-recorded-document: {pd.Series([f['properties']['t'] for f in feats]).median():.0f} yr")
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
<div style="margin:6px 0"><button id="bT" class="on" onclick="mode('t')">Last recorded document</button><button id="bO" onclick="mode('o')">Owner type</button></div>
<div id="legend"></div>
<div class="cap" id="cap">Color = years since the last document (sale, refinance, or transfer) was recorded — a recent-financial-activity signal, NOT years owned. Elmwood outlined.</div></div>
<script>
let FEATS={features:[]};
const TEN=['step',['get','t'],'#d7301f',5,'#fd8d3c',15,'#fee391',30,'#74add1',60,'#4575b4'];
const OWN=['match',['get','o'],1,'#d7301f',2,'#984ea3',3,'#377eb8','#bdbdbd'];
const LT='<div style="font-weight:600;margin-bottom:2px">Yrs since last recorded document</div><div><span class="sw" style="background:#d7301f"></span>&lt;5 yr (recent sale/refi/transfer)</div><div><span class="sw" style="background:#fd8d3c"></span>5-15</div><div><span class="sw" style="background:#fee391"></span>15-30</div><div><span class="sw" style="background:#74add1"></span>30-60</div><div><span class="sw" style="background:#4575b4"></span>60+ (no recording in decades)</div>';
const LO='<div><span class="sw" style="background:#bdbdbd"></span>individual</div><div><span class="sw" style="background:#d7301f"></span>investor (LLC/Corp/LP)</div><div><span class="sw" style="background:#984ea3"></span>trust</div><div><span class="sw" style="background:#377eb8"></span>institutional</div>';
const map=new maplibregl.Map({container:'map',center:[-122.273,37.871],zoom:12.4,
 style:{version:8,sources:{c:{type:'raster',tiles:['https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OSM © CARTO'}},layers:[{id:'bg',type:'raster',source:'c'}]}});
function mode(m){
  document.getElementById('bT').className=m=='t'?'on':''; document.getElementById('bO').className=m=='o'?'on':'';
  map.setPaintProperty('pts','circle-color', m=='t'?TEN:OWN);
  document.getElementById('legend').innerHTML = m=='t'?LT:LO;
  document.getElementById('cap').textContent = m=='t'? 'Color = years since the last document (sale, refinance, or transfer) was recorded on the parcel — the 2020-22 wave is the pandemic refi boom. A recent-financial-activity signal, NOT years owned. Elmwood outlined.' : 'Color = owner type, classified from the owner name. Trust is separated from investor (most trusts are family estate-planning). Elmwood outlined.';
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
     '<b>'+a+'</b>'+(p.n?'<br>owner: '+p.n:'')+' <span style="color:#777">('+TY[p.o]+')</span>'
     +(p.yb?'<br>built: '+p.yb:'')+(p.ub?' &middot; '+p.ub.replace(/_/g,' '):'')
     +(p.av?'<br>assessed value: $'+(p.av*1000).toLocaleString():'')
     +'<br>last recorded document: '+(2026-p.t)+' ('+p.t+' yr ago)'
     +'<br><a href="https://www.google.com/maps/search/?api=1&query='+q+'" target="_blank" rel="noopener">Street view ↗</a>').addTo(map); });
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
