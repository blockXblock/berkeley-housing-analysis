---
title: "Berkeley Pole/Infrastructure Project — kickoff prompt (\"Poley and Pipey and Stretch\")"
date: 2026-08-28
type: design
status: record
area: notes
---

# Berkeley Pole/Infrastructure Project — kickoff prompt ("Poley and Pipey and Stretch")

*(Paste the block below into a new session to start the pole project. It carries forward the
research already done on 2026-08-28 so the new session doesn't re-derive it.)*

---

I'm starting a new project: **mapping and telling the story of Berkeley's above- and below-ground
infrastructure** — utility poles, the wires between them, the pipes below, and (a new, central
requirement) **the transformers on the poles.** It has two intertwined halves:

**A. THE DATA / MAP.** Locate and count, at parcel/street resolution across Berkeley:
- every **utility pole** (power/telephone) and every **city streetlight** — two distinct populations;
- the **spans/wires** stretching pole-to-pole (the network topology);
- the **pipes** below — water (EBMUD), sanitary sewer + storm drains (City), gas (PG&E);
- **a transformer count for every pole** — which poles carry distribution transformers, how many,
  and where. This is the load-bearing new ask (see why below).
Build toward a block-by-block map of it all, in the spirit of berkeleybuild.com.

**B. THE CARTOON.** A public-facing cartoon series, **"Poley and Pipey and Stretch"**, with cute
characters representing the infrastructure — **Poley** (a utility pole), **Pipey** (a pipe), and
**Stretch** (the wire/span between poles) — to make this legible and charming to the public and to
dramatize the infrastructure-security story. (Consider a fourth character for the transformer — it's
the star of the security plot; e.g., a nervous oil-filled transformer who needs its oil changed.)

**WHY TRANSFORMERS ARE CENTRAL — the "security of infrastructure" story.** Berkeley sits on thousands
of pole-mounted distribution transformers, most decades old. Their **oil** is the problem on three
fronts: (1) **fire** — mineral-oil transformers can fail and ignite, a serious risk in a
wildfire-prone hillside city; (2) **environmental/toxics** — older units may hold **PCB-contaminated
oil** (EPA/TSCA-regulated), and any unit can leak; (3) **grid resilience** — aging transformers are a
reliability and hardening liability. **Replacing or retrofilling the oil in thousands of transformers
is a major infrastructure-security project**, and it starts with knowing where every transformer is
and what's in it. That inventory is the data spine of this project.

## WHAT'S ALREADY BEEN FOUND (2026-08-28 — don't re-derive; verify and build on)

**Two pole populations, only one publicly downloadable:**
- **City-owned streetlights = exactly 7,969**, with precise locations, on Berkeley's own ArcGIS:
  `https://gis.cityofberkeley.info/arcgis/rest/services` — layers `PublicWorks/PubWorks/MapServer/26`
  and `Public/Portal_CommSvcs/MapServer/0` (both report 7,969). **Downloadable now** via the ArcGIS
  REST `query` endpoint (`where=1=1&outFields=*&f=geojson`). START HERE — it's the immediate win.
- **Utility poles (power/telephone) = no public count.** They live in **PG&E's Joint Use Map Portal
  (JUMP)**, the authoritative pole-location database — but **JUMP access is restricted to utilities
  and communication infrastructure providers**, not the public. OpenStreetMap has only **88** Berkeley
  poles mapped (volunteer, uselessly incomplete). The real utility-pole count is likely the same order
  as the streetlights but thinner where downtown/parts of the hills are undergrounded.

**Ownership / who maintains & replaces:** Most Berkeley utility poles are **jointly owned by PG&E
(power, top of pole) and AT&T (telephone, below)** under the **Northern California Joint Pole
Agreement (NCJPA)**. The designated owner (usually PG&E) maintains and replaces its poles; the joint
association coordinates cost-sharing. The **City separately owns/maintains the 7,969 streetlights.**

**How new attachers (e.g., Sonic fiber) get on the poles:** the **pole-attachment regime** — apply to
the owner (PG&E, or AT&T which manages the telecom space), pay fees, do **"make-ready" engineering**
(that survey enumerates every attached pole, but it's the attacher's proprietary data). FCC §224 +
**CPUC** regulate it; the CPUC imposed a **45-day "shot clock"** on pole owners after Sonic's access
was contested (PG&E/AT&T/Comcast restricted Sonic; restraint-of-trade complaints).

**Other Berkeley GIS layers already spotted** (same ArcGIS server, all queryable): sanitary-sewer
manholes, storm-sewer manholes (`PublicWorks/PubWorks`), **Underground Utility Districts**
(`Planning/Accela` + `PublicWorks/PubWorks`) — the last tells you *where there are no poles* (utilities
undergrounded), which bounds the overhead network.

## DATA-ACQUISITION PLAN (in order)

1. **Now (public):** pull the 7,969 city streetlights (locations + attributes) from Berkeley ArcGIS;
   enumerate and pull every relevant Berkeley GIS layer (streetlights, sewer/storm manholes, underground
   utility districts, any conduit/duct layers) with counts. Reuse the ArcGIS-sweep pattern from the
   housing project (walk `/rest/services`, all folders, `returnCountOnly`, then `f=geojson`).
2. **Utility poles + transformers (records request):** the authoritative inventory is in **PG&E's JUMP /
   distribution asset GIS** and the **CPUC's pole & conduit databases** (the CPUC has been building
   statewide pole/conduit datasets). Draft a **CPRA/CPUC data request** (and/or PG&E data request) for:
   pole locations, joint-pole ownership, and **the distribution-transformer inventory (location per pole,
   count, kVA, install year, oil type / PCB status)**. Note JUMP itself won't open to the public — go via
   PG&E data request and the CPUC.
3. **Transformer-specific leads to chase:** **CPUC General Order 165** (mandated inspection records for
   distribution facilities incl. transformers); **PG&E's Wildfire Mitigation Plan (WMP)** filings with the
   **Office of Energy Infrastructure Safety (OEIS)** and CPUC (public; contain equipment counts + risk on
   transformers); **EPA / TSCA PCB** records for PCB-containing transformers; PG&E's asset-management and
   grid-hardening filings. Most residential poles carry **0–1** transformers (they sit at intervals serving
   clusters; three-phase locations have banks of 3), so "transformer count per pole" is really "which poles
   have them + how many + what's in them."
4. **Pipes (Pipey):** City sewer/storm layers are in Berkeley GIS (above). **EBMUD water** is private
   customer/asset data (aggregate only); **PG&E gas** distribution mains are in PG&E GIS (restricted).
   Map what's public (city sewer/storm), request the rest.

## THE CARTOON (Poley and Pipey and Stretch)

Purpose: turn a dry infrastructure inventory into a charming, sharable public-education / civic-advocacy
series — the same audience as berkeleybuild.com, but for the stuff overhead and underfoot. Characters:
- **Poley** — a utility pole; weathered, holds everyone up, quietly overloaded with attachments.
- **Pipey** — a pipe; underground, carries the flow, worries about leaks and age.
- **Stretch** — the wire/span between poles; literally stretched thin, connects everyone.
- *(suggested)* a **transformer** character — oil-filled, aging, the security-plot protagonist whose
  "oil change" is the mission; ties the cute series to the real transformer-oil-replacement story.
Deliverables to consider: character designs, short explainer strips ("why does Poley's transformer need
new oil?"), and eventually pairing the strips to the real map (click a block → meet its poles).

## PROJECT CONVENTIONS
Runs in `~/berkeley-data` (has the ArcGIS-sweep tooling, `.venv`, and the primary-source discipline).
Same working rules as the housing project: **primary sources, verify artifacts (count rows, check the
actual layer) before asserting, no fabricated counts** — where a number isn't public, say so and name the
records request that would get it. This is exploratory/read-only research to start; nothing gated yet.

**First actions:** (1) pull the 7,969 streetlights and map them; (2) full sweep + counts of every
Berkeley GIS pole/pipe/utility layer; (3) research the transformer-inventory + PCB/oil sources above and
report what's public vs records-request-only; (4) draft the PG&E/CPUC data request for the utility-pole
and transformer inventory. Then we scope the cartoon.
