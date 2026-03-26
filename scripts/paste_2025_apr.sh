#!/bin/bash
# 2025 APR Data Collection Script
# Generated: 2026-03-26
# Purpose: Collect permit data needed for 2025 Annual Progress Report

set -e

DATA_DIR="/Users/johngage/berkeley-data/data/raw/accela_status"
BUILDING_DIR="$DATA_DIR/building"
APR_DIR="$DATA_DIR/apr_2025"

# Create directories
mkdir -p "$APR_DIR"
mkdir -p "$BUILDING_DIR"

echo "=============================================="
echo "2025 APR DATA COLLECTION"
echo "=============================================="
echo ""
echo "This script will guide you through collecting permit data"
echo "needed for the 2025 Annual Progress Report."
echo ""
echo "INSTRUCTIONS:"
echo "1. Open Berkeley Accela in Chrome"
echo "2. For each permit, search and navigate to Processing Status"
echo "3. Copy all processing status data to clipboard"
echo "4. Return here and press Enter to save"
echo ""
echo "Press Enter to begin..."
read

# ============================================
# PRIORITY 1: 2025-Filed Projects (CRITICAL)
# ============================================
echo ""
echo "=============================================="
echo "PRIORITY 1: 2025-Filed Projects (2 permits)"
echo "=============================================="
echo "These are CRITICAL for Table A"
echo ""

PRIORITY1=(
    "PLN2024-0010|1750_SACRAMENTO_St|739"
    "ZP2025-0101|2190_SHATTUCK_Ave|36"
)

for item in "${PRIORITY1[@]}"; do
    IFS='|' read -r permit address units <<< "$item"
    echo "---"
    echo "PERMIT: $permit"
    echo "ADDRESS: ${address//_/ }"
    echo "UNITS: $units"
    echo ""
    echo ">> Search for $permit in Accela Planning tab"
    echo ">> Copy Processing Status to clipboard"
    echo ">> Press Enter when ready..."
    read
    pbpaste > "$APR_DIR/${permit}_${address}.txt"
    echo "✓ Saved to $APR_DIR/${permit}_${address}.txt"
done

# ============================================
# PRIORITY 2: 2024 Projects Status Refresh
# ============================================
echo ""
echo "=============================================="
echo "PRIORITY 2: 2024 Projects Status Refresh (20 permits)"
echo "=============================================="
echo "These may have been deemed complete in 2025"
echo ""

PRIORITY2=(
    "ZP2024-0131|2115_KITTREDGE_St|148"
    "ZP2022-0132|2847_SHATTUCK_Ave|132"
    "ZP2023-0058|2720_SAN_PABLO_Ave|113"
    "PLN2024-0023|2326_DURANT_Ave|70"
    "PLN2025-0038|2330_DURANT_Ave|68"
    "PLN2024-0054|2372_ELLSWORTH_St|63"
    "ZP2026-0007|2727_HASTE_St|45"
    "ZP2024-0027|2614_TELEGRAPH_Ave|31"
    "ZP2025-0079|1740_UNIVERSITY_Ave|12"
    "PLN2024-0025|2428_MILVIA_St|8"
    "ZP2025-0085|2200_FIFTH_St|8"
    "PLN2025-0040|1745_CEDAR_St|6"
    "ZP2023-0063|1850_BERRYMAN_St|6"
    "PLN2025-0068|1618_SIXTH_St|4"
    "ZP2024-0147|2420_ASHBY_Ave|4"
    "PLN2025-0031|2437_WARRING_St|4"
    "PLN2024-0013|2201_BLAKE_St|3"
    "PLN2025-0058|2812_EIGHTH_St|3"
    "ZP2024-0060|2201_BLAKE_St|3"
    "PLN2024-0047|1136_KEITH_Ave|1"
)

echo "Do you want to collect Priority 2 permits? (y/n)"
read COLLECT_P2
if [ "$COLLECT_P2" = "y" ]; then
    for item in "${PRIORITY2[@]}"; do
        IFS='|' read -r permit address units <<< "$item"
        echo "---"
        echo "PERMIT: $permit"
        echo "ADDRESS: ${address//_/ }"
        echo "UNITS: $units"
        echo ""
        echo ">> Search for $permit in Accela Planning tab"
        echo ">> Copy Processing Status to clipboard"
        echo ">> Press Enter when ready (or 's' to skip)..."
        read response
        if [ "$response" != "s" ]; then
            pbpaste > "$APR_DIR/${permit}_${address}.txt"
            echo "✓ Saved"
        else
            echo "⊘ Skipped"
        fi
    done
fi

# ============================================
# PRIORITY 3: Building Tab Searches
# ============================================
echo ""
echo "=============================================="
echo "PRIORITY 3: Building Tab Searches (30 addresses)"
echo "=============================================="
echo "Search Building tab for each entitled project"
echo "to find any 2025 building permit issuance"
echo ""

PRIORITY3=(
    "2480_BANCROFT_Way|2023-10-02|28"
    "2833_SEVENTH_St|2024-05-07|3"
    "2037_DURANT_Ave|2024-06-19|74"
    "2462_BANCROFT_Way|2024-07-01|66"
    "2427_SAN_PABLO_Ave|2024-09-16|78"
    "2128_OXFORD_St|2024-10-04|485"
    "1614_SIXTH_St|2024-10-17|3"
    "2820_SAN_PABLO_Ave|2024-12-06|1"
    "2530_BANCROFT_Way|2024-12-27|110"
    "3000_SHATTUCK_Ave|2025-03-11|166"
    "2274_SHATTUCK_Ave|2025-04-22|227"
    "1627_JAYNES_St|2025-05-16|1"
    "1974_SHATTUCK_Ave|2025-06-03|599"
    "1048_KEITH_St|2025-06-04|1"
    "2680_BANCROFT_Way|2025-06-13|37"
    "2100_MILVIA_St|2025-07-01|201"
    "811_CEDAR_St|2025-07-03|1"
    "2655_SHATTUCK_Ave|2025-08-14|97"
    "2442_HASTE_St|2025-09-08|34"
    "2147_SAN_PABLO_Ave|2025-09-09|15"
    "2425_DURANT_Ave|2025-10-09|250"
    "2138_KITTREDGE_St|2025-10-20|66"
    "2029_UNIVERSITY_Ave|2025-11-13|240"
    "2276_SHATTUCK_Ave|2025-12-04|336"
    "1899_OXFORD_St|2026-02-11|212"
    "2109_VIRGINIA_St|2026-02-26|131"
    "1750_SACRAMENTO_St|2026-03-03|739"
    "2145_GRANT_St|2026-03-26|0"
)

echo "Do you want to collect Priority 3 Building permits? (y/n)"
read COLLECT_P3
if [ "$COLLECT_P3" = "y" ]; then
    echo ""
    echo "INSTRUCTIONS for Building tab:"
    echo "1. Go to Accela Building tab"
    echo "2. Search by address"
    echo "3. Look for permits issued in 2025"
    echo "4. If found, copy permit details to clipboard"
    echo "5. If NO building permits found, just press Enter"
    echo ""

    for item in "${PRIORITY3[@]}"; do
        IFS='|' read -r address entitled units <<< "$item"
        echo "---"
        echo "ADDRESS: ${address//_/ }"
        echo "ENTITLED: $entitled"
        echo "UNITS: $units"
        echo ""
        echo ">> Search Building tab for ${address//_/ }"
        echo ">> Copy any 2025 building permits to clipboard"
        echo ">> Press Enter when ready (or 's' to skip, 'n' for no permits found)..."
        read response
        if [ "$response" = "s" ]; then
            echo "⊘ Skipped"
        elif [ "$response" = "n" ]; then
            echo "No 2025 BP found" > "$BUILDING_DIR/B_${address}.txt"
            echo "✓ Marked as no 2025 BP found"
        else
            pbpaste > "$BUILDING_DIR/B_${address}.txt"
            echo "✓ Saved"
        fi
    done
fi

# ============================================
# PRIORITY 4: ADU Bulk Search
# ============================================
echo ""
echo "=============================================="
echo "PRIORITY 4: ADU Building Permits (bulk search)"
echo "=============================================="
echo ""
echo "This requires a different approach:"
echo "1. Go to Accela Building tab"
echo "2. Search for 'ADU' or filter by permit type"
echo "3. Filter for permits issued in 2025"
echo "4. Export or copy all ADU permits"
echo ""
echo "Press Enter when you have ADU 2025 data on clipboard..."
read
pbpaste > "$APR_DIR/ADU_2025_building_permits.txt"
echo "✓ Saved ADU data"

# ============================================
# SUMMARY
# ============================================
echo ""
echo "=============================================="
echo "COLLECTION COMPLETE"
echo "=============================================="
echo ""
echo "Files saved to:"
echo "  Planning: $APR_DIR/"
echo "  Building: $BUILDING_DIR/"
echo ""
echo "Next steps:"
echo "1. Run parsing script to extract dates"
echo "2. Update housing_projects_FINAL.csv"
echo "3. Regenerate explorer DATA.json"
echo ""

# Count files
P_COUNT=$(ls -1 "$APR_DIR"/*.txt 2>/dev/null | wc -l | tr -d ' ')
B_COUNT=$(ls -1 "$BUILDING_DIR"/*.txt 2>/dev/null | wc -l | tr -d ' ')
echo "Collected: $P_COUNT planning files, $B_COUNT building files"
