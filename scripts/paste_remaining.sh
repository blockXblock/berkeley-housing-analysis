#!/bin/bash
DIR="/Users/johngage/berkeley-data/data/raw/accela_status"

echo "=== 7 Remaining Permits (1,547 units) ==="

echo "[1/7] LMSAP2024-0005 | 2276 SHATTUCK Ave | 336 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/LMSAP2024-0005_2276_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/LMSAP2024-0005_2276_SHATTUCK_Ave.txt")"

echo "[2/7] PLN2023-0025 | 1914 FIFTH St | 257 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/PLN2023-0025_1914_FIFTH_St.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/PLN2023-0025_1914_FIFTH_St.txt")"

echo "[3/7] ZP2022-0171 | 2601 SAN PABLO Ave | 223 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2022-0171_2601_SAN_PABLO_Ave.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2022-0171_2601_SAN_PABLO_Ave.txt")"

echo "[4/7] ZP2022-0116 | 2920 SHATTUCK Ave | 221 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2022-0116_2920_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2022-0116_2920_SHATTUCK_Ave.txt")"

echo "[5/7] ZP2024-0075 | 1899 OXFORD St | 212 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2024-0075_1899_OXFORD_St.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2024-0075_1899_OXFORD_St.txt")"

echo "[6/7] ZP2022-0046 | 3000 SHATTUCK Ave | 166 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2022-0046_3000_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2022-0046_3000_SHATTUCK_Ave.txt")"

echo "[7/7] ZP2022-0149 | 2420 SHATTUCK Ave | 132 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/ZP2022-0149_2420_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < "$DIR/ZP2022-0149_2420_SHATTUCK_Ave.txt")"

echo "=== Done! Run save_batch to import ==="
echo "python /Users/johngage/berkeley-data/scripts/accela_workflow.py save_batch --db /Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db --dir /Users/johngage/berkeley-data/data/raw/accela_status"
