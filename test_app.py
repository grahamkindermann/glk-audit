"""
End-to-end test suite for The Structural Audit.

Run before every push:

    python3 test_app.py

Drives the real Streamlit app headlessly (streamlit.testing.v1.AppTest):
the full fifty-question flow, the soft gate, both scoring extremes, the
insufficient-data path, save/resume code round-trips, and the funnel
analytics event sequence. Network calls are stubbed; nothing leaves the
machine and no test data pollutes PostHog or Loops.
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

# Force both integrations onto the stubbed-network path so the capture and
# analytics code runs end to end without touching the wire.
os.environ["LOOPS_API_KEY"] = "test_key_never_used_on_wire"
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
    "Get the follow-up",
    "What to do with this",
    "Share with your team",
    "Save your results",
    "Compare to a previous audit",
)

def test_full_run_best_answers_hits_durable():
    at = fresh_app()
    fill_context(at)
    fill_all_dimensions(at, best_answer)
    # Soft gate must appear with the score teaser
    assert at.session_state["step"] == "gate", f"expected gate, got {at.session_state['step']}"
    text = page_text(at)
    assert "The audit is scored." in text, "gate teaser headline missing"
    assert "100.0" in text, "gate should tease the overall score"
    assert "No subscription. No upsell." in text, "gate honesty footnote missing"
    # Decline path: full results, nothing withheld
    click(at, "btn_gate_skip")
    assert at.session_state["step"] == "results"
    assert ss_get(at, "gate_declined") is True
    text = page_text(at)
    assert "Durable" in text, "best answers must land in the Durable band"
    assert "100.0" in text, "overall score missing from results"
    for section in RESULTS_SECTIONS:
        assert section in text, f"results section missing: {section}"
    # A perfect run has no risks and no opportunities, so the 90-day plan
    # correctly stays hidden.
    assert "90-Day Focus Plan" not in text, "plan must not render without risks or opportunities"
    assert not at.exception, f"exceptions raised: {[str(e.value) for e in at.exception]}"
    print("PASS  full run, best answers -> gate -> decline -> Durable results")

def test_full_run_worst_answers_hits_critical():
    at = fresh_app()
    fill_context(at)
    fill_all_dimensions(at, worst_answer)
    assert at.session_state["step"] == "gate"
    click(at, "btn_gate_skip")
    text = page_text(at)
    assert "Critical" in text, "worst answers must land in the Critical band"
    assert "0.0" in text, "overall score missing"
    assert "90-Day Focus Plan" in text, "a risk-heavy run must render the 90-day plan"
    assert not at.exception
    print("PASS  full run, worst answers -> Critical results")

def test_gate_email_optin_reaches_loops_with_name():
    SENT.clear()
    at = fresh_app()
    fill_context(at, company="Optin Co")
    fill_all_dimensions(at, best_answer)
    assert at.session_state["step"] == "gate"
    at.text_input(key="gate_name").set_value("Graham Kindermann")
    at.text_input(key="gate_email").set_value("test@example.com")
    click(at, "btn_gate_send")
    assert at.session_state["step"] == "results"
    assert ss_get(at, "email_captured") is True
    assert ss_get(at, "gate_done") is True
    loops_calls = [p for p in SENT if "loops.so" in p["url"] and p["json"] and "email" in p["json"]]
    assert loops_calls, "no Loops contact call recorded"
    payload = loops_calls[0]["json"]
    assert payload["firstName"] == "Graham", f"firstName wrong: {payload}"
    assert payload["company"] == "Optin Co"
    text = page_text(at)
    assert "Follow-up queued" in text, "footer should confirm the follow-up"
    assert not any(b.key == "btn_capture" for b in at.button), \
        "footer must not re-ask for an email after the gate captured one"
    assert not at.exception
    print("PASS  gate opt-in reaches Loops with name; footer confirms, no re-ask")

def test_gate_rejects_invalid_email():
    at = fresh_app()
    fill_context(at)
    fill_all_dimensions(at, best_answer)
    at.text_input(key="gate_email").set_value("not-an-email")
    click(at, "btn_gate_send")
    assert at.session_state["step"] == "gate", "invalid email must not pass the gate"
    assert not ss_get(at, "email_captured")
    print("PASS  gate rejects an invalid email and stays put")

def test_insufficient_data_path():
    at = fresh_app()
    fill_context(at, company="Skipper Co")
    for i in range(len(rubric.DIMENSIONS)):
        click(at, f"dim_skip_{i}")
    # Gate must step aside when there is nothing to tease
    assert at.session_state["step"] == "results"
    assert any("Not enough of the audit" in str(w.value) for w in at.warning), \
        "insufficient-data warning missing"
    assert not at.exception
    print("PASS  all-skip run bypasses the gate and shows the guardrail warning")

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

def test_resume_banner_via_query_param():
    payload = {
        "s": "dim", "c": "Banner Co", "i": INDUSTRY, "r": "$1M to $3M",
        "p": "", "d": 1, "a": {"per_01": 4, "per_02": 2},
        "hc": "", "em": "", "yo": "", "oh": "",
    }
    code = _encode_payload(payload)
    at = AppTest.from_file(APP, default_timeout=60)
    at.query_params["code"] = code
    at.query_params["src"] = "ls"
    at.run()
    text = page_text(at)
    assert "This browser holds a saved audit for" in text, "banner missing"
    assert "Banner Co" in text and "2 of 50" in text, "banner detail wrong"
    click(at, "btn_banner_resume")
    assert at.session_state["step"] == "dim"
    assert at.session_state["dim_idx"] == 1
    assert at.session_state["company"] == "Banner Co"
    print("PASS  resume banner restores a saved audit from the query param")

def test_funnel_events_fire_once():
    SENT.clear()
    at = fresh_app()
    fill_context(at)
    fill_all_dimensions(at, best_answer)
    click(at, "btn_gate_skip")
    events = [p["json"]["event"] for p in SENT if p["json"] and "event" in (p["json"] or {})]
    expected = (
        ["audit_started", "context_completed"]
        + ["dimension_completed"] * len(rubric.DIMENSIONS)
        + ["gate_viewed", "gate_declined", "results_viewed"]
    )
    assert sorted(events) == sorted(expected), f"funnel mismatch: {sorted(events)}"
    # Rerun the results screen; nothing new may fire
    n = len(SENT)
    run_clean(at)
    events_after = [p["json"].get("event") for p in SENT if p["json"]]
    assert len(SENT) == n, f"events double-fired on rerun: {events_after[n:]}"
    print(f"PASS  funnel events fire exactly once ({len(events)} events)")

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

def test_copy_conventions():
    src = open(APP, encoding="utf-8").read()
    assert "Fifteen to twenty" not in src, "duration must be the canonical fifteen minutes"
    assert "Fifty-one" not in src, "the rubric holds fifty questions; keep the count honest"
    assert 'sa-meta">Step 1 of 8 .' not in src, "middot convention: no period separators"
    assert 'The Structural Audit . ' not in src, "middot convention: no period separators"
    print("PASS  copy conventions: canonical duration, honest count, middot separators")


if __name__ == "__main__":
    tests = [
        test_rubric_integrity,
        test_copy_conventions,
        test_full_run_best_answers_hits_durable,
        test_full_run_worst_answers_hits_critical,
        test_gate_email_optin_reaches_loops_with_name,
        test_gate_rejects_invalid_email,
        test_insufficient_data_path,
        test_save_code_roundtrip_including_mod4_lengths,
        test_resume_banner_via_query_param,
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
