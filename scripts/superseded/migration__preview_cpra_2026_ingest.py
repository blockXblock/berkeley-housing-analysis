#!/usr/bin/env python3
# ============================ SEQUESTERED 2026-09-28 ============================
# DO NOT RUN. Original path: scripts/migration/preview_cpra_2026_ingest.py
# WHY: Preview for ingest_cpra_2026 (diverged from the commit path). Retired with it.
raise SystemExit("SEQUESTERED 2026-09-28 -- see header; original path scripts/migration/preview_cpra_2026_ingest.py")
# ================================================================================
"""preview_cpra_2026_ingest.py — READ-ONLY preview of the two un-ingested CPRA files.

WHAT THIS IS. `docs/audit/2026-09-25_tour_grade_data_readiness.md` found two CPRA productions
sitting in the repo that had never been loaded into v2:

  A. data/raw/cpra-downloads/BP_Annual Permit Report-2025-2026-07-07.xlsx
     8,039 building-permit rows, post dates 2025-01-01 -> 2026-07-07. Carries the fields the
     housing-role classifier needs and the Accela list scrape lacks: Work Type, OccType, ADU,
     UnitsAdded, UnitsRemoved, Parcel Number.
  B. data/raw/cpra-downloads/2026 Master Permits Log.xlsx
     589 rows over 9 entitlement sheets (ZPs, pre-apps, ministerial, design review, landmarks,
     SB 684, condo). ** Its unit/BMR/density-bonus/streamlining columns and every date after
     'Date Received' are 100% EMPTY ** - the city produced the template but did not fill it. The
     2026-09-25 readiness note claimed these were the richest unit fields we hold; that was read
     off the HEADERS, not the data, and is corrected here. What the file actually delivers is
     application intake only: number, type, site address, applicant, res/comm, description, date
     received.

v2's permit feed stops at 2025-12-22, so every 2026 completion is missing — v2 holds 2 projects
with a 2026 CO while the city finaled 113 housing permits in 2026.

THIS SCRIPT WRITES NOTHING. It opens the database read-only (`file:...?mode=ro`) and reports what
an ingest WOULD do, so John can gate it. Per CLAUDE.md: snapshot -> read-only preview -> STOP for
John -> transactional write with verify-or-rollback.

Usage:  python scripts/migration/preview_cpra_2026_ingest.py [--md docs/audit/<file>.md]
"""
import argparse
import collections
import datetime
import sqlite3
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from housing_rules import to_canonical_apn                      # noqa: E402
from housing_rules.permit_role import classify                  # noqa: E402

BP_FILE = ROOT / "data/raw/cpra-downloads/BP_Annual Permit Report-2025-2026-07-07.xlsx"
ML_FILE = ROOT / "data/raw/cpra-downloads/2026 Master Permits Log.xlsx"
V2 = ROOT / "databases/berkeley_housing_v2.db"


def canon(a):
    try:
        return to_canonical_apn(a, "alameda")
    except Exception:
        return None


def num(x):
    try:
        return int(float(str(x).strip()))
    except Exception:
        return 0


def ro(db: Path) -> sqlite3.Connection:
    """Open read-only. A write attempt then raises rather than corrupting the serving DB."""
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


def read_bp():
    ws = openpyxl.load_workbook(BP_FILE, read_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    idx = {h: i for i, h in enumerate(rows[7]) if h}
    out = []
    for r in rows[8:]:
        if not r[0]:
            continue
        g = lambda k: r[idx[k]] if k in idx else None      # noqa: E731
        role, net, note = classify(
            work_type=g("Work Type") or "", description=g("WorkDescription") or "",
            adu_flag=g("ADU"), occtype=g("OccType") or "",
            units_added=g("UnitsAdded"), units_removed=g("UnitsRemoved"),
            permit_number=str(g("PermitNumber")))
        out.append({
            "permit": str(g("PermitNumber")).strip(), "apn": canon(g("Parcel Number")),
            "apn_raw": g("Parcel Number"),
            "submitted": g("Submittal Date"), "issued": g("Issuance Date"),
            "finaled": g("Finaled Date"),
            "street_number": g("StreetNumber"), "street": g("StreetName"),
            "street_type": g("StreetType"),
            "desc": g("WorkDescription") or "", "work_type": g("Work Type") or "",
            "occtype": g("OccType") or "", "units_added": num(g("UnitsAdded")),
            "units_removed": num(g("UnitsRemoved")), "co_required": g("CO Required"),
            "role": role, "net": net, "note": note,
        })
    return out


def read_master():
    wb = openpyxl.load_workbook(ML_FILE, read_only=True)
    sheets = {}
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        hi = next((i for i, r in enumerate(rows) if sum(1 for x in r if x) >= 5), 0)
        hdr = [str(h).replace("\n", " ").strip() if h else "" for h in rows[hi]]
        recs = []
        for r in rows[hi + 1:]:
            if not any(x for x in r):
                continue
            recs.append({hdr[i]: v for i, v in enumerate(r) if i < len(hdr) and hdr[i]})
        sheets[ws.title.strip()] = recs
    return sheets


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="")
    args = ap.parse_args()
    L = []
    def say(s=""):
        print(s)
        L.append(s)

    db = ro(V2)
    cur_permits = db.execute("SELECT COUNT(*) FROM permits").fetchone()[0]
    cur_projects = db.execute("SELECT COUNT(*) FROM projects WHERE merged_into_id IS NULL").fetchone()[0]
    have = {p for (p,) in db.execute("SELECT permit_number FROM permits WHERE permit_number IS NOT NULL")}
    apn2proj = {}
    for pid, apn in db.execute("""SELECT pp.project_id, pa.apn_normalized FROM project_parcels pp
                                  JOIN parcels pa ON pa.id = pp.parcel_id
                                  WHERE pa.apn_normalized IS NOT NULL"""):
        apn2proj.setdefault(apn, set()).add(pid)

    bp = read_bp()
    say("# CPRA 2026 ingest — READ-ONLY preview")
    say()
    say(f"Generated {datetime.date.today().isoformat()} · database opened read-only · **nothing written**")
    say()
    say("## Current v2 state")
    say()
    say(f"| | |\n|---|---|\n| permits | {cur_permits:,} |\n| live projects | {cur_projects:,} |")
    newest = db.execute("SELECT MAX(finaled_date) FROM permits").fetchone()[0]
    say(f"| newest finaled permit | {newest} |")
    for yr in ("2024", "2025", "2026"):
        n = db.execute("SELECT COUNT(*) FROM v_projects_flat WHERE co_issued_date LIKE ?", (yr + "%",)).fetchone()[0]
        say(f"| projects with a {yr} CO | {n} |")
    say()

    # ---- A. the building-permit feed ---------------------------------------------------
    say("## A. BP_Annual Permit Report 2025 → 2026-07-07")
    say()
    say(f"**{len(bp):,} rows.** Classifier roles **with the full inputs this file supplies**, "
        "against the same rows classified from description alone (all the Accela list scrape offers):")
    say()
    full = collections.Counter(r["role"] for r in bp)
    donly = collections.Counter(
        classify(work_type="", description=r["desc"], adu_flag=None, occtype="",
                 units_added=None, units_removed=None, permit_number=r["permit"])[0] for r in bp)
    say("| role | full inputs | description only |")
    say("|---|---|---|")
    for k in sorted(set(full) | set(donly)):
        say(f"| {k} | {full[k]:,} | {donly[k]:,} |")
    say()
    amb_f = full["ambiguous"] / len(bp) * 100
    amb_d = donly["ambiguous"] / len(bp) * 100
    say(f"**Ambiguity falls {amb_d:.1f}% → {amb_f:.1f}%** — the measured value of the "
        f"Work Type / OccType / UnitsAdded columns.")
    say()

    hu = [r for r in bp if r["role"] == "new_unit"]
    already = [r for r in hu if r["permit"] in have]
    fresh = [r for r in hu if r["permit"] not in have]
    match = [r for r in fresh if r["apn"] and r["apn"] in apn2proj]
    orphan = [r for r in fresh if not (r["apn"] and r["apn"] in apn2proj)]
    say("### Housing-creating permits (`new_unit`)")
    say()
    say(f"| | permits | units added |\n|---|---|---|")
    say(f"| total `new_unit` | {len(hu)} | +{sum(r['units_added'] for r in hu)} |")
    say(f"| already in v2 | {len(already)} | +{sum(r['units_added'] for r in already)} |")
    say(f"| **new, matches an existing project by APN** | **{len(match)}** | +{sum(r['units_added'] for r in match)} |")
    say(f"| **new, NO project in v2** | **{len(orphan)}** | +{sum(r['units_added'] for r in orphan)} |")
    say(f"| — on distinct APNs | {len({r['apn'] for r in orphan if r['apn']})} | |")
    say()
    say(f"APN present on every `new_unit` row: {sum(1 for r in hu if r['apn_raw'])}/{len(hu)} — "
        "so the crosswalk carries the join and no fuzzy address matching is needed.")
    say()
    for yr in (2025, 2026):
        f = [r for r in hu if isinstance(r["finaled"], datetime.datetime) and r["finaled"].year == yr]
        nv = [r for r in f if r["permit"] not in have]
        say(f"- **{yr} completions:** {len(f)} finaled housing permits, **+{sum(r['units_added'] for r in f)} units** "
            f"({len(nv)} not currently in v2)")
    say()
    big = sorted([r for r in hu if isinstance(r["finaled"], datetime.datetime) and r["finaled"].year == 2026],
                 key=lambda r: -r["units_added"])[:8]
    say("Largest 2026 completions v2 is missing:")
    say()
    say("| finaled | permit | units | address | description |")
    say("|---|---|---|---|---|")
    for r in big:
        addr = f"{r['street_number']} {r['street']} {r['street_type'] or ''}".strip()
        say(f"| {r['finaled'].date()} | {r['permit']} | +{r['units_added']} | {addr} | {str(r['desc'])[:58]} |")
    say()

    # ---- B. the entitlement feed --------------------------------------------------------
    sheets = read_master()
    say("## B. 2026 Master Permits Log — the entitlement side")
    say()
    say(f"**{sum(len(v) for v in sheets.values()):,} rows over {len(sheets)} sheets.** These are "
        "applications, not permits.")
    say()
    say("**⚠ This file is far thinner than its headers promise.** Fill rate per column, `ZPs` sheet:")
    say()
    say("| column | filled |")
    say("|---|---|")
    zp_rows = sheets.get("ZPs", [])
    keys = list(zp_rows[0].keys()) if zp_rows else []
    for k in keys:
        n = sum(1 for r in zp_rows if r.get(k) not in (None, "", "None"))
        say(f"| {k} | {n/len(zp_rows)*100:.0f}% |")
    say()
    say("Every column after `Date Received` — the entitlement dates (`Date Deemed Complete`, "
        "`Date of Final Action`, `Date of NOD`, `Date Permit Effective`), all unit counts, all BMR "
        "tiers, density bonus, waivers, concessions and the SB 9 / SB 6 / AB 2011 / SB 4 / SB 35 "
        "streamlining flag — is **100% empty**. The same holds for `Open 2025 ZPs`.")
    say()
    say("**Correction.** `docs/audit/2026-09-25_tour_grade_data_readiness.md` called this the "
        "richest unit/BMR/density-bonus source we hold. That was read off the HEADERS. The data is "
        "not there, and that note is corrected. It does **not** close the queued entitlement-event "
        "gap either, because the approval dates are exactly what is missing.")
    say()
    say("| sheet | rows | usable content |")
    say("|---|---|---|")
    for name, recs in sheets.items():
        if not recs:
            continue
        ks = list(recs[0].keys())
        good = [k for k in ks if sum(1 for r in recs if r.get(k) not in (None, "", "None")) / len(recs) >= 0.5]
        say(f"| {name} | {len(recs)} | {', '.join(good)[:90]} |")
    say()
    say("**What it is still worth.** 589 application records with number, type, address, applicant "
        "and date received — enough to create `application_submitted` events and populate "
        "`filed_date` for applications v2 does not know about, and enough to tell us *which* "
        "projects are in the planning queue right now. That is real but modest, and it is an "
        "intake feed, not an entitlement feed.")
    say()

    # ---- what this changes ---------------------------------------------------------------
    say("## What an ingest would change")
    say()
    say(f"- **`permits` {cur_permits:,} → ~{cur_permits + len(fresh):,}** if scoped to housing-creating permits "
        f"(+{len(fresh)}). Loading all {len(bp):,} rows instead would take it to ~{cur_permits + len(bp) - len(already):,}, "
        "mostly re-roofs and panel upgrades — not recommended for a project-oriented serving DB.")
    say(f"- **`projects` {cur_projects:,} → ~{cur_projects + len({r['apn'] for r in orphan if r['apn']}):,}** "
        f"(+{len({r['apn'] for r in orphan if r['apn']})}), a **{len({r['apn'] for r in orphan if r['apn']})/cur_projects*100:.0f}% increase**. "
        "These are the un-modelled ADU/infill tail CLAUDE.md names as v2's known coverage limit.")
    f26 = [r for r in hu if isinstance(r["finaled"], datetime.datetime) and r["finaled"].year == 2026]
    say(f"- **2026 COs: 2 → ~{len(f26)} projects**, unblocking the 2026 CO tour.")
    say("- **Published numbers move.** The CO-completion tiles are the site's trustworthy headline; "
        "adding real completions makes them more accurate but they will not match today's figures. "
        "That is a deliberate, gated change, not drift.")
    say()
    say("## Decisions John must make before any write")
    say()
    say("1. **Scope.** Housing-creating permits only (recommended), or the full 8,039 rows?")
    say(f"2. **Create {len({r['apn'] for r in orphan if r['apn']})} new projects** for the ADU/infill tail, "
        "or attach permits and leave them project-less (which would NOT unblock the CO tour, since "
        "`v_projects_flat` is project-oriented)?")
    say("3. **Entitlement ingest** — same pass, or a separate gated write after the BP load is verified?")
    say("4. **Re-baseline** the APR / Explorer exports and the deploy gate after the write, since "
        "headline counts move.")
    say()
    say("_No database writes were performed. The connection was opened `mode=ro`._")

    if args.md:
        p = Path(args.md)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(L) + "\n")
        print(f"\n-> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
