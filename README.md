# Berkeley Housing Development Analysis

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/blockXblock/berkeley-housing-analysis/HEAD?labpath=notebooks%2FMASTER_ANALYSIS.ipynb)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/notebooks/MASTER_ANALYSIS.ipynb)

> Interactive analysis of **84 housing development projects** in Berkeley, CA (2020-2025)

## 🚀 Quick Start

**Run in Browser (No Installation):**  
Click the Binder badge above ⬆️ (takes 2-3 min first time)

**Or Run Locally:**
```bash
git clone https://github.com/johngage/berkeley-housing-analysis.git
cd berkeley-housing-analysis
pip install -r requirements.txt
jupyter notebook notebooks/MASTER_ANALYSIS.ipynb
```

## 📊 What's Inside

- **84 housing projects** totaling **6,363 net new units**
- **100% geocoded** using Alameda County GIS address points
- **Interactive maps** color-coded by project size
- **SQL database** with analysis queries
- **Automated reports** in Markdown format
- **Data refresh workflow** (Level 1: status check, Level 2: rebuild)

## 🗺️ Interactive Map

Projects color-coded by size:
- 🔴 200+ units (Large)
- 🟠 100-199 units (Medium-Large)  
- 🔵 50-99 units (Medium)
- 🟢 20-49 units (Small-Medium)
- ⚪ <20 units (Small)

## 📁 Repository Structure
```
berkeley-housing-analysis/
├── notebooks/
│   └── MASTER_ANALYSIS.ipynb       # Complete analysis workflow
├── housing_projects_FINAL_COMPLETE.csv  # Geocoded project data (84 projects)
├── outputs/                         # Generated files (created when you run notebook)
│   ├── berkeley_housing_map.html
│   ├── berkeley_housing_analysis.db
│   └── ANALYSIS_REPORT.md
└── README.md
```

## 🔄 Data Refresh

**Current Data:** December 20, 2024

The notebook includes two refresh options:

### Level 1: Quick Status Check
- Verify data files
- Check geocoding coverage
- ~30 seconds

### Level 2: Complete Rebuild
**Note:** Berkeley's Open Data Portal currently restricts API access. We're working on alternative data access methods.

**To refresh data manually:**
1. Contact Berkeley Planning Department: planning@berkeleyca.gov
2. Request recent building permits dataset
3. Follow notebook instructions for processing

**Issue Tracker:** See [#1](link) for updates on automated refresh

## 📈 Sample Analysis

From the current dataset:

- **Total Units:** 6,363 net new housing units
- **Timeline:** 2020-2025
- **Average Project Size:** 75.8 units
- **Largest Project:** 698 units
- **Top Streets:** Analysis by development activity

Run the notebook to see complete statistics!

## 🛠️ Technical Details

**Built with:**
- Python 3.8+
- pandas (data analysis)
- folium (interactive maps)
- SQLite (database)
- Jupyter notebooks

**Data Sources:**
- Berkeley Planning Department (building permits)
- Alameda County GIS (address geocoding with 563k+ address variations)

## 📚 Use Cases

- **Civic Engagement:** Track housing development in your neighborhood
- **Urban Planning:** Analyze development patterns and trends
- **Policy Research:** Compare proposed vs. actual housing production
- **Education:** Learn data analysis with real civic data
- **Journalism:** Data-driven housing stories

## 🤝 Contributing

Issues and pull requests welcome! Especially:
- Alternative data sources for Berkeley permits
- Additional analysis queries
- Visualization improvements
- Documentation enhancements

## 📜 License

**Public Domain** - Free to use for research, education, civic engagement, or journalism

## 🙏 Acknowledgments

- Berkeley Planning Department for public data
- Alameda County for GIS address points
- BuildBerkeley.online community

## 📧 Contact

Questions? Open an issue or visit [BuildBerkeley.online](https://buildberkeley.online)

---

**Note:** This is a community project analyzing public data. Not affiliated with the City of Berkeley.
