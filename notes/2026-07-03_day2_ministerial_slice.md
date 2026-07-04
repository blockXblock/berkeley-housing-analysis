# Day 2 — Ministerial path & Middle Housing first-year slice (mayor-prep)

Source: the fresh Accela harvest (`data/raw/accela/date_range/`, 9,275 unique records,
2025-06-01 → 2026-07-03, committed `a61f00e`). Analysis: filing counts + status + description
text; the harvest carries FILE DATE + CURRENT STATUS only (no issuance/approval dates), so all
speed figures are UPPER BOUNDS (age-at-observation of already-approved records).

## Headline: the Middle Housing pathway is real, fast, small, and mostly an additions tool

Berkeley's ordinance created a dedicated record type — **ZCMH, "Zoning Certificate for Middle
Housing"** — and the harvest holds its entire life: **first application 2025-11-03**, so the
pathway is ~8 months old.

- **Volume: 28 genuine ZCMH/middle-housing planning records** (~3.5/month; a 29th text-match is a
  business-license cert for a consulting firm — excluded). Monthly: Nov 4 · Dec 7 · Jan 3 · Feb 5
  · Mar 2 · Apr 5 · May 2 · Jun 1 — no growth trend yet.
- **Outcomes: 15 Approved, 0 Denied** (6 under review, 2 withdrawn, 3 closed, 1 filed, 1
  incomplete, 1 awaiting documents). The certificate lane approves.
- **Speed (upper bounds):** the 4 approved among March-or-later filings were each ≤ 73/59/77/109
  days old at observation — planning approval inside ~2.5 months. Consistent with a functioning
  ministerial/certificate process.
- **What they build — the honest part:** roughly **two-thirds are major residential ADDITIONS or
  remodels** to existing homes (the ordinance being used as an expansion tool); roughly **ten
  projects add net units** (~15–20 units proposed in year one: three new SFDs on Allston, a
  warehouse→4-unit conversion on Eighth, establish-4-units on Eighth, 2→4 units on Russell,
  SFD→duplex on Ninth, SFD→2 units on Holly, a new second SFD on Eighth, an office→SFD change of
  use on Regent…); **one record removes a unit** (attic decommission, Grant). First-year unit
  yield: modest. The pathway works; it is not (yet) a production engine.

## The rest of the state-law toolbox (same window)

- **SB 9: essentially unused** — one address-assignment reference, zero applications.
- **Density bonus: 11 planning records** in 13 months (the big-project lane, as expected).
- **SB 330 preliminary applications: 23** (pipeline-intent signal worth tracking).
- **ADU flow steady: ~20/month** of Building records mention ADU/JADU (278 total) — the proven
  fast lane keeps running (JN-I: median 3-day issuance).
- **Solar fast lane: 1,076 ESR records** — by far the biggest ministerial stream by volume.

## The waiting room (what the CPRA feed never shows)

- **539 TMP records** — applications pending/incomplete, invisible in every prior data source.
- Planning statuses expose clock states: `Corrections Pending Applicant`, `Incomplete Pending
  Applicant`, `Pending Final Action` — applicant-side vs city-side wait is partially
  distinguishable going forward (snapshot-diff will timestamp transitions).
- Planning overall: **743 Approved vs 52 Denied** — denial is rare; delay, not denial, is the
  binding variable (consistent with JN-I).

## ⚠ Cross-check finding: the CPRA report under-captures filings

Overlap-window comparison (B-permit filings/month): harvest **478/479/467/595/564/467/533**
(Jun–Dec 2025) vs CPRA feed **332/315/288/368/359/263/207**. The harvest finds **~40–50% more**
B-permits than the "BP Annual Permit Report," and the feed's December is visibly truncated. The
report evidently applies undocumented filters. Actions: (1) a clarification line added to CPRA
Request 1 asking for the report's filter criteria; (2) all fresh-period counts in the mayor deck
source to the harvest, not the feed; (3) the divergence itself is a transparency exhibit.

## Deck implications ("what works")

1. **Ministerial lanes demonstrably work**: ADU (3-day median issuance, ~20/mo), solar (1,000+/yr),
   and now ZCMH (0 denials, ≤2.5-month approvals).
2. **Middle Housing's first year complicates both simple narratives**: it neither flooded
   neighborhoods (28 applications, ~15–20 net units) nor failed (steady use, fast approvals,
   two-thirds homeowner additions). It's currently a *homeowner flexibility* tool more than a
   *housing production* tool.
3. **Delay, not denial** is where process reform pays — matches JN-I's timeline evidence.
4. **Zero commercial-zone contact**: every ZCMH record is in residential fabric; the
   corridor/business questions (Day 3) are about the big projects, not this pathway.
