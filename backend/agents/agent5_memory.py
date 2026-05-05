import json
import hashlib
import logging
from utils.llm import chat, embed
from db.qdrant import store_pattern, search_similar, _extract_campaign_tags
from db.postgres import save_patterns
from db.redis_client import get_client as get_redis

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """You are a campaign intelligence analyst building a reusable knowledge base.
Extract 3-5 actionable, reusable lessons from this QA report that would help
PREVENT the same errors in future campaigns.

Focus on patterns that are:
- Specific enough to detect automatically (not "be more careful")
- Tied to a trigger condition (when does this mistake tend to happen?)
- Channel-aware (which channels are most affected?)

BAD lesson: "CTA should match the brief" (too generic)
GOOD lesson: "Enterprise conversion campaigns that use 'Start free trial' as CTA 
instead of 'Book a demo' see lower conversion — always verify CTA matches the 
campaign stage (trial vs paid vs awareness)"

Return ONLY valid JSON:
{
  "patterns": [
    {
      "campaignType": "", "channel": "", "errorType": "",
      "lesson": "", "triggerCondition": ""
    }
  ]
}"""

WARN_PROMPT = """You have patterns from past campaigns that had QA issues.
Given a NEW brief and these past patterns, surface 2-3 proactive warnings
that are RELEVANT to this specific brief.

Rules:
- Only warn about patterns that genuinely apply to this brief's audience, channels, or constraints.
- Be concise — each recommendation should be 1-2 sentences max.
- If no patterns are relevant, return an empty warnings array.
- Do NOT invent warnings that aren't supported by the past patterns.

Return ONLY valid JSON:
{
  "warnings": [
    {"pattern": "", "relevance": "", "recommendation": ""}
  ]
}"""


def extract_and_store_patterns(campaign_id: int, qa_report: dict, brief: dict) -> list[dict]:
    """Extracts reusable patterns from QA report, stores in Qdrant + PostgreSQL."""
    user_message = json.dumps({
        "qaReport": qa_report,
        "brief": brief,
    })

    raw = chat(EXTRACT_PROMPT, user_message)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Agent 5 extract JSON parse error: {e}. Raw response: {raw[:500]}")
        raise ValueError(f"Failed to parse pattern extraction response: {e}") from e
    patterns = result.get("patterns", [])

    # Embed the brief text for vector search
    brief_text = json.dumps(brief) if isinstance(brief, dict) else str(brief)
    embedding = embed(brief_text)

    # Store in Qdrant with metadata tags for filtered search
    store_pattern(campaign_id, embedding, patterns, brief=brief)

    # Save to PostgreSQL
    save_patterns(campaign_id, patterns)

    return patterns


def _deduplicate_patterns(patterns: list[dict]) -> list[dict]:
    """Merge duplicate lessons by comparing lesson text. Keeps first occurrence."""
    seen = set()
    unique = []
    for p in patterns:
        lesson = (p.get("lesson", "") or "").strip().lower()
        if not lesson:
            continue
        key = lesson[:80]
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def get_proactive_warnings(brief_text: str) -> list[dict]:
    """Search Qdrant for similar past campaigns and surface warnings.
    Results cached in Redis for 10 minutes keyed by brief hash."""
    # Check cache first
    brief_hash = hashlib.sha256(brief_text.encode()).hexdigest()[:16]
    cache_key = f"warn_cache:{brief_hash}"
    try:
        redis = get_redis()
        cached = redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    embedding = embed(brief_text)

    # Infer tags from raw brief to filter Qdrant results
    tags = _extract_campaign_tags({"businessObjective": brief_text, "targetAudience": brief_text})
    similar = search_similar(
        embedding,
        top_k=3,
        campaign_type=tags.get("campaign_type"),
        channels=tags.get("channels"),
    )

    if not similar:
        return []

    all_patterns = []
    for match in similar:
        all_patterns.extend(match.get("patterns", []))

    # Deduplicate before sending to LLM
    all_patterns = _deduplicate_patterns(all_patterns)

    if not all_patterns:
        return []

    user_message = json.dumps({
        "newBrief": brief_text,
        "pastPatterns": all_patterns,
    })

    raw = chat(WARN_PROMPT, user_message)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Agent 5 warn JSON parse error: {e}. Raw response: {raw[:500]}")
        return []
    warnings = result.get("warnings", [])

    # Cache in Redis for 10 minutes
    try:
        redis = get_redis()
        redis.setex(cache_key, 600, json.dumps(warnings))
    except Exception:
        pass

    return warnings
