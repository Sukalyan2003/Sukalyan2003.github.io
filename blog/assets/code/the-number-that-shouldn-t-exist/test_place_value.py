"""
test_place_value.py — Tests for place_value.py

Run: python test_place_value.py
"""

import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
sys.path.insert(0, ".")
from place_value import add_positional, add_roman, digits_to_str, from_base, to_base, to_roman


class TestBaseConversion(unittest.TestCase):

    def test_decimal_to_binary_known_values(self):
        self.assertEqual(to_base(0, 2), [0])
        self.assertEqual(to_base(1, 2), [1])
        self.assertEqual(to_base(2, 2), [1, 0])
        self.assertEqual(to_base(7, 2), [1, 1, 1])
        self.assertEqual(to_base(8, 2), [1, 0, 0, 0])
        self.assertEqual(to_base(42, 2), [1, 0, 1, 0, 1, 0])
        self.assertEqual(to_base(255, 2), [1, 1, 1, 1, 1, 1, 1, 1])

    def test_decimal_to_hex(self):
        self.assertEqual(to_base(255, 16), [15, 15])   # 0xFF
        self.assertEqual(to_base(256, 16), [1, 0, 0])  # 0x100
        self.assertEqual(to_base(16, 16), [1, 0])

    def test_round_trip(self):
        """to_base then from_base must be the identity."""
        for base in [2, 8, 10, 16, 3, 7]:
            for n in [0, 1, 9, 10, 42, 255, 1000, 65535]:
                digits = to_base(n, base)
                self.assertEqual(from_base(digits, base), n,
                                 f"round-trip failed for n={n}, base={base}")

    def test_zero_in_middle(self):
        """Zero in the interior of the digit list must survive the round-trip."""
        # 1024 in binary has internal zeros
        digits = to_base(1024, 2)
        self.assertEqual(digits, [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(from_base(digits, 2), 1024)
        # 1001 in decimal has internal zeros
        digits = to_base(1001, 10)
        self.assertEqual(digits, [1, 0, 0, 1])
        self.assertEqual(from_base(digits, 10), 1001)

    def test_base_must_be_at_least_2(self):
        with self.assertRaises(ValueError):
            to_base(5, 1)

    def test_negative_input_rejected(self):
        with self.assertRaises(ValueError):
            to_base(-1, 10)

    def test_invalid_digit_lists_rejected(self):
        for digits, base in [([], 10), ([1, 2], 2), ([1, -1], 10)]:
            with self.subTest(digits=digits, base=base):
                with self.assertRaises(ValueError):
                    from_base(digits, base)
                with self.assertRaises(ValueError):
                    digits_to_str(digits, base)

        with self.assertRaises(ValueError):
            add_positional([1], [2], base=2)
        with self.assertRaises(ValueError):
            from_base([1], base=1)

    def test_digits_to_str_binary(self):
        self.assertEqual(digits_to_str([1, 0, 1, 0], 2), "1010")

    def test_digits_to_str_hex(self):
        self.assertEqual(digits_to_str([15, 15], 16), "FF")


class TestPositionalAddition(unittest.TestCase):

    def _check(self, a, b, base=10):
        """Helper: add a+b in given base and verify against Python's arithmetic."""
        a_d = to_base(a, base)
        b_d = to_base(b, base)
        sum_d = add_positional(a_d, b_d, base)
        self.assertEqual(from_base(sum_d, base), a + b,
                         f"add_positional({a}, {b}, base={base}) wrong")

    def test_simple_decimal(self):
        self._check(0, 0)
        self._check(1, 2)
        self._check(9, 1)          # carry: 9+1 = 10

    def test_multidigit_decimal(self):
        self._check(347, 485)
        self._check(999, 1)        # 999 + 1 = 1000, carry chain
        self._check(999, 999)

    def test_different_lengths(self):
        self._check(1, 999)        # short + long
        self._check(1000, 1)       # long + short

    def test_binary(self):
        self._check(7, 1, base=2)  # 111 + 1 = 1000, full carry chain
        self._check(42, 85, base=2)
        self._check(255, 255, base=2)

    def test_hex(self):
        self._check(255, 1, base=16)   # FF + 1 = 100
        self._check(0xDEAD, 0xBEEF, base=16)

    def test_same_addition_across_bases(self):
        for base in [2, 3, 8, 10, 16]:
            with self.subTest(base=base):
                self._check(347, 485, base=base)

    def test_trace_shows_each_column(self):
        output = StringIO()
        with redirect_stdout(output):
            result = add_positional([3, 4, 7], [4, 8, 5], base=10, trace=True)

        self.assertEqual(result, [8, 3, 2])
        trace = output.getvalue()
        self.assertIn("base^0: 7 + 5 + carry 0 = 12; write 2, carry 1", trace)
        self.assertIn("base^1: 4 + 8 + carry 1 = 13; write 3, carry 1", trace)
        self.assertIn("base^2: 3 + 4 + carry 1 = 8; write 8, carry 0", trace)

    def test_zero_operand(self):
        """Adding zero should not change the other operand."""
        for n in [0, 1, 42, 1000]:
            self._check(n, 0)
            self._check(0, n)

    def test_carry_propagates_across_zeros(self):
        """1000 + 1 in decimal: carry must not get swallowed by the interior zeros."""
        self._check(1000, 1)
        self._check(10000, 1)
        self._check(10001, 9)      # 10001 + 9 = 10010


class TestRomanContrast(unittest.TestCase):

    def test_invalid_roman_input(self):
        for n in [0, -1, 4000]:
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    to_roman(n)
        with self.assertRaises(ValueError):
            add_roman(0, 1)

    def test_known_roman_values(self):
        self.assertEqual(to_roman(1),    "I")
        self.assertEqual(to_roman(4),    "IV")
        self.assertEqual(to_roman(9),    "IX")
        self.assertEqual(to_roman(14),   "XIV")
        self.assertEqual(to_roman(40),   "XL")
        self.assertEqual(to_roman(58),   "LVIII")
        self.assertEqual(to_roman(399),  "CCCXCIX")
        self.assertEqual(to_roman(400),  "CD")
        self.assertEqual(to_roman(1994), "MCMXCIV")
        self.assertEqual(to_roman(3999), "MMMCMXCIX")


if __name__ == "__main__":
    unittest.main(verbosity=2)
