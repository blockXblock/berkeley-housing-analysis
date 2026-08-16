#!/usr/bin/env python3
"""
Derive Berkeley's parcel-tax rate schedule from a sample of property tax bills.

THE PROBLEM
-----------
A Berkeley tax bill has two layers. The AD VALOREM layer (1.2323% of assessed
value in FY2025-26) is published per Tax Rate Area by the county and needs no
derivation. The FIXED CHARGES layer -- 26+ separately legislated parcel taxes,
the MAJORITY of a typical Berkeley bill -- appears in no dataset at all. It has
to be reconstructed.

THE METHOD (no published rate required to start)
------------------------------------------------
1. FLAT vs VARYING. A charge that is literally identical on every sampled parcel
   is flat-per-parcel. The rest scale with something.

2. RATIO TEST. If charge A and charge B are both (rate_i x sqft), then A/B is the
   SAME CONSTANT on every parcel regardless of what sqft is. So group the varying
   charges by pairwise-ratio stability: coefficient of variation below CV_TOL means
   a shared base. This identifies the per-square-foot family WITHOUT knowing any
   rate, and simultaneously excludes charges on some other base (EBMUD wet weather,
   storm water, vector control).

3. ANCHOR. One published rate converts the family to absolute units. BSEP Measure H
   (2024) levies $0.54 per square foot of improvements from 2025-07-01, so
   sqft = BSEP_charge / 0.54, and every other family rate follows.

4. VALIDATE. The anchor predicts each parcel's building square footage. Check it
   against the City of Berkeley's own Taxable Square Footage dataset -- an entirely
   independent source, and the one the City is bound by charter to use for these
   assessments. Agreement to the square foot confirms both the family and the anchor.

Usage:
    python -m scripts.tax_incidence.derive_rate_schedule [bill-dir] [out-json]

Bill PDFs live OUTSIDE the repo (see parse_bills.py privacy note).
"""

import json
import os
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_bills import parse  # noqa: E402

BILLS = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/Desktop/Alameda/parcels")
EXTRA = os.path.expanduser("~/Desktop/Alameda/2026-06-29-Alameda_County-Property-Tax.pdf")
# dwelling-unit counts for any sampled parcel that is not single-unit.
# 53-1695-26 is assessor UseCode 1150 (single family WITH a second unit); it pays
# exactly 2x the single-unit parcels on CSA Paramedic / Vector / Mosquito / Haz Waste,
# which is what identifies those charges as per-DWELLING-UNIT rather than flat.
UNITS = {"53-1695-26": 2}
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/derived/berkeley_parcel_tax_rate_schedule_2025-26.json"

YEAR = "2025-2026"
ANCHOR_ITEM = "SCHL ED PROGS/BSEP"
ANCHOR_RATE = 0.54          # BUSD Measure H (2024), per sqft of improvements, from 2025-07-01
CV_TOL = 0.02               # ratio-stability tolerance for "shares a base"
CITY_SQFT_API = "https://data.cityofberkeley.info/resource/9a47-nj4i.json?$limit=50000"


def load_bills(paths):
    bills = []
    for p in paths:
        b = parse(p)
        if b and b["tax_year"] == YEAR:
            bills.append(b)
    return bills


def classify(bills, units=None):
    """Split fixed charges into flat / per-dwelling-unit / per-sqft family / other-base.

    `units` maps APN -> dwelling-unit count. Charges that are constant per UNIT
    rather than per PARCEL are only separable if the sample contains a parcel with
    more than one unit; otherwise they are indistinguishable from flat and are
    reported as flat (correct for single-unit parcels, wrong for duplexes up).
    """
    units = units or {}
    universal = {}
    for b in bills:
        for k, v in b["fixed"].items():
            universal.setdefault(k, {})[b["apn"]] = v
    universal = {k: v for k, v in universal.items() if len(v) == len(bills)}

    flat, per_unit = {}, {}
    for k, v in universal.items():
        if max(v.values()) - min(v.values()) < 0.01:
            flat[k] = next(iter(v.values()))
            continue
        # constant once divided by unit count -> levied per dwelling unit
        norm = [amt / units.get(a, 1) for a, amt in v.items()]
        if max(norm) - min(norm) < 0.01:
            per_unit[k] = round(statistics.mean(norm), 2)
    varying = {k: v for k, v in universal.items() if k not in flat and k not in per_unit}

    base = ANCHOR_ITEM
    family, rejected = [], []
    for k in varying:
        ratios = [varying[k][a] / varying[base][a] for a in varying[k] if varying[base].get(a)]
        cv = statistics.pstdev(ratios) / statistics.mean(ratios)
        (family if cv < CV_TOL else rejected).append((k, cv))
    return flat, per_unit, sorted(family, key=lambda x: x[1]), sorted(rejected, key=lambda x: x[1])


def city_sqft():
    """City of Berkeley taxable square footage, keyed by canonical APN."""
    sys.path.insert(0, "scripts")
    import housing_rules
    raw = subprocess.run(["curl", "-s", "--max-time", "120", CITY_SQFT_API],
                         capture_output=True, text=True).stdout
    out = {}
    for r in json.loads(raw):
        k = housing_rules.to_canonical_apn(r["apn"], "alameda")
        if k:
            out[k] = float(r["bldsqfttaxable"] or 0)
    return out


def main():
    paths = [os.path.join(BILLS, f) for f in sorted(os.listdir(BILLS)) if f.endswith(".pdf")]
    # the multi-unit parcel is what separates per-dwelling-unit charges from flat ones;
    # without at least one in the sample they are indistinguishable
    if os.path.exists(EXTRA):
        paths.append(EXTRA)
    bills = load_bills(paths)
    print(f"{len(bills)} FY{YEAR} bills")
    if len(bills) < 10:
        print("Need >=10 bills for a stable ratio test."), sys.exit(1)

    # verification before anything is derived
    bad = [b["apn"] for b in bills
           if abs(b["av_tax_total"] + b["fixed_total"] - b["base_tax_total"]) > 0.02
           or abs(sum(b["fixed"].values()) - b["fixed_total"]) > 0.02]
    print(f"reconciliation: {len(bills)-len(bad)}/{len(bills)} bills reconcile to printed totals")
    if bad:
        print(f"HALTING -- unreconciled: {bad}")
        sys.exit(1)

    flat, per_unit, family, rejected = classify(bills, UNITS)
    print(f"\nFLAT per parcel ({len(flat)}): ${sum(flat.values()):,.2f} total")
    print(f"PER DWELLING UNIT ({len(per_unit)}): ${sum(per_unit.values()):,.2f} per unit")
    for k, v in sorted(per_unit.items(), key=lambda x: -x[1]):
        print(f"   ${v:>7,.2f}  {k}")
    print(f"PER-SQFT family ({len(family)}), by ratio stability vs {ANCHOR_ITEM}:")
    for k, cv in family:
        print(f"   CV {cv:.5f}  {k}")
    print(f"OTHER base -- excluded ({len(rejected)}):")
    for k, cv in rejected:
        print(f"   CV {cv:.4f}  {k}")

    # anchor + integrality check
    sq = {b["apn"]: b["fixed"][ANCHOR_ITEM] / ANCHOR_RATE for b in bills}
    clean = [b for b in bills if abs(sq[b["apn"]] - round(sq[b["apn"]])) < 0.01]
    print(f"\nanchor ${ANCHOR_RATE}/sqft -> {len(clean)}/{len(bills)} parcels land on whole square feet")

    fam = [k for k, _ in family]
    rates = {k: round(statistics.mean(b["fixed"][k] / sq[b["apn"]] for b in clean), 6) for k in fam}

    # independent validation against the City's own dataset
    try:
        cs = city_sqft()
        sys.path.insert(0, "scripts")
        import housing_rules
        hits = [(b["apn"], sq[b["apn"]], cs.get(housing_rules.to_canonical_apn(b["apn"], "alameda")))
                for b in bills]
        cmp_ = [(a, d, c) for a, d, c in hits if c]
        exact = sum(1 for _, d, c in cmp_ if abs(d - c) < 1)
        print(f"validation vs City taxable sqft: {exact}/{len(cmp_)} exact to the square foot")
        validation = {"matched": len(cmp_), "exact": exact,
                      "source": "data.cityofberkeley.info 9a47-nj4i"}
    except Exception as e:                                   # network optional
        print(f"validation skipped ({e})")
        validation = None

    residual = statistics.median(
        b["fixed_total"] - (sq[b["apn"]] * sum(rates.values()) + sum(flat.values())
                            + sum(per_unit.values()) * UNITS.get(b["apn"], 1)) for b in bills)

    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    sched = {
        "fiscal_year": YEAR, "derived_by": os.path.basename(__file__), "v4_sha": sha,
        "sample_n": len(bills), "anchor": {"item": ANCHOR_ITEM, "rate": ANCHOR_RATE,
                                           "authority": "BUSD Measure H (2024)"},
        "per_sqft_of_improvements": rates,
        "per_sqft_total": round(sum(rates.values()), 6),
        "flat_per_parcel": flat, "flat_total": round(sum(flat.values()), 2),
        "per_dwelling_unit": per_unit, "per_dwelling_unit_total": round(sum(per_unit.values()), 2),
        "per_dwelling_unit_confidence": "LOW -- identified from a single multi-unit parcel "
                                        "(53-1695-26, 2 units). Sample more duplexes to confirm.",
        "not_modelled": {"items": [k for k, _ in rejected],
                         "median_residual_per_parcel": round(residual, 2)},
        "ad_valorem_rate_all_berkeley_TRAs": 0.012323,
        "validation": validation,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(sched, open(OUT, "w"), indent=1)
    print(f"\nper-sqft ${sum(rates.values()):.5f}/sqft  +  flat ${sum(flat.values()):.2f}"
          f"  +  ${sum(per_unit.values()):.2f}/dwelling unit"
          f"  (+ ${residual:,.0f} median unmodelled)")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
