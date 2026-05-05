import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import call_api, defaults
from utils.stepper import render_stepper
from utils.sidebar import render_sidebar
from utils.loader import run_with_status

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.set_page_config(page_title="Clarification Review", page_icon="❓", layout="wide")

st.title("❓ Clarification Review")

render_sidebar(2)
render_stepper(2)

if not st.session_state.questions:
    st.warning("Please complete Brief Intake first — no questions to clarify yet.")
    st.page_link("pages/1_brief_intake.py", label="← Go to Brief Intake", icon="⬅️")
    st.stop()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Brief Summary")

    # Accept All Suggestions button
    questions_with_suggestions = [
        q for q in st.session_state.questions
        if q.get("suggested_answer", "").strip() or q.get("suggestedAnswer", "").strip()
    ]
    if questions_with_suggestions:
        if st.button("✅ Accept All Suggestions", help="Fill every question with its AI-suggested answer"):
            for q in questions_with_suggestions:
                qid = q.get("id", "")
                suggested = q.get("suggested_answer", "") or q.get("suggestedAnswer", "")
                if qid and suggested:
                    st.session_state.answers[qid] = suggested
                    st.session_state[f"answer_{qid}"] = suggested
            st.toast(f"Accepted {len(questions_with_suggestions)} suggested answers")
            st.rerun()

    eb = st.session_state.enriched_brief or {}
    fields = [
        ("Campaign Name", "campaignName"),
        ("Business Objective", "businessObjective"),
        ("Target Audience", "targetAudience"),
        ("Key Message", "keyMessage"),
        ("Channels", "channels"),
        ("Budget", "budget"),
        ("Timeline", "timeline"),
        ("Success Metrics", "successMetrics"),
        ("Constraints", "constraints"),
    ]
    _table_rows = ""
    for label, key in fields:
        value = eb.get(key, "Not specified")
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        # Escape HTML in values
        value = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        _table_rows += f"<tr><td style='font-weight:600;white-space:nowrap;padding:8px 14px 8px 0;vertical-align:top;color:#60a5fa;'>{label}</td><td style='padding:8px 0;color:inherit;'>{value}</td></tr>"
    st.markdown(
        f"<table style='width:100%;border-collapse:collapse;'>{_table_rows}</table>",
        unsafe_allow_html=True,
    )

    gaps = eb.get("gaps", [])
    if gaps:
        st.divider()
        st.subheader("🔎 Gaps Identified")

        # Handle categorized gaps (new format: list of {category, items})
        if gaps and isinstance(gaps[0], dict) and "category" in gaps[0]:
            for idx, gap_group in enumerate(gaps):
                category = gap_group.get("category", "Other")
                items = gap_group.get("items", [])
                with st.expander(f"📂 {category} ({len(items)} gap{'s' if len(items) != 1 else ''})", expanded=(idx == 0)):
                    for item in items:
                        st.warning(item)
        else:
            # Fallback for flat list of strings (old format)
            with st.expander(f"📂 All Gaps ({len(gaps)} total)", expanded=True):
                for gap in gaps:
                    st.warning(gap)

with col_right:
    st.subheader("Clarifying Questions")
    questions = st.session_state.questions
    answered_count = 0

    # Group questions by priority
    priority_groups = {"high": [], "medium": [], "low": []}
    for q in questions:
        p = q.get("priority", "low").lower()
        priority_groups.setdefault(p, []).append(q)

    priority_meta = [
        ("high", "🔴 High Priority", True),
        ("medium", "🟡 Medium Priority", False),
        ("low", "🔵 Low Priority", False),
    ]

    for pkey, label, expanded_default in priority_meta:
        group = priority_groups.get(pkey, [])
        if not group:
            continue
        with st.expander(f"{label} ({len(group)} question{'s' if len(group) != 1 else ''})", expanded=expanded_default):
            for q in group:
                qid = q.get("id", "")
                suggested = q.get("suggested_answer", "")
                st.markdown(f"**{q.get('question', '')}**")
                st.caption(f"Field: {q.get('field', '')}")

                # Show suggested answer with a "Use suggestion" button
                if suggested and not st.session_state.answers.get(qid, "").strip():
                    scol1, scol2 = st.columns([4, 1])
                    with scol1:
                        st.info(f"💡 **Suggested:** {suggested}")
                    with scol2:
                        if st.button("Use ✓", key=f"use_{qid}"):
                            st.session_state.answers[qid] = suggested
                            st.session_state[f"answer_{qid}"] = suggested
                            st.rerun()

                answer = st.text_input(
                    f"Your answer",
                    value=st.session_state.answers.get(qid, ""),
                    key=f"answer_{qid}",
                    label_visibility="collapsed",
                    placeholder="Type your answer or use the suggestion above...",
                )
                if answer.strip():
                    st.session_state.answers[qid] = answer
                st.markdown("---")

    # Count answered across all groups
    for q in questions:
        qid = q.get("id", "")
        if st.session_state.answers.get(qid, "").strip():
            answered_count += 1

    st.progress(answered_count / max(len(questions), 1))
    st.write(f"{answered_count} of {len(questions)} answered")

st.divider()

nav_col1, nav_col2 = st.columns(2)
with nav_col1:
    if st.button("⬅️ Back to Brief Intake"):
        st.session_state.stage = 1
        st.switch_page("pages/1_brief_intake.py")

st.caption(
    "Generating the execution plan can take a bit because the app merges your answers, "
    "calls the planning model, and saves the result before advancing to the next stage."
)

if st.button("📝 Generate Execution Plan", type="primary", help="Merges your answers with the brief and generates a channel-by-channel execution plan — this may take 15-60 seconds"):
    # Validate all HIGH priority questions are answered
    high_unanswered = []
    for q in st.session_state.questions:
        if q.get("priority") == "high":
            qid = q.get("id", "")
            if not st.session_state.answers.get(qid, "").strip():
                high_unanswered.append(q.get("question", ""))

    if high_unanswered:
        st.error("Please answer all HIGH priority questions before proceeding:")
        for q in high_unanswered:
            st.write(f"- {q}")
    else:
        answers_list = [
            {"id": qid, "answer": ans}
            for qid, ans in st.session_state.answers.items()
            if ans.strip()
        ]

        results = run_with_status(
            "Building Execution Plan",
            [
                ("Merging brief with your answers", lambda: None),
                ("Generating channel-specific plan", lambda: call_api("/api/agent2/plan", {
                    "session_id": st.session_state.session_id,
                    "campaign_id": st.session_state.campaign_id,
                    "answers": answers_list,
                })),
            ],
            intro="Your brief and clarification answers are being synthesized into a channel-by-channel execution plan.",
            expectations=[
                "Typical runtime is 15-60 seconds depending on model latency.",
                "Keep this tab open until the status box finishes and the page advances.",
                "If the call succeeds, the app will switch directly to Execution Plan.",
            ],
        )
        result = results.get(1)

        if result and "error" not in result:
            st.session_state.execution_plan = result.get("execution_plan")
            st.session_state.stage = 3
            st.success("Execution plan generated!")
            st.toast("✅ Clarification complete — generating execution plan!")
            st.balloons()
            st.switch_page("pages/3_plan.py")
        elif result:
            st.error(f"Error: {result.get('error', 'Unknown error')}")
