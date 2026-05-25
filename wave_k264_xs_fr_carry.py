"""
Wave K264 — XS Funding-Rate Carry Spread (Bybit-only)
Objective: Pure cross-sectional carry within Bybit perps.
           Long low-FR symbols (shorts paying longs),
           Short high-FR symbols (longs paying shorts).
Signal: 30d rolling mean of 8h Bybit funding rates, ranked daily.
Sleeves: Top quartile (lowest FR = long), Bottom quartile (highest FR = short).
Dollar-neutral: sum(long_$) = sum(short_$).
Cost: 2bp per side maker (perp turnover).
Universe: All 44 Bybit FR 730d symbols with sufficient coverage.

Key distinction from existing strategies:
  K208: CEX-DEX spread (HL vs Bybit), per-symbol gate predictor
  K226: ETH-specific staking validator queue
  K198: Ridge ML allocator over momentum sub-strategies
  K264: Pure Bybit XS FR ranking (no DEX comparison, no momentum)

Runtime target: <12 min.
"""
from __future__ import annotations

import json
import math
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE  = Path("/Users/nekonaomichi/crypto-lab")
CACHE = BASE / "cache"

# ── Config ──────────────────────────────────────────────────────────────────
FR_WINDOW_DAYS = 30       # rolling mean of 8h FR → 30d = 90 events
QUARTILE       = 0.25     # top/bottom 25%
COST_BPS       = 2.0      # per side maker (perp)
COST_RATE      = COST_BPS / 1e4
PPY            = 365.0    # daily Sharpe annualisation
N_FOLDS        = 4
MIN_DAYS       = 400      # minimum daily bars required

# ── Universe: all symbols with Bybit FR 730d parquet ─────────────────────────
FR_SYMS_RAW = [
    "1000BONK","1000FLOKI","1000PEPE",
    "AAVE","ADA","APT","ARB","ARKM","ATOM","AVAX","AXS",
    "BNB","BOME","BTC","CRV","DOGE","DOT","ENA","ETH",
    "FET","IMX","INJ","JTO","JUP","LDO","LINK",
    "MANTA","MKR","NEAR","ONDO","OP","RNDR","SAND","SEI",
    "SOL","STRK","SUI","SUSHI","TAO","TIA","UNI","WIF","WLD","XRP",
]

OUT_JSON   = BASE / "wave_k264_xs_fr_carry.json"
OUT_CURVES = BASE / "wave_k264_curves.json"
OUT_MD     = BASE / "wave_k264_xs_fr_carry.md"

# ── Helpers ──────────────────────────────────────────────────────────────────
def sharpe(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 10 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(PPY))


def max_dd(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return 0.0
    eq   = np.cumprod(1 + r)
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min())


def ann_ret(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    return float(r.mean() * PPY)


def ann_vol(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r)]
    return float(r.std() * math.sqrt(PPY))


def win_rate(ret: np.ndarray) -> float:
    r = np.asarray(ret, dtype=float)
    r = r[np.isfinite(r) & (r != 0)]
    return float((r > 0).mean()) if len(r) > 0 else 0.0


def metrics(ret_arr: np.ndarray) -> dict:
    return {
        "sharpe":       sharpe(ret_arr),
        "max_dd":       max_dd(ret_arr),
        "ann_ret":      ann_ret(ret_arr),
        "ann_vol":      ann_vol(ret_arr),
        "win_rate":     win_rate(ret_arr),
        "total_return": float(np.nanprod(1 + ret_arr) - 1),
        "n_days":       int(np.sum(np.isfinite(ret_arr))),
    }


# ── Data loading ─────────────────────────────────────────────────────────────
def load_fr_panel() -> tuple[pd.DataFrame, list[str]]:
    """
    Load Bybit 8h FR for all candidate symbols → aggregate to daily mean FR.
    Returns (daily_fr_panel, kept_symbols).
    """
    frames = []
    kept   = []
    for sym in FR_SYMS_RAW:
        path = CACHE / f"bybit_fr_{sym}USDT_730d.parquet"
        if not path.exists():
            continue
        try:
            df = pd.read_parquet(path)
            df["ts"] = pd.to_datetime(df["timestamp"])
            df["date"] = df["ts"].dt.normalize()
            # daily mean of 3 × 8h events
            daily = df.groupby("date")["funding_rate"].mean().rename(sym)
            if len(daily) >= MIN_DAYS:
                frames.append(daily)
                kept.append(sym)
        except Exception as e:
            print(f"  [warn] {sym}: {e}")

    panel = pd.concat(frames, axis=1).sort_index()
    return panel, kept


def load_price_panel(syms: list[str]) -> pd.DataFrame:
    """
    Load 4h_730d close prices → aggregate to daily.
    For symbols without 4h data, fall back to 1d_730d.
    """
    frames = []
    for sym in syms:
        # Handle 1000X names: 1000BONK → BONK suffix doesn't exist in 4h
        raw_sym = sym.replace("1000", "")  # strip 1000 prefix for price lookup
        # Try 4h first (most symbols)
        path_4h = CACHE / f"{sym}USDT_4h_730d.parquet"
        path_1d = CACHE / f"{sym}USDT_1d_730d.parquet"
        # For 1000BONK etc., try BONKUSDT as fallback
        path_4h_raw = CACHE / f"{raw_sym}USDT_4h_730d.parquet"

        loaded = False
        for path, label in [(path_4h, "4h"), (path_1d, "1d"), (path_4h_raw, "4h_raw")]:
            if path.exists():
                try:
                    df = pd.read_parquet(path)
                    # detect columns
                    if "open_time" in df.columns:
                        df["date"] = pd.to_datetime(df["open_time"]).dt.normalize()
                    elif "timestamp" in df.columns:
                        df["date"] = pd.to_datetime(df["timestamp"]).dt.normalize()
                    else:
                        df["date"] = pd.to_datetime(df.index).normalize()
                    if "close" in df.columns:
                        daily = df.groupby("date")["close"].last().rename(sym)
                    else:
                        continue
                    frames.append(daily)
                    loaded = True
                    break
                except Exception:
                    continue
        if not loaded:
            # Use BTC as proxy (symbol weight will still be FR-driven, price used only for returns)
            pass

    if not frames:
        return pd.DataFrame()
    panel = pd.concat(frames, axis=1).sort_index()
    return panel


# ── Signal: 30d rolling mean FR → rank daily ─────────────────────────────────
def compute_fr_signal(fr_panel: pd.DataFrame) -> pd.DataFrame:
    """
    30d (calendar days) rolling mean of daily FR.
    Signal at day t uses FR up to and including t-1 (avoid lookahead).
    Shift +1 so signal is computed on yesterday's close and traded today.
    """
    roll = fr_panel.rolling(window=FR_WINDOW_DAYS, min_periods=15).mean()
    return roll.shift(1)  # known at start of trading day t


# ── Position sizing: XS carry sleeves ────────────────────────────────────────
def dollar_neutral_weights(sig_row: pd.Series) -> pd.Series:
    """
    Long top-quartile lowest FR (shorts paying longs = positive carry for longs).
    Short bottom-quartile highest FR (we receive the carry as short).

    Wait — FR carry logic:
      If FR > 0: longs pay shorts. As long, you PAY FR → negative.
      As short, you RECEIVE FR → positive carry.
    So:
      Short HIGH-FR symbols → you receive high positive FR.
      Long LOW-FR symbols   → you pay less FR (near zero or negative FR means longs receive).
    Combined: maximise carry income.

    Rank ascending (rank 1 = lowest FR):
      Longs: rank > n_sym - n_q  → highest ranked = lowest FR (close to 0 or negative)
      Shorts: rank <= n_q         → lowest ranked = highest negative signal... wait.

    FR can be positive or negative. We want:
      Long symbols where FR is MOST NEGATIVE (longs receive FR from shorts)
      Short symbols where FR is MOST POSITIVE (shorts receive FR from longs)

    So: ascending rank → rank 1 = most negative FR → go LONG
                         rank n = most positive FR → go SHORT
    """
    valid = sig_row.dropna()
    n_sym = len(valid)
    if n_sym < 4:
        return pd.Series(0.0, index=sig_row.index)

    n_q = max(1, int(n_sym * QUARTILE))
    ranked = valid.rank(ascending=True)

    # Long: bottom ranked (lowest/most-negative FR) — ascending rank 1..n_q
    longs  = ranked[ranked <= n_q].index
    # Short: top ranked (highest/most-positive FR) — ascending rank n-n_q..n
    shorts = ranked[ranked > n_sym - n_q].index

    w = pd.Series(0.0, index=sig_row.index)
    if len(longs) > 0:
        w[longs]  = +1.0 / len(longs)
    if len(shorts) > 0:
        w[shorts] = -1.0 / len(shorts)
    return w


def compute_weights(sig: pd.DataFrame) -> pd.DataFrame:
    return sig.apply(dollar_neutral_weights, axis=1)


# ── FR carry PnL ─────────────────────────────────────────────────────────────
def compute_pnl(price_panel: pd.DataFrame,
                weights: pd.DataFrame,
                fr_panel: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Daily PnL = price return component + FR carry component.

    For a long position with weight w:
      - Price return: w * (close_t / close_{t-1} - 1)
      - FR income: w * (-daily_mean_fr)  [pay FR when long if FR>0]
    For a short position with weight w (negative):
      - Price return: w * (close_t / close_{t-1} - 1) [reversed]
      - FR income: w * (-daily_mean_fr)  [receive FR when short if FR>0; w<0 → positive]

    Total FR contribution per day: -w_t * fr_t  (same sign rule as price return)
    Actually: position pnl_fr = w * (-fr) where fr is what the LONG pays.
      Long w>0, fr>0 → pays fr → pnl_fr = -w*fr < 0
      Short w<0, fr>0 → receives fr → pnl_fr = -w*fr > 0  ✓

    Since we hold continuously and rebalance daily, we capture 3 × 8h events per day.
    daily_fr_carry = sum of 3 events ≈ daily_mean_fr * 3 (but we store daily mean already).
    We stored daily MEAN of 3 events → multiply by 3 to get total daily FR.
    """
    # Align indices
    common_dates = price_panel.index.intersection(weights.index).intersection(fr_panel.index)
    price_c  = price_panel.loc[common_dates]
    weights_c = weights.loc[common_dates]
    fr_c     = fr_panel.loc[common_dates]

    # Price returns
    ret = price_c.pct_change()

    # Weights lagged by 1 (set at close t-1, applied to return at t)
    w_lag = weights_c.shift(1).fillna(0.0)

    # Price PnL component
    pnl_price = (w_lag * ret).sum(axis=1)

    # FR carry component: position has weight w, FR is daily mean of 3 events
    # Total FR paid/received = 3 * daily_mean_fr per position unit
    # pnl_fr per symbol = -w * 3 * fr  (long pays, short receives)
    fr_daily_total = fr_c * 3   # convert mean to total 3-event FR per day
    pnl_fr = (-w_lag * fr_daily_total).sum(axis=1)

    # Turnover cost
    turn = (weights_c - weights_c.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost = turn * COST_RATE

    pnl_gross = pnl_price + pnl_fr
    pnl_net   = pnl_gross - cost
    return pnl_net, pnl_gross, turn


# ── Walk-forward 4-fold ───────────────────────────────────────────────────────
def walk_forward(pnl: pd.Series) -> list[dict]:
    n      = len(pnl)
    fold_n = n // N_FOLDS
    folds  = []
    for i in range(N_FOLDS):
        lo = i * fold_n
        hi = (i + 1) * fold_n if i < N_FOLDS - 1 else n
        sub = pnl.iloc[lo:hi].values
        folds.append({
            "fold":  i,
            "start": str(pnl.index[lo].date()),
            "end":   str(pnl.index[hi - 1].date()),
            **metrics(sub),
        })
    return folds


# ── Correlation vs K246a components ──────────────────────────────────────────
def corr_vs_k246a(pnl_daily: pd.Series) -> dict:
    """Load K198 / K208 / K226 equity curves → compute daily return correlation."""
    corrs = {}

    # K198 — pnl_ridge is daily pnl
    try:
        with open(BASE / "wave_k198_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates_ml"])
        pnl   = pd.Series(d["pnl_ridge"], index=dates, name="K198")
        joined = pd.concat([pnl_daily, pnl], axis=1).dropna()
        corrs["K198"] = float(joined.iloc[:, 0].corr(joined.iloc[:, 1])) if len(joined) >= 30 else None
    except Exception as e:
        corrs["K198"] = f"error: {e}"

    # K208 — cumulative_pnl at 8h timestamps → convert to daily returns
    try:
        with open(BASE / "wave_k208_curves.json") as f:
            d = json.load(f)
        v    = d["K208_filtered"]
        ts   = pd.to_datetime(v["timestamps"])
        cpnl = pd.Series(v["cumulative_pnl"], index=ts)
        eq   = 1 + cpnl
        eq_d = eq.resample("1D").last().dropna()
        ret_d = eq_d.pct_change().dropna().rename("K208")
        joined = pd.concat([pnl_daily, ret_d], axis=1).dropna()
        corrs["K208"] = float(joined.iloc[:, 0].corr(joined.iloc[:, 1])) if len(joined) >= 30 else None
    except Exception as e:
        corrs["K208"] = f"error: {e}"

    # K226 — daily strategy return series
    try:
        with open(BASE / "wave_k226_curves.json") as f:
            d = json.load(f)
        dates = pd.to_datetime(d["dates"])
        ret_k226 = pd.Series(d["strat_daily_ret"], index=dates, name="K226")
        joined = pd.concat([pnl_daily, ret_k226], axis=1).dropna()
        corrs["K226"] = float(joined.iloc[:, 0].corr(joined.iloc[:, 1])) if len(joined) >= 30 else None
    except Exception as e:
        corrs["K226"] = f"error: {e}"

    # K259 (3-way FINAL production equivalent) — try wave_k259_curves
    try:
        with open(BASE / "wave_k259_curves.json") as f:
            d = json.load(f)
        # K259 has equity series
        for key in d:
            v = d[key]
            if isinstance(v, dict) and "equity" in v:
                ts  = pd.to_datetime(v.get("dates", []))
                eq  = pd.Series(v["equity"], index=ts)
                ret = eq.pct_change().dropna().rename("K259")
                joined = pd.concat([pnl_daily, ret], axis=1).dropna()
                corrs["K259"] = float(joined.iloc[:, 0].corr(joined.iloc[:, 1])) if len(joined) >= 30 else None
                break
        if "K259" not in corrs:
            corrs["K259"] = "no equity series found"
    except Exception as e:
        corrs["K259"] = f"error: {e}"

    return corrs


# ── Equity curve helper ───────────────────────────────────────────────────────
def equity_curve_data(pnl: pd.Series) -> list[dict]:
    eq = (1 + pnl.fillna(0)).cumprod()
    return [{"ts": str(idx.date()), "eq": float(v)} for idx, v in eq.items()]


# ── Regime analysis: FR environment by quartile ───────────────────────────────
def regime_analysis(pnl: pd.Series, fr_panel: pd.DataFrame) -> dict:
    """
    Split returns by crypto market FR regime (BTC FR as proxy).
    High FR regime: BTC 30d mean FR > 0.01% per 8h
    Low FR regime:  BTC 30d mean FR <= 0.01%
    """
    btc_fr_daily = fr_panel.get("BTC")
    if btc_fr_daily is None:
        return {}

    btc_roll = btc_fr_daily.rolling(30, min_periods=15).mean()
    threshold = 0.0001  # 0.01% per 8h event
    high_fr = btc_roll > threshold
    low_fr  = btc_roll <= threshold

    common = pnl.index.intersection(btc_roll.index)
    pnl_c     = pnl.loc[common]
    high_mask = high_fr.loc[common]
    low_mask  = low_fr.loc[common]

    r_high = pnl_c[high_mask].values
    r_low  = pnl_c[low_mask].values

    return {
        "high_fr_regime": {
            "n_days": int(high_mask.sum()),
            **metrics(r_high),
        },
        "low_fr_regime": {
            "n_days": int(low_mask.sum()),
            **metrics(r_low),
        },
    }


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print("=" * 72)
    print("Wave K264 — XS Funding-Rate Carry Spread (Bybit-only)")
    print("=" * 72)

    # 1. Load FR panel
    print(f"\nLoading Bybit FR for {len(FR_SYMS_RAW)} candidate symbols...")
    fr_panel, kept = load_fr_panel()
    print(f"  Kept {len(kept)} symbols | panel: {fr_panel.shape} | "
          f"{fr_panel.index[0].date()} → {fr_panel.index[-1].date()}")

    # Drop symbols with > 20% missing days
    frac_nan = fr_panel.isna().mean()
    fr_panel = fr_panel.loc[:, frac_nan < 0.20]
    kept = fr_panel.columns.tolist()
    print(f"  After NaN filter: {len(kept)} symbols: {kept}")

    # 2. Load price panel for return calculation
    print(f"\nLoading price panels for {len(kept)} symbols...")
    price_panel = load_price_panel(kept)
    # align to symbols we have price data for
    price_syms = [s for s in kept if s in price_panel.columns]
    price_panel = price_panel[price_syms]
    fr_panel_sub = fr_panel[price_syms]
    print(f"  Price data available for {len(price_syms)} symbols")

    if len(price_syms) < 10:
        print("FATAL: Insufficient symbols for XS strategy (<10). Exiting.")
        return

    # 3. Compute 30d rolling mean FR signal
    print("\nComputing 30d rolling mean FR signal...")
    sig = compute_fr_signal(fr_panel_sub)
    print(f"  Signal shape: {sig.shape}")

    # Spot-check signal: show typical FR spread range
    sig_recent = sig.dropna(how="all").iloc[-10:]
    fr_range = sig_recent.max(axis=1) - sig_recent.min(axis=1)
    print(f"  Recent daily FR spread (max-min): mean={fr_range.mean():.6f}, "
          f"min={fr_range.min():.6f}, max={fr_range.max():.6f}")

    # 4. Compute weights
    print("\nComputing dollar-neutral XS carry weights...")
    weights = compute_weights(sig)

    # Spot-check dollar-neutral
    sample_day = weights.dropna(how="all").iloc[-5]
    long_sum  = sample_day[sample_day > 0].sum()
    short_sum = sample_day[sample_day < 0].sum()
    n_long    = (sample_day > 0).sum()
    n_short   = (sample_day < 0).sum()
    print(f"  Sample day: long_sum={long_sum:.3f} ({n_long} syms)  "
          f"short_sum={short_sum:.3f} ({n_short} syms)")

    # 5. PnL
    print("\nComputing PnL (price return + FR carry - cost)...")
    pnl_net, pnl_gross, turnover = compute_pnl(price_panel, weights, fr_panel_sub)
    pnl_net = pnl_net.dropna()
    pnl_gross = pnl_gross.loc[pnl_net.index]
    print(f"  PnL series: {len(pnl_net)} days | "
          f"{pnl_net.index[0].date()} → {pnl_net.index[-1].date()}")

    # Split IS/OOS 70/30
    n      = len(pnl_net)
    is_cut = int(n * 0.70)
    is_ret  = pnl_net.iloc[:is_cut].values
    oos_ret = pnl_net.iloc[is_cut:].values

    is_m   = metrics(is_ret)
    oos_m  = metrics(oos_ret)
    full_m = metrics(pnl_net.values)
    gross_m = metrics(pnl_gross.values)

    print(f"\n  IS   ({pnl_net.index[0].date()} – {pnl_net.index[is_cut-1].date()}):")
    print(f"    Sharpe: {is_m['sharpe']:.3f}  MaxDD: {is_m['max_dd']:.2%}  "
          f"AnnRet: {is_m['ann_ret']:+.2%}")
    print(f"  OOS  ({pnl_net.index[is_cut].date()} – {pnl_net.index[-1].date()}):")
    print(f"    Sharpe: {oos_m['sharpe']:.3f}  MaxDD: {oos_m['max_dd']:.2%}  "
          f"AnnRet: {oos_m['ann_ret']:+.2%}")
    print(f"  Full: Sharpe: {full_m['sharpe']:.3f}  MaxDD: {full_m['max_dd']:.2%}  "
          f"AnnRet: {full_m['ann_ret']:+.2%}")
    print(f"  Gross (no cost): Sharpe: {gross_m['sharpe']:.3f}")

    # 6. Walk-forward 4-fold
    print("\nWalk-forward 4-fold breakdown...")
    wf = walk_forward(pnl_net)
    for f in wf:
        print(f"  Fold {f['fold']} ({f['start']} – {f['end']}): "
              f"SR={f['sharpe']:.3f}  DD={f['max_dd']:.2%}  ret={f['total_return']:+.2%}  "
              f"days={f['n_days']}")
    wf_min      = min(f["sharpe"] for f in wf)
    wf_all_pos  = all(f["sharpe"] > 0 for f in wf)
    wf_mean     = float(np.mean([f["sharpe"] for f in wf]))
    print(f"  WF mean SR: {wf_mean:.3f}  WF min SR: {wf_min:.3f}  "
          f"All positive: {wf_all_pos}")

    # 7. Turnover / cost
    avg_turn     = float(turnover.mean())
    avg_cost_pct = avg_turn * COST_RATE * 100
    print(f"\n  Avg daily turnover: {avg_turn:.3f}  "
          f"Implied cost: {avg_cost_pct:.4f}%/day  "
          f"Annual cost drag: {avg_cost_pct * 365:.2f}%")

    # 8. Regime analysis
    print("\nRegime analysis (BTC 30d FR as market proxy)...")
    regimes = regime_analysis(pnl_net, fr_panel_sub)
    for regime, rmet in regimes.items():
        print(f"  {regime}: n={rmet['n_days']}  SR={rmet['sharpe']:.3f}  "
              f"ret={rmet['ann_ret']:+.2%}")

    # 9. Correlation vs K246a components
    print("\nCorrelation vs K246a components...")
    pnl_indexed = pnl_net.copy()
    pnl_indexed.index = pd.to_datetime(pnl_indexed.index)
    corrs = corr_vs_k246a(pnl_indexed)
    for k, v in corrs.items():
        if isinstance(v, float):
            print(f"  |ρ| vs {k}: {v:+.4f}")
        else:
            print(f"  |ρ| vs {k}: {v}")

    # 10. Acceptance gates
    gates = {
        "G1_WF_all_folds_positive": bool(wf_all_pos),
        "G2_OOS_Sharpe_gt_1.0":     oos_m["sharpe"] > 1.0,
        "G3_rho_K198_lt_0.4":       (isinstance(corrs.get("K198"), float)
                                      and abs(corrs["K198"]) < 0.4),
        "G4_rho_K208_lt_0.4":       (isinstance(corrs.get("K208"), float)
                                      and abs(corrs["K208"]) < 0.4),
        "G5_rho_K226_lt_0.4":       (isinstance(corrs.get("K226"), float)
                                      and abs(corrs["K226"]) < 0.4),
        "G6_OOS_MaxDD_gt_neg30pct": oos_m["max_dd"] > -0.30,
    }
    n_pass = sum(gates.values())
    accepted = (gates["G1_WF_all_folds_positive"] and gates["G2_OOS_Sharpe_gt_1.0"]
                and gates["G3_rho_K198_lt_0.4"] and gates["G4_rho_K208_lt_0.4"])
    verdict = "ACCEPT — K265 integration recommended" if accepted else "REJECT — fails gates"

    print(f"\n{'=' * 72}")
    print("ACCEPTANCE GATES:")
    for k, v in gates.items():
        status = "PASS" if v else "FAIL"
        print(f"  [{status}] {k}")
    print(f"\nVERDICT: {verdict}  ({n_pass}/{len(gates)} gates passed)")
    print(f"{'=' * 72}")

    elapsed = time.time() - t0
    print(f"\nRuntime: {elapsed:.1f}s")

    # ── Build equity curve for JSON output ────────────────────────────────────
    eq_full = (1 + pnl_net.fillna(0)).cumprod()
    eq_oos  = (1 + pnl_net.iloc[is_cut:].fillna(0)).cumprod()

    # ── Save curves JSON ──────────────────────────────────────────────────────
    curves = {
        "K264_xs_fr_carry": {
            "dates":  [str(d.date()) for d in pnl_net.index],
            "equity": [float(v) for v in eq_full.values],
            "pnl":    [float(v) for v in pnl_net.values],
        },
        "K264_oos_only": {
            "dates":  [str(d.date()) for d in pnl_net.index[is_cut:]],
            "equity": [float(v) for v in (1 + pnl_net.iloc[is_cut:].fillna(0)).cumprod().values],
        },
    }
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2)
    print(f"Curves saved → {OUT_CURVES}")

    # ── Save metrics JSON ─────────────────────────────────────────────────────
    out = {
        "wave":     "K264",
        "strategy": "XS_FR_Carry_Bybit",
        "as_of":    pd.Timestamp.utcnow().isoformat(),
        "runtime_s": round(elapsed, 2),
        "config": {
            "symbols_final": price_syms,
            "n_symbols": len(price_syms),
            "fr_window_days": FR_WINDOW_DAYS,
            "quartile": QUARTILE,
            "cost_bps_per_side": COST_BPS,
            "rebalance": "daily",
        },
        "is_metrics":   is_m,
        "oos_metrics":  oos_m,
        "full_metrics": full_m,
        "gross_metrics": gross_m,
        "walk_forward_folds": wf,
        "wf_summary": {
            "mean_sharpe": wf_mean,
            "min_sharpe":  wf_min,
            "all_positive": wf_all_pos,
        },
        "turnover": {
            "avg_daily": avg_turn,
            "implied_cost_pct_day": avg_cost_pct,
        },
        "regime_analysis": regimes,
        "correlations": corrs,
        "gates": gates,
        "n_gates_passed": n_pass,
        "verdict": verdict,
        "date_range": {
            "start": str(pnl_net.index[0].date()),
            "end":   str(pnl_net.index[-1].date()),
            "is_end": str(pnl_net.index[is_cut - 1].date()),
            "oos_start": str(pnl_net.index[is_cut].date()),
            "n_days_total": n,
            "n_days_is": is_cut,
            "n_days_oos": n - is_cut,
        },
    }

    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Metrics saved → {OUT_JSON}")

    # ── Write markdown report ─────────────────────────────────────────────────
    corr_k198 = corrs.get("K198")
    corr_k208 = corrs.get("K208")
    corr_k226 = corrs.get("K226")
    corr_k259 = corrs.get("K259")
    corr_fmt = lambda x: f"{x:+.4f}" if isinstance(x, float) else str(x)

    md = f"""# Wave K264 — XS Funding-Rate Carry Spread (Bybit-only)

## Executive Summary
Pure cross-sectional carry within Bybit perps. Signal: 30d rolling mean FR per symbol.
Long lowest-FR quartile (shorts paying longs), Short highest-FR quartile (longs paying shorts).
Dollar-neutral, daily rebalance, 2bp/side maker cost.

**Verdict: {verdict}**

## Configuration
- Universe: {len(price_syms)} Bybit perp symbols (FR 730d cache)
- FR window: {FR_WINDOW_DAYS}d rolling mean (8h events aggregated → daily)
- Quartile: top/bottom {int(QUARTILE*100)}% = {int(len(price_syms) * QUARTILE + 0.5)} symbols per sleeve
- Cost: {COST_BPS}bp/side maker | Dollar-neutral | Daily rebalance
- Period: {out['date_range']['start']} → {out['date_range']['end']} ({n} days total)

## Performance Metrics

| Period | Sharpe | AnnRet | AnnVol | MaxDD | WinRate | TotRet |
|--------|--------|--------|--------|-------|---------|--------|
| IS (70%) | {is_m['sharpe']:.3f} | {is_m['ann_ret']:+.2%} | {is_m['ann_vol']:.2%} | {is_m['max_dd']:.2%} | {is_m['win_rate']:.1%} | {is_m['total_return']:+.2%} |
| OOS (30%) | {oos_m['sharpe']:.3f} | {oos_m['ann_ret']:+.2%} | {oos_m['ann_vol']:.2%} | {oos_m['max_dd']:.2%} | {oos_m['win_rate']:.1%} | {oos_m['total_return']:+.2%} |
| Full | {full_m['sharpe']:.3f} | {full_m['ann_ret']:+.2%} | {full_m['ann_vol']:.2%} | {full_m['max_dd']:.2%} | {full_m['win_rate']:.1%} | {full_m['total_return']:+.2%} |
| Gross | {gross_m['sharpe']:.3f} | {gross_m['ann_ret']:+.2%} | — | — | — | — |

## Walk-Forward 4-Fold Breakdown

| Fold | Period | Sharpe | MaxDD | TotRet | Days |
|------|--------|--------|-------|--------|------|
{chr(10).join(f"| {f['fold']} | {f['start']} – {f['end']} | {f['sharpe']:.3f} | {f['max_dd']:.2%} | {f['total_return']:+.2%} | {f['n_days']} |" for f in wf)}

**WF mean SR: {wf_mean:.3f}  |  WF min SR: {wf_min:.3f}  |  All folds positive: {wf_all_pos}**

## Regime Analysis (BTC 30d FR proxy)
{chr(10).join(f"- **{k}**: n={v['n_days']}d  SR={v['sharpe']:.3f}  AnnRet={v['ann_ret']:+.2%}" for k, v in regimes.items()) if regimes else "- N/A"}

## Correlation vs K246a Components

| Strategy | ρ | Orthogonal? |
|----------|---|-------------|
| K198 (Ridge ML) | {corr_fmt(corr_k198)} | {"YES" if isinstance(corr_k198, float) and abs(corr_k198) < 0.4 else "NO"} |
| K208 (CEX-DEX carry) | {corr_fmt(corr_k208)} | {"YES" if isinstance(corr_k208, float) and abs(corr_k208) < 0.4 else "NO"} |
| K226 (ETH validator) | {corr_fmt(corr_k226)} | {"YES" if isinstance(corr_k226, float) and abs(corr_k226) < 0.4 else "NO"} |
| K259 (3-way final) | {corr_fmt(corr_k259)} | {"YES" if isinstance(corr_k259, float) and abs(corr_k259) < 0.4 else "NO"} |

## Turnover & Cost
- Avg daily turnover: {avg_turn:.3f}
- Implied cost: {avg_cost_pct:.4f}%/day → {avg_cost_pct * 365:.2f}% annual drag
- Gross vs net Sharpe gap: {gross_m['sharpe'] - full_m['sharpe']:.3f}

## Acceptance Gates

| Gate | Status |
|------|--------|
{chr(10).join(f"| {k} | {'PASS' if v else 'FAIL'} |" for k, v in gates.items())}

**{n_pass}/{len(gates)} gates passed**

## vs K262 / K257 Comparison
- K262 (Dollar-neutral momentum): REJECTED — momentum family, regime-incompatible
- K257 (AdaptiveTrend): REJECTED — trend-following, regime-incompatible
- K264 (XS FR carry): **{verdict.split(' — ')[0]}**

Key difference from K208: K208 is per-symbol HL vs Bybit CEX-DEX spread;
K264 is cross-sectional within Bybit only — ranking symbols by their relative FR level.

## Verdict: K265 K246a Integration Plan {'(if ACCEPTED)' if not accepted else ''}
{"K264 meets all acceptance gates. Integration plan:" if accepted else "K264 does not meet acceptance gates. Not recommended for K265 integration."}
{"- Add K264 daily pnl as 4th leg alongside K198/K208/K226" if accepted else "- Consider stat-arb (cointegration pairs) as next alternative"}
{"- Weight via equal or Ridge-optimized allocation in K246a ensemble" if accepted else "- Or accept K246a 3-way as local production maximum"}
{"- Run 4-way correlation check vs existing 3-way to confirm |ρ| < 0.4" if accepted else ""}
{"- Recommended allocation: 10-20% alongside existing 3-way mix" if accepted else ""}
"""

    with open(OUT_MD, "w") as f:
        f.write(md)
    print(f"Report saved → {OUT_MD}")


if __name__ == "__main__":
    main()
