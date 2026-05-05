import streamlit as st
import requests
import time as _time

st.set_page_config(
    page_title="Campaign Intelligence Platform",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide auto-generated page nav and collapse sidebar on homepage
st.markdown(
    """<style>
    [data-testid='stSidebarNav'] {display: none !important;}
    [data-testid='stSidebar'] {display: none !important;}
    [data-testid='stSidebarCollapsedControl'] {display: none !important;}
    .stMainBlockContainer {padding-top: 1rem !important;}
    header[data-testid='stHeader'] {display: none !important;}
    </style>""",
    unsafe_allow_html=True,
)

BACKEND_URL = "http://localhost:8000"

# --- Session State Defaults ---
defaults = {
    "stage": 1,
    "campaign_id": None,
    "session_id": None,
    "raw_brief": "",
    "enriched_brief": None,
    "questions": [],
    "answers": {},
    "execution_plan": None,
    "channel_assets": {},
    "conflicts": [],
    "qa_report": None,
    "patterns": [],
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def call_api(endpoint: str, payload: dict, retries: int = 2) -> dict | None:
    for attempt in range(retries + 1):
        try:
            res = requests.post(f"{BACKEND_URL}{endpoint}", json=payload, timeout=120)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            if attempt < retries:
                _time.sleep(1.5 * (attempt + 1))
                continue
            st.error(f"API Error (after {retries + 1} attempts): {str(e)}")
            return None


def call_api_get(endpoint: str, retries: int = 1) -> dict | None:
    for attempt in range(retries + 1):
        try:
            res = requests.get(f"{BACKEND_URL}{endpoint}", timeout=30)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            if attempt < retries:
                _time.sleep(1)
                continue
            st.error(f"API Error: {str(e)}")
            return None


def reset_campaign_state():
    for key, val in defaults.items():
        st.session_state[key] = val
    st.session_state["qa_summary"] = {}
    st.session_state["issue_statuses"] = {}
    st.session_state["plan_edit_mode"] = False
    st.session_state["_change_logs"] = {}
    st.session_state["_eval_scores"] = {}
    st.session_state["_last_uploaded_file"] = None
    # Clear widget keys that persist across campaigns
    for key in list(st.session_state.keys()):
        if key.startswith(("asset_", "answer_", "upload_asset_", "_last_asset_upload_",
                           "gen_", "custom_", "show_edit_", "brief_input")):
            del st.session_state[key]


def restore_campaign_session(campaign: dict):
    reset_campaign_state()
    st.session_state["campaign_id"] = campaign.get("campaign_id")
    st.session_state["session_id"] = campaign.get("session_id")
    st.session_state["stage"] = campaign.get("stage", 2)
    st.session_state["raw_brief"] = campaign.get("raw_brief", "")
    st.session_state["brief_input"] = campaign.get("raw_brief", "")
    st.session_state["enriched_brief"] = campaign.get("enriched_brief")
    st.session_state["questions"] = campaign.get("questions", [])
    st.session_state["execution_plan"] = campaign.get("execution_plan") or None
    st.session_state["qa_report"] = campaign.get("qa_report", [])
    st.session_state["qa_summary"] = campaign.get("qa_summary", {})
    # Restore channel assets
    saved_assets = campaign.get("channel_assets", {})
    if isinstance(saved_assets, dict):
        st.session_state["channel_assets"] = saved_assets
        for ch, copy in saved_assets.items():
            st.session_state[f"asset_{ch}"] = copy
    # Restore saved answers as {qid: answer_text} dict
    saved_answers = campaign.get("answers", [])
    if isinstance(saved_answers, list):
        st.session_state["answers"] = {
            a.get("id", ""): a.get("answer", "") for a in saved_answers if a.get("answer")
        }
    elif isinstance(saved_answers, dict):
        st.session_state["answers"] = saved_answers


def page_for_stage(stage: int) -> str:
    mapping = {
        1: "pages/1_brief_intake.py",
        2: "pages/2_clarify.py",
        3: "pages/3_plan.py",
        4: "pages/4_assets.py",
        5: "pages/5_qa_report.py",
        6: "pages/6_memory.py",
    }
    return mapping.get(stage, "pages/1_brief_intake.py")


# --- Homepage: Full-width, no sidebar content ---

# Hero section
st.markdown(
    """
    <div style="text-align: center; padding: 0.5rem 0 1rem 0;">
        <h1 style="font-size: 2.8rem;">🎯 Campaign Intelligence Platform</h1>
        <p style="font-size: 1.25rem; color: #666; max-width: 700px; margin: 0 auto;">
            Analyze campaign briefs, generate execution plans, and catch copy errors —
            all powered by AI, in minutes instead of days.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# CTA
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    st.markdown(
        "<div style='text-align: center; padding: 0.5rem 0 1.5rem 0;'>",
        unsafe_allow_html=True,
    )
    if st.button("🚀 Start Campaign Analysis", type="primary", use_container_width=True):
        reset_campaign_state()
        st.switch_page("pages/1_brief_intake.py")
    st.markdown("</div>", unsafe_allow_html=True)

# Quick-resume for active campaign
_active_campaign_id = st.session_state.get("campaign_id")
_active_stage = st.session_state.get("stage", 1)
if _active_campaign_id:
    _eb = st.session_state.get("enriched_brief") or {}
    _campaign_name = _eb.get("campaignName", f"Campaign #{_active_campaign_id}")
    _stage_labels = {1: "Brief Intake", 2: "Clarification", 3: "Execution Plan",
                     4: "Asset Submission", 5: "QA Report", 6: "Knowledge Base"}
    _stage_label = _stage_labels.get(_active_stage, "")
    _resume_col1, _resume_col2, _resume_col3 = st.columns([1, 2, 1])
    with _resume_col2:
        st.info(f"You have an active campaign: **{_campaign_name}** — Stage {_active_stage} ({_stage_label})")
        if st.button(f"▶️ Continue: {_campaign_name}", use_container_width=True):
            st.switch_page(page_for_stage(_active_stage))

# How It Works
st.markdown("### How It Works")
st.markdown("Your campaign goes through a structured 6-step review pipeline:")

_CARD_CSS = """
<style>
.step-card {
    border: 1px solid #e5e7eb; border-radius: 10px; padding: 1rem 1.1rem;
    margin-bottom: 0.8rem; background: linear-gradient(135deg, #fafafa 0%, #f5f7ff 100%);
    transition: box-shadow 0.2s; min-height: 120px;
}
.step-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
.step-card-icon { font-size: 1.6rem; margin-bottom: 0.3rem; }
.step-card-title { font-weight: 700; font-size: 0.95rem; margin-bottom: 0.3rem; color: #1e293b; }
.step-card-desc { font-size: 0.82rem; color: #64748b; line-height: 1.45; }
</style>
"""

_STEPS_INFO = [
    ("📋", "Step 1 — Brief Intake", "Upload or paste your campaign brief. The system identifies gaps and generates targeted clarifying questions."),
    ("❓", "Step 2 — Clarification", "Answer prioritized questions to fill gaps in your brief. Context-aware suggestions help you respond faster."),
    ("📊", "Step 3 — Execution Plan", "A structured, channel-by-channel plan is generated with copy guidance, timelines, and budget allocation."),
    ("📎", "Step 4 — Asset Submission", "Upload or paste copy for each channel. The system checks every asset against your brief for consistency."),
    ("🔍", "Step 5 — QA Report", "Issues are ranked by severity with specific fix suggestions. Apply fixes individually or all at once."),
    ("📚", "Step 6 — Knowledge Base", "Lessons learned are stored for future campaigns. Export your full report as JSON, DOCX, or PDF."),
]

st.markdown(_CARD_CSS, unsafe_allow_html=True)

_card_cols = st.columns(3)
for _idx, (_icon, _title, _desc) in enumerate(_STEPS_INFO):
    with _card_cols[_idx % 3]:
        st.markdown(
            f"<div class='step-card'>"
            f"<div class='step-card-icon'>{_icon}</div>"
            f"<div class='step-card-title'>{_title}</div>"
            f"<div class='step-card-desc'>{_desc}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.divider()

# Quick access to campaign history
campaigns_data = call_api_get("/api/campaigns")
campaign_count = len(campaigns_data.get("campaigns", [])) if campaigns_data else 0

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(f"### 📁 Campaign History ({campaign_count})")
    st.caption("View, resume, or manage your previous campaign analyses.")
with col_h2:
    if st.button("View All Campaigns →", use_container_width=True):
        st.switch_page("pages/7_history.py")

# Footer — system health
health = call_api_get("/api/health")
if health and all(v == "ok" for v in health.get("services", {}).values()):
    st.caption("✅ All services operational")
else:
    st.caption("⚠️ Some services may be unavailable")
