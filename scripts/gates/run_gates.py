#!/usr/bin/env python3
"""Run every gate and print ONE screen a person can read.

    .venv/bin/python -m scripts.gates.run_gates

Exit 0 only if every gate passes. The detail lines are there if wanted; the top table is the answer.
"""
from __future__ import annotations

import importlib

# TWO KINDS OF CHECK, deliberately not mixed.
#
# DEFECT gates assert something that should NEVER be true. Red means something is broken and fixable;
# green is the normal state. These are the ones to chase.
#
# STATUS gauges report where a long piece of work has got to. Red means "not finished yet" -- it is
# information, not a task, and it may stay red for months. Treating a gauge as a defect gate creates
# pressure to weaken the check so the board looks clean, which is precisely the failure this whole
# directory exists to prevent. A gauge's red NEVER fails the run.
DEFECT_GATES = [
    ("canon uniqueness", "scripts.gates.gate_canon_uniqueness",
     "one implementation per canonical rule"),
    ("join keys", "scripts.gates.gate_join_keys",
     "a key must identify ONE thing"),
    ("event referent", "scripts.gates.gate_referent",
     "a dated event must name its source action"),
]
STATUS_GAUGES = [
    ("store convergence", "scripts.gates.gate_store_focus",
     "one store, or a maintained fork? (red = migration unfinished)"),
]

def main() -> int:
    def run_all(specs):
        out = []
        for name, mod, why in specs:
            try:
                ok, msgs = importlib.import_module(mod).run()
            except Exception as e:
                ok, msgs = False, [f"FAIL gate raised: {type(e).__name__}: {e}"]
            out.append((name, ok, why, msgs))
        return out

    defects, gauges = run_all(DEFECT_GATES), run_all(STATUS_GAUGES)
    width = max(len(n) for n, *_ in defects + gauges)
    bar = "=" * (width + 52)

    print(bar)
    print(" DEFECT GATES -- red means broken and fixable")
    for name, ok, why, _ in defects:
        print(f"   {'PASS' if ok else 'FAIL':4}  {name:<{width}}   {why}")
    print(f"\n STATUS GAUGES -- red means unfinished, NOT a defect; never weaken these to go green")
    for name, ok, why, _ in gauges:
        print(f"   {'DONE' if ok else 'OPEN':4}  {name:<{width}}   {why}")
    print(bar)
    bad = [n for n, ok, *_ in defects if not ok]
    print(f" defect gates: {len(defects)-len(bad)}/{len(defects)} pass"
          + (f"   FIX: {', '.join(bad)}" if bad else "   (all clear)"))
    for name, ok, *_ in gauges:
        if not ok:
            print(f" status: {name} is OPEN -- see its detail for where the work stands")

    for label, group in (("DEFECT", defects), ("STATUS", gauges)):
        for name, ok, why, msgs in group:
            print(f"\n--- {label}: {name}")
            for m in msgs:
                print(f"  {m}")
    # only DEFECT gates decide the exit code
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
