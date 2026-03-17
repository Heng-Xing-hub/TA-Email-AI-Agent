"""
TA Email Agent — main pipeline.

Pipeline: Input → LLM Understanding → Policy Enforcement → Rule Engine
         → Memory Retrieval → Decision Engine → LLM Generation
         → Human Feedback → Learning
"""

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

from email_parser import parse_email_with_llm, ParsedEmail
from policy_engine import apply_policy_and_rules, PolicyResult
from memory_retrieval import retrieve_similar, store_case, StoredCase
from decision_engine import make_decision, Decision
from reply_generator import generate_reply_draft

load_dotenv()

# Default paths
PROJECT_ROOT = Path(__file__).parent
print(PROJECT_ROOT)
POLICY_PATH = PROJECT_ROOT / "policy.json"
EMAILS_DIR = PROJECT_ROOT / "emails"

def run_pipeline(raw_email: str) -> dict:
    """
    Run full pipeline up to (and including) LLM Generation.
    Returns all intermediate results for display and for Human Feedback.
    """
    # 1. Input (raw_email is the input)

    # 2. LLM Understanding
    parsed = parse_email_with_llm(raw_email)
    print("[LLM Understanding] Parsed:", parsed.summary, "| intent:", parsed.intent, "| topic:", parsed.topic)

    # 3. Policy Enforcement + 4. Rule Engine
    policy_result = apply_policy_and_rules(parsed, POLICY_PATH)
    print("[Policy + Rules] Escalation required:", policy_result.escalation_required, "| applicable policies:", list(policy_result.applicable_policies.keys()))

    # 5. Memory Retrieval
    similar_cases = retrieve_similar(parsed.summary, parsed.intent, parsed.topic, top_k=5)
    print("[Memory] Retrieved", len(similar_cases), "similar case(s)")

    # 6. Decision Engine
    decision = make_decision(parsed, policy_result, similar_cases)
    print("[Decision]", decision.action, "—", decision.reason)

    # 7. LLM Generation
    draft_reply = generate_reply_draft(parsed, policy_result, decision)
    print("[Draft reply generated]")

    return {
        "parsed": parsed,
        "policy_result": policy_result,
        "similar_cases": similar_cases,
        "decision": decision,
        "draft_reply": draft_reply,
    }


def run_human_feedback_and_learning(
    pipeline_result: dict,
    final_reply: str,
    final_action: str | None = None,
    store_for_learning: bool = True,
) -> str | None:
    """
    Human Feedback: TA has confirmed or edited the decision and reply.
    Learning: store (optionally) the case for future retrieval.
    Returns case_id if stored.
    """
    parsed: ParsedEmail = pipeline_result["parsed"]
    decision: Decision = pipeline_result["decision"]
    action = final_action or decision.action

    if not store_for_learning:
        return None

    case_id = str(uuid.uuid4())[:8]
    case = StoredCase(
        case_id=case_id,
        raw_email=parsed.raw_email,
        summary=parsed.summary,
        intent=parsed.intent,
        topic=parsed.topic,
        decision=action,
        reply_text=pipeline_result["draft_reply"],
        corrected_reply=final_reply if final_reply != pipeline_result["draft_reply"] else None,
    )
    store_case(case)
    print("[Learning] Stored case", case_id, "for future retrieval.")
    return case_id


def main():
    """Interactive loop: process one email, show draft, collect TA feedback, then Learning."""
    print("=== TA Email Agent ===\n")
    print("Enter the student email (end with a blank line or Ctrl+Z then Enter on Windows):\n")

    lines = []
    try:
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
    except EOFError:
        pass

    raw_email = "\n".join(lines).strip()
    if not raw_email:
        print("No email provided. Exiting.")
        return

    result = run_pipeline(raw_email)
    print("\n" + "=" * 50)
    print("DRAFT REPLY:")
    print("=" * 50)
    print(result["draft_reply"])
    print("=" * 50)

    print("\n[Human Feedback] Use this draft as-is, or edit. Enter your final reply (end with blank line):")
    final_lines = []
    try:
        while True:
            line = input()
            if line == "":
                break
            final_lines.append(line)
    except EOFError:
        pass
    final_reply = "\n".join(final_lines).strip() or result["draft_reply"]

    save = input("Store this case for future retrieval? [Y/n]: ").strip().lower()
    store = save != "n"
    case_id = run_human_feedback_and_learning(result, final_reply, store_for_learning=store)
    if case_id:
        print("Case saved with id:", case_id)
    print("Done.")


if __name__ == "__main__":
    import sys
    # 只运行片段：python main.py --snippet（不进入完整 pipeline）
    if len(sys.argv) > 1 and sys.argv[1] == "--snippet":
        print(PROJECT_ROOT)
        sys.exit(0)
    main()
