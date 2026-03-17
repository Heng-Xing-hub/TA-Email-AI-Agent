"""
LLM Understanding stage: parse raw student email and extract structured features.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

# Optional: use OpenAI; can be swapped for other LLM backends
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


@dataclass
class ParsedEmail:
    """Structured representation of a student email."""
    summary: str
    intent: str  # e.g., "extension_request", "question_about_assignment", "grade_dispute"
    topic: str   # e.g., "late_submission", "office_hours", "regrading"
    urgency: str  # "low", "medium", "high", "critical"
    student_question: str
    escalation_flags: list[str]  # e.g., ["grade_dispute"], ["academic_integrity_concern"]
    key_facts: list[str]
    raw_email: str

    def to_dict(self) -> dict:
        return asdict(self)


def parse_email_with_llm(raw_email: str, api_key: Optional[str] = None) -> ParsedEmail:
    """
    Use LLM to parse the email and extract structured features.
    Falls back to a simple heuristic if OpenAI is not configured.
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if OpenAI and api_key:
        return _parse_with_openai(raw_email, api_key)
    return _parse_heuristic(raw_email)


def _parse_with_openai(raw_email: str, api_key: str) -> ParsedEmail:
    client = OpenAI(api_key=api_key)
    prompt = """You are a TA assistant. Parse this student email and extract structured information.
Return a JSON object with exactly these fields (use empty list/string where not applicable):
- summary: one sentence summary
- intent: one of extension_request, question_about_assignment, grade_dispute, office_hours, regrading, academic_integrity_concern, special_accommodation, enrollment_issue, makeup_exam_request, other
- topic: one of late_submission, extension, office_hours, regrading, academic_integrity, enrollment, makeup_exam, other
- urgency: one of low, medium, high, critical
- student_question: the main question or request in one sentence
- escalation_flags: list of any of: grade_dispute, academic_integrity_concern, special_accommodation, enrollment_issue, makeup_exam_request (only if clearly present)
- key_facts: list of 1-5 key facts from the email

Student email:
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt + raw_email}],
        temperature=1,
    )
    text = response.choices[0].message.content.strip()
    # Handle markdown code block
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    data = json.loads(text)
    return ParsedEmail(
        summary=data.get("summary", ""),
        intent=data.get("intent", "other"),
        topic=data.get("topic", "other"),
        urgency=data.get("urgency", "medium"),
        student_question=data.get("student_question", ""),
        escalation_flags=data.get("escalation_flags", []),
        key_facts=data.get("key_facts", []),
        raw_email=raw_email,
    )


def _parse_heuristic(raw_email: str) -> ParsedEmail:
    """Fallback when no LLM: minimal extraction."""
    lines = [l.strip() for l in raw_email.splitlines() if l.strip()]
    summary = lines[0][:200] if lines else ""
    escalation_flags = []
    lower = raw_email.lower()
    if "grade" in lower and ("dispute" in lower or "regrade" in lower or "wrong" in lower):
        escalation_flags.append("grade_dispute")
    if "cheat" in lower or "plagiar" in lower or "copy" in lower:
        escalation_flags.append("academic_integrity_concern")
    if "accommodation" in lower or "disability" in lower:
        escalation_flags.append("special_accommodation")
    if "enroll" in lower or "add/drop" in lower or "registration" in lower:
        escalation_flags.append("enrollment_issue")
    return ParsedEmail(
        summary=summary,
        intent="other",
        topic="other",
        urgency="medium",
        student_question=summary,
        escalation_flags=escalation_flags,
        key_facts=lines[:3] if lines else [],
        raw_email=raw_email,
    )
