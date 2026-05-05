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

if "qa_summary" not in st.session_state:
    st.session_state.qa_summary = {}
if "issue_statuses" not in st.session_state:
    st.session_state.issue_statuses = {}

st.set_page_config(page_title="Quality Assurance Report", page_icon="🔍", layout="wide")

st.title("🔍 Quality Assurance Report")

render_sidebar(5)
render_stepper(5)

if not st.session_state.qa_report:
    st.warning("Please complete Asset Submission first — no QA report generated yet.")
    st.page_link("pages/4_assets.py", label="← Go to Asset Submission", icon="⬅️")
    st.stop()

qa_report = st.session_state.qa_report
summary = st.session_state.get("qa_summary", {})

# Summary metrics row
_crit = summary.get('critical', 0)
_warn = summary.get('warning', 0)
_adv = summary.get('advisory', 0)
_total = summary.get('total', _crit + _warn + _adv)

st.markdown("""
<style>
.qa-metric { border-radius: 10px; padding: 1rem 1.2rem; text-align: center; }
.qa-metric-num { font-size: 2rem; font-weight: 800; line-height: 1.2; }
.qa-metric-label { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
.qa-crit { background: #fef2f2; border: 1.5px solid #fca5a5; }
.qa-crit .qa-metric-num { color: #dc2626; }
.qa-crit .qa-metric-label { color: #b91c1c; }
.qa-warn { background: #fffbeb; border: 1.5px solid #fcd34d; }
.qa-warn .qa-metric-num { color: #d97706; }
.qa-warn .qa-metric-label { color: #b45309; }
.qa-adv { background: #eff6ff; border: 1.5px solid #93c5fd; }
.qa-adv .qa-metric-num { color: #2563eb; }
.qa-adv .qa-metric-label { color: #1d4ed8; }
.qa-total { background: #f8fafc; border: 1.5px solid #cbd5e1; }
.qa-total .qa-metric-num { color: #334155; }
.qa-total .qa-metric-label { color: #64748b; }
.severity-badge {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.3px;
}
.sev-critical { background: #fef2f2; color: #dc2626; border: 1px solid #fca5a5; }
.sev-warning { background: #fffbeb; color: #d97706; border: 1px solid #fcd34d; }
.sev-advisory { background: #eff6ff; color: #2563eb; border: 1px solid #93c5fd; }
</style>
""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"<div class='qa-metric qa-crit'><div class='qa-metric-num'>{_crit}</div><div class='qa-metric-label'>Critical</div></div>", unsafe_allow_html=True)
with m2:
    st.markdown(f"<div class='qa-metric qa-warn'><div class='qa-metric-num'>{_warn}</div><div class='qa-metric-label'>Warning</div></div>", unsafe_allow_html=True)
with m3:
    st.markdown(f"<div class='qa-metric qa-adv'><div class='qa-metric-num'>{_adv}</div><div class='qa-metric-label'>Advisory</div></div>", unsafe_allow_html=True)
with m4:
    st.markdown(f"<div class='qa-metric qa-total'><div class='qa-metric-num'>{_total}</div><div class='qa-metric-label'>Total</div></div>", unsafe_allow_html=True)

st.divider()

# Sort: CRITICAL first, then WARNING, then ADVISORY
severity_order = {"CRITICAL": 0, "WARNING": 1, "ADVISORY": 2}
sorted_report = sorted(qa_report, key=lambda x: severity_order.get(x.get("severity", "ADVISORY"), 3))

# Count pending issues for bulk action
pending_ids = [
    issue.get("id", "unknown")
    for issue in sorted_report
    if st.session_state.issue_statuses.get(issue.get("id", "unknown"), issue.get("status", "pending")) == "pending"
]

# Bulk action bar
if pending_ids:
    bulk_col1, bulk_col2, bulk_col3 = st.columns([2, 2, 4])
    with bulk_col1:
        if st.button(f"✅ Apply Fix to All ({len(pending_ids)})", type="primary"):
            for issue in sorted_report:
                iid = issue.get("id", "unknown")
                if iid in pending_ids:
                    st.session_state.issue_statuses[iid] = "approved"
                    # Auto-apply: patch the asset copy
                    ch = issue.get("channel", "")
                    current = issue.get("current_text", "")
                    fix = issue.get("suggested_fix", "")
                    if ch and current and fix and ch in st.session_state.channel_assets:
                        st.session_state.channel_assets[ch] = st.session_state.channel_assets[ch].replace(current, fix)
            st.toast(f"✅ Applied fixes to {len(pending_ids)} issue(s)")
            st.rerun()
    with bulk_col2:
        if st.button(f"🚫 Dismiss All ({len(pending_ids)})"):
            for pid in pending_ids:
                st.session_state.issue_statuses[pid] = "dismissed"
            st.toast(f"Dismissed {len(pending_ids)} issue(s)")
            st.rerun()

    st.divider()

resolved_count = 0
total_count = len(sorted_report)

for issue in sorted_report:
    issue_id = issue.get("id", "unknown")
    severity = issue.get("severity", "ADVISORY")
    status = st.session_state.issue_statuses.get(issue_id, issue.get("status", "pending"))

    # Color coding
    if severity == "CRITICAL":
        color = "🔴"
        border_type = "error"
    elif severity == "WARNING":
        color = "🟡"
        border_type = "warning"
    else:
        color = "🔵"
        border_type = "info"

    if status in ("approved", "dismissed"):
        resolved_count += 1

    with st.container():
        _sev_class = {"CRITICAL": "sev-critical", "WARNING": "sev-warning", "ADVISORY": "sev-advisory"}.get(severity, "sev-advisory")
        st.markdown(
            f"### {issue.get('channel', '')} / {issue.get('dimension', '')} "
            f"<span class='severity-badge {_sev_class}'>{severity}</span>",
            unsafe_allow_html=True,
        )

        if status == "approved":
            st.success("✅ Fix applied")
        elif status == "dismissed":
            st.info("🚫 Dismissed")
        else:
            st.markdown(f"**Current:** :red[{issue.get('current_text', '')}]")
            st.markdown(f"**Brief requires:** :blue[{issue.get('brief_requirement', '')}]")
            st.markdown(f"**Suggested fix:** :green[{issue.get('suggested_fix', '')}]")
            st.markdown(f"**Business impact:** {issue.get('business_impact', '')}")

            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button(f"✅ Apply Fix", key=f"apply_{issue_id}"):
                    st.session_state.issue_statuses[issue_id] = "approved"
                    # Auto-apply: patch the asset copy with the suggested fix
                    ch = issue.get("channel", "")
                    current = issue.get("current_text", "")
                    fix = issue.get("suggested_fix", "")
                    if ch and current and fix and ch in st.session_state.channel_assets:
                        st.session_state.channel_assets[ch] = st.session_state.channel_assets[ch].replace(current, fix)
                    st.rerun()
            with btn_col2:
                if st.button(f"✏️ Custom Edit", key=f"edit_{issue_id}"):
                    st.session_state[f"show_edit_{issue_id}"] = True
            with btn_col3:
                if st.button(f"🚫 Dismiss", key=f"dismiss_{issue_id}"):
                    st.session_state.issue_statuses[issue_id] = "dismissed"
                    st.rerun()

            if st.session_state.get(f"show_edit_{issue_id}", False):
                custom = st.text_input(
                    "Enter custom fix:",
                    value=issue.get("suggested_fix", ""),
                    key=f"custom_{issue_id}",
                )
                if st.button("Save Custom Fix", key=f"save_{issue_id}"):
                    st.session_state.issue_statuses[issue_id] = "approved"
                    # Patch the asset copy with the custom fix text
                    ch = issue.get("channel", "")
                    current = issue.get("current_text", "")
                    custom_text = st.session_state.get(f"custom_{issue_id}", "")
                    if ch and current and custom_text and ch in st.session_state.channel_assets:
                        st.session_state.channel_assets[ch] = st.session_state.channel_assets[ch].replace(current, custom_text)
                    st.rerun()

        st.divider()

# Progress bar
st.progress(resolved_count / max(total_count, 1))
st.write(f"{resolved_count} / {total_count} issues resolved")

critical_pending = [
    issue for issue in sorted_report
    if issue.get("severity") == "CRITICAL"
    and st.session_state.issue_statuses.get(issue.get("id"), "pending") == "pending"
]
if critical_pending:
    st.warning(f"⚠️ {len(critical_pending)} CRITICAL issue(s) still unresolved.")

# View updated assets after fixes
if resolved_count > 0:
    with st.expander(f"📝 View Updated Assets ({resolved_count} fix{'es' if resolved_count != 1 else ''} applied)", expanded=False):
        _assets = st.session_state.get("channel_assets", {})
        if _assets:
            for _ch, _copy in _assets.items():
                if _copy.strip():
                    st.markdown(f"**{_ch}**")
                    st.code(_copy, language=None)
        else:
            st.info("No assets in session. Go back to Stage 4 to add channel copy.")

# Re-run QA button — lets users verify fixes by re-checking updated assets
if resolved_count > 0:
    st.divider()
    if st.button("🔄 Re-run QA on Updated Assets"):
        assets_with_content = {
            ch: copy for ch, copy in st.session_state.channel_assets.items() if copy.strip()
        }
        if len(assets_with_content) < 2:
            st.error("Not enough asset content to re-run. Go back to Asset Submission to add more.")
        else:
            rerun_results = run_with_status("Re-checking Updated Assets", [
                ("Checking asset consistency", lambda: call_api("/api/agent3/check", {
                    "campaign_id": st.session_state.campaign_id,
                    "assets": [
                        {"channel": ch, "copy": copy}
                        for ch, copy in assets_with_content.items()
                    ],
                })),
            ])
            check_result = rerun_results.get(0)
            if check_result and "error" not in check_result:
                conflicts = check_result.get("conflicts", [])
                st.session_state.conflicts = conflicts

                qa_rerun = run_with_status("Generating Updated Report", [
                    ("Generating fix suggestions", lambda: call_api("/api/agent4/qa", {
                        "campaign_id": st.session_state.campaign_id,
                        "conflicts": conflicts,
                    })),
                ])
                qa_result = qa_rerun.get(0)
                if qa_result and "error" not in qa_result:
                        st.session_state.qa_report = qa_result.get("qa_report", [])
                        st.session_state.qa_summary = qa_result.get("summary", {})
                        st.session_state.issue_statuses = {}
                        st.toast("✅ QA re-run complete — report updated!")
                        st.rerun()

st.divider()

qa_nav_col1, qa_nav_col2 = st.columns(2)
with qa_nav_col1:
    if st.button("⬅️ Back to Asset Submission"):
        st.session_state.stage = 4
        st.switch_page("pages/4_assets.py")

if st.button("📚 Finalize & Log to Memory", type="primary", help="Extracts reusable patterns from this campaign's QA report and stores them in the knowledge base for future proactive warnings"):
    results = run_with_status("Extracting Campaign Patterns", [
        ("Analyzing QA report for lessons", lambda: None),
        ("Storing patterns to knowledge base", lambda: call_api("/api/agent5/learn", {
            "campaign_id": st.session_state.campaign_id,
        })),
    ])
    result = results.get(1)

    if result and "error" not in result:
        st.session_state.patterns = result.get("patterns", [])
        st.session_state.stage = 6
        st.success("Patterns extracted and stored!")
        st.toast("✅ QA finalized — moving to Memory & Export!")
        st.balloons()
        st.switch_page("pages/6_memory.py")
    elif result:
        st.error(f"Error: {result.get('error')}")
