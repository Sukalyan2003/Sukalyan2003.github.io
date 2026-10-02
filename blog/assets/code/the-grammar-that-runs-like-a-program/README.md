# Pāṇini-style Rule Engine -- Toy / Illustrative Model

**This is a teaching aid, not a real Sanskrit grammar engine.**
It demonstrates the *structural ideas* behind Pāṇini's Aṣṭādhyāyī using a
small Python rewrite-rule system. The rules are simplified analogues --
do not use this to generate real Sanskrit.

## What it shows

| Pāṇini concept | How the engine models it |
|---|---|
| Sūtra ordering | Rules are applied in priority order (highest first) |
| Context-sensitive rules | `left` / `right` regex fields gate each rule |
| Apavāda (exception > general) | Higher `priority` weight beats lower |
| Anuvṛtti (carry-forward) | `domain` field -- rule only fires inside active domain |
| Derivation trace | Every step logged with rule name, before, after, note |

## Run the demo

```
python panini_engine.py
```

## Run the tests

```
python test_panini_engine.py
# or, if pytest is available:
python -m pytest test_panini_engine.py -v
```

## Requirements

Python 3.8+. Standard library only -- no extra packages needed.

---

## Real output (pasted verbatim)

```
============================================================
Pāṇini-style Rule Engine  --  TOY / ILLUSTRATIVE MODEL
Rules are simplified; not a real Sanskrit grammar.
============================================================

[ a + a  →  ā  (vowel sandhi) ]
Input:  'rAm|a|aZva'
  Step 1: [6.1.101]  'rAm|a|aZva' → 'rAm|AZva'
          note: a + a → ā  (two short a's merge to long ā; vowel sandhi)
Output: 'rAm|AZva'

[ a + i  →  e  (guṇa coalescence) ]
Input:  'rAm|a|iti'
  Step 1: [6.1.102]  'rAm|a|iti' → 'rAm|eti'
          note: a + i → e  (guṇa coalescence)
Output: 'rAm|eti'

[ a + u  →  o  (guṇa coalescence) ]
Input:  'rAm|a|uvAca'
  Step 1: [6.1.103]  'rAm|a|uvAca' → 'rAm|ovAca'
          note: a + u → o  (guṇa coalescence)
Output: 'rAm|ovAca'

[ i + i  →  ī  (apavāda exception) ]
Input:  'kav|i|iti'
  Step 1: [6.1.77]  'kav|i|iti' → 'kav|Iti'
          note: i + i → ī  (homogeneous coalescence; apavāda beats guṇa rule)
Output: 'kav|Iti'

[ u + u  →  ū  (apavāda exception) ]
Input:  'sAdh|u|uvAca'
  Step 1: [6.1.78]  'sAdh|u|uvAca' → 'sAdh|UvAca'
          note: u + u → ū  (homogeneous coalescence; apavāda beats guṇa rule)
Output: 'sAdh|UvAca'

[ t → d before voiced stop (ctx-sense) ]
Input:  'tatgacchati'
  Step 1: [8.4.53]  'tatgacchati' → 'tadgacchati'
          note: t → d before a voiced consonant  (e.g. tat+gacchati → tad gacchati)
Output: 'tadgacchati'

[ k → g before voiced stop (ctx-sense) ]
Input:  'vakbodha'
  Step 1: [8.4.54]  'vakbodha' → 'vagbodha'
          note: k → g before a voiced consonant
Output: 'vagbodha'

[ ḥ + a  →  o  (visarga specific rule) ]
Input:  'saH|api'
  Step 1: [8.3.17]  'saH|api' → 'saopi'
          note: aḥ + a → o  (e.g. saḥ api → so'pi; specific exception)
Output: 'saopi'

[ ḥ + i  →  r  (visarga general rule) ]
Input:  'namaH|iti'
  Step 1: [8.3.15]  'namaH|iti' → 'namariti'
          note: ḥ → r before any vowel  (general rule)
Output: 'namariti'
```

### Test run output

```
  PASS  test_a_plus_a_merges_to_long_A
  PASS  test_a_plus_i_guna
  PASS  test_a_plus_u_guna
  PASS  test_i_plus_i_apavada
  PASS  test_u_plus_u_apavada
  PASS  test_t_voices_before_voiced_stop
  PASS  test_k_voices_before_voiced_stop
  PASS  test_consonant_rule_does_not_fire_before_unvoiced
  PASS  test_visarga_specific_rule_fires_for_aH_plus_a
  PASS  test_visarga_general_rule_fires_before_other_vowel
  PASS  test_no_rules_fire_on_plain_consonants
  PASS  test_derivation_result_has_correct_before_after
  PASS  test_priority_ordering

13 passed, 0 failed
```

## Input notation

The `|` character marks a morpheme boundary (where sandhi can apply).
ASCII proxies for Sanskrit sounds used in demos:

| ASCII | Approximate Sanskrit sound |
|---|---|
| A | ā (long a) |
| I | ī (long i) |
| U | ū (long u) |
| H | ḥ (visarga) |
| Z | ś (palatal sibilant) |

## Files

```
panini_engine.py        -- engine + demo rules + CLI demo
test_panini_engine.py   -- 13 unit tests
README.md               -- this file
```
