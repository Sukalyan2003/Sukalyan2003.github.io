# BCH Error-Correcting Code Demo

Educational Python implementation of:
- **Hamming(7,4)**: encodes 4 bits into 7, corrects 1 bit error
- **BCH(15, 7, t=2)**: encodes 7 bits into 15, corrects up to 2 bit errors

No dependencies beyond Python 3 stdlib. This is a toy implementation - meant to
make the algebra visible, not to serve production use.

## Run

```
python bch_demo.py
```

## Run tests

```
python test_bch.py
```

or with pytest:

```
pytest test_bch.py -v
```

## Real output

```
==============================================================
BCH Error-Correcting Code Demo
==============================================================

--- PART 1: Hamming(7,4)  [corrects 1 error] ---

Original message (4 bits):   1011
Hamming codeword (7 bits):   0110011

After flipping bit 3:        0111011
Syndrome identified error at position: 3 (0-indexed)
Recovered message:           1011
Match original?  YES ✓

Flipping bits 1 AND 5 (2 errors): 0010001
Syndrome 'error' at position: 3  ← wrong; Hamming misidentifies it
'Recovered': 1001 - WRONG (Hamming silently fails on 2 errors)

  → This is exactly why BCH codes exist.

--- PART 2: BCH(15, 7, t=2)  [corrects up to 2 errors] ---

Original message (7 bits):         1011001
BCH codeword (15 bits):            010000111011001
  parity[0:8]:  01000011
  message[8:15]: 1011001

[Test A: no errors]
  All syndromes zero - no errors.
  Recovered: 1011001  Match? YES ✓

[Test B: 1 error - flip bit at position 5]
  Received:  010001111011001
  Errors corrected at positions: [5]
  Recovered: 1011001  Match? YES ✓

[Test C: 2 errors - flip bits at positions 2 and 11]
  Received:  011000111010001
  Errors corrected at positions: [2, 11]
  Recovered: 1011001  Match? YES ✓

[Test D: 3 errors - beyond correction capacity (t=2)]
  Received:  110000101011011
  Decoder returned: 1010010 - WRONG (as expected with >t errors)

--- PART 3: Exhaustive sweep - every message and every 2-error pattern ---

  Checked all 128 messages × C(15,2) error pairs.
  Combinations: 13,440
  Failures: 0 / 13,440
  Result: ALL PASSED ✓

==============================================================
Demo complete.
==============================================================
```

## What the code implements

**GF(2^4) arithmetic** (`gf_mul`, `gf_inv`, `gf_alpha_pow`): The finite field
with 16 elements, built from the primitive polynomial x⁴ + x + 1. All
multiplication uses log/antilog tables.

**Polynomial operations** (`poly_eval`, `poly_divmod`): Polynomial arithmetic
over GF(2^4), stored with index = power of x (low-to-high).

**BCH encoder** (`bch_encode`): Systematic encoding - divide x^(n-k)·m(x) by
the generator polynomial g(x); the remainder is the 8-bit parity appended to
the 7-bit message.

**Syndrome computation** (`bch_syndromes`): Evaluate the received polynomial at
alpha^1 through alpha^4. Valid codewords have all-zero syndromes.

**Berlekamp-Massey** (`berlekamp_massey`): Finds the shortest LFSR (the error
locator polynomial) consistent with the syndrome sequence.

**Chien search** (`chien_search`): Exhaustively checks which bit positions are
roots of the error locator polynomial.

**BCH decoder** (`bch_decode`): Combines the above into syndrome → BM → Chien
→ flip bits at error positions → recompute syndromes. It rejects malformed bit
vectors and raises an error if the proposed correction is not a valid codeword.

## Generator polynomial

```
g(x) = x⁸ + x⁷ + x⁶ + x⁴ + 1
     = LCM(m₁(x), m₃(x))
```

where m₁(x) = x⁴ + x + 1 and m₃(x) = x⁴ + x³ + x² + x + 1 are the minimal
polynomials of α and α³ over GF(2).  
Source: Lin & Costello, *Error Control Coding*, 2nd ed., Table 6.3.

The test suite contains 18 focused checks, including exhaustive correction of
all zero-, one-, and two-error patterns for every possible seven-bit message.
