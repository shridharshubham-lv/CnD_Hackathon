import streamlit as st
import time as _time
import random as _random

_LOADING_TIPS = [
    "💡 The AI checks each asset against 5 dimensions: CTA, audience, tone, claims, and channel norms.",
    "💡 Past campaign patterns are stored as vectors — the more you use it, the smarter warnings get.",
    "💡 Each agent's output is graded by an LLM evaluator. If it scores below 7/10, it auto-retries.",
    "💡 The consistency checker uses embeddings to measure semantic similarity between your brief and copy.",
    "💡 You can re-run QA after applying fixes to verify all issues are resolved.",
    "💡 The execution plan is channel-specific — it adapts budget, timing, and CTAs per channel.",
    "💡 Export your final report as JSON to feed into other marketing tools or dashboards.",
    "💡 Custom edits on the QA page automatically patch the original asset copy.",
]


def run_with_status(
    title: str,
    steps: list[tuple[str, callable]],
    intro: str | None = None,
    expectations: list[str] | None = None,
) -> dict:
    """Run a list of (label, callable) steps with a richer progress experience.

    Returns a dict mapping step index to each step's return value.
    """
    if intro:
        st.info(intro)

    if expectations:
        expectation_lines = "\n".join(f"- {line}" for line in expectations)
        st.caption(f"What to expect:\n{expectation_lines}")

    # Pick a random tip to show during loading
    _tip = _random.choice(_LOADING_TIPS)

    with st.status(title, expanded=True) as status:
        results = {}
        total_start = _time.time()
        total_steps = len(steps)
        for i, (label, fn) in enumerate(steps, start=1):
            status.update(label=f"{title} — Step {i}/{total_steps}: {label}...", state="running")
            st.write(f"⏳ Step {i}/{total_steps}: {label}...")
            st.caption(_tip)
            step_start = _time.time()
            try:
                result = fn()
            except Exception as exc:
                elapsed = _time.time() - step_start
                total_elapsed = _time.time() - total_start
                st.error(f"{label} failed after {elapsed:.1f}s")
                st.exception(exc)
                status.update(
                    label=f"{title} — Failed on step {i}/{total_steps}: {label} ({total_elapsed:.1f}s)",
                    state="error",
                    expanded=True,
                )
                raise
            elapsed = _time.time() - step_start
            st.write(f"✅ {label} ({elapsed:.1f}s)")
            results[i - 1] = result

        total_elapsed = _time.time() - total_start

        # Extract trace info from the last result if available
        last = results.get(len(steps) - 1)
        trace_label = ""
        if isinstance(last, dict) and "_trace" in last:
            trace = last["_trace"]
            trace_label = f" [trace: {trace.get('trace_id', '?')}]"

        st.success(f"Finished in {total_elapsed:.1f}s")
        status.update(
            label=f"✅ {title} — Complete ({total_elapsed:.1f}s){trace_label}",
            state="complete",
            expanded=False,
        )
        return results
