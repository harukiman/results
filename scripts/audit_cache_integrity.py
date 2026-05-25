#!/usr/bin/env python3
"""Cache parquet integrity audit (K312).

Reads the v6.12-critical parquet files and reports:
  - rows / columns / size_mb
  - date range (oldest → newest), gap days from today
  - symbol coverage if applicable
  - null %, ±inf count, value sanity check (|fr| < 10% per period)

Output: data_integrity_audit.json + stderr summary.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

REPO_ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = REPO_ROOT / "cache"
JST = timezone(timedelta(hours=9))


@dataclass
class CacheSpec:
    path: str
    role: str
    expected_symbol_column: Optional[str] = None  # column name that holds the symbol
    expected_value_column: Optional[str] = None
    sanity_abs_max: Optional[float] = None  # |value| should be below this


REGISTRY: list[CacheSpec] = [
    CacheSpec(
        path="cache/hl_longtail_fr_daily.parquet",
        role="K265/K276 HL long-tail FR (cross-sectional source)",
        expected_symbol_column="symbol",
        expected_value_column="fr_daily",
        sanity_abs_max=1.0,
    ),
    CacheSpec(
        path="cache/hl_hip3_fr_daily.parquet",
        role="K297 PAXG/SPX RWA FR (satellite source)",
        expected_symbol_column="symbol",
        expected_value_column="fr_daily",
        sanity_abs_max=1.0,
    ),
    CacheSpec(
        path="cache/okx_fr_daily.parquet",
        role="K275 OKX cross-sectional FR",
        expected_symbol_column="symbol",
        expected_value_column="fr_daily",
        sanity_abs_max=1.0,
    ),
    CacheSpec(
        path="cache/alt_exchange_fr_daily.parquet",
        role="K208 CEX-DEX FR carry",
        expected_symbol_column="symbol",
        expected_value_column="fr_daily",
        sanity_abs_max=1.0,
    ),
    CacheSpec(
        path="cache/hlp_balance_daily.parquet",
        role="K200 HLP balance monitor (R7-001)",
        expected_value_column=None,
        sanity_abs_max=None,
    ),
    CacheSpec(
        path="cache/ethena_tvl_daily.parquet",
        role="Ethena USDe TVL (auxiliary)",
        expected_value_column=None,
        sanity_abs_max=None,
    ),
]


def audit_one(spec: CacheSpec) -> dict:
    full = REPO_ROOT / spec.path
    if not full.is_file():
        return {
            "path": spec.path,
            "role": spec.role,
            "status": "MISSING",
        }

    try:
        df = pd.read_parquet(full)
    except Exception as exc:
        return {
            "path": spec.path,
            "role": spec.role,
            "status": f"READ_ERROR: {type(exc).__name__}: {exc}",
        }

    size_mb = full.stat().st_size / (1024 * 1024)
    result: dict = {
        "path": spec.path,
        "role": spec.role,
        "status": "OK",
        "rows": int(len(df)),
        "columns": list(df.columns.astype(str)),
        "size_mb": round(size_mb, 3),
    }

    # date range — handle datetime index or column
    dt_idx = None
    if isinstance(df.index, pd.DatetimeIndex):
        dt_idx = df.index
    else:
        for cand in ("date", "datetime", "ts", "timestamp", "time"):
            if cand in df.columns:
                col = df[cand]
                if pd.api.types.is_datetime64_any_dtype(col):
                    dt_idx = pd.DatetimeIndex(col)
                    break
                try:
                    dt_idx = pd.to_datetime(col)
                    break
                except (TypeError, ValueError):
                    pass

    if dt_idx is not None and len(dt_idx) > 0:
        result["date_oldest"] = dt_idx.min().strftime("%Y-%m-%d")
        result["date_newest"] = dt_idx.max().strftime("%Y-%m-%d")
        today_naive = pd.Timestamp(datetime.now(JST).date())
        try:
            last = dt_idx.max()
            if last.tz is not None:
                last = last.tz_localize(None)
            gap = (today_naive - last.normalize()).days
        except Exception:
            gap = None
        result["staleness_days"] = gap
        if gap is not None and gap > 3:
            result["status"] = "STALE"

    # symbol coverage
    if spec.expected_symbol_column and spec.expected_symbol_column in df.columns:
        syms = df[spec.expected_symbol_column].astype(str).unique()
        result["unique_symbols"] = int(len(syms))
        result["sample_symbols"] = sorted(syms)[:8]

    # value sanity
    if spec.expected_value_column and spec.expected_value_column in df.columns:
        s = df[spec.expected_value_column]
        result["value_nulls"] = int(s.isna().sum())
        result["value_inf_count"] = int(np.isinf(s.fillna(0).to_numpy()).sum())
        nonnull = s.dropna()
        if len(nonnull):
            result["value_mean"] = float(nonnull.mean())
            result["value_std"] = float(nonnull.std())
            result["value_min"] = float(nonnull.min())
            result["value_max"] = float(nonnull.max())
            if spec.sanity_abs_max is not None:
                viol = int((nonnull.abs() > spec.sanity_abs_max).sum())
                result["sanity_violations"] = viol
                if viol > 0:
                    result["status"] = "SANITY_FAIL"

    return result


def main() -> int:
    results = [audit_one(spec) for spec in REGISTRY]
    payload = {
        "generated_at_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "audits": results,
        "summary": {
            "missing": sum(1 for r in results if r["status"] == "MISSING"),
            "stale": sum(1 for r in results if r["status"] == "STALE"),
            "sanity_fail": sum(1 for r in results if r["status"] == "SANITY_FAIL"),
            "read_error": sum(1 for r in results if r["status"].startswith("READ_ERROR")),
            "ok": sum(1 for r in results if r["status"] == "OK"),
        },
    }
    Path(REPO_ROOT / "data_integrity_audit.json").write_text(json.dumps(payload, indent=2, default=str))

    print(f"=== Cache integrity audit ({payload['generated_at_jst']}) ===", file=sys.stderr)
    for r in results:
        flag = "OK" if r["status"] == "OK" else "!!"
        line = f"{flag} {r['path']:45s} [{r['status']:12s}]"
        if r.get("rows") is not None:
            line += f" rows={r['rows']:>6d}"
        if r.get("staleness_days") is not None:
            line += f" stale={r['staleness_days']:>3d}d"
        if r.get("unique_symbols") is not None:
            line += f" syms={r['unique_symbols']}"
        if r.get("sanity_violations"):
            line += f" sanity_viol={r['sanity_violations']}"
        print(line, file=sys.stderr)
    print(f"--- summary: {payload['summary']} ---", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
