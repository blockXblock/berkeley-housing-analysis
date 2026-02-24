# Berkeley Housing Permit Pipeline

Interactive map and database tracking 115 housing development projects in Berkeley, CA (2020-2026).

## Live Map
Visit: https://blockxblock.github.io/berkeley-housing-analysis/

## Statistics
- **115** projects tracked
- **5,470** total housing units
- **6** projects with full permit timeline
- **58** permit events recorded
- **$82,784** in fees tracked
- **2020-2026** timeline

## Timeline Tracking (NEW)

We now track the complete permit lifecycle:

| Stage | Data Captured |
|-------|---------------|
| Filing | First permit submission date |
| Completeness Review | Rounds of corrections |
| CEQA Determination | Exemption or environmental review |
| Staff Decision | Approval/denial date |
| Appeal | Appeal to City Council |
| Issuance | Building permit issued |
| Certificate of Occupancy | Project completion |

### Projects with Full Timeline Data
1. **1750 Sacramento St** - 739 units - In Review
2. **2276 Shattuck Ave** - 336 units - Landmarks Approved
3. **2700 Shattuck Ave** - 276 units - Planning
4. **1914 Fifth St** - 257 units - Stalled (5+ years)
5. **2425 Durant Ave** - 250 units - Under Appeal
6. **2029 University Ave** - 240 units - Approved

## Data Sources
- Berkeley Planning Department (Accela Citizen Access)
- Berkeley Building Department (Accela)
- Alameda County GIS (geocoding)

## Features
- Clustered markers for better performance
- Color-coded by project size
- Popup details for each project
- Mobile-responsive design
- Timeline tracking with dual timestamps (action date + import date)

## Embedding
To embed this map in your website:
```html
<iframe src="https://blockxblock.github.io/berkeley-housing-analysis/"
        width="100%" height="900" frameborder="0">
</iframe>
```

## Explore the Data
- **Live Database:** https://berkeley-housing.fly.dev/
- **GitHub Repository:** https://github.com/blockXblock/berkeley-housing-analysis
- **Run in Colab:** [Master Analysis Notebook](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/MASTER_ANALYSIS.ipynb)

## Database Schema

```
projects (115 records)
├── address, apn, net_units, status
├── first_filed_date, zoning_approved_date
├── building_permit_date, co_issued_date
└── updated_at (when we last updated)

project_permits (47 records)
├── permit_number, permit_type, filed_date
└── imported_at

permit_events (58 records)
├── stage, action, event_date (when it happened)
└── imported_at (when we recorded it)

permit_fees (12 records)
├── amount, payment_date
└── imported_at
```

## License
Public Domain (CC0)
