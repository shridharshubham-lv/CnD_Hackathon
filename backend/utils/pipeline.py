import time
import uuid
import logging

logger = logging.getLogger(__name__)


class PipelineTrace:
    """Tracks execution steps through the agent pipeline for traceability."""

    def __init__(self, pipeline_name: str, campaign_id: int | None = None):
        self.trace_id = str(uuid.uuid4())[:8]
        self.pipeline_name = pipeline_name
        self.campaign_id = campaign_id
        self.steps: list[dict] = []
        self.start_time = time.time()
        logger.info(f"[{self.trace_id}] Pipeline started: {pipeline_name} (campaign={campaign_id})")

    def step(self, name: str):
        """Return a context manager that tracks a named step."""
        return _StepContext(self, name)

    def add_step(self, name: str, duration: float, status: str = "success", detail: str = ""):
        entry = {
            "step": name,
            "duration_ms": round(duration * 1000),
            "status": status,
            "detail": detail,
        }
        self.steps.append(entry)
        logger.info(
            f"[{self.trace_id}] {status.upper()} {name} "
            f"({entry['duration_ms']}ms) {detail}"
        )

    def finish(self) -> dict:
        total = time.time() - self.start_time
        trace = {
            "trace_id": self.trace_id,
            "pipeline": self.pipeline_name,
            "campaign_id": self.campaign_id,
            "total_ms": round(total * 1000),
            "steps": self.steps,
        }
        logger.info(
            f"[{self.trace_id}] Pipeline complete: {self.pipeline_name} "
            f"({trace['total_ms']}ms, {len(self.steps)} steps)"
        )
        return trace


class _StepContext:
    def __init__(self, trace: PipelineTrace, name: str):
        self.trace = trace
        self.name = name
        self.start = 0.0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start
        if exc_type:
            self.trace.add_step(
                self.name, duration, status="error", detail=str(exc_val)
            )
        else:
            self.trace.add_step(self.name, duration, status="success")
        return False
