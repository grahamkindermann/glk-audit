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
import re
import math
import json
import base64
import zlib
import datetime as _dt
import requests
import streamlit as st

from rubric import (
    DIMENSIONS,
    BANDS,
    BAND_NARRATIVE,
    BENCHMARKS,
    INDUSTRY_LIST,
    MINIMUM_ANSWERED_FRACTION,
    INSUFFICIENT_DATA_LABEL,
    BRAND,
    CTA,
    RUBRIC_VERSION,
)

# ---------------------------------------------------------------------------
# Page chrome
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="The Structural Audit . A diagnostic of the company, not the founder",
    page_icon="◆",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Social / OG meta tags (body-level; Streamlit doesn't allow <head> injection)
_SOCIAL_META = """
<meta property="og:title" content="The Structural Audit: A diagnostic of the company, not the founder" />
<meta property="og:description" content="Fifty questions across six dimensions. Weighted scoring, industry benchmarks, risk-ranked output. An honest tool for operators." />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://structural-audit.streamlit.app/" />
<meta name="twitter:card" content="summary" />
<meta name="twitter:title" content="The Structural Audit" />
<meta name="twitter:description" content="Fifty questions across six dimensions. Weighted scoring, industry benchmarks, risk-ranked output. An honest tool for operators." />
"""
st.markdown(_SOCIAL_META, unsafe_allow_html=True)

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

.sa-score-hero {
  background: var(--ink) !important;
  border-color: var(--ink) !important;
  padding: 28px 30px;
}
.sa-score-hero .label { color: var(--bone-2) !important; }
.sa-score-hero .val { color: var(--bone) !important; font-size: 2.8rem; }
.sa-score-hero .ten { color: var(--bone-2) !important; }

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
  padding: 6px 14px;
  border: 1px solid var(--ink);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink);
  margin-bottom: 1rem;
  font-weight: 600;
}
.sa-band--critical { background: #F2DDD9; border-color: var(--warn); color: var(--warn); }
.sa-band--fragile  { background: #F5EDDF; border-color: #B8872E; color: #8B6A2F; }
.sa-band--functional { background: #E8EAE0; border-color: #5A6B3F; color: #4A5A32; }
.sa-band--strong   { background: #D9E6E0; border-color: #2E6B5A; color: #2E6B5A; }
.sa-band--durable  { background: #D5E0EC; border-color: var(--ink); color: var(--ink); }

.sa-risk {
  border-left: 3px solid var(--warn);
  padding: 14px 18px;
  margin-bottom: 14px;
  background: #FBF8F1;
}
.sa-opp {
  border-left: 3px solid var(--accent);
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
[data-testid="manage-app-button"] { display: none !important; }
.viewerBadge_container__r5tak { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }

/* --- Button hierarchy: ghost class for secondary actions --- */
div.stButton.sa-ghost > button {
  background: transparent !important;
  color: var(--ink) !important;
  border: 1px solid var(--ink) !important;
}
div.stButton.sa-ghost > button * {
  color: var(--ink) !important;
}
div.stButton.sa-ghost > button:hover {
  background: var(--bone-2) !important;
  color: var(--ink) !important;
}
div.stButton.sa-ghost > button:hover * {
  color: var(--ink) !important;
}

/* --- Edit-answers: compact link-style buttons --- */
div.stButton.sa-link > button {
  background: transparent !important;
  color: var(--accent) !important;
  border: none !important;
  padding: 4px 0 !important;
  font-size: 13px !important;
  font-weight: 400 !important;
  letter-spacing: 0.04em !important;
  text-decoration: underline !important;
  text-underline-offset: 3px !important;
}
div.stButton.sa-link > button * {
  color: var(--accent) !important;
}
div.stButton.sa-link > button:hover {
  background: transparent !important;
  color: var(--accent-2) !important;
}
div.stButton.sa-link > button:hover * {
  color: var(--accent-2) !important;
}

/* --- Responsive: tablet ≤768px --- */
@media (max-width: 768px) {
  section.main > div.block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
  }
  h1 { font-size: 2.1rem !important; }
  h2 { font-size: 1.45rem !important; margin-top: 1rem !important; }
  h3 { font-size: 1.15rem !important; }
  .sa-lede { font-size: 1.12rem !important; }
  .sa-mark { margin-bottom: 1.5rem; font-size: 12px; }
  .sa-card { padding: 16px 18px; }
  .sa-card .val { font-size: 1.7rem; }
  .sa-score-hero .val { font-size: 2.4rem; }
  .sa-risk, .sa-opp { padding: 12px 14px; }
  div.stButton > button, div.stLinkButton > a {
    padding: 12px 20px !important;
    font-size: 14px !important;
  }
}

/* --- Responsive: phone ≤480px --- */
@media (max-width: 480px) {
  section.main > div.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
  }
  h1 { font-size: 1.7rem !important; line-height: 1.15 !important; }
  h2 { font-size: 1.25rem !important; }
  h3 { font-size: 1.05rem !important; }
  p, li, label, .stMarkdown, [data-testid="stMarkdownContainer"] p {
    font-size: 0.95rem !important;
  }
  .sa-lede { font-size: 1.02rem !important; margin-bottom: 1.2rem !important; }
  .sa-mark { margin-bottom: 1rem; font-size: 11px; letter-spacing: 0.12em; }
  .sa-meta { font-size: 11px; }
  .sa-card { padding: 14px 16px; }
  .sa-card .val { font-size: 1.5rem; }
  .sa-card .ten { font-size: 0.8rem; }
  .sa-score-hero .val { font-size: 2.2rem; }
  .sa-score-hero { padding: 20px 18px; }
  .sa-risk, .sa-opp { padding: 10px 12px; }
  .sa-rule { margin: 1.2rem 0; }
  div.stButton > button, div.stLinkButton > a {
    padding: 10px 14px !important;
    font-size: 13px !important;
  }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

import streamlit.components.v1 as _components

# Scroll to top on every page transition.
# st.markdown strips <script> tags, so we use st.components.v1.html() which
# creates a tiny iframe that *can* run JS.  From that iframe we reach up
# through parent frames to find Streamlit's <section class="stMain"> and
# reset its scrollTop.

def _install_parent_js(scroll=True, beforeunload=True, buttons=True, hide_chrome=True):
    """Install all parent-document JS helpers in a single iframe.
    Each feature is guarded by its own flag so it only installs once."""
    parts = []
    if hide_chrome:
        parts.append("""
          (function(){
            var css = [
              '[data-testid="manage-app-button"] { display:none!important; }',
              '.stAppDeployButton { display:none!important; }',
              '#MainMenu { visibility:hidden!important; }',
              'footer { visibility:hidden!important; }',
              'header[data-testid="stHeader"] { visibility:hidden!important; }',
              '[data-testid="stSidebarCollapsedControl"] { display:none!important; }',
              '.viewerBadge_container__r5tak { display:none!important; }',
              '[class*="viewerBadge"] { display:none!important; }',
              '[class*="StatusWidget"] { display:none!important; }',
              '[class*="stStatusWidget"] { display:none!important; }',
              '[data-testid="StatusWidget"] { display:none!important; }',
              '[class*="stAppStatus"] { display:none!important; }',
              'a[href*="streamlit.io"] img { display:none!important; }',
              'a[href*="streamlit.io/cloud"] { display:none!important; }'
            ].join('\\n');
            var w = window;
            while (w) {
              try {
                var d = w.document;
                if (d && d.head && !d._saChromeHidden) {
                  d._saChromeHidden = true;
                  var styl = d.createElement('style');
                  styl.textContent = css;
                  d.head.appendChild(styl);
                }
              } catch(e) { break; }
              if (w === w.parent) break;
              w = w.parent;
            }
            // Nuclear: hide any small fixed/absolute element in bottom-right corner
            function hideCornerJunk(doc) {
              try {
                var all = doc.querySelectorAll('*');
                var vw = doc.defaultView.innerWidth;
                var vh = doc.defaultView.innerHeight;
                for (var el of all) {
                  var cst = doc.defaultView.getComputedStyle(el);
                  if (cst.position !== 'fixed' && cst.position !== 'absolute') continue;
                  var r = el.getBoundingClientRect();
                  if (r.width > 0 && r.width < 300 && r.height > 0 && r.height < 200 &&
                      r.right > vw - 200 && r.bottom > vh - 100) {
                    el.style.setProperty('display', 'none', 'important');
                  }
                }
              } catch(e) {}
            }
            var w2 = window;
            while (w2) {
              try { hideCornerJunk(w2.document); } catch(e) { break; }
              if (w2 === w2.parent) break;
              w2 = w2.parent;
            }
            setTimeout(function(){
              var w3 = window;
              while (w3) {
                try { hideCornerJunk(w3.document); } catch(e) { break; }
                if (w3 === w3.parent) break;
                w3 = w3.parent;
              }
            }, 3000);
          })();""")
    if scroll:
        parts.append("""
          if (!pd._saScrollInstalled) {
            pd._saScrollInstalled = true;
            var stag = pd.createElement('script');
            stag.textContent = [
              '(function(){',
              '  var s = document.querySelector("section.stMain");',
              '  if (!s) return;',
              '  var lastText = s.innerText.substring(0, 80);',
              '  var hammering = false;',
              '  new MutationObserver(function(){',
              '    if (hammering) return;',
              '    var nowText = s.innerText.substring(0, 80);',
              '    if (nowText !== lastText) {',
              '      lastText = nowText;',
              '      hammering = true;',
              '      s.scrollTop = 0;',
              '      var iv = setInterval(function(){ s.scrollTop = 0; }, 20);',
              '      setTimeout(function(){ clearInterval(iv); hammering = false; }, 1500);',
              '    }',
              '  }).observe(s, { attributes: true, subtree: true });',
              '})();'
            ].join('\\n');
            pd.body.appendChild(stag);
          }""")
    if beforeunload:
        parts.append("""
          if (!pw._saUnloadHandler) {
            pw._saUnloadHandler = function(e) {
              e.preventDefault();
              e.returnValue = '';
            };
            pw.addEventListener('beforeunload', pw._saUnloadHandler);
          }""")
    else:
        # Remove the handler if it was previously installed
        parts.append("""
          if (pw._saUnloadHandler) {
            pw.removeEventListener('beforeunload', pw._saUnloadHandler);
            pw._saUnloadHandler = null;
          }""")
    if buttons:
        parts.append("""
          if (!pd._saBtnInstalled) {
            pd._saBtnInstalled = true;
            var btag = pd.createElement('script');
            btag.textContent = [
              '(function(){',
              '  function classify(){',
              '    document.querySelectorAll("div.stButton > button").forEach(function(b){',
              '      var t = (b.textContent||"").trim();',
              '      var p = b.closest("div.stButton");',
              '      if (!p) return;',
              '      if (t === "Back") p.classList.add("sa-ghost");',
              '      if (t.indexOf("Edit ") === 0 || t.indexOf("Complete ") === 0 || t.indexOf("Skip this") === 0) p.classList.add("sa-link");',
              '    });',
              '  }',
              '  classify();',
              '  var s = document.querySelector("section.stMain");',
              '  if (s) new MutationObserver(function(){ classify(); }).observe(s, { childList:true, subtree:true });',
              '})();'
            ].join('\\n');
            pd.body.appendChild(btag);
          }""")
    js_body = "\n".join(parts)
    _components.html(
        f"""
        <script>
        (function(){{
          try {{
            var pw = window.parent;
            var pd = pw.document;
            {js_body}
          }} catch(e) {{}}
        }})();
        </script>
        """,
        height=0,
    )

# ---------------------------------------------------------------------------
# State persistence (save/resume codes + localStorage auto-save)
# ---------------------------------------------------------------------------
def _encode_state():
    """Compress current session state into a short, copyable code."""
    ss = st.session_state
    payload = {
        "s": ss.get("step", "intro"),
        "c": ss.get("company", ""),
        "i": ss.get("industry", ""),
        "r": ss.get("revenue", ""),
        "p": ss.get("respondent", ""),
        "d": ss.get("dim_idx", 0),
        "a": ss.get("answers", {}),
        "hc": ss.get("headcount", ""),
        "em": ss.get("ebitda_margin", ""),
        "yo": ss.get("years_in_op", ""),
        "oh": ss.get("owner_hours", ""),
        "ai": ss.get("audit_intent", ""),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    compressed = zlib.compress(raw, 9)
    return base64.urlsafe_b64encode(compressed).decode().rstrip("=")

def _decode_state(code):
    """Decode a resume code and populate session state. Returns True on success."""
    try:
        padded = code + "=" * (4 - len(code) % 4)
        compressed = base64.urlsafe_b64decode(padded)
        raw = zlib.decompress(compressed)
        payload = json.loads(raw)
        ss = st.session_state
        ss["step"] = payload.get("s", "intro")
        ss["company"] = payload.get("c", "")
        ss["industry"] = payload.get("i", "")
        ss["revenue"] = payload.get("r", "")
        ss["respondent"] = payload.get("p", "")
        ss["dim_idx"] = payload.get("d", 0)
        ss["answers"] = payload.get("a", {})
        ss["headcount"] = payload.get("hc", "")
        ss["ebitda_margin"] = payload.get("em", "")
        ss["years_in_op"] = payload.get("yo", "")
        ss["owner_hours"] = payload.get("oh", "")
        ss["audit_intent"] = payload.get("ai", "")
        return True
    except Exception:
        return False

def _save_to_localstorage():
    """Inject JS into the parent document that auto-saves the current state
    to localStorage. Runs silently on every screen render."""
    code = _encode_state()
    _components.html(
        f"""
        <script>
        (function(){{
          try {{
            window.parent.localStorage.setItem('sa_audit_state', '{code}');
          }} catch(e) {{}}
        }})();
        </script>
        """,
        height=0,
    )

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init():
    ss = st.session_state
    ss.setdefault("step", "intro")
    ss.setdefault("company", "")
    ss.setdefault("industry", "")
    ss.setdefault("revenue", "")
    ss.setdefault("respondent", "")
    ss.setdefault("answers", {})
    ss.setdefault("dim_idx", 0)
    ss.setdefault("headcount", "")
    ss.setdefault("ebitda_margin", "")
    ss.setdefault("years_in_op", "")
    ss.setdefault("owner_hours", "")
    ss.setdefault("audit_intent", "")

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
        '<span>The Structural Audit . A diagnostic of the company, not the founder</span></div>',
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

def _band_for_score(score):
    """Return (band_id, band_label) for a numeric score, or None."""
    if score is None:
        return None
    for bid, lo, hi, label in BANDS:
        if lo <= score < hi:
            return (bid, label)
    return None

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
        if total_weight == 0 or answered_weight / total_weight < MINIMUM_ANSWERED_FRACTION:
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
    risks = [r for r in risks_ranked if r[2] < 0.4][:6]
    # Opportunities: partially in place but room to improve; no overlap with risks
    opps = [r for r in risks_ranked if 0.4 <= r[2] < 0.75][:6]
    return {
        "overall": overall,
        "band": band,
        "dimensions": dim_results,
        "risks": risks,
        "opportunities": opps,
    }

# ---------------------------------------------------------------------------
# Email capture (Loops API)
# ---------------------------------------------------------------------------
def _capture_email(email: str, company: str, band: str, score: float):
    """Send lead to Loops for nurture drip. Fails silently — no error shown to user."""
    api_key = os.environ.get("LOOPS_API_KEY") or st.secrets.get("LOOPS_API_KEY", "")
    if not api_key:
        # No key configured; just mark as captured so UX still works
        st.session_state.email_captured = True
        return
    try:
        resp = requests.post(
            "https://app.loops.so/api/v1/contacts/create",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "email": email,
                "source": "structural_audit",
                "company": company,
                "auditBand": band,
                "auditScore": round(score, 1),
                "auditIntent": st.session_state.get("audit_intent", ""),
            },
            timeout=8,
        )
        # Fire the event for the drip sequence.
        # Contact creation returns 409 for existing contacts — that's fine,
        # we still want to trigger the drip. Only true failures (5xx, timeout)
        # should soft-fail.
        if resp.status_code < 300 or resp.status_code == 409:
            requests.post(
                "https://app.loops.so/api/v1/events/send",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"email": email, "eventName": "audit_completed"},
                timeout=8,
            )
            st.session_state.email_captured = True
        else:
            st.session_state.email_captured = "soft_fail"
    except Exception:
        st.session_state.email_captured = "soft_fail"


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------
def screen_intro():
    _install_parent_js(scroll=False, beforeunload=False, buttons=False, hide_chrome=True)
    mark()
    st.markdown('<div class="sa-meta">For the company . Fifteen to twenty minutes . Six dimensions . Mostly quick ratings</div>', unsafe_allow_html=True)
    st.markdown("# An operator's diagnostic of the business itself.")
    st.markdown(
        '<p class="sa-lede">The Structural Audit is the companion to the Structural Advantage Index. '
        'The Index reads the founder. This reads the company. Fifty questions across six dimensions, '
        'weighted scoring, industry benchmarks where they exist, and a risk-ranked output that tells you '
        'what is load-bearing and what is quietly carrying disproportionate risk.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-size:0.92rem;color:var(--muted);margin:0 0 1.5rem">'
        'Built by Graham Kindermann, operational advisor to PE-backed services businesses.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("""
The six dimensions, weighted by their structural impact on durability and enterprise value:

1. **Personnel & Org.** Owner dependency, leadership depth, decision rights.
2. **Accounting & Finance.** Cash visibility, margin clarity, close discipline.
3. **Software Stack.** Systems of record, integration, data hygiene.
4. **AI Readiness.** Production adoption, team fluency, governance.
5. **Sales & Marketing.** Pipeline health, unit economics, repeatability.
6. **Operations & Process.** Delivery reliability, process documentation, recovery.

This is an honest tool. You will be asked things you do not want to answer. The value is in answering them anyway.
""")
    with st.expander("Have these numbers ready"):
        st.markdown(
            "Most of the audit is qualitative. A handful of questions ask for specific metrics. "
            "You do not need exact figures, but reasonable estimates will sharpen the result. "
            "If you do not track a number, skip it. The gaps themselves are part of the diagnostic."
        )
        st.markdown("""
- Annual voluntary turnover (%)
- Average days to fill a role
- Days to close monthly books
- Accounts receivable over 60 days (%)
- Number of paid SaaS tools in use
- Annual software spend as % of revenue
- Number of AI workflows in production
- Customer acquisition cost ($)
- Monthly customer churn rate (%)
- On-time, in-full delivery rate (%)
- Mean time to resolve customer issues (hours)
""")
    if st.button("Begin the audit", use_container_width=False):
        import time as _time
        st.session_state["_audit_start"] = _time.time()
        go("context")

    # --- Resume previous audit ---
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    with st.expander("Resume a previous audit"):
        resume_code = st.text_input(
            "Paste your save code",
            key="resume_code_input",
            placeholder="Paste the code you saved from a previous session",
        )
        if st.button("Resume", key="btn_resume"):
            if resume_code and _decode_state(resume_code.strip()):
                st.rerun()
            else:
                st.error("Invalid code. Please check and try again.")
        # Auto-detect localStorage and offer one-click restore
        _components.html(
            """
            <script>
            (function(){
              try {
                var saved = window.parent.localStorage.getItem('sa_audit_state');
                if (saved) {
                  var pd = window.parent.document;
                  // Find the resume text input and fill it
                  var inputs = pd.querySelectorAll('input[type="text"]');
                  var resumeInput = null;
                  for (var i = 0; i < inputs.length; i++) {
                    if (inputs[i].placeholder && inputs[i].placeholder.indexOf('save code') !== -1) {
                      resumeInput = inputs[i];
                      break;
                    }
                  }
                  if (resumeInput && !resumeInput.value) {
                    // Set the value via React's internal setter so Streamlit picks it up
                    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeSetter.call(resumeInput, saved);
                    resumeInput.dispatchEvent(new Event('input', { bubbles: true }));
                  }
                  // Show a hint above the expander
                  var expanders = pd.querySelectorAll('[data-testid="stExpander"]');
                  if (expanders.length > 0) {
                    var exp = expanders[expanders.length - 1];
                    if (!pd._saResumeHint) {
                      pd._saResumeHint = true;
                      var hint = pd.createElement('div');
                      hint.style.cssText = 'font-family:Inter,sans-serif;font-size:0.88rem;color:#8B6A3F;margin:0 0 6px;padding:8px 12px;background:#FBF8F1;border:1px solid #D9CFBC';
                      hint.textContent = 'You have an audit in progress in this browser. Open the panel below and click Resume to pick up where you left off.';
                      exp.parentElement.insertBefore(hint, exp);
                    }
                  }
                }
              } catch(e) {}
            })();
            </script>
            """,
            height=0,
        )

    st.markdown(
        "If you have not taken the Index yet, start there. Know your shape as an operator first. "
        "[Open the Index &rarr;](https://structuraladvantageindex.netlify.app/)",
    )
    st.markdown(
        '<p class="sa-footnote">Your progress is auto-saved in this browser. If you need to switch devices, '
        'use the save code shown at the bottom of each section.</p>',
        unsafe_allow_html=True,
    )

def screen_context():
    _install_parent_js(scroll=True, beforeunload=True, buttons=True)
    _save_to_localstorage()
    mark()
    st.markdown('<div class="sa-meta">Step 1 of 8 . Company context</div>', unsafe_allow_html=True)
    st.markdown("## Before the questions, a few pieces of context.")
    st.markdown(
        '<p class="sa-lede">The quantitative questions are scored against industry benchmarks. '
        'Telling us the industry sharpens the result. If none of the options fit cleanly, choose the closest.</p>',
        unsafe_allow_html=True,
    )
    st.progress(1 / 8)
    st.session_state.company = st.text_input("Company name", value=st.session_state.company)
    _ind_idx = INDUSTRY_LIST.index(st.session_state.industry) if st.session_state.industry in INDUSTRY_LIST else None
    st.session_state.industry = st.selectbox(
        "Industry", options=INDUSTRY_LIST,
        index=_ind_idx,
        placeholder="Select your industry",
    )
    _rev_options = ["Under $1M", "$1M to $3M", "$3M to $10M", "$10M to $30M", "$30M+"]
    _rev_idx = _rev_options.index(st.session_state.revenue) if st.session_state.revenue in _rev_options else None
    st.session_state.revenue = st.selectbox(
        "Annual revenue band",
        options=_rev_options,
        index=_rev_idx,
        placeholder="Select a revenue band",
    )
    st.session_state.respondent = st.text_input(
        "Your role (e.g., Founder / CEO, COO, President)",
        value=st.session_state.respondent,
    )
    _INTENT_OPTIONS = [
        "General curiosity",
        "Board or investor request",
        "Preparing for a transaction",
        "Evaluating advisory support",
        "Someone recommended it",
    ]
    _intent_idx = _INTENT_OPTIONS.index(st.session_state.audit_intent) if st.session_state.audit_intent in _INTENT_OPTIONS else None
    st.session_state.audit_intent = st.selectbox(
        "What prompted this audit? (optional)",
        options=_INTENT_OPTIONS,
        index=_intent_idx,
        placeholder="Select if you'd like",
    )
    # Optional firmographics. Auto-expand if any field is already filled (from resume).
    _has_firmographics = any(st.session_state.get(k) for k in ("headcount", "ebitda_margin", "years_in_op", "owner_hours"))
    with st.expander("Optional: additional company details", expanded=_has_firmographics):
        st.session_state.headcount = st.text_input(
            "Full-time headcount",
            value=st.session_state.headcount,
            placeholder="e.g. 25",
        )
        st.session_state.ebitda_margin = st.text_input(
            "EBITDA margin (%)",
            value=st.session_state.ebitda_margin,
            placeholder="e.g. 18",
        )
        st.session_state.years_in_op = st.text_input(
            "Years in operation",
            value=st.session_state.years_in_op,
            placeholder="e.g. 7",
        )
        st.session_state.owner_hours = st.text_input(
            "Owner's weekly hours in the business",
            value=st.session_state.owner_hours,
            placeholder="e.g. 55",
        )
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back", key="ctx_back", use_container_width=True):
            go("intro")
    with col2:
        ready = bool(st.session_state.company) and bool(st.session_state.revenue) and bool(st.session_state.industry)
        if st.button("Continue to the audit", key="ctx_next", use_container_width=True, disabled=not ready):
            st.session_state.dim_idx = 0
            go("dim")
    if not ready:
        st.markdown('<p class="sa-footnote">Company name, industry, and revenue band are required to continue.</p>', unsafe_allow_html=True)

def render_question(q):
    qid = q["id"]
    current = st.session_state.answers.get(qid)
    note = ""
    if q["type"] == "likert":
        options = ["—", "1", "2", "3", "4", "5"]
        if q.get("allow_na"):
            options = ["N/A", "1", "2", "3", "4", "5"]
        idx = 0  # default to placeholder (unanswered)
        if isinstance(current, (int, float)):
            label = str(int(current))
            if label in options:
                idx = options.index(label)
        elif current == "N/A":
            idx = 0 if "N/A" in options else 0
        st.markdown(f"**{q['text']}**")
        st.caption("1 = Strongly disagree · 5 = Strongly agree")
        choice = st.radio("Select", options, index=idx, key=f"rad_{qid}", horizontal=True, label_visibility="collapsed")
        if choice == "—":
            st.session_state.answers[qid] = None
        elif choice == "N/A":
            st.session_state.answers[qid] = "N/A"
        else:
            st.session_state.answers[qid] = int(choice)
    elif q["type"] == "yesno":
        options = ["Skip", "Yes", "No"]
        if q.get("allow_na"):
            options = ["Skip", "Yes", "No", "N/A"]
        if current in ("Yes", "No", "N/A"):
            idx = options.index(current)
        else:
            idx = 0  # "Skip" placeholder = unanswered
        choice = st.radio(q["text"], options, index=idx, key=f"rad_{qid}", horizontal=True)
        if choice == "Skip":
            st.session_state.answers[qid] = None
        else:
            st.session_state.answers[qid] = choice
    elif q["type"] in ("number", "percent"):
        bench = BENCHMARKS.get((st.session_state.industry, qid))
        placeholder = "e.g. 15" if q["type"] == "percent" else "e.g. 500000"
        if bench:
            placeholder = f"e.g. {bench['p50']}"
        val = st.text_input(
            q["text"] + " (blank to skip)",
            value="" if current in (None, "N/A") else str(current),
            key=f"num_{qid}",
            placeholder=placeholder,
        )
        if bench:
            _BENCH_UNITS = {
                "per_q_turnover_pct": "%", "fin_q_ar_over_60_pct": "%",
                "sw_q_software_spend_pct": "%", "sal_q_monthly_churn_pct": "%",
                "ops_q_on_time_delivery_pct": "%",
                "per_q_days_to_fill": " days", "fin_q_days_to_close": " days",
                "ops_q_mttr_hours": " hrs",
                "sw_q_num_saas_tools": " tools", "ai_q_num_ai_workflows": "",
                "sal_q_cac": "",
            }
            _u = _BENCH_UNITS.get(qid, "")
            _fmt = lambda v: f"${v:,.0f}" if qid == "sal_q_cac" else f"{v:g}{_u}"
            st.caption(f"Industry benchmark: 25th: {_fmt(bench['p25'])} · Median: {_fmt(bench['p50'])} · 75th: {_fmt(bench['p75'])}")
        cleaned = val.strip().replace(",", "").replace("$", "").replace("%", "").replace("~", "")
        # Handle k/K and m/M suffixes for thousands and millions
        _k_match = re.match(r'^([0-9]*\.?[0-9]+)[kK]$', cleaned)
        _m_match = re.match(r'^([0-9]*\.?[0-9]+)[mM]$', cleaned)
        if _k_match:
            cleaned = str(float(_k_match.group(1)) * 1000)
        elif _m_match:
            cleaned = str(float(_m_match.group(1)) * 1000000)
        if cleaned == "":
            st.session_state.answers[qid] = "N/A"
        else:
            try:
                _num_val = float(cleaned)
                if _num_val < 0:
                    st.session_state.answers[qid] = "N/A"
                    st.caption("Value must be zero or positive. This question will be skipped.")
                else:
                    st.session_state.answers[qid] = _num_val
                    # Inline benchmark feedback
                    if bench:
                        _lower = q.get("lower_is_better", False)
                        if _lower:
                            if _num_val <= bench["p25"]:
                                st.markdown('<p style="font-size:0.85rem;color:#5A6B3F;margin:2px 0 0">Better than 75% of peers in your industry.</p>', unsafe_allow_html=True)
                            elif _num_val <= bench["p50"]:
                                st.markdown('<p style="font-size:0.85rem;color:#5A6B3F;margin:2px 0 0">Better than the industry median.</p>', unsafe_allow_html=True)
                            elif _num_val <= bench["p75"]:
                                st.markdown('<p style="font-size:0.85rem;color:#B8872E;margin:2px 0 0">Below industry median.</p>', unsafe_allow_html=True)
                            else:
                                st.markdown('<p style="font-size:0.85rem;color:#7A2E20;margin:2px 0 0">Below 75% of peers in your industry.</p>', unsafe_allow_html=True)
                        else:
                            if _num_val >= bench["p75"]:
                                st.markdown('<p style="font-size:0.85rem;color:#5A6B3F;margin:2px 0 0">Better than 75% of peers in your industry.</p>', unsafe_allow_html=True)
                            elif _num_val >= bench["p50"]:
                                st.markdown('<p style="font-size:0.85rem;color:#5A6B3F;margin:2px 0 0">Better than the industry median.</p>', unsafe_allow_html=True)
                            elif _num_val >= bench["p25"]:
                                st.markdown('<p style="font-size:0.85rem;color:#B8872E;margin:2px 0 0">Below industry median.</p>', unsafe_allow_html=True)
                            else:
                                st.markdown('<p style="font-size:0.85rem;color:#7A2E20;margin:2px 0 0">Below 75% of peers in your industry.</p>', unsafe_allow_html=True)
            except ValueError:
                st.session_state.answers[qid] = "N/A"
                st.caption("Could not parse as a number. Enter a plain numeric value (e.g. 15, 500000). This question will be skipped.")

def screen_dimension():
    _install_parent_js(scroll=True, beforeunload=True, buttons=True)
    _save_to_localstorage()
    mark()
    idx = st.session_state.dim_idx
    dim = DIMENSIONS[idx]
    total = len(DIMENSIONS)
    st.markdown(f'<div class="sa-meta">Step {idx + 2} of {total + 2} . Dimension {idx + 1} of {total}</div>', unsafe_allow_html=True)
    st.markdown(f"## {dim['name']}")
    st.markdown(f'<p class="sa-lede">{dim["summary"]}</p>', unsafe_allow_html=True)
    # Progress (consistent 1-8 scale: context=1, dims=2-7)
    st.progress((idx + 2) / (total + 2))
    # Running tally + time estimate
    total_all_q = sum(len(d["questions"]) for d in DIMENSIONS)
    answered_so_far = 0
    total_so_far = 0
    for prev_dim in DIMENSIONS[:idx]:
        for pq in prev_dim["questions"]:
            total_so_far += 1
            ans = st.session_state.answers.get(pq["id"])
            if ans not in (None, "N/A", ""):
                answered_so_far += 1
    remaining_q = total_all_q - total_so_far
    est_minutes = max(1, round(remaining_q * 20 / 60))
    time_label = f"~{est_minutes} min remaining" if est_minutes > 1 else "~1 min remaining"
    if idx > 0:
        st.caption(f"{answered_so_far} of {total_so_far} questions answered across {idx} completed dimension{'s' if idx > 1 else ''}. {time_label}.")
    else:
        st.caption(f"{time_label} ({total_all_q} questions total).")
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    num_q = len(dim["questions"])
    _last_group = None
    for qi, q in enumerate(dim["questions"], 1):
        _grp = q.get("group")
        if _grp and _grp != _last_group:
            _components.html(
                f'<p style="font-family:Fraunces,Georgia,serif;font-size:1.05rem;font-weight:400;'
                f'color:#8B6A3F;margin:0;padding:0;letter-spacing:0.01em;line-height:1.4">{_grp}</p>',
                height=38,
            )
            _last_group = _grp
        st.markdown(
            f'<p style="font-size:0.85rem;letter-spacing:0.12em;text-transform:uppercase;'
            f'color:var(--muted);margin:0 0 2px">Question {qi} of {num_q}</p>',
            unsafe_allow_html=True,
        )
        render_question(q)
        st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
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
    # Skip dimension (below nav, styled as link — less prominent than primary actions)
    if st.button("Skip this dimension", key=f"dim_skip_{idx}"):
        for q in dim["questions"]:
            st.session_state.answers[q["id"]] = "N/A"
        advance_dim()
    # Save code for cross-device resume
    with st.expander("Save your progress"):
        code = _encode_state()
        st.code(code, language=None)
        _components.html(
            f"""
            <style>
            body {{ margin:0; padding:0; background:transparent; }}
            button {{
              background:#14223D; color:#F4EFE6; border:none; padding:8px 18px;
              font-family:"Inter",sans-serif; font-size:13px; font-weight:500;
              cursor:pointer; letter-spacing:0.02em;
            }}
            button:hover {{ background:#2A3758; }}
            .ok {{ color:#8B6A3F; font-size:12px; margin-left:8px; font-family:"Inter",sans-serif; }}
            </style>
            <button onclick="navigator.clipboard.writeText('{code}').then(function(){{document.getElementById('cp').textContent='Copied.'}})">
              Copy to clipboard
            </button><span id="cp" class="ok"></span>
            """,
            height=42,
        )
        st.caption("Paste this code on the intro screen to resume from any device.")

def pct_bar(pct):
    pct = max(0.0, min(100.0, pct))
    return (
        f'<div class="sa-bar-track"><div class="sa-bar-fill" style="width:{pct:.1f}%"></div></div>'
    )

def screen_results():
    _install_parent_js(scroll=True, beforeunload=False, buttons=True)
    _save_to_localstorage()
    mark()
    r = compute_results()
    company = st.session_state.company or "The Company"
    _audit_date = _dt.date.today().strftime("%B %-d, %Y")
    # Time-spent calculation
    import time as _time
    _start = st.session_state.get("_audit_start")
    _elapsed_str = ""
    if _start:
        _elapsed_min = int((_time.time() - _start) / 60)
        if _elapsed_min >= 1:
            _elapsed_str = f" · Completed in {_elapsed_min} minute{'s' if _elapsed_min != 1 else ''}"
    st.markdown(
        f'<div class="sa-meta">Prepared for {company} · {_audit_date}{_elapsed_str} · Confidential</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"# {company}. Structural Audit.")
    if r["overall"] is None:
        st.warning("Not enough of the audit was completed to generate a score. Return and answer more questions.")
        if st.button("Return to the audit"):
            st.session_state.dim_idx = 0
            go("dim")
        return
    band_id, band_label, band_narrative = r["band"]
    # Band-specific accent color for dynamic theming across results
    _BAND_ACCENT = {
        "critical": "#7A2E20",
        "fragile": "#B8872E",
        "functional": "#5A6B3F",
        "strong": "#2E6B5A",
        "durable": "#14223D",
    }
    _band_color = _BAND_ACCENT.get(band_id, "var(--accent)")
    st.markdown(f'<div class="sa-band sa-band--{band_id}">{band_label}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sa-card sa-score-hero"><div class="label">Overall structural score</div>'
        f'<div class="val" id="sa-score-val">0.0<span class="ten">/ 100</span></div></div>',
        unsafe_allow_html=True,
    )
    # Animated count-up on score reveal
    _components.html(
        f"""<script>
        (function(){{
          try {{
            var pd = window.parent.document;
            var el = pd.getElementById('sa-score-val');
            var target = {r["overall"]:.1f};
            if (!el || el._saAnimatedFor === target) return;
            el._saAnimatedFor = target;
            var span = el.querySelector('.ten');
            var dur = 1400;
            var start = performance.now();
            function tick(now) {{
              var t = Math.min((now - start) / dur, 1);
              t = 1 - Math.pow(1 - t, 3);
              var v = (t * target).toFixed(1);
              el.textContent = v;
              if (span) el.appendChild(span);
              if (t < 1) requestAnimationFrame(tick);
            }}
            requestAnimationFrame(tick);
          }} catch(e) {{}}
        }})();
        </script>""",
        height=0,
    )
    # Percentile ranking language
    _BAND_PERCENTILE = {
        "critical": "typically in the bottom 15% of businesses at this revenue band",
        "fragile": "typically in the lower third of businesses at this revenue band",
        "functional": "consistent with the middle of the pack at this revenue band",
        "strong": "consistent with the top quarter of businesses at this revenue band",
        "durable": "consistent with the top 10% of businesses at this revenue band",
    }
    _pctl_text = _BAND_PERCENTILE.get(band_id, "")
    if _pctl_text:
        st.markdown(
            f'<p style="font-size:1.05rem;color:var(--ink);margin:0.5rem 0 0.8rem">'
            f'This places {company} <strong>{_pctl_text}</strong>.</p>',
            unsafe_allow_html=True,
        )
    if band_narrative:
        st.markdown(f"<p>{band_narrative}</p>", unsafe_allow_html=True)
    # Distance to next band (motivational nudge)
    if band_id != "durable":
        _NEXT_BAND = {"critical": ("Fragile", 41), "fragile": ("Functional", 61),
                      "functional": ("Strong", 76), "strong": ("Durable", 91)}
        _nb = _NEXT_BAND.get(band_id)
        if _nb:
            _gap = _nb[1] - r["overall"]
            st.markdown(
                f'<p style="font-size:0.95rem;color:var(--accent);margin:0 0 0.8rem">'
                f'{_gap:.1f} points from {_nb[0]}.</p>',
                unsafe_allow_html=True,
            )

    # Methodology explainer
    with st.expander("How this was scored"):
        st.markdown(
            "The audit scores fifty questions across six weighted dimensions: "
            "Personnel & Org, Accounting & Finance, Software Stack, AI Readiness, "
            "Sales & Marketing, and Operations & Process. Qualitative questions "
            "(Likert scale and yes/no) are scored directly. Quantitative questions "
            "(metrics like turnover rate, days to close, CAC) are scored against "
            "industry benchmarks at the 25th, 50th, and 75th percentile for your selected industry."
        )
        st.markdown(
            "Each dimension requires at least 60% of its question weight to be answered "
            "before it receives a score. Dimensions below that threshold are excluded from "
            "the overall weighted average and marked as Insufficient Data. "
            "The overall score is the weighted average of all scored dimensions, on a 0 to 100 scale. "
            "Risks are the answered items with the lowest scores relative to their weight. "
            "Opportunities are items that are partially in place but have room to improve."
        )
        st.markdown(
            "**Band thresholds:** "
            "Critical (0–40), "
            "Fragile (41–60), "
            "Functional (61–75), "
            "Strong (76–90), "
            "Durable (91–100)."
        )
        st.markdown(
            f'<p style="font-size:0.82rem;color:var(--muted);margin-top:8px">Rubric version {RUBRIC_VERSION}</p>',
            unsafe_allow_html=True,
        )

    # Dynamic executive summary
    scored_dims = [d for d in r["dimensions"] if d["score"] is not None]
    if scored_dims:
        weakest = min(scored_dims, key=lambda d: d["score"])
        strongest = max(scored_dims, key=lambda d: d["score"])
        top_risk_text = ""
        if r["risks"]:
            top_risk_q = r["risks"][0][0]
            top_risk_dim = r["risks"][0][1]
            top_risk_text = (
                f" The single highest-weighted risk sits in {top_risk_dim['name']}: "
                f"<em>&ldquo;{top_risk_q['text']}&rdquo;</em>"
            )
        # The 90-day plan starts from top risks, not necessarily the weakest dimension
        _first_plan_dim = r["risks"][0][1]["name"] if r["risks"] else weakest["name"]
        exec_summary = (
            f"{company} scored {r['overall']:.1f}, placing it in the <strong>{band_label}</strong> band. "
            f"The weakest dimension is {weakest['name']} at {weakest['score']:.1f}. "
            f"The strongest is {strongest['name']} at {strongest['score']:.1f}."
            f"{top_risk_text}"
            f" A 90-day focus plan follows below, starting with {_first_plan_dim}."
        )
        st.markdown(
            f'<div style="border-left:3px solid {_band_color};padding:14px 18px;margin:1.5rem 0;'
            f'background:#FBF8F1;font-size:1.02rem;line-height:1.55;color:var(--ink-2)">'
            f'{exec_summary}</div>',
            unsafe_allow_html=True,
        )

    # --- Pre-compute which optional sections will render ---
    _has_opps = bool(r["opportunities"])
    _has_plan = any(q.get("recommendation") for q, _, _ in r["risks"][:3]) or (
        _has_opps and any(q.get("recommendation") for q, _, _ in r["opportunities"])
    )

    # --- Table of contents (rendered via component iframe so JS works) ---
    _toc_links = [
        '<a href="#" data-target="sa-dimensions">Dimensions</a>',
        '<a href="#" data-target="sa-risks">Risks</a>',
    ]
    if _has_opps:
        _toc_links.append('<a href="#" data-target="sa-opportunities">Opportunities</a>')
    if _has_plan:
        _toc_links.append('<a href="#" data-target="sa-plan">90-Day Plan</a>')
    _toc_links += [
        '<a href="#" data-target="sa-followup">Get the follow-up</a>',
        '<a href="#" data-target="sa-next">Next step</a>',
        '<a href="#" data-target="sa-share">Share</a>',
    ]
    _toc_html = "\n          ".join(_toc_links)
    _components.html(
        f"""
        <style>
        body {{ margin:0; padding:0; background:transparent; }}
        .toc {{ display:flex; flex-wrap:wrap; gap:6px 18px; font-family:"Inter",system-ui,sans-serif; }}
        .toc a {{ font-size:14px; color:#8B6A3F; text-decoration:none; letter-spacing:0.02em; }}
        .toc a:hover {{ text-decoration:underline; }}
        @media(max-width:500px){{
          .toc {{ gap:5px 10px; }}
          .toc a {{ font-size:12px; }}
        }}
        </style>
        <div class="toc">
          {_toc_html}
        </div>
        <script>
        (function(){{
          document.querySelectorAll('.toc a').forEach(function(a){{
            a.addEventListener('click', function(e){{
              e.preventDefault();
              var id = this.getAttribute('data-target');
              try {{
                var el = window.parent.document.getElementById(id);
                if (el) el.scrollIntoView({{behavior:'smooth', block:'start'}});
              }} catch(err) {{}}
            }});
          }});
          try {{
            var fr = window.frameElement;
            if (fr) {{
              // Auto-size iframe to content height (handles link wrapping on mobile)
              var h = document.body.scrollHeight;
              if (h > 0) fr.style.height = h + 'px';
              var wrap = fr.closest('.element-container') || fr.parentElement;
              if (wrap) {{
                wrap.style.position = 'sticky';
                wrap.style.top = '0';
                wrap.style.zIndex = '999';
                var _bg = getComputedStyle(pd.documentElement).getPropertyValue('--bone').trim() || '#F4EFE6';
                wrap.style.background = _bg;
                wrap.style.paddingTop = '4px';
                wrap.style.paddingBottom = '4px';
                wrap.style.borderBottom = '1px solid #E8E0D0';
              }}
            }}
          }} catch(e) {{}}
        }})();
        </script>
        """,
        height=56,
    )
    # --- Radar chart ---
    st.markdown(
        '<p style="font-size:0.85rem;color:var(--muted);margin:0.8rem 0 0.2rem">Larger shape = more structural strength. Uneven shapes reveal where to focus.</p>',
        unsafe_allow_html=True,
    )
    scored_for_radar = [d for d in r["dimensions"] if d["score"] is not None]
    if len(scored_for_radar) >= 3:
        _n = len(scored_for_radar)
        _cx, _cy, _R = 200, 200, 150
        _angle_offset = -math.pi / 2  # start at top

        def _polar(i, pct):
            a = _angle_offset + 2 * math.pi * i / _n
            r = _R * pct / 100.0
            return _cx + r * math.cos(a), _cy + r * math.sin(a)

        # Grid lines at 25, 50, 75, 100
        _grid_svg = ""
        for pct in [25, 50, 75, 100]:
            pts = " ".join(f"{_polar(i, pct)[0]:.1f},{_polar(i, pct)[1]:.1f}" for i in range(_n))
            _grid_svg += f'<polygon points="{pts}" fill="none" stroke="#D9CFBC" stroke-width="1"/>\n'

        # Axis lines
        _axis_svg = ""
        for i in range(_n):
            x, y = _polar(i, 100)
            _axis_svg += f'<line x1="{_cx}" y1="{_cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#D9CFBC" stroke-width="1"/>\n'

        # Data polygon
        _data_pts = " ".join(f"{_polar(i, d['score'])[0]:.1f},{_polar(i, d['score'])[1]:.1f}" for i, d in enumerate(scored_for_radar))
        _data_svg = f'<polygon points="{_data_pts}" fill="rgba(139,106,63,0.18)" stroke="#8B6A3F" stroke-width="2"/>\n'

        # Data dots + labels
        _dots_svg = ""
        _labels_svg = ""
        for i, d in enumerate(scored_for_radar):
            x, y = _polar(i, d["score"])
            _dots_svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#8B6A3F"/>\n'
            lx, ly = _polar(i, 115)
            # Compute text-anchor based on position
            a = _angle_offset + 2 * math.pi * i / _n
            if abs(math.cos(a)) < 0.15:
                anchor = "middle"
            elif math.cos(a) > 0:
                anchor = "start"
            else:
                anchor = "end"
            # Short name
            short = d["name"].replace(" & ", " &amp; ")
            _labels_svg += (
                f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
                f'font-family="Inter,sans-serif" font-size="11" fill="#14223D">'
                f'{short} <tspan font-weight="600">({d["score"]:.0f})</tspan></text>\n'
            )

        _radar_html = f"""
        <style>
          body {{ margin:0; padding:0; background:transparent; }}
          .radar-wrap {{ text-align:center; margin:1rem 0 0.5rem; }}
          .radar-wrap svg {{ max-width:440px; width:100%; }}
          @media(max-width:500px){{
            .radar-wrap svg {{ max-width:100%; }}
            .radar-wrap svg text {{ font-size:9px !important; }}
          }}
        </style>
        <div class="radar-wrap">
          <svg viewBox="-60 -15 520 430" width="100%" xmlns="http://www.w3.org/2000/svg">
            {_grid_svg}{_axis_svg}{_data_svg}{_dots_svg}{_labels_svg}
          </svg>
        </div>
        """
        _components.html(
            f'<div style="background:transparent;margin:0;padding:0">{_radar_html}</div>'
            '<script>try{var f=window.frameElement;if(f)f.classList.add("sa-radar-iframe")}catch(e){}</script>',
            height=380,
        )

    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)

    # Dimensions
    st.markdown('<div id="sa-dimensions"></div>', unsafe_allow_html=True)
    st.markdown("## Dimension scores")
    st.markdown(
        '<p class="sa-lede" style="font-size:1.05rem">Any dimension with insufficient answered weight is excluded from the overall score and marked as such.</p>',
        unsafe_allow_html=True,
    )
    dim_id_to_idx = {dim["id"]: i for i, dim in enumerate(DIMENSIONS)}
    industry = st.session_state.industry
    answers = st.session_state.answers
    for d in r["dimensions"]:
        # Compute benchmark comparison for numeric questions in this dimension
        dim_def = DIMENSIONS[dim_id_to_idx[d["id"]]]
        above, at_or_below, benchmarked_total = 0, 0, 0
        for q in dim_def["questions"]:
            if q["type"] in ("number", "percent"):
                bench = BENCHMARKS.get((industry, q["id"]))
                ans = answers.get(q["id"])
                if bench and ans not in (None, "N/A", ""):
                    try:
                        val = float(ans)
                        benchmarked_total += 1
                        lower = q.get("lower_is_better", False)
                        if (lower and val <= bench["p50"]) or (not lower and val >= bench["p50"]):
                            above += 1
                        else:
                            at_or_below += 1
                    except (ValueError, TypeError):
                        pass
        bench_line = ""
        if benchmarked_total > 0:
            if above == benchmarked_total:
                bench_line = f'<div style="font-size:0.82rem;color:var(--accent);margin-top:4px">{above} of {benchmarked_total} benchmarked metrics at or above industry median</div>'
            elif at_or_below == benchmarked_total:
                bench_line = f'<div style="font-size:0.82rem;color:var(--warn);margin-top:4px">{at_or_below} of {benchmarked_total} benchmarked metrics below industry median</div>'
            else:
                bench_line = f'<div style="font-size:0.82rem;color:var(--muted);margin-top:4px">{above} of {benchmarked_total} benchmarked metrics at or above industry median</div>'

        jump_idx = dim_id_to_idx.get(d["id"])
        if d["score"] is None:
            st.markdown(
                f'<div class="sa-card"><div class="label">{d["name"]}</div>'
                f'<div class="val" style="color:var(--muted)">{INSUFFICIENT_DATA_LABEL}</div>'
                f'<div style="font-size:0.82rem;color:var(--muted);margin-top:6px">'
                f'This dimension needs at least 60% of questions answered to produce a score.</div></div>',
                unsafe_allow_html=True,
            )
            if jump_idx is not None:
                if st.button(f"Complete {d['name']} questions", key=f"jump_{d['id']}"):
                    st.session_state.dim_idx = jump_idx
                    go("dim")
        else:
            _dim_band = _band_for_score(d["score"])
            _dim_band_label = _dim_band[1] if _dim_band else ""
            # Heat-strip: one cell per question colored by individual score
            _heat_cells = []
            for q in dim_def["questions"]:
                ans = answers.get(q["id"])
                qs, flagged = score_question(q, ans, industry)
                if not flagged or qs is None:
                    _heat_cells.append('<span style="display:inline-block;width:100%;height:6px;background:var(--hair)"></span>')
                elif qs >= 0.75:
                    _heat_cells.append('<span style="display:inline-block;width:100%;height:6px;background:#5A6B3F"></span>')
                elif qs >= 0.4:
                    _heat_cells.append('<span style="display:inline-block;width:100%;height:6px;background:#B8872E"></span>')
                else:
                    _heat_cells.append('<span style="display:inline-block;width:100%;height:6px;background:#7A2E20"></span>')
            _n_cells = len(_heat_cells)
            _heat_strip = (
                f'<div style="display:grid;grid-template-columns:repeat({_n_cells},1fr);gap:2px;margin:6px 0 4px">'
                + "".join(_heat_cells)
                + '</div>'
                + '<div style="font-size:0.72rem;color:var(--muted);margin-bottom:2px">Per-question breakdown: '
                + '<span style="color:#5A6B3F">strong</span> · '
                + '<span style="color:#B8872E">partial</span> · '
                + '<span style="color:#7A2E20">gap</span> · '
                + '<span style="color:var(--hair)">skipped</span></div>'
            )
            st.markdown(
                f'<div class="sa-card"><div class="label">{d["name"]}</div>'
                f'<div class="val">{d["score"]:.1f}<span class="ten">/ 100</span>'
                f'<span style="font-size:0.7rem;font-weight:400;color:var(--muted);margin-left:8px;letter-spacing:0.03em">{_dim_band_label}</span></div>'
                f'{pct_bar(d["score"])}'
                f'{_heat_strip}'
                f'{bench_line}</div>',
                unsafe_allow_html=True,
            )
            if jump_idx is not None:
                if st.button(f"Edit {d['name']} answers", key=f"edit_{d['id']}"):
                    st.session_state.dim_idx = jump_idx
                    go("dim")

    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)

    # Risks
    st.markdown('<div id="sa-risks"></div>', unsafe_allow_html=True)
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
        st.markdown('<div id="sa-opportunities"></div>', unsafe_allow_html=True)
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

    # --- 90-Day Focus Plan ---
    _plan_items = []
    for q, dim, score in r["risks"][:3]:
        rec = q.get("recommendation", "")
        if rec:
            _plan_items.append({"dim": dim["name"], "rec": rec, "q": q["text"]})
    # Fill remaining slots from opportunities if fewer than 3 risks
    if len(_plan_items) < 3 and r["opportunities"]:
        for q, dim, score in r["opportunities"]:
            rec = q.get("recommendation", "")
            if rec and len(_plan_items) < 3:
                _plan_items.append({"dim": dim["name"], "rec": rec, "q": q["text"]})

    if _plan_items:
        st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
        st.markdown('<div id="sa-plan"></div>', unsafe_allow_html=True)
        st.markdown("## 90-Day Focus Plan")
        st.markdown(
            '<p class="sa-lede" style="font-size:1.05rem">'
            'Three moves, sequenced. The first is the one that unblocks the others.</p>',
            unsafe_allow_html=True,
        )
        _periods = ["Days 1–30", "Days 31–60", "Days 61–90"]
        _period_labels = ["Stabilize", "Build", "Compound"]
        for i, item in enumerate(_plan_items):
            period = _periods[i] if i < len(_periods) else f"Days {i*30+1}–{(i+1)*30}"
            plabel = _period_labels[i] if i < len(_period_labels) else ""
            st.markdown(
                f'<div class="sa-card" style="border-left:3px solid {_band_color}">'
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px">'
                f'<span style="font-family:Fraunces,serif;font-size:1.1rem;color:var(--ink)">{period}</span>'
                f'<span style="font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:{_band_color}">{plabel}</span></div>'
                f'<div style="font-size:0.82rem;color:var(--muted);margin-bottom:4px">{item["dim"]}</div>'
                f'<div style="font-size:0.97rem;color:var(--ink-2)">{item["rec"]}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<p style="font-family:Fraunces,Georgia,serif;font-size:1.05rem;color:var(--ink);'
            'line-height:1.45;margin:1.5rem 0 0.5rem;font-style:italic">'
            'This is the plan. The call is where we pressure-test it.</p>',
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)

    # --- Email capture (lighter ask, higher conversion) ---
    st.markdown('<div id="sa-followup"></div>', unsafe_allow_html=True)
    st.markdown("## Get the follow-up")
    st.markdown(
        "Leave an email and we will send three short emails over the next ten days. "
        "**Email 1** (day 2): what to do this week with your audit, which dimension to focus first, and how to assign the first fix. "
        "**Email 2** (day 5): how to read the risks and opportunities section and turn it into a meeting agenda. "
        "**Email 3** (day 10): when the audit surfaces something bigger than a checklist can handle. That is it."
    )
    st.markdown(
        '<p style="font-size:0.88rem;color:var(--accent);margin:0 0 8px">'
        'Most companies that take the audit never act on it. The follow-up is designed to change that.</p>',
        unsafe_allow_html=True,
    )
    _ec = st.session_state.get("email_captured")
    if not _ec:
        email_val = st.text_input("Email address", key="capture_email", placeholder="founder@yourcompany.com")
        if st.button("Send me the action plan", key="btn_capture"):
            if email_val and "@" in email_val and "." in email_val:
                _capture_email(email_val, company, band_label, r["overall"])
                st.rerun()
            else:
                st.warning("Please enter a valid email address.")
    elif _ec == "soft_fail":
        st.info("We noted your request. If you do not hear from us within 24 hours, reach out directly.")
    else:
        st.markdown(
            '<div style="background:#E8EAE0;border:1px solid #5A6B3F;padding:16px 20px;margin:0.5rem 0">'
            '<p style="color:#4A5A32;font-weight:600;margin:0 0 4px;font-size:0.95rem">Follow-up queued</p>'
            '<p style="color:#4A5A32;margin:0;font-size:0.9rem">'
            'Check your inbox over the next few days. You will receive a short action plan for this week '
            'and a note on what to do if the audit surfaces something bigger than a checklist can fix.</p></div>',
            unsafe_allow_html=True,
        )

    # --- Call CTA (heavier ask — comes second, band-specific copy) ---
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    st.markdown('<div id="sa-next"></div>', unsafe_allow_html=True)
    st.markdown("## What to do with this")
    _CTA_COPY = {
        "critical": (
            "A score in this range means the business is carrying structural risk that compounds "
            "with time, not resolves with it. The next useful step is a read-out call. Thirty minutes. "
            "The audit in front of us. We will identify which of the top risks is load-bearing "
            "and what a realistic 90-day stabilization looks like."
        ),
        "fragile": (
            "The audit surfaced real gaps, but the business is functioning. The risk is that "
            "these gaps stay invisible until something forces the issue. The next useful step is a "
            "read-out call. Thirty minutes. The audit in front of us. A pressure-test of the top "
            "risks and the one move that would actually change the score by next quarter."
        ),
        "functional": (
            "The audit is honest but it is not a plan. A Functional score means the foundation is real "
            "but the remaining gaps are load-bearing. The next useful step is a read-out call. Thirty "
            "minutes. The audit in front of us. We will sequence the two or three moves that would "
            "push the business into durable territory."
        ),
        "strong": (
            "At this level, the remaining gaps are refinements, not emergencies. The leverage is in "
            "compounding what already works. The next useful step is a read-out call. Thirty minutes. "
            "The audit in front of us. We will identify which strengths to protect and which "
            "refinements have the highest marginal return."
        ),
        "durable": (
            "A Durable score is rare. The business is structurally sound and the question shifts from "
            "fixing weaknesses to scaling on strength. If you are considering a transaction, preparing "
            "for a capital event, or expanding into a new vertical, a read-out call sharpens the picture. "
            "Thirty minutes. The audit in front of us."
        ),
    }
    _cta_text = _CTA_COPY.get(band_id, _CTA_COPY["functional"])
    st.markdown(_cta_text)
    cal_url = CTA["lead_magnet"]["primary_url"]
    _CTA_LABELS = {
        "critical": "Book a 30-min structural review",
        "fragile": "Book a 30-min structural review",
        "functional": "Book a 30-min structural review",
        "strong": "Book a 30-min structural review",
        "durable": "Book a 30-min read-out call",
    }
    st.link_button(_CTA_LABELS.get(band_id, "Book a 30-min structural review"), cal_url, use_container_width=False)
    st.markdown(
        '<p style="font-size:0.88rem;color:var(--muted);margin-top:0.8rem">'
        'Not ready for a call? <a href="https://structuraladvantage.substack.com/" '
        'style="color:var(--accent)">Subscribe to Structural Advantage</a>, '
        'the newsletter behind this audit.</p>',
        unsafe_allow_html=True,
    )

    # --- Share summary (plain text for forwarding to team) ---
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    st.markdown('<div id="sa-share"></div>', unsafe_allow_html=True)
    st.markdown("### Share with your team")
    # Determine the weakest dimension name for the prompt
    _weakest_name = weakest["name"] if scored_dims else "the weakest dimension"
    st.markdown(
        f"If you have a leadership team, send this to whoever owns {_weakest_name}. "
        "If it is just you, save it. The 90-day plan is what matters. "
        "Copy the summary below and forward it. The audit is more useful when the people who need to act on it can see it."
    )
    _industry = st.session_state.industry
    _summary_lines = [
        f"STRUCTURAL AUDIT — {company} ({_audit_date})",
        f"Industry: {_industry}" if _industry else "",
        f"Overall score: {r['overall']:.1f} / 100 ({band_label})",
    ]
    _summary_lines = [l for l in _summary_lines if l]  # drop empty industry line
    if band_narrative:
        _summary_lines.append(f"\n{band_narrative}")
    _summary_lines.append("")
    for d in r["dimensions"]:
        if d["score"] is not None:
            _db = _band_for_score(d["score"])
            _db_label = f" ({_db[1]})" if _db else ""
            _summary_lines.append(f"  {d['name']}: {d['score']:.1f}{_db_label}")
        else:
            _summary_lines.append(f"  {d['name']}: Insufficient Data")
    if r["risks"]:
        _summary_lines.append("")
        _summary_lines.append("TOP RISKS:")
        for q, dim, score in r["risks"][:3]:
            _summary_lines.append(f"  [{dim['name']}] {q['text']}")
    if _plan_items:
        _summary_lines.append("")
        _summary_lines.append("90-DAY FOCUS PLAN:")
        _periods = ["Days 1-30", "Days 31-60", "Days 61-90"]
        for i, item in enumerate(_plan_items):
            period = _periods[i] if i < len(_periods) else f"Days {i*30+1}-{(i+1)*30}"
            _summary_lines.append(f"  {period} ({item['dim']}): {item['rec']}")
    _summary_lines.append("")
    _summary_lines.append(f"Book a 30-min structural review: https://calendly.com/gkholdingsllcva/advisory-intro")
    _summary_lines.append(f"Take the audit: https://structural-audit.streamlit.app/")
    _share_text = "\n".join(_summary_lines)
    # Escape for safe embedding in JS — prevent injection from company names
    _safe_share = json.dumps(_share_text)
    _components.html(
        f"""
        <style>
        body {{ margin:0; padding:0; background:transparent; }}
        button {{
          background:#14223D; color:#F4EFE6; border:none; padding:8px 18px;
          font-family:"Inter",system-ui,sans-serif; font-size:13px; font-weight:500;
          cursor:pointer; letter-spacing:0.02em;
        }}
        button:hover {{ background:#2A3758; }}
        .ok {{ color:#8B6A3F; font-size:12px; margin-left:8px; font-family:"Inter",system-ui,sans-serif; }}
        </style>
        <button onclick="navigator.clipboard.writeText({_safe_share}).then(function(){{document.getElementById('share_ok').textContent='Copied. Paste into an email or message.'}})">
          Copy summary to clipboard
        </button><span id="share_ok" class="ok"></span>
        """,
        height=42,
    )

    # --- Print / Save as PDF ---
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    st.markdown("### Print or save as PDF")
    st.markdown(
        "Use your browser's print dialog to save a clean copy. "
        "Works best from desktop."
    )
    _components.html(
        """
        <style>
        body { margin:0; padding:0; background:transparent; }
        button {
          background:#14223D; color:#F4EFE6; border:none; padding:8px 18px;
          font-family:"Inter",system-ui,sans-serif; font-size:13px; font-weight:500;
          cursor:pointer; letter-spacing:0.02em;
        }
        button:hover { background:#2A3758; }
        </style>
        <button onclick="try{window.parent.print()}catch(e){window.top.print()}">
          Print this page
        </button>
        <script>
        // Inject print-friendly styles into the parent document
        (function(){
          try {
            var pw = window.parent;
            var pd = pw.document;
            if (!pd._saPrintCSS) {
              pd._saPrintCSS = true;
              var s = pd.createElement('style');
              s.textContent = [
                '@media print {',
                '  [data-testid="stSidebarCollapsedControl"], #MainMenu, footer,',
                '  header[data-testid="stHeader"], [data-testid="manage-app-button"],',
                '  .stAppDeployButton, [class*="viewerBadge"], [class*="StatusWidget"],',
                '  [class*="stStatusWidget"], [data-testid="StatusWidget"],',
                '  [class*="stAppStatus"] { display:none!important; }',
                '  .stApp, html, body, [data-testid="stAppViewContainer"] {',
                '    background: white !important;',
                '  }',
                '  section.main > div.block-container {',
                '    max-width: 100% !important;',
                '    padding: 0 !important;',
                '  }',
                '  iframe:not(.sa-radar-iframe) { display:none !important; }',
                '  div.stButton, div.stLinkButton { display:none !important; }',
                '  [data-testid="stExpander"].sa-print-hide { display:none !important; }',
                '  [data-testid="stExpander"] details[open] > summary { display:none !important; }',
                '  .sa-print-footer { display:block !important; }',
                '}'
              ].join('\\n');
              pd.head.appendChild(s);
              // Before print: expand methodology, hide interactive expanders
              pw.addEventListener('beforeprint', function() {
                var exps = pd.querySelectorAll('[data-testid="stExpander"]');
                exps.forEach(function(exp) {
                  var summary = exp.querySelector('summary span, details summary');
                  var text = (exp.textContent || '').substring(0, 80).toLowerCase();
                  if (text.indexOf('how this was scored') !== -1) {
                    var details = exp.querySelector('details');
                    if (details) details.setAttribute('open', '');
                  } else {
                    exp.classList.add('sa-print-hide');
                  }
                });
              });
              pw.addEventListener('afterprint', function() {
                pd.querySelectorAll('.sa-print-hide').forEach(function(el) {
                  el.classList.remove('sa-print-hide');
                });
              });
            }
          } catch(e) {}
        })();
        </script>
        """,
        height=42,
    )

    # --- Index cross-sell ---
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    st.markdown("### If you have not taken the Index yet")
    st.markdown(
        "The Structural Advantage Index is the personal companion to this audit. Eleven minutes. An operator archetype. "
        "The shape you bring to the work, named. Most operators find the two read differently when held side by side. "
        "[Open the Index &rarr;](https://structuraladvantageindex.netlify.app/)"
    )

    # --- Save code (visible, not buried) ---
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    st.markdown("### Save your results")
    st.markdown("Copy your audit code below. Use it to resume from any device, or paste it into the comparison tool on a future audit to track your progress.")
    _results_code = _encode_state()
    st.code(_results_code, language=None)
    _components.html(
        f"""
        <style>
        body {{ margin:0; padding:0; background:transparent; }}
        button {{
          background:#14223D; color:#F4EFE6; border:none; padding:8px 18px;
          font-family:"Inter",system-ui,sans-serif; font-size:13px; font-weight:500;
          cursor:pointer; letter-spacing:0.02em;
        }}
        button:hover {{ background:#2A3758; }}
        .ok {{ color:#8B6A3F; font-size:12px; margin-left:8px; font-family:"Inter",system-ui,sans-serif; }}
        </style>
        <button onclick="navigator.clipboard.writeText('{_results_code}').then(function(){{document.getElementById('rcp').textContent='Copied.'}})">
          Copy to clipboard
        </button><span id="rcp" class="ok"></span>
        """,
        height=42,
    )

    # --- Historical comparison ---
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    st.markdown("### Compare to a previous audit")
    with st.expander("Paste a save code from a previous audit"):
        prev_code = st.text_input(
            "Previous audit save code",
            key="prev_audit_code",
            placeholder="Paste your previous save code here",
        )
        if st.button("Compare", key="btn_compare") and prev_code:
            # Temporarily swap state to compute previous results
            current_answers = st.session_state.answers.copy()
            current_industry = st.session_state.industry
            try:
                padded = prev_code.strip() + "=" * (4 - len(prev_code.strip()) % 4)
                compressed = base64.urlsafe_b64decode(padded)
                raw = zlib.decompress(compressed)
                prev_payload = json.loads(raw)
                # Temporarily set previous answers to compute results
                st.session_state.answers = prev_payload.get("a", {})
                st.session_state.industry = prev_payload.get("i", current_industry)
                prev_r = compute_results()
                # Restore current
                st.session_state.answers = current_answers
                st.session_state.industry = current_industry
                if prev_r["overall"] is not None and r["overall"] is not None:
                    delta = r["overall"] - prev_r["overall"]
                    direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
                    color = "var(--accent)" if delta > 0 else "var(--warn)" if delta < 0 else "var(--muted)"
                    arrow = "+" if delta > 0 else ""
                    st.markdown(
                        f'<div class="sa-card"><div class="label">Overall change</div>'
                        f'<div class="val" style="color:{color}">{arrow}{delta:.1f}</div>'
                        f'<div style="font-size:0.9rem;color:var(--muted);margin-top:4px">'
                        f'Previous: {prev_r["overall"]:.1f} &rarr; Current: {r["overall"]:.1f}</div></div>',
                        unsafe_allow_html=True,
                    )
                    # Per-dimension deltas
                    prev_dim_scores = {d["id"]: d["score"] for d in prev_r["dimensions"]}
                    for d in r["dimensions"]:
                        prev_score = prev_dim_scores.get(d["id"])
                        if d["score"] is not None and prev_score is not None:
                            dd = d["score"] - prev_score
                            darrow = "+" if dd > 0 else ""
                            dcolor = "var(--accent)" if dd > 0 else "var(--warn)" if dd < 0 else "var(--muted)"
                            st.markdown(
                                f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
                                f'border-bottom:1px solid var(--hair);font-size:0.95rem">'
                                f'<span>{d["name"]}</span>'
                                f'<span style="color:{dcolor};font-weight:500">{darrow}{dd:.1f}</span></div>',
                                unsafe_allow_html=True,
                            )
                else:
                    st.warning("Could not compare. The previous audit may not have enough data.")
            except Exception:
                st.error("Invalid save code. Please check and try again.")
                st.session_state.answers = current_answers
                st.session_state.industry = current_industry

    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    _components.html(
        """
        <div style="text-align:center;margin:0.5rem 0">
          <a href="#" style="font-family:Inter,sans-serif;font-size:13px;color:#8B6A3F;text-decoration:none;letter-spacing:0.04em"
             onclick="event.preventDefault();try{window.parent.document.querySelector('section.stMain').scrollTo({top:0,behavior:'smooth'})}catch(e){}">
             Back to top
          </a>
        </div>
        """,
        height=32,
    )
    # Print-only attribution footer (hidden on screen, visible on print)
    st.markdown(
        '<div class="sa-print-footer" style="display:none;margin-top:2rem;padding-top:1rem;'
        'border-top:1px solid #D9CFBC;font-size:0.8rem;color:#6B6659;text-align:center">'
        'The Structural Audit &middot; structural-audit.streamlit.app &middot; '
        'Graham Kindermann &middot; GLK Holdings LLC</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    if st.button("Start a new audit"):
        st.session_state._confirm_new = True
        st.rerun()
    if st.session_state.get("_confirm_new"):
        st.warning("This will clear all your answers. Are you sure?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, start fresh", key="confirm_yes"):
                st.session_state._confirm_new = False
                for k in ["step", "company", "industry", "revenue", "respondent", "answers", "dim_idx",
                          "headcount", "ebitda_margin", "years_in_op", "owner_hours",
                          "audit_intent", "email_captured"]:
                    if k in st.session_state:
                        del st.session_state[k]
                _init()
                # Clear localStorage so stale resume prompt doesn't appear on return
                _components.html(
                    """<script>
                    try { window.parent.localStorage.removeItem('sa_audit_state'); } catch(e) {}
                    </script>""",
                    height=0,
                )
                st.rerun()
        with c2:
            if st.button("Cancel", key="confirm_no"):
                st.session_state._confirm_new = False
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
