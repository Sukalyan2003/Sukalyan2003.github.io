"""
Tests for the Mahalanobis vs. Euclidean distance demo.
"""

import math
import numpy as np
import pytest
from demo import euclidean, mahalanobis, MEAN, COV


def test_euclidean_identity():
    """Distance from a point to itself is zero."""
    assert euclidean(MEAN, MEAN) == pytest.approx(0.0)


def test_euclidean_known():
    """Simple 2D Euclidean check: (3, 4) from origin → 5."""
    assert euclidean(np.array([3.0, 4.0]), np.array([0.0, 0.0])) == pytest.approx(5.0)


def test_mahalanobis_identity():
    """Mahalanobis distance from centre to centre is zero."""
    assert mahalanobis(MEAN, MEAN, COV) == pytest.approx(0.0)


def test_mahalanobis_unit_covariance():
    """When cov = I, Mahalanobis == Euclidean."""
    identity = np.eye(2)
    pt = np.array([3.0, 4.0])
    mu = np.array([0.0, 0.0])
    assert mahalanobis(pt, mu, identity) == pytest.approx(euclidean(pt, mu))


def test_outlier_detection():
    """
    Core demo claim: Point A (1, -1) has larger Mahalanobis distance than
    Point B (3, 3), even though A has smaller Euclidean distance.
    """
    pt_a = np.array([ 1.0, -1.0])
    pt_b = np.array([ 3.0,  3.0])

    eA = euclidean(pt_a, MEAN)
    eB = euclidean(pt_b, MEAN)
    mA = mahalanobis(pt_a, MEAN, COV)
    mB = mahalanobis(pt_b, MEAN, COV)

    # A is closer in Euclidean terms
    assert eA < eB, f"Expected eA({eA:.4f}) < eB({eB:.4f})"

    # A is farther in Mahalanobis terms — the whole point of the demo
    assert mA > mB, f"Expected mA({mA:.4f}) > mB({mB:.4f})"


def test_mahalanobis_known_value():
    """
    For point (1, -1) with COV=[[4,3.6],[3.6,4]], cross-check against
    a manually derived value.

    cov_inv = 1/(det) * [[4, -3.6], [-3.6, 4]]
    det = 4*4 - 3.6*3.6 = 16 - 12.96 = 3.04
    diff = [1, -1]
    diff @ cov_inv @ diff = (1/3.04) * (1*(4*1 + (-3.6)*(-1)) + (-1)*((-3.6)*1 + 4*(-1)))
                           = (1/3.04) * (7.6 + 7.6) = 15.2/3.04 = 5.0
    distance = sqrt(5.0) ≈ 2.2361
    """
    pt = np.array([1.0, -1.0])
    expected = math.sqrt(5.0)
    result = mahalanobis(pt, MEAN, COV)
    assert result == pytest.approx(expected, rel=1e-5)


def test_invalid_covariance_rejected():
    point = np.array([1.0, 1.0])
    with pytest.raises(ValueError, match="positive definite"):
        mahalanobis(point, MEAN, np.array([[1.0, 1.0], [1.0, 1.0]]))
    with pytest.raises(ValueError, match="symmetric"):
        mahalanobis(point, MEAN, np.array([[1.0, 0.5], [0.0, 1.0]]))


def test_shape_mismatch_rejected():
    with pytest.raises(ValueError, match="same shape"):
        mahalanobis(np.array([1.0]), MEAN, COV)
    with pytest.raises(ValueError, match="square matrix"):
        mahalanobis(MEAN, MEAN, np.eye(3))
