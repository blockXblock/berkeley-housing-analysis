// pencil_js_parity.mjs -- does docs/play/pencil.js (the game's model) reproduce scripts/v4/pencil_out.py? Every parcel of the 2026-10-28 zoned citywide pass
// (5 of its columns) and every pipeline project (3 scenarios). The CSV rounds rent multiples to 4 places.
import fs from "node:fs";
// pencil.js is a browser module next to the page; load it by source so docs/ needs no node package.json
const PLAY = new URL("../../docs/play/", import.meta.url);
const P = await import("data:text/javascript;base64," + fs.readFileSync(new URL("pencil.js", PLAY)).toString("base64"));
const data = JSON.parse(fs.readFileSync(new URL("game_data.json", PLAY)));
P.init(data);
const S = data.scenarios, { cols, cats, rows } = data.parcels;
const ix = Object.fromEntries(cols.map((c, i) => [c, i]));
const site = r => ({ key: r[ix.key], lot_sf: r[ix.lot_sf], rent_factor: r[ix.rent_factor],
  euv: { low: r[ix.euv][0], base: r[ix.euv][1], high: r[ix.euv][2] }, district: cats.district[r[ix.district]] });

const checks = [
  ["py_in_lieu_base", "in_lieu", "base", false], ["py_in_lieu_unfavorable", "in_lieu", "unfavorable", false],
  ["py_z_in_lieu_base", "in_lieu", "base", true], ["py_z_on_site_base", "on_site", "base", true],
  ["py_z_in_lieu_favorable", "in_lieu", "favorable", true],
];
let fails = 0;
for (const [col, fm, sc, zoned] of checks) {
  let n = 0, bad = 0, worst = 0, ex = null;
  for (const r of rows) {
    const py = r[ix[col]], st = site(r);
    let env = null;
    if (zoned) {
      env = P.allowedEnvelope(data.zoning.districts[st.district], fm, data.zoning.state_bonus);
      if (!env) { if (py !== null) { bad++; ex ??= [st.key, "env null", py]; } continue; }
    }
    if (py === null) { bad++; ex ??= [st.key, "py null"]; continue; }
    const be = P.breakEven(st, S[sc], fm, env), js = P.bestRow(be.rows).rent_mult_needed;
    const d = Math.abs(js - py); n++;
    if (d > worst) worst = d;
    if (d > 6e-5) { bad++; ex ??= [st.key, js, py]; }
  }
  console.log(`${col.padEnd(24)} ${n} parcels  mismatches ${bad}  worst |d| ${worst.toExponential(2)}${ex ? "  e.g. " + JSON.stringify(ex) : ""}`);
  fails += bad;
}
let pn = 0, pbad = 0;
for (const p of data.pipeline) {
  if (p.verdict === "insufficient_data") continue;
  for (const sc of ["favorable", "base", "unfavorable"]) {
    const js = P.recordProject(p, S[sc]), py = p.py[sc];
    const d = Math.max(Math.abs(js.gap - py.gap), Math.abs(js.rent_mult_needed - py.need) / 100, Math.abs(js.noi - py.noi) / 1e6);
    pn++;
    if (d > 1e-9) { pbad++; console.log("  MISMATCH", p.address, sc, js.gap, py.gap, js.noi, py.noi); }
  }
}
console.log(`pipeline projects        ${pn} runs  mismatches ${pbad}`);
fails += pbad;
console.log(fails ? `FAIL (${fails})` : "PASS");
process.exit(fails ? 1 : 0);
