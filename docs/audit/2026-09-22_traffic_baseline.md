---
title: "berkeleybuild.com traffic baseline — 2026-09-22"
date: 2026-09-22
type: report
status: record
area: audit
---

# berkeleybuild.com traffic baseline (2026-09-22)

The first measurement of the site's audience. Recorded the day the homepage was rebuilt
(hero loop, shared legend, third-party requests removed) so later numbers have something
honest to compare against.

**Source:** Cloudflare GraphQL Analytics API, zone `5a4a9915b271b81d8b854e1d5667b90e`
(berkeleybuild.com, Free plan), account `0747adf3…57681`. Read-only token, expires 2026-10-22.
Query the same way with `source .env.cloudflare` (git-ignored; see `scripts/set_cf_token.sh`).

## The headline: ~22 real pageviews per day

| measure | window | total | per day |
|---|---|---|---|
| Zone requests | 31 d (Aug 23 – Sep 22) | 51,504 | 1,661 |
| Zone "pageViews" | 31 d | 5,437 | 175 |
| **Web Analytics pageviews (RUM)** | **8 d (Sep 15–22)** | **173** | **~22** |
| Bandwidth | 31 d | 34.4 GB | ~1.1 GB |

**Use the RUM number, not the zone number.** RUM counts only real browsers executing
JavaScript. The 8× gap is bots, and the country mix proves it: **Netherlands = 16.9% of
requests, 2,060 threats, 0.04 GB** — 8,688 requests that downloaded nothing. Belgium the
same (8.5%, 0.02 GB). 35% of zone pageviews carry an `Unknown` user-agent; GoogleBot,
BingBot and curl add ~4.4% more.

**The US is 47.3% of requests but 32.13 of 34.4 GB — 93% of all bytes.** Everyone else
consumes nothing, which is the signature of scanning rather than reading.

## Where the 173 real pageviews went (Sep 15–22)

| page | views | share |
|---|---|---|
| `/` | 92 | 53.2% |
| `/maps/berkeley_construction_timelapse.html` | 20 | 11.6% |
| `/berkeley2050/` | 14 | 8.1% |
| `/maps/bond_incidence.html` | 13 | 7.5% |
| `/explorer.html` | 9 | 5.2% |
| `/data-science-curriculum.html` | 8 | 4.6% |
| `/mayor-briefing-2026-07.html` | 4 | 2.3% |
| `/players.html` | 4 | 2.3% |
| everything else | 9 | 5.2% |

**Referrers:** direct / none **67.1%** · berkeleybuild.com (internal) 20.8% ·
**com.reddit.frontpage 6.4%** · google.com 1.7% · facebook.com 1.2% · gmail app 1.2% ·
reddit.com 1.2% · linkedin.com 0.6%.

**Devices:** desktop 60.7% · **mobile 30.6% · tablet 8.7%** (39.3% non-desktop).

## Four findings

1. **Reddit is the only external channel that works, and it points at a map.** 13 of the 17
   non-internal referred views came from Reddit, landing on the construction time-lapse —
   not the homepage. That map is the #2 page on the site.
2. **Two-thirds of traffic has no referrer.** Direct, bookmarked, or opened from email and
   messaging apps (which strip it). Consistent with a list-driven audience — SBS carries
   ~1,900 addresses. Search is negligible: Google sent 3 views in 8 days.
3. **Maps outperform tools.** Maps 37 views vs explorer + curriculum + players 21.
4. **The Mayor briefing is the biggest button on the page and got 4 views, all internal.**
   Nobody arrives for it.

## Video engagement is GOOD, contrary to first impression

The 10 flyovers have **114 lifetime YouTube views** (pulled 2026-09-22; nine uploaded
Sep 5–9, one Jun 9). Per day: UC Student Housing 1.23 · Bancroft 1.08 · University 1.00 ·
17-Largest 0.69 · Kennedy 0.65 · Telegraph 0.50 · June-Shattuck 0.33 · San Pablo 0.31 ·
Shattuck S→N 0.23 · Durant 0.15.

114 looks like failure until you divide by the real audience. The homepage takes ~12 views
a day; the videos take ~8 plays a day. **A large share of homepage visitors press play** —
and the page uses click-to-play, so every one is deliberate. The videos are not the weak
link. **Distribution is.**

## A falsifiable prediction (check ~2026-09-26)

Before today the homepage autoplayed **99.7 MB** below the fold. At ~12 homepage views/day
that predicts ~1.2 GB/day; observed was **1.1 GB/day**. So the two mp4s were essentially the
entire bandwidth bill.

**Prediction: daily bandwidth falls ~90%, to roughly 100 MB/day, within days of the
2026-09-22 deploy.** If it does not, this model is wrong and something else is consuming it.

## Caveats

- RUM has **no backfill** — Web Analytics data begins when it was enabled; there is no
  history before ~Sep 15.
- Free-plan zone analytics retention is short (~30 d). Snapshot before it rolls off.
- RUM misses visitors who block JavaScript, so ~22/day is a slight **floor**.
- YouTube view counts include plays on YouTube itself, not only site embeds.
