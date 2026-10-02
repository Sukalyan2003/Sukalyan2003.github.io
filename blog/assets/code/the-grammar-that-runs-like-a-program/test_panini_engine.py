"""
Tests for the toy Pāṇini-style rule engine.

Run with:  python -m pytest test_panini_engine.py -v
       or: python test_panini_engine.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from panini_engine import PaniniEngine, Rule, DEMO_RULES


ENGINE = PaniniEngine(DEMO_RULES)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def surface(form: str) -> str:
    return ENGINE.derive(form).surface


def steps(form: str) -> list[str]:
    return [s.rule_name for s in ENGINE.derive(form).steps]


# ---------------------------------------------------------------------------
# Vowel sandhi
# ---------------------------------------------------------------------------

def test_a_plus_a_merges_to_long_A():
    assert surface("rAm|a|aZva") == "rAm|AZva"
    assert steps("rAm|a|aZva") == ["6.1.101"]

def test_a_plus_i_guna():
    assert surface("rAm|a|iti") == "rAm|eti"
    assert steps("rAm|a|iti") == ["6.1.102"]

def test_a_plus_u_guna():
    assert surface("rAm|a|uvAca") == "rAm|ovAca"
    assert steps("rAm|a|uvAca") == ["6.1.103"]

# ---------------------------------------------------------------------------
# Homogeneous coalescence (apavāda — exception over general rule)
# The high-priority rules 6.1.77 / 6.1.78 must fire before the guṇa rules
# could mis-handle them.
# ---------------------------------------------------------------------------

def test_i_plus_i_apavada():
    """6.1.77 (priority 15) must fire, not the lower-priority guṇa rules."""
    result = ENGINE.derive("kav|i|iti")
    assert result.surface == "kav|Iti"
    assert result.steps[0].rule_name == "6.1.77"

def test_u_plus_u_apavada():
    result = ENGINE.derive("sAdh|u|uvAca")
    assert result.surface == "sAdh|UvAca"
    assert result.steps[0].rule_name == "6.1.78"

# ---------------------------------------------------------------------------
# Context-sensitive consonant sandhi
# ---------------------------------------------------------------------------

def test_t_voices_before_voiced_stop():
    assert surface("tatgacchati") == "tadgacchati"
    assert steps("tatgacchati") == ["8.4.53"]

def test_k_voices_before_voiced_stop():
    assert surface("vakbodha") == "vagbodha"
    assert steps("vakbodha") == ["8.4.54"]

def test_consonant_rule_does_not_fire_before_unvoiced():
    # 't' before 'c' (voiceless) should not change
    assert surface("tatca") == "tatca"
    assert steps("tatca") == []

# ---------------------------------------------------------------------------
# Visarga sandhi — specific exception vs. general rule
# ---------------------------------------------------------------------------

def test_visarga_specific_rule_fires_for_aH_plus_a():
    """8.3.17 (priority 9) must outrank 8.3.15 (priority 8)."""
    result = ENGINE.derive("saH|api")
    assert result.surface == "saopi"
    assert result.steps[0].rule_name == "8.3.17"

def test_visarga_general_rule_fires_before_other_vowel():
    """8.3.15 fires when 8.3.17's left-context condition isn't met."""
    result = ENGINE.derive("namaH|iti")
    assert result.surface == "namariti"
    assert result.steps[0].rule_name == "8.3.15"

# ---------------------------------------------------------------------------
# No-op: no rule should fire on an already-correct string
# ---------------------------------------------------------------------------

def test_no_rules_fire_on_plain_consonants():
    assert surface("namaste") == "namaste"
    assert steps("namaste") == []

# ---------------------------------------------------------------------------
# Derivation trace integrity
# ---------------------------------------------------------------------------

def test_derivation_result_has_correct_before_after():
    result = ENGINE.derive("rAm|a|iti")
    assert len(result.steps) == 1
    step = result.steps[0]
    assert step.before == "rAm|a|iti"
    assert step.after  == "rAm|eti"
    assert step.rule_name == "6.1.102"

def test_priority_ordering():
    """
    A custom rule set: two rules match the same target, only the higher-priority
    one should fire.
    """
    high = Rule(name="HIGH", target="x|y", replace="Z", priority=10, note="high wins")
    low  = Rule(name="LOW",  target="x|y", replace="W", priority=1,  note="should not fire")
    eng  = PaniniEngine([low, high])  # intentionally list low first
    result = eng.derive("ax|yb")
    assert result.surface == "aZb"
    assert result.steps[0].rule_name == "HIGH"


# ---------------------------------------------------------------------------
# Run as script
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import traceback
    tests = [
        test_a_plus_a_merges_to_long_A,
        test_a_plus_i_guna,
        test_a_plus_u_guna,
        test_i_plus_i_apavada,
        test_u_plus_u_apavada,
        test_t_voices_before_voiced_stop,
        test_k_voices_before_voiced_stop,
        test_consonant_rule_does_not_fire_before_unvoiced,
        test_visarga_specific_rule_fires_for_aH_plus_a,
        test_visarga_general_rule_fires_before_other_vowel,
        test_no_rules_fire_on_plain_consonants,
        test_derivation_result_has_correct_before_after,
        test_priority_ordering,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception:
            print(f"  FAIL  {t.__name__}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
