import logging
import uuid
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from db.postgres import init_tables, save_campaign, update_campaign, get_campaign, get_all_campaigns, delete_campaign
from db.qdrant import init_collection
from db.redis_client import set_session, get_session
from models.schemas import (
    AnalyzeBriefRequest, AnalyzeBriefResponse,
    PlanRequest, PlanResponse,
    CheckRequest, CheckResponse,
    QARequest, QAResponse,
    LearnRequest, WarnRequest, WarnResponse,
    GenerateAssetsRequest, GenerateAssetsResponse,
    PipelineRunRequest, PipelineContinueRequest,
)
from agents.agent1_analyzer import analyze_brief
from agents.agent2_planner import generate_plan
from agents.agent3_checker import check_consistency
from agents.agent4_qa import generate_qa_report
from agents.agent5_memory import extract_and_store_patterns, get_proactive_warnings
from agents.agent6_generator import generate_channel_assets
from orchestrator import run_pipeline, continue_pipeline
from utils.pipeline import PipelineTrace

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Campaign IQ", version="1.0.0")


def _slugify_question_field(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (value or "question").strip().lower())
    return slug.strip("_") or "question"


def _normalize_questions(questions: list[dict]) -> list[dict]:
    normalized = []
    for index, question in enumerate(questions, start=1):
        normalized_question = dict(question)
        field_slug = _slugify_question_field(normalized_question.get("field", ""))
        normalized_question["id"] = f"{field_slug}_{index}_{uuid.uuid4().hex[:8]}"
        normalized.append(normalized_question)
    return normalized

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    logger.info("Initializing services...")
    try:
        init_tables()
        logger.info("PostgreSQL: tables initialized")
    except Exception as e:
        logger.error(f"PostgreSQL init failed: {e}")
    try:
        init_collection()
        logger.info("Qdrant: collection initialized")
    except Exception as e:
        logger.error(f"Qdrant init failed: {e}")
    try:
        from db.redis_client import get_client
        get_client().ping()
        logger.info("Redis: connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")


@app.get("/api/health")
def health():
    services = {}
    try:
        from db.postgres import get_connection
        conn = get_connection()
        conn.close()
        services["postgres"] = "ok"
    except Exception as e:
        services["postgres"] = str(e)
    try:
        from db.qdrant import get_client
        get_client().get_collections()
        services["qdrant"] = "ok"
    except Exception as e:
        services["qdrant"] = str(e)
    try:
        from db.redis_client import get_client
        get_client().ping()
        services["redis"] = "ok"
    except Exception as e:
        services["redis"] = str(e)
    return {"status": "ok", "services": services}


@app.get("/api/campaigns")
def list_campaigns():
    try:
        campaigns = get_all_campaigns()
        return {"campaigns": campaigns}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/campaigns/{campaign_id}/resume")
def resume_campaign(campaign_id: int):
    try:
        campaign = get_campaign(campaign_id)
        if not campaign:
            return JSONResponse(status_code=404, content={"error": "Campaign not found"})

        raw_brief = campaign.get("raw_brief", "")
        enriched_brief = campaign.get("enriched_brief", {}) or {}
        execution_plan = campaign.get("execution_plan", {}) or {}
        qa_payload = campaign.get("qa_report", {}) or {}
        saved_answers = campaign.get("answers", []) or []
        channel_assets = campaign.get("channel_assets", {}) or {}

        # Questions are not persisted in PostgreSQL, so regenerate them only when needed.
        questions = []
        if not execution_plan and raw_brief:
            regenerated = analyze_brief(raw_brief)
            questions = _normalize_questions(regenerated.get("questions", []))
            regenerated_enriched = regenerated.get("enrichedBrief", {})
            if regenerated_enriched:
                enriched_brief = regenerated_enriched

        session_id = str(uuid.uuid4())
        session_payload = {
            "campaign_id": campaign_id,
            "enriched_brief": enriched_brief,
            "questions": questions,
        }
        if execution_plan:
            session_payload["execution_plan"] = execution_plan
        set_session(session_id, session_payload)

        stage = 2
        if qa_payload.get("qaReport"):
            stage = 5
        elif channel_assets:
            stage = 4
        elif execution_plan:
            stage = 3

        return {
            "campaign_id": campaign_id,
            "session_id": session_id,
            "stage": stage,
            "raw_brief": raw_brief,
            "enriched_brief": enriched_brief,
            "questions": questions,
            "execution_plan": execution_plan,
            "qa_report": qa_payload.get("qaReport", []),
            "qa_summary": qa_payload.get(
                "summary",
                {"critical": 0, "warning": 0, "advisory": 0, "total": 0},
            ),
            "answers": saved_answers,
            "channel_assets": channel_assets,
        }
    except Exception as e:
        logger.error(f"Resume campaign error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/campaigns/{campaign_id}")
def api_delete_campaign(campaign_id: int):
    try:
        campaign = get_campaign(campaign_id)
        if not campaign:
            return JSONResponse(status_code=404, content={"error": "Campaign not found"})
        delete_campaign(campaign_id)
        return {"status": "deleted", "campaign_id": campaign_id}
    except Exception as e:
        logger.error(f"Delete campaign error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/agent1/analyze")
def api_analyze_brief(req: AnalyzeBriefRequest):
    try:
        trace = PipelineTrace("brief_analysis")

        with trace.step("Analyze brief with LLM"):
            result = analyze_brief(req.brief)
        enriched = result.get("enrichedBrief", {})
        questions = _normalize_questions(result.get("questions", []))
        gaps = enriched.get("gaps", [])

        with trace.step("Save campaign to database"):
            campaign_name = enriched.get("campaignName", "Untitled Campaign")
            campaign_id = save_campaign(campaign_name, req.brief, enriched)

        with trace.step("Create session"):
            session_id = str(uuid.uuid4())
            set_session(session_id, {
                "campaign_id": campaign_id,
                "enriched_brief": enriched,
                "questions": questions,
            })

        response = AnalyzeBriefResponse(
            session_id=session_id,
            campaign_id=campaign_id,
            enriched_brief=enriched,
            questions=[
                {
                    "id": q.get("id", ""),
                    "question": q.get("question", ""),
                    "field": q.get("field", ""),
                    "priority": q.get("priority", "low"),
                    "suggested_answer": q.get("suggestedAnswer", ""),
                }
                for q in questions
            ],
            gaps=gaps,
        )
        resp_dict = response.model_dump()
        resp_dict["_trace"] = trace.finish()
        return resp_dict
    except Exception as e:
        logger.error(f"Agent 1 error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/agent2/plan")
def api_generate_plan(req: PlanRequest):
    try:
        trace = PipelineTrace("execution_planning", req.campaign_id)

        with trace.step("Load session data"):
            session_data = get_session(req.session_id)
            if session_data:
                enriched_brief = session_data.get("enriched_brief", {})
            else:
                campaign = get_campaign(req.campaign_id)
                enriched_brief = campaign.get("enriched_brief", {}) if campaign else {}

        with trace.step("Generate execution plan with LLM"):
            plan = generate_plan(enriched_brief, req.answers)

        with trace.step("Save plan to database"):
            update_campaign(req.campaign_id, execution_plan=plan, answers=req.answers)

        with trace.step("Update session"):
            set_session(req.session_id, {
                "campaign_id": req.campaign_id,
                "enriched_brief": enriched_brief,
                "execution_plan": plan,
            })

        response = PlanResponse(campaign_id=req.campaign_id, execution_plan=plan)
        resp_dict = response.model_dump()
        resp_dict["_trace"] = trace.finish()
        return resp_dict
    except Exception as e:
        logger.error(f"Agent 2 error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/agent3/check")
def api_check_consistency(req: CheckRequest):
    try:
        trace = PipelineTrace("consistency_check", req.campaign_id)

        with trace.step("Load campaign data"):
            campaign = get_campaign(req.campaign_id)
            if not campaign:
                return JSONResponse(status_code=404, content={"error": "Campaign not found"})
            enriched_brief = campaign.get("enriched_brief", {})
            execution_plan = campaign.get("execution_plan", {})
            assets = [{"channel": a.channel, "copy": a.copy} for a in req.assets]

        with trace.step("Save channel assets to database"):
            update_campaign(req.campaign_id, channel_assets={a.channel: a.copy for a in req.assets})

        with trace.step("Compute embeddings and classify with LLM"):
            result = check_consistency(enriched_brief, execution_plan, assets)

        conflicts = result.get("conflicts", [])
        errors = [c for c in conflicts if c.get("classification") == "REAL_ERROR"]

        response = CheckResponse(
            conflicts=[
                {
                    "channel": c.get("channel", ""),
                    "dimension": c.get("dimension", ""),
                    "brief_value": c.get("briefValue", ""),
                    "asset_value": c.get("assetValue", ""),
                    "classification": c.get("classification", ""),
                    "reasoning": c.get("reasoning", ""),
                    "similarity_score": c.get("similarityScore", 0.0),
                }
                for c in conflicts
            ],
            total_checked=len(assets),
            errors_found=len(errors),
        )
        resp_dict = response.model_dump()
        resp_dict["_trace"] = trace.finish()
        return resp_dict
    except Exception as e:
        logger.error(f"Agent 3 error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/agent4/qa")
def api_qa_report(req: QARequest):
    try:
        trace = PipelineTrace("qa_report", req.campaign_id)

        with trace.step("Load campaign data"):
            campaign = get_campaign(req.campaign_id)
            if not campaign:
                return JSONResponse(status_code=404, content={"error": "Campaign not found"})
            enriched_brief = campaign.get("enriched_brief", {})

        with trace.step("Generate QA report with LLM"):
            result = generate_qa_report(req.conflicts, enriched_brief)

        qa_report = result.get("qaReport", [])
        summary = result.get("summary", {"critical": 0, "warning": 0, "advisory": 0, "total": 0})

        with trace.step("Save report to database"):
            update_campaign(req.campaign_id, qa_report=result)

        response = QAResponse(
            qa_report=[
                {
                    "id": item.get("id", ""),
                    "channel": item.get("channel", ""),
                    "dimension": item.get("dimension", ""),
                    "severity": item.get("severity", "ADVISORY"),
                    "current_text": item.get("currentText", ""),
                    "brief_requirement": item.get("briefRequirement", ""),
                    "suggested_fix": item.get("suggestedFix", ""),
                    "business_impact": item.get("businessImpact", ""),
                    "status": item.get("status", "pending"),
                }
                for item in qa_report
            ],
            summary=summary,
        )
        resp_dict = response.model_dump()
        resp_dict["_trace"] = trace.finish()
        return resp_dict
    except Exception as e:
        logger.error(f"Agent 4 error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/agent5/learn")
def api_learn(req: LearnRequest):
    try:
        trace = PipelineTrace("pattern_extraction", req.campaign_id)

        with trace.step("Load campaign data"):
            campaign = get_campaign(req.campaign_id)
            if not campaign:
                return JSONResponse(status_code=404, content={"error": "Campaign not found"})
            qa_report = campaign.get("qa_report", {})
            enriched_brief = campaign.get("enriched_brief", {})

        with trace.step("Extract patterns and store in knowledge base"):
            patterns = extract_and_store_patterns(req.campaign_id, qa_report, enriched_brief)

        resp = {"campaign_id": req.campaign_id, "patterns": patterns}
        resp["_trace"] = trace.finish()
        return resp
    except Exception as e:
        logger.error(f"Agent 5 learn error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/agent5/warn")
def api_warn(req: WarnRequest):
    try:
        warnings = get_proactive_warnings(req.brief)
        return WarnResponse(warnings=warnings)
    except Exception as e:
        logger.error(f"Agent 5 warn error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/agent6/generate")
def api_generate_assets(req: GenerateAssetsRequest):
    try:
        trace = PipelineTrace("asset_generation", req.campaign_id)

        with trace.step("Load campaign data"):
            campaign = get_campaign(req.campaign_id)
            if not campaign:
                return JSONResponse(status_code=404, content={"error": "Campaign not found"})
            enriched_brief = campaign.get("enriched_brief", {})
            execution_plan = campaign.get("execution_plan", {})

        with trace.step("Generate channel-adapted assets with LLM"):
            result = generate_channel_assets(
                req.source_asset, req.source_channel,
                req.target_channels, enriched_brief, execution_plan,
            )

        adaptations = result.get("adaptations", [])

        with trace.step("Save generated assets to database"):
            generated_assets = {req.source_channel: req.source_asset}
            for a in adaptations:
                ch = a.get("channel", "")
                copy = a.get("adaptedCopy", "")
                if ch and copy:
                    generated_assets[ch] = copy
            update_campaign(req.campaign_id, channel_assets=generated_assets)

        response = GenerateAssetsResponse(
            adaptations=[
                {
                    "channel": a.get("channel", ""),
                    "adapted_copy": a.get("adaptedCopy", ""),
                    "change_log": [
                        {"change": c.get("change", ""), "reason": c.get("reason", "")}
                        for c in a.get("changeLog", [])
                    ],
                }
                for a in adaptations
            ]
        )
        resp_dict = response.model_dump()
        resp_dict["_trace"] = trace.finish()
        return resp_dict
    except Exception as e:
        logger.error(f"Agent 6 error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# --- Pipeline Orchestrator Endpoints ---

@app.post("/api/pipeline/run")
def api_pipeline_run(req: PipelineRunRequest):
    try:
        result = run_pipeline(req.brief, req.answers)
        return result
    except Exception as e:
        logger.error(f"Pipeline run error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/pipeline/continue")
def api_pipeline_continue(req: PipelineContinueRequest):
    try:
        result = continue_pipeline(req.campaign_id, req.session_id, req.answers)
        return result
    except Exception as e:
        logger.error(f"Pipeline continue error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
