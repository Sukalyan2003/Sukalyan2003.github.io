"""
Tests for bch_demo.py — BCH(15,7,t=2) encoder and decoder.
Run with: python -m pytest test_bch.py -v
or just:  python test_bch.py
"""

import sys
from itertools import combinations

from bch_demo import (
    bch_encode, bch_decode, bch_syndromes,
    hamming_encode, hamming_decode,
    flip_bits,
    gf_mul, gf_inv, gf_alpha_pow, poly_eval,
    BCH_N, BCH_K, BCH_T,
    _G_POLY,
)


# ---------------------------------------------------------------------------
# GF(2^4) arithmetic sanity checks
# ---------------------------------------------------------------------------

def test_gf_primitive_polynomial():
    """alpha^4 + alpha + 1 = 0 in GF(2^4)."""
    alpha = gf_alpha_pow(1)   # = 2
    a4    = gf_alpha_pow(4)   # should equal alpha+1 = 3
    assert a4 ^ alpha ^ 1 == 0, f"Primitive poly check failed: alpha^4={a4}, alpha={alpha}"

def test_gf_mul_commutativity():
    for a, b in [(3, 5), (7, 12), (1, 15), (0, 9)]:
        assert gf_mul(a, b) == gf_mul(b, a)

def test_gf_mul_by_zero():
    for x in range(16):
        assert gf_mul(x, 0) == 0
        assert gf_mul(0, x) == 0

def test_gf_inv_roundtrip():
    for x in range(1, 16):
        assert gf_mul(x, gf_inv(x)) == 1, f"x * x^-1 != 1 for x={x}"

def test_generator_poly_roots():
    """BCH designed distance: alpha^1 through alpha^4 must be roots of g(x)."""
    for i in range(1, 2 * BCH_T + 1):
        val = poly_eval(_G_POLY, gf_alpha_pow(i))
        assert val == 0, f"g(alpha^{i}) = {val} != 0"


# ---------------------------------------------------------------------------
# Hamming(7,4) tests
# ---------------------------------------------------------------------------

def test_hamming_encode_decode_no_error():
    for n in range(16):
        msg = [(n >> i) & 1 for i in range(4)]
        cw  = hamming_encode(msg)
        assert len(cw) == 7
        recovered, err = hamming_decode(cw)
        assert recovered == msg
        assert err is None

def test_hamming_single_error_correction():
    msg = [1, 0, 1, 1]
    cw  = hamming_encode(msg)
    for pos in range(7):
        corrupted = flip_bits(cw, [pos])
        recovered, err_pos = hamming_decode(corrupted)
        assert recovered == msg, f"Hamming failed to correct error at pos {pos}"

def test_hamming_fails_on_two_errors():
    """Hamming(7,4) cannot reliably correct two errors — this documents the known limitation."""
    failures = 0
    for n in range(16):
        msg = [(n >> i) & 1 for i in range(4)]
        cw  = hamming_encode(msg)
        for i in range(7):
            for j in range(i + 1, 7):
                corrupted = flip_bits(cw, [i, j])
                recovered, _ = hamming_decode(corrupted)
                if recovered != msg:
                    failures += 1
    # With 2 errors, Hamming always misidentifies the error — all cases should fail
    total = 16 * 21   # 16 messages × C(7,2) = 21 pairs
    assert failures > 0, "Hamming should fail on at least some 2-error cases"
    # In fact all should fail; document the count
    assert failures == total, f"Expected all {total} two-error cases to fail, got {failures}"


# ---------------------------------------------------------------------------
# BCH(15,7,t=2) encoder tests
# ---------------------------------------------------------------------------

def test_bch_encode_length():
    msg = [1, 0, 1, 1, 0, 0, 1]
    cw  = bch_encode(msg)
    assert len(cw) == BCH_N

def test_bch_encode_message_preserved():
    """In systematic form the message appears unchanged in the high bits."""
    for n in range(128):
        msg = [(n >> i) & 1 for i in range(BCH_K)]
        cw  = bch_encode(msg)
        assert cw[BCH_N - BCH_K:] == msg, "Message not preserved in systematic codeword"

def test_bch_encode_syndromes_zero():
    """Every valid codeword has all-zero syndromes."""
    for n in range(128):
        msg = [(n >> i) & 1 for i in range(BCH_K)]
        cw  = bch_encode(msg)
        s   = bch_syndromes(cw)
        assert all(si == 0 for si in s), f"Non-zero syndrome for message {msg}: {s}"

def test_bch_encode_invalid_length():
    try:
        bch_encode([1, 0])
        assert False, "Should have raised"
    except ValueError:
        pass


def test_non_binary_inputs_rejected():
    for function, bits in [
        (bch_encode, [0, 0, 0, 0, 0, 0, 2]),
        (bch_decode, [0] * 14 + [-1]),
        (hamming_encode, [0, 0, 0, 3]),
        (hamming_decode, [0] * 6 + [2]),
    ]:
        try:
            function(bits)
            assert False, f"{function.__name__} accepted a non-binary input"
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# BCH(15,7,t=2) decoder tests
# ---------------------------------------------------------------------------

def test_bch_decode_no_error():
    msg = [1, 0, 1, 1, 0, 0, 1]
    cw  = bch_encode(msg)
    recovered, n_err, positions = bch_decode(cw)
    assert recovered == msg
    assert n_err == 0
    assert positions == []

def test_bch_decode_one_error_all_positions():
    """Single error at every possible bit position must be corrected."""
    msg = [1, 0, 1, 1, 0, 0, 1]
    cw  = bch_encode(msg)
    for pos in range(BCH_N):
        corrupted = flip_bits(cw, [pos])
        recovered, n_err, positions = bch_decode(corrupted)
        assert recovered == msg, f"Failed to correct single error at position {pos}"
        assert n_err == 1

def test_bch_decode_two_errors_all_pairs():
    """Two errors at every pair of bit positions must be corrected."""
    msg = [0, 1, 0, 1, 1, 0, 1]
    cw  = bch_encode(msg)
    failures = []
    for i in range(BCH_N):
        for j in range(i + 1, BCH_N):
            corrupted = flip_bits(cw, [i, j])
            recovered, n_err, positions = bch_decode(corrupted)
            if recovered != msg:
                failures.append((i, j))
    assert failures == [], f"BCH failed on these error pairs: {failures}"

def test_bch_exhaustive_two_errors():
    """All 128 messages × all C(15,2) error pairs must be correctable."""
    failures = 0
    for n in range(128):
        msg = [(n >> i) & 1 for i in range(BCH_K)]
        cw  = bch_encode(msg)
        for pos in combinations(range(BCH_N), 2):
            recovered, _, _ = bch_decode(flip_bits(cw, pos))
            if recovered != msg:
                failures += 1
    assert failures == 0, f"{failures} messages failed decoding"

def test_bch_decode_three_errors_detected():
    """Three errors should either raise ValueError or produce wrong output (not silently 'fix' it)."""
    msg = [1, 0, 1, 1, 0, 0, 1]
    cw  = bch_encode(msg)
    c3  = flip_bits(cw, [0, 7, 13])
    try:
        recovered, _, _ = bch_decode(c3)
        # If no exception, the recovered message should differ (decoder can't fix 3 errors)
        # Accept either outcome: wrong answer or exception
        assert recovered != msg
    except ValueError:
        pass   # expected


# ---------------------------------------------------------------------------
# Minimal self-runner (no pytest dependency required)
# ---------------------------------------------------------------------------

def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0; failed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    print("Running BCH tests...\n")
    _run_all()
