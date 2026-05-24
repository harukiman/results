"""
Wave K156 — Hyperliquid Smart-Money Mirror (R6-13)

Hypothesis:
  Hyperliquid leaderboard is fully public. Top wallets by monthly ROI
  hold perp positions that may lead retail flow by hours-days. By
  aggregating their net positions (long minus short, USD-notional
  weighted) per asset, we obtain a "smart-money tilt" signal that
  can drive directional bias on MEXC perp universe.

Data sources:
  * Leaderboard snapshot:
      GET https://stats-data.hyperliquid.xyz/Mainnet/leaderboard
      Returns ~37k traders with day/week/month/allTime PnL+ROI+Vlm.
  * Position snapshot per wallet:
      POST https://api.hyperliquid.xyz/info
      body: {"type": "clearinghouseState", "user": "0x..."}
      Returns assetPositions[] with coin, szi (signed size), positionValue,
      leverage, entryPx.
  * Mid prices (for sanity & USD conversion):
      POST https://api.hyperliquid.xyz/info  body: {"type": "allMids"}

Data availability honestly assessed:
  * Current snapshot — YES, fully public, no auth, free.
  * Historical leaderboard — NOT exposed via public API. Hyperliquid
    only returns *current* leaderboard window stats; per-wallet
    historical PnL series and position history are NOT in the public
    info endpoints. Third-party indexers (Hypurrscan, ASXN) exist but
    require paid keys or scraping.
  * Therefore: NO backtest possible from public sources in 15 min.
    We build a forward-deployable framework with full pipeline and
    take a snapshot baseline; verdict will be FRAMEWORK READY pending
    forward observation.

Method (implemented):
  1. Pull leaderboard snapshot.
  2. Filter to "smart" subset: accountValue >= MIN_ACCT_USD and
     monthly volume >= MIN_VOL_USD (to exclude micro-accounts and
     dormant wallets), then take top N by month ROI.
  3. For each wallet (concurrently), pull clearinghouseState.
  4. Compute per-asset notional flow:
       net_notional[coin] = sum(szi_i * mid[coin]) across wallets
       gross_notional[coin] = sum(|szi_i| * mid[coin])
       net_share[coin] = net_notional / gross_notional   in [-1, +1]
       n_wallets[coin] = #wallets with non-zero position
  5. Map HL coin -> MEXC perp ticker (BTC -> BTCUSDT, etc.).
  6. Emit signal table; signal trigger: |net_share| >= 0.6 with
     n_wallets >= 5 AND gross_notional >= $1M. Direction = sign(net).

Forward deployment framework documented in JSON output.

Outputs:
  wave_k156_hl_smart_money.json   — snapshot + signal table + framework
  wave_k156_hl_smart_money.md     — human-readable summary
  (no curves.json — no backtest possible from public data)

Wall time budget: < 15 min (typical ~2-5 min).
"""

import concurrent.futures as cf
import datetime as dt
import json
import time
from pathlib import Path

import requests

ROOT = Path("/Users/nekonaomichi/crypto-lab")

# ----- knobs --------------------------------------------------------------
LEADERBOARD_URL = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
INFO_URL = "https://api.hyperliquid.xyz/info"

MIN_ACCT_USD = 100_000.0   # exclude micro accounts
MIN_VOL_USD = 5_000_000.0  # exclude dormant wallets (monthly volume)
TOP_N = 20                 # top N by month ROI
RANK_WINDOW = "month"      # ranking horizon
HTTP_TIMEOUT = 20
POSITION_WORKERS = 6       # parallel position fetches
WALLET_RETRIES = 2
GLOBAL_DEADLINE_SEC = 13 * 60  # hard cap, leave 2 min slack

# Signal gates (forward use)
SIG_NET_SHARE = 0.60
SIG_MIN_WALLETS = 5
SIG_MIN_GROSS_USD = 1_000_000.0

# MEXC perp ticker mapping (HL coin -> MEXC linear-USDT symbol).
# Hyperliquid uses bare coin tickers (BTC, ETH, kPEPE for 1000PEPE, etc.).
HL_TO_MEXC = {
    "BTC": "BTC_USDT", "ETH": "ETH_USDT", "SOL": "SOL_USDT",
    "BNB": "BNB_USDT", "XRP": "XRP_USDT", "DOGE": "DOGE_USDT",
    "ADA": "ADA_USDT", "AVAX": "AVAX_USDT", "LINK": "LINK_USDT",
    "DOT": "DOT_USDT", "SUI": "SUI_USDT", "NEAR": "NEAR_USDT",
    "APT": "APT_USDT", "OP": "OP_USDT", "ARB": "ARB_USDT",
    "TIA": "TIA_USDT", "SEI": "SEI_USDT", "INJ": "INJ_USDT",
    "ATOM": "ATOM_USDT", "LTC": "LTC_USDT", "BCH": "BCH_USDT",
    "FIL": "FIL_USDT", "AAVE": "AAVE_USDT", "ENA": "ENA_USDT",
    "ONDO": "ONDO_USDT", "WLD": "WLD_USDT", "PYTH": "PYTH_USDT",
    "JUP": "JUP_USDT", "JTO": "JTO_USDT", "TAO": "TAO_USDT",
    "WIF": "WIF_USDT", "BONK": "BONK_USDT", "HYPE": "HYPE_USDT",
    "kPEPE": "PEPE_USDT", "kBONK": "BONK_USDT", "kSHIB": "SHIB_USDT",
    "kFLOKI": "FLOKI_USDT", "kDOGS": "DOGS_USDT",
    "STRK": "STRK_USDT", "MANTA": "MANTA_USDT", "ARKM": "ARKM_USDT",
    "BOME": "BOME_USDT",
}


# ----- helpers ------------------------------------------------------------
def _window(row, name):
    for w in row.get("windowPerformances", []):
        if w[0] == name:
            return w[1]
    return {"pnl": "0", "roi": "0", "vlm": "0"}


def _safe_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def fetch_leaderboard():
    t0 = time.time()
    r = requests.get(LEADERBOARD_URL, timeout=HTTP_TIMEOUT * 2)
    r.raise_for_status()
    data = r.json()
    rows = data.get("leaderboardRows", [])
    return rows, time.time() - t0


def fetch_all_mids():
    r = requests.post(INFO_URL, json={"type": "allMids"}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    raw = r.json()
    # raw is {coin: priceStr}; ignore "@N" spot vault entries (start with @ or #)
    out = {}
    for k, v in raw.items():
        if k.startswith("@") or k.startswith("#"):
            continue
        out[k] = _safe_float(v)
    return out


def fetch_position(addr):
    last_err = None
    for attempt in range(WALLET_RETRIES + 1):
        try:
            r = requests.post(
                INFO_URL,
                json={"type": "clearinghouseState", "user": addr},
                timeout=HTTP_TIMEOUT,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.5 * (attempt + 1))
    return {"_error": str(last_err)}


# ----- core ---------------------------------------------------------------
def select_top_wallets(rows):
    filtered = []
    for r in rows:
        acct = _safe_float(r.get("accountValue"))
        mw = _window(r, RANK_WINDOW)
        vol = _safe_float(mw.get("vlm"))
        if acct < MIN_ACCT_USD or vol < MIN_VOL_USD:
            continue
        filtered.append(r)

    filtered.sort(key=lambda r: _safe_float(_window(r, RANK_WINDOW).get("roi")),
                  reverse=True)
    return filtered[:TOP_N], len(filtered)


# Stricter "persistent smart-money" cohort: large book + positive allTime ROI
# AND positive month ROI (rules out one-shot lucky punts).
PERSISTENT_MIN_ACCT_USD = 1_000_000.0     # >= $1M book
PERSISTENT_MIN_ALLTIME_ROI = 0.30          # +30% allTime
PERSISTENT_MIN_MONTH_VOL_USD = 25_000_000  # active in last 30d


def select_persistent_wallets(rows):
    """Cohort B: persistent profitable whales (less survivorship)."""
    out = []
    for r in rows:
        acct = _safe_float(r.get("accountValue"))
        mw = _window(r, RANK_WINDOW)
        aw = _window(r, "allTime")
        vol = _safe_float(mw.get("vlm"))
        month_roi = _safe_float(mw.get("roi"))
        all_roi = _safe_float(aw.get("roi"))
        if acct < PERSISTENT_MIN_ACCT_USD:
            continue
        if vol < PERSISTENT_MIN_MONTH_VOL_USD:
            continue
        if all_roi < PERSISTENT_MIN_ALLTIME_ROI:
            continue
        if month_roi <= 0:
            continue
        out.append(r)
    # rank by sqrt(allTime ROI) * log(account) — favors big, persistently winning books
    import math
    out.sort(
        key=lambda r: (
            math.sqrt(max(0.0, _safe_float(_window(r, "allTime").get("roi"))))
            * math.log(max(1.0, _safe_float(r.get("accountValue"))))
        ),
        reverse=True,
    )
    return out[:TOP_N], len(out)


def aggregate_positions(positions_by_addr, mids):
    """
    Returns dict: coin -> {
        net_notional_usd, gross_notional_usd, net_share,
        n_wallets_long, n_wallets_short, n_wallets, long_notional,
        short_notional, mexc_symbol
    }
    """
    agg = {}
    for addr, ch in positions_by_addr.items():
        if not isinstance(ch, dict) or "_error" in ch:
            continue
        for ap in ch.get("assetPositions", []):
            p = ap.get("position", {})
            coin = p.get("coin")
            if not coin:
                continue
            szi = _safe_float(p.get("szi"))   # signed contract size
            pos_val = _safe_float(p.get("positionValue"))  # absolute USD value
            # Prefer positionValue (HL provides it); fall back to szi*mid
            if pos_val <= 0:
                px = mids.get(coin, 0.0)
                pos_val = abs(szi) * px
            if pos_val <= 0:
                continue
            signed_val = pos_val if szi > 0 else -pos_val

            rec = agg.setdefault(coin, {
                "net_notional_usd": 0.0,
                "gross_notional_usd": 0.0,
                "long_notional_usd": 0.0,
                "short_notional_usd": 0.0,
                "n_wallets_long": 0,
                "n_wallets_short": 0,
                "wallets": set(),
            })
            rec["net_notional_usd"] += signed_val
            rec["gross_notional_usd"] += pos_val
            if szi > 0:
                rec["long_notional_usd"] += pos_val
                rec["n_wallets_long"] += 1
            else:
                rec["short_notional_usd"] += pos_val
                rec["n_wallets_short"] += 1
            rec["wallets"].add(addr)

    out = {}
    for coin, rec in agg.items():
        gross = rec["gross_notional_usd"]
        net_share = rec["net_notional_usd"] / gross if gross > 0 else 0.0
        out[coin] = {
            "mexc_symbol": HL_TO_MEXC.get(coin),
            "net_notional_usd": round(rec["net_notional_usd"], 2),
            "gross_notional_usd": round(gross, 2),
            "long_notional_usd": round(rec["long_notional_usd"], 2),
            "short_notional_usd": round(rec["short_notional_usd"], 2),
            "n_wallets": len(rec["wallets"]),
            "n_wallets_long": rec["n_wallets_long"],
            "n_wallets_short": rec["n_wallets_short"],
            "net_share": round(net_share, 4),
        }
    return out


def derive_signals(agg):
    signals = []
    for coin, rec in agg.items():
        if rec["gross_notional_usd"] < SIG_MIN_GROSS_USD:
            continue
        if rec["n_wallets"] < SIG_MIN_WALLETS:
            continue
        if abs(rec["net_share"]) < SIG_NET_SHARE:
            continue
        signals.append({
            "coin": coin,
            "mexc_symbol": rec["mexc_symbol"],
            "direction": "LONG" if rec["net_share"] > 0 else "SHORT",
            "net_share": rec["net_share"],
            "gross_usd": rec["gross_notional_usd"],
            "n_wallets": rec["n_wallets"],
        })
    signals.sort(key=lambda s: (abs(s["net_share"]), s["gross_usd"]),
                 reverse=True)
    return signals


def build_forward_framework():
    return {
        "polling_cadence_minutes": 60,
        "rebalance_cadence_hours": 4,
        "min_hold_hours": 4,
        "max_hold_hours": 72,
        "position_sizing": (
            "per-signal target weight = clip(net_share, -1, 1) * "
            "min(1, gross_usd / $10M); total gross capped at 100%."
        ),
        "execution_venue": "MEXC perp linear USDT",
        "costs_assumed_bps": {"taker_in": 4.0, "taker_out": 4.0, "slippage": 3.0},
        "signal_gates": {
            "net_share_abs": SIG_NET_SHARE,
            "min_wallets": SIG_MIN_WALLETS,
            "min_gross_usd": SIG_MIN_GROSS_USD,
        },
        "wallet_filters": {
            "min_account_usd": MIN_ACCT_USD,
            "min_monthly_vol_usd": MIN_VOL_USD,
            "rank_window": RANK_WINDOW,
            "top_n": TOP_N,
        },
        "data_pipeline": [
            "1. GET stats-data.hyperliquid.xyz/Mainnet/leaderboard",
            "2. Filter & rank top wallets by monthly ROI",
            "3. POST info clearinghouseState per wallet (parallel)",
            "4. Aggregate per-asset net notional, derive net_share",
            "5. Emit signals to MEXC perp executor",
            "6. Log snapshot to time-series store for ex-post evaluation",
        ],
        "risk_controls": [
            "Wallet churn detection: if a top wallet falls out of top_n, "
            "fade its contribution over 24h instead of instant flip.",
            "Anti-pump filter: skip coin if 24h funding rate > +0.05% / 8h "
            "(sign of late long crowd).",
            "Hard kill: pause if rolling 7d Sharpe < -1 for 3 consecutive days.",
        ],
        "expected_backtest_when_data_available": (
            "Need >=180d of leaderboard snapshots (1h cadence) + matched "
            "MEXC close prices. Hold=24h. Costs=4bps+4bps+3bps. Target "
            "OOS Sharpe >= 0.8 and MaxDD > -25% to pass mini-gates."
        ),
        "data_blockers": [
            "Public Hyperliquid API exposes only CURRENT leaderboard "
            "window stats (day/week/month/allTime); no historical series.",
            "Per-wallet position history would require persistent polling "
            "or paid indexer (Hypurrscan, ASXN, Goldsky).",
            "Recommended: deploy snapshot poller now (cron @ 1h) and "
            "accumulate >=90d before first backtest attempt.",
        ],
    }


# ----- main ---------------------------------------------------------------
def main():
    t_start = time.time()
    timeline = []

    def log(stage, **extra):
        elapsed = time.time() - t_start
        timeline.append({"stage": stage, "elapsed_sec": round(elapsed, 2),
                         **extra})

    log("start")

    # 1) leaderboard
    try:
        rows, dt_lb = fetch_leaderboard()
        log("leaderboard_ok", rows=len(rows), fetch_sec=round(dt_lb, 2))
    except Exception as e:  # noqa: BLE001
        log("leaderboard_FAILED", error=str(e))
        rows = []

    # 2) mids
    try:
        mids = fetch_all_mids()
        log("mids_ok", n_coins=len(mids))
    except Exception as e:  # noqa: BLE001
        log("mids_FAILED", error=str(e))
        mids = {}

    # 3) select two cohorts
    top, n_universe = select_top_wallets(rows)
    log("selected_top", n_universe=n_universe, top_n=len(top))
    persistent, n_persistent_univ = select_persistent_wallets(rows)
    log("selected_persistent", n_universe=n_persistent_univ, top_n=len(persistent))

    # 4) parallel position fetch (union of both cohorts)
    positions_by_addr = {}
    addr_set = {r["ethAddress"] for r in top} | {r["ethAddress"] for r in persistent}
    if addr_set:
        deadline = t_start + GLOBAL_DEADLINE_SEC
        with cf.ThreadPoolExecutor(max_workers=POSITION_WORKERS) as ex:
            fut_to_addr = {ex.submit(fetch_position, a): a for a in addr_set}
            for fut in cf.as_completed(fut_to_addr):
                addr = fut_to_addr[fut]
                if time.time() > deadline:
                    positions_by_addr[addr] = {"_error": "deadline"}
                    continue
                try:
                    positions_by_addr[addr] = fut.result()
                except Exception as e:  # noqa: BLE001
                    positions_by_addr[addr] = {"_error": str(e)}
    n_ok = sum(1 for v in positions_by_addr.values()
               if isinstance(v, dict) and "_error" not in v)
    log("positions_done", n_wallets=len(positions_by_addr), n_ok=n_ok)

    # 5) aggregate per cohort
    top_positions = {r["ethAddress"]: positions_by_addr.get(r["ethAddress"], {})
                     for r in top}
    persistent_positions = {r["ethAddress"]: positions_by_addr.get(r["ethAddress"], {})
                            for r in persistent}
    agg = aggregate_positions(top_positions, mids)
    agg_persistent = aggregate_positions(persistent_positions, mids)
    log("aggregated", n_coins=len(agg), n_coins_persistent=len(agg_persistent))

    # 6) signals per cohort
    signals = derive_signals(agg)
    signals_persistent = derive_signals(agg_persistent)
    log("signals_derived", n_signals=len(signals),
        n_signals_persistent=len(signals_persistent))

    # Cross-cohort overlap (high-confidence signals = appear in both)
    sig_top_set = {s["coin"] + s["direction"] for s in signals}
    cross_signals = [s for s in signals_persistent
                     if s["coin"] + s["direction"] in sig_top_set]

    # 7) snapshot table for ALL aggregated coins (forward logging)
    snapshot_table = sorted(
        [{"coin": c, **rec} for c, rec in agg.items()],
        key=lambda r: r["gross_notional_usd"], reverse=True,
    )

    # Wallet roster (for transparency / reproducibility)
    def _roster_of(cohort):
        out_r = []
        for r in cohort:
            mw = _window(r, RANK_WINDOW)
            aw = _window(r, "allTime")
            ch = positions_by_addr.get(r["ethAddress"], {})
            n_pos = len(ch.get("assetPositions", [])) if isinstance(ch, dict) else 0
            out_r.append({
                "address": r["ethAddress"],
                "account_value_usd": _safe_float(r.get("accountValue")),
                "month_roi_pct": round(_safe_float(mw.get("roi")) * 100, 3),
                "alltime_roi_pct": round(_safe_float(aw.get("roi")) * 100, 3),
                "month_vlm_usd": _safe_float(mw.get("vlm")),
                "n_positions": n_pos,
                "fetch_ok": isinstance(ch, dict) and "_error" not in ch,
            })
        return out_r

    wallet_roster = _roster_of(top)
    persistent_roster = _roster_of(persistent)

    # Concentration / quality stats for top cohort
    median_acct_top = float(sorted(w["account_value_usd"] for w in wallet_roster)[len(wallet_roster) // 2]) if wallet_roster else 0.0
    median_pos_top = sorted(w["n_positions"] for w in wallet_roster)[len(wallet_roster) // 2] if wallet_roster else 0
    median_acct_pers = float(sorted(w["account_value_usd"] for w in persistent_roster)[len(persistent_roster) // 2]) if persistent_roster else 0.0
    median_pos_pers = sorted(w["n_positions"] for w in persistent_roster)[len(persistent_roster) // 2] if persistent_roster else 0

    bias_warnings = []
    if median_acct_top < 1_000_000:
        bias_warnings.append(
            f"Top cohort median account value is ${median_acct_top:,.0f} "
            f"(< $1M). These are micro-accounts whose +ROI is likely lucky "
            f"directional punts rather than alpha. Use the 'persistent' "
            f"cohort signals as the primary input."
        )
    if median_pos_top <= 2:
        bias_warnings.append(
            f"Top cohort median # of open positions is {median_pos_top}. "
            "Low diversification = high single-bet survivorship bias."
        )
    if not persistent:
        bias_warnings.append(
            "Persistent cohort is EMPTY at current filters — no wallets "
            "with acct>=$1M AND allTime ROI>=30% AND month vol>=$25M AND "
            "month ROI>0. Relax filters or treat the top cohort cautiously."
        )

    framework = build_forward_framework()

    out = {
        "wave": "K156",
        "title": "Hyperliquid Smart-Money Mirror",
        "as_of_utc": dt.datetime.utcnow().isoformat() + "Z",
        "as_of_jst": (dt.datetime.utcnow() + dt.timedelta(hours=9)).isoformat() + "+09:00",
        "data_availability": {
            "leaderboard_snapshot": True,
            "wallet_positions_snapshot": True,
            "mid_prices": True,
            "historical_leaderboard": False,
            "historical_wallet_positions": False,
            "backtest_possible_from_public_data": False,
            "reason": (
                "Hyperliquid public info API exposes only current-window "
                "leaderboard stats and current clearinghouseState. No "
                "historical leaderboard series and no per-wallet position "
                "history are publicly retrievable."
            ),
        },
        "config": {
            "min_acct_usd": MIN_ACCT_USD,
            "min_monthly_vol_usd": MIN_VOL_USD,
            "rank_window": RANK_WINDOW,
            "top_n": TOP_N,
            "signal_net_share_abs": SIG_NET_SHARE,
            "signal_min_wallets": SIG_MIN_WALLETS,
            "signal_min_gross_usd": SIG_MIN_GROSS_USD,
        },
        "universe_after_filter": n_universe,
        "wallet_roster": wallet_roster,
        "snapshot_aggregate": snapshot_table,
        "signals_live": signals,
        "persistent_cohort": {
            "filters": {
                "min_acct_usd": PERSISTENT_MIN_ACCT_USD,
                "min_alltime_roi": PERSISTENT_MIN_ALLTIME_ROI,
                "min_month_vol_usd": PERSISTENT_MIN_MONTH_VOL_USD,
                "month_roi": "> 0",
            },
            "universe_after_filter": n_persistent_univ,
            "wallet_roster": persistent_roster,
            "snapshot_aggregate": sorted(
                [{"coin": c, **rec} for c, rec in agg_persistent.items()],
                key=lambda r: r["gross_notional_usd"], reverse=True,
            ),
            "signals_live": signals_persistent,
        },
        "cross_cohort_high_confidence_signals": cross_signals,
        "bias_warnings": bias_warnings,
        "cohort_quality": {
            "top_median_acct_usd": median_acct_top,
            "top_median_n_positions": median_pos_top,
            "persistent_median_acct_usd": median_acct_pers,
            "persistent_median_n_positions": median_pos_pers,
        },
        "forward_framework": framework,
        "verdict": "FRAMEWORK READY",
        "verdict_reason": (
            "Public pipeline works end-to-end (leaderboard + per-wallet "
            "positions + mid prices). No historical data path exists from "
            "public sources, so no backtest is possible within the wall-time "
            "budget. Recommend deploying a 1h snapshot poller and "
            "accumulating >=90d before evaluating the signal vs MEXC perp "
            "returns."
        ),
        "next_steps": [
            "Deploy launchd plist com.cryptolab.k156-hl-poll.plist running "
            "this script hourly; write snapshots to cache/k156_hl_snap_*.json.",
            "Build companion ingester wave_k156_evaluate.py: after 30d of "
            "snapshots, correlate per-coin net_share(t) vs MEXC perp "
            "fwd-24h return. Compute Spearman IC per coin and pooled.",
            "If pooled IC > 0.05 with p<0.05 at 30d, escalate to live paper "
            "with $1k notional via existing ct_forward harness.",
            "Optional: subscribe to Hypurrscan or build local ETL on the "
            "Hyperliquid L1 RPC to recover 180d history.",
        ],
        "timeline": timeline,
        "wall_time_sec": round(time.time() - t_start, 2),
    }

    json_path = ROOT / "wave_k156_hl_smart_money.json"
    json_path.write_text(json.dumps(out, indent=2))
    print(f"WROTE {json_path}")

    # ---- markdown summary ----------------------------------------------------
    md_lines = []
    md_lines.append("# Wave K156 — Hyperliquid Smart-Money Mirror")
    md_lines.append("")
    md_lines.append(f"**as_of_utc:** {out['as_of_utc']}  ")
    md_lines.append(f"**as_of_jst:** {out['as_of_jst']}  ")
    md_lines.append(f"**wall_time:** {out['wall_time_sec']}s")
    md_lines.append("")
    md_lines.append("## Data Availability")
    md_lines.append("")
    da = out["data_availability"]
    md_lines.append(f"- leaderboard snapshot: **{da['leaderboard_snapshot']}**")
    md_lines.append(f"- wallet positions snapshot: **{da['wallet_positions_snapshot']}**")
    md_lines.append(f"- mid prices: **{da['mid_prices']}**")
    md_lines.append(f"- historical leaderboard: **{da['historical_leaderboard']}**")
    md_lines.append(f"- historical wallet positions: **{da['historical_wallet_positions']}**")
    md_lines.append(f"- backtest possible from public data: **{da['backtest_possible_from_public_data']}**")
    md_lines.append("")
    md_lines.append(f"_reason_: {da['reason']}")
    md_lines.append("")
    md_lines.append("## Config")
    md_lines.append("")
    md_lines.append(f"- universe filter: acct >= ${MIN_ACCT_USD:,.0f}, "
                    f"monthly vol >= ${MIN_VOL_USD:,.0f}")
    md_lines.append(f"- top N by {RANK_WINDOW} ROI: **{TOP_N}**")
    md_lines.append(f"- signal gates: |net_share| >= {SIG_NET_SHARE}, "
                    f"n_wallets >= {SIG_MIN_WALLETS}, "
                    f"gross >= ${SIG_MIN_GROSS_USD:,.0f}")
    md_lines.append("")
    md_lines.append(f"## Wallet Roster (top {len(wallet_roster)})")
    md_lines.append("")
    md_lines.append("| # | address | acct ($M) | month ROI % | month vol ($M) | #pos | ok |")
    md_lines.append("|---:|---|---:|---:|---:|---:|---:|")
    for i, w in enumerate(wallet_roster, 1):
        md_lines.append(
            f"| {i} | `{w['address'][:10]}...` "
            f"| {w['account_value_usd']/1e6:.2f} "
            f"| {w['month_roi_pct']:+.1f} "
            f"| {w['month_vlm_usd']/1e6:.1f} "
            f"| {w['n_positions']} "
            f"| {'OK' if w['fetch_ok'] else 'X'} |"
        )
    md_lines.append("")
    md_lines.append("## Live Snapshot Aggregate (top 30 by gross notional)")
    md_lines.append("")
    md_lines.append("| coin | MEXC | gross ($M) | net ($M) | net_share | n_w | long_w | short_w |")
    md_lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for r in snapshot_table[:30]:
        md_lines.append(
            f"| {r['coin']} | {r.get('mexc_symbol') or '-'} "
            f"| {r['gross_notional_usd']/1e6:.2f} "
            f"| {r['net_notional_usd']/1e6:+.2f} "
            f"| {r['net_share']:+.2f} "
            f"| {r['n_wallets']} "
            f"| {r['n_wallets_long']} "
            f"| {r['n_wallets_short']} |"
        )
    md_lines.append("")
    md_lines.append("## Live Signals — Cohort A: Top Monthly ROI (gates passed)")
    md_lines.append("")
    if signals:
        md_lines.append("| coin | MEXC | dir | net_share | gross ($M) | n_w |")
        md_lines.append("|---|---|:---:|---:|---:|---:|")
        for s in signals:
            md_lines.append(
                f"| {s['coin']} | {s['mexc_symbol'] or '-'} | **{s['direction']}** "
                f"| {s['net_share']:+.2f} "
                f"| {s['gross_usd']/1e6:.2f} "
                f"| {s['n_wallets']} |"
            )
    else:
        md_lines.append("_No coin passed all three gates in this snapshot._")
    md_lines.append("")

    md_lines.append(f"## Cohort B: Persistent Whales (n={len(persistent_roster)})")
    md_lines.append("")
    md_lines.append(
        f"Filters: acct >= ${PERSISTENT_MIN_ACCT_USD:,.0f}, allTime ROI "
        f">= {PERSISTENT_MIN_ALLTIME_ROI*100:.0f}%, month vol >= "
        f"${PERSISTENT_MIN_MONTH_VOL_USD:,.0f}, month ROI > 0."
    )
    md_lines.append("")
    if persistent_roster:
        md_lines.append("| # | address | acct ($M) | allTime ROI % | month ROI % | #pos |")
        md_lines.append("|---:|---|---:|---:|---:|---:|")
        for i, w in enumerate(persistent_roster, 1):
            md_lines.append(
                f"| {i} | `{w['address'][:10]}...` "
                f"| {w['account_value_usd']/1e6:.2f} "
                f"| {w['alltime_roi_pct']:+.1f} "
                f"| {w['month_roi_pct']:+.1f} "
                f"| {w['n_positions']} |"
            )
        md_lines.append("")
        md_lines.append("**Cohort B signals:**")
        md_lines.append("")
        if signals_persistent:
            md_lines.append("| coin | MEXC | dir | net_share | gross ($M) | n_w |")
            md_lines.append("|---|---|:---:|---:|---:|---:|")
            for s in signals_persistent:
                md_lines.append(
                    f"| {s['coin']} | {s['mexc_symbol'] or '-'} | **{s['direction']}** "
                    f"| {s['net_share']:+.2f} "
                    f"| {s['gross_usd']/1e6:.2f} "
                    f"| {s['n_wallets']} |"
                )
        else:
            md_lines.append("_No coin passed all three gates in this snapshot._")
    else:
        md_lines.append("_Persistent cohort is EMPTY at current filters._")
    md_lines.append("")

    md_lines.append("## Cross-Cohort High-Confidence Signals (A ∩ B)")
    md_lines.append("")
    if cross_signals:
        md_lines.append("These coins are flagged by BOTH the top-ROI cohort AND the persistent-whale cohort in the SAME direction. Highest conviction.")
        md_lines.append("")
        md_lines.append("| coin | MEXC | dir | net_share (B) | gross_B ($M) |")
        md_lines.append("|---|---|:---:|---:|---:|")
        for s in cross_signals:
            md_lines.append(
                f"| {s['coin']} | {s['mexc_symbol'] or '-'} | **{s['direction']}** "
                f"| {s['net_share']:+.2f} "
                f"| {s['gross_usd']/1e6:.2f} |"
            )
    else:
        md_lines.append("_No cross-cohort overlap right now._")
    md_lines.append("")

    md_lines.append("## Bias Warnings")
    md_lines.append("")
    if bias_warnings:
        for b in bias_warnings:
            md_lines.append(f"- {b}")
    else:
        md_lines.append("_None._")
    md_lines.append("")

    md_lines.append("## Cohort Quality")
    md_lines.append("")
    md_lines.append(f"- Cohort A median acct: ${median_acct_top:,.0f}, median #pos: {median_pos_top}")
    md_lines.append(f"- Cohort B median acct: ${median_acct_pers:,.0f}, median #pos: {median_pos_pers}")
    md_lines.append("")

    md_lines.append("## Forward-Deployment Framework")
    md_lines.append("")
    md_lines.append(f"- polling cadence: every {framework['polling_cadence_minutes']} min")
    md_lines.append(f"- rebalance cadence: every {framework['rebalance_cadence_hours']} h")
    md_lines.append(f"- hold: {framework['min_hold_hours']}h min, {framework['max_hold_hours']}h max")
    md_lines.append(f"- venue: {framework['execution_venue']}")
    md_lines.append(f"- assumed costs (bps): {framework['costs_assumed_bps']}")
    md_lines.append(f"- position sizing: {framework['position_sizing']}")
    md_lines.append("")
    md_lines.append("**Risk controls:**")
    for r in framework["risk_controls"]:
        md_lines.append(f"- {r}")
    md_lines.append("")
    md_lines.append("**Data blockers:**")
    for b in framework["data_blockers"]:
        md_lines.append(f"- {b}")
    md_lines.append("")
    md_lines.append("## Verdict")
    md_lines.append("")
    md_lines.append(f"**{out['verdict']}**")
    md_lines.append("")
    md_lines.append(out["verdict_reason"])
    md_lines.append("")
    md_lines.append("## Next Steps")
    md_lines.append("")
    for n in out["next_steps"]:
        md_lines.append(f"- {n}")
    md_lines.append("")
    md_lines.append("## Timeline")
    md_lines.append("")
    md_lines.append("| stage | elapsed (s) | detail |")
    md_lines.append("|---|---:|---|")
    for t in timeline:
        detail = ", ".join(f"{k}={v}" for k, v in t.items()
                           if k not in ("stage", "elapsed_sec"))
        md_lines.append(f"| {t['stage']} | {t['elapsed_sec']} | {detail} |")

    md_path = ROOT / "wave_k156_hl_smart_money.md"
    md_path.write_text("\n".join(md_lines))
    print(f"WROTE {md_path}")

    print()
    print(f"Wall time: {out['wall_time_sec']}s")
    print(f"Verdict:   {out['verdict']}")
    print(f"Cohort A signals: {len(signals)}")
    for s in signals[:5]:
        print(f"  A: {s['coin']:>6} {s['direction']:>5} net_share={s['net_share']:+.2f} "
              f"gross=${s['gross_usd']/1e6:.1f}M n_w={s['n_wallets']}")
    print(f"Cohort B signals: {len(signals_persistent)} (persistent whales)")
    for s in signals_persistent[:5]:
        print(f"  B: {s['coin']:>6} {s['direction']:>5} net_share={s['net_share']:+.2f} "
              f"gross=${s['gross_usd']/1e6:.1f}M n_w={s['n_wallets']}")
    print(f"Cross (A ∩ B): {len(cross_signals)}")
    for s in cross_signals[:5]:
        print(f"  X: {s['coin']:>6} {s['direction']:>5}")
    if bias_warnings:
        print()
        print("BIAS WARNINGS:")
        for b in bias_warnings:
            print(f"  ! {b}")

    return out


if __name__ == "__main__":
    main()
