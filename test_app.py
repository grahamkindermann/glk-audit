"""
End-to-end test suite for The Structural Audit.

Run before every push:

    python3 test_app.py

Drives the real Streamlit app headlessly (streamlit.testing.v1.AppTest):
the full fifty-question flow, both scoring extremes, the insufficient-data
path, save/resume code round-trips, and the funnel analytics event sequence.
Network calls are stubbed; nothing leaves the machine and no test data
pollutes PostHog.
"""

import base64
import json
import os
import sys
import zlib

import requests

import rubric

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
INDUSTRY = "SaaS"
REVENUE = "$3M to $10M"

# Force analytics onto the stubbed-network path so the code runs end to end
# without touching the wire.
os.environ["POSTHOG_PROJECT_TOKEN"] = "test_token_never_used_on_wire"
os.environ["POSTHOG_HOST"] = "https://posthog.invalid"

# ---------------------------------------------------------------------------
# Network stub: record every outbound POST, return 200, never touch the wire.
# ---------------------------------------------------------------------------
SENT = []

class _FakeResponse:
    status_code = 200

def _fake_post(url, *args, **kwargs):
    SENT.append({"url": url, "json": kwargs.get("json")})
    return _FakeResponse()

requests.post = _fake_post

from streamlit.testing.v1 import AppTest  # noqa: E402  (after the stub, by design)


# ---------------------------------------------------------------------------
# Answer builders
# ---------------------------------------------------------------------------
def best_answer(q):
    """The answer that should score 1.0 for this question."""
    if q["type"] == "likert":
        return "1" if q.get("reverse") else "5"
    if q["type"] == "yesno":
        return "No" if q.get("reverse") else "Yes"
    bench = rubric.BENCHMARKS.get((INDUSTRY, q["id"]))
    if not bench:
        return None
    v = bench["p25"] if q.get("lower_is_better") else bench["p75"]
    return f"{v:g}"

def worst_answer(q):
    """The answer that should score 0.0 for this question."""
    if q["type"] == "likert":
        return "5" if q.get("reverse") else "1"
    if q["type"] == "yesno":
        return "Yes" if q.get("reverse") else "No"
    bench = rubric.BENCHMARKS.get((INDUSTRY, q["id"]))
    if not bench:
        return None
    v = bench["p75"] if q.get("lower_is_better") else bench["p25"]
    return f"{v:g}"


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------
def fresh_app():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    return at

def _heal_stale_nodes(at):
    """Work around an AppTest artifact, not an app bug.

    Navigation clicks end in an internal st.rerun(). AppTest merges the
    deltas of both script executions into one tree, so when the new screen
    renders FEWER elements than the old one, tail nodes from the old screen
    survive in the tree with no backing session state. Collecting their
    widget state raises KeyError before the next run can rebuild the tree.
    Seed a value on any such orphan so collection succeeds; the following
    clean run washes them out. The real browser never sees any of this."""
    for node in list(at.text_input):
        try:
            node.value
        except KeyError:
            node.set_value("")
    for node in list(at.radio):
        try:
            node.value
        except KeyError:
            try:
                node.set_value(node.options[0])
            except Exception:
                pass
    for node in list(at.button):
        try:
            node.value
        except KeyError:
            try:
                node.set_value(False)
            except Exception:
                pass
    for node in list(at.selectbox):
        try:
            node.value
        except KeyError:
            try:
                node.set_value(node.options[0])
            except Exception:
                pass

def run_clean(at):
    _heal_stale_nodes(at)
    at.run()
    return at

def click(at, key):
    """Click a button, then chase it with a neutral run so every assertion
    reads a tree built by a single clean script execution."""
    _heal_stale_nodes(at)
    at.button(key=key).click().run()
    run_clean(at)
    return at

def fill_context(at, company="Test Co"):
    click(at, "btn_begin")
    at.text_input[0].set_value(company)          # Company name
    at.selectbox[0].set_value(INDUSTRY)          # Industry
    at.selectbox[1].set_value(REVENUE)           # Revenue band
    at.text_input[1].set_value("Founder / CEO")  # Role
    run_clean(at)
    click(at, "ctx_next")
    return at

def fill_all_dimensions(at, answer_fn):
    for i, dim in enumerate(rubric.DIMENSIONS):
        for q in dim["questions"]:
            v = answer_fn(q)
            if v is None:
                continue
            if q["type"] in ("likert", "yesno"):
                at.radio(key=f"rad_{q['id']}").set_value(v)
            else:
                at.text_input(key=f"num_{q['id']}").set_value(v)
        run_clean(at)  # commit the answers, then navigate
        click(at, f"dim_next_{i}")
    return at

def page_text(at):
    return " ".join(str(m.value) for m in at.markdown)

def ss_get(at, key, default=None):
    """AppTest's session_state proxy has no .get(); emulate it."""
    try:
        return at.session_state[key]
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
RESULTS_SECTIONS = (
    "Dimension scores",
    "What is load-bearing right now",
    "What to do with this",
    "Share with your team",
    "Save your results",
    "Compare to a previous audit",
)

def test_full_run_best_answers_hits_durable():
    at = fresh_app()
    fill_context(at)
    fill_all_dimensions(at, best_answer)
    # The interstitial gate was retired in 1.1.0: the last dimension goes
    # straight to the full results.
    assert at.session_state["step"] == "results", f"expected results, got {at.session_state['step']}"
    text = page_text(at)
    assert "The audit is scored." not in text, "the retired gate screen came back"
    assert "No subscription. No upsell." not in text, "retired gate copy still present"
    assert "Durable" in text, "best answers must land in the Durable band"
    assert "100.0" in text, "overall score missing from results"
    for section in RESULTS_SECTIONS:
        assert section in text, f"results section missing: {section}"
    # A perfect run has no risks and no opportunities, so the 90-day plan
    # correctly stays hidden.
    assert "90-Day Focus Plan" not in text, "plan must not render without risks or opportunities"
    assert not at.exception, f"exceptions raised: {[str(e.value) for e in at.exception]}"
    print("PASS  full run, best answers -> Durable results")

def test_full_run_worst_answers_hits_critical():
    at = fresh_app()
    fill_context(at)
    fill_all_dimensions(at, worst_answer)
    assert at.session_state["step"] == "results"
    text = page_text(at)
    assert "Critical" in text, "worst answers must land in the Critical band"
    assert "0.0" in text, "overall score missing"
    assert "90-Day Focus Plan" in text, "a risk-heavy run must render the 90-day plan"
    assert not at.exception
    print("PASS  full run, worst answers -> Critical results")

def test_no_email_step():
    """v1.1.3 removed the email step: nothing may ask for an address or call Loops."""
    SENT.clear()
    at = fresh_app()
    fill_context(at, company="No Email Co")
    fill_all_dimensions(at, best_answer)
    assert at.session_state["step"] == "results"
    text = page_text(at)
    for retired in ("Get the follow-up", "Follow-up queued", "Send me the action plan",
                    "Two emails", "Email address", "Unsubscribe"):
        assert retired not in text, f"retired email copy still on the results page: {retired}"
    assert not any(i.key in ("capture_email", "capture_name") for i in at.text_input), \
        "an email field came back"
    assert not any(b.key == "btn_capture" for b in at.button), "the capture button came back"
    assert not [p for p in SENT if "loops.so" in p["url"]], "something called Loops"
    src = open(APP, encoding="utf-8").read()
    for term in ("loops.so", "LOOPS_API_KEY", "audit_completed", "email_captured"):
        assert term not in src, f"email integration still in app.py: {term}"
    assert 'LINKS["privacy"]' in src, "the privacy page must stay linked from the tool"
    assert not at.exception
    print("PASS  no email step: no field, no button, no Loops call; privacy still linked")

def test_no_newsletter_link():
    """v1.1.4 removed the Substack sentence: the posts are unpublished, so nothing may send readers there."""
    SENT.clear()
    at = fresh_app()
    fill_context(at, company="No Newsletter Co")
    fill_all_dimensions(at, best_answer)
    assert at.session_state["step"] == "results"
    text = page_text(at)
    for retired in ("subscribe to Structural Advantage", "the newsletter behind this audit", "substack.com"):
        assert retired not in text, f"retired newsletter copy still on the results page: {retired}"
    assert "What to do with this" in text, "the next-step section must stay"
    assert "substack" not in rubric.LINKS, "the Substack link is back in rubric.LINKS"
    assert 'LINKS["substack"]' not in open(APP, encoding="utf-8").read()
    assert not at.exception
    print("PASS  no newsletter link: results page and links table are clear of Substack")

def test_old_save_code_with_capture_flag_still_resumes():
    """Codes saved before v1.1.3 carry an "ec" key. It must be ignored, not fatal."""
    payload = {"s": "results", "c": "Old Code Co", "i": INDUSTRY, "r": REVENUE, "p": "", "d": 0,
               "a": {}, "ec": True, "rv": rubric.RUBRIC_VERSION}
    code = base64.urlsafe_b64encode(zlib.compress(json.dumps(payload).encode())).decode().rstrip("=")
    at = AppTest.from_file(APP, default_timeout=60)
    at.query_params["code"] = code
    at.run()
    assert not at.exception, f"old code raised: {[str(e.value) for e in at.exception]}"
    assert "email_captured" not in at.session_state, "the capture flag was restored"
    print("PASS  a pre-1.1.3 save code with the capture flag still loads")

def test_insufficient_data_path():
    at = fresh_app()
    fill_context(at, company="Skipper Co")
    for i in range(len(rubric.DIMENSIONS)):
        click(at, f"dim_skip_{i}")
    assert at.session_state["step"] == "results"
    assert any("Not enough of the audit" in str(w.value) for w in at.warning), \
        "insufficient-data warning missing"
    assert not at.exception
    print("PASS  all-skip run shows the guardrail warning")

def _encode_payload(payload):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode().rstrip("=")

def test_save_code_roundtrip_including_mod4_lengths():
    base_payload = {
        "s": "dim", "c": "Roundtrip Co", "i": INDUSTRY, "r": REVENUE,
        "p": "COO", "d": 2, "a": {"per_01": 4, "fin_01": 2},
        "hc": "25", "em": "18", "yo": "7", "oh": "55",
    }
    # Old codes (pre-R10) lack the ai/ts/ec fields — decoding must tolerate
    # that, and the old padding formula broke on codes whose length was a
    # multiple of four. Cover all reachable length residues.
    seen_residues = set()
    for pad in range(64):
        payload = dict(base_payload, c="Roundtrip Co" + "x" * pad)
        code = _encode_payload(payload)
        residue = len(code) % 4
        if residue in seen_residues:
            continue
        seen_residues.add(residue)
        at = fresh_app()
        at.text_input(key="resume_code_input").set_value(code)
        click(at, "btn_resume")
        assert at.session_state["step"] == "dim", \
            f"resume failed for code length {len(code)} (mod 4 = {residue})"
        assert at.session_state["dim_idx"] == 2
        assert at.session_state["answers"]["per_01"] == 4
        assert at.session_state["company"] == payload["c"]
        # Unpadded base64 lengths are always 0, 2, or 3 mod 4; 1 is impossible.
        if seen_residues == {0, 2, 3}:
            break
    assert 0 in seen_residues, "never produced a mod-4-length code; adjust the test"
    print(f"PASS  save-code round-trip across length residues {sorted(seen_residues)}")

def _banner_payload():
    return {
        "s": "dim", "c": "Banner Co", "i": INDUSTRY, "r": "$1M to $3M",
        "p": "", "d": 1, "a": {"per_01": 4, "per_02": 2},
        "hc": "", "em": "", "yo": "", "oh": "",
    }

def test_shared_link_shows_python_banner():
    code = _encode_payload(_banner_payload())
    at = AppTest.from_file(APP, default_timeout=60)
    at.query_params["code"] = code  # a shared permalink: no src, no go
    at.run()
    text = page_text(at)
    assert "This link contains a saved audit for" in text, "shared-link banner missing"
    assert "Banner Co" in text and "2 of 50" in text, "banner detail wrong"
    click(at, "btn_banner_resume")
    assert at.session_state["step"] == "dim"
    assert at.session_state["dim_idx"] == 1
    assert at.session_state["company"] == "Banner Co"
    print("PASS  shared ?code= link shows the banner and restores on click")

def test_local_resume_go_param_restores_immediately():
    code = _encode_payload(_banner_payload())
    at = AppTest.from_file(APP, default_timeout=60)
    at.query_params["code"] = code  # the injected JS banner's Resume link
    at.query_params["src"] = "ls"
    at.query_params["go"] = "1"
    at.run()
    # The user already clicked Resume in the browser banner; no second ask.
    assert at.session_state["step"] == "dim", f"expected dim, got {at.session_state['step']}"
    assert at.session_state["dim_idx"] == 1
    assert at.session_state["company"] == "Banner Co"
    print("PASS  in-browser Resume link (go=1) restores without a second confirm")

def test_funnel_events_fire_once():
    SENT.clear()
    at = fresh_app()
    fill_context(at)
    fill_all_dimensions(at, best_answer)
    events = [p["json"]["event"] for p in SENT if p["json"] and "event" in (p["json"] or {})]
    expected = (
        ["audit_started", "context_completed"]
        + ["dimension_completed"] * len(rubric.DIMENSIONS)
        + ["results_viewed"]
    )
    assert sorted(events) == sorted(expected), f"funnel mismatch: {sorted(events)}"
    # Rerun the results screen; nothing new may fire
    n = len(SENT)
    run_clean(at)
    events_after = [p["json"].get("event") for p in SENT if p["json"]]
    assert len(SENT) == n, f"events double-fired on rerun: {events_after[n:]}"
    print(f"PASS  funnel events fire exactly once ({len(events)} events)")

# ---------------------------------------------------------------------------
# Regression guards for the August 2026 audit. Each one locks in a fix that is
# invisible from the outside and easy to undo by accident.
# ---------------------------------------------------------------------------
def _oracle_score(q, ans):
    """Independent re-implementation of the scoring rule, used as an oracle.

    Deliberately NOT imported from app.py — the point is to check the app
    against a second statement of the rule, not against itself.
    """
    if ans is None or ans in ("N/A", ""):
        return None
    if q["type"] == "likert":
        raw = (float(ans) - 1.0) / 4.0
    elif q["type"] == "yesno":
        a = str(ans).strip().lower()
        raw = 1.0 if a.startswith("y") else (rubric.YESNO_PARTIAL_SCORE if a.startswith("p") else 0.0)
    else:
        b = rubric.BENCHMARKS.get((INDUSTRY, q["id"]))
        if not b:
            return None
        v, p25, p50, p75 = float(ans), b["p25"], b["p50"], b["p75"]
        if q.get("lower_is_better"):
            if v <= p25: raw = 1.0
            elif v >= p75: raw = 0.0
            elif v <= p50: raw = 1.0 - 0.5 * (v - p25) / (p50 - p25)
            else: raw = 0.5 - 0.5 * (v - p50) / (p75 - p50)
        else:
            if v >= p75: raw = 1.0
            elif v <= p25: raw = 0.0
            elif v >= p50: raw = 0.5 + 0.5 * (v - p50) / (p75 - p50)
            else: raw = 0.5 * (v - p25) / (p50 - p25)
    if q.get("reverse"):
        raw = 1.0 - raw
    return max(0.0, min(1.0, raw))

def _oracle(answers):
    """Return (overall, [(q, dim, score, lever)]) for a full answer set."""
    dims, scored = [], []
    for d in rubric.DIMENSIONS:
        tw = aw = ws = 0.0
        items = []
        for q in d["questions"]:
            w = float(q["weight"]); tw += w
            sc = _oracle_score(q, answers.get(q["id"]))
            if sc is not None:
                aw += w; ws += w * sc; items.append((q, d, sc))
        ok = tw > 0 and aw / tw >= rubric.MINIMUM_ANSWERED_FRACTION
        dims.append({"d": d, "aw": aw, "score": (ws / aw * 100) if ok else None})
        # Items from an unscored dimension are still findings; they just carry
        # lever 0, because an excluded dimension cannot move the overall.
        scored.extend(items)
    live = [x for x in dims if x["score"] is not None]
    if not live:
        return None, []
    tot_w = sum(x["d"]["weight"] for x in live)
    overall = sum(x["score"] * x["d"]["weight"] for x in live) / tot_w
    by_id = {x["d"]["id"]: x for x in dims}
    out = []
    for q, d, sc in scored:
        x = by_id[d["id"]]
        lever = 0.0
        if x["aw"] > 0 and x["score"] is not None:
            lever = ((1 - sc) * float(q["weight"]) / x["aw"]) * 100.0 * x["d"]["weight"] / tot_w
        out.append((q, d, sc, lever))
    out.sort(key=lambda t: (t[3], (1 - t[2]) * float(t[0]["weight"])), reverse=True)
    return overall, out

def _profile(likert, yesno, metric):
    """metric: 'best' | 'med' | 'worst', resolved per question direction."""
    a = {}
    for d in rubric.DIMENSIONS:
        for q in d["questions"]:
            if q["type"] == "likert":
                a[q["id"]] = likert
            elif q["type"] == "yesno":
                a[q["id"]] = yesno
            else:
                b = rubric.BENCHMARKS[(INDUSTRY, q["id"])]
                lo = q.get("lower_is_better", False)
                key = {"best": ("p25" if lo else "p75"),
                       "med": "p50",
                       "worst": ("p75" if lo else "p25")}[metric]
                a[q["id"]] = float(b[key])
    return a

def _band_of(score):
    for _bid, lo, hi, label in rubric.BANDS:
        if lo <= score < hi:
            return label
    return None

def test_no_vendor_or_legacy_hosts():
    """No user-facing string may point at the Streamlit or Netlify host.

    The custom-domain migration left three of these on the results page: the
    share summary, the Copy-link button, and the print footer -- exactly the
    three artefacts a user forwards to their board.
    """
    src = open(APP, encoding="utf-8").read()
    for host in ("structural-audit.streamlit.app", "structuraladvantageindex.netlify.app"):
        assert host not in src, f"vendor host still referenced in app.py: {host}"
    rub = open(os.path.join(os.path.dirname(APP), "rubric.py"), encoding="utf-8").read()
    for host in ("streamlit.app", "netlify.app"):
        assert host not in rub, f"vendor host still referenced in rubric.py: {host}"
    # The legacy-host redirect must carry the query string, or turning it on
    # discards every shared ?code= audit.
    assert "pw.location.search" in src, "legacy redirect drops the query string"
    print("PASS  no vendor or legacy hosts; legacy redirect preserves ?code=")

def test_no_reverse_scored_items():
    """A lone reverse-scored item among fifty is a mis-answer trap, not a
    validity check. If one is reintroduced, the Likert caption must change."""
    rev = [q["id"] for d in rubric.DIMENSIONS for q in d["questions"] if q.get("reverse")]
    assert not rev, f"reverse-scored items reintroduced without a UI cue: {rev}"
    print("PASS  no reverse-scored items")

def test_band_threshold_text_derives_from_bands():
    """The methodology text must not restate the thresholds as literals.

    BANDS uses half-open intervals, so a hardcoded 'Fragile (41-60)' left every
    band with nine tenths of a point displayed outside its stated range.
    """
    src = open(APP, encoding="utf-8").read()
    for stale in ('"Critical (0–40), "', '"Fragile (41–60), "', '"Functional (61–75), "'):
        assert stale not in src, f"hardcoded band range still present: {stale}"
    assert "for _bid, _lo, _hi, _label in BANDS:" in src, \
        "band threshold text is no longer derived from BANDS"
    # And no score can fall outside the band it is displayed in.
    for bid, lo, hi, label in rubric.BANDS:
        for probe in (lo, (lo + hi) / 2, hi - 0.1):
            assert _band_of(probe) == label, f"{probe} not in {label}"
    print("PASS  band threshold text derives from BANDS; no gaps")

def test_yesno_partial_credit():
    """'Partly' must score half, and must be reachable in the UI."""
    q = {"id": "x", "type": "yesno", "weight": 1.0}
    assert _oracle_score(q, "Yes") == 1.0
    assert _oracle_score(q, "No") == 0.0
    assert _oracle_score(q, rubric.YESNO_PARTIAL_LABEL) == rubric.YESNO_PARTIAL_SCORE
    src = open(APP, encoding="utf-8").read()
    assert 'options = ["Skip", "Yes", YESNO_PARTIAL_LABEL, "No"]' in src, \
        "the Partly option is not offered in the yes/no widget"
    # Partly (0.5) sits inside the opportunity window, so yes/no questions can
    # now surface as opportunities. Before this they never could.
    assert rubric.RISK_THRESHOLD <= rubric.YESNO_PARTIAL_SCORE < rubric.OPPORTUNITY_CEILING
    print("PASS  yes/no partial credit scores 0.5 and is reachable")

def test_median_business_is_not_critical():
    """A business at the industry median everywhere must not read Critical.

    Median inputs producing a bottom-band output was the calibration defect
    behind the (now removed) 'bottom 15% of businesses' claim.
    """
    overall, _ = _oracle(_profile(3, rubric.YESNO_PARTIAL_LABEL, "med"))
    assert overall is not None
    assert abs(overall - 50.0) < 0.01, f"median profile should score 50.0, got {overall:.2f}"
    assert _band_of(overall) != "Critical", "a median business still reads Critical"
    # Sanity: the ladder still discriminates at both ends.
    worst, _ = _oracle(_profile(1, "No", "worst"))
    best, _ = _oracle(_profile(5, "Yes", "best"))
    assert _band_of(worst) == "Critical", f"worst profile scored {worst:.1f}"
    assert _band_of(best) == "Durable", f"best profile scored {best:.1f}"
    print(f"PASS  median business scores {overall:.1f} ({_band_of(overall)}); "
          f"worst {worst:.1f}, best {best:.1f}")

def test_risk_ranking_uses_dimension_weight():
    """The item named 'Biggest lever' must actually be the biggest lever.

    Risks used to be ranked by (1 - score) * question_weight, ignoring the
    dimension weight that the callout one paragraph below DID apply -- so the
    two disagreed, and the disagreement drove the 90-day plan.
    """
    answers = _profile(3, "No", "med")
    overall, ranked = _oracle(answers)
    risks = [t for t in ranked if t[2] < rubric.RISK_THRESHOLD]
    assert risks, "profile produced no risks; test is not exercising the path"
    top_by_lever = risks[0]
    top_by_old_rule = max(risks, key=lambda t: (1 - t[2]) * float(t[0]["weight"]))
    # Drive the real app to the same state and read what it reports.
    payload = {"s": "results", "c": "Lever Co", "i": INDUSTRY, "r": REVENUE, "p": "CEO",
               "d": len(rubric.DIMENSIONS), "a": answers, "hc": "", "em": "", "yo": "",
               "oh": "", "ai": "", "ts": None, "ec": None, "rv": rubric.RUBRIC_VERSION}
    at = AppTest.from_file(APP, default_timeout=60)
    at.query_params["code"] = _encode_payload(payload)
    at.query_params["src"] = "ls"
    at.query_params["go"] = "1"
    at.run()
    text = page_text(at)
    assert "Biggest lever." in text, "biggest-lever callout missing"
    lever_para = [str(m.value) for m in at.markdown if "Biggest lever." in str(m.value)][0]
    assert top_by_lever[0]["text"] in lever_para, (
        f"callout names the wrong question.\n"
        f"  reported : {lever_para[:160]}\n"
        f"  expected : {top_by_lever[0]['id']} ({top_by_lever[3]:.2f} pts)")
    if top_by_old_rule[0]["id"] != top_by_lever[0]["id"]:
        print(f"      (old rule would have named {top_by_old_rule[0]['id']} at "
              f"{top_by_old_rule[3]:.2f} pts vs the true {top_by_lever[3]:.2f})")
    print(f"PASS  biggest lever is {top_by_lever[0]['id']} ({top_by_lever[3]:.2f} pts)")

def test_partial_dimension_still_surfaces_its_risks():
    """A half-answered dimension is excluded from the SCORE, not from the report.

    It would be worse than useless to hide "tax filings are not current"
    because the visitor only got through half of the Finance questions.
    """
    answers = _profile(5, "Yes", "best")          # strong everywhere...
    fin = [d for d in rubric.DIMENSIONS if d["id"] == "finance"][0]
    for q in fin["questions"][3:]:                # ...but Finance half-abandoned
        answers[q["id"]] = "N/A"
    answers["fin_01"] = 1                         # with one severe gap left in
    answers["per_01"] = 2                         # and a real gap that IS scored
    overall, ranked = _oracle(answers)
    by_id = {t[0]["id"]: t for t in ranked}
    ids = [t[0]["id"] for t in ranked]
    assert "fin_01" in ids, "a risk in an unscored dimension was dropped"
    assert by_id["fin_01"][3] == 0.0, \
        "an excluded dimension must not claim it can move the overall score"
    assert by_id["per_01"][3] > 0.0, "a scored gap should carry a real lever"
    assert ids.index("per_01") < ids.index("fin_01"), \
        "lever-0 items must rank below anything that can move the score"
    print("PASS  risks in an unscored dimension surface, ranked below levered ones")

def test_css_selectors_match_current_streamlit():
    """Streamlit renamed section.main to section.stMain at 1.36.

    Three CSS rules and the whole print stylesheet still targeted the old
    name, so the 760px measure and the print layout silently did nothing.
    """
    src = open(APP, encoding="utf-8").read()
    assert "section.main" not in src, "stale section.main selector still present"
    assert src.count("section.stMain > div.block-container") >= 3
    # hidden keeps the label box in the layout; collapsed removes it. Measured
    # at 51px per Likert question, thirty times over.
    assert 'label_visibility="hidden"' not in src, "label_visibility=hidden reintroduced"
    assert src.count('label_visibility="collapsed"') >= 3
    # .sa-lede loses to the generic `p {...!important}` rule without this.
    assert 'font-size: 1.3rem !important' in src, ".sa-lede is overridable again"
    print("PASS  CSS selectors, label visibility and .sa-lede specificity")

def test_rubric_integrity():
    total = sum(len(d["questions"]) for d in rubric.DIMENSIONS)
    assert total == 50, f"question count drifted: {total}"
    for d in rubric.DIMENSIONS:
        for q in d["questions"]:
            if q["type"] in ("number", "percent"):
                for ind in rubric.INDUSTRY_LIST:
                    assert (ind, q["id"]) in rubric.BENCHMARKS, \
                        f"missing benchmark: ({ind}, {q['id']})"
    print("PASS  rubric integrity: 50 questions, full benchmark coverage")

def _captions_on_dimension(at, dim_index):
    """Advance a fresh run to one dimension and return its caption strings."""
    for i in range(dim_index):
        run_clean(at)
        click(at, f"dim_next_{i}")
    return [str(c.value) for c in at.caption]

def test_benchmark_caption_escapes_dollars_and_singularises_units():
    """Streamlit's markdown reads a matched pair of "$" as LaTeX and swallows
    the text between them, which turned the CAC benchmark line into a code
    box. Every dollar in a caption must be backslash-escaped. Separately,
    several benchmarks sit at 1, so " workflows"/" tools"/" days" have to
    drop the s."""
    src = open(APP, encoding="utf-8").read()
    assert 'f"${v:,.0f}"' not in src, "unescaped $ in the benchmark formatter"
    assert 'f"\\\\${v:,.0f}"' in src, "CAC benchmark no longer escapes its dollar signs"

    sales_idx = next(i for i, d in enumerate(rubric.DIMENSIONS)
                     if any(q["id"] == "sal_q_cac" for q in d["questions"]))
    at = fresh_app()
    fill_context(at)
    caps = _captions_on_dimension(at, sales_idx)
    cac = [c for c in caps if "25th" in c and "Median" in c]
    assert cac, f"CAC benchmark caption not rendered; captions were {caps}"
    line = cac[0]
    assert "\\$" in line, f"dollar signs not escaped in: {line}"
    assert line.count("$") == line.count("\\$"), f"a naked $ survives in: {line}"
    print("PASS  benchmark caption escapes every dollar sign")

def test_benchmark_units_are_singular_at_one():
    """Professional Services sits at 1 AI workflow at the 25th percentile."""
    ai_idx = next(i for i, d in enumerate(rubric.DIMENSIONS)
                  if any(q["id"] == "ai_q_num_ai_workflows" for q in d["questions"]))
    at = fresh_app()
    click(at, "btn_begin")
    at.text_input[0].set_value("Test Co")
    at.selectbox[0].set_value("Professional Services")
    at.selectbox[1].set_value(REVENUE)
    at.text_input[1].set_value("Founder / CEO")
    run_clean(at)
    click(at, "ctx_next")
    caps = _captions_on_dimension(at, ai_idx)
    wf = [c for c in caps if "workflow" in c]
    assert wf, f"AI workflow benchmark caption not rendered; captions were {caps}"
    assert "1 workflows" not in wf[0], f"plural at one: {wf[0]}"
    assert "1 workflow " in wf[0] or wf[0].rstrip().endswith("1 workflow"), \
        f"expected a singular unit at 1 in: {wf[0]}"
    print("PASS  benchmark units read singular at one")

def test_toc_scroll_survives_the_sandbox():
    """Chrome drops any smooth scroll a sandboxed component iframe requests on
    its parent document, so the old scrollIntoView({behavior:'smooth'}) call
    made every table-of-contents link a no-op. Verified live on 2026-08-27."""
    src = open(APP, encoding="utf-8").read()
    assert "scrollIntoView({{behavior:'smooth'" not in src, \
        "TOC is back on a smooth scrollIntoView, which a sandboxed iframe cannot do"
    assert "m.scrollTop = from + dist * e" in src, "TOC scroll animation missing"
    assert "m.scrollTop = to;" in src, "TOC scroll has no non-animated fallback"
    print("PASS  TOC scroll does not rely on a sandbox-blocked smooth scroll")

def test_copy_conventions():
    src = open(APP, encoding="utf-8").read()
    # Canonical duration is fifteen to twenty minutes, shared with the site.
    # If this changes, change the site the same day.
    assert "Fifteen to twenty minutes" in src, "canonical duration missing from the intro"
    assert "· Fifteen minutes ·" not in src, "solo fifteen-minute claim conflicts with the site"
    assert "Fifty-one" not in src, "the rubric holds fifty questions; keep the count honest"
    assert 'sa-meta">Step 1 of 8 .' not in src, "middot convention: no period separators"
    assert 'The Structural Audit . ' not in src, "middot convention: no period separators"
    print("PASS  copy conventions: canonical duration, honest count, middot separators")


if __name__ == "__main__":
    tests = [
        test_rubric_integrity,
        test_copy_conventions,
        test_toc_scroll_survives_the_sandbox,
        test_benchmark_caption_escapes_dollars_and_singularises_units,
        test_benchmark_units_are_singular_at_one,
        test_no_vendor_or_legacy_hosts,
        test_no_reverse_scored_items,
        test_band_threshold_text_derives_from_bands,
        test_yesno_partial_credit,
        test_median_business_is_not_critical,
        test_risk_ranking_uses_dimension_weight,
        test_partial_dimension_still_surfaces_its_risks,
        test_css_selectors_match_current_streamlit,
        test_full_run_best_answers_hits_durable,
        test_full_run_worst_answers_hits_critical,
        test_no_email_step,
        test_no_newsletter_link,
        test_old_save_code_with_capture_flag_still_resumes,
        test_insufficient_data_path,
        test_save_code_roundtrip_including_mod4_lengths,
        test_shared_link_shows_python_banner,
        test_local_resume_go_param_restores_immediately,
        test_funnel_events_fire_once,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    if failed:
        print(f"\n{failed} TEST(S) FAILED — do not push.")
        sys.exit(1)
    print("\nALL ASSERTIONS PASSED — safe to push.")
