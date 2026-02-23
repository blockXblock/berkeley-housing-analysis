# Berkeley Housing Pipeline - Presenter Notes

**Date:** February 23, 2026
**Duration:** ~45-60 minutes
**Audience:** Technical (can run Colab)

---

## Pre-Call Checklist

- [ ] Open landing page: https://blockxblock.github.io/berkeley-housing-analysis/
- [ ] Open Live Map in separate tab: https://berkeley-housing.fly.dev/
- [ ] Open Colab in separate tab (don't run yet): [MASTER_ANALYSIS](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/MASTER_ANALYSIS.ipynb)
- [ ] Have GitHub repo ready: https://github.com/blockXblock/berkeley-housing-analysis
- [ ] Test screen share

---

## Section 1: Opening (5 min)

### Share: Landing Page

**Key Stats to Highlight:**
- **115 housing projects** tracked in Berkeley
- **5,470 net new units** in the pipeline (2020-2026)
- **96.5% APN coverage** - almost every project matched to parcel
- **100% geocoded** - every project on the map

**Talking Points:**
> "This project tracks every significant housing development in Berkeley from initial application through certificate of occupancy. The goal is twofold: transparency for the public, and compliance with California's Annual Progress Report requirements."

> "Everything you see today is reproducible. The data pipeline runs in Google Colab - no local setup needed. By the end of this session, you'll be able to run this analysis yourself."

**Transition:**
> "Let me show you what the data looks like on a map."

---

## Section 2: Live Map Demo (5-7 min)

### Share: berkeley-housing.fly.dev

**Click Through:**
1. **Zoom to downtown** - show project clusters
2. **Click a large project** (e.g., 2190 Shattuck) - show popup with details
3. **Show the data table** - click "projects" in left sidebar
4. **Run a SQL query** - show the query interface

**Sample Query to Run:**
```sql
SELECT address_display, net_units, status, year
FROM projects
WHERE net_units > 50
ORDER BY net_units DESC
```

**Talking Points:**
> "This is Datasette - it turns a SQLite database into an instant API and web interface. No backend code needed."

> "Anyone can query this data. Journalists, advocates, city staff - they don't need to know Python, just basic SQL."

> "The map uses Leaflet.js with cluster markers. Each dot is a project; color indicates status."

**Transition:**
> "Now let's look at how this data gets created. I'll share my screen with Colab, and I'd encourage everyone to open the link in the chat and follow along."

---

## Section 3: Colab Walkthrough (20-25 min)

### Share: MASTER_ANALYSIS.ipynb in Colab

**Post in Chat:**
```
Open this link to follow along:
https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/MASTER_ANALYSIS.ipynb
```

**Wait 1-2 minutes for people to open it.**

### Cell-by-Cell Guide:

#### Setup Cell (Cell 1-2)
**Run it, explain while loading:**
> "This first cell detects whether we're in Colab or running locally, then sets up the environment. It clones the GitHub repo and configures paths."

> "Notice the CONFIG system - all paths are relative, so this works anywhere: Colab, Binder, your laptop."

#### Load Data (Cell 3-4)
**Run it:**
> "We're loading 115 housing projects from CSV. Each record has: address, coordinates, unit counts, permit numbers, status, and year."

**Point out:**
- `net_units` = new_units - old_units (handles demolitions)
- `status` comes directly from city permit system
- `apn` is the Assessor Parcel Number for state reporting

#### Summary Statistics (Cell 5-6)
**Run it:**
> "5,470 net new units across 115 projects. The median project is about 20 units, but a few large projects dominate."

**Key insight:**
> "The top 10 projects account for over 60% of all units. Housing production is very concentrated."

#### Map Generation (Cell 7-8)
**Run it:**
> "This generates an interactive map right here in the notebook. Same technology as the live site."

**Let people zoom around.**

#### Status Analysis (Cell 9-10)
**Run it:**
> "Here's where projects stand in the pipeline. Notice how many are stuck in 'Under Review' vs actually approved and building."

**Talking point:**
> "This is the 'pipeline funnel' - not everything proposed gets built. Understanding attrition helps set realistic expectations."

#### Year Trends (Cell 11-12)
**Run it:**
> "Unit counts by year. You can see the impact of policy changes, economic cycles, and COVID."

---

## Section 4: Pipeline Deep Dive (10 min)

### Show: Notebook Structure

**Explain the 4 stages:**

> "The full pipeline has 12 notebooks organized in 4 stages:"

**Stage A - Collection:**
> "A1 connects to Berkeley's API - which is often blocked by their firewall, so we have manual fallbacks. A2 standardizes addresses - '1914 FIFTH St' and '1914 5th Street' need to match. A3 geocodes everything using a 563,000-address lookup table."

**Stage B - Tracking:**
> "B1 tracks the permit lifecycle - zoning to building permit to certificate of occupancy. B2 classifies messy status values into clean categories. B3 flags stalled projects - anything stuck more than 180 days."

**Stage C - Analysis:**
> "C1 calculates conversion rates - how many proposed units actually get built? C2 analyzes processing times - where are the bottlenecks? C3 connects to RHNA - California's Regional Housing Needs Allocation."

**Stage D - Reporting:**
> "D1 generates monthly reports. D2 creates the Datasette deployment. D3 sets up alerts for status changes."

**Talking point:**
> "Each notebook has Learning Objectives and 'Why This Matters' sections. We're building this into an online course."

---

## Section 5: APR Compliance (7-10 min)

### Share: Datasette APR Views

**Go to:** https://berkeley-housing.fly.dev/berkeley_housing_apr/

**Show each view:**

1. **apr_table_a2**
> "This is formatted for HCD Table A2 - the Annual Building Activity Report. Columns match the state template."

2. **apr_rhna_progress**
> "RHNA progress by year. This shows how many units Berkeley has permitted toward its 8,934-unit target."

3. **apr_streamlining**
> "Projects using SB35, SB330, or AB2011 streamlining. These are ministerial approvals that bypass some review."

**Honest Assessment:**
> "We have good coverage on addresses, APNs, and unit counts. The gap is income categories - we need to manually classify projects as Very Low, Low, Moderate, or Above Moderate income. That requires reviewing each project's affordability agreements."

**Show compliance table:**
| Field | Status |
|-------|--------|
| Address, APN, Units | ✅ Ready |
| Unit Category, Tenure | ✅ Ready |
| Income Breakdown | ❌ Needs manual review |
| Permit Dates | ⚠️ In progress |

---

## Section 6: Q&A and Next Steps (5-10 min)

**Prompt questions:**
> "What questions do you have about the data, the pipeline, or APR compliance?"

**Common questions and answers:**

**Q: How often is data updated?**
> "Currently manual - we run `update_housing_data.py` when new Excel exports are available from the city. Goal is monthly updates."

**Q: Can this work for other cities?**
> "Yes - the pipeline is designed to be portable. You'd need to adapt the data sources (different APIs, different file formats) but the analysis and reporting stages are reusable."

**Q: What about the income categories?**
> "That's our biggest gap. Options: 1) Parse project descriptions for affordability mentions, 2) Cross-reference with city housing department records, 3) Manual review of the 17 largest projects. We've started extracting what we can from descriptions."

**Q: How do we contribute?**
> "GitHub issues and PRs welcome. The repo is public. Specific needs: income data validation, permit date extraction, documentation improvements."

---

## Closing

**Share: Landing page one more time**

> "To recap - everything is available at these links:"

| Resource | What It Is |
|----------|------------|
| Landing Page | Overview and quick links |
| Live Map | Browse projects interactively |
| Colab | Run the full analysis yourself |
| GitHub | Source code and data |

> "The Colab notebook you just ran is the same one powering everything else. If you can run that, you can reproduce our entire analysis."

> "Thank you for your time. I'll stay on for questions."

---

## Backup Material

### If Someone Has Colab Issues:

1. Make sure they're signed into Google
2. Try: Runtime → Run all
3. If still stuck: "You can watch my screen - we'll share the recording"

### If Map Isn't Loading:

Fly.dev occasionally sleeps. Give it 10-15 seconds to wake up, or:
> "The free tier sleeps after inactivity. It's waking up now."

### Key Numbers to Remember:

- **115** projects
- **5,470** units
- **96.5%** APN coverage
- **563K** addresses in geocoding lookup
- **8,934** Berkeley's RHNA target (2023-2031)
- **4 stages**, **12 notebooks**

---

## Post-Call Follow-Up Email Template

```
Subject: Berkeley Housing Pipeline - Resources from Today's Call

Hi everyone,

Thank you for joining today's session. Here are the links we discussed:

**Quick Access:**
- Landing Page: https://blockxblock.github.io/berkeley-housing-analysis/
- Live Map: https://berkeley-housing.fly.dev/
- Run in Colab: [MASTER_ANALYSIS](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/MASTER_ANALYSIS.ipynb)
- GitHub: https://github.com/blockXblock/berkeley-housing-analysis

**Key Stats:**
- 115 housing projects tracked
- 5,470 net new units (2020-2026)
- 96.5% APN coverage for state reporting

**Next Steps:**
- [Add any action items discussed]

Questions? Reply to this email or open a GitHub issue.

Best,
[Your name]
```
