# K743 LDO-ATOM FR Differential Alt-Alt Eval

**Wave**: K743
**Run time**: 2026-05-30 19:14:22 JST
**Decision**: **REJECT** — `MR9_STRICT_ALGEBRAIC_IDENTITY`
**Line status**: CLOSED

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
| Raw max_err | `2.1684e-19` | `1e-15` | **IDENTITY** |
| Smooth max_err | `5.4210e-20` | `1e-15` | **IDENTITY** |
| Signal identity err | `0.0000e+00` | `0` | **IDENTICAL** |
| Signal correlation | `1.000000` | — | **PERFECT** |
| Identity confirmed | `True` | — | **REJECT** |

### Data summary

- Rows: 17,484
- Date: 2024-05-24 – 2026-05-23  (1.99 yrs)
- LDO FR mean: 15.96%/yr
- ATOM FR mean: -3.27%/yr
- LDO-ATOM diff mean: 19.23%/yr
- Vol ratio LDO/ATOM: 0.5946

---

## Decision

**REJECT** — MR9 STRICT algebraic identity.

K743 LDO-ATOM is ALGEBRAICALLY IDENTICAL to K721 (LDO-SOL) minus K684 (ATOM-SOL). max_err = 2.17e-19 << 1e-15 threshold. Signal corr = 1.000000 (perfect). Deploying K743 alongside K721+K684 yields ZERO marginal alpha. Line CLOSED per MR9 STRICT enforcement. No backtest required — save tokens.

Backtest skipped. Tokens saved.

---

## MR9 Lesson L002 (K743)

**Pattern**: LDO-ATOM = K721_raw − K684_raw (3-token triangle collapse via SOL pivot)

**Generalisation**: In the alt-alt family using SOL as the dominant pivot, for any two tokens X and Y where (X-SOL) and (Y-SOL) are both already accepted:
> (X-Y) = (X-SOL) − (Y-SOL)  →  ALWAYS algebraically redundant.

### LDO-* pairs blocked by triangle rule (K721 LDO-SOL in family)

- LDO-ATOM (K743): K721 - K684 → CLOSED
- LDO-INJ: K721 - K684_INJ_SOL → CLOSED (if K684=SOL-INJ)
- LDO-TIA: K721 - K694 → CLOSED
- LDO-ENA: K721 - K696 → CLOSED
- LDO-BNB: K721 - K708 → CLOSED
- LDO-APT: K721 - K683 → CLOSED
- LDO-SEI: K721 - K690 → CLOSED
- LDO-AVAX: K721 - K687 → CLOSED
- LDO-HBAR: K721 - K735 → CLOSED (once K735 ACCEPT)
- LDO-FIL: K721 - K739 → CLOSED

### Recommended next candidates

- HBAR-ATOM: if K735 HBAR-SOL ACCEPTs, check HBAR-ATOM vs ATOM-SOL → if K684 in family → REJECT
- HBAR-TIA: same SOL-pivot check → likely BLOCKED if both in family
- FIL-ATOM: K739 FIL-SOL (ACCEPT) + K682 ATOM-SOL (ACCEPT) → FIL-ATOM BLOCKED
- FIL-TIA: K739 (FIL-SOL) + K694 (TIA-SOL) → FIL-TIA BLOCKED
- NEW TOKEN outside SOL-family: e.g., PENDLE, JUP, PYTH if not yet in family

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

*K339 REPO_ROOT | LIVE自動変更禁止 | 2026-05-30 19:14:22 JST*
