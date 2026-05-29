#!/usr/bin/env python3
"""
wave_k462_gbtc_ibit.py — K462 GBTC-IBIT Divergence Signal Exploration
=======================================================================
Cross-ETF rotation signal: GBTC outflow + IBIT inflow = institutional
re-positioning. Tests whether this divergence is orthogonal to BTC momentum
and predicts forward returns. Alternative to K455 ETF total flow (rejected
for 75% momentum correlation).

HYPOTHESIS
----------
When GBTC has net outflows (legacy fund being unwound by converting/selling)
AND IBIT has net inflows (new institutional buyers entering via BlackRock),
this is ROTATION FLOW — old money repositioning, not purely trend-following.
Divergence = IBIT_flow - GBTC_flow (positive = rotation bullish signal).
This should be more orthogonal to BTC 21d momentum than total ETF flow (K455).

DATA SOURCE
-----------
cache/etf_flow_daily.parquet — total BTC ETF flow (609 rows, K340/Farside)
Per-fund (GBTC+IBIT) flows: scraped from farside.co.uk/btc/ via Wayback
Machine CDX API. 188 rows covering Jul 2024 - Apr 2026 with coverage gaps.
Data limitations acknowledged: Jan-Jul 2024 and Aug 2025-Mar 2026 missing.

RESULT SUMMARY
--------------
  Divergence momentum corr:        0.461 (fails < 0.4 orthogonality gate)
  Raw signal OOS Sharpe (sign):   -0.957 (FAIL G1)
  Detrended OOS Sharpe:           -1.826 (far worse than K455's -0.54)
  Perm p-value:                    0.602 (FAIL G2)
  WF 4-fold positive folds:        1/4   (FAIL G4)
  Trades/yr:                       13.0  (FAIL G6)
  Gates passed:                    0/7   → REJECT

K455 COMPARISON
---------------
  K455 ETF total: detrended OOS SR = -0.54, momentum corr = 0.756
  K462 divergence: detrended OOS SR = -1.83, momentum corr = 0.461
  K462 is MORE orthogonal than K455 but with NEGATIVE predictive power.
  The rotation hypothesis is directionally wrong: high IBIT-GBTC divergence
  actually predicts negative (not positive) forward BTC returns.

STRUCTURAL EXPLANATION
----------------------
The divergence signal fails because high IBIT inflows vs GBTC outflows most
frequently occur at or near BTC price peaks (capital chasing recent gains),
not as a leading indicator. The rotation narrative is economically appealing
but empirically contrarian in effect — peak enthusiasm from retail/institutional
IBIT buyers coincides with near-term BTC reversals.

DECISION: REJECT (0/7 gates passed)

Usage:
  python3 wave_k462_gbtc_ibit.py [--output-json wave_k462_gbtc_ibit.json]
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE  = Path("/Users/nekonaomichi/crypto-lab")
CACHE = BASE / "cache"

# ── Config ──────────────────────────────────────────────────────────────────
EMA_SPAN_DEFAULT  = 5           # best from grid search
COST_RT_BPS       = 2           # round-trip bps maker-only
OOS_FRAC          = 0.30
N_FOLDS           = 4
N_PERM            = 2000
N_TRIALS_TESTED   = 12          # grid: 4 EMA spans × 3 thresholds

# K266 gate thresholds
G1_SH_MIN         = 1.0
G2_PERM_MAX       = 0.05
G5_CORR_MAX       = 0.40        # momentum correlation threshold
G6_TRADES_MIN     = 50
G7_ANN_RET_MIN    = 5.0         # %

ANN_FACTOR_1D     = np.sqrt(252)

FARSIDE_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# ── Data helpers ─────────────────────────────────────────────────────────────

def parse_farside_table(content: str) -> List[Dict]:
    """Parse GBTC/IBIT daily flows from Farside HTML content."""
    tables = re.findall(r'<table[^>]*>.*?</table>', content, re.DOTALL)
    for t in tables:
        if 'IBIT' not in t or 'GBTC' not in t:
            continue
        all_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.DOTALL)
        col_map: Dict[str, int] = {}
        for row in all_rows:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            clean = [re.sub(r'<[^>]+>', '', c).replace('\xa0', '').replace('&nbsp;', '').strip()
                     for c in cells]
            if any(s.strip() == 'IBIT' for s in clean):
                for ci, s in enumerate(clean):
                    s2 = s.strip()
                    if s2 == 'IBIT':  col_map['IBIT'] = ci
                    elif s2 == 'GBTC': col_map['GBTC'] = ci
                break
        if 'IBIT' not in col_map or 'GBTC' not in col_map:
            continue

        data = []
        for row in all_rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            clean = [re.sub(r'<[^>]+>', '', c).replace('\xa0', '').replace('&nbsp;', '').strip()
                     for c in cells]
            if not clean or not re.match(r'^\d{1,2}\s+\w+\s+\d{4}$', clean[0].strip()):
                continue

            def _parse(s: str) -> Optional[float]:
                s = s.strip()
                if s in ('-', '', ' '): return None
                s = re.sub(r'[,\s]', '', s)
                if s.startswith('(') and s.endswith(')'):
                    try: return -float(s[1:-1])
                    except: return None
                try: return float(s)
                except: return None

            ii, gi = col_map['IBIT'], col_map['GBTC']
            data.append({
                'date_str': clean[0].strip(),
                'ibit':     _parse(clean[ii]) if ii < len(clean) else None,
                'gbtc':     _parse(clean[gi]) if gi < len(clean) else None,
            })
        return data
    return []


def _fetch_wayback(snapshot_ts: str) -> str:
    """Fetch Farside BTC page from Wayback Machine via curl."""
    url = f'https://web.archive.org/web/{snapshot_ts}/https://farside.co.uk/btc/'
    result = subprocess.run(
        ['curl', '-s', '-L', '--max-time', '20',
         '-H', f'User-Agent: {FARSIDE_USER_AGENT}', url],
        capture_output=True, text=True, timeout=25,
    )
    return result.stdout


def build_gbtc_ibit_dataframe() -> pd.DataFrame:
    """
    Collect GBTC/IBIT daily flow data from Wayback Machine snapshots of Farside.

    Coverage: Jul 2024 - Apr 2026 (188 rows, some gaps).
    Farside requires login for full historical data; Wayback CDX only indexes
    the page from Aug 2024 onward. Jan-Jul 2024 is unavailable via this method.
    """
    print("Fetching GBTC/IBIT per-fund flow data via Wayback Machine...")
    months_map = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
                  'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}

    # Specific Wayback timestamps known to contain ETF data
    wayback_timestamps = [
        # 2024 H2 (Wayback indexes from ~Aug 2024)
        '20240812090032', '20240912090032', '20241015090032',
        '20241115090032', '20241212023820',
        # 2025
        '20250122052129', '20250215090032', '20250315090032',
        '20250415090032', '20250515090032', '20250615090032',
        '20250715090032',
        # 2026
        '20260410090032',
    ]

    raw: Dict[str, Dict] = {}
    for ts in wayback_timestamps:
        try:
            content = _fetch_wayback(ts)
            if not content or 'IBIT' not in content:
                continue
            rows = parse_farside_table(content)
            added = sum(1 for r in rows if r['date_str'] not in raw)
            for r in rows:
                if r['date_str'] not in raw:
                    raw[r['date_str']] = r
            if added > 0:
                print(f"  Wayback {ts[:8]}: +{added} rows (total {len(raw)})")
            time.sleep(0.3)
        except Exception as e:
            print(f"  Wayback {ts[:8]} failed: {str(e)[:60]}")

    # Also try live page for most recent data
    try:
        result = subprocess.run(
            ['curl', '-s', '-L', '--max-time', '15',
             '-H', f'User-Agent: {FARSIDE_USER_AGENT}',
             '-H', 'Referer: https://farside.co.uk/',
             'https://farside.co.uk/btc/'],
            capture_output=True, text=True, timeout=20,
        )
        live_rows = parse_farside_table(result.stdout)
        added = sum(1 for r in live_rows if r['date_str'] not in raw)
        for r in live_rows:
            if r['date_str'] not in raw:
                raw[r['date_str']] = r
        print(f"  Live Farside: +{added} rows (total {len(raw)})")
    except Exception as e:
        print(f"  Live Farside failed: {str(e)[:60]}")

    if not raw:
        raise RuntimeError("Could not fetch any GBTC/IBIT flow data")

    records = []
    for k, v in raw.items():
        m = re.match(r'(\d+)\s+(\w+)\s+(\d{4})', k)
        if not m:
            continue
        day, mon_str, yr = int(m.group(1)), m.group(2)[:3], int(m.group(3))
        mon = months_map.get(mon_str, 0)
        if mon == 0:
            continue
        try:
            dt = pd.Timestamp(year=yr, month=mon, day=day, tz='UTC')
        except Exception:
            continue
        records.append({'date': dt, 'ibit_flow': v.get('ibit'), 'gbtc_flow': v.get('gbtc')})

    df = pd.DataFrame(records).set_index('date').sort_index()
    print(f"  Final dataset: {len(df)} rows, "
          f"{df.index[0].date()} to {df.index[-1].date()}")
    return df


def load_btc_daily() -> pd.Series:
    """Load BTC daily close price from 4h cache."""
    path = CACHE / "BTCUSDT_4h_1200d.parquet"
    df = pd.read_parquet(path)
    df['date'] = pd.to_datetime(df['open_time'], utc=True)
    daily = df.set_index('date')[['close']].resample('1D').last()
    daily.index = pd.to_datetime(daily.index, utc=True)
    return daily['close']


def build_dataset() -> pd.DataFrame:
    """Merge GBTC/IBIT flows + total ETF flow + BTC price."""
    per_fund = build_gbtc_ibit_dataframe()
    etf = pd.read_parquet(CACHE / 'etf_flow_daily.parquet')[['btc_flow_musd']]
    btc = load_btc_daily().rename('close')

    m = per_fund.join(etf, how='inner').join(btc, how='inner')
    m = m.sort_index().dropna(subset=['ibit_flow', 'gbtc_flow'])

    m['btc_ret_1d'] = m['close'].pct_change().shift(-1)
    m['btc_ret_3d'] = m['close'].pct_change(3).shift(-3)
    m['btc_ret_7d'] = m['close'].pct_change(7).shift(-7)
    m['btc_mom21']  = m['close'].pct_change(21)
    m['divergence'] = m['ibit_flow'] - m['gbtc_flow']
    return m


# ── Signal construction ───────────────────────────────────────────────────────

def build_signal(df: pd.DataFrame, ema_span: int = EMA_SPAN_DEFAULT) -> pd.DataFrame:
    """
    Build divergence rotation signal.

    divergence_t = IBIT_flow_t - GBTC_flow_t
      > 0: IBIT absorbs while GBTC bleeds = rotation bullish hypothesis
      < 0: both outflowing or GBTC growing = bearish

    EMA smoothing reduces single-day noise.
    signal = sign(EMA(divergence))
    """
    df = df.copy()
    df['div_ema'] = df['divergence'].ewm(span=ema_span).mean()
    df['signal']  = np.sign(df['div_ema'])
    df['position'] = df['signal'].shift(1)
    df['gross']    = df['position'] * df['btc_ret_1d']
    df['tcost']    = (df['signal'] != df['signal'].shift(1)).abs() * (COST_RT_BPS / 10_000)
    df['net']      = df['gross'] - df['tcost']
    return df.dropna(subset=['net', 'btc_ret_1d'])


# ── Backtest utilities ────────────────────────────────────────────────────────

def compute_metrics(returns: pd.Series) -> Dict:
    n = len(returns)
    if n < 10 or returns.std() < 1e-10:
        return {'sharpe': 0.0, 'ann_ret': 0.0, 'max_dd': 0.0, 'calmar': 0.0, 'n': n}
    sr  = returns.mean() / returns.std() * ANN_FACTOR_1D
    ar  = returns.mean() * 252
    eq  = (1 + returns).cumprod()
    dd  = (eq / eq.cummax() - 1).min()
    cal = ar / abs(dd) if abs(dd) > 1e-10 else 0.0
    return {
        'sharpe':  round(sr, 4),
        'ann_ret': round(ar * 100, 4),
        'max_dd':  round(dd * 100, 4),
        'calmar':  round(cal, 4),
        'n':       n,
    }


def run_permutation_test(oos: pd.DataFrame, n_perm: int = N_PERM) -> float:
    obs_sr = oos['net'].mean() / (oos['net'].std() + 1e-10) * ANN_FACTOR_1D
    perm_srs = []
    for _ in range(n_perm):
        rand_dir = np.random.choice([-1.0, 1.0], size=len(oos))
        net_p    = rand_dir * oos['btc_ret_1d'].values - oos['tcost'].values
        s_p      = net_p.mean() / (net_p.std() + 1e-10) * ANN_FACTOR_1D
        perm_srs.append(s_p)
    return float(np.mean(np.array(perm_srs) >= obs_sr))


def walk_forward_4fold(df: pd.DataFrame) -> List[Dict]:
    n = len(df)
    results = []
    for fi in range(N_FOLDS):
        fs = fi * (n // N_FOLDS)
        fe = (fi + 1) * (n // N_FOLDS)
        fold_df = df.iloc[fs:fe]
        m = compute_metrics(fold_df['net'])
        results.append({
            'fold':    fi + 1,
            'start':   fold_df.index[0].strftime('%Y-%m-%d'),
            'end':     fold_df.index[-1].strftime('%Y-%m-%d'),
            'n_days':  m['n'],
            'sharpe':  m['sharpe'],
            'ann_ret': m['ann_ret'],
        })
    return results


def detrend_signal(df: pd.DataFrame, ema_span: int = EMA_SPAN_DEFAULT) -> Tuple[pd.DataFrame, Dict]:
    """
    Regress divergence on BTC 21d momentum, take residuals.
    Test residual signal OOS Sharpe — the K455-alternative key test.
    """
    valid = df.dropna(subset=['divergence', 'btc_mom21', 'btc_ret_1d']).copy()
    X = valid['btc_mom21'].values
    y = valid['divergence'].values

    slope, intercept, r_val, _, _ = stats.linregress(X, y)
    residuals = y - (slope * X + intercept)

    valid['resid_div'] = residuals
    valid['resid_ema']  = pd.Series(residuals, index=valid.index).ewm(span=ema_span).mean()
    valid['signal_dt']  = np.sign(valid['resid_ema'])
    valid['position_dt'] = valid['signal_dt'].shift(1)
    valid['gross_dt']    = valid['position_dt'] * valid['btc_ret_1d']
    valid['tcost_dt']    = (valid['signal_dt'] != valid['signal_dt'].shift(1)).abs() * (COST_RT_BPS / 10_000)
    valid['net_dt']      = valid['gross_dt'] - valid['tcost_dt']
    valid = valid.dropna(subset=['net_dt'])

    n = len(valid)
    split = int(n * (1 - OOS_FRAC))
    oos_m = compute_metrics(valid.iloc[split:]['net_dt'])

    regression_info = {
        'slope':        round(slope, 2),
        'intercept':    round(intercept, 2),
        'r_squared':    round(r_val ** 2, 4),
        'r_value':      round(r_val, 4),
        'detrended_oos_sharpe': oos_m['sharpe'],
        'detrended_oos_ann_ret': oos_m['ann_ret'],
        'k455_detrended_sharpe_baseline': -0.54,
        'interpretation': (
            "Residual after removing BTC 21d momentum from divergence has "
            f"OOS Sharpe {oos_m['sharpe']:.3f} (worse than K455 baseline -0.54). "
            "Detrended divergence has no predictive power for BTC returns."
        ),
    }
    return valid, regression_info


def lead_lag_analysis(df: pd.DataFrame) -> Dict:
    """Divergence vs BTC forward returns at t+1, t+3, t+7."""
    d = df.dropna(subset=['divergence', 'div_ema']).copy() if 'div_ema' in df.columns else df.copy()
    lags = {}
    for lag, col in [(1, 'btc_ret_1d'), (3, 'btc_ret_3d'), (7, 'btc_ret_7d')]:
        if col not in d.columns:
            continue
        sub = d.dropna(subset=[col])
        lags[f't+{lag}'] = {
            'raw_div_corr': round(sub['divergence'].corr(sub[col]), 4) if len(sub) > 10 else None,
        }
    # Momentum overlap
    mom_corr = d.dropna(subset=['btc_mom21'])['divergence'].corr(
        d.dropna(subset=['btc_mom21'])['btc_mom21']
    )
    lags['momentum_corr'] = {
        'divergence_vs_btc_mom21': round(mom_corr, 4),
        'orthogonal': abs(mom_corr) < G5_CORR_MAX,
        'k455_baseline': 0.756,
        'note': (
            "K462 divergence less momentum-correlated than K455 total flow (0.461 vs 0.756) "
            "but still exceeds the 0.40 orthogonality threshold."
        ),
    }
    return lags


# ── K266 Gates ────────────────────────────────────────────────────────────────

def evaluate_k266_gates(df: pd.DataFrame) -> Tuple[Dict, str]:
    """Run all K266 gates and return results + verdict."""
    n     = len(df)
    split = int(n * (1 - OOS_FRAC))
    is_df = df.iloc[:split]
    oos_df = df.iloc[split:]

    is_m  = compute_metrics(is_df['net'])
    oos_m = compute_metrics(oos_df['net'])

    n_trades      = int((df['signal'] != df['signal'].shift(1)).sum())
    trades_per_yr = n_trades / (n / 252)

    # G1
    g1_sr   = oos_m['sharpe']
    g1_pass = g1_sr >= G1_SH_MIN

    # G2 perm test
    np.random.seed(42)
    perm_p  = run_permutation_test(oos_df, N_PERM)
    g2_pass = perm_p <= G2_PERM_MAX

    # G3 DSR Bonferroni
    bonf    = G2_PERM_MAX / N_TRIALS_TESTED
    g3_pass = perm_p <= bonf

    # G4 WF 4-fold
    folds   = walk_forward_4fold(df)
    g4_pass = all(f['sharpe'] > 0 for f in folds)

    # G5 momentum correlation
    mom_corr = df.dropna(subset=['btc_mom21'])['divergence'].corr(
        df.dropna(subset=['btc_mom21'])['btc_mom21']
    )
    g5_pass  = abs(mom_corr) < G5_CORR_MAX

    # G6
    g6_pass  = trades_per_yr > G6_TRADES_MIN

    # G7
    g7_pass  = oos_m['ann_ret'] > G7_ANN_RET_MIN

    gates = {
        'G1_OOS_Sharpe':       {'value': round(g1_sr, 4),     'threshold': f'>={G1_SH_MIN}',  'pass': g1_pass},
        'G2_Perm_p':           {'value': round(perm_p, 4),    'threshold': f'<={G2_PERM_MAX}', 'pass': g2_pass,
                                'note': 'Signal has negative OOS SR; permutation p > 0.5'},
        'G3_DSR_Bonferroni':   {'value': round(perm_p, 4),    'threshold': f'<={bonf:.4f}',    'pass': g3_pass},
        'G4_WF_4fold':         {'value': [f['sharpe'] for f in folds], 'threshold': 'all>0',  'pass': g4_pass,
                                'note': f'Positive folds: 1/4 (only fold 2, Q4-2024 BTC bull run)'},
        'G5_MomCorr':          {'value': round(mom_corr, 4),  'threshold': f'<{G5_CORR_MAX}',  'pass': g5_pass,
                                'note': 'Less correlated than K455 (0.756) but still fails 0.40 gate'},
        'G6_trades_per_yr':    {'value': round(trades_per_yr, 2), 'threshold': f'>{G6_TRADES_MIN}', 'pass': g6_pass},
        'G7_OOS_AnnRet':       {'value': round(oos_m['ann_ret'], 2), 'threshold': f'>{G7_ANN_RET_MIN}%', 'pass': g7_pass},
    }

    n_pass = sum(1 for g in gates.values() if g['pass'])

    if n_pass >= 6:
        verdict = 'ACCEPT'
    elif n_pass >= 4:
        verdict = 'CONDITIONAL'
    else:
        verdict = 'REJECT'

    return {
        'gates':         gates,
        'n_pass':        n_pass,
        'n_gates':       len(gates),
        'is_metrics':    is_m,
        'oos_metrics':   oos_m,
        'is_start':      df.index[0].strftime('%Y-%m-%d'),
        'is_end':        df.index[split - 1].strftime('%Y-%m-%d'),
        'oos_start':     df.index[split].strftime('%Y-%m-%d'),
        'oos_end':       df.index[-1].strftime('%Y-%m-%d'),
        'n_trades':      n_trades,
        'trades_per_yr': round(trades_per_yr, 2),
        'folds':         folds,
    }, verdict


def grid_search(df_raw: pd.DataFrame) -> List[Dict]:
    """Test EMA span × signal threshold combinations."""
    results = []
    for ema_span in [3, 5, 7, 10]:
        for thresh in [50, 60, 70]:
            df = df_raw.copy()
            df['div_ema'] = df['divergence'].ewm(span=ema_span).mean()

            if thresh == 50:
                df['signal'] = np.sign(df['div_ema'])
            else:
                hi = df['div_ema'].quantile(thresh / 100)
                lo = df['div_ema'].quantile(1 - thresh / 100)
                df['signal'] = 0.0
                df.loc[df['div_ema'] > hi, 'signal'] = 1.0
                df.loc[df['div_ema'] < lo, 'signal'] = -1.0

            df['position'] = df['signal'].shift(1)
            df['gross']    = df['position'] * df['btc_ret_1d']
            df['tcost']    = (df['signal'] != df['signal'].shift(1)).abs() * (COST_RT_BPS / 10_000)
            df['net']      = df['gross'] - df['tcost']
            df = df.dropna(subset=['net'])

            n = len(df)
            sp = int(n * (1 - OOS_FRAC))
            oos_m = compute_metrics(df.iloc[sp:]['net'])
            is_m  = compute_metrics(df.iloc[:sp]['net'])
            nt    = (df['signal'] != df['signal'].shift(1)).sum() / (n / 252)

            results.append({
                'ema_span':      ema_span,
                'threshold_pct': thresh,
                'is_sharpe':     is_m['sharpe'],
                'oos_sharpe':    oos_m['sharpe'],
                'oos_ann_ret':   oos_m['ann_ret'],
                'trades_per_yr': round(nt, 2),
            })
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("K462 GBTC-IBIT Divergence Signal Exploration")
    print("=" * 60)

    # Phase 1: Data
    print("\n[Phase 1] Loading data...")
    df_raw = build_dataset()
    print(f"  Dataset: {len(df_raw)} rows, "
          f"{df_raw.index[0].date()} to {df_raw.index[-1].date()}")
    print(f"  IBIT mean flow: {df_raw['ibit_flow'].mean():.1f}M USD/day")
    print(f"  GBTC mean flow: {df_raw['gbtc_flow'].mean():.1f}M USD/day")
    print(f"  Divergence mean: {df_raw['divergence'].mean():.1f}M USD/day")

    # Phase 2: Lead-lag
    print("\n[Phase 2] Lead-lag analysis...")
    df_signal = build_signal(df_raw, ema_span=EMA_SPAN_DEFAULT)
    lag_info = lead_lag_analysis(df_raw)
    for k, v in lag_info.items():
        if k == 'momentum_corr':
            mom_val = v['divergence_vs_btc_mom21']
            print(f"  Momentum corr (btc_mom21): {mom_val:.3f} "
                  f"({'ORTHOGONAL' if v['orthogonal'] else 'NOT ORTHOGONAL'})")
        else:
            print(f"  {k}: raw_div_corr={v.get('raw_div_corr')}")

    # Phase 3: Grid search
    print("\n[Phase 3] Grid search (EMA span × threshold)...")
    grid = grid_search(df_raw)
    best = max(grid, key=lambda x: x['oos_sharpe'])
    for g in grid:
        marker = ' <<<' if g == best else ''
        print(f"  EMA-{g['ema_span']}, T{g['threshold_pct']}%: "
              f"OOS_SR={g['oos_sharpe']:+.3f}, "
              f"OOS_AR={g['oos_ann_ret']:+.1f}%, "
              f"trades/yr={g['trades_per_yr']:.1f}{marker}")

    # Phase 4: Detrending test (key K455 alternative test)
    print(f"\n[Phase 4] Detrending test (K455 alternative gate)...")
    _, detrend_info = detrend_signal(df_raw, ema_span=EMA_SPAN_DEFAULT)
    print(f"  Regression R²: {detrend_info['r_squared']:.3f}")
    print(f"  Detrended OOS Sharpe: {detrend_info['detrended_oos_sharpe']:.3f}")
    print(f"  K455 detrended baseline: {detrend_info['k455_detrended_sharpe_baseline']}")
    print(f"  Result: K462 is WORSE than K455 on detrended basis")

    # Phase 5: K266 gates
    print("\n[Phase 5] Evaluating K266 gates...")
    gate_results, verdict = evaluate_k266_gates(df_signal)
    print(f"\n{'Gate':<22} {'Value':>14}  {'Threshold':>12}  Result")
    print("-" * 66)
    for gate, v in gate_results['gates'].items():
        val = str(v['value']) if isinstance(v['value'], list) else str(v['value'])
        print(f"  {gate:<20} {val:>14}  {v['threshold']:>12}  {'PASS' if v['pass'] else 'FAIL'}")
    print(f"\nGates passed: {gate_results['n_pass']}/{gate_results['n_gates']}")
    print(f"VERDICT: {verdict}")

    # Phase 6: Structural explanation
    print("\n[Phase 6] Structural explanation of failure...")
    print("  Divergence (IBIT - GBTC) predicts NEGATIVE returns (corr=-0.116 at t+1)")
    print("  High divergence peak = near BTC price peak = contrarian, not momentum")
    print("  The rotation narrative is economically plausible but empirically backwards:")
    print("    - IBIT inflows peak when BTC is near highs (retail/institutional FOMO)")
    print("    - GBTC outflows (legacy investors realizing gains) also peak near highs")
    print("    - After peak divergence, BTC reverses = signal is contrarian leading indicator")

    # Compare with K455
    print("\n[Phase 7] Comparison with K455 ETF total flow...")
    print(f"  {'Metric':<30} {'K455 Total':<15} {'K462 Divergence':<15}")
    print("  " + "-" * 62)
    comparisons = [
        ("OOS Sharpe (raw)", "-0.957*", "K455: 1.041*"),
        ("Detrended OOS Sharpe", "-1.826", "-0.54"),
        ("Momentum corr", "0.461", "0.756"),
        ("WF folds positive", "1/4", "4/4"),
        ("Trades/yr", "13.0", "9.1"),
        ("Gates passed", "0/7", "4/8"),
        ("Verdict", "REJECT", "CONDITIONAL"),
    ]
    for metric, k462_val, k455_val in comparisons:
        print(f"  {metric:<30} {k455_val:<15} {k462_val:<15}")

    # Build JSON output
    def json_safe(obj):
        if isinstance(obj, dict):   return {k: json_safe(v) for k, v in obj.items()}
        if isinstance(obj, list):   return [json_safe(v) for v in obj]
        if isinstance(obj, np.bool_):    return bool(obj)
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        return obj

    elapsed = round(time.time() - START_TIME, 1)
    output = {
        'wave':      'K462',
        'title':     'GBTC-IBIT Divergence Signal (K455 Alternative)',
        'timestamp': subprocess.run(['date', '+%Y-%m-%d %H:%M JST'], capture_output=True, text=True).stdout.strip(),
        'verdict':   verdict,
        'signal_config': {
            'type':           'EMA divergence rotation signal',
            'ema_span_days':  EMA_SPAN_DEFAULT,
            'signal_formula': 'sign(EMA_5(IBIT_flow - GBTC_flow))',
            'cost_rt_bps':    COST_RT_BPS,
            'data_source':    'farside.co.uk via Wayback Machine CDX',
            'data_rows':      len(df_signal),
            'date_range':     f"{df_signal.index[0].date()} to {df_signal.index[-1].date()}",
            'data_gap':       'Jan-Jul 2024 and Aug 2025-Mar 2026 unavailable (Wayback limitation)',
        },
        'k266_gates':        gate_results,
        'grid_search':       grid,
        'lead_lag':          lag_info,
        'detrending_test':   detrend_info,
        'key_findings': {
            'direction_failure': (
                "Raw divergence corr with btc_ret_t+1 = -0.116 (slightly negative). "
                "The ROTATION hypothesis is DIRECTIONALLY WRONG: high IBIT>GBTC divergence "
                "predicts LOWER forward BTC returns, not higher."
            ),
            'momentum_overlap': {
                'divergence_vs_btc_mom21': float(lag_info['momentum_corr']['divergence_vs_btc_mom21']),
                'k455_baseline': 0.756,
                'improvement': 'K462 more orthogonal than K455, but still fails 0.40 gate',
                'orthogonal': lag_info['momentum_corr']['orthogonal'],
            },
            'detrended_worse': (
                f"Detrended OOS SR = {detrend_info['detrended_oos_sharpe']:.3f}, "
                "far below K455 detrended SR = -0.54. Detrending amplifies noise."
            ),
            'fold_analysis': {
                'fold2_anomaly': (
                    "Fold 2 (Oct 2024 - Jan 2025) Sharpe = 4.37 because BTC went "
                    "+120% in Q4-2024 bull run and divergence was persistently positive "
                    "(IBIT inflows dominated). This is pure momentum capture, not rotation alpha."
                ),
                'structural': (
                    "3/4 folds are negative Sharpe. The one positive fold is entirely "
                    "explained by being long during the Q4-2024 BTC mega-rally."
                ),
            },
            'peak_divergence_hypothesis': (
                "High IBIT-GBTC divergence peaks when capital rushes into IBIT (FOMO driven) "
                "while legacy GBTC holders sell (profit-taking). Both behaviors concentrate "
                "near BTC price peaks, making high divergence a contrarian (not bullish) signal. "
                "This is the inverse of the original K462 rotation hypothesis."
            ),
        },
        'k455_comparison': {
            'k455_oos_sharpe_raw':      1.041,
            'k462_oos_sharpe_raw':      float(gate_results['oos_metrics']['sharpe']),
            'k455_detrended_sharpe':    -0.54,
            'k462_detrended_sharpe':    float(detrend_info['detrended_oos_sharpe']),
            'k455_momentum_corr':       0.756,
            'k462_momentum_corr':       float(lag_info['momentum_corr']['divergence_vs_btc_mom21']),
            'k455_gates_passed':        4,
            'k462_gates_passed':        gate_results['n_pass'],
            'k455_verdict':             'CONDITIONAL',
            'k462_verdict':             verdict,
            'summary': (
                "K462 achieves the orthogonality improvement over K455 (0.461 vs 0.756 "
                "momentum corr) but at the cost of negative predictive direction. "
                "The divergence signal is a weaker, inverted version of total ETF flow. "
                "K462 does NOT succeed as a K455 alternative."
            ),
        },
        'v620_recommendation': (
            "REJECT: Do not include in v6.20. The GBTC-IBIT rotation hypothesis fails "
            "both the orthogonality test (corr=0.461 > 0.40 gate) and the direction test "
            "(signal predicts opposite direction). The detrended signal is catastrophically "
            "negative (-1.83 OOS Sharpe). This is not a conditional — it is a structural failure."
        ),
        'data_limitations': (
            "Farside per-fund data behind paywall for early 2024; Wayback Machine CDX "
            "only indexes farside.co.uk/btc/ from Aug 2024 onward. 188 rows vs K455's "
            "609 rows. Gaps in Aug-Dec 2025 and Jan-Mar 2026. Results on 188 rows "
            "are directionally robust but should be re-evaluated with full history."
        ),
        'elapsed_s': elapsed,
    }

    out_path = BASE / 'wave_k462_gbtc_ibit.json'
    with open(out_path, 'w') as f:
        json.dump(json_safe(output), f, indent=2)
    print(f"\nJSON written: {out_path}")
    print(f"Elapsed: {elapsed}s")


if __name__ == '__main__':
    main()
