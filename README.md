# TA Email Agent

AI-assisted pipeline for TA email responses: **Input → LLM Understanding → Policy Enforcement → Rule Engine → Memory Retrieval → Decision Engine → LLM Generation → Human Feedback → Learning**.

## Setup

```bash
cd ta_email_agent
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set OPENAI_API_KEY if you want LLM parsing and reply generation.
```

## Usage

**Interactive (one email from stdin):**

```bash
python main.py
```

Then paste the student email and press Enter twice. The agent will print a draft reply; you can confirm or edit it. Optionally store the case for future retrieval.

**Programmatic:**

```python
from main import run_pipeline, run_human_feedback_and_learning

result = run_pipeline("Student raw email text...")
print(result["draft_reply"])
# After TA confirms/edits:
run_human_feedback_and_learning(result, final_reply="...", store_for_learning=True)
```

## Pipeline Stages

| Stage | Module | Responsibility |
|-------|--------|----------------|
| Input | `main.py` | Receive raw student email |
| LLM Understanding | `email_parser.py` | Parse email, extract intent, topic, escalation flags |
| Policy Enforcement | `policy_engine.py` | Apply fixed course policies from `policy.json` |
| Rule Engine | `policy_engine.py` | Evaluate escalation rules (e.g. grade dispute → escalate) |
| Memory Retrieval | `memory_retrieval.py` | Retrieve similar past cases from `memory_cases.json` |
| Decision Engine | `decision_engine.py` | Recommend action (direct_reply vs escalate) |
| LLM Generation | `reply_generator.py` | Generate natural-language reply draft |
| Human Feedback | `main.py` | TA confirms or edits decision and reply |
| Learning | `memory_retrieval.py` | Store corrected cases for future retrieval |

## Files

- `policy.json` — Course policies and escalation rules (edit for your course).
- `memory_cases.json` — Created automatically; stores past cases for retrieval.
- `emails/` — Optional: place sample or incoming emails here.

Without `OPENAI_API_KEY`, the agent uses heuristic parsing and template replies only.
