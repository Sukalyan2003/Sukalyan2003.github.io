"""
BCH Error-Correcting Code Demo
-------------------------------
Educational implementation of:
  1. Hamming(7,4) — the simplest single-error-correcting code, as an on-ramp
  2. Binary BCH(15, 7, t=2) over GF(2^4) — corrects up to 2 bit errors

This is a toy; it exists to make the algebra visible, not to serve production use.

Run:
    python bch_demo.py

No dependencies beyond Python 3 stdlib.
"""

from itertools import combinations

# ---------------------------------------------------------------------------
# GF(2^4) arithmetic  — the field with 16 elements
#
# Primitive polynomial: p(x) = x^4 + x + 1  (binary 10011 = 19)
# This is the standard irreducible polynomial for GF(2^4).
# alpha = 2 (binary 0010) is a primitive element: its powers generate
# all 15 non-zero elements of GF(2^4).
#
# Reference: Lin & Costello, "Error Control Coding," 2nd ed., Table 2.2.
# ---------------------------------------------------------------------------

GF16_PRIM = 0b10011   # x^4 + x + 1
GF16_SIZE  = 16        # 2^4

# Log and antilog (exp) tables.
_gf_exp = [0] * (2 * GF16_SIZE)
_gf_log = [0] * GF16_SIZE

def _build_gf_tables():
    x = 1
    for i in range(GF16_SIZE - 1):
        _gf_exp[i] = x
        _gf_log[x] = i
        x <<= 1
        if x & GF16_SIZE:          # degree 4 term present → reduce mod p(x)
            x ^= GF16_PRIM
    # extend table for wrap-around arithmetic
    for i in range(GF16_SIZE - 1, 2 * GF16_SIZE):
        _gf_exp[i] = _gf_exp[i - (GF16_SIZE - 1)]

_build_gf_tables()

def gf_mul(a, b):
    """Multiply two elements of GF(2^4) using log/antilog tables."""
    if a == 0 or b == 0:
        return 0
    return _gf_exp[(_gf_log[a] + _gf_log[b]) % (GF16_SIZE - 1)]

def gf_inv(x):
    """Multiplicative inverse of x in GF(2^4), x != 0."""
    if x == 0:
        raise ZeroDivisionError("0 has no multiplicative inverse in GF(2^4)")
    return _gf_exp[(GF16_SIZE - 1) - _gf_log[x]]

def gf_alpha_pow(n):
    """Return alpha^n in GF(2^4), where alpha = 2 is the primitive element."""
    return _gf_exp[n % (GF16_SIZE - 1)]

# ---------------------------------------------------------------------------
# Polynomial operations over GF(2^4)
# Convention: coefficient list is stored LOW-to-HIGH (index = power of x).
# So [1, 0, 1] represents 1 + x^2.
# ---------------------------------------------------------------------------

def poly_eval(p, x):
    """Evaluate polynomial p at x using Horner's method."""
    result = 0
    for coef in reversed(p):
        result = gf_mul(result, x) ^ coef
    return result

def poly_divmod(dividend, divisor):
    """
    Polynomial long division over GF(2^4).
    Returns (quotient, remainder), both stored low-to-high.
    """
    # Reverse to high-to-low for the division algorithm, then reverse back.
    div = list(reversed(dividend))
    dsr = list(reversed(divisor))
    out = []
    for i in range(len(div) - len(dsr) + 1):
        coef = div[i]
        out.append(coef)
        if coef != 0:
            for j in range(1, len(dsr)):
                div[i + j] ^= gf_mul(dsr[j], coef)
    sep = len(dsr) - 1
    return list(reversed(out)), list(reversed(div[-sep:]))

# ---------------------------------------------------------------------------
# BCH(15, 7, t=2): n=15, k=7, designed distance d=5, corrects t=2 errors
#
# Over GF(2^4) with primitive polynomial x^4 + x + 1.
# Generator polynomial g(x) = LCM(m_1(x), m_3(x))
# where m_i is the minimal polynomial of alpha^i over GF(2).
#
#   m_1(x) = x^4 + x + 1                (roots: alpha, alpha^2, alpha^4, alpha^8)
#   m_3(x) = x^4 + x^3 + x^2 + x + 1   (roots: alpha^3, alpha^6, alpha^9, alpha^12)
#   g(x)   = m_1 * m_3 = x^8 + x^7 + x^6 + x^4 + 1
#
# This g(x) has alpha^1, alpha^2, alpha^3, alpha^4 as roots (2*t = 4 consecutive
# powers), satisfying the BCH bound: d >= 5, so t = floor((5-1)/2) = 2.
# n - k = deg(g) = 8, so parity bits = 8, message bits = 7.
#
# Reference: Lin & Costello, "Error Control Coding," 2nd ed., Table 6.3.
# Also: Wikipedia, "BCH code," example BCH(15,7).
# ---------------------------------------------------------------------------

BCH_N       = 15
BCH_K       = 7
BCH_T       = 2
BCH_NPARITY = BCH_N - BCH_K   # 8

# g(x) = 1 + x^4 + x^6 + x^7 + x^8  (stored low-to-high)
_G_POLY = [1, 0, 0, 0, 1, 0, 1, 1, 1]


def _validate_bits(bits, expected_length, label):
    if len(bits) != expected_length:
        raise ValueError(f"{label} must be {expected_length} bits, got {len(bits)}")
    if any(bit not in (0, 1) for bit in bits):
        raise ValueError(f"{label} must contain only 0 and 1")

def bch_encode(message_bits):
    """
    Encode a 7-bit message as a BCH(15,7) codeword (systematic form).

    Systematic encoding: c(x) = x^(n-k)*m(x) + r(x)
    where r(x) = x^(n-k)*m(x) mod g(x).
    The message occupies the high-order bits; the remainder is the parity.

    message_bits : list of 7 ints in {0, 1}, index 0 = lowest-order bit
    Returns      : list of 15 ints (parity[0:8] + message[0:7])
    """
    _validate_bits(message_bits, BCH_K, "Message")
    shifted = [0] * BCH_NPARITY + list(message_bits)   # x^8 * m(x)
    _, parity = poly_divmod(shifted, _G_POLY)
    codeword = parity + list(message_bits)
    assert len(codeword) == BCH_N
    return codeword

def bch_syndromes(received):
    """
    Compute syndromes S_i = r(alpha^i) for i = 1 .. 2t.
    A valid codeword is a multiple of g(x), so all S_i = 0.
    Any non-zero syndrome signals an error.
    """
    _validate_bits(received, BCH_N, "Received word")
    return [poly_eval(received, gf_alpha_pow(i)) for i in range(1, 2 * BCH_T + 1)]

def berlekamp_massey(syndromes, t):
    """
    Berlekamp-Massey algorithm: finds the shortest LFSR (the error locator
    polynomial Lambda(x)) consistent with the syndrome sequence.

    The roots of Lambda(x) are the inverses of the error locators.

    Reference: Blahut, "Algebraic Codes for Data Transmission," Cambridge
    University Press, 2003, ch. 7.
    """
    n = 2 * t
    C = [1] + [0] * n    # current candidate locator
    B = [1] + [0] * n    # previous locator
    L = 0                 # current LFSR length
    m = 1                 # number of steps since last length update
    b = 1                 # leading coefficient at last update

    for i in range(n):
        # Discrepancy: how well C predicts the next syndrome
        d = syndromes[i]
        for j in range(1, L + 1):
            d ^= gf_mul(C[j], syndromes[i - j])

        if d == 0:
            m += 1
        elif 2 * L <= i:
            T = C[:]
            coef = gf_mul(d, gf_inv(b))
            for j in range(n + 1 - m):
                C[j + m] ^= gf_mul(coef, B[j])
            L = i + 1 - L
            B = T[:]
            b = d
            m = 1
        else:
            coef = gf_mul(d, gf_inv(b))
            for j in range(n + 1 - m):
                C[j + m] ^= gf_mul(coef, B[j])
            m += 1

    return C[:L + 1]

def chien_search(locator_poly, n):
    """
    Chien search: substitute alpha^(-i) for i = 0..n-1 into Lambda(x).
    A zero means position i is in error.
    (For binary BCH the error magnitude is always 1, so we only need locations.)
    """
    error_positions = []
    for i in range(n):
        alpha_neg_i = gf_alpha_pow((GF16_SIZE - 1 - i) % (GF16_SIZE - 1))
        if poly_eval(locator_poly, alpha_neg_i) == 0:
            error_positions.append(i)
    return error_positions

def bch_decode(received_bits):
    """
    Decode a (possibly corrupted) BCH(15,7) codeword.

    received_bits : list of 15 ints in {0, 1}
    Returns       : (corrected_message, num_errors_corrected, error_positions)
    Raises        : ValueError if root-count or post-correction checks fail.
    Beyond t=2 errors, a wrong valid codeword may be returned without raising.
    """
    _validate_bits(received_bits, BCH_N, "Received word")

    syndromes = bch_syndromes(received_bits)

    if all(s == 0 for s in syndromes):
        return received_bits[BCH_NPARITY:], 0, []

    locator = berlekamp_massey(syndromes, BCH_T)
    num_errors = len(locator) - 1

    error_positions = chien_search(locator, BCH_N)

    if len(error_positions) != num_errors:
        raise ValueError(
            f"Decoder found {len(error_positions)} roots but locator has degree "
            f"{num_errors} — likely more than {BCH_T} errors in this word"
        )

    corrected = list(received_bits)
    for pos in error_positions:
        corrected[pos] ^= 1   # binary BCH: error value is always 1

    if any(bch_syndromes(corrected)):
        raise ValueError("Correction did not produce a valid BCH codeword")

    return corrected[BCH_NPARITY:], len(error_positions), error_positions

# ---------------------------------------------------------------------------
# Hamming(7,4) — the simplest single-error-correcting code
#
# Included as a warm-up so the upgrade to BCH has a concrete reference point.
#
# Layout: codeword = [p1, p2, d1, p3, d2, d3, d4] (positions 1..7)
# Parity checks:
#   p1 covers bits at positions 1,3,5,7  (p1, d1, d2, d4)
#   p2 covers bits at positions 2,3,6,7  (p2, d1, d3, d4)
#   p3 covers bits at positions 4,5,6,7  (p3, d2, d3, d4)
#
# Syndrome = [s1, s2, s3]; error position = s1 + 2*s2 + 4*s3 (1-indexed).
# ---------------------------------------------------------------------------

_HAMMING_H = [
    [1, 0, 1, 0, 1, 0, 1],   # p1 check
    [0, 1, 1, 0, 0, 1, 1],   # p2 check
    [0, 0, 0, 1, 1, 1, 1],   # p3 check
]

# Generator matrix G (4×7): row i = codeword for the i-th basis vector
_HAMMING_G = [
    [1, 1, 1, 0, 0, 0, 0],   # d1
    [1, 0, 0, 1, 1, 0, 0],   # d2
    [0, 1, 0, 1, 0, 1, 0],   # d3
    [1, 1, 0, 1, 0, 0, 1],   # d4
]

def hamming_encode(message_bits):
    """Encode 4-bit message to a Hamming(7,4) codeword."""
    _validate_bits(message_bits, 4, "Hamming message")
    cw = [0] * 7
    for i, row in enumerate(_HAMMING_G):
        if message_bits[i]:
            for j in range(7):
                cw[j] ^= row[j]
    return cw

def hamming_decode(received):
    """Decode a (possibly corrupted) Hamming(7,4) codeword. Returns (message, err_pos_0indexed_or_None)."""
    _validate_bits(received, 7, "Hamming codeword")
    syndrome = [0, 0, 0]
    for i in range(3):
        for j in range(7):
            syndrome[i] ^= _HAMMING_H[i][j] * received[j]
    err_pos_1indexed = syndrome[0] * 1 + syndrome[1] * 2 + syndrome[2] * 4
    corrected = list(received)
    if err_pos_1indexed != 0:
        corrected[err_pos_1indexed - 1] ^= 1
    # Data bits are at positions 2,4,5,6 (0-indexed) = d1,d2,d3,d4
    message = [corrected[2], corrected[4], corrected[5], corrected[6]]
    return message, (err_pos_1indexed - 1) if err_pos_1indexed else None

# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

def bits_to_str(bits):
    return ''.join(str(b) for b in bits)

def flip_bits(word, positions):
    """Return a copy of word with bits at positions flipped."""
    c = list(word)
    for p in positions:
        c[p] ^= 1
    return c

def run_demo():
    print("=" * 62)
    print("BCH Error-Correcting Code Demo")
    print("=" * 62)

    # ------------------------------------------------------------------
    # Part 1: Hamming(7,4) — single-error correction
    # ------------------------------------------------------------------
    print("\n--- PART 1: Hamming(7,4)  [corrects 1 error] ---\n")

    msg4 = [1, 0, 1, 1]          # d1=1, d2=0, d3=1, d4=1
    cw7  = hamming_encode(msg4)
    print(f"Original message (4 bits):   {bits_to_str(msg4)}")
    print(f"Hamming codeword (7 bits):   {bits_to_str(cw7)}")

    # Corrupt 1 bit (position 3 = p3 parity bit)
    corrupted7 = flip_bits(cw7, [3])
    print(f"\nAfter flipping bit 3:        {bits_to_str(corrupted7)}")
    recovered4, err_pos = hamming_decode(corrupted7)
    print(f"Syndrome identified error at position: {err_pos} (0-indexed)")
    print(f"Recovered message:           {bits_to_str(recovered4)}")
    print(f"Match original?  {'YES ✓' if recovered4 == msg4 else 'NO ✗'}")

    # Try 2 errors — Hamming silently fails
    corrupted7_2 = flip_bits(cw7, [1, 5])
    print(f"\nFlipping bits 1 AND 5 (2 errors): {bits_to_str(corrupted7_2)}")
    recovered4_2, err_pos2 = hamming_decode(corrupted7_2)
    print(f"Syndrome 'error' at position: {err_pos2}  ← wrong; Hamming misidentifies it")
    print(f"'Recovered': {bits_to_str(recovered4_2)} — WRONG (Hamming silently fails on 2 errors)")
    print("\n  → This is exactly why BCH codes exist.")

    # ------------------------------------------------------------------
    # Part 2: BCH(15,7,t=2) — double-error correction
    # ------------------------------------------------------------------
    print("\n--- PART 2: BCH(15, 7, t=2)  [corrects up to 2 errors] ---\n")

    message = [1, 0, 1, 1, 0, 0, 1]
    print(f"Original message (7 bits):         {bits_to_str(message)}")
    codeword = bch_encode(message)
    print(f"BCH codeword (15 bits):            {bits_to_str(codeword)}")
    print(f"  parity[0:8]:  {bits_to_str(codeword[:8])}")
    print(f"  message[8:15]: {bits_to_str(codeword[8:])}")

    # Test A: 0 errors
    print("\n[Test A: no errors]")
    recovered, n_err, positions = bch_decode(codeword)
    print(f"  All syndromes zero — no errors.")
    print(f"  Recovered: {bits_to_str(recovered)}  Match? {'YES ✓' if recovered == message else 'NO ✗'}")

    # Test B: 1 error
    print("\n[Test B: 1 error — flip bit at position 5]")
    c1 = flip_bits(codeword, [5])
    print(f"  Received:  {bits_to_str(c1)}")
    recovered, n_err, positions = bch_decode(c1)
    print(f"  Errors corrected at positions: {positions}")
    print(f"  Recovered: {bits_to_str(recovered)}  Match? {'YES ✓' if recovered == message else 'NO ✗'}")

    # Test C: 2 errors
    print("\n[Test C: 2 errors — flip bits at positions 2 and 11]")
    c2 = flip_bits(codeword, [2, 11])
    print(f"  Received:  {bits_to_str(c2)}")
    recovered, n_err, positions = bch_decode(c2)
    print(f"  Errors corrected at positions: {positions}")
    print(f"  Recovered: {bits_to_str(recovered)}  Match? {'YES ✓' if recovered == message else 'NO ✗'}")

    # Test D: 3 errors — beyond the t=2 design limit
    print("\n[Test D: 3 errors — beyond correction capacity (t=2)]")
    c3 = flip_bits(codeword, [0, 7, 13])
    print(f"  Received:  {bits_to_str(c3)}")
    try:
        recovered, n_err, positions = bch_decode(c3)
        wrong = recovered != message
        print(f"  Decoder returned: {bits_to_str(recovered)} — {'WRONG (as expected with >t errors)' if wrong else 'accidentally right'}")
    except ValueError as e:
        print(f"  Decoder raised ValueError: {e}")

    # ------------------------------------------------------------------
    # Part 3: Exhaustive sweep — all messages and all two-error patterns
    # ------------------------------------------------------------------
    print("\n--- PART 3: Exhaustive sweep — every message and every 2-error pattern ---\n")
    failures = 0
    checked = 0
    for n in range(128):
        msg = [(n >> i) & 1 for i in range(7)]
        cw  = bch_encode(msg)
        for pos in combinations(range(15), 2):
            corrupted = flip_bits(cw, pos)
            rec, _, _ = bch_decode(corrupted)
            checked += 1
            if rec != msg:
                failures += 1

    print(f"  Checked all 128 messages × C(15,2) error pairs.")
    print(f"  Combinations: {checked:,}")
    print(f"  Failures: {failures} / {checked:,}")
    print(f"  Result: {'ALL PASSED ✓' if failures == 0 else f'{failures} FAILURES ✗'}")

    print("\n" + "=" * 62)
    print("Demo complete.")
    print("=" * 62)


if __name__ == "__main__":
    run_demo()
