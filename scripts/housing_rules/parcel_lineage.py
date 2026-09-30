"""parcel_lineage.py -- THE ONE resolver from (APN, address) to CURRENT parcels, through the County's lineage.

An APN on a permit names the parcel as it was when the permit was filed. Parcels are re-platted (CLAUDE.md rule 4), so
that APN may since have been renumbered, merged, or split. v4 holds the County assessor's own parent -> child record
(stage_methods.load_county_lineage) and each current parcel's situs address (load_parcels). This module follows them.

JOHN'S RULE, 2026-09-30 (the split rule):
  * one current descendant (renumber or merger)          -> that parcel                    'lineage_one'
  * a SPLIT: the children whose situs matches the address -> those children                'split_address_match'
  * a SPLIT whose children all share one situs (a condo
    map), none matching the permit address                -> all of them (a building may
                                                             span parcels)                 'split_shared_address'
  * a split nothing decides                               -> no parcel, reason recorded    'split_unresolved'
Other outcomes: 'current' (already a current APN), 'apn_unknown' (not in v4 at all), 'no_current_descendant'
(retired with no living child in the record, or an APN newer than the Feb-2026 roll). Nothing here guesses.
"""
from __future__ import annotations

import collections

from .apn import to_canonical_apn
from .address import normalize_address


class Resolver:
    def __init__(self, con):
        self.ident, self.current = {}, set()
        for apn, pid, cur in con.execute("SELECT apn_normalized, parcel_id, is_current FROM parcel_identifiers "
                                         "WHERE apn_normalized IS NOT NULL ORDER BY is_current"):
            self.ident[apn] = pid                   # a current identifier wins: it is read last
            if cur:
                self.current.add(pid)
        self.children = collections.defaultdict(set)
        for p, c in con.execute("SELECT parent_parcel_id, child_parcel_id FROM parcel_lineage WHERE status='confirmed'"):
            self.children[p].add(c)
        self.addr = collections.defaultdict(set)
        for pid, key in con.execute("SELECT pa.parcel_id, a.normalized FROM parcel_addresses pa "
                                    "JOIN addresses a USING(address_id)"):
            self.addr[pid].add(key)

    def _descend(self, pid, seen=None):
        if pid in self.current:
            return {pid}
        seen = seen if seen is not None else set()
        if pid in seen:
            return set()
        seen.add(pid)
        out = set()
        for c in self.children.get(pid, ()):
            out |= self._descend(c, seen)
        return out

    @staticmethod
    def _key(address):
        try:
            n, s = normalize_address(address) if address else (None, None)
        except Exception:
            return None
        return f"{n}|{s}" if n and s and n != "0" else None

    def resolve(self, apn_raw, address=None) -> tuple[tuple[int, ...], str]:
        """-> (current parcel ids, basis)."""
        try:
            c = to_canonical_apn(str(apn_raw).split(",")[0].strip(), "alameda") if apn_raw else None
        except Exception:
            c = None
        if not c:
            return (), "no_apn"
        pid = self.ident.get(c)
        if pid is None:
            return (), "apn_unknown"
        if pid in self.current:
            return (pid,), "current"
        ds = self._descend(pid)
        if not ds:
            return (), "no_current_descendant"
        if len(ds) == 1:
            return tuple(ds), "lineage_one"
        key = self._key(address)
        hit = sorted(d for d in ds if key and key in self.addr.get(d, ()))
        if hit:
            return tuple(hit), "split_address_match"
        situs = [frozenset(self.addr.get(d, ())) for d in ds]
        if all(situs) and len(set(situs)) == 1:
            return tuple(sorted(ds)), "split_shared_address"
        return (), "split_unresolved"
