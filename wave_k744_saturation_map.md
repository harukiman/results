# K744 Alt-Alt Family Saturation Map (MR9 L002 SOL-Pivot Triangle)

**Wave**: K744
**Run time**: 2026-05-30 19:24:05 JST
**K339 REPO_ROOT**: /Users/nekonaomichi/crypto-lab
**LIVE changes**: NONE — read-only analysis

---

## Executive Summary

After K743 LDO-ATOM was auto-rejected as `K721_raw − K684_raw` (max_err=2.17e-19),
K744 formally characterises the algebraic saturation of the 14-member alt-alt family.

**Key findings:**
- Vertex set V = 12 tokens, all connected to SOL via X-SOL pivot legs
- 66 total C(12,2) pairs: 14 ACCEPT | 1 REJECT | 51 BLOCKED_SOL_TRIANGLE | 0 FREE internal
- **Saturation: 100.0%** of all vertex-pair space is consumed
- Maximum algebraically independent pairs for 12 vertices = **11** (spanning tree bound)
- **Zero internal FREE pairs remain** — expansion requires adding a new vertex W ∉ V
- Top candidate: **ONDO-SOL** (wave K745)

---

## Phase 1: Family Inventory (14 Members)

| Wave | Pair | A | B | OOS Sharpe | Decision |
|------|------|---|---|-----------|---------|
| K683 | APT-SOL | APT | SOL | 39.3 | ACCEPT |
| K684 | ATOM-SOL | ATOM | SOL | 43.4 | ACCEPT |
| K686 | SOL-INJ | SOL | INJ | 50.3 | ACCEPT |
| K687 | AVAX-SOL | AVAX | SOL | 50.3 | ACCEPT |
| K689 | SEI-SOL | SEI | SOL | 35.0 | ACCEPT |
| K694 | TIA-SOL | TIA | SOL | 19.1 | ACCEPT |
| K696 | ENA-SOL | ENA | SOL | 26.9 | ACCEPT |
| K700 | BNB-SOL | BNB | SOL | 48.6 | ACCEPT |
| K719 | ENA-ATOM | ENA | ATOM | 29.7 | ACCEPT |
| K721 | LDO-SOL | LDO | SOL | 46.8 | ACCEPT COND |
| K728 | INJ-ATOM | INJ | ATOM | 18.8 | ACCEPT |
| K735 | HBAR-SOL | HBAR | SOL | N/A | IN_PROGRESS |
| K736 | TIA-AVAX | TIA | AVAX | 13.0 | ACCEPT |
| K739 | FIL-SOL | FIL | SOL | 23.4 | ACCEPT |

**Vertex set V** (12 tokens): APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA

**SOL-pivot tokens** (have X-SOL in family): APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, TIA

**Non-SOL edges** (K719, K728, K736 — themselves derivable from SOL-pivot pairs):
ENA-ATOM, INJ-ATOM, TIA-AVAX

---

## Phase 2: Algebraic Saturation Matrix (66 Pairs)

| Status | Count | % of 66 |
|--------|-------|---------|
| ACCEPT | 14 | 21.2% |
| REJECT_K740 | 1 | 1.5% |
| BLOCKED_SOL_TRIANGLE | 51 | 77.3% |
| FREE | 0 | 0.0% |

### SOL-Pivot Triangle Rule (MR9 L002)

For any X, Y ∈ V where both X-SOL and Y-SOL are in the family:

```
(X-Y)_raw = (X-SOL)_raw − (Y-SOL)_raw
max_err < 1e-15 (machine precision)
```

**51 pairs blocked** by this rule (all pairs X-Y where X,Y both have SOL-pivot legs).

### Non-SOL Edges Are Also SOL-Derivable

The 3 non-SOL edges in the family are themselves SOL-triangle results:
- K719 ENA-ATOM = K696(ENA-SOL) − K684(ATOM-SOL)
- K728 INJ-ATOM = K686(SOL-INJ, reversed) − K684(ATOM-SOL)
- K736 TIA-AVAX = K694(TIA-SOL) − K687(AVAX-SOL)

This means they add **zero additional algebraic degrees of freedom** beyond the SOL-pivot span.

---

## Phase 3: Genuinely Independent Candidate Set

**Internal FREE pairs: 0**

All 12 vertices are SOL-pivot spanned. The current 12-vertex family is algebraically COMPLETE:
every vertex V has a SOL-pivot leg → all C(12,2)=66 internal pairs are consumed.

**Spanning tree bound**: Max independent pairs = |V| − 1 = 11.
The family has 14 members → 3 linearly dependent
members (K719/K728/K736, which were accepted due to strategy-level independence, not raw-level).

### Expansion Strategy

The ONLY path to genuinely new alpha from this family is to introduce **new vertex W ∉ V**:
1. Test **W-SOL** first → 1 new independent degree of freedom
2. Once W-SOL ACCEPTED: all W-X (X ∈ sol_pivot) become BLOCKED by extended triangle rule
3. Exception: W-AVAX or W-ATOM can be tested BEFORE W-SOL is accepted
4. Cluster independence of W from all 12 existing vertices = primary pre-screen filter

---

## Phase 4: Candidate Vertex Ranking (Top 10 W)

**Scoring**: composite = vol_ratio × cycle_indep × (1 + fr_amp_factor)

| Rank | Token | Vol Ratio/SOL | Corr/SOL | Cycle Indep | FR Amp | Score |
|------|-------|--------------|---------|------------|--------|-------|
| 1 | ONDO | 1.421 | 0.268 | 0.732 | 20.6%/yr | 2.1123 |
| 2 | TAO | 1.573 | 0.409 | 0.591 | 17.9%/yr | 1.7627 |
| 3 | WLD | 1.129 | 0.280 | 0.720 | 18.3%/yr | 1.5557 |
| 4 | PENDLE | 1.106 | 0.193 | 0.807 | 14.0%/yr | 1.5186 |
| 5 | PYTH | 1.153 | 0.269 | 0.731 | 14.5%/yr | 1.4532 |
| 6 | PEPE | 1.239 | 0.411 | 0.589 | 17.0%/yr | 1.3495 |
| 7 | AAVE | 0.797 | 0.021 | 0.979 | 13.0%/yr | 1.2882 |
| 8 | WIF | 1.347 | 0.487 | 0.513 | 14.6%/yr | 1.1944 |
| 9 | JUP | 0.849 | 0.250 | 0.750 | 16.6%/yr | 1.1649 |
| 10 | BONK | 1.315 | 0.520 | 0.480 | 15.8%/yr | 1.1308 |

**Governance-blocked** (K532 v5 closed lines): DOT, ARB, ALGO, NEAR

### First Pair Recommendation

**ONDO-SOL** (Wave K745)

ONDO has raw_corr(SOL)=0.268 ≤ 0.4. Test ONDO-SOL first — direct SOL-pivot extension. vol_ratio(ONDO/SOL)=1.421

---

## Phase 5: ROI Projections (K523 3-Point Mandatory)

@$10M @1% sleeve. K523 haircuts: R2S=0.38, OOS=25%, fee=15%.
Upper bound = gross_est (NOT central estimate per K523 rule).

| Pair | Conservative | Central | Optimistic | Upper Bound |
|------|-------------|---------|-----------|------------|
| ONDO-SOL | $59,625 | $104,606 | $135,988 | $246,131 |
| TAO-SOL | $60,642 | $106,389 | $138,306 | $250,328 |
| WLD-SOL | $47,026 | $82,501 | $107,251 | $194,120 |
| PENDLE-SOL | $48,419 | $84,946 | $110,429 | $199,872 |
| PYTH-SOL | $48,327 | $84,784 | $110,219 | $199,492 |
| PEPE-SOL | $47,703 | $83,690 | $108,797 | $196,918 |
| AAVE-SOL | $38,218 | $67,049 | $87,164 | $157,762 |
| WIF-SOL | $49,370 | $86,615 | $112,599 | $203,799 |
| JUP-SOL | $35,994 | $63,148 | $82,093 | $148,584 |
| BONK-SOL | $47,153 | $82,725 | $107,543 | $194,648 |

### Wave Priority Queue K745–K754

| Wave | Pair | Central $/yr | Rationale |
|------|------|-------------|-----------|
| K745 | ONDO-SOL | $104,606 | vol_ratio=1.421, cycle_indep=0.732, score=2.1123 |
| K746 | TAO-SOL | $106,389 | vol_ratio=1.573, cycle_indep=0.591, score=1.7627 |
| K747 | WLD-SOL | $82,501 | vol_ratio=1.129, cycle_indep=0.720, score=1.5557 |
| K748 | PENDLE-SOL | $84,946 | vol_ratio=1.106, cycle_indep=0.807, score=1.5186 |
| K749 | PYTH-SOL | $84,784 | vol_ratio=1.153, cycle_indep=0.731, score=1.4532 |
| K750 | PEPE-SOL | $83,690 | vol_ratio=1.239, cycle_indep=0.589, score=1.3495 |
| K751 | AAVE-SOL | $67,049 | vol_ratio=0.797, cycle_indep=0.979, score=1.2882 |
| K752 | WIF-SOL | $86,615 | vol_ratio=1.347, cycle_indep=0.513, score=1.1944 |
| K753 | JUP-SOL | $63,148 | vol_ratio=0.849, cycle_indep=0.750, score=1.1649 |
| K754 | BONK-SOL | $82,725 | vol_ratio=1.315, cycle_indep=0.480, score=1.1308 |

---

## Phase 6: MR9 L002 SOL-Pivot Triangle Rule (Formal Memo)

### Theorem

THEOREM (SOL-Pivot Triangle Rule): Let F be an alt-alt family using SOL as a dominant pivot token. If both (X-SOL) ∈ F and (Y-SOL) ∈ F, then (X-Y)_raw = (X-SOL)_raw − (Y-SOL)_raw identically (machine precision, max_err < 1e-15). Therefore, the pair (X-Y) carries ZERO marginal alpha beyond {F} and MUST be rejected at MR9 pre-check without backtest.

### Proof

Let X_fr, Y_fr, S_fr denote funding-rate time series. (X-Y)_raw = X_fr − Y_fr. (X-SOL)_raw = X_fr − S_fr. (Y-SOL)_raw = Y_fr − S_fr. (X-SOL)_raw − (Y-SOL)_raw = (X_fr − S_fr) − (Y_fr − S_fr) = X_fr − Y_fr = (X-Y)_raw. QED. Numerical confirmation: K743 LDO-ATOM max_err = 2.17e-19 << 1e-15 (K743, 2026-05-30).

### Generalisation

The rule applies to ANY 3 tokens A, B, C where two of the three pair differentials are already in the family. In general: for any graph G on vertices V where signal(u-v) = fr_u − fr_v, the signal space has dimension |V|−1 (spanning tree). Adding more than |V|−1 edges introduces linear dependencies. The SOL-pivot family with 12 vertices can support at most 11 algebraically independent pairs. The current 14-member family has 3 linearly dependent members (K719 ENA-ATOM, K728 INJ-ATOM, K736 TIA-AVAX) which were accepted because their SIGNAL correlation differs (strategy uses sign thresholding + smoothing), but at raw differential level they ARE dependent.

### Family Saturation Statistics

| Metric | Value |
|--------|-------|
| Vertices \|V\| | 12 |
| Max independent pairs (spanning tree) | 11 |
| Current family members | 14 |
| Total C(12,2) pairs | 66 |
| Blocked (SOL triangle) | 51 |
| Accept | 14 |
| Reject K740 | 1 |
| Free internal | 0 |
| Saturation % | 100.0% |

### Expansion Strategy

To generate genuinely new alpha from this family: (1) Add new vertex W ∉ V. Test W-SOL first. (2) Once W-SOL ACCEPT: W-X for all X∈sol_pivot are BLOCKED.     Do NOT test W-ATOM, W-INJ, W-TIA etc. after W-SOL ACCEPT. (3) Exception: W-AVAX or W-ATOM if W-SOL is NOT in family.     This preserves independence until the SOL leg is added. (4) Cluster independence of W from all 12 existing vertices     is the primary filter — meta-narrative overlap trumps G5 corr.

### MR9 Update

**Lesson**: Signal correlation ≠ algebraic independence. K721 (LDO-SOL) × K684 (ATOM-SOL) signal corr = 0.133 (low), yet K743 (LDO-ATOM) = K721_raw − K684_raw EXACTLY. MR9 STRICT checks algebraic identity (raw FR), NOT signal correlation. Use spanning-tree counting: with 12 vertices, max 11 independent pairs.

**First confirmed**: K743 LDO-ATOM (2026-05-30)
**Extended by**: K744 (2026-05-30) — full family saturation map

---

## Deliverables

- `wave_k744_saturation_map.py` — K339 analysis script
- `wave_k744_saturation_map.json` — full matrix + candidate rankings
- `wave_k744_saturation_map.md` — this insight document
- `data/alt_alt_saturation_matrix.csv` — 66-row BLOCKED/FREE matrix
- `report.html` — K744 badge

---

*K339 REPO_ROOT | LIVE自動変更禁止 | 2026-05-30 19:24:05 JST*
