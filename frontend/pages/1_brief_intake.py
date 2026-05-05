import streamlit as st
import hashlib
import requests
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import call_api, BACKEND_URL, defaults
from utils.file_parser import extract_text_from_pdf, extract_text_from_docx
from utils.stepper import render_stepper
from utils.sidebar import render_sidebar
from utils.loader import run_with_status

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.set_page_config(page_title="Campaign Brief Intake", page_icon="📋", layout="wide")

SAMPLE_BRIEF_A = """Campaign Name: Q3 Enterprise Trial-to-Paid Push
Business Objective: Convert 200 enterprise trial accounts (1000+ employees) to paid contracts before end of Q3. Secondary: generate 50 new enterprise demo requests from net-new prospects.
Target Audience: Trial users at companies with 1000+ employees in technology, financial services, and professional services. Decision-maker titles: VP of Operations, Director of Revenue Operations, Chief Marketing Officer.
Key Message: Teams that manage revenue operations at scale are leaving hours of manual work on the table. Our platform eliminates the reporting lag between data capture and decision.
Channels: Email, LinkedIn, social (unspecified), sales outreach
Budget: Not specified
Timeline: Campaign live by July 1, all assets locked by June 20
Success Metrics: Trial-to-paid conversion rate (baseline 14%, target 22%); 50 new enterprise demo requests in 6 weeks
Constraints: Do not reference competitors. Claims about time savings need customer quotes. Tone: confident, not aggressive. Avoid AI-powered without a concrete example."""

SAMPLE_BRIEF_B = """Campaign Name: Summer Re-Purchase Drive — Home & Garden
Business Objective: Drive 15% lift in repeat purchase rate among Home & Garden buyers from last 12 months who haven't purchased in 90 days.
Target Audience: Lapsed customers, homeowners aged 35-55, 2+ past purchases, email and SMS opted-in.
Key Message: Your garden doesn't wait for the right moment. Neither do our summer prices.
Channels: Email, SMS, Instagram, Facebook, loyalty push notification
Budget: $18,000 total. Email/SMS $3,000. Paid social $12,000. Creative $3,000.
Timeline: June 15 to July 31. Flash sales July 4 weekend and July 21.
Success Metrics: Repeat purchase rate baseline 22% target 25%; AOV baseline $67 target $74; email open rate >28%; SMS click rate >12%
Constraints: No countdown timers in email (EU legal). Suppress active buyers from flash sale. Warm enthusiastic tone, never pressuring."""

def load_sample_brief(sample_text: str) -> None:
    st.session_state.raw_brief = sample_text
    st.session_state.brief_input = sample_text

st.title("📋 Campaign Brief Intake")

render_sidebar(1)
render_stepper(1)

col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("📄 Upload a Campaign Document")

    # Upload behavior guidance
    with st.expander("ℹ️ How does file upload work?", expanded=False):
        st.markdown(
            "**Upload flow:**\n"
            "1. Upload a **PDF** or **DOCX** file containing your campaign brief\n"
            "2. Text is automatically extracted and shown in the editor below\n"
            "3. Review and edit the extracted text if needed\n"
            "4. Click **Analyze Brief** to start a **new campaign session**\n\n"
            "**Important:**\n"
            "- Each upload + analysis creates a **new campaign** with a fresh session\n"
            "- Uploading a new file **replaces** the current text — it does not append\n"
            "- You can edit the extracted text freely before analyzing\n"
            "- Your previous campaigns are saved and visible in the sidebar"
        )

    uploaded_file = st.file_uploader(
        "Upload a PDF or DOCX campaign brief",
        type=["pdf", "docx"],
        help="Supported formats: PDF, DOCX. Text will be extracted and shown below for review.",
    )
    if uploaded_file is not None:
        # Only process if this is a new file (avoid re-extracting on every rerun)
        last_uploaded = st.session_state.get("_last_uploaded_file", None)
        if last_uploaded != uploaded_file.name + str(uploaded_file.size):
            try:
                if uploaded_file.name.lower().endswith(".pdf"):
                    extracted = extract_text_from_pdf(uploaded_file)
                else:
                    extracted = extract_text_from_docx(uploaded_file)
                if extracted.strip():
                    st.session_state.raw_brief = extracted
                    st.session_state.brief_input = extracted
                    st.session_state._last_uploaded_file = uploaded_file.name + str(uploaded_file.size)
                    st.rerun()
                else:
                    st.warning("The uploaded file appears to be empty. Please try a different file.")
            except Exception as e:
                st.error(f"Could not read file: {e}")
        else:
            st.success(f"✅ Extracted text from **{uploaded_file.name}** — review below and click Analyze.")

    st.markdown("---")
    st.subheader("✏️ Or Paste Your Brief")
    brief_text = st.text_area(
        "Paste your campaign brief here",
        value=st.session_state.raw_brief,
        height=350,
        key="brief_input",
    )

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        st.button(
            "Load Sample A (B2B SaaS)",
            on_click=load_sample_brief,
            args=[SAMPLE_BRIEF_A],
        )
    with btn_col2:
        st.button(
            "Load Sample B (B2C Retail)",
            on_click=load_sample_brief,
            args=[SAMPLE_BRIEF_B],
        )

with col_right:
    st.info(
        "**What happens next:**\n\n"
        "- Your brief is scanned for missing or ambiguous information\n"
        "- Targeted clarifying questions are generated with suggestions\n"
        "- Gaps are categorized for easy review"
    )

    # Show proactive warnings from past campaigns (cached by brief hash)
    if brief_text.strip():
        _brief_hash = hashlib.md5(brief_text.strip().encode()).hexdigest()
        _last_hash = st.session_state.get("_last_warn_brief_hash", "")
        _cached_warnings = st.session_state.get("_cached_warnings", [])

        if _brief_hash != _last_hash:
            try:
                res = requests.post(
                    f"{BACKEND_URL}/api/agent5/warn",
                    json={"brief": brief_text},
                    timeout=30,
                )
                if res.status_code == 200:
                    _cached_warnings = res.json().get("warnings", [])
                    st.session_state["_cached_warnings"] = _cached_warnings
                    st.session_state["_last_warn_brief_hash"] = _brief_hash
            except Exception:
                pass  # No warnings if backend unreachable

        if _cached_warnings:
            st.subheader("⚠️ Insights from Past Campaigns")
            for w in _cached_warnings:
                st.warning(
                    f"**{w.get('pattern', '')}** — "
                    f"{w.get('recommendation', '')}"
                )

st.divider()

if st.button("🔍 Analyze Brief", type="primary", help="Sends your brief to the AI analyzer which extracts fields, identifies gaps, and generates clarifying questions"):
    if not brief_text.strip():
        st.error("Please paste a campaign brief before analyzing.")
    else:
        st.session_state.raw_brief = brief_text

        results = run_with_status("Analyzing Campaign Brief", [
            ("Scanning brief for gaps and ambiguities", lambda: None),
            ("Generating clarifying questions", lambda: call_api("/api/agent1/analyze", {"brief": brief_text})),
        ])
        result = results.get(1)

        if result and "error" not in result:
            st.session_state.session_id = result.get("session_id")
            st.session_state.campaign_id = result.get("campaign_id")
            st.session_state.enriched_brief = result.get("enriched_brief")
            st.session_state.questions = result.get("questions", [])
            st.session_state.stage = 2

            st.success(
                f"Brief analyzed! Campaign #{result.get('campaign_id')} created. "
                f"{len(result.get('questions', []))} clarifying questions generated."
            )
            st.toast("✅ Brief analyzed — moving to Clarification!")
            st.balloons()
            st.switch_page("pages/2_clarify.py")
        elif result:
            st.error(f"Error: {result.get('error', 'Unknown error')}")
