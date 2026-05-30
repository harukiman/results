# K773 — HIP-3 Batch FR Fetch + Round 2 Screen

**Wave:** K773  
**Date:** 2026-05-30  
**K339 REPO_ROOT:** /Users/nekonaomichi/crypto-lab  
**LIVE 自動変更禁止**

---

## Mission

K766 long-tail screen identified 99 tokens with no cached FR data.  
K766 produced 2 ACCEPTs (K768 BLUR, K769 AXS) from cached-data only.  
K773 fetches 30d FR history for the top-25 no-cache tokens (by dayNtlVlm) and re-runs the same K766/K744 pre-screen framework.

---

## Phase 1 Summary — K766 Input

| Stat | Count |
|------|-------|
| no_cache_hip3 tokens | 99 |
| K766 survivors (already cached) | 10 |
| K766 backlog | 7 |
| Top-N fetched this wave | 25 |

---

## Phase 2 — Batch FR Fetch Results

- **25/25 tokens** successfully fetched (500 rows each, ~30d hourly FR)
- 1 token (NXPC) hit 429 rate-limit on first run → fetched on re-run
- All data cached to `cache/k163_hl/hl_fr_{token}.parquet`
- **Fix applied:** New fetches return UTC-aware timestamps with microseconds; `_load_cached_fr` now applies `.dt.tz_convert("UTC").dt.tz_localize(None).dt.floor("h")` for alignment with legacy SOL anchor (hourly naive UTC)

---

## Phase 3 — Pre-Screen Results (K744/K766 framework)

Thresholds: vol_ratio ≥ 1.5x | max_corr ≤ 0.45 | carry_stability 35–80%

| # | Token | vol_ratio | max_corr | carry | FR_std_ann | DayVlm | Result |
|---|-------|-----------|----------|-------|------------|--------|--------|
| 1 | IO | 17.26x | -0.019 | 0.688 | 1.5% | $1.42M | **PASS** |
| 2 | MEGA | 9.53x | 0.134 | 0.704 | 0.8% | $1.06M | **PASS** |
| 3 | EIGEN | 3.97x | 0.031 | 0.622 | 0.3% | $1.13M | **PASS** |
| 4 | APE | 4.04x | 0.284 | 0.580 | 0.4% | $0.78M | **PASS** |
| 5 | SKY | 2.61x | 0.126 | 0.578 | 0.2% | $0.50M | **PASS** |
| 6 | WLFI | 2.45x | 0.258 | 0.660 | 0.2% | $1.14M | **PASS** |
| 7 | kSHIB | 1.66x | 0.389 | 0.800 | 0.1% | $0.65M | **PASS** |
| – | CHIP | 17.35x | – | 0.310 | – | $0.63M | FAIL: carry too low |
| – | STABLE | 12.87x | – | 0.252 | – | $0.58M | FAIL: carry too low |
| – | AZTEC | 8.75x | – | 0.968 | – | $0.60M | FAIL: structural carry |
| – | STBL | 13.36x | – | 0.994 | – | $0.48M | FAIL: structural carry |
| – | VINE | 12.18x | – | 0.996 | – | $0.43M | FAIL: structural carry |
| – | 13 others | – | – | – | – | – | FAIL: vol_ratio or carry |

**Summary:** 7 PASS / 18 FAIL / 0 no-data

---

## Phase 4 — K774+ Wave Queue

### Top-3 → Immediate queue

| Wave | Token | Composite | vol_ratio | max_corr | carry | FR_std_ann | DayVlm | Notes |
|------|-------|-----------|-----------|----------|-------|------------|--------|-------|
| **K774** | **IO** | 0.2639 | 17.26x | -0.019 | 0.688 | 1.5% | $1.42M | LOW-LIQ, IOnet GPU DePIN |
| **K775** | **MEGA** | 0.0684 | 9.53x | 0.134 | 0.704 | 0.8% | $1.06M | LOW-LIQ |
| **K776** | **EIGEN** | 0.0133 | 3.97x | 0.031 | 0.622 | 0.3% | $1.13M | LOW-LIQ, EigenLayer restaking |

### Backlog (rank 4–7)

| Token | Composite | vol_ratio | max_corr | carry | DayVlm |
|-------|-----------|-----------|----------|-------|--------|
| APE | 0.0102 | 4.04x | 0.284 | 0.580 | $0.78M |
| SKY | 0.0052 | 2.61x | 0.126 | 0.578 | $0.50M |
| WLFI | 0.0039 | 2.45x | 0.258 | 0.660 | $1.14M |
| kSHIB | 0.0015 | 1.66x | 0.389 | 0.800 | $0.65M |

---

## Combined K766+K773 Ranked — Top 10

| # | Source | Token | Composite | vol_ratio | max_corr | carry |
|---|--------|-------|-----------|-----------|----------|-------|
| 1 | K766 | BLUR | 2.0558 | 39.79x | -0.001 | 0.409 |
| 2 | **K773** | **IO** | **0.2639** | **17.26x** | **-0.019** | **0.688** |
| 3 | K766 | AXS | 0.0815 | 9.62x | 0.325 | 0.358 |
| 4 | **K773** | **MEGA** | **0.0684** | **9.53x** | **0.134** | **0.704** |
| 5 | K766 | COMP | 0.0469 | 6.02x | -0.008 | 0.430 |
| 6 | K766 | STX | 0.0388 | 5.64x | 0.047 | 0.649 |
| 7 | K766 | MEME | 0.0246 | 4.76x | 0.163 | 0.628 |
| 8 | **K773** | **EIGEN** | **0.0133** | **3.97x** | **0.031** | **0.622** |
| 9 | K766 | IMX | 0.0133 | 2.70x | 0.211 | 0.402 |
| 10 | **K773** | **APE** | **0.0102** | **4.04x** | **0.284** | **0.580** |

---

## Key Findings

### Notable pattern: structural carry dominance
- 14 of 18 failing tokens fail on carry_stability > 0.80 (structural long-carry)
- These HIP-3 deploys appear to have consistently positive funding — not suitable for mean-reversion alt-alt strategy
- This is likely because many are newly listed with high speculative demand and no short-seller pressure yet

### IO stands out
- IO (IOnet, GPU DePIN): vol_ratio 17.26x, max_corr **-0.019** (near-zero, highly cycle-independent), carry 0.688
- Composite 0.2639 — ranks #2 overall behind BLUR (2.0558)
- CONCERN: Only 30d history; $1.42M/day liquidity (well below $5M G6 threshold)
- Need full 180d eval at K774 to assess history depth and G6 entries/yr

### CHIP / STABLE near-miss
- CHIP: vol_ratio 17.35x (highest of batch!), carry 0.310 (just below 0.35 floor)
- STABLE: vol_ratio 12.87x, carry 0.252 (too low — mostly negative FR)
- Both would be strong candidates if carry_stability threshold adjusted — DEFERRED for sensitivity analysis

### HBAR corr now computed explicitly
- K766 had NaN for HBAR corr (cache gap); K773 computes it for all tokens
- No token failed on HBAR corr alone (max HBAR corr observed: 0.389 for kSHIB)

---

## Constraints & Risks

- **ROI deferred to K774+**: Pre-screen only; no full 180d backtest
- **Liquidity concern**: All 7 survivors are LOW-LIQ (<$5M/day) — may fail G6 entries/yr at full §6 eval
- **30d data only**: Newly listed HIP-3 tokens; insufficient for G9 history requirement (need 180d+)
- **K523**: 3-point projection (cons/mid/opt) mandatory at K774+ full eval
- **HL 66.8% concentration** (at CAP): new paired-trade paper-gate-strict still applies

---

## Deliverables

| File | Description |
|------|-------------|
| `wave_k773_hip3_round2_screen.py` | Main script (~430 LOC, K339) |
| `wave_k773_hip3_round2_screen.json` | Full output JSON (see data/) |
| `wave_k773_hip3_round2_screen.md` | This summary |
| `data/hl_long_tail_candidates_round2.json` | Round-2 candidates JSON |
| `report.html` | K773 badge injected after K770 badge |

---

## Next Wave Queue

- **K774**: IO (IOnet GPU DePIN) — full §6 alt-alt eval
- **K775**: MEGA — full §6 alt-alt eval  
- **K776**: EIGEN (EigenLayer restaking) — full §6 alt-alt eval
- **K772 STX**: Complete first (as noted in wave spec)

---

*K339 REPO_ROOT | LIVE 自動変更禁止 | 2026-05-30 22:43 JST*
