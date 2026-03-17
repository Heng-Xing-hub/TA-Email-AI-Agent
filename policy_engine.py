"""
Policy Enforcement: apply fixed course policies (cannot be changed by AI).
Rule Engine: evaluate hard constraints and mandatory escalation cases.
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any

# Import parsed email type for type hints
from email_parser import ParsedEmail


@dataclass
class PolicyResult:
    """Result of applying policies and rules."""
    applicable_policies: dict[str, str]  # policy_key -> policy_text
    escalation_required: bool
    escalation_action: str | None  # e.g., "escalate_to_instructor"
    escalation_reason: str | None
    rule_matched: dict | None  # the escalation rule that matched, if any


def load_policy(policy_path: str | Path) -> dict[str, Any]:
    path = Path(policy_path)
    if not path.exists():
        return {"policies": {}, "escalation_rules": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_policy_and_rules(
    parsed: ParsedEmail,
    policy_path: str | Path = "policy.json",
) -> PolicyResult:
    """
    Policy Enforcement: select which fixed policies apply to this email.
    Rule Engine: check escalation rules; if any match, escalation is required.
    """
    config = load_policy(policy_path)
    policies: dict = config.get("policies", {})
    escalation_rules: list = config.get("escalation_rules", [])

    # Policy Enforcement: which policies are relevant by topic
    topic_to_policy = {
        "late_submission": "late_submission",
        "extension": "extension",
        "office_hours": "office_hours",
        "regrading": "regrading",
        "academic_integrity": "academic_integrity",
        "enrollment": None,
    }
    applicable = {}
    topic = (parsed.topic or "other").strip().lower()
    if topic in topic_to_policy and topic_to_policy[topic]:
        key = topic_to_policy[topic]
        if key in policies:
            applicable[key] = policies[key]
    # Always include a generic set if we have any policies
    for k, v in policies.items():
        if k not in applicable and _topic_matches(parsed, k):
            applicable[k] = v

    # Rule Engine: mandatory escalation
    escalation_required = False
    escalation_action = None
    escalation_reason = None
    rule_matched = None
    for rule in escalation_rules:
        condition = rule.get("condition", "")
        if condition in (parsed.escalation_flags or []):
            escalation_required = True
            escalation_action = rule.get("action")
            escalation_reason = rule.get("description", condition)
            rule_matched = rule
            break

    return PolicyResult(
        applicable_policies=applicable,
        escalation_required=escalation_required,
        escalation_action=escalation_action,
        escalation_reason=escalation_reason,
        rule_matched=rule_matched,
    )


def _topic_matches(parsed: ParsedEmail, policy_key: str) -> bool:
    """Simple heuristic: intent or topic mentions this policy."""
    t = (parsed.topic or "").lower()
    i = (parsed.intent or "").lower()
    k = policy_key.lower()
    return k in t or k in i
