# tax_incidence — Berkeley property tax reconstruction

Reconstructs the **fixed-charge layer** of Berkeley property tax bills (the majority of a
typical bill, published in no dataset) and models the full stack citywide.

Method, traps and privacy rules: `docs/methodology/berkeley_property_tax_structure.md`.
Findings: `docs/audit/2026-08-15_tax_collector_convergence_and_city_comparison.md`.

## Pipeline

```
bill PDFs (OUTSIDE the repo)            berkeley.db parcels      City taxable sqft
  ~/Desktop/Alameda/parcels/*.pdf        (Alameda assessor)       (9a47-nj4i)
            |                                    |                      |
   parse_bills.py                                |                      |
            |                                    |                      |
   derive_rate_schedule.py  <---------------------------- validates against ----+
            |
   data/derived/berkeley_parcel_tax_rate_schedule_2025-26.json
            |
   model_citywide.py  ------> data/derived/berkeley_sfr_tax_by_decile_2025-26.csv
```

`build_sampling_frame.py` produced the stratified parcel list that the bills were pulled
for; rerun it to draw a new sample.

## Run

```bash
python -m scripts.tax_incidence.derive_rate_schedule   # bills  -> rate schedule
python -m scripts.tax_incidence.model_citywide         # schedule -> citywide model
```

Requires `pdftotext` (`brew install poppler`) and network access for the City sqft API.

## Inputs that are NOT in this repo

Bill PDFs are a household's assessed value, payment dates and delinquency history — public
record, but this repo publishes to berkeleybuild.com. They live in `~/Desktop/Alameda/`.
To reproduce, pull bills from https://propertytax.alamedacountyca.gov/ for the APNs in a
sampling frame (Parcel Number tab; you must click the auto-suggest entry, typing alone does
nothing), then View Bill → Print Copy of Bill.
