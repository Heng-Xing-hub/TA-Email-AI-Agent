"""
Memory Retrieval: retrieve similar past cases from history database.
Stores cases as JSON; uses simple text similarity (keyword overlap) for retrieval.
For production, consider vector DB 
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any


CASES_DB = Path(__file__).parent / "memory_cases.json"


@dataclass
class StoredCase:
    """A past case (optionally corrected by TA) for retrieval."""
    case_id: str
    raw_email: str
    summary: str
    intent: str
    topic: str
    decision: str  # e.g., "direct_reply", "escalate_to_instructor"
    reply_text: str
    corrected_reply: str | None  # TA-edited version; if present, use for learning

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StoredCase":
        return cls(
            case_id=d.get("case_id", ""),
            raw_email=d.get("raw_email", ""),
            summary=d.get("summary", ""),
            intent=d.get("intent", ""),
            topic=d.get("topic", ""),
            decision=d.get("decision", ""),
            reply_text=d.get("reply_text", ""),
            corrected_reply=d.get("corrected_reply"),
        )


def _load_cases() -> list[dict]:
    if not CASES_DB.exists():
        return []
    with open(CASES_DB, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_cases(cases: list[dict]) -> None:
    CASES_DB.parent.mkdir(parents=True, exist_ok=True)
    with open(CASES_DB, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)


def _simple_similarity(text_a: str, text_b: str) -> float:
    """Jaccard-like overlap on words (no embeddings)."""
    a = set((text_a or "").lower().split())
    b = set((text_b or "").lower().split())
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def retrieve_similar(
    query_summary: str,
    query_intent: str,
    query_topic: str,
    top_k: int = 5,
) -> list[StoredCase]:
    """
    Retrieve top_k most similar past cases.
    Combines intent/topic match with text similarity on summary.
    """
    cases = _load_cases()
    if not cases:
        return []
    query_text = f"{query_summary} {query_intent} {query_topic}"
    scored = []
    for c in cases:
        stored = StoredCase.from_dict(c)
        text = f"{stored.summary} {stored.intent} {stored.topic}"
        sim = _simple_similarity(query_text, text)
        if (stored.intent == query_intent) or (stored.topic == query_topic):
            sim += 0.3
        scored.append((sim, stored))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:top_k]]


def store_case(case: StoredCase) -> None:
    """Append a case to the memory (for Learning stage)."""
    cases = _load_cases()
    cases.append(case.to_dict())
    _save_cases(cases)


def update_case_correction(case_id: str, corrected_reply: str) -> bool:
    """Update a case with TA-corrected reply (Learning)."""
    cases = _load_cases()
    for c in cases:
        if c.get("case_id") == case_id:
            c["corrected_reply"] = corrected_reply
            _save_cases(cases)
            return True
    return False
