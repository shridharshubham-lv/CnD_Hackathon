import json
import logging
import numpy as np
from utils.llm import chat, embed

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a campaign QA specialist who catches copy errors before launch.
Compare each channel asset against the brief AND the execution plan's copy guidance.

Check these dimensions for EVERY asset:
1. CTA alignment — does the asset's call-to-action match the brief's specified CTA?
2. Audience framing — is the copy written for the brief's target audience (seniority, industry, pain points)?
3. Key message fidelity — does the copy convey the brief's core message?
4. Tone — does the tone match the brief's requirements (confident vs casual, etc.)?
5. Brand constraints — does the copy violate any stated constraints (competitor mentions, unsupported claims, etc.)?

Use the similarityScore provided for each asset:
- Score > 0.85: likely well-aligned, look for subtle issues only
- Score 0.65-0.85: moderate alignment, check each dimension carefully
- Score < 0.65: likely significant divergence, flag all mismatches

Classification rules:
- INTENTIONAL_ADAPTATION: a deliberate, acceptable channel-specific adjustment
  (e.g., shorter copy for social, informal tone for Instagram)
- REAL_ERROR: genuine misalignment that needs fixing
  (e.g., wrong CTA, wrong audience, unsupported claim, constraint violation)

When in doubt, classify as REAL_ERROR — it's safer to flag and let the user dismiss.

Return ONLY valid JSON:
{
  "conflicts": [
    {
      "channel": "", "dimension": "CTA|Audience|KeyMessage|Tone|BrandConstraint",
      "briefValue": "", "assetValue": "",
      "classification": "REAL_ERROR|INTENTIONAL_ADAPTATION",
      "reasoning": "", "similarityScore": 0.0
    }
  ]
}"""


def check_consistency(brief: dict, execution_plan: dict, assets: list[dict]) -> dict:
    """For each asset: compute embedding similarity and call LLM to classify divergences."""
    key_message = brief.get("keyMessage", "")
    if key_message:
        brief_embedding = embed(key_message)
    else:
        brief_embedding = None

    asset_similarities = []
    for asset in assets:
        similarity = 0.0
        if brief_embedding and asset.get("copy"):
            asset_embedding = embed(asset["copy"])
            dot = np.dot(brief_embedding, asset_embedding)
            norm_a = np.linalg.norm(brief_embedding)
            norm_b = np.linalg.norm(asset_embedding)
            if norm_a > 0 and norm_b > 0:
                similarity = float(dot / (norm_a * norm_b))
        asset_similarities.append({
            "channel": asset["channel"],
            "copy": asset["copy"],
            "similarityScore": round(similarity, 4),
        })

    user_message = json.dumps({
        "brief": brief,
        "executionPlan": execution_plan,
        "assets": asset_similarities,
    })

    raw = chat(SYSTEM_PROMPT, user_message)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Agent 3 JSON parse error: {e}. Raw response: {raw[:500]}")
        raise ValueError(f"Failed to parse consistency check response: {e}") from e
    return result
