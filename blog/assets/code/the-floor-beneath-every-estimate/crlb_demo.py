"""
Cramér–Rao Lower Bound — Monte Carlo demonstration.

Model: X_1, ..., X_n  i.i.d. ~ Normal(mu, sigma^2), sigma^2 known.
Parameter of interest: mu (the true mean).

Fisher information for mu with known sigma^2:
    I(mu) = n / sigma^2   (for n observations)

CRLB: Var(mu_hat) >= sigma^2 / n

The MLE is the sample mean: mu_hat = (1/n) * sum(X_i).
Var(sample mean) = sigma^2 / n  -- exactly achieves the CRLB.

This script draws many Monte Carlo samples for each n, computes the
sample-mean MLE on each, measures the empirical variance, and shows
that the efficient estimator tracks the CRLB while a wasteful unbiased
estimator remains above it. Finite Monte Carlo estimates may fluctuate on
either side of the true bound.

Educational toy -- not production code.
"""

import numpy as np

RNG_SEED = 42
N_TRIALS = 100_000   # Monte Carlo repetitions per sample size
TRUE_MU = 3.7        # arbitrary; CRLB doesn't depend on it
SIGMA_SQ = 1.0       # known variance; CRLB = sigma^2 / n
SIGMA = np.sqrt(SIGMA_SQ)

SAMPLE_SIZES = [5, 10, 20, 50, 100, 200, 500, 1000]


def crlb(n: int) -> float:
    """Cramér–Rao lower bound on Var(mu_hat) for n i.i.d. Normal obs."""
    if n <= 0:
        raise ValueError("n must be positive")
    return SIGMA_SQ / n


def empirical_variances(
    n: int,
    rng: np.random.Generator,
    *,
    n_trials: int = N_TRIALS,
    batch_size: int = 5_000,
) -> tuple[float, float]:
    """
    Return variances for the sample mean and the first observation.

    Both estimators are unbiased. The first observation deliberately discards
    n-1 values, so its variance is sigma^2 instead of sigma^2/n. Sampling in
    batches avoids allocating an N_TRIALS-by-n array for large n.
    """
    if n <= 0 or n_trials <= 0 or batch_size <= 0:
        raise ValueError("n, n_trials, and batch_size must be positive")

    means = []
    first_observations = []
    remaining = n_trials
    while remaining:
        current_batch = min(batch_size, remaining)
        data = rng.normal(loc=TRUE_MU, scale=SIGMA, size=(current_batch, n))
        means.append(data.mean(axis=1))
        first_observations.append(data[:, 0])
        remaining -= current_batch

    return (
        float(np.concatenate(means).var(ddof=0)),
        float(np.concatenate(first_observations).var(ddof=0)),
    )


def empirical_variance(n: int, rng: np.random.Generator) -> float:
    """Backward-compatible wrapper returning the sample-mean variance."""
    return empirical_variances(n, rng)[0]


def main() -> None:
    rng = np.random.default_rng(RNG_SEED)

    header = (
        f"{'n':>6}  {'CRLB':>10}  {'Mean Var':>10}  {'Mean/Bound':>11}  "
        f"{'First-X Var':>11}  {'First/Bound':>11}"
    )
    sep = "-" * len(header)
    print("Cramér–Rao Lower Bound — Monte Carlo Demo")
    print(f"Model: X ~ Normal(mu={TRUE_MU}, sigma^2={SIGMA_SQ:.1f}), mu unknown")
    print(f"Estimator: sample mean (MLE)   |   Trials per n: {N_TRIALS:,}")
    print()
    print(header)
    print(sep)

    for n in SAMPLE_SIZES:
        bound = crlb(n)
        mean_var, first_var = empirical_variances(n, rng)
        print(
            f"{n:>6}  {bound:>10.6f}  {mean_var:>10.6f}  "
            f"{mean_var / bound:>11.4f}  {first_var:>11.6f}  "
            f"{first_var / bound:>11.2f}"
        )

    print(sep)
    print()
    print("Interpretation:")
    print("  The sample mean is efficient: its true variance equals the bound.")
    print("  Monte Carlo ratios can land slightly above or below 1.0.")
    print("  The first observation is unbiased but wastes data, so its ratio grows with n.")


if __name__ == "__main__":
    main()
