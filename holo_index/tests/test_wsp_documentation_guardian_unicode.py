# -*- coding: utf-8 -*-
"""
WSP Documentation Guardian Unicode Classification Tests

Tests for the Unicode allowlist patch that distinguishes intentional
documentation characters (box drawing, arrows, math) from suspicious
patterns (mojibake, replacement chars).

Per audit 2026-04-26: 42 WSP_framework files had intentional Unicode.
All were box drawing, arrows, math subscripts - none were corruption.

WSP References: WSP 90 (UTF-8), WSP 50 (Pre-Action)
"""

import pytest
from pathlib import Path
import sys

# Add holo_index to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qwen_advisor.orchestration.src.wsp_documentation_guardian import (
    is_allowed_unicode,
    is_suspicious_unicode,
    ALLOWED_UNICODE_RANGES,
    SUSPICIOUS_UNICODE,
)


class TestUnicodeClassification:
    """Test Unicode character classification functions."""

    def test_ascii_always_allowed(self):
        """ASCII characters (0-127) are always allowed."""
        for i in range(128):
            char = chr(i)
            assert is_allowed_unicode(char), f"ASCII char {i} should be allowed"

    def test_box_drawing_allowed(self):
        """Box drawing characters (U+2500-257F) are allowed for ASCII diagrams."""
        box_chars = [
            '\u2500',  # BOX DRAWINGS LIGHT HORIZONTAL
            '\u2502',  # BOX DRAWINGS LIGHT VERTICAL
            '\u250C',  # BOX DRAWINGS LIGHT DOWN AND RIGHT
            '\u2510',  # BOX DRAWINGS LIGHT DOWN AND LEFT
            '\u2514',  # BOX DRAWINGS LIGHT UP AND RIGHT
            '\u2518',  # BOX DRAWINGS LIGHT UP AND LEFT
            '\u252C',  # BOX DRAWINGS LIGHT DOWN AND HORIZONTAL
            '\u2534',  # BOX DRAWINGS LIGHT UP AND HORIZONTAL
        ]
        for char in box_chars:
            assert is_allowed_unicode(char), f"Box drawing {repr(char)} should be allowed"
            assert not is_suspicious_unicode(char), f"Box drawing {repr(char)} should not be suspicious"

    def test_arrows_allowed(self):
        """Arrow characters (U+2190-21FF) are allowed for flow documentation."""
        arrow_chars = [
            '\u2190',  # LEFTWARDS ARROW
            '\u2191',  # UPWARDS ARROW
            '\u2192',  # RIGHTWARDS ARROW
            '\u2193',  # DOWNWARDS ARROW
            '\u21D2',  # RIGHTWARDS DOUBLE ARROW
            '\u21D4',  # LEFT RIGHT DOUBLE ARROW
        ]
        for char in arrow_chars:
            assert is_allowed_unicode(char), f"Arrow {repr(char)} should be allowed"
            assert not is_suspicious_unicode(char), f"Arrow {repr(char)} should not be suspicious"

    def test_math_subscripts_allowed(self):
        """Math subscripts/superscripts (U+2070-209F) are allowed for notation."""
        math_chars = [
            '\u2070',  # SUPERSCRIPT ZERO
            '\u2074',  # SUPERSCRIPT FOUR
            '\u2080',  # SUBSCRIPT ZERO
            '\u2081',  # SUBSCRIPT ONE
            '\u2082',  # SUBSCRIPT TWO
            '\u2083',  # SUBSCRIPT THREE
        ]
        for char in math_chars:
            assert is_allowed_unicode(char), f"Math {repr(char)} should be allowed"
            assert not is_suspicious_unicode(char), f"Math {repr(char)} should not be suspicious"

    def test_emoji_allowed(self):
        """Emojis (U+1F300-1F9FF) are allowed per WSP 90 Rule 3."""
        emoji_chars = [
            '\U0001F4CD',  # ROUND PUSHPIN
            '\U0001F680',  # ROCKET
            '\U0001F4A1',  # LIGHT BULB
            '\U0001F50D',  # MAGNIFYING GLASS
        ]
        for char in emoji_chars:
            assert is_allowed_unicode(char), f"Emoji {repr(char)} should be allowed"
            assert not is_suspicious_unicode(char), f"Emoji {repr(char)} should not be suspicious"

    def test_replacement_char_suspicious(self):
        """Replacement character (U+FFFD) is suspicious - indicates encoding error."""
        char = '\uFFFD'  # REPLACEMENT CHARACTER
        assert is_suspicious_unicode(char), "Replacement char should be suspicious"

    def test_control_chars_suspicious(self):
        """Control characters (except tab, LF, CR) are suspicious."""
        # Suspicious control chars
        for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 14, 15]:
            char = chr(i)
            assert is_suspicious_unicode(char), f"Control char {i} should be suspicious"

        # Allowed whitespace
        assert not is_suspicious_unicode('\t'), "Tab should not be suspicious"
        assert not is_suspicious_unicode('\n'), "LF should not be suspicious"
        assert not is_suspicious_unicode('\r'), "CR should not be suspicious"

    def test_private_use_area_suspicious(self):
        """Private Use Area (U+E000-F8FF) is suspicious."""
        char = '\uE000'  # First char in PUA
        assert is_suspicious_unicode(char), "PUA char should be suspicious"

    def test_latin_accents_allowed(self):
        """Latin-1 Supplement accented chars are allowed for international text."""
        accent_chars = [
            '\u00E9',  # LATIN SMALL LETTER E WITH ACUTE
            '\u00F1',  # LATIN SMALL LETTER N WITH TILDE
            '\u00FC',  # LATIN SMALL LETTER U WITH DIAERESIS
            '\u00B1',  # PLUS-MINUS SIGN
        ]
        for char in accent_chars:
            assert is_allowed_unicode(char), f"Accent {repr(char)} should be allowed"

    def test_greek_letters_allowed(self):
        """Greek letters are allowed for math/science notation."""
        greek_chars = [
            '\u03C1',  # rho
            '\u03C6',  # phi
            '\u03A9',  # Omega
            '\u03BB',  # lambda
            '\u03C4',  # tau
            '\u0394',  # Delta
        ]
        for char in greek_chars:
            assert is_allowed_unicode(char), f"Greek {repr(char)} should be allowed"
            assert not is_suspicious_unicode(char), f"Greek {repr(char)} should not be suspicious"

    def test_currency_symbols_allowed(self):
        """Currency symbols are allowed."""
        currency_chars = [
            '\u20BF',  # Bitcoin sign
            '\u20AC',  # Euro sign (if in Latin-1 Supplement or Currency)
        ]
        for char in currency_chars:
            assert is_allowed_unicode(char), f"Currency {repr(char)} should be allowed"

    def test_variation_selectors_allowed(self):
        """Variation selectors (emoji modifiers) are allowed."""
        char = '\uFE0F'  # Variation Selector-16
        assert is_allowed_unicode(char), "Variation selector should be allowed"

    def test_mathematical_brackets_allowed(self):
        """Mathematical angle brackets are allowed."""
        bracket_chars = [
            '\u27E8',  # MATHEMATICAL LEFT ANGLE BRACKET
            '\u27E9',  # MATHEMATICAL RIGHT ANGLE BRACKET
        ]
        for char in bracket_chars:
            assert is_allowed_unicode(char), f"Math bracket {repr(char)} should be allowed"

    def test_supplemental_arrows_allowed(self):
        """Supplemental arrows (long arrows) are allowed."""
        arrow_chars = [
            '\u27F9',  # LONG RIGHTWARDS DOUBLE ARROW
            '\u27F7',  # LONG LEFT RIGHT ARROW
        ]
        for char in arrow_chars:
            assert is_allowed_unicode(char), f"Long arrow {repr(char)} should be allowed"


class TestDocumentSamples:
    """Test with realistic document content samples."""

    def test_box_drawing_diagram_sample(self):
        """Sample with box drawing diagram has no suspicious chars."""
        sample = """
        \u250C\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510
        \u2502  Module A   \u2502
        \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u252C\u2500\u2500\u2500\u2500\u2500\u2500\u2518
               \u2502
               \u2193
        \u250C\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510
        \u2502  Module B   \u2502
        \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518
        """
        suspicious = [c for c in sample if is_suspicious_unicode(c)]
        assert len(suspicious) == 0, f"Diagram should have no suspicious chars, found: {suspicious}"

    def test_math_notation_sample(self):
        """Sample with math notation has no suspicious chars."""
        sample = "Formula: x\u2080 + x\u2081 = x\u2082 where n \u2192 \u221E"
        suspicious = [c for c in sample if is_suspicious_unicode(c)]
        assert len(suspicious) == 0, f"Math notation should have no suspicious chars"

    def test_emoji_documentation_sample(self):
        """Sample with emojis has no suspicious chars (per WSP 90)."""
        sample = "\U0001F680 Launch sequence \u2192 \u2713 Complete"
        suspicious = [c for c in sample if is_suspicious_unicode(c)]
        assert len(suspicious) == 0, f"Emoji docs should have no suspicious chars"

    def test_mojibake_sample_flagged(self):
        """Sample with replacement char is flagged."""
        sample = "Corrupted text: hello\uFFFDworld"
        suspicious = [c for c in sample if is_suspicious_unicode(c)]
        assert len(suspicious) == 1, "Replacement char should be flagged"
        assert '\uFFFD' in suspicious


class TestIntegration:
    """Integration tests for guardian behavior."""

    def test_intentional_unicode_file_not_violation(self):
        """Files with only intentional Unicode should not be violations."""
        # Content matching WSP_100_DAE_SmartDAO_Escalation_Protocol.md pattern
        content = """
# WSP 100: DAE SmartDAO Escalation Protocol

## Architecture Diagram

\u250C\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510
\u2502           SmartDAO Layer            \u2502
\u251C\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524
\u2502  Escalation: Level\u2080 \u2192 Level\u2081 \u2192 L\u2082  \u2502
\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518

Transition: State\u2080 \u2194 State\u2081
        """
        # Count suspicious vs intentional
        suspicious = [c for c in content if is_suspicious_unicode(c)]
        intentional = [c for c in content if ord(c) > 127 and is_allowed_unicode(c) and not is_suspicious_unicode(c)]

        assert len(suspicious) == 0, "Should have no suspicious chars"
        assert len(intentional) > 0, "Should have intentional Unicode (box drawing, subscripts)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
