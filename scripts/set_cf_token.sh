#!/usr/bin/env bash
# Put a Cloudflare API token into .env.cloudflare from the clipboard, without the token
# ever appearing in a command line, shell history, or a Claude transcript.
#
# WHY THIS EXISTS. The obvious one-liner --
#     printf 'export CLOUDFLARE_API_TOKEN=%s\n' "$(pbpaste)" > .env.cloudflare
# -- is self-defeating, because to run it you copy the command, which overwrites the very
# clipboard entry holding the token. (Happened 2026-09-22: the file ended up containing the
# command text.) This script is short enough to TYPE, so the token stays on the clipboard.
#
# Usage:  copy the token from Cloudflare, then type:   bash scripts/set_cf_token.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

TOK=$(pbpaste | tr -d '[:space:]')

# Refuse anything that is not shaped like a Cloudflare API token, rather than writing
# junk and failing opaquely at query time.
if [ -z "$TOK" ]; then
    echo "clipboard is empty -- copy the token from Cloudflare first"; exit 2
fi
if ! printf '%s' "$TOK" | grep -qE '^[A-Za-z0-9_-]{35,60}$'; then
    echo "clipboard does not look like a Cloudflare API token"
    echo "  length ${#TOK}, starts '${TOK:0:4}'"
    echo "  expected 35-60 chars of [A-Za-z0-9_-] and nothing else."
    echo "  did you copy the command instead of the token?"
    exit 2
fi

printf 'export CLOUDFLARE_API_TOKEN=%s\n' "$TOK" > .env.cloudflare
chmod 600 .env.cloudflare
echo "wrote .env.cloudflare  (${#TOK} chars, ${TOK:0:4}...${TOK: -3}, mode 600, git-ignored)"
