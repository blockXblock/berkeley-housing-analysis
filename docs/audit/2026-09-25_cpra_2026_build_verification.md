---
title: CPRA 2026 build verification — three-way comparison
date: 2026-09-25
type: audit
status: open
area: docs/audit
---

# CPRA 2026 build verification

Output of `scripts/verify_cpra_2026_build.py`, comparing the clean pre-ingest snapshot (BASE),
the first buggy build (BUGGY) and the candidate (FIXED). Read-only on all three.

```

==========================================================================
1. STRUCTURAL INTEGRITY  — a failure here means do not ship
==========================================================================
                                                 BASE      BUGGY      FIXED
  integrity_check                                  ok         ok         ok
  projects                                        909       1180       1096
  permits                                         995       1323       1211
  project_events                                 3916       4439       4256
  orphan permits                                    0          0          0
  orphan events                                     0          0          0
  duplicate addresses                               0          0          0
  projects w/o a current version                    2          2          2
  'completes' with no finaled_date                 25         25         22
  FK violations (FIXED)                                                   0

==========================================================================
2. DID ANY EXISTING COMPLETION DATE MOVE?  — the bug that made v2 *wrong*
==========================================================================
  BUGGY  CO date changed:  14   CO YEAR changed:   5   lost a CO date:   0
           proj329 1208 DELAWARE St                   2025-02-24 -> 2026-04-07
           proj365 2227 CARLETON St                   2025-09-10 -> 2026-04-17
           proj402 131 Avenida Dr                     2023-08-15 -> 2026-05-27
           proj483 122 Avenida Dr                     2018-05-29 -> 2026-04-21
           proj598 1527 Woolsey                       2019-11-07 -> 2025-12-30
  FIXED  CO date changed:   4   CO YEAR changed:   0   lost a CO date:   0

==========================================================================
3. COMPLETIONS BY YEAR (UC excluded, as generate_apr_v2.py does)
==========================================================================
                                                 BASE      BUGGY      FIXED
  2023  projects                                  100         99        100
  2023  units                                     625        623        625
  2024  projects                                   86         86         86
  2024  units                                     694        694        694
  2025  projects                                   98        115        117
  2025  units                                     530        586        588
  2026  projects                                    2        103         47
  2026  units                                     216        285        271

==========================================================================
4. BUILDING PERMITS — bp_issued_date and the RHNA 6th-cycle boundary
==========================================================================
                                                 BASE      BUGGY      FIXED
  projects with a bp_issued_date                   36        327        229
  first BP on/after 2022-06-30                     29        311        213
    their units (6th-cycle lower bound)          1361       1685       1660
  bp_issued_date BEFORE filed_date                  7         10          9
  CO before BP (impossible order)                   0          3          0

==========================================================================
5. PIPELINE TOTALS (what the site's headline counts read from)
==========================================================================
                                                 BASE      BUGGY      FIXED
  total live projects                             909       1180       1096
    with coordinates                              888       1149       1067
    with a unit count                             907       1178       1094
  all-time units                                19669      19957      19951
  all-time completions                            704        819        768
  UC projects (kept in pipeline)                    4          4          4

==========================================================================
6. SPOT CHECKS — named facts, verified individually
==========================================================================
  [PASS] 3030 Telegraph is a 2026 completion at 144 units    ('2026-04-16', 144)
  [PASS] its BP carries the feed's 2026-04-16 final (back-fill)    ('2026-04-16',)
  [PASS] proj483 122 Avenida keeps its 2018 CO    ('2018-05-29',)
  [PASS] meter-panel / water-line permits kept OUT    (0,)
  [PASS] sibling projects addressed traceably    (6,)
  [PASS] no 2026 completion missing a unit count    (0,)

==========================================================================
7. WHAT THE VETO REFUSED — did we throw away real housing?
==========================================================================
  125 rows refused, all listed in cpra_2026_vetoed_zero_units.csv for review (not dropped silently).
  rows whose text still mentions a dwelling/ADU: 23 — these need a human read:
     B2022-05428     UnitsAdded=0   New pool + two story pool house, greenhouse, and landscape imp
     B2022-06065     UnitsAdded=0   Additions and alteration to the existing house including a jun
     B2024-01867     UnitsAdded=    Revised: Upgrade main service panel from 100 amps to 200 amp 2
     B2024-02503     UnitsAdded=0   Remodel and addition to exist. single family dwelling. House t
     B2024-05247     UnitsAdded=    Roof mount PV 2.8 KWDC 7 panels on ADU unit A
     B2024-05764     UnitsAdded=    Install 2.0 (DC) / 1.8 (AC) KW PV solar panels (5 modules) on 

==========================================================================
VERDICT
==========================================================================
  No blocking defect found in FIXED.
  WARN: 23 vetoed rows mention a dwelling; review cpra_2026_vetoed_zero_units.csv

  Reminder: docs/explorer_data.js was generated 2026-09-08, so the LIVE SITE shows the
  pre-ingest state. Swapping the database changes nothing published until
  export_explorer_data_v2.py is re-run and the result is reviewed and deployed.
```
