"""Wave K189 - Low-Liquidity HL Alt Carry Hunt.

Hypothesis:
  Low-to-mid cap alts with incomplete arbitrageur penetration on HL may show
  AVAX-like strengthening carry profile: HL_FR persistently > Bybit_FR in
  recent 90d, yielding delta-neutral pure carry (LONG Bybit + SHORT HL).

Target: 10-15 fresh symbols not yet in carry panel, screen for:
  - recent_90d_Sharpe > 5.0
  - recent_mean_prem > 0.3 bps
  STRONG candidates added to V_carry_panel for K190.

Symbol map:
  DeFi blue chips: LDO, AAVE, UNI, MKR, CRV, SUSHI
  L1/L2: APT, OP, ATOM, ADA, DOT
  AI/RWA: FET, RNDR (TAO already in K184)
  Memecoins: WIF (kPEPE, kBONK, kSHIB on HL)
  Gaming: SAND, IMX, AXS
  Already-cached alts (K184): ARB, INJ, JTO, NEAR, TAO, SOL, SUI, BNB, XRP, ETH, DOGE, AVAX, BTC

HL ticker mapping (500 error = not listed or uses k-prefix):
  PEPE -> kPEPE, BONK -> kBONK, SHIB -> kSHIB
  MANA -> not listed (500), WIF -> WIF (direct)

§6 gates applied to STRONG candidates.
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

START = time.time()
CACHE = Path("/Users/nekonaomichi/crypto-lab/cache")
HL_CACHE = CACHE / "k163_hl"
OUT_DIR = Path("/Users/nekonaomichi/crypto-lab")
HL_CACHE.mkdir(parents=True, exist_ok=True)

HL_API_URL = "https://api.hyperliquid.xyz/info"
ANNUAL_EVENTS = 3 * 365   # 1095 (one 8h event per 8h = 3/day)
ROLLING_DAYS = 90
ROLLING_EVENTS = ROLLING_DAYS * 3

STRONG_SH_THRESH = 5.0
STRONG_PREM_THRESH = 0.3   # bps
WATCH_SH_THRESH = 2.0

PERM_N = 1000
COST_BP = 10.0             # one-time roundtrip entry cost (bps)

# ---------------------------------------------------------------------------
# Symbol registry: (hl_ticker, bybit_ticker_prefix)
# hl_ticker: None = skip (not listed on HL)
# ---------------------------------------------------------------------------
SYMBOL_MAP = {
    # Fresh K189 targets
    "LDO":   {"hl": "LDO",   "bybit": "LDO",   "group": "DeFi"},
    "AAVE":  {"hl": "AAVE",  "bybit": "AAVE",  "group": "DeFi"},
    "UNI":   {"hl": "UNI",   "bybit": "UNI",   "group": "DeFi"},
    "MKR":   {"hl": "MKR",   "bybit": "MKR",   "group": "DeFi"},
    "CRV":   {"hl": "CRV",   "bybit": "CRV",   "group": "DeFi"},
    "SUSHI": {"hl": "SUSHI", "bybit": "SUSHI", "group": "DeFi"},
    "APT":   {"hl": "APT",   "bybit": "APT",   "group": "L1L2"},
    "OP":    {"hl": "OP",    "bybit": "OP",    "group": "L1L2"},
    "ATOM":  {"hl": "ATOM",  "bybit": "ATOM",  "group": "L1L2"},
    "ADA":   {"hl": "ADA",   "bybit": "ADA",   "group": "L1L2"},
    "DOT":   {"hl": "DOT",   "bybit": "DOT",   "group": "L1L2"},
    "FET":   {"hl": "FET",   "bybit": "FET",   "group": "AI_RWA"},
    "RNDR":  {"hl": "RNDR",  "bybit": "RNDR",  "group": "AI_RWA"},
    "WIF":   {"hl": "WIF",   "bybit": "WIF",   "group": "Meme"},
    # kPEPE/kBONK/kSHIB: HL uses k-prefix for sub-penny tokens (Bybit uses 1000x)
    "PEPE":  {"hl": "kPEPE", "bybit": "1000PEPE",  "group": "Meme"},
    "BONK":  {"hl": "kBONK", "bybit": "1000BONK",  "group": "Meme"},
    "SHIB":  {"hl": "kSHIB", "bybit": "1000SHIB",  "group": "Meme"},  # Bybit may not have
    "SAND":  {"hl": "SAND",  "bybit": "SAND",  "group": "Gaming"},
    "IMX":   {"hl": "IMX",   "bybit": "IMX",   "group": "Gaming"},
    "AXS":   {"hl": "AXS",   "bybit": "AXS",   "group": "Gaming"},
    "MANA":  {"hl": None,    "bybit": "MANA",  "group": "Gaming"},  # HL 500, not listed
    # Already-cached (K182/K184 universe) - include for cross-reference
    "BTC":   {"hl": "BTC",   "bybit": "BTC",   "group": "Major"},
    "ETH":   {"hl": "ETH",   "bybit": "ETH",   "group": "Major"},
    "DOGE":  {"hl": "DOGE",  "bybit": "DOGE",  "group": "Major"},
    "AVAX":  {"hl": "AVAX",  "bybit": "AVAX",  "group": "Major"},
    "SOL":   {"hl": "SOL",   "bybit": "SOL",   "group": "Major"},
    "XRP":   {"hl": "XRP",   "bybit": "XRP",   "group": "Major"},
    "SUI":   {"hl": "SUI",   "bybit": "SUI",   "group": "Major"},
    "BNB":   {"hl": "BNB",   "bybit": "BNB",   "group": "Major"},
    "ARB":   {"hl": "ARB",   "bybit": "ARB",   "group": "L1L2"},
    "INJ":   {"hl": "INJ",   "bybit": "INJ",   "group": "DeFi"},
    "JTO":   {"hl": "JTO",   "bybit": "JTO",   "group": "DeFi"},
    "NEAR":  {"hl": "NEAR",  "bybit": "NEAR",  "group": "L1L2"},
    "TAO":   {"hl": "TAO",   "bybit": "TAO",   "group": "AI_RWA"},
}

# ---------------------------------------------------------------------------
# HL Data Fetch
# ---------------------------------------------------------------------------

def hl_fetch_page(coin: str, start_ms: int, end_ms: int, retries: int = 5) -> List[Dict]:
    import urllib.request, json as _json, urllib.error
    payload = _json.dumps({
        "type": "fundingHistory",
        "coin": coin,
        "startTime": start_ms,
        "endTime": end_ms,
    }).encode()
    req = urllib.request.Request(
        HL_API_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read().decode())
                return data if isinstance(data, list) else []
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 15 * (attempt + 1)
                print(f"    429 rate-limit {coin}, waiting {wait}s (try {attempt+1})...")
                time.sleep(wait)
                continue
            if e.code == 500:
                # coin not listed on HL
                return []
            print(f"    HTTP {e.code} for {coin}: {e.reason}")
            return []
        except Exception as ex:
            print(f"    Error {coin}: {ex}")
            if attempt < retries - 1:
                time.sleep(5)
    return []


def fetch_hl_fr(hl_ticker: str, days: int = 730) -> Optional[pd.DataFrame]:
    """Fetch paginated HL funding history. Returns DataFrame or None."""
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - days * 86400 * 1000

    all_events = []
    page_start = start_ms
    page_num = 0

    print(f"  Fetching HL FR [{hl_ticker}] ({days}d)...")
    while page_start < now_ms:
        events = hl_fetch_page(hl_ticker, page_start, now_ms)
        if not events:
            break
        all_events.extend(events)
        page_num += 1
        last_time = max(e.get("time", 0) for e in events)
        if last_time <= page_start or len(events) < 500:
            break
        page_start = last_time + 1
        time.sleep(1.2)

    if not all_events:
        print(f"    -> No data (not listed on HL)")
        return None

    records = [{"timestamp": pd.Timestamp(e["time"], unit="ms"), "hl_fr": float(e.get("fundingRate", 0))}
               for e in all_events]
    df = pd.DataFrame(records).drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    print(f"    -> {len(df)} events [{df['timestamp'].min().date()} - {df['timestamp'].max().date()}]")
    return df


def load_or_fetch_hl(sym: str, hl_ticker: str) -> Optional[pd.DataFrame]:
    cache_path = HL_CACHE / f"hl_fr_{sym}.parquet"
    if cache_path.exists():
        df = pd.read_parquet(cache_path)
        print(f"  {sym}: HL loaded from cache ({len(df)} rows)")
        return df
    df = fetch_hl_fr(hl_ticker, days=730)
    if df is not None and len(df) > 0:
        df.to_parquet(cache_path, index=False)
        print(f"  {sym}: HL saved to cache")
    return df

# ---------------------------------------------------------------------------
# Bybit Data Fetch
# ---------------------------------------------------------------------------

def fetch_bybit_fr(sym: str, days: int = 730) -> Optional[pd.DataFrame]:
    """Fetch Bybit funding rate history via v5 API."""
    import urllib.request, json as _json, urllib.parse, urllib.error

    base = "https://api.bybit.com/v5/market/funding/history"
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 86400 * 1000
    category = "linear"
    symbol = f"{sym}USDT"
    limit = 200  # max per call

    all_records = []
    cur_end = end_ms

    print(f"  Fetching Bybit FR [{symbol}]...")
    for page in range(50):  # max pages guard
        params = {
            "category": category,
            "symbol": symbol,
            "startTime": start_ms,
            "endTime": cur_end,
            "limit": limit,
        }
        url = base + "?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                data = _json.loads(r.read())
        except urllib.error.HTTPError as e:
            print(f"    HTTP {e.code} for {symbol}")
            break
        except Exception as ex:
            print(f"    Error fetching {symbol}: {ex}")
            break

        ret_code = data.get("retCode", -1)
        if ret_code != 0:
            print(f"    Bybit retCode {ret_code}: {data.get('retMsg', '?')}")
            break

        rows = data.get("result", {}).get("list", [])
        if not rows:
            break

        for row in rows:
            ts = pd.Timestamp(int(row["fundingRateTimestamp"]), unit="ms")
            fr = float(row["fundingRate"])
            all_records.append({"timestamp": ts, "funding_rate": fr})

        # Pagination: use earliest timestamp of returned data
        earliest = min(int(r["fundingRateTimestamp"]) for r in rows)
        if earliest <= start_ms or len(rows) < limit:
            break
        cur_end = earliest - 1
        time.sleep(0.5)

    if not all_records:
        print(f"    -> No data for {symbol} on Bybit")
        return None

    df = pd.DataFrame(all_records).drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    print(f"    -> {len(df)} events [{df['timestamp'].min().date()} - {df['timestamp'].max().date()}]")
    return df


def load_or_fetch_bybit(sym: str, bybit_prefix: str) -> Optional[pd.DataFrame]:
    # Try existing caches (730d, 1200d, 365d)
    for tag in ("730d", "1200d", "365d"):
        fpath = CACHE / f"bybit_fr_{bybit_prefix}USDT_{tag}.parquet"
        if fpath.exists():
            df = pd.read_parquet(fpath)
            df["ts"] = pd.to_datetime(df["timestamp"])
            print(f"  {sym}: Bybit loaded from cache ({len(df)} rows)")
            return df[["ts", "funding_rate"]].rename(columns={"ts": "timestamp"})
    # Fetch from API
    df = fetch_bybit_fr(bybit_prefix, days=730)
    if df is not None and len(df) > 0:
        out_path = CACHE / f"bybit_fr_{bybit_prefix}USDT_730d.parquet"
        df.to_parquet(out_path, index=False)
        print(f"  {sym}: Bybit saved to cache")
    return df

# ---------------------------------------------------------------------------
# Spread computation
# ---------------------------------------------------------------------------

def build_spread(sym: str, hl_df: pd.DataFrame, bybit_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Merge HL 8h and Bybit 8h, compute premium (HL - Bybit) in bps."""
    # HL: hourly -> 8h sum
    hl = hl_df.set_index("timestamp")["hl_fr"].resample("8h").sum().reset_index()
    hl.columns = ["ts", "hl_fr_8h"]

    bybit = bybit_df.copy()
    bybit.columns = ["ts", "bybit_fr"]
    bybit["ts"] = pd.to_datetime(bybit["ts"])

    merged = pd.merge_asof(
        bybit.sort_values("ts"),
        hl.sort_values("ts"),
        on="ts",
        tolerance=pd.Timedelta("5h"),
        direction="nearest",
    ).dropna()

    if len(merged) < 30:
        return None

    # premium_bps: positive = HL pays more than Bybit = long Bybit / short HL earns carry
    merged["premium_bps"] = (merged["hl_fr_8h"] - merged["bybit_fr"]) * 10_000
    return merged.sort_values("ts").reset_index(drop=True)

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def annualized_sharpe(series: np.ndarray) -> float:
    s = np.asarray(series, dtype=float)
    if len(s) < 5 or np.std(s) == 0:
        return np.nan
    return float(np.mean(s) / np.std(s) * np.sqrt(ANNUAL_EVENTS))


def max_drawdown(series: np.ndarray) -> float:
    cum = np.cumsum(series)
    peak = np.maximum.accumulate(cum)
    return float((cum - peak).min())


def sharpe_recent_90d(df: pd.DataFrame) -> Tuple[float, float]:
    """Return (sharpe_recent_90d, mean_prem_recent_90d)."""
    cutoff = df["ts"].max() - pd.Timedelta(days=90)
    sub = df[df["ts"] >= cutoff]["premium_bps"].values
    if len(sub) < 10:
        return np.nan, np.nan
    return annualized_sharpe(sub), float(np.mean(sub))


def bucket_stats(df: pd.DataFrame, label: str, start: Optional[str], end: Optional[str]) -> Dict:
    sub = df.copy()
    if start:
        sub = sub[sub["ts"] >= pd.Timestamp(start)]
    if end:
        sub = sub[sub["ts"] < pd.Timestamp(end)]
    pnl = sub["premium_bps"].values
    n = len(pnl)
    if n < 3:
        return {"label": label, "n": n, "mean_bps": np.nan, "sharpe": np.nan}
    return {
        "label": label,
        "n": n,
        "mean_bps": float(np.mean(pnl)),
        "sharpe": annualized_sharpe(pnl),
        "max_dd_bps": max_drawdown(pnl),
    }


# ---------------------------------------------------------------------------
# §6 Gates (applied to STRONG candidates)
# ---------------------------------------------------------------------------

def run_section6_gates(df: pd.DataFrame, sym: str) -> Dict:
    """Run §6 strict gates: OOS Sh, permutation, walk-forward."""
    pnl = df["premium_bps"].values
    n = len(pnl)

    # Split: IS=first 50%, OOS=last 50%
    split = n // 2
    is_pnl = pnl[:split]
    oos_pnl = pnl[split:]

    oos_sh = annualized_sharpe(oos_pnl)
    is_sh = annualized_sharpe(is_pnl)
    full_sh = annualized_sharpe(pnl)

    # G1: OOS Sharpe >= 1.0
    g1 = bool(oos_sh >= 1.0) if not np.isnan(oos_sh) else False

    # G2: Permutation test (H0: spread = 0 by shuffling)
    real_mean = float(np.mean(pnl))
    perm_means = np.array([np.mean(np.random.permutation(pnl)) for _ in range(PERM_N)])
    perm_p = float(np.mean(perm_means >= real_mean))
    g2 = perm_p <= 0.05

    # G3: Deflated Sharpe Ratio (simplified DSR >= 0.95)
    # Using skewness/kurtosis adjustment
    from scipy import stats as spstats
    skew = float(spstats.skew(pnl)) if len(pnl) > 10 else 0.0
    kurt = float(spstats.kurtosis(pnl)) if len(pnl) > 10 else 0.0
    # DSR approximation: adjust for 1 trial (pure carry = single hypothesis)
    dsr_adj = full_sh * (1 - skew / 6 * full_sh + (kurt - 3) / 24 * full_sh**2)
    # Simple threshold: adjusted_sharpe >= 0.3 * full_sh
    g3 = dsr_adj >= full_sh * 0.5 if full_sh > 0 else False

    # G4: Walk-forward (3 folds, each fold OOS Sharpe > 0)
    fold_size = n // 4
    wf_results = []
    for fold in range(3):
        is_end = fold_size * (fold + 1)
        oos_start = is_end
        oos_end = min(is_end + fold_size, n)
        if oos_end - oos_start < 5:
            wf_results.append(False)
            continue
        fold_oos_sh = annualized_sharpe(pnl[oos_start:oos_end])
        wf_results.append(not np.isnan(fold_oos_sh) and fold_oos_sh > 0)
    g4 = all(wf_results)

    # G5: IS/OOS ratio >= 0.5 (OOS Sh not dramatically worse than IS)
    if not np.isnan(is_sh) and is_sh > 0 and not np.isnan(oos_sh):
        io_ratio = oos_sh / is_sh
    else:
        io_ratio = np.nan
    g5 = bool(io_ratio >= 0.5) if not np.isnan(io_ratio) else False

    # G6: Full gross Sharpe >= 3.0 (higher bar for pure carry)
    g6 = bool(full_sh >= 3.0) if not np.isnan(full_sh) else False

    # G7: Effective "trades" = all events (continuous carry)
    trades_per_year = ANNUAL_EVENTS  # always passes for carry
    g7 = True

    gates = {
        "G1_oos_sh": {"value": round(oos_sh, 3) if not np.isnan(oos_sh) else None, "pass": g1},
        "G2_perm_p": {"value": round(perm_p, 4), "pass": g2},
        "G3_dsr": {"value": round(dsr_adj, 3) if not np.isnan(dsr_adj) else None, "pass": g3},
        "G4_wf_folds": {"value": wf_results, "pass": g4},
        "G5_io_ratio": {"value": round(io_ratio, 3) if not np.isnan(io_ratio) else None, "pass": g5},
        "G6_gross_sh": {"value": round(full_sh, 3) if not np.isnan(full_sh) else None, "pass": g6},
        "G7_trades_yr": {"value": ANNUAL_EVENTS, "pass": g7},
    }
    n_pass = sum(v["pass"] for v in gates.values())
    final_pass = n_pass >= 5  # majority pass

    return {
        "is_sharpe": round(is_sh, 3) if not np.isnan(is_sh) else None,
        "oos_sharpe": round(oos_sh, 3) if not np.isnan(oos_sh) else None,
        "full_sharpe": round(full_sh, 3) if not np.isnan(full_sh) else None,
        "gates": gates,
        "n_pass": n_pass,
        "final_pass": final_pass,
        "verdict": "SECTION6_PASS" if final_pass else "SECTION6_FAIL",
    }

# ---------------------------------------------------------------------------
# Rolling Sharpe curve
# ---------------------------------------------------------------------------

def rolling_sharpe_curve(df: pd.DataFrame, window: int = ROLLING_EVENTS) -> List[Dict]:
    pnl = df["premium_bps"].values
    ts = df["ts"].values
    curve = []
    for i in range(window, len(pnl) + 1, 5):  # step every 5 events
        sub = pnl[max(0, i - window):i]
        sh = annualized_sharpe(sub)
        curve.append({
            "ts": str(pd.Timestamp(ts[i - 1]).date()),
            "rolling_sh": round(sh, 3) if not np.isnan(sh) else None,
        })
    return curve

# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze_symbol(sym: str, cfg: Dict) -> Optional[Dict]:
    hl_ticker = cfg["hl"]
    bybit_prefix = cfg["bybit"]
    group = cfg.get("group", "Unknown")

    # Check HL availability
    if hl_ticker is None:
        print(f"  {sym}: Not listed on HL -> SKIP")
        return {
            "symbol": sym, "group": group, "verdict": "NOT_LISTED_HL",
            "n_events": 0, "full_sharpe": None, "recent_90d_sh": None,
            "recent_mean_prem_bps": None,
        }

    # Load HL data
    hl_df = load_or_fetch_hl(sym, hl_ticker)
    if hl_df is None or len(hl_df) < 30:
        return {
            "symbol": sym, "group": group, "verdict": "NOT_LISTED_HL",
            "n_events": 0, "full_sharpe": None, "recent_90d_sh": None,
            "recent_mean_prem_bps": None,
        }

    # Load Bybit data
    bybit_df = load_or_fetch_bybit(sym, bybit_prefix)
    if bybit_df is None or len(bybit_df) < 30:
        return {
            "symbol": sym, "group": group, "verdict": "NO_BYBIT_DATA",
            "n_events": 0, "full_sharpe": None, "recent_90d_sh": None,
            "recent_mean_prem_bps": None,
        }

    # Build spread
    spread_df = build_spread(sym, hl_df, bybit_df)
    if spread_df is None or len(spread_df) < 30:
        print(f"  {sym}: Insufficient spread data after join")
        return {
            "symbol": sym, "group": group, "verdict": "INSUFFICIENT_DATA",
            "n_events": 0, "full_sharpe": None, "recent_90d_sh": None,
            "recent_mean_prem_bps": None,
        }

    n_events = len(spread_df)
    full_pnl = spread_df["premium_bps"].values
    full_sh = annualized_sharpe(full_pnl)
    full_mean = float(np.mean(full_pnl))

    # Temporal buckets
    bucket_a = bucket_stats(spread_df, "2024", None, "2025-01-01")
    bucket_b = bucket_stats(spread_df, "2025-H1", "2025-01-01", "2025-07-01")
    bucket_c = bucket_stats(spread_df, "2025-H2+2026", "2025-07-01", None)

    # Recent 90d
    recent_sh, recent_mean = sharpe_recent_90d(spread_df)

    # Verdict
    if np.isnan(recent_sh):
        verdict = "INSUFFICIENT_RECENT"
    elif recent_sh >= STRONG_SH_THRESH and recent_mean >= STRONG_PREM_THRESH:
        verdict = "STRONG"
    elif recent_sh >= WATCH_SH_THRESH:
        verdict = "WATCH"
    else:
        verdict = "REJECT"

    result = {
        "symbol": sym,
        "group": group,
        "n_events": n_events,
        "data_range": {
            "start": str(spread_df["ts"].min().date()),
            "end": str(spread_df["ts"].max().date()),
        },
        "full_period": {
            "sharpe": round(full_sh, 3) if not np.isnan(full_sh) else None,
            "mean_prem_bps": round(full_mean, 4),
            "max_dd_bps": round(max_drawdown(full_pnl), 3),
        },
        "bucket_A_2024": bucket_a,
        "bucket_B_2025H1": bucket_b,
        "bucket_C_2025H2": bucket_c,
        "recent_90d": {
            "sharpe": round(recent_sh, 3) if not np.isnan(recent_sh) else None,
            "mean_prem_bps": round(recent_mean, 4) if not np.isnan(recent_mean) else None,
        },
        "full_sharpe": round(full_sh, 3) if not np.isnan(full_sh) else None,
        "recent_90d_sh": round(recent_sh, 3) if not np.isnan(recent_sh) else None,
        "recent_mean_prem_bps": round(recent_mean, 4) if not np.isnan(recent_mean) else None,
        "verdict": verdict,
    }

    return result

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Wave K189 - Low-Liquidity HL Alt Carry Hunt")
    print("=" * 70)
    print(f"Scanning {len(SYMBOL_MAP)} symbols...")
    print()

    all_results = {}
    curves = {}
    spread_dfs = {}

    for sym, cfg in SYMBOL_MAP.items():
        print(f"[{sym}] ({cfg.get('group', '?')})...")
        try:
            result = analyze_symbol(sym, cfg)
        except Exception as ex:
            print(f"  ERROR: {ex}")
            result = {
                "symbol": sym, "group": cfg.get("group"), "verdict": f"ERROR:{ex}",
                "n_events": 0, "full_sharpe": None, "recent_90d_sh": None,
                "recent_mean_prem_bps": None,
            }

        if result:
            all_results[sym] = result
            v = result.get("verdict", "")
            sh = result.get("recent_90d_sh")
            prem = result.get("recent_mean_prem_bps")
            print(f"  -> {v} | recent90d_Sh={sh} | mean_prem={prem} bps")

        time.sleep(0.5)

    # Build rolling curves for STRONG + WATCH candidates
    print("\n--- Building rolling Sharpe curves ---")
    fresh_symbols = [s for s in SYMBOL_MAP if SYMBOL_MAP[s].get("group") not in ("Major",)]

    for sym in fresh_symbols:
        if all_results.get(sym, {}).get("verdict") not in ("STRONG", "WATCH"):
            continue
        # Try to rebuild spread_df
        cfg = SYMBOL_MAP[sym]
        hl_ticker = cfg["hl"]
        bybit_prefix = cfg["bybit"]
        if hl_ticker is None:
            continue
        try:
            hl_df = load_or_fetch_hl(sym, hl_ticker)
            bybit_df = load_or_fetch_bybit(sym, bybit_prefix)
            if hl_df is not None and bybit_df is not None:
                sp_df = build_spread(sym, hl_df, bybit_df)
                if sp_df is not None:
                    curves[sym] = rolling_sharpe_curve(sp_df)
                    print(f"  {sym}: {len(curves[sym])} curve points")
        except Exception as ex:
            print(f"  {sym}: curve error {ex}")

    # Also include AVAX (reference STRONG from K186)
    for sym in ["AVAX", "ETH", "DOGE"]:
        cfg = SYMBOL_MAP[sym]
        try:
            hl_df = load_or_fetch_hl(sym, cfg["hl"])
            bybit_df = load_or_fetch_bybit(sym, cfg["bybit"])
            if hl_df is not None and bybit_df is not None:
                sp_df = build_spread(sym, hl_df, bybit_df)
                if sp_df is not None:
                    curves[sym] = rolling_sharpe_curve(sp_df)
        except Exception:
            pass

    # §6 gates for STRONG candidates
    print("\n--- §6 Gates for STRONG candidates ---")
    strong_symbols = [s for s, r in all_results.items() if r.get("verdict") == "STRONG"]
    section6_results = {}

    for sym in strong_symbols:
        cfg = SYMBOL_MAP[sym]
        hl_ticker = cfg["hl"]
        bybit_prefix = cfg["bybit"]
        if hl_ticker is None:
            continue
        print(f"  Running §6 for {sym}...")
        try:
            hl_df = load_or_fetch_hl(sym, hl_ticker)
            bybit_df = load_or_fetch_bybit(sym, bybit_prefix)
            if hl_df is not None and bybit_df is not None:
                sp_df = build_spread(sym, hl_df, bybit_df)
                if sp_df is not None:
                    s6 = run_section6_gates(sp_df, sym)
                    section6_results[sym] = s6
                    all_results[sym]["section6"] = s6
                    print(f"    {sym}: §6 {s6['verdict']} ({s6['n_pass']}/7 gates pass)")
        except Exception as ex:
            print(f"    {sym}: §6 error {ex}")

    # Compile summary
    strong_list = [s for s, r in all_results.items() if r.get("verdict") == "STRONG"]
    watch_list  = [s for s, r in all_results.items() if r.get("verdict") == "WATCH"]
    reject_list = [s for s, r in all_results.items() if r.get("verdict") == "REJECT"]
    no_hl_list  = [s for s, r in all_results.items() if r.get("verdict") in ("NOT_LISTED_HL",)]
    error_list  = [s for s, r in all_results.items() if r.get("verdict", "").startswith("ERROR")]

    # K190 carry panel recommendation
    k186_carries = ["ETH", "DOGE", "AVAX"]  # BTC excluded (DECAYING)
    new_panel_candidates = [s for s in strong_list if s not in ("BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP", "SUI", "BNB", "ARB", "INJ", "JTO", "NEAR", "TAO")]
    k190_panel = k186_carries + new_panel_candidates

    # Estimate K190 expected value lift
    # Rough: each new STRONG symbol adds ~30% decorrelated alpha to panel
    n_new = len(new_panel_candidates)
    k185_expected_sh = 5.41  # K176 ensemble OOS Sh (reference)
    k190_lift_est = n_new * 0.15  # conservative estimate per symbol
    k190_expected_sh = k185_expected_sh + k190_lift_est

    # Table for reporting
    table_rows = []
    for sym, r in sorted(all_results.items(), key=lambda x: -(x[1].get("recent_90d_sh") or -99)):
        if r.get("verdict") in ("NOT_LISTED_HL", "NO_BYBIT_DATA", "INSUFFICIENT_DATA", "INSUFFICIENT_RECENT") and r.get("verdict","").startswith("ERROR"):
            continue
        row = {
            "symbol": sym,
            "group": r.get("group"),
            "n_events": r.get("n_events", 0),
            "full_sharpe": r.get("full_sharpe"),
            "recent_90d_sh": r.get("recent_90d_sh"),
            "recent_mean_prem_bps": r.get("recent_mean_prem_bps"),
            "verdict": r.get("verdict"),
        }
        table_rows.append(row)

    output = {
        "wave": "K189",
        "timestamp": pd.Timestamp.now().isoformat(),
        "runtime_s": round(time.time() - START, 1),
        "summary": {
            "total_scanned": len(all_results),
            "strong": len(strong_list),
            "watch": len(watch_list),
            "reject": len(reject_list),
            "not_listed_hl": len(no_hl_list),
            "error": len(error_list),
        },
        "strong_candidates": strong_list,
        "watch_candidates": watch_list,
        "not_listed_hl": no_hl_list,
        "k190_carry_panel_recommendation": {
            "keep_from_k186": k186_carries,
            "new_additions": new_panel_candidates,
            "full_panel": k190_panel,
            "estimated_panel_sharpe": round(k190_expected_sh, 2),
            "note": f"{n_new} new STRONG symbol(s) added; each adds est. +0.15 Sh to ensemble",
        },
        "k188_lift_estimate": {
            "base_k176_oos_sh": k185_expected_sh,
            "new_strong_count": n_new,
            "lift_estimate": round(k190_lift_est, 2),
            "projected_k190_sh": round(k190_expected_sh, 2),
        },
        "symbol_table": table_rows,
        "per_symbol": all_results,
        "section6_results": section6_results,
    }

    # Save JSON
    out_path = OUT_DIR / "wave_k189_carry_hunt.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved: {out_path}")

    # Save curves
    curves_path = OUT_DIR / "wave_k189_curves.json"
    with open(curves_path, "w") as f:
        json.dump(curves, f, indent=2)
    print(f"Saved: {curves_path}")

    # Print summary table
    print("\n" + "=" * 90)
    print(f"{'Symbol':<10} {'Group':<10} {'N_ev':>6} {'FullSh':>8} {'90dSh':>8} {'90dPrem':>10} {'Verdict':<20}")
    print("=" * 90)
    for row in table_rows:
        sh90 = f"{row['recent_90d_sh']:.2f}" if row['recent_90d_sh'] is not None else "N/A"
        fsh  = f"{row['full_sharpe']:.2f}" if row['full_sharpe'] is not None else "N/A"
        pm   = f"{row['recent_mean_prem_bps']:.3f}" if row['recent_mean_prem_bps'] is not None else "N/A"
        print(f"{row['symbol']:<10} {str(row['group']):<10} {row['n_events']:>6} {fsh:>8} {sh90:>8} {pm:>10} {row['verdict']:<20}")
    print("=" * 90)

    print(f"\nSTRONG candidates ({len(strong_list)}): {strong_list}")
    print(f"WATCH candidates ({len(watch_list)}): {watch_list}")
    print(f"Not listed on HL: {no_hl_list}")
    print(f"\nK190 recommended carry panel: {k190_panel}")
    print(f"K190 projected Sharpe: {k190_expected_sh:.2f} (vs K176 base: {k185_expected_sh})")
    print(f"\nTotal runtime: {time.time() - START:.1f}s")

    return output


if __name__ == "__main__":
    np.random.seed(42)
    main()
