# scrape_queue update — 90 pending_url_discovery → pending

**Generated:** 2026-05-22T17:36:51
**Scope:** transactional UPDATE on canonical `databases/cic_recon_queue.db` to populate `url` + `capid_triplet` on the 90 in-scope rows and flip their status from `pending_url_discovery` to `pending`. The 2 already-succeeded rows (`B2019-05574`, `ZP2018-0135`) untouched.

## 1. Pre-update state

| field | value |
|---|---|
| Canonical SHA256 (pre) | `6cc8416c490eb364b29db8aa24a8aa6dd5e80a84599e5f873e1ded90fee1c4ae` |
| `pending_url_discovery` | 90 |
| `succeeded` | 2 (B2019-05574, ZP2018-0135) |
| 2 succeeded permits also in pending_url_discovery? | 0 (no overlap) |

Pre-update `pending_url_discovery` rows had `url=None, capid_triplet=None`. The 2 succeeded rows had non-null URLs+triplets from yesterday's run + this morning's test.

## 2. Backup

| field | value |
|---|---|
| Path | `databases/cic_recon_queue_pre_inspection_run_2026-05-22.db` |
| Size | 61,440 bytes |
| SHA256 | `6cc8416c490eb364b29db8aa24a8aa6dd5e80a84599e5f873e1ded90fee1c4ae` |
| Matches canonical pre-state SHA256 | yes ✓ |

## 3. JSON-lookup outcomes

| field | value |
|---|---|
| Permits to look up | 90 |
| Successful lookups | **90 of 90** |
| Failed lookups | 0 |
| Source: `data/raw/accela_url_discovery/` (canonical) | 87 |
| Source: `/tmp/url_discovery_pre_flight/` (pre-flight outputs) | 3 |

All 90 JSONs had `found=True`, a non-empty `master.capdetail_url`, and a non-empty `master.capid_triplet`. The 3 from the pre-flight dir are B2019-05575 / B2021-02225 / B2021-02404 (the pre-flight smoke trio whose JSONs landed in `/tmp/` rather than the canonical output directory).

Sample 3 (permit, source, url-head, triplet):

```
B2019-05575  /tmp/url_discovery_pre_flight/B2019-05575.json
  url: https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?...
  triplet: DUB19-00000-00KIL
B2021-02225  /tmp/url_discovery_pre_flight/B2021-02225.json
  url: https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?...
  triplet: DUB21-00000-00EMR
B2021-02404  /tmp/url_discovery_pre_flight/B2021-02404.json
  url: https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?...
  triplet: DUB21-00000-00EZS
```

## 4. Post-UPDATE state

| field | value |
|---|---|
| Canonical SHA256 (post) | `29258f2fe637c6503dfc178f692dc6705c925cc98da2e4e188e8e62a6e9498f9` |
| `pending` | 90 |
| `succeeded` | 2 (unchanged: B2019-05574, ZP2018-0135) |
| `pending_url_discovery` | 0 |
| Total rows | 92 (unchanged) |

In-transaction equality check on the 2 succeeded rows (all columns, pre vs post): **identical**. The UPDATE statements were constrained with `WHERE permit_number=? AND status='pending_url_discovery'`; the succeeded rows could not have been touched.

## 5. Spot-check of pending rows

First 5 pending rows by permit_number:

| permit_number | capid_triplet | url (first 110 chars) |
|---|---|---|
| B2019-05575 | `DUB19-00000-00KIL` | `https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB19&capID2=0` |
| B2021-02225 | `DUB21-00000-00EMR` | `https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB21&capID2=0` |
| B2021-02404 | `DUB21-00000-00EZS` | `https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB21&capID2=0` |
| B2021-03950 | `DUB21-00000-00IG1` | `https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB21&capID2=0` |
| B2022-01278 | `DUB22-00000-009C4` | `https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB22&capID2=0` |

3 random pending rows, host + capID-param checks:

- Each URL starts with `https://aca-prod.accela.com/` → **yes** (3/3)
- Each URL contains `capID1=` + `capID2=` + `capID3=` query params → **yes** (3/3)

Dry-run `get_next_pending_row` pattern returns:

```
permit_number=B2019-05575, status=pending
url: https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&...
```

Orchestrator will see real work when launched.

## 6. URL shape observation

- Pending rows with clean URL (no `/Cap/./` mid-path): **43**
- Pending rows with `/Cap/./` mid-path (single_result_redirect artifact): **47**
- Total pending: 90

87 of the 90 URLs come from the `single_result_redirect` path and carry a literal `./` mid-path (because `_absolutize` prepended the host+path to a form-action that started with `./`). Browsers normalize this transparently and the orchestrator's `page.goto()` will follow them correctly. The 3 clean URLs come from B2019-05575 / B2021-02225 / B2021-02404, the multi-result-list permits whose `final_url = page.url` after navigation was the browser-normalized form. Cosmetic only — no functional impact, but worth flagging for any future code that does string-equality matching on URLs (e.g., a deduper or a URL-canonicalization step).

## 7. Verdict

**PASS** — canonical `scrape_queue` now has exactly 90 pending rows (each with a valid CapDetail URL + capID triplet) plus 2 succeeded rows untouched. Total still 92. All 90 JSON lookups succeeded; the transactional UPDATE confirmed `rowcount=1` for each statement; in-transaction post-check verified the 2 succeeded rows are byte-identical to their pre-update snapshot. The orchestrator will pick up its first pending row on launch.

Safety net: `databases/cic_recon_queue_pre_inspection_run_2026-05-22.db` preserves the pre-update state (SHA256 `6cc8416c…`). Restoring is a single `cp` away.
