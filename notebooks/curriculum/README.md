# The Berkeley Housing Data Curriculum

A hands-on course that takes a curious beginner — no coding required to start — from a city's
raw permit spreadsheets to a scored, independently verified housing record. The course page
with the full sequence and one-click Colab links: **https://berkeleybuild.com/data-science-curriculum.html**

## Two ways to run the notebooks

**1. Google Colab (nothing to install).** Click any notebook's Colab badge on the course page
(or open it from this folder on GitHub via Colab). Each notebook's first code cell fetches the
data it needs — the city's permit spreadsheets, the shared helper modules, and the pinned state
filing — from our public archive automatically.

**2. Locally, with git clone (recommended for the full experience).**

```bash
git clone https://github.com/blockXblock/berkeley-housing-analysis.git
cd berkeley-housing-analysis
jupyter lab notebooks/curriculum/JN00_look_first.ipynb
```

The repo already contains everything the notebooks download in Colab — the raw CPRA
spreadsheets (`data/raw/cpra-downloads/`), the shared modules (`scripts/`), and the pinned
HCD mirror (`databases/`) — so the bootstrap cell detects the repo and **skips all downloads**.
You need Python 3.10+ with `pandas`, `openpyxl`, `pyarrow`, and `jupyter`.

## The sequence

| Stage | Notebooks | What you learn |
|---|---|---|
| The on-ramp | JN00, JN0a–JN0h | Look at the data first; the vocabulary from zero (data, notebooks, functions, tables, charts, tools, agents) |
| Build the record | JN1–JN5 | Ingest the messy export, build the address key, assemble projects & units, order lifecycle events, tag years & RHNA cycles |
| Grade the answer key | JN6a, JN6b | Pull the city's own state filing (as a verification target, never an input) and score every difference |
| Audit yourself | JN7 | Re-key buildings to permit families; run the audit's error-detectors |
| Never stop watching | JN8 | Pin a snapshot, re-pull the live filing, diff — the record watches itself |

## Adapting it to another city

Only JN1's configuration cell changes — the path to your city's permit ledger and its header
row. The verification oracle (JN6a) already works statewide: HCD's open-data portal carries
every California city's APR. See https://berkeleybuild.com/possibility-lab-test.html for
live-verified notes on Oakland, San Francisco, Fresno, and Delano.
