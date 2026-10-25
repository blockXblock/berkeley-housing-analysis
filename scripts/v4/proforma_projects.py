"""proforma_projects.py -- JN-Feasibility Part 2: did Berkeley's actual housing projects pencil? (MACHINERY, read-only)

John, 2026-10-08 ("package it into JN-Feasibility"). JN-Feasibility Part 1 rebuilt UrbanSim's pro-forma on placeholder
inputs for one commercial strip. Part 2 runs the same model -- yield on cost against the exit cap rate plus a spread
(Part 1, Step 4b), never `profit > 0` -- on every v4 project of 5+ units (UC excluded), with OBSERVED inputs where v4
holds them and CITED or LABELED assumptions where it does not, then tests it on the buildings that were built.

OBSERVED (v4, read-only; berkeley.db for land)
  units, stories ............ v_projects (units_built_or_permitted / proposed_units; height_stories)
  floor area ................ built: the assessor's taxable building sqft (the new building); unbuilt: the area the
                              application states; kept at 500-2,000 gross sqft/unit, else the built median per unit
                              (the assessor's figure for an UNBUILT project is the OLD building on the lot)
  rents ..................... Rent Board lease-ups: tenancies starting within 24 months of the first CO in buildings
                              registered "Partially Covered" (new construction); affordable buildings, group/per-bed
                              buildings, Gov-Subsidized units and leases under 60% of the building's own same-size
                              median (likely unflagged inclusionary units) are kept out of the market figures
  land ...................... the assessor's Land $ on the project's parcels
  City fees ................. fees_paid (Accela Fees tab); else the median fee per unit of the projects that have it
  months approval -> permit . entitled_date -> bp_issued_date, carried on the land
  parking spaces ............ v_projects.parking_spaces (read from the City's text)
  commercial floor area ..... data/derived/commercial_area_evidence_<date>.json (a model reading of the City's text,
                              kept only with a verbatim quote stating the number)
  outcome ................... v_projects.status: went ahead (completed, under construction), waiting (entitled),
                              abandoned (withdrawn, void), in review, stale
CITED
  hard cost ................. Terner Center, "The Hard Costs of Construction" (March 2020): Bay Area "more than $380 per
                              square foot in 2018"; affordable +$48/sqft over market-rate; Type I +$65-71/sqft
                              -> market-rate 2018 base $332, Type I +$68
  escalation ................ TBD Consultants SF bid index, year on year to June (City & County of SF, AICCIE memos
                              Oct 2022 and Oct 21 2024); 2025 +3.5% (the City's adopted rate)
  exit cap rate ............. CBRE U.S. Cap Rate Survey, multifamily infill, Class A stabilized, Oakland (midpoints):
                              H2 2017 & H2 2019 4.50; H2 2023 & H1 2024 6.00. ESTIMATED 2021-22 from San Francisco
                              (H2 2021 3.75, H1 2022 3.75, H2 2022 4.75) + Oakland's observed 50 bps premium (H2 2017,
                              H2 2019); INTERPOLATED 2018 and 2020
  retail rent ............... $36/sqft/yr (Telegraph Ave asking rents $28-51, listings 2026-10)
  parking ................... $200/month (Berkeley monthly parking $150-325, 2026-10)
LABELED ASSUMPTIONS (central, band) -- values and sources now in data/assumptions/pencil_out_<date>.yaml
  soft costs 25% (20-30) . operating costs 35% of effective rent (30-40) . residential vacancy 5% . retail vacancy 20%,
  retail expenses 10% . parking occupancy 70% . spread over the exit cap 125 bps . land carry 7%/yr . hard-cost band +-10%
CALIBRATED
  one hard-cost factor, fitted so the median building that went ahead with a decision year <= 2019 meets the hurdle,
  and TESTED out of sample on those that went ahead with a decision year >= 2020. It is a catch-all for everything
  still unmodeled (real costs below Terner's mostly-affordable, SF-weighted sample; lower operating costs; smaller
  spreads), not a measured construction cost.
"""
from __future__ import annotations

import collections
import json
import sqlite3
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from housing_rules import to_canonical_apn  # noqa: E402
from housing_rules.address import normalize_address  # noqa: E402

V4 = ROOT / "databases/berkeley_housing_v4.db"
ASSESSOR = ROOT / "databases/berkeley.db"
COMMERCIAL_EVIDENCE = ROOT / "data/derived/commercial_area_evidence_2026-10-08.json"
# current (2026) asking rents from the buildings' own leasing sites -- per bed or per unit, each with URL + snippet
# (John, 2026-10-12: "collect and rerun"); used, when asked, for buildings the Rent Board registry has no lease-ups for
LEASING_EVIDENCE = ROOT / "data/derived/leasing_rents_evidence_2026-10-12.json"

# ---- CITED + LABELED: every value, with its source and band, lives in the versioned assumptions file (John,
# 2026-10-25: "never hardcode these"); the names below are the ones the model has always used
ASSUMPTIONS = ROOT / "data/assumptions/pencil_out_2026-10-25.yaml"


def load_assumptions(path=ASSUMPTIONS) -> dict:
    import yaml
    return yaml.safe_load(open(path))


A = load_assumptions()
ESCALATION = A["hard_cost_escalation"]["by_year"]
HARD_2018, TYPE_I_PREMIUM = A["hard_cost_2018_per_gsf"]["base"], A["type_i_premium_per_gsf"]["base"]
EXIT_CAP, EXIT_CAP_BASIS = A["exit_cap_rate"]["by_year"], A["exit_cap_rate"]["basis"]
RETAIL_RENT, PARKING_RENT = A["retail_rent_per_sf_yr"]["base"], A["parking_rent_per_month"]["base"]
# ---- LABELED ASSUMPTIONS (central, low, high)
SOFT = tuple(A["soft_cost_share"][k] for k in ("base", "low", "high"))
OPEX = tuple(A["opex_share"][k] for k in ("base", "low", "high"))
VACANCY, RETAIL_VACANCY = A["residential_vacancy"]["base"], A["retail_vacancy"]["base"]
RETAIL_EXPENSES, PARKING_OCC = A["retail_expenses"]["base"], A["parking_occupancy"]["base"]
SPREAD, CARRY, COST_BAND = A["yield_spread_over_exit_cap"]["base"], A["land_carry_rate"]["base"], A["hard_cost_band"]["base"]
TODAY = 2025
SATHER_GATE, NEAR_CAMPUS_MI = (37.8702, -122.2595), 0.6      # "near campus" = within 0.6 mi of Sather Gate
WENT_AHEAD, WAITING, ABANDONED = {"completed", "under_construction"}, {"entitled"}, {"withdrawn", "void"}


def hard_cost(year: int) -> float:
    """market-rate hard cost per gross sqft, non-Type-I, in a year (Terner 2018 base x the TBD SF bid index)."""
    c = HARD_2018
    if year >= 2018:
        for y in range(2019, year + 1):
            c *= ESCALATION[y]
    else:
        c /= ESCALATION[2018]
    return c


def _canon(a):
    try:
        h, s = normalize_address(a or "")
        return (h, s) if h and s else None
    except Exception:
        return None


def lease_ups(con):
    """Rent Board lease-up leases of completed 5+ unit buildings, classed, with the market pool."""
    apn_of = collections.defaultdict(set)
    for pid, apn in con.execute("SELECT parcel_id, apn_normalized FROM parcel_identifiers WHERE apn_normalized IS NOT NULL"):
        apn_of[pid].add(apn)
    proj = {}
    for key, units, co, pid, funding in con.execute("""
            SELECT project_key, units_built_or_permitted, COALESCE(first_co_date, co_issued_date), project_id, funding
            FROM v_projects WHERE units_built_or_permitted >= 5 AND COALESCE(rhna_excluded,0) = 0
              AND COALESCE(first_co_date, co_issued_date) IS NOT NULL"""):
        proj[key] = dict(co=co, pid=pid, units=units, funded=bool(funding and json.loads(funding)), apns=set(), addrs=set())
    pp = collections.defaultdict(set)
    for pid, parcel in con.execute("""SELECT project_id, parcel_id FROM project_parcels UNION
            SELECT ps.project_id, sp.parcel_id FROM project_structures ps JOIN structure_parcels sp USING(structure_id)"""):
        pp[pid].add(parcel)
    saddr = collections.defaultdict(set)
    for pid, num, street in con.execute("""SELECT ps.project_id, a.number, a.street FROM project_structures ps
            JOIN structure_addresses sa USING(structure_id) JOIN addresses a USING(address_id)"""):
        c = _canon(f"{num} {street}")
        if c:
            saddr[pid].add(c)
    for pid, notes in con.execute("SELECT ps.project_id, s.notes FROM project_structures ps JOIN structures s USING(structure_id)"):
        for al in (json.loads(notes or "{}").get("address_aliases") or []):
            c = _canon(al.get("address"))
            if c:
                saddr[pid].add(c)
    for p in proj.values():
        for parcel in pp[p["pid"]]:
            p["apns"] |= apn_of[parcel]
        p["addrs"] |= saddr[p["pid"]]
    unit, by_apn, by_addr = {}, collections.defaultdict(set), collections.defaultdict(set)
    for key, pl in con.execute("SELECT source_record_key, raw_payload FROM events WHERE event_type_code='registry_unit'"):
        _, apn, ua = key.split(":", 2)
        j = json.loads(pl)
        unit[(apn, ua)] = j
        by_apn[apn].add((apn, ua))
        c = _canon(j.get("Master Property Address"))
        if c:
            by_addr[c].add((apn, ua))
    ten = collections.defaultdict(dict)
    for key, pl in con.execute("SELECT source_record_key, raw_payload FROM events WHERE event_type_code='registry_tenancy'"):
        _, apn, ua = key.split(":", 2)
        j = json.loads(pl)
        ten[(apn, ua)].setdefault((j.get("Start Date Of Tenancy") or "")[:10], j)
    leases, classes, mix = [], {}, {}
    for k, p in proj.items():
        keys = set().union(*[by_apn[a] for a in p["apns"]], *[by_addr[c] for c in p["addrs"]]) if (p["apns"] or p["addrs"]) else set()
        if not keys:
            continue
        us = [unit[x] for x in keys if x in unit]
        beds = [int(u["Number of Bedrooms"]) for u in us if str(u.get("Number of Bedrooms") or "").isdigit()]
        subsidized = sum(1 for u in us if u.get("Gov Subsidized") == "Yes")
        group = any(u.get("Unit Status Code") in ("GREEK", "HOTEL", "COOP") or u.get("Occupant Type") in ("GREEK", "HOTEL", "COOP")
                    for u in us) or (beds and st.median(beds) >= 3)
        cls = "affordable" if (p["funded"] or (us and subsidized / len(us) > 0.5)) else "group" if group else "market"
        classes[k] = cls
        if beds and len(beds) >= 0.5 * p["units"]:  # the building's own bedroom mix -- only if most units are registered
            c_ = collections.Counter(str(min(b, 4)) for b in beds)
            mix[k] = {b: n / len(beds) for b, n in c_.items()}
        end = str(int(p["co"][:4]) + 2) + p["co"][4:]
        rows = []
        for x in keys:
            u = unit.get(x, {})
            for start, j in ten.get(x, {}).items():
                r = j.get("Initial Rent") or ""
                if start and p["co"] <= start <= end and r.replace(".", "", 1).isdigit() and float(r) > 300:
                    rows.append(dict(project=k, cls=cls, year=int(p["co"][:4]), rent=float(r),
                                     beds=u.get("Number of Bedrooms") or "?", subsidized=u.get("Gov Subsidized") == "Yes"))
        med = {}
        for b in {x["beds"] for x in rows}:
            v = [x["rent"] for x in rows if x["beds"] == b and not x["subsidized"]]
            if v:
                med[b] = st.median(v)
        for x in rows:
            x["below_market"] = (not x["subsidized"]) and x["beds"] in med and x["rent"] < 0.6 * med[x["beds"]]
        leases += rows
    market = [x for x in leases if x["cls"] == "market" and not x["subsidized"] and not x["below_market"]]
    pool = collections.defaultdict(list)
    for x in market:
        if 2022 <= x["year"] <= 2024 and x["beds"] in ("0", "1", "2", "3"):
            pool[x["beds"]].append(x["rent"])
    pool_rent = {b: st.median(v) for b, v in pool.items()}
    pool_mix = {b: len(v) / sum(len(w) for w in pool.values()) for b, v in pool.items()}
    own = collections.defaultdict(lambda: collections.defaultdict(list))
    for x in market:
        own[x["project"]][x["beds"]].append(x["rent"])
    return dict(leases=leases, market=market, classes=classes, mix=mix, pool_rent=pool_rent, pool_mix=pool_mix, own=own,
                pool_n={b: len(v) for b, v in pool.items()})


def leasing_rent_per_unit(reading, mix):
    """monthly rent per unit from a building's leasing site, over a bedroom mix: a per-bed rate x bedrooms (a studio
    = 1 bed), a per-unit rent as is; a size the site does not list takes the nearest listed size."""
    by_b = collections.defaultdict(list)
    for fp in reading["floor_plans"]:
        b = int(fp["bedrooms"])
        per_bed = fp["rent_basis"].startswith("per bed")        # "per bed", "per bedroom (double x2)"
        per_unit = fp["rent"] * max(b, 1) if per_bed else fp["rent"]
        by_b[b].append((per_unit, per_bed))
    sizes = sorted(by_b)
    total = 0.0
    for b_s, share in mix.items():
        b = int(b_s)
        near = min(sizes, key=lambda x: (abs(x - b), x))
        vals = [v / max(near, 1) * max(b, 1) if per_bed else v for v, per_bed in by_b[near]]
        total += share * st.median(vals)
    return total


def projects(con, asr, rents, commercial, leasing=None):
    """every 5+ unit, non-UC v4 project with its observed inputs and their basis."""
    out = []
    for r in con.execute("""SELECT project_key, name, status, COALESCE(NULLIF(units_built_or_permitted,0), proposed_units),
            height_stories, building_sqft, parcel_taxable_building_sqft, fees_paid, entitled_date, bp_issued_date,
            COALESCE(first_co_date, co_issued_date), funding, project_id, parking_spaces, latitude, longitude
            FROM v_projects WHERE COALESCE(NULLIF(units_built_or_permitted,0), proposed_units) >= 5
              AND COALESCE(rhna_excluded,0) = 0"""):
        out.append(dict(zip(["key", "name", "status", "units", "stories", "stated_sqft", "taxable_sqft", "fees", "entitled",
                             "bp", "co", "funding", "pid", "parking", "lat", "lon"], r)))
    apns = collections.defaultdict(set)
    for pid, apn in con.execute("""SELECT pp.project_id, pi.apn_normalized FROM project_parcels pp JOIN parcel_identifiers pi
            USING(parcel_id) WHERE pi.apn_normalized IS NOT NULL UNION SELECT ps.project_id, pi.apn_normalized
            FROM project_structures ps JOIN structure_parcels sp USING(structure_id)
            JOIN parcel_identifiers pi ON pi.parcel_id = sp.parcel_id WHERE pi.apn_normalized IS NOT NULL"""):
        apns[pid].add(apn)
    land_of = {}
    for apn, land in asr.execute("SELECT APN, Land FROM parcels"):
        try:
            land_of[to_canonical_apn(apn, "alameda")] = land or 0
        except Exception:
            pass
    for p in out:
        p["near_campus"] = (p["lat"] is not None and
                            ((p["lat"] - SATHER_GATE[0]) * 69.0) ** 2 + ((p["lon"] - SATHER_GATE[1]) * 54.6) ** 2 < NEAR_CAMPUS_MI ** 2)
        cand = [(p["taxable_sqft"], "assessor (built)")] if p["co"] else []
        cand.append((p["stated_sqft"], "stated in the application"))
        p["sqft"], p["sqft_basis"] = next(((v, b) for v, b in cand if v and 500 <= v / p["units"] <= 2000), (None, None))
    per_unit = st.median(p["sqft"] / p["units"] for p in out if p["co"] and p["sqft"])
    fee_unit = st.median(p["fees"] / p["units"] for p in out if p["fees"])
    for p in out:
        if not p["sqft"]:
            p["sqft"], p["sqft_basis"] = p["units"] * per_unit, f"built median {per_unit:.0f}/unit"
        if p["fees"]:
            p["fee_basis"] = "observed"
        else:
            p["fees"], p["fee_basis"] = p["units"] * fee_unit, "median fee/unit"
        p["land"] = sum(land_of.get(a, 0) for a in apns[p["pid"]])
        p["kind"] = ("affordable" if (p["funding"] and json.loads(p["funding"])) or rents["classes"].get(p["key"]) == "affordable"
                     else "group" if rents["classes"].get(p["key"]) == "group" else "market")
        own = rents["own"].get(p["key"], {})
        lr = (leasing or {}).get(p["key"])
        if lr and not own:                         # no registry lease-ups: the building's own current asking rents
            mix = rents["mix"].get(p["key"])
            if not mix:                            # else the floor plans the site lists, equally weighted, sizes as listed
                c_ = collections.Counter(str(int(fp["bedrooms"])) for fp in lr["floor_plans"])
                mix = {b: n / sum(c_.values()) for b, n in c_.items()}
            p["rent_basis"] = f"leasing site 2026 ({lr['leasing_model']})"
            p["gross_rent"] = p["units"] * 12 * leasing_rent_per_unit(lr, mix)
        else:
            p["rent_basis"] = "own lease-ups" if own else "market pool 2022-24"
            p["gross_rent"] = sum(p["units"] * share * 12 * (st.median(own[b]) if len(own.get(b, [])) >= 3 else rents["pool_rent"][b])
                                  for b, share in rents["pool_mix"].items())
        p["parking_noi"] = (p["parking"] or 0) * PARKING_RENT * 12 * PARKING_OCC * (1 - OPEX[0])
        c = commercial.get(p["key"])
        p["commercial_sqft"] = c["commercial_sqft"] if c else 0
        p["commercial_noi"] = p["commercial_sqft"] * RETAIL_RENT * (1 - RETAIL_VACANCY) * (1 - RETAIL_EXPENSES)
        e, b = p["entitled"], p["bp"]
        p["months_to_permit"] = ((int(b[:4]) - int(e[:4])) * 12 + int(b[5:7]) - int(e[5:7])) if (e and b and b >= e) else None
        p["carry"] = p["land"] * CARRY * (p["months_to_permit"] or 0) / 12
        p["tier"] = "tower" if (p["stories"] or 0) >= 9 else "podium" if (p["stories"] or 0) >= 6 else "wood" if p["stories"] else "podium?"
        ent_y = int(e[:4]) if e else None
        bp_y = int(b[:4]) if b else None
        p["decision_year"] = (ent_y if ent_y and (bp_y is None or ent_y <= bp_y) else (bp_y - 1) if bp_y else TODAY)
        p["decision_year"] = min(max(p["decision_year"], 2017), 2026)
        p["outcome"] = ("went ahead" if p["status"] in WENT_AHEAD else "waiting" if p["status"] in WAITING
                        else "abandoned" if p["status"] in ABANDONED else p["status"])
    return out, dict(gross_sqft_per_unit=per_unit, fee_per_unit=fee_unit)


def gap(p, year, factor, cost_mult=1.0, soft=SOFT[0], opex=OPEX[0]):
    """yield on cost minus the hurdle (exit cap in `year` + spread), for one project priced in `year`."""
    cost = (hard_cost(year) + (TYPE_I_PREMIUM if p["tier"] == "tower" else 0)) * factor * cost_mult
    noi = p["gross_rent"] * (1 - VACANCY) * (1 - opex) + p["parking_noi"] + p["commercial_noi"]
    tdc = p["sqft"] * cost * (1 + soft) + p["fees"] + p["land"] + p["carry"]
    return noi / tdc - (EXIT_CAP[year] + SPREAD)


def verdict(p, year, factor):
    best = gap(p, year, factor, 1 - COST_BAND, SOFT[1], OPEX[1])
    worst = gap(p, year, factor, 1 + COST_BAND, SOFT[2], OPEX[2])
    return "pencils" if worst >= 0 else "marginal" if best >= 0 else "does not pencil"


def fit_factor(fit):
    lo, hi = 0.3, 1.5
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if st.median(gap(p, p["decision_year"], mid) for p in fit) > 0 else (lo, mid)
    return (lo + hi) / 2


def run(v4=V4, assessor=ASSESSOR, commercial_evidence=COMMERCIAL_EVIDENCE, leasing_evidence=None):
    con = sqlite3.connect(f"file:{v4}?mode=ro", uri=True)
    asr = sqlite3.connect(f"file:{assessor}?mode=ro", uri=True)
    rents = lease_ups(con)
    commercial = {}
    if Path(commercial_evidence).exists():
        commercial = {r["project_key"]: r for r in json.load(open(commercial_evidence))["readings"] if r.get("commercial_sqft")}
    leasing = {}
    if leasing_evidence and Path(leasing_evidence).exists():
        leasing = {r["project_key"]: r for r in json.load(open(leasing_evidence))["readings"]}
    ps, derived = projects(con, asr, rents, commercial, leasing)
    mk = [p for p in ps if p["kind"] == "market"]
    ahead = [p for p in mk if p["outcome"] == "went ahead"]
    fit = [p for p in ahead if p["decision_year"] <= 2019]
    test = [p for p in ahead if p["decision_year"] >= 2020]
    k = fit_factor(fit)
    for p in mk:
        p["gap_decision"] = gap(p, p["decision_year"], k)
        p["verdict_decision"] = verdict(p, p["decision_year"], k)
        p["gap_today"] = gap(p, TODAY, k)
        p["verdict_today"] = verdict(p, TODAY, k)
    pool_market = []
    if leasing:                                    # the same projects at pool / registry rents, for the per-bed uplift
        pool_market = [p for p in projects(con, asr, rents, commercial)[0] if p["kind"] == "market"]
    return dict(projects=ps, market=mk, fit=fit, test=test, factor=k, rents=rents, commercial=commercial,
                derived=derived, v4_path=str(v4), pool_market=pool_market)


def figures(res):
    """the gated figures (structural + calibration), all derived."""
    mk, fit, test = res["market"], res["fit"], res["test"]
    waiting = [p for p in mk if p["outcome"] == "waiting"]
    abandoned = [p for p in mk if p["outcome"] == "abandoned"]
    vc = lambda s, f: sum(1 for p in s if p[f] != "does not pencil")
    return {
        "projects_5plus_nonuc": len(res["projects"]), "market_projects": len(mk),
        "lease_ups_market": len(res["rents"]["market"]),
        "pool_rent_studio": round(res["rents"]["pool_rent"]["0"]), "pool_rent_1br": round(res["rents"]["pool_rent"]["1"]),
        "pool_rent_2br": round(res["rents"]["pool_rent"]["2"]), "pool_rent_3br": round(res["rents"]["pool_rent"]["3"]),
        "commercial_area_projects": sum(1 for p in res["projects"] if p["commercial_sqft"]),
        "fit_n": len(fit), "test_n": len(test), "cost_factor": round(res["factor"], 3),
        "fitted_hard_cost_2018": round(HARD_2018 * res["factor"]),
        "fit_median_gap_bps": round(st.median(p["gap_decision"] for p in fit) * 1e4),
        "test_median_gap_bps": round(st.median(p["gap_decision"] for p in test) * 1e4),
        "test_pencil_or_marginal": vc(test, "verdict_decision"),
        "abandoned_n": len(abandoned), "abandoned_pencil_or_marginal": vc(abandoned, "verdict_decision"),
        "waiting_n": len(waiting),
        "waiting_met_then_short_today": sum(1 for p in waiting if p["gap_decision"] >= 0 and p["gap_today"] < 0),
        "waiting_never_met": sum(1 for p in waiting if p["gap_decision"] < 0 and p["gap_today"] < 0),
        "waiting_meets_today": sum(1 for p in waiting if p["gap_today"] >= 0),
        "waiting_median_gap_today_bps": round(st.median(p["gap_today"] for p in waiting) * 1e4),
    }


# ---------------------------------------------------------------- DECISION TIMING (John, 2026-10-12)
ERAS = (("2017-21", 2017, 2021), ("2022", 2022, 2022), ("2023+", 2023, 2026))


def timing_parts(p, factor):
    """the gap at approval -> today, split: costs moved (approval-year cap held), then rates moved. Rent held."""
    y = p["decision_year"]
    g0, g1 = gap(p, y, factor), gap(p, TODAY, factor)
    cost_only = g1 + (EXIT_CAP[TODAY] - EXIT_CAP[y])
    return dict(at_approval=g0, costs=cost_only - g0, rates=g1 - cost_only, today=g1)


def decision_timing(res, uplift_quantile=0.5):
    """by outcome x approval era: median gap at approval, the cost and rate moves since, today; the yield on cost the
    go-aheads accepted (and the exit cap it implies); near-campus waiters re-priced at the per-bed uplift over pool rent
    that the leasing-site buildings show (needs `res` run with leasing evidence)."""
    k, mk = res["factor"], res["market"]
    rows = []
    for o in ("went ahead", "waiting", "abandoned"):
        for e, lo, hi in ERAS:
            s = [p for p in mk if p["outcome"] == o and lo <= p["decision_year"] <= hi]
            if not s:
                continue
            P = [timing_parts(p, k) for p in s]
            rows.append({"outcome": o, "approved": e, "projects": len(s), "units": sum(p["units"] for p in s),
                         "near campus": sum(bool(p["near_campus"]) for p in s),
                         **{f"{c} (bps)": round(st.median(x[c] for x in P) * 1e4) for c in ("at_approval", "costs", "rates", "today")},
                         "at or above hurdle at approval": sum(x["at_approval"] >= 0 for x in P)})
    yoc = []
    for e, lo, hi in ERAS:
        A = [p for p in mk if p["outcome"] == "went ahead" and lo <= p["decision_year"] <= hi]
        if A:
            y_ = st.median(gap(p, p["decision_year"], k) + EXIT_CAP[p["decision_year"]] + SPREAD for p in A)
            yoc.append({"approved": e, "went ahead": len(A), "median yield on cost %": round(y_ * 100, 2),
                        "implied exit cap %": round((y_ - SPREAD) * 100, 2),
                        "model exit cap % (range)": f"{min(EXIT_CAP[y] for y in range(lo, hi + 1))*100:.2f}-"
                                                    f"{max(EXIT_CAP[y] for y in range(lo, hi + 1))*100:.2f}"})
    pool = {p["key"]: p for p in res.get("pool_market", [])}
    up = sorted(p["gross_rent"] / pool[p["key"]]["gross_rent"] for p in mk
                if p["rent_basis"].startswith("leasing") and p["near_campus"] and p["key"] in pool)
    nc = [p for p in mk if p["outcome"] == "waiting" and p["near_campus"]]
    uplift = up[int(uplift_quantile * (len(up) - 1))] if up else None
    rep = [dict(p, gross_rent=p["gross_rent"] * uplift) for p in nc] if uplift else []
    return dict(rows=rows, yield_on_cost=yoc, uplifts=up, uplift=uplift,
                near_campus_waiting=len(nc),
                near_campus_waiting_gap_pool_bps=round(st.median(gap(p, p["decision_year"], k) for p in nc) * 1e4),
                near_campus_waiting_gap_uplift_bps=round(st.median(gap(p, p["decision_year"], k) for p in rep) * 1e4) if rep else None,
                near_campus_waiting_meet_today_uplift=[(p["name"] or p["key"], p["units"]) for p in rep if gap(p, TODAY, k) >= 0])


# ---------------------------------------------------------------- THE PIPELINE'S SHAPE (John's questions, 2026-10-08)
def _months(a, b):
    return (int(b[:4]) - int(a[:4])) * 12 + int(b[5:7]) - int(a[5:7])


def pipeline_dates(con):
    """5+ unit, non-UC projects with filed / entitled / first-BP application / first BP issued / first CO / end dates.
    The application = the earliest permit_submitted on the project's master or phase permits; the END of a withdrawn
    or void project = the latest Withdrawn / Void task on its anchor Planning record (else its last Planning event)."""
    P = {}
    for k, pid, units, status, filed, ent, bp, co, anchor in con.execute("""
        SELECT project_key, project_id, COALESCE(NULLIF(units_built_or_permitted,0), proposed_units), status, filed_date,
               entitled_date, bp_issued_date, COALESCE(first_co_date, co_issued_date), anchor_record FROM v_projects
        WHERE COALESCE(NULLIF(units_built_or_permitted,0), proposed_units) >= 5 AND COALESCE(rhna_excluded,0) = 0"""):
        P[k] = dict(pid=pid, units=units, status=status, filed=filed, ent=ent, bp=bp, co=co, anchor=anchor)
    applied = dict(con.execute("""SELECT ps.project_id, MIN(e.event_date) FROM project_structures ps JOIN structure_events se
        USING(structure_id) JOIN events e USING(event_id) WHERE e.event_type_code='permit_submitted'
        AND se.role_in_structure IN ('master','phase') GROUP BY 1"""))
    ended = {}
    for rec, d in con.execute("""SELECT source_record_key, event_date FROM events WHERE event_type_code='planning_task'
            AND (raw_description LIKE '%Withdrawn%' OR raw_description LIKE '%Void%')"""):
        ended[rec] = max(ended.get(rec, ''), d or '')
    last = dict(con.execute("SELECT source_record_key, MAX(event_date) FROM events WHERE event_type_code LIKE 'planning_%' GROUP BY 1"))
    for p in P.values():
        p["applied"] = applied.get(p["pid"])
        p["end"] = (ended.get(p["anchor"]) or last.get(p["anchor"])) if p["status"] in ABANDONED else None
    return P


def apply_speed(P, first=2015, followup_to="2026-06-30"):
    """per entitlement-year cohort: how many applied for a building permit, how fast, and how many within 24 months."""
    out = []
    for y in sorted({int(p["ent"][:4]) for p in P.values() if p["ent"] and p["ent"][:4] >= str(first)}):
        ps = [p for p in P.values() if p["ent"] and int(p["ent"][:4]) == y]
        after = [_months(p["ent"], p["applied"]) for p in ps if p["applied"] and p["applied"] >= p["ent"]]
        w24 = sum(1 for p in ps if p["applied"] and _months(p["ent"], p["applied"]) <= 24)
        out.append(dict(entitled_year=y, projects=len(ps), units=sum(p["units"] for p in ps),
                        applied=sum(1 for p in ps if p["applied"]), median_months_to_apply=st.median(after) if after else None,
                        applied_within_24_months=w24, share_within_24=round(w24 / len(ps), 2),
                        full_24_month_followup=f"{y + 2}-12-31" <= followup_to))
    return out


def pipeline_shape(P, years=range(2016, TODAY + 1)):
    """at each year-end: projects and units holding in each stage, the completions and endings of that year, and how
    long the waiting (entitled, no permit) projects have waited."""
    rows = []
    for y in years:
        ye, ys = f"{y}-12-31", f"{y}-01-01"
        c = collections.defaultdict(lambda: [0, 0])
        waits = []
        for p in P.values():
            if p["end"] and p["end"] <= ye:
                if p["end"] >= ys:
                    c["ended that year"][0] += 1; c["ended that year"][1] += p["units"]
                continue
            if p["co"] and p["co"] <= ye:
                if p["co"] >= ys:
                    c["completed that year"][0] += 1; c["completed that year"][1] += p["units"]
                continue
            if p["bp"] and p["bp"] <= ye:
                s_ = "under construction"
            elif p["ent"] and p["ent"] <= ye:
                s_ = "entitled, no permit"; waits.append(_months(p["ent"], ye))
            elif p["filed"] and p["filed"] <= ye:
                s_ = "in review"
            else:
                continue
            c[s_][0] += 1; c[s_][1] += p["units"]
        row = dict(year=y)
        for s_ in ("in review", "entitled, no permit", "under construction", "completed that year", "ended that year"):
            row[s_ + " projects"], row[s_ + " units"] = c[s_]
        row["median months waiting"] = st.median(waits) if waits else None
        row["waiting over 3 years"] = sum(1 for w in waits if w > 36)
        rows.append(row)
    return rows
