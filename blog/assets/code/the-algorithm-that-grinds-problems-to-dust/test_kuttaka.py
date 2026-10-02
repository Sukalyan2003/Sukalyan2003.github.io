"""
test_kuttaka.py — small regression suite for kuttaka.py

Run with:  python3 test_kuttaka.py
"""

import sys
from math import gcd
from kuttaka import bezout_recovery_steps, kuttaka, extended_euclid_solve


def check(a: int, b: int, c: int, expected_x: int = None) -> bool:
    """
    Solve ax − by = c with both methods; assert both solutions are valid.
    If expected_x is given, also assert the kuṭṭaka returns that x value.
    """
    k = kuttaka(a, b, c, verbose=False)
    e = extended_euclid_solve(a, b, c)

    g = gcd(a, b)
    if c % g != 0:
        # No solution expected
        assert k is None, f"kuttaka should return None for {a}x−{b}y={c}"
        assert e is None, f"ext_euclid should return None for {a}x−{b}y={c}"
        return True

    assert k is not None, f"kuttaka returned None for {a}x−{b}y={c}"
    assert e is not None, f"ext_euclid returned None for {a}x−{b}y={c}"

    kx, ky = k
    ex, ey = e

    assert a * kx - b * ky == c, (
        f"Kuṭṭaka wrong: {a}×{kx} − {b}×{ky} = {a*kx - b*ky}, expected {c}"
    )
    assert a * ex - b * ey == c, (
        f"Ext-Euclid wrong: {a}×{ex} − {b}×{ey} = {a*ex - b*ey}, expected {c}"
    )

    # Solutions must agree up to the free parameter (differ by a multiple of b/g)
    step = b // g
    assert (kx - ex) % step == 0, (
        f"Solutions differ by non-multiple of {step}: kx={kx}, ex={ex}"
    )

    if expected_x is not None:
        assert kx == expected_x, (
            f"Expected x={expected_x}, got x={kx} for {a}x−{b}y={c}"
        )

    return True


def test_run_tests() -> None:
    cases = [
        # (a, b, c, expected_x, description)
        (137,  60,  10,  50,  "classic 137x−60y=10"),
        (100,  63,  90,  45,  "100x−63y=90"),
        (17,    5,   1,   3,  "modular inverse 17x≡1 mod 5"),
        (7,    11,  10,   3,  "astronomical 7x−11y=10"),
        (3,    5,   1,   2,  "3x−5y=1  →  x=2, y=1"),
        (5,    3,   1,   2,  "5x−3y=1  →  x=2, y=3"),
        (1,    1,   1,   0,  "trivial: 1x−1y=1  →  x=0,y=−1 — edge case"),
        (6,    4,   2,   1,  "gcd>1: 6x−4y=2  →  3x−2y=1  →  x=1"),
        (6,    4,   3,  None, "no solution: gcd(6,4)=2 ∤ 3"),
        (15,  10,  25,   1,  "gcd=5: 15x−10y=25  →  3x−2y=5  →  x=1,y=−1"),
        (2,    3,   1,   2,  "2x−3y=1  →  x=2, y=1"),
        (13,   7,   1,   6,  "13x−7y=1  →  x=6, y=11"),
        (99,  17,   1,  None, "99x≡1 mod 17"),  # don't fix expected, just verify valid
        (1,  100,  99,  99,  "1x−100y=99  →  x=99"),
    ]

    passed = 0
    failed = 0
    for a, b, c, expected_x, desc in cases:
        try:
            check(a, b, c, expected_x)
            print(f"  PASS  {desc}")
            passed += 1
        except AssertionError as err:
            print(f"  FAIL  {desc}")
            print(f"        {err}")
            failed += 1

    try:
        check_coefficient_recovery_and_validation()
        print("  PASS  coefficient recovery and invalid-input checks")
        passed += 1
    except AssertionError as err:
        print("  FAIL  coefficient recovery and invalid-input checks")
        print(f"        {err}")
        failed += 1

    print(f"\n  {passed} passed, {failed} failed.")
    if failed:
        sys.exit(1)


def check_coefficient_recovery_and_validation() -> None:
    steps = bezout_recovery_steps(137, 60)
    assert steps[-1] == (1, -7, 16)
    for remainder, a_coefficient, b_coefficient in steps:
        assert remainder == a_coefficient * 137 + b_coefficient * 60

    for solver in (kuttaka, extended_euclid_solve):
        for a, b in ((0, 5), (5, 0), (-1, 5), (5, -1)):
            try:
                solver(a, b, 1, verbose=False) if solver is kuttaka else solver(a, b, 1)
            except ValueError:
                pass
            else:
                raise AssertionError(f"{solver.__name__} accepted a={a}, b={b}")

if __name__ == "__main__":
    print("Running kuṭṭaka tests...\n")
    test_run_tests()
