# Berkeley Housing Pipeline - Datasette

Interactive database tracking 115 Berkeley housing projects (5,470 units) with permit timeline data.

**Live Site:** https://berkeley-housing.fly.dev

## Features
- Interactive OpenStreetMap with clustering
- SQL query interface
- Filter by year, project size, permit type, status
- Export data as CSV/JSON
- **Timeline tracking** with permit events
- **Fee tracking** for projects

## Data
- **115** housing projects
- **5,470** total units
- **47** permits linked
- **58** permit events tracked
- **$82,784** in fees recorded

## Tables
| Table | Records | Description |
|-------|---------|-------------|
| projects | 115 | Master project list with timeline dates |
| project_permits | 47 | Individual permits by project |
| permit_events | 58 | Processing status events with dates |
| permit_fees | 12 | Fee payment records |
| project_velocity | view | Days at each stage analysis |

## Canned Queries
- Stalled Projects (180+ days inactive)
- Project Timeline Events
- Fees by Project
- Permits by Year

## Data Sources
- City of Berkeley Planning Department (Accela)
- City of Berkeley Building Department (Accela)

## Tech Stack
- Datasette (database UI)
- datasette-cluster-map (mapping)
- Fly.dev (hosting)
- SQLite (database)

## Deployment
```bash
flyctl deploy
```

## About
Part of [Berkeley Housing Analysis](https://blockxblock.github.io/berkeley-housing-analysis/)
