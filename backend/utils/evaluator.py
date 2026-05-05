import json
import logging
from utils.llm import chat
from agents.evaluator_prompts import RUBRICS, GRADER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def evaluate(pipeline_name: str, agent_output: dict, context: dict) -> dict:
    """Evaluate an agent's output using LLM-as-Judge.

    Args:
        pipeline_name: Key from RUBRICS (e.g. "brief_analysis")
        agent_output: The agent's raw output dict
        context: Additional context (brief, plan, etc.) for the grader

    Returns:
        Dict with scores, avg_score, passed, summary
    """
    rubric = RUBRICS.get(pipeline_name)
    if not rubric:
        logger.warning(f"No rubric found for pipeline: {pipeline_name}")
        return {"scores": [], "avg_score": 10.0, "passed": True, "summary": "No rubric — skipped evaluation."}

    # Build the grading prompt
    criteria_text = "\n".join(
        f"- {name}: {desc}" for name, desc in rubric["criteria"]
    )

    user_message = json.dumps({
        "agent": rubric["agent"],
        "criteria": criteria_text,
        "agentOutput": agent_output,
        "context": context,
    })

    try:
        raw = chat(GRADER_SYSTEM_PROMPT, user_message, temperature=0.1)
        result = json.loads(raw)

        # Ensure required fields
        scores = result.get("scores", [])
        if scores:
            avg = sum(s.get("score", 0) for s in scores) / len(scores)
        else:
            avg = 0.0
        result["avg_score"] = round(avg, 1)
        result["passed"] = avg >= 7.0

        logger.info(
            f"Evaluation [{pipeline_name}]: avg={result['avg_score']}/10 "
            f"passed={result['passed']} — {result.get('summary', '')}"
        )
        return result
    except Exception as e:
        logger.error(f"Evaluation failed for {pipeline_name}: {e}")
        return {
            "scores": [],
            "avg_score": 0.0,
            "passed": False,
            "summary": f"Evaluation error: {str(e)}",
        }
