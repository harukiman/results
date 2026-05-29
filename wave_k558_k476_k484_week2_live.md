# K558 Week 2 — K476 SOL-BTC + K484 AVAX-BTC Dual LIVE Activation

**Wave:** K558 | **Generated:** 2026-05-30 06:15 JST | **Pattern:** K339 REPO_ROOT  
**Status:** DUAL LIVE PREP — D+7 (K476) and D+9 (K484), 48h cascade gap  
**Combined Week 2:** +$263K/yr @$10M | **Cumulative W1-W2:** +$276K/yr @$10M

---

## Executive Summary

Week 2 of the K547 sequenced activation deploys two paired-trade FR differential
strategies in parallel, separated by 48 hours to manage cascade risk.

| Strategy | Activation | OOS Sharpe | Ann @$10M | Venue | Sleeve |
|----------|-----------|-----------|----------|-------|--------|
| K476 SOL-BTC FR | D+7 | 16.30 | $187K/yr | HL_ONLY | 3% |
| K484 AVAX-BTC FR | D+9 (+48h) | 43.89 | $76K/yr | HL_ONLY | 3% |
| **Week 2 combined** | — | — | **$263K/yr** | — | 6% |

### Profit @ All AUM Scales

| Strategy | @$10M | @$30M | @$100M |
|----------|-------|-------|--------|
| K449 ETH-BTC (W1) | $13K/yr | $39K/yr | $130K/yr |
| K476 SOL-BTC (W2 D+7) | $187K/yr | $561K/yr | $1,870K/yr |
| K484 AVAX-BTC (W2 D+9) | $76K/yr | $228K/yr | $760K/yr |
| **Cumulative W1+W2** | **$276K/yr** | **$828K/yr** | **$2,760K/yr** |

### HL Exposure Post-Week 2

```
Baseline (K280 60%, K449 3%): ~52%
+ K476 SOL-BTC D+7 (+3pp):   ~55%
+ K484 AVAX-BTC D+9 (+3pp):  ~58%  ← Post-Week 2 (7pp headroom to 65% cap)
```

---

## Phase 1: Pre-requisite Checklist

Before activating K476 (D+7), confirm ALL of the following:

- [ ] **K449 Week 1 Day 7 PASS** — K449 must be in LIVE mode (paper_trade_mode=False)
  ```bash
  cat data/k449_dashboard.json | python3 -c "import json,sys; print('LIVE:', not json.load(sys.stdin).get('paper_trade_mode', True))"
  ```
- [ ] **K280 75→60% applied (K552)** — HL exposure baseline at 52%
  ```bash
  cat data/k280_live_dashboard.json | python3 -c "import json,sys; print('K280 weight:', json.load(sys.stdin).get('k280_weight_pct', 75))"
  ```
- [ ] **HL post-Week1 ~52%** — verify exposure after K449 activation
- [ ] **K476 plist present** — `com.cryptolab.k476-sol-btc.plist` in REPO_ROOT
- [ ] **K484 plist present** — `com.cryptolab.k484-avax-btc.plist` in REPO_ROOT
- [ ] **K357 emergency exit registered** — `launchctl list | grep k357`
- [ ] **K476 scaffold in paper-trade** — `data/k476_dashboard.json` paper_trade_mode=True
- [ ] **K484 scaffold in paper-trade** — `data/k484_dashboard.json` paper_trade_mode=True
- [ ] **K498 Phase 1A (optional)** — BBO_SELECT smart router; K434 covers if not done

```bash
# Full pre-requisite check:
python3 wave_k558_k476_k484_week2_live.py --phase1
```

---

## Phase 2: K476 SOL-BTC Scaffold State

```bash
python3 wave_k558_k476_k484_week2_live.py --phase2
```

**Current state** (`data/k476_dashboard.json`):
- Strategy: K476 SOL-BTC FR Differential
- OOS Sharpe: **16.30** | Ann return: **$187,000/yr @$10M**
- Paper-trade: True | Position: NEUTRAL | HL_ONLY
- Sleeve: 3% | Leverage: 4x | Notional: $1,200,000 | Margin: $300,000

**SOL alpha thesis:** SOL perpetual FR driven by meme/DeFi activity spikes, L1 rivalry
sentiment, dApp gas surges — decorrelated from BTC FR baseline. G5b corr=0.28 (PASS
<0.40). Funding rate differential exploits this divergence as pure carry.

---

## Phase 3: K484 AVAX-BTC Scaffold State

```bash
python3 wave_k558_k476_k484_week2_live.py --phase3
```

**Current state** (`data/k484_dashboard.json`):
- Strategy: K484 AVAX-BTC FR Differential
- OOS Sharpe: **43.89** (family #1: AVAX > SOL 16.30 > BNB-BLOCKED > ETH 5.66)
- Paper-trade: True | Position: NEUTRAL | HL_ONLY
- Sleeve: 3% | Leverage: 4x | Notional: $1,200,000 | Margin: $300,000
- G5a corr: 0.30 (PASS <0.40) | HL post-W2 projected: 56-58%

**AVAX alpha thesis:** AVAX FR elevated by subnet launch cycles, subnet-native staking
competition, C-chain congestion during bull micro-cycles, Avalanche ecosystem launches
(USDC native, Wormhole inflows). Decorrelated from SOL (G5 corr ~0.28).

---

## Phase 4: D+7 K476 SOL-BTC LIVE Activation

> **LIVE 自動変更禁止** — execute manually only, per this checklist.

### D+7 User Checklist

1. **K449 W1 Day 7 PASS confirm**
   ```bash
   cat data/k449_dashboard.json | python3 -c "import json,sys; print('LIVE:', not json.load(sys.stdin).get('paper_trade_mode', True))"
   ```

2. **K476 dashboard fresh check**
   ```bash
   python3 wave_k558_k476_k484_week2_live.py --phase2
   ```

3. **K280 weight ≤60% verify**
   ```bash
   cat data/k280_live_dashboard.json | python3 -c "import json,sys; print(json.load(sys.stdin).get('k280_weight_pct'))"
   ```

4. **K357 emergency exit alive**
   ```bash
   launchctl list | grep k357
   ```

5. **Set environment variables** (runtime injection only — never store in files)
   ```bash
   export PAPER_TRADE=False
   export HL_USER_ADDRESS=<your-hl-wallet-address>
   export HL_PRIVATE_KEY=<your-private-key>
   ```

6. **Copy plist and replace REPO_ROOT placeholder**
   ```bash
   REPO_ROOT="$(pwd)"
   sed "s|REPO_ROOT|$REPO_ROOT|g" com.cryptolab.k476-sol-btc.plist \
     > ~/Library/LaunchAgents/com.cryptolab.k476-sol-btc.plist
   ```

7. **launchctl load K476**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.cryptolab.k476-sol-btc.plist
   launchctl list | grep k476-sol-btc
   # Expected: com.cryptolab.k476-sol-btc listed with PID
   ```

8. **Verify 3% sleeve initial position**
   ```bash
   tail -20 logs/k476_sol_btc.log
   ```

9. **Position sizing verification**
   - Sleeve: 3% × $10M = $300,000 margin
   - Leverage: 4x → $1,200,000 notional (2 legs)
   - SOL-PERP long $600K + BTC-PERP short $600K (delta-neutral)
   - HL exposure after: ~55% (52% + 3pp)

10. **24h monitor begins** — D+7 → D+8: fill rate, delta drift, FR polling

---

## Phase 5: D+9 K484 AVAX-BTC LIVE Activation (48h after K476)

> **48h cascade gap rationale:** SOL-AVAX G5 cross-corr ≈ 0.28 (below 0.40 PASS
> threshold, but non-trivial). Sequential D+7/D+9 spreads margin deployment, allows
> monitoring K476 fill rate and HL health before adding K484 exposure.

### D+9 User Checklist

1. **K476 D+2 PASS check (48h cascade gate)**
   ```bash
   cat data/k476_dashboard.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('Active:', not d.get('paper_trade_mode', True))"
   ```

2. **K476 first 48h fill rate check**
   ```bash
   grep -i 'fill\|trade\|position' logs/k476_sol_btc.log | tail -10
   ```

3. **HL margin health check** (post-K476 ~55%)
   ```bash
   launchctl list | grep -E 'k476|k449|k280'
   ```

4. **K484 dashboard fresh check**
   ```bash
   python3 wave_k558_k476_k484_week2_live.py --phase3
   ```

5. **Set environment variables**
   ```bash
   export PAPER_TRADE=False
   export HL_USER_ADDRESS=<your-hl-wallet-address>
   export HL_PRIVATE_KEY=<your-private-key>
   ```

6. **Copy plist and replace REPO_ROOT placeholder**
   ```bash
   REPO_ROOT="$(pwd)"
   sed "s|REPO_ROOT|$REPO_ROOT|g" com.cryptolab.k484-avax-btc.plist \
     > ~/Library/LaunchAgents/com.cryptolab.k484-avax-btc.plist
   ```

7. **launchctl load K484**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.cryptolab.k484-avax-btc.plist
   launchctl list | grep k484-avax-btc
   ```

8. **Verify 3% sleeve initial position**
   ```bash
   tail -20 logs/k484_avax_btc.log
   ```

9. **Position sizing verification**
   - Sleeve: 3% × $10M = $300,000 margin
   - Leverage: 4x → $1,200,000 notional (2 legs)
   - AVAX-PERP long $600K + BTC-PERP short $600K (delta-neutral)
   - HL exposure after: ~58% (55% + 3pp, 7pp headroom to 65% cap)

10. **HL exposure verify**
    ```
    K449 ~52% + K476 3pp + K484 3pp = ~58% < 65% cap ✓
    Headroom: 7pp for W3 K493 (2.5pp HL split) + W4/W5
    ```

11. **24h dual monitor begins** — D+9 → D+14 decision matrix

---

## Phase 6: Day 7-21 Monitoring

```bash
python3 wave_k558_k476_k484_week2_live.py --phase6
```

### Daily monitoring commands

```bash
# K476 log tail
tail -20 logs/k476_sol_btc.log

# K484 log tail
tail -20 logs/k484_avax_btc.log

# All daemon status
launchctl list | grep -E "k476|k484|k449|k280|k357"

# HL exposure proxy (combined margin check)
# K449 $300K + K476 $300K + K484 $300K = $900K margin (9% of $10M AUM)
```

### Monitoring metrics

| Metric | Gate | Frequency |
|--------|------|-----------|
| Daily realized Sharpe | ≥50% of OOS target (rolling 7d) | Daily |
| Fill rate | ≥60% per 8h interval | 8h |
| HL margin ratio | <80% (K357 triggers at 85%) | 8h |
| Cross-strategy corr K476-K484 | ≤0.40 (G5 check) | Weekly |
| Delta-neutral drift | <2% per leg | 8h |
| FR signal fires | ≥1/week minimum | Weekly |
| HL exposure total | ≤65% hard cap | Daily |
| FR diff 7d avg SOL-BTC | >0 (signal active) | 8h |
| FR diff 7d avg AVAX-BTC | >0 (signal active) | 8h |

---

## Phase 7: Decision Matrix Day 14

```bash
python3 wave_k558_k476_k484_week2_live.py --phase7
# or
python3 wave_k558_k476_k484_week2_live.py --checklist-d14
```

### K476 SOL-BTC D+14 (OOS Sh 16.30)

| Realized Sh | Threshold | Decision | Action |
|------------|----------|----------|--------|
| ≥ 8.0 | ≥50% of OOS | **PASS** | Expand 3% → 4% sleeve |
| 5.0 – 8.0 | 30-50% | **HOLD** | Maintain 3%, continue D+21 |
| < 5.0 | <30% | **ROLLBACK** | Unload daemon, paper-trade |

### K484 AVAX-BTC D+14 (OOS Sh 43.89)

| Realized Sh | Threshold | Decision | Action |
|------------|----------|----------|--------|
| ≥ 22.0 | ≥50% of OOS | **PASS** | Expand 3% → 4% sleeve |
| 13.0 – 22.0 | 30-50% | **HOLD** | Maintain 3%, continue D+21 |
| < 13.0 | <30% | **ROLLBACK** | Unload daemon, paper-trade |

### Joint D+14 gates (both required)

- Fill rate both ≥ 60%
- HL exposure ≤ 65% (post-W2 ~58%, headroom 7pp)
- No HL margin calls in 7 days
- Cross-corr K476-K484 ≤ 0.40 (confirm G5 design-time value 0.28)

### Expand path (both PASS)

```bash
# K476 expand 3% → 4%:  +$1,600K notional (+$400K margin)
# K484 expand 3% → 4%:  +$1,600K notional (+$400K margin)
# HL post-expand: ~60% (2pp add, still under 65% cap)
# Then proceed to K493 Week 3 (K556 in flight)
```

### Rollback commands (if FAIL)

```bash
# K476 FAIL:
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k476-sol-btc.plist
# Reset to paper-trade, restart daemon with --dry-run

# K484 FAIL:
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k484-avax-btc.plist
# Reset to paper-trade, restart daemon with --dry-run
```

---

## Phase 8: HL Exposure Trajectory Post-Week 2

| Phase | HL% | Note |
|-------|-----|------|
| Baseline (K280 60%, K449 live) | ~52% | After K449 W1, K552 applied |
| + K476 SOL-BTC D+7 (+3pp) | ~55% | 3% sleeve × 100% HL |
| **+ K484 AVAX-BTC D+9 (+3pp)** | **~58%** | **Post-Week 2 state** |
| Cap (hard limit) | 65% | Never exceed |
| + K493 ATOM W3 (+2.5pp HL) | ~60.5% | 5% sleeve × 50% HL (Bybit split) |
| + K500+K507 SEI+TIA W4 (+2pp) | ~62.5% | Combined estimate |
| + K512 APT W5 (+1.5pp) | ~64% | v6.28 full live target |

**Headroom post-Week 2: 7pp** for Week 3-5 strategies.

---

## Phase 9: Profit Summary

### Week 2 combined profit

| | @$10M | @$30M | @$100M |
|--|------|------|------|
| K476 SOL-BTC | $187,000/yr | $561,000/yr | $1,870,000/yr |
| K484 AVAX-BTC | $76,000/yr | $228,000/yr | $760,000/yr |
| **Week 2 combined** | **$263,000/yr** | **$789,000/yr** | **$2,630,000/yr** |

### Cumulative W1+W2

| | @$10M | @$30M | @$100M |
|--|------|------|------|
| K449 ETH-BTC (W1) | $13,000/yr | $39,000/yr | $130,000/yr |
| K476 SOL-BTC (W2) | $187,000/yr | $561,000/yr | $1,870,000/yr |
| K484 AVAX-BTC (W2) | $76,000/yr | $228,000/yr | $760,000/yr |
| **Total cumulative** | **$276,000/yr** | **$828,000/yr** | **$2,760,000/yr** |

### Daily / monthly breakdown (@$10M)

- K476: $512/day | $15,583/mo | $187,000/yr
- K484: $208/day | $6,333/mo | $76,000/yr
- Week 2 add: $720/day | $21,916/mo | $263,000/yr
- Cumulative W1+W2: $756/day | $23,000/mo | $276,000/yr

---

## Phase 10: Risk Register

| Risk | Level | Mitigation |
|------|-------|------------|
| Dual activation same week | MEDIUM | 48h cascade gap (K547 protocol) |
| SOL high volatility | MEDIUM | 4x leverage, delta-neutral — vol isolated to FR diff |
| AVAX subnet ecosystem risk | LOW | Subnet-driven FR spikes = edge source; G5 corr=0.28 |
| HL cap proximity | LOW | 58% post-W2 vs 65% cap — 7pp headroom |
| SOL-AVAX cross-corr spike | LOW | G5 design-time corr=0.28 (PASS <0.40); 48h gap monitoring |
| Fill rate degradation | MEDIUM | POST_ONLY_PARALLEL, HL_ONLY primary confirmed |
| FR regime shift (SOL→0) | LOW | 7d rolling avg gate; NEUTRAL if diff < threshold |
| FR regime shift (AVAX→0) | LOW | Same gate; AVAX-BTC diff check |
| HL margin call (dual LIVE) | LOW | 3% × 4x × 2 = 9% total margin; K357 exit registered |
| K449 W1 not PASS by D+7 | LOW | Phase 1 prereq gate; delay K476 if K449 not LIVE |

---

## K547 Full Activation Sequence (Context)

| Week | Strategy | Day | Ann @$10M | Cumulative | Wave |
|------|----------|-----|-----------|-----------|------|
| W1 | K449 ETH-BTC | D0 | $13K | $13K | K549 |
| W2 | K476 SOL-BTC | **D+7** | $187K | $200K | **K558** |
| W2 | K484 AVAX-BTC | **D+9** | $76K | $276K | **K558** |
| W3 | K493 ATOM-BTC | D+14 | $231K | $507K | K556 |
| W4 | K500+K507 SEI+TIA | D+21 | $354K | $861K | TBD |
| W5 | K512 APT-BTC | D+35 | $302K | $1,163K | TBD |

---

## User Action Reference

| Action | Day | Script | Status |
|--------|-----|--------|--------|
| K449 W1 confirm | D+7 prereq | `wave_k549_k449_week1_live.py` | K549 |
| K476 LIVE activation | D+7 | `wave_k558_k476_k484_week2_live.py --checklist-d7` | K558 |
| K484 LIVE activation | D+9 | `wave_k558_k476_k484_week2_live.py --checklist-d9` | K558 |
| D+14 decision matrix | D+14 | `wave_k558_k476_k484_week2_live.py --checklist-d14` | K558 |
| K493 Week 3 prep | D+14 | `wave_k556_k493_week3_live.py --status` | K556 |

Source files: `wave_k558_k476_k484_week2_live.{py,json,md}` | K339 REPO_ROOT

*K558 — Generated 2026-05-30 06:15 JST*
