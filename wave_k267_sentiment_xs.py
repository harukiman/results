"""Wave K267 — Sentiment Cross-Sectional Strategy.

Mechanism family: Macro/Sentiment (Fear & Greed, Altcoin Season, TVL momentum)
This is DISTINCT from K246a components (carry/momentum/staking flow).

Variants:
  K267a: F&G Extreme Fear (< 25) → long BTC, else cash
  K267b: Altcoin Season (>75 alts outperforming BTC 90d) → long alts vs BTC
  K267c: TVL momentum + F&G combined regime signal

Data sources:
  - Fear & Greed Index: https://api.alternative.me/fng/?limit=730
  - Total TVL: https://api.llama.fi/v2/historicalChainTvl
  - OHLCV: existing cache (daily 730d)

WF: 4-fold on K246a OOS window (2025-01-22 to 2026-04-14)
Correlation vs K198/K208/K226 from wave_k246_curves.json

Acceptance hard gates (K266 lesson):
  - OOS Sh >= 7.0
  - WF all 4 folds positive AND Sh >= 7 each
  - |rho| < 0.4 vs K198/K208/K226

Runtime: <12 min
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE   = Path("/Users/nekonaomichi/crypto-lab")
CACHE  = BASE / "cache"

# ── Constants ─────────────────────────────────────────────────────────────────
TRADING_DAYS = 365
OOS_START    = "2025-01-22"
OOS_END      = "2026-04-14"
N_FOLDS      = 4

# Altcoin season: top alts to use (all available in daily 730d cache)
ALTS_DAILY = [
    "ADA", "AVAX", "BNB", "DOGE", "LINK", "PEPE", "SOL", "SUI", "XRP"
]
BTC_SYM = "BTC"
ETH_SYM = "ETH"

# ── Utility ───────────────────────────────────────────────────────────────────

def elapsed() -> str:
    return f"{time.time() - START_TIME:.1f}s"


def sharpe(rets: pd.Series, ann: int = TRADING_DAYS) -> float:
    """Annualized Sharpe from daily returns."""
    if len(rets) < 5 or rets.std() == 0:
        return 0.0
    return float(rets.mean() / rets.std() * math.sqrt(ann))


def max_drawdown(cum: pd.Series) -> float:
    roll_max = cum.cummax()
    dd = (cum - roll_max) / (roll_max + 1e-12)
    return float(dd.min())


def wf_folds(rets: pd.Series, n_folds: int = N_FOLDS) -> List[Dict]:
    """Split OOS returns into n equal folds and compute per-fold Sharpe."""
    n = len(rets)
    fold_size = n // n_folds
    results = []
    for i in range(n_folds):
        start = i * fold_size
        end = (i + 1) * fold_size if i < n_folds - 1 else n
        fold_rets = rets.iloc[start:end]
        sh = sharpe(fold_rets)
        results.append({
            "fold": i,
            "start": str(rets.index[start].date()),
            "end": str(rets.index[end - 1].date()),
            "sharpe": round(sh, 4),
            "n_days": len(fold_rets),
            "ann_ret": round(float(fold_rets.mean() * TRADING_DAYS), 4),
            "max_dd": round(max_drawdown((1 + fold_rets).cumprod()), 6),
        })
    return results


def oos_metrics(rets: pd.Series) -> Dict:
    cum = (1 + rets).cumprod()
    sh = sharpe(rets)
    dd = max_drawdown(cum)
    ann_ret = float(rets.mean() * TRADING_DAYS)
    ann_vol = float(rets.std() * math.sqrt(TRADING_DAYS))
    total_ret = float(cum.iloc[-1] - 1) if len(cum) > 0 else 0.0
    win_rate = float((rets > 0).mean()) if len(rets) > 0 else 0.0
    return {
        "sharpe": round(sh, 4),
        "max_dd": round(dd, 6),
        "ann_ret": round(ann_ret, 4),
        "ann_vol": round(ann_vol, 6),
        "total_return": round(total_ret, 4),
        "win_rate": round(win_rate, 4),
        "n_days": len(rets),
    }


# ── 1. Fetch Fear & Greed Index ───────────────────────────────────────────────

FNG_CACHE = CACHE / "fng_daily.parquet"


def fetch_fng(limit: int = 730) -> pd.DataFrame:
    """Fetch Fear & Greed Index from alternative.me API."""
    if FNG_CACHE.exists():
        df = pd.read_parquet(FNG_CACHE)
        print(f"[{elapsed()}] F&G loaded from cache: {len(df)} rows")
        return df
    url = f"https://api.alternative.me/fng/?limit={limit}&format=json"
    print(f"[{elapsed()}] Fetching F&G from {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        rows = []
        for entry in data.get("data", []):
            ts = int(entry["timestamp"])
            rows.append({
                "date": pd.Timestamp(ts, unit="s").normalize(),
                "fng": int(entry["value"]),
                "label": entry["value_classification"],
            })
        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        df.to_parquet(FNG_CACHE)
        print(f"[{elapsed()}] F&G fetched: {len(df)} rows ({df['date'].iloc[0].date()} – {df['date'].iloc[-1].date()})")
        return df
    except Exception as e:
        print(f"[{elapsed()}] F&G fetch failed: {e}. Using synthetic fallback.")
        # Fallback: synthetic F&G based on BTC 30d returns (proxy)
        return None


# ── 2. Fetch Total TVL ─────────────────────────────────────────────────────────

TVL_CACHE = CACHE / "total_tvl_daily.parquet"


def fetch_total_tvl() -> Optional[pd.DataFrame]:
    """Fetch total crypto TVL from DeFiLlama."""
    if TVL_CACHE.exists():
        df = pd.read_parquet(TVL_CACHE)
        print(f"[{elapsed()}] TVL loaded from cache: {len(df)} rows")
        return df
    url = "https://api.llama.fi/v2/historicalChainTvl"
    print(f"[{elapsed()}] Fetching TVL from {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        rows = []
        for entry in data:
            rows.append({
                "date": pd.Timestamp(entry["date"], unit="s").normalize(),
                "tvl": float(entry["tvl"]),
            })
        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        df.to_parquet(TVL_CACHE)
        print(f"[{elapsed()}] TVL fetched: {len(df)} rows ({df['date'].iloc[0].date()} – {df['date'].iloc[-1].date()})")
        return df
    except Exception as e:
        print(f"[{elapsed()}] TVL fetch failed: {e}")
        return None


# ── 3. Load OHLCV Daily Data ──────────────────────────────────────────────────

def load_daily(sym: str) -> Optional[pd.DataFrame]:
    """Load 730-day daily OHLCV from cache."""
    path = CACHE / f"{sym}USDT_1d_730d.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    df = df.set_index("open_time").sort_index()
    df.index = pd.to_datetime(df.index).normalize()
    return df


# ── 4. Build Feature DataFrame ────────────────────────────────────────────────

def build_features(fng_df: Optional[pd.DataFrame], tvl_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Assemble daily feature set: F&G signals, Altcoin Season, TVL momentum."""
    btc = load_daily(BTC_SYM)
    if btc is None:
        raise RuntimeError("BTC daily cache missing")

    # Base date index
    dates = btc.index
    feat = pd.DataFrame(index=dates)

    # BTC daily return
    feat["btc_ret"] = btc["close"].pct_change()

    # ─── Fear & Greed ──────────────────────────────────────────────────────────
    if fng_df is not None:
        fng = fng_df.set_index("date")["fng"].reindex(dates, method="ffill")
        feat["fng"] = fng
        feat["fng_7d"]  = fng.rolling(7).mean()
        feat["fng_30d"] = fng.rolling(30).mean()
        # Extreme Fear flag
        feat["extreme_fear"] = (fng < 25).astype(float)
        feat["fear"]         = (fng < 50).astype(float)
        feat["greed"]        = (fng > 70).astype(float)
        feat["extreme_greed"]= (fng > 80).astype(float)
    else:
        # Synthetic proxy: when BTC 30d return < -15%, mimic extreme fear
        btc_30d = btc["close"].pct_change(30)
        feat["fng"]          = 50 - btc_30d.clip(-0.5, 0.5) * 100
        feat["fng_7d"]       = feat["fng"].rolling(7).mean()
        feat["fng_30d"]      = feat["fng"].rolling(30).mean()
        feat["extreme_fear"] = (feat["fng"] < 25).astype(float)
        feat["fear"]         = (feat["fng"] < 50).astype(float)
        feat["greed"]        = (feat["fng"] > 70).astype(float)
        feat["extreme_greed"]= (feat["fng"] > 80).astype(float)

    # ─── Altcoin Season ────────────────────────────────────────────────────────
    # % of alts outperforming BTC over rolling 90 days
    btc_90d = btc["close"].pct_change(90)
    alt_90d_returns = {}
    for sym in ALTS_DAILY:
        alt = load_daily(sym)
        if alt is not None:
            alt_ret = alt["close"].reindex(dates, method="ffill").pct_change(90)
            alt_90d_returns[sym] = alt_ret

    if alt_90d_returns:
        alt_df = pd.DataFrame(alt_90d_returns, index=dates)
        # At each day, count how many alts beat BTC 90d return
        beats_btc = (alt_df.T > btc_90d).T
        feat["alt_season"] = beats_btc.mean(axis=1) * 100  # 0-100 scale
        feat["alt_season_high"] = (feat["alt_season"] > 75).astype(float)
        feat["alt_season_low"]  = (feat["alt_season"] < 25).astype(float)
    else:
        feat["alt_season"]      = 50.0
        feat["alt_season_high"] = 0.0
        feat["alt_season_low"]  = 0.0

    # ─── TVL Momentum ──────────────────────────────────────────────────────────
    if tvl_df is not None:
        tvl = tvl_df.set_index("date")["tvl"].reindex(dates, method="ffill")
        feat["tvl_30d_chg"] = tvl.pct_change(30)
        feat["tvl_growing"]  = (feat["tvl_30d_chg"] > 0).astype(float)
        feat["tvl_expanding"]= (feat["tvl_30d_chg"] > 0.10).astype(float)
    else:
        feat["tvl_30d_chg"]  = 0.0
        feat["tvl_growing"]   = 0.0
        feat["tvl_expanding"] = 0.0

    feat = feat.dropna(subset=["btc_ret"])
    return feat


# ── 5. Strategy Implementations ───────────────────────────────────────────────

def strategy_k267a(feat: pd.DataFrame) -> pd.Series:
    """K267a: Extreme Fear Contrarian — long BTC when F&G < 25.

    Logic: When market is in extreme fear, historical evidence shows BTC tends
    to recover. Enter long BTC when F&G < 25, hold 1 day.
    Execution: signal from day t → return day t+1.
    """
    # Signal: 1 = long BTC, 0 = cash
    signal = feat["extreme_fear"].shift(1).fillna(0)
    rets = signal * feat["btc_ret"]
    return rets


def strategy_k267a_fear(feat: pd.DataFrame) -> pd.Series:
    """K267a_fear: Long BTC when F&G < 50 (broader fear zone)."""
    signal = feat["fear"].shift(1).fillna(0)
    rets = signal * feat["btc_ret"]
    return rets


def strategy_k267a_greed_short(feat: pd.DataFrame) -> pd.Series:
    """K267a_greed: Short BTC when F&G > 80 (extreme greed = contrarian short)."""
    signal = -feat["extreme_greed"].shift(1).fillna(0)
    rets = signal * feat["btc_ret"]
    return rets


def strategy_k267a_bidir(feat: pd.DataFrame) -> pd.Series:
    """K267a_bidir: Long in fear, short in greed."""
    long_sig  = feat["extreme_fear"].shift(1).fillna(0)
    short_sig = feat["extreme_greed"].shift(1).fillna(0)
    signal = long_sig - short_sig
    # normalize to unit exposure
    signal = signal.clip(-1, 1)
    rets = signal * feat["btc_ret"]
    return rets


def strategy_k267b(feat: pd.DataFrame) -> pd.Series:
    """K267b: Altcoin Season — when alt_season > 75, long equal-weight alts vs BTC.

    Logic: During alt season, hold equal-weight alt basket. During BTC season,
    hold BTC or cash.
    """
    # During alt season: long equal-weight alts, no BTC exposure
    # During BTC season: long BTC
    # Load individual alt returns
    btc = load_daily(BTC_SYM)
    btc_ret = btc["close"].pct_change().reindex(feat.index, method="ffill").fillna(0)

    alt_rets = []
    for sym in ALTS_DAILY:
        alt = load_daily(sym)
        if alt is not None:
            r = alt["close"].pct_change().reindex(feat.index, method="ffill").fillna(0)
            alt_rets.append(r)
    if alt_rets:
        alt_basket = pd.concat(alt_rets, axis=1).mean(axis=1)
    else:
        alt_basket = btc_ret * 0

    # Signal: day t signal → day t+1 return
    alt_season_sig = feat["alt_season_high"].shift(1).fillna(0)
    btc_season_sig = feat["alt_season_low"].shift(1).fillna(0)

    rets = alt_season_sig * alt_basket + btc_season_sig * btc_ret
    return rets


def strategy_k267b_xs(feat: pd.DataFrame) -> pd.Series:
    """K267b_xs: Cross-sectional — during alt season, long alts SHORT BTC."""
    btc = load_daily(BTC_SYM)
    btc_ret = btc["close"].pct_change().reindex(feat.index, method="ffill").fillna(0)

    alt_rets = []
    for sym in ALTS_DAILY:
        alt = load_daily(sym)
        if alt is not None:
            r = alt["close"].pct_change().reindex(feat.index, method="ffill").fillna(0)
            alt_rets.append(r)
    if alt_rets:
        alt_basket = pd.concat(alt_rets, axis=1).mean(axis=1)
    else:
        alt_basket = btc_ret * 0

    alt_season_sig = feat["alt_season_high"].shift(1).fillna(0)
    # Long alts, short BTC (dollar-neutral)
    rets = alt_season_sig * (alt_basket - btc_ret)
    return rets


def strategy_k267c(feat: pd.DataFrame) -> pd.Series:
    """K267c: TVL+F&G combined regime.

    Regime logic:
      Bull regime: TVL growing AND F&G > 50 → long BTC
      Bear regime: TVL shrinking AND F&G < 50 → short BTC
      Neutral: cash
    """
    btc_ret = feat["btc_ret"]
    tvl_up = feat["tvl_growing"].shift(1).fillna(0)
    tvl_dn = (1 - feat["tvl_growing"]).shift(1).fillna(0)
    fg_bull = feat["fear"].shift(1).fillna(0)  # fear < 50 = True = fear
    fg_greed = feat["greed"].shift(1).fillna(0)

    # Bull: TVL rising AND greed > 70
    bull = (tvl_up * fg_greed)
    # Bear: TVL falling AND fear < 50
    bear = (tvl_dn * fg_bull)

    signal = bull - bear
    rets = signal * btc_ret
    return rets


def strategy_k267c_v2(feat: pd.DataFrame) -> pd.Series:
    """K267c_v2: TVL expansion + fear = contrarian long (dip buying on TVL-backed markets)."""
    btc_ret = feat["btc_ret"]
    # Long when: TVL expanding (fundamental growth) AND fear (sentiment overshoot)
    tvl_expand = feat["tvl_expanding"].shift(1).fillna(0)
    fear_sig    = feat["fear"].shift(1).fillna(0)

    signal = tvl_expand * fear_sig
    rets = signal * btc_ret
    return rets


def strategy_k267d_altseason_fear(feat: pd.DataFrame) -> pd.Series:
    """K267d: Alt Season + Fear composite — when alts dominate AND fear is high,
    buy alts (dip in alt season).
    """
    btc = load_daily(BTC_SYM)
    btc_ret = btc["close"].pct_change().reindex(feat.index, method="ffill").fillna(0)

    alt_rets = []
    for sym in ALTS_DAILY:
        alt = load_daily(sym)
        if alt is not None:
            r = alt["close"].pct_change().reindex(feat.index, method="ffill").fillna(0)
            alt_rets.append(r)
    if alt_rets:
        alt_basket = pd.concat(alt_rets, axis=1).mean(axis=1)
    else:
        alt_basket = btc_ret * 0

    # Signal: alt season > 50 AND fear (F&G < 50)
    mod_alt_season = (feat["alt_season"] > 50).astype(float)
    fear_sig = feat["fear"]

    signal = (mod_alt_season * fear_sig).shift(1).fillna(0)
    rets = signal * alt_basket
    return rets


# ── 6. Walk-Forward Evaluation ────────────────────────────────────────────────

def evaluate_strategy(rets: pd.Series, name: str) -> Dict:
    """Evaluate strategy over OOS window with WF fold breakdown."""
    # Filter to OOS window
    oos_start = pd.Timestamp(OOS_START)
    oos_end   = pd.Timestamp(OOS_END)
    oos = rets[(rets.index >= oos_start) & (rets.index <= oos_end)].dropna()

    if len(oos) < 50:
        return {
            "name": name,
            "error": "insufficient OOS data",
            "oos": {},
            "folds": [],
            "fold_sharpes": [],
            "wf_min": None,
            "wf_mean": None,
        }

    oos_m = oos_metrics(oos)
    folds = wf_folds(oos)
    fold_shs = [f["sharpe"] for f in folds]

    return {
        "name": name,
        "oos": oos_m,
        "folds": folds,
        "fold_sharpes": [round(s, 4) for s in fold_shs],
        "wf_min": round(min(fold_shs), 4),
        "wf_mean": round(sum(fold_shs) / len(fold_shs), 4),
        "all_positive": all(s > 0 for s in fold_shs),
    }


# ── 7. Correlation vs K246a Components ───────────────────────────────────────

def compute_correlations(
    strategy_rets: Dict[str, pd.Series],
    reference_rets: Dict[str, pd.Series],
) -> Dict:
    """Compute correlation of each K267 variant vs K198/K208/K226."""
    corrs = {}
    for strat_name, s_rets in strategy_rets.items():
        corrs[strat_name] = {}
        for ref_name, r_rets in reference_rets.items():
            aligned = s_rets.align(r_rets, join="inner")
            s_aligned, r_aligned = aligned
            if len(s_aligned) < 10:
                corrs[strat_name][ref_name] = None
                continue
            rho = float(np.corrcoef(s_aligned, r_aligned)[0, 1])
            corrs[strat_name][ref_name] = round(rho, 4)
    return corrs


def load_reference_rets(curves_path: str) -> Dict[str, pd.Series]:
    """Load K198/K208/K226 daily returns from wave_k246_curves.json."""
    with open(curves_path) as f:
        data = json.load(f)
    dates = pd.to_datetime(data["dates"])
    ref_keys = ["K198", "K208", "K226", "K246a"]
    result = {}
    for key in ref_keys:
        if key in data:
            cum = pd.Series(data[key], index=dates, dtype=float)
            # Convert cumulative equity to daily returns
            rets = cum.pct_change().fillna(0)
            result[key] = rets
    return result


# ── 8. Main ───────────────────────────────────────────────────────────────────

def main():
    print(f"[{elapsed()}] === Wave K267 Sentiment XS Strategy ===")

    # 8.1 Fetch/load data
    fng_df  = fetch_fng(730)
    tvl_df  = fetch_total_tvl()

    # 8.2 Build features
    print(f"[{elapsed()}] Building feature DataFrame...")
    feat = build_features(fng_df, tvl_df)
    print(f"[{elapsed()}] Features: {feat.shape}, dates: {feat.index[0].date()} – {feat.index[-1].date()}")
    print(f"[{elapsed()}] F&G stats: mean={feat['fng'].mean():.1f}, extreme_fear_days={feat['extreme_fear'].sum():.0f}, alt_season_high_days={feat['alt_season_high'].sum():.0f}")

    # 8.3 Compute strategy returns
    print(f"[{elapsed()}] Computing strategy returns...")
    strategy_returns = {
        "K267a_extreme_fear":   strategy_k267a(feat),
        "K267a_fear":           strategy_k267a_fear(feat),
        "K267a_greed_short":    strategy_k267a_greed_short(feat),
        "K267a_bidir":          strategy_k267a_bidir(feat),
        "K267b_alt_season":     strategy_k267b(feat),
        "K267b_xs_neutral":     strategy_k267b_xs(feat),
        "K267c_tvl_fg":         strategy_k267c(feat),
        "K267c_v2_tvl_fear":    strategy_k267c_v2(feat),
        "K267d_altseason_fear": strategy_k267d_altseason_fear(feat),
    }

    # 8.4 Evaluate each
    print(f"[{elapsed()}] Evaluating strategies over OOS window...")
    results = {}
    for name, rets in strategy_returns.items():
        res = evaluate_strategy(rets, name)
        results[name] = res
        sh = res.get("oos", {}).get("sharpe", "N/A")
        folds = res.get("fold_sharpes", [])
        wf_min = res.get("wf_min", "N/A")
        print(f"  {name}: OOS Sh={sh}, folds={folds}, wf_min={wf_min}")

    # 8.5 Load reference equity curves
    print(f"[{elapsed()}] Loading K198/K208/K226 reference curves...")
    curves_path = str(BASE / "wave_k246_curves.json")
    ref_rets = load_reference_rets(curves_path)

    # 8.6 Compute correlations
    print(f"[{elapsed()}] Computing correlations vs K198/K208/K226...")
    oos_start = pd.Timestamp(OOS_START)
    oos_end   = pd.Timestamp(OOS_END)
    oos_strategy_rets = {}
    for name, rets in strategy_returns.items():
        oos_r = rets[(rets.index >= oos_start) & (rets.index <= oos_end)].dropna()
        oos_strategy_rets[name] = oos_r

    oos_ref_rets = {}
    for ref_name, r_rets in ref_rets.items():
        oos_r = r_rets[(r_rets.index >= oos_start) & (r_rets.index <= oos_end)]
        oos_ref_rets[ref_name] = oos_r

    corrs = compute_correlations(oos_strategy_rets, oos_ref_rets)

    # 8.7 Apply acceptance gates
    GATE_OOS_SH  = 7.0
    GATE_WF_SH   = 7.0
    GATE_RHO_MAX = 0.4

    gate_results = {}
    for name, res in results.items():
        oos_sh = res.get("oos", {}).get("sharpe", 0)
        wf_min = res.get("wf_min", 0) or 0
        all_pos = res.get("all_positive", False)
        fold_shs = res.get("fold_sharpes", [])
        all_above_7 = all(s >= GATE_WF_SH for s in fold_shs) if fold_shs else False

        rho_vals = [abs(corrs.get(name, {}).get(ref, 999)) for ref in ["K198", "K208", "K226"]]
        rho_ok = all(r < GATE_RHO_MAX for r in rho_vals if r < 900)

        gate = {
            "g_oos_sh": oos_sh >= GATE_OOS_SH,
            "g_wf_all_pos": all_pos,
            "g_wf_all_7": all_above_7,
            "g_rho": rho_ok,
            "passed": (oos_sh >= GATE_OOS_SH and all_pos and all_above_7 and rho_ok),
        }
        gate_results[name] = gate
        print(f"  {name}: gate={gate}")

    any_pass = any(g["passed"] for g in gate_results.values())
    best_oos_sh = max(
        (res.get("oos", {}).get("sharpe", -999) for res in results.values()),
        default=-999
    )
    best_variant = max(
        results.keys(),
        key=lambda k: results[k].get("oos", {}).get("sharpe", -999),
    )

    # 8.8 Build JSON output
    output = {
        "wave": "K267",
        "strategy": "Sentiment_CrossSectional",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "data_sources": {
            "fng": "alternative.me/fng" if fng_df is not None else "synthetic_btc_proxy",
            "tvl": "api.llama.fi/v2/historicalChainTvl" if tvl_df is not None else "unavailable",
            "ohlcv": "binance_cache_730d_daily",
        },
        "feature_summary": {
            "total_days": len(feat),
            "date_range": f"{feat.index[0].date()} – {feat.index[-1].date()}",
            "fng_mean": round(float(feat["fng"].mean()), 1),
            "extreme_fear_days": int(feat["extreme_fear"].sum()),
            "extreme_greed_days": int(feat["extreme_greed"].sum()),
            "alt_season_high_days": int(feat["alt_season_high"].sum()),
            "tvl_available": tvl_df is not None,
        },
        "oos_window": {"start": OOS_START, "end": OOS_END},
        "variants": {
            name: {
                "oos": res.get("oos", {}),
                "fold_sharpes": res.get("fold_sharpes", []),
                "wf_min": res.get("wf_min"),
                "wf_mean": res.get("wf_mean"),
                "all_positive": res.get("all_positive", False),
                "folds": res.get("folds", []),
                "gate": gate_results.get(name, {}),
                "correlations": corrs.get(name, {}),
            }
            for name, res in results.items()
        },
        "correlation_matrix": corrs,
        "gates": {
            "oos_sh_threshold": GATE_OOS_SH,
            "wf_fold_sh_threshold": GATE_WF_SH,
            "rho_max": GATE_RHO_MAX,
        },
        "best_variant": best_variant,
        "best_oos_sh": round(best_oos_sh, 4),
        "any_pass": any_pass,
        "verdict": (
            "PASSED — at least one variant meets K266 hard criteria. INVESTIGATE for K268."
            if any_pass else
            "FAILED — no variant meets Sh>=7 all-folds gate. K267 sentiment signals as FRAMEWORK only."
        ),
    }

    out_path = BASE / "wave_k267_sentiment_xs.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"[{elapsed()}] JSON saved: {out_path}")

    # 8.9 Build curves JSON
    # Build equity curves for each variant over full history
    curves_out = {"dates": [str(d.date()) for d in feat.index]}

    for name, rets in strategy_returns.items():
        rets_aligned = rets.reindex(feat.index, fill_value=0.0)
        cum = (1 + rets_aligned).cumprod().tolist()
        curves_out[name] = [round(v, 6) for v in cum]

    # Add sentiment indicators
    curves_out["fng"] = [round(v, 2) for v in feat["fng"].fillna(50).tolist()]
    curves_out["alt_season"] = [round(v, 2) for v in feat["alt_season"].fillna(50).tolist()]
    if feat["tvl_30d_chg"].abs().sum() > 0:
        curves_out["tvl_30d_chg"] = [round(v, 4) for v in feat["tvl_30d_chg"].fillna(0).tolist()]

    curves_path_out = BASE / "wave_k267_curves.json"
    with open(curves_path_out, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"[{elapsed()}] Curves saved: {curves_path_out}")

    # 8.10 Print summary
    print(f"\n{'=' * 70}")
    print(f"WAVE K267 SENTIMENT XS — SUMMARY")
    print(f"{'=' * 70}")
    print(f"Best variant: {best_variant} OOS Sh={best_oos_sh:.4f}")
    print(f"Any gate passed: {any_pass}")
    print(f"\nPer-variant OOS Sharpe and WF folds:")
    for name, res in sorted(results.items(), key=lambda x: x[1].get("oos", {}).get("sharpe", -999), reverse=True):
        sh = res.get("oos", {}).get("sharpe", "N/A")
        folds = res.get("fold_sharpes", [])
        wf_min = res.get("wf_min", "N/A")
        rhos = {k: v for k, v in corrs.get(name, {}).items() if k in ["K198", "K208", "K226"]}
        print(f"  {name}: OOS={sh:.3f}, folds={[f'{s:.2f}' for s in folds]}, wf_min={wf_min:.2f}, rhos={rhos}")
    print(f"\nVerdict: {output['verdict']}")
    print(f"Total runtime: {elapsed()}")

    return output


if __name__ == "__main__":
    main()
