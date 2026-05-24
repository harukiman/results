# Wave K239 — 3-Way Meta-Ensemble Validation (no K226)
*Generated: 2026-05-24T23:48:38.093351+00:00  |  Runtime: 0.16s*

## Verdict: REJECT — maintain K229d v6.8

**K237g finding**: dropping K226 from K229 raises OOS Sh 12.61 → 12.858.
**K239 objective**: formal validation with proper 3-way ensemble variants.

## 4-Variant Comparison Table

| Variant | Description | OOS Sh | MaxDD | WF Mean | WF Min | DR | K198/K204/K208 | Gate |
|---------|-------------|--------|-------|---------|--------|----|-----------------|------|
| K239a | Inv-vol weighted (30d rollin | 13.7295 | -0.001353 | 12.1662 | 6.8984 | 1.407 | 0.04/0.04/0.92 | **FAIL** |
| K239b | Inv-vol weighted (30d rollin | 11.0310 | -0.003640 | 8.3160 | 6.9282 | 1.079 | 0.39/0.32/0.30 | **FAIL** |
| K239c | Minimum Variance Portfolio ( | 15.2029 | -0.000062 | 11.8191 | 5.2333 | 1.289 | 0.01/0.01/0.98 | **FAIL** |
| K239d | Equal weight 33/33/33 | 11.1297 | -0.003456 | 8.2739 | 6.8540 | 1.082 | 0.33/0.33/0.33 | **FAIL** |

## vs K229d Reference

| Metric | K229d (4-way, with K226) | Best K239 | Delta |
|--------|--------------------------|-----------|-------|
| OOS Sharpe | 12.6100 | 15.2029 (K239c) | +2.5929 |
| WF Min | 7.4400 | 5.2333 | -2.2067 |
| WF Mean | 11.4250 | 11.8191 | +0.3941 |
| MaxDD | -0.001201 | -0.000062 | +0.001139 |
| Components | 4 | 3 | -1 (simpler) |

## Per-Fold Breakdown (best variant)

| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF Min | WF Mean |
|---------|--------|--------|--------|--------|--------|---------|
| K229d (ref) | 12.8545 | 7.4435 | 12.9221 | 12.4798 | 7.4435 | 11.4250 |
| K239c | 9.2182 | 5.2333 | 18.2913 | 14.5338 | 5.2333 | 11.8191 |

## All Variants Per-Fold

| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF Min |
|---------|--------|--------|--------|--------|--------|
| K239a | 12.2676 | 6.8984 | 15.9773 | 13.5214 | 6.8984 |
| K239b | 7.5144 | 6.9282 | 8.3475 | 10.4739 | 6.9282 |
| K239c | 9.2182 | 5.2333 | 18.2913 | 14.5338 | 5.2333 |
| K239d | 7.2789 | 6.8540 | 8.3844 | 10.5782 | 6.8540 |

## Verdict Line

**REJECT — no K239 variant meets K229d thresholds; maintain K229d v6.8**

Gates (vs K229d): OOS Sh >= 12.61 | WF Min >= 7.44 | MaxDD <= -0.001201

---
*Wave K239 | crypto-lab | 2026-05-24T23:48:38.093351+00:00*