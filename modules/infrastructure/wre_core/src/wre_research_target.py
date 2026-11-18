# -*- coding: utf-8 -*-
"""
WRE ROC Auto-Researcher Target File (WSP 48)

This file contains the variables that are optimized by the autonomous
research agent to maximize ROC and maintain sustainable ROI.
"""

# Allocation fractions per agent type (must sum to exactly 1.0)
AGENT_ALLOCATION = {
    "basic_search": 0.30,
    "openclaw_lite": 0.25,
    "openclaw": 0.25,
    "gotjunk_browse": 0.10,
    "gotjunk": 0.05,
    "cabr_validator": 0.05,
}

# Premium price multipliers applied to infra costs (must be in range [1.0, 5.0])
AGENT_PREMIUM_MULTIPLIERS = {
    "basic_search": 1.5,
    "openclaw_lite": 1.8,
    "openclaw": 2.0,
    "gotjunk_browse": 1.2,
    "gotjunk": 2.2,
    "cabr_validator": 2.5,
}
