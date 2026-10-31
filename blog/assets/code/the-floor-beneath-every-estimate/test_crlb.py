"""
Tests for crlb_demo.py.

Checks:
1. crlb() returns sigma^2/n (the theoretical value).
2. empirical_variance() stays close to the theoretical variance, allowing for
   Monte Carlo noise on either side of the bound.
3. The ratio empirical_var / CRLB converges toward 1.0 as n grows.
"""

import numpy as np
import pytest

# Import from the module under test
import importlib.util, pathlib, sys

_module_path = pathlib.Path(__file__).parent / "crlb_demo.py"
_spec = importlib.util.spec_from_file_location("crlb_demo", _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

crlb = _mod.crlb
empirical_variance = _mod.empirical_variance
empirical_variances = _mod.empirical_variances
SIGMA_SQ = _mod.SIGMA_SQ
N_TRIALS = _mod.N_TRIALS


# ── Unit tests ──────────────────────────────────────────────────────────────

def test_crlb_formula():
    """CRLB for Gaussian mean with known variance = sigma^2 / n."""
    assert crlb(1) == pytest.approx(SIGMA_SQ, rel=1e-10)
    assert crlb(10) == pytest.approx(SIGMA_SQ / 10, rel=1e-10)
    assert crlb(100) == pytest.approx(SIGMA_SQ / 100, rel=1e-10)


def test_crlb_strictly_positive():
    for n in [1, 5, 100, 1000]:
        assert crlb(n) > 0


def test_crlb_decreasing():
    """More data => tighter bound."""
    assert crlb(10) > crlb(100) > crlb(1000)


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError):
        crlb(0)
    with pytest.raises(ValueError):
        empirical_variances(0, np.random.default_rng(0))


def test_empirical_variance_not_suspiciously_below_bound():
    """
    A finite empirical variance may sit below the CRLB through simulation noise,
    but it should not be far below the theoretical value.
    """
    rng = np.random.default_rng(0)
    n = 100
    emp_var = empirical_variance(n, rng)
    bound = crlb(n)
    # Must not violate the bound beyond Monte Carlo noise
    assert emp_var >= bound * 0.97, (
        f"Empirical variance {emp_var:.6f} suspiciously below CRLB {bound:.6f}"
    )


def test_empirical_variance_not_wildly_off():
    """Sample mean is efficient -- empirical var should be close to CRLB."""
    rng = np.random.default_rng(1)
    n = 500
    emp_var = empirical_variance(n, rng)
    bound = crlb(n)
    ratio = emp_var / bound
    assert 0.98 <= ratio <= 1.05, (
        f"Ratio {ratio:.4f} outside expected [0.98, 1.05] — MLE efficiency check failed"
    )


def test_ratio_near_one_for_large_n():
    """
    For large n, the sample mean is efficient: empirical_var / CRLB should
    be within 2% of 1.0 (very tight with 100,000 Monte Carlo trials).
    """
    rng = np.random.default_rng(99)
    for n in [500, 1000]:
        ratio = empirical_variance(n, rng) / crlb(n)
        assert abs(ratio - 1.0) < 0.02, (
            f"n={n}: ratio {ratio:.4f} is more than 2% from 1.0; "
            "MLE should be near-efficient at this sample size"
        )


def test_wasteful_unbiased_estimator_stays_above_bound():
    rng = np.random.default_rng(7)
    mean_var, first_var = empirical_variances(20, rng, n_trials=50_000)
    assert mean_var == pytest.approx(crlb(20), rel=0.03)
    assert first_var == pytest.approx(SIGMA_SQ, rel=0.03)
    assert first_var > 15 * crlb(20)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
