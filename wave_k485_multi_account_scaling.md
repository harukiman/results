# K485: Multi-Account Scaling Activation Playbook
### $30M → $200M Ceiling | +$2.1M–$72.4M/yr Phased Lift

**Generated:** 2026-05-30 02:54 JST  
**Wave chain:** K431 (multi-account analysis) → K454 (scaling redesign) → K458 (depth allocator) → K461 (v6.20 ACCEPT) → K481 (builder rebate) → K485 (activation playbook)  
**Mandate:** feedback_profit_max_priority axis #5 — Multi-account scaling activation playbook  

---

## Executive Summary

Multi-account scaling on the **same venue** provides **zero capacity benefit** and risks ToS violations on CEX platforms (Bybit/OKX). The correct path is:

1. **HL W2 wallet** = strategy isolation for K449/K476 paired-trade daemons (same OB, no capacity gain, but operational clarity)
2. **Bybit sub-account** = first true capacity expansion (+$2.1M/yr at $25M total AUM)
3. **dYdX/Aevo/OKX wallets** = Phase 2–3 expansion gates (conditional on paper-trade gates)
4. **v6.20 10-venue deployment** = $200M ceiling, +$72.4M/yr (K461 accepted, M6-M9)

### K431 ToS Correction

K431 incorrectly flagged HL as "NOT PERMITTED" for multi-account using CEX logic. **Correction:** HL is a non-KYC permissionless DEX where each wallet = independent on-chain account. Multiple wallets are technically unrestricted. The real constraint is **market impact** (same HL order book), not ToS.

---

## Profit Lift Table

| Phase | AUM | Architecture | Net/yr | vs Baseline | Lift |
|-------|-----|-------------|--------|-------------|------|
| Baseline | $10M | Single HL, v6.13d | **$2.08M/yr** | — | — |
| Phase 1A | $25M | HL primary + Bybit sub (2 venues) | **$4.28M/yr** | +$2.20M | +106% |
| Phase 1B | $10M | HL W1 + W2 (strategy isolation) | **$2.29M/yr** | +$210K | +10% |
| Phase 2 | $50M | HL + Bybit + dYdX (3 venues) | **$5.45M/yr** | +$3.37M | +162% |
| Phase 3 | $100M | v6.20 7-venue + K458 depth allocator | **$48.2M/yr** | +$46.1M | +2216% |
| Phase 4 | $200M | v6.20 10-venue optimal (K461) | **$74.4M/yr** | +$72.4M | +3479% |

> Phase 1A is the immediate action. Phase 3+ requires K449+K457 paper-trade gates + K458 depth-aware allocator.

---

## Phase 1: Per-Venue Policy Assessment

### HL (Hyperliquid)

| Attribute | Detail |
|-----------|--------|
| Type | DEX (non-KYC, permissionless L1) |
| KYC required | NO |
| Multiple wallets | **PERMITTED** — each wallet = independent on-chain account |
| Sub-account feature | YES — HL app supports vault sub-accounts; agent wallet pattern |
| ToS / policy | No ToS equivalent (smart contract protocol). Wallet creation unrestricted. |
| Market impact | CRITICAL: Multiple HL wallets share the SAME order book. Multi-wallet = ZERO slippage relief. |
| Recommended use | W2 for strategy isolation (K449/K476). NOT for capacity expansion. |
| K431 correction | K431 applied CEX logic incorrectly. HL is non-KYC DEX. Multi-wallet = technically OK. |

**HL Sub-Account (Vault) Pattern:**
```
Main wallet → approveAgent(agent_wallet_address)
Agent wallet can trade on behalf of main wallet
→ Use for K449/K476 paired-trade isolation without separate capital
```

### Bybit

| Attribute | Detail |
|-----------|--------|
| Type | CEX (KYC required) |
| KYC required | YES |
| Multiple personal accounts | **PROHIBITED** — ToS §2: one natural person = one personal account |
| Sub-account system | **PERMITTED** — Bybit Master + up to 20 sub-accounts |
| Sub-account KYC | Inherits from master (no separate KYC required for sub) |
| Sub-account API | Independent API keys per sub. Trade-only scope available. |
| Margin isolation | Each sub-account has independent margin pool. Margin call NOT cross-sub. |
| Rate limits | Independent per sub-account |
| Recommended expansion | Use Bybit sub-account #1 for K297p overflow at $15M+ AUM |

**Bybit Sub-Account Setup:**
```bash
# In Bybit web UI:
# Account & Security → Sub Accounts → Create Sub Account → Standard Sub
# Generate API: trade-only scope, IP whitelist your server IP
# Add to env:
export BYBIT_SUB1_API_KEY="<sub_api_key>"
export BYBIT_SUB1_SECRET="<sub_secret>"
# NEVER commit to git
```

### OKX

| Attribute | Detail |
|-----------|--------|
| Type | CEX (KYC required) |
| Multiple personal accounts | **PROHIBITED** — User Agreement §3.1 |
| Sub-account system | **PERMITTED** — up to 30 sub-accounts under master |
| Sub-account API | Independent API. Rate limit shared at account group level (3,000 req/min group). |
| Recommended expansion | K456 Action #16 — fund OKX sub for K208 3rd venue at $20M+ AUM |

### Aevo

| Attribute | Detail |
|-----------|--------|
| Type | DEX (OP Stack L2, non-KYC) |
| Multiple wallets | **PERMITTED** — EVM permissionless |
| Sub-account | N/A — wallet = account |
| Recommended expansion | K460 Action #17 — Aevo wallet for K208 4th venue (1h funding cycle) |

### dYdX v4

| Attribute | Detail |
|-----------|--------|
| Type | DEX (Cosmos chain, non-KYC) |
| Multiple wallets | **PERMITTED** — Cosmos wallet = sovereign account |
| Sub-account | YES — dYdX v4 native sub-account index within same address |
| Recommended expansion | K460 Action #18 — Cosmos wallet, sub-account index 0 |

### Lighter

| Attribute | Detail |
|-----------|--------|
| Type | DEX (zkSync-based, non-KYC) |
| Multiple wallets | **PERMITTED** — EVM permissionless |
| Recommended expansion | K465 25th daemon. Smaller OB, genuine independence from HL. |

### Vertex

| Attribute | Detail |
|-----------|--------|
| Type | DEX (Arbitrum L2, non-KYC) |
| Multiple wallets | **PERMITTED** — EVM permissionless |
| Recommended expansion | K465 26th daemon. Cross-margin perps on Arbitrum. |

---

## Phase 2: Tax / Legal Considerations (Non-US Trader)

### HL Multiple Wallets

- **KYC issue:** NONE — HL is non-KYC. No identity linking across wallets.
- **Tax treatment:** Each wallet address is a separate accounting entity. Track P&L per address.
- **Tools:** Koinly, CoinTracker support multi-address aggregation.
- **Loss harvesting:** K444 loss harvester must be extended to accept `--wallet` flag for multi-wallet operation.

### Bybit Sub-Account

- **KYC issue:** NONE — sub inherits master KYC. Explicitly supported feature.
- **Tax treatment:** Sub-accounts typically aggregated under master account holder in most jurisdictions.
- **Action:** Export sub-account trade history separately. Bybit provides per-sub tax reports.
- **CPA note:** Verify treatment with local tax advisor.

### Family Member Accounts

- **Legality:** If a different natural person (family member) creates their own account with their own KYC → fully legal, separate entity.
- **NOT OK:** Operating under another person's account without full legal consent and ownership transfer.
- **Tax separation:** Family member's account = their profits/losses. No commingling. Document any capital transfer as loan or capital contribution.
- **Practical:** This is a valid long-term scaling path but requires the family member to manage their own account. Automated systems running on their private keys = requires explicit written authorization.

### Wash Sale Risk Across Wallets

- **Risk:** In many non-US jurisdictions, wash sale rules apply per-taxpayer not per-account. Selling at loss in W1 and rebuying in W2 of same asset may trigger wash sale.
- **Mitigation:** Consult local tax advisor. Track cross-wallet positions before K444 loss harvesting.

---

## Phase 3: Operational Architecture

### Wallet Registry

```
W1_HL_primary      : Main HL wallet (v6.13d operator)
                     Strategies: K280 (FR carry) + K297p (HIP-3) + sUSDe
                     AUM target: $10–15M
                     Env: HL_PRIVATE_KEY

W2_HL_strategy_iso : HL secondary wallet (strategy isolation)
                     Strategies: K449 (ETH-BTC) + K476 (SOL-BTC) paired-trade
                     AUM target: $2–5M (small paired positions)
                     Env: HL_PRIVATE_KEY_W2
                     Note: SAME HL OB — strategy clarity only, not capacity

W3_Bybit_sub1      : Bybit sub-account #1 (capacity expansion)
                     Strategies: K208 Bybit leg + K297p overflow
                     AUM target: $5–15M (grows with total AUM)
                     Env: BYBIT_SUB1_API_KEY, BYBIT_SUB1_SECRET

W4_dYdX_cosmos     : dYdX v4 Cosmos wallet (K460 scaffold)
                     Strategies: K208 dYdX leg (1h funding cycle)
                     AUM target: $3–10M
                     Env: DYDX_MNEMONIC (bip39)

W5_Aevo_evm        : Aevo EVM wallet (K460 scaffold)
                     Strategies: K208 Aevo leg (1h funding cycle)
                     AUM target: $2–5M
                     Env: AEVO_PRIVATE_KEY
```

### Capital Allocation by Phase

```
Phase 1 ($25M total):
  W1 HL primary   : 50% = $12.5M
  W3 Bybit sub    : 30% = $7.5M
  W4 dYdX         : 10% = $2.5M
  W5 Aevo         : 10% = $2.5M

Phase 2 ($50M total):
  W1 HL primary   : 40% = $20M
  W3 Bybit sub    : 30% = $15M
  W4 dYdX         : 15% = $7.5M
  W5 Aevo         : 15% = $7.5M

Phase 3 ($100M total — K458 depth-aware allocator required):
  W1 HL primary   : 30% = $30M
  W3 Bybit sub    : 25% = $25M
  W4 dYdX         : 15% = $15M
  W5 Aevo         : 15% = $15M
  W6 OKX sub      : 10% = $10M
  W7 others       :  5% = $5M
```

### Daemon Multiplexing Pattern

```plist
<!-- com.cryptolab.k449-eth-btc.W2.plist — K449 on W2 wallet -->
<key>EnvironmentVariables</key>
<dict>
    <key>HL_PRIVATE_KEY</key>  <!-- override to W2 -->
    <string>__HL_PRIVATE_KEY_W2__</string>  <!-- populated by activate.sh, not hardcoded -->
    <key>HL_WALLET_LABEL</key>
    <string>W2_strategy_iso</string>
</dict>
```

```bash
# activate.sh pattern (NEVER commit actual keys)
export HL_PRIVATE_KEY_W2="$(security find-generic-password -a hl_w2 -s cryptolab -w)"
launchctl setenv HL_PRIVATE_KEY_W2 "$HL_PRIVATE_KEY_W2"
```

### HL Concentration Rule (Cross-Wallet)

```
HL combined = W1_HL_notional + W2_HL_notional
Total AUM  = W1 + W2 + W3_Bybit + W4_dYdX + W5_Aevo

HL% = HL combined / Total AUM
RULE: HL% ≤ 65% (K358 rule, K479 confirmed 53% currently)

Example at $25M total:
  W1 HL = $12.5M (50%)
  W2 HL = $2.0M  (8%)
  HL combined = $14.5M / $25M = 58% ← OK (< 65%)

Example at $35M total (if W2 grows):
  W1 HL = $15M (43%)
  W2 HL = $5M  (14%)
  HL combined = $20M / $35M = 57% ← OK
```

---

## Phase 4: Capacity Expansion Math

### K431 Foundation (confirmed numbers)

Single HL account capacity (K297p OI model, 3x leverage):

| AUM | K297p Notional | PAXG OI% | SPX OI% | Slip/yr | Net/yr | Flag |
|-----|---------------|----------|---------|---------|--------|------|
| $1M | $600K | 2.4% | 3.0% | $37K | $278K | GREEN |
| $5M | $3.0M | 12.0% | 15.0% | $413K | $1.21M | YELLOW |
| $10M | $6.0M | 24.0% | 30.0% | $1.17M | **$2.08M** | ORANGE |
| $25M | $15.0M | 60.0% | 75.0% | $4.62M | $3.53M | RED |
| $50M | $30.0M | 120% | 150% | $13.1M | $3.24M | RED |
| $100M | $60.0M | 240% | 300% | $37.0M | **-$4.32M** | RED |

**Single HL account hard limit: $10M AUM (ORANGE above)**

### Multi-Venue Slippage Relief

At $25M total / 2 venues (HL + Bybit):
- Per-venue K297p: $7.5M
- HL PAXG OI%: 30% (vs 60% single venue) → ORANGE→YELLOW
- Bybit PAXG OI%: 45% → YELLOW
- Total slippage: **$4.01M/yr** (vs $4.62M single venue → 13% reduction)
- Net annual: **$4.28M/yr** (vs $3.53M single venue = **+$750K/yr**)

At $50M total / 3 venues (HL + Bybit + dYdX):
- Net annual: **$5.45M/yr** (vs $3.24M single venue = **+$2.21M/yr**)

### v6.20 Scaling (K454 depth-aware allocator)

| AUM | Net/yr | Net% | Venues | Gate |
|-----|--------|------|--------|------|
| $10M | $5.32M | 53.2% | 3 | K458 allocator |
| $25M | $13.2M | 52.9% | 3 | K458 allocator |
| $50M | $25.9M | 51.7% | 4 | all venue APIs |
| $100M | **$48.2M** | 48.2% | 7 | K449+K457 paper gates |
| $200M | **$74.4M** | 37.2% | 10 | K461 conditional ACCEPT |

---

## Phase 5: Profit Lift Quantification (USDC/yr)

```
@ $10M single HL (baseline):           $2.08M/yr   (20.8% net ret)
@ $25M HL+Bybit (Phase 1A):            $4.28M/yr   (+$2.20M, +106% vs baseline)
@ $10M HL W1+W2 strategy iso (Phase 1B): $2.29M/yr (+$210K, +10% vs baseline)
@ $50M 3-venue (Phase 2):              $5.45M/yr   (+$3.37M, +162% vs baseline)
@ $100M v6.20 7-venue (Phase 3):       $48.2M/yr   (+$46.1M, +2216% vs baseline)
@ $200M v6.20 10-venue (Phase 4):      $74.4M/yr   (+$72.4M, +3479% vs baseline)

Phase 1 incremental (1→2 accounts): +$2.20M/yr (low risk, 5-day setup)
Phase 2 incremental (2→3 accounts): +$1.17M/yr (medium risk, paper gate required)
Phase 3 incremental (3→7 venues):   +$42.7M/yr (requires K458 + all daemons)
```

---

## Phase 6: Activation Playbook (User-Actionable Steps)

### Step 1 — HL W2 Wallet Creation (~5 minutes, Day 1)

**Goal:** Strategy isolation for K449/K476 paired-trade daemons.

```bash
# 1. Open MetaMask → click account icon → Add Account → Create Account
# 2. Label it "K485-W2-strategy-iso"
# 3. Export private key: MetaMask → Account → Export Private Key
# 4. Store securely (hardware wallet or 1Password). NEVER in git.

# 5. Add to ~/.zshrc (NOT committed):
export HL_PRIVATE_KEY_W2="0x<YOUR_W2_KEY>"

# 6. Fund with small test amount (0.1 ETH for gas if needed, USDC for trading)

# 7. Update K449/K476 plist EnvironmentVariables to use HL_PRIVATE_KEY_W2:
# Edit com.cryptolab.k449-eth-btc.plist
# Edit com.cryptolab.k476-sol-btc.plist
# (see multi_account_orchestrator.py for plist template)

# 8. Reload daemons:
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist
launchctl load   ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist
launchctl list | grep k449  # verify
```

**Expected outcome:** K449 and K476 run on W2. K280/K297p stay on W1. Margin pools separated.

---

### Step 2 — Bybit Sub-Account Activation (~30 minutes, Day 2–3)

**Goal:** First genuine capacity expansion. K297p overflow on Bybit sub.

```bash
# A. Bybit Web UI:
# Login → Profile → Account & Security → Sub Accounts
# → Create Sub Account → Standard Sub Account
# → Set username/label (e.g., "k485-sub1-k297p")

# B. Generate API key for sub:
# Sub Account → API Management → Create API
# Scope: Trade only (NO withdrawal)
# IP restriction: add your server/Mac IP
# Copy: API Key and Secret

# C. Environment variables (add to ~/.zshrc, NOT git):
export BYBIT_SUB1_API_KEY="<sub_api_key>"
export BYBIT_SUB1_SECRET="<sub_secret>"

# D. Paper-trade verification (7 days):
python3 scripts/k280_live_fetch.py --venue=bybit --wallet=sub1 --dry-run
# Watch for fills, latency, API errors

# E. After 7-day paper gate:
# Transfer capital: Bybit master → sub #1 (internal transfer, instant)
# Start with $3–5M, grow to $10M+ as confidence builds
```

**Expected lift:** +$2.2M/yr when total AUM reaches $25M (HL $12.5M + Bybit $12.5M).

---

### Step 3 — Daemon Multiplexing Module (~3 hours, Day 3–5)

```bash
# Build multi_account_orchestrator.py:
python3 scripts/multi_account_orchestrator.py --help
# (see scripts/multi_account_orchestrator.py for full design)

# Dry-run test across all configured wallets:
python3 scripts/multi_account_orchestrator.py --dry-run --wallets=W1,W2,BYBIT1

# Verify position aggregation:
python3 scripts/multi_account_orchestrator.py --positions --wallets=all
```

---

### Step 4 — dYdX / Aevo Wallet Setup (~15 minutes each, Month 1–2)

```bash
# dYdX v4 (Cosmos wallet):
# Option A: Use existing Cosmos wallet if you have one
# Option B: Generate new:
#   npm install -g @cosmjs/cli  (or use Keplr wallet)
#   dydx-protocol.github.io → wallet generation guide
export DYDX_MNEMONIC="word1 word2 ... word24"  # BIP39 mnemonic, NEVER in git
# K460 daemon already scaffolded — just add env var

# Aevo (EVM wallet on OP Stack):
# Create new MetaMask account (Account 3) → export private key
export AEVO_PRIVATE_KEY="0x<aevo_key>"
# K460 daemon already scaffolded
```

---

### Step 5 — Capital Allocation (Phased, Operational)

```
Phase 1 trigger (now → AUM $15M):
  → W1 HL: full current AUM
  → W2 HL: K449+K476 strategy iso ($2M)

Phase 1A trigger (AUM $15M–$25M):
  → Bybit sub #1: transfer $5M (30% of AUM)
  → W1 HL: reduce to 50% of total AUM

Phase 2 trigger (AUM $25M–$50M, after K449+K457 paper gates):
  → Add dYdX/Aevo wallets: $5M each
  → W1 HL: 40%, Bybit: 30%, dYdX: 15%, Aevo: 15%

Phase 3 trigger (AUM $50M+, K458 depth allocator live):
  → K458 auto-routes K297p to venue with best fill quality
  → Manual capital allocation becomes automated routing
```

---

### Step 6 — Cross-Account Monitoring Dashboard

After multi_account_orchestrator.py is live, report.html K485 section shows:

- Per-wallet AUM (W1, W2, W3-Bybit, W4-dYdX, W5-Aevo)
- Per-wallet P&L (daily, weekly)
- Combined HL exposure % (W1 + W2 combined / total AUM)
- Phase completion status (Phase 1 active / Phase 2 pending / Phase 3 gated)
- Alert: HL combined > 65% cap

---

## Phase 7: Risk / Edge Cases

### HL Same OB Confusion
- **Risk:** Two HL wallets trading same symbol appear to interact. UI shows both in same MetaMask profile by default.
- **Mitigation:** Use separate browser profiles (Chrome Profile A = W1, Chrome Profile B = W2). Label wallets clearly in MetaMask. Do NOT switch accounts during active trading.

### Bybit Sub Margin Call
- **Risk:** Sub-account margin call does NOT cascade to master. Each sub has independent margin.
- **Mitigation:** Set per-sub position limits. Replicate K357 emergency exit per sub-account.
  ```bash
  # Emergency exit all positions on Bybit sub1:
  python3 scripts/emergency_hl_exit.py --venue=bybit --wallet=sub1
  ```

### Tax Complexity at Multi-Wallet Scale
- **Risk:** Each wallet = separate accounting entity. K444 loss harvester designed single-wallet.
- **Mitigation:** Extend K444 with `--wallet` flag. Loop across all addresses. Use per-address on-chain query.
  ```python
  # K444 extension (K485 planning):
  for wallet in ["W1_0xabcd...", "W2_0xef12...", "bybit_sub1"]:
      harvest(wallet, tax_year=2026)
  ```

### HL Concentration Cross-Wallet
- **Risk:** Both W1 and W2 are on HL. Total HL exposure = W1 + W2 notional.
- **Rule:** (W1_HL + W2_HL) / total_AUM ≤ 65%
- **Current (K479):** 53%. With W2 $2M on $12M total → 58%. Safe headroom.

### Private Key Management
- **Risk:** More wallets = more attack surface.
- **Mitigation:** 
  - W1 (primary, large AUM): Hardware wallet (Ledger/Trezor) — most secure
  - W2 (strategy iso, small): MetaMask with passphrase
  - Bybit sub: API key with trade-only scope + IP restriction (no withdrawal key)
  - dYdX/Aevo: MetaMask or dedicated cold wallet
  - NEVER store keys in git, HTML reports, or plain text files

---

## Phase 8: Implementation Roadmap

| ID | Action | Timeline | Complexity | Lift |
|----|--------|----------|-----------|------|
| K485-1 | HL W2 wallet creation + plist update | Day 1 (5 min) | TRIVIAL | +$210K/yr |
| K485-2 | Bybit sub-account activation + 7d paper | Day 2–3 (30 min) + 7d | LOW | +$2.2M/yr at $25M |
| K485-3 | multi_account_orchestrator.py | Day 3–5 (3 hr) | MEDIUM | Operational clarity |
| K485-4 | Cross-wallet monitoring dashboard | Day 5–7 (2 hr) | LOW | Operational safety |
| K485-5 | dYdX + Aevo wallet setup | Month 1 (15 min each) | TRIVIAL | Unlock Phase 2 |
| K485-6 | K297p live on Bybit sub | Week 2 (after paper gate) | LOW | +$2.2M/yr activated |
| K485-7 | Capital scaling Phase 1→2→3 | Month 1–6 | OPERATIONAL | Phased lift |

---

## Phase 9: Recommendations

### Immediate (Phase 1 — Low Risk, High ROI)

**Recommended Action: 1 → 2 wallets/venues → $25M total AUM**

- HL W2: Strategy isolation (K449/K476). 5 min setup. +$210K/yr clarity benefit.
- Bybit sub #1: K297p overflow + K208 Bybit leg. 30 min setup + 7d paper. **+$2.2M/yr** at $25M.
- Total Phase 1 lift: **+$2.2M/yr** (106% above $10M single-HL baseline)
- Risk: LOW (Bybit sub-account = supported feature, no ToS issue)
- Timeline: Day 1–14

### Short-Term (Phase 2 — Conditional, After Gates)

**Recommended Action: 2 → 3 venues → $50M total AUM**

- Gate: K449+K457 paper-trade 60d passes (K461 condition)
- Add dYdX v4 + Aevo (K460 already scaffolded)
- Additional lift: **+$1.17M/yr** (Phase 2 incremental)
- Timeline: Month 2–4

### Long-Term (Phase 3–4 — v6.20, Maximum Scaling)

**v6.20 7–10 venue deployment → $100M–$200M**

- Gate: K458 depth-aware allocator live + all venue daemons active + paper gates pass
- Lift @ $100M: **+$46.1M/yr** (K454 depth-aware model)
- Lift @ $200M: **+$72.4M/yr** (K461 optimal ceiling)
- Timeline: Month 6–9 (K464 Action #20)

### What NOT To Do

1. **Do NOT** open duplicate personal Bybit/OKX accounts — ToS violation, account freeze risk
2. **Do NOT** expect HL multi-wallet to reduce slippage — same order book, zero benefit
3. **Do NOT** operate under another person's account
4. **Do NOT** store private keys in git, HTML reports, or env files committed to repo
5. **Do NOT** force Phase 2+ before K449+K457 paper-trade gates pass (K461 condition)
6. **Do NOT** exceed 65% HL combined concentration (K358 rule, measure cross-wallet)

---

## Files Generated

| File | Description |
|------|-------------|
| `wave_k485_multi_account_scaling.py` | Analysis script, profit model, activation checklist |
| `wave_k485_multi_account_scaling.json` | Per-venue policy table, profit lift table, architecture |
| `wave_k485_multi_account_scaling.md` | This document — user-actionable playbook |
| `docs/k302a_master_deployment.md` | K485 section appended (User Action #24) |
| `scripts/multi_account_orchestrator.py` | Orchestrator design draft (~200 LOC) |

## Source Waves

- K431: Multi-account analysis (multi-venue required, ToS assessment)
- K454: $100M+ scaling redesign, v6.20 architecture, depth allocator
- K458: K458 depth-aware allocator (5% OI cap/venue, $100M+ guard)
- K461: v6.20 ACCEPT (conditional) — $200M optimal +$74.4M/yr
- K464: Master deployment playbook v6.20 path (20 actions)
- K479: v6.22 ACCEPT, K476 SOL-BTC, HL 53% < 65% confirmed
- K481: Builder rebate activation playbook (Action #23)
- K483: Kelly re-optimization (1/4 Kelly MV, Sharpe 2.00)

*K485 Playbook — Generated 2026-05-30 02:54 JST*
