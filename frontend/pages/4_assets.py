import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import call_api, defaults
from utils.file_parser import extract_text_from_pdf, extract_text_from_docx
from utils.stepper import render_stepper
from utils.sidebar import render_sidebar
from utils.loader import run_with_status

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.set_page_config(page_title="Channel Asset Submission", page_icon="📎", layout="wide")

st.title("📎 Channel Asset Submission")

render_sidebar(4)
render_stepper(4)

if not st.session_state.execution_plan:
    st.warning("Please complete the Execution Plan first — no plan available yet.")
    st.page_link("pages/3_plan.py", label="← Go to Execution Plan", icon="⬅️")
    st.stop()

DEMO_ASSETS = {
    "Email": """Subject: Ready to schedule a call about your trial?

Hi [First Name], your team has been exploring our platform for a few weeks.
We'd love to schedule a call to walk you through what's possible at enterprise scale.
Our customers save hours every week on manual reporting. Let's talk about what that
could mean for your team.

[Schedule a call]""",
    "LinkedIn": """Struggling with your reporting workflow? Our tool makes it easy and quick to learn —
even for teams just getting started with revenue ops. Give it a try today and see
results fast.

Start your free trial →""",
    "Paid Search": """Headline 1: AI-Powered Revenue Operations
Headline 2: Automate Your Reporting Today
Description: Our AI-powered platform handles revenue reporting automatically.
Save time, reduce errors. Start free.""",
    "Landing Page": """The smart way to manage revenue operations.
See why 500+ teams trust us to handle their reporting.
Book a demo today.""",
    "Sales Outreach": """Hi [Name], I noticed your team has been using our trial for a few weeks.
Would love to jump on a quick call to share how similar companies use us.
Let me know a time that works!""",
}

st.info(
    "**Provide copy assets for each channel** — upload a document (PDF/DOCX), paste text directly, "
    "or **generate all channels from a single source asset** using AI."
)

channels = st.session_state.execution_plan.get("channels", [])
channel_names = [ch.get("name", f"Channel {i}") for i, ch in enumerate(channels)]

# Add demo channels if not in plan
for demo_ch in DEMO_ASSETS:
    if demo_ch not in channel_names:
        channel_names.append(demo_ch)

if not channel_names:
    st.error("No channels found in the execution plan. Please go back and regenerate the plan.")
    st.stop()

# --- Generate from Source Asset ---
with st.expander("🤖 Generate Channel Assets from a Single Source", expanded=False):
    st.markdown(
        "Paste one approved asset (e.g., your Email copy) and the AI will adapt it "
        "for every other channel — maintaining brand compliance and logging every change."
    )

    gen_col1, gen_col2 = st.columns([3, 1])
    with gen_col1:
        source_copy = st.text_area(
            "Source asset copy",
            height=180,
            key="gen_source_copy",
            placeholder="Paste your approved source copy here (e.g., your finalized Email draft)...",
        )
    with gen_col2:
        source_channel = st.selectbox(
            "Source channel",
            options=channel_names,
            key="gen_source_channel",
        )
        target_channels = [ch for ch in channel_names if ch != source_channel]
        st.caption(f"Will generate for: {', '.join(target_channels)}")

    if st.button("🚀 Generate Adapted Assets", type="primary"):
        if not source_copy.strip():
            st.error("Please paste a source asset before generating.")
        elif not target_channels:
            st.error("Need at least 2 channels in the plan to generate adaptations.")
        else:
            gen_results = run_with_status("Generating Channel-Adapted Assets", [
                ("Analyzing source asset against brief", lambda: None),
                ("Adapting copy for each channel", lambda: call_api("/api/agent6/generate", {
                    "campaign_id": st.session_state.campaign_id,
                    "source_asset": source_copy,
                    "source_channel": source_channel,
                    "target_channels": target_channels,
                })),
            ])
            gen_result = gen_results.get(1)

            if gen_result and "error" not in gen_result:
                adaptations = gen_result.get("adaptations", [])
                # Store generated assets into session state
                for adapt in adaptations:
                    ch = adapt.get("channel", "")
                    copy = adapt.get("adapted_copy", "")
                    if ch and copy:
                        st.session_state.channel_assets[ch] = copy
                        st.session_state[f"asset_{ch}"] = copy

                # Also store the source channel's copy
                st.session_state.channel_assets[source_channel] = source_copy
                st.session_state[f"asset_{source_channel}"] = source_copy

                # Store change logs in session state for display
                st.session_state["_change_logs"] = {
                    a.get("channel"): a.get("change_log", []) for a in adaptations
                }

                st.toast(f"✅ Generated assets for {len(adaptations)} channels!")
                st.rerun()
            elif gen_result:
                st.error(f"Generation error: {gen_result.get('error')}")

    # Display change logs if they exist
    change_logs = st.session_state.get("_change_logs", {})
    if change_logs:
        st.divider()
        st.subheader("📋 Change Log — Modifications Traced to Brief Rules")
        for ch, logs in change_logs.items():
            if not logs:
                continue
            with st.expander(f"📝 {ch} ({len(logs)} change{'s' if len(logs) != 1 else ''})"):
                for entry in logs:
                    st.markdown(
                        f"• **Change:** {entry.get('change', '')}\n\n"
                        f"  **Rule:** _{entry.get('reason', '')}_"
                    )

st.divider()

tabs = st.tabs(channel_names)

# Channel-specific placeholder guidance
CHANNEL_PLACEHOLDERS = {
    "Email": "e.g. Subject line, greeting, body copy, CTA button text, sign-off...",
    "LinkedIn": "e.g. Post copy, hashtags, CTA link text...",
    "Paid Search": "e.g. Headlines (30 chars each), descriptions (90 chars), display URL...",
    "Landing Page": "e.g. Hero headline, subheadline, body copy, CTA button, testimonial...",
    "Sales Outreach": "e.g. Subject line, personalized opening, value proposition, CTA, sign-off...",
    "SMS": "e.g. Short message (160 chars), CTA link, opt-out notice...",
    "Instagram": "e.g. Caption, hashtags, CTA, story text overlay...",
    "Facebook": "e.g. Ad headline, primary text, description, CTA button label...",
}
DEFAULT_PLACEHOLDER = "Enter your copy for this channel — include headlines, body text, CTAs, and any key messaging."

for i, tab in enumerate(tabs):
    ch_name = channel_names[i]
    with tab:
        placeholder = CHANNEL_PLACEHOLDERS.get(ch_name, DEFAULT_PLACEHOLDER)
        has_demo = ch_name in DEMO_ASSETS

        # File upload option
        uploaded_asset = st.file_uploader(
            f"Upload {ch_name} copy (PDF or DOCX)",
            type=["pdf", "docx"],
            key=f"upload_asset_{ch_name}",
            help=f"Upload a document containing your {ch_name} copy. Text will be extracted below.",
        )
        if uploaded_asset is not None:
            upload_key = f"_last_asset_upload_{ch_name}"
            last_upload = st.session_state.get(upload_key, None)
            if last_upload != uploaded_asset.name + str(uploaded_asset.size):
                try:
                    if uploaded_asset.name.lower().endswith(".pdf"):
                        extracted = extract_text_from_pdf(uploaded_asset)
                    else:
                        extracted = extract_text_from_docx(uploaded_asset)
                    if extracted.strip():
                        st.session_state.channel_assets[ch_name] = extracted
                        st.session_state[f"asset_{ch_name}"] = extracted
                        st.session_state[upload_key] = uploaded_asset.name + str(uploaded_asset.size)
                        st.rerun()
                    else:
                        st.warning("Uploaded file appears empty.")
                except Exception as e:
                    st.error(f"Could not read file: {e}")
            else:
                st.success(f"✅ Loaded copy from **{uploaded_asset.name}**")

        # Text area with placeholder or demo content
        # Only use demo assets as default when no active campaign exists
        if st.session_state.campaign_id is not None:
            default_value = st.session_state.channel_assets.get(ch_name, "")
        else:
            default_value = st.session_state.channel_assets.get(
                ch_name, DEMO_ASSETS.get(ch_name, "")
            )
        content = st.text_area(
            f"Copy for {ch_name}",
            value=default_value,
            height=200,
            key=f"asset_{ch_name}",
            placeholder=placeholder,
        )
        if not has_demo and not content.strip():
            st.caption(f"💡 *{placeholder}*")
        # Character count with limit warnings for length-sensitive channels
        CHANNEL_LIMITS = {"SMS": 160, "Paid Search": 90}
        char_count = len(content)
        limit = CHANNEL_LIMITS.get(ch_name)
        if limit and char_count > limit:
            st.caption(f":red[{char_count} / {limit} characters — over limit]")
        elif limit:
            st.caption(f"{char_count} / {limit} characters")
        else:
            st.caption(f"{char_count} characters")
        st.session_state.channel_assets[ch_name] = content

st.divider()

# --- Channel Fill Indicator ---
_filled = {ch: bool(st.session_state.channel_assets.get(ch, "").strip()) for ch in channel_names}
_filled_count = sum(_filled.values())
_total_channels = len(channel_names)
st.markdown(f"**Channel status: {_filled_count} / {_total_channels} filled**")
_indicator_cols = st.columns(min(_total_channels, 6))
for idx, ch in enumerate(channel_names):
    with _indicator_cols[idx % len(_indicator_cols)]:
        if _filled[ch]:
            st.success(f"✅ {ch}")
        else:
            st.error(f"❌ {ch}")

nav_col1, _nav_spacer = st.columns([1, 3])
with nav_col1:
    if st.button("⬅️ Back to Execution Plan"):
        st.session_state.stage = 3
        st.switch_page("pages/3_plan.py")

st.caption(
    "The consistency check runs two AI passes: one to classify asset conflicts and one to write fixes. "
    "With multiple channels, this can take longer than a normal page action."
)

if st.button("🔍 Run Consistency Check", type="primary", help="Runs two AI passes: first classifies asset conflicts against the brief, then generates severity-ranked fix suggestions"):
    assets_with_content = {
        ch: copy for ch, copy in st.session_state.channel_assets.items() if copy.strip()
    }

    if len(assets_with_content) < 2:
        st.error("Please provide content for at least 2 channels.")
    else:
        results = run_with_status(
            "Running Quality Check",
            [
                ("Checking asset consistency against brief", lambda: call_api("/api/agent3/check", {
                    "campaign_id": st.session_state.campaign_id,
                    "assets": [
                        {"channel": ch, "copy": copy}
                        for ch, copy in assets_with_content.items()
                    ],
                })),
            ],
            intro="Each asset is being compared against the approved brief and execution plan to detect misalignments.",
            expectations=[
                "More channels and longer copy usually mean a longer wait.",
                "The next step generates fix suggestions automatically after the consistency pass finishes.",
                "If the run succeeds, the app will move straight to QA Report.",
            ],
        )
        check_result = results.get(0)

        if check_result and "error" not in check_result:
            conflicts = check_result.get("conflicts", [])
            st.session_state.conflicts = conflicts

            errors = check_result.get("errors_found", 0)
            adaptations = len(conflicts) - errors

            st.success(
                f"Found **{errors} errors** and **{adaptations} intentional adaptations** "
                f"across {check_result.get('total_checked', 0)} assets."
            )

            # Agent 4 — QA Report
            qa_results = run_with_status(
                "Generating Fix Suggestions",
                [
                    ("Ranking issues by severity", lambda: None),
                    ("Generating fix suggestions", lambda: call_api("/api/agent4/qa", {
                        "campaign_id": st.session_state.campaign_id,
                        "conflicts": conflicts,
                    })),
                ],
                intro="Detected conflicts are being ranked by severity and transformed into actionable fix suggestions.",
                expectations=[
                    "The status box will show each sub-step as it completes.",
                    "When this finishes, the page will switch to QA Report automatically.",
                ],
            )
            qa_result = qa_results.get(1)

            if qa_result and "error" not in qa_result:
                st.session_state.qa_report = qa_result.get("qa_report", [])
                st.session_state.qa_summary = qa_result.get("summary", {})
                st.session_state.stage = 5

                summary = qa_result.get("summary", {})
                st.info(
                    f"QA Report: {summary.get('critical', 0)} critical, "
                    f"{summary.get('warning', 0)} warnings, "
                    f"{summary.get('advisory', 0)} advisory"
                )
                st.toast("✅ Consistency check complete — moving to QA Report!")
                st.balloons()
                st.switch_page("pages/5_qa_report.py")
            elif qa_result:
                st.error(f"QA Error: {qa_result.get('error')}")
        elif check_result:
            st.error(f"Check Error: {check_result.get('error')}")
