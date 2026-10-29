"""pencil_backtest.py -- the pencil-out model back-tested on buildings that DID get built (read-only).

John, 2026-10-29: "run the year-of-permit back-test", then "add those two" (the commitment-year market and value/cost);
graduated from scratch/2026-10-29/backtest_year_of_permit.py ("move the back-test script to scripts/v4 and commit").

Cohort = JN-O §10's built cohort: first BP on/after 2022-07-01, completed or under construction, 10+ units, not
RHNA-excluded, not publicly funded, with RECORD inputs (data/derived/pencil_out/project_inputs_record_built_*.csv) the
model can score. Each building at its RECORD size (pencil_out.stalled_project, land at market) under the market of:
  today  -- the model as published (today's cap rate, the price year's cost level, 2022-24 lease-up pool rents)
  bp     -- its first-BP year: the CBRE cap rate (exit_cap_rate.by_year) and hard costs at that year's price level
            (hard_cost_escalation.by_year)
  ent    -- the same at its entitlement year
  filed  -- the same at its planning-FILING year: a PROXY for when the developer committed to the site (v4 and the
            assessor hold no deed history; press dates 2538 Durant's purchase to 2022-12, its filing year). The run uses
            that year's construction costs = what the developer expected to pay, not what it paid.
  own    -- bp + the building's OWN Rent Board initial rents (first 2 years after CO), apartments only (by-the-bed
            buildings' registry rents are not comparable to per-bed asking rents)
vc_* = value / total cost = (NOI / that year's cap rate) / (cost ex land + land basis), no developer margin: >= 1 means
the finished building is worth at least what it cost. gap_* = yield on cost - hurdle (cap + spread). Construction rate,
land $/sf, opex and spread are held at base (the assumptions file has no year series for them).

Writes data/derived/pencil_out/backtest_built_<date>.csv (full precision; counts are taken unrounded) + .meta.json.
Run: python scripts/v4/pencil_backtest.py
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
import statistics as st
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "v4"))
import pencil_out as po  # noqa: E402

A = po.A
CAP_BY = {int(k): v for k, v in A["exit_cap_rate"]["by_year"].items()}
ESC = {int(k): v for k, v in A["hard_cost_escalation"]["by_year"].items()}
OUT_DIR = ROOT / "data/derived/pencil_out"


def cap(y: int) -> float:
    return CAP_BY[min(max(y, min(CAP_BY)), max(CAP_BY))]


def level(y: int) -> float:
    """construction price level in year y relative to 2024 (BFA24's dollars), from the escalation index."""
    y = min(max(y, min(ESC)), max(ESC))
    v = 1.0
    for k in range(y + 1, 2025):
        v /= ESC[k]
    for k in range(2025, y + 1):
        v *= ESC[k]
    return v


def year_scenario(y: int) -> dict:
    return po.scenario("base", cap=cap(y), hard_mult=level(y) / po.ESC_2024_TO_PRICE_YEAR)


def cohort(con4) -> pd.DataFrame:
    b = pd.read_sql_query("""SELECT anchor_record AS anchor, project_key, address_display AS address, status, filed_date,
           entitled_date, bp_issued_date, co_issued_date, funding FROM v_projects
     WHERE bp_issued_date >= '2022-07-01' AND status IN ('completed', 'under_construction')
       AND COALESCE(units_built_or_permitted, 0) >= 10 AND COALESCE(rhna_excluded, 0) = 0""", con4)
    b = b[~(b.funding.fillna('').str.len() > 2)].copy()
    b["fee"] = ["iho_combo" if (f or "") >= "2023-04-01" else "legacy_ahmf" for f in b.filed_date]
    return b


def value_cost(r, y: int) -> float:
    return (r["acct"]["noi"] / cap(y)) / (r["acct"]["cost_ex_land"] + r["land_basis"])


def run_backtest() -> pd.DataFrame:
    con4 = sqlite3.connect(f"file:{po.pp.V4}?mode=ro", uri=True)
    asr = sqlite3.connect(f"file:{po.pp.ASSESSOR}?mode=ro", uri=True)
    recs = po.record_inputs(po.RECORD_INPUTS_BUILT)
    R = po.rents()
    own = po.pp.lease_ups(con4)["own"]
    rows = []
    for _, p in cohort(con4).iterrows():
        if p.anchor not in recs:
            continue

        def run(s, Rx=R):
            return po.stalled_project(p.anchor, recs[p.anchor], Rx, con4, asr, s, use_record_land=False, fee_mode=p.fee)
        t = run(po.scenario("base"))
        if t["verdict"] == "insufficient_data":
            continue
        today = dt.date.today().year
        years = dict(bp=int(p.bp_issued_date[:4]), ent=int((p.entitled_date or p.bp_issued_date)[:4]),
                     filed=int((p.filed_date or p.entitled_date or p.bp_issued_date)[:4]))
        row = dict(anchor=p.anchor, address=p.address, status=p.status, layout="by the bed" if t["group"] else "apartments",
                   units=t["units"], stories=t["stories"], fee_mode=p.fee, **{f"{k}_year": v for k, v in years.items()},
                   gap_today=t["gap"], need_today=t["rent_mult_needed"], vc_today=value_cost(t, today))
        for k, y in years.items():
            r = run(year_scenario(y))
            row.update({f"gap_{k}": r["gap"], f"need_{k}": r["rent_mult_needed"], f"vc_{k}": value_cost(r, y)})
        row.update(gap_own=None, need_own=None, own_rents="")
        if not t["group"] and p.project_key in own:
            orent = {k: st.median(v) for k, v in own[p.project_key].items() if k in ("0", "1", "2", "3") and v}
            if orent:
                Ro = dict(R, pool_rent={k: orent.get(k, R["pool_rent"][k]) for k in R["pool_rent"]})
                o = run(year_scenario(years["bp"]), Ro)
                row.update(gap_own=o["gap"], need_own=o["rent_mult_needed"],
                           own_rents=f"{sum(len(own[p.project_key][k]) for k in orent)} leases; " + ", ".join(
                               f"{k}BR {orent[k] / R['pool_rent'][k]:.2f}x" for k in sorted(orent)))
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["layout", "bp_year", "address"]).reset_index(drop=True)


def summary(D: pd.DataFrame) -> dict:
    out = {}
    for name, d in (("all", D), ("apartments", D[D.layout == "apartments"]), ("by the bed", D[D.layout == "by the bed"])):
        s = dict(n=len(d))
        for k in ("today", "bp", "ent", "filed"):
            s[k] = dict(pencil=int((d[f"gap_{k}"] >= 0).sum()), worth_cost=int((d[f"vc_{k}"] >= 1).sum()),
                        median_vc=float(d[f"vc_{k}"].median()), median_need=float(d[f"need_{k}"].median()))
        if name == "apartments":
            own = d.need_own.dropna()
            s["own"] = dict(n=len(own), median_need=float(own.median()) if len(own) else None,
                            pencil=int((d.gap_own.dropna() >= 0).sum()))
        out[name] = s
    return out


def main():
    D = run_backtest()
    S = summary(D)
    stamp = dt.date.today().isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / f"backtest_built_{stamp}.csv"
    D.to_csv(csv_path, index=False)
    meta = dict(written=stamp, script="scripts/v4/pencil_backtest.py", assumptions=po.ASSUMPTIONS_FILE.name,
                assumptions_sha16=po._sha16(po.ASSUMPTIONS_FILE), record_inputs=po.RECORD_INPUTS_BUILT.name,
                record_inputs_sha16=po._sha16(po.RECORD_INPUTS_BUILT), v4_sha16=po._sha16(Path(po.pp.V4)), summary=S)
    csv_path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    pd.set_option("display.width", 250)
    show = D[["address", "layout", "filed_year", "ent_year", "bp_year", "need_today", "need_bp", "need_ent", "need_filed",
              "vc_today", "vc_bp", "vc_filed"]]
    print(show.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    for name, s in S.items():
        print(f"\n{name} (n={s['n']})")
        for k in ("today", "bp", "ent", "filed"):
            v = s[k]
            print(f"  {k:6} pencil {v['pencil']:>2}  worth >= cost {v['worth_cost']:>2}  median v/c {v['median_vc']:.2f}"
                  f"  median rent needed {v['median_need']:.2f}x")
        if "own" in s:
            print(f"  own rents (bp-year market): n={s['own']['n']} median need {s['own']['median_need']:.2f}x"
                  f" pencil {s['own']['pencil']}")
    print(f"\nwrote {csv_path.relative_to(ROOT)} (+ .meta.json)")


if __name__ == "__main__":
    main()
