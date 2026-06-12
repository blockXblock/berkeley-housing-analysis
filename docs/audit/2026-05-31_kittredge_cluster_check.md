# Kittredge Street Cluster — v2 vs Real-World Check — 2026-05-31

**Scope:** Read-only. Checks whether v2's Kittredge records (2065/2115/2138/2150/
2176) correspond to real-world projects or show cross-contamination. **No data,
DB, or script modified.** Does not touch external drives or the Toshiba copy.

---

## Headline (supersedes part of the P1b diagnosis)

**APNs are correctly mapped — there is no APN mis-keying.** But id113's
"Permitted, 73 units" status for **2138 Kittredge is spurious**: it derives from
**permit B2024-04964 = "Remove & replace bathroom window same size & location,"
valuation $690** — a trivial alteration permit that v2 ingested as a "Building
Permit Issued" milestone. **2138 is in design review, not permitted.** This
**revises my earlier P1b recommendation** ("keep id113/73u as canonical"):
id118 (66u) is the real project; id113's permitted status is a data artifact.

This is a **systematic CPRA ingestion problem** — minor alteration permits
(windows, solar, signs) are being read as project-level BP/CO milestones — and
likely contributes to the **APR pilot's CO-total overshoot**.

---

## Ground-truth APN ↔ address (berkeley.db) vs v2

| Address | berkeley.db APN | v2 record APN | Match |
|---|---|---|---|
| 2115 Kittredge | 57-2030-9 | 057 203000900 (id12) | ✅ |
| 2138 Kittredge | 57-2029-**15** | 057 2029**015**00 (id113, id118) | ✅ |
| 2150 Kittredge | 57-2029-**16** | 057 2029**016**00 (id135) | ✅ |
| 2176 Kittredge | 57-2029-2-4 | — (no v2 record) | n/a |

**No APN mis-keying.** id113 is genuinely on 2138's parcel; 2150 is a *different*
parcel with *different* permits. So the hypothesis "id113's permit belongs to
2150 mis-keyed to 2138" is **refuted on APN grounds.**

## Each project: v2 vs known real-world fact

| Address (v2 id) | v2 record | Known fact | Verdict |
|---|---|---|---|
| **2115** (id12) | 148u, **In Review**, filed 2024-09-17, no permit | California Theater; 23-story conversion **ABANDONED mid-2025** | ⚠️ **Stale status** — should be withdrawn/abandoned, shows In Review |
| **2138** (id118) | 66u, **Entitled** | ~66u, **design review** Apr 2026 (not permitted) | ≈ Match on units; status slightly ahead (Entitled vs design-review) — the **real** 2138 record |
| **2138** (id113) | 73u, **Permitted**, BP "B2024-04964" 2024-10-16 | 2138 NOT permitted | ❌ **Spurious** — "BP" is a **$690 bathroom-window** permit |
| **2150** (id135) | 169u, **Completed**, CO 2024-03-06 | 169u, **completed**, 7-story mixed-use | ✅ Match (but CO date derives from a **sign permit's** finaled date — weak basis, project genuinely complete) |
| **2176** | none | "relatively new" complex, maybe part of 2150 | — not tracked separately; not a contamination issue |
| 2065 (id180) | 189u, Entitled | (outside the asked set) | separate project; fine |

## The contamination mechanism (the crux)

v2's `permits` for these projects are **minor CPRA alteration permits**, ingested
2026-05-12 and surfaced as project milestones:

| Project | v2 "permit" | Real description | Valuation | v2 treated it as |
|---|---|---|---|---|
| 2138 (id113) | B2024-04964 | **Remove & replace bathroom window** | **$690** | "Building Permit Issued" → **Permitted** |
| 2150 (id135) | B2022-05181 | Install 23.85 KW PV solar panels | $0 | (permit record) |
| 2150 (id135) | B2023-01578 | Install exterior sign | $20,000 | CO date 2024-03-06 = sign permit finaled |

The **real residential building permits are absent**; trivial alteration permits
took their place and drove status. A $690 bathroom-window permit should never
confer "Permitted" on a housing project.

## Answer to the framed hypotheses

- **(a) "id113/id118 are one project, two stages — merge to 73u":** **Partially —
  but the canonical pick was wrong.** They *are* one project (same APN, dates,
  flags), but id113's 73u/Permitted is an artifact of the bathroom-window permit.
  **id118 (66u, design-review) is authoritative**, not id113.
- **(b) "id113's permit belongs to 2150/another, mis-keyed":** **Refuted on APN**
  (id113 is correctly on 2138's parcel; 2150 has different permits). Not a mis-key.
- **(c)/NEW (d) — the actual cause:** id113's milestone is a **misclassified minor
  alteration permit** ($690 bathroom window) read as a Building-Permit-Issued
  event. Resolvable from data on hand (the permit description is dispositive);
  Accela would only confirm 2138 has no real housing BP.

## Recommendations (not executed)

1. **2138:** treat **id118 (66u)** as the authoritative record; **strip id113's
   spurious "Permitted" status** (its BP is a bathroom-window permit). Then the
   113/118 duplicate collapses to one design-review/entitled project at 66u.
2. **Systemic — audit CPRA permit ingestion:** minor alteration permits (windows,
   solar, signs) are being classified as BP-Issued / CO milestones. This
   over-promotes projects' pipeline stage and **likely inflates the APR CO/permitted
   totals** (cf. the APR pilot's CY2024 1233-vs-708 overshoot). Add a
   permit-type/valuation filter so only structural/new-construction permits drive
   stage milestones.
3. **2115:** refresh status — California Theater conversion abandoned mid-2025;
   v2 still shows "In Review."
4. **2150:** correct on units/completion; note its CO date rests on a sign permit
   and could be re-anchored to a real CO if available.

*Diagnosis only. No data/DB/script modified. Uncommitted — review before any fix.
This supersedes the "merge to 73u" line in `2026-05-31_p1_artifacts_diagnosis.md`.*
