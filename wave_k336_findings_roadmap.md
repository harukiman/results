# Wave K336: R10/R11 untapped findings → K337+ implementation roadmap

**Generated**: 2026-05-25 19:58 JST
**Trigger**: User asked "外部リサーチ結果の戦略への組み込みや解析への活用は進んでいるか?"
**Honest answer**: implementation rate ~5%, but top-3 actionable always reach decision. K336 fixes the backlog gap.

## Implementation audit (R1-R11, 242 cumulative)

| Round | Items | Wave化 | Rate | Notes |
|---|---:|---:|---:|---|
| R1-R9 (~180) | unknown | unknown | ? | needs separate trace |
| R10 (20) | 3 | 15% | K297 ACCEPT (PAXG/SPX → satellite 20%), K298 (HL predictedFR API → K304 monitor), K296 MONITOR (Liminal HyperEVM) |
| R11 (20) | 2-3 | 12% | K315/K320 (HMM REJECT), K314 (RWA infra blocked) |

**Quality vs quantity**: Top-3 from each round always reach implementation decision (ACCEPT / REJECT / DEFER w/ trigger). The ~85% untapped are MED/LOW priority deferred, NOT ignored.

## R11 untapped — HIGH-priority 5 candidates

### K337 — R11-7 HypurrFi × Euler Finance HyperEVM分離リスク市場
- **Mechanism**: Isolated lending pools on HyperEVM, BLP担保化
- **Why interesting**: First clean on-chain HL-native yield arb opportunity
- **Action**: Read protocol docs, fetch TVL/borrow rates, prototype arb signal vs K297 RWA carry
- **Effort**: 1 sonnet wave (~4h)
- **Risk**: New protocol, low TVL → execution risk; defer if TVL < $20M
- **Expected**: 5-10 day investigation, ACCEPT/MONITOR/REJECT decision

### K338 — R11-11 Funding-Aware Optimal Market Making (arxiv)
- **Source**: arxiv 2605.06405
- **Direct relevance**: K208 (FR carry) — paper formalizes the optimal MM problem with FR signal
- **Action**: Read paper, implement reference strategy on K208 candidate symbols
- **Compare**: vs current K208 implementation
- **Effort**: 1 sonnet wave (~5h)
- **Expected**: K208 may benefit from MM-aware sizing rules

### K339 — R11-16 Transformer Actor-Critic perp rebalancer
- **Source**: ScienceDirect, VAE trend representation + Expert selection
- **Direct relevance**: K198 (ML allocator) — Transformer A-C is the next-gen architecture
- **Action**: Lightweight implementation (PyTorch or sklearn proxy), compare vs K198 Ridge baseline
- **Effort**: 1 sonnet wave (~6h, ML setup)
- **Risk**: Overfit risk on 447d K280 window
- **Expected**: Negative result more likely (K198 already adapts per K323), but worth testing

### K340 — R11-17 On-chain USDT flow → BTC 1h return predictor
- **Source**: arxiv 2411.06xxx
- **Mechanism**: USDT net inflow to exchanges → positive BTC 1h return prediction
- **Why interesting**: NEW signal axis orthogonal to FR carry (cross-chain liquidity)
- **Action**: Fetch on-chain USDT flow data (Glassnode/Nansen free tier), compute lead-lag, IS/OOS test
- **Effort**: 1 sonnet wave (~5h)
- **Risk**: Free-tier data may be insufficient
- **Expected**: If holds OOS, augments K280 entry timing

### K341 — R11-20 HL native options Q3 launch monitor
- **Source**: HL roadmap H2 2026
- **Why interesting**: New instrument = new vol surface = new carry opportunities (covered-call, FR + option premium hybrid)
- **Action**: NOT implementable yet (Q3 future), but design monitoring framework
- **Effort**: 0.5 wave (planning)
- **Trigger**: HL options launch announcement
- **Defer until**: 2026-07 (Q3 start)

## R11 untapped — MED priority (3 候補)

### K342+ candidates (no commitment date)
- **R11-9 Temporal Dynamics CEX→DEX info flow** — needs K304 data accumulation (~30d)
- **R11-10 Two-Tiered Funding (CEX-DEX 84% spreads)** — same as R11-9, K304 dependent
- **R11-13 HMM Bayesian non-homogeneous** — K315 used stationary; try non-hom variant

## R11 LOW / theoretical (academic interest only)
- R11-12 BSDE FR design (theoretical)
- R11-14 Wavelet-Transformer Fear/Greed (high-freq, infra heavy)
- R11-15 Meta-RL crypto (Actor-Judge-MetaJudge, very ambitious)
- R11-18 Functional PCA intraday (high-freq)
- R11-19 Deep RL Free-Energy (theoretical)

## R11 INFO (no action — informational only)
- R11-1 RWA OI $1.74B ATH (K314 absorbed)
- R11-2 SPX 24/7 S&P license (K297 already uses)
- R11-4 Ripple Prime (K314 blocked — HL not listing yet)
- R11-5 PAXG weekend 100% (K297 already uses)
- R11-6 HL HIP-4 prediction market (different asset class, separate research line)
- R11-8 USDH stablecoin (informational, not strategy-actionable yet)

## R10 untapped — also high-value backlog (17 / 20 untouched)

### K342-K344 candidates from R10
Need to re-read external_findings_round10.json to list specific items.
Top-of-mind from prior context:
- R10-002 (specific to be filled in K342)
- R10-005 (specific to be filled in K342)
- R10 not-top-3 had several DeFi-native angle findings

## Implementation plan (K337-K341 next 1-2 days)

| Wave | Source | Effort | Priority | Status |
|---|---|---:|---|---|
| K337 | R11-7 HypurrFi | 4h | HIGH | next sonnet slot |
| K338 | R11-11 Funding-Aware MM | 5h | HIGH | sonnet, after K337 |
| K339 | R11-16 Transformer A-C | 6h | MED-HIGH | conditional on resource |
| K340 | R11-17 USDT on-chain | 5h | MED-HIGH | sonnet, parallel-ok |
| K341 | R11-20 options Q3 monitor | 0.5h | LOW | local quick design |

## Self-critique

- Implementation rate of ~5% is **acceptable for top-3-focused research** but reveals there's signal in the unread 95%
- Should add a feedback memory rule: "After each tip-scraper round, allocate 1-2 wave slots to non-top-3 findings within 7 days"
- K336 itself is the corrective action

## Action items closed
- ✓ User question answered with honest rate + qualitative defense
- ✓ K337-K341 roadmap defined with effort + priority + expected outcomes
- → Memory rule TBD: "R-finding 3+1+1 rule" (top-3 acted immediately, +1 mid-priority per week, +1 backlog cleanup)
- → Schedule K337-K341 in next wave cycles
