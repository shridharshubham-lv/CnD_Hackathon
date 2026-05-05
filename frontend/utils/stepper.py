import streamlit as st

STEPS = [
    ("📋", "Brief Intake"),
    ("❓", "Clarification"),
    ("📊", "Execution Plan"),
    ("📎", "Asset Submission"),
    ("🔍", "QA Report"),
    ("📚", "Knowledge Base"),
]

_STEPPER_CSS = """
<style>
.stepper-row { display: flex; align-items: flex-start; justify-content: center; gap: 0; padding: 0.5rem 0 0.2rem 0; }
.stepper-step { display: flex; flex-direction: column; align-items: center; position: relative; flex: 1; min-width: 0; }
.stepper-circle {
    width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center;
    justify-content: center; font-size: 1.1rem; z-index: 2; border: 2.5px solid;
}
.stepper-circle.done { background: #22c55e; border-color: #16a34a; color: #fff; }
.stepper-circle.active { background: #3b82f6; border-color: #2563eb; color: #fff; box-shadow: 0 0 0 4px rgba(59,130,246,0.2); }
.stepper-circle.pending { background: #f3f4f6; border-color: #d1d5db; color: #9ca3af; }
.stepper-label { font-size: 0.72rem; margin-top: 4px; text-align: center; line-height: 1.2; }
.stepper-label.done { color: #22c55e; font-weight: 600; }
.stepper-label.active { color: #3b82f6; font-weight: 700; }
.stepper-label.pending { color: #9ca3af; }
.stepper-line {
    position: absolute; top: 19px; left: calc(50% + 22px); right: calc(-50% + 22px);
    height: 3px; z-index: 1; border-radius: 2px;
}
.stepper-line.done { background: #22c55e; }
.stepper-line.active { background: linear-gradient(90deg, #22c55e 0%, #3b82f6 100%); }
.stepper-line.pending { background: #e5e7eb; }
</style>
"""


def render_stepper(current_step: int):
    """Render a horizontal progress stepper with connecting lines. current_step is 1-indexed."""
    steps_html = []
    for i, (icon, label) in enumerate(STEPS):
        step_num = i + 1
        if step_num < current_step:
            state = "done"
            circle_content = "✓"
        elif step_num == current_step:
            state = "active"
            circle_content = icon
        else:
            state = "pending"
            circle_content = icon

        # Connecting line (not on the last step)
        line_html = ""
        if i < len(STEPS) - 1:
            if step_num < current_step:
                line_state = "done"
            elif step_num == current_step:
                line_state = "active"
            else:
                line_state = "pending"
            line_html = f"<div class='stepper-line {line_state}'></div>"

        steps_html.append(
            f"<div class='stepper-step'>"
            f"  <div class='stepper-circle {state}'>{circle_content}</div>"
            f"  <div class='stepper-label {state}'>{label}</div>"
            f"  {line_html}"
            f"</div>"
        )

    st.markdown(_STEPPER_CSS + "<div class='stepper-row'>" + "".join(steps_html) + "</div>", unsafe_allow_html=True)
    st.divider()
