"""
app.py — Streamlit UI for the Structural Advantage Business Audit.

Multi-step flow:
    Step 0 (optional): Login / Sign-up (when Supabase is configured)
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
import streamlit.components.v1 as components

from db_client import get_client, is_configured as db_is_configured
from db_queries import (
    sign_up, sign_in, sign_out, get_current_user,
    upsert_company, get_companies, save_audit,
    get_audits_for_user, get_audits_for_company,
)
from recommendations import generate_recommendations
from report import build_pdf
from rubric import (
    BENCHMARKS,
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
    if "saved_answers" not in st.session_state:
        st.session_state.saved_answers = {}
    if "saved_firm" not in st.session_state:
        st.session_state.saved_firm = {}


def answer_key(qid):
    return f"ans_{qid}"


def firm_key(fid):
    return f"firm_{fid}"


def _snapshot():
    """Save current-step widget values into persistent (non-widget) dicts
    so they survive when widgets are no longer rendered."""
    step = st.session_state.current_step
    if 1 <= step <= len(DIMENSIONS):
        dim = DIMENSIONS[step - 1]
        for q in dim["questions"]:
            v = st.session_state.get(answer_key(q["id"]))
            if v is not None:
                st.session_state.saved_answers[q["id"]] = v
    elif step == 0:
        for f in FIRMOGRAPHICS:
            v = st.session_state.get(firm_key(f["id"]))
            if v is not None:
                st.session_state.saved_firm[f["id"]] = v


def goto_step(delta):
    _snapshot()
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
    # Restore previously saved firmographic answers
    for f in FIRMOGRAPHICS:
        k = firm_key(f["id"])
        if k not in st.session_state and f["id"] in st.session_state.saved_firm:
            st.session_state[k] = st.session_state.saved_firm[f["id"]]

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
    # Restore previously saved answers so Back-nav preserves selections
    for q in dim["questions"]:
        k = answer_key(q["id"])
        if k not in st.session_state and q["id"] in st.session_state.saved_answers:
            st.session_state[k] = st.session_state.saved_answers[q["id"]]

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
    elif q["type"] in ("number", "percent"):
        suffix = " (%)" if q["type"] == "percent" else ""
        st.number_input(
            label=f"{q['id']}{suffix}",
            min_value=0.0 if q["type"] == "percent" else 0,
            step=0.1 if q["type"] == "percent" else 1,
            key=k,
            value=None,
            placeholder="Enter a number",
            label_visibility="collapsed",
        )
        # Show benchmark caption if industry is selected
        industry = (st.session_state.get(firm_key("industry"))
                    or st.session_state.saved_firm.get("industry"))
        if industry:
            bm = BENCHMARKS.get((industry, q["id"]))
            if bm:
                lib = q.get("lower_is_better", False)
                best_label = "Top quartile" if lib else "Top quartile"
                st.caption(
                    f"Industry median: {bm['p50']} · "
                    f"{best_label}: {bm['p25'] if lib else bm['p75']}"
                )

    st.write("")


# ---------------------------------------------------------------------------
# Collectors for passing into scoring.run_audit
# ---------------------------------------------------------------------------

def collect_answers():
    _snapshot()  # capture the last dimension before scoring
    answers = dict(st.session_state.saved_answers)
    # Also pick up any current-step widget values (belt-and-suspenders)
    for d in DIMENSIONS:
        for q in d["questions"]:
            v = st.session_state.get(answer_key(q["id"]))
            if v is not None:
                answers[q["id"]] = v
    return answers


def collect_firmographics():
    firm = dict(st.session_state.saved_firm)
    for f in FIRMOGRAPHICS:
        v = st.session_state.get(firm_key(f["id"]))
        if v is not None:
            firm[f["id"]] = v
    return firm


# ---------------------------------------------------------------------------
# Screen: Results
# ---------------------------------------------------------------------------

def render_results():
    answers = collect_answers()
    firm = collect_firmographics()
    st.session_state.firmographics = firm

    industry = firm.get("industry")
    result = run_audit(answers, industry=industry)

    # Incomplete-submission guardrail: if 3+ dimensions lack data,
    # show a warning instead of the full report.
    insufficient_dims = [
        d for d in result["dimensions"].values() if d["insufficient"]
    ]
    if len(insufficient_dims) >= 3:
        _render_incomplete_warning(insufficient_dims)
        return

    # --- AI recommendations (gated on ANTHROPIC_API_KEY) ---
    ai_recs = _get_or_generate_ai_recs(result, firm, answers)

    st.header("Results")
    if MODE == "advisory":
        company = (firm.get("company_name") or "").strip() or "your business"
        st.caption(f"Prepared for {company}")
    st.write("")

    # AI executive summary at the top (advisory mode only)
    if ai_recs and MODE == "advisory":
        _render_ai_executive_summary(ai_recs)

    _render_overall(result["overall"])
    _render_dimension_table(result["dimensions"])
    _render_risks(result["risks"])

    if MODE == "advisory":
        _render_benchmark_comparison(answers, industry)
        _render_opportunities(result["opportunities"])
        if ai_recs:
            _render_ai_dimension_analyses(ai_recs)
            _render_ai_action_plan(ai_recs)
            _render_ai_roi_estimates(ai_recs)
        else:
            _render_recommendations(result["risks"], result["opportunities"])
            _render_action_plan(result["action_plan"])
    elif industry:
        _render_benchmark_comparison(answers, industry)

    # Regenerate button (advisory mode with API key)
    if MODE == "advisory" and os.environ.get("ANTHROPIC_API_KEY"):
        if st.button("Regenerate AI analysis", key="regen_ai"):
            st.session_state.pop("ai_recommendations", None)
            st.rerun()

    # Auto-save to Supabase if logged in
    _auto_save_audit(result, firm, answers, ai_recs=ai_recs)

    _render_cta()
    _render_downloads(result, firm, answers, ai_recs=ai_recs)


def _render_incomplete_warning(insufficient_dims):
    """Show a warning when too many dimensions lack sufficient data."""
    st.header("Incomplete Submission")
    st.warning(
        f"{len(insufficient_dims)} of 6 dimensions have insufficient data to score. "
        "Please go back and answer more questions to receive your full report."
    )
    st.write("")
    st.subheader("Dimensions needing more answers")
    for d in insufficient_dims:
        st.markdown(f"- **{d['name']}**")
    st.write("")
    if st.button("Go back and complete", type="primary", use_container_width=True):
        # Jump to the first incomplete dimension (step 1-6)
        for i, dim in enumerate(DIMENSIONS):
            if dim["id"] in {d["id"] for d in insufficient_dims}:
                st.session_state.current_step = i + 1
                st.rerun()


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


def _render_benchmark_comparison(answers, industry):
    """Show a 'How You Compare' table for quantitative inputs vs benchmarks."""
    if not industry:
        return
    rows = []
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
            lib = q.get("lower_is_better", False)
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            if lib:
                if v <= bm["p25"]:
                    grade = "Above p75"
                elif v <= bm["p50"]:
                    grade = "Above median"
                elif v <= bm["p75"]:
                    grade = "Below median"
                else:
                    grade = "Below p25"
            else:
                if v >= bm["p75"]:
                    grade = "Above p75"
                elif v >= bm["p50"]:
                    grade = "Above median"
                elif v >= bm["p25"]:
                    grade = "Below median"
                else:
                    grade = "Below p25"
            suffix = "%" if q["type"] == "percent" else ""
            rows.append({
                "Metric": q["text"],
                "Your Value": f"{v:g}{suffix}",
                "Median": f"{bm['p50']}{suffix}",
                "Top Quartile": f"{bm['p25'] if lib else bm['p75']}{suffix}",
                "Standing": grade,
            })
    if not rows:
        return
    st.subheader("How You Compare")
    st.caption(f"Benchmarks for {industry}")
    st.table(rows)


def _render_recommendations(risks, opportunities):
    """Render a consolidated Recommended Next Steps section for advisory mode."""
    # Gather recommendations from both risks and opportunities
    steps = []
    for r in risks:
        rec = r.get("recommendation", "")
        if rec:
            steps.append({"dimension": r["dimension_name"], "text": rec})
    for o in opportunities:
        rec = o.get("recommendation", "")
        if rec:
            steps.append({"dimension": o["dimension_name"], "text": rec})
    if not steps:
        return
    st.subheader("Recommended Next Steps")
    for i, s in enumerate(steps, 1):
        st.markdown(f"**{i}. {s['dimension']}**")
        st.markdown(s["text"])
        st.write("")


def _render_action_plan(action_plan):
    """Render the 30/60/90 day action plan for advisory mode."""
    st.subheader("30 / 60 / 90 Day Action Plan")
    for phase, label in [("30_day", "30 Days — Quick Wins"),
                          ("60_day", "60 Days — Systemic Fixes"),
                          ("90_day", "90 Days — Strategic Initiatives")]:
        items = action_plan.get(phase, [])
        st.markdown(f"**{label}**")
        if not items:
            st.caption("No items for this phase.")
        else:
            for item in items:
                st.markdown(f"- **{item['dimension_name']}**: {item['action']}")
        st.write("")


def _get_or_generate_ai_recs(result, firm, answers):
    """Return cached AI recommendations or generate new ones."""
    if "ai_recommendations" in st.session_state:
        return st.session_state["ai_recommendations"]

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None

    with st.spinner("Generating AI-powered analysis..."):
        ai_recs = generate_recommendations(result, firm, answers)

    if ai_recs:
        st.session_state["ai_recommendations"] = ai_recs
    return ai_recs


def _render_ai_executive_summary(ai_recs):
    """Render the AI-generated executive summary."""
    st.subheader("Executive Summary")
    st.markdown(ai_recs.get("executive_summary", ""))
    st.write("")


def _render_ai_dimension_analyses(ai_recs):
    """Render per-dimension AI analyses."""
    analyses = ai_recs.get("dimension_analyses", [])
    if not analyses:
        return
    st.subheader("Detailed Analysis")
    for da in analyses:
        st.markdown(f"**{da['dimension']}**")
        st.markdown(da.get("analysis", ""))
        recs = da.get("recommendations", [])
        if recs:
            for r in recs:
                st.markdown(f"- {r}")
        st.write("")


def _render_ai_action_plan(ai_recs):
    """Render the AI-generated 30/60/90 action plan."""
    plan = ai_recs.get("action_plan", {})
    if not plan:
        return
    st.subheader("30 / 60 / 90 Day Action Plan")
    for phase, label in [("30_day", "30 Days — Quick Wins"),
                          ("60_day", "60 Days — Systemic Fixes"),
                          ("90_day", "90 Days — Strategic Initiatives")]:
        items = plan.get(phase, [])
        st.markdown(f"**{label}**")
        if not items:
            st.caption("No items for this phase.")
        else:
            for item in items:
                action = item.get("action", "")
                owner = item.get("owner", "")
                outcome = item.get("expected_outcome", "")
                st.markdown(f"- **{action}**")
                if owner:
                    st.caption(f"Owner: {owner} · Expected outcome: {outcome}")
        st.write("")


def _render_ai_roi_estimates(ai_recs):
    """Render the AI-generated ROI estimates."""
    estimates = ai_recs.get("roi_estimates", [])
    if not estimates:
        return
    st.subheader("Estimated ROI — Top Recommendations")
    rows = []
    for e in estimates:
        rows.append({
            "Recommendation": e.get("recommendation", ""),
            "Estimated Impact": e.get("estimated_impact", ""),
            "Confidence": e.get("confidence", "").title(),
        })
    st.table(rows)


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


def _render_downloads(result, firm, answers, ai_recs=None):
    st.markdown("---")
    pdf_bytes = _build_pdf_bytes(result, firm, answers, ai_recs=ai_recs)
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


def _build_pdf_bytes(result, firm, answers, ai_recs=None):
    """Render the PDF to a tempfile, read it back, clean up, return bytes."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        build_pdf(result, firm, tmp_path, answers=answers, ai_recommendations=ai_recs)
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
    # Preserve auth state across resets
    auth_keys = {"auth_user", "auth_session", "auth_user_id"}
    preserved = {k: st.session_state[k] for k in auth_keys if k in st.session_state}
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.saved_answers = {}
    st.session_state.saved_firm = {}
    st.session_state.update(preserved)


# ---------------------------------------------------------------------------
# Auth sidebar (only when Supabase is configured)
# ---------------------------------------------------------------------------

def _render_auth_sidebar():
    """Render login/signup/account info in the sidebar."""
    if not db_is_configured():
        return

    client = get_client()
    if client is None:
        return

    with st.sidebar:
        st.markdown(f"**{BRAND['wordmark']}**")

        if st.session_state.get("auth_user_id"):
            # Logged in
            user_email = st.session_state.get("auth_email", "")
            st.caption(f"Signed in as {user_email}")

            # Past audits
            _render_past_audits_sidebar(client)

            if st.button("Sign out", key="sign_out_btn"):
                sign_out(client)
                for k in ["auth_user", "auth_session", "auth_user_id", "auth_email"]:
                    st.session_state.pop(k, None)
                st.rerun()
        else:
            # Login / Sign-up form
            tab_login, tab_signup = st.tabs(["Sign in", "Sign up"])

            with tab_login:
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                if st.button("Sign in", key="login_btn", use_container_width=True):
                    if email and password:
                        session, err = sign_in(client, email, password)
                        if session:
                            st.session_state.auth_session = session
                            st.session_state.auth_user_id = session.user.id
                            st.session_state.auth_email = session.user.email
                            st.rerun()
                        else:
                            st.error(err or "Sign-in failed.")
                    else:
                        st.warning("Enter email and password.")

            with tab_signup:
                new_email = st.text_input("Email", key="signup_email")
                new_pass = st.text_input("Password", type="password", key="signup_password")
                if st.button("Create account", key="signup_btn", use_container_width=True):
                    if new_email and new_pass:
                        user, err = sign_up(client, new_email, new_pass)
                        if user:
                            st.success("Account created! Check your email to confirm, then sign in.")
                        else:
                            st.error(err or "Sign-up failed.")
                    else:
                        st.warning("Enter email and password.")


def _render_past_audits_sidebar(client):
    """Show past audits in the sidebar for logged-in users."""
    user_id = st.session_state.get("auth_user_id")
    if not user_id:
        return

    audits = get_audits_for_user(client, user_id, limit=10)
    if not audits:
        st.caption("No past audits yet.")
        return

    st.markdown("---")
    st.caption("Past audits")
    for a in audits:
        firm = a.get("firmographics", {})
        name = firm.get("company_name", "Unnamed")
        score = a.get("overall_score")
        band = a.get("overall_band", "")
        date_str = (a.get("created_at") or "")[:10]
        score_str = f"{score:.0f}" if score is not None else "—"
        st.caption(f"{name} · {score_str} ({band}) · {date_str}")


def _auto_save_audit(result, firm, answers, ai_recs=None):
    """Save the audit to Supabase if the user is logged in."""
    if not st.session_state.get("auth_user_id"):
        return
    if st.session_state.get("audit_saved"):
        return  # Already saved this audit

    client = get_client()
    if client is None:
        return

    user_id = st.session_state["auth_user_id"]

    # Upsert company
    company = upsert_company(client, user_id, firm)
    if not company:
        return

    # Save audit
    saved = save_audit(
        client, user_id, company["id"], MODE, answers, firm, result,
        ai_recommendations=ai_recs,
    )
    if saved:
        st.session_state.audit_saved = True


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

    # Auth sidebar (only renders when Supabase is configured)
    _render_auth_sidebar()

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

    # Scroll to top on every page render (fixes "stuck at bottom" after Next).
    # The Streamlit app lives inside a nested iframe on Cloud; the actual
    # scrollable container is <section data-testid="stMain"> in the parent doc.
    components.html(
        """
        <script>
        setTimeout(function() {
            try {
                var main = window.parent.document.querySelector('[data-testid="stMain"]');
                if (main) { main.scrollTop = 0; }
            } catch(e) {}
        }, 100);
        </script>
        """,
        height=0,
    )

    st.caption(f"Rubric v{RUBRIC_VERSION}")


if __name__ == "__main__":
    main()
