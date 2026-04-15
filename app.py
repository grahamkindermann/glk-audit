"""
The Structural Audit
=====================

A B2B operational diagnostic of the business itself, across six dimensions.
Companion to the Structural Advantage Index, which is a personal diagnostic
of the operator. This tool reads the business. The Index reads the founder.

This file is intentionally self-contained. No auth, no Stripe, no database.
Reads the rubric directly from rubric.py. Deploy as-is on Streamlit Cloud.
"""

import os
import math
import streamlit as st

from rubric import (
    DIMENSIONS,
    BANDS,
    BAND_NARRATIVE,
    BENCHMARKS,
    INDUSTRY_LIST,
    INSUFFICIENT_DATA_THRESHOLD,
    INSUFFICIENT_DATA_LABEL,
    BRAND,
)

# ---------------------------------------------------------------------------
# Page chrome
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="The Structural Audit . A diagnostic of the company, not the founder",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS. Matches the visual register of the Structural Advantage Index.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500&family=Inter:wght@400;500;600&display=swap');

:root {
  --bone: #F4EFE6;
  --bone-2: #EAE2D3;
  --hair: #D9CFBC;
  --ink: #14223D;
  --ink-2: #2A3758;
  --muted: #6B6659;
  --accent: #8B6A3F;
  --accent-2: #5B4A2E;
  --warn: #7A2E20;
}

.stApp, html, body, [data-testid="stAppViewContainer"] {
  background: var(--bone) !important;
  color: var(--ink) !important;
  font-family: "Inter", system-ui, sans-serif !important;
}

section.main > div.block-container {
  max-width: 760px !important;
  padding-top: 3.5rem !important;
  padding-bottom: 6rem !important;
}

h1, h2, h3, h4 {
  font-family: "Fraunces", Georgia, serif !important;
  font-weight: 400 !important;
  color: var(--ink) !important;
  letter-spacing: -0.01em !important;
}
h1 { font-size: 2.9rem !important; line-height: 1.08 !important; }
h2 { font-size: 1.75rem !important; line-height: 1.2 !important; margin-top: 1.5rem !important; }
h3 { font-size: 1.25rem !important; line-height: 1.25 !important; }

p, li, label, .stMarkdown, [data-testid="stMarkdownContainer"] p {
  font-family: "Inter", sans-serif !important;
  font-size: 1.02rem !important;
  line-height: 1.55 !important;
  color: var(--ink-2) !important;
}

.sa-mark {
  font-family: "Fraunces", serif;
  font-size: 13px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ink-2);
  margin-bottom: 2.5rem;
  display: flex;
  align-items: center;
  gap: 12px;
}
.sa-mark .dot {
  width: 6px; height: 6px;
  background: var(--accent);
  transform: rotate(45deg);
  display: inline-block;
}

.sa-meta {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--muted);
  margin: 0 0 10px;
}

.sa-lede {
  font-family: "Fraunces", Georgia, serif;
  font-weight: 300;
  font-size: 1.3rem;
  line-height: 1.45;
  color: var(--ink-2);
  max-width: 620px;
  margin-bottom: 2rem;
}

.sa-footnote {
  font-size: 0.85rem;
  color: var(--muted);
  font-style: italic;
}

.sa-rule {
  border: 0;
  border-top: 1px solid var(--hair);
  margin: 2rem 0;
}

.sa-card {
  background: #FBF8F1;
  border: 1px solid var(--hair);
  padding: 22px 26px;
  margin-bottom: 14px;
}
.sa-card .label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--muted);
  margin-bottom: 6px;
}
.sa-card .val {
  font-family: "Fraunces", Georgia, serif;
  font-size: 2rem;
  color: var(--ink);
  line-height: 1;
}
.sa-card .ten { font-size: 0.9rem; color: var(--muted); margin-left: 6px; }

.sa-bar-track {
  background: var(--hair);
  height: 6px;
  width: 100%;
  margin: 4px 0 12px;
  position: relative;
}
.sa-bar-fill {
  background: var(--ink);
  height: 6px;
  position: absolute;
  top: 0; left: 0;
}

.sa-band {
  display: inline-block;
  padding: 4px 10px;
  border: 1px solid var(--ink);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink);
  margin-bottom: 1rem;
}

.sa-risk, .sa-opp {
  border-left: 2px solid var(--accent);
  padding: 14px 18px;
  margin-bottom: 14px;
  background: #FBF8F1;
}
.sa-risk .q, .sa-opp .q {
  font-family: "Fraunces", Georgia, serif;
  font-size: 1.05rem;
  color: var(--ink);
  margin-bottom: 6px;
  font-style: italic;
}
.sa-risk .copy, .sa-opp .copy { font-size: 0.97rem; color: var(--ink-2); }
.sa-rec {
  font-size: 0.94rem;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dotted var(--hair);
  color: var(--ink);
}

div.stButton > button, div.stLinkButton > a {
  background: var(--ink) !important;
  color: var(--bone) !important;
  border: 1px solid var(--ink) !important;
  border-radius: 0 !important;
  font-family: "Inter", sans-serif !important;
  font-weight: 500 !important;
  font-size: 15px !important;
  padding: 14px 28px !important;
  letter-spacing: 0.01em !important;
  transition: background 0.15s, color 0.15s !important;
}
div.stButton > button *, div.stLinkButton > a * {
  color: var(--bone) !important;
}
div.stButton > button:hover, div.stLinkButton > a:hover {
  background: var(--ink-2) !important;
  color: var(--bone) !important;
}
div.stButton > button:hover *, div.stLinkButton > a:hover * {
  color: var(--bone) !important;
}
div.stButton > button:focus, div.stButton > button:active {
  box-shadow: none !important;
  outline: 1px solid var(--ink) !important;
  background: var(--ink) !important;
  color: var(--bone) !important;
}
div.stButton > button:focus *, div.stButton > button:active * {
  color: var(--bone) !important;
}

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] div[role="combobox"],
textarea {
  background: #FBF8F1 !important;
  border: 1px solid var(--hair) !important;
  border-radius: 0 !important;
  font-family: "Inter", sans-serif !important;
  color: var(--ink) !important;
}

div[data-testid="stRadio"] label {
  font-family: "Inter", sans-serif !important;
  color: var(--ink-2) !important;
}

.stProgress > div > div > div > div { background: var(--ink) !important; }

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init():
    ss = st.session_state
    ss.setdefault("step", "intro")
    ss.setdefault("company", "")
    ss.setdefault("industry", INDUSTRY_LIST[0])
    ss.setdefault("revenue", "")
    ss.setdefault("respondent", "")
    ss.setdefault("answers", {})
    ss.setdefault("dim_idx", 0)

_init()

def go(step):
    st.session_state.step = step
    st.rerun()

def advance_dim():
    st.session_state.dim_idx += 1
    if st.session_state.dim_idx >= len(DIMENSIONS):
        st.session_state.step = "results"
    st.rerun()

def back_dim():
    st.session_state.dim_idx = max(0, st.session_state.dim_idx - 1)
    st.rerun()

# ---------------------------------------------------------------------------
# Mark (common header)
# ---------------------------------------------------------------------------
def mark():
    st.markdown(
        '<div class="sa-mark"><span class="dot"></span>'
        '<span>The Structural Audit . A diagnostic of the company</span></div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def score_question(q, answer, industry):
    """
    Return (score in 0..1, answered_flag). None if the question cannot be
    scored (missing answer, missing benchmark, etc.).
    """
    if answer is None or answer == "N/A" or answer == "":
        return None, False
    t = q["type"]
    reverse = q.get("reverse", False)
    try:
        if t == "likert":
            raw = (float(answer) - 1.0) / 4.0
            if reverse:
                raw = 1.0 - raw
            return max(0.0, min(1.0, raw)), True
        if t == "yesno":
            raw = 1.0 if str(answer).lower().startswith("y") else 0.0
            if reverse:
                raw = 1.0 - raw
            return raw, True
        if t in ("number", "percent"):
            bench = BENCHMARKS.get((industry, q["id"]))
            if not bench:
                return None, False
            val = float(answer)
            p25, p50, p75 = bench["p25"], bench["p50"], bench["p75"]
            if q.get("lower_is_better"):
                if val <= p25: return 1.0, True
                if val >= p75: return 0.0, True
                if val <= p50:
                    return 1.0 - 0.5 * (val - p25) / max(p50 - p25, 1e-9), True
                return 0.5 - 0.5 * (val - p50) / max(p75 - p50, 1e-9), True
            else:
                if val >= p75: return 1.0, True
                if val <= p25: return 0.0, True
                if val >= p50:
                    return 0.5 + 0.5 * (val - p50) / max(p75 - p50, 1e-9), True
                return 0.5 * (val - p25) / max(p50 - p25, 1e-9), True
    except Exception:
        return None, False
    return None, False

def compute_results():
    """
    Returns dict:
      {
        "overall": float 0..100 or None,
        "band": (id, label, narrative) or None,
        "dimensions": [ { id, name, score 0..100 or None, weight } ],
        "risks": [ (q, dim, score) ... ],
        "opportunities": [ (q, dim, score) ... ],
      }
    """
    ss = st.session_state
    industry = ss.industry
    answers = ss.answers
    dim_results = []
    scored_q = []
    for dim in DIMENSIONS:
        total_weight = 0.0
        answered_weight = 0.0
        weighted_sum = 0.0
        for q in dim["questions"]:
            w = float(q.get("weight", 1.0))
            total_weight += w
            ans = answers.get(q["id"])
            score, flagged = score_question(q, ans, industry)
            if flagged and score is not None:
                answered_weight += w
                weighted_sum += w * score
                scored_q.append((q, dim, score))
        if total_weight == 0 or answered_weight / total_weight < (1.0 - INSUFFICIENT_DATA_THRESHOLD):
            dim_results.append({
                "id": dim["id"], "name": dim["name"],
                "weight": dim["weight"], "score": None,
            })
        else:
            dim_score = (weighted_sum / answered_weight) * 100.0
            dim_results.append({
                "id": dim["id"], "name": dim["name"],
                "weight": dim["weight"], "score": dim_score,
            })
    # Overall: weighted average of scored dimensions
    scored_dims = [d for d in dim_results if d["score"] is not None]
    if not scored_dims:
        overall = None
        band = None
    else:
        total_w = sum(d["weight"] for d in scored_dims)
        overall = sum(d["score"] * d["weight"] for d in scored_dims) / total_w
        band = None
        for bid, lo, hi, label in BANDS:
            if lo <= overall < hi:
                band = (bid, label, BAND_NARRATIVE.get(bid, ""))
                break
    # Risks: answered questions with lowest score, weighted
    risks_ranked = sorted(
        scored_q,
        key=lambda t: ((1.0 - t[2]) * float(t[0].get("weight", 1.0))),
        reverse=True,
    )
    risks = [r for r in risks_ranked if r[2] < 0.6][:6]
    # Opportunities: same list; in advisory flavor, anything below 0.8 has room
    opps = [r for r in risks_ranked if 0.4 <= r[2] < 0.85][:6]
    return {
        "overall": overall,
        "band": band,
        "dimensions": dim_results,
        "risks": risks,
        "opportunities": opps,
    }

# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------
def screen_intro():
    mark()
    st.markdown('<div class="sa-meta">For the company . Thirty to forty minutes . Six dimensions</div>', unsafe_allow_html=True)
    st.markdown("# An operator's diagnostic of the business itself.")
    st.markdown(
        '<p class="sa-lede">The Structural Audit is the companion to the Structural Advantage Index. '
        'The Index reads the founder. This reads the company. Fifty-eight questions across six dimensions, '
        'weighted scoring, industry benchmarks where they exist, and a risk-ranked output that tells you '
        'what is load-bearing and what is quietly carrying disproportionate risk.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("""
The six dimensions, weighted by their structural impact on durability and enterprise value:

1. **Personnel and Org.** Owner dependency, leadership depth, decision rights.
2. **Accounting and Finance.** Cash visibility, margin clarity, close discipline.
3. **Software Stack.** Systems of record, integration, data hygiene.
4. **AI Readiness.** Workflow maturity, data posture, leverage opportunity.
5. **Sales and Marketing.** Pipeline health, unit economics, repeatability.
6. **Operations.** Delivery reliability, process documentation, recovery.

This is an honest tool. You will be asked things you do not want to answer. The value is in answering them anyway.
""")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Begin the audit", use_container_width=True):
            go("context")
    with col2:
        st.markdown(
            '<a href="#" onclick="return false" style="font-size:14px;color:var(--muted);text-decoration:none;letter-spacing:0.1em;text-transform:uppercase">or,</a>',
            unsafe_allow_html=True,
        )
        st.markdown(
            "If you have not taken the Index yet, start there. Know your shape as an operator first. "
            "[Open the Index &rarr;](https://structuraladvantagediagnostic.netlify.app/)",
        )
    st.markdown(
        '<p class="sa-footnote">Your answers stay in this browser session. Nothing is stored on a server. '
        'If you close the tab, your progress is lost.</p>',
        unsafe_allow_html=True,
    )

def screen_context():
    mark()
    st.markdown('<div class="sa-meta">Step one of seven . Company context</div>', unsafe_allow_html=True)
    st.markdown("## Before the questions, three pieces of context.")
    st.markdown(
        '<p class="sa-lede">The quantitative questions are scored against industry benchmarks. '
        'Telling us the industry sharpens the result. If none of the options fit cleanly, choose the closest.</p>',
        unsafe_allow_html=True,
    )
    st.session_state.company = st.text_input("Company name", value=st.session_state.company)
    st.session_state.industry = st.selectbox(
        "Industry", options=INDUSTRY_LIST,
        index=INDUSTRY_LIST.index(st.session_state.industry) if st.session_state.industry in INDUSTRY_LIST else 0,
    )
    st.session_state.revenue = st.selectbox(
        "Annual revenue band",
        options=["", "$1M to $3M", "$3M to $10M", "$10M to $30M", "$30M+"],
        index=["", "$1M to $3M", "$3M to $10M", "$10M to $30M", "$30M+"].index(st.session_state.revenue) if st.session_state.revenue else 0,
    )
    st.session_state.respondent = st.text_input(
        "Your role (e.g., Founder / CEO, COO, President)",
        value=st.session_state.respondent,
    )
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back", key="ctx_back", use_container_width=True):
            go("intro")
    with col2:
        ready = bool(st.session_state.company) and bool(st.session_state.revenue)
        if st.button("Continue to the audit", key="ctx_next", use_container_width=True, disabled=not ready):
            st.session_state.dim_idx = 0
            go("dim")
    if not ready:
        st.markdown('<p class="sa-footnote">Company name and revenue band are required to continue.</p>', unsafe_allow_html=True)

def render_question(q):
    qid = q["id"]
    current = st.session_state.answers.get(qid)
    note = ""
    if q["type"] == "likert":
        options = ["1 . Strongly disagree", "2 . Disagree", "3 . Neutral", "4 . Agree", "5 . Strongly agree"]
        if q.get("allow_na"):
            options = ["N/A"] + options
        idx = 0
        if isinstance(current, (int, float)):
            label = [o for o in options if o.startswith(str(int(current)) + " ")]
            if label: idx = options.index(label[0])
        elif current == "N/A":
            idx = 0 if "N/A" in options else 0
        choice = st.radio(q["text"], options, index=idx, key=f"rad_{qid}", horizontal=False)
        if choice == "N/A":
            st.session_state.answers[qid] = "N/A"
        else:
            st.session_state.answers[qid] = int(choice.split(" ")[0])
    elif q["type"] == "yesno":
        options = ["Yes", "No"]
        if q.get("allow_na"):
            options = options + ["N/A"]
        idx = options.index(current) if current in options else 0
        choice = st.radio(q["text"], options, index=idx, key=f"rad_{qid}", horizontal=True)
        st.session_state.answers[qid] = choice
    elif q["type"] in ("number", "percent"):
        bench = BENCHMARKS.get((st.session_state.industry, qid))
        note = ""
        if bench:
            note = f" Industry p25 / p50 / p75: {bench['p25']} / {bench['p50']} / {bench['p75']}."
        val = st.text_input(
            q["text"] + (" (numeric value, blank to skip)" if not note else ""),
            value="" if current in (None, "N/A") else str(current),
            key=f"num_{qid}",
            help=note.strip() if note else None,
        )
        if val.strip() == "":
            st.session_state.answers[qid] = "N/A"
        else:
            try:
                st.session_state.answers[qid] = float(val)
            except ValueError:
                st.session_state.answers[qid] = "N/A"
                st.caption("Not a number. This question will be skipped.")

def screen_dimension():
    mark()
    idx = st.session_state.dim_idx
    dim = DIMENSIONS[idx]
    total = len(DIMENSIONS)
    st.markdown(f'<div class="sa-meta">Step {idx + 2} of {total + 2} . Dimension {idx + 1} of {total}</div>', unsafe_allow_html=True)
    st.markdown(f"## {dim['name']}")
    st.markdown(f'<p class="sa-lede">{dim["summary"]}</p>', unsafe_allow_html=True)
    # Progress
    st.progress((idx) / total)
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    for q in dim["questions"]:
        render_question(q)
        st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("Back", key=f"dim_back_{idx}", use_container_width=True):
            if idx == 0:
                go("context")
            else:
                back_dim()
    with col2:
        label = "Continue" if idx < total - 1 else "See results"
        if st.button(label, key=f"dim_next_{idx}", use_container_width=True):
            advance_dim()

def pct_bar(pct):
    pct = max(0.0, min(100.0, pct))
    return (
        f'<div class="sa-bar-track"><div class="sa-bar-fill" style="width:{pct:.1f}%"></div></div>'
    )

def screen_results():
    mark()
    r = compute_results()
    st.markdown('<div class="sa-meta">Results . The structural audit</div>', unsafe_allow_html=True)
    company = st.session_state.company or "The Company"
    st.markdown(f"# {company}. Structural Audit.")
    if r["overall"] is None:
        st.warning("Not enough of the audit was completed to generate a score. Return and answer more questions.")
        if st.button("Return to the audit"):
            st.session_state.dim_idx = 0
            go("dim")
        return
    band_id, band_label, band_narrative = r["band"]
    st.markdown(f'<div class="sa-band">{band_label}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sa-card"><div class="label">Overall structural score</div>'
        f'<div class="val">{r["overall"]:.1f}<span class="ten">/ 100</span></div></div>',
        unsafe_allow_html=True,
    )
    if band_narrative:
        st.markdown(f"<p>{band_narrative}</p>", unsafe_allow_html=True)
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)

    # Dimensions
    st.markdown("## The six dimensions")
    st.markdown(
        '<p class="sa-lede" style="font-size:1.05rem">Any dimension with insufficient answered weight is excluded from the overall score and marked as such.</p>',
        unsafe_allow_html=True,
    )
    for d in r["dimensions"]:
        if d["score"] is None:
            st.markdown(
                f'<div class="sa-card"><div class="label">{d["name"]}</div>'
                f'<div class="val" style="color:var(--muted)">{INSUFFICIENT_DATA_LABEL}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="sa-card"><div class="label">{d["name"]}</div>'
                f'<div class="val">{d["score"]:.1f}<span class="ten">/ 100</span></div>'
                f'{pct_bar(d["score"])}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)

    # Risks
    st.markdown("## What is load-bearing right now")
    st.markdown(
        '<p class="sa-lede" style="font-size:1.05rem">These are the answered items carrying the most risk relative to their weight. '
        'Ordered by structural cost, not severity of feeling.</p>',
        unsafe_allow_html=True,
    )
    if not r["risks"]:
        st.markdown("<p>No material risks surfaced. This is rare. Double-check the answers with a skeptical eye.</p>", unsafe_allow_html=True)
    for q, dim, score in r["risks"]:
        risk = q.get("risk_copy", "")
        rec = q.get("recommendation", "")
        st.markdown(
            f'<div class="sa-risk">'
            f'<div class="sa-meta">{dim["name"]}</div>'
            f'<div class="q">&ldquo;{q["text"]}&rdquo;</div>'
            f'<div class="copy">{risk}</div>'
            + (f'<div class="sa-rec"><strong>Next action.</strong> {rec}</div>' if rec else "")
            + '</div>',
            unsafe_allow_html=True,
        )

    # Opportunities
    if r["opportunities"]:
        st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
        st.markdown("## Where the compounding is waiting")
        st.markdown(
            '<p class="sa-lede" style="font-size:1.05rem">Items that are partially in place. A focused quarter on a few of these usually moves the overall score more than closing a risk.</p>',
            unsafe_allow_html=True,
        )
        for q, dim, score in r["opportunities"]:
            opp = q.get("opportunity_copy", "")
            rec = q.get("recommendation", "")
            st.markdown(
                f'<div class="sa-opp">'
                f'<div class="sa-meta">{dim["name"]}</div>'
                f'<div class="q">&ldquo;{q["text"]}&rdquo;</div>'
                f'<div class="copy">{opp}</div>'
                + (f'<div class="sa-rec"><strong>Next action.</strong> {rec}</div>' if rec else "")
                + '</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)

    # CTAs
    st.markdown("## What to do with this")
    st.markdown(
        "The audit is honest but it is not a plan. If the shape of the score surprised you, the next useful step is a "
        "read-out call. Thirty minutes. The audit in front of us. A pressure-test of the top three risks and the one "
        "move that would actually change the score by the next quarter."
    )
    mail_subject = f"Structural audit read-out ({company})"
    mail_url = f"mailto:hello@grahamkindermann.com?subject={mail_subject.replace(' ', '%20')}"
    st.markdown(
        f'<a href="{mail_url}" style="display:inline-block;background:var(--ink);color:var(--bone);padding:14px 28px;'
        f'text-decoration:none;font-family:Inter,sans-serif;font-weight:500;font-size:15px;border:1px solid var(--ink)">'
        f'Request a read-out</a>',
        unsafe_allow_html=True,
    )

    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    st.markdown("### If you have not taken the Index yet")
    st.markdown(
        "The Structural Advantage Index is the personal companion to this audit. Eleven minutes. An operator archetype. "
        "The shape you bring to the work, named. Most operators find the two read differently when held side by side. "
        "[Open the Index &rarr;](https://structuraladvantagediagnostic.netlify.app/)"
    )

    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    if st.button("Start a new audit"):
        for k in ["step", "company", "industry", "revenue", "respondent", "answers", "dim_idx"]:
            if k in st.session_state:
                del st.session_state[k]
        _init()
        st.rerun()

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
step = st.session_state.step
if step == "intro":
    screen_intro()
elif step == "context":
    screen_context()
elif step == "dim":
    screen_dimension()
elif step == "results":
    screen_results()
else:
    go("intro")
