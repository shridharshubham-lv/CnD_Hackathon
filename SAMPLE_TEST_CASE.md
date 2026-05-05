# Sample Test Case

## Scenario

Use this scenario to test the full app flow from Stage 1 through Stage 6.

- Campaign type: B2B SaaS enterprise conversion campaign
- Goal: Trigger realistic gaps in the brief, then surface cross-channel copy errors in QA
- Expected app coverage: Agent 1 clarification, Agent 2 planning, Agent 3 consistency detection, Agent 4 fix suggestions, Agent 5 memory logging

## Stage 1: Brief To Paste

```text
Campaign Name: Q3 Enterprise Trial-to-Paid Push
Business Objective: Convert 200 enterprise trial accounts (1000+ employees) to paid contracts before end of Q3. Secondary: generate 50 new enterprise demo requests from net-new prospects.
Target Audience: Trial users at companies with 1000+ employees in technology, financial services, and professional services. Decision-maker titles: VP of Operations, Director of Revenue Operations, Chief Marketing Officer.
Key Message: Teams that manage revenue operations at scale are leaving hours of manual work on the table. Our platform eliminates the reporting lag between data capture and decision.
Channels: Email, LinkedIn, social (unspecified), sales outreach
Budget: Not specified
Timeline: Campaign live by July 1, all assets locked by June 20
Success Metrics: Trial-to-paid conversion rate (baseline 14%, target 22%); 50 new enterprise demo requests in 6 weeks
Constraints: Do not reference competitors. Claims about time savings need customer quotes. Tone: confident, not aggressive. Avoid AI-powered without a concrete example.
```

## Stage 2: Suggested Clarification Answers

Agent 1 will generate variable questions, so the wording may differ. If it asks about the topics below, use these answers.

- Budget: `$45,000 total campaign budget`
- Primary CTA: `Book a demo`
- Secondary CTA: `Reply to schedule a tailored enterprise walkthrough`
- Social clarification: `Use LinkedIn only for paid or organic social; do not create Instagram, Facebook, or TikTok assets`
- Proof for time-saving claims: `Only use time-saving claims when paired with a customer quote or attributed proof point`
- Tone guardrail: `Confident, executive, practical, never hype-driven or aggressive`
- Decision maker focus: `Write primarily for VP Operations, RevOps leaders, and CMOs at enterprise companies`

## Stage 3: What A Good Plan Should Include

The exact plan will vary, but a healthy output should usually include:

- Enterprise decision-maker targeting
- Channel-specific work for Email, LinkedIn, Sales Outreach, and a landing page or demo destination
- CTA centered on `Book a demo`
- Guardrails against unsupported AI claims and unsupported time-saving claims
- A timeline aligned to June 20 asset lock and July 1 launch

## Stage 4: Assets To Paste

These intentionally contain mismatches so Agents 3 and 4 have something to catch.

### Email

```text
Subject: Ready to schedule a call about your trial?

Hi [First Name], your team has been exploring our platform for a few weeks.
We'd love to schedule a call to walk you through what's possible at enterprise scale.
Our customers save hours every week on manual reporting. Let's talk about what that
could mean for your team.

[Schedule a call]
```

### LinkedIn

```text
Struggling with your reporting workflow? Our tool makes it easy and quick to learn —
even for teams just getting started with revenue ops. Give it a try today and see
results fast.

Start your free trial ->
```

### Paid Search

```text
Headline 1: AI-Powered Revenue Operations
Headline 2: Automate Your Reporting Today
Description: Our AI-powered platform handles revenue reporting automatically.
Save time, reduce errors. Start free.
```

### Landing Page

```text
The smart way to manage revenue operations.
See why 500+ teams trust us to handle their reporting.
Book a demo today.
```

### Sales Outreach

```text
Hi [Name], I noticed your team has been using our trial for a few weeks.
Would love to jump on a quick call to share how similar companies use us.
Let me know a time that works!
```

## Expected Results

Because the app relies on LLM output, exact wording and counts may vary. Use these as pass criteria, not exact snapshots.

### Agent 1 Should Likely Catch

- Missing or incomplete budget detail
- Ambiguity around `social (unspecified)`
- CTA ambiguity between demo request and other actions
- Need for proof before making time-saving claims

### Agent 3 Should Likely Flag

- Email CTA mismatch: `Schedule a call` vs `Book a demo`
- LinkedIn audience mismatch: beginner framing vs enterprise decision-makers
- LinkedIn CTA mismatch: `Start your free trial` vs enterprise demo goal
- Paid Search brand constraint issue: `AI-powered` without a concrete example
- Possible unsupported time-saving claim where no proof quote is supplied

### Agent 4 Should Likely Produce

- At least 2 real errors
- Severity split across `CRITICAL` and `WARNING`
- Suggested fixes in the exact channel-specific format used by the app

### Agent 5 Should Likely Do

- Store patterns after you click `Finalize & Log to Memory`
- Return proactive warnings on future briefs with similar ambiguity or unsupported claims

## Quick Demo Path

1. Open Stage 1 and paste the brief.
2. Run Agent 1 and answer clarification questions using the guidance above.
3. Approve the plan in Stage 3.
4. Paste the assets above into Stage 4.
5. Run consistency check and QA.
6. Confirm the flagged issues make sense.
7. Finalize to store campaign memory.

## Pass / Fail Guide

- Pass: the app surfaces brief gaps, finds multiple copy mismatches, and generates usable fixes.
- Partial pass: the app runs but misses one or two expected conflicts due to LLM variance.
- Fail: the app cannot progress stages, returns backend errors, or produces no meaningful conflicts from the intentionally flawed assets.