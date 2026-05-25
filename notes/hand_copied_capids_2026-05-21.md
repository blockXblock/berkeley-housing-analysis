# Hand-copied Accela capID triplets — 2026-05-21 browser verification

**Generated:** 2026-05-21T17:15:03
**Source:** Manual browser verification during prior chat session
"Building the Berkeley Housing orchestrator from design sketch"
(last activity 2026-05-21 evening).

## Overview

Three Accela CapDetail master-record triplets were hand-copied during
browser verification of the master-and-suffix pattern. "Master" means
the record whose displayed permit_number exactly matches the search
query, with no `-REV##` or `-DEF##` suffix. Subsidiary records (REV /
DEF revisions and deferred-submittal entries) sit underneath each master.

These three triplets are the only fully-verified data points from the
previous session's verification pass and should be used as known-good
anchors when the URL-discovery scraper is built and validated.

All three masters share these properties:
- Status: **Finaled**
- Module: **Building**
- capID2 (the middle component): **00000** in every case observed
- capID1 prefix: **DUB** + 2-digit year (DUB19, DUB21, …) — matches the
  permit_number's year fragment

## The 3 verified triplets

| permit_number | address | total_records | master_capid_triplet | status |
|---|---|---|---|---|
| B2019-05575 | 2352 Shattuck Ave | 3 | DUB19-00000-00KIL | Finaled |
| B2021-02225 | 2650 TELEGRAPH Ave | 10 | DUB21-00000-00EMR | Finaled |
| B2021-02404 | 2000 DWIGHT Way | 20 | DUB21-00000-00EZS | Finaled |

(`address` for B2019-05575 — "2352 Shattuck Ave" — was resolved by a
read-only lookup in `databases/berkeley_housing_v2.db`; it was not
recorded in the prior chat. Project id 179. Same project as B2019-05574,
the inspection-scraper POC permit.)

## Sub-record counts

| permit_number | total | breakdown |
|---|---|---|
| B2019-05575 | 3 | 1 master + 2 subs |
| B2021-02225 | 10 | 1 master + 9 subs |
| B2021-02404 | 20 | 1 master + 19 subs (REV01–REV19, DEF01–DEF17) |

## Notes & open questions

- **B2019-05574** (note the `-05574`, distinct from `-05575` above) was
  the inspection-scraper POC permit per the previous session — 557
  inspections retrieved. Its capID triplet was NOT recorded in chat;
  it needs lookup or rediscovery (likely `DUB19-00000-00???`).
  B2019-05574 lives at the same address (2352 Shattuck Ave, project 179).
- The session opener for the current session says "URL discovery scraper:
  browser verification 4 of 5 test permits done." This document captures
  the 3 fully-verified entries. A 4th may exist but is not findable from
  chat history, so it is not recorded here.
- All three triplets are anchors only. They should be re-verified by the
  scraper on first build to confirm the master-vs-subsidiary disambiguation
  logic.

## How to reconstruct the CapDetail URL from a triplet

Template (verify exact host/path during scraper build — this is the
commonly-observed Accela Citizen Access form; subject to change):

```
https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1={capID1}&capID2={capID2}&capID3={capID3}
```

Worked example for B2021-02225 (master triplet `DUB21-00000-00EMR`):

```
https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB21&capID2=00000&capID3=00EMR
```

Reminder: do NOT treat this URL template as canonical until confirmed
against a live page. The host (`aca-prod.accela.com` vs an alternate),
the path (`/BERKELEY/...`), and the query-string parameter casing all
need empirical verification by the URL-discovery scraper.

## Addendum (2026-05-21 evening) — B2019-05574 added

A 4th master capID surfaced from the cic_recon_queue.db's existing
queue row (id=1, from the 2026-05-20 inspection scraper POC). This
is the sibling permit to B2019-05575 — both for project 179 (2352
Shattuck Ave).

| permit_number | master capID triplet | total records | status | notes |
|---|---|---|---|---|
| B2019-05574 | DUB19-00000-00KIJ | (not yet counted) | scraped 2026-05-21 (557 inspections) | sibling to B2019-05575 |

CapID3 components differ by one character (00KIJ vs 00KIL),
consistent with adjacent records filed close in time within the
same project.

The orchestrator end-to-end test re-ran B2019-05574 on 2026-05-21
at 17:48-17:53 PT, producing 557 unique inspections (exact match
to the 2026-05-20 baseline). Output JSON at
data/raw/accela_inspections/B2019-05574.json (117 KB).
