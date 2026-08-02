#!/bin/bash
# Usage: scan_sd.sh "/Volumes/CARDNAME" LABEL
# Inventories a card and prints a one-line KEEP/DUPLICATE/EMPTY verdict.
V="$1"; L="$2"
[ -d "$V" ] || { echo "  ✗ not mounted: $V"; exit 1; }
/opt/miniconda3/envs/jupyter_env/bin/python ~/berkeley-data/scripts/inventory_medium.py "$V" "$L" 2>&1 | tail -4
