"""
LLM Generation: generate natural-language reply draft from decision + policy + context.
"""

import os
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from email_parser import ParsedEmail
from policy_engine import PolicyResult
from decision_engine import Decision


def generate_reply_draft(
    parsed: ParsedEmail,
    policy_result: PolicyResult,
    decision: Decision,
    api_key: Optional[str] = None,
) -> str:
    """
    Generate a natural-language reply draft using LLM.
    Uses policy text and decision talking points; respects escalation (short template).
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if OpenAI and api_key:
        return _generate_with_openai(parsed, policy_result, decision, api_key)
    return _generate_template(parsed, policy_result, decision)


def _generate_with_openai(
    parsed: ParsedEmail,
    policy_result: PolicyResult,
    decision: Decision,
    api_key: str,
) -> str:
    client = OpenAI(api_key=api_key)
    system = """You are a professional TA for a university course. Write a concise, helpful email reply.
- Be polite and clear.
- Use only the policies and talking points provided; do not invent policy.
- If the decision is to escalate, write a short reply that acknowledges the student and states you are forwarding to the instructor/registrar."""

    user_parts = [
        f"Student email:\n{parsed.raw_email}",
        f"\nApplicable policies (use these exactly where relevant):\n{chr(10).join(f'- {k}: {v}' for k, v in policy_result.applicable_policies.items()) or 'None'}",
        f"\nDecision: {decision.action}. Reason: {decision.reason}",
        f"\nSuggested talking points:\n" + "\n".join(f"- {p}" for p in decision.suggested_talking_points),
    ]
    user = "\n".join(user_parts)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def _generate_template(
    parsed: ParsedEmail,
    policy_result: PolicyResult,
    decision: Decision,
) -> str:
    """Fallback when no LLM: template reply."""
    if decision.action.startswith("escalate"):
        return (
            f"Hi,\n\nThank you for your email regarding: {parsed.summary}\n\n"
            f"This matter falls under our course policy and requires escalation. "
            f"I am forwarding your message to the appropriate person and they will follow up shortly.\n\nBest,\nTA"
        )
    lines = [
        "Hi,",
        "",
        f"Thanks for reaching out about: {parsed.student_question}",
        "",
    ]
    for pt in decision.suggested_talking_points[:3]:
        lines.append(pt)
        lines.append("")
    lines.append("If you have more questions, feel free to reply or come to office hours.")
    lines.append("")
    lines.append("Best,")
    lines.append("TA")
    return "\n".join(lines)
