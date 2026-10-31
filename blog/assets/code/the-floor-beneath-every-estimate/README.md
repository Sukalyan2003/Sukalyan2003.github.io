# Cramér–Rao Lower Bound - Monte Carlo Demo

Companion code for *"The Floor Beneath Every Estimate"* (Unsung Bits, post 06).

This is an **educational toy**, not production code. It empirically demonstrates the
Cramér–Rao lower bound: the hard floor on the variance of any unbiased estimator.

## What it does

**Model:** n i.i.d. observations from Normal(μ, σ²), with σ² = 1.0 known, μ unknown.

**Fisher information:** I(μ) = n / σ²  
**CRLB:** Var(μ̂) ≥ σ² / n  
**MLE:** sample mean μ̂ = (1/n) Σ Xᵢ, which achieves Var = σ²/n exactly.

The script runs 100,000 Monte Carlo trials for each sample size n, computes the
sample-mean MLE on every trial, measures the empirical variance of those estimates,
and compares it with an unbiased estimator that uses only the first observation.
The efficient sample mean should hover near the bound; the wasteful estimator
should remain far above it. Finite Monte Carlo estimates can fall on either side
of the true theoretical variance.

## Run command

```
python3 crlb_demo.py
```

## Real output (Python 3.12, numpy 2.4.6, seed 42)

```
Cramér–Rao Lower Bound - Monte Carlo Demo
Model: X ~ Normal(mu=3.7, sigma^2=1.0), mu unknown
Estimator: sample mean (MLE)   |   Trials per n: 100,000

     n        CRLB    Mean Var   Mean/Bound  First-X Var  First/Bound
---------------------------------------------------------------------
     5    0.200000    0.200851       1.0043     1.001149         5.01
    10    0.100000    0.099180       0.9918     1.006865        10.07
    20    0.050000    0.049961       0.9992     0.998617        19.97
    50    0.020000    0.020049       1.0024     0.994109        49.71
   100    0.010000    0.010021       1.0021     1.000740       100.07
   200    0.005000    0.004993       0.9986     0.998797       199.76
   500    0.002000    0.002008       1.0038     1.006028       503.01
  1000    0.001000    0.000998       0.9978     1.003978      1003.98
---------------------------------------------------------------------

Interpretation:
  The sample mean is efficient: its true variance equals the bound.
  Monte Carlo ratios can land slightly above or below 1.0.
  The first observation is unbiased but wastes data, so its ratio grows with n.
```

The sample-mean deviations are Monte Carlo noise from 100,000 finite trials,
not genuine bound violations. The CRLB constrains the estimator's true variance,
not every finite simulation estimate.

## Run tests

```
python3 -m pytest test_crlb.py -v
```

Expected output: 8 passed.

## Files

| File | Description |
|------|-------------|
| `crlb_demo.py` | Monte Carlo demo - main script |
| `test_crlb.py` | Pytest test suite (8 tests) |
| `requirements.txt` | numpy, pytest |

## Dependencies

```
pip install -r requirements.txt
```

Requires Python 3.9+ and numpy ≥ 1.24.
