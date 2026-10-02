"""
Mahalanobis vs. Euclidean distance demo.

We generate a correlated 2D Gaussian cloud (rho = 0.9), then compare two
test points:
  - Point A: (1.0, -1.0)  small Euclidean distance, but it sits against
                            the grain of the cloud — a genuine outlier.
  - Point B: (3.0,  3.0)  large Euclidean distance, but it lies along the
                            cloud's main axis — consistent with the data.

Euclidean distance rates A as closer. Mahalanobis rates A as more unusual
under the stated covariance model and B as the more plausible point.
"""

from pathlib import Path

import numpy as np

# ── distribution parameters ───────────────────────────────────────────────
MEAN = np.array([0.0, 0.0])
COV  = np.array([[4.0, 3.6],
                 [3.6, 4.0]])   # sigma_x = sigma_y = 2, Pearson r = 0.9
RNG_SEED = 42
N_SAMPLES = 500

# ── helpers ───────────────────────────────────────────────────────────────

def euclidean(x: np.ndarray, mu: np.ndarray) -> float:
    """Standard Euclidean distance from point x to centre mu."""
    return float(np.linalg.norm(x - mu))


def mahalanobis(x: np.ndarray, mu: np.ndarray, sigma: np.ndarray) -> float:
    """
    Mahalanobis distance from x to distribution (mu, sigma).

    D_M(x) = sqrt((x - mu)^T  Sigma^{-1}  (x - mu))

    When Sigma = I, this reduces to the Euclidean distance.
    """
    x = np.asarray(x, dtype=float)
    mu = np.asarray(mu, dtype=float)
    sigma = np.asarray(sigma, dtype=float)

    if x.ndim != 1 or mu.ndim != 1 or x.shape != mu.shape:
        raise ValueError("x and mu must be one-dimensional vectors with the same shape")
    if sigma.shape != (x.size, x.size):
        raise ValueError("sigma must be a square matrix matching x and mu")
    if not np.allclose(sigma, sigma.T):
        raise ValueError("sigma must be symmetric")
    try:
        np.linalg.cholesky(sigma)
        solved = np.linalg.solve(sigma, x - mu)
    except np.linalg.LinAlgError as error:
        raise ValueError("sigma must be positive definite and non-singular") from error

    squared_distance = float((x - mu) @ solved)
    return float(np.sqrt(max(squared_distance, 0.0)))


def save_geometry_plot(
    cloud: np.ndarray,
    mean: np.ndarray,
    covariance: np.ndarray,
    points: dict[str, np.ndarray],
    output_path: str | Path = "mahalanobis-ellipse-comparison.png",
) -> Path:
    """Plot the correlated cloud, covariance contours, and comparison points."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Ellipse
    except ImportError as error:
        raise RuntimeError(
            "Plotting requires matplotlib; run: pip install -r requirements.txt"
        ) from error

    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))

    figure, axis = plt.subplots(figsize=(8, 6))
    axis.scatter(cloud[:, 0], cloud[:, 1], s=12, alpha=0.24, color="#64748b")
    for level, alpha in ((1, 0.55), (2, 0.35), (3, 0.2)):
        width, height = 2 * level * np.sqrt(eigenvalues)
        axis.add_patch(
            Ellipse(
                mean,
                width,
                height,
                angle=angle,
                fill=False,
                linewidth=2,
                alpha=alpha,
                color="#2563eb",
            )
        )

    colors = {"A": "#dc2626", "B": "#16a34a"}
    for label, point in points.items():
        axis.scatter(*point, s=100, color=colors[label], edgecolor="white", linewidth=1.5)
        axis.annotate(f"Point {label}", point, xytext=(8, 8), textcoords="offset points")

    axis.scatter(*mean, marker="x", s=100, linewidth=2, color="#111827", label="Mean")
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("Feature 1")
    axis.set_ylabel("Feature 2")
    axis.set_title("Euclidean closeness is not covariance-aware closeness")
    axis.grid(alpha=0.15)
    figure.tight_layout()

    destination = Path(output_path)
    figure.savefig(destination, dpi=180)
    plt.close(figure)
    return destination


# ── main ──────────────────────────────────────────────────────────────────

def main() -> None:
    rng = np.random.default_rng(RNG_SEED)
    cloud = rng.multivariate_normal(MEAN, COV, size=N_SAMPLES)

    print("=" * 56)
    print("  Mahalanobis vs. Euclidean distance demo")
    print("=" * 56)

    print("\nCovariance matrix (sigma_x = sigma_y = 2, r = 0.9):")
    print(COV)

    # Sample mean and sample covariance (should be close to true parameters)
    sample_mean = cloud.mean(axis=0)
    sample_cov  = np.cov(cloud.T)
    print(f"\nSample mean  : [{sample_mean[0]:+.4f}, {sample_mean[1]:+.4f}]")
    print(f"Sample cov   :\n{np.round(sample_cov, 4)}")

    test_points = {
        "A": np.array([1.0, -1.0]),
        "B": np.array([3.0, 3.0]),
    }

    print("\nDistances use the known mean and covariance that generated the cloud.")

    print("\n" + "-" * 56)
    print(f"{'Point':<38}  {'Euclidean':>10}  {'Mahalanobis':>12}")
    print("-" * 56)

    distances = {}
    descriptions = {"A": "against grain", "B": "with grain"}
    for label, pt in test_points.items():
        e = euclidean(pt, MEAN)
        m = mahalanobis(pt, MEAN, COV)
        distances[label] = (e, m)
        row_label = f"{label} ({pt[0]:>4.1f}, {pt[1]:>4.1f})  [{descriptions[label]}]"
        print(f"{row_label:<38}  {e:>10.4f}  {m:>12.4f}")

    print("-" * 56)

    print("\nVerdict")
    print("-------")
    eA, mA = distances["A"]
    eB, mB = distances["B"]

    eucl_closer = "A" if eA < eB else "B"
    mah_further = "A" if mA > mB else "B"

    print(f"  Euclidean says '{eucl_closer}' is closer.")
    print(f"  Mahalanobis rates '{mah_further}' as more unusual.")
    print()
    print("  Point A is only 1.41 units from the centre but cuts across")
    print("  the covariance axis — a direction the cloud almost never")
    print("  produces. Mahalanobis distance: 2.24.")
    print()
    print("  Point B is 4.24 units away but lies along the main axis")
    print("  of the ellipse. Mahalanobis distance: 1.54.")
    print()
    print("  Euclidean misses the covariance pattern. Mahalanobis uses it.")
    plot_path = save_geometry_plot(cloud, MEAN, COV, test_points)
    print(f"\n  Saved geometry plot: {plot_path}")
    print("=" * 56)


if __name__ == "__main__":
    main()
