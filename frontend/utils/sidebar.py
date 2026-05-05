import streamlit as st

# Hide the auto-generated page navigation that Streamlit creates from the pages/ folder
HIDE_PAGES_NAV = """
<style>
[data-testid="stSidebarNav"] {display: none !important;}
</style>
"""


STAGES = [
    (1, "📋", "Brief Intake", "pages/1_brief_intake.py"),
    (2, "❓", "Clarification", "pages/2_clarify.py"),
    (3, "📊", "Execution Plan", "pages/3_plan.py"),
    (4, "📎", "Asset Submission", "pages/4_assets.py"),
    (5, "🔍", "QA Report", "pages/5_qa_report.py"),
    (6, "📚", "Knowledge Base", "pages/6_memory.py"),
]

HOW_TO_USE = """
**Step 1 — Brief Intake**
Upload or paste your campaign brief. The system identifies gaps and generates clarifying questions.

**Step 2 — Clarification**
Answer prioritized questions with context-aware suggestions to fill gaps in your brief.

**Step 3 — Execution Plan**
Review a structured plan with channel guidance, timelines, and budget allocation. Edit if needed.

**Step 4 — Channel Assets**
Generate channel-adapted copy from a single source asset, or paste/upload copy manually.

**Step 5 — QA Report**
Review issues ranked by severity. Apply fixes individually or all at once, then re-run QA to verify.

**Step 6 — Knowledge Base**
Lessons are stored for future campaigns. Export your full report as JSON or text.
"""


def _stage_completed(num: int) -> bool:
    if num == 1:
        return st.session_state.get("enriched_brief") is not None
    if num == 2:
        return st.session_state.get("execution_plan") is not None
    if num == 3:
        return st.session_state.get("execution_plan") is not None
    if num == 4:
        return bool(st.session_state.get("qa_report"))
    if num == 5:
        return bool(st.session_state.get("patterns"))
    if num == 6:
        return bool(st.session_state.get("patterns"))
    return False


def _current_stage_index() -> int:
    """Return the highest completed stage + 1, capped at 6."""
    for i in range(6, 0, -1):
        if _stage_completed(i):
            return min(i + 1, 6)
    return 1


def render_sidebar(current_stage: int):
    """Render a clean sidebar with navigation, campaign context, and guides."""
    st.markdown(HIDE_PAGES_NAV, unsafe_allow_html=True)
    with st.sidebar:
        # --- Header ---
        st.markdown("### 🎯 Campaign Intelligence")

        st.divider()

        # --- Main Navigation ---
        if st.button("🏠 Home", key="sb_home", use_container_width=True):
            from app import reset_campaign_state
            reset_campaign_state()
            st.switch_page("app.py")
        if st.button("📁 Campaign History", key="sb_history", use_container_width=True):
            st.switch_page("pages/7_history.py")
        if st.button("🔄 New Campaign", key="sb_new", use_container_width=True):
            from app import reset_campaign_state
            reset_campaign_state()
            st.switch_page("pages/1_brief_intake.py")

        # --- How to Use ---
        with st.expander("❓ How to Use", expanded=False):
            st.markdown(HOW_TO_USE)

        st.divider()

        # --- Campaign Context ---
        campaign_id = st.session_state.get("campaign_id")
        eb = st.session_state.get("enriched_brief") or {}
        campaign_name = eb.get("campaignName", "")

        if campaign_id:
            st.markdown("##### Active Campaign")
            if campaign_name:
                st.markdown(f"**{campaign_name}**")
            st.caption(f"ID: #{campaign_id}")

            # Pipeline progress ring
            completed = sum(1 for i in range(1, 7) if _stage_completed(i))
            _pct = completed / 6
            _dash = 251.2  # circumference of r=40
            _filled_dash = _pct * _dash
            _gap_dash = _dash - _filled_dash
            _ring_color = "#22c55e" if completed == 6 else "#3b82f6"
            current_label = STAGES[current_stage - 1][2] if 1 <= current_stage <= 6 else ""
            st.markdown(
                f"""
                <div style="text-align:center;padding:0.4rem 0;">
                    <svg width="90" height="90" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" stroke-width="7"/>
                        <circle cx="50" cy="50" r="40" fill="none" stroke="{_ring_color}" stroke-width="7"
                            stroke-dasharray="{_filled_dash:.1f} {_gap_dash:.1f}"
                            stroke-dashoffset="62.8" stroke-linecap="round"
                            style="transition: stroke-dasharray 0.5s ease;"/>
                        <text x="50" y="46" text-anchor="middle" font-size="18" font-weight="800" fill="{_ring_color}">{completed}/6</text>
                        <text x="50" y="62" text-anchor="middle" font-size="9" fill="#94a3b8">stages</text>
                    </svg>
                    <div style="font-size:0.78rem;color:#64748b;margin-top:-2px;">Stage {current_stage} — {current_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.divider()

        # --- Brief Snapshot ---
        if eb:
            with st.expander("📋 Brief Snapshot", expanded=True):
                audience = eb.get("targetAudience", "")
                channels = eb.get("channels", [])
                if isinstance(channels, list):
                    channels = ", ".join(str(c) for c in channels[:4])
                if audience:
                    st.caption(f"🎯 {audience[:80]}{'...' if len(audience) > 80 else ''}")
                if channels:
                    st.caption(f"📢 {channels}")
                budget = eb.get("budget", "")
                if budget and budget.lower() != "not specified":
                    st.caption(f"💰 {budget}")

        # --- QA Status ---
        qa_summary = st.session_state.get("qa_summary", {})
        if qa_summary and any(qa_summary.get(k, 0) > 0 for k in ("critical", "warning", "advisory")):
            with st.expander("🔍 QA Status", expanded=True):
                c = qa_summary.get("critical", 0)
                w = qa_summary.get("warning", 0)
                a = qa_summary.get("advisory", 0)
                badges = []
                if c:
                    badges.append(f"🔴 {c} Critical")
                if w:
                    badges.append(f"🟡 {w} Warning")
                if a:
                    badges.append(f"🔵 {a} Advisory")
                st.markdown(" · ".join(badges))
                statuses = st.session_state.get("issue_statuses", {})
                resolved = sum(1 for v in statuses.values() if v in ("approved", "dismissed"))
                total = qa_summary.get("total", c + w + a)
                if total > 0:
                    st.progress(resolved / total)
                    st.caption(f"{resolved}/{total} resolved")

        # --- Evaluation Scores (placeholder for Workstream B) ---
        eval_scores = st.session_state.get("_eval_scores", {})
        if eval_scores:
            with st.expander("📊 Quality Scores", expanded=True):
                for stage_name, score_data in eval_scores.items():
                    score = score_data.get("avg_score", 0)
                    passed = score_data.get("passed", False)
                    icon = "✅" if passed else "❌"
                    st.caption(f"{icon} {stage_name}: {score:.1f}/10")
