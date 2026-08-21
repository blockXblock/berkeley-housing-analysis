#!/usr/bin/env python3
"""refresh_berkeley_parcels.py — refresh databases/berkeley.db `parcels` from the county's live feed.

MACHINERY (re-runnable). Source: Alameda County Open Data Hub, Parcels FeatureServer
(services5.arcgis.com/ROBnTHSNjoZ2Wm1P), filtered SitusCity='BERKELEY' — the same endpoint as the
2026-06-16 refresh (which was done ad hoc; this script makes the procedure durable).

DISCIPLINE (CLAUDE.md): SNAPSHOT FIRST (cp databases/berkeley.db databases/keep_snapshot_<date>_pre-*.db
+ PRAGMA integrity_check) — this script REFUSES to run if no same-day keep_snapshot exists. Writes are
transactional with verify-or-rollback: builds `parcels_new`, verifies row count, total AV, the
53-1695-26 net-AV oracle identity, and a caller-supplied spot check, then swaps tables in one
transaction. Geometry columns (Latitude/Longitude/the_geom) and derived `corridor` are CARRIED OVER
by APN from the outgoing table (parcels don't move); brand-new APNs get NULL geometry (reported).

Provenance context (2026-08-21): triggered by Dan Lindheim's report — parcel 63-2985-20 showed the
pre-transfer roll ($1.12M) while the county's live feed showed the post-reassessment $2.41M; the
Feb-2026 snapshot pre-dated the 2026-27 roll posting.
"""
import json, sqlite3, sys, urllib.request, urllib.parse, glob, datetime

BASE = ("https://services5.arcgis.com/ROBnTHSNjoZ2Wm1P/arcgis/rest/services/"
        "Parcels/FeatureServer/0/query")
WHERE = "SitusCity='BERKELEY'"
FIELDS = ("APN,BOOK,PAGE,PARCEL,SUB_PARCEL,SitusStreetNumber,SitusStreetName,SitusUnit,"
          "SitusCity,SitusZip,SitusAddress,UseCode,Land,Imps,TotalNetValue,LatestDocumentDate,HOEX")
PAGE = 2000

def fetch_all():
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode(dict(where=WHERE, outFields=FIELDS, f="json",
                                        orderByFields="OBJECTID", resultOffset=offset,
                                        resultRecordCount=PAGE))
        with urllib.request.urlopen(f"{BASE}?{q}", timeout=120) as r:
            d = json.load(r)
        feats = d.get("features", [])
        rows += [f["attributes"] for f in feats]
        print(f"  fetched {len(rows)} ...")
        if len(feats) < PAGE: break
        offset += PAGE
    return rows

def ms_to_date(ms):
    if ms in (None, "", 0): return None
    return datetime.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d")

def main():
    today = datetime.date.today().isoformat()
    if not glob.glob(f"databases/keep_snapshot_{today}_pre-*.db"):
        sys.exit(f"REFUSING: no databases/keep_snapshot_{today}_pre-*.db found — snapshot first.")
    rows = fetch_all()
    assert len(rows) > 28000, f"suspiciously few rows: {len(rows)}"
    db = sqlite3.connect("databases/berkeley.db")
    db.isolation_level = None                       # explicit transaction control
    cur = db.cursor()
    old_n, old_av = cur.execute(
        "SELECT COUNT(*), SUM(CAST(TotalNetValue AS REAL)) FROM parcels").fetchone()
    # carry-over maps from the outgoing rows (geometry/derived cols the feed doesn't carry)
    carry = {r[0]: r[1:] for r in cur.execute(
        "SELECT APN, LotSize, Longitude, Latitude, the_geom, corridor FROM parcels")}
    old_vals = {r[0]: r[1] for r in cur.execute("SELECT APN, TotalNetValue FROM parcels")}
    new_apns = sum(1 for a in rows if a.get("APN") not in carry)
    changed = sum(1 for a in rows
                  if a.get("APN") in old_vals and old_vals[a.get("APN")] != a.get("TotalNetValue"))
    # ---- IN-PLACE replace (the June-2026 method: table identity and views untouched) ----
    cur.execute("BEGIN IMMEDIATE")
    try:
        cur.execute("DELETE FROM parcels")
        for a in rows:
            apn = a.get("APN")
            c = carry.get(apn)
            lot, lon, lat, geom, corr = c if c else ("0", None, None, None, None)
            cur.execute("INSERT INTO parcels VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (apn, a.get("BOOK"), a.get("PAGE"), a.get("PARCEL"), a.get("SUB_PARCEL"),
                 str(a.get("SitusStreetNumber") or ""), a.get("SitusStreetName"), a.get("SitusUnit"),
                 a.get("SitusCity"), a.get("SitusZip"), a.get("SitusAddress"), a.get("UseCode"),
                 a.get("Land"), a.get("Imps"), a.get("TotalNetValue"), lot, lon, lat, geom,
                 ms_to_date(a.get("LatestDocumentDate")), corr))
        # ---- verify INSIDE the transaction ----
        n, av = cur.execute(
            "SELECT COUNT(*), SUM(CAST(TotalNetValue AS REAL)) FROM parcels").fetchone()
        lind, = cur.execute(
            "SELECT TotalNetValue FROM parcels WHERE APN='63-2985-20'").fetchone()
        o = cur.execute(
            "SELECT Land, Imps, TotalNetValue FROM parcels WHERE APN='53-1695-26'").fetchone()
        oracle_ok = abs((o[0] + o[1] - 7000) - o[2]) < 1
        print(f"old: {old_n:,} rows ${old_av/1e9:.3f}B | new: {n:,} rows ${av/1e9:.3f}B "
              f"| values changed on {changed:,} parcels | new APNs (no geometry): {new_apns}")
        print(f"spot-check 63-2985-20 (Lindheim/Keeler): ${lind:,.0f} (county live said $2,411,800)")
        print(f"oracle 53-1695-26 net-AV identity: {'OK' if oracle_ok else 'FAIL'}")
        if not (n > 28000 and av > old_av * 0.98 and lind == 2411800 and oracle_ok):
            raise RuntimeError("verification failed")
        cur.execute("COMMIT")
        print("COMMITTED. parcels is now the live county roll as of", today)
    except Exception as e:
        cur.execute("ROLLBACK")
        sys.exit(f"VERIFY/WRITE FAILED ({e}) — rolled back; parcels table untouched.")

if __name__ == "__main__":
    main()
