set -u
cd ~/berkeley-data/scratch/2026-09-02/journals
UA="research (john.gage@gmail.com)"
IDS=$(curl -s --max-time 90 -G "https://archive.org/advancedsearch.php" \
  --data-urlencode 'q=identifier:journalofele*' --data-urlencode 'fl[]=identifier' \
  --data-urlencode 'rows=100' --data-urlencode 'output=json' \
  | python3 -c "import json,sys;print('\n'.join(d['identifier'] for d in json.load(sys.stdin)['response']['docs']))")
for id in $IDS; do
  [ -s "$id.txt" ] && { echo "have $id"; continue; }
  curl -sL --max-time 600 -A "$UA" -o "$id.txt" "https://archive.org/download/$id/${id}_djvu.txt"
  printf "%-32s %s\n" "$id" "$(du -h "$id.txt" 2>/dev/null | cut -f1)"
done
echo FETCH_DONE
