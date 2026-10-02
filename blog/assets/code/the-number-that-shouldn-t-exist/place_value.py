"""
place_value.py — Why positional notation makes arithmetic algorithmic.

Demonstrates:
1. Base conversion (decimal ↔ arbitrary base, including binary)
2. Grade-school multi-digit addition with carry, operating on digit lists
3. The zero placeholder: what goes wrong without it
4. A contrast with Roman-numeral 'addition' — no clean column algorithm possible

Educational/toy implementation. Not production-quality.
"""

# ---------------------------------------------------------------------------
# 1. Base conversion
# ---------------------------------------------------------------------------

def _validate_base(base: int) -> None:
    if base < 2:
        raise ValueError(f"base must be ≥ 2, got {base}")


def _validate_digits(digits: list[int], base: int) -> None:
    _validate_base(base)
    if not digits:
        raise ValueError("digits must contain at least one digit")
    if any(not isinstance(digit, int) or digit < 0 or digit >= base for digit in digits):
        raise ValueError(f"every digit must be an integer in [0, {base - 1}]")


def to_base(n: int, base: int) -> list[int]:
    """
    Convert non-negative integer n to the given base.
    Returns a list of digits, most-significant first.
    Each digit is an integer in [0, base-1].

    Example: to_base(42, 2) → [1, 0, 1, 0, 1, 0]   (42 in binary)
             to_base(255, 16) → [15, 15]              (0xFF)
    """
    _validate_base(base)
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    if n == 0:
        return [0]
    digits = []
    while n > 0:
        digits.append(n % base)  # remainder → current digit
        n //= base               # shift right by one position
    return digits[::-1]          # reverse: we built LSB-first


def from_base(digits: list[int], base: int) -> int:
    """
    Convert a list of digits (most-significant first) in the given base
    back to a Python int.

    This is the place-value expansion: each position is base^k.
    """
    _validate_digits(digits, base)
    result = 0
    for d in digits:
        result = result * base + d   # Horner's method: same as shift-and-add
    return result


def digits_to_str(digits: list[int], base: int) -> str:
    """Human-readable representation using 0-9 and A-F for bases ≤ 16."""
    _validate_digits(digits, base)
    chars = "0123456789ABCDEF"
    if base > 16:
        return str(digits)  # just show the list for larger bases
    return "".join(chars[d] for d in digits)


def show_base_conversion(n: int, target_base: int) -> None:
    digits = to_base(n, target_base)
    back = from_base(digits, target_base)
    rep = digits_to_str(digits, target_base)
    label = {2: "binary", 8: "octal", 16: "hex"}.get(target_base, f"base-{target_base}")
    print(f"  {n} (decimal) → {rep} ({label})")
    # Show the expansion so the positional structure is explicit
    terms = [f"{d}×{target_base}^{len(digits)-1-i}"
             for i, d in enumerate(digits)]
    print(f"    = {' + '.join(terms)} = {back}")


# ---------------------------------------------------------------------------
# 2. Grade-school addition on digit lists (with carry)
# ---------------------------------------------------------------------------

def add_positional(
    a_digits: list[int],
    b_digits: list[int],
    base: int = 10,
    *,
    trace: bool = False,
) -> list[int]:
    """
    Add two numbers represented as digit lists (most-significant first).
    Uses the standard right-to-left column algorithm with carry.

    This is the algorithm that only works because:
      (a) Each column is independent once the carry from the right is known.
      (b) Zero is a valid digit — a column can be empty without breaking the grid.
      (c) Position encodes magnitude — we never need to inspect other columns
          to know what this column contributes to the total.

    Returns the result as a digit list, most-significant first.
    """
    _validate_digits(a_digits, base)
    _validate_digits(b_digits, base)

    # Pad to equal length (zero-padding on the left is safe because 0 in the
    # highest positions contributes nothing — this is what makes it work)
    length = max(len(a_digits), len(b_digits))
    a = [0] * (length - len(a_digits)) + list(a_digits)
    b = [0] * (length - len(b_digits)) + list(b_digits)

    result = []
    carry = 0
    # Right to left — the direction carry propagates
    for i in range(length - 1, -1, -1):
        incoming_carry = carry
        col_sum = a[i] + b[i] + incoming_carry
        digit = col_sum % base   # this column's digit
        carry = col_sum // base  # propagate upward
        result.append(digit)
        if trace:
            place = length - 1 - i
            print(
                f"  base^{place}: {a[i]} + {b[i]} + carry {incoming_carry} "
                f"= {col_sum}; write {digit}, carry {carry}"
            )

    if carry:
        result.append(carry)

    result.reverse()
    return result


def show_addition(a: int, b: int, base: int = 10, *, trace: bool = False) -> None:
    a_d = to_base(a, base)
    b_d = to_base(b, base)
    sum_d = add_positional(a_d, b_d, base, trace=trace)
    label = {2: "binary", 8: "octal", 10: "decimal", 16: "hex"}.get(base, f"base-{base}")
    a_s = digits_to_str(a_d, base)
    b_s = digits_to_str(b_d, base)
    s_s = digits_to_str(sum_d, base)
    width = max(len(a_s), len(b_s), len(s_s)) + 2
    print(f"  Addition in {label} (base {base}):")
    print(f"    {a_s:>{width}}")
    print(f"  + {b_s:>{width}}")
    print(f"    {'—'*width}")
    print(f"    {s_s:>{width}}")
    assert from_base(sum_d, base) == a + b, "BUG: result doesn't match Python's addition"
    print(f"    ✓  (= {a + b} in decimal)")


# ---------------------------------------------------------------------------
# 3. What the zero placeholder does — breaking it on purpose
# ---------------------------------------------------------------------------

def show_zero_placeholder_matters() -> None:
    """
    Illustrate that zero as a placeholder digit is *load-bearing*.
    Without it, 1024 and 124 and 14 would be indistinguishable in a
    non-zero-padded system.
    """
    print("\n--- Why zero is load-bearing ---")
    examples = [1024, 1204, 1240, 1004, 1000]
    for n in examples:
        digits = to_base(n, 10)
        print(f"  {n:>5}  →  digit list: {digits}")
    print()
    print("  Each number has a UNIQUE digit list only because 0 can appear.")
    print("  Strip all zeros from the digit list and you lose the number:")
    for n in examples:
        digits = to_base(n, 10)
        stripped = [d for d in digits if d != 0]
        print(f"  {n:>5}  →  strip zeros → {stripped}  "
              f"{'(ambiguous!)' if stripped != digits else '(unchanged)'}")


# ---------------------------------------------------------------------------
# 4. Roman numeral contrast — no column algorithm
# ---------------------------------------------------------------------------

ROMAN_VALUES = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100,  "C"), (90,  "XC"), (50,  "L"), (40,  "XL"),
    (10,   "X"), (9,   "IX"), (5,   "V"), (4,   "IV"),
    (1,    "I"),
]


def to_roman(n: int) -> str:
    """Convert n to Roman numeral string (1 ≤ n ≤ 3999)."""
    if not 1 <= n <= 3999:
        raise ValueError(f"Roman numeral input must be in [1, 3999], got {n}")
    result = ""
    for value, symbol in ROMAN_VALUES:
        while n >= value:
            result += symbol
            n -= value
    return result


def add_roman(a: int, b: int) -> str:
    """
    'Add' two numbers as Roman numerals.
    There is no column algorithm. We have to go through the integer value.
    The function exists only to show the contrast — it is not an algorithm
    ON the Roman representation; it is an algorithm that IGNORES it.
    """
    if a < 1 or b < 1:
        raise ValueError("Roman numeral operands must be positive")
    return to_roman(a + b)


def show_roman_contrast() -> None:
    pairs = [(14, 9), (47, 58), (399, 401)]
    print("\n--- Roman numeral contrast ---")
    print("  No column addition algorithm exists for Roman numerals.")
    print("  To 'add' XIV + IX you must mentally convert, compute, re-encode.")
    print()
    for a, b in pairs:
        ra, rb, rs = to_roman(a), to_roman(b), to_roman(a + b)
        print(f"  {ra} + {rb} = {rs}")
        print(f"    (i.e. {a} + {b} = {a+b}  — you need the integers to get there)")
        # Show the positional version to highlight the contrast
        a_d = to_base(a, 10)
        b_d = to_base(b, 10)
        sum_d = add_positional(a_d, b_d, 10)
        print(f"    Positional: {digits_to_str(a_d,10)} + {digits_to_str(b_d,10)} "
              f"= {digits_to_str(sum_d,10)}  (column algorithm, no mental detour)")
        print()


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Positional notation and zero: why arithmetic is algorithmic")
    print("=" * 60)

    print("\n--- Base conversion ---")
    for n in [42, 255, 1000, 2024]:
        for base in [2, 8, 16]:
            show_base_conversion(n, base)
        print()

    print("\n--- Multi-digit addition with carry ---")
    show_addition(347, 485, base=10, trace=True)
    print()
    show_addition(347, 485, base=2)   # same numbers, same algorithm, base 2
    print()
    show_addition(255, 1,   base=16)  # 0xFF + 1 = 0x100
    print()
    show_addition(7,   1,   base=2)   # carry chain: 111 + 1 = 1000

    show_zero_placeholder_matters()

    show_roman_contrast()

    print("=" * 60)
    print("  All assertions passed.")
    print("=" * 60)
