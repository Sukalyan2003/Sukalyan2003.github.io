# Illustrative rewrite engine

A small Python rule engine for the Pāṇini post, not a Sanskrit grammar implementation.

## Run

```bash
python3 panini_engine.py
python3 test_panini_engine.py
# Or, with pytest installed:
python3 -m pytest -q test_panini_engine.py
```

Python standard library only for the engine and direct test runner.

## What the labels mean

The a+a, i+i, and u+u examples are restricted illustrations of vowel lengthening under
6.1.101. The a+i and a+u examples illustrate guṇa under 6.1.87. These targets do not
overlap, so priority is not what selects between them. Sutra references identify the
relevant vowel rule, not a complete derivation with all of its grammatical conditions.

The `toy-t-voicing` and `toy-k-voicing` rules are simplified context-dependent rewrites,
without a claim that one numbered Sanskrit rule alone produces the whole derivation.
The `toy-specific` and `toy-general` rules use an invented alphabet: both match x|y,
but the more specific rule wins when a is on the left. They demonstrate priority without
passing off incorrect visarga rewrites as Sanskrit.

The engine does not implement full phonology, grammatical domains, asiddha visibility,
or Rajpopat's proposed conflict rule. ASCII uppercase A/I/U represents long vowels in
these examples; | is an explicit input boundary marker.

## Actual output excerpt

```text
[ a + i  →  e  (guṇa coalescence) ]
Input:  'rAm|a|iti'
  Step 1: [6.1.87]  'rAm|a|iti' → 'rAm|eti'
          note: a + i → e  (guṇa coalescence)
Output: 'rAm|eti'
```

## Sources for the vowel labels

- https://www.learnsanskrit.org/vyakarana/sounds/ac-sandhi/
- https://www.learnsanskrit.org/static/pdf/vyakarana.pdf

Tests check the small model's output, trace labels, context restrictions, and priority
between genuinely competing invented rules. They do not establish linguistic completeness
or certify all Sanskrit rule attributions.
