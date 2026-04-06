"""
test_scoring.py — Smoke test for scoring.py and rubric.py.

Runs end-to-end against a deterministic synthetic answer set covering all
39 question ids, exercises the N/A path via ai_04 and sw_06, and asserts
the invariants promised by scoring.py. Prints overall score, per-dimension
scores, and the three top risks.

Run from inside glk-audit/:
    python3 test_scoring.py
"""

from rubric import DIMENSIONS, RUBRIC_VERSION
from scoring import run_audit


def build_synthetic_answers():
    """Deterministic answer set.

    - Likert questions: alternating 4 / 2 in declaration order.
    - Yes/No questions: alternating Yes / No in declaration order.
    - ai_04 and sw_06 overridden to "N/A" to exercise the N/A path.
    """
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

    result = run_audit(answers)

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


if __name__ == "__main__":
    main()
    test_opportunities_path()
