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
import html as _html
import base64
import zlib
import time as _time
import datetime as _dt
import requests
import streamlit as st

from rubric import (
    DIMENSIONS,
    BANDS,
    BAND_NARRATIVE,
    BENCHMARKS,
    BENCHMARK_DISCLOSURE,
    INDUSTRY_LIST,
    MINIMUM_ANSWERED_FRACTION,
    INSUFFICIENT_DATA_LABEL,
    RISK_THRESHOLD,
    OPPORTUNITY_CEILING,
    YESNO_PARTIAL_SCORE,
    YESNO_PARTIAL_LABEL,
    YESNO_PARTIAL_HINT,
    BRAND,
    CTA,
    LINKS,
    RUBRIC_VERSION,
)

# ---------------------------------------------------------------------------
# Config lookup: env var -> Streamlit secrets -> local .env file.
# Never raises. Streamlit does not auto-load .env, and st.secrets throws when
# no secrets.toml exists, so both are wrapped.
# ---------------------------------------------------------------------------
def _get_conf(name: str, default: str = "") -> str:
    val = os.environ.get(name)
    if val:
        return val
    try:
        val = st.secrets.get(name, "")
        if val:
            return str(val)
    except Exception:
        pass
    try:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith(name + "="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return default

# ---------------------------------------------------------------------------
# Page chrome
# ---------------------------------------------------------------------------
_PAGE_TITLE = "The Structural Audit · A diagnostic of the company, not the founder"
_META_DESCRIPTION = (
    "Fifty questions across six dimensions. Weighted scoring, industry benchmarks, "
    "risk-ranked output. An honest tool for operators."
)
_FAVICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "favicon.png")

# Canonical URL for the app. Defaults to the custom domain; override with the
# AUDIT_CANONICAL_URL env var / secret (e.g. during staging). The OG image is
# served from Streamlit's static directory (enableStaticServing in config.toml).
_CANONICAL_URL = _get_conf("AUDIT_CANONICAL_URL", "https://audit.grahamkindermann.com").rstrip("/")
_OG_IMAGE_URL = f"{_CANONICAL_URL}/app/static/og-audit.png"
# When "1", a visitor landing on the legacy *.streamlit.app host is redirected
# to the canonical domain (top window). Leave "0" until DNS + hosting are live.
_REDIRECT_LEGACY = _get_conf("AUDIT_REDIRECT_LEGACY", "0") == "1"

# Outbound attribution. Every other property in the stack (Substack posts,
# grahamkindermann.com) stamps UTMs on links into the tools; the tools stamped
# nothing on the way back out, so tool-originated traffic was invisible.
def _utm(url: str, campaign: str, medium: str = "tool") -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}utm_source=audit&utm_medium={medium}&utm_campaign={campaign}"

st.set_page_config(
    page_title=_PAGE_TITLE,
    page_icon=_FAVICON if os.path.exists(_FAVICON) else "◆",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Social / OG meta tags (body-level; Streamlit does not allow <head> injection
# server-side). Non-JS scrapers see Streamlit's HTML shell regardless — full
# link-preview support requires migration off Community Cloud. This block
# covers regex-based scrapers; _install_head_meta() covers JS-rendering
# crawlers and enforces the clean tab title.
_SOCIAL_META = f"""
<meta name="description" content="{_META_DESCRIPTION}" />
<meta property="og:title" content="The Structural Audit: A diagnostic of the company, not the founder" />
<meta property="og:description" content="{_META_DESCRIPTION}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{_CANONICAL_URL}/" />
<meta property="og:site_name" content="Structural Advantage" />
<meta property="og:image" content="{_OG_IMAGE_URL}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="The Structural Audit" />
<meta name="twitter:description" content="{_META_DESCRIPTION}" />
<meta name="twitter:image" content="{_OG_IMAGE_URL}" />
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

section.stMain > div.block-container {
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

/* Every class below is applied to a raw <div>, which the `p, li, label` rule
   does not match, so without this they inherit Streamlit's theme font. The
   theme font is declared in .streamlit/config.toml; do not rely on it. More
   specific rules further down (.sa-card .val, .sa-risk .q) still win where
   Fraunces is wanted. */
.sa-meta, .sa-footnote, .sa-card, .sa-card .label, .sa-band,
.sa-risk, .sa-opp, .sa-risk .copy, .sa-opp .copy, .sa-rec,
.sa-group, .sa-heat-legend, .sa-bench-line, .sa-exec, .sa-lever {
  font-family: "Inter", system-ui, sans-serif;
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

/* Specificity matters here, not just !important. The generic body rule above
   includes `[data-testid="stMarkdownContainer"] p` (0,1,1), which OUTRANKS a
   bare `.sa-lede` (0,1,0) even when both carry !important — which is why the
   lede rendered as plain 1.02rem Inter everywhere. Matching the container
   explicitly takes it to (0,2,1). The doubled class keeps the rule winning if
   the element is ever rendered outside a markdown container. */
[data-testid="stMarkdownContainer"] p.sa-lede,
p.sa-lede.sa-lede,
.sa-lede {
  font-family: "Fraunces", Georgia, serif !important;
  font-weight: 300 !important;
  font-size: 1.3rem !important;
  line-height: 1.45 !important;
  color: var(--ink-2) !important;
  max-width: 620px;
  margin-bottom: 2rem;
}

[data-testid="stMarkdownContainer"] p.sa-footnote,
p.sa-footnote.sa-footnote,
.sa-footnote {
  font-family: "Inter", system-ui, sans-serif !important;
  font-size: 0.85rem !important;
  line-height: 1.5 !important;
  color: var(--muted) !important;
  font-style: italic;
}

/* Section heading inside a dimension. Was rendered in a fixed-height component
   iframe, which clipped descenders and sat 8px off the text column. */
.sa-group {
  font-family: "Fraunces", Georgia, serif !important;
  font-size: 1.05rem;
  font-weight: 400;
  color: var(--accent);
  letter-spacing: 0.01em;
  line-height: 1.5;
  margin: 1.6rem 0 0.2rem;
  padding: 0;
}

/* Per-question heat strip under each dimension score. */
.sa-heat {
  display: grid;
  gap: 2px;
  margin: 12px 0 6px;
}
.sa-heat span { display: block; height: 6px; }
.sa-heat-legend {
  font-size: 0.74rem;
  color: var(--muted);
  margin-bottom: 2px;
}
.sa-heat-legend b { font-weight: 500; }
.sa-heat-legend .k { color: var(--ink-2); }
.sa-bench-line { font-size: 0.82rem; margin-top: 6px; }

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
.sa-band--fragile  { background: #F5EDDF; border-color: #B8872E; color: #6B5220; }
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
  section.stMain > div.block-container {
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
  section.stMain > div.block-container {
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
  /* Larger tap targets for the likert/yesno radios on phones */
  div[data-testid="stRadio"] label {
    padding: 8px 12px 8px 2px !important;
    margin-right: 2px !important;
  }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

import streamlit.components.v1 as _components

# st.components.v1.html is deprecated ("will be removed after 2026-06-01") in
# favour of st.iframe. Every piece of this app's chrome — scroll reset, badge
# hiding, the radar, the table of contents, the copy and print buttons, the
# resume banner — runs through it, so its removal in any 1.x release would
# take all of that with it. Route through one wrapper that prefers st.iframe
# where it exists and falls back on older Streamlit.
# st.components.v1.html is deprecated ("will be removed after 2026-06-01") in
# favour of st.iframe, and every piece of this app's chrome runs through it:
# scroll reset, badge hiding, the radar, the table of contents, the copy and
# print buttons, the resume banner. It is NOT a drop-in swap, verified in a
# browser on Streamlit 1.62:
#   * st.iframe rejects height=0, and most frames here are invisible JS
#     carriers;
#   * Streamlit rewrites the iframe's className on every rerun under
#     st.iframe, so the radar's `classList.add("sa-radar-iframe")` does not
#     survive — and the print stylesheet keys off that class, so the chart
#     silently disappears from every printed report.
# requirements.txt pins below the release that would remove components.html.
# Migrating means re-homing the radar's print marker onto the parent element
# (which does survive, as the sticky table of contents proves) and giving the
# zero-height frames a real height. Do it as its own change, with a browser
# pass, not inside a content release.
def _frame(html: str, height=0):
    """Embed an HTML/JS fragment. height may be an int or "content"."""
    if height == "content":
        height = 340
    return _components.html(html, height=height)

def _install_head_meta():
    """Enforce a clean tab title (Streamlit Cloud appends a vendor suffix) and
    inject head-level meta for JS-rendering crawlers. Installs once per page
    load; the title observer re-asserts after every rerun."""
    _frame(
        f"""
        <script>
        (function(){{
          try {{
            // Walk to the TOPMOST same-origin window. On Streamlit Cloud the
            // app runs inside a hosting-shell iframe; the tab title and
            // favicon live on the shell document, one level above the app.
            var pw = window.parent;
            try {{
              while (pw !== pw.parent) {{ void pw.parent.document; pw = pw.parent; }}
            }} catch(e) {{}}
            var pd = pw.document;
            var appDoc = window.parent.document;
            var DESIRED = {json.dumps(_PAGE_TITLE)};
            if (!pw._saTitleInstalled) {{
              pw._saTitleInstalled = true;
              var enforce = function() {{
                if (pd.title !== DESIRED) pd.title = DESIRED;
                try {{
                  var srcIcon = appDoc.querySelector('link[rel*="icon"]');
                  if (srcIcon && srcIcon.href) {{
                    var cur = pd.querySelector('link[data-sa-favicon]');
                    if (!cur || cur.href !== srcIcon.href) {{
                      pd.querySelectorAll('link[rel*="icon"]').forEach(function(l) {{ l.remove(); }});
                      var l = pd.createElement('link');
                      l.rel = 'icon';
                      l.href = srcIcon.href;
                      l.setAttribute('data-sa-favicon', '1');
                      pd.head.appendChild(l);
                    }}
                  }}
                }} catch(e) {{}}
              }};
              enforce();
              var tEl = pd.querySelector('title');
              if (tEl) new MutationObserver(enforce).observe(tEl, {{ childList: true }});
              setInterval(enforce, 1500);
            }}
            if (!pw._saMetaInstalled) {{
              pw._saMetaInstalled = true;
              var metas = [
                {{ name: "description", content: {json.dumps(_META_DESCRIPTION)} }},
                {{ property: "og:title", content: DESIRED }},
                {{ property: "og:description", content: {json.dumps(_META_DESCRIPTION)} }},
                {{ property: "og:type", content: "website" }},
                {{ property: "og:url", content: {json.dumps(_CANONICAL_URL + "/")} }},
                {{ property: "og:image", content: {json.dumps(_OG_IMAGE_URL)} }},
                {{ name: "twitter:card", content: "summary_large_image" }},
                {{ name: "twitter:image", content: {json.dumps(_OG_IMAGE_URL)} }}
              ];
              metas.forEach(function(m) {{
                var el = pd.createElement('meta');
                Object.keys(m).forEach(function(k) {{ el.setAttribute(k, m[k]); }});
                pd.head.appendChild(el);
              }});
              var canonEl = pd.createElement('link');
              canonEl.rel = 'canonical';
              canonEl.href = {json.dumps(_CANONICAL_URL + "/")};
              pd.head.appendChild(canonEl);
            }}
            if ({str(_REDIRECT_LEGACY).lower()}) {{
              try {{
                var host = pw.location.hostname || "";
                var canonHost = {json.dumps(_CANONICAL_URL)}.replace(/^https?:\\/\\//, "");
                if (host.indexOf("streamlit.app") !== -1 && host !== canonHost) {{
                  // Preserve search + hash. A shared audit lives entirely in
                  // ?code=, so dropping the query discards the audit itself.
                  pw.location.replace(
                    {json.dumps(_CANONICAL_URL)} + "/" + (pw.location.search || "") + (pw.location.hash || "")
                  );
                }}
              }} catch(e) {{}}
            }}
          }} catch(e) {{}}
        }})();
        </script>
        """,
        height=0,
    )

_install_head_meta()

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
              '      if (t === "Back" || t.indexOf("No thanks") === 0 || t === "Start fresh") p.classList.add("sa-ghost");',
              '      if (t.indexOf("Edit ") === 0 || t.indexOf("Complete ") === 0 || t.indexOf("Skip this") === 0) p.classList.add("sa-link");',
              '    });',
              '    document.querySelectorAll("div[data-testid=stTextInput] input").forEach(function(inp){',
              '      var ph = inp.getAttribute("placeholder") || "";',
              '      if (ph.indexOf("e.g") === 0) inp.setAttribute("inputmode","decimal");',
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
    _frame(
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
        "ts": ss.get("_audit_start", None),
        "ec": ss.get("email_captured", None),
        "rv": RUBRIC_VERSION,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    compressed = zlib.compress(raw, 9)
    return base64.urlsafe_b64encode(compressed).decode().rstrip("=")

def _peek_state(code):
    """Decode a save code WITHOUT touching session state. Returns the payload
    dict, or None if the code is invalid or not a dict."""
    try:
        padded = code + "=" * (-len(code) % 4)
        payload = json.loads(zlib.decompress(base64.urlsafe_b64decode(padded)))
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None

def _decode_state(code):
    """Decode a resume code and populate session state. Returns True on success."""
    try:
        padded = code + "=" * (-len(code) % 4)
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
        _ts = payload.get("ts")
        if _ts is not None:
            ss["_audit_start"] = _ts
        _ec = payload.get("ec")
        if _ec is not None:
            ss["email_captured"] = _ec
        # Codes written before 1.1.0 carry no version. Questions can be
        # reworded between rubrics (sal_02 was reverse-scored until 1.1.0), so
        # an old code can score differently than it did when it was saved.
        ss["_saved_rubric_version"] = payload.get("rv", "1.0.x")
        return True
    except Exception:
        return False

def _save_to_localstorage():
    """Inject JS into the parent document that auto-saves the current state
    to localStorage. Runs silently on every screen render."""
    code = _encode_state()
    _safe_code = json.dumps(code)
    _frame(
        f"""
        <script>
        (function(){{
          try {{
            window.parent.localStorage.setItem('sa_audit_state', {_safe_code});
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
    # Once a session has navigated anywhere, never auto-offer the resume
    # banner on a return to the intro — it would reload the page and drop
    # the live session.
    st.session_state["_navigated"] = True
    st.rerun()

def advance_dim(skipped=False):
    ss = st.session_state
    if 0 <= ss.dim_idx < len(DIMENSIONS):
        dim = DIMENSIONS[ss.dim_idx]
        track(
            "dimension_completed",
            once_key=f"dim_done_{dim['id']}",
            dim=dim["id"],
            dim_index=ss.dim_idx + 1,
            skipped=skipped,
        )
    ss.dim_idx += 1
    if ss.dim_idx >= len(DIMENSIONS):
        # No interstitial gate. It closed with "No subscription. No upsell."
        # one screen before an email capture and a booking CTA, and anyone who
        # declined was asked again on the results page anyway. One ask, on the
        # results page, after the value has been delivered.
        ss.step = "results"
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
        '<span>The Structural Audit · A diagnostic of the company, not the founder</span></div>',
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
            _a = str(answer).strip().lower()
            if _a.startswith("y"):
                raw = 1.0
            elif _a.startswith(YESNO_PARTIAL_LABEL[0].lower()):
                # "Partly" — half credit. A business with the thing partly in
                # place is not the same as one that has never attempted it.
                raw = YESNO_PARTIAL_SCORE
            else:
                raw = 0.0
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
        "dimensions": [ { id, name, score 0..100 or None, weight, answered_weight } ],
        "risks": [ (q, dim, score, lever) ... ],
        "opportunities": [ (q, dim, score, lever) ... ],
        "skipped": [ dimension names excluded for insufficient data ],
      }

    `lever` is the number of points the OVERALL score would gain if that one
    question moved to full marks, holding everything else constant. Risks and
    opportunities are both ranked by it. Ranking by question weight alone
    (the pre-1.1.0 behaviour) ignored dimension weight, so the least-weighted
    dimension could supply the headline risk, the "biggest lever" callout and
    the first item of the 90-day plan.
    """
    ss = st.session_state
    industry = ss.industry
    answers = ss.answers
    dim_results = []
    scored_q = []   # (q, dim, score, dim_id) — lever filled in below
    for dim in DIMENSIONS:
        total_weight = 0.0
        answered_weight = 0.0
        weighted_sum = 0.0
        dim_scored = []
        for q in dim["questions"]:
            w = float(q.get("weight", 1.0))
            total_weight += w
            ans = answers.get(q["id"])
            score, flagged = score_question(q, ans, industry)
            if flagged and score is not None:
                answered_weight += w
                weighted_sum += w * score
                dim_scored.append((q, dim, score))
        if total_weight == 0 or answered_weight / total_weight < MINIMUM_ANSWERED_FRACTION:
            dim_results.append({
                "id": dim["id"], "name": dim["name"],
                "weight": dim["weight"], "score": None,
                "answered_weight": answered_weight,
            })
            # Answers in an unscored dimension still surface as findings. They
            # get lever 0 — an excluded dimension genuinely cannot move the
            # overall score — so they rank below everything that can, but a
            # real gap is not hidden just because the dimension was left
            # half-answered.
            scored_q.extend(dim_scored)
        else:
            dim_score = (weighted_sum / answered_weight) * 100.0
            dim_results.append({
                "id": dim["id"], "name": dim["name"],
                "weight": dim["weight"], "score": dim_score,
                "answered_weight": answered_weight,
            })
            scored_q.extend(dim_scored)
    # Overall: weighted average of scored dimensions
    scored_dims = [d for d in dim_results if d["score"] is not None]
    skipped = [d["name"] for d in dim_results if d["score"] is None]
    if not scored_dims:
        return {
            "overall": None, "band": None, "dimensions": dim_results,
            "risks": [], "opportunities": [], "skipped": skipped,
        }
    total_w = sum(d["weight"] for d in scored_dims)
    overall = sum(d["score"] * d["weight"] for d in scored_dims) / total_w
    band = None
    for bid, lo, hi, label in BANDS:
        if lo <= overall < hi:
            band = (bid, label, BAND_NARRATIVE.get(bid, ""))
            break
    # Attach each question's overall-score lever.
    dim_by_id = {d["id"]: d for d in dim_results}
    ranked = []
    for q, dim, score in scored_q:
        dr = dim_by_id[dim["id"]]
        aw = dr["answered_weight"]
        lever = 0.0
        if aw > 0 and dr["score"] is not None:
            dim_gain = ((1.0 - score) * float(q.get("weight", 1.0)) / aw) * 100.0
            lever = dim_gain * dr["weight"] / total_w
        ranked.append((q, dim, score, lever))
    # Primary key is the lever. The tie-break keeps items from excluded
    # dimensions (lever 0) in a sensible order among themselves.
    ranked.sort(key=lambda t: (t[3], (1.0 - t[2]) * float(t[0].get("weight", 1.0))),
                reverse=True)
    risks = [r for r in ranked if r[2] < RISK_THRESHOLD][:6]
    # Opportunities: partially in place; no overlap with risks by construction.
    opps = [r for r in ranked if RISK_THRESHOLD <= r[2] < OPPORTUNITY_CEILING][:6]
    return {
        "overall": overall,
        "band": band,
        "dimensions": dim_results,
        "risks": risks,
        "opportunities": opps,
        "skipped": skipped,
    }

# ---------------------------------------------------------------------------
# Funnel analytics (PostHog, server-side)
# ---------------------------------------------------------------------------
# Silent no-op without a POSTHOG_PROJECT_TOKEN (env, secrets, or .env).
# Each event fires at most once per session, so reruns from widget
# interaction never inflate the funnel. The numbers this exists to answer:
# starts, per-dimension completion, drop-off, results views, capture rate.
def track(event: str, once_key: str = None, **props):
    ss = st.session_state
    key = once_key or event
    sent = ss.setdefault("_ph_sent", set())
    if key in sent:
        return
    sent.add(key)  # mark before sending so a slow endpoint cannot double-fire
    token = _get_conf("POSTHOG_PROJECT_TOKEN")
    if not token:
        return
    host = _get_conf("POSTHOG_HOST", "https://us.i.posthog.com").rstrip("/")
    if "ph_id" not in ss:
        import uuid
        ss["ph_id"] = str(uuid.uuid4())
    try:
        requests.post(
            host + "/capture/",
            json={
                "api_key": token,
                "event": event,
                "distinct_id": ss["ph_id"],
                "properties": {"rubric_version": RUBRIC_VERSION, **props},
            },
            timeout=3,
        )
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Email capture (Loops API)
# ---------------------------------------------------------------------------
def _capture_email(email: str, company: str, band: str, score: float, name: str = ""):
    """Send lead to Loops for nurture drip. Fails silently — no error shown to user."""
    api_key = _get_conf("LOOPS_API_KEY")
    if not api_key:
        # No key configured. Mark it soft_fail rather than returning silently:
        # leaving email_captured unset made the results page re-render the
        # capture form, so the visitor was asked a second time with no hint
        # that anything had gone wrong.
        st.session_state.email_captured = "soft_fail"
        return
    try:
        payload = {
            "email": email,
            "source": "structural_audit",
            "company": company,
            "auditBand": band,
            "auditScore": round(score, 1),
            "auditIntent": st.session_state.get("audit_intent", ""),
        }
        if name:
            payload["firstName"] = name.split(" ")[0].strip()
            payload["fullName"] = name.strip()
        resp = requests.post(
            "https://app.loops.so/api/v1/contacts/create",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
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
    _install_parent_js(scroll=False, beforeunload=False, buttons=True, hide_chrome=True)
    mark()

    # --- Resume banner (?code= param, from a share link or the localStorage
    # redirect below). Restore is explicit — never silent. ---
    _resume_qp, _resume_src, _resume_go = "", "", ""
    try:
        _resume_qp = st.query_params.get("code", "")
        _resume_src = st.query_params.get("src", "")
        _resume_go = st.query_params.get("go", "")
    except Exception:
        pass
    _resume_payload = _peek_state(_resume_qp) if _resume_qp else None
    # The in-browser banner (injected by JS below) already asked; its Resume
    # link carries go=1. Restore immediately — the click was the confirmation.
    if _resume_payload and _resume_src == "ls" and _resume_go == "1":
        if _decode_state(_resume_qp):
            track("audit_resumed", origin="banner")
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.rerun()
    if _resume_payload and _resume_payload.get("s") in ("context", "dim", "gate", "results"):
        _saved_company = _resume_payload.get("c", "") or "an unnamed company"
        _saved_answers = _resume_payload.get("a", {})
        if not isinstance(_saved_answers, dict):
            _saved_answers = {}
        _n_answered = sum(1 for v in _saved_answers.values() if v not in (None, "", "N/A"))
        _total_q = sum(len(d["questions"]) for d in DIMENSIONS)
        _origin_line = (
            "This browser holds a saved audit for"
            if _resume_src == "ls"
            else "This link contains a saved audit for"
        )
        st.markdown(
            f'<div class="sa-card" style="border-left:3px solid var(--accent)">'
            f'<div class="label">Audit in progress</div>'
            f'<p style="margin:6px 0 2px;font-size:1rem">{_origin_line} '
            f'<strong>{_html.escape(_saved_company)}</strong>. {_n_answered} of {_total_q} questions answered. '
            f'Restore it to pick up where it left off.</p></div>',
            unsafe_allow_html=True,
        )
        _rc1, _rc2 = st.columns(2)
        with _rc1:
            _saved_rv = _resume_payload.get("rv", "1.0.x")
            if _saved_rv != RUBRIC_VERSION:
                st.caption(
                    f"Saved on rubric {_saved_rv}; the audit now runs {RUBRIC_VERSION}. "
                    "One sales question was reworded, so check that answer before trusting the score."
                )
            if st.button("Restore this audit", key="btn_banner_resume", use_container_width=True):
                if _decode_state(_resume_qp):
                    track("audit_resumed", origin="banner" if _resume_src == "ls" else "link")
                    try:
                        st.query_params.clear()
                    except Exception:
                        pass
                    st.rerun()
        with _rc2:
            if st.button("Start fresh", key="btn_banner_fresh", use_container_width=True):
                st.session_state["_ls_clear"] = True
                try:
                    st.query_params.clear()
                except Exception:
                    pass
                st.rerun()
        st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)

    # Clear the abandoned save if the visitor chose to start fresh
    if st.session_state.pop("_ls_clear", False):
        _frame(
            """
            <script>
            (function(){
              try { window.parent.localStorage.removeItem('sa_audit_state'); } catch(e) {}
            })();
            </script>
            """,
            height=0,
        )

    st.markdown('<div class="sa-meta">For the company · Fifteen to twenty minutes · Six dimensions</div>', unsafe_allow_html=True)
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
    # Save/resume capability, advertised before the start — it is a
    # differentiator, not a footnote.
    st.markdown(
        '<p class="sa-footnote" style="margin-bottom:0.8rem">Progress auto-saves in this browser. '
        'A save code lets you stop midway and resume on any device. Nothing is lost.</p>',
        unsafe_allow_html=True,
    )
    if st.button("Begin the audit", key="btn_begin", use_container_width=False):
        st.session_state["_audit_start"] = _time.time()
        # Capture inbound attribution BEFORE clearing the query string —
        # grahamkindermann.com/tools and every Substack post send utm_* here.
        _utm_props = {}
        try:
            for _k in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"):
                _v = st.query_params.get(_k, "")
                if _v:
                    _utm_props[_k] = _v
        except Exception:
            pass
        st.session_state["_utm"] = _utm_props
        track("audit_started", **_utm_props)
        try:
            st.query_params.clear()
        except Exception:
            pass
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
                track("audit_resumed", origin="code")
                st.rerun()
            else:
                st.error("Invalid code. Please check and try again.")
    # Auto-detect a saved audit in this browser and offer to resume it.
    # The offer is a banner injected into the parent DOM: sandboxed component
    # iframes on Streamlit Cloud cannot navigate ancestor frames, so the
    # Resume control is a plain link (?code=...&src=ls&go=1) that the USER
    # clicks in the parent document. Explicit restore only — never silent.
    if not _resume_payload and not st.session_state.get("_navigated") and not st.session_state.answers:
        _frame(
            """
            <script>
            (function(){
              try {
                var pw = window.parent;
                var pd = pw.document;
                var saved = pw.localStorage.getItem('sa_audit_state');
                if (!saved) return;
                if (pw.sessionStorage.getItem('sa_resume_dismissed')) return;
                var loc = new URL(pw.location.href);
                if (loc.searchParams.has('code')) return;
                if (pd.getElementById('sa-resume-offer')) return;
                var main = pd.querySelector('section.stMain div.block-container') || pd.querySelector('section.stMain');
                if (!main) return;
                loc.searchParams.set('code', saved);
                loc.searchParams.set('src', 'ls');
                loc.searchParams.set('go', '1');
                var div = pd.createElement('div');
                div.id = 'sa-resume-offer';
                div.style.cssText = 'border:1px solid #D9CFBC;border-left:3px solid #8B6A3F;background:#FBF8F1;padding:16px 20px;margin:0 0 1.6rem;font-family:Inter,system-ui,sans-serif';
                div.innerHTML =
                  '<div style="font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#6B6659;margin-bottom:6px">Audit in progress</div>'
                  + '<p style="margin:0 0 12px;font-size:15px;line-height:1.5;color:#2A3758">This browser holds a saved audit. Pick up where you left off.</p>'
                  + '<a href="' + loc.toString() + '" style="display:inline-block;background:#14223D;color:#F4EFE6;padding:10px 22px;font-size:14px;text-decoration:none;margin-right:10px">Resume the audit</a>'
                  + '<button id="sa-resume-dismiss" style="background:transparent;border:1px solid #14223D;color:#14223D;padding:9px 22px;font-size:14px;cursor:pointer;font-family:Inter,system-ui,sans-serif">Start fresh</button>';
                main.insertBefore(div, main.firstChild);
                pd.getElementById('sa-resume-dismiss').addEventListener('click', function(){
                  try {
                    pw.localStorage.removeItem('sa_audit_state');
                    pw.sessionStorage.setItem('sa_resume_dismissed', '1');
                  } catch(e) {}
                  div.remove();
                });
              } catch(e) {}
            })();
            </script>
            """,
            height=0,
        )

    st.markdown(
        "If you have not taken the Index yet, start there. Know your shape as an operator first. "
        f"[Open the Index &rarr;]({_utm(LINKS['index'], 'audit_intro', 'cross_tool')})",
    )

def screen_context():
    _install_parent_js(scroll=True, beforeunload=True, buttons=True)
    _save_to_localstorage()
    mark()
    st.markdown('<div class="sa-meta">Step 1 of 8 · Company context</div>', unsafe_allow_html=True)
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
    ready = bool(st.session_state.company) and bool(st.session_state.revenue) and bool(st.session_state.industry)
    if not ready:
        st.markdown('<p class="sa-footnote">Company name, industry, and revenue band are required to continue.</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back", key="ctx_back", use_container_width=True):
            go("intro")
    with col2:
        if st.button("Continue to the audit", key="ctx_next", use_container_width=True, disabled=not ready):
            track(
                "context_completed",
                industry=st.session_state.industry,
                revenue=st.session_state.revenue,
                intent=st.session_state.audit_intent,
            )
            st.session_state.dim_idx = 0
            go("dim")

def render_question(q):
    """Render one question.

    All three question types get identical typography: the text in bold via
    st.markdown, and the widget's own label collapsed. Before 1.1.0, Likert
    questions were bold (markdown) while yes/no and metric questions inherited
    the widget label's regular weight, so three type treatments appeared in one
    list. `label_visibility="collapsed"` rather than `"hidden"`: hidden keeps
    the label's box in the layout, which added a measured 51px of dead space
    to every one of the thirty Likert questions.
    """
    qid = q["id"]
    current = st.session_state.answers.get(qid)
    st.markdown(f"**{q['text']}**")

    if q["type"] == "likert":
        # "Skip" is the unanswered placeholder for every type. N/A sits last
        # and means "this genuinely does not apply", which is a different
        # statement — and used to be the pre-selected default here.
        options = ["Skip", "1", "2", "3", "4", "5"]
        if q.get("allow_na"):
            options.append("N/A")
        idx = 0
        if isinstance(current, (int, float)):
            label = str(int(current))
            if label in options:
                idx = options.index(label)
        elif current == "N/A" and "N/A" in options:
            idx = options.index("N/A")
        st.caption("1 = Strongly disagree · 5 = Strongly agree")
        choice = st.radio(
            q["text"], options, index=idx, key=f"rad_{qid}",
            horizontal=True, label_visibility="collapsed",
        )
        if choice == "Skip":
            st.session_state.answers[qid] = None
        elif choice == "N/A":
            st.session_state.answers[qid] = "N/A"
        else:
            st.session_state.answers[qid] = int(choice)

    elif q["type"] == "yesno":
        options = ["Skip", "Yes", YESNO_PARTIAL_LABEL, "No"]
        if q.get("allow_na"):
            options.append("N/A")
        idx = options.index(current) if current in options and current != "Skip" else 0
        st.caption(YESNO_PARTIAL_HINT)
        choice = st.radio(
            q["text"], options, index=idx, key=f"rad_{qid}",
            horizontal=True, label_visibility="collapsed",
        )
        st.session_state.answers[qid] = None if choice == "Skip" else choice

    elif q["type"] in ("number", "percent"):
        bench = BENCHMARKS.get((st.session_state.industry, qid))
        placeholder = "e.g. 15" if q["type"] == "percent" else "e.g. 500000"
        if bench:
            placeholder = f"e.g. {bench['p50']}"
        val = st.text_input(
            q["text"],
            value="" if current in (None, "N/A") else str(current),
            key=f"num_{qid}",
            placeholder=placeholder,
            label_visibility="collapsed",
        )
        if bench:
            _BENCH_UNITS = {
                "per_q_turnover_pct": "%", "fin_q_ar_over_60_pct": "%",
                "sw_q_software_spend_pct": "%", "sal_q_monthly_churn_pct": "%",
                "ops_q_on_time_delivery_pct": "%",
                "per_q_days_to_fill": " days", "fin_q_days_to_close": " days",
                "ops_q_mttr_hours": " hrs",
                "sw_q_num_saas_tools": " tools", "ai_q_num_ai_workflows": " workflows",
                "sal_q_cac": "",
            }
            _u = _BENCH_UNITS.get(qid, "")
            _fmt = lambda v: f"${v:,.0f}" if qid == "sal_q_cac" else f"{v:g}{_u}"
            # The three numbers run low-to-high either way, so the good end
            # flips between questions. Say which end is good.
            _dir = "lower is better" if q.get("lower_is_better") else "higher is better"
            st.caption(
                f"Industry benchmark ({_dir}): 25th: {_fmt(bench['p25'])} · "
                f"Median: {_fmt(bench['p50'])} · 75th: {_fmt(bench['p75'])}"
            )
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
                    # A percentage entered as a decimal (0.15 for 15%) scores as
                    # near-perfect and says nothing. Flag it rather than guess.
                    if (q["type"] == "percent" and bench and 0 < _num_val < 1
                            and float(bench["p25"]) >= 1):
                        st.markdown(
                            f'<p style="font-size:0.85rem;color:#7A2E20;margin:2px 0 0">'
                            f'&#9888; Entered as {_num_val:g}. If you meant '
                            f'{_num_val * 100:g}%, enter {_num_val * 100:g}.</p>',
                            unsafe_allow_html=True,
                        )
                    # Inline benchmark feedback
                    if bench:
                        _lower = q.get("lower_is_better", False)
                        if _lower:
                            if _num_val <= bench["p25"]:
                                st.markdown('<p style="font-size:0.85rem;color:#4A5A32;margin:2px 0 0">&#10003; Better than 75% of peers in your industry.</p>', unsafe_allow_html=True)
                            elif _num_val <= bench["p50"]:
                                st.markdown('<p style="font-size:0.85rem;color:#4A5A32;margin:2px 0 0">&#10003; Better than the industry median.</p>', unsafe_allow_html=True)
                            elif _num_val <= bench["p75"]:
                                st.markdown('<p style="font-size:0.85rem;color:#8A6420;margin:2px 0 0">&#9888; Worse than the industry median.</p>', unsafe_allow_html=True)
                            else:
                                st.markdown('<p style="font-size:0.85rem;color:#7A2E20;margin:2px 0 0">&#9888; Worse than 75% of peers in your industry.</p>', unsafe_allow_html=True)
                        else:
                            if _num_val >= bench["p75"]:
                                st.markdown('<p style="font-size:0.85rem;color:#4A5A32;margin:2px 0 0">&#10003; Better than 75% of peers in your industry.</p>', unsafe_allow_html=True)
                            elif _num_val >= bench["p50"]:
                                st.markdown('<p style="font-size:0.85rem;color:#4A5A32;margin:2px 0 0">&#10003; Better than the industry median.</p>', unsafe_allow_html=True)
                            elif _num_val >= bench["p25"]:
                                st.markdown('<p style="font-size:0.85rem;color:#8A6420;margin:2px 0 0">&#9888; Worse than the industry median.</p>', unsafe_allow_html=True)
                            else:
                                st.markdown('<p style="font-size:0.85rem;color:#7A2E20;margin:2px 0 0">&#9888; Worse than 75% of peers in your industry.</p>', unsafe_allow_html=True)
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
    st.markdown(f'<div class="sa-meta">Step {idx + 2} of {total + 2} · Dimension {idx + 1} of {total}</div>', unsafe_allow_html=True)
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
    # 20s per question: 50 questions = 17 minutes, mid-band of the canonical
    # fifteen-to-twenty claim shared with grahamkindermann.com.
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
            # Plain markup, not a component iframe. At height=38 the iframe
            # clipped the descenders of "Team Quality & Retention" and sat
            # ~8px right of the text column, because it was the only element
            # on the page rendered in an iframe.
            st.markdown(
                f'<p class="sa-group">{_html.escape(_grp)}</p>',
                unsafe_allow_html=True,
            )
            # "(blank to skip)" used to be appended to all eleven metric
            # labels. Say it once, per metric group.
            if all(gq["type"] in ("number", "percent")
                   for gq in dim["questions"] if gq.get("group") == _grp):
                st.caption("Estimates are fine. Leave any of these blank to skip.")
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
    # Save code for cross-device resume
    with st.expander("Save your progress"):
        code = _encode_state()
        _safe_code = json.dumps(code)
        st.code(code, language=None)
        _frame(
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
            <button onclick="navigator.clipboard.writeText({_safe_code}).then(function(){{document.getElementById('cp').textContent='Copied.'}})">
              Copy to clipboard
            </button><span id="cp" class="ok"></span>
            """,
            height=42,
        )
        st.caption("Paste this code on the intro screen to resume from any device.")
        st.caption(
            "The code contains your answers. Treat it like the report."
        )

    # Skip dimension. Below the save block rather than directly under the
    # primary action: a skipped dimension is EXCLUDED from the overall score
    # rather than scored as zero, so it nudges the score up slightly. Say so.
    if st.button("Skip this dimension", key=f"dim_skip_{idx}"):
        for q in dim["questions"]:
            st.session_state.answers[q["id"]] = "N/A"
        advance_dim(skipped=True)
    st.caption(
        "Skipping excludes this dimension from the overall score rather than "
        "scoring it zero. The report names any dimension that was skipped."
    )

def pct_bar(pct):
    pct = max(0.0, min(100.0, pct))
    return (
        f'<div class="sa-bar-track"><div class="sa-bar-fill" style="width:{pct:.1f}%"></div></div>'
    )

def screen_results():
    _install_parent_js(scroll=True, beforeunload=False, buttons=True)
    _save_to_localstorage()
    mark()
    _total_dims = len(DIMENSIONS)
    st.markdown(f'<div class="sa-meta">Step {_total_dims + 2} of {_total_dims + 2} · Results</div>', unsafe_allow_html=True)
    r = compute_results()
    if r["overall"] is not None:
        track(
            "results_viewed",
            score=round(r["overall"], 1),
            band=r["band"][0] if r["band"] else "",
            industry=st.session_state.industry,
            revenue=st.session_state.revenue,
            intent=st.session_state.audit_intent,
        )
    _raw_company = st.session_state.company or "The Company"
    company = _html.escape(_raw_company)  # safe for embedding in HTML
    # %-d is a glibc/BSD extension and raises ValueError on Windows.
    _today = _dt.date.today()
    _audit_date = f"{_today:%B} {_today.day}, {_today:%Y}"
    # Time-spent calculation
    # _audit_start is wall-clock from the first "Begin", and it survives in the
    # save code, so a resumed audit would otherwise report elapsed calendar
    # time ("Completed in 4320 minutes"). Only claim a duration when it is
    # plausibly a single sitting.
    _start = st.session_state.get("_audit_start")
    _elapsed_str = ""
    if _start:
        _elapsed_min = int((_time.time() - _start) / 60)
        if 1 <= _elapsed_min <= 120:
            _elapsed_str = f" · Completed in {_elapsed_min} minute{'s' if _elapsed_min != 1 else ''}"
    _respondent = st.session_state.get("respondent", "")
    _role_str = f" · Completed by: {_html.escape(_respondent)}" if _respondent else ""
    st.markdown(
        f'<div class="sa-meta">Prepared for {company} · {_audit_date}{_elapsed_str}{_role_str} · Confidential</div>',
        unsafe_allow_html=True,
    )
    _title_name = _raw_company.rstrip(".")
    st.markdown(f"# {_title_name}. Structural Audit.")
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
    _frame(
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
    # NOTE: there is deliberately no peer-percentile claim here. Until enough
    # audits have accumulated to build a real distribution, the tool has no
    # cohort to rank anyone against, and revenue band is not an input to the
    # score at all. Saying "bottom 15% of businesses at this revenue band"
    # would be an invented statistic on a tool sold on diagnostic honesty.
    st.markdown(
        '<p class="sa-footnote" style="margin:0.5rem 0 0.8rem">'
        'This is a score against the rubric, not a ranking against peers. '
        'Peer comparison arrives once enough audits are in.</p>',
        unsafe_allow_html=True,
    )
    if band_narrative:
        st.markdown(f"<p>{band_narrative}</p>", unsafe_allow_html=True)
    # A skipped dimension is excluded from the weighted average, not scored
    # zero, so it moves the overall score. Say which, and say it near the
    # score rather than only in the dimension list further down.
    if r.get("skipped"):
        _sk = ", ".join(r["skipped"])
        st.markdown(
            f'<div class="sa-card" style="border-left:3px solid var(--muted);background:#F7F3EA">'
            f'<div class="label">Excluded from this score</div>'
            f'<p style="margin:6px 0 0;font-size:0.95rem">{_html.escape(_sk)} '
            f'{"was" if len(r["skipped"]) == 1 else "were"} not answered fully enough to score, and '
            f'{"is" if len(r["skipped"]) == 1 else "are"} excluded from the overall rather than counted as zero. '
            f'The score above reflects the remaining dimensions only.</p></div>',
            unsafe_allow_html=True,
        )
    # Distance to next band (motivational nudge)
    if band_id != "durable":
        # Derive next band from BANDS at runtime to avoid threshold drift
        _band_ids = [b[0] for b in BANDS]
        _cur_idx = _band_ids.index(band_id) if band_id in _band_ids else -1
        _nb = (BANDS[_cur_idx + 1][3], BANDS[_cur_idx + 1][1]) if 0 <= _cur_idx < len(BANDS) - 1 else None
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
            "Sales & Marketing, and Operations & Process. Rating questions map 1 to 5 "
            "onto 0 to 100. Yes/no questions score 100 for yes, 50 for partly, 0 for no. "
            "Metric questions (turnover, days to close, CAC and the rest) are scored against "
            "industry benchmarks at the 25th, 50th and 75th percentile for your selected industry."
        )
        st.markdown(
            "Each dimension requires at least 60% of its question weight to be answered "
            "before it receives a score. Dimensions below that threshold are excluded from "
            "the overall weighted average and marked as Insufficient Data — which means "
            "skipping a dimension removes it from the score rather than scoring it as zero. "
            "The overall score is the weighted average of all scored dimensions, 0 to 100."
        )
        st.markdown(
            "**Risks** are answered items scoring below 40. **Opportunities** are items "
            "between 40 and 75 — partly in place, cheaper to move than a risk, though not "
            "worth more. Both lists are ordered by the same measure: how many points the "
            "overall score would gain if that one answer moved to full marks. That "
            "calculation accounts for the question's weight, how much of its dimension was "
            "answered, and the dimension's own weight."
        )
        st.markdown(f"_{BENCHMARK_DISCLOSURE}_")
        # Derived from BANDS so the stated ranges can never drift from the
        # half-open intervals actually used. The old hardcoded string said
        # "Fragile (41-60)" while the code banded everything up to 60.9 as
        # Fragile, so nine tenths of every band fell outside its stated range.
        _band_strs = []
        for _bid, _lo, _hi, _label in BANDS:
            if _hi >= 101:
                _band_strs.append(f"{_label} ({_lo} and above)")
            else:
                _band_strs.append(f"{_label} ({_lo} to under {_hi})")
        st.markdown("**Band thresholds:** " + ", ".join(_band_strs) + ".")
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
                f" The largest single lever sits in {top_risk_dim['name']}: "
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

    # Pre-compute lookups needed by both the biggest-lever callout and dimension cards
    dim_id_to_idx = {dim["id"]: i for i, dim in enumerate(DIMENSIONS)}
    industry = st.session_state.industry
    answers = st.session_state.answers

    # --- Biggest lever callout ---
    # r["risks"] is already ranked by this exact quantity, so the item named
    # here is always the one with the largest available gain. Before 1.1.0 the
    # ranking used question weight alone while this callout used the
    # dimension-weighted lever, so the two disagreed.
    if r["risks"] and scored_dims:
        _top_q, _top_dim, _top_score, _top_lever = r["risks"][0]
        if _top_lever >= 0.5:
            st.markdown(
                f'<div class="sa-lever" style="font-size:0.95rem;color:{_band_color};margin:0 0 1rem;padding:10px 14px;'
                f'background:transparent;border:1px dashed {_band_color}">'
                f'<strong>Biggest lever.</strong> Fixing '
                f'<em>&ldquo;{_html.escape(_top_q["text"])}&rdquo;</em> '
                f'in {_html.escape(_top_dim["name"])} would move the overall score by ~{_top_lever:.1f} points '
                f'&mdash; more than any other single answer.</div>',
                unsafe_allow_html=True,
            )

    # --- Pre-compute which optional sections will render ---
    _has_opps = bool(r["opportunities"])
    _has_plan = any(q.get("recommendation") for q, _, _, _ in r["risks"][:3]) or (
        _has_opps and any(q.get("recommendation") for q, _, _, _ in r["opportunities"])
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
    _frame(
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
                var _bg = getComputedStyle(window.parent.document.documentElement).getPropertyValue('--bone').trim() || '#F4EFE6';
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
          .radar-wrap {{ text-align:center; margin:0; }}
          .radar-wrap svg {{ max-width:440px; width:100%; }}
          @media(max-width:500px){{
            .radar-wrap svg {{ max-width:100%; }}
            .radar-wrap svg text {{ font-size:9px !important; }}
          }}
        </style>
        <div class="radar-wrap">
          <!-- Was "-60 -15 520 430". At 520 units wide the 11px labels
               overflowed both edges on desktop: "Operations & Process" lost
               its opening letters and "Accounting & Finance" lost its score
               entirely. Mobile escaped only because the <=500px rule drops
               label text to 9px. Widened to fit the labels, then trimmed
               vertically to the measured ink box so the frame stops
               reserving empty space above "Dimension scores". -->
          <svg viewBox="-87 10 574 374" width="100%" xmlns="http://www.w3.org/2000/svg"
               role="img" aria-label="Radar chart of dimension scores: {', '.join(f'{d["name"]} {d["score"]:.0f}' for d in scored_for_radar)}">
            <title>Dimension score radar chart</title>
            {_grid_svg}{_axis_svg}{_data_svg}{_dots_svg}{_labels_svg}
          </svg>
        </div>
        """
        # Height is deterministic, so state it rather than chase it: the SVG
        # is capped at 440px wide and the viewBox is 574x374, so it renders
        # 287px tall at the desktop measure. Streamlit fixes the element
        # container's height from the `height` argument via an emotion class
        # with !important, which an in-frame script cannot release (verified),
        # so an autosizing script would shrink the iframe and leave the
        # container's reserved space behind. 380 was the old value and left
        # ~300px of dead band above "Dimension scores".
        _frame(
            f'<div style="background:transparent;margin:0;padding:0">{_radar_html}</div>'
            # The class is the print stylesheet's marker: it hides every
            # component frame except this one. classList.add survives on the
            # components.html path but NOT under st.iframe — see _frame().
            '<script>try{var f=window.frameElement;'
            'if(f)f.classList.add("sa-radar-iframe")}catch(e){}</script>',
            height=295,
        )

    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)

    # Dimensions
    st.markdown('<div id="sa-dimensions"></div>', unsafe_allow_html=True)
    st.markdown("## Dimension scores")
    st.markdown(
        '<p class="sa-lede" style="font-size:1.05rem">Any dimension with insufficient answered weight is excluded from the overall score and marked as such.</p>',
        unsafe_allow_html=True,
    )
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
            # "above" reads as good, but six of these metrics are
            # lower-is-better: above the median on turnover, days to
            # close, AR over 60, MTTR, CAC or churn is the bad end.
            _n_word = "metric" if benchmarked_total == 1 else "metrics"
            if above == benchmarked_total:
                _bc, _bw = "#4A5A32", "at or better than"
            elif at_or_below == benchmarked_total:
                _bc, _bw = "var(--warn)", "worse than"
            else:
                _bc, _bw = "var(--muted)", "at or better than"
            _bn = above if _bw.startswith("at or") else at_or_below
            bench_line = (
                f'<div class="sa-bench-line" style="color:{_bc}">'
                f'{_bn} of {benchmarked_total} benchmarked {_n_word} {_bw} the industry median</div>'
            )

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
                _q_short = _html.escape(q.get("text", q["id"])[:40])
                # #9A8B6E, not var(--hair) #D9CFBC: the old swatch sat at
                # roughly 1.5:1 against the page background, under the 3:1
                # minimum for a non-text graphic.
                if not flagged or qs is None:
                    _st, _col = "skipped", "#9A8B6E"
                elif qs >= 0.75:
                    _st, _col = "strong", "#4A5A32"
                elif qs >= 0.4:
                    _st, _col = "partial", "#8A6420"
                else:
                    _st, _col = "gap", "#7A2E20"
                _heat_cells.append(
                    f'<span title="{_q_short}: {_st}" aria-label="{_q_short}: {_st}" '
                    f'style="background:{_col}"></span>'
                )
            _n_cells = len(_heat_cells)
            _heat_strip = (
                f'<div class="sa-heat" role="img" aria-label="Per-question score breakdown for {_html.escape(d["name"])}" '
                f'style="grid-template-columns:repeat({_n_cells},1fr)">'
                + "".join(_heat_cells)
                + '</div>'
                + '<div class="sa-heat-legend">Per-question breakdown: '
                + '<span style="color:#4A5A32">&#9632;</span> <span class="k">strong</span> · '
                + '<span style="color:#8A6420">&#9632;</span> <span class="k">partial</span> · '
                + '<span style="color:#7A2E20">&#9632;</span> <span class="k">gap</span> · '
                + '<span style="color:#9A8B6E">&#9632;</span> <span class="k">skipped</span></div>'
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
        # Two very different situations produce an empty risk list, and the
        # old copy ("this is rare") only described one of them. Nothing scored
        # below 40 can equally mean everything landed mid-scale — which is
        # what a page of neutral ratings and at-median metrics produces.
        _mid = [t for t in r["opportunities"]]
        if _mid and (r["overall"] or 0) < 61:
            st.markdown(
                "<p>Nothing scored low enough to register as a risk, but little scored high "
                "either — the answers cluster in the middle. That usually means one of two "
                "things: the business really is evenly average across the board, or the "
                "questions were answered defensively. If it is the second, go back and answer "
                "the uncomfortable ones honestly; a middling score hides more than a bad one.</p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<p>No material risks surfaced. That is rare. Double-check the answers with a "
                "skeptical eye before you trust it.</p>",
                unsafe_allow_html=True,
            )
    for q, dim, score, _lever in r["risks"]:
        risk = _html.escape(q.get("risk_copy", ""))
        rec = _html.escape(q.get("recommendation", ""))
        st.markdown(
            f'<div class="sa-risk">'
            f'<div class="sa-meta">{_html.escape(dim["name"])}</div>'
            f'<div class="q">&ldquo;{_html.escape(q["text"])}&rdquo;</div>'
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
            '<p class="sa-lede" style="font-size:1.05rem">Items that are partly in place. '
            'Individually these move the score less than closing a risk does &mdash; that is what '
            'makes them opportunities rather than risks &mdash; but they are already half built, '
            'so they are usually the cheapest points on the board.</p>',
            unsafe_allow_html=True,
        )
        for q, dim, score, _lever in r["opportunities"]:
            opp = _html.escape(q.get("opportunity_copy", ""))
            rec = _html.escape(q.get("recommendation", ""))
            st.markdown(
                f'<div class="sa-opp">'
                f'<div class="sa-meta">{_html.escape(dim["name"])}</div>'
                f'<div class="q">&ldquo;{_html.escape(q["text"])}&rdquo;</div>'
                f'<div class="copy">{opp}</div>'
                + (f'<div class="sa-rec"><strong>Next action.</strong> {rec}</div>' if rec else "")
                + '</div>',
                unsafe_allow_html=True,
            )

    # --- 90-Day Focus Plan ---
    _plan_items = []
    for q, dim, score, _lever in r["risks"][:3]:
        rec = q.get("recommendation", "")
        if rec:
            _plan_items.append({"dim": dim["name"], "rec": rec, "q": q["text"]})
    # Fill remaining slots from opportunities if fewer than 3 risks
    if len(_plan_items) < 3 and r["opportunities"]:
        for q, dim, score, _lever in r["opportunities"]:
            rec = q.get("recommendation", "")
            if rec and len(_plan_items) < 3:
                _plan_items.append({"dim": dim["name"], "rec": rec, "q": q["text"]})

    if _plan_items:
        st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
        st.markdown('<div id="sa-plan"></div>', unsafe_allow_html=True)
        st.markdown("## 90-Day Focus Plan")
        st.markdown(
            '<p class="sa-lede" style="font-size:1.05rem">'
            'Three moves, ordered by how many points each returns to the overall score. '
            'Start at the top; the cadence below is a suggested rhythm, not a dependency chain.</p>',
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
        _cap_name = st.text_input("Your name (optional)", key="capture_name", placeholder="First name is enough")
        email_val = st.text_input("Email address", key="capture_email", placeholder="founder@yourcompany.com")
        st.markdown(
            '<p class="sa-footnote" style="margin:2px 0 10px">'
            'Three emails, then nothing. Unsubscribe from any of them. '
            'We store your email, company name, score band and industry &mdash; '
            'never your individual answers. '
            f'<a href="{LINKS["privacy"]}" style="color:var(--accent)">How we handle your data</a>.</p>',
            unsafe_allow_html=True,
        )
        if st.button("Send me the action plan", key="btn_capture"):
            if email_val and re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email_val.strip()):
                _capture_email(
                    email_val.strip(), _raw_company, band_label, r["overall"],
                    name=(st.session_state.get("capture_name") or "").strip(),
                )
                track("report_requested", where="results_footer")
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
        if st.button("Change email", key="btn_change_email"):
            st.session_state.email_captured = None
            st.rerun()

    # --- Call CTA (heavier ask — comes second, band-specific copy) ---
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    st.markdown('<div id="sa-next"></div>', unsafe_allow_html=True)
    st.markdown("## What to do with this")
    _CTA_COPY = {
        "critical": (
            "A score in this range means the business is carrying structural risk that compounds "
            "with time, not resolves with it. The next useful step is a fit call. Thirty minutes. "
            "The audit in front of us. We will identify which of the top risks is load-bearing "
            "and what a realistic 90-day stabilization looks like."
        ),
        "fragile": (
            "The audit surfaced real gaps, but the business is functioning. The risk is that "
            "these gaps stay invisible until something forces the issue. The next useful step is a "
            "fit call. Thirty minutes. The audit in front of us. A pressure-test of the top "
            "risks and the one move that would actually change the score by next quarter."
        ),
        "functional": (
            "The audit is honest but it is not a plan. A Functional score means the foundation is real "
            "but the remaining gaps are load-bearing. The next useful step is a fit call. Thirty "
            "minutes. The audit in front of us. We will sequence the two or three moves that would "
            "push the business into durable territory."
        ),
        "strong": (
            "At this level, the remaining gaps are refinements, not emergencies. The leverage is in "
            "compounding what already works. The next useful step is a fit call. Thirty minutes. "
            "The audit in front of us. We will identify which strengths to protect and which "
            "refinements have the highest marginal return."
        ),
        "durable": (
            "A Durable score is rare. The business is structurally sound and the question shifts from "
            "fixing weaknesses to scaling on strength. If you are considering a transaction, preparing "
            "for a capital event, or expanding into a new vertical, a fit call sharpens the picture. "
            "Thirty minutes. The audit in front of us."
        ),
    }
    _cta_text = _CTA_COPY.get(band_id, _CTA_COPY["functional"])
    st.markdown(_cta_text)
    cal_url = CTA["lead_magnet"]["primary_url"]
    # One name for the call across button, body copy, share text and Calendly.
    # "Structural review" collided with the paid Structural Position Review.
    _cta_label = CTA["lead_magnet"]["primary_label"]
    st.link_button(_cta_label, _utm(cal_url, f"results_{band_id}", "cta"), use_container_width=False)
    st.markdown(
        '<p style="font-size:0.88rem;color:var(--muted);margin-top:0.8rem">'
        'Not ready for a call? <a href="' + _utm(LINKS["substack"], f"results_{band_id}", "newsletter") + '" '
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
        f"STRUCTURAL AUDIT — {_raw_company} ({_audit_date})",
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
        for q, dim, score, _lever in r["risks"][:3]:
            _summary_lines.append(f"  [{dim['name']}] {q['text']}")
    if _plan_items:
        _summary_lines.append("")
        _summary_lines.append("90-DAY FOCUS PLAN:")
        _periods = ["Days 1-30", "Days 31-60", "Days 61-90"]
        for i, item in enumerate(_plan_items):
            period = _periods[i] if i < len(_periods) else f"Days {i*30+1}-{(i+1)*30}"
            _summary_lines.append(f"  {period} ({item['dim']}): {item['rec']}")
    _summary_lines.append("")
    _summary_lines.append(f"{CTA['lead_magnet']['primary_label']}: {LINKS['calendly']}")
    _summary_lines.append(f"Take the audit: {_CANONICAL_URL}/")
    _share_text = "\n".join(_summary_lines)
    # Escape for safe embedding in JS — prevent injection from company names
    _safe_share = json.dumps(_share_text)
    _frame(
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
    _frame(
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
                '  section.stMain > div.block-container {',
                '    max-width: 100% !important;',
                  // A little horizontal padding so the report still reads well
                  // if the visitor prints with page margins set to None.
                '    padding: 0 0.3cm !important;',
                '  }',
                '  iframe:not(.sa-radar-iframe) { display:none !important; }',
                '  div.stButton, div.stLinkButton { display:none !important; }',
                '  [data-testid="stExpander"].sa-print-hide { display:none !important; }',
                '  [data-testid="stExpander"] details[open] > summary { display:none !important; }',
                '  .sa-print-footer { display:block !important; }',
                '}'
              ].join('\\n');
              // Appended to BODY, not head. The app's base stylesheet is
              // injected by st.markdown into the body, so a <style> in <head>
              // loses to it on source order even though both use !important —
              // which is why the print rules for page background and column
              // width silently did nothing. Body-appended, they come last.
              pd.body.appendChild(s);
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
        "The Structural Advantage Index is the personal companion to this audit. Ten minutes. An operator archetype. "
        "The shape you bring to the work, named. Most operators find the two read differently when held side by side. "
        f"[Open the Index &rarr;]({_utm(LINKS['index'], 'audit_results', 'cross_tool')})"
    )

    # --- Save code (visible, not buried) ---
    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    st.markdown("### Save your results")
    st.markdown(
        "Copy your audit code below, or share a direct link. Use it to resume from any device, "
        "or paste it into the comparison tool on a future audit to track your progress."
    )
    st.markdown(
        f'<p class="sa-footnote">The code contains every answer you gave, and a shared link '
        f'carries them in the URL. Treat it like the report itself. '
        f'Rubric {RUBRIC_VERSION}.</p>',
        unsafe_allow_html=True,
    )
    _results_code = _encode_state()
    _safe_results_code = json.dumps(_results_code)
    _safe_canonical = json.dumps(_CANONICAL_URL)
    st.code(_results_code, language=None)
    _frame(
        f"""
        <style>
        body {{ margin:0; padding:0; background:transparent; }}
        button {{
          background:#14223D; color:#F4EFE6; border:none; padding:8px 18px;
          font-family:"Inter",system-ui,sans-serif; font-size:13px; font-weight:500;
          cursor:pointer; letter-spacing:0.02em; margin-right:8px;
        }}
        button:hover {{ background:#2A3758; }}
        .link-btn {{ background:transparent!important; color:#14223D!important; border:1px solid #14223D!important; }}
        .link-btn:hover {{ background:#EAE2D3!important; }}
        .ok {{ color:#8B6A3F; font-size:12px; margin-left:8px; font-family:"Inter",system-ui,sans-serif; }}
        </style>
        <button onclick="navigator.clipboard.writeText({_safe_results_code}).then(function(){{document.getElementById('rcp').textContent='Copied.'}})">
          Copy code
        </button><button class="link-btn" onclick="var u={_safe_canonical}+'/?code='+{_safe_results_code};navigator.clipboard.writeText(u).then(function(){{document.getElementById('rcp').textContent='Link copied.'}})">
          Copy link
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
                padded = prev_code.strip() + "=" * (-len(prev_code.strip()) % 4)
                compressed = base64.urlsafe_b64decode(padded)
                raw = zlib.decompress(compressed)
                prev_payload = json.loads(raw)
                # Temporarily set previous answers to compute results
                st.session_state.answers = prev_payload.get("a", {})
                st.session_state.industry = prev_payload.get("i", current_industry)
                prev_r = compute_results()
                _prev_rv = prev_payload.get("rv", "1.0.x")
                if _prev_rv != RUBRIC_VERSION:
                    st.warning(
                        f"That audit was scored on rubric {_prev_rv}; this one is {RUBRIC_VERSION}. "
                        "Question wording and scoring changed between them, so treat the "
                        "comparison as directional rather than exact."
                    )
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
            finally:
                st.session_state.answers = current_answers
                st.session_state.industry = current_industry

    st.markdown("<hr class='sa-rule'/>", unsafe_allow_html=True)
    _frame(
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
        'The Structural Audit &middot; ' + _CANONICAL_URL.replace('https://', '') + ' &middot; '
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
                          "audit_intent", "email_captured", "capture_email", "_ph_sent",
                          # Without these the new audit inherits the old one's
                          # start time and reports a nonsense duration.
                          "_audit_start", "_navigated", "_utm", "_saved_rubric_version"]:
                    if k in st.session_state:
                        del st.session_state[k]
                _init()
                # Clear localStorage so stale resume prompt doesn't appear on return
                _frame(
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
elif step == "gate":
    # Retired in 1.1.0. Save codes written before then can still carry it.
    st.session_state.step = "results"
    screen_results()
elif step == "results":
    screen_results()
else:
    go("intro")
