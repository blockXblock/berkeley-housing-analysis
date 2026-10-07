"""Package marker (2026-09-07, env consolidation): lets `from scripts.build_v2...` resolve
under the editable install, replacing per-script sys.path insertion.

v3 (2026-10-07): this package builds databases/berkeley_housing_v3.db (S0-S9), now FROZEN as the research record of the
identity turn. It is v2-ASSISTED, not from-sources: stages S0-S8 read v2 (keys, units, events, the S8 cross-check),
now at databases/archive/berkeley_housing_v2.db. v4 is the from-sources build. The curriculum imports s0_keys and
housing_predicates as the student's own first key and rule -- the planted limitations JN7 resolves.
"""