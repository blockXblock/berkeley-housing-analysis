# SESSION RESUME BRIEFING — Berkeley project

**Last updated: 2026-06-01**
**Supersedes:** (none — first version)
**Purpose:** The LIVING current-state pointer. Overwrite this file (update
the date line) whenever state materially changes. There should be exactly
ONE of these — always read the latest. Detailed historical records live in
the dated `docs/audit/2026-*_*.md` files this briefing points to.

---

## HOW TO USE THIS (for a resuming Claude or CC)
The compaction SUMMARY is lossy and has caused concrete errors. On resume:
1. Read THIS file first (high-signal corrections).
2. For details, read the transcript section (grep the topic — they're large):
   - /mnt/transcripts/2026-06-01-16-06-27-berkeley-storage-photos-v2-session.txt (current)
   - /mnt/transcripts/2026-05-31-20-21-02-berkeley-foundation-day-storage-v2-migration.txt (prior)
3. When in doubt, read the source rather than reconstruct from summary.
NOTE: This file is NOT auto-loaded by the chat compaction system — the user
pastes it or points to it; CC reads it from the repo. It is a briefing, not
an auto-trigger.

## HARD FACTS the summary flattens or gets wrong
1. **`is_uc_project` flag EXISTS and is populated in v2.** Group-quarters /
   UC student-housing exclusion is a CLEAN RULE, not a hand one-off: exclude
   `WHERE is_uc_project = true` from APR unit counts. 4 projects carry it:
   2400 Bowditch (750), 2556 Haste (556), 2200 Bancroft (550), 1950 Oxford
   (300) — ~2,156 beds-as-units in the explorer. RECONCILE: user's earlier
   note said ~5,250 beds across "4 major projects" — may be a different set
   or counts need fixing; the exclusion MECHANISM is solid regardless.

2. **The explorer (berkeleybuild.com) is ALREADY on v2** since commit 52b87c0
   (May 13). No cutover to do — the "stale site" premise was a wrong
   inference from script paths, corrected by inspecting the deployed
   artifact. The genuinely stale surface is the Fly.io DATASETTE
   (map.db/address_centric.db, March 30) — needs A8/D2 notebooks re-run from
   v2 + redeploy.

3. **Permit-misclassification fix = THE headline finding.** Minor alteration
   permits (bathroom window $690, solar, signs, washer/dryer) were ingested
   as BP/CO milestones, inflating completions. Fix = populate
   permit_classified_primary/subsidiary (event types 26/27, schema built for
   it). Final adjudicated classification: SUBSIDIARY 108 · PRIMARY 40 ·
   MANUAL-NO_DESC 30 keep · HOLD 13. demolish/demolition = HARD disqualifier.
   Snapshot: keep_snapshot_2026-06-01_pre-permit-fix.db.
   After permit fix: CY2024 -> 826 (excl 2352), CY2025 -> 497 (ref ~482).
   The 826->~708 CY2024 residual = the GROUP-QUARTERS exclusion (is_uc_project)
   — a SEPARATE clean fix, APPLY it (do not defer indefinitely).
   Detail: docs/audit/2026-05-31_permit_misclassification_survey.md.

4. **2352 Shattuck (id179, 237u) & 2440 Shattuck (id176, 40u) HELD pending
   Accela.** 2352 is the big swing: hold -> CY2024 1063; drop its "revised
   job card" -> 826. Verify via Accela.

5. **Accela = Claude in Chrome, TEXT extraction only, NO screenshots.**
   Portal aca-prod.accela.com/BERKELEY. Building search:
   .../Cap/CapHome.aspx?module=Building&TabName=Building. Drive search via JS
   __doPostBack('ctl00$PlaceHolderMain$btnNewSearch',''), read
   document.body.innerText. User logs in (never enter password). Use BOTH
   street number + street name fields. "Finaled" = CO-equivalent; multi-dept
   CofO stages appear in Processing Status.

## LIVE-SITE data-quality items (on the public map NOW)
- P1: 2328 Channing (id183) & 2330 Blake (id184) — units=0, lat=None,
  unmappable. Coords ARE in berkeley.db; 2330 Blake = 6 new ADUs.
- P1: 2138 Kittredge shows twice; id118 (66u, design-review per SFYIMBY) is
  authoritative; id113's "permitted" is a spurious $690 bathroom-window
  permit. Do NOT merge to 73u (corrected error).
- P2: ~104 Jan-1 placeholder dates display as real dates.
- P2: 6 negative processing_days (1701 San Pablo -3798).
- P3: 4 UC projects — ensure front-end LABELS them, not blends beds.

## STORAGE / PHOTOS (personal-data thread)
- Photo originals: ~90GB on Seagate (2011-2020) + iCloud (recent; iCloud
  Photos shows OFF — verify at iCloud.com). Local "main" libraries are
  optimized (near-empty originals/).
- Drives: all report SMART "Not Supported" (USB bridges); DriveDx needs a
  Recovery-mode kext approval — DECLINED as not worth it. Treat Seagate
  (~9yr, irreplaceable photos) as priority-migrate regardless of health.
- IN PROGRESS this session: copy Seagate photo libs -> new T7 (copy_seagate
  _photos.sh). Do NOT reformat old-T7 until photos copied to a modern drive.
- Next-disk sizing: run video_inventory.sh before buying (YouTube 4K source
  likely the biggest driver; 2TB may be too small). Plan primary+backup.
- Full plan: PHOTO_REBUILD_PLAN.md, NEXT_SESSION.md.

## DISCIPLINE
- Read-only / preview before any write; snapshot before destructive ops.
- COPY not move; verify before delete.
- Never carry forward /dev/diskN nodes — re-resolve (they drift).
- 7 audit docs committed AND pushed to dev (through 3a41b5e).

## WHY THIS FILE EXISTS
The lossy summary caused: (a) wrongly framing group-quarters as
un-fixable/defer when is_uc_project makes it a clean filter; (b) nearly
missing that the explorer was already on v2. This briefing is the corrective
layer on top of the summary. Keep it current; read the transcript for detail.
