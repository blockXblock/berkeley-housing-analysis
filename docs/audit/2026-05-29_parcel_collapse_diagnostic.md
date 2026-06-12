# Parcel-Collapse Diagnostic — 2026-05-29

## Headline

D5's master-selection logic in Cell 5 was collapsing parcels with 
multiple independent New-construction permits to a single master,
dropping sibling permits and their units. Phase A investigation 
identified 14 affected parcels across 8 CY years contributing
22 dropped BP units total. The fix landed today (companion 
commits).

## The bug

D5's Cell 5 grouped permits by APN and selected one master per 
parcel. Siblings — independent New-construction permits for 
separate structures on the same parcel — were demoted to subs 
along with REV/DEF children. Their UnitsAdded was dropped entirely.

The bug surfaced during yesterday's bijection construction (D7), 
where 20 HCD CY 2024 rows for multi-structure parcels appeared in 
the "multi_row_same_apn" residual classification. Initial estimate 
of "28 BP units lost" was higher than the actual D5-fixable 
universe.

## Phase A investigation

Two key findings reshaped the fix design:

**Finding 1 — fixable universe is smaller than initially estimated.**
Of 20 HCD multi_row rows spanning 16 APNs:
- 4 APNs are Case 1 (D5-fixable): D5 has multiple independent 
  New-with-units permits that the collapse logic drops
- 12 APNs are Case 2 (NOT D5-fixable): CPRA only released ≤1 
  New-with-units permit; HCD recorded finer per-unit granularity 
  that D5 has no source evidence for

The Case 2 residual is a CPRA-source limitation, not a D5 bug. 
Only Case 1 is addressable in the pipeline.

**Finding 2 — same-year gating is essential.**
Cross-year application of the sibling rule produced two confirmed 
false positives:
- 2538 Durant (APN 055 187602101): an 83-unit building permit 
  (2024) and a "Temporary Power Service... tower crane" permit 
  (2025) that inherited UnitsAdded=83 from the building it 
  supports. Treating these as siblings would add +83 phantom units.
- 1182 Euclid (APN 061 255000300): a residence permit (2023) and 
  a "Replacement of existing garage with new garage" permit (2024) 
  carrying UnitsAdded=1. The garage is not a dwelling.

Same-year gating eliminates both false positives by construction. 
The Durant pattern is a documented CPRA data-quality artifact: 
non-housing permits sometimes carry UnitsAdded values inherited 
from their associated building permit.

## The 14-parcel population

Same-year sibling parcels with ≥2 independent New-with-units permits, 
verified across all 8 CY years.

CY 2018: 2 parcels (2212 Tenth Building A/B; 1446 Fifth, 4 houses)
CY 2019: 2 parcels (809 Folger Buildings A-D; 1444 Fifth, 4 houses)
CY 2020: 1 parcel (1811 Sixty-Third, SFD + Duplex with explicit 
  cross-reference in WorkDescription)
CY 2022: 1 parcel (776 Page, two "new three-story house" permits 
  same-day, text-ambiguous but structurally adjacent to multi-house 
  developer lots — included per discussion; bijection validation 
  confirmed correctness in this commit's D7 output)
CY 2024: 4 parcels (1200 Dwight Front/Rear; 2421 Fifth main+Building B; 
  805 Jones 3 duplexes; 98 Avenida SFR+detached ADU)
CY 2025: 4 parcels (1330 Haskell front/rear; 1340 Haskell front/rear; 
  2708 Prince Duplex+detached ADU; 1614 Sixth Building A/B)

All 14 classified as explicit_sibling via WorkDescription text 
patterns (Building A/B/C, distinct sub-addresses, front/rear with 
cross-references, explicit "See B202X-XXXXX" pointers).

## The fix

Added a gated sibling branch in Cell 5 before the original 
single-master logic:

```python
for apn, group in parcels:
    is_child = (permit numbers containing "-REV" or "-DEF")
    sib_all = group filtered to Work Type="New" + UnitsAdded>0 + not_child
    # same-year gating
    sib_all["__iy"] = pd.to_datetime(sib_all["Issuance Date"]).dt.year
    sibling_years = years where >=2 same-year siblings exist
    if sibling_years:
        # promote each sibling to its own master row
        for _, master in siblings[in sibling_years].iterrows():
            projects.append(...)
    else:
        # original single-master logic, unchanged
```

Same-year gating is the load-bearing detail. Cross-year application 
surfaces Durant-pattern false positives.

## Impact

Total BP delta across all years: +22 (matches Phase A exactly).
Per-year: see commit message in the companion fix commit.

CO totals shift only when sibling permits finaled in the same year 
they were issued. BP totals shift in the year siblings were issued.

One unit-neutral de-match in CY 2024: HCD row 1301 (1614 Sixth) 
previously matched a re-wire alteration permit (B2023-05397-REV01, 
Work Type=Alteration, UnitsAdded=2/UnitsRemoved=2, net 0 units). 
With the fix, 1614 Sixth's two 2025 SFR permits become masters; 
the 2024 re-wire alteration no longer appears as a master and its 
cosmetic match to HCD row 1301 drops. Unit impact: 0. Arguably a 
correction — an HCD housing entry shouldn't have been matched to 
a non-housing alteration.

## Deferred work

**Cross-year siblings (~5 units across 3 parcels).** Carleton 
(2u 2024 + 1u 2025), 2310 Eighth (1u 2023 + 1u 2024), 2411 Sixth 
(1u 2023 + 1u 2024). All are genuine siblings per text analysis 
but cross-year application is too contaminated (Durant/Euclid 
pattern) to bulk-include. Per-row vetting workstream.

**CPRA data quality pattern documented.** The Durant case revealed 
that non-housing permits in Berkeley's Accela export sometimes 
carry UnitsAdded values inherited from associated building permits. 
This is a CPRA-side quirk relevant to Causes 2 and 3 fix design — 
non-housing permits flagged ADU=Yes may carry inflated UnitsAdded 
that the Work Type filter needs to handle.

## Companion artifacts

- D5 Cell 5 source change: fix(d5) commit
- 8-year reconciliation ledger regeneration: feat(d7) commit
- Cell 12 regression test baseline updated to match post-fix state
