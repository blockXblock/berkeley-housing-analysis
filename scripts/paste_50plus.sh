#!/bin/bash
DIR="/Users/johngage/berkeley-data/data/raw/accela_status"

echo "=== 14 Projects 50+ Units Missing Timeline Data ==="

echo "[1/14] ZP2024-0079 | 2036 BANCROFT Way | 85 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2024-0079_2036_BANCROFT_Way.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2024-0079_2036_BANCROFT_Way.txt")"

echo "[2/14] ZP2024-0071 | 2955 SHATTUCK Ave | 74 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2024-0071_2955_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2024-0071_2955_SHATTUCK_Ave.txt")"

echo "[3/14] ZP2026-0006 | 2138 KITTREDGE St | 73 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2026-0006_2138_KITTREDGE_St.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2026-0006_2138_KITTREDGE_St.txt")"

echo "[4/14] PLN2024-0023 | 2326 DURANT Ave | 70 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/PLN2024-0023_2326_DURANT_Ave.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/PLN2024-0023_2326_DURANT_Ave.txt")"

echo "[5/14] ZP2026-0015 | 2455 TELEGRAPH Ave | 68 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2026-0015_2455_TELEGRAPH_Ave.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2026-0015_2455_TELEGRAPH_Ave.txt")"

echo "[6/14] PLN2025-0038 | 2330 DURANT Ave | 68 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/PLN2025-0038_2330_DURANT_Ave.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/PLN2025-0038_2330_DURANT_Ave.txt")"

echo "[7/14] ZP2024-0114 | 2138 KITTREDGE St | 66 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2024-0114_2138_KITTREDGE_St.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2024-0114_2138_KITTREDGE_St.txt")"

echo "[8/14] ZP2023-0089 | 2441 LE CONTE Ave | 65 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2023-0089_2441_LE_CONTE_Ave.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2023-0089_2441_LE_CONTE_Ave.txt")"

echo "[9/14] PLN2024-0054 | 2372 ELLSWORTH St | 63 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/PLN2024-0054_2372_ELLSWORTH_St.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/PLN2024-0054_2372_ELLSWORTH_St.txt")"

echo "[10/14] ZP2025-0107 | 2001 CENTER St | 58 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2025-0107_2001_CENTER_St.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2025-0107_2001_CENTER_St.txt")"

echo "[11/14] ZP2025-0105 | 2712 TELEGRAPH Ave | 57 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2025-0105_2712_TELEGRAPH_Ave.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2025-0105_2712_TELEGRAPH_Ave.txt")"

echo "[12/14] PLN2023-0065 | 1740 SAN PABLO Ave | 54 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/PLN2023-0065_1740_SAN_PABLO_Ave.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/PLN2023-0065_1740_SAN_PABLO_Ave.txt")"

echo "[13/14] ZP2021-0158 | 130 BERKELEY Sq | 50 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2021-0158_130_BERKELEY_Sq.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2021-0158_130_BERKELEY_Sq.txt")"

echo "[14/14] ZP2024-0138 | 2145 GRANT St | recollect — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2024-0138_2145_GRANT_St.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2024-0138_2145_GRANT_St.txt")"

echo "=== Done! Run save_batch ==="
