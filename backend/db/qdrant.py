from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchAny
import uuid


def get_client() -> QdrantClient:
    return QdrantClient(host="localhost", port=6333)


def init_collection():
    client = get_client()
    collections = [c.name for c in client.get_collections().collections]
    if "campaign_memory" not in collections:
        client.create_collection(
            collection_name="campaign_memory",
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )


def _extract_campaign_tags(brief: dict) -> dict:
    """Extract searchable metadata tags from an enriched brief."""
    channels = brief.get("channels", [])
    if isinstance(channels, str):
        channels = [c.strip() for c in channels.split(",")]
    channels = [c.lower().strip() for c in channels if c]

    objective = (brief.get("businessObjective", "") or "").lower()
    audience = (brief.get("targetAudience", "") or "").lower()

    campaign_type = "general"
    b2b_signals = ["enterprise", "b2b", "saas", "demo request", "trial-to-paid", "decision-maker"]
    b2c_signals = ["b2c", "consumer", "retail", "purchase", "homeowner", "lapsed"]
    if any(s in objective + audience for s in b2b_signals):
        campaign_type = "b2b"
    elif any(s in objective + audience for s in b2c_signals):
        campaign_type = "b2c"

    industry = "general"
    industry_map = {
        "saas": ["saas", "software", "platform", "subscription"],
        "finance": ["financial", "banking", "fintech", "insurance"],
        "retail": ["retail", "ecommerce", "e-commerce", "shopping", "store"],
        "healthcare": ["health", "medical", "pharma", "clinical"],
    }
    combined = objective + " " + audience
    for ind, keywords in industry_map.items():
        if any(k in combined for k in keywords):
            industry = ind
            break

    return {
        "campaign_type": campaign_type,
        "industry": industry,
        "channels": channels,
    }


def store_pattern(campaign_id: int, embedding: list[float], patterns_payload: list[dict],
                  brief: dict | None = None):
    client = get_client()
    point_id = str(uuid.uuid4())
    payload = {
        "campaign_id": campaign_id,
        "patterns": patterns_payload,
    }
    if brief:
        payload.update(_extract_campaign_tags(brief))
    client.upsert(
        collection_name="campaign_memory",
        points=[
            PointStruct(id=point_id, vector=embedding, payload=payload)
        ],
    )


def search_similar(embedding: list[float], top_k: int = 3,
                   campaign_type: str | None = None,
                   channels: list[str] | None = None) -> list[dict]:
    client = get_client()

    conditions = []
    if campaign_type and campaign_type != "general":
        conditions.append(
            FieldCondition(key="campaign_type", match=MatchAny(any=[campaign_type, "general"]))
        )
    if channels:
        conditions.append(
            FieldCondition(key="channels", match=MatchAny(any=[c.lower() for c in channels]))
        )
    query_filter = Filter(must=conditions) if conditions else None

    results = client.query_points(
        collection_name="campaign_memory",
        query=embedding,
        query_filter=query_filter,
        limit=top_k,
        score_threshold=0.5,
    )
    return [
        {
            "score": hit.score,
            "campaign_id": hit.payload.get("campaign_id"),
            "patterns": hit.payload.get("patterns", []),
        }
        for hit in results.points
    ]
