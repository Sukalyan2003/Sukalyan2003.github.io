# Place-value and zero - code demo

Educational Python demo for the "Zero and place-value" post in the Unsung Bits series.

Demonstrates why **positional notation** (with a zero digit) is what makes
arithmetic algorithmic - and why non-positional systems like Roman numerals
have no equivalent clean procedure.

## What's here

| File | Purpose |
|---|---|
| `place_value.py` | Main demo: base conversion, positional addition with carry, zero-placeholder illustration, Roman numeral contrast |
| `test_place_value.py` | 20 unit tests covering valid conversions, addition, traces, and rejected inputs |

## Run

```
python3 place_value.py
python3 test_place_value.py
```

No dependencies beyond the Python 3 standard library.

Pass `trace=True` to `add_positional` to print the incoming carry, written
digit, and outgoing carry for every column. Conversion and addition functions
reject negative numbers, invalid bases, empty digit lists, and out-of-range digits.

## Expected output

```
============================================================
  Positional notation and zero: why arithmetic is algorithmic
============================================================

--- Base conversion ---
  42 (decimal) → 101010 (binary)
    = 1×2^5 + 0×2^4 + 1×2^3 + 0×2^2 + 1×2^1 + 0×2^0 = 42
  42 (decimal) → 52 (octal)
    = 5×8^1 + 2×8^0 = 42
  42 (decimal) → 2A (hex)
    = 2×16^1 + 10×16^0 = 42

  255 (decimal) → 11111111 (binary)
    = 1×2^7 + 1×2^6 + 1×2^5 + 1×2^4 + 1×2^3 + 1×2^2 + 1×2^1 + 1×2^0 = 255
  255 (decimal) → 377 (octal)
    = 3×8^2 + 7×8^1 + 7×8^0 = 255
  255 (decimal) → FF (hex)
    = 15×16^1 + 15×16^0 = 255

  1000 (decimal) → 1111101000 (binary)
    = 1×2^9 + 1×2^8 + 1×2^7 + 1×2^6 + 1×2^5 + 0×2^4 + 1×2^3 + 0×2^2 + 0×2^1 + 0×2^0 = 1000
  1000 (decimal) → 1750 (octal)
    = 1×8^3 + 7×8^2 + 5×8^1 + 0×8^0 = 1000
  1000 (decimal) → 3E8 (hex)
    = 3×16^2 + 14×16^1 + 8×16^0 = 1000

  2024 (decimal) → 11111101000 (binary)
    = 1×2^10 + 1×2^9 + 1×2^8 + 1×2^7 + 1×2^6 + 1×2^5 + 0×2^4 + 1×2^3 + 0×2^2 + 0×2^1 + 0×2^0 = 2024
  2024 (decimal) → 3750 (octal)
    = 3×8^3 + 7×8^2 + 5×8^1 + 0×8^0 = 2024
  2024 (decimal) → 7E8 (hex)
    = 7×16^2 + 14×16^1 + 8×16^0 = 2024


--- Multi-digit addition with carry ---
  base^0: 7 + 5 + carry 0 = 12; write 2, carry 1
  base^1: 4 + 8 + carry 1 = 13; write 3, carry 1
  base^2: 3 + 4 + carry 1 = 8; write 8, carry 0
  Addition in decimal (base 10):
      347
  +   485 -  -  -  -  - 832
    ✓  (= 832 in decimal)

  Addition in binary (base 2):
       101011011
  +    111100101 -  -  -  -  -  -  -  -  -  -  -  - 1101000000
    ✓  (= 832 in decimal)

  Addition in hex (base 16):
       FF
  +     1 -  -  -  -  - 100
    ✓  (= 256 in decimal)

  Addition in binary (base 2):
       111
  +      1 -  -  -  -  -  - 1000
    ✓  (= 8 in decimal)

--- Why zero is load-bearing ---
   1024  →  digit list: [1, 0, 2, 4]
   1204  →  digit list: [1, 2, 0, 4]
   1240  →  digit list: [1, 2, 4, 0]
   1004  →  digit list: [1, 0, 0, 4]
   1000  →  digit list: [1, 0, 0, 0]

  Each number has a UNIQUE digit list only because 0 can appear.
  Strip all zeros from the digit list and you lose the number:
   1024  →  strip zeros → [1, 2, 4]  (ambiguous!)
   1204  →  strip zeros → [1, 2, 4]  (ambiguous!)
   1240  →  strip zeros → [1, 2, 4]  (ambiguous!)
   1004  →  strip zeros → [1, 4]  (ambiguous!)
   1000  →  strip zeros → [1]  (ambiguous!)

--- Roman numeral contrast ---
  No column addition algorithm exists for Roman numerals.
  To 'add' XIV + IX you must mentally convert, compute, re-encode.

  XIV + IX = XXIII
    (i.e. 14 + 9 = 23 - you need the integers to get there)
    Positional: 14 + 9 = 23  (column algorithm, no mental detour)

  XLVII + LVIII = CV
    (i.e. 47 + 58 = 105 - you need the integers to get there)
    Positional: 47 + 58 = 105  (column algorithm, no mental detour)

  CCCXCIX + CDI = DCCC
    (i.e. 399 + 401 = 800 - you need the integers to get there)
    Positional: 399 + 401 = 800  (column algorithm, no mental detour)

============================================================
  All assertions passed.
============================================================
```

## Test output

```
test_base_must_be_at_least_2 ... ok
test_decimal_to_binary_known_values ... ok
test_decimal_to_hex ... ok
test_digits_to_str_binary ... ok
test_digits_to_str_hex ... ok
test_invalid_digit_lists_rejected ... ok
test_negative_input_rejected ... ok
test_round_trip ... ok
test_zero_in_middle ... ok
test_binary ... ok
test_carry_propagates_across_zeros ... ok
test_different_lengths ... ok
test_hex ... ok
test_multidigit_decimal ... ok
test_same_addition_across_bases ... ok
test_simple_decimal ... ok
test_trace_shows_each_column ... ok
test_zero_operand ... ok
test_invalid_roman_input ... ok
test_known_roman_values ... ok

----------------------------------------------------------------------
Ran 20 tests in 0.000s

OK
```
