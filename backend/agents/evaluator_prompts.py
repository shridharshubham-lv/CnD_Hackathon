"""Grading rubric prompts for the LLM-as-Judge evaluator, one per agent."""

RUBRICS = {
    "brief_analysis": {
        "agent": "Brief Analyzer",
        "criteria": [
            ("completeness", "Are all extractable fields populated from the brief? Score 0 if most fields are empty, 10 if every stated field is captured."),
            ("question_quality", "Are the clarifying questions specific, answerable, and tied to real gaps? Score 0 for generic questions like 'What is the budget?', 10 for context-rich questions with suggested answers."),
            ("gap_coverage", "Are the identified gaps real and categorized correctly? Score 0 if gaps are fabricated or missed, 10 if every genuine gap is found and grouped."),
        ],
    },
    "execution_planning": {
        "agent": "Execution Planner",
        "criteria": [
            ("constraint_adherence", "Does the plan honor every constraint from the brief and clarification answers? Score 0 if constraints are violated, 10 if all are respected."),
            ("channel_coverage", "Does the plan address all channels mentioned in the brief? Score 0 if channels are missing, 10 if every channel has specific guidance."),
            ("actionability", "Is the plan specific enough for a copywriter to execute without a meeting? Score 0 if vague, 10 if it includes CTAs, tone, character limits, and mustAvoid rules per channel."),
        ],
    },
    "consistency_check": {
        "agent": "Consistency Checker",
        "criteria": [
            ("detection_accuracy", "Are genuine misalignments between assets and brief correctly identified? Score 0 if real errors are missed, 10 if all are caught."),
            ("classification_correctness", "Are issues correctly classified as REAL_ERROR vs INTENTIONAL_ADAPTATION? Score 0 if most are wrong, 10 if classifications are accurate."),
            ("dimension_coverage", "Are all 5 dimensions checked (CTA, Audience, KeyMessage, Tone, BrandConstraint)? Score 0 if only 1-2 checked, 10 if all are covered per asset."),
        ],
    },
    "qa_report": {
        "agent": "QA Reviewer",
        "criteria": [
            ("fix_specificity", "Are suggestedFix values exact replacement text (not vague instructions)? Score 0 if fixes say 'change the CTA', 10 if they provide copy-pasteable text."),
            ("severity_accuracy", "Are severity levels assigned correctly (CRITICAL for constraint violations, WARNING for inconsistencies, ADVISORY for style)? Score 0 if levels are random, 10 if accurate."),
            ("impact_clarity", "Does each businessImpact explain a real-world consequence in one sentence? Score 0 if empty/generic, 10 if specific and actionable."),
        ],
    },
    "pattern_extraction": {
        "agent": "Memory Agent",
        "criteria": [
            ("pattern_actionability", "Are extracted lessons specific enough to prevent future errors? Score 0 for 'be more careful' lessons, 10 for lessons with concrete trigger conditions."),
            ("relevance", "Are patterns tied to actual issues found in the QA report? Score 0 if fabricated, 10 if every pattern maps to a real finding."),
        ],
    },
    "asset_generation": {
        "agent": "Asset Generator",
        "criteria": [
            ("brief_compliance", "Do generated assets honor all brief constraints? Score 0 if constraints are violated, 10 if all are respected."),
            ("channel_format", "Is each asset formatted correctly for its channel (character limits, structure)? Score 0 if formats are wrong, 10 if channel-native."),
            ("changelog_completeness", "Does the change log trace every modification to a specific brief rule? Score 0 if changes are unlogged, 10 if every change cites a rule."),
        ],
    },
}

GRADER_SYSTEM_PROMPT = """You are a strict quality evaluator for a marketing campaign AI system.
Score the agent's output on each criterion from 0 to 10.
Be objective and critical — do not inflate scores.

For each criterion, provide:
- score: integer 0-10
- feedback: one sentence explaining the score

Then provide an overall verdict:
- passed: true if average score >= 7, false otherwise
- summary: one sentence overall assessment

Return ONLY valid JSON:
{
  "scores": [
    {"criterion": "", "score": 0, "feedback": ""}
  ],
  "avg_score": 0.0,
  "passed": true,
  "summary": ""
}"""
