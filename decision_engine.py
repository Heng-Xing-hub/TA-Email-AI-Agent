"""
Decision Engine: combine policy, rules, and historical evidence to make a recommendation.
"""

from dataclasses import dataclass
from email_parser import ParsedEmail
from policy_engine import PolicyResult
from memory_retrieval import StoredCase


@dataclass
class Decision:
    """Recommended action and reasoning."""
    action: str  # "direct_reply" | "escalate_to_instructor" | "escalate_to_registrar"
    reason: str
    suggested_talking_points: list[str]
    confidence: str  # "high" | "medium" | "low"


def make_decision(
    parsed: ParsedEmail,
    policy_result: PolicyResult,
    similar_cases: list[StoredCase],
) -> Decision:
    """
    Combine:
    - Policy: applicable policy text (fixed, cannot be changed by AI).
    - Rules: if escalation_required, action is forced.
    - Historical evidence: similar past cases suggest action and talking points.
    """
    if policy_result.escalation_required:
        return Decision(
            action=policy_result.escalation_action or "escalate_to_instructor",
            reason=policy_result.escalation_reason or "Rule requires escalation.",
            suggested_talking_points=[
                "This falls under a mandatory escalation rule.",
                "Please forward to the appropriate authority.",
            ],
            confidence="high",
        )

    # No mandatory escalation: use policy + history
    talking_points = []
    for _k, v in policy_result.applicable_policies.items():
        talking_points.append(v)

    action = "direct_reply"
    reason = "No escalation rule matched; policy and similar cases support a direct reply."
    confidence = "medium"

    if similar_cases:
        # Prefer corrected replies from past cases
        for c in similar_cases:
            reply = (c.corrected_reply or c.reply_text).strip()
            if reply:
                talking_points.append(f"[Similar case]: {reply[:300]}...")
        if any(c.decision == "escalate_to_instructor" for c in similar_cases):
            confidence = "high"

    return Decision(
        action=action,
        reason=reason,
        suggested_talking_points=talking_points[:5],
        confidence=confidence,
    )
