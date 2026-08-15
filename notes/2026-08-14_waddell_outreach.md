# Outreach draft — Paul Waddell (UrbanSim / UC Berkeley CED)

**Status:** DRAFT for John to review, personalize, and send himself (sending is John's call, not CC's).
Contact: Paul Waddell, Prof. of City & Regional Planning, UC Berkeley CED; founder, UrbanSim Inc.
(find current email via CED directory / UrbanSim Inc.). Tone: peer, specific, reciprocal — not a data beg.

---

**Subject:** Open Berkeley housing-data project — a feasibility question your pro-forma answers

Professor Waddell,

I'm an independent researcher building an open, primary-sourced reconstruction of Berkeley's housing
pipeline — entitlement → permit → occupancy — from Alameda assessor + CPRA permit data, published as an
interactive explorer (berkeleybuild.com) and a Datasette dataset. It's a civic-data project, not
commercial.

I've been studying UrbanSim closely, and I'd value a short conversation. Three specific things:

**1. The feasibility question — the reason I'm writing.** I'm analyzing a live Berkeley policy debate:
whether raising the height/FAR limit on the ~5-acre Elmwood *commercial* strip would actually produce
housing, or whether the district densifies residentially regardless (ADUs, conversions, Middle Housing).
This is exactly what your `SqFtProForma` / `developer` model answers. I've reimplemented the pro-forma
method transparently (openly, for teaching — cited to UDST/developer, BSD-3) and run a baseline-vs-upzone
pass. The machinery works; the result is **entirely calibration-bound** — and that's my ask:

**2. Would you share (or point me to) your Bay Area calibration** — construction costs by structure type,
rents by use, cap rate, land-acquisition assumptions — the parameters your model already carries for
exactly this region? Even directional values would move my Elmwood analysis from "method demo" to
defensible. I'd equally welcome a critique of my calibration approach.

**3. Your assessor → building-attributes pipeline.** You've solved the problem I'm grinding on — turning
messy county assessor records into reliable building attributes (year built, sqft, units, type). If any
of that (or the building-type/land-use classification vocabulary) is shareable, it would save me
reinventing it.

**In return** — and I mean this as a genuine exchange — I've assembled some things your models could use as
ground truth: a primary-source ADU / "ghost unit" inventory (unpermitted backyard conversions the assessor,
permits, and licenses all miss), a corrected build-date layer from the City landmark list, and a
parcel-level structure-history model. All open. Happy to share data, or to have a student in your lab work
with it.

Would you have 30 minutes in the coming weeks? I can send the Elmwood feasibility notebook ahead of time so
the conversation is concrete.

With appreciation for UrbanSim and for keeping the core open,
John Gage
[contact]

---

## Why these three asks (CC notes for John, not part of the email)
- **Ask #1/#2 (feasibility + calibration) is the crown jewel:** his model is *built* to answer the Elmwood
  upzoning question, and calibration is the one thing we can't derive from open data — see JN-Feasibility
  Step 10. If his model shows the strip won't redevelop even upzoned (occupied retail + high land cost)
  while densification continues elsewhere, that's decisive quantitative backing for the op-ed, from the
  field's authority.
- **Ask #3** offloads our single hardest data-cleaning problem onto someone who solved it.
- **Reciprocity is real, not framing:** our ghost-unit / ADU ground truth is novel primary-source data his
  regional model genuinely lacks — frame it as mutual so it's a collaboration, not extraction.
- **Do NOT lead with a request for the gated regional parcel data** (it's MTC/AWS-restricted; likely not
  his to give freely). Lead with advising + calibration — things he *can* give.
- Related people if he defers: his Urban Analytics Lab (UAL), and Berkeley's Terner Center (same
  source-assembly pattern).
