---
title: "Video prose — DFW-voice rewrite (first trial)"
date: 2026-09-22
type: draft
status: for-review
area: notes
---

# The flyover texts, rewritten in the voice of David Foster Wallace

**What this is.** A first trial, at John's request, of rewriting the prose that precedes
each video on berkeleybuild.com in the voice of DFW's essays — *E Unibus Pluram*, *The
Nature of the Fun*, *Authority and American Usage*. Not deployed. Not committed. The live
text in `docs/index.html` is untouched.

**What I kept and why.**

1. **Every number is the number now on the site.** Where the current prose says 3,690
   units or 9% built, the rewrite says 3,690 and 9%. I did not round, soften, or invent a
   single figure. Values that are data-bound are marked `{{like_this}}` in the *Data
   bindings* line under each entry — see the engineering note at the bottom.
2. **The colour legend survives intact.** Per the comment at `docs/index.html:296`, the
   per-video prose legend is what a screen reader reads. Every colour→stage mapping, the
   warm/cool gloss, and the thick-outline/agency rule are preserved verbatim in a closing
   paragraph. The DFW register is applied to the body, not to the accessibility apparatus.
   (DFW would have approved of that distinction, having written a whole essay about how a
   usage rule is a political fact about who gets to be understood.)
3. **The last sentence of each entry stays sincere.** This is the *E Unibus Pluram* point
   and the whole reason to use this voice on this material: irony is a solvent that
   dissolves everything including the ground you need to stand on to say something true.
   A housing dataset is exactly the kind of thing that invites the knowing shrug. The
   rewrite refuses the shrug.

**The governing idea (revised 2026-09-22).** Everything here now serves one proposition,
and it is deliberately not a partisan one:

> Almost nobody — on any side — knows how Berkeley actually builds housing, or how a Berkeley
> merchant actually keeps a shop open. People reason from intuition instead, because intuition
> is free and the records are not. Intuition is quick, it feels like knowledge, and it sorts
> you onto a team. Once you are on a team you inherit its predictions, and the predictions
> turn out to be wrong — not because the people holding them are foolish, but because the
> process they are predicting has stages, durations and failure modes that nobody looking at
> a street can see.

So the captions are not for winning a dispute. They exist because a person standing on College
Avenue or San Pablo, looking at a building and forming a confident view of what will happen
there, is missing information that exists, is public, and is on this site. That framing also
keeps the page defensible: it implies no villain, and it is equally uncomfortable for everyone.

**Why this voice actually fits the material** (rather than being a costume). Three moves
transfer cleanly:

- **The medium is implicated in the argument.** A flyover makes a street look finished.
  Nine percent of it exists. DFW's central technique is to describe the machinery of the
  representation *while* the representation is running — which is precisely what an honest
  caption on a rendering has to do.
- **Precision as a moral act.** *Authority and American Usage* is 60 pages arguing that a
  definition is never neutral. "Entitled" vs. "permitted" vs. "built" is the same problem,
  with money and five years riding on which word you thought you heard.
- **The footnote as second, more honest voice.** These read as bracketed asides below;
  on the page they'd be `<small>` or a disclosure.

---

## 1. Bancroft Way — Piedmont to Aquatic Park

Before the camera moves, one thing worth fixing in your head: almost none of this exists.
The flight runs east to west, Piedmont Avenue at the campus edge, through downtown, out
across the flats to Aquatic Park, and it will name **thirty buildings** as it reaches
them — address, homes, storeys, height, who is developing it, who owns the ground
underneath — and the cumulative effect of all that labelling, which is the thing to watch
yourself for, is to make the street feel *done*. It isn't. The thirty are **3,690 units**,
of which 1,625 are student beds in the one UC tower rising at Bancroft and Fulton, leaving
**2,065 homes** for people who are not undergraduates. Of those, **325** are finished —
standing, occupiable, a place a person could actually sleep tonight. That is **9%**.
Another 1,182 are *entitled*, a word that means the city has said yes and no one has yet
pulled a building permit, and 1,730 are under construction, nearly all of them that single
tower. The flight orbits 2530 Bancroft, 2200 Bancroft, and 2276 Shattuck on the way, and
the orbits are the tell: a building gets circled because it is large, and largeness in a
rendering reads as inevitability, and inevitability is not a stage in the permit system.
Current to September 2026. Watch it twice — once for the street, once for how badly you
want the street to be real.

> *Data bindings:* `{{building_count}}` 30 · `{{total_units}}` 3,690 · `{{uc_beds}}` 1,625
> · `{{net_homes}}` 2,065 · `{{completed}}` 325 · `{{pct_built}}` 9% · `{{entitled}}` 1,182
> · `{{under_construction}}` 1,730 · `{{orbits}}` · `{{current_to}}` September 2026

---

## 2. Telegraph Avenue — Woolsey north to UC Berkeley

Telegraph south to north — Woolsey Street at the Oakland line, up past Ashby and Dwight,
through the Southside blocks under the campus, to the UC edge at Bancroft — and
**seventeen buildings** labelled as the camera reaches each one. Seventeen is a small
enough number that you can hold the whole street in your head, which makes this the tour
to learn the vocabulary on. **905 units** total. **261** of them exist: **29% built**, the
highest ratio in this collection and still under a third. **324 are entitled**, which is
the stage where a project has the city's permission and has not spent the money; 177 are
still in review; 91 are under construction; **52 were withdrawn**, and withdrawn is worth
sitting with, because it is the only stage on the legend that means somebody looked at the
arithmetic and walked away. Approval is not construction. Nothing you can see from the street
tells you which approved building will be abandoned by the people who asked for it. The largest thing on the street is **3030 Telegraph, 144
units**, completed January 2026, and the flight makes a full orbit of it. At Dwight the
camera follows the dog-leg the avenue itself makes through the intersection — a detail
nobody asked for, included because the street does it and the model should not be more
tidy than the place. Current to September 2026.

> *Data bindings:* `{{building_count}}` 17 · `{{total_units}}` 905 · `{{completed}}` 261 ·
> `{{pct_built}}` 29% · `{{entitled}}` 324 · `{{in_review}}` 177 · `{{under_construction}}`
> 91 · `{{withdrawn}}` 52 · `{{largest_project}}` 3030 Telegraph / 144 units / Jan 2026

---

## 3. UC Berkeley Student Housing — 5,010 Beds in Four Projects

A technical note first, because the unit of measure is the argument. The University builds
**rooms, not apartments**, so this tour counts **beds**, and no ratio converts one to the
other honestly — 1950 Oxford, Anchor House, is **772 beds** in 244 apartments, and if you
divide you get 3.16, and 3.16 is not a fact about student housing, it is a fact about that
one building. Four projects, flown north to south: **Anchor House, 772 beds, complete**;
**2200 Bancroft, 1,625 beds, under construction**, which at 23 storeys and 263 feet will
be among the tallest buildings in Berkeley and, when it opens in 2027, the tallest
completed one — still shorter than the Campanile at 307 feet, a comparison worth keeping
because the Campanile has been the answer to "how tall is too tall" here since 1914;
**2556 Haste at People's Park, 1,113 beds, under construction**; and the **Anna Head site
at 2400 Bowditch, more than 1,500 beds, still at pre-application**. Together at least
**5,010 beds**. People's Park adds a second building outside that count: roughly **100
permanent supportive and affordable apartments**, run by Satellite Affordable Housing
Associates, which start construction only after the student building opens in autumn 2027.
And now the part that matters more than any of the numbers: **none of this is in
Berkeley's permit system and none of it counts toward Berkeley's state housing targets**.
The Regents approve these; the University issues its own building permits; the city is a
spectator with a view. Which produces a specific and very common error: a person walks past
four enormous cranes, concludes Berkeley is building plenty, and is looking at buildings that
by law are not Berkeley's to count. Someone else reads the city's official total, concludes
Berkeley builds nothing, and has not been told the 5,010 beds were excluded before the number
reached them. Both of them are reasoning honestly from what they can see. Neither has been
given the one fact that reconciles it — and you cannot get that fact by looking at the street,
only by reading the permits.

> *Data bindings:* `{{total_beds}}` 5,010 · per-project beds/status · `{{sat_units}}` ~100
> · exemption rule from the `uc_project` classification flag, never a hardcoded id

---

## 4. Shattuck Avenue — South to North, past the towers

This is the big one, and bigness is its own rhetorical problem. Shattuck south to north,
Woolsey through downtown to Rose: **sixty buildings**, each labelled as the camera reaches
it, **9,347 units**, of which 2,397 are UC student beds, leaving **6,950 homes along a
single street** — a number large enough that it stops being a number and becomes a mood.
So here is the corrective, stated plainly: **23% of it is built.** **2,147 units** are
finished and occupiable. **3,585 are entitled** — approved, no building permit pulled —
and another **1,673 are still in review**, which means an application, a planner, and a
queue. The flight orbits the four largest: **2700 Shattuck, 359 units**; **2276 Shattuck,
336**; and the two tallest towers in the pipeline, **2190 Shattuck at 110 m and 452
units** and **1974 Shattuck at 98 m and 599 units**. Notice what the orbit does to a
tower. It gives it mass, shadow, a sun angle, four sides — all the sensory furniture of a
building that is there. Two of those four are paper. The video cannot show you the
difference; the colour can, and does, which is why the legend below is not decoration.
Current to September 2026.

> *Data bindings:* `{{building_count}}` 60 · `{{total_units}}` 9,347 · `{{uc_beds}}` 2,397
> · `{{net_homes}}` 6,950 · `{{pct_built}}` 23% · `{{completed}}` 2,147 · `{{entitled}}`
> 3,585 · `{{in_review}}` 1,673 · four orbit projects w/ units + height

---

## 5. University Avenue — Berkeley Harbor to UC Berkeley at Oxford Street

The full length of University, west to east: the Berkeley Harbor, over the freeway, across
the flats, through downtown, to the campus gate at Oxford. Every project in the pipeline
along the way, with full orbits of the four largest — **1581, 1598 and 2029 University**,
and the **599-unit tower at 1974 Shattuck**. Two small disclosures about how the thing you
are looking at was made, offered because a rendering that hides its sources is just a
picture. **Heights are taken from each project's own filings** — not estimated from the
model, not scaled off a photograph, but read off the drawings the developer submitted to
the city, which means they are as accurate as the applicant was and no more. And **street
names are labelled at every crossing**, which sounds like a nicety and is actually the whole
navigational contract: a flyover with no labels is a mood piece, and a mood piece is exactly
what nobody needs more of here. Feelings about this avenue are abundant and cheap. What is
scarce is knowing which building is which, who filed it, and when.

> *Data bindings:* orbit list `{{orbits}}` · heights sourced from project filings (schema
> note, not a figure)

---

## 6. Durant Avenue — Milvia to Piedmont

Durant west to east, Milvia to Piedmont, one block south of the campus edge — a short
street, and the shortness is the point, because it lets you see how the counting works.
**Six projects sit on Durant itself**, 2037 at the west end to 2538 at the east. The
flight orbits three: **2425 Durant, 117 units, entitled**; **2538 Durant, 83 units,
completed**; and the **1,625-bed UC tower at 2200 Bancroft**, 23 storeys, which is not on
Durant at all. That last one is the honest complication. Widen the frame by one block
either side and the downtown Shattuck towers and the UC dormitories come into view and the
total "in view" becomes roughly **2,500 homes and 3,100 student beds** — a number four
times the street's own, produced entirely by moving the camera. Nobody is cheating. It is
simply that *in view* and *on this street* are different claims, and a flyover blurs them
by construction, and you should know which one a number is before you repeat it. Heights
come from each project's own filings; street names are labelled at every crossing.

> *Data bindings:* `{{on_street_projects}}` 6 · orbits w/ units+stage · `{{in_view_homes}}`
> ~2,500 · `{{in_view_beds}}` ~3,100 — **flag:** in-view totals are camera-frustum-derived,
> not a corridor query; keep the distinction explicit in any generator

---

## 7. San Pablo Avenue — North to South

San Pablo down the length of west Berkeley, north to south, **3.7 kilometres** from the
Albany line to the Oakland border. Four orbits: **2136 San Pablo, 125 units, entitled**;
**2198, 100 units, entitled**; **2601, 223 units, in review**; **2733, 152 units, in
review**. Eighteen projects line the avenue, **1,056 homes in all — and 157 of them are
finished.** Twelve of the eighteen are still on paper: **568 units under review, 241
entitled but not yet permitted.** Which is why this tour looks wrong if you have watched
the downtown ones first. Downtown reads cool — blues and greens, construction and
completion. San Pablo reads warm, orange and yellow the length of the avenue, and warm on
this legend means paper. That is not a rendering artefact or a colour-grading choice. It
is a three-kilometre picture of a street where the permission has been granted and the
building has not started, and the distance between those two facts, measured in years and
in interest rates and in whether anybody ever breaks ground, is the actual subject of this
entire website.

> *Data bindings:* `{{corridor_km}}` 3.7 · `{{project_count}}` 18 · `{{total_units}}`
> 1,056 · `{{completed}}` 157 · `{{on_paper_count}}` 12 · `{{in_review}}` 568 ·
> `{{entitled}}` 241 · four orbits

---

## 8. Patrick Kennedy & Panoramic Interests — 35 Years of Berkeley Housing

Every Berkeley building by Patrick Kennedy's Panoramic Interests, 1990 to 2028 — from the
six-unit Henry Court to the proposed tower at 2274 Shattuck. **Twenty-three buildings,
twenty-one of them housing: 699 homes across three decades.** The other two are here for a
reason that is really a methodological confession: this is **one developer's entire
Berkeley output**, not a curated housing list, so a 2006 self-storage building and a 2009
historic renovation on Center Street stay in, because dropping them would quietly turn a
record into an argument. Thirty-five years is long enough to watch a person's ideas change
and long enough to watch a city's rules change around them, and you cannot tell from the
air which of those two is doing the work in any given building. What you can see is
cadence: how long between projects, how the massing moves, what got built in the years
when nothing got built. **699 homes in thirty-five years, by the developer most associated
with building here**, is a figure worth carrying into any conversation about how fast this
city can move.

> *Data bindings:* `{{buildings}}` 23 · `{{housing_buildings}}` 21 · `{{total_homes}}` 699
> · span 1990–2028 · owner join via `players` / developer classification

---

## 9. June 2026 Shattuck Avenue Building Pipeline

A narrow slice, deliberately: **Shattuck Avenue, June 2026, only the projects that are
Entitled or In Review.** Everything built is removed. Everything under construction is
removed. What is left is the pure paper stage — the buildings that have been argued over
at a hearing, drawn by an architect, priced by somebody, and not started. Strip out the
finished city and this is the residue, and the residue is what people actually mean when
they say "the pipeline," and it is also, almost always, what they are picturing when they
say a thing has been *approved*.

> *Data bindings:* stage filter = entitled ∪ in-review · snapshot month `{{as_of}}` June 2026

---

## 10. 2026 Berkeley's 17 Largest Private Housing Projects

**The seventeen largest private housing projects in Berkeley, each over 200 units
planned.** Two words in that sentence are doing all the work. **Private** — which means UC
is absent, and UC is 5,010 beds, so the thing you are looking at is the city's housing
minus its single largest producer of housing, because the University is exempt from city
permitting and does not count toward the city's targets. **Planned** — which means unit
counts as filed, not as built, and a project's plan can shrink at permit, shrink again at
revision, or never be built at all. Neither word is a hedge. Each one is the precise term for a real legal distinction, and the
reason to spell them out rather than smooth them away is that a number stripped of its
qualifiers travels faster, lands harder, and produces confident predictions that do not come
true. "Berkeley approved 3,000 homes" and "Berkeley built 3,000 homes" are different sentences
about different worlds, and only one of them is a place anybody can live.

> *Data bindings:* `{{project_count}}` 17 · threshold `{{min_units}}` 200 · filter:
> `uc_project` flag excluded (never a hardcoded id) · "planned" = filed unit count

---

## 11. Adeline & Shattuck Corridor

South to north along Adeline and Shattuck, starting at the Campanile — which is where
every Berkeley aerial starts, because the Campanile is the only thing in town everyone can
locate from the air, and a tour has to begin somewhere a viewer already is. This is the
downtown development corridor: the stretch with the towers, the stretch that gets cited in
both directions, as proof that Berkeley builds and as proof of what building costs. The
camera does not adjudicate that. It goes up the street.

---

## 12. Elmwood to Shattuck via College & Bancroft

From the Elmwood Theater north up College Avenue, then west along Bancroft to Shattuck.
Residential fabric, then commercial fabric, then downtown, in one continuous move. Watch the
stretch between the theater and Ashby: two- and three-storey commercial frontage, and then,
immediately behind it, a neighbourhood that has been adding homes for a century in ways no
aerial can see — flats cut out of houses, cottages behind houses, units that are occupied and
rented and appear in no dataset. This is the exact spot where intuition fails hardest in both
directions. Look at the frontage and the neighbourhood appears frozen, which it is not. Look
at the storefronts and they appear permanent, which they also are not: a shop's survival turns
on a lease term, an insurance renewal and a landlord's tax basis, none of which are visible
from any altitude. A flyover is a device for looking at frontage. It cannot show you either of
the things that actually determine what happens here — and that limitation is worth holding
for the whole three minutes, including and especially the parts where the video is beautiful.

---

## The legend (appended verbatim to each entry; unchanged from the live site)

> **Colour shows where each project stands:** grey at pre-application · yellow under
> review · orange entitled (approved, no building permit yet) · cyan permitted, not yet
> started · blue under construction · green completed and occupiable · dark red withdrawn.
> Warm colours are paper stages, cool colours are physical ones. A thick outline marks a
> project permitted by its own agency rather than by the City — purple for UC Berkeley and
> magenta for BART joint development; the fill still shows the stage. Elsewhere on
> BerkeleyBuild.com: the architects' own plan sets and the affordability tabulations filed
> with them, and for every project in the pipeline the full permit timeline — when it was
> filed, when it was approved, when the building permit issued, and when it was finished.

---

## Engineering note (this matters more than the prose)

The current per-video text in `docs/index.html` is **hand-written, with the figures typed
in**. I looked for a generator and there isn't one: `scripts/update_legend.py` generates
the SVG legend and the geometry census, but no script emits the paragraph bodies (grep for
"Piedmont to Aquatic Park" across `scripts/` returns nothing).

That makes every number above a **hardcoded current-state total** — precisely the smell
`CLAUDE.md` names under *Anchor checks to what stays true*: "any assertion of a raw
current-state total that a future correction could move." When the next CO lands or the
next gated write corrects a unit count, the video captions silently go stale, and stale
captions on a site whose entire pitch is *we publish the record* cost more than they save.

**Recommendation, if the rewrite is adopted:** land it as a template + generator
(`scripts/gen_video_prose.py`) that reads `v_projects_flat` per tour geometry, fills the
`{{bindings}}`, and asserts the derived figures against a timestamped baseline
(`data/baselines/video_prose_baseline_<date>.json`) the way JN-E does — so the prose
changes when the data changes, and a legitimate change re-passes by appending a baseline,
never by hand-editing a magic number. The DFW voice survives that fine; the sentences
above are built so the numbers sit in slots.

Two figures need a flag before any generator runs:
- **Durant's "in view" totals** (~2,500 homes / ~3,100 beds) are derived from what the
  camera sees, not from a corridor query. Keep them labelled as such or drop them.
- **Anchor House 772 beds / 244 apartments** is the one place the text does arithmetic
  (3.16 beds per apartment) — it is there to refute the ratio, and it should stay
  hand-written prose, not a computed field.
