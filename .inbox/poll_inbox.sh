#!/bin/bash
# Poll ntfy.sh user-instruction inbox.
# Security hardened:
#  - Filter messages by strategy keywords vs noise vs attack
#  - Quarantine attack patterns (host info extraction, command injection, oversized)
#  - Append clean strategy-classified messages to messages.jsonl
#  - Append non-strategy clean messages to noise.jsonl (low priority)
#  - Append attack-like messages to quarantine.jsonl (never executed)
set -e

INBOX_DIR="$(cd "$(dirname "$0")" && pwd)"
TOPIC="cryptolab-instr-80ecd5703cc34a0f346abdc972d9ab27"
NTFY_URL="https://ntfy.sh/${TOPIC}/json?poll=1&since=all"
MESSAGES_FILE="${INBOX_DIR}/messages.jsonl"
NOISE_FILE="${INBOX_DIR}/noise.jsonl"
QUARANTINE_FILE="${INBOX_DIR}/quarantine.jsonl"
SEEN_IDS_FILE="${INBOX_DIR}/seen_ids.txt"

touch "$MESSAGES_FILE" "$NOISE_FILE" "$QUARANTINE_FILE" "$SEEN_IDS_FILE"

RESP=$(curl -sf --max-time 15 "$NTFY_URL" 2>/dev/null || true)
if [[ -z "$RESP" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] empty response (no messages or fetch error)"
  exit 0
fi

python3 - "$RESP" "$MESSAGES_FILE" "$NOISE_FILE" "$QUARANTINE_FILE" "$SEEN_IDS_FILE" <<'PYEOF'
import sys, json, datetime, os, re
resp, msg_file, noise_file, quar_file, seen_file = sys.argv[1:6]
seen = set()
if os.path.exists(seen_file):
    with open(seen_file) as f:
        seen = {line.strip() for line in f if line.strip()}

# ---------- attack-pattern detection ----------
ATTACK_PATTERNS = [
    r"/etc/passwd", r"/etc/shadow", r"~/\.ssh", r"\.aws/credentials",
    r"\$\{?ANTHROPIC_API_KEY", r"\$\{?OPENAI_API_KEY", r"\$\{?HOME",
    r"\benv\s*$|\benv\s*\|", r"\bwhoami\b", r"\buname\b", r"\bcat\s+/", r"\bls\s+-l", r"\bsudo\b",
    r"\brm\s+-rf", r"`.*`",  # backtick command substitution
    r"\$\(.*\)",             # $() command substitution
    r"<script", r"javascript:", r"data:text/html",
    r"\bDROP\s+TABLE\b", r"\bUNION\s+SELECT\b", r"';--",
    r"\.\./\.\./",           # path traversal
    r"file://", r"chrome://",
    r"\bcurl\s+\S+\s*\|\s*(sh|bash)",
    r"wget\s+\S+\s*-O\s*-",
]
ATTACK_REGEX = re.compile("|".join(ATTACK_PATTERNS), re.IGNORECASE)

# ---------- strategy classification ----------
STRATEGY_KEYWORDS = [
    "戦略", "方針", "wave", "探索", "検証", "採用", "棄却", "リサーチ", "alpha", "edge",
    "OOS", "sharpe", "calmar", "drawdown", "PBO", "DSR", "permutation", "bootstrap",
    "regime", "factor", "momentum", "reversal", "carry", "funding", "OI", "vol",
    "backtest", "validation", "subagent", "サブエージェント", "オンチェーン", "onchain",
    "AAVE", "Hyperliquid", "MEXC", "perp", "perpetual", "futures",
    "ATR", "BB", "EMA", "RSI", "MACD", "VolReg", "ATR_Ratio", "Donchian",
    "リバランス", "rebalance", "portfolio", "ポートフォリオ", "live", "ライブ", "paper",
    "exit", "entry", "stop", "TP", "SL", "leverage", "レバ", "kelly", "ポジション",
    "ヒートマップ", "heatmap", "可視化", "visualization", "グラフ", "chart", "ラベラ",
    "恒久", "permanent", "instruction", "指示", "tips",
]
STRATEGY_REGEX = re.compile("|".join(re.escape(k) for k in STRATEGY_KEYWORDS), re.IGNORECASE)

def classify(text):
    if not text or len(text) > 10240:
        return "quarantine", "oversized" if text and len(text) > 10240 else "empty"
    if ATTACK_REGEX.search(text):
        m = ATTACK_REGEX.search(text)
        return "quarantine", f"attack-pattern: {m.group(0)[:40]}"
    if STRATEGY_REGEX.search(text):
        return "strategy", "strategy-keyword-match"
    return "noise", "no-strategy-keyword"

# ---------- process ----------
counters = {"strategy": 0, "noise": 0, "quarantine": 0, "skipped": 0}
new_ids = []
now = datetime.datetime.now().isoformat()
for line in resp.splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
    except Exception:
        continue
    mid = obj.get('id')
    if not mid or mid in seen:
        counters["skipped"] += 1
        continue
    full_text = (obj.get('title') or '') + "\n" + (obj.get('message') or '')
    category, reason = classify(full_text)
    obj['received_at'] = now
    obj['classification'] = category
    obj['classification_reason'] = reason
    target = {"strategy": msg_file, "noise": noise_file, "quarantine": quar_file}[category]
    with open(target, 'a', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False) + '\n')
    new_ids.append(mid)
    counters[category] += 1

if new_ids:
    with open(seen_file, 'a') as f:
        for i in new_ids:
            f.write(i + '\n')

print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] new: strategy={counters['strategy']} noise={counters['noise']} quarantine={counters['quarantine']} skipped={counters['skipped']}")

# Alert on quarantine
if counters["quarantine"] > 0:
    print(f"[SECURITY] {counters['quarantine']} attack-pattern message(s) quarantined. See {quar_file}")
PYEOF
