#!/bin/bash
DIR="/Users/johngage/berkeley-data/data/raw/accela_status"

echo "=== TIER 1: City APR 2024 Validation ==="

echo "1. Search: B2025-05534 (1750 SACRAMENTO, 739 units) — press Enter when clipboard ready"
read
pbpaste > "$DIR/B2025-05534_1750_SACRAMENTO.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/B2025-05534_1750_SACRAMENTO.txt")"

echo "2. Search: ZP2024-0058 (2700 SHATTUCK, 276 units) — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2024-0058_2700_SHATTUCK.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2024-0058_2700_SHATTUCK.txt")"

echo "3. Search: ZP2024-0074 (1581 UNIVERSITY, 158 units) — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2024-0074_1581_UNIVERSITY.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2024-0074_1581_UNIVERSITY.txt")"

echo "4. Search: ZP2022-0132 (2847 SHATTUCK, 132 units) — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2022-0132_2847_SHATTUCK.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2022-0132_2847_SHATTUCK.txt")"

echo "5. Search: ZP2024-0066 (2109 VIRGINIA, 131 units) — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2024-0066_2109_VIRGINIA.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2024-0066_2109_VIRGINIA.txt")"

echo "Done with first 5. Run save_batch to verify, then continue."
