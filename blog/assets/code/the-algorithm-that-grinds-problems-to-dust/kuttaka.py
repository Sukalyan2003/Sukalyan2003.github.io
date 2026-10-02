"""
kuttaka.py — Aryabhata's kuṭṭaka ("pulveriser") for linear Diophantine equations.

Solves:  ax - by = c   (linear indeterminate / Diophantine equation)
    i.e. ax ≡ c (mod b)  (linear congruence)

The algorithm builds the Euclidean quotient sequence (the 'valli', or column),
then computes the penultimate continued-fraction convergent of a/b by folding
upward from the bottom of that column.  That convergent gives the coefficients
of Bézout's identity for (a, b), which are then scaled by c to produce a
particular solution.

This is structurally identical to the extended Euclidean algorithm's back-
substitution — the kuṭṭaka is the Indian name for essentially the same idea,
described by Aryabhata in 499 CE in the Āryabhaṭīya (Ganitapāda, verses 32–33)
and elaborated with worked examples by Bhāskara I in 628 CE.

Educational/toy implementation.  Not production-hardened.
"""

from math import gcd


# ─────────────────────────────────────────────────────────────────
# Core: the kuṭṭaka
# ─────────────────────────────────────────────────────────────────

def bezout_recovery_steps(a: int, b: int) -> list[tuple[int, int, int]]:
    """Return non-zero remainders as ``(r, s, t)`` where ``r = s*a + t*b``."""
    if a <= 0 or b <= 0:
        raise ValueError("a and b must be positive.")

    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    steps = []

    while r:
        quotient = old_r // r
        next_r = old_r - quotient * r
        next_s = old_s - quotient * s
        next_t = old_t - quotient * t
        if next_r:
            steps.append((next_r, next_s, next_t))
        old_r, r = r, next_r
        old_s, s = s, next_s
        old_t, t = t, next_t

    # If one input divides the other, the first Euclidean step has remainder 0.
    if not steps:
        steps.append((old_r, old_s, old_t))
    return steps


def kuttaka(a: int, b: int, c: int, *, verbose: bool = True) -> tuple[int, int] | None:
    """
    Solve  ax - by = c  for integers x, y  (a, b > 0).

    Equivalently: find the smallest non-negative x such that  ax ≡ c (mod b).

    Returns (x0, y0) — a particular solution — or None if no integer solution
    exists (i.e., gcd(a, b) does not divide c).

    General solution:  x = x0 + (b/g)*t,  y = y0 + (a/g)*t  for any integer t.
    """
    if a <= 0 or b <= 0:
        raise ValueError("a and b must be positive.")

    g = gcd(a, b)
    if c % g != 0:
        if verbose:
            print(f"  No integer solution: gcd({a}, {b}) = {g} does not divide {c}.")
        return None

    # Reduce to a primitive equation  A·x - B·y = C  with gcd(A, B) = 1
    A, B, C = a // g, b // g, c // g

    if verbose:
        print(f"\n{'='*60}")
        print(f"  Solving  {a}x − {b}y = {c}")
        if g > 1:
            print(f"  gcd({a},{b}) = {g}; reduce to  {A}x − {B}y = {C}")
        print(f"  Equivalently: {a}x ≡ {c} (mod {b})")
        print(f"{'='*60}")

    # ── Step 1: Build the valli (quotient column) ─────────────────
    # Run the Euclidean algorithm on (A, B), collecting quotients
    # until the remainder hits 0.  This is the "pulverising" phase —
    # grinding A and B down to 1 (their gcd, since we already reduced).
    quotients = []
    aa, bb = A, B
    if verbose:
        print("\n  Step 1 — Euclidean reduction (building the valli / quotient column):")
        print(f"  {'#':<4} {'Division':<28} {'q':>4}   {'r'}")
        print(f"  {'-'*50}")
    step = 0
    while bb > 0:
        q, r = divmod(aa, bb)
        if verbose:
            print(f"  {step:<4} {aa} = {q}×{bb} + {r:<10}   q={q:<5}  r={r}")
        quotients.append(q)
        aa, bb = bb, r
        step += 1

    if verbose:
        print(f"\n  Valli (quotient column, top to bottom): {quotients}")

        print("\n  Recovering Bézout coefficients from the remainder chain:")
        for remainder, a_coefficient, b_coefficient in bezout_recovery_steps(A, B):
            print(
                f"  {remainder} = ({a_coefficient})×{A} + "
                f"({b_coefficient})×{B}"
            )

    # ── Step 2: Backward induction — compute the penultimate convergent ──
    # The continued-fraction convergents h_k/k_k of A/B satisfy:
    #   A · k_{n-2} - B · h_{n-2} = (-1)^{n-1}   (Bézout's identity)
    # where n = len(quotients) and the final convergent is h_{n-1}/k_{n-1} = A/B.
    #
    # We compute k_{n-2} (denominator of penultimate convergent) bottom-up:
    #   k_{-1} = 0,  k_0 = 1
    #   k_i = q[i] * k_{i-1} + k_{i-2}
    # This is the "fold upward" through the valli that the kuttaka describes.
    # Simultaneously, h_{n-2} (numerator) follows the same recurrence seeded
    # with h_{-1}=1, h_0=q[0].

    if verbose:
        print(f"\n  Step 2 — Backward induction through the valli")
        print(f"  (computing numerator h and denominator k of convergents):")
        print(f"  {'i':<4} {'q[i]':<6} {'h (num)':<12} {'k (den)'}")
        print(f"  {'-'*38}")

    h_prev, h_curr = 1, quotients[0]
    k_prev, k_curr = 0, 1
    if verbose:
        print(f"  {'−1':<4} {'—':<6} {h_prev:<12} {k_prev}")
        print(f"  {'0':<4} {quotients[0]:<6} {h_curr:<12} {k_curr}")
    for i in range(1, len(quotients)):
        h_prev, h_curr = h_curr, quotients[i] * h_curr + h_prev
        k_prev, k_curr = k_curr, quotients[i] * k_curr + k_prev
        if verbose:
            print(f"  {i:<4} {quotients[i]:<6} {h_curr:<12} {k_curr}")

    # Final convergent: h_curr = A, k_curr = B  (sanity check)
    # Penultimate convergent: h_prev, k_prev
    sign = A * k_prev - B * h_prev   # = (-1)^(n-1), either +1 or -1
    if verbose:
        print(f"\n  Final convergent: {h_curr}/{k_curr} = {A}/{B}  ✓")
        print(f"  Penultimate:      {h_prev}/{k_prev}")
        print(f"  Bézout check: {A}×{k_prev} − {B}×{h_prev} = {sign}  (= ±1 ✓)")

    # ── Step 3: Scale and reduce ──────────────────────────────────
    # A * k_prev - B * h_prev = sign  →  multiply both sides by C*sign:
    # A*(C*sign*k_prev) - B*(C*sign*h_prev) = C
    # So x0_raw = C * sign * k_prev, y0_raw = C * sign * h_prev
    x0_raw = C * sign * k_prev
    x0 = x0_raw % B               # reduce to [0, B)
    y0 = (A * x0 - C) // B

    if verbose:
        print(f"\n  x₀ (raw) = {C} × {sign} × {k_prev} = {x0_raw}")
        print(f"  x₀ (reduced mod {B}) = {x0_raw} % {B} = {x0}")
        print(f"  y₀ = ({A}×{x0} − {C}) / {B} = {y0}")
        check = A * x0 - B * y0
        print(f"\n  Particular solution to  {A}x − {B}y = {C}:")
        print(f"    x₀ = {x0},  y₀ = {y0}")
        print(f"  Check: {A}×{x0} − {B}×{y0} = {check}  "
              f"{'✓' if check == C else '✗ ERROR'}")

    if verbose and g > 1:
        orig = a * x0 - b * y0
        print(f"\n  Original scale: {a}×{x0} − {b}×{y0} = {orig}"
              f"  {'✓' if orig == c else '✗ ERROR'}")

    return x0, y0


# ─────────────────────────────────────────────────────────────────
# Cross-check: extended Euclidean algorithm (independent method)
# ─────────────────────────────────────────────────────────────────

def _ext_gcd(a: int, b: int) -> tuple[int, int, int]:
    """Return (g, x, y) with a*x + b*y = g = gcd(a, b)."""
    if b == 0:
        return a, 1, 0
    g, x1, y1 = _ext_gcd(b, a % b)
    return g, y1, x1 - (a // b) * y1


def extended_euclid_solve(a: int, b: int, c: int) -> tuple[int, int] | None:
    """
    Solve  ax - by = c  using extended Euclidean back-substitution.
    Returns canonical (x0, y0) with 0 ≤ x0 < b/gcd(a,b), or None.
    Used only as an independent cross-check of the kuṭṭaka result.
    """
    if a <= 0 or b <= 0:
        raise ValueError("a and b must be positive.")
    g, px, py = _ext_gcd(a, b)   # a*px + b*py = g
    if c % g != 0:
        return None
    B = b // g
    # a*(px*(c/g)) + b*(py*(c/g)) = c  but we want ax - by = c
    # so x_raw = px*(c/g),  and y_raw = -py*(c/g)
    x_raw = px * (c // g)
    x0 = x_raw % B
    y0 = (a * x0 - c) // b
    return x0, y0


def cross_check(
    a: int, b: int, c: int,
    k_result: tuple[int, int] | None,
    e_result: tuple[int, int] | None,
    verbose: bool = True,
) -> bool:
    """Confirm both methods return valid solutions to ax − by = c."""
    if verbose:
        print(f"\n  ── Cross-check ──────────────────────────────────────────")
    all_ok = True
    for label, result in [("Kuṭṭaka   ", k_result), ("Ext-Euclid", e_result)]:
        if result is None:
            if verbose:
                print(f"  {label}: No solution returned")
            all_ok = False
            continue
        x, y = result
        lhs = a * x - b * y
        ok = (lhs == c)
        if verbose:
            print(f"  {label}: x={x}, y={y}  →  {a}×{x} − {b}×{y} = {lhs}"
                  f"  {'✓' if ok else '✗ ERROR'}")
        all_ok = all_ok and ok

    if verbose and k_result and e_result:
        g = gcd(a, b)
        step_x = b // g
        diff = k_result[0] - e_result[0]
        if step_x and diff % step_x == 0:
            print(f"  Solutions agree up to free-parameter t "
                  f"(x differs by {diff // step_x} × {step_x})  ✓")
        else:
            print(f"  Both satisfy the equation ✓")
    return all_ok


# ─────────────────────────────────────────────────────────────────
# Demo
# ─────────────────────────────────────────────────────────────────

def run_demo() -> None:
    print("=" * 60)
    print("  Kuṭṭaka (Pulveriser) — Aryabhata's algorithm, 499 CE")
    print("=" * 60)

    # Equations are  ax − by = c  with a, b > 0
    problems = [
        (
            137, 60, 10,
            "137x − 60y = 10  (classic Indian mathematics example;\n"
            "  general solution x = 50 + 60t, y = 114 + 137t)"
        ),
        (
            100, 63, 90,
            "100x − 63y = 90  (from Indian mathematics literature)"
        ),
        (
            17, 5, 1,
            "17x ≡ 1 (mod 5)  — modular inverse of 17 mod 5\n"
            "  (i.e. 17x − 5y = 1)"
        ),
        (
            # Astronomical flavour:
            # Find the day-count t satisfying t ≡ 3 (mod 7) and t ≡ 2 (mod 11).
            # t = 7x + 3, so 7x + 3 ≡ 2 (mod 11) → 7x ≡ 10 (mod 11)
            # → 7x − 11y = 10
            7, 11, 10,
            "7x − 11y = 10  (astronomical flavour:\n"
            "  find day-count t = 7x+3 satisfying t ≡ 3 mod 7 AND t ≡ 2 mod 11;\n"
            "  answer: t = 7×3+3 = 24)"
        ),
    ]

    all_ok = True
    for a, b, c, desc in problems:
        print(f"\n{'─'*60}")
        print(f"  Problem: {desc}")
        k_result = kuttaka(a, b, c, verbose=True)
        e_result = extended_euclid_solve(a, b, c)
        ok = cross_check(a, b, c, k_result, e_result, verbose=True)
        all_ok = all_ok and ok

    print(f"\n{'='*60}")
    print(f"  All cross-checks passed: {'YES ✓' if all_ok else 'NO — see errors above'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_demo()
