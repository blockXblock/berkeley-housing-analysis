#!/bin/bash
#
# scrape_and_save.sh - Interactive Accela data collection script
#
# Reads from scraping_queue.csv, guides user through collection,
# validates saved files, and logs results.
#
# Usage:
#   ./scripts/scrape_and_save.sh           # Start from beginning
#   ./scripts/scrape_and_save.sh --resume  # Resume from last position
#   ./scripts/scrape_and_save.sh --skip N  # Skip first N projects
#

set -e

# Paths
QUEUE_CSV="data/processed/scraping_queue.csv"
LOG_CSV="data/processed/scraping_log.csv"
ACCELA_DIR="data/raw/accela_status"
VALIDATE_SCRIPT="scripts/validate_scraped_file.py"
POSITION_FILE="/tmp/scrape_position.txt"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Initialize log file if it doesn't exist
if [ ! -f "$LOG_CSV" ]; then
    echo "timestamp,filename,permit,address,validation_result,errors,warnings" > "$LOG_CSV"
fi

# Parse arguments
SKIP=0
RESUME=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --resume)
            RESUME=true
            shift
            ;;
        --skip)
            SKIP="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Resume from last position
if [ "$RESUME" = true ] && [ -f "$POSITION_FILE" ]; then
    SKIP=$(cat "$POSITION_FILE")
    echo -e "${CYAN}Resuming from position $SKIP${NC}"
fi

# Read queue into array (skip header)
mapfile -t PROJECTS < <(tail -n +2 "$QUEUE_CSV")
TOTAL=${#PROJECTS[@]}

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}       BERKELEY HOUSING PIPELINE - DATA COLLECTION         ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Queue: ${CYAN}$QUEUE_CSV${NC}"
echo -e "Total projects in queue: ${YELLOW}$TOTAL${NC}"
echo -e "Starting from: ${YELLOW}$SKIP${NC}"
echo ""
echo -e "${YELLOW}Instructions:${NC}"
echo "  1. Open Accela in Chrome with Claude sidebar"
echo "  2. Search for the permit/address shown"
echo "  3. Copy the sidebar output to clipboard"
echo "  4. Press Enter to save and validate"
echo "  5. Type 'skip' to skip this project"
echo "  6. Type 'quit' to exit"
echo ""

# Process each project
for ((i=SKIP; i<TOTAL; i++)); do
    IFS=',' read -r address permit units missing search_term priority score <<< "${PROJECTS[$i]}"

    # Remove quotes if present
    address=$(echo "$address" | tr -d '"')
    permit=$(echo "$permit" | tr -d '"')
    units=$(echo "$units" | tr -d '"')
    missing=$(echo "$missing" | tr -d '"')
    search_term=$(echo "$search_term" | tr -d '"')
    priority=$(echo "$priority" | tr -d '"')

    # Generate filename
    if [[ "$permit" != "TBD" && -n "$permit" ]]; then
        # Use first permit
        first_permit=$(echo "$permit" | cut -d',' -f1 | xargs)
        addr_clean=$(echo "$address" | sed 's/ /_/g' | sed 's/[^a-zA-Z0-9_]//g')
        FILENAME="${first_permit}_${addr_clean}.txt"
    else
        addr_clean=$(echo "$address" | sed 's/ /_/g' | sed 's/[^a-zA-Z0-9_]//g')
        FILENAME="${addr_clean}.txt"
    fi

    FILEPATH="$ACCELA_DIR/$FILENAME"

    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "  Project ${CYAN}$((i+1))${NC} of ${TOTAL}  |  Priority: ${YELLOW}${priority}${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  Address:      ${GREEN}${address}${NC}"
    echo -e "  Permit:       ${CYAN}${permit}${NC}"
    echo -e "  Units:        ${YELLOW}${units}${NC}"
    echo -e "  Missing:      ${RED}${missing}${NC}"
    echo -e "  Search term:  ${CYAN}${search_term}${NC}"
    echo ""
    echo -e "  Will save to: ${CYAN}${FILENAME}${NC}"
    echo ""

    # Check if file already exists
    if [ -f "$FILEPATH" ]; then
        echo -e "${YELLOW}⚠ File already exists. Will append if needed.${NC}"
    fi

    while true; do
        echo -e "${YELLOW}Copy sidebar output to clipboard, then press Enter (or 'skip'/'quit'):${NC}"
        read -r input

        if [ "$input" = "quit" ] || [ "$input" = "q" ]; then
            echo "$i" > "$POSITION_FILE"
            echo -e "${CYAN}Position saved. Run with --resume to continue.${NC}"
            exit 0
        fi

        if [ "$input" = "skip" ] || [ "$input" = "s" ]; then
            echo -e "${YELLOW}Skipping...${NC}"
            # Log skip
            echo "$(date -Iseconds),$FILENAME,$permit,$address,SKIPPED,User skipped," >> "$LOG_CSV"
            break
        fi

        if [ "$input" = "append" ] || [ "$input" = "a" ]; then
            # Append mode
            echo "" >> "$FILEPATH"
            echo "=== ADDITIONAL DATA ===" >> "$FILEPATH"
            echo "" >> "$FILEPATH"
            pbpaste >> "$FILEPATH"
            echo -e "${GREEN}✓ Appended to file${NC}"
            continue
        fi

        # Save clipboard to file
        pbpaste > "$FILEPATH"

        # Validate
        echo ""
        echo -e "${CYAN}Validating...${NC}"

        if python3 "$VALIDATE_SCRIPT" "$FILEPATH"; then
            # Valid!
            echo ""
            echo -e "${GREEN}✓ FILE VALID - Saved successfully${NC}"

            # Show data quality checklist
            echo ""
            echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
            echo -e "${CYAN}  DATA QUALITY CHECKLIST - Please verify:${NC}"
            echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"

            # Check for specific content
            HAS_STATUS=$(grep -c "PROCESSING STATUS\|Marked as\|Due:" "$FILEPATH" 2>/dev/null || echo 0)
            HAS_STAFF=$(grep -cE "By:?\s+[A-Z][a-z]+" "$FILEPATH" 2>/dev/null || echo 0)
            HAS_FEES=$(grep -c "FEES\|Total.*\$\|\$[0-9]" "$FILEPATH" 2>/dev/null || echo 0)
            HAS_URLS=$(grep -cE "https?://" "$FILEPATH" 2>/dev/null || echo 0)
            HAS_ENTITIES=$(grep -cE "DEVELOPER|ARCHITECT|CONTRACTOR|APPLICANT|OWNER" "$FILEPATH" 2>/dev/null || echo 0)

            if [ "$HAS_STATUS" -gt 0 ]; then
                echo -e "  ${GREEN}[✓]${NC} Processing Status events captured"
            else
                echo -e "  ${RED}[ ]${NC} Processing Status events captured"
            fi

            if [ "$HAS_STAFF" -gt 0 ]; then
                echo -e "  ${GREEN}[✓]${NC} Staff names captured (By: Name) - found $HAS_STAFF"
            else
                echo -e "  ${RED}[ ]${NC} Staff names captured (By: Name)"
            fi

            if [ "$HAS_FEES" -gt 0 ]; then
                echo -e "  ${GREEN}[✓]${NC} Fees captured with totals"
            else
                echo -e "  ${RED}[ ]${NC} Fees captured with totals"
            fi

            if [ "$HAS_URLS" -gt 0 ]; then
                echo -e "  ${GREEN}[✓]${NC} Attachments captured with URLs - found $HAS_URLS"
            else
                echo -e "  ${YELLOW}[ ]${NC} Attachments captured with URLs"
            fi

            if [ "$HAS_ENTITIES" -gt 0 ]; then
                echo -e "  ${GREEN}[✓]${NC} Developer/Architect/Contractor names"
            else
                echo -e "  ${YELLOW}[ ]${NC} Developer/Architect/Contractor names"
            fi

            echo -e "  ${YELLOW}[ ]${NC} Building permits searched (manual check)"
            echo ""

            # Prompt for additional data
            echo -e "${YELLOW}Need to add more data? Type 'append' or press Enter to continue:${NC}"
            read -r add_more
            if [ "$add_more" = "append" ] || [ "$add_more" = "a" ]; then
                echo "" >> "$FILEPATH"
                echo "=== ADDITIONAL DATA ===" >> "$FILEPATH"
                echo "" >> "$FILEPATH"
                pbpaste >> "$FILEPATH"
                echo -e "${GREEN}✓ Appended additional data${NC}"
            fi

            # Log success
            echo "$(date -Iseconds),$FILENAME,$permit,$address,VALID,," >> "$LOG_CSV"
            break
        else
            # Invalid
            echo ""
            echo -e "${RED}✗ VALIDATION FAILED${NC}"
            echo ""
            echo -e "Options:"
            echo -e "  ${CYAN}Enter${NC}  - Try again (paste new content)"
            echo -e "  ${CYAN}append${NC} - Append additional data (fees/attachments)"
            echo -e "  ${CYAN}skip${NC}   - Skip this project"
            echo -e "  ${CYAN}force${NC}  - Accept anyway and continue"
            echo ""
            read -r retry_input

            if [ "$retry_input" = "skip" ] || [ "$retry_input" = "s" ]; then
                echo -e "${YELLOW}Skipping...${NC}"
                echo "$(date -Iseconds),$FILENAME,$permit,$address,SKIPPED,Validation failed - user skipped," >> "$LOG_CSV"
                break
            fi

            if [ "$retry_input" = "force" ] || [ "$retry_input" = "f" ]; then
                echo -e "${YELLOW}Accepting file despite validation issues...${NC}"
                echo "$(date -Iseconds),$FILENAME,$permit,$address,FORCED,Validation failed - user forced," >> "$LOG_CSV"
                break
            fi

            if [ "$retry_input" = "append" ] || [ "$retry_input" = "a" ]; then
                echo "" >> "$FILEPATH"
                echo "=== ADDITIONAL DATA ===" >> "$FILEPATH"
                echo "" >> "$FILEPATH"
                pbpaste >> "$FILEPATH"
                echo -e "${GREEN}✓ Appended to file${NC}"
            fi
            # Otherwise, loop again to retry
        fi
    done

    # Save position
    echo "$((i+1))" > "$POSITION_FILE"
done

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}             COLLECTION COMPLETE!                          ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Log saved to: $LOG_CSV"
echo ""

# Clean up position file
rm -f "$POSITION_FILE"
