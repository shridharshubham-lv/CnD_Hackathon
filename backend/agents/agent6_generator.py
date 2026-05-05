import json
import logging
from utils.llm import chat

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert content adaptation specialist. Given a single SOURCE ASSET
(approved copy for one channel), adapt it into channel-ready versions for each
TARGET CHANNEL listed, while maintaining brand compliance with the brief.

Rules:
- Every adaptation must preserve the core message, CTA, and audience framing from the brief.
- Adapt tone, length, and format to match each channel's norms:
  • Email: subject line + greeting + body + CTA button text + sign-off
  • LinkedIn: professional tone, 1-3 paragraphs, relevant hashtags
  • Paid Search: headlines (30 chars), descriptions (90 chars), display URL
  • Landing Page: hero headline + subheadline + body + CTA + social proof
  • Sales Outreach: personalized, conversational, specific CTA
  • SMS: under 160 chars, direct CTA link
  • Instagram/Facebook: casual, visual-first, emoji-friendly, hashtags
- Honor ALL constraints from the brief (no competitor mentions, proof requirements, etc.)
- For EACH modification from the source, log the change and cite the specific brief rule
  or channel requirement that motivated it.

Return ONLY valid JSON:
{
  "adaptations": [
    {
      "channel": "",
      "adaptedCopy": "",
      "changeLog": [
        {
          "change": "what was changed (e.g. 'CTA changed from Schedule a call to Book a demo')",
          "reason": "specific brief rule or channel requirement (e.g. 'Brief constraint: Primary CTA must be Book a demo')"
        }
      ]
    }
  ]
}"""


def generate_channel_assets(source_asset: str, source_channel: str,
                            target_channels: list[str], brief: dict,
                            execution_plan: dict) -> dict:
    """Adapt a single source asset into channel-ready versions with change logs."""
    user_message = json.dumps({
        "sourceAsset": source_asset,
        "sourceChannel": source_channel,
        "targetChannels": target_channels,
        "brief": brief,
        "executionPlan": execution_plan,
    })
    raw = chat(SYSTEM_PROMPT, user_message)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Agent 6 JSON parse error: {e}. Raw response: {raw[:500]}")
        raise ValueError(f"Failed to parse asset generation response: {e}") from e
    return result
