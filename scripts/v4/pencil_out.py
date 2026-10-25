"""pencil_out.py -- does it pencil? (1) the stalled "Entitled but Inactive" projects, (2) the break-even height of a
hypothetical building on any site. MACHINERY, read-only.

John, 2026-10-25: "For each project in the 'Entitled 3+ yrs, inactive' stage, estimate whether it pencils financially at
its approved height ... do these projects stall because they don't pencil, or for other reasons?" and "how high each
[Elmwood] project must be to have enough units to allow the project to pencil out. Later, we will apply that analysis to
each potential building site in Berkeley."

Built on JN-Feasibility Part 2 (scripts/v4/proforma_projects.py): its Rent Board lease-up rents and its decision rule,
yield on cost against the exit cap rate plus a spread. Every market assumption comes from ONE versioned file,
data/assumptions/pencil_out_<date>.yaml (low / base / high, source, date); none is written here.

Every input row carries a LABEL:
  RECORD      -- from the City's records or the assessor (staff reports, plan sets, the Rent Board registry, the roll)
  ASSUMPTION  -- from the assumptions file
A project missing a core RECORD input is `insufficient_data`; no gap is filled with a guess.

Verdicts are four-valued, never collapsed: pencils (clears the hurdle in the unfavorable case) / marginal (clears it in
the base or favorable case only) / does_not (fails even in the favorable case) / insufficient_data.

THE SITE MODEL (one function, any parcel): a ground floor (retail + lobby) and residential floors above; height ->
construction tier (cost and months); net area -> units over the Rent Board bedroom mix; NOI -> value at the hurdle ->
residual land value (RLV) = value - every cost except land. A site pencils at a height when RLV >= its land basis, the
higher of market land value and the existing use's value (John, 2026-10-25: "Both, take the higher").
"""
from __future__ import annotations

import csv
import json
import math
import sqlite3
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "v4"))
import proforma_projects as pp  # noqa: E402

A = pp.A                                    # the same versioned assumptions file Part 2 reads
ASSUMPTIONS_FILE = pp.ASSUMPTIONS
RECORD_INPUTS = ROOT / "data/derived/pencil_out/project_inputs_record_2026-10-25.csv"
ESC_2024_TO_PRICE_YEAR = A["hard_cost_escalation"]["by_year"][A["price_year"]]   # BFA24 2024 $ -> price year

SCENARIOS = ("favorable", "base", "unfavorable")


# ------------------------------------------------------------------------------------------- assumptions -> scenario
def scenario(name="base", **override):
    """every assumption the model uses, for one scenario. favorable = each assumption at the end of its band that helps
    a project pencil; unfavorable = the other end. `override` sets single values (the sensitivity runs)."""
    f, u = name == "favorable", name == "unfavorable"

    def pick(entry, good="low"):
        """a band entry's value for this scenario; `good` is the end that helps a project pencil."""
        if name == "base":
            return entry["base"]
        bad = "high" if good == "low" else "low"
        v = entry.get(good if f else bad)
        return entry["base"] if v is None else v
    cov = A["lot_coverage"]
    s = dict(
        hard_mult=1.0 if name == "base" else A["construction_tiers"]["band"]["low" if f else "high"],
        rent_mult=pick(A["market_rent_multiplier"], "high"),
        soft=pick(A["soft_costs_ex_fees_ex_financing"]),
        rate=pick(A["construction_financing"]["rate"]),
        cap=pick(A["exit_cap_rate_today"]),
        spread=pick(A["yield_spread_over_exit_cap"]),
        opex=pick(A["operating_expenses_share_of_egi"]),
        efficiency=pick(A["efficiency"], "high"),
        cov_ground=cov["base"]["ground"] if name == "base" else cov["high" if f else "low"]["ground"],
        cov_upper=cov["base"]["upper"] if name == "base" else cov["high" if f else "low"]["upper"],
        retail_share=pick(A["ground_floor_retail_share"], "high"),
        site_work=pick(A["site_work_per_land_sf_2024"]),
        land_psf=pick(A["land_market_per_lot_sf"]),
        euv_rent=pick(A["existing_use_value"]["retail_nnn_rent_per_sf_yr"]),
        euv_vacancy=pick(A["existing_use_value"]["retail_vacancy"], "high"),
        euv_cap=pick(A["existing_use_value"]["retail_cap_rate"]),
    )
    s.update(override)
    return s


# where each scenario key lives in the assumptions file (for the RECORD/ASSUMPTION ledger and the sensitivity runs)
ASSUMPTION_KEYS = {
    "hard_mult": "construction_tiers.band", "rent_mult": "market_rent_multiplier", "soft": "soft_costs_ex_fees_ex_financing",
    "rate": "construction_financing.rate", "cap": "exit_cap_rate_today", "spread": "yield_spread_over_exit_cap",
    "opex": "operating_expenses_share_of_egi", "efficiency": "efficiency", "cov_ground": "lot_coverage.ground",
    "cov_upper": "lot_coverage.upper", "retail_share": "ground_floor_retail_share", "site_work": "site_work_per_land_sf_2024",
    "land_psf": "land_market_per_lot_sf", "euv_rent": "existing_use_value.retail_nnn_rent_per_sf_yr",
    "euv_vacancy": "existing_use_value.retail_vacancy", "euv_cap": "existing_use_value.retail_cap_rate",
}


def tier_for(storeys: int, height_ft: float) -> dict:
    for t in A["construction_tiers"]["tiers"]:
        if storeys <= t["max_storeys"] and height_ft <= t["max_height_ft"]:
            return t
    return A["construction_tiers"]["tiers"][-1]


def height_ft(storeys: int) -> float:
    f = A["floor_to_floor_ft"]["base"]
    return f["ground"] + f["upper"] * (storeys - 1)


# ------------------------------------------------------------------------------------------------- rents (RECORD)
def rents():
    """market rents per unit/month by bedrooms and the bedroom mix: the Rent Board lease-up pool (JN-Feasibility Part 2a);
    per-bed rent: the median per-bed asking rent of the near-campus buildings' leasing sites (Part 2f)."""
    con = sqlite3.connect(f"file:{pp.V4}?mode=ro", uri=True)
    r = pp.lease_ups(con)
    beds = []
    for rd in json.load(open(pp.LEASING_EVIDENCE))["readings"]:
        for fp in rd["floor_plans"]:
            if str(fp.get("rent_basis", "")).startswith("per bed") and fp.get("rent"):
                beds.append(fp["rent"])
    return dict(pool_rent={k: float(v) for k, v in r["pool_rent"].items()},
                pool_mix={k: float(v) for k, v in r["pool_mix"].items()},
                lease_ups=len(r["market"]), per_bed=st.median(beds) if beds else None, per_bed_n=len(beds))


def bmr_rent(tier: str, bedrooms: str) -> float:
    """net monthly rent of a below-market unit: the City's 2025 gross rent less the utility allowance."""
    b = A["bmr_rents_monthly"]
    key = str(min(int(bedrooms), 3))
    ua = b["utility_allowance"][key]
    if tier == "VLI":
        return b["vli_50_ami_gross"][key] - ua
    if tier == "ELI":
        return b["vli_50_ami_gross"][key] * A["eli_rent_share_of_vli"]["base"] - ua
    if tier == "LI":
        return b["li_capped_60_ami_gross"][key] - ua
    raise ValueError(tier)


# --------------------------------------------------------------------------------------- the money (one building)
def account(*, units_mix, net_sf, res_gross, retail_sf, lobby_sf, storeys, lot_sf, s, R, affordable=None,
            fee_mode="in_lieu", per_bed_beds=None):
    """NOI, every cost but land, value at the hurdle, residual land value -- for one building in scenario `s`.
    units_mix: {bedrooms: market+affordable unit count}; affordable: {tier: {bedrooms: n}} carved out of units_mix;
    fee_mode: 'in_lieu' (IHO fee on net area), 'on_site' (no fee: 20% on-site units), 'legacy_ahmf' (BMC 22.20.065)."""
    affordable = affordable or {}
    fees_a, fin = A["berkeley_fees"], A["construction_financing"]
    units = sum(units_mix.values())
    aff_by_b = {}
    for tier, by_b in affordable.items():
        for b, n in by_b.items():
            aff_by_b[b] = aff_by_b.get(b, 0) + n
    # revenue
    if per_bed_beds:                                   # group living: per-bed rent x beds, less the affordable units' beds
        aff_units = sum(aff_by_b.values())
        market_gpr = R["per_bed"] * s["rent_mult"] * 12 * per_bed_beds * (units - aff_units) / units
    else:
        market_gpr = sum((n - aff_by_b.get(b, 0)) * R["pool_rent"][str(min(int(b), 3))] * s["rent_mult"] * 12
                         for b, n in units_mix.items())
    market_noi = market_gpr * (1 - pp.VACANCY) * (1 - s["opex"])
    bmr = A["bmr_rents_monthly"]
    bmr_noi = sum(n * (bmr_rent(t, b) * 12 * (1 - bmr["bmr_vacancy"]) - bmr["bmr_opex_per_unit_yr"])
                  for t, by_b in affordable.items() for b, n in by_b.items())
    retail_noi = retail_sf * pp.RETAIL_RENT * (1 - pp.RETAIL_VACANCY) * (1 - pp.RETAIL_EXPENSES)
    noi = market_noi + bmr_noi + retail_noi
    # cost (no land)
    t = tier_for(storeys, height_ft(storeys))
    esc = ESC_2024_TO_PRICE_YEAR
    hard = ((res_gross + lobby_sf) * t["per_gsf_2024"] + retail_sf * A["retail_shell_cost_per_gsf_2024"]["base"]
            + lot_sf * s["site_work"]) * esc * s["hard_mult"]
    soft = hard * s["soft"]
    other = fees_a["other_city_fees_per_unit_2024"] * esc * units
    school = fees_a["school_fee_per_residential_sf"] * net_sf
    art = fees_a["public_art_in_lieu_share"] * hard
    if fee_mode == "in_lieu":
        afford_fee = fees_a["inclusionary_in_lieu_per_rufa_sf"] * max(0.0, net_sf - fees_a["in_lieu_rufa_deduction_sf"])
    elif fee_mode == "legacy_ahmf":
        vli_li = sum(n for tr, by_b in affordable.items() if tr in ("ELI", "VLI", "LI") for n in by_b.values())
        afford_fee = max(0.0, units * A["legacy_ahmf_per_unit"]["base"] * (1 - vli_li / (0.20 * units)))
    else:
        afford_fee = 0.0
    loan = (hard + soft) * fin["loan_to_cost"]
    interest = loan * fin["average_outstanding"] * s["rate"] * t["construction_months"] / 12 + loan * fin["points"]
    cost_ex_land = hard + soft + other + school + art + afford_fee + interest
    hurdle = s["cap"] + s["spread"]
    value = noi / hurdle
    return dict(units=units, noi=noi, market_noi=market_noi, other_noi=bmr_noi + retail_noi, hard=hard, soft=soft,
                fees=other + school + art + afford_fee, afford_fee=afford_fee, interest=interest,
                cost_ex_land=cost_ex_land, hurdle=hurdle, value=value, rlv=value - cost_ex_land, tier=t["name"],
                height_ft=height_ft(storeys))


# ------------------------------------------------------------------------------------------ part A: hypothetical sites
def mix_units(net_sf: float, R) -> dict:
    """units over the Rent Board bedroom mix that fit in `net_sf` (whole units, largest remainders)."""
    sizes = A["unit_size_sf"]["by_bedrooms"]
    avg = sum(R["pool_mix"][b] * sizes[b] for b in R["pool_mix"])
    n = int(net_sf // avg)
    raw = {b: n * R["pool_mix"][b] for b in R["pool_mix"]}
    out = {b: int(math.floor(v)) for b, v in raw.items()}
    for b in sorted(raw, key=lambda b: raw[b] - out[b], reverse=True)[: n - sum(out.values())]:
        out[b] += 1
    return out


def site_building(site, storeys, s, R, fee_mode="in_lieu"):
    """a hypothetical building of `storeys` on a site: ground floor retail + lobby, residential above."""
    lot = site["lot_sf"]
    ground = lot * s["cov_ground"]
    retail = ground * s["retail_share"]
    res_gross = lot * s["cov_upper"] * (storeys - 1)
    net = res_gross * s["efficiency"]
    mix = mix_units(net, R)
    affordable = None
    if fee_mode == "on_site":                          # 20% of units on site: half VLI, half LI (rent capped at 60% AMI)
        k = math.ceil(A["berkeley_fees"]["on_site_share"] * sum(mix.values()))
        vli, li = math.ceil(k / 2), k - math.ceil(k / 2)
        affordable = {"VLI": _spread(vli, mix), "LI": _spread(li, mix)}
    acct = account(units_mix=mix, net_sf=net, res_gross=res_gross, retail_sf=retail, lobby_sf=ground - retail,
                   storeys=storeys, lot_sf=lot, s=s, R=R, affordable=affordable, fee_mode=fee_mode)
    acct.update(storeys=storeys, net_sf=net, res_gross=res_gross, retail_sf=retail, mix=mix)
    return acct


def _spread(k, mix):
    """k affordable units spread over the bedroom mix in proportion (the IHO requires comparable units)."""
    tot = sum(mix.values())
    raw = {b: k * n / tot for b, n in mix.items()}
    out = {b: int(math.floor(v)) for b, v in raw.items()}
    for b in sorted(raw, key=lambda b: raw[b] - out[b], reverse=True)[: k - sum(out.values())]:
        out[b] += 1
    return {b: n for b, n in out.items() if n}


def land_basis(site, s):
    """the land basis: the higher of market land (lot x $/sqft) and the existing use's value (EUV)."""
    market = site["lot_sf"] * s["land_psf"]
    euv = (site.get("existing_retail_sf") or 0) * s["euv_rent"] * (1 - s["euv_vacancy"]) / s["euv_cap"]
    return dict(market=market, euv=euv, basis=max(market, euv), binding="existing use" if euv > market else "market land")


def break_even(site, s, R, fee_mode="in_lieu"):
    """every height in the search range: RLV vs land basis, the rent multiplier that would make it pencil; and the lowest
    height that pencils (None if none does)."""
    hs = A["height_search"]
    lb = land_basis(site, s)
    rows = []
    for n in range(hs["min_storeys"], hs["max_storeys"] + 1):
        b = site_building(site, n, s, R, fee_mode)
        # the rent multiplier at which RLV = land basis (NOI is linear in market rent; costs do not depend on rent)
        need = ((lb["basis"] + b["cost_ex_land"]) * b["hurdle"] - b["other_noi"]) / (b["market_noi"] / s["rent_mult"])
        rows.append(dict(storeys=n, height_ft=b["height_ft"], tier=b["tier"], units=b["units"], noi=b["noi"],
                         value=b["value"], cost_ex_land=b["cost_ex_land"], rlv=b["rlv"], land_basis=lb["basis"],
                         surplus=b["rlv"] - lb["basis"], pencils=b["rlv"] >= lb["basis"], rent_mult_needed=need,
                         rlv_per_unit=b["rlv"] / b["units"] if b["units"] else None))
    first = next((r["storeys"] for r in rows if r["pencils"]), None)
    return dict(rows=rows, break_even_storeys=first, land=lb)


# ----------------------------------------------------------------------------------------- part B: stalled projects
CORE = ("units", "floor_area", "unit_mix", "stories", "land_basis")


def record_inputs(path=RECORD_INPUTS):
    """the RECORD inputs per anchor record (staff reports, plan sets, planning descriptions), each with its source."""
    out = {}
    for r in csv.DictReader(open(path)):
        out.setdefault(r["anchor"], {"address": r["address"]})[r["field"]] = r
    return out


def parse_mix(text: str) -> dict:
    """'studio 22; 1BR 34; 2BR 10' -> {'0': 22, '1': 34, '2': 10} (4BR/5BR kept as 4/5)."""
    out = {}
    for part in text.split(";"):
        k, n = part.strip().rsplit(" ", 1)
        b = "0" if k.lower() == "studio" else k.upper().replace("BR", "")
        out[b] = out.get(b, 0) + int(n)
    return out


def parse_affordable(text: str, mix: dict) -> dict:
    """'VLI 23; LI 2' -> {'VLI': {...}, 'LI': {...}} spread over the mix (MOD units rent near market: left in market)."""
    tiers = {}
    for part in text.split(";"):
        t, n = part.strip().split(" ")
        if t in ("ELI", "VLI", "LI"):
            tiers[t] = _spread(int(n), mix)
    return tiers


_ASSESSOR = {}


def assessor_index(asr) -> dict:
    """canonical APN -> (land + improvements, latest recorded document), built once per process."""
    if not _ASSESSOR:
        for apn, land, imps, ldd in asr.execute("SELECT APN, Land, Imps, LatestDocumentDate FROM parcels"):
            try:
                _ASSESSOR[pp.to_canonical_apn(apn, "alameda")] = ((land or 0) + (imps or 0), ldd)
            except Exception:
                pass
    return _ASSESSOR


def land_basis_record(con_v4, asr, anchor: str, lot_sf: float, s):
    """a stalled project's land basis: RECORD = the assessed value of its parcels when the last recorded document is a
    2018+ transfer (Prop 13 resets assessment at a sale); else ASSUMPTION = lot x market $/sqft. Both are returned."""
    pid = con_v4.execute("SELECT project_id FROM projects WHERE json_extract(notes, '$.anchor') = ?", (anchor,)).fetchone()
    apns = [a for (a,) in con_v4.execute("""SELECT pi.apn_normalized FROM project_parcels pp
                 JOIN parcel_identifiers pi ON pi.parcel_id = pp.parcel_id AND pi.is_current = 1
                 WHERE pp.project_id = ?""", (pid[0],))] if pid else []
    linked_lot = sum(a or 0 for (a,) in con_v4.execute(f"""SELECT pa.lot_sqft FROM parcel_identifiers pi
                 JOIN parcel_area pa ON pa.parcel_id = pi.parcel_id WHERE pi.is_current = 1
                 AND pi.apn_normalized IN ({','.join('?' * len(apns))})""", apns)) if apns else 0
    idx = assessor_index(asr)
    rows = [(a, *idx[a]) for a in apns if a in idx]
    assessed = sum(v for _, v, _ in rows)
    recent = bool(rows) and all((d or "") >= "2018-01-01" for _, _, d in rows)
    # the staff report's site is larger than the parcels v4 links (e.g. a two-parcel site with one linked): partial
    partial = bool(lot_sf) and linked_lot < 0.8 * lot_sf
    return dict(apns=apns, assessed=assessed, last_documents=[d for _, _, d in rows], recent_transfer=recent,
                linked_lot=linked_lot, partial_site=partial, market=(lot_sf or 0) * s["land_psf"])


def stalled_project(anchor, rec, R, con_v4, asr, s, use_record_land=True):
    """one stalled project at its approved size: inputs with labels, the account, and missing core inputs."""
    g = lambda f: rec.get(f, {}).get("value")                     # noqa: E731
    ledger, missing = [], []

    def note(field, value, label, source):
        ledger.append(dict(anchor=anchor, field=field, value=value, label=label, source=source))
    units = int(g("units")) if g("units") else None
    gross = float(g("gross_floor_area")) if g("gross_floor_area") else None
    net_rec = float(g("net_unit_area")) if g("net_unit_area") else None
    stories = int(g("stories")) if g("stories") else None
    lot = float(g("lot_area")) if g("lot_area") else None
    mix = parse_mix(g("unit_mix")) if g("unit_mix") else None
    beds = int(g("bedrooms")) if g("bedrooms") else None
    commercial = float(g("commercial_floor_area") or 0)
    for f, v in (("units", units), ("stories", stories), ("lot_area", lot)):
        if v is None:
            missing.append(f)
        else:
            note(f, v, "RECORD", rec[f]["source"] + " " + rec[f]["locator"])
    partial = "PARTIAL" in (rec.get("gross_floor_area", {}).get("note") or "")
    if gross and not partial:
        note("gross_floor_area", gross, "RECORD", rec["gross_floor_area"]["source"] + " " + rec["gross_floor_area"]["locator"])
    elif net_rec:
        note("net_unit_area", net_rec, "RECORD", rec["net_unit_area"]["source"] + " " + rec["net_unit_area"]["locator"])
    else:
        missing.append("floor_area")
    if mix:
        note("unit_mix", g("unit_mix"), "RECORD", rec["unit_mix"]["source"] + " " + rec["unit_mix"]["locator"])
        if units and sum(mix.values()) != units:
            missing.append("unit_mix (does not sum to units)")
    elif beds:
        note("bedrooms", beds, "RECORD", rec["bedrooms"]["source"])
        missing.append("unit_mix")
    else:
        missing.append("unit_mix")
    if missing:
        return dict(anchor=anchor, address=rec["address"], verdict="insufficient_data", missing=missing, ledger=ledger)
    # areas: residential gross = gross less commercial; net = gross x efficiency (ASSUMPTION) unless net is on record
    res_gross = (gross - commercial) if gross else net_rec / s["efficiency"]
    net = net_rec if net_rec else res_gross * s["efficiency"]
    if not net_rec:
        note("net_unit_area", round(net), "ASSUMPTION", f"gross x efficiency ({ASSUMPTIONS_FILE.name}: efficiency)")
    else:
        note("residential_gross", round(res_gross), "ASSUMPTION", f"net / efficiency ({ASSUMPTIONS_FILE.name}: efficiency)")
    affordable = parse_affordable(g("affordable"), mix) if g("affordable") else {}
    if g("affordable"):
        note("affordable", g("affordable"), "RECORD", rec["affordable"]["source"] + " " + rec["affordable"]["locator"])
    group = any(int(b) >= 4 for b in mix)
    per_bed_beds = sum(max(int(b), 1) * n for b, n in mix.items()) if group else None
    note("market_rent", "per-bed (leasing sites, median)" if group else "Rent Board lease-up pool by bedrooms",
         "RECORD", "JN-Feasibility Part 2a/2f (scripts/v4/proforma_projects.py)")
    lb = land_basis_record(con_v4, asr, anchor, lot, s)
    if use_record_land and lb["recent_transfer"] and lb["assessed"] > 0 and not lb["partial_site"]:
        basis, basis_label = lb["assessed"], "RECORD"
        note("land_basis", round(basis), "RECORD", f"assessed value, parcels {lb['apns']}, last document {lb['last_documents']}")
    else:
        basis, basis_label = lb["market"], "ASSUMPTION"
        why = (f"v4 links {lb['linked_lot']:,.0f} sf of the {lot:,.0f} sf site" if lb["partial_site"] else
               "no 2018+ transfer on record (assessment is stale)" if lb["apns"] else "no parcel linked")
        note("land_basis", round(basis), "ASSUMPTION", f"lot x market $/sqft ({why}; {ASSUMPTIONS_FILE.name}: land_market_per_lot_sf)")
    fee_mode = "legacy_ahmf"
    note("affordable_housing_fee", "BMC 22.20.065 formula, 2022 rate", "ASSUMPTION",
         f"{ASSUMPTIONS_FILE.name}: legacy_ahmf_per_unit (projects vested before 2023-03-31)")
    acct = account(units_mix=mix, net_sf=net, res_gross=res_gross, retail_sf=commercial,
                   lobby_sf=0.0, storeys=stories, lot_sf=lot, s=s, R=R, affordable=affordable, fee_mode=fee_mode,
                   per_bed_beds=per_bed_beds)
    yoc = acct["noi"] / (acct["cost_ex_land"] + basis)
    # the market-rent multiplier at which the project meets the hurdle (NOI is linear in market rent)
    need = ((basis + acct["cost_ex_land"]) * acct["hurdle"] - acct["other_noi"]) / (acct["market_noi"] / s["rent_mult"])
    return dict(rent_mult_needed=need, anchor=anchor, address=rec["address"], units=units, stories=stories, verdict=None, missing=[],
                ledger=ledger, acct=acct, land_basis=basis, land_label=basis_label, land=lb, yoc=yoc,
                gap=yoc - acct["hurdle"], rlv=acct["rlv"], rlv_minus_basis=acct["rlv"] - basis, group=group)


def evaluate_stalled(anchors=None):
    """every stalled project with RECORD inputs: three scenarios -> four-valued verdict, plus RLV vs land basis."""
    R = rents()
    recs = record_inputs()
    con = sqlite3.connect(f"file:{pp.V4}?mode=ro", uri=True)
    asr = sqlite3.connect(f"file:{pp.ASSESSOR}?mode=ro", uri=True)
    out = []
    for anchor in (anchors or recs):
        runs = {sc: stalled_project(anchor, recs[anchor], R, con, asr, scenario(sc)) for sc in SCENARIOS}
        b = runs["base"]
        if b["verdict"] == "insufficient_data":
            out.append(b)
            continue
        ok = {sc: runs[sc]["gap"] >= 0 for sc in SCENARIOS}
        b["verdict"] = ("pencils" if ok["unfavorable"] else "marginal" if (ok["base"] or ok["favorable"]) else "does_not")
        b["runs"] = {sc: dict(gap=runs[sc]["gap"], yoc=runs[sc]["yoc"], rlv=runs[sc]["rlv"], land_basis=runs[sc]["land_basis"],
                              rent_mult_needed=runs[sc]["rent_mult_needed"])
                     for sc in SCENARIOS}
        out.append(b)
    return dict(projects=out, rents=R)


def sensitivity_stalled(anchor, R=None):
    """one assumption at a time to its low and high end (others at base): the gap, and whether the verdict-relevant
    sign (base gap >= 0) flips."""
    R = R or rents()
    rec = record_inputs()[anchor]
    con = sqlite3.connect(f"file:{pp.V4}?mode=ro", uri=True)
    asr = sqlite3.connect(f"file:{pp.ASSESSOR}?mode=ro", uri=True)
    base = stalled_project(anchor, rec, R, con, asr, scenario("base"))
    if base.get("verdict") == "insufficient_data":
        return None
    fav, unf = scenario("favorable"), scenario("unfavorable")
    rows = []
    for k in ASSUMPTION_KEYS:
        lo = stalled_project(anchor, rec, R, con, asr, scenario("base", **{k: fav[k]}))["gap"]
        hi = stalled_project(anchor, rec, R, con, asr, scenario("base", **{k: unf[k]}))["gap"]
        rows.append(dict(assumption=k, file_key=ASSUMPTION_KEYS[k], favorable_gap=lo, unfavorable_gap=hi,
                         flips=(lo >= 0) != (base["gap"] >= 0) or (hi >= 0) != (base["gap"] >= 0)))
    rows.sort(key=lambda r: -abs(r["favorable_gap"] - r["unfavorable_gap"]))
    # flip points, others at base: the rent multiplier, the exit cap rate and the hard-cost multiplier that meet the hurdle
    gap_at = lambda k, v: stalled_project(anchor, rec, R, con, asr, scenario("base", **{k: v}))["gap"]   # noqa: E731
    lo, hi = 0.05, 2.0
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gap_at("hard_mult", mid) >= 0 else (lo, mid)
    flip = dict(rent_mult=base["rent_mult_needed"], exit_cap=base["yoc"] - scenario("base")["spread"],
                hard_mult=lo if gap_at("hard_mult", lo) >= 0 else None)
    return dict(anchor=anchor, base_gap=base["gap"], rows=rows, flip_points=flip)


# --------------------------------------------------------------------------------------------- Elmwood sites (RECORD)
ELMWOOD_SITES = [
    # lot: assessor polygon (docs/audit/2026-10-24_elmwood_option1b_parcel_check.md); existing building: assessor taxable
    # sqft (v4 parcel_area). Parking lots carry no existing building, so market land governs their basis.
    dict(key="7-eleven", name="2887 College Ave (7-Eleven)", apns=["053-1696-015-00"]),
    dict(key="five-monkeys", name="2901 College Ave (Nabolom / Five Little Monkeys)", apns=["052-1567-024-01"]),
    dict(key="wells-fargo", name="2711 Ashby Pl (Wells Fargo parking lot)", apns=["052-1567-016-00"]),
    dict(key="post-office", name="2701 + 2709 Webster St (Elmwood Post Office + lot)", apns=["052-1567-062-06", "052-1567-062-12"]),
]
CORNER_CSV = ROOT / "scratch/2026-10-24_corners/ce_parcels_option1b.csv"


def elmwood_sites():
    """the four Elmwood sites with RECORD facts: lot (assessor polygon), existing building sqft, assessed values."""
    poly = {r["apn"]: float(r["lot_sf_polygon"]) for r in csv.DictReader(open(CORNER_CSV))}
    con = sqlite3.connect(f"file:{pp.V4}?mode=ro", uri=True)
    out = []
    for s in ELMWOOD_SITES:
        q = con.execute(f"""SELECT pi.apn_normalized, pa.building_sqft_taxable, av.land, av.improvements
                 FROM parcel_identifiers pi JOIN parcel_area pa ON pa.parcel_id = pi.parcel_id
                 LEFT JOIN assessed_values av ON av.parcel_id = pi.parcel_id AND av.valid_to IS NULL
                 WHERE pi.is_current = 1 AND pi.apn_normalized IN ({','.join('?' * len(s['apns']))})""", s["apns"]).fetchall()
        out.append(dict(s, lot_sf=sum(poly[a] for a in s["apns"]), existing_retail_sf=sum(r[1] or 0 for r in q),
                        assessed_land=sum(r[2] or 0 for r in q), assessed_imps=sum(r[3] or 0 for r in q)))
    return out


def run_sites(sites, fee_modes=("in_lieu", "on_site")):
    R = rents()
    res = []
    for site in sites:
        for fm in fee_modes:
            for sc in SCENARIOS:
                be = break_even(site, scenario(sc), R, fm)
                res.append(dict(site=site["key"], name=site["name"], fee_mode=fm, scenario=sc, **{
                    k: be[k] for k in ("break_even_storeys",)}, land=be["land"], rows=be["rows"]))
    return dict(results=res, rents=R)
