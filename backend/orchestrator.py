import json
import uuid
import logging
from utils.pipeline import PipelineTrace
from utils.evaluator import evaluate
from utils.llm import chat
from agents.agent1_analyzer import analyze_brief
from agents.agent2_planner import generate_plan
from agents.agent3_checker import check_consistency
from agents.agent4_qa import generate_qa_report
from agents.agent5_memory import extract_and_store_patterns
from agents.agent6_generator import generate_channel_assets
from db.postgres import save_campaign, update_campaign, get_campaign
from db.redis_client import set_session

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
PASS_THRESHOLD = 7.0


def _run_with_eval(trace: PipelineTrace, step_name: str, pipeline_name: str,
                   agent_fn, context: dict, max_retries: int = MAX_RETRIES) -> tuple[dict, dict]:
    """Run an agent function, evaluate the output, and retry if it fails.

    Returns (agent_output, evaluation_result).
    """
    last_output = {}
    last_eval = {}

    for attempt in range(max_retries + 1):
        attempt_label = f"{step_name} (attempt {attempt + 1})" if attempt > 0 else step_name

        with trace.step(attempt_label):
            last_output = agent_fn()

        with trace.step(f"Evaluate {step_name}"):
            last_eval = evaluate(pipeline_name, last_output, context)

        if last_eval.get("passed", False):
            break

        if attempt < max_retries:
            # Inject evaluator feedback for retry
            feedback = last_eval.get("summary", "Output quality was insufficient.")
            score_details = "; ".join(
                f"{s['criterion']}: {s['score']}/10 — {s.get('feedback', '')}"
                for s in last_eval.get("scores", [])
            )
            logger.info(
                f"[{trace.trace_id}] {step_name} failed eval (attempt {attempt + 1}), "
                f"retrying with feedback: {feedback}"
            )
            context["_retry_feedback"] = f"Previous attempt scored {last_eval.get('avg_score', 0)}/10. Issues: {score_details}. Please improve."

    return last_output, last_eval


def run_pipeline(brief: str, answers: list[dict] | None = None) -> dict:
    """Run the full campaign pipeline from brief to patterns.

    If answers is None, stops after Agent 1 (returns questions for human input).
    If answers is provided, runs the full pipeline through Agent 5.

    Returns a dict with all stage results, evaluations, and trace.
    """
    trace = PipelineTrace("full_pipeline")
    results = {}
    evaluations = {}

    # --- Stage 1: Analyze Brief ---
    context_1 = {"brief": brief}
    output_1, eval_1 = _run_with_eval(
        trace, "Analyze brief", "brief_analysis",
        lambda: analyze_brief(brief),
        context_1,
    )
    evaluations["brief_analysis"] = eval_1

    enriched = output_1.get("enrichedBrief", {})
    questions = output_1.get("questions", [])
    gaps = enriched.get("gaps", [])

    with trace.step("Save campaign to database"):
        campaign_name = enriched.get("campaignName", "Untitled Campaign")
        campaign_id = save_campaign(campaign_name, brief, enriched)

    with trace.step("Create session"):
        session_id = str(uuid.uuid4())
        set_session(session_id, {
            "campaign_id": campaign_id,
            "enriched_brief": enriched,
            "questions": questions,
        })

    results["stage_1"] = {
        "session_id": session_id,
        "campaign_id": campaign_id,
        "enriched_brief": enriched,
        "questions": questions,
        "gaps": gaps,
    }

    # If no answers provided, pause for human input
    if answers is None:
        results["status"] = "awaiting_answers"
        results["_evaluations"] = evaluations
        results["_trace"] = trace.finish()
        return results

    # --- Stage 2: Generate Plan ---
    context_2 = {"enriched_brief": enriched, "answers": answers}
    output_2, eval_2 = _run_with_eval(
        trace, "Generate execution plan", "execution_planning",
        lambda: {"plan": generate_plan(enriched, answers)},
        context_2,
    )
    evaluations["execution_planning"] = eval_2
    plan = output_2.get("plan", {})

    with trace.step("Save plan to database"):
        update_campaign(campaign_id, execution_plan=plan, answers=answers)

    results["stage_2"] = {"execution_plan": plan}

    # --- Stage 3: Generate Assets (Agent 6) ---
    channels = plan.get("channels", [])
    channel_names = [ch.get("name", "") for ch in channels if ch.get("name")]

    if len(channel_names) >= 2:
        source_channel = channel_names[0]
        target_channels = channel_names[1:]

        # Generate a source asset from the plan's copy guidance
        source_guidance = channels[0].get("copyGuidance", {})
        source_asset_prompt = (
            f"Write a complete {source_channel} asset for this campaign.\n"
            f"Audience: {source_guidance.get('audience', '')}\n"
            f"Tone: {source_guidance.get('tone', '')}\n"
            f"Key message: {source_guidance.get('keyMessage', '')}\n"
            f"CTA: {source_guidance.get('cta', '')}\n"
            f"Must include: {source_guidance.get('mustInclude', [])}\n"
            f"Must avoid: {source_guidance.get('mustAvoid', [])}"
        )

        with trace.step("Generate source asset from plan"):
            source_asset = chat(
                "You are a senior copywriter. Write campaign copy based on the guidance. Return ONLY the copy text, no JSON.",
                source_asset_prompt,
                temperature=0.4,
            )

        context_6 = {"brief": enriched, "execution_plan": plan, "source_channel": source_channel}
        output_6, eval_6 = _run_with_eval(
            trace, "Generate channel adaptations", "asset_generation",
            lambda: generate_channel_assets(source_asset, source_channel, target_channels, enriched, plan),
            context_6,
        )
        evaluations["asset_generation"] = eval_6

        # Build assets dict
        assets = {source_channel: source_asset}
        for adapt in output_6.get("adaptations", []):
            ch = adapt.get("adaptedCopy") and adapt.get("channel")
            if ch:
                assets[adapt["channel"]] = adapt["adaptedCopy"]

        results["stage_3"] = {
            "source_channel": source_channel,
            "source_asset": source_asset,
            "adaptations": output_6.get("adaptations", []),
            "assets": assets,
        }
    else:
        assets = {}
        results["stage_3"] = {"assets": {}, "adaptations": []}

    # --- Stage 4: Consistency Check (Agent 3) ---
    if assets:
        asset_list = [{"channel": ch, "copy": copy} for ch, copy in assets.items()]
        context_3 = {"brief": enriched, "execution_plan": plan, "assets": asset_list}
        output_3, eval_3 = _run_with_eval(
            trace, "Check consistency", "consistency_check",
            lambda: check_consistency(enriched, plan, asset_list),
            context_3,
        )
        evaluations["consistency_check"] = eval_3
        conflicts = output_3.get("conflicts", [])
    else:
        conflicts = []

    # --- Stage 5: QA Report (Agent 4) ---
    if conflicts:
        context_4 = {"brief": enriched, "conflicts": conflicts}
        output_4, eval_4 = _run_with_eval(
            trace, "Generate QA report", "qa_report",
            lambda: generate_qa_report(conflicts, enriched),
            context_4,
        )
        evaluations["qa_report"] = eval_4

        with trace.step("Save QA report to database"):
            update_campaign(campaign_id, qa_report=output_4)

        results["stage_4"] = {
            "conflicts": conflicts,
            "qa_report": output_4.get("qaReport", []),
            "summary": output_4.get("summary", {}),
        }
    else:
        results["stage_4"] = {"conflicts": [], "qa_report": [], "summary": {}}

    # --- Stage 6: Memory (Agent 5) ---
    qa_report = results["stage_4"].get("qa_report", [])
    if qa_report:
        context_5 = {"brief": enriched, "qa_report": results.get("stage_4", {})}
        output_5, eval_5 = _run_with_eval(
            trace, "Extract patterns", "pattern_extraction",
            lambda: {"patterns": extract_and_store_patterns(campaign_id, {"qaReport": qa_report}, enriched)},
            context_5,
        )
        evaluations["pattern_extraction"] = eval_5
        results["stage_5"] = {"patterns": output_5.get("patterns", [])}
    else:
        results["stage_5"] = {"patterns": []}

    results["status"] = "complete"
    results["campaign_id"] = campaign_id
    results["session_id"] = session_id
    results["_evaluations"] = evaluations
    results["_trace"] = trace.finish()
    return results


def continue_pipeline(campaign_id: int, session_id: str, answers: list[dict]) -> dict:
    """Continue a paused pipeline from Stage 2 onwards using saved campaign data."""
    campaign = get_campaign(campaign_id)
    if not campaign:
        return {"error": "Campaign not found"}

    enriched = campaign.get("enriched_brief", {})
    brief = campaign.get("raw_brief", "")

    # Re-run from Stage 2 with answers
    trace = PipelineTrace("continue_pipeline", campaign_id)
    results = {"campaign_id": campaign_id, "session_id": session_id}
    evaluations = {}

    # Stage 2
    context_2 = {"enriched_brief": enriched, "answers": answers}
    output_2, eval_2 = _run_with_eval(
        trace, "Generate execution plan", "execution_planning",
        lambda: {"plan": generate_plan(enriched, answers)},
        context_2,
    )
    evaluations["execution_planning"] = eval_2
    plan = output_2.get("plan", {})

    with trace.step("Save plan to database"):
        update_campaign(campaign_id, execution_plan=plan, answers=answers)

    results["stage_2"] = {"execution_plan": plan}
    results["status"] = "complete"
    results["_evaluations"] = evaluations
    results["_trace"] = trace.finish()
    return results
