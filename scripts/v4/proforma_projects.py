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
LABELED ASSUMPTIONS (central, band)
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

# ---- CITED
ESCALATION = {2018: 1.0054, 2019: 1.104, 2020: 1.026, 2021: 1.036, 2022: 1.172, 2023: 1.049, 2024: 1.026, 2025: 1.035,
              2026: 1.035}
HARD_2018, TYPE_I_PREMIUM = 332.0, 68.0
EXIT_CAP = {2017: 0.045, 2018: 0.045, 2019: 0.045, 2020: 0.04375, 2021: 0.0425, 2022: 0.0475, 2023: 0.06,
            2024: 0.06, 2025: 0.06, 2026: 0.06}
EXIT_CAP_BASIS = {2017: "CBRE H2 2017", 2018: "interpolated", 2019: "CBRE H2 2019", 2020: "interpolated",
                  2021: "SF H2 2021 + 50 bps", 2022: "SF H1+H2 2022 + 50 bps", 2023: "CBRE H2 2023",
                  2024: "CBRE H1 2024", 2025: "H1 2024 carried", 2026: "H1 2024 carried"}
RETAIL_RENT, PARKING_RENT = 36.0, 200.0
# ---- LABELED ASSUMPTIONS (central, low, high)
SOFT, OPEX = (0.25, 0.20, 0.30), (0.35, 0.30, 0.40)
VACANCY, RETAIL_VACANCY, RETAIL_EXPENSES, PARKING_OCC = 0.05, 0.20, 0.10, 0.70
SPREAD, CARRY, COST_BAND = 0.0125, 0.07, 0.10
TODAY = 2025
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
        proj[key] = dict(co=co, pid=pid, funded=bool(funding and json.loads(funding)), apns=set(), addrs=set())
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
    leases, classes = [], {}
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
    return dict(leases=leases, market=market, classes=classes, pool_rent=pool_rent, pool_mix=pool_mix, own=own,
                pool_n={b: len(v) for b, v in pool.items()})


def projects(con, asr, rents, commercial):
    """every 5+ unit, non-UC v4 project with its observed inputs and their basis."""
    out = []
    for r in con.execute("""SELECT project_key, name, status, COALESCE(NULLIF(units_built_or_permitted,0), proposed_units),
            height_stories, building_sqft, parcel_taxable_building_sqft, fees_paid, entitled_date, bp_issued_date,
            COALESCE(first_co_date, co_issued_date), funding, project_id, parking_spaces
            FROM v_projects WHERE COALESCE(NULLIF(units_built_or_permitted,0), proposed_units) >= 5
              AND COALESCE(rhna_excluded,0) = 0"""):
        out.append(dict(zip(["key", "name", "status", "units", "stories", "stated_sqft", "taxable_sqft", "fees", "entitled",
                             "bp", "co", "funding", "pid", "parking"], r)))
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


def run(v4=V4, assessor=ASSESSOR, commercial_evidence=COMMERCIAL_EVIDENCE):
    con = sqlite3.connect(f"file:{v4}?mode=ro", uri=True)
    asr = sqlite3.connect(f"file:{assessor}?mode=ro", uri=True)
    rents = lease_ups(con)
    commercial = {}
    if Path(commercial_evidence).exists():
        commercial = {r["project_key"]: r for r in json.load(open(commercial_evidence))["readings"] if r.get("commercial_sqft")}
    ps, derived = projects(con, asr, rents, commercial)
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
    return dict(projects=ps, market=mk, fit=fit, test=test, factor=k, rents=rents, commercial=commercial,
                derived=derived, v4_path=str(v4))


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
