"""Classify correspondence work origin, never authorize a provider mutation.

The live operator supplies session-bound 012 instructions. This policy projection
is not a receipt, signer, recipient resolver, or mechanical sender boundary.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CorrespondenceExecutionContext:
    origin: str
    work_item_id: str = ""
    principal_instruction_ref: str = ""
    explicit_send_requested: bool = False
    engineering_hold: bool = False


def correspondence_execution_mode(context: CorrespondenceExecutionContext) -> str:
    if context.engineering_hold:
        return "HOLD_ENGINEERING"
    if context.origin == "REDDOG_AUTO":
        return "REDDOG_BOUNDARY_REQUIRED"
    if context.origin != "012_DIRECTED_WORK":
        return "HOLD_UNKNOWN_ORIGIN"
    if not (context.explicit_send_requested is True
            and context.work_item_id.strip() and context.principal_instruction_ref.strip()):
        return "HOLD_MISSING_012_DIRECTION"
    return "WORK_DIRECTED_CHECKS_REQUIRED"
