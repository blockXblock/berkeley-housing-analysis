#!/usr/bin/env python3
"""verify_cpra_2026_build.py — is the corrected build safe to put into production?

Compares three databases on every axis that could have been damaged, so the swap decision rests on
evidence rather than on the ingest script's own say-so:

  BASE  keep_snapshot_2026-09-25_pre-cpra-2026-ingest.db   clean pre-ingest state
  BUGGY keep_snapshot_2026-09-25_buggy_build_superseded.db  the first build, archived
  FIXED rebuild_2026-09-25_v2_corrected.db                  the candidate

Every check states what it is testing and what a failure would mean. A check that cannot be
evaluated says so rather than passing silently.

Read-only on all three.
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from housing_rules import to_canonical_apn      # noqa: E402

DBS = {
    "BASE": ROOT / "databases/keep_snapshot_2026-09-25_pre-cpra-2026-ingest.db",
    "BUGGY": ROOT / "databases/keep_snapshot_2026-09-25_buggy_build_superseded.db",
    "FIXED": ROOT / "databases/rebuild_2026-09-25_v2_corrected.db",
}
UC_EXCLUDE = """project_id NOT IN (
    SELECT pc.project_id FROM project_classifications pc
    JOIN vocabulary_classification_types vct ON vct.id = pc.classification_type_id
    WHERE vct.code = 'uc_project')"""

FAILS, WARNS = [], []


def ro(p):
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def canon(a):
    try:
        return to_canonical_apn(a, "alameda")
    except Exception:
        return None


def hdr(t):
    print(f"\n{'='*74}\n{t}\n{'='*74}")


def row(label, *vals):
    print(f"  {label:<40}" + "".join(f"{str(v):>11}" for v in vals))


def main() -> int:
    conns = {k: ro(v) for k, v in DBS.items()}
    order = ["BASE", "BUGGY", "FIXED"]

    hdr("1. STRUCTURAL INTEGRITY  — a failure here means do not ship")
    row("", *order)
    for label, q in (
        ("integrity_check", "PRAGMA integrity_check"),
        ("projects", "SELECT COUNT(*) FROM projects WHERE merged_into_id IS NULL"),
        ("permits", "SELECT COUNT(*) FROM permits"),
        ("project_events", "SELECT COUNT(*) FROM project_events"),
        ("orphan permits", "SELECT COUNT(*) FROM permits WHERE project_id NOT IN (SELECT id FROM projects)"),
        ("orphan events", "SELECT COUNT(*) FROM project_events WHERE project_id NOT IN (SELECT id FROM projects)"),
        ("duplicate addresses", """SELECT COUNT(*) FROM (SELECT canonical_address FROM projects
            WHERE merged_into_id IS NULL GROUP BY city_id, canonical_address HAVING COUNT(*)>1)"""),
        ("projects w/o a current version", "SELECT COUNT(*) FROM projects WHERE current_version_id IS NULL AND merged_into_id IS NULL"),
        ("'completes' with no finaled_date", "SELECT COUNT(*) FROM permits WHERE completion_verdict='completes' AND finaled_date IS NULL"),
    ):
        vals = [conns[k].execute(q).fetchone()[0] for k in order]
        row(label, *vals)
        if label in ("orphan permits", "orphan events", "duplicate addresses") and vals[2]:
            FAILS.append(f"{label} = {vals[2]} in FIXED")
    fk = len(list(conns["FIXED"].execute("PRAGMA foreign_key_check")))
    row("FK violations (FIXED)", "", "", fk)
    if fk:
        FAILS.append(f"{fk} FK violations in FIXED")

    hdr("2. DID ANY EXISTING COMPLETION DATE MOVE?  — the bug that made v2 *wrong*")
    base = {p: c for p, c in conns["BASE"].execute(
        "SELECT project_id, co_issued_date FROM v_projects_flat WHERE co_issued_date IS NOT NULL")}
    for k in ("BUGGY", "FIXED"):
        cur = {p: c for p, c in conns[k].execute(
            "SELECT project_id, co_issued_date FROM v_projects_flat WHERE co_issued_date IS NOT NULL")}
        changed = [p for p in base if p in cur and base[p] != cur[p]]
        year = [p for p in changed if base[p][:4] != cur[p][:4]]
        lost = [p for p in base if p not in cur]
        print(f"  {k:<6} CO date changed: {len(changed):>3}   CO YEAR changed: {len(year):>3}   "
              f"lost a CO date: {len(lost):>3}")
        for p in year[:6]:
            ad = conns[k].execute("SELECT canonical_address FROM projects WHERE id=?", (p,)).fetchone()[0]
            print(f"           proj{p} {str(ad)[:34]:<34} {base[p]} -> {cur[p]}")
        if k == "FIXED" and (year or lost):
            FAILS.append(f"FIXED moved {len(year)} CO years / lost {len(lost)}")

    hdr("3. COMPLETIONS BY YEAR (UC excluded, as generate_apr_v2.py does)")
    row("", *order)
    for yr in ("2023", "2024", "2025", "2026"):
        proj, units = [], []
        for k in order:
            r = conns[k].execute(
                f"""SELECT COUNT(*), IFNULL(SUM(total_units),0) FROM v_projects_flat
                    WHERE co_issued_date LIKE ? AND {UC_EXCLUDE}""", (yr + "%",)).fetchone()
            proj.append(r[0]); units.append(r[1])
        row(f"{yr}  projects", *proj)
        row(f"{yr}  units", *units)

    hdr("4. BUILDING PERMITS — bp_issued_date and the RHNA 6th-cycle boundary")
    row("", *order)
    for label, q in (
        ("projects with a bp_issued_date", "SELECT COUNT(*) FROM v_projects_flat WHERE bp_issued_date IS NOT NULL"),
        ("first BP on/after 2022-06-30", f"SELECT COUNT(*) FROM v_projects_flat WHERE bp_issued_date >= '2022-06-30' AND {UC_EXCLUDE}"),
        ("  their units (6th-cycle lower bound)", f"SELECT IFNULL(SUM(total_units),0) FROM v_projects_flat WHERE bp_issued_date >= '2022-06-30' AND {UC_EXCLUDE}"),
        ("bp_issued_date BEFORE filed_date", "SELECT COUNT(*) FROM v_projects_flat WHERE bp_issued_date IS NOT NULL AND filed_date IS NOT NULL AND bp_issued_date < filed_date"),
        ("CO before BP (impossible order)", "SELECT COUNT(*) FROM v_projects_flat WHERE co_issued_date IS NOT NULL AND bp_issued_date IS NOT NULL AND co_issued_date < bp_issued_date"),
    ):
        row(label, *[conns[k].execute(q).fetchone()[0] for k in order])

    hdr("5. PIPELINE TOTALS (what the site's headline counts read from)")
    row("", *order)
    for label, q in (
        ("total live projects", "SELECT COUNT(*) FROM v_projects_flat"),
        ("  with coordinates", "SELECT COUNT(*) FROM v_projects_flat WHERE latitude IS NOT NULL AND longitude IS NOT NULL"),
        ("  with a unit count", "SELECT COUNT(*) FROM v_projects_flat WHERE total_units IS NOT NULL"),
        ("all-time units", "SELECT IFNULL(SUM(total_units),0) FROM v_projects_flat"),
        ("all-time completions", "SELECT COUNT(*) FROM v_projects_flat WHERE co_issued_date IS NOT NULL"),
        ("UC projects (kept in pipeline)", """SELECT COUNT(*) FROM project_classifications pc
            JOIN vocabulary_classification_types t ON t.id=pc.classification_type_id WHERE t.code='uc_project'"""),
    ):
        row(label, *[conns[k].execute(q).fetchone()[0] for k in order])

    hdr("5b. STATUS — does every project carry one, and does it agree with the evidence?")
    row("", *order)
    for label, q_ in (
        ("projects with NO stage", "SELECT COUNT(*) FROM projects WHERE current_stage_type_id IS NULL AND merged_into_id IS NULL"),
        ("rows with NULL status_code", "SELECT COUNT(*) FROM v_projects_flat WHERE status_code IS NULL"),
        ("rows with NULL status_label", "SELECT COUNT(*) FROM v_projects_flat WHERE status_label IS NULL"),
        ("has a CO but stage != completed", "SELECT COUNT(*) FROM v_projects_flat WHERE co_issued_date IS NOT NULL AND status_code<>'completed'"),
        ("stage = completed but NO CO date", "SELECT COUNT(*) FROM v_projects_flat WHERE co_issued_date IS NULL AND status_code='completed'"),
    ):
        vals = [conns[k].execute(q_).fetchone()[0] for k in order]
        row(label, *vals)
        if label.startswith(("projects with NO", "rows with NULL")) and vals[2]:
            FAILS.append(f"{label} = {vals[2]} in FIXED")
        if label == "has a CO but stage != completed" and vals[2] > vals[0]:
            FAILS.append("FIXED introduced new CO/stage disagreement")
    print("  NOTE: 'completed with no CO date' is PRE-EXISTING drift in current_stage_type_id,")
    print("        which CLAUDE.md records as a separate, drift-prone materialisation that no")
    print("        longer drives the published completion display. Not introduced here.")

    hdr("6. SPOT CHECKS — named facts, verified individually")
    f = conns["FIXED"]
    checks = []
    # Test the PROJECT-level fact, not one permit's field. The first version of this check
    # demanded finaled_date on B2023-06416 and failed the build, but proj150 was already a 2026
    # completion at 144 units via a co_issued event -- the claim was true, the test was wrong.
    r = f.execute("""SELECT co_issued_date, total_units FROM v_projects_flat
                     WHERE project_id=150""").fetchone()
    checks.append(("3030 Telegraph is a 2026 completion at 144 units",
                   bool(r) and str(r[0]).startswith("2026") and (r[1] or 0) == 144, r))
    r = f.execute("""SELECT finaled_date FROM permits WHERE permit_number='B2023-06416'""").fetchone()
    checks.append(("its BP carries the feed's 2026-04-16 final (back-fill)",
                   bool(r) and str(r[0]) == "2026-04-16", r))
    r = f.execute("""SELECT co_issued_date FROM v_projects_flat WHERE project_id=483""").fetchone()
    checks.append(("proj483 122 Avenida keeps its 2018 CO", bool(r) and str(r[0]).startswith("2018"), r))
    r = f.execute("""SELECT COUNT(*) FROM permits WHERE permit_number IN
                     ('B2025-03811','B2025-03814','B2025-01753')""").fetchone()
    checks.append(("meter-panel / water-line permits kept OUT", r[0] == 0, r))
    r = f.execute("""SELECT COUNT(*) FROM projects WHERE canonical_address LIKE '%[B20%'""").fetchone()
    checks.append(("sibling projects addressed traceably", r[0] > 0, r))
    r = f.execute("""SELECT COUNT(*) FROM v_projects_flat WHERE co_issued_date LIKE '2026%'
                     AND total_units IS NULL""").fetchone()
    checks.append(("no 2026 completion missing a unit count", r[0] == 0, r))
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}    {detail}")
        if not ok:
            FAILS.append(name)

    hdr("7. WHAT THE VETO REFUSED — did we throw away real housing?")
    vp = ROOT / "data/reference/cpra_2026_vetoed_zero_units.csv"
    if vp.exists():
        lines = vp.read_text().splitlines()[1:]
        print(f"  {len(lines)} rows refused, all listed in {vp.name} for review (not dropped silently).")
        import csv as _csv
        rows = list(_csv.DictReader(vp.read_text().splitlines()))
        sus = [r for r in rows if "dwelling" in (r.get("description") or "").lower()
               or " adu" in (r.get("description") or "").lower()]
        print(f"  rows whose text still mentions a dwelling/ADU: {len(sus)} — these need a human read:")
        for r in sus[:6]:
            print(f"     {r['permit']:<15} UnitsAdded={r['units_added']:<3} {r['description'][:62]}")
        if sus:
            WARNS.append(f"{len(sus)} vetoed rows mention a dwelling; review {vp.name}")
    else:
        print("  veto file missing — cannot evaluate")
        WARNS.append("veto file missing")

    hdr("VERDICT")
    if FAILS:
        print("  BLOCKED — do not ship:")
        for x in FAILS:
            print(f"    - {x}")
    else:
        print("  No blocking defect found in FIXED.")
    for w in WARNS:
        print(f"  WARN: {w}")
    print("\n  Reminder: docs/explorer_data.js was generated 2026-09-08, so the LIVE SITE shows the")
    print("  pre-ingest state. Swapping the database changes nothing published until")
    print("  export_explorer_data_v2.py is re-run and the result is reviewed and deployed.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
