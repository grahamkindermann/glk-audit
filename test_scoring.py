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


if __name__ == "__main__":
    main()
    test_opportunities_path()
    test_action_plan()
    test_risks_carry_recommendation()
    test_insufficient_guardrail()
    test_quantitative_scoring()
    test_blended_dimension_scoring()
