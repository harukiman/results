# K380 — K376 Volume Momentum Production Scaffold

**Wave:** K380 | **Parent:** K378 CONDITIONAL_ACCEPT | **Status:** DONE
**Completed:** 2026-05-27 09:35 JST | **Verdict:** SCAFFOLD-READY

---

## Executive Summary

K378 issued CONDITIONAL_ACCEPT for K376 volume-spike momentum with 7 activation criteria.
K380 implements all 7 criteria as a production scaffold:

- `scripts/k376_momentum_run.py` — paper-trade daemon (5min cron via launchd)
- `com.cryptolab.k376-momentum.plist` — StartInterval=300, RunAtLoad=false
- `data/k376_momentum_dashboard.json` — live state (regime, fills, Sharpe, fill rate)
- `scripts/verify_deployment_status.py` — REGISTRY updated, 0 mismatches confirmed
- `scripts/emergency_hl_exit.py` — Bybit close-all gap fixed (K378 criterion #6)
- `docs/k302a_runbook.md` — §17 activation plan + §14.8 Bybit gap fix docs
- `report.html` — Live Monitoring row, K376 widget, v6.14 banner, task pipeline

---

## K378 Criteria Implementation

| # | Criterion | Implementation |
|---|-----------|---------------|
| 1 | BTC 20d SMA slope filter | `fetch_btc_1h_sma()` — 480 1h bars, half-period slope. Bear → exit 0. |
| 2 | ETH + LINK + AVAX universe | `UNIVERSE = ["ETH", "LINK", "AVAX"]` (PEPE/SUI dropped) |
| 3 | 3% sleeve allocation | `SLEEVE_PCT = 0.03`, recorded in all fill JSONL records |
| 4 | Maker-only execution | `fill_type = "post_only_limit"`, `maker_rebate_bps = 2.0` |
| 5 | 60-day paper-trade (G8 gate ≥ 65%) | `fill_rate_60d` computed from JSONL; `g8_gate_passed` flag in dashboard |
| 6 | K357 Bybit close-all endpoint | `close_bybit_positions()` in `emergency_hl_exit.py` (HMAC-SHA256, stdlib) |
| 7 | G8 + G9 live gates pre-activation | Thresholds enforced in dashboard, §17 gate table |

---

## Architecture

```
v6.14 target (post 60d paper-trade gate):
  K280 Core          73%   (from 75%)
  K297' Satellite    18.5% (from 20%)
  sUSDe OC            5%   (unchanged)
  K376 Momentum       3%   (NEW — after gate pass)
  ─────────────────────
  Total              99.5%
  HL exposure        58.5% (cap 65%, K355)
```

---

## Script Architecture — k376_momentum_run.py

Single-shot execution flow (launchd invokes every 5min):

1. Check `EMERGENCY_EXIT_TRIGGERED.flag` → exit 0 if present
2. Fetch BTC 1h OHLCV (480 bars = 20d) from Binance public API
3. Compute 20d SMA slope: `(late_half_avg - early_half_avg)`. slope > 0 = bull.
4. Bear regime → update dashboard, exit 0 (no signal eval)
5. Fetch 5min OHLCV for ETH, LINK, AVAX (288 bars = 24h)
6. Per coin: `vol_ratio = bar_vol / 12h_rolling_avg`. Signal if `vol_ratio > 4.0 AND |ret| > 0.4%`
7. Triggered signals → append to `data/k376_paper_fills.jsonl` (post-only limit simulation)
8. Load all fills → compute open positions (exit_time > now), fill_rate_60d, live_sharpe_30d
9. Write `data/k376_momentum_dashboard.json`

**Dependencies:** `requests` only (already in venv). No new packages.
**K339 compliance:** `REPO_ROOT = Path(__file__).resolve().parent.parent` — zero `/Users/` literals.

---

## Emergency Exit Bybit Gap Fix

`close_bybit_positions(api_key, api_secret, dry_run, logger, category="linear")`:

1. `POST /v5/order/cancel-all` — cancel all linear USDT perp orders
2. `GET  /v5/position/list`    — fetch open positions
3. `POST /v5/order/create ×N` — market-close each position (reduceOnly + IOC)

Signing: HMAC-SHA256 via `hmac` + `hashlib` (stdlib only — no eth-account needed for Bybit).
CLI: `--include-bybit` (default True) / `--no-bybit` to skip.

---

## Test Results

```
python3 scripts/k376_momentum_run.py --dry-run
  → BTC 20d SMA slope: -3306.82 (BEAR regime)
  → BEAR regime: skipped signal eval (regime gate working)
  → Dashboard update skipped (dry-run)

python3 scripts/verify_deployment_status.py
  → com.cryptolab.k376-momentum: SCAFFOLD-READY (html claims: SCAFFOLD-READY)
  → mismatches_with_html: 0 ✓

python3 scripts/emergency_hl_exit.py --dry-run --user 0x0000...
  → K357 DRY-RUN MODE ✓
  → Bybit dry-run acknowledged (--include-bybit=True logged)
```

---

## Next Steps (K381)

| Step | Action |
|------|--------|
| K381 | Run paper-trade daemon for 60 days; monitor fill_rate_60d |
| Gate | After 60d: confirm fill_rate_60d ≥ 0.65 AND live_sharpe_30d ≥ 1.0 |
| Universe expansion | After 30d Sharpe positive: add ADA; after +60d: evaluate SUI/PEPE |
| Capital activation | See docs/k302a_runbook.md §17.4 for activation commands |
| Rollback trigger | live_sharpe_30d < 0.5 OR fill_rate < 50% for 7+ days |
