#!/bin/bash
# Poll ntfy.sh user-instruction inbox, append unseen messages to messages.jsonl
set -e

INBOX_DIR="$(cd "$(dirname "$0")" && pwd)"
TOPIC="cryptolab-instr-80ecd5703cc34a0f346abdc972d9ab27"
NTFY_URL="https://ntfy.sh/${TOPIC}/json?poll=1&since=all"
MESSAGES_FILE="${INBOX_DIR}/messages.jsonl"
SEEN_IDS_FILE="${INBOX_DIR}/seen_ids.txt"

touch "$MESSAGES_FILE" "$SEEN_IDS_FILE"

RESP=$(curl -sf --max-time 15 "$NTFY_URL" 2>/dev/null || true)
if [[ -z "$RESP" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] empty response (no messages or fetch error)"
  exit 0
fi

python3 - "$RESP" "$MESSAGES_FILE" "$SEEN_IDS_FILE" <<'PYEOF'
import sys, json, datetime, os
resp, msg_file, seen_file = sys.argv[1], sys.argv[2], sys.argv[3]
seen = set()
if os.path.exists(seen_file):
    with open(seen_file) as f:
        seen = {line.strip() for line in f if line.strip()}
new_count = 0
now = datetime.datetime.now().isoformat()
new_ids = []
with open(msg_file, 'a', encoding='utf-8') as mf:
    for line in resp.splitlines():
        line = line.strip()
        if not line: continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        mid = obj.get('id')
        if not mid or mid in seen: continue
        obj['received_at'] = now
        mf.write(json.dumps(obj, ensure_ascii=False) + '\n')
        new_ids.append(mid)
        new_count += 1
if new_ids:
    with open(seen_file, 'a') as f:
        for i in new_ids: f.write(i + '\n')
print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] new messages: {new_count}")
PYEOF
