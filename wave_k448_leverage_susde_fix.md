# Wave K448: sUSDe Leverage Cap Bug Fix

**Wave:** K448 | **Issue:** K446 finding (margin_used=88% → 80%)  
**Fix Type:** Surgical leverage cap application per-sleeve  
**Files:** `scripts/leverage_manager.py` (+6 LOC)

---

## Problem

K446 end-to-end test discovered:
- `compute_position_size(sleeve_name)` applied 3x leverage uniformly to ALL sleeves
- sUSDe is a spot yield product (no leverage support) → should be capped at 1x
- At LIVE_3X: sUSDe notional incorrectly = $400K × 3.0 = $1.2M margin
- Total margin used: $8.8M / $10M AUM = **88%** (exceeds 80% circuit breaker threshold)

## Solution

Modified `compute_position_size()` to apply per-sleeve exchange caps BEFORE computing notional:

```python
# K448: cap leverage by exchange limit per sleeve
cap_key_map = {
    "K280":   "K280_K208_HL",
    "K297":   "K297_PAXG",
    "sUSDe":  "sUSDe",
}
cap_key = cap_key_map.get(sleeve_name, sleeve_name)
exchange_caps = cfg.get("exchange_caps", DEFAULT_EXCHANGE_CAPS)
sleeve_cap = float(exchange_caps.get(cap_key, raw_leverage))
effective_leverage = min(raw_leverage, sleeve_cap)
```

sUSDe now correctly capped at 1x regardless of global leverage setting.

## Verification

Tested at LIVE_3X with $10M AUM:

| Sleeve | Notional | Leverage | Exchange Cap | Effective Lev | Margin |
|--------|----------|----------|--------------|---------------|--------|
| K280   | $18.0M   | 3x       | 3x           | 3x            | $6.0M  |
| K297   | $4.8M    | 3x       | 10x (PAXG)   | 3x            | $1.6M  |
| sUSDe  | $0.4M    | 3x       | 1x           | **1x**        | $0.4M  |
| **Total** | — | — | — | — | **$8.0M (80%)** |

- ✓ Margin used: 80% (was 88%)
- ✓ Circuit breaker: **STANDBY** (not FIRE)
- ✓ K280/K297 leverage unchanged (still apply 3x correctly)
- ✓ No regressions in PAPER_TRADE (1x) mode

## Config

`data/leverage_config.json` already includes:
```json
"exchange_caps": {
    "sUSDe": 1.0
}
```

No changes needed.

## Deployment Notes

1. Fix is backward-compatible; works at all leverage levels (PAPER_TRADE/LIVE_1.5X/LIVE_3X)
2. Circuit breaker integration unaffected (still monitors margin_used_pct)
3. Production daemons (K280, K297, K376) unaffected by margin reduction
4. K344 sUSDe OC daemon benefits from correct margin accounting

---

*Wave K448 fix: 6-LOC surgical patch, 0 LOC in config*
