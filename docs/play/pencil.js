// pencil.js -- a line-for-line JavaScript port of scripts/v4/pencil_out.py (the pencil-out model, JN-O), for the
// "Can it pencil?" game. Same inputs (game_data.json, exported from the Python model's own files), same arithmetic.
// parity_test.mjs checks this file reproduces the Python results for every parcel and pipeline project.
//
// Section 1 is the port (names follow pencil_out.py). Section 2 holds the game's EXTENSIONS, each labeled: the
// by-the-bed layout on any site, the density-bonus and SB 79 envelopes, and the "redesign a recorded project" levers.

let A, C, R;
export function init(data) { A = data.A; C = data.consts; R = data.R; }

// ------------------------------------------------------------------------------------------- 1. the port
export function tierFor(stories, hft) {
  for (const t of A.construction_tiers.tiers) if (stories <= t.max_stories && hft <= t.max_height_ft) return t;
  return A.construction_tiers.tiers.at(-1);
}

export function heightFt(stories) {
  const f = A.floor_to_floor_ft.base;
  return f.ground + f.upper * (stories - 1);
}

export function bmrRent(tier, bedrooms) {
  const b = A.bmr_rents_monthly, key = String(Math.min(parseInt(bedrooms), 3)), ua = b.utility_allowance[key];
  if (tier === "VLI") return b.vli_50_ami_gross[key] - ua;
  if (tier === "ELI") return b.vli_50_ami_gross[key] * A.eli_rent_share_of_vli.base - ua;
  if (tier === "LI") return b.li_capped_60_ami_gross[key] - ua;
  throw new Error(tier);
}

const sumv = o => Object.values(o).reduce((a, b) => a + b, 0);

export function account({ units_mix, net_sf, res_gross, retail_sf, lobby_sf, stories, lot_sf, s, affordable = null,
                          fee_mode = "in_lieu", per_bed_beds = null, loc = 1.0 }) {
  affordable = affordable || {};
  const fees = A.berkeley_fees, fin = A.construction_financing;
  const units = sumv(units_mix);
  const affByB = {};
  for (const byB of Object.values(affordable)) for (const [b, n] of Object.entries(byB)) affByB[b] = (affByB[b] || 0) + n;
  let market_gpr;
  if (per_bed_beds) {
    const affUnits = sumv(affByB);
    market_gpr = R.per_bed * s.rent_mult * 12 * per_bed_beds * (units - affUnits) / units;
  } else {
    market_gpr = 0;
    for (const [b, n] of Object.entries(units_mix))
      market_gpr += (n - (affByB[b] || 0)) * R.pool_rent[String(Math.min(parseInt(b), 3))] * s.rent_mult * loc * 12;
  }
  const market_noi = market_gpr * (1 - C.vacancy) * (1 - s.opex);
  const bmr = A.bmr_rents_monthly;
  let bmr_noi = 0;
  for (const [t, byB] of Object.entries(affordable))
    for (const [b, n] of Object.entries(byB))
      bmr_noi += n * (bmrRent(t, b) * 12 * (1 - bmr.bmr_vacancy) - bmr.bmr_opex_per_unit_yr);
  const retail_noi = retail_sf * C.retail_rent * (1 - C.retail_vacancy) * (1 - C.retail_expenses);
  const noi = market_noi + bmr_noi + retail_noi;
  const t = tierFor(stories, heightFt(stories)), esc = C.esc;
  const hard = ((res_gross + lobby_sf) * t.per_gsf_2024 + retail_sf * A.retail_shell_cost_per_gsf_2024.base
                + lot_sf * s.site_work) * esc * s.hard_mult;
  const soft = hard * s.soft;
  const other = fees.other_city_fees_per_unit_2024 * esc * units;
  const school = fees.school_fee_per_residential_sf * net_sf;
  const art = fees.public_art_in_lieu_share * hard;
  const bmrCount = () => { let k = 0; for (const [tr, byB] of Object.entries(affordable)) if (["ELI", "VLI", "LI"].includes(tr)) k += sumv(byB); return k; };
  let afford_fee;
  if (fee_mode === "in_lieu") afford_fee = fees.inclusionary_in_lieu_per_rufa_sf * Math.max(0, net_sf - fees.in_lieu_rufa_deduction_sf);
  else if (fee_mode === "iho_combo") afford_fee = fees.inclusionary_in_lieu_per_rufa_sf * net_sf * Math.max(0, 1 - bmrCount() / (fees.on_site_share * units));
  else if (fee_mode === "legacy_ahmf") afford_fee = Math.max(0, units * A.legacy_ahmf_per_unit.base * (1 - bmrCount() / (0.20 * units)));
  else afford_fee = 0;
  const loan = (hard + soft) * fin.loan_to_cost;
  const interest = loan * fin.average_outstanding * s.rate * t.construction_months / 12 + loan * fin.points;
  const cost_ex_land = hard + soft + other + school + art + afford_fee + interest;
  const hurdle = s.cap + s.spread, value = noi / hurdle;
  return { units, noi, market_noi, other_noi: bmr_noi + retail_noi, bmr_noi, retail_noi, hard, soft,
           fees: other + school + art + afford_fee, other_fees: other, school, art, afford_fee, interest,
           cost_ex_land, hurdle, value, rlv: value - cost_ex_land, tier: t.name, height_ft: heightFt(stories) };
}

// largest remainders, ties in key order (Python's sorted() is stable; R.pool_mix keys are "0".."3" in order)
function largestRemainder(raw, n) {
  const out = {};
  for (const [b, v] of Object.entries(raw)) out[b] = Math.floor(v);
  const order = Object.keys(raw).map((b, i) => [b, i]).sort((x, y) => ((raw[y[0]] - out[y[0]]) - (raw[x[0]] - out[x[0]])) || (x[1] - y[1]));
  for (const [b] of order.slice(0, Math.max(0, n - sumv(out)))) out[b] += 1;
  return out;
}

export function avgUnitSf() {
  const sizes = A.unit_size_sf.by_bedrooms;
  let avg = 0; for (const b in R.pool_mix) avg += R.pool_mix[b] * sizes[b];
  return avg;
}

export function mixUnits(net_sf) {
  const n = Math.floor(net_sf / avgUnitSf());
  const raw = {}; for (const b in R.pool_mix) raw[b] = n * R.pool_mix[b];
  return largestRemainder(raw, n);
}

export function spread(k, mix) {
  const tot = sumv(mix), raw = {};
  for (const [b, n] of Object.entries(mix)) raw[b] = k * n / tot;
  const out = largestRemainder(raw, k), r = {};
  for (const [b, n] of Object.entries(out)) if (n) r[b] = n;
  return r;
}

export function siteBuilding(site, stories, s, fee_mode = "in_lieu", env = null) {
  const lot = site.lot_sf;
  let ground, retail, res_gross;
  if (env && env.ground === "residential") {
    const cov = env.lot_coverage || s.cov_upper;
    ground = retail = 0; res_gross = lot * cov * stories;
  } else {
    ground = lot * s.cov_ground; retail = ground * s.retail_share; res_gross = lot * s.cov_upper * (stories - 1);
  }
  if (env && env.far) res_gross = Math.min(res_gross, Math.max(0, env.far * lot - ground));
  let net = res_gross * s.efficiency;
  let mix = mixUnits(net);
  if (env && env.du_ac && sumv(mix) > Math.trunc(env.du_ac * lot / 43560)) {
    const cap = Math.trunc(env.du_ac * lot / 43560);
    net = (cap + 1e-9) * avgUnitSf(); res_gross = net / s.efficiency; mix = mixUnits(net);
  }
  let affordable = null;
  if (fee_mode === "on_site") {
    const k = Math.ceil(A.berkeley_fees.on_site_share * sumv(mix));
    const vli = Math.ceil(k / 2), li = k - Math.ceil(k / 2);
    affordable = { VLI: spread(vli, mix), LI: spread(li, mix) };
  }
  const acct = account({ units_mix: mix, net_sf: net, res_gross, retail_sf: retail, lobby_sf: ground - retail, stories,
                         lot_sf: lot, s, affordable, fee_mode, loc: site.rent_factor ?? 1.0 });
  return Object.assign(acct, { stories, net_sf: net, res_gross, retail_sf: retail, lobby_sf: ground - retail, mix, affordable });
}

export function landBasis(site, s) {
  const market = site.lot_sf * s.land_psf;
  const euv = site.euv ? site.euv[s.euv_case || "base"]
    : (site.existing_retail_sf || 0) * s.euv_rent * (1 - s.euv_vacancy) / s.euv_cap;
  return { market, euv, basis: Math.max(market, euv), binding: euv > market ? "existing use" : "market land" };
}

export function needFor(b, basis, s) {
  return b.market_noi > 0 ? ((basis + b.cost_ex_land) * b.hurdle - b.other_noi) / (b.market_noi / s.rent_mult) : Infinity;
}

export function breakEven(site, s, fee_mode = "in_lieu", env = null, build = siteBuilding) {
  const hs = A.height_search, lb = landBasis(site, s);
  const top = env ? Math.min(hs.max_stories, env.stories) : hs.max_stories;
  const rows = [];
  for (let n = Math.min(hs.min_stories, top); n <= top; n++) {
    const b = build(site, n, s, fee_mode, env);
    const need = needFor(b, lb.basis, s);
    rows.push({ stories: n, height_ft: b.height_ft, tier: b.tier, units: b.units, noi: b.noi, value: b.value,
                cost_ex_land: b.cost_ex_land, rlv: b.rlv, land_basis: lb.basis, surplus: b.rlv - lb.basis,
                pencils: b.units > 0 && b.rlv >= lb.basis, rent_mult_needed: need, b });
  }
  const first = rows.find(r => r.pencils);
  return { rows, break_even_stories: first ? first.stories : null, land: lb };
}

export const bestRow = rows => rows.reduce((m, r) => (r.rent_mult_needed < m.rent_mult_needed ? r : m), rows[0]);

export function storiesUnder(ft) { let n = 1; while (heightFt(n + 1) <= ft) n++; return n; }

const pyRound = x => { const f = Math.floor(x), d = x - f; return d > 0.5 ? f + 1 : d < 0.5 ? f : (f % 2 === 0 ? f : f + 1); };

export function allowedEnvelope(row, fee_mode, bonus) {
  if (!row || !row.residential) return null;
  const caps = [row.max_stories, row.max_height_ft ? storiesUnder(row.max_height_ft) : null].filter(x => x);
  const env = { stories: Math.min(...caps), far: row.far_max, du_ac: row.density_max, ground: row.ground,
                lot_coverage: row.lot_coverage, basis: `${row.district} standard` };
  if (fee_mode !== "on_site") return env;
  const m = 1 + bonus.bonus_share;
  const state = { ...env, stories: pyRound(env.stories * m), far: env.far && env.far * m, du_ac: env.du_ac && env.du_ac * m,
                  basis: `${row.district} + state bonus ${(bonus.bonus_share * 100).toFixed(1)}%` };
  const lb = row.local_bonus;
  if (lb && A.berkeley_fees.on_site_share >= lb.min_affordable_share) {
    const local = { ...env, stories: Math.min(lb.max_stories, storiesUnder(lb.max_height_ft)), far: lb.far_max,
                    du_ac: lb.density_max, basis: `${row.district} + ${lb.name}` };
    if (local.stories > state.stories) return local;
  }
  return state;
}

// a recorded project at its approved size (pencil_out.stalled_project), from the exported RECORD inputs
export function parseAffordable(text, mix) {
  const tiers = {};
  if (!text || ["0", "none"].includes(text.trim())) return tiers;
  for (const part of text.split(";")) {
    const [t, n] = part.trim().split(" ");
    if (["ELI", "VLI", "LI"].includes(t)) tiers[t] = spread(parseInt(n), mix);
  }
  return tiers;
}

export function recordProject(p, s, over = {}) {
  const q = { ...p, ...over };
  const res_gross = q.gross ? q.gross - q.commercial : q.net_rec / s.efficiency;
  const net = q.net_rec ? q.net_rec : res_gross * s.efficiency;
  const affordable = over.affordable || parseAffordable(q.affordable_text, q.mix);
  const group = Object.keys(q.mix).some(b => parseInt(b) >= 4);
  let per_bed_beds = null;
  if (group) { per_bed_beds = 0; for (const [b, n] of Object.entries(q.mix)) per_bed_beds += Math.max(parseInt(b), 1) * n; }
  const L = q.land, market = q.lot_sf * s.land_psf;
  const useRecord = q.record_land && L.recent_transfer && L.assessed > 0 && !L.partial_site;
  const basis = useRecord ? L.assessed : market;
  const acct = account({ units_mix: q.mix, net_sf: net, res_gross, retail_sf: q.commercial, lobby_sf: 0, stories: q.stories,
                         lot_sf: q.lot_sf, s, affordable, fee_mode: q.fee_mode, per_bed_beds });
  const yoc = acct.noi / (acct.cost_ex_land + basis);
  return { ...acct, yoc, gap: yoc - acct.hurdle, land_basis: basis, land_label: useRecord ? "RECORD" : "ASSUMPTION",
           rent_mult_needed: needFor(acct, basis, s), net_sf: net, res_gross, per_bed_beds, group, affordable,
           stories: q.stories, mix: q.mix };
}

// ------------------------------------------------------------------------------- 2. the game's extensions
// Each is LABELED in the game's ledger. None changes the ported functions above.

// (a) by-the-bed layout on any site: beds = net area / net sf per bed, units = beds / beds per unit, priced at the
//     per-bed rent (pencil_out prices group-living RECORD projects this way). The two ratios are DERIVED from the 2800
//     Telegraph plan set: 18,387 sf residential / 51 beds = 360 sf per bed, 51 beds / 16 units = 3.2 beds per unit.
export const BED = { sf_per_bed: 360, beds_per_unit: 3.2, source: "DERIVED: 2800 Telegraph plan set A0.1 (18,387 sf / 51 beds; 51 beds / 16 units)" };

// (b) a design on any site under a legal pathway. pathway:
//   "zoning"  -- zoning as written, pay the in-lieu fee (the zoned pass's in_lieu scenario, exactly)
//   "bonus"   -- State Density Bonus: vliPct VLI units on site (of base units) buy the AB 2345 bonus; AB 1287 adds
//                more for extra VLI after 15%. Base units = what zoning as written yields at its full height; the bonus
//                multiplies the UNIT COUNT (rounded up, 65915(f)(5)); waivers (65915(e)) may not deny the height and
//                FAR the bonus units need -- the game lets stories run to the search maximum (12) but caps units.
//                Fee: today's IHO combination fee (on-site VLI count against the 20% requirement).
//   "sb79"    -- SB 79 standards by distance to BART (Tier 1): height, du/ac, FAR; 11+ units need 10% VLI on site
//                (Berkeley's IHO is higher, so the combination fee is charged on the unmet share of 20%).
//   "sb79bonus" -- SB 79 + density bonus: SB 79 density as the base, the bonus on top, no extra height.
export function bonusPct(vliPct, extraVli, table) {
  const t = table.vli_pct_to_bonus, keys = Object.keys(t).map(Number).sort((a, b) => a - b);
  if (vliPct < keys[0]) return 0;
  let b = 0; for (const k of keys) if (vliPct >= k) b = t[k];
  if (vliPct >= 15 && extraVli >= 5) {
    const t2 = table.ab1287_additional_vli_pct_to_bonus; let e = 0;
    for (const k of Object.keys(t2).map(Number).sort((a, b) => a - b)) if (extraVli >= k) e = t2[k];
    b += e;
  }
  return b / 100;
}

function bedBuilding(site, stories, s, fee_mode, env, unitCap, vliUnits) {
  // the ported site geometry, then the area re-cut into beds
  const geo = siteBuilding(site, stories, s, "in_lieu", env);
  const net = geo.net_sf, beds = Math.floor(net / BED.sf_per_bed);
  let units = Math.max(1, Math.round(beds / BED.beds_per_unit));
  if (unitCap) units = Math.min(units, unitCap);
  if (beds < 1) return null;
  // units as 3- and 4-bed suites (priced per bed, so the split only matters for BMR rents and the fee base)
  const mix = { "3": units, };
  const aff = vliUnits ? { VLI: { "3": Math.min(vliUnits, units) } } : null;
  const acct = account({ units_mix: mix, net_sf: net, res_gross: geo.res_gross, retail_sf: geo.retail_sf, lobby_sf: geo.lobby_sf,
                         stories, lot_sf: site.lot_sf, s, affordable: aff, fee_mode, per_bed_beds: beds });
  return Object.assign(acct, { stories, net_sf: net, res_gross: geo.res_gross, retail_sf: geo.retail_sf, mix, beds, affordable: aff });
}

function aptCapped(site, stories, s, fee_mode, env, unitCap, vliUnits) {
  // apartments; with a unit cap, the extra area makes the capped units larger (more bedrooms, to the 3BR price)
  const geo = siteBuilding(site, stories, s, "in_lieu", env);
  let mix = geo.mix;
  if (unitCap && sumv(mix) > unitCap) {
    const sizes = A.unit_size_sf.by_bedrooms, raw = {};
    for (const b in mix) raw[b] = unitCap * mix[b] / sumv(mix);
    mix = largestRemainder(raw, unitCap);
    // upgrade bedrooms while the area allows
    let used = 0; for (const b in mix) used += mix[b] * sizes[b];
    for (const [from, to] of [["0", "1"], ["1", "2"], ["2", "3"]]) {
      while ((mix[from] || 0) > 0 && used + sizes[to] - sizes[from] <= geo.net_sf) { mix[from]--; mix[to] = (mix[to] || 0) + 1; used += sizes[to] - sizes[from]; }
    }
  }
  const aff = vliUnits ? { VLI: spread(Math.min(vliUnits, sumv(mix)), mix) } : null;
  const acct = account({ units_mix: mix, net_sf: geo.net_sf, res_gross: geo.res_gross, retail_sf: geo.retail_sf, lobby_sf: geo.lobby_sf,
                         stories, lot_sf: site.lot_sf, s, affordable: aff, fee_mode, loc: site.rent_factor ?? 1.0 });
  return Object.assign(acct, { stories, net_sf: geo.net_sf, res_gross: geo.res_gross, retail_sf: geo.retail_sf, mix, affordable: aff });
}

export function sb79Band(site, data) {
  let best = null;
  for (const st of data.bart) {
    const dy = (site.lat - st.lat) * 69.05, dx = (site.lon - st.lon) * 69.05 * Math.cos(st.lat * Math.PI / 180);
    const mi = Math.hypot(dx, dy);
    if (!best || mi < best.mi) best = { station: st.name, mi };
  }
  const band = data.sb79.tier1.find(b => best.mi <= b.max_mi);
  return { ...best, band: band || null };
}

// one design: returns the building + land + need, or {blocked: reason}
export function design(site, data, o) {
  const s = o.s, zrow = data.zoning.districts[site.district];
  const std = allowedEnvelope(zrow, "in_lieu", data.zoning.state_bonus);
  const layout = o.layout || "apartments";
  const lb = landBasis(site, s);
  let env = std, unitCap = null, vliUnits = 0, fee = "in_lieu", law = [], maxStories = std ? std.stories : 0;
  if (o.pathway === "zoning") {
    if (!std) return { blocked: `${site.district || "This district"} does not permit multi-unit housing` };
    law.push(`${std.basis}: ${std.stories} stories${std.far ? `, FAR ${std.far}` : ""}${std.du_ac ? `, ${std.du_ac} du/ac` : ""}; full in-lieu fee`);
  } else if (o.pathway === "bonus" || o.pathway === "sb79bonus" || o.pathway === "sb79") {
    let baseEnv = std;
    if (o.pathway !== "bonus") {
      const tod = sb79Band(site, data);
      if (!tod.band) return { blocked: `${tod.mi.toFixed(2)} mi from ${tod.station} BART: outside SB 79's 1/2-mile zone` };
      if (!zrow || !zrow.residential) {
        // SB 79 makes housing an allowed use on residential, mixed-use or commercial sites; the table holds the district
        if (!zrow) return { blocked: "no zoning district on record for this parcel" };
      }
      baseEnv = { stories: storiesUnder(tod.band.height_ft), far: tod.band.far, du_ac: tod.band.du_ac,
                  ground: zrow && zrow.ground, lot_coverage: zrow && zrow.lot_coverage,
                  basis: `SB 79 Tier 1, ${tod.band.band} of ${tod.station} BART (${tod.mi.toFixed(2)} mi)` };
      if (std) { // a local standard that allows more still applies
        baseEnv.stories = Math.max(baseEnv.stories, std.stories);
        baseEnv.far = std.far && baseEnv.far ? Math.max(baseEnv.far, std.far) : null;
        baseEnv.du_ac = std.du_ac && baseEnv.du_ac ? Math.max(baseEnv.du_ac, std.du_ac) : null;
      }
      law.push(`${baseEnv.basis}: ${tod.band.height_ft} ft (${baseEnv.stories} stories), ${tod.band.du_ac} du/ac, residential FAR ${tod.band.far}`);
    } else if (!std) return { blocked: `${site.district || "This district"} does not permit multi-unit housing` };
    const top = Math.min(A.height_search.max_stories, baseEnv.stories);
    const baseUnits = siteBuilding(site, top, s, "in_lieu", baseEnv).units;
    if (o.pathway === "sb79") {
      env = baseEnv; maxStories = baseEnv.stories; fee = "sb79";      // the set-aside is sized below, at the chosen height
    } else {
      const b = bonusPct(o.vliPct, o.extraVli || 0, data.density_bonus);
      vliUnits = Math.ceil((o.vliPct + (o.vliPct >= 15 ? (o.extraVli || 0) : 0)) / 100 * baseUnits);
      unitCap = Math.ceil(baseUnits * (1 + b));
      fee = "iho_combo";
      // waivers: the bonus needs floor area; the game lets height run to the search max, FAR and du/ac are waived
      env = { ...baseEnv, far: null, du_ac: null };
      maxStories = o.pathway === "bonus" ? A.height_search.max_stories : baseEnv.stories;
      law.push(`base ${baseUnits} units; ${o.vliPct}% VLI${o.extraVli && o.vliPct >= 15 ? ` + ${o.extraVli}% more (AB 1287)` : ""} = ${vliUnits} VLI units -> ${(b * 100).toFixed(2).replace(/\.?0+$/, "")}% bonus -> up to ${unitCap} units`);
      law.push(o.pathway === "bonus" ? "waivers: height/FAR waived as needed (2800 Telegraph got 6 stories on a 3-story base)" : "SB 79 base: no height beyond SB 79's");
      if (!b) law.push("under 5% VLI: no bonus");
    }
  }
  const stories = Math.max(A.height_search.min_stories, Math.min(o.stories || maxStories, maxStories));
  if (fee === "sb79") {                    // SB 79: 11+ units -> 10% VLI on site; Berkeley's IHO fee on the rest of 20%
    const u = layout === "beds" ? Math.max(1, Math.round(Math.floor(siteBuilding(site, stories, s, "in_lieu", env).net_sf / BED.sf_per_bed) / BED.beds_per_unit))
                                : siteBuilding(site, stories, s, "in_lieu", env).units;
    vliUnits = u >= 11 ? Math.ceil(0.10 * u) : 0;
    fee = vliUnits ? "iho_combo" : "in_lieu";
    law.push(vliUnits ? `SB 79: ${vliUnits} VLI units (10% of ${u}); IHO combination fee on the rest of Berkeley's 20%` : "under 11 units: no SB 79 set-aside; IHO in-lieu fee");
  }
  const b = layout === "beds"
    ? bedBuilding(site, stories, s, fee, env, unitCap, vliUnits)
    : (o.pathway === "zoning" ? siteBuilding(site, stories, s, "in_lieu", env) : aptCapped(site, stories, s, fee, env, unitCap, vliUnits));
  if (!b || b.units < 1) return { blocked: "nothing fits at this height" };
  const need = needFor(b, lb.basis, s);
  const yoc = b.noi / (b.cost_ex_land + lb.basis);
  return { b, land: lb, need, yoc, gap: yoc - b.hurdle, surplus: b.rlv - lb.basis, pencils: b.rlv >= lb.basis,
           stories, maxStories, law, unitCap, vliUnits, fee };
}

// (c) re-design a RECORDED project (the pipeline mode). Levers, each LABELED in the ledger:
//   vli       -- VLI units on site (replaces the record's affordable units; spread over the mix as the IHO requires)
//   addUnits  -- units beyond the approved count, at the project's own average size and mix; the extra floor area is
//                stacked as whole floors at the project's average floor plate (gross / stories), so height and
//                construction tier follow. A by-the-bed project adds beds at its own beds per unit.
//   fee_mode  -- "legacy_ahmf" (vested before 2023-04-01) or "iho_combo" (today's ordinance)
//   bonusTable-- with p.base_units on record, the bonus the unit count needs and the VLI share that buys it
export function recordVariant(p, s, data, { vli = null, addUnits = 0, fee_mode = null } = {}) {
  const units0 = sumv(p.mix);
  let mix = { ...p.mix }, gross = p.gross, net_rec = p.net_rec, stories = p.stories;
  if (addUnits > 0) {
    const raw = {}; for (const b in mix) raw[b] = addUnits * mix[b] / units0;
    const add = largestRemainder(raw, addUnits);
    for (const b in add) mix[b] = (mix[b] || 0) + add[b];
    const k = (units0 + addUnits) / units0;
    const res0 = (p.gross ? p.gross - p.commercial : p.net_rec / s.efficiency);
    const plate = (p.gross || res0) / p.stories;
    const extra = res0 * (k - 1);
    if (gross) gross = gross + extra; else net_rec = net_rec * k;
    stories = p.stories + Math.ceil(extra / plate - 1e-9);
  }
  const units = sumv(mix);
  let affordable = null;
  if (vli !== null) affordable = vli > 0 ? { VLI: spread(Math.min(vli, units), mix) } : {};
  const r = recordProject({ ...p, mix, gross, net_rec, stories, fee_mode: fee_mode || p.fee_mode }, s, affordable ? { affordable } : {});
  // the density bonus this unit count needs over the recorded base project, and what buys it (65915(f)(2), AB 1287)
  let bonus = null;
  if (p.base_units) {
    const needPct = (units / p.base_units - 1) * 100;
    const vliN = vli !== null ? vli : (p.affordable_text.match(/VLI (\d+)/) || [0, 0])[1] * 1;
    const vliPct = 100 * vliN / p.base_units;
    const have = bonusPct(Math.min(vliPct, 15), Math.max(0, vliPct - 15), data.density_bonus) * 100;
    bonus = { base_units: p.base_units, needPct, vliPct, have, max_units: Math.ceil(p.base_units * (1 + have / 100) - 1e-9),
              ok: units <= Math.ceil(p.base_units * (1 + have / 100) - 1e-9) };
  }
  return { ...r, units, stories, bonus };
}

// (d) value / cost, beside the hurdle verdict. value = NOI / the exit cap rate (no developer's margin); cost = every
//     cost but land + the land basis. >= 1: the finished building is worth at least what it cost; the hurdle verdict
//     says whether it also clears the developer's spread (cap + 1.25%). Computed from fields the port returns.
export function valueCost(acct, landBasis, cap) {
  const value = acct.noi / cap, cost = acct.cost_ex_land + landBasis, ratio = value / cost;
  const clears = acct.noi / cost >= acct.hurdle;
  const worth = ratio < 1 ? "worth less than it cost" : ratio < 1.05 ? "worth about what it cost" : "worth more than it cost";
  const reading = ratio < 1 ? worth : `${worth}, ${clears ? "clearing" : "short of"} a developer's margin`;
  return { value, cost, ratio, clears, reading };
}
