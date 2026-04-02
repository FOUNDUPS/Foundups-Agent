#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Member Mall presentation overrides — canonical source for UI-only fields.

These fields are consumed by the Firebase-hosted member Mall UI
(public/member/index.html) but are NOT part of the FoundUp manifest schema.
They live here so that mall-catalog.json can be generated from one truth.

Fields:
    theme       - CSS theme class for the swipe card
    hero_label  - short hero text on the card face
    hero_mood   - one-line mood/status text for the agent concierge hint
    entry_copy  - longer copy shown in card focus/overlay
"""

from typing import Any, Dict


# Keyed by foundup_id. Only tenants with overrides get presentation fields;
# tenants without an entry get safe defaults via get_presentation().
MEMBER_PRESENTATION: Dict[str, Dict[str, str]] = {
    "antifafm_001": {
        "theme": "antifafm",
        "hero_label": "SIGNAL",
        "hero_mood": "Signal-first, always on, discoverable inside the shell.",
        "entry_copy": (
            "The broadcast stack is real, but shell entry stays "
            "discoverable-only until tenant handoff is wired."
        ),
    },
    "gotjunk_001": {
        "theme": "gotjunk",
        "hero_label": "REUSE",
        "hero_mood": "Clean, useful, conditional entry pending one more operational pass.",
        "entry_copy": (
            "GotJunk is the strongest shopper-facing FoundUp in the Mall, "
            "but it still carries a conditional launch posture."
        ),
    },
    "magadoom_001": {
        "theme": "magadoom",
        "hero_label": "FRAG",
        "hero_mood": "Visible, sharp, still incubating until the test surface catches up.",
        "entry_copy": (
            "MAGADOOM remains in shell discovery mode while its public-facing "
            "test expectations are brought back into line."
        ),
    },
}

_DEFAULTS: Dict[str, str] = {
    "theme": "default",
    "hero_label": "",
    "hero_mood": "",
    "entry_copy": "",
}


def get_presentation(foundup_id: str) -> Dict[str, str]:
    """Return presentation overrides for a FoundUp, with safe defaults."""
    return MEMBER_PRESENTATION.get(foundup_id, dict(_DEFAULTS))
