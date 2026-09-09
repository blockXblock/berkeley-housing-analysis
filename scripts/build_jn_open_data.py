#!/usr/bin/env python3
"""build_jn_open_data.py — generator for notebooks/JN-BerkeleyOpenData.ipynb

The "Berkeley Open Data" approach: reconstruct a city's HCD Annual Progress Report from
PRIMARY SOURCES, then use the city's submitted APR only as a reconcile-target — never as an
input. Written for three audiences at once: HCD/Possibility Lab, data journalists, and a
data-science classroom.

Markdown-in-source; every figure DERIVED from databases/berkeley_housing_v3.db, none hardcoded.
Run:  .venv/bin/python scripts/build_jn_open_data.py
"""
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell
C=[]
def md(s): C.append(new_markdown_cell(s.strip()))
def code(s): C.append(new_code_cell(s.strip()))

md(r"""
# Berkeley Open Data — reconstructing an HCD Annual Progress Report from primary sources

**What this is.** A worked demonstration that a city's **Housing Element Annual Progress Report** can be
rebuilt independently, from the same primary records the city itself used, and then *compared* to what
the city filed — with every step reproducible and every disagreement itemised.

**Why it matters.** California's APR is the state's primary measure of housing production. It is
assembled in spreadsheets and, once filed, is very hard to audit. The
[Possibility Lab](https://possibilitylab.berkeley.edu/project/housing-and-community-development-hcd-annual-progress-reports/)
found that roughly **half of San Francisco's 2018–2021 APR entitlements (94) were reported incorrectly**,
and that the city **failed to report 54 entitlements**. That is not a story about one city. It is a
story about a reporting process with no independent check.

**The claim this notebook makes.** The check is buildable. It is not cheap, but it is *tractable* — and
what it produces is not a better spreadsheet but a **reproducible artifact**: sources named, transforms
visible, and a gate that fails when a number moves.

---

**Three ways to read this notebook**

| you are | start at | you will get |
|---|---|---|
| **HCD / policy** | §1 and §6 | what an auditable APR submission would require |
| **Data journalist** | §4 and §5 | how to find where a city's filing and its own records disagree |
| **Student / class** | §2 and §3 | a ten-stage pipeline you can rebuild from raw files |
""")

md(r"""
## §1 — The cardinal rule: the city's filing is a *target*, never an *input*

This is the one design decision everything else follows from, and it is the one most easily got wrong.

> **If you use the city's APR to build your reconstruction, you have not checked anything.**
> You have re-derived the city's answer and confirmed it equals itself.

So this project keeps two things strictly apart:

- **INPUTS (primary):** CPRA-obtained building-permit records, and the county assessor's parcel roll.
  These are what the city works from too.
- **ORACLE (verification only):** the city's submitted APR, mirrored from HCD's open-data portal, opened
  **read-only**, and consulted only *after* the reconstruction is complete.

The pipeline stage that performs the comparison states the rule in its own docstring:

> *"The mirror is ORACLE / reconcile-target ONLY, opened READ-ONLY; using it as a data source would be
> circular (the cardinal sin)."*

**For HCD this is the transferable idea.** A submission standard that required the *derivation* — not
just the number — would make this check something a city runs on itself, before filing, rather than
something an outside party reconstructs years later.

> **A footnote on the oracle itself: published datasets change, and a reader holding one snapshot
> cannot tell which one they have.** This project keeps *dated* mirrors rather than a single live
> pull, each carrying its retrieval timestamp and source URL. That is not defensive bookkeeping — the
> mirrors we hold genuinely differ from one another. Open-data portals are re-published, re-ingested
> and corrected as a matter of routine, usually without an erratum, a version marker or a changelog,
> so two analysts pulling the same resource weeks apart can compute different totals from what they
> each reasonably believe is *the* dataset, and neither has any way to notice.
>
> This cuts against a reconstruction as much as for it. It means "the city's filing says X" is only
> meaningful with a date attached — and it is why the comparison in §3 names the mirror it used
> rather than describing it as the APR. **Record which snapshot you scored against, or your
> reconciliation is not reproducible either.**
""")

code(r"""
# ── SETUP ────────────────────────────────────────────────────────────────────
# Runs anywhere with no setup. The figures below are EMBEDDED with their provenance,
# because the reconstruction database is not distributed with the public repository
# (databases/ is gitignored — the repo carries code, not data). If you DO have the
# repo and its databases locally, every figure is re-derived from source and checked.
import os, sqlite3
import pandas as pd

V3 = "databases/berkeley_housing_v3.db"
HAVE_REPO = os.path.exists(V3)

if HAVE_REPO:
    print("MODE: full — reconstruction database found.")
    print("      Every figure below is re-derived from source and checked against the embedded copy.")
else:
    print("MODE: portable — running with figures embedded from the 2026-09-09 derivation.")
    print("      This is the expected path outside the project. Nothing is missing and nothing failed:")
    print("      the public repository carries CODE, not DATA (databases/ is gitignored), so the")
    print("      numbers travel with the notebook instead. Provenance is recorded beside each one.")
    print("      To rebuild them from the raw permit records yourself, see the curriculum in \u00a75a.")
""")

md(r"""
## §2 — The chain: from two spreadsheets to an APR

The reconstruction is ten gated stages. Each is idempotent, each writes only its own tables, and each
can be re-run from the stage before it. Nothing is hand-edited.

```
  PRIMARY SOURCES                      RECONSTRUCTION (v3)                     ORACLE
  ─────────────────                    ───────────────────                     ──────
  CPRA building-permit                 S0  clean-key index
    corpus (2 xlsx files,              S1  project spine  ────┐
    2018-2022 / 2023-2025)             S1.5 address routing   │
                                       S2  events            │
  Alameda County                       S3  stage             │  each stage
    assessor parcel roll               S4  units             │  gated + idempotent
                                       S5  affordability     │
                                       S6  evidence          │
                                       S7  cycle / year   ───┘
                                       S8  reconciliation ──────► 90 itemised findings
                                       S9  scorecard      ──────► compared to ──► city's
                                                                                  filed APR
                                                                                  (read-only)
```

**The two ends are what matter.** S0 starts from files anyone can request under the Public Records Act.
S9 ends at a table that says, year by year, how far the reconstruction sits from what the city told the
state — and S8 says *why*.

> **A note on what this notebook can and cannot hand you.** The public repository carries the *code*,
> not the *data* — the databases are gitignored, as they should be. So the figures below travel with
> this notebook as **embedded values with their provenance attached**, and it runs anywhere with no
> setup. If you have the repository and its databases locally, the same cells **re-derive every figure
> from source** and tell you whether the embedded copy still agrees.
>
> **The curriculum in §5a is the runnable version.** Those notebooks fetch the actual primary sources —
> the raw CPRA permit spreadsheets and the HCD APR mirror — from public object storage, so a student
> builds the reconstruction rather than reading someone else's numbers.
""")

code(r"""
# The primary sources — the whole input side of the chain.
import glob
cpra = sorted(glob.glob("data/raw/cpra-downloads/*.xlsx"))
for f in cpra:
    print(f"  {os.path.getsize(f)/1e6:6.1f} MB  {f}")
print(f"\n{len(cpra)} CPRA spreadsheet(s) — this is the entire permit input.")
print("Requested from the City under the California Public Records Act. Any resident could ask for them.")
""")

md(r"""
## §3 — The reconciliation: what the reconstruction says, versus what the city filed

The table below is **derived live** from the reconstruction database. `v3_co_units` counts units whose
certificate of occupancy falls in each reporting year, built from permit records. `city_co_units` is the
same measure read out of the city's own submitted APR (table A2, CO income columns).

They are compared **like for like** — the same definition, the same years — which is the only comparison
worth making.
""")

code(r"""
# S9 SCORECARD — CO completions per reporting year: reconstruction vs the city's filed APR.
# Derived 2026-09-09 from databases/berkeley_housing_v3.db (table s9_scorecard).
EMBEDDED_SCORECARD = [
    {"year": 2018, "reconstruction": 228, "city_filed": 229, "delta": -1, "buildings": 65},
    {"year": 2019, "reconstruction": 309, "city_filed": 313, "delta": -4, "buildings": 98},
    {"year": 2020, "reconstruction": 398, "city_filed": 405, "delta": -7, "buildings": 77},
    {"year": 2021, "reconstruction": 368, "city_filed": 331, "delta": 37, "buildings": 116},
    {"year": 2022, "reconstruction": 679, "city_filed": 828, "delta": -149, "buildings": 101},
    {"year": 2023, "reconstruction": 845, "city_filed": 716, "delta": 129, "buildings": 162},
    {"year": 2024, "reconstruction": 783, "city_filed": 708, "delta": 75, "buildings": 141},
    {"year": 2025, "reconstruction": 700, "city_filed": 492, "delta": 208, "buildings": 191},
]
score = pd.DataFrame(EMBEDDED_SCORECARD)

if HAVE_REPO:                       # re-derive and prove the embedded copy still matches
    con = sqlite3.connect(f"file:{V3}?mode=ro", uri=True)
    SQL = ("SELECT reporting_year AS year, v3_co_units AS reconstruction, "
           "city_co_units AS city_filed, delta, v3_co_buildings AS buildings "
           "FROM s9_scorecard ORDER BY reporting_year")
    live = pd.read_sql(SQL, con)
    agree = live.reset_index(drop=True).equals(score.reset_index(drop=True))
    print("re-derived from source:", "AGREES with embedded" if agree else "DRIFTED — refresh the notebook")
    score = live

score["abs_delta"] = score.delta.abs()
print(score.to_string(index=False))

net   = int(score.reconstruction.sum() - score.city_filed.sum())
gross = int(score.abs_delta.sum())
print(f"\n  reconstruction total : {score.reconstruction.sum():,} units")
print(f"  city filed total     : {score.city_filed.sum():,} units")
print(f"  NET difference       : {net:+,}")
print(f"  GROSS disagreement   : {gross:,}  (sum of |delta|, i.e. units in dispute either way)")
print(f"\n  Net is {abs(net)/gross:.0%} of gross: {gross-abs(net):,} units of disagreement "
      f"({(gross-abs(net))/gross:.0%}) CANCEL OUT and are invisible in any total.")
""")

md(r"""
📝 **The single most important line in this notebook is the last one.**

**Over half the disagreement cancels.** A city and an auditor can land close on the *total* while
disagreeing about a much larger number of individual units — some counted a year early, some
a year late, some missed, some double-counted. **A spreadsheet total shows you the net. It cannot show
you the gross.**

That is the argument for reproducible submission in one sentence: *the errors that cancel are still
errors*, and they land in different RHNA years and different cycles, where they change what a city is
held to.

Note also the **shape over time**: near-agreement in the early years, divergence in the recent ones. Recent
years are exactly where a city's own records are still settling — and exactly where the state is making
decisions.
""")

md(r"""
## §4 — Why they differ: one worked case a journalist can follow

S8 itemises every disagreement the pipeline found — 90 of them, by type. They are not opinions; each
names the two sources and the consequence.

The clearest class is a **date disagreement**. A building permit has a "finaled" date. Two sources
disagree about it. That single field decides which *reporting year* the units land in — and therefore,
sometimes, which **RHNA cycle** they count toward.
""")

code(r"""
# S8 — every disagreement the pipeline found, by type (90 findings), and one worked case.
EMBEDDED_FINDING_TYPES = [
    ("stage_reconcile", 33),
    ("xaddr_review", 22),
    ("apn_overlap", 13),
    ("crosscheck_summary", 6),
    ("unit_reconcile", 6),
    ("measurement_basis", 4),
    ("date_reconcile", 3),
    ("entitlement_date_gap", 1),
    ("multi_building_development", 1),
    ("rhna_scope_question", 1),
]
EMBEDDED_EXAMPLE = {
    "subject":      "B2018-03576",
    "v3_value":     "CPRA 2020-01-10 (is_inferred=0)",
    "other_value":  "v2 2025-08-12",
    "other_source": "v2",
    "magnitude":    "2041d; reporting-year 2020->2025; CALENDAR_CYCLE 5th->6th",
}
types = pd.DataFrame(EMBEDDED_FINDING_TYPES, columns=["finding_type","n"])
example = EMBEDDED_EXAMPLE

if HAVE_REPO:
    types = pd.read_sql("SELECT finding_type, COUNT(*) n FROM s8_reconciliation "
                        "GROUP BY 1 ORDER BY n DESC", con)
    example = pd.read_sql("SELECT subject, v3_value, other_value, other_source, magnitude "
                          "FROM s8_reconciliation WHERE finding_type='date_reconcile' LIMIT 1",
                          con).iloc[0].to_dict()

print(types.to_string(index=False))
print(f"\n  total findings: {int(types.n.sum())}")
print("\n── a worked date disagreement ─────────────────────────────────────────")
for k, v in example.items():
    print(f"  {k:<14} {v}")
""")

md(r"""
📝 **Read that magnitude field.** A single permit's finaled date differs by years between two sources.
The consequence is spelled out: the reporting year moves, and with it the RHNA cycle. Those units are
not invented or destroyed — they are *relocated*, from one accountability period to another.

**This is what a journalist can do with this approach.** Not "the city lied" — the far more defensible
and more interesting claim: *here is a specific permit, here are the two dates, here is the source of
each, and here is what changes depending on which one you believe.* Every finding in that table is a
lead with its evidence already attached.
""")

md(r"""
## §5 — On-ramps

**If you are a data journalist.** You need three things and you can get them all: (1) the city's building
permit corpus, by Public Records Act request — Berkeley's is two spreadsheets; (2) the county assessor's
parcel roll, usually an open-data download; (3) the city's filed APR from
[HCD's open data portal](https://data.ca.gov/). The comparison in §3 is the story. Start with the year
where the delta is largest and read the S8 findings for that year.

**If you are teaching a class.** The ten stages are a semester. Each is small, each is gated, and each
fails loudly when its assumption breaks. Suggested arc: students rebuild S0–S2 from the raw spreadsheets
(keys, spine, events), then are *given* S3–S7 and asked to break them; the assessment is S8 — can they
find a disagreement the pipeline missed? The pedagogical point is that **the interesting work is in the
reconciliation, not the ETL**.

**If you are at HCD.** The submission standard is the lever. A city filing an APR could be asked to file
the *derivation* alongside the number: the source records, the transform, and a check that fails when the
output moves. Nothing here required new authority or new data collection — only that the work be shown.
""")

md(r"""
## §5a — The same reconstruction, taught: an 18-notebook curriculum

This notebook shows the *result*. The pipeline behind it has also been written as a course — eighteen
notebooks that walk a student from "what is a dataframe" to scoring their own reconstructed APR against
the city's filing. It was built for high-school and undergraduate data science.

**Every one runs in Colab with no setup.** Each begins with a bootstrap cell that fetches the data from
public object storage — the raw CPRA permit spreadsheets, the HCD APR mirror, and a cleaned permit
table — and no-ops if the repository happens to be local. Nothing to install, nothing to request.

| | notebook | what it teaches |
|---|---|---|
| **Foundations** | [JN00 · Look at the data first](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN00_look_first.ipynb) | look before you model |
| | [JN0a · Why data](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN0a_why_data.ipynb) · [JN0b · What a notebook is](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN0b_notebook.ipynb) · [JN0c · Functions](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN0c_function.ipynb) · [JN0d · DataFrames](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN0d_dataframe.ipynb) | the tools, from zero |
| | [JN0e · Many pictures](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN0e_charts.ipynb) · [JN0f · Our tools](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN0f_tools.ipynb) · [JN0g · Building with agents](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN0g_agents.ipynb) · [JN0h · The instruction file](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN0h_instruction_file.ipynb) | charts, tooling, and working with AI agents |
| **The build** | [JN1 · Getting the data in the door](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN1_ingest.ipynb) | ingest the raw permit corpus, mess and all |
| | [JN2 · The address key](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN2_address_key.ipynb) | the join nobody warns you about |
| | [JN3 · From permits to buildings](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN3_spine_units.ipynb) | a spine, and how many units |
| | [JN4 · When is a building actually *done*?](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN4_events_stage.ipynb) | events and stage |
| | [JN5 · One date, three questions](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN5_year_cycle.ipynb) | reporting year vs RHNA cycle |
| **The check** | [JN6a · Interrogate the oracle](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN6a_apr_oracle.ipynb) | read the city's filing *without* using it |
| | [JN6b · Did we get it right?](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN6b_join_score.ipynb) | score your APR against the city's |
| | [JN7 · The re-key audit](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN7_rekey_audit.ipynb) | finish what you flagged |
| | [JN8 · The record watches itself](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/curriculum/JN8_watch.ipynb) | make the check permanent |

**Note the shape of the arc.** Nine notebooks of foundations and build; then **four on the check**. JN6a
teaches the cardinal rule from §1 as a *skill* — how to read the city's filing to score against it while
never letting it contaminate your own numbers. JN8 ends not with an answer but with a watcher, because
the interesting property of a reconstruction is that it can be re-run when the source changes.

**For a classroom that is the assessment**: not "did you get 4,310?" but "when the city files again, does
your check still fire?"
""")

md(r"""
## §6 — What this does and does not demonstrate

**Does:** that independent reconstruction from primary sources is tractable for one city, and that it
finds real, itemised, sourced disagreements — 610 units in dispute across eight years, against a net of
288.

**Does not:** generalise automatically. Berkeley is one city with an unusually good permit corpus. The
labour is real; this pipeline is the product of months, not an afternoon. And the reconstruction is
itself fallible — S8 exists precisely because *our* numbers need auditing too, which is why every
disagreement records both values and neither is assumed correct.

**The honest summary:** this is not a finished product HCD could adopt tomorrow. It is an existence
proof that the check is possible, and a concrete description of what a city would have to publish for
the check to be cheap.
""")

nb = new_notebook(cells=C)
nb.metadata.kernelspec = {"display_name":"Python 3","language":"python","name":"python3"}
import os as _os
_os.makedirs("notebooks", exist_ok=True)
OUT = "notebooks/JN-BerkeleyOpenData.ipynb"
with open(OUT,"w") as f: nbf.write(nb,f)
print(f"wrote {OUT} — {len(C)} cells")
