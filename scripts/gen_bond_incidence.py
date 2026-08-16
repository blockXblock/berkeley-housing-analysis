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

    # ---- inline parcel card from parcel_facts.db (owner + use + build year) ----
    # propinfo.acgov.org (assessor/tax record) can't be deep-linked and hides owner names, so we show the
    # county-record facts INLINE in the popup. Built by scripts/build_parcel_facts.py.
    from housing_rules import to_canonical_apn
    p["capn"] = p.APN.apply(lambda a: to_canonical_apn(a, "alameda") if pd.notna(a) else None)
    pf = pd.read_sql("SELECT capn, owner_name, owner_type, use_bucket, build_year, owner_occupied FROM parcel_facts",
                     sqlite3.connect("databases/parcel_facts.db"))
    p = p.merge(pf.drop_duplicates("capn"), on="capn", how="left")
    p["owner_occupied"] = p.owner_occupied.fillna(0).astype(int)

    # ---- OFFICIAL figures: single source of truth is B2050BIS's reconciliation baseline (CONTRACT: the map
    #      READS official numbers, never hardcodes them). Fallback to the 5%/30yr assumption if it's absent. ----
    BASELINE = "data/baselines/measure_u_reconciliation_baseline_2026-08-15.json"
    OFF = {}
    if os.path.exists(BASELINE):
        _b = json.load(open(BASELINE)); OFF = {**_b.get("official", {}), **_b.get("derived", {})}

    # ---- the levy math (today's-base rate reconciled to the baseline; else 5%/30yr) ----
    tot_av = p.TotalNetValue.sum()
    rate = (OFF["rate_today_100k"] / 1e5) if OFF.get("rate_today_100k") else \
           (PRINCIPAL * INTEREST / (1 - (1 + INTEREST) ** -TERM_YEARS)) / tot_av
    annual = rate * tot_av                                                # peak-year debt service on TODAY's base
    n = len(p)
    p["cost_av"] = (rate * p.TotalNetValue).round(0)                      # ad-valorem annual cost (today's-base rate)
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
        "rate_today": round(OFF.get("rate_today_100k", rate * 1e5), 1),
        "rate_peak": OFF.get("peak_rate_100k", 0), "rate_avg": OFF.get("avg_rate_100k", 0),
        "base_mult": round(OFF.get("base_avg_multiple", 0), 2), "peak_fy": OFF.get("peak_first_fy", 0),
        # who pays: owner-occupied share of the bond. READ the gated figure from B2050BIS's baseline
        # (owner_occupied_share_pct, derived from the same $7k-exemption definition) so map + site show ONE
        # number; fall back to computing it if the baseline is absent.
        "oo_share": round(OFF.get("owner_occupied_share_pct",
                          100 * p.loc[p.owner_occupied == 1, "cost_av"].sum() / p.cost_av.sum()), 1),
        "n_parcels": n, "flat_lit": round(OFF.get("flat_parcel_cost", cost_flat)),
        # concentration + top-1% composition (from B2050BIS baseline)
        "top1": round(OFF.get("top1_share_pct", 0), 1), "top10": round(OFF.get("top10_share_pct", 0), 1),
        "bottom50": round(100 - OFF.get("top50_share_pct", 0), 1), "apt_share": round(OFF.get("apt_share_pct", 0), 1),
        "tier1": (OFF.get("tier_composition_av_pct", {}) or {}).get("1", {}),
        "tier1_entry": OFF.get("tier_entry_av", {}).get("1", 0) if OFF.get("tier_entry_av") else 0,
        "tier1_sfr_n": (OFF.get("tier_composition_count", {}) or {}).get("1", {}).get("single_family", 0),
    }
    print(f"tax base (total AV): ${stats['base_b']:.2f}B over {n:,} parcels")
    print(f"today's-base rate (from baseline) = ${stats['rate_100k']:.0f}/$100k -> ${stats['annual_m']:.1f}M/yr peak DS; "
          f"city advertises ${stats['rate_avg']}/avg, ${stats['rate_peak']}/peak (base {stats['base_mult']}x today)")
    print(f"ad-valorem annual cost: median ${stats['med_av']:.0f}, p10 ${stats['p10']:.0f}, "
          f"p90 ${stats['p90']:.0f}  ({stats['ineq']:.0f}x spread)")
    print(f"flat parcel tax (same $): ${cost_flat}/parcel (uniform)")
    print(f"recorded a document in last 5yr (refi/transfer/sale): {recent5:.0f}% of parcels")

    def _s(v): return "" if pd.isna(v) else str(v)
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(x, 5), round(y, 5)]},
              "properties": {"v": int(av / 1000), "c": int(c), "d": int(d), "t": int(t) if pd.notna(t) else -1,
                             "a": a, "own": _s(ow), "ot": _s(otp), "ub": _s(ub),
                             "yb": int(yb) if pd.notna(yb) else 0, "oo": int(oo)}}
             for x, y, av, c, d, t, a, ow, otp, ub, yb, oo in zip(
                 p.Longitude, p.Latitude, p.TotalNetValue, p.cost_av, p.delta, p.tenure, p.addr,
                 p.owner_name, p.owner_type, p.use_bucket, p.build_year, p.owner_occupied)]

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
.stat{background:#f4f4f4;border-radius:6px;padding:7px 9px;margin-top:8px;font-size:12px}
.tag{background:#111;color:#fff;border-radius:6px;padding:8px 11px;margin:-2px 0 8px;font-size:12.5px;line-height:1.35}
.who{background:#fff7ec;border:1px solid #f0d8b0;border-radius:6px;padding:8px 10px;margin-top:8px;font-size:11.5px;line-height:1.4}</style></head>
<body><div id="map"></div>
<div class="panel">
<div class="tag">🔎 Every dot is a parcel — click it for its <b>property tax, owner, and bond cost</b>. Find where you live.</div>
<h3>Measure U — a new $300M city bond</h3>
<div class="sub">Levied on <b>$__BASE__B</b> of assessed value; peak debt service ≈ $__ANNUAL__M/yr. The city advertises <b>$__AVG__ per $100k</b> average; on <i>today's</i> base the same bond is <b>$__RATE__</b>. Costs below are the actual annual dollars per parcel — toggle the rate to see the city's figures.</div>
<div style="margin:8px 0 2px"><b>Color each parcel by:</b></div>
<div>
<button id="b_c" class="on" onclick="mode('c')">Annual $ cost</button>
<button id="b_o" onclick="mode('o')">Owner-occupied vs rental</button>
<button id="b_d" onclick="mode('d')">Flat vs ad-valorem</button>
<button id="b_t" onclick="mode('t')">Recorded-doc recency</button></div>
<div id="rates" style="margin:6px 0 2px"><span class="sub">rate:</span>
<button id="r_today" class="on" onclick="setRate(S.rate_today)">today $__RATE__</button>
<button id="r_peak" onclick="setRate(S.rate_peak)">city peak $__PEAK__</button>
<button id="r_avg" onclick="setRate(S.rate_avg)">city avg $__AVG__</button></div>
<div id="legend"></div>
<div class="stat" id="stat"></div>
<div class="cap" id="cap"></div>
<div class="who" id="who"></div><div style="margin-top:8px;font-size:11px"><a href="https://www.sfchronicle.com/projects/2025/ca-property-map/" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:none">↗ Compare: SF Chronicle statewide owner map</a></div></div>
<script>
const S=__STATS__;
let FEATS={features:[]}, MODE='c', RATE=S.rate_today;
const usd=x=>'$'+Math.round(x).toLocaleString();
// cost = assessed value × rate/$100k. v = AV/1000, so cost = v × rate_per_100k / 100. Rate is selectable.
const costExpr=r=>['step',['*',['get','v'],r/100],'#2c7fb8',200,'#7fcdbb',500,'#ffffb2',1000,'#fd8d3c',2500,'#e31a1c'];
const DELTA=['step',['get','d'],'#b2182b',-400,'#ef8a62',-100,'#f7f7f7',100,'#67a9cf',400,'#2166ac']; // red=flat costs you MORE
const TEN=['step',['get','t'],'#e31a1c',5,'#fd8d3c',15,'#ffffb2',30,'#74add1',60,'#4575b4'];
const LC='<div><span class="sw" style="background:#2c7fb8"></span>&lt;$200/yr</div><div><span class="sw" style="background:#7fcdbb"></span>$200–500</div><div><span class="sw" style="background:#ffffb2"></span>$500–1,000</div><div><span class="sw" style="background:#fd8d3c"></span>$1,000–2,500</div><div><span class="sw" style="background:#e31a1c"></span>$2,500+ /yr</div>';
const LD='<div><span class="sw" style="background:#2166ac"></span>flat tax cheaper for you (high-value)</div><div><span class="sw" style="background:#f7f7f7;border:1px solid #ccc"></span>about the same</div><div><span class="sw" style="background:#b2182b"></span>flat tax costs you MORE (long-held/low-value)</div>';
const LT='<div><span class="sw" style="background:#e31a1c"></span>&lt;5 yr (recent sale/refi/transfer)</div><div><span class="sw" style="background:#fd8d3c"></span>5–15</div><div><span class="sw" style="background:#ffffb2"></span>15–30</div><div><span class="sw" style="background:#74add1"></span>30–60</div><div><span class="sw" style="background:#4575b4"></span>60+ (no recording in decades)</div>';
const CAPd='Same $300M raised as a FLAT parcel tax ('+usd(S.flat)+'/parcel). Red = you would pay MORE under a flat tax (long-held, low assessed value); blue = LESS (recent, high value). A flat tax shifts burden onto long-held owners.';
const CAPt='Years since the LAST RECORDED DOCUMENT (sale, refinance, transfer) — NOT years owned. The red 2020-22 bulge is the pandemic refinance wave (2811 Benvenue, owned since 1988, shows as 2021 from a refi/trust recording). A financial-activity signal, not tenure.';
const OO=['match',['get','oo'],1,'#1a9850','#e34a33'];
const LO='<div><span class="sw" style="background:#1a9850"></span>owner-occupied (has $7k homeowner\\'s exemption)</div><div><span class="sw" style="background:#e34a33"></span>rental / non-owner-occupied / commercial</div>';
const CAPo='Owner-occupied (green) vs everything else (red), flagged by the $7,000 homeowner\\'s exemption — a FLOOR (some owner-occupiers never file). Tax on rentals & commercial is largely passed through to tenants, so renters bear it indirectly.';
function rateLbl(){return RATE==S.rate_avg?'city avg $'+S.rate_avg:(RATE==S.rate_peak?'city peak $'+S.rate_peak:"today\\'s base $"+Math.round(S.rate_today));}
function rateNote(){
 if(RATE==S.rate_avg) return 'City-advertised AVERAGE ($'+S.rate_avg+'/$100k). It looks low only because it is levied on a projected ~'+S.base_mult.toFixed(1)+'× larger FUTURE base (Prop-13 growth from future sales + new construction). The same debt service on today\\'s base is $'+Math.round(S.rate_today)+'.';
 if(RATE==S.rate_peak) return 'City-disclosed PEAK ($'+S.rate_peak+'/$100k, first applying FY'+S.peak_fy+'-41). Still levied on a larger future base than today\\'s.';
 return 'TODAY\\'S-BASE rate ($'+Math.round(S.rate_today)+'/$100k): what current parcels would pay to service the bond now. The city advertises $'+S.rate_avg+' avg / $'+S.rate_peak+' peak — lower only because those assume a ~'+S.base_mult.toFixed(1)+'× larger future base.';
}
function stat(m){
 const f=RATE/S.rate_today;
 if(m=='c') return '<span class="big">'+usd(S.med_av*f)+'/yr</span> median parcel · '+rateLbl()+'<br>range '+usd(S.p10*f)+' – '+usd(S.p90*f)+' ('+Math.round(S.ineq)+'× spread for the same bond)';
 if(m=='o') return '<span class="big">'+S.oo_share+'%</span> of the bond falls on owner-occupied homes<br>the other '+(100-S.oo_share).toFixed(1)+'% is on rentals & commercial — largely tenant-borne via pass-through';
 if(m=='d') return '<span class="big">'+usd(S.flat_lit)+'/yr</span> flat, every parcel<br>vs ad-valorem median '+usd(S.med_av)+' — a flat tax is blind to value';
 return '<span class="big">'+Math.round(S.recent5)+'%</span> of parcels recorded a document in the last 5 years (the refi wave) — a financial-activity signal, <b>not</b> years owned';
}
function mode(m){ MODE=m;
 for(const k of ['c','o','d','t']) document.getElementById('b_'+k).className = k==m?'on':'';
 document.getElementById('rates').style.display = m=='c'?'block':'none';
 map.setPaintProperty('pts','circle-color', m=='c'?costExpr(RATE):m=='o'?OO:m=='d'?DELTA:TEN);
 document.getElementById('legend').innerHTML = m=='c'?LC:m=='o'?LO:m=='d'?LD:LT;
 document.getElementById('cap').innerHTML = m=='c'?('Ad-valorem: each parcel pays rate × its assessed value. <i>'+rateNote()+'</i>'):m=='o'?CAPo:m=='d'?CAPd:CAPt;
 document.getElementById('stat').innerHTML = stat(m);
}
function setRate(r){ RATE=r;
 document.getElementById('r_today').className=(Math.abs(r-S.rate_today)<1e-9)?'on':'';
 document.getElementById('r_peak').className=(r==S.rate_peak)?'on':'';
 document.getElementById('r_avg').className=(r==S.rate_avg)?'on':'';
 if(MODE=='c') mode('c');
}
(function(){ var w='<b>Who actually pays.</b> The bond is levied on <b>'+S.n_parcels.toLocaleString()+' taxable parcels</b> — not on Berkeley\\'s ~124,000 residents. Roughly 45,000 are UC students who rent or live in dorms and own no parcel; renters bear property tax only indirectly, through rent. The top 10% of parcels carry <b>'+S.top10+'%</b> of the bond; the bottom half pays <b>'+S.bottom50+'%</b>.';
 if(S.tier1&&S.tier1.apartments_mixed!==undefined) w+=' And the biggest payers are <b>not homeowners</b>: the top 1% (parcels over $'+(S.tier1_entry/1e6).toFixed(1)+'M assessed) are <b>'+Math.round(S.tier1.apartments_mixed)+'% apartment buildings, '+Math.round(S.tier1.commercial_industrial)+'% commercial, '+Math.round(S.tier1.institutional)+'% institutional</b> — just '+S.tier1_sfr_n+' single-family homes. Apartments alone are <b>'+S.apt_share+'%</b> of the bond, passed through to renters.';
 document.getElementById('who').innerHTML=w; })();
const map=new maplibregl.Map({container:'map',center:[-122.273,37.871],zoom:12.3,
 style:{version:8,sources:{c:{type:'raster',tiles:['https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OSM © CARTO'}},layers:[{id:'bg',type:'raster',source:'c'}]}});
map.on('load',()=>{
 map.addSource('el',{type:'geojson',data:__ELB__});
 map.addLayer({id:'elw',type:'line',source:'el',paint:{'line-color':'#111','line-width':1.5,'line-dasharray':[2,2]}});
 map.addSource('p',{type:'geojson',data:'bond_incidence_data.json'});
 map.addLayer({id:'pts',type:'circle',source:'p',paint:{'circle-radius':['interpolate',['linear'],['zoom'],11,1.6,15,4.5],'circle-color':costExpr(S.rate_today),'circle-opacity':0.82}});
 fetch('bond_incidence_data.json').then(r=>r.json()).then(d=>{FEATS=d;}); mode('c');
 map.on('click','pts',e=>{const p=e.features[0].properties,a=p.a||'(address unavailable)';
   const t=p.t<0?'unknown':(2026-p.t)+' ('+p.t+' yr ago)';
   const q=encodeURIComponent(a+' Berkeley CA');
   new maplibregl.Popup().setLngLat(e.lngLat).setHTML(
     '<b>'+a+'</b>'
     +(p.own?'<br>owner: '+p.own+(p.ot?' <span style="color:#777">('+p.ot+')</span>':''):'')
     +(p.yb?'<br>built: '+p.yb:'')+(p.ub?' &middot; '+p.ub.replace(/_/g,' '):'')
     +(p.oo?'<br><span style="color:#1a9850">owner-occupied</span> (homeowner\\'s exemption)':'<br><span style="color:#c0392b">rental / non-owner-occupied</span>')
     +'<br>assessed value: '+usd(p.v*1000)
     +'<hr style="margin:5px 0;border:none;border-top:1px solid #ddd">'
     +'your Measure U bond cost: <b>'+usd(p.v*RATE/100)+'/yr</b> <span style="color:#777">('+rateLbl()+')</span>'
     +'<br>if it were a flat parcel tax: '+usd(S.flat_lit)+'/yr'
     +'<br>last recorded document: '+t
     +'<br><a href="https://www.google.com/maps/search/?api=1&query='+q+'" target="_blank" rel="noopener">Street view ↗</a>'
     ).addTo(map);});
 map.on('mouseenter','pts',()=>map.getCanvas().style.cursor='pointer');
 map.on('mouseleave','pts',()=>map.getCanvas().style.cursor='');
});
</script></body></html>""".replace("__ELB__", json.dumps(elb)).replace("__STATS__", js_stats) \
        .replace("__ANNUAL__", f"{stats['annual_m']:.1f}").replace("__BASE__", f"{stats['base_b']:.0f}") \
        .replace("__RATE__", f"{stats['rate_100k']:.0f}") \
        .replace("__PEAK__", f"{stats['rate_peak']:.0f}").replace("__AVG__", f"{stats['rate_avg']:.0f}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"type": "FeatureCollection", "features": feats}, open(DATA, "w"))
    open(OUT, "w").write(html)
    print(f"\nwrote {OUT} ({round(len(html)/1024)} KB) + {DATA} ({round(os.path.getsize(DATA)/1e6,1)} MB)")

if __name__ == "__main__":
    main()
