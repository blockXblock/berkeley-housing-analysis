#!/bin/bash
# Interactive Building Permit Paste Script
# Generated from housing_projects_FINAL.csv
# Projects with status Approved, Pending Final Action, or filed before 2024
# Plus 4 known completed projects

set -e

DIR="/Users/johngage/berkeley-data/data/raw/accela_status/building"
mkdir -p "$DIR"

TOTAL=64

echo "=========================================="
echo "Building Permit Data Collection"
echo "Total projects: $TOTAL"
echo "Output directory: $DIR"
echo "=========================================="
echo ""
echo "Instructions:"
echo "1. Go to Accela Citizen Access Building tab"
echo "2. Search by Street Number and Street Name"
echo "3. Select all results (Cmd+A) and copy (Cmd+C)"
echo "4. Return here and press Enter to save"
echo ""
echo "Press Enter to begin..."
read


echo "[1/$TOTAL] BUILDING TAB: search street number '1974' street name 'SHATTUCK' | 1974 SHATTUCK Ave | 599 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1974_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1974_SHATTUCK_Ave.txt\")"

echo "[2/$TOTAL] BUILDING TAB: search street number '2128' street name 'OXFORD' | 2128 Oxford St | 485 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2128_Oxford_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2128_Oxford_St.txt\")"

echo "[3/$TOTAL] BUILDING TAB: search street number '1914' street name 'FIFTH' | 1914 FIFTH St | 257 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1914_FIFTH_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1914_FIFTH_St.txt\")"

echo "[4/$TOTAL] BUILDING TAB: search street number '2425' street name 'DURANT' | 2425 DURANT Ave | 250 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2425_DURANT_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2425_DURANT_Ave.txt\")"

echo "[5/$TOTAL] BUILDING TAB: search street number '2029' street name 'UNIVERSITY' | 2029 UNIVERSITY Ave | 240 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2029_UNIVERSITY_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2029_UNIVERSITY_Ave.txt\")"

echo "[6/$TOTAL] BUILDING TAB: search street number '2274' street name 'SHATTUCK' | 2274 SHATTUCK Ave | 227 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2274_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2274_SHATTUCK_Ave.txt\")"

echo "[7/$TOTAL] BUILDING TAB: search street number '2601' street name 'SAN PABLO' | 2601 SAN PABLO Ave | 223 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2601_SAN_PABLO_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2601_SAN_PABLO_Ave.txt\")"

echo "[8/$TOTAL] BUILDING TAB: search street number '2920' street name 'SHATTUCK' | 2920 SHATTUCK Ave | 221 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2920_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2920_SHATTUCK_Ave.txt\")"

echo "[9/$TOTAL] BUILDING TAB: search street number '1899' street name 'OXFORD' | 1899 OXFORD St | 220 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1899_OXFORD_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1899_OXFORD_St.txt\")"

echo "[10/$TOTAL] BUILDING TAB: search street number '2100' street name 'MILVIA' | 2100 MILVIA St | 201 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2100_MILVIA_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2100_MILVIA_St.txt\")"

echo "[11/$TOTAL] BUILDING TAB: search street number '3000' street name 'SHATTUCK' | 3000 SHATTUCK Ave | 166 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_3000_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_3000_SHATTUCK_Ave.txt\")"

echo "[12/$TOTAL] BUILDING TAB: search street number '2147' street name 'SAN PABLO' | 2147 SAN PABLO Ave | 141 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2147_SAN_PABLO_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2147_SAN_PABLO_Ave.txt\")"

echo "[13/$TOTAL] BUILDING TAB: search street number '2847' street name 'SHATTUCK' | 2847 SHATTUCK Ave | 136 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2847_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2847_SHATTUCK_Ave.txt\")"

echo "[14/$TOTAL] BUILDING TAB: search street number '2420' street name 'SHATTUCK' | 2420 SHATTUCK Ave | 132 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2420_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2420_SHATTUCK_Ave.txt\")"

echo "[15/$TOTAL] BUILDING TAB: search street number '2109' street name 'VIRGINIA' | 2109 VIRGINIA St | 131 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2109_VIRGINIA_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2109_VIRGINIA_St.txt\")"

echo "[16/$TOTAL] BUILDING TAB: search street number '2720' street name 'SAN PABLO' | 2720 SAN PABLO Ave | 117 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2720_SAN_PABLO_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2720_SAN_PABLO_Ave.txt\")"

echo "[17/$TOTAL] BUILDING TAB: search street number '2530' street name 'BANCROFT' | 2530 BANCROFT Way | 110 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2530_BANCROFT_Way.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2530_BANCROFT_Way.txt\")"

echo "[18/$TOTAL] BUILDING TAB: search street number '2109' street name 'MILVIA' | 2109 MILVIA St | 105 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2109_MILVIA_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2109_MILVIA_St.txt\")"

echo "[19/$TOTAL] BUILDING TAB: search street number '2655' street name 'SHATTUCK' | 2655 SHATTUCK Ave | 97 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2655_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2655_SHATTUCK_Ave.txt\")"

echo "[20/$TOTAL] BUILDING TAB: search street number '2660' street name 'BANCROFT' | 2660 BANCROFT Way | 78 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2660_BANCROFT_Way.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2660_BANCROFT_Way.txt\")"

echo "[21/$TOTAL] BUILDING TAB: search street number '2427' street name 'SAN PABLO' | 2427 San Pablo | 78 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2427_San_Pablo.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2427_San_Pablo.txt\")"

echo "[22/$TOTAL] BUILDING TAB: search street number '2037' street name 'DURANT' | 2037 DURANT Ave | 74 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2037_DURANT_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2037_DURANT_Ave.txt\")"

echo "[23/$TOTAL] BUILDING TAB: search street number '2462' street name 'BANCROFT' | 2462 BANCROFT Way | 66 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2462_BANCROFT_Way.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2462_BANCROFT_Way.txt\")"

echo "[24/$TOTAL] BUILDING TAB: search street number '2138' street name 'KITTREDGE' | 2138 KITTREDGE St | 66 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2138_KITTREDGE_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2138_KITTREDGE_St.txt\")"

echo "[25/$TOTAL] BUILDING TAB: search street number '2298' street name 'DURANT' | 2298 DURANT Ave | 65 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2298_DURANT_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2298_DURANT_Ave.txt\")"

echo "[26/$TOTAL] BUILDING TAB: search street number '2441' street name 'LE CONTE' | 2441 LE CONTE Ave | 65 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2441_LE_CONTE_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2441_LE_CONTE_Ave.txt\")"

echo "[27/$TOTAL] BUILDING TAB: search street number '1740' street name 'SAN PABLO' | 1740 SAN PABLO Ave | 54 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1740_SAN_PABLO_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1740_SAN_PABLO_Ave.txt\")"

echo "[28/$TOTAL] BUILDING TAB: search street number '2449' street name 'DWIGHT' | 2449 DWIGHT Way | 51 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2449_DWIGHT_Way.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2449_DWIGHT_Way.txt\")"

echo "[29/$TOTAL] BUILDING TAB: search street number '130' street name 'BERKELEY SQ' | 130 BERKELEY Sq | 50 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_130_BERKELEY_Sq.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_130_BERKELEY_Sq.txt\")"

echo "[30/$TOTAL] BUILDING TAB: search street number '2442' street name 'HASTE' | 2442 HASTE St | 38 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2442_HASTE_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2442_HASTE_St.txt\")"

echo "[31/$TOTAL] BUILDING TAB: search street number '2680' street name 'BANCROFT' | 2680 BANCROFT Way | 37 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2680_BANCROFT_Way.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2680_BANCROFT_Way.txt\")"

echo "[32/$TOTAL] BUILDING TAB: search street number '2733' street name 'SAN PABLO' | 2733 SAN PABLO Ave | 32 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2733_SAN_PABLO_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2733_SAN_PABLO_Ave.txt\")"

echo "[33/$TOTAL] BUILDING TAB: search street number '2480' street name 'BANCROFT' | 2480 Bancroft Way | 28 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2480_Bancroft_Way.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2480_Bancroft_Way.txt\")"

echo "[34/$TOTAL] BUILDING TAB: search street number '2317' street name 'CHANNING' | 2317 CHANNING Way | 22 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2317_CHANNING_Way.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2317_CHANNING_Way.txt\")"

echo "[35/$TOTAL] BUILDING TAB: search street number '1790' street name 'UNIVERSITY' | 1790 UNIVERSITY Ave | 17 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1790_UNIVERSITY_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1790_UNIVERSITY_Ave.txt\")"

echo "[36/$TOTAL] BUILDING TAB: search street number '1710' street name 'UNIVERSITY' | 1710 UNIVERSITY Ave | 16 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1710_UNIVERSITY_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1710_UNIVERSITY_Ave.txt\")"

echo "[37/$TOTAL] BUILDING TAB: search street number '1015' street name 'UNIVERSITY' | 1015 UNIVERSITY Ave | 9 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1015_UNIVERSITY_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1015_UNIVERSITY_Ave.txt\")"

echo "[38/$TOTAL] BUILDING TAB: search street number '2201' street name 'BLAKE' | 2201 BLAKE St | 7 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2201_BLAKE_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2201_BLAKE_St.txt\")"

echo "[39/$TOTAL] BUILDING TAB: search street number '2942' street name 'COLLEGE' | 2942 COLLEGE Ave | 4 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2942_COLLEGE_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2942_COLLEGE_Ave.txt\")"

echo "[40/$TOTAL] BUILDING TAB: search street number '2221' street name 'FIFTH' | 2221 FIFTH St | 3 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2221_FIFTH_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2221_FIFTH_St.txt\")"

echo "[41/$TOTAL] BUILDING TAB: search street number '2833' street name 'SEVENTH' | 2833 Seventh St | 3 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2833_Seventh_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2833_Seventh_St.txt\")"

echo "[42/$TOTAL] BUILDING TAB: search street number '1614' street name 'SIXTH' | 1614 Sixth St | 3 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1614_Sixth_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1614_Sixth_St.txt\")"

echo "[43/$TOTAL] BUILDING TAB: search street number '2204' street name 'DWIGHT' | 2204 DWIGHT Way | 2 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2204_DWIGHT_Way.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2204_DWIGHT_Way.txt\")"

echo "[44/$TOTAL] BUILDING TAB: search street number '3001' street name 'BENVENUE' | 3001 BENVENUE Ave | 2 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_3001_BENVENUE_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_3001_BENVENUE_Ave.txt\")"

echo "[45/$TOTAL] BUILDING TAB: search street number '3035' street name 'COLBY' | 3035 COLBY St | 2 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_3035_COLBY_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_3035_COLBY_St.txt\")"

echo "[46/$TOTAL] BUILDING TAB: search street number '40' street name 'HILL' | 40 HILL Rd | 1 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_40_HILL_Rd.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_40_HILL_Rd.txt\")"

echo "[47/$TOTAL] BUILDING TAB: search street number '1420' street name 'FIFTH' | 1420 FIFTH St | 1 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1420_FIFTH_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1420_FIFTH_St.txt\")"

echo "[48/$TOTAL] BUILDING TAB: search street number '1139' street name 'KEELER' | 1139 KEELER Ave | 1 units — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1139_KEELER_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1139_KEELER_Ave.txt\")"

echo "[49/$TOTAL] BUILDING TAB: search street number '1730' street name 'PARKER' | 1730 PARKER St | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1730_PARKER_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1730_PARKER_St.txt\")"

echo "[50/$TOTAL] BUILDING TAB: search street number '2740' street name 'SHASTA' | 2740 SHASTA Rd | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2740_SHASTA_Rd.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2740_SHASTA_Rd.txt\")"

echo "[51/$TOTAL] BUILDING TAB: search street number '1109' street name 'COWPER' | 1109 COWPER St | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1109_COWPER_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1109_COWPER_St.txt\")"

echo "[52/$TOTAL] BUILDING TAB: search street number '705' street name 'ARLINGTON' | 705 ARLINGTON Ave | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_705_ARLINGTON_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_705_ARLINGTON_Ave.txt\")"

echo "[53/$TOTAL] BUILDING TAB: search street number '2027' street name 'SEVENTH' | 2027 SEVENTH St | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2027_SEVENTH_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2027_SEVENTH_St.txt\")"

echo "[54/$TOTAL] BUILDING TAB: search street number '2145' street name 'GRANT' | 2145 GRANT St | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2145_GRANT_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2145_GRANT_St.txt\")"

echo "[55/$TOTAL] BUILDING TAB: search street number '1187' street name 'SHATTUCK' | 1187 SHATTUCK Ave | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1187_SHATTUCK_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1187_SHATTUCK_Ave.txt\")"

echo "[56/$TOTAL] BUILDING TAB: search street number '830' street name 'BANCROFT' | 830 BANCROFT Way | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_830_BANCROFT_Way.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_830_BANCROFT_Way.txt\")"

echo "[57/$TOTAL] BUILDING TAB: search street number '2820' street name 'SAN PABLO' | 2820 San Pablo | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2820_San_Pablo.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2820_San_Pablo.txt\")"

echo "[58/$TOTAL] BUILDING TAB: search street number '1048' street name 'KEITH' | 1048 Keith St | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1048_Keith_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1048_Keith_St.txt\")"

echo "[59/$TOTAL] BUILDING TAB: search street number '811' street name 'CEDAR' | 811 Cedar | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_811_Cedar.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_811_Cedar.txt\")"

echo "[60/$TOTAL] BUILDING TAB: search street number '1627' street name 'JAYNES' | 1627 Jaynes St | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1627_Jaynes_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1627_Jaynes_St.txt\")"

echo "[61/$TOTAL] BUILDING TAB: search street number '2150' street name 'KITTREDGE' | 2150 Kittredge St | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2150_Kittredge_St.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2150_Kittredge_St.txt\")"

echo "[62/$TOTAL] BUILDING TAB: search street number '1951' street name 'SHATTUCK' | 1951 Shattuck Ave | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_1951_Shattuck_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_1951_Shattuck_Ave.txt\")"

echo "[63/$TOTAL] BUILDING TAB: search street number '2000' street name 'UNIVERSITY' | 2000 University Ave | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2000_University_Ave.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2000_University_Ave.txt\")"

echo "[64/$TOTAL] BUILDING TAB: search street number '2099' street name 'MARTIN LUTHER KING' | 2099 MLK Jr Way | units TBD — press Enter when clipboard ready"
read
pbpaste > "$DIR/B_2099_MLK_Jr_Way.txt"
echo "   Saved. Lines: $(wc -l < \"$DIR/B_2099_MLK_Jr_Way.txt\")"

echo ""
echo "=========================================="
echo "Complete! Saved $TOTAL building permit files to:"
echo "$DIR"
echo "=========================================="
