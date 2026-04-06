# Structural Advantage — Business Audit Tool

A Streamlit-based self-assessment that scores a business across six structural dimensions — Personnel & Org, Accounting & Finance, Software Stack, AI Readiness, Sales & Marketing, and Operations & Process — and produces a printable PDF report with an overall score, per-dimension scores, a radar chart, top risks, and mode-dependent next steps. Built for US-based owner-operators in the $2M–$20M revenue range. Runs in two modes: a free **lead magnet** version surfaced from the Structural Advantage Substack, and a fuller **advisory** version used as a paid deliverable for GLK Holdings clients.

## Local run

Requires Python 3.11 or newer.

```
git clone <this-repo>
cd glk-audit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will open the app at `http://localhost:8501`. The flow is firmographics → six dimension screens → results, with a PDF download button on the results page.

## Modes

The `MODE` flag at the top of `rubric.py` controls what the report contains. Values:

- `"lead_magnet"` — the free version. The PDF shows the overall score, per-dimension scores, the radar chart, and the top three risks, then closes with a prominent CTA block (headline, Calendly button, secondary Substack link). Opportunities and written recommendations are hidden.
- `"advisory"` — the paid version. The PDF shows everything in the lead-magnet version except the CTA, plus a top-three opportunities section (green accent) and a "Recommended Next Steps" section listing each opportunity's recommendation. The cover subtitle changes to "Confidential Advisory Audit" and the results page adds a "Prepared for [company name]" caption.

Change `MODE` in `rubric.py` and restart the app to switch. The flag is read once per process.

## Editing the rubric

All scoring content lives in `rubric.py`. Nothing in `app.py`, `scoring.py`, or `report.py` needs to change when you tune the audit.

- **`DIMENSIONS`** — list of six dimensions. Each has a raw `weight` (normalized to sum to 6.0 at runtime by `scoring.normalize_weights`) and a list of `questions`. Edit weights to rebalance which dimensions drive the overall score.
- **Questions** inside each dimension — each has `id`, `text`, `type` (`"likert"` or `"yesno"`), within-dimension `weight`, a `reverse` flag for inverted scoring, `allow_na`, and three copy fields: `risk_copy`, `opportunity_copy`, `recommendation`. Bump `RUBRIC_VERSION` whenever you change questions, weights, or reverse flags so generated reports can be traced back to the rubric that produced them.
- **`BANDS`** — five score tiers (`critical`, `fragile`, `functional`, `strong`, `durable`) defined as half-open intervals. Downstream code keys off the band id; labels can be edited freely.
- **`BAND_NARRATIVE`** — two-sentence executive-summary interpretation per band id, shown in the PDF exec summary only. Tune the voice here.
- **`CTA`** — headline and URLs per mode. **Swap the Calendly placeholder URL (`https://calendly.com/glk-holdings/structural-review`) before shipping.** Do this in both the `lead_magnet` and `advisory` entries.
- **`FIRMOGRAPHICS`** — intake fields on the first screen. Not scored, but included in the JSON export and printed on the PDF cover.

## Deploy to Streamlit Cloud

Push the `glk-audit/` directory to a GitHub repo, then on [share.streamlit.io](https://share.streamlit.io) connect the repo, select `app.py` as the main file, pin the Python version to 3.11 or newer, and deploy. Streamlit Cloud reads `requirements.txt` automatically and picks up the theme from `.streamlit/config.toml`. No environment variables, secrets, or database configuration are required — the app is fully stateless and writes nothing to disk beyond the tempfile used for PDF generation.

## File map

- `rubric.py` — all scoring content: dimensions, questions, weights, bands, band narratives, CTA, brand strings, firmographics intake fields, `MODE` flag, `RUBRIC_VERSION`.
- `scoring.py` — pure scoring functions: `normalize_weights`, `score_question`, `score_dimension`, `score_overall`, `assign_band`, `select_top_risks`, `select_top_opportunities`, `run_audit`. No Streamlit imports.
- `report.py` — PDF builder via ReportLab + matplotlib radar chart. Pure `build_pdf(audit_result, firmographics, output_path, mode=None)` interface. Running this file directly regenerates the two sample PDFs.
- `app.py` — Streamlit UI: multi-step flow, session state, progress bar, completion-gated Next button, results screen, PDF download button.
- `test_scoring.py` — smoke test for the scoring engine. Two deterministic test functions; run with `python3 test_scoring.py`.
- `sample_lead_magnet.pdf` — reference PDF generated from the deterministic test answer set in lead-magnet mode.
- `sample_advisory.pdf` — reference PDF in advisory mode.
- `requirements.txt` — pinned Python dependencies.
- `.streamlit/config.toml` — Streamlit theme (navy primary, off-white background, serif font) matching the PDF brand palette.
