# Kuṭṭaka (Pulveriser) - Aryabhata's algorithm, 499 CE

Educational Python 3 implementation of the **kuṭṭaka** ("pulveriser"), the
algorithm Aryabhata described in the *Āryabhaṭīya* (499 CE) for solving
linear indeterminate equations.

Solves: `ax − by = c`  (equivalently: `ax ≡ c (mod b)`)

## Run command

```
python3 kuttaka.py
```

No dependencies beyond the Python 3 standard library.

## Run tests

```
python3 test_kuttaka.py
```

Expected: `15 passed, 0 failed` (14 equations plus coefficient-recovery and
invalid-input checks).

---

## What the algorithm does

1. **Build the valli** - run the Euclidean algorithm on `a` and `b`, collecting
   the quotient at each step into a column called the *valli* (Sanskrit for
   "creeper" or "column").

2. **Backward induction** - fold upward through the valli to compute the
   numerators and denominators of the continued-fraction convergents of `a/b`.
   The penultimate convergent `h/k` satisfies `a·k − b·h = ±1` (Bézout's
   identity with gcd = 1 after reduction).

3. **Scale and reduce** - multiply by `c` and reduce modulo `b` to get the
   smallest non-negative `x₀`.

This is structurally identical to the extended Euclidean algorithm's
back-substitution. The kuṭṭaka is the Indian name for the same idea, arrived
at independently over a millennium earlier. Both produce the same result; the
cross-check in the demo confirms they agree on all four problems.

---

## Real output (pasted)

```
============================================================
  Kuṭṭaka (Pulveriser) - Aryabhata's algorithm, 499 CE
============================================================

────────────────────────────────────────────────────────────
  Problem: 137x − 60y = 10  (classic Indian mathematics example;
  general solution x = 50 + 60t, y = 114 + 137t)

============================================================
  Solving  137x − 60y = 10
  Equivalently: 137x ≡ 10 (mod 60)
============================================================

  Step 1 - Euclidean reduction (building the valli / quotient column):
  #    Division                        q   r
  --------------------------------------------------
  0    137 = 2×60 + 17           q=2      r=17
  1    60 = 3×17 + 9            q=3      r=9
  2    17 = 1×9 + 8            q=1      r=8
  3    9 = 1×8 + 1            q=1      r=1
  4    8 = 8×1 + 0            q=8      r=0

  Valli (quotient column, top to bottom): [2, 3, 1, 1, 8]

  Recovering Bézout coefficients from the remainder chain:
  17 = (1)×137 + (-2)×60
  9 = (-3)×137 + (7)×60
  8 = (4)×137 + (-9)×60
  1 = (-7)×137 + (16)×60

  Step 2 - Backward induction through the valli
  (computing numerator h and denominator k of convergents):
  i    q[i]   h (num)      k (den)
  --------------------------------------
  −1 - 1            0
  0    2      2            1
  1    3      7            3
  2    1      9            4
  3    1      16           7
  4    8      137          60

  Final convergent: 137/60 = 137/60  ✓
  Penultimate:      16/7
  Bézout check: 137×7 − 60×16 = -1  (= ±1 ✓)

  x₀ (raw) = 10 × -1 × 7 = -70
  x₀ (reduced mod 60) = -70 % 60 = 50
  y₀ = (137×50 − 10) / 60 = 114

  Particular solution to  137x − 60y = 10:
    x₀ = 50,  y₀ = 114
  Check: 137×50 − 60×114 = 10  ✓

  ── Cross-check ──────────────────────────────────────────
  Kuṭṭaka   : x=50, y=114  →  137×50 − 60×114 = 10  ✓
  Ext-Euclid: x=50, y=114  →  137×50 − 60×114 = 10  ✓
  Solutions agree up to free-parameter t (x differs by 0 × 60)  ✓

────────────────────────────────────────────────────────────
  Problem: 17x ≡ 1 (mod 5) - modular inverse of 17 mod 5
  (i.e. 17x − 5y = 1)

============================================================
  Solving  17x − 5y = 1
  Equivalently: 17x ≡ 1 (mod 5)
============================================================

  Step 1 - Euclidean reduction (building the valli / quotient column):
  #    Division                        q   r
  --------------------------------------------------
  0    17 = 3×5 + 2            q=3      r=2
  1    5 = 2×2 + 1            q=2      r=1
  2    2 = 2×1 + 0            q=2      r=0

  Valli (quotient column, top to bottom): [3, 2, 2]

  Step 2 - Backward induction through the valli
  (computing numerator h and denominator k of convergents):
  i    q[i]   h (num)      k (den)
  --------------------------------------
  −1 - 1            0
  0    3      3            1
  1    2      7            2
  2    2      17           5

  Final convergent: 17/5 = 17/5  ✓
  Penultimate:      7/2
  Bézout check: 17×2 − 5×7 = -1  (= ±1 ✓)

  x₀ (raw) = 1 × -1 × 2 = -2
  x₀ (reduced mod 5) = -2 % 5 = 3
  y₀ = (17×3 − 1) / 5 = 10

  Particular solution to  17x − 5y = 1:
    x₀ = 3,  y₀ = 10
  Check: 17×3 − 5×10 = 1  ✓

  ── Cross-check ──────────────────────────────────────────
  Kuṭṭaka   : x=3, y=10  →  17×3 − 5×10 = 1  ✓
  Ext-Euclid: x=3, y=10  →  17×3 − 5×10 = 1  ✓
  Solutions agree up to free-parameter t (x differs by 0 × 5)  ✓

────────────────────────────────────────────────────────────
  Problem: 7x − 11y = 10  (astronomical flavour:
  find day-count t = 7x+3 satisfying t ≡ 3 mod 7 AND t ≡ 2 mod 11;
  answer: t = 7×3+3 = 24)

  ...

============================================================
  All cross-checks passed: YES ✓
============================================================
```

## Test output (pasted)

```
Running kuṭṭaka tests...

  PASS  classic 137x−60y=10
  PASS  100x−63y=90
  PASS  modular inverse 17x≡1 mod 5
  PASS  astronomical 7x−11y=10
  PASS  3x−5y=1  →  x=2, y=1
  PASS  5x−3y=1  →  x=2, y=3
  PASS  trivial: 1x−1y=1  →  x=0,y=−1 - edge case
  PASS  gcd>1: 6x−4y=2  →  3x−2y=1  →  x=1
  PASS  no solution: gcd(6,4)=2 ∤ 3
  PASS  gcd=5: 15x−10y=25  →  3x−2y=5  →  x=1,y=−1
  PASS  2x−3y=1  →  x=2, y=1
  PASS  13x−7y=1  →  x=6, y=11
  PASS  99x≡1 mod 17
  PASS  1x−100y=99  →  x=99

  PASS  coefficient recovery and invalid-input checks

  15 passed, 0 failed.
```

## Note on historical fidelity

This implementation is a modern rendering of the algorithm's structure. The
historical kuttaka was described in verse (Sanskrit ślokas) and performed by
hand with tokens or sand-table arithmetic. The convergent-based interpretation
shown here is the mathematically equivalent modern formulation; the step-by-step
valli construction matches the spirit of the backward-induction the historical
texts describe.
