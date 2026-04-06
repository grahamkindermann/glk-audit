"""
scoring.py — Pure scoring logic for the Structural Advantage Business Audit.

No Streamlit imports. No I/O. No side effects. Every function is pure:
same input -> same output. Safe to import from app.py, report.py, or tests.

================================================================================
SCORING RULES (rubric v0.1.0)
================================================================================

Likert (1-5):
    Normal:   1 -> 0, 2 -> 25, 3 -> 50, 4 -> 75, 5 -> 100
    Reversed: 1 -> 100, 2 -> 75, 3 -> 50, 4 -> 25, 5 -> 0

Yes/No:
    Normal:   Yes -> 100, No -> 0
    Reversed: Yes -> 0,   No -> 100

N/A:
    - score_question returns None.
    - The question is dropped from the dimension denominator.
    - If (N/A weight) / (total dimension weight) > INSUFFICIENT_DATA_THRESHOLD
      (0.40), the dimension is marked "Insufficient Data" and excluded from
      the overall score. Remaining dimension weights are re-normalized on the
      fly inside score_overall so an insufficient dimension does not silently
      drag the overall score down.

Dimension score:
    Weighted average of answered question scores within the dimension.

Overall score:
    Weighted average of dimension scores, using dimension weights normalized
    to sum to 6.0 via normalize_weights(). Insufficient-Data dimensions are
    excluded and the remaining weights are re-normalized on the fly.

Bands (assign_band):
    Half-open intervals [lo, hi). The final band closes at 101 so that a
    score of exactly 100 lands in "Durable". A score of exactly 40 is
    "Critical", 60 is "Fragile", 75 is "Functional", 90 is "Strong".

Top risks (select_top_risks, v0.1.0 rule):
    - Candidates:   every answered question across every dimension.
    - Severity:     (100 - score) * weight. Pain times importance.
    - Primary sort: severity descending (biggest risk first).
    - Tiebreaker:   raw score ascending (lower score wins the tie).
    - Constraint:   no more than max_per_dimension (default 2) items from
                    any single dimension.
    - Take first `limit` (default 3).

Top opportunities (select_top_opportunities, v0.1.0 rule):
    - Candidates: answered questions with score in [score_min, score_max],
                  defaults [40, 70] inclusive.
    - Sort:       question weight descending, score ascending as tiebreak.
    - Exclude:    anything already surfaced in top risks.
    - Take first `limit` (default 3).
    - Only rendered in advisory mode at the UI/report layer; this module
      computes them unconditionally and lets the caller decide.
================================================================================
"""

from rubric import (
    BANDS,
    DIMENSIONS,
    INSUFFICIENT_DATA_LABEL,
    INSUFFICIENT_DATA_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

def normalize_weights(dimensions=None, target_sum=6.0):
    """Return {dimension_id: normalized_weight} summing to target_sum.

    Raw dimension weights live in rubric.DIMENSIONS. They are normalized at
    call time so you can edit raw weights in rubric.py without manually
    rebalancing.
    """
    dims = dimensions if dimensions is not None else DIMENSIONS
    raw_sum = sum(d["weight"] for d in dims)
    if raw_sum == 0:
        return {d["id"]: 0.0 for d in dims}
    scale = target_sum / raw_sum
    return {d["id"]: d["weight"] * scale for d in dims}


# ---------------------------------------------------------------------------
# Single-question scoring
# ---------------------------------------------------------------------------

def score_question(answer, q_type, reverse=False):
    """Score a single answer to 0-100. Returns None for N/A.

    Accepted answer values:
        likert -> int 1..5 or string "1".."5", or "N/A"/None
        yesno  -> "Yes"/"No", True/False, or "N/A"/None
    """
    if answer is None or answer == "N/A":
        return None

    if q_type == "likert":
        val = int(answer)
        if val < 1 or val > 5:
            raise ValueError(f"Likert answer out of range: {val}")
        base = (val - 1) * 25  # 1->0, 2->25, 3->50, 4->75, 5->100
        return float(100 - base) if reverse else float(base)

    if q_type == "yesno":
        is_yes = answer in (True, "Yes", "yes", "YES", 1)
        is_no = answer in (False, "No", "no", "NO", 0)
        if not (is_yes or is_no):
            raise ValueError(f"Yes/No answer not recognized: {answer!r}")
        if reverse:
            return 0.0 if is_yes else 100.0
        return 100.0 if is_yes else 0.0

    raise ValueError(f"Unknown question type: {q_type}")


# ---------------------------------------------------------------------------
# Dimension scoring
# ---------------------------------------------------------------------------

def score_dimension(dimension, answers):
    """Score a single dimension given a flat {question_id: answer} dict.

    Returns:
        {
            "id":              str,
            "name":            str,
            "score":           float or None,
            "band_id":         str or None,
            "band_label":      str,     # "Insufficient Data" when insufficient
            "insufficient":    bool,
            "na_fraction":     float,   # fraction of dim weight answered N/A
            "question_scores": [
                {"id", "score" or None, "weight", "na": bool},
                ...
            ],
        }
    """
    total_weight = sum(q["weight"] for q in dimension["questions"])
    na_weight = 0.0
    weighted_sum = 0.0
    effective_weight = 0.0
    question_scores = []

    for q in dimension["questions"]:
        raw = answers.get(q["id"])
        s = score_question(raw, q["type"], q.get("reverse", False))
        if s is None:
            na_weight += q["weight"]
            question_scores.append({
                "id": q["id"],
                "score": None,
                "weight": q["weight"],
                "na": True,
            })
        else:
            weighted_sum += s * q["weight"]
            effective_weight += q["weight"]
            question_scores.append({
                "id": q["id"],
                "score": s,
                "weight": q["weight"],
                "na": False,
            })

    na_fraction = (na_weight / total_weight) if total_weight > 0 else 0.0
    insufficient = (
        total_weight == 0
        or na_fraction > INSUFFICIENT_DATA_THRESHOLD
        or effective_weight == 0
    )

    if insufficient:
        return {
            "id": dimension["id"],
            "name": dimension["name"],
            "score": None,
            "band_id": None,
            "band_label": INSUFFICIENT_DATA_LABEL,
            "insufficient": True,
            "na_fraction": na_fraction,
            "question_scores": question_scores,
        }

    score = weighted_sum / effective_weight
    band = assign_band(score)
    return {
        "id": dimension["id"],
        "name": dimension["name"],
        "score": score,
        "band_id": band["id"],
        "band_label": band["label"],
        "insufficient": False,
        "na_fraction": na_fraction,
        "question_scores": question_scores,
    }


# ---------------------------------------------------------------------------
# Overall scoring
# ---------------------------------------------------------------------------

def score_overall(dimension_results, normalized_weights):
    """Weighted average of dimension scores, excluding Insufficient Data dims.

    Re-normalizes across the remaining dimensions on the fly.

    dimension_results: {dim_id: result_from_score_dimension}
    normalized_weights: {dim_id: weight} as produced by normalize_weights()

    Returns:
        {"score": float or None, "band_id": str or None, "band_label": str}
    """
    num = 0.0
    den = 0.0
    for dim_id, result in dimension_results.items():
        if result["insufficient"]:
            continue
        w = normalized_weights.get(dim_id, 0.0)
        num += result["score"] * w
        den += w

    if den == 0:
        return {
            "score": None,
            "band_id": None,
            "band_label": INSUFFICIENT_DATA_LABEL,
        }

    score = num / den
    band = assign_band(score)
    return {
        "score": score,
        "band_id": band["id"],
        "band_label": band["label"],
    }


# ---------------------------------------------------------------------------
# Bands
# ---------------------------------------------------------------------------

def assign_band(score):
    """Return {"id": str, "label": str} for a 0-100 score.

    Half-open intervals [lo, hi). Final band closes at 101 so that 100
    lands in the top band.
    """
    for band_id, lo, hi, label in BANDS:
        if lo <= score < hi:
            return {"id": band_id, "label": label}
    # Defensive fallback: clamp out-of-range scores to the nearest end band.
    if score < BANDS[0][1]:
        return {"id": BANDS[0][0], "label": BANDS[0][3]}
    return {"id": BANDS[-1][0], "label": BANDS[-1][3]}


# ---------------------------------------------------------------------------
# Risks and opportunities
# ---------------------------------------------------------------------------

def select_top_risks(dimension_results, dimensions=None, limit=3, max_per_dimension=2):
    """Return the top-N riskiest answered question items.

    Severity = (100 - score) * weight.
    Sort: severity descending; raw score ascending as tiebreaker.
    Constraint: no more than max_per_dimension items from any single dimension.

    Questions inside an Insufficient-Data dimension are still eligible as
    risk candidates if they were individually answered.
    """
    dims = dimensions if dimensions is not None else DIMENSIONS
    dim_by_id = {d["id"]: d for d in dims}
    q_by_id = {q["id"]: (d, q) for d in dims for q in d["questions"]}

    candidates = []
    for dim_id, result in dimension_results.items():
        for qs in result["question_scores"]:
            if qs["na"] or qs["score"] is None:
                continue
            _d, q_meta = q_by_id[qs["id"]]
            candidates.append({
                "dimension_id": dim_id,
                "dimension_name": dim_by_id[dim_id]["name"],
                "question_id": qs["id"],
                "question_text": q_meta["text"],
                "score": qs["score"],
                "weight": qs["weight"],
                "risk_copy": q_meta.get("risk_copy", ""),
                "recommendation": q_meta.get("recommendation", ""),
            })

    candidates.sort(key=lambda c: (-((100.0 - c["score"]) * c["weight"]), c["score"]))

    selected = []
    per_dim_count = {}
    for c in candidates:
        if per_dim_count.get(c["dimension_id"], 0) >= max_per_dimension:
            continue
        selected.append(c)
        per_dim_count[c["dimension_id"]] = per_dim_count.get(c["dimension_id"], 0) + 1
        if len(selected) >= limit:
            break
    return selected


def select_top_opportunities(
    dimension_results,
    dimensions=None,
    risks=None,
    limit=3,
    score_min=40.0,
    score_max=70.0,
):
    """Return the top-N opportunity items.

    Candidates: answered questions with score in [score_min, score_max].
    Sort: weight descending, score ascending as tiebreaker.
    Excludes any question already present in `risks`.
    """
    dims = dimensions if dimensions is not None else DIMENSIONS
    dim_by_id = {d["id"]: d for d in dims}
    q_by_id = {q["id"]: (d, q) for d in dims for q in d["questions"]}
    risk_qids = {r["question_id"] for r in (risks or [])}

    candidates = []
    for dim_id, result in dimension_results.items():
        for qs in result["question_scores"]:
            if qs["na"] or qs["score"] is None:
                continue
            if qs["id"] in risk_qids:
                continue
            if not (score_min <= qs["score"] <= score_max):
                continue
            _d, q_meta = q_by_id[qs["id"]]
            candidates.append({
                "dimension_id": dim_id,
                "dimension_name": dim_by_id[dim_id]["name"],
                "question_id": qs["id"],
                "question_text": q_meta["text"],
                "score": qs["score"],
                "weight": qs["weight"],
                "opportunity_copy": q_meta.get("opportunity_copy", ""),
                "recommendation": q_meta.get("recommendation", ""),
            })

    candidates.sort(key=lambda c: (-c["weight"], c["score"]))
    return candidates[:limit]


# ---------------------------------------------------------------------------
# 30/60/90 action plan (advisory mode)
# ---------------------------------------------------------------------------

def build_action_plan(risks, opportunities):
    """Build a 30/60/90 day action plan from risks and opportunities.

    30-day: Quick wins from top risks (immediate, high-severity items).
    60-day: Systemic fixes from remaining risks and high-weight opportunities.
    90-day: Strategic initiatives from opportunities.

    Returns:
        {
            "30_day": [{"dimension_name", "action"}],
            "60_day": [{"dimension_name", "action"}],
            "90_day": [{"dimension_name", "action"}],
        }
    """
    plan = {"30_day": [], "60_day": [], "90_day": []}

    # 30-day: top 3 risks with recommendations → quick wins
    for r in risks[:3]:
        rec = r.get("recommendation", "")
        if rec:
            plan["30_day"].append({
                "dimension_name": r["dimension_name"],
                "action": rec,
            })
        else:
            plan["30_day"].append({
                "dimension_name": r["dimension_name"],
                "action": r.get("risk_copy", "Address this risk area."),
            })

    # 60-day: remaining risks (if any beyond top 3) + first opportunity
    remaining_risks = risks[3:]
    for r in remaining_risks[:2]:
        rec = r.get("recommendation", r.get("risk_copy", ""))
        if rec:
            plan["60_day"].append({
                "dimension_name": r["dimension_name"],
                "action": rec,
            })
    if opportunities:
        o = opportunities[0]
        rec = o.get("recommendation", o.get("opportunity_copy", ""))
        if rec:
            plan["60_day"].append({
                "dimension_name": o["dimension_name"],
                "action": rec,
            })

    # 90-day: remaining opportunities → strategic initiatives
    for o in opportunities[1:3]:
        rec = o.get("recommendation", o.get("opportunity_copy", ""))
        if rec:
            plan["90_day"].append({
                "dimension_name": o["dimension_name"],
                "action": rec,
            })

    # If 60-day or 90-day are empty, fill from the other bucket
    if not plan["60_day"] and len(plan["30_day"]) > 1:
        plan["60_day"].append(plan["30_day"].pop())
    if not plan["90_day"] and len(plan["60_day"]) > 1:
        plan["90_day"].append(plan["60_day"].pop())

    return plan


# ---------------------------------------------------------------------------
# End-to-end convenience
# ---------------------------------------------------------------------------

def run_audit(answers, dimensions=None):
    """Run the full scoring pipeline.

    answers: flat dict {question_id: answer_value_or_"N/A"}
    Returns a single dict suitable for downstream rendering and JSON export.
    """
    dims = dimensions if dimensions is not None else DIMENSIONS

    dim_results = {d["id"]: score_dimension(d, answers) for d in dims}
    norm_weights = normalize_weights(dims)
    overall = score_overall(dim_results, norm_weights)
    risks = select_top_risks(dim_results, dims)
    opportunities = select_top_opportunities(dim_results, dims, risks=risks)
    action_plan = build_action_plan(risks, opportunities)

    return {
        "overall": overall,
        "dimensions": dim_results,
        "normalized_weights": norm_weights,
        "risks": risks,
        "opportunities": opportunities,
        "action_plan": action_plan,
    }
