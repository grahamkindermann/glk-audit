"""
app.py — Streamlit UI for the Structural Advantage Business Audit.

Multi-step flow:
    Step 1: Firmographics
    Steps 2-7: One dimension per screen, in rubric.DIMENSIONS order
    Step 8: Results

All content (questions, dimension names, CTA, brand) is pulled from rubric.py.
All scoring is delegated to scoring.run_audit. This file is UI plumbing only.

Requires Streamlit >= 1.28 for index=None / value=None widget semantics
and st.rerun().
"""

import os
import re
import tempfile

import streamlit as st

from report import build_pdf
from rubric import (
    BRAND,
    CTA,
    DIMENSIONS,
    FIRMOGRAPHICS,
    MODE,
    RUBRIC_VERSION,
)
from scoring import run_audit


# ---------------------------------------------------------------------------
# UI plumbing constants
# Note: Likert labels are dictated by product spec and tied to the 1-5 scoring
# scale. They live here (not in rubric.py) because changing them would break
# the scoring contract.
# ---------------------------------------------------------------------------
LIKERT_LABELS = {
    1: "Strongly disagree",
    2: "Disagree",
    3: "Neutral",
    4: "Agree",
    5: "Strongly agree",
}
LIKERT_VALUES = [1, 2, 3, 4, 5]

YESNO_OPTIONS = ["Yes", "No"]
YESNO_OPTIONS_WITH_NA = ["Yes", "No", "N/A"]

TOTAL_STEPS = 1 + len(DIMENSIONS) + 1  # firmographics + 6 dims + results


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def init_state():
    if "current_step" not in st.session_state:
        st.session_state.current_step = 0
    if "firmographics" not in st.session_state:
        st.session_state.firmographics = {}


def answer_key(qid):
    return f"ans_{qid}"


def firm_key(fid):
    return f"firm_{fid}"


def goto_step(delta):
    st.session_state.current_step = max(
        0, min(TOTAL_STEPS - 1, st.session_state.current_step + delta)
    )


# ---------------------------------------------------------------------------
# Completion checks (drive Next-disabled state)
# ---------------------------------------------------------------------------

def _firm_value(f):
    return st.session_state.get(firm_key(f["id"]))


def firmographics_complete():
    for f in FIRMOGRAPHICS:
        v = _firm_value(f)
        if v is None:
            return False
        if f["type"] == "text" and str(v).strip() == "":
            return False
    return True


def dimension_complete(dim):
    for q in dim["questions"]:
        if st.session_state.get(answer_key(q["id"])) is None:
            return False
    return True


# ---------------------------------------------------------------------------
# Screen: Firmographics
# ---------------------------------------------------------------------------

def render_firmographics():
    st.header("Business Context")
    st.caption("A minute of context, then the audit. Nothing on this screen is scored.")
    st.write("")

    for f in FIRMOGRAPHICS:
        k = firm_key(f["id"])
        if f["type"] == "select":
            st.selectbox(
                f["label"],
                options=f["options"],
                key=k,
                index=None,
                placeholder="Select one",
            )
        elif f["type"] == "int":
            st.number_input(
                f["label"],
                min_value=0,
                step=1,
                key=k,
                value=None,
                placeholder="0",
            )
        elif f["type"] == "text":
            st.text_input(f["label"], key=k)


# ---------------------------------------------------------------------------
# Screen: Dimension
# ---------------------------------------------------------------------------

def render_dimension(dim):
    st.header(dim["name"])
    if dim.get("summary"):
        st.caption(dim["summary"])
    st.write("")

    for q in dim["questions"]:
        render_question(q)


def render_question(q):
    k = answer_key(q["id"])
    st.markdown(f"**{q['text']}**")

    if q["type"] == "likert":
        st.radio(
            label=q["id"],
            options=LIKERT_VALUES,
            format_func=lambda v: LIKERT_LABELS[v],
            key=k,
            horizontal=True,
            index=None,
            label_visibility="collapsed",
        )
    elif q["type"] == "yesno":
        options = YESNO_OPTIONS_WITH_NA if q.get("allow_na") else YESNO_OPTIONS
        st.radio(
            label=q["id"],
            options=options,
            key=k,
            horizontal=True,
            index=None,
            label_visibility="collapsed",
        )

    st.write("")


# ---------------------------------------------------------------------------
# Collectors for passing into scoring.run_audit
# ---------------------------------------------------------------------------

def collect_answers():
    answers = {}
    for d in DIMENSIONS:
        for q in d["questions"]:
            v = st.session_state.get(answer_key(q["id"]))
            if v is not None:
                answers[q["id"]] = v
    return answers


def collect_firmographics():
    firm = {}
    for f in FIRMOGRAPHICS:
        firm[f["id"]] = st.session_state.get(firm_key(f["id"]))
    return firm


# ---------------------------------------------------------------------------
# Screen: Results
# ---------------------------------------------------------------------------

def render_results():
    answers = collect_answers()
    firm = collect_firmographics()
    st.session_state.firmographics = firm

    result = run_audit(answers)

    st.header("Results")
    if MODE == "advisory":
        company = (firm.get("company_name") or "").strip() or "your business"
        st.caption(f"Prepared for {company}")
    st.write("")

    _render_overall(result["overall"])
    _render_dimension_table(result["dimensions"])
    _render_risks(result["risks"])

    if MODE == "advisory":
        _render_opportunities(result["opportunities"])

    _render_cta()
    _render_downloads(result, firm)


def _render_overall(overall):
    col1, col2 = st.columns([1, 2])
    with col1:
        if overall["score"] is not None:
            st.metric(
                label="Overall Score",
                value=f"{overall['score']:.0f}",
                delta=overall["band_label"],
                delta_color="off",
            )
        else:
            st.metric(label="Overall Score", value="—", delta=overall["band_label"], delta_color="off")
    st.write("")


def _render_dimension_table(dimensions):
    st.subheader("Per-dimension scores")
    rows = []
    for _dim_id, dim in dimensions.items():
        score_str = f"{dim['score']:.0f}" if dim["score"] is not None else "—"
        rows.append({
            "Dimension": dim["name"],
            "Score": score_str,
            "Band": dim["band_label"],
        })
    st.table(rows)


def _render_risks(risks):
    st.subheader("Top risks")
    if not risks:
        st.caption("No risks surfaced.")
        return
    for i, r in enumerate(risks, 1):
        st.markdown(f"**{i}. {r['dimension_name']}**")
        st.markdown(r["risk_copy"])
        st.write("")


def _render_opportunities(opportunities):
    st.subheader("Top opportunities")
    if not opportunities:
        st.caption("No mid-band opportunities surfaced under this input.")
        return
    for i, o in enumerate(opportunities, 1):
        st.markdown(f"**{i}. {o['dimension_name']}**")
        st.markdown(o["opportunity_copy"])
        if o.get("recommendation"):
            st.caption(f"Next step: {o['recommendation']}")
        st.write("")


def _render_cta():
    st.markdown("---")
    cta = CTA.get(MODE)
    if cta is None:
        return
    st.subheader(cta["headline"])
    if cta.get("primary_url"):
        st.markdown(f"[{cta['primary_label']}]({cta['primary_url']})")
    if cta.get("secondary_url"):
        st.markdown(f"[{cta['secondary_label']}]({cta['secondary_url']})")


def _render_downloads(result, firm):
    st.markdown("---")
    pdf_bytes = _build_pdf_bytes(result, firm)
    filename = _pdf_filename(firm)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download PDF report",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            key="download_pdf",
            use_container_width=True,
        )
    with col2:
        st.button(
            "Start over",
            key="start_over",
            on_click=_reset_state,
            use_container_width=True,
        )


def _build_pdf_bytes(result, firm):
    """Render the PDF to a tempfile, read it back, clean up, return bytes."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        build_pdf(result, firm, tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _pdf_filename(firm):
    raw = (firm.get("company_name") or "audit").strip() or "audit"
    slug = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").lower() or "audit"
    return f"structural_advantage_{slug}.pdf"


def _reset_state():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def render_progress():
    step_num = st.session_state.current_step + 1
    st.progress(step_num / TOTAL_STEPS, text=f"Step {step_num} of {TOTAL_STEPS}")


def render_wordmark():
    st.markdown(
        f"<div style='letter-spacing:0.2em;font-family:\"Times New Roman\",serif;"
        f"font-size:1.1rem;color:#0B1F3A;'>{BRAND['wordmark']}</div>",
        unsafe_allow_html=True,
    )
    subtitle = BRAND["cover_subtitle"].get(MODE, "")
    if subtitle:
        st.caption(subtitle)


def render_nav():
    step = st.session_state.current_step

    if step == 0:
        can_advance = firmographics_complete()
    elif 1 <= step <= len(DIMENSIONS):
        can_advance = dimension_complete(DIMENSIONS[step - 1])
    else:
        can_advance = False

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if step > 0 and step < TOTAL_STEPS - 1:
            if st.button("Back", key=f"back_{step}", use_container_width=True):
                goto_step(-1)
                st.rerun()
        elif step == TOTAL_STEPS - 1:
            # Results screen: no back button; Start over is on the results page.
            st.empty()
    with col2:
        if step < TOTAL_STEPS - 1:
            next_label = "See results" if step == len(DIMENSIONS) else "Next"
            clicked = st.button(
                next_label,
                key=f"next_{step}",
                disabled=not can_advance,
                use_container_width=True,
                type="primary",
            )
            if clicked:
                goto_step(1)
                st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title=f"{BRAND['wordmark']} — Audit",
        layout="centered",
    )
    init_state()

    render_wordmark()
    render_progress()
    st.write("")

    step = st.session_state.current_step
    if step == 0:
        render_firmographics()
    elif 1 <= step <= len(DIMENSIONS):
        render_dimension(DIMENSIONS[step - 1])
    else:
        render_results()

    render_nav()

    st.caption(f"Rubric v{RUBRIC_VERSION}")


if __name__ == "__main__":
    main()
