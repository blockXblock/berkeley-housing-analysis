#!/usr/bin/env python3
"""refresh_parcel_owners.py — the OWNERSHIP layer, from the county's own maintained feeds.

MACHINERY (re-runnable). Fills the gap commit ef84640 recorded as "Owner-name layer refresh still
open (source layer URL unknown — maps-session asset)". Two Alameda County ArcGIS tables nobody had
found, both on the same org as the Parcels feed (services5.arcgis.com/ROBnTHSNjoZ2Wm1P):

  1. Assessor_Office_Secured_Tax_Roll_<YYYY>_to_<YYYY>  — one table per roll year, 2019-20 onward.
     29,163 Berkeley rows. Carries MAILING ADDRESS, HOEX/OTEX (exemptions), TRA_Primary/Secondary,
     and the Latest_Document prefix+series+date. Discovered dynamically (a new vintage posts each
     July; hardcoding one would silently go stale).
  2. Assessor_Office_Ownership_Transfer_List — two-year rolling transfer list, 11,431 Berkeley rows
     spanning 2023-03-31..2025-03-17. Rows are one per NAME (transferor or transferee), so they
     collapse to 4,392 DOCUMENTS. Carries doc_prefix+doc_series (the Recorder key) and
     value_from_trans_tax, a price derived from documentary transfer tax — present on 1,286 of the
     4,392 documents (29%), NOT on all of them. Count documents, never rows.

⚠ THE COUNTY PUBLISHES NO OWNER NAMES — verified, not assumed. The Parcels layer has no name field;
the roll HAS an `Attention_Name` column that is populated on 0 of 29,163 Berkeley parcels; and the
transfer list types each row TRANSFEROR/TRANSFEREE but carries NO name column at all. Names remain a
Regrid/Recorder acquisition. What this script provides is what the names were WANTED FOR — owner-
occupancy, absentee ownership, portfolio grouping, and turnover — from data the county maintains.

⚠ TWO TRAPS, both already paid for once in this repo:
  (a) THE ROLL IS A VINTAGE, NOT A LIVE FEED. The 2025-26 table was published 2025-07-07 and is a
      year behind the live Parcels feed: 63-2985-20 (Keeler) reads $1,123,631 here vs $2,411,800
      live — the exact pre-transfer value Dan Lindheim reported as stale. Use it as a HISTORICAL
      PANEL. `berkeley.db` stays the current-value source (scripts/refresh_berkeley_parcels.py).
  (b) `Mailing_Address_Effective_Date` IS NOT TENURE. On both spot-check parcels it equals
      Latest_Document_Date, and on 2811 Benvenue — owned since 1988 — it reads 2021. This is the
      same refi/trust-transfer artefact that made the 2026-08-14 "years held" correction necessary
      (see gen_ownership_map.py's docstring). Stored, never labelled as tenure. TRUE years-owned
      still needs the Recorder deed index WITH document type.

ABSENTEE is a PROXY, not a fact: mailing city != BERKELEY. An out-of-town owner who mails to a local
property manager reads as local; a Berkeley owner with a PO box elsewhere reads as absentee.

NAMED OWNERS come from a CITY source, never the county: Berkeley rental business licences (see
LICENCES). Every name carries `named_owner_source`, because a 2025 licence and a 2017 assessor
extract are different claims and must never be displayed as though they were the same one. Parcels
with no licence read `named_owner_source='none'` — unknown WITH provenance, per CLAUDE.md rule 1.

READ-ONLY on berkeley.db and the canonical v2 DB. Writes only NEW tables into databases/parcel_facts.db
(assessor_roll, ownership_transfers, owner_signals, source_provenance) — the `parcel_facts` table that
build_parcel_facts.py owns is never touched, and that script's to_sql(if_exists="replace") replaces only
its own table, so these survive its rebuilds.

Run:  python scripts/refresh_parcel_owners.py            # PREVIEW — fetches, derives, writes NOTHING
      python scripts/refresh_parcel_owners.py --commit   # snapshot + transactional write w/ rollback
      python scripts/refresh_parcel_owners.py --roll 2024_to_2025 --commit   # a specific vintage
"""
import argparse, csv, datetime, json, re, shutil, sqlite3, sys, time, urllib.error, urllib.parse, urllib.request
from collections import Counter, defaultdict

sys.path.insert(0, "scripts")
from housing_rules import to_canonical_apn

ORG = "https://services5.arcgis.com/ROBnTHSNjoZ2Wm1P/arcgis/rest/services"
ROLL_PREFIX = "Assessor_Office_Secured_Tax_Roll_"
TRANSFERS = "Assessor_Office_Ownership_Transfer_List"
DB = "databases/parcel_facts.db"
# The frozen 2017 name extract. NOT a data source — a VALIDATOR. It is the only thing that can tell
# a real portfolio from a property manager's mail drop (see classify_portfolios), which is the one
# way mailing-address grouping goes badly wrong. Optional: absent, portfolio_class reads 'unchecked'.
OWNERS_2017 = "data/reference/berkeley_parcel_owners_2026-08-13.csv"
# City of Berkeley business licences. A rental licence names the OWNER of the rental property, and
# it is a CURRENT (Nov-2025) primary source from a DIFFERENT agency than the county — so it is the
# one named-owner layer we hold that is neither frozen at 2017 nor licensed from a vendor.
# VALIDATED: across 2,945 parcels present in both, 78% of licence names share a name token with the
# 2017 assessor name — independent confirmation that the licensee is the owner, not a tenant.
LICENCES = "data/raw/business_licenses_20251115.json"
PAGE = 2000                                    # = the services' maxRecordCount

# Oracles — stable identities, not moving totals (CLAUDE.md: anchor to what stays true).
# 2811 Benvenue: the known-truth calibration parcel (owner-occupied, mails to itself, HOEX filed).
# 1146 Keeler: the Lindheim parcel (absentee — mails to Los Gatos — and no exemption).
ORACLES = {"53-1695-26": dict(hoex=7000, mail_city="BERKELEY"),
           "63-2985-20": dict(hoex=0, mail_city="LOS GATOS")}


# ---------------------------------------------------------------- fetch
def _get(url, **params):
    """RETRY BEFORE BELIEVING A FAILURE. The county's ArcGIS returns transient errors mid-pagination
    — an HTTP 304 arrived at offset 20,000 of a fetch that had just succeeded end-to-end twice. Same
    discipline as the harvester rule in CLAUDE.md: a one-shot failure is not evidence of anything.
    Cache-buster on retry, since a spurious 304 means something upstream thinks we already have it."""
    q = urllib.parse.urlencode({"f": "json", **params})
    last = None
    for attempt in range(5):
        try:
            bust = f"&_={datetime.datetime.now().timestamp()}" if attempt else ""
            req = urllib.request.Request(f"{url}?{q}{bust}",
                                         headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.load(r)
            if "error" in d:
                sys.exit(f"ArcGIS error on {url}: {d['error']}")   # a real API error, not transient
            return d
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            print(f"\n  transient {type(e).__name__} ({e}) — retry {attempt + 1}/5", flush=True)
            time.sleep(2 ** attempt)
    sys.exit(f"FAILED after 5 retries on {url}: {last}")


def latest_roll_name():
    """Newest Secured_Tax_Roll vintage on the org. Dynamic: a new one posts each July."""
    names = sorted(s["name"] for s in _get(ORG)["services"] if s["name"].startswith(ROLL_PREFIX))
    if not names:
        sys.exit(f"no {ROLL_PREFIX}* service found on the org — did the county rename it?")
    return names[-1]


def layer_meta(service):
    d = _get(f"{ORG}/{service}/FeatureServer/0")
    ms = (d.get("editingInfo") or {}).get("lastEditDate")
    return dict(published=datetime.datetime.fromtimestamp(ms / 1000).date().isoformat() if ms else None,
                fields=[f["name"] for f in d.get("fields", [])])


def fetch_all(service, where):
    url, rows, off = f"{ORG}/{service}/FeatureServer/0/query", [], 0
    while True:
        d = _get(url, where=where, outFields="*", orderByFields="OBJECTID",
                 resultOffset=off, resultRecordCount=PAGE)
        feats = d.get("features", [])
        rows += [f["attributes"] for f in feats]
        print(f"  {service}: {len(rows):,} ...", end="\r", flush=True)
        if len(feats) < PAGE:
            break
        off += PAGE
    print(f"  {service}: {len(rows):,} rows fetched      ")
    return rows


# ---------------------------------------------------------------- normalize
def s(v):
    """County tables are fixed-width: every string arrives space-padded."""
    return re.sub(r"\s+", " ", str(v)).strip() if v is not None else ""


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def as_date(v):
    """The roll returns dates as 'YYYY-MM-DD' strings; the transfer list as epoch ms. Accept both."""
    if v in (None, "", 0):
        return None
    if isinstance(v, (int, float)):
        return datetime.datetime.fromtimestamp(v / 1000).date().isoformat()
    t = s(v)[:10]
    return t if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t) else None


def canon(raw):
    try:
        return to_canonical_apn(s(raw), "alameda") or None
    except Exception:
        return None                              # malformed APNs are reported, never guessed at


def mailing_key(r):
    """The portfolio key. Grouping by MAILING ADDRESS beats grouping by name: it is immune to the
    name variants ('SMITH JOHN A' / 'SMITH JOHN ALAN TR') that wreck name-matching — which matters
    doubly here, since we have no names at all."""
    parts = [s(r.get("Mailing_Address_Street")), s(r.get("Mailing_Address_Unit")),
             s(r.get("Mailing_Address_City_State")), s(r.get("Mailing_Address_Zip"))]
    if not parts[0]:
        return None
    return re.sub(r"[^A-Z0-9 |]", "", "|".join(parts).upper())


# ---------------------------------------------------------------- derive
def build_roll(raw, roll_name):
    out, bad_apn, seen = [], 0, set()
    for r in raw:
        cp = canon(r.get("Print_Parcel"))
        if not cp or cp in seen:                 # the roll is one row per parcel; dupes would be a feed fault
            bad_apn += not cp
            continue
        seen.add(cp)
        out.append(dict(
            capn=cp, apn_raw=s(r.get("Print_Parcel")), roll=roll_name.replace(ROLL_PREFIX, ""),
            situs_address=" ".join(x for x in [s(r.get("Situs_Street_Number")),
                                               s(r.get("Situs_Street_Name")),
                                               s(r.get("Situs_Unit"))] if x),
            situs_city=s(r.get("Situs_City")), situs_zip=s(r.get("Situs_Zip")),
            tra_primary=s(r.get("TRA_Primary")), tra_secondary=s(r.get("TRA_Secondary")),
            land=num(r.get("Land")), imps=num(r.get("Imps")), fixtures=num(r.get("Fixtures")),
            bpp=num(r.get("BPP")), hpp=num(r.get("HPP")),
            hoex=num(r.get("HOEX")), otex=num(r.get("OTEX")),
            total_net_value=num(r.get("Total_Net_Value")), use_code=s(r.get("Use_Code")),
            latest_doc_prefix=s(r.get("Latest_Document_Prefix")),
            latest_doc_series=s(r.get("Latest_Document_Series")),
            latest_doc_date=as_date(r.get("Latest_Document_Date")),
            latest_doc_input_date=as_date(r.get("Latest_Document_Input_Date")),
            attention_name=s(r.get("Attention_Name")),          # 0% populated — kept to PROVE that
            mailing_street=s(r.get("Mailing_Address_Street")),
            mailing_unit=s(r.get("Mailing_Address_Unit")),
            mailing_city_state=s(r.get("Mailing_Address_City_State")),
            mailing_zip=s(r.get("Mailing_Address_Zip")),
            # NOT tenure — see docstring trap (b). Stored under a name that cannot be misread.
            mailing_effective_date=as_date(r.get("Mailing_Address_Effective_Date")),
            mailing_key=mailing_key(r)))
    return out, bad_apn


def build_transfers(raw):
    """Collapse the TRANSFEROR/TRANSFEREE rows into one row per (parcel, document).

    The rows are one per NAME, not one per side: 11,431 Berkeley rows collapse to 4,392 documents
    (2.6 rows each), because a sale between two couples files four. So although the county withholds
    the names themselves, the ROW COUNT still reveals HOW MANY parties stood on each side — kept as
    transferor_parties/transferee_parties, since a 1->1 transfer and a 6->1 consolidation are
    different events and nothing else in our data distinguishes them."""
    bydoc, bad_apn = defaultdict(lambda: dict(sides=Counter())), 0
    for r in raw:
        cp = canon(r.get("apn"))
        if not cp:
            bad_apn += 1
            continue
        k = (cp, s(r.get("doc_prefix")), s(r.get("doc_series")), as_date(r.get("transfer_dt")))
        d = bydoc[k]
        d["sides"][s(r.get("name_type")).upper()] += 1
        d.update(capn=cp, apn_raw=s(r.get("apn")), doc_prefix=k[1], doc_series=k[2],
                 transfer_date=k[3], doc_date=as_date(r.get("doc_dt")),
                 use_code=s(r.get("use_cd")), use_name=s(r.get("use_name")),
                 address=" ".join(x for x in [s(r.get("street_num")), s(r.get("pre_dir")),
                                              s(r.get("street_name")), s(r.get("street_suffix")),
                                              s(r.get("post_dir"))] if x),
                 city=s(r.get("city_name")), zip=s(r.get("zip_cd")),
                 doc_parcel_count=num(s(r.get("doc_parcel_count"))))
        # Coalesce rather than overwrite. MEASURED on the 2023-25 window: 0 documents carry the
        # value on only one row, so this is a guard, not a fix for an observed fault — but a plain
        # update() would silently drop the price the first time the county files one that way.
        v = num(s(r.get("value_from_trans_tax")) or None)   # zero-padded, trailing '.': '000002525000.'
        if v is not None:
            d["transfer_value"] = max(v, d.get("transfer_value") or 0)
        d.setdefault("transfer_value", None)
    out = []
    for d in bydoc.values():
        sides = d.pop("sides")
        out.append(dict(d, transferor_parties=sides.get("TRANSFEROR", 0),
                        transferee_parties=sides.get("TRANSFEREE", 0)))
    return out, bad_apn


def classify_portfolios(roll):
    """MAILING-ADDRESS GROUPING CONFLATES OWNER WITH AGENT — measured, not feared:

        2180 Milvia St   184 parcels -> 176/178 are 'CITY OF BERKELEY'      one owner
        1111 Franklin St  55 parcels ->  52/53 are 'REGENTS OF THE UNIV...'  one owner
        2278 Shattuck Ave 47 parcels ->  25 DISTINCT owners behind 44        a manager's mail drop
        2941 Telegraph    42 parcels ->  31 DISTINCT owners behind 42        a manager's mail drop

    Institutional owners mail to themselves, so grouping recovers them cleanly (and absorbs name
    variants for free). Private owners often mail to a property manager or a lender's tax servicer,
    where the same key is dozens of UNRELATED owners. Calling that a portfolio would publish a false
    claim about who owns Berkeley, so every key is classified and the classification travels WITH
    the row. The stale 2017 name file is what makes this possible — its proper role is validator,
    never the map's spine."""
    try:
        with open(OWNERS_2017, newline="") as fh:
            names = {}
            for r in csv.DictReader(fh):
                cp = canon(r.get("APN"))
                if cp and s(r.get("OwnersName")):
                    names[cp] = s(r.get("OwnersName")).upper()
    except FileNotFoundError:
        return {}, None

    members = defaultdict(list)
    for r in roll:
        if r["mailing_key"]:
            members[r["mailing_key"]].append(r["capn"])
    out = {}
    for mk, caps in members.items():
        if len(caps) < 2:
            out[mk] = ("single_parcel", 0, 0)
            continue
        found = [names[c] for c in caps if c in names]
        distinct = len(set(found))
        # EVIDENCE FLOOR, and it is load-bearing. Dominant-share over the FOUND names alone gives a
        # single name 100% confidence: PO Box 4747, Oak Brook IL — 173 parcels with exactly ONE 2017
        # name among them — first classified as 'single_owner', which would have published "one owner
        # holds 173 Berkeley parcels" on the strength of a single row. A thin base proves nothing in
        # either direction, so it is 'unverified', never a verdict.
        if len(found) < max(3, 0.3 * len(caps)):
            cls = "unverified"                    # incl. parcels created after the 2017 extract
        else:
            dominant = Counter(found).most_common(1)[0][1] / len(found)
            cls = ("single_owner" if dominant >= 0.8 else
                   "agent_or_servicer" if distinct >= 3 and dominant <= 0.5 else "mixed")
        out[mk] = (cls, distinct, len(found))
    return out, len(names)


def load_licences():
    """Rental business licences, keyed by canonical APN.

    Coverage is the point: these land on 605 of the 1,334 `agent_or_servicer` parcels and 532
    `unverified` ones — precisely the cases where mailing-address grouping cannot say who the owner
    is. A licence is filed BY the owner, so it cuts straight through the manager's mail drop.

    `busdesc` also encodes the unit count ('RES. RENTAL - 4 UNITS'), kept as licensed_rental_units:
    an independently-sourced unit figure for the rental stock, useful to the ghost-units work.
    Commercial rental licences name a commercial property's owner — kept, but tagged, since they say
    nothing about housing."""
    try:
        with open(LICENCES) as fh:
            rows = json.load(fh)
    except FileNotFoundError:
        return {}
    rows = rows if isinstance(rows, list) else list(rows.values())[0]
    out = {}
    for r in rows:
        desc = s(r.get("busdesc")).upper()
        if "RENTAL" not in desc and "DWELL" not in desc:
            continue
        cp = canon(r.get("apn_normalized") or r.get("apn"))
        name = s(r.get("b1_business_name")) or s(r.get("dba"))
        if not cp or not name:
            continue
        m = re.search(r"(\d+)\s*UNITS?", desc)
        kind = "commercial" if desc.startswith("COMMERCIAL") else "residential"
        cur = out.get(cp)
        # One parcel can carry several licences. Prefer a RESIDENTIAL licence (it is the one that
        # speaks to housing) and, within that, the one declaring the most units.
        if cur is None or (kind == "residential" and cur["kind"] == "commercial") or \
           (kind == cur["kind"] and (int(m.group(1)) if m else 0) > (cur["units"] or 0)):
            out[cp] = dict(name=name.upper(), kind=kind,
                           units=int(m.group(1)) if m else None, desc=desc, count=0)
        out[cp]["count"] += 1
    return out


def build_signals(roll, transfers, city, portfolios, licences):
    """One row per parcel: the honest ownership signals, each traceable to a source column."""
    portfolio = Counter(r["mailing_key"] for r in roll if r["mailing_key"])
    last = {}
    for t in transfers:                          # most recent transfer per parcel
        if t["transfer_date"] and (t["capn"] not in last
                                   or t["transfer_date"] > last[t["capn"]]["transfer_date"]):
            last[t["capn"]] = t
    sig = []
    for r in roll:
        mk, lt = r["mailing_key"], last.get(r["capn"])
        pcls, pdist, pnamed = portfolios.get(mk, ("unchecked", 0, 0)) if mk else (None, None, None)
        lic = licences.get(r["capn"])
        # HOEX is FILED, not inferred: the $7,000 homeowner's exemption applies only to an
        # owner-occupied home. It UNDERCOUNTS owner-occupancy (eligible owners who never filed).
        occ = 1 if (r["hoex"] or 0) > 0 else 0
        # Absentee: mailing city != the situs city. A proxy — see docstring.
        mc = r["mailing_city_state"].upper()
        absentee = None if not mc else int(not mc.startswith(city.upper()))
        sig.append(dict(
            capn=r["capn"], situs_address=r["situs_address"],
            owner_occupied_hoex=occ, other_exemption=int((r["otex"] or 0) > 0),
            absentee_mailing=absentee, mailing_key=mk,
            mailing_city_state=r["mailing_city_state"],
            portfolio_parcels=portfolio.get(mk, 0) if mk else None,
            # Only 'single_owner' may be described to the public as one owner's holdings.
            portfolio_class=pcls, portfolio_distinct_names_2017=pdist,
            portfolio_named_parcels_2017=pnamed,
            tra_primary=r["tra_primary"], tra_secondary=r["tra_secondary"],
            total_net_value=r["total_net_value"], use_code=r["use_code"],
            last_transfer_date=lt["transfer_date"] if lt else None,
            last_transfer_value=lt["transfer_value"] if lt else None,
            # NAMED OWNER, WITH ITS PROVENANCE ATTACHED (CLAUDE.md rule 1: unknown-with-provenance,
            # never a bare fill). The county publishes no names, so every name here comes from a
            # City source and says so. `named_owner_source` is the whole point of the column — a
            # 2025 licence and a 2017 assessor extract are not the same claim and must never be
            # displayed as if they were.
            licensed_owner_name=lic["name"] if lic else None,
            licensed_owner_kind=lic["kind"] if lic else None,
            licensed_rental_units=lic["units"] if lic else None,
            licence_count=lic["count"] if lic else 0,
            named_owner=lic["name"] if lic else None,
            named_owner_source="business_licence_2025-11-15" if lic else "none",
            roll=r["roll"]))
    return sig


# ---------------------------------------------------------------- verify
def verify(roll, transfers, signals, city):
    """Invariant checks, run in PREVIEW and again INSIDE the write transaction. Anchored to
    structural identities and stable oracles — never to a current total that a legitimate county
    update would move (CLAUDE.md: invariant - documented deltas, not a frozen number)."""
    ok, notes = True, []

    n = len(roll)
    if n < 28000:
        ok = False
    notes.append(f"{'OK ' if n >= 28000 else 'FAIL'} roll rows: {n:,} (invariant: >28,000 {city} parcels)")

    # NET-AV IDENTITY — the same class of check as refresh_berkeley_parcels.py's 53-1695-26 oracle:
    # gross assessed value minus the filed exemptions must equal the net. Structural, so it holds
    # across roll years; a feed that broke it would be silently unusable.
    checked = [r for r in roll if None not in (r["land"], r["imps"], r["total_net_value"])]
    bad = [r for r in checked
           if abs(sum(r[k] or 0 for k in ("land", "imps", "fixtures", "bpp", "hpp"))
                  - (r["hoex"] or 0) - (r["otex"] or 0) - r["total_net_value"]) > 1]
    rate = 1 - len(bad) / max(len(checked), 1)
    if rate < 0.99:
        ok = False
    notes.append(f"{'OK ' if rate >= 0.99 else 'FAIL'} net-AV identity "
                 f"(land+imps+fixtures+bpp+hpp-hoex-otex == total_net_value): "
                 f"{rate:.4%} of {len(checked):,}" + (f"  [{len(bad)} violators]" if bad else ""))

    by_apn = {r["apn_raw"]: r for r in roll}
    for apn, exp in ORACLES.items():
        r = by_apn.get(apn)
        if not r:
            ok = False
            notes.append(f"FAIL oracle {apn}: absent from the roll")
            continue
        hit = (r["hoex"] or 0) == exp["hoex"] and r["mailing_city_state"].upper().startswith(exp["mail_city"])
        ok &= hit
        notes.append(f"{'OK ' if hit else 'FAIL'} oracle {apn} ({r['situs_address']}): "
                     f"HOEX ${r['hoex']:,.0f} (want ${exp['hoex']:,}), mails to "
                     f"{r['mailing_city_state']} (want {exp['mail_city']})")

    # The county publishes no owner names. If Attention_Name ever populates, that is NEWS, not a
    # failure — the check reports it rather than blocking.
    att = sum(1 for r in roll if r["attention_name"])
    notes.append(f"{'--' if att == 0 else '!!'} Attention_Name populated: {att:,} of {n:,}"
                 + ("  (as expected: the county publishes NO owner names)" if att == 0
                    else "  <- CHANGED: the county has started publishing a name field. Investigate."))

    if transfers:
        ds = sorted(t["transfer_date"] for t in transfers if t["transfer_date"])
        val = sum(1 for t in transfers if t["transfer_value"])
        notes.append(f"OK  transfers: {len(transfers):,} documents, {ds[0]}..{ds[-1]}, "
                     f"{val:,} with a transfer-tax value")
    else:
        ok = False
        notes.append("FAIL transfers: none fetched")

    named = [g for g in signals if g["named_owner"]]
    on_hard = sum(1 for g in named if g["portfolio_class"] in ("agent_or_servicer", "unverified"))
    notes.append(f"--  named owners (Berkeley rental licences, {LICENCES[-13:-5]}): {len(named):,} "
                 f"parcels, of which {on_hard:,} sit on keys mailing-address grouping could not "
                 f"resolve")

    occ = sum(s["owner_occupied_hoex"] for s in signals)
    abs_ = sum(1 for s in signals if s["absentee_mailing"] == 1)
    notes.append(f"--  signals: {occ:,} owner-occupied (HOEX filed) | {abs_:,} absentee mailing "
                 f"| {sum(1 for s in signals if (s['portfolio_parcels'] or 0) >= 2):,} parcels "
                 f"in a multi-parcel portfolio")
    return ok, notes


# ---------------------------------------------------------------- write
def write(con, table, rows):
    cols = list(rows[0])
    con.execute(f"DROP TABLE IF EXISTS {table}")
    con.execute(f"CREATE TABLE {table} ({', '.join(chr(34) + c + chr(34) for c in cols)})")
    con.executemany(f"INSERT INTO {table} VALUES ({','.join('?' * len(cols))})",
                    [tuple(r[c] for c in cols) for r in rows])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="write (default is a read-only preview)")
    ap.add_argument("--roll", help="roll vintage, e.g. 2024_to_2025 (default: newest on the org)")
    ap.add_argument("--city", default="BERKELEY")
    a = ap.parse_args()

    roll_svc = ROLL_PREFIX + a.roll if a.roll else latest_roll_name()
    rm, tm = layer_meta(roll_svc), layer_meta(TRANSFERS)
    print(f"roll      : {roll_svc}  (county published {rm['published']})")
    print(f"transfers : {TRANSFERS}  (county published {tm['published']})")
    print("NOTE: the roll is a VINTAGE, a year behind the live Parcels feed — historical panel, "
          "NOT a current-value source (berkeley.db stays that).\n")

    raw_roll = fetch_all(roll_svc, f"Situs_City='{a.city}'")
    raw_tr = fetch_all(TRANSFERS, f"city_name LIKE '{a.city}%'")
    roll, bad1 = build_roll(raw_roll, roll_svc)
    transfers, bad2 = build_transfers(raw_tr)
    portfolios, n_names = classify_portfolios(roll)
    if n_names is None:
        print(f"  NOTE: {OWNERS_2017} absent — portfolios cannot be validated (class='unchecked')")
    licences = load_licences()
    if not licences:
        print(f"  NOTE: {LICENCES} absent — no named-owner layer (named_owner_source='none')")
    signals = build_signals(roll, transfers, a.city, portfolios, licences)
    if bad1 or bad2:
        print(f"  (skipped un-canonicalizable APNs: {bad1} roll, {bad2} transfer rows)")

    print("\n--- verification " + "-" * 46)
    ok, notes = verify(roll, transfers, signals, a.city)
    for ln in notes:
        print("  " + ln)

    cls = Counter(s["portfolio_class"] for s in signals if s["portfolio_class"])
    print("\n  portfolio classification (validated against the 2017 name file):")
    for k in ("single_owner", "agent_or_servicer", "mixed", "unverified", "single_parcel", "unchecked"):
        if cls.get(k):
            print(f"    {cls[k]:>7,} parcels  {k}")
    print("\n  largest mailing-address groups (the county publishes no names):")
    seen = set()
    for k, c in Counter(s["mailing_key"] for s in signals if s["mailing_key"]).most_common(6):
        pc = next(s["portfolio_class"] for s in signals if s["mailing_key"] == k)
        flag = "" if pc == "single_owner" else "   <- NOT one owner"
        print(f"    {c:>4} parcels  [{pc:<17}] {k.replace('|', '  ')[:52]}{flag}")

    if not a.commit:
        print(f"\nPREVIEW ONLY — nothing written. --commit would write to {DB}:")
        print(f"  assessor_roll      {len(roll):,} rows\n  ownership_transfers {len(transfers):,} rows"
              f"\n  owner_signals      {len(signals):,} rows\n  source_provenance   2 rows")
        return

    if not ok:
        sys.exit("\nREFUSING to write: verification failed above.")

    stamp = datetime.date.today().isoformat()
    snap = f"databases/keep_snapshot_{stamp}_pre-owner-signals.db"
    shutil.copy(DB, snap)
    chk = sqlite3.connect(snap).execute("PRAGMA integrity_check").fetchone()[0]
    print(f"\nsnapshot: {snap}  integrity_check={chk}")
    if chk != "ok":
        sys.exit("snapshot integrity_check failed — not writing.")

    prov = [dict(table=t, service=f"{ORG}/{svc}/FeatureServer/0", county_published=pub,
                 fetched=datetime.datetime.now().isoformat(timespec="seconds"), rows=n,
                 note=note)
            for t, svc, pub, n, note in [
                ("assessor_roll", roll_svc, rm["published"], len(roll),
                 "VINTAGE roll, a year behind the live Parcels feed — historical panel, not current values. "
                 "mailing_effective_date is NOT tenure. No owner names: attention_name is 0% populated."),
                ("ownership_transfers", TRANSFERS, tm["published"], len(transfers),
                 "Two-year rolling window; transferor/transferee rows collapsed per document. No names.")]]

    con = sqlite3.connect(DB)
    con.isolation_level = None
    cur = con.cursor()
    cur.execute("BEGIN IMMEDIATE")
    try:
        write(cur, "assessor_roll", roll)
        write(cur, "ownership_transfers", transfers)
        write(cur, "owner_signals", signals)
        write(cur, "source_provenance", prov)
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_roll_capn ON assessor_roll(capn)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_sig_capn ON owner_signals(capn)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_tr_capn ON ownership_transfers(capn)")
        # re-verify from what actually landed, inside the transaction
        n_roll = cur.execute("SELECT COUNT(*) FROM assessor_roll").fetchone()[0]
        n_sig = cur.execute("SELECT COUNT(*) FROM owner_signals").fetchone()[0]
        n_tr = cur.execute("SELECT COUNT(*) FROM ownership_transfers").fetchone()[0]
        orc = cur.execute("SELECT hoex, mailing_city_state FROM assessor_roll "
                          "WHERE apn_raw='53-1695-26'").fetchone()
        untouched = cur.execute("SELECT COUNT(*) FROM parcel_facts").fetchone()[0]
        if not (n_roll == len(roll) and n_sig == len(signals) and n_tr == len(transfers)
                and orc and orc[0] == 7000 and orc[1].upper().startswith("BERKELEY")
                and untouched > 28000):
            raise RuntimeError(f"post-write verify: roll={n_roll} sig={n_sig} tr={n_tr} "
                               f"oracle={orc} parcel_facts={untouched}")
        cur.execute("COMMIT")
    except Exception as e:
        cur.execute("ROLLBACK")
        sys.exit(f"VERIFY/WRITE FAILED ({e}) — rolled back; {DB} untouched.")
    con.close()

    fresh = sqlite3.connect(DB)                  # fresh-connection fingerprint (CLAUDE.md discipline)
    print(f"COMMITTED to {DB}")
    for t in ("assessor_roll", "ownership_transfers", "owner_signals", "parcel_facts"):
        print(f"  {t:<20} {fresh.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>8,} rows"
              + ("   (pre-existing, untouched)" if t == "parcel_facts" else ""))


if __name__ == "__main__":
    main()
