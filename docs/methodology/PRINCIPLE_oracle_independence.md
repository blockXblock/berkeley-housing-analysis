# PRINCIPLE — Oracle Triangulation and Independence

*The conceptual frame inherited by the JN-D build notebook (the ADU bijection) and the
oracle-triangulation curriculum notebook. Berkeley instances are illustration; the principle is
meant to transfer to any California city.*

---

## 1. What an oracle is

An **oracle** is any independent record of the *same real-world event* you are trying to characterize
from your own source. You hold building permits (a stream of administrative transactions). An ADU got
built. Some *other* system also recorded that an ADU got built — the city's state filing, the tax
roll, a building-footprint map. Each of those is an oracle: a second witness you did not author.

The first discipline is the one JN6a already teaches: **an answer key is a hypothesis too.** You
interrogate an oracle before you trust it — locate it, verify it against a number you already know,
and check it is *current* (Berkeley's accidental CY2025 double-submission is the standing example). An
oracle is corroboration, never authority.

## 2. The two kinds, and the independence ladder

Not all oracles are equally independent of your source, and the difference is the whole method.

- A **concordant** oracle re-describes *the same paperwork* (the city told the state about the same
  permit it issued). It catches **transcription and recall errors** — but a shared upstream means a
  shared blind spot.
- An **independent-mechanism** oracle detects a *physical or administrative consequence* of the event
  (the dwelling got taxed, drew water, cast a roofline). It catches **whether the thing is real** —
  because its record was produced for an entirely different reason, by a system with no stake in your
  question.

**Rank your oracles by how independent their production mechanism is from the source you're checking.**
The more independent the mechanism, the stronger the corroboration — and, crucially, the *coarser* the
signal:

| oracle (Berkeley instance) | kind | independence | what it asserts | characteristic blindness |
|---|---|---|---|---|
| HCD APR (`UNIT_CAT='ADU'`) | concordant | low | "city reported an ADU here" | its silence may be a city **under-report** |
| Assessor `Imps` | independent admin | medium | "an improvement was valued here" | **reassessment lag** (1–2 yr) — silent on recent permits |
| Address Points (own address assigned) | independent admin | medium | "a distinct unit was addressed here" | not all ADUs get a new point |
| Building footprints (structure count) | independent physical | high | "≥2 structures exist on this parcel" | **interior conversions add no footprint**; atemporal (no year) |
| Utility new-meter (EBMUD/PG&E) | independent physical | high | "a new service was connected" | meter **reuse** on conversions; *named-only, CPRA-gated* |

The ladder is the lesson: **you trade specificity for independence as you climb it.** HCD names "ADU"
precisely but is only paperwork. The footprint proves a real structure exists but cannot name which one
is the ADU. No single oracle is both maximally independent and maximally specific — so you triangulate.

## 3. Silence ≠ negative

The hardest discipline. **An oracle's blank means "this system did not witness the event," not "the
event did not happen."** Reading silence as a negative is the same recall bug — now committed against
the oracle instead of your own data.

Every oracle has a *characteristic blindness*, and they differ:

- HCD silent → possibly a city under-report (the inverse finding).
- Assessor silent → reassessment lag; meaningless for a recent permit.
- Footprint shows one structure → no ADU **or** an interior conversion (the footprint is blind to
  exactly the most common ADU mode — garage/basement conversion).

Because the blindnesses differ, **oracles do not rescue each other uniformly.** A conversion ADU can be
invisible to your own flag, invisible to the footprint, and lagged out of the assessor — yet real and
sitting in HCD. So **choose your oracles deliberately to cover each other's blind spots** (Address
Points partly covers the footprint's conversion blindness — a JADU still gets an address).

## 4. The operational discipline: corroborate, never source

An oracle **raises or lowers confidence in a determination you made on your own evidence.** It never
*becomes* the determination. Gating your label on the oracle is circular (you would be grading your
homework with the answer key copied in). This is the standing oracle-only rule: surface divergence,
never tune toward the oracle.

Concretely, every independent-mechanism oracle is a **positive-direction, often atemporal corroborator**:
- "≥2 footprints is *consistent with* an ADU here" — never "therefore an ADU," never a year.
- "an `Imps` bump near the finaled date is *consistent with* something built" — absent ≠ not-built.

The unit is sourced by *your* description-gated classifier. The oracles confirm it is real and locate
where you should look. They are the flashlight, not the verdict.

## 5. Two audits catch different bugs

A corollary worth stating, because it is *why* entity-level triangulation exists alongside total
reconciliation:

- **Aggregate reconciliation** (JN6-style: sum the units, compare totals, name every unit of difference)
  catches **counting** errors.
- **Entity-level classification triangulation** (the JN-D bijection: match parcel-by-parcel, compare
  *labels*) catches **classification** errors that totals can hide.

The ADU recall blind-spot (≈584 real ADUs misfiled because the `ADU=Yes` flag was blank) was
**invisible to aggregate totals** — a missed ADU and a present alteration can net out in a sum. It
became visible only by triangulating *labels* against a classifying oracle. To audit your count, sum
against an oracle. To audit your *labels*, triangulate entities against one.

## 6. The generalizable move (for any city)

The transferable skill is not the Berkeley code. It is the habit of asking:

> **"What disinterested system also recorded this event, for its own unrelated reasons — and what is
> that system blind to?"**

The tax roll records it to bill it. The water utility to meter it. The footprint map to plan around it.
None is trying to count housing, and that disinterest is what makes the testimony worth something. Every
city has some version of all four. Find them, rank them by independence, read their agreement *and their
silence* honestly, and let them corroborate — never source — the determinations you make on your own
evidence.
