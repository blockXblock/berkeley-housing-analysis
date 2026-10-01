# Berkeley Housing Pipeline - Datasette

**Live site:** https://berkeley-housing.fly.dev

**Regenerate with `.venv/bin/python scripts/gen_datasette_dbs.py` -- never hand-build.** It reads the canonical **v4**
database's serving views (read-only; re-pointed from v2 on 2026-10-01), writes `berkeley_housing_map.db`, `czu.db`
and `metadata.json` here, and prints a was/now table. Nothing is deployed until someone runs `flyctl deploy`.

**Publishing rule (2026-10-01):** organizations are named; private individuals appear as "individual owner" (owners)
or "individual" (applicants); Rent Board tenancy dates are shown as the year. The full data stays in v4.

## berkeley_housing_map.db (as generated)
| table | rows |
|---|---|
| projects | 1,544 |
| timeline | 12,183 |
| people | 12,607 |
| businesses | 282 |
| city_records | 9,289 |
| adu_rent_board | 684 |
| permits | 2,445 |
| parcels | 1,559 |
| documents | 263 |

`czu.db` holds the Corridors Zoning Update layers from CPRA #26-2367; `berkeley_address_centric.db` is the older
hand-built address database, served unchanged.
