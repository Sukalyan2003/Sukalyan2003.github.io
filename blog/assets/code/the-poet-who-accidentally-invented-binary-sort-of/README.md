# Pingala's Chandahsastra - Runnable Demo

Educational Python implementation of the combinatorial procedures from
Pingala's *Chandaḥśāstra* (~3rd–2nd c. BCE), plus the later elaborations
by Halayudha (~10th c. CE) and the Fibonacci connection formalized by
Virahanka, Gopala, and Hemachandra (6th–12th c. CE).

**Stdlib only. No dependencies beyond Python 3.8+.**

## Run

```
python3 pingala.py
```

## Test

```
python3 test_pingala.py
```

Expected: `15 passed, 0 failed`

## What it implements

| Pratyaya (procedure)  | What it does                                    | Modern parallel        |
|-----------------------|-------------------------------------------------|------------------------|
| Prastara              | Enumerate all n-syllable laghu/guru patterns    | Binary counting        |
| Sankhya               | Count total patterns for length n               | 2ⁿ                     |
| Nashta                | Given row number k, find the pattern            | Decimal → binary       |
| Uddishta              | Given pattern, find its row number              | Binary → decimal       |
| Lagakriya             | Count patterns with exactly r laghu syllables   | Binomial coefficient C(n,r) |
| (Meru-prastara)       | Triangular layout of binomial coefficients      | Pascal's triangle      |

Plus: matra-vritta counting → Fibonacci numbers.

## Historical ordering note

Pingala's prastara numbers row 1 as GGG…G (all guru/long) and the final
row as LLL…L (all laghu/short). This is the opposite of the modern binary
convention (000…0 first). The `prastara()` and `nashta()`/`uddishta()`
functions all use this historical ordering.

## Historical caveats (important)

1. Pingala's algorithms are prosodic, not arithmetic. The place-value binary
   reading is a modern structural observation.
2. The meru-prastara (Pascal's triangle) was made *explicit* by **Halayudha**
   in his ~10th-century commentary *Mritasanjeevani* on Pingala's cryptic
   sūtra "pare pūrṇam iti" (8.34). Pingala's own text requires a commentary
   to be fully legible.
3. The Fibonacci recurrence from matra-vritta counting was formalized by
   **Virahanka** (~6th–8th c.), **Gopala** (before 1135 CE), and
   **Hemachandra** (1150 CE) - all before Fibonacci's *Liber Abaci* (1202 CE).

## Actual output (Python 3.12)

```
=================================================================
Pingala's Chandahsastra - Combinatorics in Sanskrit Prosody
  (~3rd–2nd c. BCE, with later elaborations by Halayudha
   ~10th c. CE, Virahanka ~6th–8th c., Hemachandra 1150 CE)
=================================================================

=== Prastara for n=3 (8 patterns, Pingala's historical order) ===
  Row 1 = all-G (guru), Row 8 = all-L (laghu)
 Row  Pattern (laghu=L, guru=G)       modern binary (MSB-left)
   1  G G G                           111  (7)
   2  L G G                           110  (6)
   3  G L G                           101  (5)
   4  L L G                           100  (4)
   5  G G L                           011  (3)
   6  L G L                           010  (2)
   7  G L L                           001  (1)
   8  L L L                           000  (0)

Sankhya(n=3): total patterns = 8  (= 2^3)
Sankhya(n=4): total patterns = 16  (= 2^4)
Sankhya(n=6): total patterns = 64  (= 2^6)

=== Row 4 through a modern binary lens ===
  row 4 → 2^3 − 4 = 4 → 100₂ → reverse → 001 → LLG

=== Nashta/Uddishta round-trip verification for n=4 ===
  All 16 patterns: nashta(uddishta(p)) == p  ✓

  Sample conversions:
   Row k  Pattern                         Recovered k
       1  G G G G                                  1  ✓
       7  G L L G                                  7  ✓
       5  G G L G                                  5  ✓
      16  L L L L                                 16  ✓

=== Lagakriya for n=6 ===
   r (# laghu)  count C(n,r)
             0             1
             1             6
             2            15
             3            20
             4            15
             5             6
             6             1
         TOTAL            64  (= 2^6 = 64)

=== Meru-Prastara (Pascal's Triangle), 8 rows ===
  (Halayudha ~10th c. CE made this triangular arrangement explicit)
  n=0:                  1               
  n=1:                1   1             
  n=2:              1   2   1           
  n=3:            1   3   3   1         
  n=4:          1   4   6   4   1       
  n=5:        1   5  10  10   5   1     
  n=6:      1   6  15  20  15   6   1   
  n=7:    1   7  21  35  35  21   7   1 

  Row n gives C(n,0)..C(n,n): the count of n-syllable patterns
  with 0,1,...,n laghu syllables. Sum of row n = 2^n.

=== Matra-Vritta counts (Fibonacci via Virahanka/Gopala/Hemachandra) ===
   n (morae)   count  patterns
           1       1  L
           2       2  L L, G
           3       3  L L L, L G, G L
           4       5  L L L L, L L G, L G L, G L L, G G
           5       8  L L L L L, L L L G, L L G L, L G L L, L G G, G L L L, G L G, G G L
           6      13  [13 patterns]
           7      21  [21 patterns]
           8      34  [34 patterns]
           9      55  [55 patterns]
          10      89  [89 patterns]

  Sequence for n=1..10: [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
  This is the Fibonacci sequence (shifted): 1, 2, 3, 5, 8, 13, ...
  Hemachandra (1150 CE) stated: 'Sum of last and the last but one
  numbers is that of the matra-vritta coming next.'
  Fibonacci published Liber Abaci with this sequence in 1202 CE.

=================================================================
Key historical caveats:
  1. Pingala enumerated laghu/guru patterns for Sanskrit prosody.
     The place-value binary reading is a modern structural parallel.
  2. The meru-prastara (Pascal's triangle) was made explicit by
     Halayudha in his ~10th-c. commentary Mritasanjeevani.
  3. The Fibonacci recurrence from matra-vrittas is due to
     Virahanka, Gopala, and Hemachandra - all before Fibonacci (1202).
=================================================================
```
