# Berkeley Housing Pipeline - Datasette

**Live site:** https://berkeley-housing.fly.dev

**Regenerate with `.venv/bin/python scripts/gen_datasette_dbs.py` -- never hand-build.** It reads the canonical **v4**
database's serving views (read-only; re-pointed from v2 on 2026-10-01), writes `berkeley_housing_map.db`, `czu.db`
and `metadata.json` here, and prints a was/now table. Nothing is deployed until someone runs `flyctl deploy`.

**Publishing rule (2026-10-01):** organizations are named; private individuals appear as "individual owner" (owners)
or "individual" (applicants); Rent Board tenancy dates are shown as the year. The full data stays in v4.

## berkeley_housing_map.db (as generated)
<!-- rows:start (written by gen_datasette_dbs.py) -->
| table | rows |
|---|---|
| projects | 1,554 |
| timeline | 12,191 |
| people | 12,741 |
| businesses | 282 |
| city_records | 9,290 |
| adu_rent_board | 684 |
| permits | 2,449 |
| parcels | 1,572 |
| documents | 266 |
<!-- rows:end -->

`czu.db` holds the Corridors Zoning Update layers from CPRA #26-2367; `berkeley_address_centric.db` is the older
hand-built address database, served unchanged.
