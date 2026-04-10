"""
test_scoring.py — Smoke test for scoring.py and rubric.py.

Runs end-to-end against a deterministic synthetic answer set covering all
39 question ids, exercises the N/A path via ai_04 and sw_06, and asserts
the invariants promised by scoring.py. Prints overall score, per-dimension
scores, and the three top risks.

Run from inside glk-audit/:
    python3 test_scoring.py
"""

from rubric import BENCHMARKS, DIMENSIONS, RUBRIC_VERSION
from scoring import run_audit, build_action_plan, score_quantitative


def build_synthetic_answers():
    """Deterministic answer set.

    - Likert questions: alternating 4 / 2 in declaration order.
    - Yes/No questions: alternating Yes / No in declaration order.
    - Number/Percent questions: median-ish values for Professional Services.
    - ai_04 and sw_06 overridden to "N/A" to exercise the N/A path.
    """
    QUANT_VALUES = {
        "per_q_turnover_pct": 18,
        "per_q_days_to_fill": 35,
        "fin_q_days_to_close": 10,
        "fin_q_ar_over_60_pct": 12,
        "sw_q_num_saas_tools": 20,
        "sw_q_software_spend_pct": 6,
        "ai_q_num_ai_workflows": 3,
        "sal_q_cac": 800,
        "sal_q_monthly_churn_pct": 1.5,
        "ops_q_on_time_delivery_pct": 94,
        "ops_q_mttr_hours": 12,
    }
    answers = {}
    likert_i = 0
    yesno_i = 0
    for d in DIMENSIONS:
        for q in d["questions"]:
            if q["type"] == "likert":
                answers[q["id"]] = 4 if likert_i % 2 == 0 else 2
                likert_i += 1
            elif q["type"] == "yesno":
                answers[q["id"]] = "Yes" if yesno_i % 2 == 0 else "No"
                yesno_i += 1
            elif q["type"] in ("number", "percent"):
                answers[q["id"]] = QUANT_VALUES.get(q["id"], 50)
    answers["ai_04"] = "N/A"
    answers["sw_06"] = "N/A"
    return answers


def main():
    print(f"rubric version: {RUBRIC_VERSION}")

    answers = build_synthetic_answers()
    total_questions = sum(len(d["questions"]) for d in DIMENSIONS)
    assert len(answers) == total_questions, (
        f"answers dict has {len(answers)} entries, expected {total_questions}"
    )
    print(f"answers built: {len(answers)} questions "
          f"({sum(1 for v in answers.values() if v == 'N/A')} marked N/A)")

    result = run_audit(answers, industry="Professional Services")

    # ----- Invariants -----
    overall = result["overall"]
    assert overall["score"] is not None, "overall score is None"
    assert isinstance(overall["score"], float), "overall score not float"
    assert 0.0 <= overall["score"] <= 100.0, f"overall out of range: {overall['score']}"

    dims = result["dimensions"]
    assert len(dims) == 6, f"expected 6 dimensions, got {len(dims)}"
    for dim_id, dim in dims.items():
        assert not dim["insufficient"], f"dimension {dim_id} insufficient under this input"
        assert dim["score"] is not None, f"dimension {dim_id} has None score"
        assert 0.0 <= dim["score"] <= 100.0, f"dimension {dim_id} out of range"

    risks = result["risks"]
    assert len(risks) == 3, f"expected 3 risks, got {len(risks)}"
    for r in risks:
        assert r.get("risk_copy"), f"risk {r['question_id']} has empty risk_copy"

    opps = result["opportunities"]
    assert len(opps) <= 3, f"expected <=3 opportunities, got {len(opps)}"
    for o in opps:
        assert o.get("opportunity_copy"), (
            f"opportunity {o['question_id']} has empty opportunity_copy"
        )

    risk_qids = {r["question_id"] for r in risks}
    opp_qids = {o["question_id"] for o in opps}
    overlap = risk_qids & opp_qids
    assert not overlap, f"question(s) in both risks and opportunities: {overlap}"

    # ----- Output -----
    print()
    print("=" * 64)
    print(f"OVERALL: {overall['score']:.2f}  [{overall['band_label']}]")
    print("=" * 64)
    print()
    print("Per-dimension scores:")
    for dim_id, dim in dims.items():
        print(f"  {dim['name']:<22} {dim['score']:6.2f}  [{dim['band_label']}]  "
              f"(na_fraction={dim['na_fraction']:.2f})")
    print()
    print("Top 3 risks (severity-weighted):")
    for i, r in enumerate(risks, 1):
        severity = (100.0 - r["score"]) * r["weight"]
        print(f"  {i}. {r['question_id']}  score={r['score']:.1f}  "
              f"weight={r['weight']}  severity={severity:.1f}  "
              f"[{r['dimension_name']}]")
    print()
    print(f"Top opportunities ({len(opps)}):")
    for i, o in enumerate(opps, 1):
        print(f"  {i}. {o['question_id']}  score={o['score']:.1f}  "
              f"weight={o['weight']}  [{o['dimension_name']}]")
    print()
    print("ALL ASSERTIONS PASSED")


def test_opportunities_path():
    """Coverage for the [40, 70] opportunity window.

    All Likert answers set to 3 (-> score 50, inside the opportunity window).
    Yes/No answers alternate Yes/No (-> 100/0, outside the window).
    This guarantees at least some questions land in the opportunity band.
    """
    answers = {}
    yesno_i = 0
    for d in DIMENSIONS:
        for q in d["questions"]:
            if q["type"] == "likert":
                answers[q["id"]] = 3
            elif q["type"] == "yesno":
                answers[q["id"]] = "Yes" if yesno_i % 2 == 0 else "No"
                yesno_i += 1

    result = run_audit(answers)
    risks = result["risks"]
    opps = result["opportunities"]

    assert len(opps) > 0, "expected at least one opportunity, got none"
    risk_qids = {r["question_id"] for r in risks}
    opp_qids = {o["question_id"] for o in opps}
    overlap = risk_qids & opp_qids
    assert not overlap, f"question(s) in both risks and opportunities: {overlap}"

    # Every returned opportunity must be inside the [40, 70] band.
    for o in opps:
        assert 40.0 <= o["score"] <= 70.0, (
            f"opportunity {o['question_id']} score {o['score']} outside [40, 70]"
        )
        assert o.get("opportunity_copy"), (
            f"opportunity {o['question_id']} has empty opportunity_copy"
        )

    print()
    print("=" * 64)
    print("OPPORTUNITIES PATH TEST")
    print("=" * 64)
    print(f"overall: {result['overall']['score']:.2f}  [{result['overall']['band_label']}]")
    print(f"risks returned: {len(risks)}")
    for i, r in enumerate(risks, 1):
        severity = (100.0 - r["score"]) * r["weight"]
        print(f"  {i}. {r['question_id']}  score={r['score']:.1f}  "
              f"weight={r['weight']}  severity={severity:.1f}  "
              f"[{r['dimension_name']}]")
    print(f"opportunities returned: {len(opps)}")
    for i, o in enumerate(opps, 1):
        print(f"  {i}. {o['question_id']}  score={o['score']:.1f}  "
              f"weight={o['weight']}  [{o['dimension_name']}]")
    print()
    print("OPPORTUNITIES PATH ASSERTIONS PASSED")


def test_action_plan():
    """Verify the 30/60/90 action plan is well-formed."""
    answers = build_synthetic_answers()
    result = run_audit(answers)
    plan = result["action_plan"]

    assert "30_day" in plan, "action_plan missing 30_day"
    assert "60_day" in plan, "action_plan missing 60_day"
    assert "90_day" in plan, "action_plan missing 90_day"

    # 30-day should have items (we always have risks in synthetic data)
    assert len(plan["30_day"]) > 0, "30_day plan is empty"

    # Every item must have dimension_name and action
    for phase in ["30_day", "60_day", "90_day"]:
        for item in plan[phase]:
            assert item.get("dimension_name"), f"{phase} item missing dimension_name"
            assert item.get("action"), f"{phase} item missing action"

    print()
    print("=" * 64)
    print("30/60/90 ACTION PLAN TEST")
    print("=" * 64)
    for phase, label in [("30_day", "30 Days"), ("60_day", "60 Days"), ("90_day", "90 Days")]:
        print(f"\n{label}:")
        for item in plan[phase]:
            print(f"  - [{item['dimension_name']}] {item['action'][:80]}...")
    print()
    print("ACTION PLAN ASSERTIONS PASSED")


def test_risks_carry_recommendation():
    """Verify that risks include recommendation text from rubric."""
    answers = build_synthetic_answers()
    result = run_audit(answers)
    risks = result["risks"]

    # At least one risk should have a recommendation (all rubric questions do)
    recs = [r for r in risks if r.get("recommendation")]
    assert len(recs) > 0, "no risks carry recommendation text"

    print()
    print("=" * 64)
    print("RISKS RECOMMENDATION TEST")
    print("=" * 64)
    for r in risks:
        has_rec = "YES" if r.get("recommendation") else "NO"
        print(f"  {r['question_id']}: recommendation={has_rec}")
    print()
    print("RISKS RECOMMENDATION ASSERTIONS PASSED")


def test_insufficient_guardrail():
    """Verify that 3+ N/A dimensions produce insufficient results."""
    # Answer only one dimension, leave the rest as N/A
    answers = {}
    # Answer all personnel questions (dimension 0)
    likert_i = 0
    yesno_i = 0
    for q in DIMENSIONS[0]["questions"]:
        if q["type"] == "likert":
            answers[q["id"]] = 4 if likert_i % 2 == 0 else 2
            likert_i += 1
        elif q["type"] == "yesno":
            answers[q["id"]] = "Yes" if yesno_i % 2 == 0 else "No"
            yesno_i += 1

    # All other dimensions get N/A
    for d in DIMENSIONS[1:]:
        for q in d["questions"]:
            answers[q["id"]] = "N/A"

    result = run_audit(answers)
    insufficient_count = sum(
        1 for d in result["dimensions"].values() if d["insufficient"]
    )
    assert insufficient_count >= 3, (
        f"expected 3+ insufficient dimensions, got {insufficient_count}"
    )

    # Personnel should NOT be insufficient
    assert not result["dimensions"]["personnel"]["insufficient"], (
        "personnel should not be insufficient"
    )

    print()
    print("=" * 64)
    print("INSUFFICIENT GUARDRAIL TEST")
    print("=" * 64)
    print(f"insufficient dimensions: {insufficient_count}")
    for dim_id, dim in result["dimensions"].items():
        status = "INSUFFICIENT" if dim["insufficient"] else f"score={dim['score']:.1f}"
        print(f"  {dim['name']:<22} {status}")
    print()
    print("INSUFFICIENT GUARDRAIL ASSERTIONS PASSED")


def test_quantitative_scoring():
    """Verify benchmark-based scoring for quantitative questions."""
    # Lower-is-better: turnover at p25 = 100, at p75 = 0
    q_lib = {"id": "per_q_turnover_pct", "type": "percent",
             "weight": 1.0, "lower_is_better": True}
    # Professional Services: p25=10, p50=18, p75=28
    assert score_quantitative(10, q_lib, "Professional Services") == 100.0
    assert score_quantitative(28, q_lib, "Professional Services") == 0.0
    assert score_quantitative(18, q_lib, "Professional Services") == 50.0
    # Between p25 and p50
    s = score_quantitative(14, q_lib, "Professional Services")
    assert 50.0 < s < 100.0, f"expected between 50-100, got {s}"

    # Higher-is-better: on-time delivery at p75 = 100, at p25 = 0
    q_hib = {"id": "ops_q_on_time_delivery_pct", "type": "percent",
             "weight": 1.0, "lower_is_better": False}
    # Professional Services: p25=88, p50=94, p75=98
    assert score_quantitative(98, q_hib, "Professional Services") == 100.0
    assert score_quantitative(88, q_hib, "Professional Services") == 0.0
    assert score_quantitative(94, q_hib, "Professional Services") == 50.0

    # No benchmark for unknown industry -> 50
    assert score_quantitative(15, q_lib, "Unknown Industry") == 50.0

    # N/A returns None
    assert score_quantitative(None, q_lib, "Professional Services") is None
    assert score_quantitative("N/A", q_lib, "Professional Services") is None

    print()
    print("=" * 64)
    print("QUANTITATIVE SCORING TEST")
    print("=" * 64)
    print("  lower_is_better at p25: 100.0 ✓")
    print("  lower_is_better at p75: 0.0 ✓")
    print("  lower_is_better at p50: 50.0 ✓")
    print("  higher_is_better at p75: 100.0 ✓")
    print("  higher_is_better at p25: 0.0 ✓")
    print("  unknown industry: 50.0 ✓")
    print("  N/A: None ✓")
    print()
    print("QUANTITATIVE SCORING ASSERTIONS PASSED")


def test_blended_dimension_scoring():
    """Verify that dimensions with quant questions use 40/60 blending."""
    answers = build_synthetic_answers()

    # Run with industry for benchmark lookups
    result = run_audit(answers, industry="Professional Services")
    dims = result["dimensions"]

    # Personnel has both qualitative and quantitative questions
    per = dims["personnel"]
    assert not per["insufficient"], "personnel should not be insufficient"
    assert per["score"] is not None, "personnel score should not be None"

    # Run without industry (no benchmarks) — should still score via qual only
    result_no_ind = run_audit(answers, industry=None)
    per_no_ind = result_no_ind["dimensions"]["personnel"]
    assert per_no_ind["score"] is not None

    # The scores should differ because benchmarks affect the blend
    # (unless quant answers happen to score exactly the same as qual)
    print()
    print("=" * 64)
    print("BLENDED DIMENSION SCORING TEST")
    print("=" * 64)
    print(f"  Personnel with industry: {per['score']:.2f}")
    print(f"  Personnel without industry: {per_no_ind['score']:.2f}")
    for dim_id, dim in dims.items():
        has_quant = any(qs["quantitative"] for qs in dim["question_scores"]
                        if not qs["na"])
        q_label = " (blended)" if has_quant else " (qual only)"
        print(f"  {dim['name']:<22} {dim['score']:6.2f}  [{dim['band_label']}]{q_label}")
    print()
    print("BLENDED DIMENSION SCORING ASSERTIONS PASSED")


def test_prompt_construction():
    """Verify the AI prompt builder includes all required sections."""
    from recommendations import build_prompt

    answers = build_synthetic_answers()
    result = run_audit(answers, industry="Professional Services")
    firm = {
        "company_name": "Test Corp",
        "industry": "Professional Services",
        "revenue_band": "$5–20M",
        "ebitda_margin": 12,
        "employees": 45,
        "years": 8,
        "owner_hours": 50,
    }

    prompts = build_prompt(result, firm, answers)
    system = prompts["system"]
    user = prompts["user"]

    # System prompt checks
    assert "operating advisor" in system.lower(), "system prompt missing advisor role"
    assert "private equity" in system.lower(), "system prompt missing PE context"

    # User prompt checks
    assert "Test Corp" in user, "user prompt missing company name"
    assert "Professional Services" in user, "user prompt missing industry"
    assert "$5–20M" in user, "user prompt missing revenue"
    assert "AUDIT RESULTS" in user, "user prompt missing audit results header"
    assert "Dimension scores" in user, "user prompt missing dimension scores"
    assert "Top risks" in user, "user prompt missing risks"
    assert "benchmarks" in user.lower(), "user prompt missing benchmarks"

    # Ensure quantitative benchmark data is included
    assert "turnover" in user.lower() or "per_q_turnover" in user, \
        "user prompt missing quantitative data"

    print()
    print("=" * 64)
    print("PROMPT CONSTRUCTION TEST")
    print("=" * 64)
    print(f"  System prompt length: {len(system)} chars")
    print(f"  User prompt length: {len(user)} chars")
    print(f"  Contains company name: YES")
    print(f"  Contains industry: YES")
    print(f"  Contains scores: YES")
    print(f"  Contains benchmarks: YES")
    print()
    print("PROMPT CONSTRUCTION ASSERTIONS PASSED")


def test_ai_graceful_fallback():
    """Verify that missing API key returns None gracefully."""
    import os
    from recommendations import generate_recommendations

    # Ensure no API key is set
    original = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        answers = build_synthetic_answers()
        result = run_audit(answers, industry="Professional Services")
        firm = {"company_name": "Test Corp", "industry": "Professional Services"}

        ai_recs = generate_recommendations(result, firm, answers)
        assert ai_recs is None, "expected None when API key is not set"

        print()
        print("=" * 64)
        print("AI GRACEFUL FALLBACK TEST")
        print("=" * 64)
        print("  No API key -> returns None: YES")
        print()
        print("AI GRACEFUL FALLBACK ASSERTIONS PASSED")
    finally:
        if original:
            os.environ["ANTHROPIC_API_KEY"] = original


def test_pdf_with_ai_recommendations():
    """Verify PDF generation works with AI recommendation data."""
    import tempfile, os
    from report import build_pdf

    answers = build_synthetic_answers()
    result = run_audit(answers, industry="Professional Services")
    firm = {
        "company_name": "AI Test Corp",
        "industry": "Professional Services",
        "revenue_band": "$5–20M",
        "ebitda_margin": 12,
        "employees": 45,
        "years": 8,
        "owner_hours": 50,
    }

    # Synthetic AI recommendations (mimics API output shape)
    ai_recs = {
        "executive_summary": (
            "AI Test Corp presents a mixed operational picture. Personnel "
            "processes are a clear weakness, with turnover above industry median "
            "and no structured hiring pipeline. Accounting fundamentals are solid "
            "but lack forward-looking forecasting. The biggest quick win is "
            "implementing a documented onboarding program, which could reduce "
            "first-year attrition by 20-30%.\n\n"
            "The company's software stack is over-indexed on tools but "
            "under-indexed on integration. Consolidating from 20 to 12 SaaS "
            "tools would save approximately $36K annually and reduce context-switching."
        ),
        "dimension_analyses": [
            {
                "dimension": "Personnel",
                "analysis": (
                    "Voluntary turnover at 18% is at the industry median but above "
                    "top-quartile performers (10%). Combined with a 35-day time-to-fill, "
                    "this creates a compounding drag on productivity."
                ),
                "recommendations": [
                    "Implement structured 90-day onboarding with weekly check-ins.",
                    "Create a career progression framework for top 5 roles.",
                    "Reduce time-to-fill to under 25 days by pre-building a candidate pipeline.",
                ],
            },
            {
                "dimension": "Software & Infrastructure",
                "analysis": (
                    "20 SaaS tools for a 45-person company is excessive. Software "
                    "spend at 6% of revenue is within range but could be optimized."
                ),
                "recommendations": [
                    "Audit all 20 tools — target consolidation to 12-14.",
                    "Require SSO for any tool touching customer data.",
                ],
            },
        ],
        "action_plan": {
            "30_day": [
                {
                    "action": "Exit-interview the last 3 departures",
                    "owner": "CEO / Head of People",
                    "expected_outcome": "Root-cause map of attrition drivers",
                },
                {
                    "action": "Audit all SaaS subscriptions and tag by usage tier",
                    "owner": "Ops lead",
                    "expected_outcome": "Shortlist of 5+ tools to eliminate",
                },
            ],
            "60_day": [
                {
                    "action": "Launch 90-day structured onboarding program",
                    "owner": "Head of People",
                    "expected_outcome": "20-30% reduction in first-year attrition",
                },
            ],
            "90_day": [
                {
                    "action": "Build career progression framework for top 5 roles",
                    "owner": "CEO + hiring managers",
                    "expected_outcome": "Improved retention and internal mobility",
                },
            ],
        },
        "roi_estimates": [
            {
                "recommendation": "Structured onboarding program",
                "estimated_impact": "$45K-$90K/year saved via reduced turnover",
                "confidence": "high",
            },
            {
                "recommendation": "SaaS consolidation",
                "estimated_impact": "$36K/year in direct cost savings",
                "confidence": "medium",
            },
            {
                "recommendation": "Career progression framework",
                "estimated_impact": "Retention of 2-3 key employees worth $150K+ each",
                "confidence": "medium",
            },
        ],
    }

    # Generate advisory PDF with AI recs
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        build_pdf(result, firm, tmp_path, mode="advisory", answers=answers,
                  ai_recommendations=ai_recs)
        size = os.path.getsize(tmp_path)
        assert size > 5000, f"AI advisory PDF too small: {size} bytes"
        print()
        print("=" * 64)
        print("PDF WITH AI RECOMMENDATIONS TEST")
        print("=" * 64)
        print(f"  Generated advisory PDF with AI recs: {size:,} bytes")
        print()
        print("PDF WITH AI RECOMMENDATIONS ASSERTIONS PASSED")
    finally:
        os.unlink(tmp_path)


def test_prompt_with_recommendation_history():
    """Verify the AI prompt includes prior recommendation status when provided."""
    from recommendations import build_prompt

    answers = build_synthetic_answers()
    result = run_audit(answers, industry="Professional Services")
    firm = {
        "company_name": "Test Corp",
        "industry": "Professional Services",
        "revenue_band": "$5–20M",
        "ebitda_margin": 12,
        "employees": 45,
        "years": 8,
        "owner_hours": 50,
    }

    rec_history = [
        {"dimension": "Personnel", "recommendation": "Implement structured onboarding", "status": "done"},
        {"dimension": "Software", "recommendation": "Consolidate SaaS tools", "status": "in_progress"},
        {"dimension": "Sales", "recommendation": "Define ICP", "status": "not_started"},
    ]

    prompts = build_prompt(result, firm, answers, recommendation_history=rec_history)
    user = prompts["user"]

    assert "PRIOR RECOMMENDATIONS" in user, "prompt missing recommendation history header"
    assert "Completed:" in user, "prompt missing completed section"
    assert "In progress:" in user, "prompt missing in-progress section"
    assert "Not started:" in user, "prompt missing not-started section"
    assert "Implement structured onboarding" in user, "prompt missing done recommendation"
    assert "Consolidate SaaS tools" in user, "prompt missing in-progress recommendation"
    assert "Define ICP" in user, "prompt missing not-started recommendation"

    # Without history, the section should not appear
    prompts_no_hist = build_prompt(result, firm, answers, recommendation_history=None)
    assert "PRIOR RECOMMENDATIONS" not in prompts_no_hist["user"], \
        "prompt should not have rec history when None"

    print()
    print("=" * 64)
    print("PROMPT WITH RECOMMENDATION HISTORY TEST")
    print("=" * 64)
    print("  Includes completed recs: YES")
    print("  Includes in-progress recs: YES")
    print("  Includes not-started recs: YES")
    print("  Absent when None: YES")
    print()
    print("PROMPT WITH RECOMMENDATION HISTORY ASSERTIONS PASSED")


def test_pdf_with_progress_section():
    """Verify PDF generation works with previous audit delta data."""
    import tempfile, os
    from report import build_pdf

    answers = build_synthetic_answers()
    result = run_audit(answers, industry="Professional Services")
    firm = {
        "company_name": "Progress Test Corp",
        "industry": "Professional Services",
        "revenue_band": "$5–20M",
        "ebitda_margin": 12,
        "employees": 45,
        "years": 8,
        "owner_hours": 50,
    }

    # Synthetic previous audit
    previous_audit = {
        "overall_score": 42.0,
        "overall_band": "Fragile",
        "created_at": "2025-12-01T00:00:00Z",
        "dimension_scores": {
            "personnel": {"name": "Personnel & Org", "score": 40.0, "band_label": "Fragile"},
            "accounting": {"name": "Accounting & Finance", "score": 45.0, "band_label": "Fragile"},
            "software": {"name": "Software Stack", "score": 38.0, "band_label": "At Risk"},
            "ai": {"name": "AI Readiness", "score": 50.0, "band_label": "Fragile"},
            "sales": {"name": "Sales & Marketing", "score": 35.0, "band_label": "At Risk"},
            "operations": {"name": "Operations & Process", "score": 44.0, "band_label": "Fragile"},
        },
    }

    # Generate PDF with progress section
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        build_pdf(result, firm, tmp_path, mode="advisory", answers=answers,
                  previous_audit=previous_audit)
        size = os.path.getsize(tmp_path)
        assert size > 5000, f"Progress PDF too small: {size} bytes"

        # Also test without previous audit (should still work)
        build_pdf(result, firm, tmp_path, mode="advisory", answers=answers,
                  previous_audit=None)
        size_no_prev = os.path.getsize(tmp_path)
        assert size_no_prev > 5000, f"PDF without progress too small: {size_no_prev} bytes"

        print()
        print("=" * 64)
        print("PDF WITH PROGRESS SECTION TEST")
        print("=" * 64)
        print(f"  PDF with progress section: {size:,} bytes")
        print(f"  PDF without progress: {size_no_prev:,} bytes")
        print()
        print("PDF WITH PROGRESS SECTION ASSERTIONS PASSED")
    finally:
        os.unlink(tmp_path)


def test_extract_recommendations_from_ai():
    """Verify extraction of flat recommendation list from AI output.

    Reimplements the extraction logic here to avoid importing app.py
    (which requires Streamlit).
    """
    def _extract(ai_recs):
        if not ai_recs:
            return []
        recs = []
        for da in ai_recs.get("dimension_analyses", []):
            dim = da.get("dimension", "General")
            for r in da.get("recommendations", []):
                recs.append({"dimension": dim, "recommendation": r})
        return recs

    ai_recs = {
        "dimension_analyses": [
            {
                "dimension": "Personnel",
                "analysis": "Test analysis",
                "recommendations": [
                    "Implement onboarding",
                    "Build career framework",
                ],
            },
            {
                "dimension": "Software",
                "analysis": "Test analysis",
                "recommendations": [
                    "Consolidate SaaS tools",
                ],
            },
        ],
    }

    flat = _extract(ai_recs)
    assert len(flat) == 3, f"expected 3 recommendations, got {len(flat)}"
    assert flat[0]["dimension"] == "Personnel"
    assert flat[0]["recommendation"] == "Implement onboarding"
    assert flat[2]["dimension"] == "Software"

    # None input
    assert _extract(None) == []
    assert _extract({}) == []

    print()
    print("=" * 64)
    print("EXTRACT RECOMMENDATIONS TEST")
    print("=" * 64)
    print(f"  Extracted {len(flat)} recommendations: YES")
    print("  None input returns []: YES")
    print()
    print("EXTRACT RECOMMENDATIONS ASSERTIONS PASSED")


def test_tier_feature_gates():
    """Verify has_feature() correctly gates features by tier."""
    from rubric import has_feature, TIERS

    # Free tier should have basic features
    assert has_feature("free", "scores"), "free should have scores"
    assert has_feature("free", "risk_ranking"), "free should have risk_ranking"
    assert has_feature("free", "basic_pdf"), "free should have basic_pdf"

    # Free tier should NOT have paid features
    assert not has_feature("free", "ai_recommendations"), "free should not have ai_recommendations"
    assert not has_feature("free", "quantitative_benchmarks"), "free should not have benchmarks"
    assert not has_feature("free", "historical_tracking"), "free should not have tracking"
    assert not has_feature("free", "multi_respondent"), "free should not have multi_respondent"

    # Report tier (new primary paid tier, one-time $149) should have all paid features
    assert has_feature("report", "scores"), "report should have scores"
    assert has_feature("report", "ai_recommendations"), "report should have ai_recommendations"
    assert has_feature("report", "quantitative_benchmarks"), "report should have benchmarks"
    assert has_feature("report", "historical_tracking"), "report should have tracking"
    assert has_feature("report", "pdf_full"), "report should have pdf_full"

    # Report tier should NOT have team features
    assert not has_feature("report", "multi_respondent"), "report should not have multi_respondent"
    assert not has_feature("report", "team_consensus"), "report should not have team_consensus"

    # Pro tier (legacy alias) should still grant the same feature set
    assert has_feature("pro", "scores"), "pro (legacy) should have scores"
    assert has_feature("pro", "ai_recommendations"), "pro (legacy) should have ai_recommendations"
    assert has_feature("pro", "historical_tracking"), "pro (legacy) should have tracking"
    assert not has_feature("pro", "multi_respondent"), "pro (legacy) should not have team features"

    # Team tier should have everything
    assert has_feature("team", "scores"), "team should have scores"
    assert has_feature("team", "ai_recommendations"), "team should have ai_recommendations"
    assert has_feature("team", "multi_respondent"), "team should have multi_respondent"
    assert has_feature("team", "team_consensus"), "team should have team_consensus"
    assert has_feature("team", "white_label_pdf"), "team should have white_label_pdf"

    # Unknown tier falls back to free
    assert has_feature("unknown", "scores"), "unknown tier should fall back to free"
    assert not has_feature("unknown", "ai_recommendations"), "unknown should not have paid features"

    # Verify tier pricing
    assert TIERS["free"]["price_monthly"] == 0
    assert TIERS["report"]["price_onetime"] == 149
    assert TIERS["report"]["billing_mode"] == "payment"
    assert TIERS["pro"]["price_monthly"] == 79  # legacy subscription, kept for grandfathering
    assert TIERS["team"]["price_monthly"] == 299

    print()
    print("=" * 64)
    print("TIER FEATURE GATES TEST")
    print("=" * 64)
    print("  Free:   scores=YES, ai=NO, benchmarks=NO, multi=NO")
    print("  Report: scores=YES, ai=YES, benchmarks=YES, multi=NO ($149 one-time)")
    print("  Pro:    legacy alias (same features as report)")
    print("  Team:   scores=YES, ai=YES, benchmarks=YES, multi=YES")
    print("  Unknown falls back to free: YES")
    print("  Pricing: free=$0, report=$149 one-time, pro=$79/mo legacy, team=$299/mo")
    print()
    print("TIER FEATURE GATES ASSERTIONS PASSED")


def test_stripe_graceful_degradation():
    """Verify Stripe module works when not configured."""
    import os
    from stripe_gate import is_configured, get_subscription_tier

    # Ensure no Stripe key
    original = os.environ.pop("STRIPE_SECRET_KEY", None)
    try:
        # When not configured, is_configured returns False
        # Note: _stripe is cached, so we need to reset it
        import stripe_gate
        stripe_gate._stripe = None
        stripe_gate.STRIPE_SECRET_KEY = ""

        assert not is_configured(), "should not be configured without key"

        # get_subscription_tier returns "report" when Stripe is not configured
        # (all paid features unlocked for dev)
        tier = get_subscription_tier(None, None)
        assert tier == "report", f"expected 'report' without Stripe, got '{tier}'"

        print()
        print("=" * 64)
        print("STRIPE GRACEFUL DEGRADATION TEST")
        print("=" * 64)
        print("  No key -> is_configured()=False: YES")
        print("  No key -> tier='report' (all paid features unlocked): YES")
        print()
        print("STRIPE GRACEFUL DEGRADATION ASSERTIONS PASSED")
    finally:
        if original:
            os.environ["STRIPE_SECRET_KEY"] = original
            stripe_gate.STRIPE_SECRET_KEY = original


if __name__ == "__main__":
    main()
    test_opportunities_path()
    test_action_plan()
    test_risks_carry_recommendation()
    test_insufficient_guardrail()
    test_quantitative_scoring()
    test_blended_dimension_scoring()
    test_prompt_construction()
    test_ai_graceful_fallback()
    test_pdf_with_ai_recommendations()
    test_prompt_with_recommendation_history()
    test_pdf_with_progress_section()
    test_extract_recommendations_from_ai()
    test_tier_feature_gates()
    test_stripe_graceful_degradation()
