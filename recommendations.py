"""
recommendations.py: AI-generated consulting memo via Claude API.

Pure function interface:
    generate_recommendations(result, firmographics, answers) -> dict or None

If ANTHROPIC_API_KEY is not set, returns None (graceful degradation).
If the API call fails, returns None and logs the error, never blocks the
results page.

The returned dict has this shape:
{
    "executive_summary": str,
    "dimension_analyses": [
        {"dimension": str, "analysis": str, "recommendations": [str]},
        ...
    ],
    "action_plan": {
        "30_day": [{"action": str, "owner": str, "expected_outcome": str}],
        "60_day": [...],
        "90_day": [...],
    },
    "roi_estimates": [
        {"recommendation": str, "estimated_impact": str, "confidence": str},
        ...
    ],
}
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API setup
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
TEMPERATURE = 0.3

# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a senior operating advisor at a private equity firm. You have just \
reviewed a comprehensive business audit for a portfolio company. Your job is \
to write a specific, actionable diagnostic memo, not generic advice.

Rules:
- Reference the company's actual scores, answers, and benchmark gaps.
- Be direct about what's broken and what the fix costs (time, money, effort).
- Every recommendation must have a concrete next step, not a vague suggestion.
- Quantify impact where possible (e.g., "reducing turnover by 5pp saves ~$X").
- Write for a CEO or owner-operator who is smart but time-constrained.
- Be concise. No filler. No platitudes.
"""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {
            "type": "string",
            "description": "2-3 paragraph executive summary of findings and top priorities.",
        },
        "dimension_analyses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dimension": {"type": "string"},
                    "analysis": {"type": "string"},
                    "recommendations": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["dimension", "analysis", "recommendations"],
            },
            "description": "Per-dimension analysis with specific recommendations.",
        },
        "action_plan": {
            "type": "object",
            "properties": {
                "30_day": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "owner": {"type": "string"},
                            "expected_outcome": {"type": "string"},
                        },
                        "required": ["action", "owner", "expected_outcome"],
                    },
                },
                "60_day": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "owner": {"type": "string"},
                            "expected_outcome": {"type": "string"},
                        },
                        "required": ["action", "owner", "expected_outcome"],
                    },
                },
                "90_day": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "owner": {"type": "string"},
                            "expected_outcome": {"type": "string"},
                        },
                        "required": ["action", "owner", "expected_outcome"],
                    },
                },
            },
            "required": ["30_day", "60_day", "90_day"],
            "description": "Prioritized 30/60/90 day action plan.",
        },
        "roi_estimates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "recommendation": {"type": "string"},
                    "estimated_impact": {"type": "string"},
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": ["recommendation", "estimated_impact", "confidence"],
            },
            "description": "ROI estimates for top 3 recommendations.",
        },
    },
    "required": [
        "executive_summary",
        "dimension_analyses",
        "action_plan",
        "roi_estimates",
    ],
}


def _build_user_prompt(result, firmographics, answers, recommendation_history=None):
    """Construct the user prompt with all audit data.

    recommendation_history: optional list of dicts with keys:
        dimension, recommendation, status ('not_started'|'in_progress'|'done')
    """
    from rubric import BENCHMARKS, DIMENSIONS

    industry = firmographics.get("industry", "Unknown")
    headcount = firmographics.get("employees", "Unknown")
    revenue = firmographics.get("revenue_band", "Unknown")
    ebitda = firmographics.get("ebitda_margin", "Unknown")
    years = firmographics.get("years", "Unknown")
    owner_hours = firmographics.get("owner_hours", "Unknown")
    company = firmographics.get("company_name", "the company")

    # Overall score
    overall = result["overall"]
    overall_line = (
        f"Overall score: {overall['score']:.0f}/100, {overall['band_label']}"
        if overall["score"] is not None
        else f"Overall score: Insufficient data, {overall['band_label']}"
    )

    # Per-dimension scores
    dim_lines = []
    for dim in DIMENSIONS:
        dr = result["dimensions"].get(dim["id"], {})
        if dr.get("insufficient"):
            dim_lines.append(f"  - {dim['name']}: Insufficient Data")
        elif dr.get("score") is not None:
            dim_lines.append(
                f"  - {dim['name']}: {dr['score']:.0f}/100, {dr['band_label']}"
            )

    # Top risks
    risk_lines = []
    for r in result.get("risks", []):
        risk_lines.append(
            f"  - [{r['dimension_name']}] {r['question_text']} "
            f"(score: {r['score']:.0f}, weight: {r['weight']})\n"
            f"    Risk: {r.get('risk_copy', 'N/A')}"
        )

    # Top opportunities
    opp_lines = []
    for o in result.get("opportunities", []):
        opp_lines.append(
            f"  - [{o['dimension_name']}] {o['question_text']} "
            f"(score: {o['score']:.0f}, weight: {o['weight']})\n"
            f"    Opportunity: {o.get('opportunity_copy', 'N/A')}"
        )

    # Benchmark comparisons
    bench_lines = []
    for dim in DIMENSIONS:
        for q in dim["questions"]:
            if q["type"] not in ("number", "percent"):
                continue
            val = answers.get(q["id"])
            if val is None or val == "N/A":
                continue
            bm = BENCHMARKS.get((industry, q["id"]))
            if not bm:
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            lib = q.get("lower_is_better", False)
            direction = "lower is better" if lib else "higher is better"
            bench_lines.append(
                f"  - {q['text']}: {v:g} "
                f"(p25={bm['p25']}, p50={bm['p50']}, p75={bm['p75']}; {direction})"
            )

    prompt = f"""\
COMPANY PROFILE:
  Name: {company}
  Industry: {industry}
  Annual revenue: {revenue}
  EBITDA margin: {ebitda}%
  Headcount: {headcount}
  Years in operation: {years}
  Owner weekly hours: {owner_hours}

AUDIT RESULTS:
{overall_line}

Dimension scores:
{chr(10).join(dim_lines)}

Top risks:
{chr(10).join(risk_lines) if risk_lines else "  None identified."}

Top opportunities:
{chr(10).join(opp_lines) if opp_lines else "  None identified."}

Quantitative inputs vs. industry benchmarks ({industry}):
{chr(10).join(bench_lines) if bench_lines else "  No quantitative data provided."}

"""

    # Add recommendation history if available
    if recommendation_history:
        done = [r for r in recommendation_history if r.get("status") == "done"]
        in_prog = [r for r in recommendation_history if r.get("status") == "in_progress"]
        not_started = [r for r in recommendation_history if r.get("status") == "not_started"]

        rec_lines = []
        if done:
            rec_lines.append("Completed:")
            for r in done:
                rec_lines.append(f"  - [{r['dimension']}] {r['recommendation']}")
        if in_prog:
            rec_lines.append("In progress:")
            for r in in_prog:
                rec_lines.append(f"  - [{r['dimension']}] {r['recommendation']}")
        if not_started:
            rec_lines.append("Not started:")
            for r in not_started:
                rec_lines.append(f"  - [{r['dimension']}] {r['recommendation']}")

        prompt += f"""

PRIOR RECOMMENDATIONS AND STATUS:
{chr(10).join(rec_lines)}

In your memo, acknowledge which recommendations were implemented and \
comment on whether the scores reflect the expected improvement. For \
recommendations still in progress or not started, assess whether they \
remain the right priorities given the new scores."""

    prompt += """

Write your diagnostic memo as JSON matching the schema provided. \
Be specific to this company's data. Do not include generic advice that \
could apply to any business. Every recommendation should reference a \
specific score, gap, or answer from the audit above."""

    return prompt


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def generate_recommendations(result, firmographics, answers, recommendation_history=None):
    """Generate AI recommendations via Claude API.

    recommendation_history: optional list of prior recommendation dicts with
        dimension, recommendation, status keys (for follow-up audits).
    Returns the structured dict on success, or None on failure / no API key.
    """
    if not ANTHROPIC_API_KEY:
        logger.info("ANTHROPIC_API_KEY not set, skipping AI recommendations.")
        return None

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed, skipping AI recommendations.")
        return None

    user_prompt = _build_user_prompt(result, firmographics, answers,
                                     recommendation_history=recommendation_history)

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                    + "\n\nRespond with ONLY valid JSON. No markdown fencing, no preamble.",
                },
            ],
        )
        raw = message.content[0].text.strip()

        # Strip markdown fencing if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines)

        data = json.loads(raw)

        # Validate required keys
        required = ["executive_summary", "dimension_analyses", "action_plan", "roi_estimates"]
        for key in required:
            if key not in data:
                logger.error(f"AI response missing required key: {key}")
                return None

        return data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"AI recommendation generation failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Prompt construction helper (for testing)
# ---------------------------------------------------------------------------

def build_prompt(result, firmographics, answers, recommendation_history=None):
    """Public wrapper for testing prompt construction."""
    return {
        "system": SYSTEM_PROMPT,
        "user": _build_user_prompt(result, firmographics, answers,
                                   recommendation_history=recommendation_history),
    }
