#!/usr/bin/env python3
from __future__ import annotations
# ============================ SEQUESTERED 2026-09-29 ============================
# DO NOT RUN. Original path: scripts/migration/fix_my_normalized_address_error.py
# WHY: Applied one-time v2 write (John, 2026-09-28).
raise SystemExit('SEQUESTERED 2026-09-29 -- see header; original path scripts/migration/fix_my_normalized_address_error.py')
# ================================================================================
r"""fix_my_normalized_address_error.py -- repair normalized_address values I wrote WRONG on 2026-09-26.
PREVIEW BY DEFAULT; --commit needs John's go-ahead and an unlocked DB.

THE ERROR. fix_unnumbered_addresses.py set `normalized_address` to `normalize_address(addr)[1]` --
element [1] is the STREET ALONE. So proj73 got 'LE ROY' and proj769 got 'QUEENS': a normalized
address with NO HOUSE NUMBER, which matches every project on that street. That is precisely the
wildcard failure the same session spent hours removing ("0 <street>" keys), reintroduced by my own
write two hours later. It also made proj377's superseded and current rows IDENTICAL ('GRIZZLY PEAK'),
so the history could not be told apart by that column.

THE CONVENTION, measured rather than assumed: 718 of 1,106 projects use `NUMBER|STREET`
('1609 FIFTH St' -> '1609|FIFTH'; uppercase, street type dropped), 379 use a space form
`123 STREET TYPE`, and the 4 I wrote are a third shape. The pipe form is both the majority AND the
direct output of the canon (`housing_rules.address.normalize_address` returns the (number, street)
pair this joins), so it is what this writes.

⚠ NOT FIXED HERE, because it is not mine to decide: the column legitimately holds TWO conventions
(718 pipe, 379 space). Normalising those 379 is a separate question for John -- and a real one, since
a column with two shapes cannot be joined on reliably.

  .venv/bin/python scripts/migration/fix_my_normalized_address_error.py            # preview
  .venv/bin/python scripts/migration/fix_my_normalized_address_error.py --commit
"""

import argparse
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from housing_rules.address import normalize_address        # noqa: E402  THE rule-4c canon

V2 = ROOT / "databases/berkeley_housing_v2.db"
BAD_WRITER = "unnumbered_address_resolution@2026-09-26"
OBSERVED_BY = "normalized_address_repair@2026-09-26"


def canon_norm(addr: str) -> str:
    """the majority convention: NUMBER|STREET, uppercase, street type dropped."""
    num, street = normalize_address(addr)
    return f"{num}|{street.upper()}" if num and street else (street or "").upper()


def build_plan(db):
    pids = [r[0] for r in db.execute(
        "SELECT DISTINCT project_id FROM project_addresses WHERE asserted_by=?", (BAD_WRITER,))]
    proj, addrs = [], []
    for pid in sorted(pids):
        a, n = db.execute("SELECT canonical_address,normalized_address FROM projects WHERE id=?",
                          (pid,)).fetchone()
        want = canon_norm(a)
        if n != want:
            proj.append((pid, a, n, want))
    for rid, pid, a, n, cur in db.execute(
            "SELECT id,project_id,address,normalized_address,is_current FROM project_addresses "
            "WHERE project_id IN (%s)" % ",".join("?" * len(pids)), pids):
        want = canon_norm(a)
        if n != want:
            addrs.append((rid, pid, a, n, want, cur))
    return proj, addrs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    db = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)
    proj, addrs = build_plan(db)
    print(f"projects.normalized_address to repair: {len(proj)}")
    for pid, a, old, want in proj:
        print(f"   proj{pid:<5} {a!r}\n         {old!r}  ->  {want!r}")
    print(f"\nproject_addresses.normalized_address to repair: {len(addrs)}")
    for rid, pid, a, old, want, cur in addrs:
        print(f"   row{rid:<5} proj{pid:<5} is_current={cur} {a!r}\n         {old!r}  ->  {want!r}")
    db.close()
    if not args.commit:
        print("\nPREVIEW ONLY -- nothing written.")
        return 0
    if not proj and not addrs:
        print("\nnothing to repair.")
        return 0

    snap = ROOT / f"databases/keep_snapshot_{time.strftime('%Y-%m-%d')}_pre-norm_addr_repair.db"
    if not snap.exists():
        shutil.copy2(V2, snap)
    print(f"\nsnapshot {snap.name} ({snap.stat().st_size:,} bytes)")
    w = sqlite3.connect(V2)
    if w.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise SystemExit("integrity_check failed -- aborting")
    w.execute("PRAGMA foreign_keys=ON")
    n = 0
    try:
        w.execute("BEGIN")
        for pid, a, old, want in proj:
            cur = w.execute("UPDATE projects SET normalized_address=?, updated_at=? WHERE id=?",
                            (want, time.strftime("%Y-%m-%dT%H:%M:%S"), pid))
            if cur.rowcount != 1:
                raise RuntimeError(f"rowcount {cur.rowcount} on proj{pid}")
            n += 1
        for rid, pid, a, old, want, is_cur in addrs:
            cur = w.execute("UPDATE project_addresses SET normalized_address=? WHERE id=?",
                            (want, rid))
            if cur.rowcount != 1:
                raise RuntimeError(f"rowcount {cur.rowcount} on project_addresses row {rid}")
            n += 1
        # verify THIS run's targets, not a global total (the delta lesson, 2026-09-26)
        for pid, a, old, want in proj:
            got = w.execute("SELECT normalized_address FROM projects WHERE id=?", (pid,)).fetchone()[0]
            if got != want:
                raise RuntimeError(f"proj{pid} is {got!r}, wanted {want!r}")
        left = w.execute(
            "SELECT COUNT(*) FROM projects WHERE id IN (%s) AND normalized_address NOT LIKE '%%|%%'"
            % ",".join(str(p[0]) for p in proj)).fetchone()[0] if proj else 0
        if left:
            raise RuntimeError(f"{left} of the repaired projects still lack a house number")
        w.commit()
        print(f"committed {n} value repairs")
    except Exception as e:
        w.rollback()
        print(f"ROLLED BACK: {e}")
        return 1
    finally:
        w.close()
    f = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)
    print("fresh-connection fingerprint:")
    for pid, a, old, want in proj:
        print(f"   proj{pid:<5} {f.execute('SELECT normalized_address FROM projects WHERE id=?', (pid,)).fetchone()[0]!r}")
    print("   integrity", f.execute("PRAGMA integrity_check").fetchone()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
