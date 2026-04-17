"""Backtesting engine v3 — stop-loss, take-profit, trailing stops."""

import pandas as pd
import numpy as np
from engine.metrics import compute_metrics, grade_strategy

FEE_RATE = 0.0007   # Realistic avg of maker/taker with tier discounts
SLIPPAGE = 0.0003   # Limit orders reduce slippage


def run_backtest(
    df: pd.DataFrame,
    signals: pd.Series,
    strategy_name: str = "unnamed",
    params: dict | None = None,
    stop_loss_pct: float = 0.0,   # 0 = disabled
    take_profit_pct: float = 0.0, # 0 = disabled
    trailing_stop_pct: float = 0.0,
    cooldown_bars: int = 0,       # min bars between exit and next entry
    bars_per_year: int = 35040,   # 15m default; 105120 for 5m, 8760 for 1h
    leverage: float = 1.0,        # position leverage multiplier
    equity_ma_bars: int = 0,      # equity curve filter: skip entries when equity < MA(N bars). 0=disabled
    dd_throttle_pct: float = 0.0, # reduce to cash when current DD exceeds this. 0=disabled
    lev_scale_dd: float = 0.0,    # adaptive leverage: start scaling down at this DD%. 0=disabled
                                  # e.g. 0.10 = start reducing lev at -10% DD, reach 1x at 2*dd
    cond_ts_pct: float = 0.0,     # conditional trailing stop: only active when equity DD > cond_ts_dd_pct
    cond_ts_dd_pct: float = 0.0,  # equity DD threshold to activate conditional trailing stop
    max_dd_exit_pct: float = 0.0, # force close ALL positions when equity DD exceeds this. 0=disabled
                                  # e.g. 0.15 = force liquidation at -15% DD, guaranteeing DD cap
    mde_cooldown_bars: int = 0,   # extra cooldown after MDE exit (avoid re-entering during DD). 0=use normal cooldown
    price_lev_scale: float = 0.0, # price-based leverage scaling: start reducing at this price DD%. 0=disabled
                                  # e.g. 0.05 = full lev at -5% price DD, scale to 1x at -10% price DD
                                  # uses rolling high of close prices (lookback=200 bars)
    price_lev_lb: int = 200,      # lookback bars for price rolling high (default 200)
    sl_cooldown_bars: int = 0,    # extra cooldown after SL exit only. 0=use normal cooldown
                                  # key insight: SL-specific cooldown limits DD during crashes
                                  # while allowing normal signal exits to re-enter immediately
    vol_lev_atr: int = 0,         # volatility-based leverage: ATR lookback bars. 0=disabled
                                  # e.g. 48 = use 48-bar ATR to measure volatility
    vol_lev_threshold: float = 0.0,  # ATR/close ratio threshold. 0=disabled
                                  # e.g. 0.003 = at 0.3% ATR/close, start reducing leverage
                                  # full lev below threshold, linear scale to 1x at 2*threshold
                                  # set ONCE at entry (prospective), not adjusted mid-trade
    trend_lev_sma: int = 0,       # trend-based leverage: SMA lookback bars. 0=disabled
                                  # e.g. 200 = use SMA(200) to detect bull/bear regime
    trend_lev_bull: float = 0.0,  # leverage when price > SMA (bull regime). 0=use base leverage
    trend_lev_bear: float = 0.0,  # leverage when price < SMA (bear regime). 0=use base leverage
                                  # set ONCE at entry (prospective), not adjusted mid-trade
) -> dict:
    df = df.copy()
    signals = signals.reindex(df.index, fill_value=0)

    position = 0
    entry_price = 0.0
    entry_time = None
    equity = 1.0
    peak_price = 0.0  # for trailing stop
    peak_equity = 1.0  # for DD throttle
    last_exit_bar = -9999  # allow first trade immediately
    _last_mde_bar = -9999  # track last MDE exit for mde_cooldown
    _last_sl_bar = -9999   # track last SL exit for sl_cooldown
    trades = []
    equity_points = [1.0]

    # Pre-convert to numpy for fast loop access (~20x speedup)
    _close = df["close"].values
    _high = df["high"].values
    _low = df["low"].values
    _sig = signals.values.astype(int)
    _time = df["open_time"].values
    _lev = max(1.0, leverage)  # minimum 1x
    _eff_lev = _lev  # effective leverage (may be reduced by lev_scale_dd)
    _n = len(df)

    # Equity curve filter state
    _eq_ma_enabled = equity_ma_bars > 0
    _eq_ma_buf = np.ones(equity_ma_bars) if _eq_ma_enabled else None
    _eq_ma_idx = 0
    _eq_ma_sum = float(equity_ma_bars) if _eq_ma_enabled else 0.0
    _dd_throttle = dd_throttle_pct > 0
    _lev_scale = lev_scale_dd > 0  # adaptive leverage scaling (equity-based)
    _price_lev = price_lev_scale > 0  # price-based leverage scaling
    _price_lev_lb = max(1, price_lev_lb)
    _cond_ts = cond_ts_pct > 0 and cond_ts_dd_pct > 0  # conditional trailing stop
    _vol_lev = vol_lev_atr > 0 and vol_lev_threshold > 0  # volatility-based leverage
    _vol_atr = None
    if _vol_lev:
        # Pre-compute ATR series for fast lookup
        _tr = np.maximum(_high - _low,
                         np.maximum(np.abs(_high - np.roll(_close, 1)),
                                    np.abs(_low - np.roll(_close, 1))))
        _tr[0] = _high[0] - _low[0]
        _vol_atr = pd.Series(_tr).rolling(vol_lev_atr, min_periods=1).mean().values
    _max_dd_exit = max_dd_exit_pct > 0  # hard DD cap with forced liquidation
    _trend_lev = trend_lev_sma > 0 and (trend_lev_bull > 0 or trend_lev_bear > 0)
    _trend_sma = None
    if _trend_lev:
        _trend_sma = pd.Series(_close).rolling(trend_lev_sma, min_periods=1).mean().values

    for i in range(_n):
        price = _close[i]
        h_i = _high[i]
        l_i = _low[i]
        sig = int(_sig[i])
        t = _time[i]

        # Compute live equity DD for conditional trailing stop
        _eq_dd_active = False
        if _cond_ts and position != 0:
            if position == 1:
                _live_eq = equity * (1 + (_close[i-1] / entry_price - 1) * _eff_lev) if i > 0 else equity
            else:
                _live_eq = equity * (1 + (entry_price / _close[i-1] - 1) * _eff_lev) if i > 0 else equity
            _eq_dd_active = (_live_eq / peak_equity - 1) < -cond_ts_dd_pct

        # Check stop-loss / take-profit / trailing stop
        forced_exit = False
        if position == 1:
            peak_price = max(peak_price, h_i)
            if stop_loss_pct > 0 and l_i <= entry_price * (1 - stop_loss_pct):
                price = entry_price * (1 - stop_loss_pct)
                forced_exit = True
            elif take_profit_pct > 0 and h_i >= entry_price * (1 + take_profit_pct):
                price = entry_price * (1 + take_profit_pct)
                forced_exit = True
            elif trailing_stop_pct > 0 and l_i <= peak_price * (1 - trailing_stop_pct):
                price = peak_price * (1 - trailing_stop_pct)
                forced_exit = True
            elif _eq_dd_active and l_i <= peak_price * (1 - cond_ts_pct):
                price = peak_price * (1 - cond_ts_pct)
                forced_exit = True
        elif position == -1:
            peak_price = min(peak_price, l_i) if peak_price > 0 else l_i
            if stop_loss_pct > 0 and h_i >= entry_price * (1 + stop_loss_pct):
                price = entry_price * (1 + stop_loss_pct)
                forced_exit = True
            elif take_profit_pct > 0 and l_i <= entry_price * (1 - take_profit_pct):
                price = entry_price * (1 - take_profit_pct)
                forced_exit = True
            elif trailing_stop_pct > 0 and h_i >= peak_price * (1 + trailing_stop_pct):
                price = peak_price * (1 + trailing_stop_pct)
                forced_exit = True
            elif _eq_dd_active and h_i >= peak_price * (1 + cond_ts_pct):
                price = peak_price * (1 + cond_ts_pct)
                forced_exit = True

        # Hard DD cap: force liquidation when equity DD exceeds max_dd_exit_pct
        _mde_triggered = False
        if not forced_exit and _max_dd_exit and position != 0:
            if position == 1:
                _live = equity * (1 + (price / entry_price - 1) * _eff_lev)
            else:
                _live = equity * (1 + (entry_price / price - 1) * _eff_lev)
            if (_live / peak_equity - 1) < -max_dd_exit_pct:
                forced_exit = True
                _mde_triggered = True
                # price stays at close — liquidation at market

        should_close = forced_exit or (position != 0 and sig != position and sig != 2)

        if should_close and position != 0:
            if position == 1:
                exit_price = price * (1 - SLIPPAGE) if not forced_exit else price
                pnl_pct = (exit_price / entry_price - 1)
            else:
                exit_price = price * (1 + SLIPPAGE) if not forced_exit else price
                pnl_pct = (entry_price / exit_price - 1)

            lev_pnl = pnl_pct * _eff_lev
            equity *= (1 + lev_pnl) * (1 - FEE_RATE)
            _is_sl_exit = (not _mde_triggered and forced_exit
                           and (stop_loss_pct > 0 or trailing_stop_pct > 0) and (
                (position == 1 and exit_price < entry_price) or
                (position == -1 and exit_price > entry_price)
            ))
            trades.append({
                "entry_time": str(entry_time),
                "exit_time": str(t),
                "entry_price": round(entry_price, 6),
                "exit_price": round(exit_price, 6),
                "pnl_pct": round(lev_pnl * 100, 4),
                "side": "LONG" if position == 1 else "SHORT",
                "exit_reason": "MDE" if _mde_triggered else (
                    "SL" if _is_sl_exit else ("TP" if forced_exit else "SIGNAL")),
            })
            # Reset peak equity after MDE liquidation to prevent cascade
            if _mde_triggered:
                peak_equity = equity
                _last_mde_bar = i
            if _is_sl_exit:
                _last_sl_bar = i
            position = 0
            last_exit_bar = i

        # Open new position (skip if just hit SL/TP or cooldown not met)
        # SL-specific cooldown: long wait after SL, normal wait after signal/TP exits
        if sl_cooldown_bars > 0 and _last_sl_bar == last_exit_bar:
            _cd = sl_cooldown_bars
        elif mde_cooldown_bars > 0 and _last_mde_bar == last_exit_bar:
            _cd = mde_cooldown_bars
        else:
            _cd = cooldown_bars
        entry_allowed = (not forced_exit and position == 0 and sig in (1, -1)
                         and (i - last_exit_bar) >= _cd)

        # Equity curve filter: skip entries during drawdown streaks
        if entry_allowed and _eq_ma_enabled and i > equity_ma_bars:
            eq_ma = _eq_ma_sum / equity_ma_bars
            if equity < eq_ma:
                entry_allowed = False

        # DD throttle: skip entries when current DD exceeds threshold
        if entry_allowed and _dd_throttle:
            cur_dd = (equity / peak_equity - 1) if peak_equity > 0 else 0
            if cur_dd < -dd_throttle_pct:
                entry_allowed = False

        if entry_allowed:
            close_price = _close[i]
            if sig == 1:
                entry_price = close_price * (1 + SLIPPAGE)
                peak_price = h_i
            else:
                entry_price = close_price * (1 - SLIPPAGE)
                peak_price = l_i
            entry_time = t
            position = sig
            equity *= (1 - FEE_RATE)
            # Compute effective leverage for this trade
            if _trend_lev:
                # Trend-based leverage: bull/bear regime from SMA
                _is_bull = close_price > _trend_sma[i]
                _eff_lev = max(1.0, trend_lev_bull if _is_bull else trend_lev_bear)
            elif _price_lev and sig == 1:
                # Price-based leverage scaling for LONGS only
                # Shorts keep full leverage to profit from crashes
                _start = max(0, i - _price_lev_lb)
                _p_hi = _high[_start:i + 1].max()
                _p_dd = (close_price / _p_hi - 1) if _p_hi > 0 else 0
                if _p_dd < -price_lev_scale:
                    # Linear scale: at -pls → full lev, at -2*pls → 1x
                    scale = max(0.0, 1.0 - (abs(_p_dd) - price_lev_scale) / price_lev_scale)
                    _eff_lev = 1.0 + (_lev - 1.0) * scale
                else:
                    _eff_lev = _lev
            elif _price_lev and sig == -1:
                _eff_lev = _lev  # full leverage for shorts
            elif _lev_scale:
                cur_dd = (equity / peak_equity - 1) if peak_equity > 0 else 0
                if cur_dd < -lev_scale_dd:
                    # Linear scale: at -lev_scale_dd → full lev, at -2*lev_scale_dd → 1x
                    scale = max(0.0, 1.0 - (abs(cur_dd) - lev_scale_dd) / lev_scale_dd)
                    _eff_lev = 1.0 + (_lev - 1.0) * scale
                else:
                    _eff_lev = _lev
            else:
                _eff_lev = _lev
            # Volatility-based leverage: reduce when ATR/close is high (prospective)
            # Applied as additional scaling on top of other leverage adjustments
            if _vol_lev:
                _atr_ratio = _vol_atr[i] / close_price if close_price > 0 else 0
                if _atr_ratio > vol_lev_threshold:
                    _v_scale = max(0.0, 1.0 - (_atr_ratio - vol_lev_threshold) / vol_lev_threshold)
                    _eff_lev = 1.0 + (_eff_lev - 1.0) * _v_scale

        # Dynamic price-based leverage: adjust mid-trade when price DD changes
        # Only for LONG positions — shorts keep full leverage to profit from crashes
        if _price_lev and position == 1:
            close_price = _close[i]
            _start = max(0, i - _price_lev_lb)
            _p_hi = _high[_start:i + 1].max()
            _p_dd = (close_price / _p_hi - 1) if _p_hi > 0 else 0
            if _p_dd < -price_lev_scale:
                new_lev = 1.0 + (_lev - 1.0) * max(0.0, 1.0 - (abs(_p_dd) - price_lev_scale) / price_lev_scale)
            else:
                new_lev = _lev
            if abs(new_lev - _eff_lev) > 0.01:
                # Settle current segment at old leverage, start new segment at new leverage
                seg_pnl = (close_price / entry_price - 1) * _eff_lev
                equity *= (1 + seg_pnl)
                entry_price = close_price  # reset entry for new segment
                _eff_lev = new_lev

        # Track equity (with leverage)
        close_price = _close[i]
        if position == 1:
            raw_pnl = close_price / entry_price - 1
            cur_equity = equity * (1 + raw_pnl * _eff_lev)
        elif position == -1:
            raw_pnl = entry_price / close_price - 1
            cur_equity = equity * (1 + raw_pnl * _eff_lev)
        else:
            cur_equity = equity
        equity_points.append(cur_equity)

        # Update equity MA buffer
        if _eq_ma_enabled:
            _eq_ma_sum -= _eq_ma_buf[_eq_ma_idx]
            _eq_ma_buf[_eq_ma_idx] = cur_equity
            _eq_ma_sum += cur_equity
            _eq_ma_idx = (_eq_ma_idx + 1) % equity_ma_bars

        # Update peak equity for DD throttle
        if cur_equity > peak_equity:
            peak_equity = cur_equity

    # Close open position
    if position != 0:
        close_price = _close[-1]
        if position == 1:
            pnl_pct = (close_price * (1 - SLIPPAGE) / entry_price - 1)
        else:
            pnl_pct = (entry_price / (close_price * (1 + SLIPPAGE)) - 1)
        lev_pnl = pnl_pct * _eff_lev
        equity *= (1 + lev_pnl) * (1 - FEE_RATE)
        trades.append({
            "entry_time": str(entry_time),
            "exit_time": str(_time[-1]),
            "entry_price": round(entry_price, 6),
            "exit_price": round(close_price, 6),
            "pnl_pct": round(lev_pnl * 100, 4),
            "side": "LONG" if position == 1 else "SHORT",
            "exit_reason": "EOD",
        })

    eq_len = min(len(equity_points), len(df))
    equity_curve = pd.Series(equity_points[:eq_len], index=df.index[:eq_len])
    benchmark = df["close"] / df["close"].iloc[0]

    metrics = compute_metrics(trades, equity_curve, benchmark, bars_per_year=bars_per_year)
    grade = grade_strategy(metrics)

    return {
        "name": strategy_name,
        "params": params or {},
        "metrics": metrics,
        "grade": grade,
        "trades": trades,
        "equity_curve": equity_curve.tolist(),
        "benchmark_curve": benchmark.tolist(),
        "times": [str(t) for t in df["open_time"].tolist()],
    }
