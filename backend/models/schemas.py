from pydantic import BaseModel
from typing import Any


# Agent 1 — Brief Analyzer
class AnalyzeBriefRequest(BaseModel):
    brief: str


class ClarifyingQuestion(BaseModel):
    id: str
    question: str
    field: str
    priority: str  # high | medium | low
    suggested_answer: str = ""  # context-aware suggestion from Agent 1


class AnalyzeBriefResponse(BaseModel):
    session_id: str
    campaign_id: int
    enriched_brief: dict
    questions: list[ClarifyingQuestion]
    gaps: list[Any]  # list of strings or {"category": str, "items": list[str]}


# Agent 2 — Execution Planner
class PlanRequest(BaseModel):
    session_id: str
    campaign_id: int
    answers: list[dict]  # [{"id": "q1", "answer": "..."}]


class PlanResponse(BaseModel):
    campaign_id: int
    execution_plan: dict


# Agent 3 — Consistency Checker
class AssetItem(BaseModel):
    channel: str
    copy: str

    class Config:
        # Silence Pydantic warning about "copy" shadowing BaseModel.copy()
        populate_by_name = True


class CheckRequest(BaseModel):
    campaign_id: int
    assets: list[AssetItem]


class Conflict(BaseModel):
    channel: str
    dimension: str
    brief_value: str
    asset_value: str
    classification: str  # REAL_ERROR | INTENTIONAL_ADAPTATION
    reasoning: str
    similarity_score: float


class CheckResponse(BaseModel):
    conflicts: list[Conflict]
    total_checked: int
    errors_found: int


# Agent 4 — QA & Fix Agent
class QARequest(BaseModel):
    campaign_id: int
    conflicts: list[dict]


class QAIssue(BaseModel):
    id: str
    channel: str
    dimension: str
    severity: str  # CRITICAL | WARNING | ADVISORY
    current_text: str
    brief_requirement: str
    suggested_fix: str
    business_impact: str
    status: str  # pending | approved | dismissed


class QAResponse(BaseModel):
    qa_report: list[QAIssue]
    summary: dict


# Agent 5 — Memory Agent
class LearnRequest(BaseModel):
    campaign_id: int


class WarnRequest(BaseModel):
    brief: str


class WarnResponse(BaseModel):
    warnings: list[dict]


# Agent 6 — Asset Generator
class GenerateAssetsRequest(BaseModel):
    campaign_id: int
    source_asset: str
    source_channel: str
    target_channels: list[str]


class ChangeLogEntry(BaseModel):
    change: str
    reason: str


class ChannelAdaptation(BaseModel):
    channel: str
    adapted_copy: str
    change_log: list[ChangeLogEntry]


class GenerateAssetsResponse(BaseModel):
    adaptations: list[ChannelAdaptation]


# Pipeline Orchestrator
class PipelineRunRequest(BaseModel):
    brief: str
    answers: list[dict] | None = None  # None = pause after Stage 1


class PipelineContinueRequest(BaseModel):
    campaign_id: int
    session_id: str
    answers: list[dict]
