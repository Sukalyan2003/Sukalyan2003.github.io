"""
Pingala's Chandahsastra — combinatorics in Sanskrit prosody (~3rd–2nd c. BCE)

This module implements the six pratyaya (algorithmic procedures) from the
Chandahsastra, plus the meru-prastara (Pascal's triangle) and the
matra-vritta Fibonacci count.

IMPORTANT HISTORICAL CAVEATS (reflected in the code's own docstrings):
- The laghu/guru patterns are Pingala's. The binary place-value reading is
  a structural parallel that modern scholars make explicit; Pingala was doing
  prosody, not base-2 arithmetic.
- The meru-prastara (Pascal's triangle) is attributed to Halayudha's 10th-c.
  commentary on Pingala's cryptic sutra "pare purnam iti."
- The Fibonacci sequence from matra-vritta counting is formalized by
  Virahanka (~6th–8th c.), Gopala (before 1135 CE), and Hemachandra (1150 CE).

Educational/toy implementation. Stdlib only.

TODO: Run it on a real sankrit phrase instead of abstract symbols
"""

from __future__ import annotations
from itertools import product


# ---------------------------------------------------------------------------
# 0.  Syllable representation
# ---------------------------------------------------------------------------

L = "L"  # laghu — short syllable (one mora)
G = "G"  # guru  — long  syllable (two morae)


# ---------------------------------------------------------------------------
# 1.  Pratyaya 1: Prastara — enumerate all patterns for n syllables
#     (= binary counting from 000…0 to 111…1, LSB=Laghu)
# ---------------------------------------------------------------------------

def prastara(n: int) -> list[tuple[str, ...]]:
    """
    List all 2**n laghu/guru patterns for n syllables, in Pingala's historical order.

    Pingala's prastara numbers rows starting from all-G (row 1 = GGG…G) down to
    all-L (row 2**n = LLL…L). This is consistent with the nashta/uddishta algorithms
    as preserved in the Chandahsastra: nashta(1, n) = GGG…G.

    The structural parallel to binary: within each row, the leftmost syllable is the
    least significant position (L=0, G=1). Row k corresponds to the bit pattern of
    (2**n - k), not k itself. This reverse ordering is a noted feature: "Pingala's
    binary representation increases towards the right, and not to the left as modern
    binary numbers usually do." (Wikipedia, citing van Nooten)

    Returns a list of 2**n tuples, each of length n.
    """
    rows = []
    for value in range(2 ** n - 1, -1, -1):  # descending: GGG first, LLL last
        # extract n bits, LSB first
        pattern = tuple(G if (value >> i) & 1 else L for i in range(n))
        rows.append(pattern)
    return rows


def print_prastara(n: int) -> None:
    rows = prastara(n)
    print(f"\n=== Prastara for n={n} ({2**n} patterns, Pingala's historical order) ===")
    print(f"  Row 1 = all-G (guru), Row {2**n} = all-L (laghu)")
    print(f"{'Row':>4}  {'Pattern (laghu=L, guru=G)':30}  modern binary (MSB-left)")
    for i, row in enumerate(rows):
        pat = " ".join(row)
        # modern binary value: reverse read with G=1, L=0
        modern_val = sum((1 if s == G else 0) * (2 ** (n - 1 - j)) for j, s in enumerate(reversed(row)))
        print(f"{i+1:>4}  {pat:30}  {modern_val:0{n}b}  ({modern_val})")


# ---------------------------------------------------------------------------
# 2.  Pratyaya 2: Sankhya — total count of patterns
#     (trivially 2**n; Pingala's rule halves repeatedly)
# ---------------------------------------------------------------------------

def sankhya(n: int) -> int:
    """Total number of varna-vrittas (syllable patterns) for length n = 2**n."""
    count = 1
    for _ in range(n):
        count *= 2
    return count


# ---------------------------------------------------------------------------
# 3.  Pratyaya 3: Nashta — given row number k, find the pattern
#     (= decimal → binary, but Pingala-ordered, 1-indexed)
#     Pingala's rule (Chandahsastra 8.24-25):
#       Start with row number k.
#       If k is even: write L, halve k.
#       If k is odd:  write G, add 1, halve k.
#       Repeat n times.
# ---------------------------------------------------------------------------

def nashta(k: int, n: int) -> tuple[str, ...]:
    """
    Return the k-th pattern (1-indexed) in the prastara of length n.

    The resulting pattern is equivalent to writing (2**n - k) as an
    n-bit binary value, reversing it because Pingala's least-significant
    position is on the left, then mapping 0→L and 1→G. Pingala's procedure
    reaches that pattern without explicitly naming binary arithmetic.
    """
    if not (1 <= k <= 2 ** n):
        raise ValueError(f"k={k} out of range for n={n} (1..{2**n})")
    pattern = []
    val = k
    for _ in range(n):
        if val % 2 == 0:
            pattern.append(L)
            val //= 2
        else:
            pattern.append(G)
            val += 1
            val //= 2
    return tuple(pattern)


def explain_row(k: int, n: int) -> str:
    """Show the exact modern binary relationship for a historical row."""
    pattern = nashta(k, n)
    value = 2 ** n - k
    binary = f"{value:0{n}b}"
    reversed_binary = binary[::-1]
    pattern_text = "".join(pattern)
    decoded = "".join(G if bit == "1" else L for bit in reversed_binary)
    assert decoded == pattern_text
    return (
        f"row {k} → 2^{n} − {k} = {value} → {binary}₂ "
        f"→ reverse → {reversed_binary} → {pattern_text}"
    )


# ---------------------------------------------------------------------------
# 4.  Pratyaya 4: Uddishta — given a pattern, find its row number
#     (= binary → decimal, Pingala-ordered, 1-indexed)
#     Pingala's rule: scan pattern from right, start at 1.
#       For each G: double and subtract 1.
#       For each L: double.
#     (Equivalent to reading bits from MSB, accumulating place values.)
# ---------------------------------------------------------------------------

def uddishta(pattern: tuple[str, ...]) -> int:
    """
    Return the row number (1-indexed) of the given pattern in the prastara.

    Pingala's scan-from-right procedure:
      val = 1
      for each syllable from rightmost to leftmost:
          if L: val = 2 * val
          if G: val = 2 * val - 1
    """
    val = 1
    for syllable in reversed(pattern):
        if syllable == L:
            val = 2 * val
        else:  # G
            val = 2 * val - 1
    return val


def verify_nashta_uddishta(n: int) -> bool:
    """Verify nashta and uddishta are inverses for all patterns of length n."""
    ok = True
    for k in range(1, 2 ** n + 1):
        pat = nashta(k, n)
        k2 = uddishta(pat)
        if k != k2:
            print(f"  MISMATCH: nashta({k},{n})={pat} -> uddishta={k2}")
            ok = False
    return ok


# ---------------------------------------------------------------------------
# 5.  Pratyaya 5: Lagakriya — how many patterns have exactly r laghu syllables?
#     Answer: C(n, r) — binomial coefficient.
#     Pingala's method computed these; the triangular arrangement is
#     meru-prastara (Halayudha, 10th c.).
# ---------------------------------------------------------------------------

def lagakriya(n: int, r: int) -> int:
    """
    Count patterns of length n with exactly r laghu syllables = C(n, r).

    Uses Pascal's recurrence (the same recurrence underlying meru-prastara):
      C(n, 0) = C(n, n) = 1
      C(n, r) = C(n-1, r-1) + C(n-1, r)
    """
    if r < 0 or r > n:
        return 0
    if r == 0 or r == n:
        return 1
    return lagakriya(n - 1, r - 1) + lagakriya(n - 1, r)


def print_lagakriya(n: int) -> None:
    total = 0
    print(f"\n=== Lagakriya for n={n} ===")
    print(f"  {'r (# laghu)':>12}  {'count C(n,r)':>12}")
    for r in range(n + 1):
        c = lagakriya(n, r)
        total += c
        print(f"  {r:>12}  {c:>12}")
    print(f"  {'TOTAL':>12}  {total:>12}  (= 2^{n} = {2**n})")


# ---------------------------------------------------------------------------
# 6.  Meru-Prastara — Pascal's triangle / binomial coefficient table
#     Halayudha (~10th c. CE) built this explicitly in his commentary on
#     Pingala's cryptic sutra "pare purnam iti" (Chandahsastra 8.34).
#     Pingala's own text is not fully legible without a commentary;
#     the triangular construction is Halayudha's exposition.
# ---------------------------------------------------------------------------

def meru_prastara(rows: int) -> list[list[int]]:
    """
    Build the meru-prastara (Pascal's triangle) for `rows` rows.

    Row n (0-indexed) contains the binomial coefficients C(n, 0..n).
    Row n of the triangle gives lagakriya values for n-syllable meters:
      C(n,0) patterns with 0 laghu, C(n,1) with 1 laghu, …, C(n,n) with n laghu.
    """
    triangle = []
    for n in range(rows):
        row = [lagakriya(n, r) for r in range(n + 1)]
        triangle.append(row)
    return triangle


def print_meru_prastara(rows: int) -> None:
    triangle = meru_prastara(rows)
    print(f"\n=== Meru-Prastara (Pascal's Triangle), {rows} rows ===")
    print("  (Halayudha ~10th c. CE made this triangular arrangement explicit)")
    width = rows * 4
    for n, row in enumerate(triangle):
        row_str = "  ".join(f"{v:2}" for v in row)
        print(f"  n={n}:  {row_str.center(width)}")
    print()
    print("  Row n gives C(n,0)..C(n,n): the count of n-syllable patterns")
    print("  with 0,1,...,n laghu syllables. Sum of row n = 2^n.")


# ---------------------------------------------------------------------------
# 7.  Matra-vritta count → Fibonacci numbers
#     Matra-vrittas: meters defined by mora count (matras), not syllable count.
#     Laghu = 1 mora, Guru = 2 morae.
#     f(n) = ways to fill exactly n morae = f(n-1) + f(n-2).
#     Formalized by Virahanka (~6th–8th c.), Gopala (before 1135 CE),
#     Hemachandra (1150 CE) — all before Fibonacci (1202 CE).
# ---------------------------------------------------------------------------

def matra_vritta_count(n: int) -> int:
    """
    Count the number of ways to fill n morae using laghu (1 mora) and guru (2 morae).

    Recurrence: f(n) = f(n-1) + f(n-2)
      f(0) = 1  (the empty arrangement)
      f(1) = 1  (only: L)
      f(2) = 2  (LL or G)
    This is the Fibonacci sequence, starting at index 1.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 1
    if n == 1:
        return 1
    if n == 2:
        return 2
    a, b = 1, 2
    for _ in range(n - 2):
        a, b = b, a + b
    return b


def list_matra_vritta(n: int) -> list[tuple[str, ...]]:
    """List all ways to fill n morae with L (1) and G (2) syllables."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return [()]
    result = []
    # append L (costs 1 mora)
    for rest in list_matra_vritta(n - 1):
        result.append((L,) + rest)
    # append G (costs 2 morae)
    if n >= 2:
        for rest in list_matra_vritta(n - 2):
            result.append((G,) + rest)
    return result


def print_matra_vritta(max_n: int) -> None:
    print(f"\n=== Matra-Vritta counts (Fibonacci via Virahanka/Gopala/Hemachandra) ===")
    print(f"  {'n (morae)':>10}  {'count':>6}  {'patterns'}")
    for n in range(1, max_n + 1):
        count = matra_vritta_count(n)
        patterns = list_matra_vritta(n)
        pat_str = ", ".join(" ".join(p) for p in patterns)
        print(f"  {n:>10}  {count:>6}  {pat_str}")
    print()
    seq = [matra_vritta_count(n) for n in range(1, max_n + 1)]
    print(f"  Sequence for n=1..{max_n}: {seq}")
    print(f"  This is the Fibonacci sequence (shifted): 1, 2, 3, 5, 8, 13, ...")
    print(f"  Hemachandra (1150 CE) stated: 'Sum of last and the last but one")
    print(f"  numbers is that of the matra-vritta coming next.'")
    print(f"  Fibonacci published Liber Abaci with this sequence in 1202 CE.")


# ---------------------------------------------------------------------------
# 8.  Round-trip demonstration
# ---------------------------------------------------------------------------

def demo_round_trip(n: int) -> None:
    print(f"\n=== Nashta/Uddishta round-trip verification for n={n} ===")
    ok = verify_nashta_uddishta(n)
    if ok:
        print(f"  All {2**n} patterns: nashta(uddishta(p)) == p  ✓")
    # Show a few examples
    examples = [1, 7, 2 ** n // 3, 2 ** n]
    print(f"\n  Sample conversions:")
    print(f"  {'Row k':>6}  {'Pattern':30}  {'Recovered k':>10}")
    for k in examples:
        if 1 <= k <= 2 ** n:
            pat = nashta(k, n)
            k2 = uddishta(pat)
            pat_str = " ".join(pat)
            print(f"  {k:>6}  {pat_str:30}  {k2:>10}  {'✓' if k==k2 else '✗'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 65)
    print("Pingala's Chandahsastra — Combinatorics in Sanskrit Prosody")
    print("  (~3rd–2nd c. BCE, with later elaborations by Halayudha")
    print("   ~10th c. CE, Virahanka ~6th–8th c., Hemachandra 1150 CE)")
    print("=" * 65)

    # Prastara: all patterns for n=3 syllables
    print_prastara(3)

    # Sankhya
    for n in [3, 4, 6]:
        print(f"\nSankhya(n={n}): total patterns = {sankhya(n)}  (= 2^{n})")

    print("\n=== Row 4 through a modern binary lens ===")
    print(f"  {explain_row(4, 3)}")

    # Nashta & Uddishta round trip
    demo_round_trip(4)

    # Lagakriya
    print_lagakriya(6)

    # Meru-Prastara
    print_meru_prastara(8)

    # Matra-Vritta / Fibonacci
    print_matra_vritta(10)

    print("\n" + "=" * 65)
    print("Key historical caveats:")
    print("  1. Pingala enumerated laghu/guru patterns for Sanskrit prosody.")
    print("     The place-value binary reading is a modern structural parallel.")
    print("  2. The meru-prastara (Pascal's triangle) was made explicit by")
    print("     Halayudha in his ~10th-c. commentary Mritasanjeevani.")
    print("  3. The Fibonacci recurrence from matra-vrittas is due to")
    print("     Virahanka, Gopala, and Hemachandra — all before Fibonacci (1202).")
    print("=" * 65)
