import json
import logging
from utils.llm import chat

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior campaign strategist with 15+ years in B2B and B2C marketing.
Analyze the raw campaign brief below. Your job:

1. EXTRACT every field you can find — even if vague, capture what's stated.
2. IDENTIFY gaps — fields that are missing, ambiguous, or too vague to act on.
3. GENERATE 3-5 clarifying questions ranked by priority.
4. For EACH question, provide a context-aware SUGGESTED ANSWER inferred from the
   brief's industry, audience, objectives, and tone.

Priority definitions:
- high: blocks execution — cannot write copy or allocate budget without this answer
- medium: affects quality — plan will work but may underperform without clarification
- low: nice to have — improves precision but won't block progress

Question quality rules:
- BAD: "Timeline is vague" (observation, not a question)
- BAD: "What is the budget?" (too generic)
- GOOD: "The brief says end of July — should we target July 1 as live date to allow 3 weeks of optimization before month-end?"
- GOOD: "Budget is unspecified — based on the 5 channels and enterprise audience, should we plan for a $40-60K range with 60% allocated to paid?"

Group gaps into 3-5 of these categories (skip empty categories):
- Budget & Resources
- Audience & Targeting
- Channel & Creative
- Timeline & Milestones
- Compliance & Constraints

Return ONLY valid JSON:
{
  "enrichedBrief": {
    "campaignName": "", "businessObjective": "", "targetAudience": "",
    "keyMessage": "", "channels": [], "budget": "", "timeline": "",
    "successMetrics": "", "constraints": "",
    "gaps": [
      {"category": "Budget & Resources", "items": ["No budget specified"]},
      {"category": "Channel & Creative", "items": ["Social channel unspecified"]}
    ]
  },
  "questions": [
    {"id": "q1", "question": "", "field": "", "priority": "high|medium|low", "suggestedAnswer": ""}
  ]
}"""


def analyze_brief(brief: str) -> dict:
    """Takes raw brief string. Calls the configured OpenAI model and returns enriched brief + questions."""
    raw = chat(SYSTEM_PROMPT, brief)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Agent 1 JSON parse error: {e}. Raw response: {raw[:500]}")
        raise ValueError(f"Failed to parse brief analysis response: {e}") from e
    return result
