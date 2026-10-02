"""
TOY MODEL — illustrative only.
This is NOT a real Sanskrit grammar engine and does NOT cover the full Ashtadhyayi.
It demonstrates the *structural ideas* behind Panini's rule system:
  - Ordered, named rules applied in sequence (like sutras)
  - Context-sensitive rules (replacement depends on surrounding context)
  - Metarules that govern how other rules interact
  - Derivation traces so you can see exactly what fired and why

Concepts modelled here (simplified):
  - Rule ordering and priority: later rules in the list override earlier ones
    unless a priority weight says otherwise (analogous to the utsarga/apavada
    general-rule / exception hierarchy in the Ashtadhyayi).
  - Anuvritta-style carry-forward: a "domain" annotation on a rule means the
    rule only fires when a prior "governing rule" has been declared active.
  - Context-sensitive replacement: rules match LEFT and RIGHT environments
    as well as the target element, mirroring Panini's A=>B/C_D notation.
  - Asiddha-like ordering: within a marked section, earlier rules are treated
    as not yet applied when later rules look back.

This is a teaching aid. Do not use it to generate real Sanskrit.

TODO: Add more rules (e.g., a + i → e, as in mahā + īśa = maheśa)

"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    """
    A single rewrite rule.

    Fields:
      name    — short label (e.g. "6.1.77")
      target  — substring to look for (the element being replaced)
      replace — what to write instead
      left    — regex that must match immediately to the LEFT of target
      right   — regex that must match immediately to the RIGHT of target
      domain  — if set, rule only fires when this governing rule is active
      priority— higher number = applied first when two rules compete
      note    — human-readable explanation
    """
    name: str
    target: str
    replace: str
    left: Optional[str] = None
    right: Optional[str] = None
    domain: Optional[str] = None
    priority: int = 0
    note: str = ""


@dataclass
class DerivationStep:
    rule_name: str
    before: str
    after: str
    note: str


@dataclass
class DerivationResult:
    surface: str
    steps: list[DerivationStep] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class PaniniEngine:
    """
    Ordered, context-sensitive rewrite-rule engine.

    Rules are stored in priority order (highest priority first).
    Within the same priority, the rule listed earlier wins — this mirrors
    the 'earlier in the grammar wins' default of the Ashtadhyayi (before
    Rajpopat's 2022 re-reading, which reinterprets the conflict metarule).

    The engine keeps applying rules until no rule fires (fixpoint), up to
    a configurable maximum number of passes.
    """

    def __init__(self, rules: list[Rule], max_passes: int = 20):
        # Sort by descending priority so higher-priority rules are tried first
        self.rules = sorted(rules, key=lambda r: -r.priority)
        self.max_passes = max_passes

    def _try_rule(self, form: str, rule: Rule) -> Optional[str]:
        """
        Try to apply a single rule to `form`.  Returns new form if the rule
        fired, otherwise None.

        We build a regex that captures LEFT + TARGET + RIGHT together so
        variable-length lookbehind is never needed (Python re doesn't allow it).
        The matched left/right context is preserved verbatim; only the target
        portion is replaced.
        """
        # Groups: (1) left_ctx  (2) target  (3) right_ctx
        left_pat  = f"({rule.left})"  if rule.left  else "()"
        right_pat = f"({rule.right})" if rule.right else "()"

        pattern = left_pat + f"({re.escape(rule.target)})" + right_pat

        # replacement: keep group 1 (left context), insert replace, keep group 3
        repl = r"\g<1>" + rule.replace + r"\g<3>"

        try:
            new_form, n = re.subn(pattern, repl, form, count=1)
        except re.error:
            return None

        return new_form if n > 0 else None

    def derive(self, form: str, active_domains: Optional[set[str]] = None) -> DerivationResult:
        """
        Apply rules to `form` until fixpoint, returning the surface form and trace.

        active_domains: set of governing-rule names currently in scope
                        (simulates anuvritta / adhikara carry-forward).
        """
        if active_domains is None:
            active_domains = set()

        steps: list[DerivationStep] = []
        current = form

        for _pass in range(self.max_passes):
            fired = False
            for rule in self.rules:
                # Domain check (anuvritta-style)
                if rule.domain and rule.domain not in active_domains:
                    continue

                new_form = self._try_rule(current, rule)

                if new_form is not None and new_form != current:
                    steps.append(DerivationStep(
                        rule_name=rule.name,
                        before=current,
                        after=new_form,
                        note=rule.note,
                    ))
                    current = new_form
                    fired = True
                    break  # restart rule scan after each application

            if not fired:
                break  # fixpoint reached

        return DerivationResult(surface=current, steps=steps)

    def derive_verbose(self, form: str, active_domains: Optional[set[str]] = None) -> str:
        """Return a human-readable derivation trace."""
        result = self.derive(form, active_domains)
        lines = [f"Input:  {form!r}"]
        if not result.steps:
            lines.append("  (no rules fired)")
        for i, step in enumerate(result.steps, 1):
            lines.append(f"  Step {i}: [{step.rule_name}]  {step.before!r} → {step.after!r}")
            if step.note:
                lines.append(f"          note: {step.note}")
        lines.append(f"Output: {result.surface!r}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Example rule set: a handful of simplified Sanskrit sandhi / morphology rules
# These are ILLUSTRATIVE simplifications, not faithful reproductions.
# ---------------------------------------------------------------------------

# The Shiva-sutras organise Sanskrit phonemes into compact "pratyahara" groups.
# Here we just name the phoneme classes we use so the rules can reference them.
VOWELS = "aeiouAEIOU"  # rough stand-in for Sanskrit vowels
VOICED_STOPS = "bgdGD"

DEMO_RULES: list[Rule] = [
    # --- Vowel sandhi (vowel + vowel at morpheme boundary) ---
    # Input convention: the boundary is marked with '|'; the engine treats the
    # string as a sequence of segments.  We use simple ASCII proxies:
    #   A/E/I/O/U = long vowels  (ā/ē/ī/ō/ū)
    #   a/e/i/o/u = short vowels

    Rule(
        name="6.1.101",
        target="a|a",
        replace="A",
        note="a + a → ā  (two short a's merge to long ā; vowel sandhi)",
        priority=10,
    ),
    Rule(
        name="6.1.102",
        target="a|i",
        replace="e",
        note="a + i → e  (guṇa coalescence)",
        priority=10,
    ),
    Rule(
        name="6.1.103",
        target="a|u",
        replace="o",
        note="a + u → o  (guṇa coalescence)",
        priority=10,
    ),

    # --- Homogeneous coalescence — exception (apavāda) over guṇa ---
    # Higher priority so these fire before the guṇa rules can mis-apply.

    Rule(
        name="6.1.77",
        target="i|i",
        replace="I",
        note="i + i → ī  (homogeneous coalescence; apavāda beats guṇa rule)",
        priority=15,
    ),
    Rule(
        name="6.1.78",
        target="u|u",
        replace="U",
        note="u + u → ū  (homogeneous coalescence; apavāda beats guṇa rule)",
        priority=15,
    ),

    # --- Final-consonant voicing before voiced stops (context-sensitive) ---
    # RIGHT context is a voiced stop class.

    Rule(
        name="8.4.53",
        target="t",
        replace="d",
        right="[bgdGDjzv]",
        note="t → d before a voiced consonant  (e.g. tat+gacchati → tad gacchati)",
        priority=5,
    ),
    Rule(
        name="8.4.54",
        target="k",
        replace="g",
        right="[bgdGDjzv]",
        note="k → g before a voiced consonant",
        priority=5,
    ),

    # --- Visarga sandhi ---
    # Rule 8.3.17 (specific: aH+a) outranks 8.3.15 (general: H before vowel).

    Rule(
        name="8.3.17",
        target="H|a",
        replace="o",
        left="a",
        note="aḥ + a → o  (e.g. saḥ api → so'pi; specific exception)",
        priority=9,
    ),
    Rule(
        name="8.3.15",
        target="H|",
        replace="r",
        right="[aeiouAEIOU]",
        note="ḥ → r before any vowel  (general rule)",
        priority=8,
    ),
]


# ---------------------------------------------------------------------------
# CLI / demo
# ---------------------------------------------------------------------------

def run_demos():
    engine = PaniniEngine(DEMO_RULES)

    demos = [
        # (description, input_string, active_domains)
        # Boundary between morphemes is marked with '|'
        ("a + a  →  ā  (vowel sandhi)",          "rAm|a|aZva",    None),
        ("a + i  →  e  (guṇa coalescence)",      "rAm|a|iti",     None),
        ("a + u  →  o  (guṇa coalescence)",      "rAm|a|uvAca",   None),
        ("i + i  →  ī  (apavāda exception)",     "kav|i|iti",     None),
        ("u + u  →  ū  (apavāda exception)",     "sAdh|u|uvAca",  None),
        ("t → d before voiced stop (ctx-sense)", "tatgacchati",   None),
        ("k → g before voiced stop (ctx-sense)", "vakbodha",      None),
        ("ḥ + a  →  o  (visarga specific rule)", "saH|api",       None),
        ("ḥ + i  →  r  (visarga general rule)",  "namaH|iti",     None),
    ]

    print("=" * 60)
    print("Pāṇini-style Rule Engine  —  TOY / ILLUSTRATIVE MODEL")
    print("Rules are simplified; not a real Sanskrit grammar.")
    print("=" * 60)
    print()

    for desc, form, domains in demos:
        print(f"[ {desc} ]")
        print(engine.derive_verbose(form, domains))
        print()


if __name__ == "__main__":
    run_demos()
