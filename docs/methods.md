# Methods & Data Quality

This section covers the core data science methods used in the project, plus how we ensure data quality.

## Core Methods

### [C0: Methods Overview](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/03_analysis/C0_methods_overview.ipynb)

A reference guide to patterns you'll use throughout the project:

**Table Joins**
- Connecting permits, projects, parcels, and zoning data
- Inner vs left vs outer joins
- When to use each type

**Grouping & Aggregation**
- Counting projects by status
- Summing units by year
- Calculating averages and percentages

**Visualization**
- Bar charts for comparisons
- Line charts for trends
- Reusable plotting functions

**Using Modules**
- How to import project code
- Address normalization
- Geocoding functions

## Data Quality

### [C4: Quality Checks](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/03_analysis/C4_quality_checks.ipynb)

Learn patterns for ensuring data quality:

**Soft Asserts**
- Check conditions without crashing
- Log all issues at once
- Categorize by severity

**Common Checks**
- Missing values (nulls)
- Duplicate records
- Invalid value ranges
- Geographic bounds validation

**Aggregate Validation**
- Compare totals to expected values
- Verify distributions make sense
- Flag outliers for review

**Quality Reports**
- Generate summary of data health
- Track issues over time
- Document data lineage

## Why This Matters

In civic data, errors have consequences:
- Bad data → wrong reports → compliance issues
- Missing records → incomplete maps → hidden projects
- Duplicates → inflated counts → misleading statistics

**Quality checks aren't optional—they're essential infrastructure.**

## Skills You'll Learn

These patterns are reusable far beyond housing data:
- Any tabular data analysis
- API data validation
- Report generation
- Monitoring systems

## Notebooks

| Notebook | Purpose |
|----------|---------|
| [C0_methods_overview](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/03_analysis/C0_methods_overview.ipynb) | Reference guide to core patterns |
| [C4_quality_checks](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/03_analysis/C4_quality_checks.ipynb) | Data validation techniques |
