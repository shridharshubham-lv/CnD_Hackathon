import streamlit as st
import requests
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import call_api, call_api_get, BACKEND_URL, defaults, reset_campaign_state, restore_campaign_session, page_for_stage
from utils.sidebar import render_sidebar

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.set_page_config(page_title="Campaign History", page_icon="📁", layout="wide")

# Hide auto-generated page nav
st.markdown(
    "<style>[data-testid='stSidebarNav'] {display: none !important;}</style>",
    unsafe_allow_html=True,
)

st.title("📁 Campaign History")

with st.sidebar:
    st.markdown("### 🎯 Campaign Intelligence")
    st.divider()
    if st.button("🏠 Home", key="hist_home", use_container_width=True):
        reset_campaign_state()
        st.switch_page("app.py")
    if st.button("🔄 New Campaign", key="hist_new", use_container_width=True):
        reset_campaign_state()
        st.switch_page("pages/1_brief_intake.py")

campaigns_data = call_api_get("/api/campaigns")

if not campaigns_data:
    st.warning("Could not load campaign history — backend may be unavailable.")
    st.stop()

campaigns = campaigns_data.get("campaigns", [])

if not campaigns:
    st.info("No campaigns yet. Start your first analysis to see it here.")
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        if st.button("🚀 Start Campaign Analysis", type="primary", use_container_width=True):
            reset_campaign_state()
            st.switch_page("pages/1_brief_intake.py")
    st.stop()

# Summary
st.caption(f"{len(campaigns)} campaign(s) total")

# Search / filter
search = st.text_input("🔍 Search campaigns", placeholder="Filter by name...", key="hist_search")
if search.strip():
    campaigns = [c for c in campaigns if search.lower() in (c.get("name") or "").lower()]
    st.caption(f"{len(campaigns)} matching '{search}'")

st.divider()

st.markdown("""
<style>
.campaign-card {
    border: 1px solid #e2e8f0; border-radius: 10px; padding: 0.9rem 1.2rem;
    margin-bottom: 0.7rem; background: #fff;
    transition: box-shadow 0.2s, border-color 0.2s;
}
.campaign-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.07); border-color: #93c5fd; }
.campaign-card-name { font-weight: 700; font-size: 1rem; color: #1e293b; }
.campaign-card-meta { font-size: 0.78rem; color: #64748b; margin-top: 2px; }
.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }
.dot-qa { background: #22c55e; }
.dot-plan { background: #3b82f6; }
.dot-brief { background: #f59e0b; }
</style>
""", unsafe_allow_html=True)

for campaign in campaigns:
    campaign_name = campaign.get("name") or "Untitled Campaign"
    campaign_id = campaign.get("id", "N/A")
    created_at = str(campaign.get("created_at", "")).replace("T", " ")[:19]
    status = campaign.get("status", "in_progress").replace("_", " ").title()

    # Determine how far the campaign progressed
    has_plan = bool(campaign.get("execution_plan"))
    has_qa = bool(campaign.get("qa_report"))
    if has_qa:
        progress_label = "QA Complete"
        progress_icon = "🔍"
    elif has_plan:
        progress_label = "Plan Generated"
        progress_icon = "📊"
    else:
        progress_label = "Brief Analyzed"
        progress_icon = "📋"

    card_col1, card_col2, card_col3 = st.columns([5, 1, 1])
    with card_col1:
        _dot_class = {"QA Complete": "dot-qa", "Plan Generated": "dot-plan", "Brief Analyzed": "dot-brief"}.get(progress_label, "dot-brief")
        st.markdown(
            f"<div class='campaign-card'>"
            f"<div class='campaign-card-name'><span class='status-dot {_dot_class}'></span>{campaign_name}</div>"
            f"<div class='campaign-card-meta'>#{campaign_id} · {progress_icon} {progress_label} · {status} · {created_at}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with card_col2:
        if st.button("Resume", key=f"hist_resume_{campaign_id}", use_container_width=True):
            resumed = call_api(f"/api/campaigns/{campaign_id}/resume", {})
            if resumed and "error" not in resumed:
                restore_campaign_session(resumed)
                st.toast(f"Resumed: {campaign_name}")
                st.switch_page(page_for_stage(resumed.get("stage", 2)))
    with card_col3:
        confirm_key = f"_confirm_del_{campaign_id}"
        if st.session_state.get(confirm_key, False):
            st.warning(f"Delete **{campaign_name}**?")
            cfm_col1, cfm_col2 = st.columns(2)
            with cfm_col1:
                if st.button("✅ Yes", key=f"hist_cfm_{campaign_id}", use_container_width=True):
                    try:
                        res = requests.delete(f"{BACKEND_URL}/api/campaigns/{campaign_id}", timeout=10)
                        if res.status_code == 200:
                            st.session_state[confirm_key] = False
                            st.toast(f"Deleted: {campaign_name}")
                            st.rerun()
                        else:
                            st.error("Could not delete campaign.")
                    except Exception:
                        st.error("Delete failed — backend unreachable.")
            with cfm_col2:
                if st.button("Cancel", key=f"hist_cancel_{campaign_id}", use_container_width=True):
                    st.session_state[confirm_key] = False
                    st.rerun()
        else:
            if st.button("🗑️", key=f"hist_del_{campaign_id}", use_container_width=True):
                st.session_state[confirm_key] = True
                st.rerun()
    st.divider()
