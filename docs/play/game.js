// game.js -- "Can it pencil?" A Berkeley developer's game on the JN-O pencil-out model (pencil.js, a verified port).
import * as THREE from "three";
import { MapControls } from "three/addons/controls/MapControls.js";
import * as P from "./pencil.js";

const $ = s => document.querySelector(s);
const VEX = 1.6;                       // vertical exaggeration of the model, so heights read from above
const FT = 0.3048;
const BINS = [1.0, 1.15, 1.35, 1.75, 2.5];
const BIN_LABEL = ["pencils", "≤1.15×", "≤1.35×", "≤1.75×", "≤2.5×", ">2.5×"];
const store = {
  get(k, d) { try { const v = localStorage.getItem("pencil." + k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem("pencil." + k, JSON.stringify(v)); } catch { /* no storage: fine */ } },
};

// ------------------------------------------------------------------------------------------------ data
const data = await (await fetch("game_data.json")).json();
P.init(data);
const S = data.scenarios;
const { cols, cats, rows } = data.parcels;
const ix = Object.fromEntries(cols.map((c, i) => [c, i]));
const lat0 = 37.8705, lon0 = -122.2700, mx = 111320 * Math.cos(lat0 * Math.PI / 180), my = 110540;
const toXZ = (lat, lon) => [(lon - lon0) * mx, -(lat - lat0) * my];
const sites = rows.map((r, i) => {
  const [x, z] = toXZ(r[ix.lat], r[ix.lon]);
  return { i, key: r[ix.key], name: r[ix.name], lat: r[ix.lat], lon: r[ix.lon], lot_sf: r[ix.lot_sf], building_sf: r[ix.building_sf],
    bucket: cats.bucket[r[ix.bucket]], nb: cats.nb[r[ix.nb]], district: cats.district[r[ix.district]], fire: cats.fire[r[ix.fire]],
    landmark: !!r[ix.landmark], exempt: !!r[ix.exempt], rental_units: r[ix.rental_units], rent_factor: r[ix.rent_factor],
    euv: { low: r[ix.euv][0], base: r[ix.euv][1], high: r[ix.euv][2] },
    py: { zoning: r[ix.py_z_in_lieu_base], bonus32: r[ix.py_z_on_site_base] }, x, z };
});
const pipeline = data.pipeline.filter(p => p.lat);
const featured = data.pipeline.find(p => p.group === "featured");

// ------------------------------------------------------------------------------------------------ market
const BAND = { rent_mult: [0.9, 1.1], cap: [0.05, 0.065], rate: [0.062, 0.08], hard_mult: [0.9, 1.18] };
let scenName = "base";
let market = { ...S.base };
const dials = [["rent_mult", "d_rent", "o_rent", v => v.toFixed(2) + "×"], ["cap", "d_cap", "o_cap", v => (v * 100).toFixed(2) + "%"],
  ["rate", "d_rate", "o_rate", v => (v * 100).toFixed(2) + "%"], ["hard_mult", "d_hard", "o_hard", v => v.toFixed(2) + "×"]];
const inBand = () => dials.every(([k]) => market[k] >= BAND[k][0] - 1e-9 && market[k] <= BAND[k][1] + 1e-9);
const isBase = () => scenName === "base" && dials.every(([k]) => Math.abs(market[k] - S.base[k]) < 1e-9);
function syncDials() {
  for (const [k, id, oid, fmt] of dials) {
    $("#" + id).value = market[k]; const o = $("#" + oid); o.textContent = fmt(market[k]);
    o.classList.toggle("out", market[k] < BAND[k][0] - 1e-9 || market[k] > BAND[k][1] + 1e-9);
  }
  for (const b of $("#scen").children) b.setAttribute("aria-pressed", String(b.dataset.scen === scenName && dials.every(([k]) => Math.abs(market[k] - S[scenName][k]) < 1e-9)));
  const note = $("#bandnote");
  note.classList.toggle("out", !inBand());
  note.textContent = inBand()
    ? "Every dial is inside the range the model's sources support (pencil_out_2026-10-25.yaml)."
    : "A dial is outside its sourced range: results are a what-if, and don't count toward the portfolio mission.";
}
for (const [k, id] of dials) {
  $("#" + id).addEventListener("input", e => { market[k] = +e.target.value; scenName = "custom"; syncDials(); refreshCard(); });
  $("#" + id).addEventListener("change", () => recolor());
}
$("#scen").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  scenName = b.dataset.scen; market = { ...S[scenName] }; syncDials(); refreshCard(); recolor();
});
$("#marketToggle").addEventListener("click", () => $("#market").classList.toggle("open"));

// ------------------------------------------------------------------------------------------------ theme
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let T = {};
function readTheme() {
  T = { bg: new THREE.Color(css("--bg")), ground: new THREE.Color(css("--ground")), block: new THREE.Color(css("--block")),
    accent: new THREE.Color(css("--accent")), retail: new THREE.Color(css("--retail")), none: new THREE.Color(css("--pnone")),
    p: ["--p0", "--p1", "--p2", "--p3", "--p4", "--p5"].map(v => new THREE.Color(css(v))), ink: new THREE.Color(css("--ink")) };
}
readTheme();

// ------------------------------------------------------------------------------------------------ scene
const host = $("#scene");
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(host.clientWidth, host.clientHeight);
host.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, host.clientWidth / host.clientHeight, 5, 40000);
const controls = new MapControls(camera, renderer.domElement);
controls.enableDamping = true; controls.maxPolarAngle = 1.3; controls.minDistance = 120; controls.maxDistance = 14000;
camera.position.set(400, 5200, 5600); controls.target.set(300, 0, -200);
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a929a, 1.7));
const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-2000, 4000, 1500); scene.add(sun);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(30000, 30000), new THREE.MeshLambertMaterial());
ground.rotation.x = -Math.PI / 2; ground.position.y = -0.5; scene.add(ground);

// parcels: one instanced box each, footprint from the lot, height from the existing building
const box = new THREE.BoxGeometry(1, 1, 1); box.translate(0, 0.5, 0);
const parcels = new THREE.InstancedMesh(box, new THREE.MeshLambertMaterial(), sites.length);
const m4 = new THREE.Matrix4(), q0 = new THREE.Quaternion();
function existingHeight(s) {
  const stories = Math.min(12, Math.max(0.25, s.building_sf / Math.max(1, s.lot_sf * 0.55)));
  return Math.max(1.5, stories * 3.1 * VEX);
}
function placeParcel(s, hide = false) {
  const w = Math.sqrt(s.lot_sf) * FT * 0.82;
  m4.compose(new THREE.Vector3(s.x, 0, s.z), q0, new THREE.Vector3(w, hide ? 0.01 : existingHeight(s), w));
  parcels.setMatrixAt(s.i, m4);
}
sites.forEach(s => placeParcel(s));
scene.add(parcels);

// BART stations and their SB 79 rings (1/4 and 1/2 mile; within 200 ft)
const rings = new THREE.Group(); scene.add(rings);
const stationMat = new THREE.MeshLambertMaterial();
function label(text, scale = 1) {
  const c = document.createElement("canvas"), g = c.getContext("2d"), f = 44;
  g.font = `800 ${f}px "Big Shoulders Display", "Arial Narrow", sans-serif`;
  c.width = Math.ceil(g.measureText(text).width) + 28; c.height = f + 22;
  g.font = `800 ${f}px "Big Shoulders Display", "Arial Narrow", sans-serif`;
  g.fillStyle = css("--panel"); g.fillRect(0, 0, c.width, c.height);
  g.fillStyle = css("--ink"); g.textBaseline = "middle"; g.fillText(text, 14, c.height / 2 + 2);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false, sizeAttenuation: false }));
  sp.scale.set(0.034 * scale * c.width / c.height, 0.034 * scale, 1); sp.renderOrder = 10; sp.userData.text = text; sp.userData.scale = scale;
  return sp;
}
const labels = [];
for (const st of data.bart) {
  const [x, z] = toXZ(st.lat, st.lon);
  const m = new THREE.Mesh(new THREE.CylinderGeometry(40, 40, 160, 24), stationMat); m.position.set(x, 80, z); scene.add(m);
  const l = label(st.name + " BART", 0.9); l.position.set(x, 320, z); scene.add(l); labels.push(l);
  for (const [r, op] of [[200 * FT, 0.55], [0.25 * 1609.34, 0.35], [0.5 * 1609.34, 0.22]]) {
    const ring = new THREE.Mesh(new THREE.RingGeometry(r - 9, r + 9, 128), new THREE.MeshBasicMaterial({ transparent: true, opacity: op, depthWrite: false }));
    ring.rotation.x = -Math.PI / 2; ring.position.set(x, 1, z); rings.add(ring);
  }
}

// pipeline pins
const pins = new THREE.Group(); scene.add(pins);
const VERDICT_COLOR = { pencils: 0, marginal: 2, does_not: 4 };
for (const p of pipeline) {
  const [x, z] = toXZ(p.lat, p.lon), big = p.group === "featured";
  const g = new THREE.Group(); g.position.set(x, 0, z); g.userData.p = p;
  const mat = new THREE.MeshLambertMaterial();
  const stem = new THREE.Mesh(new THREE.CylinderGeometry(big ? 4 : 3, big ? 4 : 3, big ? 150 : 110, 8), mat); stem.position.y = big ? 75 : 55;
  const head = new THREE.Mesh(big ? new THREE.OctahedronGeometry(26) : new THREE.SphereGeometry(16, 16, 12), mat); head.position.y = big ? 175 : 125;
  g.add(stem, head); g.userData.mat = mat; g.userData.head = head; pins.add(g);
  if (big) { const l = label("2800 Telegraph", 1.1); l.position.set(0, 250, 0); g.add(l); labels.push(l); }
}

// the proposed building: floors stacked on the selected lot
const massing = new THREE.Group(); scene.add(massing);
const floorMat = new THREE.MeshLambertMaterial(), retailMat = new THREE.MeshLambertMaterial(), bmrMat = new THREE.MeshLambertMaterial();
const edgeMat = new THREE.LineBasicMaterial();
let hidden = null, rise = 1;
function showMassing(site, b, pencils) {
  massing.clear();
  if (hidden) placeParcel(hidden);
  hidden = site; placeParcel(site, true); parcels.instanceMatrix.needsUpdate = true;
  if (!b) return;
  const lotW = Math.sqrt(site.lot_sf) * FT;
  const retailGround = b.retail_sf > 0 || (b.lobby_sf || 0) > 0;
  const cov = b.res_gross / Math.max(1, (b.stories - (retailGround ? 1 : 0))) / site.lot_sf;
  const wUp = lotW * Math.sqrt(Math.min(0.95, Math.max(0.3, cov))), wG = lotW * 0.92;
  const bmrUnits = b.affordable ? Object.values(b.affordable).reduce((a, o) => a + Object.values(o).reduce((x, y) => x + y, 0), 0) : 0;
  const bmrFloors = Math.round(bmrUnits / Math.max(1, b.units) * (b.stories - (retailGround ? 1 : 0)));
  floorMat.color.copy(pencils ? T.p[0] : T.p[4]); retailMat.color.copy(T.retail); bmrMat.color.copy(T.accent); edgeMat.color.copy(T.ink);
  let y = 0;
  for (let k = 0; k < b.stories; k++) {
    const h = (k === 0 ? 15 : 10) * FT * VEX, ground = k === 0 && retailGround, w = ground ? wG : wUp;
    const mat = ground ? retailMat : (k >= b.stories - bmrFloors ? bmrMat : floorMat);
    const geo = new THREE.BoxGeometry(w, h * 0.94, w); geo.translate(0, h / 2, 0);
    const m = new THREE.Mesh(geo, mat); m.position.set(site.x, y, site.z); massing.add(m);
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(geo), edgeMat); e.position.copy(m.position); massing.add(e);
    y += h;
  }
  massing.position.y = 0; rise = 0;
}

function applyTheme() {
  readTheme();
  scene.background = T.bg; ground.material.color.copy(T.ground); stationMat.color.copy(T.accent);
  rings.children.forEach(r => r.material.color.copy(T.accent));
  for (const g of pins.children) {
    const p = g.userData.p;
    g.userData.mat.color.copy(p.group === "featured" ? T.accent : (p.verdict in VERDICT_COLOR ? T.p[VERDICT_COLOR[p.verdict]] : T.none));
  }
  for (const l of labels) { const n = label(l.userData.text, l.userData.scale); l.material.map.dispose(); l.material.map = n.material.map; l.scale.copy(n.scale); }
  paint(); refreshCard();
}
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme);
new MutationObserver(applyTheme).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

// ------------------------------------------------------------------------------------------------ lenses
let lens = "zoning";
let need = new Float32Array(sites.length).fill(NaN);     // NaN: not permitted / outside the lens
const binOf = v => (Number.isFinite(v) ? BINS.findIndex(t => v <= t) : -2);
function paint() {
  const c = new THREE.Color();
  for (const s of sites) {
    const b = binOf(need[s.i]);
    if (b === -2) c.copy(T.block).lerp(T.none, 0.6);
    else c.copy(T.p[b === -1 ? 5 : b]);
    parcels.setColorAt(s.i, c);
  }
  parcels.instanceColor.needsUpdate = true;
  rings.visible = lens === "sb79";
}
function bestDesign(site, o) {
  let best = null;
  for (let k = 2; k <= 12; k++) {
    const d = P.design(site, data, { ...o, stories: k });
    if (d.blocked) return best || d;
    if (d.stories < k) break;
    if (!best || best.blocked || d.need < best.need) best = d;
  }
  return best;
}
function lensNeed(site, s) {
  if (lens === "zoning" || lens === "bonus32") {
    const fm = lens === "zoning" ? "in_lieu" : "on_site";
    const env = P.allowedEnvelope(data.zoning.districts[site.district], fm, data.zoning.state_bonus);
    if (!env) return NaN;
    return P.bestRow(P.breakEven(site, s, fm, env).rows).rent_mult_needed;
  }
  if (lens === "sb79") {
    if (!P.sb79Band(site, data).band) return NaN;
    const d = bestDesign(site, { s, pathway: "sb79", layout: "apartments" });
    return d && !d.blocked ? d.need : NaN;
  }
  const d = bestDesign(site, { s, pathway: "zoning", layout: "beds" });
  return d && !d.blocked ? d.need : NaN;
}
let job = 0;
function recolor() {
  const my = ++job, s = { ...market }, bar = $("#progress i");
  if (isBase() && (lens === "zoning" || lens === "bonus32")) {      // the Python pass's own numbers
    for (const site of sites) need[site.i] = site.py[lens] ?? NaN;
    bar.style.width = "0"; paint(); missionsCheck(); return;
  }
  let i = 0;
  const step = () => {
    if (my !== job) return;
    const t = performance.now();
    while (i < sites.length && performance.now() - t < 24) { need[i] = lensNeed(sites[i], s); i++; }
    bar.style.width = (100 * i / sites.length) + "%";
    if (i % 4000 < 300 || i >= sites.length) paint();
    if (i < sites.length) requestAnimationFrame(step); else { bar.style.width = "0"; paint(); missionsCheck(); }
  };
  step();
}
$("#lens").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  lens = b.dataset.lens;
  for (const x of $("#lens").children) x.setAttribute("aria-pressed", String(x === b));
  recolor(); store.set("lens", lens);
});
function legend() {
  const items = BIN_LABEL.map((t, k) => `<span class="sw"><i style="background:var(--p${k})"></i>${t}</span>`);
  $("#legend").innerHTML = `${items.join("")}<span class="sw"><i style="background:var(--pnone)"></i>not allowed</span>`;
}

// ------------------------------------------------------------------------------------------------ picking
const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
let down = null;
renderer.domElement.addEventListener("pointerdown", e => { down = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener("pointerup", e => {
  if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 6) return;
  const r = renderer.domElement.getBoundingClientRect();
  ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ptr, camera);
  const pin = ray.intersectObjects(pins.children, true).find(h => h.object.type === "Mesh");
  if (pin) { let g = pin.object; while (!g.userData.p) g = g.parent; openProject(g.userData.p); return; }
  const hit = ray.intersectObject(parcels)[0];
  if (hit) openSite(sites[hit.instanceId]);
});

let fly = null;
function flyTo(x, z, dist = 900) {
  const from = { t: controls.target.clone(), p: camera.position.clone() };
  const to = { t: new THREE.Vector3(x, 0, z), p: new THREE.Vector3(x + dist * 0.35, dist * 0.9, z + dist) };
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) { controls.target.copy(to.t); camera.position.copy(to.p); return; }
  fly = { from, to, t0: performance.now() };
}

// ------------------------------------------------------------------------------------------------ the card
let card = null;
const money = v => (v < 0 ? "−" : "") + (Math.abs(v) >= 1e6 ? `$${(Math.abs(v) / 1e6).toFixed(2)}M` : `$${Math.round(Math.abs(v) / 1e3).toLocaleString()}k`);
const pct = v => (v * 100).toFixed(2) + "%";
const esc = t => String(t ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function verdictHTML(pencils, gapBp, needX, blocked) {
  if (blocked) return `<div class="verdict blocked"><b>Can't build</b><span>${esc(blocked)}</span></div>`;
  return `<div class="verdict ${pencils ? "yes" : "no"}"><b>${pencils ? "Pencils" : "Doesn't pencil"}</b>
    <span class="mono">${gapBp >= 0 ? "+" : ""}${gapBp} bp vs hurdle<br>needs rents ${needX.toFixed(2)}× today's</span></div>`;
}
function gaugeHTML(yoc, hurdle) {
  const max = 0.12, w = Math.max(0, Math.min(1, yoc / max)) * 100, h = Math.min(1, hurdle / max) * 100;
  return `<div><div class="eyebrow" style="margin-bottom:4px">Yield on cost vs the hurdle</div>
    <div class="gauge"><div class="fill" style="width:${w}%;background:var(${yoc >= hurdle ? "--p0" : "--p4"});opacity:.35"></div>
    <div class="mark" style="left:${h}%"></div><div class="lbl"><span>yield ${pct(yoc)}</span><span>hurdle ${pct(hurdle)}</span></div></div></div>`;
}
function napkinHTML(b, landBasis, landLabel, needX) {
  const rowsH = [
    ["Rent from market units, after vacancy and operating costs", b.market_noi],
    ...(b.bmr_noi ? [["Rent from below-market units", b.bmr_noi, "sub"]] : []),
    ...(b.retail_noi ? [["Ground-floor retail", b.retail_noi, "sub"]] : []),
    ["Net operating income, per year", b.noi, "sum"],
    [`What a buyer pays for that income (÷ ${pct(b.hurdle)})`, b.value],
    ["Construction (" + b.tier + ")", -b.hard, "sub"],
    ["Design, permits, insurance, developer overhead", -b.soft, "sub"],
    ["City fees, school fee, public art", -(b.other_fees + b.school + b.art), "sub"],
    ["Affordable housing fee", -b.afford_fee, "sub"],
    ["Construction loan interest", -b.interest, "sub"],
    ["What the land is worth to this building", b.rlv, "sum"],
    [`What the land costs (${landLabel})`, -landBasis, "sub"],
    [b.rlv >= landBasis ? "Left over for the developer" : "Shortfall", b.rlv - landBasis, "sum"],
  ];
  return `<table class="napkin">${rowsH.map(([t, v, c]) => `<tr class="${c || ""}"><td>${esc(t)}</td><td class="v">${money(v)}</td></tr>`).join("")}</table>`;
}
function factsHTML(items) { return `<div class="facts">${items.map(([k, v]) => `<div><span class="eyebrow">${k}</span><b>${v}</b></div>`).join("")}</div>`; }

function openSite(site, keep = {}) {
  const tod = P.sb79Band(site, data);
  card = { kind: "site", site, pathway: keep.pathway || (tod.band ? "sb79" : "zoning"), layout: keep.layout || "apartments",
           stories: keep.stories || null, vliPct: keep.vliPct || 10, extraVli: keep.extraVli || 0, tod };
  if (!keep.stories) {
    const d = bestDesign(site, { s: market, pathway: card.pathway, layout: card.layout, vliPct: card.vliPct, extraVli: 0 });
    if (d && d.blocked && card.pathway === "sb79") card.pathway = "zoning";
    const d2 = d && !d.blocked ? d : bestDesign(site, { s: market, pathway: card.pathway, layout: card.layout, vliPct: card.vliPct });
    card.stories = d2 && !d2.blocked ? d2.stories : 3;
  }
  flyTo(site.x, site.z); refreshCard();
}
function openProject(p, keep = {}) {
  const vli0 = (p.affordable_text || "").match(/VLI (\d+)/);
  card = { kind: "project", p, fee: keep.fee || p.fee_mode, vli: keep.vli ?? (vli0 ? +vli0[1] : null), addUnits: keep.addUnits || 0 };
  const [x, z] = toXZ(p.lat, p.lon);
  flyTo(x, z, 700); refreshCard();
  if (p.group === "featured") missionDone("open2800");
}

function siteBlockReason(site, pathway, tod) {
  if ((pathway === "sb79" || pathway === "sb79bonus") && site.rental_units > 2)
    return `${site.rental_units} rent-registered units on the lot: SB 79 excludes sites whose development demolishes more than 2 occupied rent-controlled units`;
  return null;
}

function refreshCard() {
  const el = $("#card");
  if (!card) { el.hidden = true; return; }
  el.hidden = false;
  if (card.kind === "site") return renderSite(el);
  return renderProject(el);
}

function renderSite(el) {
  const { site, tod } = card;
  const o = { s: market, pathway: card.pathway, layout: card.layout, stories: card.stories, vliPct: card.vliPct, extraVli: card.extraVli };
  const block = siteBlockReason(site, card.pathway, tod);
  const d = block ? { blocked: block } : P.design(site, data, o);
  const pw = [["zoning", "Zoning as written"], ["bonus", "Density bonus"], ["sb79", "SB 79"], ["sb79bonus", "SB 79 + bonus"]];
  const tags = [site.district || "no district", site.nb, `${Math.round(site.lot_sf).toLocaleString()} sf lot`,
    site.building_sf ? `${Math.round(site.building_sf).toLocaleString()} sf existing` : "no building",
    site.rental_units ? `${site.rental_units} rent-registered units` : null, site.landmark ? "landmark" : null,
    site.fire ? `${site.fire.replace("_", " ")} fire zone` : null].filter(Boolean);
  const todLine = tod.band ? `${tod.mi.toFixed(2)} mi from ${tod.station} BART: SB 79 ${tod.band.band}` : `${tod.mi.toFixed(2)} mi from ${tod.station} BART: outside SB 79`;
  let body = "";
  if (!d.blocked) {
    const b = d.b, bmr = d.vliUnits || (b.affordable ? Object.values(b.affordable).reduce((a, x) => a + Object.values(x).reduce((p, q) => p + q, 0), 0) : 0);
    body = verdictHTML(d.pencils, Math.round(d.gap * 1e4), d.need) + gaugeHTML(d.yoc, b.hurdle)
      + factsHTML([[card.layout === "beds" ? "Beds / units" : "Units", card.layout === "beds" ? `${b.beds}/${b.units}` : b.units],
                   ["Stories", `${d.stories} · ${Math.round(b.height_ft)} ft`], ["Below-market", bmr]])
      + `<div class="note">${esc(b.tier)}. Land basis: ${esc(d.land.binding)} (${money(d.land.basis)}).</div>`
      + napkinHTML(b, d.land.basis, d.land.binding, d.need)
      + `<ul class="law">${d.law.map(x => `<li>${esc(x)}</li>`).join("")}</ul>`;
    missionsSite(site, d);
  } else body = verdictHTML(false, 0, 0, d.blocked);
  const max = d.blocked ? 3 : d.maxStories;
  el.innerHTML = `<button class="close" aria-label="Close">×</button>
    <div class="head"><span class="eyebrow">Parcel ${esc(site.key)}</span><h2>${esc(site.name)}</h2>
      <span class="sub">${tags.map(esc).join(" · ")}</span><span class="sub">${esc(todLine)}</span></div>
    <div class="body">
      <div class="ctl">
        <div class="seg" id="pw" role="group" aria-label="Legal pathway">${pw.map(([k, t]) => `<button data-pw="${k}" aria-pressed="${card.pathway === k}">${t}</button>`).join("")}</div>
        <div class="seg" id="lay" role="group" aria-label="Layout"><button data-lay="apartments" aria-pressed="${card.layout === "apartments"}">Apartments</button><button data-lay="beds" aria-pressed="${card.layout === "beds"}">By the bed (student)</button></div>
        <label for="c_st">Stories <input type="range" id="c_st" min="2" max="${Math.max(2, max)}" step="1" value="${Math.min(card.stories, max)}"><output>${Math.min(card.stories, max)}</output></label>
        ${card.pathway === "bonus" || card.pathway === "sb79bonus" ? `
        <label for="c_vli">VLI share <input type="range" id="c_vli" min="5" max="15" step="1" value="${card.vliPct}"><output>${card.vliPct}%</output></label>
        <label for="c_x">AB 1287 extra <input type="range" id="c_x" min="0" max="10" step="1" value="${card.extraVli}" ${card.vliPct < 15 ? "disabled" : ""}><output>${card.extraVli}%</output></label>` : ""}
        <div class="row"><button class="btn" id="bestH">Find the best height</button><button class="btn primary" id="addP" ${d.blocked || !d.pencils ? "disabled" : ""}>Add to portfolio</button></div>
      </div>
      ${body}
      <p class="note"><span class="chip GAME">GAME</span> The base model is JN-O's pencil-out (verified line for line). The by-the-bed layout, the density-bonus unit cap with waivers and the SB 79 envelopes are game extensions built on it; station distances are from the station centroid, and MTC's SB 79 map is the legal test.</p>
    </div>`;
  el.querySelector(".close").onclick = () => { card = null; if (hidden) { placeParcel(hidden); parcels.instanceMatrix.needsUpdate = true; hidden = null; } massing.clear(); refreshCard(); };
  el.querySelector("#pw").onclick = e => { const b = e.target.closest("button"); if (!b) return; card.pathway = b.dataset.pw; card.stories = 12; bestHeight(); };
  el.querySelector("#lay").onclick = e => { const b = e.target.closest("button"); if (!b) return; card.layout = b.dataset.lay; bestHeight(); };
  el.querySelector("#c_st").oninput = e => { card.stories = +e.target.value; refreshCard(); };
  const v = el.querySelector("#c_vli"); if (v) v.oninput = e => { card.vliPct = +e.target.value; if (card.vliPct < 15) card.extraVli = 0; refreshCard(); };
  const x = el.querySelector("#c_x"); if (x) x.oninput = e => { card.extraVli = +e.target.value; refreshCard(); };
  el.querySelector("#bestH").onclick = bestHeight;
  el.querySelector("#addP").onclick = () => addPortfolio(site, d);
  showMassing(site, d.blocked ? null : d.b, !d.blocked && d.pencils);
  keepFocus();
}
function bestHeight() {
  const d = bestDesign(card.site, { s: market, pathway: card.pathway, layout: card.layout, vliPct: card.vliPct, extraVli: card.extraVli });
  if (d && !d.blocked) card.stories = d.stories;
  refreshCard();
}

function renderProject(el) {
  const { p } = card;
  const groupName = { stalled: "Stalled entitlement", built: "Built or building since mid-2022", featured: "In the pipeline" }[p.group];
  let body = "";
  if (p.verdict === "insufficient_data") {
    body = `<div class="verdict blocked"><b>Can't price it</b><span>${esc(p.missing.join("; "))}</span></div>`;
  } else {
    const r = P.recordVariant(p, market, data, { vli: card.vli, addUnits: card.addUnits, fee_mode: card.fee });
    const bmr = r.affordable ? Object.values(r.affordable).reduce((a, x) => a + Object.values(x).reduce((q, w) => q + w, 0), 0) : 0;
    const bonusLine = r.bonus ? `<p class="note">${r.bonus.ok ? "Legal" : "Not legal"} under the State Density Bonus: ${r.units} units on a ${r.bonus.base_units}-unit base is a ${r.bonus.needPct.toFixed(1)}% bonus; ${r.bonus.vliPct.toFixed(1)}% VLI buys ${+r.bonus.have.toFixed(2)}% (up to ${r.bonus.max_units} units).</p>` : "";
    body = verdictHTML(r.gap >= 0, Math.round(r.gap * 1e4), r.rent_mult_needed) + gaugeHTML(r.yoc, r.hurdle)
      + factsHTML([[r.per_bed_beds ? "Beds / units" : "Units", r.per_bed_beds ? `${r.per_bed_beds}/${r.units}` : r.units],
                   ["Stories", `${r.stories} · ${Math.round(r.height_ft)} ft`], ["Below-market", bmr]])
      + bonusLine + napkinHTML(r, r.land_basis, r.land_label === "RECORD" ? "assessed after a 2018+ sale" : "market land, assumed", r.rent_mult_needed)
      + `<details><summary>Where every input comes from</summary><div class="ledger">${p.ledger.map(l => `<div><span><span class="chip ${l.label}">${l.label}</span></span><span><b>${esc(l.field)}</b> ${esc(l.value)}<br><span class="note">${esc(l.source)}</span></span></div>`).join("")}
         ${card.addUnits ? `<div><span><span class="chip GAME">GAME</span></span><span>+${card.addUnits} units at the project's own mix; the extra floor area is stacked as whole floors at its average floor plate.</span></div>` : ""}</div></details>`;
    showMassing(nearestSite(p), { ...r, retail_sf: p.commercial, lobby_sf: 0 }, r.gap >= 0);
    missionsProject(p, r);
  }
  const units = p.units || 0, vliMax = Math.max(4, Math.ceil(units * 0.25));
  el.innerHTML = `<button class="close" aria-label="Close">×</button>
    <div class="head"><span class="eyebrow">${esc(groupName)} · ${esc(p.anchor)}</span><h2>${esc(p.address)}</h2>
      <span class="sub">${units ? units + " units approved · " : ""}v4 status: ${esc(p.v4_status || "unknown")} · filed ${esc(p.filed || "?")}</span></div>
    <div class="body">
      ${p.story ? `<p class="story">${esc(p.story)}</p>` : ""}
      ${p.verdict !== "insufficient_data" ? `<div class="ctl">
        <div class="seg" id="fee" role="group" aria-label="Affordable housing fee rules">
          <button data-fee="legacy_ahmf" aria-pressed="${card.fee === "legacy_ahmf"}">Pre-2023 fee (vested)</button><button data-fee="iho_combo" aria-pressed="${card.fee === "iho_combo"}">Today's IHO</button></div>
        <label for="c_vli">VLI units <input type="range" id="c_vli" min="0" max="${vliMax}" step="1" value="${card.vli ?? 0}"><output>${card.vli ?? 0}</output></label>
        <label for="c_add">Extra units <input type="range" id="c_add" min="0" max="${Math.max(4, Math.ceil(units * 0.5))}" step="1" value="${card.addUnits}"><output>+${card.addUnits}</output></label>
        <div class="row"><button class="btn" id="reset">As approved</button><button class="btn" id="redo">Redesign this lot from scratch</button></div>
      </div>` : `<div class="row"><button class="btn" id="redo">Redesign this lot from scratch</button></div>`}
      ${body}
    </div>`;
  el.querySelector(".close").onclick = () => { card = null; massing.clear(); if (hidden) { placeParcel(hidden); parcels.instanceMatrix.needsUpdate = true; hidden = null; } refreshCard(); };
  const f = el.querySelector("#fee"); if (f) f.onclick = e => { const b = e.target.closest("button"); if (!b) return; card.fee = b.dataset.fee; refreshCard(); };
  const v = el.querySelector("#c_vli"); if (v) v.oninput = e => { card.vli = +e.target.value; refreshCard(); };
  const a = el.querySelector("#c_add"); if (a) a.oninput = e => { card.addUnits = +e.target.value; refreshCard(); };
  const rs = el.querySelector("#reset"); if (rs) rs.onclick = () => openProject(p);
  el.querySelector("#redo").onclick = () => openSite(nearestSite(p), { pathway: "bonus", layout: Object.keys(p.mix || {}).some(b => +b >= 4) ? "beds" : "apartments", vliPct: 8 });
  keepFocus();
}
function nearestSite(p) {
  let best = null, bd = Infinity;
  const [x, z] = toXZ(p.lat, p.lon);
  for (const s of sites) { const d = (s.x - x) ** 2 + (s.z - z) ** 2; if (d < bd) { bd = d; best = s; } }
  return best;
}
let lastFocus = null;
document.addEventListener("focusin", e => { if (e.target.id) lastFocus = e.target.id; });
function keepFocus() { if (lastFocus && $("#card").contains(document.activeElement) === false) { const n = document.getElementById(lastFocus); if (n && $("#card").contains(n)) n.focus(); } }

// ------------------------------------------------------------------------------------------------ missions & portfolio
const done = store.get("missions", {});
let portfolio = store.get("portfolio", {});
const MISSIONS = [
  ["open2800", "Open 2800 Telegraph", "The blue pin on Telegraph at Stuart: approved 2023, demolition under way."],
  ["pencil2800", "Make 2800 Telegraph pencil", "Which lever does it: the law, the fee, or the market?"],
  ["near", "Find a parcel within 25% of penciling at today's market", "Base market, any pathway: rents needed 1.25× or less."],
  ["sb79", "Use SB 79 to beat zoning on a BART-area parcel", "Same parcel, same layout: SB 79 needs lower rents than zoning as written."],
  ["units500", "Assemble 500 units that pencil", "With every market dial inside its sourced range."],
];
function missionDone(id, note) {
  if (done[id]) return;
  done[id] = note || true; store.set("missions", done); renderMissions();
  toast("Mission complete: " + MISSIONS.find(m => m[0] === id)[1]);
}
function renderMissions() {
  const units = Object.values(portfolio).filter(x => x.inBand).reduce((a, x) => a + x.units, 0);
  $("#missions").innerHTML = MISSIONS.map(([id, t, sub]) => `<li class="${done[id] ? "done" : ""}"><span class="box"></span><span class="txt">${esc(t)}
    <small>${esc(typeof done[id] === "string" ? done[id] : id === "units500" ? `${units} of 500 units · ${Object.keys(portfolio).length} sites` : sub)}</small></span></li>`).join("");
}
const PW_NAME = { zoning: "zoning as written", bonus: "density bonus", sb79: "SB 79", sb79bonus: "SB 79 + bonus" };
function missionsSite(site, d) {
  if (isBase() && d.need <= 1.25) missionDone("near", `${site.name}: ${d.need.toFixed(2)}× rents (${PW_NAME[card.pathway]}, ${card.layout === "beds" ? "by the bed" : "apartments"})`);
  if ((card.pathway === "sb79" || card.pathway === "sb79bonus") && !done.sb79) {
    const z = bestDesign(site, { s: market, pathway: "zoning", layout: card.layout });
    if (z && !z.blocked && d.need < z.need - 1e-6) missionDone("sb79", `${site.name}: ${d.need.toFixed(2)}× vs ${z.need.toFixed(2)}× under zoning`);
  }
}
function missionsProject(p, r) {
  if (p.group === "featured" && r.gap >= 0) {
    const what = [card.fee !== p.fee_mode ? "today's IHO" : null, card.addUnits ? `+${card.addUnits} units` : null,
                  card.vli !== null && card.vli !== +(((p.affordable_text || "").match(/VLI (\d+)/) || [0, 0])[1]) ? `${card.vli} VLI` : null, scenName !== "base" ? `${scenName} market` : null,
                  ...dials.filter(([k]) => Math.abs(market[k] - S.base[k]) > 1e-9).map(([k, , , fmt]) => `${k.replace("_mult", "")} ${fmt(market[k])}`)]
      .filter(Boolean);
    missionDone("pencil2800", "It took: " + (what.join(", ") || "nothing?"));
  }
}
function addPortfolio(site, d) {
  if (d.blocked || !d.pencils) return;
  portfolio[site.key] = { name: site.name, units: d.b.units, surplus: d.surplus, inBand: inBand() };
  store.set("portfolio", portfolio); renderMissions();
  const units = Object.values(portfolio).filter(x => x.inBand).reduce((a, x) => a + x.units, 0);
  toast(`Added ${site.name}: ${d.b.units} units${inBand() ? "" : " (dials outside their range: not counted)"}`);
  if (units >= 500) missionDone("units500", `${units} units on ${Object.keys(portfolio).length} sites`);
}
function missionsCheck() { renderMissions(); }
let toastT;
function toast(t) { const el = $("#toast"); el.textContent = t; el.style.opacity = 1; clearTimeout(toastT); toastT = setTimeout(() => (el.style.opacity = 0), 3200); }

// ------------------------------------------------------------------------------------------------ search
const idxNames = sites.map(s => s.name.toUpperCase());
$("#search").addEventListener("input", e => {
  const q = e.target.value.trim().toUpperCase().replace(/\bAVENUE\b/, "AVE").replace(/\bSTREET\b/, "ST");
  const hits = $("#hits");
  if (q.length < 3) { hits.innerHTML = ""; return; }
  const proj = pipeline.filter(p => p.address.toUpperCase().includes(q)).slice(0, 3);
  const ps = []; for (let i = 0; i < sites.length && ps.length < 6; i++) if (idxNames[i].includes(q)) ps.push(sites[i]);
  hits.innerHTML = proj.map(p => `<button data-p="${esc(p.anchor)}"><b>Pipeline</b> ${esc(p.address)}</button>`).join("")
    + ps.map(s => `<button data-s="${s.i}">${esc(s.name)} · ${esc(s.district || "")}</button>`).join("");
});
$("#hits").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  if (b.dataset.p) openProject(pipeline.find(p => p.anchor === b.dataset.p)); else openSite(sites[+b.dataset.s]);
  $("#hits").innerHTML = ""; $("#search").value = "";
});

// ------------------------------------------------------------------------------------------------ loop
addEventListener("resize", () => {
  camera.aspect = host.clientWidth / host.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(host.clientWidth, host.clientHeight);
});
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const t = clock.getElapsedTime();
  if (fly) {
    const k = Math.min(1, (performance.now() - fly.t0) / 1100), e = k < .5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
    controls.target.lerpVectors(fly.from.t, fly.to.t, e); camera.position.lerpVectors(fly.from.p, fly.to.p, e);
    if (k >= 1) fly = null;
  }
  if (rise < 1) rise = matchMedia("(prefers-reduced-motion: reduce)").matches ? 1 : Math.min(1, rise + 0.05);
  massing.scale.y = Math.max(0.001, rise);
  for (const g of pins.children) if (g.userData.p.group === "featured") g.userData.head.rotation.y = t * 1.2;
  controls.update(); renderer.render(scene, camera);
});

// ------------------------------------------------------------------------------------------------ start
legend(); syncDials(); applyTheme();
const savedLens = store.get("lens", "zoning");
if (savedLens !== "zoning") $(`#lens [data-lens="${savedLens}"]`)?.click(); else recolor();
renderMissions();
$("#loading").remove();
openProject(featured);
