"""Tests for Pingala's pratyaya implementations."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pingala import (
    prastara, sankhya, nashta, explain_row, uddishta, lagakriya,
    meru_prastara, matra_vritta_count, list_matra_vritta,
    verify_nashta_uddishta, L, G
)


def test_prastara_length():
    """prastara(n) has exactly 2**n rows, each of length n."""
    for n in range(1, 6):
        rows = prastara(n)
        assert len(rows) == 2 ** n, f"Expected {2**n} rows for n={n}"
        for row in rows:
            assert len(row) == n, f"Each row must have {n} syllables"


def test_prastara_all_guru_first():
    """First row of prastara is all-G (Pingala's historical order), last is all-L."""
    for n in range(1, 5):
        rows = prastara(n)
        assert rows[0] == tuple(G for _ in range(n)), "Row 1 should be all guru (Pingala's ordering)"
        assert rows[-1] == tuple(L for _ in range(n)), "Last row should be all laghu"


def test_sankhya():
    for n in range(0, 8):
        assert sankhya(n) == 2 ** n


def test_nashta_known_values():
    """Test against manually verified values (Pingala's historical ordering: row 1 = GGG)."""
    # nashta(1, 3): val=1 odd → G, (1+1)/2=1 → G, (1+1)/2=1 → G => GGG
    assert nashta(1, 3) == (G, G, G), "Row 1 in Pingala's system is all-guru"
    # nashta(8, 3): val=8 even→L, 4 even→L, 2 even→L => LLL
    assert nashta(8, 3) == (L, L, L), "Row 8 (last) in Pingala's system is all-laghu"
    # nashta(4, 3): val=4 even→L, 2 even→L, 1 odd→G => LLG
    assert nashta(4, 3) == (L, L, G)


def test_explain_row_uses_historical_order():
    explanation = explain_row(4, 3)
    assert "2^3 − 4 = 4" in explanation
    assert "100₂ → reverse → 001 → LLG" in explanation


def test_uddishta_known_values():
    # uddishta(GGG): scan reversed GGG = GGG; val=1, G→2*1-1=1, G→2*1-1=1, G→2*1-1=1
    # Hmm: let's compute manually
    # reversed((G,G,G)) = G,G,G
    # val=1; G: val=2*1-1=1; G: val=2*1-1=1; G: val=2*1-1=1 => 1
    assert uddishta((G, G, G)) == 1, "All-guru should be row 1"
    # reversed((L,L,L)) = L,L,L
    # val=1; L: val=2*1=2; L: val=2*2=4; L: val=2*4=8 => 8
    assert uddishta((L, L, L)) == 8, "All-laghu should be last row"
    # nashta(4,3) = LLG, so uddishta(LLG) should = 4
    assert uddishta((L, L, G)) == 4


def test_nashta_uddishta_inverse():
    """nashta and uddishta are inverses for all n up to 5."""
    for n in range(1, 6):
        assert verify_nashta_uddishta(n), f"Round-trip failed for n={n}"


def test_lagakriya_values():
    # C(6,0)=1, C(6,1)=6, C(6,2)=15, C(6,3)=20
    assert lagakriya(6, 0) == 1
    assert lagakriya(6, 1) == 6
    assert lagakriya(6, 2) == 15
    assert lagakriya(6, 3) == 20
    assert lagakriya(6, 6) == 1


def test_lagakriya_row_sums_to_sankhya():
    """Sum of lagakriya(n,r) for r=0..n equals sankhya(n)."""
    for n in range(0, 8):
        total = sum(lagakriya(n, r) for r in range(n + 1))
        assert total == sankhya(n), f"Row sum mismatch at n={n}"


def test_meru_prastara_shape():
    tri = meru_prastara(6)
    assert len(tri) == 6
    for n, row in enumerate(tri):
        assert len(row) == n + 1
        assert row[0] == 1
        assert row[-1] == 1


def test_meru_prastara_recurrence():
    tri = meru_prastara(8)
    for n in range(2, 8):
        for r in range(1, n):
            assert tri[n][r] == tri[n-1][r-1] + tri[n-1][r], \
                f"Pascal recurrence failed at n={n}, r={r}"


def test_matra_vritta_count_fibonacci():
    """matra_vritta_count follows Fibonacci: 1,2,3,5,8,13,21,..."""
    expected = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
    for i, exp in enumerate(expected, start=1):
        got = matra_vritta_count(i)
        assert got == exp, f"matra_vritta_count({i}) = {got}, expected {exp}"


def test_empty_matra_arrangement_and_negative_input():
    assert matra_vritta_count(0) == 1
    assert list_matra_vritta(0) == [()]
    for function in (matra_vritta_count, list_matra_vritta):
        try:
            function(-1)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{function.__name__} should reject negative n")


def test_matra_vritta_list_count_matches():
    """The number of listed patterns equals matra_vritta_count."""
    for n in range(1, 9):
        patterns = list_matra_vritta(n)
        assert len(patterns) == matra_vritta_count(n), \
            f"List length mismatch at n={n}"


def test_matra_vritta_mora_sum():
    """Every listed pattern sums to exactly n morae."""
    for n in range(1, 7):
        for pat in list_matra_vritta(n):
            mora_sum = sum(2 if s == G else 1 for s in pat)
            assert mora_sum == n, f"Mora sum {mora_sum} != {n} for pattern {pat}"


if __name__ == "__main__":
    # Run all tests manually if not using pytest
    import traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
