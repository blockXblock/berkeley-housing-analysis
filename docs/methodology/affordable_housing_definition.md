# What counts as "affordable" housing

**Decided by John, 2026-10-23.** Used for the affordability ledger (`corrections/v4/affordability_rulings.csv`), the
affordable-projects table, map and flyby, and any count of affordable units we publish.

## The definition

A unit is **affordable** when a **legally binding restriction** caps BOTH its rent (or sale price) AND its occupant's
income at **no more than 120% of Area Median Income (AMI)** for a stated term. The restriction is a recorded regulatory
agreement or deed restriction, or a condition of approval.

**Income tier = the statutory cutoff** (California Health & Safety Code), applied to the AMI percentage a document states:

| Tier | AMI | Statute |
|---|---|---|
| Extremely low (ELI) | ≤ 30% | H&S 50106 |
| Very low (VLI) | ≤ 50% | H&S 50105 |
| Low (LI) | ≤ 80% | H&S 50079.5 |
| Moderate (MOD) | ≤ 120% | H&S 50093 |

A unit at 60% AMI is **low**, not very low, even when a plan sheet, density-bonus table or the City's APR groups it with
very low (2001 Ashby: the APR's 80 VLI / 6 LI is 25 ELI / 28 VLI / 33 LI under these cutoffs).

**Strength of evidence, recorded separately:** committed at approval (conditions) → recorded (a regulatory agreement at
the County Recorder) → in service (occupied).

## Not counted as affordable units
- ADUs the City's APR places in lower tiers by assumption (non-deed-restricted).
- Rent-controlled units: rent stabilization limits increases, not who may live there.
- "Naturally affordable" market-rate units.
- UC student housing (outside City permitting; counted in beds).

## Tracked, but as money, not units: the affordable housing fee
A project that pays the City's fee instead of (or as well as) providing units on site — the **Affordable Housing
Mitigation Fee (AHMF)**, which applied to projects with a building permit or preliminary application on or before
2023-04-01, then the **Inclusionary Housing Ordinance in-lieu fee (IHO, BMC 23.328)** — is recorded with its project,
developer, ordinance, fee amount and status (estimated / final / paid), so that we can:
1. follow the fee-versus-units trend over time, and
2. trace whether the money reached affordable units elsewhere (fees go to the Housing Trust Fund, which funds nonprofit
   100%-affordable buildings; the use side is `corrections/v4/funding_ledger.csv`).

Fee figures come from the City's own records (the HHCS Inclusionary Housing Program annual reports to Council,
conditions of approval, payment records), never from the HCD APR, which stays a verification target.
