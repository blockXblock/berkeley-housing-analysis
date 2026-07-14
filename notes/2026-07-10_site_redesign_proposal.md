# berkeleybuild.com redesign proposal — "One record, many views"

*Drafted 2026-07-10 in response to John's direction: archive the stale v1-era home text
(DONE — `technical-archive-2026.html`), regenerate flybys from current KML, new intro,
position the Mayor's Briefing, add THE PLAYERS view, add PIPELINE-STATE diagrams with
policy levers. Status: proposal for John's review; build order at bottom.*

## The organizing idea

The site's asset is **one independently verified record** (every permit 2015–2026, audited
against the state filing to ±130 units). The redesign makes the home page a **hub of
views**, each answering one civic question, each visibly drawing on the same record.
The intro says this in three sentences; every view card repeats its own question.

## Home page (top → bottom)

1. **New intro block** (replaces nothing — new): *"Berkeley argues about housing from
   anecdotes. This site is the alternative: an independent, permit-level reconstruction of
   the city's entire housing pipeline — 82,065 records, 2015–2026, audited row-by-row
   against the state filing, updated on a schedule, and open for anyone to rebuild. Below,
   the same record from seven angles."* (Subhead keeps the grow-and-innovate sentence.)
2. **The view grid** (cards, each: question → view → provenance line):
   - 🏛 **The Policy View — Mayor's Briefing.** *"What does the record say works?"* Why it
     matters: the distilled argument for decision-makers — 18 slides, every number traced,
     honesty tags on every model. This is the view that turns data into asks.
   - 🔍 **The Project View — Explorer.** *"What's happening at this address?"* 895 projects,
     dates, values, RHNA bar.
   - 🗺 **The Skyline View — Maps & Flybys.** *"What will Berkeley look like?"* Videos +
     Google Earth (regenerated from the canonical `docs/geometry.kml`).
   - 🕸 **The Players View — NEW.** *"Who builds Berkeley?"* Network of developers,
     architects, builders, owners — who works with whom, who repeats, who pairs.
   - ⏳ **The Pipeline-State View — NEW.** *"Where is every project stuck right now?"*
     State diagrams + the policy levers that could move them.
   - ⚖️ **The Audit View.** *"Can we trust any of this?"* Ours vs the city's, every row named.
   - 🎓 **The Curriculum View.** *"Could I rebuild this myself?"* 19 notebooks, JN00→JN8.
3. **Videos** (kept, regenerated — see work plan), **Reading**, **Google Earth card**.
4. **Archive card** (done): the v1-era text + notebook index, banner'd pending reverification.

## The two NEW views

### The Players (docs/players.html)
- **Have now (v2):** developer / architect / owner per project (export already carries
  21 developers, 11 architects, 27 owners + per-project links). Phase 1 = a bipartite
  network: player ↔ project, sized by units, colored by role; derived from
  `v_projects_flat` + the players tables, rendered as force-directed SVG (self-contained,
  no CDN) or pre-laid-out with networkx → SVG. Side panel: each player's project list,
  total units, stage mix (who's building vs who's waiting).
- **Honesty rails:** coverage is majors-heavy (small permits carry no player fields);
  name normalization needed (LLC variants — "the Acheson lesson" for names); "who works
  with whom" = co-occurrence on a project, not contract knowledge.
- **NOT yet in the record: investors and lenders.** Construction lenders live on deeds of
  trust at the County Recorder; investors in LLC filings (CA SOS). Both are acquirable,
  neither is loaded. Phase 2 acquisition — until then the view says so explicitly.

### The Pipeline State (docs/pipeline-state.html)
- **The state machine, whole-city:** every tracked project binned by furthest hard
  evidence (the JN-K discipline): (1) applied, not yet entitled → (2) entitled, no BP
  (the waiting room — 22 majors / 4,777u today) → (3) BP issued, no construction
  activity (the stalled register — JN-J; "activity" = inspection events, we harvest
  them) → (4) under construction → (5) complete. Rendered as the Sankey + per-state
  registers with named projects and time-in-state.
- **The policy-lever panel:** for each stalled state, the lever that addresses its
  *documented* cause and the units it touches — e.g. waiting-room levers (entitlement
  extension, fee deferral at BP, by-right conversion for entitled projects) sized
  against the 4,777 waiting units. **All lever effects are MODELED and tagged** — we can
  say "this lever touches N units in this state" from the record; we cannot promise
  behavior. Ties directly to the financial deck work (fee CPRA) as it lands.
- Derivation: one generator script reading v2/v4 (JN-K's populations), re-runnable, so
  the page updates with the record.

## Work plan (order + dependencies)

| # | item | depends on | who |
|---|------|-----------|-----|
| 1 | Archive old home text | — | DONE 2026-07-10 |
| 2 | New intro + view-grid home | copy approval | CC, 1 session |
| 3 | Pipeline-State view v1 (states + registers + Sankey) | JN-K populations (have) | CC, 1–2 sessions |
| 4 | Players view v1 (bipartite network) | name normalization pass | CC, 1–2 sessions |
| 5 | KML regeneration from current DB | tour-package generator (have) | CC |
| 6 | Flyby re-render + YouTube swap | #5 + Google Earth Studio | John/CIC (GES not scriptable headless) |
| 7 | Policy-lever panel numbers | #3 + fee CPRA (for $ levers) | CC after CPRA |
| 8 | Reverify archive text → fold back or retire | v4 APR reconciliation (have) | CC + John review |
| 9 | Players phase 2: lenders/investors | County Recorder + SOS acquisition | acquisition project |

## Design notes
- Views share the deck's visual language (navy/gold; derived/modeled/preliminary tags).
- Every view page ends with the same footer: source line + "rebuild this yourself" link.
- No CDN dependencies anywhere (self-contained SVG/JS, as the deck).
