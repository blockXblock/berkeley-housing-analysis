#!/usr/bin/env python3
"""gen_bond_incidence.py — PROTOTYPE lead visual for the Berkeley bond op-ed.

Question: what would a new $300M city bond cost each property owner, and how unequally?
A GO bond is repaid by an ad-valorem debt-service rate = annual_debt_service / total_assessed_value.
Per parcel: cost = rate x assessed_value. Because assessed value is acquisition-based (Prop 13,
frozen +2%/yr until sale), an ad-valorem bond falls FAR harder on recent buyers than long-held owners
for the SAME house. The alternative — a flat parcel tax — is uniform per parcel. This map lets a
narrator explore both, parcel by parcel.

DATA (all in-hand, read-only): databases/berkeley.db parcels — TotalNetValue (assessed value = base),
Latitude/Longitude, situs address, LatestDocumentDate. ⚠ LatestDocumentDate is the LAST RECORDED
DOCUMENT of any kind (sale, REFINANCE, trust transfer) — NOT years owned. Calibrated on 2811 Benvenue
(owned since 1988, last doc 2021 = a refi/trust recording, not a sale). The map's 3rd mode shows this
honestly as "recording recency" (a refi/financial-activity signal). TRUE years-owned needs the deed
index with document type (Phase-2 acquisition). The ad-valorem incidence itself does NOT depend on it —
it rests on assessed value, which is the real Prop-13 base.

HONESTY RAILS: (1) Assessed value != market value (Prop 13) — this is the point, not a bug, but the
AV distribution is NOT a wealth distribution. (2) Exemptions (homeowner's $7k, nonprofit, veteran) are
NOT modeled in v1 — the base is gross TotalNetValue. (3) The bond's annual debt service assumes 30yr
@ 5% level payments — an explicit, adjustable assumption printed below. (4) This uses TOTAL citywide AV
as the district base; the exact figure must be validated against the county tax-rate book + actual
bills before publication. Directionally honest; not a certified rate.

Output: docs/maps/bond_incidence.html (+ _data.json). Serve to view (file:// blocks the streamed fetch).
"""
import sqlite3, json, os, sys, warnings
import pandas as pd, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0, "scripts")

# ---- bond assumptions (explicit, adjustable) ----
PRINCIPAL = 300_000_000      # $300M
TERM_YEARS = 30
INTEREST = 0.05
OUT = "docs/maps/bond_incidence.html"
DATA = "docs/maps/bond_incidence_data.json"   # streamed sibling (serve; file:// blocks the fetch)

def main():
    db = sqlite3.connect("databases/berkeley.db")
    p = pd.read_sql("SELECT APN,Latitude,Longitude,Land,Imps,TotalNetValue,SitusStree,SitusStr_1,"
                    "LatestDocumentDate,UseCode FROM parcels", db)
    for c in ["Latitude", "Longitude", "Land", "Imps", "TotalNetValue"]:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    p = p[(p.TotalNetValue > 0) & p.Latitude.between(37.8, 37.95) & p.Longitude.between(-122.35, -122.2)].copy()
    yr = pd.to_datetime(p.LatestDocumentDate, errors="coerce").dt.year
    # 1900-01-01 is the county's NULL placeholder -> treat as unknown tenure, not "126 yr"
    p["tenure"] = (2026 - yr).where(yr.between(1901, 2026)).clip(0, 99)
    p["addr"] = (p.SitusStree.fillna("").astype(str).str.strip() + " " +
                 p.SitusStr_1.fillna("").astype(str).str.strip()).str.strip()

    # ---- the levy math ----
    tot_av = p.TotalNetValue.sum()
    annual = PRINCIPAL * INTEREST / (1 - (1 + INTEREST) ** -TERM_YEARS)   # level debt service
    rate = annual / tot_av                                                # $ per $1 AV
    n = len(p)
    p["cost_av"] = (rate * p.TotalNetValue).round(0)                      # ad-valorem annual cost
    cost_flat = round(annual / n)                                          # flat parcel-tax annual cost
    p["delta"] = cost_flat - p.cost_av        # >0: flat costs you MORE (low-AV long-held); <0: flat cheaper

    # ---- headline stats (DERIVED, printed + injected — never hardcoded in the HTML) ----
    # NOTE: `tenure` here is YEARS SINCE LAST RECORDED DOCUMENT (refi/transfer/sale), NOT years owned.
    # We do NOT compute a "recent-buyer vs long-held" cost ratio off it — that would mislabel refinancers
    # as recent buyers (retracted 2026-08-14 after 2811 Benvenue, owned since 1988, showed as 5 yr).
    recent5 = float((p.tenure < 5).mean() * 100)      # % of parcels with a recording in the last 5 yr (the refi wave)
    stats = {
        "base_b": tot_av / 1e9, "annual_m": annual / 1e6, "rate_100k": rate * 100_000,
        "n": n, "med_av": p.cost_av.median(), "p10": p.cost_av.quantile(.10), "p90": p.cost_av.quantile(.90),
        "flat": cost_flat, "ineq": p.cost_av.quantile(.90) / max(p.cost_av.quantile(.10), 1),
        "recent5": recent5,
    }
    print(f"tax base (total AV): ${stats['base_b']:.2f}B over {n:,} parcels")
    print(f"$300M / 30yr / 5% -> ${stats['annual_m']:.1f}M annual debt service; "
          f"ad-valorem rate = ${stats['rate_100k']:.0f} per $100k AV")
    print(f"ad-valorem annual cost: median ${stats['med_av']:.0f}, p10 ${stats['p10']:.0f}, "
          f"p90 ${stats['p90']:.0f}  ({stats['ineq']:.0f}x spread)")
    print(f"flat parcel tax (same $): ${cost_flat}/parcel (uniform)")
    print(f"recorded a document in last 5yr (refi/transfer/sale): {recent5:.0f}% of parcels")

    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(x, 5), round(y, 5)]},
              "properties": {"v": int(av / 1000), "c": int(c), "d": int(d), "t": int(t) if pd.notna(t) else -1,
                             "a": a}}
             for x, y, av, c, d, t, a in zip(p.Longitude, p.Latitude, p.TotalNetValue, p.cost_av,
                                             p.delta, p.tenure, p.addr)]

    import geopandas as gpd
    el = gpd.read_file("data/reference/berkeley_neighborhoods.geojson").to_crs(4326)
    elb = json.loads(el[el.Name.astype(str).str.contains("lmwood", case=False)][["geometry"]].to_json())

    js_stats = json.dumps({k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in stats.items()})
    html = """<!doctype html><html><head><meta charset="utf-8"><title>What a $300M bond costs each owner</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<style>body,html,#map{margin:0;height:100%;font-family:system-ui}
.panel{position:absolute;top:12px;left:12px;width:340px;background:rgba(255,255,255,.95);padding:12px 15px;border-radius:8px;box-shadow:0 1px 8px rgba(0,0,0,.35);font-size:13px}
.panel h3{margin:0 0 6px} .panel button{font-size:12px;padding:5px 9px;margin:2px 3px 2px 0;cursor:pointer;border:1px solid #999;background:#fff;border-radius:5px}
.panel button.on{background:#111;color:#fff;border-color:#111}
.big{font-size:22px;font-weight:700} .sub{color:#555;font-size:11px}
#legend{margin-top:8px} .sw{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:5px;vertical-align:middle}
.cap{color:#444;font-size:11px;margin-top:8px;line-height:1.35}
.stat{background:#f4f4f4;border-radius:6px;padding:7px 9px;margin-top:8px;font-size:12px}</style></head>
<body><div id="map"></div>
<div class="panel"><h3>A new $300M city bond</h3>
<div class="sub">$300M · 30 yr · 5% → __ANNUAL__M/yr, spread across __BASE__B of assessed value = <b>$__RATE__ per $100,000</b> of assessed value.</div>
<div style="margin:8px 0 2px"><b>Show each parcel by:</b></div>
<div>
<button id="b_c" class="on" onclick="mode('c')">Annual cost (ad-valorem bond)</button>
<button id="b_d" onclick="mode('d')">Flat-tax vs ad-valorem</button>
<button id="b_t" onclick="mode('t')">Last recorded document (refi/transfer)</button></div>
<div id="legend"></div>
<div class="stat" id="stat"></div>
<div class="cap" id="cap"></div></div>
<script>
const S=__STATS__;
let FEATS={features:[]};
const usd=x=>'$'+Math.round(x).toLocaleString();
const COST=['step',['get','c'],'#2c7fb8',200,'#7fcdbb',500,'#ffffb2',1000,'#fd8d3c',2500,'#e31a1c'];
const DELTA=['step',['get','d'],'#b2182b',-400,'#ef8a62',-100,'#f7f7f7',100,'#67a9cf',400,'#2166ac']; // red=flat costs you MORE
const TEN=['step',['get','t'],'#e31a1c',5,'#fd8d3c',15,'#ffffb2',30,'#74add1',60,'#4575b4'];
const LC='<div><span class="sw" style="background:#2c7fb8"></span>&lt;$200/yr</div><div><span class="sw" style="background:#7fcdbb"></span>$200–500</div><div><span class="sw" style="background:#ffffb2"></span>$500–1,000</div><div><span class="sw" style="background:#fd8d3c"></span>$1,000–2,500</div><div><span class="sw" style="background:#e31a1c"></span>$2,500+ /yr</div>';
const LD='<div><span class="sw" style="background:#2166ac"></span>flat tax cheaper for you (you\\'re high-value)</div><div><span class="sw" style="background:#f7f7f7;border:1px solid #ccc"></span>about the same</div><div><span class="sw" style="background:#b2182b"></span>flat tax costs you MORE (you\\'re long-held/low-value)</div>';
const LT='<div><span class="sw" style="background:#e31a1c"></span>&lt;5 yr (recent sale/refi/transfer)</div><div><span class="sw" style="background:#fd8d3c"></span>5–15</div><div><span class="sw" style="background:#ffffb2"></span>15–30</div><div><span class="sw" style="background:#74add1"></span>30–60</div><div><span class="sw" style="background:#4575b4"></span>60+ (no recording in decades)</div>';
const CAP={
 c:'Ad-valorem bond: each parcel pays rate × its assessed value. Red parcels — recently sold, high assessed value — pay many times what pale long-held parcels pay for the identical bond.',
 d:'Same $300M raised as a FLAT parcel tax ('+usd(S.flat)+'/parcel). Red = you\\'d pay MORE under a flat tax (long-held, low assessed value); blue = you\\'d pay LESS (recent, high value). The flat tax shifts burden onto long-held owners.',
 t:'Years since the LAST RECORDED DOCUMENT (sale, refinance, or transfer) — NOT years owned. The red 2020-22 bulge is the pandemic refinance wave (2811 Benvenue, owned since 1988, shows here as 2021 from a refi/trust recording). Read as recent financial/ownership activity — a strain/leverage signal — not tenure.'};
function stat(m){
 if(m=='c') return '<span class="big">'+usd(S.med_av)+'/yr</span> median parcel<br>'+
   'range '+usd(S.p10)+' – '+usd(S.p90)+' (a '+Math.round(S.ineq)+'× spread for the same bond)';
 if(m=='d') return '<span class="big">'+usd(S.flat)+'/yr</span> flat, every parcel<br>vs ad-valorem median '+usd(S.med_av)+' — flat tax is uniform by parcel, blind to value';
 return '<span class="big">'+Math.round(S.recent5)+'%</span> of parcels recorded a document in the last 5 years (the refi wave) — a financial-activity signal, <b>not</b> years owned';
}
function mode(m){
 for(const k of ['c','d','t']) document.getElementById('b_'+k).className = k==m?'on':'';
 map.setPaintProperty('pts','circle-color', m=='c'?COST:m=='d'?DELTA:TEN);
 document.getElementById('legend').innerHTML = m=='c'?LC:m=='d'?LD:LT;
 document.getElementById('cap').textContent = CAP[m];
 document.getElementById('stat').innerHTML = stat(m);
}
const map=new maplibregl.Map({container:'map',center:[-122.273,37.871],zoom:12.3,
 style:{version:8,sources:{c:{type:'raster',tiles:['https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OSM © CARTO'}},layers:[{id:'bg',type:'raster',source:'c'}]}});
map.on('load',()=>{
 map.addSource('el',{type:'geojson',data:__ELB__});
 map.addLayer({id:'elw',type:'line',source:'el',paint:{'line-color':'#111','line-width':1.5,'line-dasharray':[2,2]}});
 map.addSource('p',{type:'geojson',data:'bond_incidence_data.json'});
 map.addLayer({id:'pts',type:'circle',source:'p',paint:{'circle-radius':['interpolate',['linear'],['zoom'],11,1.6,15,4.5],'circle-color':COST,'circle-opacity':0.82}});
 fetch('bond_incidence_data.json').then(r=>r.json()).then(d=>{FEATS=d;}); mode('c');
 map.on('click','pts',e=>{const p=e.features[0].properties,a=p.a||'(address unavailable)';
   const t=p.t<0?'unknown':(2026-p.t)+' ('+p.t+' yr ago)';
   new maplibregl.Popup().setLngLat(e.lngLat).setHTML(
     '<b>'+a+'</b><br>assessed value: '+usd(p.v*1000)
     +'<br>ad-valorem bond: <b>'+usd(p.c)+'/yr</b>'
     +'<br>flat parcel tax: '+usd(S.flat)+'/yr'
     +'<br>last recorded document: '+t).addTo(map);});
 map.on('mouseenter','pts',()=>map.getCanvas().style.cursor='pointer');
 map.on('mouseleave','pts',()=>map.getCanvas().style.cursor='');
});
</script></body></html>""".replace("__ELB__", json.dumps(elb)).replace("__STATS__", js_stats) \
        .replace("__ANNUAL__", f"{stats['annual_m']:.1f}").replace("__BASE__", f"{stats['base_b']:.0f}") \
        .replace("__RATE__", f"{stats['rate_100k']:.0f}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"type": "FeatureCollection", "features": feats}, open(DATA, "w"))
    open(OUT, "w").write(html)
    print(f"\nwrote {OUT} ({round(len(html)/1024)} KB) + {DATA} ({round(os.path.getsize(DATA)/1e6,1)} MB)")

if __name__ == "__main__":
    main()
