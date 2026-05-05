import streamlit as st
import pandas as pd
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import call_api, defaults
from utils.stepper import render_stepper
from utils.sidebar import render_sidebar

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

if "plan_edit_mode" not in st.session_state:
    st.session_state.plan_edit_mode = False

st.set_page_config(page_title="Strategic Execution Plan", page_icon="📊", layout="wide")

st.title("📊 Strategic Execution Plan")

render_sidebar(3)
render_stepper(3)

if not st.session_state.execution_plan:
    st.warning("Please complete Clarification Review first — no execution plan generated yet.")
    st.page_link("pages/2_clarify.py", label="← Go to Clarification", icon="⬅️")
    st.stop()

plan = st.session_state.execution_plan

# --- Action bar: Edit / Re-analyze ---
act_col1, act_col2, act_col3 = st.columns([1, 1, 3])
with act_col1:
    if st.button("✏️ Edit Plan" if not st.session_state.plan_edit_mode else "👁️ View Plan"):
        st.session_state.plan_edit_mode = not st.session_state.plan_edit_mode
        st.rerun()
with act_col2:
    if st.button("🔄 Re-generate Plan"):
        answers_list = [
            {"id": qid, "answer": ans}
            for qid, ans in st.session_state.answers.items()
            if ans.strip()
        ]
        with st.spinner("Re-generating execution plan..."):
            result = call_api("/api/agent2/plan", {
                "session_id": st.session_state.session_id,
                "campaign_id": st.session_state.campaign_id,
                "answers": answers_list,
            })
        if result and "error" not in result:
            st.session_state.execution_plan = result.get("execution_plan")
            st.session_state.plan_edit_mode = False
            st.toast("✅ Plan re-generated!")
            st.rerun()
        elif result:
            st.error(f"Error: {result.get('error', 'Unknown error')}")

st.divider()

# --- Edit mode ---
if st.session_state.plan_edit_mode:
    st.info("**Edit mode** — Modify the plan JSON below and click **Save Changes**.")
    edited_json = st.text_area(
        "Execution Plan (JSON)",
        value=json.dumps(plan, indent=2),
        height=500,
        key="plan_editor",
    )
    if st.button("💾 Save Changes", type="primary"):
        try:
            updated_plan = json.loads(edited_json)
            st.session_state.execution_plan = updated_plan
            st.session_state.plan_edit_mode = False
            st.toast("✅ Plan updated!")
            st.rerun()
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
    st.stop()

# --- View mode (read-only) ---

tab_channels, tab_timeline, tab_budget, tab_metrics = st.tabs(
    ["📢 Channels", "📅 Timeline", "💰 Budget", "📈 Success Metrics"]
)

with tab_channels:
    channels = plan.get("channels", [])
    if not channels:
        st.info("No channel data in plan.")
    for idx, ch in enumerate(channels):
        priority = ch.get("priority", "secondary")
        badge = "🟢 PRIMARY" if priority == "primary" else "🔵 SECONDARY"
        with st.expander(f"{badge} — {ch.get('name', 'Unknown Channel')}", expanded=(idx == 0)):
            st.subheader("Specs")
            specs = ch.get("specs", {})
            for k, v in specs.items():
                st.markdown(f"**{k}:** {v}")

            st.subheader("Copy Guidance")
            guidance = ch.get("copyGuidance", {})
            for k, v in guidance.items():
                if isinstance(v, list):
                    v = ", ".join(str(i) for i in v)
                st.markdown(f"**{k}:** {v}")

with tab_timeline:
    timeline = plan.get("timeline", [])
    if not timeline:
        st.info("No timeline data in plan.")
    for week in timeline:
        with st.container():
            st.markdown(f"### Week {week.get('week', '?')} — {week.get('label', '')}")
            milestones = week.get("milestones", [])
            for m in milestones:
                st.markdown(f"- {m}")
            owner = week.get("owner", "")
            if owner:
                st.caption(f"Owner: {owner}")
            st.divider()

with tab_budget:
    budget = plan.get("budgetAllocation", [])
    if not budget:
        st.info("Budget not specified in brief.")
    else:
        df = pd.DataFrame(budget)
        if "channel" in df.columns and "amount" in df.columns:
            st.bar_chart(df.set_index("channel")["amount"])
        st.dataframe(df, use_container_width=True)

with tab_metrics:
    metrics = plan.get("successMetrics", [])
    if not metrics:
        st.info("No success metrics in plan.")
    else:
        df = pd.DataFrame(metrics)
        st.table(df)

st.divider()

nav_col1, nav_col2 = st.columns(2)
with nav_col1:
    if st.button("⬅️ Back to Clarification"):
        st.session_state.stage = 2
        st.switch_page("pages/2_clarify.py")
with nav_col2:
    if st.button("✅ Approve Plan & Upload Assets →", type="primary"):
        st.session_state.stage = 4
        st.toast("✅ Plan approved — moving to Asset Upload!")
        st.balloons()
        st.switch_page("pages/4_assets.py")
