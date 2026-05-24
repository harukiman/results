"""Build chart sample dataset for the human-prediction labeler (Strategy Idea 2 MVP).

Generates random (symbol, start_idx, window_in, window_out) cutouts from cached 4H parquets.
Each sample has:
  - visible: list of bars (open_time, open, high, low, close, volume) — the LEFT side
  - hidden:  list of bars — the RIGHT side (answer)
  - meta: symbol, regime tags (vol Z bucket, trend sign)

Output: /Users/nekonaomichi/crypto-lab/data/chart_samples.json (compact, ~200KB)
"""
import json
import math
import random
from pathlib import Path
import pandas as pd
import numpy as np

CACHE = Path("/Users/nekonaomichi/crypto-lab/cache")
OUT = Path("/Users/nekonaomichi/crypto-lab/data/chart_samples.json")
N_SAMPLES = 200
WIN_IN = 60   # bars shown to user (60 * 4H = 10 days)
WIN_OUT = 12  # bars hidden as answer (12 * 4H = 2 days)
SEED = 42

SYMS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
    "AVAXUSDT", "LINKUSDT", "ADAUSDT", "XRPUSDT", "INJUSDT",
    "ARBUSDT", "OPUSDT", "ATOMUSDT", "APTUSDT", "DOTUSDT",
]


def regime_tags(df_full, idx_end):
    """Compute regime tags from the data up through idx_end (no look-ahead beyond hidden)."""
    win = 60
    if idx_end < win + 360:
        return {"vol_z_bucket": "n/a", "trend": "n/a"}
    sub = df_full.iloc[:idx_end + 1]
    ret = sub['close'].pct_change()
    rv = ret.rolling(win).std().iloc[-1] * math.sqrt(2190) * 100
    rvm = ret.rolling(win).std().rolling(360).mean().iloc[-1] * math.sqrt(2190) * 100
    rvs = ret.rolling(win).std().rolling(360).std().iloc[-1] * math.sqrt(2190) * 100
    if rvs and not np.isnan(rvs) and rvs > 0:
        z = (rv - rvm) / rvs
        if z < -0.5: vol_z_bucket = "low"
        elif z < 0.5: vol_z_bucket = "mid"
        elif z < 1.5: vol_z_bucket = "elevated"
        else: vol_z_bucket = "extreme"
    else:
        vol_z_bucket = "n/a"
    ema200 = sub['close'].ewm(span=200, adjust=False).mean().iloc[-1]
    px = sub['close'].iloc[-1]
    trend = "up" if px > ema200 else "down"
    return {"vol_z_bucket": vol_z_bucket, "trend": trend}


def main():
    random.seed(SEED)
    samples = []
    for sym in SYMS:
        path = CACHE / f"{sym}_4h_730d.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        # standardize column names
        if 'open_time' not in df.columns and 'timestamp' in df.columns:
            df = df.rename(columns={'timestamp': 'open_time'})
        df = df.sort_values('open_time').reset_index(drop=True)
        if len(df) < WIN_IN + WIN_OUT + 400:
            continue
        per_sym = max(1, N_SAMPLES // len(SYMS))
        for _ in range(per_sym + 4):
            start = random.randint(400, len(df) - WIN_IN - WIN_OUT - 1)
            visible = df.iloc[start:start + WIN_IN]
            hidden = df.iloc[start + WIN_IN:start + WIN_IN + WIN_OUT]
            tags = regime_tags(df, start + WIN_IN - 1)
            sample = {
                "id": f"{sym}_{start}",
                "symbol": sym,
                "tf": "4h",
                "regime": tags,
                "visible": [
                    {
                        "t": pd.Timestamp(r['open_time']).strftime("%Y-%m-%d %H:%M"),
                        "o": float(r['open']), "h": float(r['high']),
                        "l": float(r['low']), "c": float(r['close']),
                        "v": float(r['volume']) if 'volume' in r else 0.0,
                    } for _, r in visible.iterrows()
                ],
                "hidden": [
                    {
                        "t": pd.Timestamp(r['open_time']).strftime("%Y-%m-%d %H:%M"),
                        "o": float(r['open']), "h": float(r['high']),
                        "l": float(r['low']), "c": float(r['close']),
                        "v": float(r['volume']) if 'volume' in r else 0.0,
                    } for _, r in hidden.iterrows()
                ],
            }
            # ground truth aggregate
            last_close = sample["visible"][-1]["c"]
            future_high = max(b["h"] for b in sample["hidden"])
            future_low = min(b["l"] for b in sample["hidden"])
            future_end = sample["hidden"][-1]["c"]
            sample["answer"] = {
                "ret_end_pct": (future_end / last_close - 1) * 100,
                "max_up_pct": (future_high / last_close - 1) * 100,
                "max_dn_pct": (future_low / last_close - 1) * 100,
                "direction": "up" if future_end > last_close * 1.005 else "down" if future_end < last_close * 0.995 else "flat",
            }
            samples.append(sample)
            if len(samples) >= N_SAMPLES:
                break
        if len(samples) >= N_SAMPLES:
            break
    random.shuffle(samples)
    OUT.write_text(json.dumps({"samples": samples, "generated_at": pd.Timestamp.now().isoformat()}, separators=(',', ':')))
    print(f"wrote {len(samples)} samples to {OUT}, size={OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
