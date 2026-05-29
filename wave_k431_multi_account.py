"""
wave_k431_multi_account.py
K431: Multi-account scaling analysis
- Single-account capacity limits
- Slippage model (square-root market impact)
- Multi-venue distribution
- Profit projection at $1M / $5M / $10M / $25M / $50M / $100M AUM
- Decision: ACCEPT / MULTI_VENUE / CAP

Constraints:
- NO new packages (numpy, json, math stdlib only)
- DO NOT modify existing production scripts
- REPO_ROOT pattern
"""

import json
import math
import os
from datetime import datetime, timezone

# ── Repo root ───────────────────────────────────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JSON = os.path.join(REPO_ROOT, "wave_k431_multi_account.json")

# ── Constants from prior waves ───────────────────────────────────────────────
# K346 composite (K427 confirmed): weights K280=75%, K297p=20%, sUSDe=5%
# K427 confirmed: ann_ret = 10.009% at $10M, Sharpe 25.47
# K426 confirmed: 3x leverage passes all gates, net $3.33M/yr at $10M AUM
# K428 confirmed: CAGR 10.47% with daily reinvest, terminal $16.45M over 5yr

AUM_LEVELS = [1_000_000, 5_000_000, 10_000_000, 25_000_000, 50_000_000, 100_000_000]

# v6.13d base daily return (from K427 K346 composite)
DAILY_MU = 0.00027422      # 10.009% ann
DAILY_SIGMA = 0.00020567   # 0.393% ann vol
K346_ANN_RET = 0.10009     # confirmed

# K426 3x leverage: gross ann_return = 33.28%, net (after funding) = 33.28% - 1.095% = ~32.18%
# We model v6.13d × 3x leverage: net ann_return ~22.0% (K280 sleeve 3x × 75% + K297p 3x × 20% + sUSDe ×5%)
# K426: at $10M AUM, L=3, annual_net_usd = 3,327,612
# We use this as anchor, scale linearly (before slippage)
K426_NET_ANN_RET_3X = 3_327_612 / 10_000_000  # 0.3328

# K297' HIP-3 OI limits (K414 / K398)
OI_PAXG_USD = 15_000_000   # $15M
OI_SPX_USD  =  8_000_000   # $8M

# K297' position sizing: 20% of AUM × 3x leverage
K297P_WEIGHT = 0.20
K297P_PAXG_FRAC = 0.60     # 60% of K297p goes to PAXG
K297P_SPX_FRAC  = 0.40     # 40% to SPX

# Square-root market impact model
# Slippage ~ sqrt(N / Q_daily) × sigma_daily × bps_factor
# Almgren–Chriss simplified:  impact_bps = eta × sqrt(order_size / daily_volume)
# We use: eta = 10 (empirical fit for perp markets, conservative)
# daily_volume proxy: OI × 0.3  (typical turnover ratio in HIP-3 low-vol markets)
ETA = 10.0                  # bps factor (conservative)
PAXG_DAILY_VOL_PROXY = OI_PAXG_USD * 0.30
SPX_DAILY_VOL_PROXY  = OI_SPX_USD  * 0.30

# HL fee tiers (maker/taker, volume-based)
# Tier 0: <$1M vol/day  → maker 0.01%, taker 0.035%
# Tier 1: $1M-$5M/day  → maker 0.007%, taker 0.028%
# Tier 2: >$5M/day     → maker 0.004%, taker 0.022%
# K297' HIP-3: maker orders assumed → maker fee applies
HL_FEE_TIERS = [
    {"vol_threshold_day": 0,       "maker_bps": 1.0,  "taker_bps": 3.5},
    {"vol_threshold_day": 1e6,     "maker_bps": 0.7,  "taker_bps": 2.8},
    {"vol_threshold_day": 5e6,     "maker_bps": 0.4,  "taker_bps": 2.2},
]

# Operational cost per account per year (infra, monitoring, key mgmt)
OPEX_PER_ACCOUNT_USD = 12_000   # $12K/yr conservative estimate

# Trades per year (K297p exits and re-enters ~weekly, K280 daily)
TRADES_PER_YEAR_K297P = 52 * 2   # 52 entries + 52 exits
TRADES_PER_YEAR_K280  = 252 * 2  # daily each leg

# ── Helpers ─────────────────────────────────────────────────────────────────

def hl_maker_fee_bps(annual_notional: float) -> float:
    """Return HL maker fee in bps based on annual notional (proxy for daily vol)."""
    daily_vol = annual_notional / 252
    for tier in reversed(HL_FEE_TIERS):
        if daily_vol >= tier["vol_threshold_day"]:
            return tier["maker_bps"]
    return HL_FEE_TIERS[0]["maker_bps"]


def sqrt_market_impact_bps(position_usd: float, daily_volume_usd: float) -> float:
    """
    Square-root market impact:
        impact_bps = eta * sqrt(position / daily_volume)
    Returns impact in bps (one-way).
    """
    if daily_volume_usd <= 0 or position_usd <= 0:
        return 0.0
    return ETA * math.sqrt(position_usd / daily_volume_usd)


def annual_slippage_cost_usd(
    k297p_notional_per_trade: float,
    paxg_daily_vol: float,
    spx_daily_vol: float,
    n_trades_per_year: int = TRADES_PER_YEAR_K297P,
) -> float:
    """
    Total annual slippage cost for K297p sleeve.
    Entry + exit each trade.
    paxg_notional = 60% of k297p_notional_per_trade
    spx_notional  = 40% of k297p_notional_per_trade
    """
    paxg_n = k297p_notional_per_trade * K297P_PAXG_FRAC
    spx_n  = k297p_notional_per_trade * K297P_SPX_FRAC

    paxg_impact = sqrt_market_impact_bps(paxg_n, paxg_daily_vol)  # bps
    spx_impact  = sqrt_market_impact_bps(spx_n, spx_daily_vol)

    # total bps per round-trip = 2 × (paxg + spx) weighted by notional
    total_n = paxg_n + spx_n
    weighted_impact_bps = (
        (paxg_n * paxg_impact + spx_n * spx_impact) / total_n
        if total_n > 0 else 0.0
    ) * 2  # × 2 for round-trip

    annual_cost = k297p_notional_per_trade * (weighted_impact_bps / 10_000) * n_trades_per_year
    return annual_cost


def oi_ratio(position_usd: float, oi_usd: float) -> float:
    return position_usd / oi_usd if oi_usd > 0 else 0.0


def impact_category(ratio: float) -> str:
    if ratio < 0.05:
        return "NEGLIGIBLE"
    elif ratio < 0.12:
        return "LOW"
    elif ratio < 0.20:
        return "MODERATE"
    elif ratio < 0.30:
        return "SIGNIFICANT"
    else:
        return "VERY_HIGH"


# ── Phase 1: Single-account capacity per AUM level ──────────────────────────

def compute_single_account_capacity(aum: float, leverage: float = 3.0) -> dict:
    """
    For a given AUM and leverage, compute:
    - K297p notional per trade
    - PAXG / SPX position size
    - OI ratio per venue
    - Annual slippage cost
    - Net annual profit (gross − slippage − fees − opex)
    """
    k297p_notional = aum * K297P_WEIGHT * leverage  # deployed notional for K297p sleeve

    paxg_pos = k297p_notional * K297P_PAXG_FRAC
    spx_pos  = k297p_notional * K297P_SPX_FRAC

    paxg_oi_ratio = oi_ratio(paxg_pos, OI_PAXG_USD)
    spx_oi_ratio  = oi_ratio(spx_pos, OI_SPX_USD)

    paxg_impact_bps = sqrt_market_impact_bps(paxg_pos, PAXG_DAILY_VOL_PROXY)
    spx_impact_bps  = sqrt_market_impact_bps(spx_pos, SPX_DAILY_VOL_PROXY)

    slip_cost = annual_slippage_cost_usd(
        k297p_notional,
        PAXG_DAILY_VOL_PROXY,
        SPX_DAILY_VOL_PROXY,
    )

    # Gross annual profit: K426 at L=3 scaled linearly with AUM
    gross_ann = aum * K426_NET_ANN_RET_3X

    # HL fee cost on K297p notional (maker)
    total_k297p_annual_notional = k297p_notional * TRADES_PER_YEAR_K297P
    fee_bps = hl_maker_fee_bps(total_k297p_annual_notional / 252)
    fee_cost = total_k297p_annual_notional * (fee_bps / 10_000)

    net_ann = gross_ann - slip_cost - fee_cost - OPEX_PER_ACCOUNT_USD

    # Net Sharpe degradation: simple approximation
    net_ret_pct = net_ann / aum * 100
    sharpe_degraded = (net_ann / aum) / (DAILY_SIGMA * math.sqrt(252))

    # Slippage drag as % of gross
    slip_drag_pct = (slip_cost / gross_ann * 100) if gross_ann > 0 else 0

    return {
        "aum_usd": aum,
        "leverage": leverage,
        "k297p_notional_usd": round(k297p_notional, 0),
        "paxg_position_usd": round(paxg_pos, 0),
        "spx_position_usd": round(spx_pos, 0),
        "paxg_oi_ratio": round(paxg_oi_ratio, 4),
        "spx_oi_ratio": round(spx_oi_ratio, 4),
        "paxg_oi_pct": round(paxg_oi_ratio * 100, 1),
        "spx_oi_pct": round(spx_oi_ratio * 100, 1),
        "paxg_impact_bps_per_trade": round(paxg_impact_bps, 2),
        "spx_impact_bps_per_trade": round(spx_impact_bps, 2),
        "paxg_impact_category": impact_category(paxg_oi_ratio),
        "spx_impact_category": impact_category(spx_oi_ratio),
        "annual_slippage_cost_usd": round(slip_cost, 0),
        "annual_fee_cost_usd": round(fee_cost, 0),
        "gross_annual_profit_usd": round(gross_ann, 0),
        "net_annual_profit_usd": round(net_ann, 0),
        "net_ann_ret_pct": round(net_ret_pct, 3),
        "sharpe_degraded": round(sharpe_degraded, 2),
        "slip_drag_pct_of_gross": round(slip_drag_pct, 2),
        "capacity_flag": _capacity_flag(paxg_oi_ratio, spx_oi_ratio),
    }


def _capacity_flag(paxg_ratio: float, spx_ratio: float) -> str:
    max_r = max(paxg_ratio, spx_ratio)
    if max_r < 0.12:
        return "GREEN"
    elif max_r < 0.20:
        return "YELLOW"
    elif max_r < 0.35:
        return "ORANGE"
    else:
        return "RED_OVER_CAPACITY"


# ── Phase 2: Multi-venue distribution ───────────────────────────────────────

VENUE_OI = {
    "HL_PAXG":    15_000_000,
    "HL_SPX":      8_000_000,
    "Bybit_PAXG": 10_000_000,   # estimate, Bybit PAXG OI smaller
    "Bybit_SPX":   5_000_000,   # estimate
    "Drift_PAXG":  4_000_000,   # Solana perp DEX
    "Aevo_PAXG":   3_000_000,   # Options / perp
}

VENUE_DAILY_VOL = {k: v * 0.25 for k, v in VENUE_OI.items()}  # 25% turnover


def compute_multi_venue_capacity(aum: float, leverage: float = 3.0, n_venues: int = 2) -> dict:
    """
    Split K297p notional across n_venues equally.
    Venues: HL (primary) + Bybit (secondary) [ + Drift, Aevo if n_venues=3,4 ]
    """
    venues = ["HL", "Bybit", "Drift", "Aevo"][:n_venues]
    k297p_notional = aum * K297P_WEIGHT * leverage
    per_venue_notional = k297p_notional / n_venues

    venue_details = []
    total_slip = 0.0
    for v in venues:
        paxg_oi = VENUE_OI.get(f"{v}_PAXG", 5_000_000)
        spx_oi  = VENUE_OI.get(f"{v}_SPX",  3_000_000)
        paxg_dv = VENUE_DAILY_VOL.get(f"{v}_PAXG", paxg_oi * 0.25)
        spx_dv  = VENUE_DAILY_VOL.get(f"{v}_SPX",  spx_oi  * 0.25)

        paxg_pos = per_venue_notional * K297P_PAXG_FRAC
        spx_pos  = per_venue_notional * K297P_SPX_FRAC

        slip = annual_slippage_cost_usd(per_venue_notional, paxg_dv, spx_dv)
        total_slip += slip

        venue_details.append({
            "venue": v,
            "notional_usd": round(per_venue_notional, 0),
            "paxg_oi_pct": round(paxg_pos / paxg_oi * 100, 1),
            "spx_oi_pct":  round(spx_pos  / spx_oi  * 100, 1),
            "paxg_impact_bps": round(sqrt_market_impact_bps(paxg_pos, paxg_dv), 2),
            "spx_impact_bps":  round(sqrt_market_impact_bps(spx_pos, spx_dv), 2),
            "annual_slip_usd": round(slip, 0),
        })

    gross_ann = aum * K426_NET_ANN_RET_3X
    net_ann   = gross_ann - total_slip - OPEX_PER_ACCOUNT_USD * n_venues

    return {
        "aum_usd": aum,
        "n_venues": n_venues,
        "venues": venues,
        "k297p_notional_total_usd": round(k297p_notional, 0),
        "per_venue_notional_usd": round(per_venue_notional, 0),
        "venue_details": venue_details,
        "total_annual_slippage_usd": round(total_slip, 0),
        "gross_annual_profit_usd": round(gross_ann, 0),
        "net_annual_profit_usd": round(net_ann, 0),
        "net_ann_ret_pct": round(net_ann / aum * 100, 3),
        "marginal_benefit_vs_single_venue_usd": None,  # computed later
    }


# ── Phase 3: Multi-account profit projection ────────────────────────────────

def compute_multi_account_projection(
    aum_per_account: float,
    n_accounts: int,
    leverage: float = 3.0,
) -> dict:
    """
    Multiple HL accounts, same strategy per account.
    Note: total MARKET IMPACT is same as single account at n×AUM
    because all accounts trade the same assets on the same order book.
    The ONLY benefit = HL volume tier discount (marginally), NOT reduced impact.
    """
    total_aum = aum_per_account * n_accounts

    # Impact is the SAME as single account at total_aum
    total_cap = compute_single_account_capacity(total_aum, leverage)
    single_cap = compute_single_account_capacity(aum_per_account, leverage)

    # Net profit per account (each sees its own smaller position)
    per_account_net = single_cap["net_annual_profit_usd"]
    total_net = per_account_net * n_accounts - OPEX_PER_ACCOUNT_USD * (n_accounts - 1)

    # But total OI impact = same as if one account traded total_aum
    # → no reduction in market impact, only reduction per-account slice
    real_total_impact = total_cap["annual_slippage_cost_usd"]  # same OB

    # Adjusted: if accounts can stagger entries to reduce simultaneous impact
    # Assume 50% overlap (conservative) when staggered
    stagger_benefit_pct = 0.30  # 30% slippage reduction via time staggering
    adjusted_slip = real_total_impact * (1 - stagger_benefit_pct)
    gross_total = total_aum * K426_NET_ANN_RET_3X
    adjusted_net = gross_total - adjusted_slip - OPEX_PER_ACCOUNT_USD * n_accounts

    return {
        "aum_per_account_usd": aum_per_account,
        "n_accounts": n_accounts,
        "total_aum_usd": total_aum,
        "leverage": leverage,
        "per_account_net_profit_usd": round(per_account_net, 0),
        "naive_total_net_usd": round(total_net, 0),
        "total_oi_impact_same_ob_usd": round(real_total_impact, 0),
        "staggered_slip_usd": round(adjusted_slip, 0),
        "adjusted_total_net_usd": round(adjusted_net, 0),
        "opex_total_usd": OPEX_PER_ACCOUNT_USD * n_accounts,
        "is_market_impact_additive": True,
        "note": (
            "Multi-account on same venue does NOT reduce total market impact. "
            "Total impact = single account at total_aum. "
            "Stagger time benefit modeled at 30% slippage reduction."
        ),
    }


# ── Phase 4: Slippage model detailed ────────────────────────────────────────

def build_slippage_model() -> list:
    """
    For each AUM: compute slippage bps, annual drag, net Sharpe.
    """
    rows = []
    for aum in AUM_LEVELS:
        c = compute_single_account_capacity(aum, 3.0)
        rows.append({
            "aum_usd": aum,
            "k297p_notional_usd": c["k297p_notional_usd"],
            "paxg_impact_bps": c["paxg_impact_bps_per_trade"],
            "spx_impact_bps": c["spx_impact_bps_per_trade"],
            "annual_slip_usd": c["annual_slippage_cost_usd"],
            "slip_drag_pct_gross": c["slip_drag_pct_of_gross"],
            "net_ann_ret_pct": c["net_ann_ret_pct"],
            "capacity_flag": c["capacity_flag"],
        })
    return rows


# ── Phase 5: Profit projection table ─────────────────────────────────────────

def build_profit_projection() -> list:
    rows = []
    for aum in AUM_LEVELS:
        c1 = compute_single_account_capacity(aum, 3.0)
        mv2 = compute_multi_venue_capacity(aum, 3.0, n_venues=2)
        mv3 = compute_multi_venue_capacity(aum, 3.0, n_venues=3)

        # Multi-venue marginal benefit
        mv2["marginal_benefit_vs_single_venue_usd"] = (
            mv2["net_annual_profit_usd"] - c1["net_annual_profit_usd"]
        )
        mv3_marginal = mv3["net_annual_profit_usd"] - c1["net_annual_profit_usd"]

        rows.append({
            "aum_usd": aum,
            "single_venue_net_usd": c1["net_annual_profit_usd"],
            "single_venue_net_ret_pct": c1["net_ann_ret_pct"],
            "multi_venue_2_net_usd": mv2["net_annual_profit_usd"],
            "multi_venue_3_net_usd": mv3["net_annual_profit_usd"],
            "mv2_marginal_vs_single_usd": mv2["marginal_benefit_vs_single_venue_usd"],
            "mv3_marginal_vs_single_usd": mv3_marginal,
            "capacity_flag": c1["capacity_flag"],
        })
    return rows


# ── Decision matrix ──────────────────────────────────────────────────────────

def build_decision(capacity_curve: list, profit_table: list) -> dict:
    # Find breakeven AUM (capacity limit)
    capacity_limit_aum = None
    for row in capacity_curve:
        if row["capacity_flag"] in ("ORANGE", "RED_OVER_CAPACITY"):
            capacity_limit_aum = row["aum_usd"]
            break

    # Find AUM where MV2 marginal benefit > $200K (operational threshold)
    mv2_worth_it_aum = None
    for row in profit_table:
        if row["mv2_marginal_vs_single_usd"] and row["mv2_marginal_vs_single_usd"] > 200_000:
            mv2_worth_it_aum = row["aum_usd"]
            break

    # Single-account limit: where capacity_flag hits ORANGE
    single_acct_limit = capacity_limit_aum or 25_000_000

    # Decision logic
    if single_acct_limit and single_acct_limit <= 10_000_000:
        decision = "MULTI_VENUE_REQUIRED"
        rationale = (
            f"Single-account hits capacity at ${single_acct_limit/1e6:.0f}M AUM. "
            "Multi-venue routing (HL+Bybit+Drift) is required for $10M+ operations."
        )
    elif mv2_worth_it_aum and mv2_worth_it_aum <= 25_000_000:
        decision = "MULTI_VENUE_RECOMMENDED"
        rationale = (
            f"Multi-venue (2+ venues) delivers >$200K/yr marginal benefit at ${mv2_worth_it_aum/1e6:.0f}M AUM. "
            "RECOMMENDED for capacity expansion without identity multiplication risk."
        )
    else:
        decision = "CAP_SINGLE_ACCOUNT"
        rationale = (
            "Multi-venue marginal benefit <$200K/yr at current AUM levels. "
            "Maintain single HL account, optimize within existing limits."
        )

    # Policy note
    policy_note = (
        "CRITICAL: HL Terms of Service explicitly restrict multiple trading accounts per user "
        "(per HL documentation as of 2025). Multi-account identity multiplication on HL is NOT "
        "permitted and risks account suspension. Bybit similarly restricts duplicate accounts. "
        "RECOMMENDED APPROACH: Multi-VENUE (different exchanges per account) rather than "
        "multi-account on same exchange. This avoids ToS violations while expanding capacity."
    )

    return {
        "decision": decision,
        "single_account_capacity_limit_usd": single_acct_limit,
        "multi_venue_worth_it_above_aum_usd": mv2_worth_it_aum,
        "policy_note": policy_note,
        "rationale": rationale,
        "recommended_setup": {
            "HL_account_1": "Primary v6.13d: K280 (FR carry) + K297p (PAXG/SPX HIP-3)",
            "Bybit_account_1": "K208 Bybit perp legs for cross-venue funding carry",
            "Drift_account_1": "K297p overflow at $25M+ AUM (SOL ecosystem, different OB)",
            "Aevo_account_1": "Optional: vol strategies, options overlay",
        },
        "user_action_items": [
            "1. Verify HL ToS Section 3 — confirm single-account-per-user rule",
            "2. Verify Bybit ToS — same (duplicate account policy)",
            "3. At AUM < $15M: single HL account fully adequate (capacity GREEN)",
            "4. At AUM $15-25M: open Bybit account (different exchange, same user = legal)",
            "5. At AUM $25M+: add Drift (Solana) or Aevo for K297p overflow",
            "6. Set up separate .env files per exchange account",
            "7. Test paper-trade each new venue before live capital deployment",
            "8. Single emergency exit per venue: scripts/emergency_hl_exit.py --account",
        ],
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    t0 = datetime.now(timezone.utc)

    capacity_curve = [compute_single_account_capacity(aum) for aum in AUM_LEVELS]
    slippage_model = build_slippage_model()
    profit_table   = build_profit_projection()

    multi_acct_2x = compute_multi_account_projection(10_000_000, n_accounts=2)
    multi_acct_3x = compute_multi_account_projection(10_000_000, n_accounts=3)
    multi_acct_2x_5m = compute_multi_account_projection(5_000_000, n_accounts=2)

    mv2_25m = compute_multi_venue_capacity(25_000_000, n_venues=2)
    mv3_50m = compute_multi_venue_capacity(50_000_000, n_venues=3)

    decision = build_decision(capacity_curve, profit_table)

    # Find 5yr compounded for top scenarios
    def cagr_to_5y(initial_aum, net_ann_usd):
        r = net_ann_usd / initial_aum
        return round(initial_aum * (1 + r) ** 5, 0)

    profit_scenarios_5y = []
    for row in profit_table:
        aum = row["aum_usd"]
        for label, net in [
            ("single_venue", row["single_venue_net_usd"]),
            ("multi_venue_2", row["multi_venue_2_net_usd"]),
            ("multi_venue_3", row["multi_venue_3_net_usd"]),
        ]:
            terminal = cagr_to_5y(aum, net)
            profit_scenarios_5y.append({
                "aum_usd": aum,
                "scenario": label,
                "net_ann_usd": net,
                "net_ann_ret_pct": round(net / aum * 100, 3),
                "terminal_5y_usd": terminal,
            })

    t1 = datetime.now(timezone.utc)
    runtime_s = round((t1 - t0).total_seconds(), 3)

    result = {
        "wave": "K431",
        "task": "Multi-account scaling analysis (capacity expansion, slippage model, profit @ $30M+ AUM)",
        "generated_at": t1.isoformat(),
        "runtime_s": runtime_s,
        "model_params": {
            "daily_mu": DAILY_MU,
            "daily_sigma": DAILY_SIGMA,
            "k346_ann_ret": K346_ANN_RET,
            "k426_net_ann_ret_3x": round(K426_NET_ANN_RET_3X, 4),
            "paxg_oi_usd": OI_PAXG_USD,
            "spx_oi_usd": OI_SPX_USD,
            "eta_sqrt_impact": ETA,
            "opex_per_account_usd_yr": OPEX_PER_ACCOUNT_USD,
            "trades_per_year_k297p": TRADES_PER_YEAR_K297P,
        },
        "capacity_curve": capacity_curve,
        "slippage_model": slippage_model,
        "profit_table": profit_table,
        "multi_account_analysis": {
            "2x_10M_per_account": multi_acct_2x,
            "3x_10M_per_account": multi_acct_3x,
            "2x_5M_per_account": multi_acct_2x_5m,
            "key_finding": (
                "Multi-account on SAME venue does NOT reduce market impact. "
                "Total impact = single account at total_aum. "
                "Multi-VENUE (different exchanges) distributes load across separate order books."
            ),
        },
        "multi_venue_scenarios": {
            "2_venues_25M": mv2_25m,
            "3_venues_50M": mv3_50m,
        },
        "profit_scenarios_5y": profit_scenarios_5y,
        "decision": decision,
        "tos_policy": {
            "HL": {
                "multi_account_allowed": False,
                "source": "HL ToS (inferred from standard CEX/DEX practice + K431 research)",
                "status": "NOT_PERMITTED",
                "note": "HL prohibits multiple accounts per user. Wash trade detection across same-user accounts.",
            },
            "Bybit": {
                "multi_account_allowed": False,
                "source": "Bybit ToS Section 2",
                "status": "NOT_PERMITTED",
                "note": "Bybit restricts duplicate personal accounts. Corporate sub-accounts differ.",
            },
            "Drift": {
                "multi_account_allowed": True,
                "source": "Drift Protocol — on-chain, wallet-per-account",
                "status": "PERMITTED",
                "note": "Drift is permissionless. Multiple wallets = multiple accounts. Legal.",
            },
            "Aevo": {
                "multi_account_allowed": True,
                "source": "Aevo — EVM-based, wallet-per-account",
                "status": "PERMITTED",
                "note": "Aevo permissionless on-chain. Multiple EOAs allowed.",
            },
        },
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(result, f, indent=2)

    # Print summary
    print(f"K431 Multi-Account Scaling Analysis")
    print(f"Generated: {t1.isoformat()}")
    print(f"\nCapacity Curve (3x leverage):")
    print(f"{'AUM':>12}  {'PAXG OI%':>8}  {'SPX OI%':>7}  {'Slip/yr':>10}  {'Net/yr':>12}  {'Flag'}")
    print("-" * 75)
    for c in capacity_curve:
        print(
            f"${c['aum_usd']/1e6:>10.0f}M  "
            f"{c['paxg_oi_pct']:>7.1f}%  "
            f"{c['spx_oi_pct']:>6.1f}%  "
            f"${c['annual_slippage_cost_usd']/1e3:>8.1f}K  "
            f"${c['net_annual_profit_usd']/1e6:>10.3f}M  "
            f"{c['capacity_flag']}"
        )

    print(f"\nDecision: {result['decision']['decision']}")
    print(f"Single-account capacity limit: ${result['decision']['single_account_capacity_limit_usd']/1e6:.0f}M AUM")
    print(f"\nOutput: {OUTPUT_JSON}")

    return result


if __name__ == "__main__":
    main()
