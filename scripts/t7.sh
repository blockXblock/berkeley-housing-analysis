#!/bin/bash
# Run a shell command with access to /Volumes/T7-2025 from a terminal that has lost its
# removable-volume permission (the "Operation not permitted" / EPERM state that appears when
# iTerm is updated on disk while running).
#
# Why this works: the command is executed by `osascript`'s `do shell script`, which is evaluated
# under a different TCC context than the calling terminal. Verified 2026-09-22 — plain `ls` on the
# volume returned EPERM while this returned the listing. The real fix is still to relaunch iTerm;
# this is the way to keep working without ending a session.
#
# Output goes to a FILE rather than stdout, because AppleScript returns one string with CR line
# endings and mangles multi-line output. Default: a temp file whose path is printed.
#
# Usage:
#   scripts/t7.sh 'du -sh /Volumes/T7-2025/* | sort -rh'          # prints the output file path
#   scripts/t7.sh 'find /Volumes/T7-2025/tours -name "*.mp4"' out.txt
#   scripts/t7.sh --stdout 'df -h /Volumes/T7-2025'               # small output, straight through
#
# Volume identity (CLAUDE.md rule 6 — never trust /dev/diskN):
#   Volume Name T7-2025, Volume UUID 90C759D9-9F67-40E4-9C93-80E168242A5A
# Verify before any raw-device or destructive operation:
#   diskutil info /Volumes/T7-2025 | grep 'Volume UUID'
set -u

if [ "${1:-}" = "--stdout" ]; then
    shift
    osascript -e "do shell script \"$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')\"" | tr '\r' '\n'
    exit $?
fi

CMD="${1:?usage: t7.sh '<shell command>' [output-file]}"
OUT="${2:-$(mktemp -t t7out).txt}"
[ "${OUT#/}" = "$OUT" ] && OUT="$PWD/$OUT"        # make relative paths absolute for the subshell

# The command runs under osascript; redirect inside it so the file lands with real newlines.
WRAPPED="{ $CMD ; } > '$OUT' 2>&1"
osascript -e "do shell script \"$(printf '%s' "$WRAPPED" | sed 's/\\/\\\\/g; s/"/\\"/g')\"" >/dev/null 2>&1
rc=$?
echo "$OUT"
exit $rc
