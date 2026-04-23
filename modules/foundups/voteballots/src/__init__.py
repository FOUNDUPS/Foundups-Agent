"""
Vote/Ballots FoundUp - AI-native political transparency.

User provides candidate name (speech or text), receives funding
transparency report with evidence trail.

WSP 97 Compliance: All outputs explicitly separate:
- verified_fact
- high_confidence_inference
- low_confidence_inference
- unknown

Model Behavior Rules:
- Never state hidden funding as fact unless sourced
- Distinguish direct disclosure from inferred alignment
- Never flatten influence categories
- Show where evidence stops
- No hallucinated accusations
- Flag dangerous edge cases for human review
"""

__version__ = "0.1.0"
__status__ = "design"
