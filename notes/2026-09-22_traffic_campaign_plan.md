---
title: "Campaign: from 22 pageviews/day to thousands"
date: 2026-09-22
type: plan
status: for-review
area: notes
---

# Getting thousands of views to berkeleybuild.com

Baseline, measured today: **~22 real pageviews/day** (`docs/audit/2026-09-22_traffic_baseline.md`).

## First, the honest arithmetic

Berkeley has ~125,000 residents. The population plausibly interested in housing politics —
people who attend meetings, read Berkeleyside, vote in council races — is maybe 10–20k.

So **"thousands of views/day, sustained" is not achievable and is not the goal.** What is
achievable, and what this plan targets:

| | now | target (90 days) |
|---|---|---|
| Daily floor | 22 | **60–100** |
| Spike events | none | **3 events of 1,000–5,000 views each** |
| External referrers that work | 1 (Reddit) | 4 (Reddit, press, list, Nextdoor) |
| Total 90-day views | ~2,000 | **12,000–20,000** |

That is "thousands of views." It comes from a small number of well-aimed hits, not from
posting more often.

## What the data says to do

Four findings from the baseline, each with a direct implication:

1. **Reddit works and points at a MAP, not the homepage.** → Lead with maps, and link
   deep, never to `/`.
2. **67% of traffic has no referrer** — email and messaging. → The SBS list (~1,900
   addresses) is the single biggest owned channel. Use it deliberately.
3. **Maps beat tools** (37 views vs 21). → The explorer and curriculum are credibility
   assets, not acquisition assets. Stop leading with them.
4. **The Mayor briefing is the biggest button and got 4 internal views.** → Button
   prominence does not create demand. A reason to click does.

**The mechanic that drives local sharing is "find your address."** Every high-performing
local data story works this way. Nothing on the site currently does it well.

---

## Wave 1 — The scoop: publish the map the City didn't

**This is the highest-leverage asset in the repo and it is currently sitting unanalysed.**

On 2026-09-21 CPRA **#26-2367** delivered Raimi + Associates' **parcel geodatabase** for the
Corridors Zoning Update — `data/raw/corridors/raimi_corridors.gdb/`, 8 layers, including
**`Opportunity_Sites` (258 parcels, 63 fields)** and `housing_element_sites` (382).

The City published **PDFs only**. There is no public interactive map, shapefile, or parcel
CSV (`docs/audit/2026-08-12_czu_zoning_extract.md`). **Nobody outside City Hall and the
consultant has seen this at parcel level.**

**The story:** *"The City hired a consultant for $600,000 to decide which Berkeley parcels
get upzoned. The consultant drew the map. The City published pictures of it. We obtained
the underlying file under the Public Records Act — here it is, parcel by parcel. Find your
address."*

**The build:** an address-search map at `/maps/corridors_opportunity_sites.html` — type an
address, see whether your parcel is designated, what the designation is, and what the
consultant recorded about it. Style it like the existing maps (they already work).

**Why it will travel:** it is a records scoop, it is personally relevant, it is map-shaped,
and it is *neutral* — publishing the city's own model, taking no position. That neutrality
is what makes it press-safe and what makes it credible to people who disagree with SBS.

**Before publishing — two gates:**
- **Analyze it first.** I have not opened the 63 fields. The story must be what the data
  actually says, not what we expect it to say. If the designations are mundane, say so.
- **Withhold the `rent_controlled` layer (1,098 parcels).** Publishing which specific
  parcels are rent-controlled is a targeting risk for tenants. The Opportunity Sites are a
  government planning designation and are squarely public interest; tenancy status is not.
  Different data, different answer.

---

## Wave 2 — The recurring hook: "is your block on it?"

Two existing assets already have the address mechanic latent in them:

- **`/maps/elmwood_hidden_units_map.html`** — 601 secondary-unit addresses. Reframe as
  *"Berkeley has thousands of homes nobody counted. Here's where."* Ties directly to the
  Elmwood argument (density is already happening residentially) without arguing it.
- **`/maps/bond_incidence.html`** — Measure U's $300M, parcel by parcel. **"What will the
  bond cost your house?"** with address search. This is the most shareable thing on the
  site and it is on the November ballot.

**Measure U is a hard deadline.** Ballots arrive early October. A parcel-level "what it
costs you" tool published in the first week of October, and only then, is worth more than
the same tool published in November.

---

## Wave 3 — The credibility story, for a bigger room

*"I rebuilt my city's housing pipeline from primary sources because the official numbers
were wrong."* 909 projects, 19 notebooks, every figure reproducible from the city's own
records, gated against timestamped baselines.

This is a Hacker News / civic-tech story, not a Berkeley story, and it reaches a different
and much larger audience. It also does something local coverage cannot: it makes the site
*authoritative* rather than *partisan*, which pays off in Waves 1 and 2.

Target: HN, `r/dataisbeautiful` (with the construction time-lapse as the visual),
`r/urbanplanning`, the Terner Center and Possibility Lab networks, and the Berkeley GSPP /
D-Lab lists. The curriculum is the hook — "rebuild it yourself" is the part that travels.

---

## Distribution, in order

For each wave, the same sequence. Order matters: press first, because press will not run a
story that is already on Reddit.

1. **Local press, 48-hour exclusive.** Berkeleyside first (they cover CZU), then Daily Cal
   (they interviewed you 2025-11-05), East Bay Times, SF Chronicle (ran the CZU fight
   2025-11-17). Pitch is three sentences: what the record shows, why it is new, and a link.
2. **r/berkeley** — the proven channel. Post the *map*, not the site. Title states the
   finding, not the brand. Answer every comment for the first six hours; that is what
   keeps a post alive.
3. **The SBS list (~1,900).** One email, one link, one sentence of why. See the caution
   below about framing.
4. **Nextdoor, per neighborhood** — Elmwood, Solano, North Shattuck, and your own. Highest
   conversion per impression of anything on this list, and you are already a member.
5. **The council candidates and commissioners.** They cite data in public meetings; a cited
   map is a durable referrer.
6. **YouTube** — a 60–90 second vertical cut of the relevant map or flyover, posted to
   @BuildBerkeleyNeighborhoods, linking to the deep page.

---

## The independence problem — read this before using the SBS list

You are simultaneously an SBS officer and the operator of a site whose authority rests on
being non-partisan. That is manageable, but only in one direction:

- **SBS links to berkeleybuild.com. berkeleybuild.com never argues SBS's case.**
- Keep advocacy copy off the site. This is also the argument against shipping the
  DFW-voice rewrite's thesis sentences (`notes/2026-09-22_dfw_voice_video_prose_trial.md`) —
  "It is most of the fight" is quotable against the site's independence.
- When press asks, state both roles plainly and first. Disclosed, it is fine. Discovered,
  it is the story.

The Wave 1 scoop is strongest precisely because it is *not* an argument: a public record
the City chose not to publish, published. That framing survives a hostile reading. An
advocacy framing does not.

---

## Measurement

Re-query with `source .env.cloudflare` (token expires **2026-10-22** — renew). Compare to
`docs/audit/2026-09-22_traffic_baseline.md`. Track per wave: peak day, 7-day average after
vs before, referrer mix, and which *page* they land on.

**Check ~2026-09-26 first:** the baseline predicts daily bandwidth falls ~90% (1.1 GB → ~100
MB) after today's deploy. That is a falsification test of the measurement setup itself — if
the prediction fails, fix the model before trusting any campaign numbers.

## Sequence

| when | what |
|---|---|
| this week | Analyze the Raimi geodatabase. Decide if Wave 1 has a story. |
| this week | Verify the bandwidth prediction. |
| by Oct 3 | **Measure U parcel tool live** — ballots arrive. Hard deadline. |
| early Oct | Wave 1 scoop: press exclusive → Reddit → list → Nextdoor. |
| mid Oct | Wave 3: curriculum / reproducibility story to HN + academic networks. |
| Nov | Election week: the pipeline numbers are the reference everyone needs. |

## First decision

**Open the geodatabase and find out whether the story is there.** Everything in Wave 1
depends on the answer, and nobody has looked.
