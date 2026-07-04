# Harvest vs the CPRA feed — what the +40–65% actually is (2026-07-03)

Diagnostic (Sept 2025, base B-permits): harvest **544**, CPRA feed **331**, overlap **330**
(feed-only: 1). The feed is a near-perfect SUBSET of the harvest; the harvest-only 214 include
**100 Finaled and 77 Issued real permits**, 21 with dwelling-related descriptions — among them
**B2025-03880 (detached backyard ADU, FINALED)** and **B2025-04273 (JADU legalization, Amnesty
Program)**.

## What this means

1. **The CPRA "BP Annual Permit Report" filters out real, finaled, unit-adding permits.** Not
   just trade permits — completed ADUs. The report's undocumented filters are a COVERAGE
   mechanism on our side of the audit.
2. **A root-cause candidate for the reconciliation's city-coverage rows.** The audit names units
   the city credits that our record lacked; some of those may be permits the feed simply never
   contained. TO CHECK: sample the named city-only rows against harvest presence (feed-era months
   are beyond the harvest window — the check runs on 2025-06+ rows or awaits the CPRA refresh).
   **→ RESOLVED 2026-07-03 (post-backfill triage): hypothesis CLOSED — the answer is NO.** With
   the full 2015–2025 universe in hand: city-APR tracking permits ∩ harvest-only = **0 rows,
   0 units**. Every B-permit the city ever credited units to WAS in our feed. The audit's
   city-coverage rows are NOT feed-filter artifacts; the reconciliation stands stronger.
   Full triage of the 13,721 harvest-only base permits (2018–2025): **8,608 Finaled — but only
   ~57 dwelling-related, and reading them, nearly all incidental** (solar on an ADU, water
   heaters, service upgrades); true unit-adding misses are rare singletons (B2025-03880 remains
   the specimen). The feed's filters excluded trades/minor permits, not housing production.
   **The real prize is different: 3,687 Closed-Expired applications** — the abandonment/attrition
   class, now enumerable for entitled-but-unbuilt.
3. **The harvest strictly supersedes the feed's universe** for the months both cover (330/331) —
   but NOT its depth: the feed carries submittal/issuance/finaled dates, units, valuation, ADU
   flag; the harvest carries file date + status + description. **Complements: harvest = the
   universe; CPRA = the fields.**
4. **JN-I rail #1 gains a clause**: the feed is survivors-only AND filtered — measured waits
   describe the report's subset, another reason its figures are bounds.
5. **CPRA Request 1's filter-clarification paragraph now has a specimen** (B2025-03880) — cite it
   if the city asks what we mean by "captures fewer records."

## Standing significance

Every downstream analysis that treated the CPRA feed as "the permit record" inherited its
filters. The harvest is the first instrument that measures the feed's completeness — the same
oracle-triangulation move we run on the city's APR, now pointed at our own primary source.
Nothing in the audited COUNT is invalidated (completions were verdict-driven per permit), but the
recall ceiling of the feed era is now a measured, named phenomenon rather than a suspicion.
