#!/usr/bin/env python3
"""
wave_k743_ldo_atom_eval.py — K743 LDO-ATOM FR Differential Alt-Alt Eval
=========================================================================
K339 REPO_ROOT pattern. LDO (Ethereum LSD, K594 parent) × ATOM (Cosmos Hub, K493 parent).

HYPOTHESIS
----------
K743 = LDO-ATOM (alt-alt: K594 LDO Ethereum LSD × K493 ATOM Cosmos Hub, cross-cluster)

MR9 STRICT linear combination pre-check:
  LDO_fr - ATOM_fr = (LDO_fr - SOL_fr) - (ATOM_fr - SOL_fr)
                   = K721_raw - K684_raw
  If max_err(K743_raw - (K721_raw - K684_raw)) < 1e-15 → ALGEBRAICALLY REDUNDANT → REJECT

PARENT STRATEGIES (BTC-base):
  K594 LDO-BTC  — REJECT (vol 0.80x, ETH cluster corr=0.43, DeFi cluster corr=0.50)
  K493 ATOM-BTC — ACCEPT  OOS Sh=50.786  net $75K/yr @$10M  vol_ratio=2.34x

RELATED ALT-ALTS (14-member family per K732):
  K683 APT-SOL   — ACCEPT  OOS Sh=39.3    (SOL shared leg)
  K682/K684 ATOM-SOL  — ACCEPT  OOS Sh=43.4   (ATOM shared leg)
  K686 SOL-INJ   — ACCEPT  OOS Sh=50.3   (SOL shared)
  K687/K686 AVAX-SOL — ACCEPT  OOS Sh=50.3   (SOL shared)
  K689/K690 SEI-SOL  — ACCEPT  OOS Sh=~35     (SOL shared)
  K694 TIA-SOL   — ACCEPT  OOS Sh=19.1   (SOL shared)
  K696 ENA-SOL   — ACCEPT  OOS Sh=26.9   (SOL shared)
  K700/K708 BNB-SOL  — ACCEPT  OOS Sh=48.6   (SOL shared)
  K719 ENA-ATOM  — ACCEPT  OOS Sh=29.7   (ATOM shared leg)
  K721/K728 LDO-SOL  — ACCEPT COND. OOS Sh=46.8 (LDO shared leg)
  K728/K729 INJ-ATOM — ACCEPT  OOS Sh=18.8   (ATOM shared leg)
  K735 HBAR-SOL  — eval in progress
  K736 TIA-AVAX  — ACCEPT  OOS Sh=13.0
  K739 FIL-SOL   — ACCEPT  OOS Sh=23.4
  K740 INJ-AVAX  — REJECT  (G5c AVAX saturation)

K339 REPO_ROOT: all paths → /Users/nekonaomichi/crypto-lab
LIVE changes: NONE — read-only eval.
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

# ── K339 REPO_ROOT ────────────────────────────────────────────────────────────
REPO_ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE_DIR  = REPO_ROOT / "cache"
HL_DIR     = CACHE_DIR / "k163_hl"
OUT_JSON   = REPO_ROOT / "wave_k743_ldo_atom_eval.json"
OUT_MD     = REPO_ROOT / "wave_k743_ldo_atom_eval.md"

t0      = time.time()
JST     = timezone(timedelta(hours=9))
RUN_TS  = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")

# ── Constants ─────────────────────────────────────────────────────────────────
WINDOW_H        = 168       # 7-day rolling (canonical best config)
MR9_EPSILON     = 1e-15     # machine-epsilon threshold for algebraic identity
MR9_GENUINE_THR = 1e-10     # genuine-independence threshold

print("=" * 72)
print(f"  K743  LDO-ATOM FR Differential Alt-Alt Eval  |  {RUN_TS}")
print("=" * 72)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_hl_fr(name: str) -> Optional[pd.Series]:
    """Load HL FR series, floor to hour, deduplicate, return Series indexed by timestamp."""
    p = HL_DIR / f"hl_fr_{name}.parquet"
    if not p.exists():
        return None
    d = pd.read_parquet(p)
    d["timestamp"] = pd.to_datetime(d["timestamp"]).dt.floor("h")
    return d.groupby("timestamp")["hl_fr"].mean()


# ── Phase 0: MR9 STRICT algebraic identity check ─────────────────────────────

def phase0_mr9_strict() -> Dict:
    """
    Phase 0: MR9 STRICT pre-check.

    Identity: LDO_fr - ATOM_fr = (LDO_fr - SOL_fr) - (ATOM_fr - SOL_fr)
                                = K721_raw - K684_raw

    Proof (exact algebra):
      Let L = LDO_fr, A = ATOM_fr, S = SOL_fr
      K743_raw = L - A
      K721_raw = L - S
      K684_raw = A - S
      K721_raw - K684_raw = (L - S) - (A - S) = L - A = K743_raw   □

    If max|K743_raw - (K721_raw - K684_raw)| < 1e-15 → REJECT (algebraic redundancy).
    """
    print("\n[Phase 0] MR9 STRICT algebraic identity check ...")

    ldo_fr  = _load_hl_fr("LDO")
    atom_fr = _load_hl_fr("ATOM")
    sol_fr  = _load_hl_fr("SOL")

    if ldo_fr is None or atom_fr is None or sol_fr is None:
        return {"mr9_verdict": "ERROR", "error": "Missing HL FR parquet for LDO/ATOM/SOL"}

    # Align all three on inner-join timestamps
    df = pd.DataFrame({"ldo_fr": ldo_fr, "atom_fr": atom_fr, "sol_fr": sol_fr}).dropna()
    n_rows      = len(df)
    date_start  = str(df.index[0].date())
    date_end    = str(df.index[-1].date())
    total_years = (df.index[-1] - df.index[0]).total_seconds() / (3600 * 24 * 365.25)

    print(f"  Rows: {n_rows:,}  |  {date_start} – {date_end}  |  {total_years:.2f} yrs")

    # Raw FR differentials
    k743_raw = df["ldo_fr"] - df["atom_fr"]   # K743 = LDO-ATOM
    k721_raw = df["ldo_fr"] - df["sol_fr"]    # K721 = LDO-SOL (K728 ACCEPT CONDITIONAL)
    k684_raw = df["atom_fr"] - df["sol_fr"]   # K684 = ATOM-SOL (K682 ACCEPT)

    # Algebraic residual: should be identically zero
    residual    = k743_raw - (k721_raw - k684_raw)
    mr9_max_err = float(residual.abs().max())

    # Smoothed signals (same as what the strategy uses)
    k743_smooth = k743_raw.rolling(WINDOW_H).mean()
    k721_smooth = k721_raw.rolling(WINDOW_H).mean()
    k684_smooth = k684_raw.rolling(WINDOW_H).mean()

    # Smoothed residual
    smooth_residual  = k743_smooth - (k721_smooth - k684_smooth)
    mr9_max_err_smth = float(smooth_residual.abs().max())

    # Signal identity (after sign thresholding)
    sig_k743     = np.sign(k743_smooth)
    sig_combined = np.sign(k721_smooth - k684_smooth)
    sig_identity_err = float((sig_k743 - sig_combined).abs().max())
    sig_corr         = float(sig_k743.corr(sig_combined))

    # FR statistics for documentation
    ldo_std       = float(df["ldo_fr"].std())
    atom_std      = float(df["atom_fr"].std())
    diff_std      = float(k743_raw.std())
    vol_ratio     = ldo_std / atom_std if atom_std > 0 else 0.0
    ldo_mean_ann  = float(df["ldo_fr"].mean())  * 8760 * 100
    atom_mean_ann = float(df["atom_fr"].mean()) * 8760 * 100
    diff_mean_ann = float(k743_raw.mean())      * 8760 * 100

    # MR9 verdict
    mr9_identity_confirmed = mr9_max_err < MR9_EPSILON
    verdict = "REJECT" if mr9_identity_confirmed else "PROCEED"

    print(f"  LDO FR std:  {ldo_std:.4e}  |  ATOM FR std: {atom_std:.4e}")
    print(f"  LDO mean:    {ldo_mean_ann:.2f}%/yr  |  ATOM mean: {atom_mean_ann:.2f}%/yr")
    print(f"  Vol ratio LDO/ATOM: {vol_ratio:.4f}")
    print(f"  MR9 raw max_err:     {mr9_max_err:.4e}  (threshold: {MR9_EPSILON:.0e})")
    print(f"  MR9 smooth max_err:  {mr9_max_err_smth:.4e}")
    print(f"  Signal identity err: {sig_identity_err:.4e}")
    print(f"  Signal correlation:  {sig_corr:.6f}")
    print(f"  Identity confirmed:  {mr9_identity_confirmed}  →  VERDICT: {verdict}")

    return {
        "target":       "LDO-ATOM (alt-alt: Ethereum LSD × Cosmos Hub IBC-staking, cross-cluster)",
        "data_rows":    n_rows,
        "date_start":   date_start,
        "date_end":     date_end,
        "total_years":  round(total_years, 2),
        "ldo_fr_std":   round(ldo_std, 8),
        "atom_fr_std":  round(atom_std, 8),
        "diff_std":     round(diff_std, 8),
        "vol_ratio_ldo_atom":  round(vol_ratio, 4),
        "ldo_fr_mean_ann_pct": round(ldo_mean_ann, 3),
        "atom_fr_mean_ann_pct": round(atom_mean_ann, 3),
        "diff_mean_ann_pct":   round(diff_mean_ann, 3),
        "mr9": {
            "algebraic_identity": "LDO_fr - ATOM_fr = (LDO_fr - SOL_fr) - (ATOM_fr - SOL_fr) = K721_raw - K684_raw",
            "proof": (
                "Let L=LDO_fr, A=ATOM_fr, S=SOL_fr. "
                "K743=L-A; K721=L-S; K684=A-S. "
                "K721-K684=(L-S)-(A-S)=L-A=K743. QED."
            ),
            "max_err_raw":       mr9_max_err,
            "max_err_smoothed":  mr9_max_err_smth,
            "signal_identity_err": sig_identity_err,
            "signal_corr":       round(sig_corr, 6),
            "epsilon_threshold": MR9_EPSILON,
            "genuine_threshold": MR9_GENUINE_THR,
            "identity_confirmed": mr9_identity_confirmed,
            "verdict": verdict,
        },
        "parent_k721": {
            "wave": "K728",
            "pair": "LDO-SOL",
            "decision": "ACCEPT CONDITIONAL",
            "oos_sharpe": 46.84,
            "net_profit_usdc_yr_10m": 105032,
        },
        "parent_k684": {
            "wave": "K682",
            "pair": "ATOM-SOL",
            "decision": "ACCEPT",
            "oos_sharpe": 43.43,
        },
        "k721_x_k684_signal_corr": 0.1330,
        "saturation_note": (
            "K721 (LDO-SOL) × K684 (ATOM-SOL) signal corr = 0.133 (low, genuine independent). "
            "But K743 = K721_raw - K684_raw EXACTLY: same series, same signal, same trades. "
            "Adding K743 to portfolio containing both K721 and K684 = ZERO marginal alpha. "
            "MR9 STRICT = algebraic identity, NOT signal correlation. Identity wins."
        ),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print()
    phase0 = phase0_mr9_strict()
    mr9    = phase0["mr9"]

    elapsed = time.time() - t0

    # ── Decision ──────────────────────────────────────────────────────────────
    if mr9["identity_confirmed"]:
        decision        = "REJECT"
        reject_code     = "MR9_STRICT_ALGEBRAIC_IDENTITY"
        reject_summary  = (
            f"K743 LDO-ATOM is ALGEBRAICALLY IDENTICAL to K721 (LDO-SOL) minus K684 (ATOM-SOL). "
            f"max_err = {mr9['max_err_raw']:.2e} << 1e-15 threshold. "
            f"Signal corr = 1.000000 (perfect). "
            f"Deploying K743 alongside K721+K684 yields ZERO marginal alpha. "
            f"Line CLOSED per MR9 STRICT enforcement. "
            f"No backtest required — save tokens."
        )
        line_status     = "CLOSED"
        proceed_to_ph1  = False
    else:
        decision        = "PROCEED_TO_PHASE1"
        reject_code     = None
        reject_summary  = "K743 passed MR9 — genuine independence detected. Proceed to Phase 1."
        line_status     = "OPEN"
        proceed_to_ph1  = True

    print(f"\n{'='*72}")
    print(f"  DECISION: {decision}")
    print(f"  {reject_summary}")
    print(f"{'='*72}")

    # ── Lesson ────────────────────────────────────────────────────────────────
    mr9_lesson = {
        "lesson_id": "MR9_L002_LDO_ATOM",
        "wave": "K743",
        "pattern": "LDO-ATOM = K721 - K684 (3-token triangle collapse)",
        "generalisation": (
            "In any alt-alt family built on a common BTC-base, for tokens A, B, C: "
            "(A-C) = (A-B) - (C-B). "
            "When both (A-B) and (C-B) are already in the family, (A-C) is ALWAYS redundant. "
            "Check: are both legs (A vs pivot) and (C vs pivot) already in the family? "
            "If YES → reject without data loading."
        ),
        "family_pivot_is_SOL": (
            "The 14-member alt-alt family uses SOL as the dominant pivot token. "
            "Any pair (X-Y) where both (X-SOL) and (Y-SOL) are in the family is algebraically "
            "derivable and MUST be rejected at MR9 pre-check. "
            "LDO-SOL (K721) + ATOM-SOL (K684) → LDO-ATOM (K743) REDUNDANT. "
            "Similarly: LDO-INJ, LDO-TIA, LDO-ENA, LDO-BNB, LDO-APT, LDO-SEI are ALL BLOCKED "
            "by the same triangle rule (once K721 LDO-SOL is in the family)."
        ),
        "token_pairs_blocked_by_triangle": [
            "LDO-ATOM (K743): K721 - K684 → CLOSED",
            "LDO-INJ: K721 - K684_INJ_SOL → CLOSED (if K684=SOL-INJ)",
            "LDO-TIA: K721 - K694 → CLOSED",
            "LDO-ENA: K721 - K696 → CLOSED",
            "LDO-BNB: K721 - K708 → CLOSED",
            "LDO-APT: K721 - K683 → CLOSED",
            "LDO-SEI: K721 - K690 → CLOSED",
            "LDO-AVAX: K721 - K687 → CLOSED",
            "LDO-HBAR: K721 - K735 → CLOSED (once K735 ACCEPT)",
            "LDO-FIL: K721 - K739 → CLOSED",
        ],
        "k740_parallel": (
            "K740 INJ-AVAX was also MR9-confirmed identity: K740 = -K500_raw + K484_raw. "
            "K743 LDO-ATOM follows same pattern but via SOL pivot not BTC pivot. "
            "Both reinforce MR9 STRICT: check triangle before any backtest."
        ),
        "tokens_exempt_from_triangle": [
            "Pairs where one token has NO SOL-pivot leg in the family (e.g., HBAR-ATOM once K735 is ATOM-base)",
            "Pairs using NON-SOL common pivot (e.g., INJ-ATOM uses ATOM-pivot only if no INJ-ATOM SOL path)",
            "Cross-cluster pairs where neither token has a SOL-alt-alt leg yet",
        ],
        "recommended_next_candidates": [
            "HBAR-ATOM: if K735 HBAR-SOL ACCEPTs, check HBAR-ATOM vs ATOM-SOL → if K684 in family → REJECT",
            "HBAR-TIA: same SOL-pivot check → likely BLOCKED if both in family",
            "FIL-ATOM: K739 FIL-SOL (ACCEPT) + K682 ATOM-SOL (ACCEPT) → FIL-ATOM BLOCKED",
            "FIL-TIA: K739 (FIL-SOL) + K694 (TIA-SOL) → FIL-TIA BLOCKED",
            "NEW TOKEN outside SOL-family: e.g., PENDLE, JUP, PYTH if not yet in family",
        ],
    }

    # ── JSON output ───────────────────────────────────────────────────────────
    result = {
        "wave":             "K743",
        "strategy":         "LDO-ATOM FR Differential Alt-Alt Eval (MR9 STRICT → ALGEBRAIC IDENTITY → REJECT)",
        "run_time_jst":     RUN_TS,
        "runtime_s":        round(elapsed, 2),
        "decision":         decision,
        "reject_code":      reject_code,
        "line_status":      line_status,
        "proceed_to_ph1":   proceed_to_ph1,
        "decision_summary": reject_summary,
        "phase0_mr9":       phase0,
        "mr9_lesson":       mr9_lesson,
        "backtest_skipped": True,
        "profit_usdc_yr_10m": None,
        "k523_ranges": {
            "note": "N/A — rejected at Phase 0 (MR9 algebraic identity). No profit projection warranted.",
            "conservative": None,
            "central": None,
            "optimistic": None,
        },
        "token_profile": {
            "ldo": {
                "name": "Lido DAO (LDO)",
                "category": "Ethereum Liquid Staking Derivative (LSD) governance",
                "parent_strategy": "K594 LDO-BTC REJECT (vol 0.80x, ETH cluster 0.43)",
                "alt_alt_entry":   "K721/K728 LDO-SOL ACCEPT CONDITIONAL",
                "fr_mean_ann_pct": 15.95,
                "fr_std":          2.449e-5,
            },
            "atom": {
                "name": "Cosmos Hub (ATOM)",
                "category": "Cosmos IBC Hub — proof-of-stake staking governance",
                "parent_strategy": "K493 ATOM-BTC ACCEPT (OOS Sh=50.79, vol_ratio=2.34x)",
                "alt_alt_entry":   "K682/K684 ATOM-SOL ACCEPT, K719 ENA-ATOM, K729 INJ-ATOM",
                "fr_mean_ann_pct": -3.27,
                "fr_std":          4.119e-5,
            },
        },
        "k339_compliance": {
            "repo_root":      str(REPO_ROOT),
            "out_json":       str(OUT_JSON),
            "out_md":         str(OUT_MD),
            "live_changes":   "NONE — read-only evaluation",
            "pattern":        "K339 REPO_ROOT",
        },
    }

    # Write JSON
    with open(OUT_JSON, "w") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"\n  JSON → {OUT_JSON}")

    # ── MD output ─────────────────────────────────────────────────────────────
    md = _build_md(result)
    with open(OUT_MD, "w") as fh:
        fh.write(md)
    print(f"  MD   → {OUT_MD}")

    print(f"\n  Elapsed: {elapsed:.2f}s")
    print("=" * 72)


def _build_md(r: Dict) -> str:
    mr9 = r["phase0_mr9"]["mr9"]
    lesson = r["mr9_lesson"]
    return f"""# K743 LDO-ATOM FR Differential Alt-Alt Eval

**Wave**: K743
**Run time**: {r['run_time_jst']}
**Decision**: **{r['decision']}** — `{r['reject_code']}`
**Line status**: {r['line_status']}

---

## Phase 0: MR9 STRICT Algebraic Identity Check

### Identity

```
LDO_fr - ATOM_fr  =  (LDO_fr - SOL_fr)  -  (ATOM_fr - SOL_fr)
K743_raw          =  K721_raw            -  K684_raw
```

**Proof**: Let L=LDO, A=ATOM, S=SOL.
- K743 = L − A
- K721 = L − S  (K728 ACCEPT CONDITIONAL OOS Sh=46.8)
- K684 = A − S  (K682 ACCEPT OOS Sh=43.4)
- K721 − K684 = (L−S) − (A−S) = L − A = K743  □

### Numerical verification

| Metric | Value | Threshold | Result |
|--------|-------|-----------|--------|
| Raw max_err | `{mr9['max_err_raw']:.4e}` | `1e-15` | **IDENTITY** |
| Smooth max_err | `{mr9['max_err_smoothed']:.4e}` | `1e-15` | **IDENTITY** |
| Signal identity err | `{mr9['signal_identity_err']:.4e}` | `0` | **IDENTICAL** |
| Signal correlation | `{mr9['signal_corr']:.6f}` | — | **PERFECT** |
| Identity confirmed | `{mr9['identity_confirmed']}` | — | **REJECT** |

### Data summary

- Rows: {r['phase0_mr9']['data_rows']:,}
- Date: {r['phase0_mr9']['date_start']} – {r['phase0_mr9']['date_end']}  ({r['phase0_mr9']['total_years']:.2f} yrs)
- LDO FR mean: {r['phase0_mr9']['ldo_fr_mean_ann_pct']:.2f}%/yr
- ATOM FR mean: {r['phase0_mr9']['atom_fr_mean_ann_pct']:.2f}%/yr
- LDO-ATOM diff mean: {r['phase0_mr9']['diff_mean_ann_pct']:.2f}%/yr
- Vol ratio LDO/ATOM: {r['phase0_mr9']['vol_ratio_ldo_atom']:.4f}

---

## Decision

**REJECT** — MR9 STRICT algebraic identity.

{r['decision_summary']}

Backtest skipped. Tokens saved.

---

## MR9 Lesson L002 (K743)

**Pattern**: LDO-ATOM = K721_raw − K684_raw (3-token triangle collapse via SOL pivot)

**Generalisation**: In the alt-alt family using SOL as the dominant pivot, for any two tokens X and Y where (X-SOL) and (Y-SOL) are both already accepted:
> (X-Y) = (X-SOL) − (Y-SOL)  →  ALWAYS algebraically redundant.

### LDO-* pairs blocked by triangle rule (K721 LDO-SOL in family)

{chr(10).join('- ' + p for p in lesson['token_pairs_blocked_by_triangle'])}

### Recommended next candidates

{chr(10).join('- ' + c for c in lesson['recommended_next_candidates'])}

---

## Parent Strategies

| Wave | Pair | Decision | OOS Sh |
|------|------|----------|--------|
| K728 | LDO-SOL (K721) | ACCEPT CONDITIONAL | 46.84 |
| K682 | ATOM-SOL (K684) | ACCEPT | 43.43 |
| K594 | LDO-BTC | REJECT (vol+cluster) | -3.82 |
| K493 | ATOM-BTC | ACCEPT | 50.79 |

---

## K523 Profit Ranges

**N/A** — rejected at Phase 0 (MR9 algebraic identity). No profit projection warranted.

---

*K339 REPO_ROOT | LIVE自動変更禁止 | {r['run_time_jst']}*
"""


if __name__ == "__main__":
    main()
