#!/bin/bash

# ==========================================================
# Accela Data Collection Script - Interactive Version
# ==========================================================
#
# Instructions:
# 1. Open https://aca-prod.accela.com/BERKELEY/ in your browser
# 2. For each permit, search by permit number
# 3. Copy the "Processing Status" section to clipboard
# 4. Press Enter when prompted to save
#
# ==========================================================

DIR="/Users/johngage/berkeley-data/data/raw/accela_status"
COUNT=0

echo "=========================================================="
echo "ACCELA DATA COLLECTION - Tier 1 + Tier 2 (28 projects)"
echo "=========================================================="
echo ""
echo "Open https://aca-prod.accela.com/BERKELEY/ in your browser"
echo ""
read -p "Press Enter when ready to begin..."
echo ""

# ==========================================================
# TIER 1: City APR 2024 Validation (21 projects, 2133 units)
# ==========================================================

echo "=========================================================="
echo "TIER 1: City APR 2024 Validation (21 projects)"
echo "=========================================================="
echo ""

# 1
COUNT=$((COUNT + 1))
echo "[$COUNT/28] B2025-05534 | 1750 SACRAMENTO St | 739 units"
echo "Search for: B2025-05534"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/B2025-05534_1750_SACRAMENTO_St.txt"
echo "Saved: $(wc -l < "$DIR/B2025-05534_1750_SACRAMENTO_St.txt") lines"
echo ""

# 2
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0058 | 2700 SHATTUCK Ave | 276 units"
echo "Search for: ZP2024-0058"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0058_2700_SHATTUCK_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0058_2700_SHATTUCK_Ave.txt") lines"
echo ""

# 3
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0074 | 1581 UNIVERSITY Ave | 158 units"
echo "Search for: ZP2024-0074"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0074_1581_UNIVERSITY_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0074_1581_UNIVERSITY_Ave.txt") lines"
echo ""

# 4
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2022-0132 | 2847 SHATTUCK Ave | 132 units"
echo "Search for: ZP2022-0132"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2022-0132_2847_SHATTUCK_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2022-0132_2847_SHATTUCK_Ave.txt") lines"
echo ""

# 5
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0066 | 2109 VIRGINIA St | 131 units"
echo "Search for: ZP2024-0066"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0066_2109_VIRGINIA_St.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0066_2109_VIRGINIA_St.txt") lines"
echo ""

echo ">>> TIP: You can verify progress so far with:"
echo ">>> python /Users/johngage/berkeley-data/scripts/accela_workflow.py save_batch --db /Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db --dir $DIR"
echo ""
read -p "Press Enter to continue..."
echo ""

# 6
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2023-0058 | 2720 SAN PABLO Ave | 113 units"
echo "Search for: ZP2023-0058"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2023-0058_2720_SAN_PABLO_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2023-0058_2720_SAN_PABLO_Ave.txt") lines"
echo ""

# 7
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2023-0099 | 2109 MILVIA St | 105 units"
echo "Search for: ZP2023-0099"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2023-0099_2109_MILVIA_St.txt"
echo "Saved: $(wc -l < "$DIR/ZP2023-0099_2109_MILVIA_St.txt") lines"
echo ""

# 8
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0057 | 2655 SHATTUCK Ave | 97 units"
echo "Search for: ZP2024-0057"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0057_2655_SHATTUCK_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0057_2655_SHATTUCK_Ave.txt") lines"
echo ""

# 9
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0047 | 2450 SHATTUCK Ave | 94 units"
echo "Search for: ZP2024-0047"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0047_2450_SHATTUCK_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0047_2450_SHATTUCK_Ave.txt") lines"
echo ""

# 10
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0079 | 2036 BANCROFT Way | 85 units"
echo "Search for: ZP2024-0079"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0079_2036_BANCROFT_Way.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0079_2036_BANCROFT_Way.txt") lines"
echo ""

echo ">>> TIP: You can verify progress so far with:"
echo ">>> python /Users/johngage/berkeley-data/scripts/accela_workflow.py save_batch --db /Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db --dir $DIR"
echo ""
read -p "Press Enter to continue..."
echo ""

# 11
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0114 | 2138 KITTREDGE St | 66 units"
echo "Search for: ZP2024-0114"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0114_2138_KITTREDGE_St.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0114_2138_KITTREDGE_St.txt") lines"
echo ""

# 12
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0126 | 2298 DURANT Ave | 65 units"
echo "Search for: ZP2024-0126"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0126_2298_DURANT_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0126_2298_DURANT_Ave.txt") lines"
echo ""

# 13
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2023-0090 | 2733 SAN PABLO Ave | 32 units"
echo "Search for: ZP2023-0090"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2023-0090_2733_SAN_PABLO_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2023-0090_2733_SAN_PABLO_Ave.txt") lines"
echo ""

# 14
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0033 | 2317 CHANNING Way | 22 units"
echo "Search for: ZP2024-0033"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0033_2317_CHANNING_Way.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0033_2317_CHANNING_Way.txt") lines"
echo ""

# 15
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0096 | 2147 SAN PABLO Ave | 15 units"
echo "Search for: ZP2024-0096"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0096_2147_SAN_PABLO_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0096_2147_SAN_PABLO_Ave.txt") lines"
echo ""

echo ">>> TIP: You can verify progress so far with:"
echo ">>> python /Users/johngage/berkeley-data/scripts/accela_workflow.py save_batch --db /Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db --dir $DIR"
echo ""
read -p "Press Enter to continue..."
echo ""

# 16
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0059 | 2204 DWIGHT Way | 2 units"
echo "Search for: ZP2024-0059"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0059_2204_DWIGHT_Way.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0059_2204_DWIGHT_Way.txt") lines"
echo ""

# 17
COUNT=$((COUNT + 1))
echo "[$COUNT/28] PLN2024-0024 | 0 LE ROY Ave | 1 units"
echo "Search for: PLN2024-0024"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/PLN2024-0024_0_LE_ROY_Ave.txt"
echo "Saved: $(wc -l < "$DIR/PLN2024-0024_0_LE_ROY_Ave.txt") lines"
echo ""

# 18
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0112 | 3035 COLBY St | 0 units"
echo "Search for: ZP2024-0112"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0112_3035_COLBY_St.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0112_3035_COLBY_St.txt") lines"
echo ""

# 19
COUNT=$((COUNT + 1))
echo "[$COUNT/28] PLN2024-0047 | 1136 KEITH Ave | 0 units"
echo "Search for: PLN2024-0047"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/PLN2024-0047_1136_KEITH_Ave.txt"
echo "Saved: $(wc -l < "$DIR/PLN2024-0047_1136_KEITH_Ave.txt") lines"
echo ""

# 20
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0122 | 3036 REGENT St | 0 units"
echo "Search for: ZP2024-0122"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0122_3036_REGENT_St.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0122_3036_REGENT_St.txt") lines"
echo ""

echo ">>> TIP: You can verify progress so far with:"
echo ">>> python /Users/johngage/berkeley-data/scripts/accela_workflow.py save_batch --db /Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db --dir $DIR"
echo ""
read -p "Press Enter to continue..."
echo ""

# 21
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0138 | 2145 GRANT St | 0 units"
echo "Search for: ZP2024-0138"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0138_2145_GRANT_St.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0138_2145_GRANT_St.txt") lines"
echo ""

echo "=========================================================="
echo "TIER 1 COMPLETE! (21 projects)"
echo "=========================================================="
echo ""

# ==========================================================
# TIER 2: Large Projects 100+ Units (7 projects, 1547 units)
# ==========================================================

echo "=========================================================="
echo "TIER 2: Large Projects 100+ Units (7 projects)"
echo "=========================================================="
echo ""

# 22
COUNT=$((COUNT + 1))
echo "[$COUNT/28] LMSAP2024-0005 | 2276 SHATTUCK Ave | 336 units"
echo "Search for: LMSAP2024-0005"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/LMSAP2024-0005_2276_SHATTUCK_Ave.txt"
echo "Saved: $(wc -l < "$DIR/LMSAP2024-0005_2276_SHATTUCK_Ave.txt") lines"
echo ""

# 23
COUNT=$((COUNT + 1))
echo "[$COUNT/28] PLN2023-0025 | 1914 FIFTH St | 257 units"
echo "Search for: PLN2023-0025"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/PLN2023-0025_1914_FIFTH_St.txt"
echo "Saved: $(wc -l < "$DIR/PLN2023-0025_1914_FIFTH_St.txt") lines"
echo ""

# 24
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2022-0171 | 2601 SAN PABLO Ave | 223 units"
echo "Search for: ZP2022-0171"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2022-0171_2601_SAN_PABLO_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2022-0171_2601_SAN_PABLO_Ave.txt") lines"
echo ""

# 25
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2022-0116 | 2920 SHATTUCK Ave | 221 units"
echo "Search for: ZP2022-0116"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2022-0116_2920_SHATTUCK_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2022-0116_2920_SHATTUCK_Ave.txt") lines"
echo ""

# 26
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2024-0075 | 1899 OXFORD St | 212 units"
echo "Search for: ZP2024-0075"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2024-0075_1899_OXFORD_St.txt"
echo "Saved: $(wc -l < "$DIR/ZP2024-0075_1899_OXFORD_St.txt") lines"
echo ""

echo ">>> TIP: You can verify progress so far with:"
echo ">>> python /Users/johngage/berkeley-data/scripts/accela_workflow.py save_batch --db /Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db --dir $DIR"
echo ""
read -p "Press Enter to continue..."
echo ""

# 27
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2022-0046 | 3000 SHATTUCK Ave | 166 units"
echo "Search for: ZP2022-0046"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2022-0046_3000_SHATTUCK_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2022-0046_3000_SHATTUCK_Ave.txt") lines"
echo ""

# 28
COUNT=$((COUNT + 1))
echo "[$COUNT/28] ZP2022-0149 | 2420 SHATTUCK Ave | 132 units"
echo "Search for: ZP2022-0149"
read -p "Copy 'Processing Status' and press Enter to save..."
pbpaste > "$DIR/ZP2022-0149_2420_SHATTUCK_Ave.txt"
echo "Saved: $(wc -l < "$DIR/ZP2022-0149_2420_SHATTUCK_Ave.txt") lines"
echo ""

echo "=========================================================="
echo "ALL DONE! Collected $COUNT permits"
echo "=========================================================="
echo ""
echo "Files saved to: $DIR"
echo ""
echo "Run this to import all events:"
echo "python /Users/johngage/berkeley-data/scripts/accela_workflow.py save_batch --db /Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db --dir $DIR"
echo ""
