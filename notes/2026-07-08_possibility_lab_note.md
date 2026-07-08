# Note to the Possibility Lab — the JN sequence as a multi-city APR builder

*Drafted 2026-07-08 for Laura, Amy, and Lindsay (Possibility Lab). Web version:
`docs/possibility-lab-test.html` (linked from the Mayor's brief title slide as
"PL Multi-City Open Data APR Test").*

Over the past month we distilled the Berkeley reconstruction into a teachable
notebook sequence that takes anyone from a city's raw permit spreadsheets to a
scored, independently verified APR. The pipeline is seven short Jupyter
notebooks (plus a no-coding-required on-ramp for beginners): **JN1** ingests
the city's messy permit export exactly as it arrives — title rows, buried
headers, the traps where honest mistakes are born; **JN2** builds the address
key; **JN3** assembles the project spine and unit counts; **JN4** orders each
project's permits into lifecycle events (application → issuance → certificate
of occupancy); **JN5** tags calendar years and RHNA cycles; **JN6a** pulls the
city's own APR filing from HCD's statewide open-data portal — used strictly as
a verification target, never as an input; and **JN6b** joins the two and
scores every difference, row by row. Each notebook opens free in Google Colab
with one click from **berkeleybuild.com/data-science-curriculum.html** and
fetches its data automatically from our public archive, so **to rebuild the
Berkeley APR** a student needs nothing but a browser: open JN1, run it top to
bottom, and continue through JN6b (a one-line switch in the setup cell skips
ingestion and starts from our cleaned permit table instead). **To do the same
for another city**, only JN1's configuration cell changes — two values: the
path to that city's permit ledger and the row its column headings sit on.
Oakland exports a full month of permits in one click from its public Accela
portal (we verified this on July 3rd); San Francisco publishes its permit
ledger on DataSF; Delano or Fresno would take a single public-records request
for the same annual building-permit report Berkeley gave us. The scoring step
needs no change at all: HCD's portal carries every California city's APR, so
JN6a's oracle works statewide.

---

**Caveats kept out of the letter body** (for our own record): the "two knobs"
claim is literal (JN1's config cell), but a city whose permit ledger lacks
unit counts would need adaptation at JN3. The Oakland one-click bulk export
was live-probed 2026-07-03 (deck slide 7 specimen, committed). The DataSF
claim is not yet live-probed.
