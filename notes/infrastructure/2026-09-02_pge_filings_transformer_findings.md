# What PG&E's own filings say about its transformers — 2026-09-02

**Method:** downloaded four filings (2,887 pages), extracted with `pdftotext -layout`,
searched for transformer counts, ages, ignition rates and Berkeley mentions. All page
citations are to the filings themselves. Sources are public; nothing here needed a
records request.

| File | Pages | What it is |
|---|---:|---|
| `grc_A2505009_566347744.pdf` | 559 | **Exhibit (PG&E-4)**, 2027 GRC prepared testimony, **Electric Distribution**, Chapters 1–9, Vol 1 of 2 (15 May 2025) |
| `grc_A2505009_pge18_rebuttal.pdf` | 550 | Exhibit (PG&E-18), rebuttal testimony (31 Mar 2026) |
| `grc_A2505009_pge30_errata.pdf` | 134 | Exhibit (PG&E-30), errata (1 Jun 2026) |
| `wmp_2023-2025_r4.pdf` | 1,644 | 2023–2025 Wildfire Mitigation Plan, revision 4 (8 Jan 2024) |

Held in `scratch/2026-09-02/pge_filings/` (gitignored — re-downloadable from the URLs
in `docs.cpuc.ca.gov` / `pge.com`).

---

## 1. The finding: a 137-to-168-year replacement backlog, by PG&E's own arithmetic

Exhibit (PG&E-4), p. 9-35, lines 14–19, verbatim:

> "PG&E is currently tracking over **67,000 overloaded service transformers** in the
> system, but because the CBR for this activity is low, PG&E is limiting transformer
> replacements to between **400 and 488 transformers per year**."

(CBR = cost-benefit ratio. Sourced in the filing's footnote 42 to Exhibit (PG&E-4),
WP 9-71, Workpaper Table 9-17, line 20.)

**67,000 ÷ 488 = 137 years. 67,000 ÷ 400 = 168 years.** And that is the *optimistic*
reading, because it assumes not one additional transformer becomes overloaded in the
meantime — while the same testimony forecasts 5,000–9,400 *newly* overloaded
transformers from EV charging alone over 2027–2030 (Exhibit PG&E-18, Ch. 9 Atch F,
rows 14–16).

PG&E is not hiding this. It is the stated justification for a funding request. But it
is the sentence the whole project was looking for: **the utility knows about 67,000
overloaded transformers and has decided, on cost-benefit grounds, to replace roughly
450 a year.**

## 2. The maintenance posture, in PG&E's own words

2023–2025 WMP, p. 512, on Distribution Overhead Transformers:

> "Distribution overhead transformers are partly proactively managed and **generally
> run to condition**."

"Run to condition" means replaced on failure or on an inspection finding — not on a
schedule. The monitored conditions are named: "corrosion, physical damage, and
**leaking oil**." One improvement is in flight: an EPIC 3.20 "Maintenance Analytics"
model using SmartMeter data to predict failures, which PG&E says *may* expand
proactive replacement, prioritised to high wildfire-consequence locations.

## 3. Berkeley is named — twice, specifically

**(a) Berkeley is one of PG&E's legacy 4 kV systems.** Exhibit (PG&E-4), p. 9-51:
the 4 kV systems "have been a part of PG&E's distribution network from at least the
1930s" and are found "especially in California's oldest downtown areas, such as San
Francisco, Oakland, **Berkeley**, San Jose, Stockton, Santa Cruz, and Monterey." The
East Bay 4 kV group runs "from Richmond to Hayward." **Over 350,000 customers**
system-wide are served at 4 kV.

**(b) PG&E photographed Berkeley's oldest transformers as its own argument.**
Exhibit (PG&E-4), Figure 9-9, p. 9-56 — the caption is:

> "THREE 4 KV TRANSFORMERS AT **RIDGE SUBSTATION, BERKELEY, INSTALLED IN 1937**"

Two pages earlier, Figure 9-8 is "AGE OF 4 KV SUBSTATION TRANSFORMERS," and the
filing's footnote 64 cites the U.S. Department of the Interior (*Transformers: Basics,
Maintenance, and Diagnostics*, 2005, p. 217): "the average expected life for an
individual transformer is statistically about **40 years**."

**Berkeley substation transformers installed in 1937 are 89 years old, against a
40-year expected life — and PG&E put their photograph in a rate case to make that
point.** This is a gift: it is Berkeley-specific, primary-sourced, visual, and it is
the utility's own characterisation, not ours.

**The remedy, and its timetable.** The 4 kV Voltage Conversion Program (MAT 46A, 06E)
begins in **2027** — $29.0M in 2027, then ~$170.4M a year for 2028, 2029 and 2030
(Table 9-12) — on "a 15 to 20-year timeframe for conversion of all 4 kV substation
transformers and circuits." Berkeley's 1937 units are in scope, sometime in the next
15–20 years.

## 4. A correction the project needs to absorb: the fire premise is the weak one

The brief puts fire first among the three transformer risks. **PG&E's own wildfire
risk model does not support that ranking.** From the WMP's Wildfire Distribution Risk
Model v3 target dataset (Table PG&E-6.2.1-2, p. 160):

| Failure subset | Outage events | Ignitions | Ignitions per outage |
|---|---:|---:|---:|
| Support structure — electrical | 2,096 | 582 | **27.77%** |
| Voltage control equipment | 502 | 99 | 19.72% |
| Animal — other | 834 | 106 | 12.71% |
| Vegetation — other | 1,655 | 184 | 11.12% |
| Primary conductor | 12,343 | 974 | 7.89% |
| **All causes** | **113,884** | **4,197** | **3.69%** |
| **Transformer — equipment cause** | 8,809 | 62 | **0.70%** |
| **Transformer — leaking** | 1,126 | 0 | **0.00%** |

Transformers are among the **lowest** ignition-rate categories in PG&E's model, well
below the 3.69% all-cause average, and leaking transformers produced **zero ignitions
in 1,126 recorded events**. Publishing "aging transformers are a serious wildfire
risk" would be contradicted by the utility's own filing, and we would deserve it.

**What survives, and is stronger:**
- **Toxics.** 1,126 recorded leaking-transformer events is the *oil-on-the-ground*
  number, and it stands whether or not anything ignites. Combined with 40 CFR 761.2 —
  pre-2-July-1979 mineral-oil equipment of unestablished PCB concentration must be
  *assumed* PCB-contaminated — this is the real case.
- **Reliability and cost.** 67,000 known-overloaded units against ~450 replacements a
  year is a defensible scandal on its own terms, and it is PG&E's own number.
- **Age.** 1937 equipment against a 40-year design life, in Berkeley, photographed by
  the utility.

Reframing the cartoon's transformer character around *"nobody has changed my oil, and
nobody is going to for 137 years"* is both more accurate and funnier than a fire scare.

## 5. We can now make a bounded Berkeley estimate — honestly

Previously we refused to estimate, because any customers-per-transformer ratio would
have been invented. It no longer has to be. Exhibit (PG&E-18), Ch. 9, Attachment F,
note [2]:

> "**Average number of customers per residential transformer is 7.**"

That is PG&E's own planning assumption in sworn testimony. With a primary-sourced
Berkeley customer or housing-unit count as the denominator, a residential-transformer
estimate becomes a derivation from two cited numbers rather than a guess.

**Not done yet, deliberately.** Two cautions before anyone publishes a figure:
1. The ratio covers **residential** transformers and does not separate **overhead from
   underground/pad-mounted** — and Berkeley has substantial undergrounding (49% of
   arterials). It would overstate the pole-mounted count.
2. It excludes commercial and industrial services entirely.
The denominator should come from the Census/ACS housing-unit count, and the estimate
must be published as a range with both cautions attached.

## 6. Still not found in these filings

- **No system-wide distribution-transformer unit count.** The 67,000 is the *overloaded*
  subset, not the population. Transformer figures in the GRC are overwhelmingly dollars
  (purchase cost, scrapping) rather than units.
- **No age distribution in extractable text.** Figure 9-8 ("Age of 4 kV Substation
  Transformers") is an image; `pdftotext` yields the caption only. Worth reading the
  figure by eye — it is on p. 9-55 of Exhibit (PG&E-4).
- **Nothing at municipal granularity** beyond the two Berkeley mentions above.
- **Nothing on PCB or fluid type.** Neither filing discusses PCB content or insulating
  fluid. That remains a records-request item, and it confirms manufacture year plus
  test status as the ask.

## 7. What this changes in the requests

Both drafts in `records_requests/` still stand, and get sharper:
- Cite the 67,000 figure back to PG&E and ask for **the Berkeley subset** of it.
  Asking a company to break out its own published number by city is a far smaller ask
  than asking for an asset register.
- Ask specifically for the **Ridge Substation** record and the 4 kV conversion schedule
  for Berkeley — PG&E has already published the photograph and the programme, so the
  schedule is a natural follow-on.
- Drop any framing that leads with wildfire risk from transformers; lead with **leaking
  oil, PCB test status, and the replacement backlog.**
