- date: 2026-05-02


⏺ All 3 tasks complete. Ready for your review before finalizing:

  1. ✅ Fixed 4 missing unit counts (+486 units to completed total)
  2. ✅ Showed 1507 Josephine record (recommend units=-1, category=housing_loss)
  3. ✅ Added project_category column with 174 projects categorized

  Pending decisions:
  - Update 1507 Josephine to units=-1 and category=housing_loss?
  - Fix 1136 Keith Ave category to housing_replacement?
  - Investigate 2903 Adeline & 3036 Regent (commercial→residential conversions)?
  - What to do with 2820 San Pablo (no description)?
- ⏺ 10 Random Unmatched SFYIMBY Projects — Verification Results

  | #   | Address                       | SFYIMBY Data                                      | Verification Result                                                                                                           |
  |-----|-------------------------------|---------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
  | 1   | People's Park                 | 1,113 units, "UC approved" (Oct 2021)             | ✅ REAL & ACTIVE — Topped out Aug 2025, opening Fall 2027. UC Berkeley project, not in City permit system.                    |
  | 2   | 2900 Shattuck Ave             | 221 units, "plans filed" (Mar 2022)               | ⚠️ DUPLICATE — This is likely 2920 Shattuck Ave in main DB. Same developer (NX Ventures), same unit count.                    |
  | 3   | 1822-1828 San Pablo Ave       | 44 units, "plans revealed" (Aug 2022)             | ✅ REAL — 5-story mixed-use by Gunkel Architecture. Status unclear, may need Accela lookup.                                   |
  | 4   | 2012 Berkeley Way             | units TBD, "affordable housing opened" (Nov 2022) | ✅ COMPLETED — 142 units (89 affordable + 53 supportive). Opened Oct 2022. Should be in DB as completed.                      |
  | 5   | 2352 Shattuck Ave ph2         | 69 units, "permits filed" (Jul 2021)              | ⚠️ DUPLICATE — Phase 2 of Logan Park. Phase 1 (135 units) + Phase 2 (69 units) = 204 total. May be tracked as single project. |
  | 6   | 1130 Oxford St                | units TBD, "preliminary permits" (Jan 2026)       | ✅ REAL & ACTIVE — Former Oxford Elementary. Sold to Panoramic Interests Oct 2025 for $3M. Early planning stage.              |
  | 7   | 3000 San Pablo Ave            | units TBD, "permits filed" (Dec 2020)             | ✅ COMPLETED — 78 units "Aquatic Ashby" by Read Investments/Trachtenberg. Now leasing. Should be in DB.                       |
  | 8   | 2132 Center St (The Hub)      | 283 units, "renderings updated" (Mar 2022)        | ✅ REAL & ACTIVE — Now 456 units, 26 stories. Approved Sep 2024 by ZAB. Major project, should be in DB.                       |
  | 9   | 1921 Walnut St (Anchor House) | 772 bedrooms, "excavation underway" (May 2022)    | ✅ COMPLETED — Helen Diller Anchor House opened Aug 2024. 772 beds, $300M UC Berkeley project.                                |
  | 10  | 2660-2680 Bancroft Way        | 115 units, "pre-application" (Apr 2023)           | ✅ REAL & ACTIVE — 8-story + hotel conversion. Zoning permits filed Mar 2024. Studio KDA architect.                           |

  ---
  Summary

  | Category                    | Count | Action                                      |
  |-----------------------------|-------|---------------------------------------------|
  | Real & Active               |   5   | Add to main projects table                  |
  | Completed (missing from DB) |   3   | Add with status=Completed                   |
  | Likely Duplicates           |   2   | Verify address match, merge if same project |

  Specific Issues Found

  1. UC Projects not tracked — People's Park, Anchor House are UC Berkeley developments outside City permit system
  2. Address variations — "2900 Shattuck" vs "2920 Shattuck", "2352 Shattuck ph2" vs main entry
  3. Completed projects missing — 2012 Berkeley Way (142 units), 3000 San Pablo (78 units), Anchor House (772 beds)
  4. Outdated unit counts — The Hub grew from 283 → 456 units


Sources

  - https://peoplesparkhousing.berkeley.edu/
  - https://sfyimby.com/2022/06/renderings-revealed-for-2900-shattuck-avenue-in-south-berkeley.html
  - https://sfyimby.com/2022/08/plans-revealed-for-1822-1828-san-pablo-avenue-northwest-berkeley.html
  - https://sfyimby.com/2022/11/largest-affordable-housing-project-in-berkeley-opens-at-2012-berkeley-way.html
  - https://sfyimby.com/2021/03/construction-topped-out-for-phase-one-of-2352-shattuck-avenue-downtown-berkeley.html
  - https://www.berkeleyside.org/2025/10/21/oxford-elementary-site
  - https://sfyimby.com/2020/12/permits-filed-for-3000-san-pablo-avenue-southwest-berkeley.html
  - https://www.berkeleyside.org/2024/09/13/hub-berkeley-zoning-adjustments-board-use-permit
  - https://www.berkeleyside.org/2024/08/02/helen-diller-anchor-house-opening-uc-berkeley
  - https://sfyimby.com/2024/03/zoning-permits-submitted-for-2660-2680-bancroft-way-berkeley.html

---
A future session worth scoping: pull Accela's complete list of multifamily building permits issued 2018-2024, cross-reference against your projects table, find the gaps. That's the actual answer to "is our pipeline complete?" Not by checking SFYIMBY's curated articles, but by querying the city's source-of-record directly.