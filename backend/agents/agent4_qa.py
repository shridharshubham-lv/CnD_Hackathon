import json
import logging
from utils.llm import chat

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior campaign QA reviewer who writes actionable fix instructions.

For each error, assign severity:
- CRITICAL: violates a business objective, compliance constraint, or explicitly stated rule
  (e.g., references competitors when brief says "do not reference competitors")
- WARNING: creates audience confusion, cross-channel inconsistency, or weakens conversion
  (e.g., CTA says "Start free trial" when brief targets existing trial users for paid conversion)
- ADVISORY: stylistic or minor tone observation that won't impact campaign performance

Fix quality rules:
- currentText MUST be the EXACT text from the asset — copy it verbatim, do not paraphrase
- suggestedFix MUST be exact replacement text that can be copy-pasted into the asset
- BAD fix: "Change the CTA to align with the brief" (vague instruction)
- GOOD fix: "Book a demo" (exact replacement text)
- businessImpact should explain the real-world consequence in one sentence

Return ONLY valid JSON sorted by severity (CRITICAL first):
{
  "qaReport": [
    {
      "id": "issue_1", "channel": "", "dimension": "",
      "severity": "CRITICAL|WARNING|ADVISORY",
      "currentText": "", "briefRequirement": "",
      "suggestedFix": "", "businessImpact": "",
      "status": "pending"
    }
  ],
  "summary": {"critical": 0, "warning": 0, "advisory": 0, "total": 0}
}"""


def generate_qa_report(conflicts: list[dict], brief: dict) -> dict:
    """Takes only REAL_ERROR conflicts. Ranks severity and generates fix suggestions."""
    real_errors = [c for c in conflicts if c.get("classification") == "REAL_ERROR"]

    user_message = json.dumps({
        "conflicts": real_errors,
        "brief": brief,
    })

    raw = chat(SYSTEM_PROMPT, user_message)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Agent 4 JSON parse error: {e}. Raw response: {raw[:500]}")
        raise ValueError(f"Failed to parse QA report response: {e}") from e
    return result
