# An independent check on Berkeley's housing numbers — what matched, what didn't, and what neither of us can see

*A reproducibility note fronting the Berkeley housing-data series. Every number here traces to the
reconciliation engine `scripts/reconcile_apr_vs_city.py` (G1), which compares our independent
reconstruction (built from primary permit records) against the City of Berkeley's own submitted
Annual Progress Report (APR) to the state. Read-only on both. The comparison window is 2018–2025
(the years the city has filed).*

---

## The short version

We rebuilt Berkeley's record of completed housing **from primary permit sources alone** — no access
to the city's internal database — and then checked it against the city's official state filing,
project by project. On the housing that actually got built, **the two independent records
substantially agree**: they match on **695 completed developments**. Along the way our independent
build **caught at least one completion the city's filing left out** — a **39-unit congregate
residence at 1367 University Ave**. And the exercise exposed a structural blind spot that is the real
story: **affordability — who the housing is actually for — is invisible in the permit record**, because
it lives in deed-restriction documents the city holds but doesn't publish as data.

This is **not** a "we're more accurate than the city" claim. In raw totals the city's number is
*larger* than ours, and we can account for the difference to the unit. The point is narrower and more
useful: **an outsider, working only from public permit records, can independently reproduce the city's
production count — and the one thing that outsider provably *cannot* see is affordability.**

---

## 1. The two independent records agree on what got built

Our reconstruction and the city's filing **match on 695 completed developments**. That is the headline:
two records built from different inputs (ours from primary permit records; the city's from its internal
tracking) land on the same large-development production.

At first glance there's a gap — the city reports **4,514** completed units (2018–2025), we report
**3,395** — a **1,119-unit** difference that looks like the city found a thousand units we missed. It
didn't. The gap **dissolves into how each side models the same data**, not into different buildings
(section 4).

## 2. We caught an omission — proj158, 1367 University Ave (39 units)

Our independent build flags **5 completed projects (43 units) that aren't in the city's filing.** Most
are small or ambiguous and we won't oversell them. But one is solid and concrete: a **39-unit
congregate residence at 1367 University Ave**, which our record shows completed with a City-finaled
building permit (B2022-04366, finaled 2025-05-06) and which **does not appear in the city's APR**. That
is the demonstrable value of an independent rebuild: it functions as an **audit** that can surface real
gaps in the official count.

We are deliberately not claiming more. The other four ours-only items (a single-family home and three
ADUs) are small and could reflect the city filing them differently rather than omitting them — so the
honest omission headline is **proj158**, not a number we've inflated.

## 3. Where our record stops — the small-project tail (49 units)

The city tracks a **49-unit tail of ADUs and single-family homes** (across ~49 small parcels) that our
reconstruction does not. This is **our** coverage boundary, stated plainly: our build concentrates on
the larger developments that drive the housing-production debate, and the city's full permit feed
reaches further down into the small-project tail. That's a limit of our reconstruction, not an error in
the city's filing.

## 4. We do **not** beat the city on totals — and here is exactly why, to the unit

The city's 4,514 is larger than our 3,395. The full **1,119-unit difference decomposes into accountable
causes that sum exactly** — and almost none of it is "different buildings":

| cause of the gap | units | what it actually is |
|---|---|---|
| **Parcel re-numbering (re-plats)** | **+607** | The city files under a parcel's *old* APN; our record re-points to the *current* APN after the lot was re-platted. Same buildings, different parcel numbers — a **join mismatch**, recovered as our parcel-lineage matching completes. |
| **Per-permit vs per-project granularity** | **+616** | The city itemizes **each permit/unit on a parcel as its own row** (e.g. three ADUs on one lot = three rows, each its own permit number; split lots = the parent parcel's children). Our model carries **one project per parcel** and *collapses* them. The city is **more granular here, and arguably more correct** — this is **our** under-count, not the city's over-count. |
| **Small-project / ADU tail** | **+49** | Real housing the city tracks and we don't (section 3). |
| **Per-project unit deltas** | **−110** | On matched developments, our unit counts net slightly *higher* than the city's. |
| **Omissions we caught** | **−43** | Completed units in our record absent from the city's (section 2). |
| **= net gap** | **1,119** | reconciles exactly |

The reading: **1,223 of the gap (607 + 616) is reconcilable modeling difference** — parcel-numbering
and per-permit-vs-per-project — that says nothing about how much housing was built. Only **49 units** is
a genuine coverage difference. On *actual production*, the two independent records are concordant.

### A claim we tested and threw out

We initially suspected the city's larger total came from **double-counting** — the same building
reported at multiple stages or in multiple years. **We checked it, and it's false.** The parcels with
multiple city rows have **distinct permit numbers** (three different building permits on one lot are
three different units, not one counted thrice) or are **split lots** (the city files the parent parcel;
we hold its children). That's the city being more granular — **our** model collapsing it — *not* the
city inflating. We mention this because the discipline cuts both ways: **the same scrutiny that caught
the city's omission also killed our most convenient claim against the city.** A number that doesn't
survive that check doesn't appear in this report.

## 5. The finding that matters for policy: affordability is invisible in the permit record

Here is the structural result. The city's APR populates the full **affordability matrix** — for **773
completed affordable units** it records the income tier (very-low / low / moderate) **and** whether each
is deed-restricted. **Our independent reconstruction records essentially none of it** — not because we
counted wrong, but because **affordability is not in the building-permit record at all.** It lives in
separate documents — density-bonus eligibility statements, regulatory agreements, recorded affordability
covenants — that the city holds but does not publish as structured data.

That asymmetry is the policy payload, made concrete:

> **Anyone working from Berkeley's public permit records — an independent analyst, a journalist, a member
> of the public — can reproduce *how much* housing got built, but *cannot* see *who it is for*. The
> affordability signal exists only in documents that aren't open data.**

This is the **transparency-ordinance argument with a number attached**, and it lines up with the
project's earlier "≈18% affordable capture" finding: if affordability tracking depended on **structured,
open** deed-restriction data instead of PDFs in a file room, an independent check on the city's
affordability claims would be *possible*. Today it isn't. That's a **data-access gap with a concrete
policy fix** — publish the affordability documents as data — not a flaw in anyone's arithmetic.

---

## What this is, and what it isn't

**It is:** an independent reconstruction from primary permit sources that **cross-validates** the city's
production count (695 matched), **audits** it (caught the 39-unit omission), **knows its own limits**
(the 49-unit ADU tail), accounts for **every unit** of the headline gap, and **isolates exactly where
the public record goes dark** (affordability).

**It isn't:** a claim that we're more accurate than the city (in raw totals the city is larger, and we
say why); and it isn't a claim that the city's numbers are inflated (we tested that and withdrew it).

**Quality bound — and why it improves:** the two largest pieces of the gap are *reconciliation* artifacts,
not real differences. The **607-unit re-plat chunk** shrinks toward zero as our parcel-lineage matching
finishes linking old-to-current APNs, and the **616-unit granularity chunk** shrinks as we model
multi-permit parcels at the permit level the city already uses. As both complete, our number and the
city's converge — the agreement on actual production gets *tighter*, and the affordability blind spot
remains the one finding that no amount of reconciliation can close, because the data simply isn't public.

*Reproducible: every figure is regenerated by `scripts/reconcile_apr_vs_city.py` (G1) against the
canonical v2 database and the mirrored city APR; the APR itself by `scripts/apr_hcd.py` / the Q1
notebook (HCD-schema-faithful, 69/69 columns). Point either at any v2 to re-run.*
