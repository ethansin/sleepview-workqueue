#!/usr/bin/env bash
# Batch-create workqueue items from a list of study IDs via POST /items.
#
# Usage:
#   BASE_URL=https://sleepview-backend-996574964703.us-central1.run.app \
#   SESSION=<admin_session_token> \
#   ./scripts/seed_study_ids.sh study_ids.txt
#
# study_ids.txt: one study ID per line. Blank lines and lines starting
# with # are ignored.

set -u

FILE="${1:?usage: $0 <study_ids_file>}"
BASE_URL="${BASE_URL:?set BASE_URL to the backend URL}"
SESSION="${SESSION:?set SESSION to the admin session token}"

ok=0
failed=()

while IFS= read -r study_id || [ -n "$study_id" ]; do
  study_id="$(echo "$study_id" | xargs)"
  [ -z "$study_id" ] && continue
  [[ "$study_id" == \#* ]] && continue

  status=$(curl -s -o /tmp/seed_response.json -w '%{http_code}' \
    -X POST "$BASE_URL/items" \
    -H "Content-Type: application/json" \
    -H "Cookie: session=$SESSION" \
    -d "{\"study_id\": \"$study_id\"}")

  if [ "$status" -ge 200 ] && [ "$status" -lt 300 ]; then
    echo "OK   $study_id"
    ok=$((ok + 1))
  else
    echo "FAIL $study_id (HTTP $status): $(cat /tmp/seed_response.json)"
    failed+=("$study_id")
  fi
done < "$FILE"

rm -f /tmp/seed_response.json

echo
echo "$ok succeeded, ${#failed[@]} failed"
if [ "${#failed[@]}" -gt 0 ]; then
  printf 'Failed IDs: %s\n' "${failed[*]}"
  exit 1
fi
